"""bbdfs — unified Best-Ball + DFS toolkit package.

ONE shared core (names, teams, parsing, stats, feature store, source-fusion,
playoff-week ceiling, config) with thin best-ball and DFS layers on top.

This package CONSOLIDATES the proven-but-unadopted modules already in the repo
(core.py, refactor/parse.py, refactor/statlib.py, refactor/featurestore.py,
flag_engine.py, boom_lib.py) into one importable API, and adds the genuinely
missing shared engines (fusionkit, playoff_week, config) plus the bestball/ and
dfs/ splits the two models need.

Why a package: the audit found the same helpers re-implemented across the tree
(fn() in ~20 files, num() in 10, pct() in 6, team maps in 12, the within-position
percentile in 5, consensus/divergence in 2). Those are not re-implemented here —
they are imported from the one proven source and re-exported, so there is a single
place to change each concern.

Import side effect: puts the repo root on sys.path so the consolidated modules
resolve whether bbdfs is imported from the repo root or elsewhere.
"""
import os as _os
import sys as _sys

ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if ROOT not in _sys.path:
    _sys.path.insert(0, ROOT)

__version__ = "1.0.0"
