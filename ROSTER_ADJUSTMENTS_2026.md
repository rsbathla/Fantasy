# 2026 Roster Adjustments — Offense Movers + Defense Reweight

**Question this answers:** *"Are you adjusting for 2026 rosters, or using 2025 raw data relabeled 2026?"*

**Answer:** The model now adjusts both sides for 2026 rosters. Before this work the **identity/context** layer was 2026 (team from the live ADP board, schedule, team volume, win totals, rookies) but two role-defining layers were silently stale or broken. Both are fixed and verified below.

---

## Fix 1 — Offense mover usage re-projection (`reproject_movers.py`)

**Problem.** The feature store keys 2025 usage (`tgt_share`, `carry_share`, `tgt_pg`, `car_pg`, `rec_pg`) by player *name*, so a player who changed teams still carried the role he had on his **old** offense. `build_features.py` flagged movers but never re-cast their usage.

**Method.** For each genuine mover (normalized `team25 != team`):

| Path | When | Projection |
|---|---|---|
| `reproj_clay` | Clay 2026 share available | share = Clay 2026 share; per-game = share × **new-team** volume (`tm_pass_att`, `tm_plays`) |
| `reproj_carry` | Clay share missing | carry the player's **2025 share** onto new-team volume (role continuity, fixes team/pace context only) |
| `moved_to_FA` | new team = FA | no NFL role to project — flagged, raw kept, not used |

- **Portable skill traits left untouched** (aDOT, YPRR, EPA, man/zone): these travel with the player; only *usage/volume* is re-cast.
- **Raw preserved** under `*_25raw`; re-projection always reads from raw → **idempotent** (verified across 4 runs).
- **Provenance** on every skill player: `usage_src` ∈ {`reproj_clay`, `reproj_carry`, `moved_to_FA`, `2025_actual`} and `mover_conf` ∈ {high, med, low}.
- **Audit:** `boom/movers_reprojection.json` (per-mover raw → 2026).

**Result:** 52 movers — 36 `reproj_clay`, 9 `reproj_carry`, 7 FA. Spot-checks: Pacheco KC→DET 9.8%→4.0% target share (Clay sees him behind Gibbs); Waddle MIA→DEN 6.2→7.0 tgt/g (higher-pass offense); Kyler Murray ARI→MIN rushing re-cast 5.8→6.4 car/g; A.J. Brown PHI→NE 8.0→7.7 tgt/g.

**Wired:** `refactor/pipeline.py` after `reweight_defense_2026`, before `dfs_scenarios` (so fusion / gameplan / personnel consume re-projected usage).

---

## Fix 2 — Defense roster-adjustment (repair + bridge, not a rebuild)

**The truth:** the roster-adjustment engine **already existed** — `reweight_defense_2026.py` reassigns ~72 sourced 2026 defensive moves (Myles Garrett→LAR, Dexter Lawrence→CIN, McDuffie+Watson+Sneed→LAR, the Jets' haul, etc.), recomputes 32-team unit percentiles, and writes move-aware `*_2026` fields to `defense.json`. The fusion/DFS side was genuinely roster-adjusted. Three real defects were hiding it:

1. **`defense.json` was corrupted** — truncated mid-array (the recurring large-file write issue). → Hardened the prior-load against a bad/corrupt file (falls back to backup), regenerated clean.
2. **The `_2025` reference was contaminated** — the script read its *own previous 2026 output* as the "2025" baseline, so every `2025→2026` delta showed `0.0` and it *looked* like nothing changed. → Now stores the **true no-moves 2025 baseline** it already computes internally.
3. **The bridge to the boom side wasn't in any pipeline** — `defense_2026_matchup.json` (what the boom matchup engine reads) is built from `defense.json`, but only by a `dfs_review` script that no pipeline called, so the boom side could read a **stale** table. → New `sync_boom_defense.py` refreshes it, **wired into `boom_pipeline.py` before `boom_foundation`**.

**Verification (true 2025 → 2026, 29/32 teams move):**

- Coverage: **KC 60.9 → 20.3** (lost McDuffie/Cook/Gilman), **NYJ 1.6 → 32.8** (Fitzpatrick/Wright/Belton), **BUF 54.7 → 82.8** (Gardner-Johnson/Stone/Alford).
- Pass-rush: **CLE 92.2 → 67.2** (Garrett out), **LAR 79.7 → 95.3** (Garrett in), **TB +26.5**.
- Run-def: **CHI −56.3**, **NYJ/BUF +43.7**.

The boom matchup file now equals the move-aware `defense.json` canonical percentiles (verified: KC cov = 20.3 on both sides).

---

## What is 2026-adjusted now vs intentionally 2025

**2026-adjusted:** team affiliation (live ADP board) · offense usage role for movers (re-projected) · team volume/pace/TD ranks · schedule + opponents · **defense coverage / pass-rush / run percentiles (move-aware, ~72 sourced moves)** · win totals · rookie class.

**Kept as 2025 by design (portable player skill):** aDOT, YPRR, EPA, separation, man/zone splits — efficiency travels with the player; re-casting it would inject noise. `dk_mean25` is a labeled 2025 outcome.

**Known gaps (documented, not hidden):**
- Defensive **man-rate / sack-rate scheme tendencies** still come from 2025 charting (coach/scheme-stable, low churn).
- **Rookie DB → NFL-team** mapping is omitted by best-ball boards, so incoming rookie corners add replacement-level to their team's coverage (grades staged in `boom/rookie_db_grades.json`, ready when a map is supplied).
- 5 movers in the MOVES map were unmatched in the SIS CSVs (Danna ×2, PJ Locke, Tim Settle, Colby Wooden) — no 2025 PS to move; negligible.
- Year-over-year defense regression-to-mean is **not** applied (the reweight is an accounting reweight, not a refit) — a documented future option, deliberately left off to avoid an untested weight.

---

## Re-run (user's machine)

Both stages are now in the pipelines, so a normal full refresh applies everything:

```powershell
python refactor\pipeline.py      # ... reweight_defense_2026 -> reproject_movers -> fusion/gameplan/personnel
python boom_pipeline.py          # sync_boom_defense -> boom_foundation -> ... (boom matchups now move-aware)
python command_center.py
```

## Bug fixes shipped alongside
- `personnel.py`: `bool(p.get('mover'))` treated the CSV-stringified `"False"` as truthy → tagged **every** player "[incoming]". Now parses the flag robustly.
- `reweight_defense_2026.py`: corruption-tolerant prior-load; true-2025 baseline; honest deltas in its report.

---

# v2 — Defense normalization upgrade + rookies (replaces the raw Points-Saved sum)

Two follow-ups to the defense side, per request: *normalize it better* and *include rookies properly*.

## Normalization: snap-weighted rate, not a counting-stat sum
The old engine summed each team's defenders' **Points Saved** — a counting stat measured vs zero, so depth/volume inflated it and a mover's whole total got transplanted to his new team. The new engine (`normalize_defense_2026.py`) computes each unit as the **snap-weighted mean of PAA-per-play** (Points Above Average per snap) over the projected 2026 roster:

```
team_unit_strength = Σ(PAA_per_play_i × snaps_i) / Σ(snaps_i)
```

So a player's **quality (rate)** travels with him, **weighted by his projected role (snaps)**. Movers carry their rate + snaps to the 2026 team; percentiles are recomputed across 32 teams. This is the defensive analogue of the offense mover re-projection (transplant the rate, apply the new role). `reweight_defense_2026.py` is retained only as the curated ~72-move MOVES-map source that the new engine imports.

## Rookies: draft-round curves ("NFL effect by round") + college blend
Rookies previously added nothing. Now every drafted defender (`sis_value/draft_2026.csv`, pulled from Pro-Football-Reference) is folded into his NFL team, projected by:

- **Snaps** from a `snap_by_round` curve, and **rate** from an `nfl_paa_by_round` curve, both calibrated to the **2025 rookie class** (joined to `sis_value/draft_2025.csv`). The observed signal is intuitive: rookie snaps decline by round, and rookie PAA/play sits at/below the veteran baseline and worsens by round — i.e., draft capital predicts both playing time and (lower) production.
- For rookie **DBs**, the round rate is nudged ±0.004 by their **college coverage grade** (`rookie_db_grades.json`).

Curves (snaps | PAA/play), as computed:

| Unit | R1 | R2 | R3 |
|---|---|---|---|
| coverage | 365 / −0.0056 | 340 / −0.0097 | 332 / −0.0083 |
| pass_rush | 364 / ~0 | 364 / ~0 | 326 / ~0 |
| run_def | 320 / −0.0063 | 320 / −0.0009 | 316 / +0.0033 |

## Honest limitations (what would sharpen this)
- **Sample:** SIS unit files are **top-200 leaderboards for 2025 only**, so the rookie sample is 9–14/unit. The round curves are therefore **shrunk priors** (k=4 pseudo-obs toward the overall-rookie median, monotone-smoothed), not fitted per-cell values.
- **2024 class:** adding the second rookie class needs a **SIS NFL 2024 defensive Value pull** (the user's SIS session). The curve builder accepts a second season with no code change.
- **Roster completeness:** top-200 omits deep rotation; the snap-weighted *mean* is robust to this (low-snap depth barely moves it), but full rosters would be cleaner.
- **Draft pull truncated at round 5** (rounds 6–7 add negligible projected snaps).

## Files
`normalize_defense_2026.py` (new engine, wired into `refactor/pipeline.py`), `sis_value/draft_2026.csv`, `sis_value/draft_2025.csv`. Canonical `defense.json` percentiles are now rate+rookie based; `*_pctl_2025` is the no-moves rate baseline, `*_rate_2026` the raw snap-weighted rate, `rookies_2026` the folded-in rookies (name, pos, unit, round, projected rate).

---

# v3 — 2024 class added; the draft-round finding (snaps stable, rate is not)

Pulled the **2024** NFL defensive Value (all 3 units, via the capture-replay puller) and the 2024 draft (PFR via the browser, after Cloudflare). With two rookie classes instead of one:

**Snaps-by-round is a real, stable signal** — earlier picks play more, both years (coverage R1≈480–580 snaps tapering to ~360 by R3+). Kept as the rookie playing-time prior.

**Production-rate-by-round is NOT stable — it flips sign between classes:**

| rookie median PAA/play | 2024 | 2025 |
|---|---|---|
| coverage | +0.011 | −0.008 |
| pass rush | +0.006 | ~0.000 |
| run def | +0.010 | −0.004 |

The 2024 class (Verse, Latu, Q. Mitchell, DeJean, Newton) played *above* average as rookies; the 2025 class slightly below. At n=2–8 per round-cell the per-round rate gradient I'd derived from 2025 alone **did not replicate** — it was one-year overfit.

**Correction applied** in `normalize_defense_2026.py`: rookies are now modeled at **one pooled ~league-average rate** per unit (capped at the current veteran baseline), with **playing time scaled by draft round** and the **DB college grade** as the only rate differentiator. Net: rookies are average-rate players taking round-appropriate snaps — not a fabricated drag. Movers still drive the team deltas.

**Meta-lesson:** single-season defensive signals are low-stickiness and easy to overfit — relevant to any other one-year-trained piece in the system. Files added: `sis_value/{pass_defense,pass_rush,run_defense}_2024.csv`, `sis_value/draft_2024.csv`.
