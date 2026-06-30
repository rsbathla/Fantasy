# Best Ball / DFS 2026 — Senior Engineering Review & Refactor

*Inherited-codebase audit. Architecture, data flow, problem areas, refactor strategy, and a delivered shared-core package. Prepared 2026-06-23.*

This review supersedes the framing of `ARCHITECTURE_AUDIT_2026.md` and `BOOM_SUBSYSTEM_AUDIT_2026.md` (both still accurate on the problems they scoped) by adding the organizing lens the project now needs: **two models — a pure best-ball model and a DFS model — sharing one core.** Every quantitative claim here was verified against source (`wc -l`, `grep`, file reads) on 2026-06-23.

---

## TL;DR

The modeling is good; the **engineering discipline around it is what's failing.** Three things stand out:

1. **🔴 URGENT — the live feature store is silently corrupted.** `features.json` has **81 columns**; the design target (and the backup from 4 days earlier) has **139**. A partial re-run of the hand-ordered ingest chain dropped **58 advanced columns** (all of `ingest_advanced2..10` — every efficiency, EPA, coverage-split, and SIS signal) with no error. The whole point of the DFS model — efficiency and matchup — is currently running on a degraded store. *Recoverable; tool delivered.*

2. **The right abstractions exist but were never adopted.** `core.py`, the `refactor/` package (parse/statlib/featurestore/registry/pipeline), `flag_engine.py`, `ui/bb-components.js` — all well-written, all designed to kill the duplication — have **zero importers in the hot paths**. So the duplication they were meant to remove is still live: `fn()` re-defined in ~22 files, `num()` in 18 (10 of them ingest scripts), `pct()` in 6, team maps in 9–12, the within-position percentile in 5 (3 named + 2 open-coded), the source-fusion math in 2, `esc()` in 4 (3 divergent behaviors — one is an XSS hole).

3. **The two models were built by copy-paste, not by sharing a core.** `fusion.py` (1,152 LOC, draft-leaning) and `dfs_scenarios.py` (870 LOC, weekly/DFS) independently re-implement the *same* within-position-percentile + consensus/divergence engine, and the best-ball **playoff-week ceiling is computed twice** (a real Vegas version in `dfs_scenarios`, a weaker proxy in `engine/playoff_overlay`). The genuinely best-ball-specific spine (the Monte-Carlo survival chain + decision tree) is, by contrast, clean and well-isolated — it's the asset to build the shared core *around*.

**What's delivered in this pass:** a `bbdfs/` package that consolidates the proven-but-orphaned modules into one shared core, adds the missing shared engines (source-fusion, playoff-week, config), splits **best-ball** and **DFS** into thin layers on top, replaces the 5× flag scaffolding with one config-driven engine, ships the missing tests, and provides a non-destructive feature-store recovery tool. See [§6](#6-whats-delivered) and `bbdfs/MIGRATION.md`.

---

## 1. Scope & method

| | |
|---|---|
| Repo | `~/Downloads/bestball/` — 26 MB, 62 root `.py` files (~16k root LOC) + `engine/`, `pipeline/`, `boom/`, `refactor/`, `api/`, `ui/` |
| Read in full | the orientation docs, `core.py`, `refactor/*`, `flag_engine.py`, `boom_lib.py`, plus four parallel deep-dives over the flags family, the BB/DFS engines, the ingestion chain, and the render/hygiene layer |
| Verified | every number below via `wc -l` / `grep` / direct read on 2026-06-23 |

---

## 2. Architecture overview

The system turns raw football data (SIS charting, FantasyPoints/NFL-master, ffdataroma exports, Clay projections, Vegas lines, DK/UD ADP) into interactive draft and DFS dashboards. It has grown in **two generations** that now coexist:

- **Gen-1 — the feature-store + fusion pipeline** (Jun 15–19): `build_features.py` → the `ingest_advanced*` chain → `features.json`, consumed by `fusion.py` / `dfs_scenarios.py` / `gameplan.py` / `personnel.py` → `command_center.html`. Has prior audits and a started-but-unadopted `refactor/`.
- **Gen-2 — the `boom/` subsystem** (Jun 21–23, the "BBM handoff" work): `boom_foundation.py` → augmenters → the `build_flags_{QB,RB,WR,TE,DST}.py` family → `boom/flags_*.json` → the decision dashboard, player explorer, team dashboards, plus the in-flight rookie/funnel work.

### 2.1 The four layers (and where each model lives)

```
                    ┌──────────────────────── SHARED (should be) ───────────────────────┐
 raw sources ──▶ ingestion ──▶ feature store ──▶ source-fusion ──▶ per-player signals
 (SIS, FP,        (build_       (features.json   (within-pos        (boom flags, ceiling,
  Clay, Vegas,     features +    139→81 cols)      percentile +       efficiency, matchup)
  ADP)             ingest_*)                       consensus/div)
                                                        │
              ┌─────────────────────────────────────────┴───────────────────────────────┐
              ▼                                                                            ▼
   BEST-BALL model (clean spine)                                          DFS model (entangled)
   pipeline/sim_prod → survival_chain                                     dfs_scenarios.py:
     → win_delta  (Monte-Carlo advancement,                                 per-matchup ceiling,
        W15→16→17 gates)                                                     weekly Vegas env,
   engine/bbengine → decision_tree                                          P(ceiling) per W15-17
     → playoff_overlay (W15-17 ceiling)                                   (+ re-implements the
   gameplan/correlation/stacking                                            fusion engine, and
                                                                            the playoff-week math)
              └───────────────────────────┬───────────────────────────────┘
                                           ▼
                         render: 7 dashboards (command_center, decision_dashboard,
                         player_explorer 4.8MB, team_dashboard, team_scout, upside_cases, pick)
```

### 2.2 The best-ball ↔ DFS map (the central lens)

| Concern | Where it lives today | Verdict |
|---|---|---|
| **Best-ball only** — survival chain (top-2/12 + W15→16→17), playoff overlay, decision tree, build curves, correlation/stacking | `pipeline/survival_chain.py`, `pipeline/win_delta.py`, `engine/decision_tree.py`, `engine/playoff_overlay.py`, `gameplan.py` | **Healthy & isolated** — the asset to build around |
| **DFS only** — per-matchup ceiling, weekly Vegas environment, P(ceiling) scenarios | `dfs_scenarios.py` | Works, but *is* the best-ball playoff-week engine wearing a DFS hat (it computes W15-17, the BB playoff weeks) |
| **Should be shared, is duplicated** — within-position percentile, consensus/divergence fusion, name/team/number parsing, the playoff-week ceiling | `fusion.py` ⟷ `dfs_scenarios.py` (engine dup), `playoff_overlay` ⟷ `dfs_scenarios` (ceiling dup), ~20 files (parsing) | **The core problem** |

The two models don't need to be torn apart — they need a **shared substrate** extracted from underneath them. Today, "best ball" vs "DFS" is two copies of the same fusion engine fed slightly different columns; it should be **one engine, two source lists.**

### 2.3 What's genuinely good (keep)

- The **model-fusion contract**: every source is an independent within-position percentile; missing signals **abstain** (never filled to a fake 50 inside a source); consensus and divergence are computed, and **disagreement is treated as the signal.** This is the intellectual core and it's sound in both engines.
- The **best-ball simulation spine**: `sim_prod` (compositional Monte-Carlo, Clay-calibrated, correlation-preserving) → `survival_chain` → `win_delta`, wrapped by a clean `engine/bbengine.py` API with a real test (`engine/test_bbengine.py`). Fidelity is exact (grade == chain).
- `core.py` is the right idea (one join, one team map, one atomic NaN-safe JSON writer), and the **clobber-guard + integrity asserts** in `boom_pipeline.py` are real and working.
- The **backtest harness** (`backtest_boom.py`: AUC/Brier/calibration/lift) and the principled boom-threshold derivation.

---

## 3. Problem areas (ranked by impact)

| # | Problem | Severity | Evidence |
|---|---|---|---|
| **P1** | **Live feature store corrupted 139 → 81 cols** — 58 advanced columns silently dropped by a partial ingest re-run | 🔴 Critical | `features.json` meta = 81 cols; `_prebuild_backup_.../features.json` & `refactor/columns.json` = 139; lost set = all of `ingest_advanced2..10` (efficiency/EPA/coverage/SIS) |
| **P2** | **Abstractions delivered but unadopted** → duplication still live | 🔴 High | `grep` for `refactor.parse/statlib/featurestore` imports = **0** outside `refactor/`; `fn()` redefined ~22×, `num()` 18× (10 ingest), `pct()` 6×, `TMAP` 9× literal (12 incl. aliases), `within_pos_pctl` 5× (3 named + 2 open-coded), consensus/divergence 2× |
| **P3** | **BB ↔ DFS engine duplication** — fusion & dfs_scenarios re-implement the same percentile+fusion machinery; playoff-week ceiling computed twice | 🔴 High | `fusion.py` 1,152 LOC / `dfs_scenarios.py` 870 LOC, ~350–450 LOC conceptually identical; `playoff_overlay` proxy vs `dfs_scenarios` Vegas version |
| **P4** | **5× flag builders** — 5,767 LOC, per-week condition encoded 4 incompatible ways, ~850–1,150 LOC duplicated plumbing | 🟠 High | `build_flags_{QB,RB,WR,TE,DST}.py` = 1439/1270/985/1364/709; `flag_engine.py` written to fix this, imported by **0** builders |
| **P5** | **No orchestration guardrails on the hand-run chains** — skip/reorder a stage and columns vanish silently (this caused P1) | 🟠 High | ingest chain order enforced only in the unadopted `refactor/pipeline.py`; `ingest_defense ↔ reweight` ordering footgun |
| **P6** | **~190 magic-constant weights** scattered, same concept set in ≥4 files | 🟠 Med | ceiling weight = 0.75 (fusion) / 0.50 (gameplan) / 0.42 (draft_assistant); 61 float literals in dfs_scenarios alone |
| **P7** | **Render bloat & duplication** — 7 overlapping dashboards, `player_explorer.html` 4.8 MB (2.7 MB tweets inlined), JS copy-pasted per file | 🟠 Med | `esc()` in 4 dashboards, 3 divergent behaviors; decision_dashboard's does **no HTML-escaping** (injection risk); `ui/bb-components.js` built and unused |
| **P8** | **~Zero tests on the shared logic** | 🟠 Med | only `engine/test_bbengine.py` is a real suite; fusion/dfs ship ~270 LOC of `print()` "verification" with no assertions |
| **P9** | **Repo hygiene** — ~3.45 MB cruft, data/code/outputs mixed in a flat root | 🟡 Low-Med | `_prebuild_backup_*` 2.9 MB, stray `lu*.tmp` PDF, `__pycache__` committed (mixed 3.10/3.14), duplicate `merged_rankings_upload.csv` (root + pipeline), duplicate HANDOFF md |

**The throughline:** P1/P5 are one failure mode (an implicit, in-place, hand-run chain with no guardrails, so an out-of-order or skipped step corrupts state *silently* — and already has). P2/P3/P4/P6 are duplication that multiplies the cost of every change. P8 means none of it is regression-locked. **Almost none of this is a design gap — it's an *adoption* gap.** The fixes were largely written; they were never wired in.

---

## 4. Refactor strategy

Four principles, then a phased plan that keeps the live tools runnable throughout.

**Principles**
1. **Adopt, don't add.** The repo's problem is unadopted good code, not missing good code. Prefer wiring in `core`/`refactor`/`flag_engine`/`ui` over writing more.
2. **One shared core, two thin model layers.** Extract the substrate (parsing, percentile, fusion, feature store, playoff-week, config) so best-ball and DFS differ only in their source lists, not their math.
3. **Fail loud, not silent.** Every place that today degrades to "abstain" on missing data (the cause of P1) gets a `require()` boundary that raises.
4. **Lock it with tests before moving it.** No import swap without a parity/property test as the gate.

**Phased plan (each phase independently shippable, parity-tested)**

| Phase | Action | Gate |
|---|---|---|
| **0** | **Recover the store (P1).** Run the orchestrated rebuild (or promote the recovered snapshot), confirm 139 cols, add the `require()` boundary so it can't silently drop again. | `features.json` back to 139 cols; `bbdfs` boards see efficiency/matchup sources |
| **1** | **Adopt the shared core (P2).** Swap the ~20 `fn()`, 10 `num()`, 6 `pct()`, 12 `TMAP`, 5 percentile copies for `import bbdfs.core` (or the existing `refactor`), one file at a time. | `bbdfs/tests` green after each swap |
| **2** | **Collapse BB↔DFS onto one engine (P3).** Re-express `fusion.py` and `dfs_scenarios.py` as source lists fed to `bbdfs.core.fuse_board`; unify the playoff-week ceiling on `bbdfs.core.playoff_week`. | board outputs match the legacy JSON within tolerance |
| **3** | **Config-drive the flags (P4/P6).** Port each `build_flags_*` if-cascade into a `bbdfs.flags.config` table; lift the ~190 weights into `bbdfs.core.config`. | `validate_boom.py` passes on the regenerated `flags_*.json` |
| **4** | **Orchestrate + de-bloat render + hygiene (P5/P7/P9).** Make `refactor/pipeline.py` the only sanctioned build entry; externalize `player_explorer` tweets; one shared `esc()`; `.gitignore` + `src/ data/ out/` layout. | `pipeline --check` green; dashboards < 2 MB; cruft gone |

---

## 5. Target architecture

```
bbdfs/                         # ONE package: shared core + two thin model layers
  core/                        # the substrate both models share
    names.py      fn, canon            ← ~20 duplicate normalizers
    teams.py      team_code, TMAP      ← 12 team-map copies
    parse.py      num, pct, pnum, ab   ← num()×10, pct()×6
    statlib.py    pctl, consensus, divergence, zscore_blend  ← percentile×5, fusion math×2
    io.py         safe_json_dump, load_json/csv
    featurestore.py  FeatureStore (build) + load_features/FeatureFrame.require (read, FAIL-LOUD)
    fusionkit.py  SourceSet + fuse_board + leverage_flags    ← the engine fusion & dfs duplicated
    playoff_week.py  p_ceiling, playoff_up                   ← the W15-17 ceiling computed twice
    config.py     all weights/thresholds                     ← ~190 scattered literals
  bestball/                    # thin: BB source list + correlation/stacking over the core
    board.py, correlation.py
  dfs/                         # thin: DFS source list + holistic per-matchup view over the core
    board.py, matchup.py
  flags/                       # ONE config-driven flag engine (replaces 5× builders)
    engine.py, config.py
  tools/recover_feature_store.py   # non-destructive P1 recovery
  tests/test_core.py               # the missing test layer
```

**Principle in one line:** the difference between the best-ball model and the DFS model becomes a **difference in source lists and objective**, computed by one shared engine — not two copies of the same math. The clean best-ball sim spine (`pipeline/` + `engine/`) stays where it is and is wrapped, not rewritten.

---

## 6. What's delivered

A runnable, tested `bbdfs/` package (consolidation, not a rewrite — it imports the proven `core.py`/`refactor/*`/`flag_engine.py`/`boom_lib.py` so there is a single source of truth):

| Delivered | What it is | Status |
|---|---|---|
| `bbdfs/core/` | the shared substrate: names, teams, parse, statlib, io, **featurestore (with fail-loud `require`)**, **fusionkit** (the shared fusion engine), **playoff_week** (the unified W15-17 ceiling), **config** (centralized weights) | ✅ runs on the live store |
| `bbdfs/bestball/` | `build_board()` (ceiling/spike/value/advancement fused + playoff overlay) + consolidated `stack_bonus` correlation | ✅ builds 371-player board |
| `bbdfs/dfs/` | `build_board()` (matchup/efficiency/opportunity fused + per-week P(ceiling)) + `player_card()` holistic per-matchup view | ✅ builds + per-week ceilings |
| `bbdfs/flags/` | one **config-driven flag engine** replacing the 5× scaffolding; WR table as a worked example, QB/RB/TE/DST stubbed for the mechanical port | ✅ lights/grades/handles byes via the existing calibrated path |
| `bbdfs/tools/recover_feature_store.py` | **non-destructive** P1 diagnosis + recovery (pinpoints all 58 lost columns; writes `features.recovered.json`, never overwrites live) | ✅ verified |
| `bbdfs/tests/test_core.py` | 12 property/parity/integration tests (the missing test layer) | ✅ 12/12 pass |
| `bbdfs/MIGRATION.md` | the adopt-one-import-at-a-time guide mapped to Phases 1–4 | ✅ |

Run it:
```bash
python3 bbdfs/tests/test_core.py                    # 12/12 pass
python3 -m bbdfs.bestball.board                     # best-ball board
python3 -m bbdfs.dfs.board                          # DFS board
python3 bbdfs/tools/recover_feature_store.py        # diagnose the 139→81 loss
```

> **Honest scope note.** The flag engine + WR config prove the pattern and run through the existing calibrated grading path; porting QB/RB/TE/DST is transcribing each builder's if-cascade into config rows (data entry, gated by `validate_boom`) and is intentionally left as the migration step rather than risking a blind 5,767-LOC rewrite without parity runs. Likewise the boards currently run on the **degraded 81-col store**, so their efficiency/matchup sources are thin until Phase 0 recovery — by design they abstain on missing columns and get richer automatically once the store is restored.

---

## 7. Appendix — evidence

- Feature store: live `features.json` **81** cols vs backup/manifest **139** → **58 lost** (full list in `recover_feature_store.py` output).
- Flags family LOC: QB 1,439 · TE 1,364 · RB 1,270 · WR 985 · DST 709 = **5,767**.
- Engines: `fusion.py` **1,152** · `dfs_scenarios.py` **870**.
- Duplication (grep, 2026-06-23): `fn()` 22 · `num()` 18 (10 ingest) · `pct()` 6 · `TMAP` 9 literal (12 incl. aliases) · `within_pos_pctl` 5 (3 named + 2 open-coded) · consensus/divergence 2 · `esc()` 4 (3 divergent behaviors).
- Refactor adoption: **0** imports of `refactor.parse/statlib/featurestore` outside `refactor/`.
- Render: 7 dashboards, total HTML ~6.6 MB; `player_explorer.html` **4.8 MB** (2.7 MB tweets inlined on one line).
- Hygiene: ~**3.45 MB** removable cruft; duplicate `merged_rankings_upload.csv` (root + `pipeline/`); committed `__pycache__` (mixed 3.10/3.14).
