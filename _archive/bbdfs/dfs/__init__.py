"""bbdfs.dfs — the DFS model layer (thin, on the SAME shared core).

DFS wants a holistic per-player, per-matchup view: weekly ceiling shaped by the opponent
and the Vegas environment. The fusion math is identical to best ball (shared
core.fuse_board); the difference is the SOURCE LIST (matchup + environment + efficiency +
opportunity) and that the output is per-week (W15-17 here, extensible to any week via the
same core.playoff_week.p_ceiling).
"""
from .board import build_board
from .matchup import player_card

__all__ = ["build_board", "player_card"]
