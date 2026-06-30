"""Within-position percentile + source-fusion statistics.

Replaces the `(rank-0.5)/n*100` within-position percentile reimplemented 5x
(fusion.within_pos_pctl + within_pos_pctl_series, dfs_scenarios.within_pos_pctl,
ingest_defense, reweight_defense_2026) and the consensus/divergence math duplicated
between fusion.py and dfs_scenarios.py.

Single source: refactor.statlib (pctl/consensus/divergence/composite). `zscore_blend`
lived only in dfs_scenarios; it is promoted here so the best-ball board can use the
same standardize-and-weight primitive.

NaN policy is an explicit argument, never an accident of which file you copied:
    pctl(..., fill=None) -> ABSTAIN (missing stays NaN)   [modeling default]
    pctl(..., fill=50)   -> NEUTRAL-FILL (display only)
"""
import numpy as _np
import pandas as _pd
from refactor.statlib import pctl, consensus, divergence, composite, NEUTRAL

__all__ = ["pctl", "consensus", "divergence", "composite", "zscore_blend", "NEUTRAL"]


def zscore_blend(drivers, weights=None):
    """Weighted blend of standardized drivers -> one raw vote (pre-percentile).

    drivers : list of aligned array-likes.
    weights : optional parallel list; if omitted, equal-weight nan-aware mean.
    Missing drivers are skipped per-row (a player with some drivers absent is still
    scored on the present ones), matching dfs_scenarios.zscore_blend semantics.
    """
    cols = [_pd.Series(_pd.to_numeric(_pd.Series(d), errors="coerce")).reset_index(drop=True)
            for d in drivers]
    if not cols:
        return _pd.Series(dtype=float)
    mat = _pd.concat(cols, axis=1)
    mat.columns = range(mat.shape[1])
    z = (mat - mat.mean()) / mat.std(ddof=0).replace(0, _np.nan)
    if weights is None:
        return z.mean(axis=1, skipna=True)
    w = list(weights)[:z.shape[1]]
    w = w + [0.0] * (z.shape[1] - len(w))
    w = _pd.Series(w, index=z.columns)
    num = (z * w).sum(axis=1, min_count=1)
    den = (z.notna() * w.abs()).sum(axis=1)
    return num / den.replace(0, _np.nan)
