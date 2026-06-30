"""fusionkit — the SHARED source-fusion engine.

THE central duplication the audit found: fusion.py (draft board) and dfs_scenarios.py
(weekly board) independently re-implemented the SAME machinery — turn each data source
into a within-position percentile (abstain, never neutral-fill), then report consensus
(nanmean), divergence (population nanstd, single vote -> 0), n_votes, and leverage tags.
~350-450 LOC of conceptually identical code lived in two files.

This is that engine, once. Both bb/board.py and dfs/board.py build their boards by
handing fusionkit their own list of sources; the difference between the two MODELS becomes
a difference in the source list and weights, not a second copy of the fusion math.

Contract (preserved verbatim from both engines):
  * every source is an independent within-position percentile in [0, 100]
  * a source ABSTAINS (NaN) when it has no signal for a player — never filled to 50
    inside the source (optional neutral-fill is a display-only choice at the edge)
  * consensus  = nanmean across present sources
  * divergence = population nanstd across present sources (one vote -> 0.0)
  * n_votes    = count of present sources
  * disagreement (divergence) is itself the leverage signal (FADE / DARLING / POLARIZING)
"""
from dataclasses import dataclass, field

import pandas as pd

from . import statlib
from . import config

__all__ = ["SourceSet", "fuse_board", "leverage_flags"]


@dataclass
class SourceSet:
    """Collects named sources for one position-aware board.

    pos: a Series of positions aligned to the player rows.
    Use .add(name, raw, ...) to register each source; raw is either a pre-ranked
    percentile (already_pctl=True) or a raw driver to be within-position ranked here.
    """
    pos: pd.Series
    _ranked: dict = field(default_factory=dict, init=False)

    def add(self, name, raw, *, invert=False, already_pctl=False):
        s = pd.Series(raw).reset_index(drop=True)
        self._ranked[name] = s.round(1) if already_pctl else statlib.pctl(s, self.pos, invert=invert)
        return self

    def add_blend(self, name, drivers, weights=None, *, invert=False):
        """Register a source built from several standardized drivers (zscore_blend)."""
        raw = statlib.zscore_blend(drivers, weights)
        self._ranked[name] = statlib.pctl(raw, self.pos, invert=invert)
        return self

    def matrix(self):
        return pd.DataFrame(self._ranked)


def fuse_board(sourceset):
    """SourceSet -> DataFrame[<each source percentile>, consensus, divergence, n_votes]."""
    mat = sourceset.matrix()
    out = mat.copy()
    out["consensus"] = mat.mean(axis=1, skipna=True).round(1)
    out["divergence"] = mat.std(axis=1, ddof=0).round(1).fillna(0.0)
    out["n_votes"] = mat.notna().sum(axis=1).astype(int)
    return out


def leverage_flags(board, *, hot=None, cold=None, polar=None):
    """Human-readable leverage tags from consensus/divergence — the shared half of
    fusion.make_flags + dfs_scenarios.make_profile. Returns a list[list[str]] aligned
    to board rows. Thresholds default to config so they are set once."""
    hot = config.HOT_PCTL if hot is None else hot
    cold = config.COLD_PCTL if cold is None else cold
    polar = config.POLARIZING_DIV if polar is None else polar
    tags = []
    for _, r in board.iterrows():
        f = []
        c, d, n = r.get("consensus"), r.get("divergence"), r.get("n_votes", 0) or 0
        if pd.notna(c):
            if c >= hot:
                f.append("CONSENSUS_UP")
            elif c <= cold:
                f.append("CONSENSUS_DOWN")
        if pd.notna(d) and d >= polar and n >= 3:
            f.append("POLARIZING")  # sources disagree -> leverage (FADE/DARLING)
        tags.append(f)
    return tags
