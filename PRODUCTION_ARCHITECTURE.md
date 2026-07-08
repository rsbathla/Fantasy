# PRODUCTION_ARCHITECTURE.md — Senior-Engineer Production-Readiness Review

*2026-07-05. Method: mapped the layers from the real files, ran both gates for real, traced
producer→consumer edges, then designed. Every claim cites file:line or a command run in this
session. Claims verified first-hand are marked (verified); claims from a code-reading pass that
were not independently re-derived are marked (read). No code or weights were changed; all
remediations are returned as proposals. Gate runs regenerated `INTEGRATION_AUDIT.md` and
`ROSTER_MOVES_2026.md` (expected — the gates write their own reports). `PERSONNEL.md` was already
modified before this review (mtime 21:50, pre-dating the gate runs at 22:35).*

---

## 0. Verdicts up front

**CONTINUITY: holds structurally, currently RED operationally.**
`python3 integration_audit.py --strict` → **exit 1** (verified), 3 P0 findings, all Check F2
stale-input outputs. `python3 audit_roster_moves.py` → **exit 0** (verified), 0 cross-source
disagreements. `python3 run_all.py --check` → all 19 stage outputs present (verified). The wiring
is correct and the gates work — the gate being red is the gate doing its job: three builders that
live *outside* the `run_all.py` chain were not re-run after their inputs moved.

**CORRECT USAGE: the five repo invariants are honored in the enforced core** (Checks A/H/H2/I/J/K
all zero, verified). The violations that remain are at the *edges*: residual non-canonical name
joins in the boom subsystem, silent-empty ingestion builders, and seven undeclared layers in the
FP/brain sidecar.

---

## 1. Architecture overview — the layers and how they compose

Two products (season-long best-ball, weekly DFS) share one data spine. Four tiers:

```
TIER 1 · INGESTION            TIER 2 · MODEL/ENGINE           TIER 3 · DELIVERY            TIER 4 · GATES
raw pulls -> data contracts   contracts -> derived layers     layers -> artifacts          everything -> verdict

fp_puller.py (FP Data Suite)  refactor/pipeline.py (18-stage  run_all.py DOSSIER chain     integration_audit.py
NFL-master/ (FP,FTN,PFF,NGS)    DAG: features.csv, defense    (17 builders + 2 gates):     (FINAL GATE, checks A..K,
sis_value/ (SIS, 27 csv)        .json, fusion.json ...)         rankings.html, dossier,      --strict = ship gate)
nfl_pro_scraper/ weekly csv   normalize_defense_2026.py        flag_ranks, team_ceiling,
build_nflpro.py               (CANONICAL defense writer)       slot_paths, stack_menu,      audit_roster_moves.py
build_player_funnels.py       env_blend.py (THE env formula)   strategy board render        (DATA GATE, cross-source
build_fp_alignment.py         game_sim.py (40k sims/game)    dfs_model.py --week N          roster reconciliation)
build_fp_personnel.py         pipeline/sim_prod.py (12k)     build_matchup_notes.py
build_sis_personnel.py        pipeline/survival_chain.py     build_team_preview.py TEAM
brain/ (daily news/video ->     (4k) + engine/bbengine.py    engine/run_live.py (live
  brain_intel.json)           personnel.py, team_review_       draft loop) -> live_tree
ffdataroma vegas lines csv      build.py, roster_moves_        -> build_decision_dashboard
ground_truth_registry.json      offense_2026.py (roster      command_center.py
  (verified 2026 facts)         join, collision-guarded)     api/app (FastAPI, dormant)
```

Composition rules that make this more than a script pile:

- **Environment** is never the Vegas total alone: `env_blend.py:53-58` `blend_total()` = posted
  O/U + `ENV_BLEND_SLOPE(0.10)` × pair-ceiling deviation from league mean, consumed by
  `dfs_model.py`, `build_matchup_notes.py`, `build_dfs_week_report.py`,
  `build_dfs_weekly_breakdown.py`, `validate_proe_conversion.py` (verified by grep).
- **Matchup** is strength × softness × *exposure*: `dfs_model.py:173-211` weights man/zone edges
  by `shell.man_rate` (`freq_w` clamped [0.3, 1.8]; a "smash" requires `freq_w >= 0.8`) (verified).
- **Defense identity** has one canonical writer: `normalize_defense_2026.py` (rate-based,
  rookie-aware, 2yr blend), wired at `refactor/pipeline.py:42`. The legacy rookie-blind
  `reweight_defense_2026.py` survives only as the MOVES-map source and refuses to run
  (`reweight_defense_2026.py:158-165`, exit 2 without `BB_ALLOW_LEGACY_DEFENSE=1`) (verified).
- **Facts beat memory**: `ground_truth_registry.json` + auditor Checks I/J/K protect verified
  post-cutoff facts (coaching carousel, Vegas-line provenance) from being "corrected" by a stale
  model; forbidden-claim scans make the exact past failure phrases unshippable.
- **Nothing ships un-audited**: `run_all.py:58-59` ends every chain run with both gates.

## 2. Module/folder structure — the real one, and the sprawl

Real, today (verified counts, `_archive/` excluded):

```
bestball/                    153 .py at ROOT (238 total), 75 .md, 36 .html, 52 .json at root; 171MB
├── run_all.py               orchestrator (DOSSIER chain; --full adds upstream engines)
├── integration_audit.py     FINAL GATE (1,425 lines, checks A..K)
├── audit_roster_moves.py    DATA GATE
├── build_*.py               ~80 builders, flat at root (rankings, dossier, flags, funnels, FP, X/brain views…)
├── dfs_model.py             week-parameterized DFS model (--week 1..18)
├── game_sim.py              40k-sim/game script model         [OFF-CHAIN]
├── env_blend.py             the environment formula (importable module + tiny CLI)
├── normalize_defense_2026.py / reweight_defense_2026.py       canonical vs guarded-legacy
├── team_review_build.py / roster_moves_offense_2026.py / personnel.py   roster join + moves registry
├── pipeline/                sim_prod.py (12k), survival_chain.py (4k), layer2 params, correlation_structure.json
├── refactor/pipeline.py     upstream 18-stage feature/defense/fusion DAG with per-stage integrity checks
├── engine/                  bbengine.py (draft engine + canon() resolver), run_live.py, strategy_live.py, test_bbengine.py
├── boom/                    boom subsystem outputs (defensive_profile, scheme_fit, schedule2026, statmenu…)
├── brain/                   daily intel: brain_video.py, brain_export.py, run_brain.sh, run_brain_weekly.sh, brain_film.sh
├── api/app/                 FastAPI (routers: meta/players/defense/gameplan/personnel/admin) — dormant
├── NFL-master/, sis_value/, data/, ffdataroma…/               raw vendor data
├── tests/test_names.py      canonical-key contract test (passes, verified)
└── agents/, PLAYBOOK.md, CLAUDE.md, ground_truth_registry.json, deliverable_manifest.json
```

**Sprawl assessment.** The *dependency structure* is disciplined (the auditor proves the graph),
but the *namespace* is one flat root: 153 scripts, 75 markdown docs, 36 rendered HTML artifacts,
and 52 data JSONs share a directory. Builders, gates, one-off audits, rendered deliverables, and
data contracts are distinguishable only by naming convention. A clean MVP shape (proposal only —
a large refactor is user-owned):

```
src/{ingest,layers,engines,delivery}/    out/{data,html}/    gates/    docs/    raw/
```

with `core.py` name/team resolution as the single shared kernel it already de-facto is. The
auditor's path assumptions (`SURFACE_ENTRYPOINTS`, producer maps) would need a coordinated move —
this is exactly the class of change to do once, early, before a team joins, or not at all.

## 3. Data flow end-to-end, the JSON contracts, and the CLI "API"

### 3.1 The flow

```
RAW PULLS                       DATA CONTRACTS                    ENGINES                          DELIVERABLES                    GATES
fp_puller.py --seed seed.sh --> NFL-master/FP*/... csv            refactor/pipeline.py -->         run_all.py:
  (bearer in user-local           |                                 features.csv/.json               build_coverage_spec -> build_scheme_fit
   seed.sh, masked; retries/    build_nflpro.py -> nflpro_2025.json  defense.json (via              -> build_flag_ranks -> build_dossier
   backoff on 429/5xx)          build_player_funnels.py ->           normalize_defense_2026)        -> levers/flags -> rankings.html,
sis DataHub -> sis_value/*.csv    player_funnels.json                fusion.json, gameplan.json      adp_clusters, big_board, dossier.html,
nfl_pro_scraper -> weekly csv   build_fp_alignment/-personnel -->  boom_pipeline.py -> boom/*        dossier_deep -> offense_profile ->
ffdataroma -> weekly-vegas-       fp_alignment.json,               game_sim.py -> game_sim.json      team_ceiling -> slot_paths, stack_menu
  lines.csv (POSTED totals,       fp_personnel.json               pipeline/sim_prod.py ->           -> render_strategy_board
  registry-attested)            brain_export.py -> brain_intel      player_sim_distributions.csv    -> integration_audit (FINAL GATE)
brain/run_brain.sh (daily) -->    .json                           pipeline/survival_chain.py        -> audit_roster_moves (DATA GATE)
  vault -> brain_intel.json     coordinator_changes_2026.json       (4k sims/roster path)          dfs_model.py --week N -> dfs_week.html
brain/run_brain_weekly.sh -->     (verified: true, registry)      engine/bbengine.py grade()/      build_matchup_notes -> matchup_notes.json
  nflpro + funnels + FP +       ground_truth_registry.json          pick_values()                  engine/run_live.py -> live_tree.json ->
  defense refresh                                                                                    build_decision_dashboard.py
```

### 3.2 Key inter-layer JSON contracts (the de-facto schemas)

| Contract file | Producer | Shape (top level) | Consumed by |
|---|---|---|---|
| `features.csv`/`.json` | `refactor/pipeline.py` stages | per-player row: name, pos, adp, charting/EPA cols, `opp_*_pctl_2026` | team_review_build, build_splits, boom subsystem, audits |
| `defense.json` | `normalize_defense_2026.py:284` | `teams{code: {*_rate_2026, *_pctl_2026, *_pctl_2025, rookies_2026, moves_2026, top3…}}` | fusion, build_defense_splits, flags, lever_calendar, team_scout |
| `defense_splits.json` | `build_defense_splits.py` | per-team man/zone/deep `softness_pctl` + `shell.man_rate` (the C8 denominator) | `dfs_model.py:177,199`, weekly breakdown, home |
| `team_ceiling.json` | `build_team_ceiling.py` | `teams{}` ceiling prob + drivers (env, pace, pass rate, scheme upgrade, QB ascend, shootout) | env_blend, game_sim, slot_paths, stack_menu, matchup_notes, run_live |
| `offense_profile.json` | `build_offense_profile.py` | per-team identity: pace, PROE, run scheme, motion, outlook | team_ceiling, game_sim, matchup_notes, build_home |
| `coordinator_scheme_2026.json` | `build_coordinator_scheme.py` [OFF-CHAIN] | per-team DC/OC scheme priors, `man_rate_adj`, confidence | build_scheme_fit (chain stage 2), team_ceiling, lever_count/calendar, def_profile, boom_pipeline (verified by grep) |
| `boom/scheme_fit.json` | `build_scheme_fit.py` | player-route spec × W15-17 opponents; `_meta.new_dc_regressed`, `_meta.skipped` telemetry | build_flag_ranks, dossier |
| `flag_ranks.json` | `build_flag_ranks.py` | ADP-anchored composite: adj_rank, deltas, flags | rankings, big board, adp_clusters, slot_paths, stack_menu, bbengine nudge (`engine/bbengine.py:394-416`) |
| `game_sim.json` | `game_sim.py:210` [OFF-CHAIN] | per-game score/script distributions (40k sims, seed 20260703) | dfs_model (script_mult), matchup_notes, team_preview, render_game_sim |
| `dfs_season_baseline.json` | `build_dfs_season_baseline.py:17` [OFF-CHAIN] | all-18-week play scores, freq-weighted edges | matchup_notes, dfs_weekly_breakdown |
| `player_sim_distributions.csv` | `pipeline/sim_prod.py:62` (N=12000, seed 3) | per-player outcome quantiles (p95 ceiling) | bbengine load_board, team_review_build |
| `brain_intel.json` | `brain_export.py` | `_meta, players{claims, fwd, tw…}, teams{hc,oc,dc…}, coaches` | decision_dashboard, team_preview, week1_report, run_live (read) |
| `cc_context.json` | `build_cc_context.py` | per-player 4-layer drilldown | command_center, dfs_model, ctx_panel |
| `ground_truth_registry.json` | hand-authored | protected facts + min_consumers + forbidden claims | integration_audit Check I |
| `deliverable_manifest.json` | hand-authored | per hand-authored deliverable: layers_used + layers_unused_justified | integration_audit Check H2 (`integration_audit.py:257`) |

### 3.3 The CLI "API" (entry points + arguments)

| Command | Purpose | Key args / notes |
|---|---|---|
| `python3 run_all.py [--full|--check]` | rebuild dossier chain (+upstream with `--full`); `--check` lists output existence | stages fail loud: nonzero exit or missing/empty output aborts (`run_all.py:32-40`) |
| `python3 integration_audit.py [--strict]` | FINAL GATE; writes INTEGRATION_AUDIT.md | `--strict` exits 1 on any P0 (`integration_audit.py:1418-1420`) |
| `python3 audit_roster_moves.py [--strict]` | DATA GATE; writes ROSTER_MOVES_2026.md | `--strict` exits 1 on p0 (read: line ~433) |
| `python3 dfs_model.py --week N` | weekly DFS model (default wk 15) | self-provisions defense_splits if missing (`dfs_model.py:33-35`, read) |
| `python3 game_sim.py` | 40k-sim/game script model | seeded `SEED=20260703` (`game_sim.py:51`); stated priors carry revert flags (`game_sim.py:36-51`) |
| `python3 bb_grade.py board.txt [--mine…] [--seat…] [--platform dk|ud]` | grade a pasted draft board (~40s) | per `HOW_TO_RUN_BESTBALL.md` |
| `python3 engine/run_live.py [clip|clip+|path] [user] [--seat]` | live-draft loop → `engine/live_tree.json` → decision dashboard | clipboard via pbpaste/powershell/pyperclip (`engine/run_live.py:13-18`, read) |
| `python3 build_team_preview.py TEAM` | per-team preview (default ARI) | off-chain, manual |
| `python3 fp_puller.py --seed seed.sh --mode base|personnel …` | FP Data Suite pull | backoff on 429/5xx, `--dry-run`, per-code skip-and-continue (read) |
| `bash brain/run_brain.sh` (daily) / `run_brain_weekly.sh` (weekly) / `brain_film.sh` | intel ingest; weekly quantitative refresh | manual invocation; no cron found in repo (verified: no scheduler references) |
| `uvicorn api.app.main:app` | dormant REST facade; `/api/v1/*`, `POST /admin/rebuild` (API-key) spawns `run_all.py` | fastapi not installed in this env; statically audited (read) |

## 4. Edge cases + error handling — where inputs go missing/stale/malformed

**Handled well (verified unless noted):**

- **Chain failures fail loud.** `run_all.py:32-40` aborts on nonzero exit or missing/empty output;
  `refactor/pipeline.py:58-87` adds per-stage column-integrity checks, CSV/JSON desync abort, and
  an explicit run-order guard.
- **Staleness is machine-detected.** Check F (deliverable older than `flag_ranks.json`) and Check
  F2 (`FRESHNESS_DEPS`, `integration_audit.py:718-749`) — F2 is currently firing on three real
  cases, i.e. the guard demonstrably works on a live known-bad input.
- **Token/rate-limit resilience at the pull edge.** `fp_puller.py`: HTTPError caught, exponential
  backoff on 429/5xx, per-code skip-and-continue, dry-run mode; secrets stay in user-local
  `seed.sh`, header values masked (read). `brain_video.py`: captions-first, BotFlag exception
  stops rather than retries (exit 2), idempotent URL manifest (read).
- **Legacy path is a tested guard.** Bare `reweight_defense_2026.py` invocation exits 2 with an
  explanatory message (`reweight_defense_2026.py:158-165`) — the known-bad case (accidental run)
  fires by construction.
- **Fallbacks are loud, not silent.** Check D harvests `_meta` skip/fallback counters; currently
  surfaces `scheme_fit` skips `{no_bucket:52, no_pair:66, no_team:6}` and 8 new-DC regressed teams.
- **2026-not-yet-pulled is designed for.** `build_player_funnels.py` blends 2026 via `--raw2026`
  with stabilization weights and falls back to 2025-only; `run_brain_weekly.sh` gates the blend on
  `WK26` and re-anchoring on `LINES_UPDATED=1` (read).

**Gaps (named, with location):**

1. **Silent-empty ingestion.** `build_nflpro.py`, `build_player_funnels.py`,
   `build_fp_alignment.py` write structurally valid but empty outputs when raw globs match nothing
   — an empty vendor folder is indistinguishable from a 0-player season (read; pattern consistent
   with their empty-glob aggregation paths). No `_meta.row_count` for Check D to catch.
2. **Unguarded file opens in the engine core.** `pipeline/sim_prod.py`, `pipeline/survival_chain.py`,
   `normalize_defense_2026.py`, `env_blend.py:40` open inputs with no existence guard — they crash
   with a raw traceback outside the runner context (read). Acceptable inside `run_all --full`
   (wrapped), sharp when run standalone.
3. **Schema drift = silent nulls.** Hardcoded vendor column maps (`build_nflpro.py` PASS_SPLITS/
   TEAM_ABBR, `build_fp_alignment.py` ACOLS) mean a vendor rename yields nulls or KeyError with no
   drift detector (read). This class already bit the FP layer once.
4. **Delivery renders stale silently by itself.** `build_rankings.py`, `build_matchup_notes.py`,
   `command_center.py` do no input-freshness checks — the *auditor* is the only staleness defense,
   and it runs after, not before, a render.
5. **Brain token expiry surfaces downstream, not at read time.** `TWITTERAPI_IO_KEY` from
   `brain/brain.conf` fails inside the pull rather than pre-flight (read).
6. **Auditor self-blindspot (cosmetic).** `deliverable_manifest.json` is listed as an orphan
   candidate while being consumed by the auditor itself (`integration_audit.py:63,257`) — the
   orphan scan doesn't count the auditor as a consumer (verified).

## 5. Performance notes — the expensive steps and where they bottleneck

| Step | Cost today | Scaling pressure |
|---|---|---|
| `game_sim.py` | `N_SIM=40000` (`game_sim.py:32`) × ~272 games ≈ 10.9M correlated draws; vectorized gaussian-copula + gamma marginals; deterministic (SEED 20260703) | fine per-run; becomes the unit to re-run on every Vegas-line move — batch by changed-games only if run in-season daily |
| `pipeline/sim_prod.py` | `N=12000`, seed 3 (`pipeline/sim_prod.py:53`); vectorized dirichlet/poisson | cheap; safe in a loop |
| `pipeline/survival_chain.py` | `NS=4000`, seed 11; ~40s per graded board end-to-end (`HOW_TO_RUN_BESTBALL.md`) | 40s/board is fine for solo live drafting; too slow for an API serving concurrent grades — precompute or cut NS with error bars |
| brain video ingest | captions-first (`brain_video.py:48-71`), Whisper only as no-caption fallback (`:148-154`, CPU int8) | the old whisper-per-video wall is gone; residual bottleneck is yt-dlp throttling/bot flags (handled by stop-not-retry) |
| daily/weekly loops | `run_brain.sh` (news/video/export), `run_brain_weekly.sh` (nflpro + funnels + FP + defense + game_sim re-anchor) | both manual; the human is the scheduler — see productionization #5 |
| `integration_audit.py` | repo-wide scan of 89 layers, seconds per run | grows with file count; the flat 153-script root is the multiplier, not the checks |
| `run_all.py` default chain | ~19 stages, JSON-bound, fast (skips `--full` engines) | fine; adding the three off-chain builders (see #2 below) adds one game_sim run (~seconds–minutes, vectorized) |

## 6. CONTINUITY + CORRECT-USAGE table

Wired = outputs feed the intended consumer end-to-end. Invariants = repo rules honored in code.

| Layer / component | Wired end-to-end? | Invariants honored? | Breaks / orphans / violations (evidence) |
|---|---|---|---|
| fp_puller → NFL-master/FP* | YES (manual pull) | n/a | token-gated, backoff OK; downstream FP builders off any runner (audit: `builders off-pipeline` incl. `build_fp_personnel.py`) |
| build_nflpro / player_funnels / fp_alignment / fp_personnel | PARTIAL — run only via `run_brain_weekly.sh:41-52` | n/a | silent-empty on missing raw (gap §4.1); all four outputs sit in G2 undeclared-layers triage (INTEGRATION_AUDIT.md §G2, 7 entries) |
| build_sis_personnel → `sis_personnel.json` | **ORPHAN** | n/a | zero consumers repo-wide (verified grep: only its producer references it) |
| brain daily/weekly → `brain_intel.json` | YES — 4 consumers (decision_dashboard, team_preview, week1_report, run_live) | n/a | consumers are off-chain; go stale between manual runs; `brain_intel.json` undeclared (G2) |
| refactor/pipeline.py → features/defense/fusion | YES (`--full` path) | YES — per-stage integrity + run-order guards (`refactor/pipeline.py:58-87`) | dead branch for retired stage remains at `refactor/pipeline.py:69` (cosmetic) |
| normalize_defense_2026 (canonical) vs reweight (legacy) | YES — canonical at `refactor/pipeline.py:42` | **YES** — legacy blocked (`reweight_defense_2026.py:158-165`, exit 2); only MOVES-dict imports remain (verified) | none |
| env_blend | YES — 5 consumers (verified grep) | **YES (C5)** — Check H pins it in dfs_model/matchup_notes/weekly_breakdown/game_sim (`integration_audit.py:161-240`); H violations = 0 (verified run) | no guard on missing `team_ceiling.json` (`env_blend.py:40`) |
| defense_splits + man_rate | YES | **YES (C8)** — `dfs_model.py:173-211` freq_w/cov_rate; smash gated at freq_w≥0.8 (verified) | none |
| coordinator layer → scheme_fit → flag_ranks | YES structurally — Check H pins coordinator tokens in build_scheme_fit (C1) | YES | **P0 (STALE)**: `coordinator_scheme_2026.json` +184,091s older than `coordinator_changes_2026.json` (verified mtimes) — chain stage 2 consumed a 2-day-stale coordinator layer because `build_coordinator_scheme.py` is off-chain (verified: not in `run_all.py:41-59`) |
| game_sim | consumers wired (dfs_model script_mult, matchup_notes) | YES — Vegas anchor + ceiling + offense_profile pinned (Check H); priors carry revert flags (`game_sim.py:36-51`) | **P0 (STALE)**: `game_sim.json` +190,543s older than `offense_profile.json` (verified); off-chain |
| dfs_season_baseline | consumers wired (matchup_notes, weekly_breakdown) | YES | **P0 (STALE)**: +186,126s older than `offense_profile.json` (verified); producer `build_dfs_season_baseline.py` off-chain |
| dfs_model (weekly) | YES | **YES (C5+C8+C9)** — zero `adp` references in `dfs_model.py` (verified grep); script_mult deliberately reverted to 0.0 after backtest mis-sign (`dfs_model.py:51`) | none |
| roster join (team_review_build + roster_moves_offense_2026 + bbengine.canon) | YES | **YES** — pos-gated, team-unique recovery, ambiguity abstention (`team_review_build.py:38-61`); Coleman/Taylor entries corrected with provenance (`roster_moves_offense_2026.py:69,81`); `bbengine.canon()` pos-guard + single-survivor rule (`engine/bbengine.py:205-244`, read); DATA GATE 0 disagreements (verified run) | residual non-canonical joins OUTSIDE the fixed core: `adv2yr.py:20-27` (first-initial, partly forced by `I.Lastname` source format), `boom_base2yr.py:20-23,55` (lastname), `build_qual_summary.py:9-11` (surname counter + hand STOP-list) — production-fed via boom subsystem; violates the repo's own contract stated in `tests/test_names.py:1` |
| flag_ranks → rankings/big_board/adp_clusters/slot_paths/stack_menu | YES (Utilization map, INTEGRATION_AUDIT.md:99-131) | YES | none |
| strategy_board.json (agent-authored) → render | YES via curated pass | YES — H2 manifest enforced, 0 violations (verified run) | none |
| decision dashboard + run_live | YES (live_tree.json handoff) | YES | live-only by design; embedded placeholder when live_tree absent (read) |
| command_center | YES | YES | renders stale silently (no freshness check) |
| api/app | **DORMANT** — no repo reference consumes it | n/a | permissive CORS default; fastapi not installed in this env (verified import failure); rebuild endpoint spawns `run_all.py` (read) |
| Gates themselves | YES — final two chain stages (`run_all.py:58-59`) | guard-fires-on-known-bad honored: F2 firing live ×3; legacy-defense guard fires on bare run; Check G removal-tested day-one (PLAYBOOK §5) | removal tests are *procedural* history, not codified regression tests; no CI (verified: no `.github/`); orphan list: `data/fantasypoints/proe_defense_2025.csv`, `deliverable_manifest.json` (auditor self-blindspot), `personnel_2026_projection.json` |
| ground truth (registry, Checks I/J/K) | YES | **YES** — I/J/K = 0 (verified run) | none |
| Weights discipline (C3) | n/a | **YES** — game_sim RHO backtest-earned (nflverse 1,424 games, `game_sim.py:35-41`); stated priors labeled with revert values (SIGMA_TEAM, K_CEIL, SPREAD_SHRINK); `backtest_composite_2025.py` is the gate | none found |

**Net continuity verdict:** the producer→consumer graph is sound and machine-verified; there are
no dangling reads or schema mismatches in the enforced core today (H/H2/I/J/K/A all zero). The
break class that exists is *temporal*: three off-chain builders (`build_coordinator_scheme.py`,
`game_sim.py`, `build_dfs_season_baseline.py`) sit between chain-managed inputs and chain-managed
consumers, so a chain run refreshes their inputs and silently strands them — F2 catches it, but
only after the fact.

## 7. MVP productionization plan — minimal, highest-leverage, in priority order

Ship-blockers first. Per repo rules, items changing chain semantics or weights are **proposals
returned for owner sign-off**, not applied.

**SHIP-BLOCKERS**

1. **Clear the red gate (mechanical, but owner-ack because numbers refresh).** Re-run
   `build_coordinator_scheme.py`, `game_sim.py`, `build_dfs_season_baseline.py`, then
   `integration_audit.py --strict` to exit 0. Deterministic seeds mean outputs change only insofar
   as inputs changed — which is the point — but downstream deliverable numbers the owner may have
   already read (matchup notes, DFS baselines) will move. *Decision returned: rebuild now vs
   batch with next chain run.*
2. **Close the chain-coverage gap that caused #1.** Any builder appearing in the auditor's
   `FRESHNESS_DEPS` (`integration_audit.py:718`) should be a `run_all.py` stage or explicitly
   declared manual-with-reason. Concretely: insert `build_coordinator_scheme.py` before
   `build_scheme_fit.py` (its consumer at chain stage 2), and add `game_sim.py` +
   `build_dfs_season_baseline.py` after `build_team_ceiling.py`/`build_offense_profile.py`.
   This makes the F2 class structurally unrepeatable instead of merely detectable. *Chain
   composition is owner-owned; proposal only.*
3. **One name-resolution kernel.** `tests/test_names.py:1` already states the contract ("every
   module must join on the SAME canonical key (core.fn)"); `adv2yr.py:20-27`,
   `boom_base2yr.py:20-23,55`, `build_qual_summary.py:9-11` still run private initial/surname
   joins with hand STOP-lists — the exact class just fixed in the roster layer
   (`roster_moves_offense_2026.py:69,81`). Port them onto `core.fn`/`core.resolve` (+
   `bbengine.canon` where board→projection mapping is needed) and add an auditor check that greps
   for private `split()[0][0]`-style keying, proven by a removal test per PLAYBOOK §5.
4. **CI + codified guard regression suite.** No `.github/`, no runner. Minimum viable: on every
   change run `tests/test_names.py`, `engine/test_bbengine.py` (NS lowered — it already supports
   this), `integration_audit.py --strict`, `audit_roster_moves.py --strict`. Convert the
   procedural removal tests (PLAYBOOK §5) into pytest cases that feed each guard its known-bad
   input (e.g. assert bare `reweight_defense_2026.py` exits 2; assert F2 fires on a touched
   input). Guards that were proven once are currently protected only by session memory.

**HIGH-VALUE, NOT BLOCKING**

5. **Fail-loud ingestion + scheduling.** (a) Empty-glob → nonzero exit and `_meta.row_count` in
   `build_nflpro.py` / `build_player_funnels.py` / `build_fp_alignment.py` so Check D surfaces
   vendor outages instead of shipping empty JSON; add a lightweight vendor-header drift check
   where column maps are hardcoded. (b) Put `brain/run_brain.sh` (daily) and
   `run_brain_weekly.sh` (weekly) on a scheduler with failure notification; today the human is
   the cron daemon, and a missed week silently stales four brain consumers.
6. **Declare-or-retire the sidecar layers.** Resolve the 7 G2 undeclared layers
   (`brain_intel.json`, `dfs_week.json`, `fp_alignment.json`, `fp_personnel.json`,
   `nflpro_2025.json`, `personnel_2026.json`, `player_funnels.json`) via `_meta.surfaces` or
   `SURFACE_EXEMPT`-with-reason, and decide `sis_personnel.json` (true orphan, zero consumers —
   verified): wire its heavy-rate cross-check into `build_offense_profile.py` or archive it per
   ORPHAN_TRIAGE. Built-but-unused is this repo's founding defect class (C1). *Which — owner call.*
7. **Guard the engine-core file opens.** Existence checks with actionable messages in
   `pipeline/sim_prod.py`, `pipeline/survival_chain.py`, `normalize_defense_2026.py`,
   `env_blend.py:40` — cheap, removes the raw-traceback failure mode when run outside the runner.

**NICE-TO-HAVE**

8. **API + repo shape.** Either productionize `api/app` (pin CORS, deploy the rebuild endpoint,
   add auth beyond a single key) or archive it — dormant infrastructure is maintenance surface.
   Fold the root sprawl (153 scripts / 75 docs / 36 HTML / 52 JSON in one directory) into the §2
   package layout in one coordinated move with auditor path updates. *Large refactor — explicitly
   owner-owned; do not do piecemeal.*

---

*Verification ledger for this document (rule 7): F2 staleness re-derived by hand from raw mtimes
(+186,126s / +190,543s / +184,091s — matches the auditor within run-time skew); C8 frequency
weighting read directly at `dfs_model.py:173-211`; legacy-defense guard read at
`reweight_defense_2026.py:158-165` and confirmed to fire on any bare invocation; collision fix
read at `team_review_build.py:38-61` and `roster_moves_offense_2026.py:69,81`;
`tests/test_names.py` and `engine/test_bbengine.py` executed to PASS in this session; both gates
executed with real exit codes (1 and 0).*
