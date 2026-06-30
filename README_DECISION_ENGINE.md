# Best Ball 2026 — Decision-Tree Engine

DraftKings Best Ball, 12-team pods: **top-2 of 12 advance on W1–14 cumulative points**, then single-week
playoff gates **W15 (top 50%) → W16 (top 50%) → W17 (top 10%)**. The engine maximizes regular-season
**advancement** (volume) and **overlays W15/16/17 ceiling** (upside), then turns the board + your roster
into **branching decision trees** for each pick.

## Run it live (during a draft)
```
# 1. copy the DK board to Board.txt (or pipe clipboard), then:
cd engine && python3 run_live.py ../Board.txt rsbathla     # -> engine/live_tree.json
cd .. && python3 build_decision_dashboard.py               # -> decision_dashboard.html (embeds the live tree)
# open decision_dashboard.html
```
`run_live.py` parses the board, reconstructs the 12-team field, builds the decision tree, and prints the
headline pick + branches. Players you drafted that aren't in the sim universe are listed as `untracked`.

## Pieces
- `engine/bbengine.py` — clean API over the existing sim. `load_board()`, `grade(rosters,me)` (=survival_chain,
  reproduced exactly), `pick_values(rosters,me,cands)` (=win_delta marginal Δ), `parse_board(text,seat)`.
- `engine/playoff_overlay.py` → `playoff_overlay.csv` — per-player **W15–17 ceiling overlay** (own ceiling ×
  playoff-week matchup, W17 weighted heaviest).
- `engine/decision_tree.py` — `build_tree(board,rosters,me,seat,pick,rnd,plies)` → the Contract-3 decision tree.
  Score = `0.6·dTitle + 0.4·dAdv` + playoff_up tilt (off R1–7, tiebreak R8–10, primary R11+) + build-curve
  need (QB2-3/RB5-6/WR8-9/TE2-3, QB-before-R6 discipline) + stack/anchor bonus + uncorrelated-bye penalty.
  Picks valued **over replacement** (rosters padded to 18 with fillers) so deltas are realistic at any stage.
- `engine/run_live.py` — board → field → tree (production entry).
- `decision_dashboard.html` (+ `build_decision_dashboard.py`) — self-contained, plain-HTML interactive tree.
- `docs/STRATEGY_SPEC.md` — the construction strategy. `engine/CONTRACTS.md` — interfaces. `engine/tree_schema.json` — output schema.

## Validate
```
cd engine && python3 test_bbengine.py            # API + grade==chain
cd engine && python3 verify_decision_tree.py     # build_tree + schema
NODE_PATH=<jsdom> node _validate_dashboard.cjs    # UI render + interactions, 0 JS errors
```

## Status / honesty
Built on the validated 2026 compositional Monte Carlo (Clay means, real schedule, calibrated correlations).
Independently reviewed (GO): engine fidelity exact, all strategy rules implemented, overlay sound, schema +
dashboard clean. Deltas are marginal-over-replacement (comparable within a pick). Caveat: pick value is a
within-position tiebreaker; the construction heuristics carry most of the ranking by design.
