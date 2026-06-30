"""Canonical numeric/text parsers for ingest + engines.

Replaces num() (10 copies across ingest_advanced*.py, ingest_defense, reweight,
build_features), pct() (6 copies), and the pnum()/ab() pair. Single source:
refactor.parse — re-exported so ingest scripts swap a local def for one import.
"""
from refactor.parse import num, pct, pnum, ab, team_code

__all__ = ["num", "pct", "pnum", "ab", "team_code"]
