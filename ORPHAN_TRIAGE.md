# ORPHAN TRIAGE & REPO-WIDE WIRING VERIFICATION — 2026-07-02

Full triage of INTEGRATION_AUDIT.md's 29 orphan candidates + 8 off-pipeline builders, review of all 34
divergent-consumer candidates, unused load-bearing field sweep, and the audit hardening that keeps every
confirmed gap caught. Verification method: every verdict below is backed by file:line evidence read in this
repo (no facts assumed). Root cause of most false flags: `integration_audit.py` scans **literal basenames in
root `*.py` only** — f-string paths (`f'cfb_receiving_value_{season}.csv'`), suffix swaps
(`.replace('.csv','_2024.csv')`), and `engine/` + `pipeline/` subdir scripts were invisible. The audit now
carries curated, **runtime-re-verified** allowlists for exactly these (see §4).

---

## 1. Triage table — 29 orphan candidates

| # | Item | Producer | Verdict | Evidence | Exact action | LARGE? |
|---|------|----------|---------|----------|--------------|--------|
| 1 | `analysis/w17_blowup_rank.csv` | one-shot export (no writer in repo) | **TERMINAL** | the live `w17_blowup_rank` signal is a CSV **column** read by `gameplan.py:411`, `team_review_build.py:91`, `draft_assistant.py:62`; this file itself has no reader | allowlisted: `^analysis/` in TERMINAL_RE | no |
| 2 | `boom/defender_profiles.json` | `build_defenders.py:52` | **SUPERSEDED** | replaced by `boom/defender_grades.json` (`build_defender_grades.py`, a boom_pipeline STAGE feeding `build_def_profile.py:84` cb1/wr1_funnel) | none; archive candidate. Kept loud as orphan | no |
| 3 | `boom/funnel_projection_2026.json` | none current (pre-Branch-4 draft) | **SUPERSEDED** | `boom/defensive_profile.json` per-team records carry `funnels`/`lean_2025`/`lean_2026` (verified in file), consumed by `build_intel.py:35`, `command_center.py:12,35`, `apply_funnel_overlay.py` | none; archive candidate. Kept loud | no |
| 4 | `boom/manzone_tags_cfb.json` | frozen FBS snapshot (PFF NCAA export, no builder) | **TERMINAL** | `build_rookie_manzone_pff.py` re-derives within-class man/zone pctls fresh from `sis_value/pff_receiving_scheme_2025.csv` (lines 31-72); the full-FBS tag snapshot is context only | allowlisted: `manzone_tags_cfb\.json$` | no |
| 5 | `boom/rookie_situations.json` | `analyze_rookie_situations.py` | **TERMINAL** | findings memo (draft-capital dominates 0.244 vs 0.08/0.089; TE/RB>WR>QB rookie boom; role-volume floor) — insight document, not a model input | allowlisted: `rookie_situations\.json$` | no |
| 6 | `boom/rookie_weight_opt.json` | `woptimize_rookie.py` | **TERMINAL** | optimizer snapshot; its `best_W: 0.15` is hardcoded at `apply_rookie_to_statmenu.py:12` with citing comment (verified equal) | allowlisted: `rookie_weight_opt\.json$` | no |
| 7 | `boom/separation.json` | none in repo (215-player sep/man-sep pctl snapshot, Jun 22) | **SUPERSEDED** | NGS separation is live via `fusion.py:421-425` (`rec_separation` from `ingest_advanced4.py:35`) and read by flags at `build_flags_WR.py:139` `g(fus,'separation_pctl',50)`; man-coverage skill is live via `boom/cover_spec.json` + `boom/coverage_route_spec.json` MAN rollups. statmenu's own `separation_pctl` mirror is 0/411 filled AND unread (inert — see §3.7) | none; archive candidate. Kept loud | no |
| 8 | `boom/sis_defenders.json` | none (manual SIS defender leaderboard snapshot: coverage/pass_rush/run_def Points Saved/WAR) | **SUPERSEDED** | same SIS source ingested directly by `ingest_defense.py:57-59` from `sis_value/{pass_defense,pass_rush,run_defense}.csv` → `defense.json` unit pctls + `top_coverage/top_pass_rush/top_run_def` | none. Kept loud | no |
| 9 | `engine/tree_schema.json` | engine contract | **WIRE — already wired** (false orphan) | consumed by `engine/verify_decision_tree.py:91` (Draft7Validator) + contract ref `engine/decision_tree.py:691`; subdir consumer invisible to root-only scan | curated consumer entry (self-healing needle check) | no |
| 10 | `pipeline/byes_2026.json` | pipeline data | **WIRE — already wired** (false orphan) | `engine/bbengine.py:371-372` (`byes_2026.json -> {TEAM: bye_week}`), `pipeline/build_draft_board.py:37`. NOT superseded by `boom/schedule2026.json` for the engine path | curated consumer entry | no |
| 11 | `pipeline/clay_2026_ud.csv` | pipeline data (Clay projections, Underdog scoring) | **WIRE — already wired** (false orphan) | `engine/bbengine.py:288-291`: `fname = "clay_2026_ud.csv" if plat == "UD" else "clay_2026.csv"` — platform-switched sibling, not superseded | curated consumer entry | no |
| 12 | `pipeline/games_by_week.json` | pipeline data | **WIRE — already wired** (false orphan) | `engine/playoff_overlay.py:123`, `engine/decision_tree.py:177`, `pipeline/build_draft_board.py:37` (W15-17 opponents) | curated consumer entry | no |
| 13 | `player_boom.json` | `build_player_boom.py:54` | **DEAD** | early plain-language boom summary; superseded by the boom subsystem (`boom/statmenu.json` + `boom/boom_marks.json` → rankings/dashboards). Nothing reads it (recursive grep) | none; archive candidate. Kept loud | no |
| 14 | `profiles/profiles_summary.csv` | `build_profiles.py:404` | **TERMINAL** | human-readable situational matrix; the consumed layer is `profiles/player_profiles.json` | allowlisted: `profiles_summary\.csv$` | no |
| 15-20 | `sis_value/cfb/cfb_{receiving,rushing,passing}_value_{2024,2025}.csv` (6) | SIS CFB pull | **WIRE — already wired** (false orphans) | consumed dynamically by `build_rookie_profiles.py:35-37` `f'cfb_{stat}_value_{season}.csv'` with `build_season('2024'), build_season('2025')` at `:77` → `boom/rookie_college_profile.json` → `build_rookie_prior.py` → `apply_rookie_to_statmenu.py` (W=0.15) | 3 curated consumer entries (needle = each f-string stem) | no |
| 21 | `sis_value/cfb/cfb_passdef_value_2024.csv` | SIS CFB pull | **DEAD** | `build_rookie_db_funnel.py:31` reads the **2025** file only, literally; no code path ever touches 2024; no 2-yr DB blend written | none (hold for a possible DB backtest). Kept loud | no |
| 22-23 | `sis_value/cfb/cfb_passrush_value_2025.csv`, `cfb_rundef_value_2025.csv` | SIS CFB pull | **DEAD** | listed as "bonus" in ROOKIE_MODEL.md but never consumed; defensive-unit college signals with no wired pathway (rookie model targets offense ceilings + DB coverage) | none. Kept loud | no |
| 24-26 | `sis_value/{pass_defense,pass_rush,run_defense}_2024.csv` (3) | SIS NFL pull | **WIRE — already wired** (false orphans) | consumed dynamically by `normalize_defense_2026.py:147` `path.replace('.csv','_2024.csv')` — the 2024+2025 recovery blend for injured/DNP starters (gated on snaps/grade), feeding the canonical `defense.json` `*_pctl` | curated consumer entry (needle `_2024.csv`) | no |
| 27 | `sis_value/receiving_manzone_nfl_2025.csv` | SIS NFL pull | **SUPERSEDED** | the repo ingests the split EPA leaderboards instead: `ingest_advanced7.py:13` (`receiving_man.csv`) + `ingest_advanced8.py:14` (`receiving_zone.csv`, computes man/zone delta) | none. Kept loud | no |
| 28 | `ud_cheatsheet.csv` | `pipeline/build_ud_board.py:63` | **TERMINAL** | Underdog draft cheatsheet deliverable (subdir producer also invisible to the scan) | allowlisted: `ud_cheatsheet\.csv$` | no |
| 29 | `video_notes_review.csv` | none (X-pull review sheet) | **TERMINAL** | schema is `player,flag,firstname_present,stat_hits,handle,sentence` — a tweet-candidate review sheet, NOT film notes; the wired film-notes input is `video_notes.csv` (`team_review_build.py:65`, `team_dashboard.py:22`, `build_player_explorer.py:34`, `engine/run_live.py:82`) | allowlisted: `video_notes_review\.csv$` | no |

**Orphan verdict counts:** 13 WIRE-already-wired (false orphans, now curated-cleared) · 7 TERMINAL (allowlisted) · 5 SUPERSEDED · 4 DEAD. The 9 SUPERSEDED/DEAD stay in the orphan list **deliberately** (pressure to archive; nothing was deleted).

## 1b. Off-pipeline builders — the 8 flagged + 3 discovered

| Builder | Output → consumers | Verdict | Evidence / exact action | LARGE? |
|---|---|---|---|---|
| `build_scheme_fit.py` | `boom/scheme_fit.json` → `build_dossier.py` (SCHEME FIT card), `build_flag_ranks.py` (bounded smq nudge) | **WIRE into run_all** | a `--full` rebuild refreshes flags/coordinator via boom_pipeline then builds dossier/rankings from a **stale** scheme_fit. Action = ledger L1 | **YES** |
| `build_flag_ranks.py` | `flag_ranks.json` → `build_rankings.py`, `build_big_board.py`, `build_adp_clusters.py` | **WIRE into run_all** | rank-affecting (nudge → adj_order → adj_rank/delta read by rankings). Action = L1 | **YES** |
| `build_coverage_spec.py` (**discovered 9th** — was audit-invisible) | `boom/coverage_route_spec.json` → `build_scheme_fit.py:270` | **WIRE into run_all** | writes via `json.dump(out, open(jp,'w'))` (`:186`) — a variable path the `is_writer` 140-char window can't see, so the audit never flagged it. Now visible via KNOWN_PRODUCERS. Action = L1 (first of the three) | **YES** |
| `build_rookie_manzone_pff.py` | merges manzone tags **into** `boom/rookie_college_profile.json` (`:50,:72`) | **WIRE into boom_pipeline** | **CLOBBER IS LIVE**: `build_rookie_profiles.py:98` (a boom_pipeline STAGE) rewrites the file wholesale — the profile currently has **906 players, 0 `manzone_tag`**. Every boom run wipes the tags until a manual re-run. Action = L2 | **YES** |
| `build_profiles.py` | `profiles/player_profiles.json` (`:302`) → `build_dossier.py`, `build_dossier_deep.py`, `dfs_model.py` | **WIRE into run_all** | consumed model layer rebuilt only by hand (reads `features.csv:39`); write also invisible to `is_writer` (paren inside `open(os.path.join(...))`) — it silently fell OFF the off-pipeline list when profiles_summary.csv became terminal; restored via KNOWN_PRODUCERS. Action = L5 | **YES** |
| `build_splits.py` | `player_splits.json` (`:92`) → `engine/run_live.py:101` (live draft assistant), `build_player_boom.py:28` | **WIRE (keep fresh)** | reads `dfs_review/out/defense_2026_matchup.json` (refreshed by boom stage `sync_boom_defense`) — live-draft boom-conditions go stale on roster moves. Action = L5 | **YES** |
| `build_defenders.py` | `boom/defender_profiles.json` | **DEAD** | superseded by `build_defender_grades.py` (boom STAGE); also loads `boom/defensive_profile.json:42` without reading any field | none | no |
| `build_player_boom.py` | `player_boom.json` | **DEAD** | output consumed by nothing (see orphan #13) | none | no |
| `build_x_store.py` | `x_store.json` | **MANUAL-BY-DESIGN** | X/Twitter ingest step requiring an external pull; downstream x-chain (`build_x_media/narrative`, `x_dossier_refresh`) is refresh-on-demand | document only | no |
| `build_cc_context.py` (**discovered**) | `cc_context.json` (`:171`) → `command_center.py`, `ctx_panel.py`, `dfs_model.py`, `build_dossier_deep.py` | **WIRE (optional)** | same is_writer blindness (`open(core.P('cc_context.json'),'w')`); nothing invokes it | L6 | YES (opt) |
| `build_offense_profile.py` (**discovered**) | `offense_profile.json` (`:119`) → `build_home.py` | **WIRE (optional)** | same blindness; home-page identity cards go stale | L6 | YES (opt) |

---

## 2. Divergence feed review — all 34 candidates

Confirmed real under-uses: **1** (plus 1 more surfaced via the same coordinator layer below the divergence
threshold — see §3.1). The other 33 are false positives with verified mechanisms. After the producer
reclassification (KNOWN_PRODUCERS), the audit itself now reports 26, all documented FPs.

| Consumer | Layer | Missing field? | Real? | Evidence / action |
|---|---|---|---|---|
| **`build_lever_calendar.py`** | `coordinator_scheme_2026.json` (surfaced via mission check; layer sits below the ≥8-field divergence trigger) | **`conf`** | **REAL** | its own header says "mirrors build_lever_count.py" (`:24`) but it percentile-ranks `man_rate_adj` RAW (`:30,:35`); `build_lever_count.py:65` gates lambda on `conf` and `:73-75` refines the regressed man rate toward the researched lean → the calendar's man-lever weeks drift from the count for new-DC teams. **Invariant added (fires). Wiring = L3 (LARGE)** |
| `analyze_rookie_situations.py`, `build_manzone_tags.py` | `boom/base2yr.json` | — | FP | read `g24/g25` only to detect rookies — legitimately narrow |
| `validate_signal_stability.py` | `boom/base2yr.json` | — | FP | dynamic access `.get(gk)/.get(bk)` (year-parameterized keys) — literal count is 0 by construction |
| `build_player_explorer.py` | `boom/cover_spec.json` | — | FP | passes the whole cspec record into the HTML blob (wholesale pass-through) |
| `build_flags_QB.py` | `boom/defense_shell.json` | — | FP | **intentional**: docstring `:23` "no rz/shell for QB"; uses `SHELL['_LEAGUE']` only as the league baseline for the coverage-specialist amp (`:753-773`). QB ceiling drivers are pressure/volume/rushing, not shell exploitation |
| `build_defenders.py` | `boom/defensive_profile.json` | — | FP | loads at `:42`, never reads a field — dead builder (§1b), not an under-use |
| `refresh_intel.py` | `boom/manzone_2yr.json` | — | FP | orchestrates `run('build_manzone_2yr.py')` (`:21`); never loads the JSON |
| `boom_lib.py`, `build_scheme_fit.py`, `dfs_model.py` | `boom/schedule2026.json` | — | FP | schedule records are accessed dynamically (`g.get('wk')/g.get('opp')` per team key, e.g. `build_scheme_fit.py:299-301`); the "32 fields" are team-code index keys |
| `boomutil.py` | `boom/statmenu.json` | — | FP | mentions statmenu in comments only (`:12,:56`); never loads it |
| `build_dossier_deep.py`, `command_center.py`, `ctx_panel.py`, `dfs_model.py` | `cc_context.json` | — | FP | records really have **4 keys** (`splits,opp,matchup,pos` — verified); the 47-field count came from one-level descent into nested dicts + the producer's self-read (now reclassified) |
| `build_features.py` | `coordinator_notes.json` | — | FP | extracts the scheme question only (`.get(tm,[{}])[0].get('q')`, `:13`) — narrow by design |
| `team_review_render.py` | `coordinator_notes.json` | — | FP | loads `:8`, uses dynamically at `:188` (`COORD.get(t['team'])`) |
| `boom_foundation.py`, `build_defense_splits.py`, `build_flags_layer.py`, `build_lever_calendar.py`, `build_team_scout.py`, `fusion.py`, `sync_boom_defense.py` | `defense.json` | — | FP | each reads exactly the unit pctls its purpose needs (e.g. `build_lever_count.py:104-106` covWeak/rushStr/runWeak); `command_center`'s 16 is a UI displaying everything. The `*_rate_2026` fields are provenance, not decisions (§3.6) |
| `build_home.py`, `render_dfs_week.py` | `defense_splits.json` | — | FP | serialize the layer into `__DEFS__`/JS blobs; fields are read client-side (`render_dfs_week.py:66,:103`) |
| `build_home.py` | `offense_profile.json` | — | FP | same JS pass-through; peer-max was the producer re-reading its output (now reclassified) |
| `build_offense_profile.py`, `command_center.py` | `personnel_changes.json` | — | FP | offense_profile needs only vacated-usage aggregates; command_center passes `per['teams']/per['coverage']` through to the UI (`:12,:35`); the 22-field peer is `personnel.py`, the layer's own curator |
| `build_dossier.py`, `build_dossier_deep.py`, `dfs_model.py` | `profiles/player_profiles.json` | — | FP | renderers/models read the `situations`/`trend` subtrees they need; peer-max 34 was the producer (now reclassified) |
| `build_coordinator_scheme.py` | `scheme_2026.json` | — | FP | producer-side reference, no load-bearing read |
| `build_def_profile.py` | `scheme_2026.json` | — | FP | needs one field; its scheme signal comes from `coordinator_scheme_2026.json` (5 fields, invariant-checked) |

## 3. Unused load-bearing fields (Part 3)

1. **`coordinator_scheme_2026.json.sack_rate_adj` — REAL, the headline gap.** Computed per new-DC team by
   `build_coordinator_scheme.py:31` (printed `:41` as `sack {2025}->{adj}`), read by **nobody**. The pressure
   side of the model runs on: `defense.json pass_rush_pctl` (roster-aware but scheme-unaware) in
   `build_lever_count.py:105-109` (rushStr/passD_strength), and `sackp` in `build_flags_QB.py:257-476`
   (pressure/clean-pocket/protection amps) which `boom_foundation.py:192` computes from frozen 2025
   `def_sack_rate`. A new-DC pressure scheme never reaches any lever. **Invariant added (fires until wired);
   wiring = L4 (LARGE).** Companion fields `sack_rate_2025`/`verified`/`oc_new` are provenance — not gaps.
2. **`coordinator_scheme_2026.json.conf` for `build_lever_calendar.py` — REAL** (see §2 row 1; invariant added).
3. `flag_ranks.json` `nudge`/`sf_adj`/`adj_order`/`smq_pctl_adj`/`scheme_fit` — **NOT gaps**: transparency
   fields; their effect is baked into `adj_rank`/`adj_pos_rank`/`delta` (`build_flag_ranks.py:160-178`), which
   `build_rankings/build_big_board/build_adp_clusters` do read. The scheme_fit signal verifiably flows:
   `scheme_fit.season → sf_adj → flag_score → nudge → adj_order → adj_rank/delta`.
4. `boom/defensive_profile.json.wr1_funnel` — **NOT a gap (dynamic)**: flows wholesale through the `cb1` dict:
   `build_def_profile.py:84` → `build_intel.py:159` (`'cb1':pr.get('cb1')`) → `build_dossier.py:540,:566`
   (reads `wr1_funnel` literal) → `render_dossier.py:337` + `render_intel.py:86`.
5. `boom/defensive_profile.json.eng2026` — genuinely unread, **not load-bearing**: duplicate of `defense.json`
   `*_pctl` (written `build_def_profile.py:86`), which every consumer reads from `defense.json` directly.
   Cleanup candidate only.
6. `defense.json` `pass_cov_rate_2026/pass_rush_rate_2026/run_def_rate_2026` — **NOT gaps**: provenance rates
   ("snap-weighted mean PAA/play", `normalize_defense_2026.py:282`); the canonical decision fields are the
   `*_pctl`, which ARE derived from those same 2026 rates (`:16,:260-262`) and are consumed everywhere.
7. `boom/statmenu.json` PCTLS mirror — **inert vestige**: all 17 fields in `boom_foundation.py:141-143`
   (`value_pctl … sis_value_pctl`, incl. `separation_pctl`) are **0/411 filled and unread**; flag builders take
   the same pctls from fusion directly (`g(fus,'separation_pctl',50)` etc.). Cleanup candidate; deliberately NO
   invariant (would be a false positive).
8. `boom/defense2026.json` `sackp/covp/runp/manp` "unused" — indirection FP: `build_flags_QB.py:263` etc. read
   them from dicts handed over by `boom_lib`, so the literal scan credits nobody. (Their **values** being
   2025-frozen is exactly finding #1.)
9. `boom/flags_{RB,TE,WR,DST}.json` showing 0 consumers in check B — scan artifact: flag consumers use
   f-string paths (`f'boom/flags_{pos}.json'` in `build_flag_ranks.py:74`, `build_scheme_fit.py:275`).
10. Remaining 400+ unused fields (check B) were not exhaustively triaged; the count **rose** 366→458 in this
   pass because producer self-reads no longer mask genuinely-unconsumed fields — the list is now honest input
   for future sweeps.

## 4. SAFE vs LARGE action ledger

### SAFE — executed (audit-only; model outputs untouched, verified by running only `integration_audit.py`)

- **S1. +2 INVARIANTS** in `integration_audit.py` (same format as the coordinator entries), both **firing now
  by design** (open gaps — they clear only when the wiring lands):
  - `coordinator_scheme_2026.json.conf` × `applies_to:['lever_calendar']`
  - `coordinator_scheme_2026.json.sack_rate_adj` × `applies_to:['lever_count']`
  (Invariants can only test scripts that already reference the artifact — `build_flags_QB`/`boom_foundation`
  don't touch the coordinator layer, so their sack wiring is tracked here + L4, not by an invariant.)
- **S2. +7 TERMINAL_RE patterns** (`^analysis/`, `profiles_summary\.csv$`, `ud_cheatsheet\.csv$`,
  `video_notes_review\.csv$`, `rookie_weight_opt\.json$`, `rookie_situations\.json$`,
  `manzone_tags_cfb\.json$`) — each justified in §1. SUPERSEDED/DEAD items were **not** allowlisted.
- **S3. +CURATED_CONSUMERS** (8 entries → clears 13 false orphans): each entry stores the consumer file and a
  `needle` substring that is **re-verified on every audit run** — refactor the read away and the artifact
  drops back to being an orphan (self-healing, no lying allowlist).
- **S4. +KNOWN_PRODUCERS** (4 verified entries: `build_coverage_spec.py`, `build_profiles.py`,
  `build_cc_context.py`, `build_offense_profile.py`) wired into `refs()` + the off-pipeline check — fixes the
  `is_writer` blindness (`open\([^)]*,'w'` can't cross the `)` of `os.path.join/core.P`), which had (a) hidden
  build_coverage_spec's off-pipeline status entirely, (b) counted producers as consumers of their own output
  and inflated divergence peer-maxes (34→26 candidates after the fix). Residual known cases of the same class
  (e.g. `build_defense_splits`, `build_manzone_2yr`, `team_review_build`) are benign for this triage and left
  for a future sweep.
- Console/report now show the curated-cleared list explicitly. `--strict` exits 1 on the 2 P0s (verified);
  `run_all.py` invokes the audit **without** `--strict`, so the pipeline gate is unaffected.

### LARGE — specified, NOT executed (each changes model output → needs user confirmation)

- **L1 (highest priority — rank-affecting).** Wire the scheme chain into `run_all.py`, replacing the head of
  `DOSSIER` with:
  ```python
  DOSSIER=[(["build_coverage_spec.py"],["boom/coverage_route_spec.json"]),   # FP charting 2024+25 -> per-scheme/route spec
   (["build_scheme_fit.py"],["boom/scheme_fit.json"]),                       # spec x 2026 schedule (coordinator-aware new-DC)
   (["build_flag_ranks.py"],["flag_ranks.json"]),                            # ADP-anchored nudge (consumes scheme_fit)
   (["build_dossier.py"],["dossier_data.json"]),
   ... rest unchanged ...]
  ```
  Dependency order verified: `build_coverage_spec` reads only `NFL-master/FP/{2024,2025}` raw charting;
  `build_scheme_fit` reads `coverage_route_spec` + `coordinator_scheme_2026.json` + `coordinator_changes_2026.json`
  + `boom/schedule2026.json` + `boom/flags_{WR,TE}.json` (all built by boom_pipeline, which precedes DOSSIER in
  `--full`); `build_flag_ranks` reads `scheme_fit` + `boom/flags_*` + the engine board; `build_dossier` (stage 4)
  reads `scheme_fit`; `build_rankings` (stage 8) reads `flag_ranks`. Without this, every rebuild ships a stale
  scheme_fit/flag_ranks under fresh rankings.
- **L2 (data-restoring).** `boom_pipeline.py` STAGES: insert
  `("build_rookie_manzone_pff", ["boom/rookie_college_profile.json"], None)` immediately after
  `("build_rookie_profiles", ...)`, then re-run the tagger once — the clobber already happened
  (906 players, 0 `manzone_tag` on disk right now).
- **L3.** `build_lever_calendar.py`: gate the man activator on `conf` + researched-lean refinement, mirroring
  `build_lever_count.py:65-75` (clears invariant S1a).
- **L4.** Pressure-side sack wiring: in `build_lever_count.py`, blend `coordinator_scheme_2026.sack_rate_adj`
  (ported league-relatively, exactly like `build_scheme_fit.py:174-189` ports man) into `rushStr()`; optionally
  the same blend in `boom_foundation.py:192` so `build_flags_QB`'s `sackp` amps see 2026 coordinators (clears
  invariant S1b).
- **L5.** `run_all.py` DOSSIER: add `(["build_profiles.py"],["profiles/player_profiles.json"])` before
  `build_dossier.py`, and `(["build_splits.py"],["player_splits.json"])` anywhere after boom refresh (its
  input `dfs_review/out/defense_2026_matchup.json` is refreshed by boom stage `sync_boom_defense`).
- **L6 (optional).** Also wire `build_cc_context.py` (before `command_center` consumers matter) and
  `build_offense_profile.py` (before `build_home.py`) — lower stakes (UI context layers).
- **Not proposed:** wiring any SUPERSEDED/DEAD item (§1) — no unique live signal found in any of them.

### Post-hardening audit console (final run)

```
INTEGRATION AUDIT ->  INTEGRATION_AUDIT.md
  P0 invariant violations : 2
     - build_lever_calendar.py ignores conf of coordinator_scheme_2026.json
     - build_lever_count.py ignores sack_rate_adj of coordinator_scheme_2026.json
  orphan candidates       : 9  (+13 cleared by verified curated dynamic/subdir reads)
  builders off-pipeline   : 11  ['build_cc_context.py', 'build_coverage_spec.py', 'build_defenders.py',
                                 'build_flag_ranks.py', 'build_offense_profile.py', 'build_player_boom.py',
                                 'build_profiles.py', 'build_rookie_manzone_pff.py', 'build_scheme_fit.py',
                                 'build_splits.py', 'build_x_store.py']
  layers field-audited    : 71  |  unused rich fields: 458  |  divergent consumers: 26
  fallback counters firing: 3   (fusion abstain policy; scheme_fit new-DC regressions + skip counts — reviewed, expected)
```
Both new invariants fire because the gaps are genuinely open (not aspirational) — they clear when L3/L4 land.
