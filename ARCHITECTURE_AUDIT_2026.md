# Best-Ball / DFS Toolkit — Architecture Audit & Refactor Plan
*Senior-engineer review, June 2026. Scope: the `bestball/` analytics pipeline (26 Python files, ~5,381 LOC, a 139-column feature store, an 18-stage build, and a browser command center).*

---

## 1. Architecture Overview

The system turns raw football data into a single interactive draft/DFS dashboard. It is organized in four layers.

**Layer 1 — Shared core (`core.py`, 61 LOC).** One canonical name normalizer (`fn`), team-code map (`norm_team`/`TMAP`), a NaN-safe **atomic** JSON writer (`safe_json_dump`), and the position-strict fuzzy player join (`match_usage`) that resolves collisions like A.J. Brown vs Amon-Ra and Jeremiyah Love vs Jordan Love. Imported by virtually every script.

**Layer 2 — Feature store (an append-only chain).** `build_features.py` creates `features.csv` + `features.json` (one row per ~371 board players), then **twelve** scripts each read that file, add columns, and rewrite it: `ingest_advanced.py` → `ingest_advanced2..10.py` → `ingest_defense.py` → `reweight_defense_2026.py`. The end state is a flat 139-column store that is the single source every engine consumes.

**Layer 3 — Source-fusion engines.** `dfs_scenarios.py` (870 LOC) and `fusion.py` (1,152 LOC) read the feature store and emit independent **model-fusion** outputs: each data source becomes its own within-position percentile, displayed side-by-side with a consensus (mean) and divergence (std). `gameplan.py` and `personnel.py` add draft/scheme layers. Nothing is refit or collapsed — disagreement is the signal.

**Layer 4 — Render.** `command_center.py` (25 LOC) merges five JSON outputs (fusion, dfs, gameplan, personnel, defense) into `command_center.html` via a `__DATA__` placeholder in a template.

### Data flow

```
raw (sis_value/*.csv, NFL-master/*, ffdataroma/*, pipeline/*.parquet, schedule, ADP)
  │
  ▼  build_features.py                    → features.{csv,json}  (~40 cols)
  ▼  ingest_advanced(.py … 10.py)  ×11    → features.{csv,json}  (+~85 cols, append-in-place)
  ▼  ingest_defense.py                    → defense.json (2025) + opp_*_pctl on features
  ▼  reweight_defense_2026.py             → defense.json (2026) + 2026-adjusted opp_*_pctl   ← MUST run last
  │
  ├─ dfs_scenarios.py  → dfs_scenarios.json   (5 source models, P(ceiling))
  ├─ fusion.py         → fusion.json          (per-source votes + consensus/divergence)
  ├─ gameplan.py       → gameplan.json
  ├─ personnel.py      → personnel_changes.json
  │
  ▼  command_center.py → command_center.html  (merges all five)
```

### What's genuinely good
- **The model-fusion contract is sound and consistent**: every source is an independent within-position percentile, missing signals *abstain* (never filled to a fake 50 inside a source), and consensus/divergence are computed rather than collapsed. This is the system's intellectual core and it holds across both engines.
- **`core.py` is the right abstraction** — one join, one team map, one atomic JSON writer.
- **Atomic JSON writes** (`safe_json_dump`, tmp+`os.replace`) already prevent truncated JSON on crash.

---

## 2. Problem Areas

| # | Problem | Severity | Evidence |
|---|---|---|---|
| P1 | **No orchestrator** — the 18-stage build is run by hand | High | no `.sh`/`Makefile`/runner exists |
| P2 | **Append-only chain + silent skips** — skip/!reorder any ingest and columns vanish with no error | High | each `ingest_advanced*` reads→rewrites `features.csv`; downstream just abstains |
| P3 | **`ingest_defense` ↔ `reweight_2026` ordering footgun** — re-running ingest_defense silently reverts the 2026 reweight | High | both write `defense.json` + `opp_*_pctl`; agent already hit this, had to re-run reweight last |
| P4 | **Non-atomic CSV write** — a crash mid-write desyncs `features.csv` from `features.json` | Med | JSON uses atomic `safe_json_dump`; CSV uses raw `open()`+`DictWriter` |
| P5 | **Duplicated parsers** — `num()` in 11 files, `pct()` in 6, team maps (`TMAP`/`FULL2AB`/`NICK`) in 3 | High | grep counts; `ingest_defense`/`reweight`/`team_*` re-define instead of importing core |
| P6 | **Duplicated stats math** — the `(rank-0.5)/n*100` percentile copied across 3 functions in 2 files | Med | `dfs_scenarios.within_pos_pctl` vs `fusion.within_pos_pctl` + `within_pos_pctl_series`; diverge only on NaN policy |
| P7 | **CSV read→merge→rewrite boilerplate** repeated verbatim | Med | 12 ingest scripts |
| P8 | **~20 magic constants** scattered in function bodies, no config | Med | `LG_MAN=17`, `HOT/COLD=70/35`, `ENV 0.80/1.25`, source weights, `W_P95/W_SPIKE` |
| P9 | **Zero tests** (1 stub) | High | no coverage of `fn`, `norm_team`, percentile, or ingest |
| P10 | **No column provenance** — 139 cols, no record of producer/coverage | Med | `features.json.meta.cols` is names only |
| P11 | **Inconsistent NaN/abstention** — preserve vs neutral-fill chosen ad hoc | Low-Med | dfs preserves; fusion has both variants |
| P12 | **Perf: full re-read/re-write ×12 + recompute every run + double-parse of defense CSVs** | Low-Med | acceptable at 371 rows, but compounds the fragility of P2 |

The throughline: **P1–P4 are one failure mode** — an implicit, in-place, hand-run chain with no guardrails, so an out-of-order or skipped step corrupts state *silently*. **P5–P7** are duplication that multiplies the cost of every change and every bug. **P9–P10** mean none of it is verified or documented.

---

## 3. Refactor Strategy (incremental, non-breaking)

Sequenced lowest-risk-first; each phase is independently shippable and parity-tested before the next.

**Phase 0 — Safety net (no behavior change).** Land `refactor/tests/` and `pipeline.py --check`. Now any regression is caught. *(Delivered.)*

**Phase 1 — Dedupe leaf helpers.** Replace the 11 `num()`/6 `pct()`/3 team-maps with `refactor/parse.py`; replace the 3 percentile copies with `refactor/statlib.py`. Pure functions, exact-parity tested, swap one import at a time. *(Delivered + parity-verified.)*

**Phase 2 — Collapse the ingest chain.** Re-express the 12 ingest scripts as declarative `SourceSpec`s consumed by `refactor/featurestore.py` (load once, merge all, write once, atomically). Kills P2/P4/P7 and records provenance for P10. *(Framework delivered; one stage reproduced at parity.)*

**Phase 3 — Orchestrate.** Adopt `refactor/pipeline.py` as the single entry point with per-stage integrity checks (column presence, csv/json sync, the defense ordering guard). Kills P1/P3. *(Delivered; `--check` green.)*

**Phase 4 — Config + provenance.** Lift the ~20 magic constants into one config; ship `registry.py`/`columns.json` in CI to fail on schema drift. *(Registry delivered.)*

Each phase leaves the live pipeline runnable; nothing is a big-bang rewrite.

---

## 4. Improved Architecture

```
            ┌── parse.py ──┐   ┌── statlib.py ──┐        (pure, tested leaves)
core.py ────┤  num/pct/    │   │ pctl(abstain|  │
(join, IO)  │  team_code   │   │  neutral),     │
            └──────┬───────┘   │ consensus/div  │
                   │           └───────┬────────┘
                   ▼                   │
        featurestore.py (load once,    │   engines import statlib instead of
        apply SourceSpec[], write      │   re-deriving the percentile:
        once, atomic, provenance) ─────┼──► dfs_scenarios.py / fusion.py
                   │                   │
              columns.json ◄── registry.py (provenance + CI drift guard)
                   │
        pipeline.py  ── ordered DAG + integrity checks ──► command_center.html
```

The engines keep their model-fusion logic but lose their private copies of the percentile math (import `statlib`); the 12 ingest scripts become ~12 `SourceSpec` literals fed to one `FeatureStore`; the hand-run chain becomes `python3 refactor/pipeline.py`. Net: fewer lines, one place to change each concern, and every ordering hazard becomes a loud failure.

---

## 5. Delivered reference code (`refactor/`)

| Module | What it is | Validation |
|---|---|---|
| `statlib.py` | one within-position percentile primitive + `consensus`/`divergence`/`composite`; NaN policy is a named arg (`fill=None` abstain / `fill=50` neutral) | **exact parity** vs live `within_pos_pctl` on 371 real rows |
| `parse.py` | canonical `num`/`pct`/`pnum`/`ab` + one `team_code` (code/full/nickname/rank-prefix) | unit-tested edge cases incl. `"97%Elite"`, `"1PIT"`, `"Las Vegas Raiders"` |
| `featurestore.py` | `FeatureStore` (load/apply/save, **atomic CSV+JSON**) + `SourceSpec` (declarative source) | reproduced `ingest_advanced6` merge exactly (**145 WR/TE**), live store untouched |
| `registry.py` + `columns.json` | column → producer/dtype/coverage/abstains; `validate()` fails on drift | **139/139 registered, 0 unregistered** |
| `pipeline.py` | single orchestrator; per-stage column/sync/order integrity checks; `--check`/`--from` | `--check` green: csv/json in sync, all 18 stages' columns present |
| `tests/test_refactor.py` | the missing test layer | **6/6 PASS** |

> Adoption is incremental and reversible: the modules sit beside the working code and are swapped in one import / one stage at a time, with the test suite and `pipeline --check` as the gate. See `refactor/README.md`.
