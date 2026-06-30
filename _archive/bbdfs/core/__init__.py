"""bbdfs.core — the single shared substrate.

Re-exports the canonical primitives so every consumer imports from ONE place
instead of re-defining helpers. Each name below replaces a cluster of duplicates
found in the audit:

    fn / canon            <- ~20 hand-rolled name normalizers
    team_code / norm_team <- 12 TMAP literals + 3 norm_team variants
    num / pct / pnum / ab <- num() x10, pct() x6
    pctl / consensus /
      divergence / composite / zscore_blend
                          <- within_pos_pctl x5, consensus/divergence x2
    safe_json_dump        <- the one atomic, NaN-safe writer
    FeatureStore /
      load_features       <- the 12-script append-only chain (build) + 15 raw readers
    fuse_board            <- the source-fusion engine duplicated in fusion & dfs
    p_ceiling / playoff_up<- the W15-17 ceiling computed twice (dfs vs playoff_overlay)
"""
from .names import fn, canon
from .teams import team_code, norm_team, TMAP, NICK
from .parse import num, pct, pnum, ab
from .statlib import pctl, consensus, divergence, composite, zscore_blend, NEUTRAL
from .io import safe_json_dump, load_json, load_csv, repo_path
from .featurestore import (
    FeatureStore, SourceSpec, merge_sources, load_features, FeatureFrame,
)
from .fusionkit import fuse_board, leverage_flags, SourceSet
from .playoff_week import p_ceiling, playoff_up, WEEK_W
from . import config

__all__ = [
    "fn", "canon", "team_code", "norm_team", "TMAP", "NICK",
    "num", "pct", "pnum", "ab",
    "pctl", "consensus", "divergence", "composite", "zscore_blend", "NEUTRAL",
    "safe_json_dump", "load_json", "load_csv", "repo_path",
    "FeatureStore", "SourceSpec", "merge_sources", "load_features", "FeatureFrame",
    "fuse_board", "leverage_flags", "SourceSet",
    "p_ceiling", "playoff_up", "WEEK_W", "config",
]
