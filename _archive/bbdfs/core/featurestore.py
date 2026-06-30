"""Feature store — both sides of the store, in one place.

BUILD side: the proven refactor.featurestore (declarative SourceSpec merge; load once,
apply all, write once, atomically, with provenance). It replaces the 12 copy-pasted
"read features.csv -> mutate -> rewrite csv+json" ingest scripts.

READ side (added here): `load_features` + `FeatureFrame`. The audit found 15 consumers
re-opening features.json and indexing columns by raw string, where a missing column
silently degrades to "abstain". `FeatureFrame.require([...])` turns that into a LOUD
error — which is exactly the failure that let the live store silently drop 139 -> 81
columns without anything noticing.
"""
import json as _json
import os as _os
import pandas as _pd
import core as _core
from refactor.featurestore import FeatureStore, SourceSpec, merge_sources

__all__ = ["FeatureStore", "SourceSpec", "merge_sources", "load_features", "FeatureFrame"]


class FeatureFrame:
    """Typed view over features.json.

    .df       -> pandas DataFrame (one row per board player)
    .meta     -> the store's meta block (n, cols, provenance, added)
    .require(cols) -> raises KeyError listing every missing column (loud, not silent)
    """

    def __init__(self, df, meta):
        self.df = df
        self.meta = meta or {}

    @property
    def cols(self):
        return list(self.df.columns)

    def require(self, cols):
        missing = [c for c in cols if c not in self.df.columns]
        if missing:
            shown = missing[:12]
            more = "" if len(missing) <= 12 else f" (+{len(missing) - 12} more)"
            raise KeyError(
                f"feature store missing {len(missing)} required column(s): "
                f"{shown}{more}. Store has {len(self.df.columns)} columns. "
                f"This is the silent-column-loss failure mode — run the orchestrated "
                f"rebuild and re-validate the store."
            )
        return self

    def __len__(self):
        return len(self.df)


def load_features(root=None, require=None):
    """Load features.json into a FeatureFrame. If `require` is given, validate loudly."""
    root = root or _core.HERE
    with open(_os.path.join(root, "features.json"), encoding="utf-8") as fh:
        blob = _json.load(fh)
    df = _pd.DataFrame(blob.get("players", []))
    ff = FeatureFrame(df, blob.get("meta", {}))
    if require:
        ff.require(require)
    return ff
