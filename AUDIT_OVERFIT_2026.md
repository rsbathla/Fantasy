# Overfit Audit — 2026 architecture (Branch 2)

## Method
Inventory tuned parameters vs data size; test the *outcome's* year-over-year stability (the ceiling on any model); locate the overfit surface; prescribe pruning. Data: `base2yr.json` per-season boom counts (b24/g24, b25/g25), the flag files, `fusion.py`.

## Findings

**1. The core is NOT a high-variance fitted model (good).** `fusion` consensus = **equal-weight mean of available signals** (abstain-not-fill, ~several votes/player); **no learned weight vector, no ML models** (one trivial univariate `polyfit`). Adding a descriptive feature here *reduces* variance. So the 146-feature count is **not** the overfit problem.

**2. The weight/prior surface is small and principled (good).** The only tuned weights/priors are a few **0.5 shrinkage constants** (`SHRINK_LAMBDA`, coordinator `LAMBDA/BLEND`, rookie `SHRINK`) plus the **one optimized `W=0.15`** (rookie blend). SPIKE thresholds are *derived* (derive_boom_threshold.py), not hand-set.

**3. The overfit surface is the FLAG layer.** ~**195 distinct hand-set numeric cutoffs** across the four flag files (QB 47, RB 52, WR 55, TE 41), calibrated against ~1–2 seasons.

**4. The outcome itself caps how precise any model can be (centerpiece).** Boom-rate year-over-year correlation (n=159, ≥6 g both yrs): **overall r = 0.40 (r²≈0.16)** —
- **RB 0.62** (most predictable; usage/role is sticky)
- **WR 0.41**, **TE 0.35**
- **QB −0.02** (essentially random year-to-year)
Two-year validation sample is capped at ~**226 players**.

## Diagnosis
With r²≈0.16 and a ~160–226 player sample, the model can support only a **handful of free parameters per position**. ~195 hand-set thresholds is well over budget. **QB is the worst case**: 47 thresholds fitting an outcome with ~0 year-over-year signal — almost pure noise-fit. RB (0.62) is the one place added structure is justified.

## Recommendations (prune > add)
1. **Collapse the QB flag layer** toward the base rate + the *one* stable QB signal (game environment / Vegas implied total — the only QB driver that surfaced on the upside board). Drop most of the 47 QB cutoffs.
2. **Shrink, don't hard-threshold.** Replace brittle cutoffs with shrinkage toward position base rates; prefer round/directional cutoffs validated in *both* 2024 and 2025.
3. **Keep RB role/usage structure** (it's genuinely sticky) but still trim redundant cutoffs.
4. **Lean on the equal-weight consensus** (robust) and treat flags as a thin, validated overlay — not ~50 knobs/position.
5. **Parameter budget:** cap *freely-tuned* params to single digits per position; everything else is shrinkage or an equal ensemble vote.
6. **New features (scheme-tags, etc.):** enter as equal ensemble votes that **replicate across 2024↔2025**, never as new thresholds. If a signal doesn't survive both years, it's noise.

## Net
The architecture's bones are anti-overfit (equal-weight ensemble, abstain, shrinkage). The accumulated **flag thresholds — especially QB — are the overfit risk**, confirmed by the near-zero QB outcome stickiness. The fix is **pruning + shrinkage**, not more features.

---

## Per-signal stability test (the individual, not-cluster prune basis)
*`validate_signal_stability.py` — corr(signal, boom) computed in 2024 AND 2025 separately, per position. A signal that flips/vanishes across years is overfit; the flags built on it get dropped/shrunk. Re-run when 2026 lands.*

| Pos | Signal | r 2024 | r 2025 | Verdict |
|---|---|---|---|---|
| WR | tgt_share | +0.58 | +0.54 | **KEEP** |
| WR | rec_pg | +0.71 | +0.79 | **KEEP** |
| WR | ypt (efficiency) | +0.33 | +0.40 | **KEEP** |
| WR | td_pg | +0.67 | +0.67 | **KEEP** (regression-aware) |
| WR | **aDOT (depth)** | −0.31 | −0.02 | **SHRINK — noise** (vanishes) |
| TE | tgt_share / ypt / rec_pg / td_pg | + | + | **KEEP** (all replicate) |
| RB | carry_share | +0.66 | +0.49 | **KEEP** |
| RB | rush_pg | +0.80 | +0.55 | **KEEP** |
| RB | rec_pg (pass role) | +0.37 | +0.63 | **KEEP** |
| RB | td_pg | +0.82 | +0.67 | **KEEP** (regression-aware) |
| QB | **qb_rush_pg** | +0.32 | +0.27 | **KEEP** (the stable QB driver) |
| QB | td_pg | +0.28 | +0.26 | **KEEP** |
| QB | **pass_att_pg (volume)** | +0.05 | +0.25 | **SHRINK — noise** |

### Verdicts → flag actions
- **KEEP (replicate both years):** all volume/role signals (tgt_share, carry_share, rec_pg, rush_pg), efficiency (ypt), and — critically — **QB rushing + TD**. Flags built on these are real; leave them.
- **SHRINK/DROP (one-year artifacts):** **WR aDOT/deep-shot** flags and **QB passing-volume** flags — these don't replicate. Prune or shrink toward base rate.
- **Untestable (no clean year-split data):** man/zone, charting, and opponent-matchup flags can't be individually validated with current data → shrink by the position prior (and lower confidence), don't trust their hard cutoffs.

### Why this matters (cluster vs individual — resolved)
QB *aggregate* boom is random (r≈0), but the individual test shows **qb_rush_pg + td_pg are stable** — a blanket "drop all QB flags" cull would have destroyed the one real QB edge. Individual testing keeps it and condemns specifically the QB passing-volume and WR-depth flags. **Prune by evidence per signal, not by position cluster.**

---

## ADDENDUM — Man/Zone + charting ARE testable (audit correction)

**Correction to the earlier "untestable → shrink by prior" line.** I wrongly checked `chart2.json`
(absent). The real files exist and carry per-season splits, so these signals get a proper
2024-vs-2025 verdict like the box-score ones — not a blanket shrink:
- `boom/chart2yr.json` — `y2024`/`y2025` charting per player (yprr, tprr, fp_rr, aDOT, threat, …)
- `Downloads/receivingManVsZone_2024.csv` & `_2025.csv` — per-season FP man/zone receiving

### Charting signals (chart2yr y2024/y2025 → per-season boom)
| signal | r2024 | r2025 | verdict |
|---|---|---|---|
| fp_rr | +0.73 | +0.76 | KEEP (strongest receiving signal) |
| yprr | +0.65 | +0.69 | KEEP |
| threat | +0.53 | +0.64 | KEEP |
| tprr | +0.51 | +0.66 | KEEP |
| ypt | +0.33 | +0.41 | KEEP |
| yaco_rec | +0.10 | +0.19 | SHRINK |
| mtf_rec | +0.16 | +0.12 | SHRINK |
| contested_pct | +0.09 | +0.03 | SHRINK |
| **aDOT** | **-0.04** | **+0.08** | **DROP (sign flip)** — corroborates parquet finding |
| **deep_pct** | **-0.11** | **+0.06** | **DROP (sign flip)** — same deep-shot family |

### Man/Zone — trait stickiness (2024→2025, ≥60 man routes both yrs, n=96)
| metric | YoY r | verdict |
|---|---|---|
| overall FP/RR | +0.57 | STABLE — the robust thing |
| man YPRR | +0.51 | STABLE — man *skill* is real |
| man FP/RR | +0.47 | STABLE |
| zone FP/RR | +0.44 | weak |
| **man-zone DELTA (the specialist tag)** | **+0.21** | **NOISE — does not persist** |

Delta → boom: **+0.11 (2024), +0.05 (2025)** vs overall FP/RR → boom **+0.75 / +0.74**.

**Verdict (man/zone):** keep man-coverage **quality/level** as an equal vote (stable, real); **shrink the
man-beater / zone-specialist *split tag*** to low-confidence flavor — the split is noise and adds
~nothing beyond overall quality. Same level-vs-differential pattern as aDOT/deep_pct.

**Open (Branch 3):** the *defense's* man-rate is a team/coordinator trait and likely stickier than the
player split — test opponent-side man-rate stickiness before wiring the man/zone matchup. "Good
receivers eat vs man-heavy D" may survive; "target this specific man-specialist" is the noisy part.

---

## ADDENDUM 2 — Per-flag individual test (zone/cover/deep/RB-scheme specialists)

Tested the exact proposal: instead of pooling, test EACH specialization flag individually for
year-over-year persistence. Result is decisive and consistent across receiving + rushing.

### Per-coverage *specialization* (lift = coverage FP/RR − overall), WR/TE, ≥40 routes both yrs
| coverage | specialization-lift r | raw-level r | tail: 2024 top-12 → 2025 pctile | top-Q repeat (chance 25%) |
|---|---|---|---|---|
| **man** | +0.14 | +0.41 | **60.5th** | **43%** ← only keeper |
| zone | +0.19 | +0.47 | 45.0th | 29% |
| single-high (≈Cover 1/3) | +0.25 | +0.43 | 56.0th | 26% |
| two-high (≈Cover 2/4/6) | +0.19 | +0.42 | 66.0th | 32% |

### deep specialist (chart2yr)
aDOT **trait** stickiness r=+0.66 (deep guys stay deep) — BUT aDOT→boom flips (−0.04/+0.08).
**Stable trait ≠ useful flag.** Identifiable in advance, doesn't move our target. Don't build.

### RB run-scheme specialist (SIS rushing advanced, weekly→season, ≥60 car + ≥20/scheme both yrs, n=40)
| signal | r | verdict |
|---|---|---|
| overall YPC (level) | +0.20 | NOISE — RB efficiency itself barely persists |
| scheme SHARE (gap/zone mix) | +0.52 | STABLE — but that's **usage/OL**, not a player edge |
| scheme SPECIALIZATION lift (the flag) | **−0.18** | **NOISE** (slightly reverses); tail top-8 → 55th pctile |

### The universal law (now tested on 5 coverage buckets + RB scheme)
- **LEVEL / role / usage / scheme-mix = stable** (overall FP/RR 0.57, raw coverage 0.41–0.47, RB scheme mix 0.52).
- **SPECIALIZATION / matchup-specific lift = noise** (per-coverage lifts 0.14–0.25, RB scheme lift −0.18, aDOT/deep→boom flip).
- **One survivor:** man-beater tail (top-12 → 60th pctile, 43% repeat vs 25% chance) → keep as a LOW-WEIGHT binary flag on extremes only.

### Verdict on the proposed flags
| proposed flag | verdict |
|---|---|
| man-beater | **KEEP (low-weight, extreme tail only)** — modest persistence |
| zone-beater | DROP — lift noise, tail below coinflip |
| Cover-3 / single-high beater | DROP — tail ≈ chance (26%) |
| two-high beater | DROP — lift noise |
| deep specialist | DROP as boom flag — real trait, flips on our target |
| RB gap/zone-scheme specialist | DROP — lift reverses; only the *mix* (usage) is stable |

**Meta:** this IS the overfit mechanism. Each granular flag measures a *specialization* that doesn't
persist, so it fits one year's noise and fails the next. The 2024↔2025 test is the gate: no flag
enters without clearing it both years, same sign. Individual testing is correct (it rescued
man-beater, like it rescued QB-rush) — and it kills most of the granular flag wishlist.

---

## ADDENDUM 3 — Descriptor dashboard (flags as human-review context, NOT model inputs)

Decision: keep specialization flags OUT of the projection (they fail the gate), but surface them on
the **player-explorer profile** as descriptive context for human review. The human applies judgment;
the flag just hands over the situational fact. Critical: each descriptor carries its **measured
stability** so it isn't silently over-trusted.

### Opponent-side null result (tested, surprising)
I expected team deep-ball vulnerability to be the *sticky* half of a "player deep skill × weak deep D"
matchup. It is NOT. Team pass-defense identity 2024→2025 (n=31, attempt-weighted):
| allowed metric | YoY r | |
|---|---|---|
| boomPct (big plays) | −0.03 | noisy |
| aDoT faced | +0.03 | noisy |
| ypa | +0.13 | noisy |
| EPA/tgt | +0.19 | noisy |
| **compPct** | **+0.32** | only moderately sticky pass-D trait |

=> BOTH halves of the deep-matchup story are low-stability. Confirms: never auto-weight it.

### Reliability tiers for the dashboard
- **GREEN (repeatable, draft-the-trait-all-year):** volume, role, target/carry share, overall
  efficiency (FP/RR, yprr, tprr), QB rushing, completion% allowed (defense). r≈0.4–0.8 both years.
- **YELLOW (current-form / matchup, low stability — use for THIS-WEEK reads, not season bets):**
  deep specialization, coverage splits (man/zone/cover-shell), RB run-scheme split, team
  boom/aDoT-allowed. r≈0–0.25. man-beater slightly better (tail repeat 43% vs 25% chance).

### DFS vs best-ball wrinkle
YoY stability matters for **best-ball** (you hold the trait all season). For **DFS** (one week), recent
form + this-week matchup + who's actually on the field legitimately matter even when not season-sticky.
So the YELLOW descriptors are genuinely useful as DFS matchup callouts — *labeled as such* — while
GREEN drives best-ball value.

---

## ADDENDUM 4 — Prune EXECUTED + board-stability proof (Branch 2 done)

Implemented as reversible shrink constants in `build_flags_WR.py` + `build_flags_QB.py`
(`_shr(mult, lam)`; set factors to 1.0 to restore). Baselines saved in `_prune_baseline/`.
- **DEEP_SHRINK = 0.0** — WR + QB aDOT/deep-shot multipliers DROPPED (2024→2025 sign-flip).
- **COV_SHRINK = 0.5** — man/zone + coverage-shell + coverage-specialist HALVED (split r~0.2; man-beater tail retains modest signal).
- **PASSVOL_SHRINK = 0.35** — QB pass-volume/usage-value multipliers shrunk (corr +0.05/+0.25).
- Untouched (KEEP): volume/role, efficiency (yprr/tprr/fp_rr), QB rushing, TD, team pass-D tier, pass-funnel, home/dome, env/pace/script.

### The proof the cut flags were noise: the board barely moved
| | WR (n=148) | QB (n=53) |
|---|---|---|
| Spearman rank corr (pruned vs baseline) | **0.9985** | **0.9980** |
| mean abs Δ season boom prob | 0.86 pts | 0.58 pts |
| top-24 / top-36 retained | 24/24 · 36/36 | top-12 12/12 · top-24 23/24 |

Per-player probabilities nudged a few points (the flags *were* firing), but the **ranking is
materially identical** — i.e. those multipliers added jitter, not ordering. Real signal would have
re-sorted the board. Biggest prob drops landed exactly where predicted (deep/coverage-reliant:
Nico Collins, Olave, JSN, CeeDee; Lamar/Allen on the QB side) — yet all hold their ranks because
the KEEP signals (volume, efficiency, QB rushing) carry them. Overfit surface reduced, board intact.

Note: a mid-edit file-truncation on the mounted FS clipped the tails of both builders; both were
restored and verified (153 WR / 53 QB, JSON parses, counts match baseline). Full propagation into
command_center/fusion is Branch 1 (pipeline re-run).

---

## ADDENDUM 5 — Branch 3: fusion matchup rewired onto OUR 2026 defense

The best-ball fusion board's `matchup` vote used third-party **ffdataroma** tiers
(`opp_pass_def_tier` / `team_run_def_tier`) while boom + DFS already used our projected defense —
the two models ran on different defensive brains. Fixed:

- **New `season_sos()`** in fusion.py: strength-of-schedule from OUR `defense.json`, averaging each
  team's full-2026-schedule opponent unit percentile. QB/WR/TE → opp `pass_cov_pctl`; RB → opp
  `run_def_pctl`. Softer schedule = higher matchup vote (`within_pos_pctl(invert=True)`).
- **RB bug fixed**: the old vote used the RB's OWN `team_run_def_tier`, not the opponent's. Now
  opponent-correct (e.g., all LAR backs 7→98 once it reads the opponent run-D SoS instead of LAR's).
- **Stable, not single-week**: season SoS (≈17 opponents) rather than the W15-only `opp_*_pctl`
  remap — more robust, and the apples-to-apples replacement for ffdataroma's season tier. The
  W15–17 playoff matchup stays in the boom/overlay side.

**Verification (vs pre-rewire baseline `_prune_baseline/fusion.preB3.json`):**
- matchup vote changed for 359/371 players; polarity correct (Jeudy CLE 39→98 softest cov schedule;
  Odunze CHI 39→2 toughest).
- Consensus rank barely-to-modestly shifted — Spearman QB 0.96 / RB 0.95 / WR 0.95 / TE 0.93 —
  because matchup is **1 of 15 equal votes**: real signal folded in without overfitting the board.
- Propagated fusion → gameplan → personnel → command_center; `refactor/pipeline.py --check` GREEN.

Note: a mounted-FS truncation clipped fusion.py's tail mid-edit (3rd occurrence); restored the
`__main__` entrypoint + verified (1150 lines, parses, writes fusion.json). The ffdataroma `TIER_RANK`
is left defined but unused (ref only).

---

## ADDENDUM 6 — Branch 4: funnel/defender layer reconciled with the 2026 engine

The funnel layer ran off `defensive_profile.json`, built from a HARDCODED 2025 DVOA-FPAA table —
stale (no movers/rookies/coordinators) while boom/DFS/fusion now use the roster-adjusted engine.

Reconcile (NOT a blind overwrite — the 2025 positional `dvoa_fpaa` nudge is VALIDATED: apply_funnel_overlay
AUC 0.617 > raw opp-pctl 0.540, so it stays):
- `build_def_profile.py` now loads `defense.json`, attaches `eng2026` (pass_cov/run_def/pass_rush pctl)
  + `rookies` per team, computes the 2026 PASS/RUN lean, and flags **FUNNEL SHIFT** where the 2025 grade
  disagrees with the 2026 engine.
- **6 roster-shift defenses surfaced:** CHI, DEN, GB, PIT (2025 PASS→2026 RUN), CIN, NYG (2025 RUN→2026 PASS).
  e.g. CIN: 2025 graded RUN-funnel, 2026 engine PASS-funnel (pass_cov_pctl 10.9 = soft secondary).
- Rookies attached to 30/32 defenses.

Surfaced in **command_center Defense tab**: reconciled funnels + lean25/lean26 + a ⚠SHIFT row badge +
2026 defensive rookies in the click-expand detail (verified embedded: `[SHIFT 25->26]`, rookie names).

Durability: wired `build_def_profile` into boom_pipeline (before apply_funnel_overlay) so the reconcile
can't drift. Both pipelines `--check` GREEN.

### Tooling note (recurring)
The mounted FS truncates Edit/Write-tool writes (hit WR/QB/fusion/this file). Reliable path = bash
shell writes (`cat <<'EOF'` / python `open('w')`). Used that for all repairs.

---

## ADDENDUM 7 — Auto-refresh + orphan wiring + best-ball-engine clarification

**Auto-refresh:** intel rebuild (`build_intel.py`+`render_intel.py`) appended to the existing 7am
`run_ingest.bat` (backup `.bak`), so the dashboard tracks the daily tweet/video ingest hands-off.
Entry points: `refresh_intel.py` (daily, tweets) and `refresh_all.py` (full model rebuild, correct order).

**Best-ball engine (verified):** the LIVE board (`fusion.py`→fusion.json→command_center) has every
update (Branch 3 rewire + pruned boom flags via boom_marks). The refactored `bbdfs/` package
(incl. `bbdfs/bestball/board.py`) is imported by NOTHING — dead/parallel code from the old refactor.
Recommend archiving it rather than maintaining two best-ball engines.

**Orphans resolved (now consumed + pipeline-wired):**
- `command_center` added as the FINAL boom_pipeline stage (no more stale boom_marks).
- `build_coordinator_scheme` → `coordinator_scheme_2026.json` (DC man-rate projection, 6 researched DC priors)
  now CONSUMED by `build_def_profile` → `defensive_profile.dc` → surfaced on command_center + intel team cards.
- `build_defender_grades` → `defender_grades.json` (per-CB1 coverage grade + expected WR1 funnel)
  now CONSUMED by `build_def_profile` → `defensive_profile.cb1` → surfaced on both team cards.
- Both builders added as boom_pipeline stages before `build_def_profile`. `--check` GREEN.
- Posture: DC scheme + CB1 enter as **descriptive defense context** (not force-injected into the
  demoted man/zone model signal) — coherent with the anti-overfit findings.

**Remaining loose ends (low priority):** `bbdfs/` dead package (archive), `build_player_tweets.py`
(legacy, superseded by intel).
