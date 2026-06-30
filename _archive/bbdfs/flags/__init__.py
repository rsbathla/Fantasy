"""bbdfs.flags — ONE config-driven flag engine, replacing the 5x hand-rolled builders.

The audit found build_flags_{QB,RB,WR,TE,DST}.py = 5,767 LOC, with the per-week condition
encoded FOUR incompatible ways and ~850-1,150 LOC of duplicated plumbing (load, week loop,
record assembly, write) that flag_engine.py + boom_lib already cover but the builders never
call. This engine calls them; a position becomes DATA (a list of FlagSpec). The valuable
position-specific SEMANTICS (the ~879 inline thresholds) move into flags/config tables.
"""
from .engine import FlagSpec, build_position, SKILL, MATCHUP, ENV, SUPPRESSOR
from .config import CONFIGS

__all__ = ["FlagSpec", "build_position", "SKILL", "MATCHUP", "ENV", "SUPPRESSOR", "CONFIGS"]
