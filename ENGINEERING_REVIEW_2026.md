# Engineering Review — NFL Best-Ball / DFS Model (2026)
*Senior review, fresh pass. Scope: the live `bestball/` codebase (excludes `_archive/`).*

## 1. Architecture & data flow

This is a **batch analytics monolith**: ~139 Python files / ~22.8k LOC, ~72 JSON + 64 CSV data
artifacts, 18 HTML dashboards. There is no service/DB — every stage reads files, writes files, and
the HTML boards embed a JSON blob. It runs as two orchestrated DAGs plus a live draft engine.

**Data flow (happy path):**
```
RAW SOURCES                         → INGEST / PROJECTION              → SPINE
DK ADP (DkPreDraftRankings)           pipeline/parse_clay, sim_prod,     draft_board_signals.csv
Clay 2026, SIS DataHub, FantasyPoints   build_layer2, build_draft_board   features.json (+csv)
PFF, nflverse parquet, tweets.db        build_features + ingest_advanced1-10
                                                                          defense.json
MODEL                               → BOARDS / OUTPUTS                 → LIVE
fusion.py        → fusion.json        command_center.html               engine/run_live.py
boom_pipeline    → boom_marks.json    intel.html / rankings.html        + decision_tree + bbengine
normalize_defense_2026 → defense.json player_explorer / dashboards      → live_tree.json + dashboard
merge_rankings   → merged_rankings    
```

**Orchestrators / entry points (5):** `refactor/pipeline.py` (features→defense→fusion→command_center),
`boom_pipeline.py` (boom subsystem, 26 stages), `refresh_all.py` (master), `refresh_intel.py` (daily
tweets), `engine/run_live.py` (live draft). The first two are well-built: ordered stage lists with
per-stage integrity checks and `--check`/`--from` modes. That's the strongest part of the codebase.

**Layering (as-built):** there is an *intended* shared core (`core.py`: `fn`, `norm_team`, `P`,
`safe_json_dump`) but it is **inconsistently adopted** — most scripts bypass it (see §2.1). The
`bbdfs/` package was a clean-architecture rewrite that was **never imported by anything** and is now
archived (see §2.7).

## 2. Problem areas (evidence-based, ranked by risk)

### 2.1 — No single identity key: 24 divergent name-normalizers  ⚠ CORRECTNESS
Player joins are the backbone (every CSV/JSON is keyed by a normalized name). **24 files define their
own `fn`/`_norm`, and they disagree:**

| name | `core.fn` / `merge` | `build_intel` norm |
|---|---|---|
| Amon-Ra St. Brown | `amon ra st brown` | `amonra st brown` |
| Kenneth Walker III | `kenneth walker` | `kenneth walker iii` |
| Marvin Harrison Jr. | `marvin harrison` | `marvin harrison jr` |

These are **silent join misses** — a player simply vanishes from a merge with no error. This class of
bug bit us live this session (the intel tweet→player and team-comparable matching). It is the single
highest-leverage fix in the codebase.

### 2.2 — Duplication: 16 team-abbrev maps, 3 glob helpers, ~195 thresholds
`FULL2ABBR`/team-alias maps are copy-pasted across **16 files**; the `_latest()` glob helper across
**3** (`merge_rankings`, `build_draft_board`, `build_ud_board`). The `_latest` copies have a real
**latent bug**: `sorted(glob(...))[-1]` picks `DkPreDraftRankings.csv` over `... (2).csv` (space sorts
before `.`), i.e. the *oldest* file — only avoided this session by hand-copying the upload to a
sorts-last name. The boom flag layer also carries ~195 hand-set thresholds (the overfit surface from
`AUDIT_OVERFIT_2026.md`).

### 2.3 — No data-access layer: the spine is re-parsed 17–24× 
`features.json` is opened+parsed by **24** scripts, `draft_board_signals.csv` by **17**,
`fusion_table.csv` by **9** — each independently, each applying its *own* normalizer (§2.1). There is
no cached loader and no schema. This is both a performance cost (re-parsing multi-hundred-KB JSON
repeatedly) and the surface that lets §2.1 diverge.

### 2.4 — Sprawl & unclear liveness: 30 `build_*` + 11 `ingest_*` scripts
139 modules with no manifest of what is live vs legacy. Three orphans were discovered *this session*
(`bbdfs/`, `build_player_tweets.py`, and — until wired — `coordinator_scheme` + `defender_grades`). A
new engineer cannot tell which scripts matter without running greps.

### 2.5 — Orchestration gaps
Two DAGs that must run in a specific order with no top-level guard: `command_center` historically ran
*inside* the refactor pipeline **before** boom produced `boom_marks` (stale board — fixed this session
by making it boom's final stage). `derive_boom_threshold` reads a `dfs_review/` file absent in some
environments; `build_draft_board` has a cwd assumption + a missing `w17_blowup_rank.csv` input. These
are the kind of failures that only surface at run time.

### 2.6 — Data embedded in code
`build_def_profile.py` hardcodes a 32-team DVOA table as a `RAW=""" """` block; `build_defender_grades.py`
hardcodes 50 CB grades. Updating data requires editing Python; there's no provenance/versioning.

### 2.7 — Thin tests + a cautionary tale
**5 test files for 139 modules** (`api`, `engine/bbengine`, `refactor`, two stragglers). Nothing tests
the join keys, pipeline smoke, or rankings determinism. Separately: `bbdfs/` was a *full* "shared-core +
BB/DFS layers" rewrite — well-designed, but **nothing ever imported it**, so it silently rotted while
all real work happened in the top-level scripts. **Lesson: big-bang parallel rewrites do not land here;
migrate in place.**

### 2.8 — Environment brittleness
Writers were historically non-atomic; the mounted filesystem truncated tool-writes repeatedly this
session. The hardened writers (`run_live._write_json_safely`, the boom builders' temp+rename) are the
right pattern — but it's applied unevenly.

## 3. Refactor strategy (incremental, keep the pipeline green)

Ordered by leverage ÷ risk. **Each step ships independently and leaves the live model working** — the
explicit anti-pattern is another `bbdfs` parallel rewrite.

1. **P0 — One identity. (low risk, highest leverage.)** Make `core.fn` THE canonical player key and add
   `core.team_abbr()` + `core.latest()`. Migrate the 24/16/3 call sites *incrementally*, starting with
   the spots where divergence is active. Add a one-assert test that all normalizers agree on a fixture
   of hard names (St. Brown, Walker III, Harrison Jr., D'Andre Swift). Fix the `_latest` sort bug.
2. **P1 — Thin data-access layer.** `core.load_features()`, `core.load_board()` — parse once, cache,
   return rows keyed by `core.fn`. Convert the 24 re-readers to it over time. Removes the divergence
   surface *and* the repeated-parse cost.
3. **P2 — One orchestrator.** Promote `refresh_all.py` to the single entry with a stage registry +
   integrity gates (the two existing DAGs already have the machinery). Kill cwd assumptions: every path
   via `core.P`. Make `derive_boom_threshold`/`build_draft_board` degrade gracefully when inputs absent.
3. **P3 — Data out of code.** Move the DVOA table and CB grades to versioned CSVs under `data/`.
4. **P4 — Liveness manifest + prune.** A `PIPELINE.md` (or the stage registry itself) declares the live
   DAG; everything not reachable from it gets archived. Enforce the both-years stability gate for any
   new boom flag (we have `validate_signal_stability.py` — make it a required check).
5. **P5 — Spine tests.** Join-key fixture, pipeline `--check` in CI, rankings determinism (same inputs →
   same `merged_rank`).

## 4. Target architecture

Same monolith, but with a real spine and one source of truth — reachable by in-place migration:

```
core/            identity (fn/pkey), teams (abbr+aliases), io (cached loaders, atomic writes), paths (P, latest)
data/            ALL raw + derived files (no data literals in code; provenance-tagged)
pipeline/        projections → board   (one DAG)
model/           defense engine · fusion · boom   (consume the spine via core.io)
outputs/         renderers: command_center · intel · rankings · dashboards   (pure read)
engine/          live draft
refresh_all.py   the ONE orchestrator: stage registry + integrity gates + --check/--from
```

The discipline that makes it stick: **nothing re-implements identity, team mapping, file discovery, or
file IO** — those live only in `core`. Every other module is a pure function of the spine. This is the
design `bbdfs/` aimed at; the difference is we get there by moving the *live* code onto `core` one call
site at a time, never by maintaining a second copy.

## 5. What this review already actioned
Branch 2 (overfit prune), Branch 3 (fusion on the 2026 defense), Branch 4 (funnel/defender reconcile),
the orphan wiring (coordinator scheme, CB1 grades), `command_center`-after-boom ordering, and the
`bbdfs`/legacy archive are done. The remaining backlog is P0–P5 above; P0 + the `_latest` fix are
delivered alongside this review (see `core.py` additions + `names` consistency check).
