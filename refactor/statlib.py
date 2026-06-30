#!/usr/bin/env python3
"""
statlib — the SINGLE within-position percentile + fusion primitive.

Replaces three copy-pasted implementations of the `(rank-0.5)/n*100` math:
  - dfs_scenarios.within_pos_pctl(raw,pos)          [NaN-preserving]
  - fusion.within_pos_pctl(df,col,...,neutral)      [neutral-filled, for display]
  - fusion.within_pos_pctl_series(df,raw,...)        [NaN-preserving, for composites]

ONE ranking core (`_rank`), TWO explicit policies (abstain vs neutral-fill).
The NaN policy is now a NAMED CHOICE at the call site, not an accident of which
file you copied from. Pure pandas/numpy; no project imports, so it is trivially
unit-testable and shareable by every engine.
"""
import numpy as np
import pandas as pd

NEUTRAL = 50.0


def _rank(vals: pd.Series) -> pd.Series:
    """Within a single cohort: NaN-preserving percentile on (0,100].
    Absent -> NaN; a lone eligible player -> NEUTRAL (no spread to rank)."""
    out = pd.Series(np.nan, index=vals.index, dtype=float)
    present = vals.dropna()
    if len(present) == 0:
        return out
    if len(present) == 1:
        out.loc[present.index] = NEUTRAL
        return out
    r = present.rank(method="average")
    out.loc[present.index] = ((r - 0.5) / len(present) * 100.0).values
    return out


def pctl(values, pos, *, invert=False, fill=None, round_to=1) -> pd.Series:
    """Within-POSITION percentile (higher input -> higher pct unless invert).

    fill=None  -> ABSTAIN: missing/absent stay NaN  (dfs_scenarios policy)
    fill=50    -> NEUTRAL-FILL: applicable-but-absent -> 50 (fusion display policy)

    `values` and `pos` are aligned Series (or array-likes); one call, one policy.
    """
    values = pd.Series(pd.to_numeric(pd.Series(values), errors="coerce")).reset_index(drop=True)
    pos = pd.Series(pos).reset_index(drop=True)
    if invert:
        values = -values
    out = pd.Series(np.nan, index=values.index, dtype=float)
    for _, idx in pos.groupby(pos).groups.items():
        out.loc[idx] = _rank(values.loc[idx])
    if fill is not None:
        out = out.fillna(fill)
    return out.round(round_to)


def composite(component_pctls, *, scope_mask=None, fill=NEUTRAL, round_to=2):
    """Row-wise mean of already-ranked component percentiles, skipping absent ones.
    Returns (vote, real_mask): real_mask is True where >=1 component actually voted.
    Mirrors fusion.composite_vote semantics with the shared primitive."""
    if not component_pctls:
        n = 0
        empty = pd.Series(dtype=float)
        return empty, empty
    mat = pd.concat([pd.Series(c).reset_index(drop=True) for c in component_pctls], axis=1)
    vote = mat.mean(axis=1, skipna=True)
    real = mat.notna().any(axis=1)
    if scope_mask is not None:
        scope_mask = pd.Series(scope_mask).reset_index(drop=True)
        vote = vote.where(scope_mask)
        real = real & scope_mask
    return vote.round(round_to), (real & vote.notna())


def consensus(source_pctls) -> pd.Series:
    """Mean across independent source percentiles, skipping abstentions."""
    mat = pd.concat([pd.Series(s).reset_index(drop=True) for s in source_pctls], axis=1)
    return mat.mean(axis=1, skipna=True)


def divergence(source_pctls) -> pd.Series:
    """Std across independent source percentiles (disagreement = the signal)."""
    mat = pd.concat([pd.Series(s).reset_index(drop=True) for s in source_pctls], axis=1)
    return mat.std(axis=1, skipna=True)
