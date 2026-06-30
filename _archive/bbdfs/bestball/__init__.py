"""bbdfs.bestball — the BEST-BALL model layer (thin, on the shared core).

Best ball drafts a season-long roster judged on cumulative advancement (W1-14) plus
single-week playoff ceiling (W15-17). What makes this layer 'best-ball' is the SOURCE
LIST and the objective, NOT a private copy of the fusion math — it calls core.fuse_board
and core.playoff_week like the DFS layer does.

The simulation spine (pipeline/sim_prod, survival_chain, win_delta) and the live draft
engine (engine/bbengine, decision_tree, playoff_overlay) are the already-clean best-ball
assets; this package is the board/correlation surface that sits over the shared core and
should, during migration, feed those engines via core accessors instead of CSV reaches.
"""
from .board import build_board
from .correlation import stack_bonus, R_QB_WR1, R_BRINGBACK

__all__ = ["build_board", "stack_bonus", "R_QB_WR1", "R_BRINGBACK"]
