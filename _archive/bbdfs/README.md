# bbdfs — unified Best-Ball + DFS toolkit

One **shared core** with thin **best-ball** and **DFS** layers on top. Built to resolve the
central finding of `AUDIT_2026_SENIOR_REVIEW.md`: the two models were built by copy-paste
(two source-fusion engines, the playoff-week ceiling computed twice, helpers re-defined
across ~20 files) instead of by sharing a core.

This package **consolidates, it does not reinvent.** Where the repo already had the right,
proven code (`core.py`, `refactor/parse.py`, `refactor/statlib.py`, `refactor/featurestore.py`,
`flag_engine.py`, `boom_lib.py`) `bbdfs` imports and re-exports it, so there is exactly one
source of truth. It adds only the genuinely missing pieces: the shared **fusion engine**,
the unified **playoff-week ceiling**, centralized **config**, the **fail-loud feature loader**,
the **two model layers**, and the **config-driven flag engine**.

## Layout

```
bbdfs/
  core/        names · teams · parse · statlib · io · featurestore · fusionkit · playoff_week · config
  bestball/    board (ceiling/spike/value/advancement + playoff overlay) · correlation/stacking
  dfs/         board (matchup/efficiency/opportunity + per-week P(ceiling)) · matchup (player card)
  flags/       engine (one config-driven builder) · config (per-position flag tables)
  tools/       recover_feature_store.py  (non-destructive 139→81 recovery)
  tests/       test_core.py              (12 property/parity/integration tests)
```

## Quick start

```python
from bbdfs import core, bestball, dfs

bb  = bestball.build_board()        # best-ball board (fused + playoff_up + bb_score)
df  = dfs.build_board()             # DFS board (fused + per-week P(ceiling))
card = dfs.player_card("Puka Nacua")  # holistic per-matchup view

# the shared engine both layers call:
ss = core.SourceSet(bb["pos"])
ss.add("ceiling", bb["bb_score"])          # any raw driver -> within-position percentile
board = core.fuse_board(ss)                 # consensus / divergence / n_votes
```

```bash
python3 bbdfs/tests/test_core.py             # 12/12
python3 -m bbdfs.bestball.board              # print BB board
python3 -m bbdfs.dfs.board                   # print DFS board
python3 bbdfs/tools/recover_feature_store.py # diagnose the corrupted store
```

## Design contract (shared by both models)

- Every data source becomes an **independent within-position percentile** in [0, 100].
- A source with no signal for a player **abstains (NaN)** — never filled to 50 inside the
  source. Neutral-fill is an explicit, display-only opt-in (`pctl(..., fill=50)`).
- `consensus` = nanmean of present sources; `divergence` = population nanstd (one vote → 0);
  `n_votes` = count present. **Disagreement is the leverage signal.**
- Missing *columns* (not missing player values) **fail loud** via `FeatureFrame.require(...)`
  — this is the guard against the silent 139→81 column loss.

## Notes

- Importing `bbdfs` puts the repo root on `sys.path` so the consolidated modules resolve.
- The boards currently read the **live (degraded 81-col) store** and abstain on absent
  columns; run the Phase-0 recovery and they get richer automatically.
- See `MIGRATION.md` for how to adopt this one import at a time without breaking the live tools.
