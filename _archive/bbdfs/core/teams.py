"""Canonical NFL team-code resolution.

Replaces the TMAP literal copied into 12 files and the 3 divergent norm_team variants
(the LA->LAR Rams bug once lived in one copy and not the others). Resolves any of:
code ('LV'), full name ('Las Vegas Raiders'), nickname ('Raiders'), or rank-prefixed
token ('1LV') to ONE canonical code, via the proven refactor.parse.team_code which folds
core.TMAP + the SIS nickname map.
"""
import core as _core
from refactor import parse as _parse

TMAP = _core.TMAP            # code-alias map (LA->LAR, JAC->JAX, ...)
NICK = _parse.NICK           # nickname -> code (Raiders -> LV)
norm_team = _core.norm_team  # code/alias -> canonical code
team_code = _parse.team_code  # full/nick/prefixed/code -> canonical code
