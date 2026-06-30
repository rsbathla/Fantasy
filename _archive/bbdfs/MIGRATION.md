# Migration guide — adopt `bbdfs` one import at a time

The audit's core finding is an **adoption gap**: the right abstractions exist but nothing
imports them. This guide swaps the duplicates for the shared core incrementally, with the
test suite (`python3 bbdfs/tests/test_core.py`) as the gate after each step. Nothing here
is a big-bang rewrite; the live tools keep running throughout.

## Phase 0 — recover the feature store (do this first) 🔴

```bash
python3 bbdfs/tools/recover_feature_store.py            # diagnose: prints the 58 lost cols
# Option A (preferred): clean rebuild under the orchestrator
python3 refactor/pipeline.py                            # runs all stages in order, with checks
python3 -c "import json;print(len(json.load(open('features.json'))['meta']['cols']))"  # expect 139
# Option B (fallback snapshot): non-destructive, review then promote
python3 bbdfs/tools/recover_feature_store.py --write    # writes features.recovered.json
```
Then make the loss impossible to repeat silently: have consumers call
`bbdfs.core.load_features(require=[...])` so a missing column raises instead of abstaining.

## Phase 1 — adopt the shared leaf helpers (kills P2 duplication)

Swap each local helper for the shared one, one file per commit, running the tests between.

| Replace (in N files) | With |
|---|---|
| `def fn(n): ...` / `_norm` (~20 files) | `from bbdfs.core import fn` |
| `def num(x): ...` (10) / `def pct(x): ...` (6) | `from bbdfs.core import num, pct` |
| `TMAP = {...}` (12) / `norm_team` variants (3) | `from bbdfs.core import team_code, norm_team, TMAP` |
| `within_pos_pctl(...)` (5: fusion ×2, dfs_scenarios, ingest_defense, reweight) | `from bbdfs.core import pctl` |

Example (in `dfs_scenarios.py`):
```python
# before:  def within_pos_pctl(raw, pos): ...
from bbdfs.core import pctl
# ...
within_pos_pctl = lambda raw, pos: pctl(raw, pos)     # shim, or call pctl() directly
```

## Phase 2 — collapse the two fusion engines (kills P3)

`fusion.py` and `dfs_scenarios.py` both hand-roll the percentile + consensus/divergence
machinery. Re-express each as a **source list** fed to the shared engine:

```python
from bbdfs.core import SourceSet, fuse_board, leverage_flags

ss = SourceSet(df["pos"])
ss.add("ceiling", df["p95"])            # best-ball source list (fusion.py)
ss.add("spike",   df["spike"])
# ...or the DFS source list (dfs_scenarios.py): efficiency / matchup / opportunity
board = fuse_board(ss)                   # consensus, divergence, n_votes
tags  = leverage_flags(board)           # MARKET FADE / POLARIZING, shared
```
Parity-check the new `consensus`/`divergence` against the legacy JSON before deleting the
old code. Then unify the **playoff-week ceiling**: replace `engine/playoff_overlay.py`'s
offense-proxy and `dfs_scenarios`' inline P(ceiling) with `bbdfs.core.p_ceiling` +
`playoff_up` so the W15-17 ceiling is computed one way.

## Phase 3 — config-drive the flags (kills P4/P6)

Replace each `build_flags_<pos>.py` with a `bbdfs.flags.config.CONFIGS[pos]` table + the
shared engine:
```python
from bbdfs.flags import build_position, CONFIGS
records = build_position("WR", players, CONFIGS["WR"])   # writes boom/flags_WR.json
```
Porting QB/RB/TE/DST = transcribing each builder's `if/elif` cascade into `FlagSpec` rows
(see `flags/config.py` WR for the pattern). The grading path (`boom_lib.prob`/`label` via
`flag_engine.grade`) is unchanged, so `validate_boom.py` is the parity gate. Lift the
~190 scattered weights into `bbdfs.core.config` as you go.

## Phase 4 — orchestrate, de-bloat render, hygiene (P5/P7/P9)

- Make `refactor/pipeline.py` the **only** sanctioned build path; deprecate hand-running
  `ingest_advanced*.py`.
- `player_explorer.html`: stop inlining `player_tweets.json` (2.7 MB) — `fetch` it or load
  per-player on click. Collapse the 3 divergent `esc()` into one (the decision-dashboard
  one does no HTML-escaping — fix it). Promote `ui/bb-components.js` (already built, unused).
- Add `.gitignore` (`__pycache__/`, `*.pyc`, `*.tmp`, `*.bak`, `*.log`, `.~lock.*#`,
  `_prebuild_backup_*/`, generated `*.html`/`*.pdf`/`*.docx`); move to `src/ data/ out/ docs/`;
  delete the duplicate `merged_rankings_upload.csv` and the stray `lu*.tmp`.

## Rollback

Every phase is import-level and reversible: revert the one changed import and the legacy
path is back. The shared modules sit beside the working code; nothing is deleted until its
replacement is parity-verified.
