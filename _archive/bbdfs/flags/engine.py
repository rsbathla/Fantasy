"""flags/engine — ONE config-driven flag engine.

Replaces the duplicated scaffolding in the 5 build_flags_*.py builders. The grading path is
the EXISTING, backtest-calibrated one: boom_lib.prob (shrink-aware + capped) via
flag_engine.grade, and boom_lib.label for the SMASH/GOOD/NEU/TOUGH setup grade. The week
loop, BYE/FA handling, record assembly, and write all come from flag_engine + boom_lib —
exactly the modules the original builders defined but never imported.

A position is now DATA: a list[FlagSpec]. Each FlagSpec has a `test(ctx) -> bool` where
ctx = the player's season fields merged with the current week's matchup/env fields. This
unifies the four incompatible per-week encodings (QB/DST dict-of-conditions, RB tuple+add(),
TE inline if/elif, WR inline if/elif+suppress) into one.
"""
from dataclasses import dataclass
from typing import Callable

import flag_engine
import boom_lib

SKILL = "skill"          # player/season flag, evaluated once
MATCHUP = "matchup"      # per-week opponent flag
ENV = "env"              # per-week environment (Vegas) flag
SUPPRESSOR = "suppressor"  # per-week down-multiplier

_PER_WEEK = (MATCHUP, ENV, SUPPRESSOR)


@dataclass
class FlagSpec:
    name: str
    kind: str                 # SKILL | MATCHUP | ENV | SUPPRESSOR
    test: Callable            # ctx(dict) -> bool
    mult: float = 1.10        # multiplier when lit (>1 boost, <1 suppress)
    label: str = ""           # human-readable description when lit

    def lit(self, ctx):
        try:
            return bool(self.test(ctx))
        except Exception:
            return False       # a missing field never crashes a build; the flag just abstains


def build_position(pos, players, specs, *, write=True):
    """Build flags for one position from a config table.

    players : list of player ctx dicts. Each needs at least:
        name, team, adp, base (0-1 ceiling rate), weeks=[{wk, opp, home, dome, of, bye?, fa?, ...}]
      plus whatever season fields the SKILL specs read, and whatever per-week fields the
      MATCHUP/ENV specs read (merged into ctx per week).
    specs   : list[FlagSpec] for this position (from flags.config.CONFIGS[pos]).

    Returns the records list and (optionally) writes boom/flags_<pos>.json via boom_lib.write
    — byte-identical output contract to the legacy builders, so validate_boom still applies.
    """
    skill_specs = [s for s in specs if s.kind == SKILL]
    week_specs = [s for s in specs if s.kind in _PER_WEEK]
    out = []
    for p in players:
        base = p.get("base")
        if base is None:
            continue  # ungradeable (no base ceiling rate) — skipped, as the builders do
        skill_flags = [s.name for s in skill_specs if s.lit(p)]
        weeks = []
        for w in p.get("weeks", []):
            if w.get("bye"):
                weeks.append(flag_engine.bye_week(w["wk"]))
                continue
            if w.get("fa"):
                weeks.append(flag_engine.fa_week(w["wk"]))
                continue
            ctx = {**p, **w}
            lit, mults = [], []
            for s in skill_specs:
                if s.name in skill_flags:
                    lit.append(s.name)
                    mults.append(s.mult)
            for s in week_specs:
                if s.lit(ctx):
                    lit.append(s.name)
                    mults.append(s.mult)
            p_int, lab = flag_engine.grade(base, mults)
            weeks.append(flag_engine.week(w["wk"], w.get("opp"), w.get("home"),
                                          w.get("dome"), p_int, lab, len(lit),
                                          w.get("of"), lit))
        rec = flag_engine.record(
            p["name"], pos, p.get("team"), p.get("adp"),
            int(round(base * 100)), p.get("hist", False),
            p.get("n_games", 0), p.get("boom_games", 0),
            skill_flags, p.get("line", ""), weeks, p.get("empirical", ""),
        )
        out.append(rec)
    if write and out:
        boom_lib.write(pos, out)
    return out
