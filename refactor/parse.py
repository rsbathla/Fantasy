#!/usr/bin/env python3
"""
parse — the SINGLE numeric/team parsing surface for ingest.

Consolidates parsers that were redefined in 11+ scripts:
  num()  (strip quotes/commas -> float)        -> was in 11 files
  pct()  (strip % -> rounded float)            -> was in 6 files
  pnum() (regex-extract first number)          -> was in ingest_advanced.py
  ab()   (strip rank prefix e.g. '1PIT'->PIT)  -> was in ingest_advanced.py
And ONE team resolver that folds core.TMAP + full-names + SIS nicknames so a code,
a full name ('Las Vegas Raiders'), a nickname ('Raiders'), or a rank-prefixed
token ('1PIT') all normalize to the same canonical code.

Re-exports core.fn / core.norm_team so ingest scripts have a single import.
"""
import re
import os as _o, sys as _s
_s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))))  # repo root for `core`
import core

fn = core.fn  # canonical name normalizer (do not redefine)

NICK = {  # SIS nickname -> code
    "Cardinals": "ARI", "Falcons": "ATL", "Ravens": "BAL", "Bills": "BUF", "Panthers": "CAR",
    "Bears": "CHI", "Bengals": "CIN", "Browns": "CLE", "Cowboys": "DAL", "Broncos": "DEN",
    "Lions": "DET", "Packers": "GB", "Texans": "HOU", "Colts": "IND", "Jaguars": "JAX",
    "Chiefs": "KC", "Raiders": "LV", "Chargers": "LAC", "Rams": "LAR", "Dolphins": "MIA",
    "Vikings": "MIN", "Patriots": "NE", "Saints": "NO", "Giants": "NYG", "Jets": "NYJ",
    "Eagles": "PHI", "Steelers": "PIT", "49ers": "SF", "Seahawks": "SEA", "Buccaneers": "TB",
    "Titans": "TEN", "Commanders": "WAS",
}
FULL2AB = {  # 'Las Vegas Raiders' -> LV  (last word is the nickname)
    **{f"{city} {nick}": code for nick, code in NICK.items() for city in [""]},
}


def num(x):
    """'"-2.07"' / '1,234' -> float, else None."""
    try:
        return float(str(x).replace('"', "").replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def pct(x, round_to=1):
    """'43.5%' -> 43.5 ; None on failure."""
    try:
        return round(float(str(x).replace("%", "").replace('"', "").strip()), round_to)
    except (TypeError, ValueError):
        return None


def pnum(x):
    """Extract the first signed/decimal number from messy text ('97%Elite' -> 97.0)."""
    m = re.search(r"-?\d+\.?\d*", str(x))
    return float(m.group()) if m else None


def ab(x):
    """Resolve to a team code. Try the RAW token first (protects '49ers' -> SF), then strip a leading
    rank prefix only as a fallback ('1PIT' -> PIT). Was corrupting '49ers' -> 'ers' by stripping first."""
    s = str(x).strip()
    c = team_code(s)
    _NFL32 = {'ARI','ATL','BAL','BUF','CAR','CHI','CIN','CLE','DAL','DEN','DET','GB','HOU','IND','JAX','KC',
              'LAC','LAR','LV','MIA','MIN','NE','NO','NYG','NYJ','PHI','PIT','SEA','SF','TB','TEN','WAS'}
    if c in _NFL32:
        return c
    return team_code(re.sub(r"^\d+", "", s).strip())


def team_code(s):
    """Resolve code / full name / nickname / messy token -> canonical code."""
    s = (str(s) if s is not None else "").strip()
    if not s:
        return s
    if s in NICK:
        return NICK[s]
    last = s.split()[-1]
    if last in NICK:                 # 'Las Vegas Raiders' -> LV
        return NICK[last]
    return core.norm_team(s)         # codes + TMAP aliases (LA->LAR, etc.)
