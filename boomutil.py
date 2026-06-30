#!/usr/bin/env python3
"""
boomutil — ONE import for the boom subsystem's leaf helpers.

The audit found fn() redefined 7x, team-code maps 6x (with one inconsistency — only
build_defense_shell.py mapped the FantasyPoints aliases BLT/CLV/HST), and num() in ~3 drifted
variants. This consolidates them onto the repo's canonical core.py.

    from boomutil import fn, team, num, rows, dump

Verified against the on-disk data: the boom subsystem's name convention maps a hyphen to a
SPACE (statmenu key for Amon-Ra St. Brown is "amon ra st brown"), which is EXACTLY core.fn.
So fn here aliases core.fn directly (no divergence — an earlier note claiming otherwise was
wrong). team() = core.norm_team plus the FantasyPoints aliases so every script agrees.
"""
import os, csv, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # repo root for `core`
import core

fn = core.fn  # canonical: lowercase, strip Jr/Sr/II-V, drop . ' , hyphen->space, collapse ws

# team codes: core.TMAP + the FantasyPoints export aliases (BLT/CLV/HST were the ones only
# build_defense_shell.py knew). Verified == defense_shell's FPMAP for all keys.
FP_ALIASES = {'BLT': 'BAL', 'CLV': 'CLE', 'HST': 'HOU', 'ARZ': 'ARI', 'LA': 'LAR'}

def team(code):
    """Canonical team abbreviation, FantasyPoints-alias aware. None/'' -> ''."""
    c = (str(code) if code is not None else '').strip().upper()
    if not c:
        return ''
    return core.norm_team(FP_ALIASES.get(c, c))

def num(x, d=None):
    """Tolerant float: handles '95%', '1,234', '$', '', None. Returns d (default None) on failure.
    Matches the boom scripts' num() which return None on bad input."""
    if x is None:
        return d
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip().replace('%', '').replace(',', '').replace('$', '')
    if s in ('', '-', 'NA', 'N/A', 'nan', 'None'):
        return d
    try:
        return float(s)
    except ValueError:
        return d

def rows(path):
    """One CSV reader for the whole subsystem. BOM-safe (utf-8-sig). Returns list[dict]."""
    with open(path, encoding='utf-8-sig') as fh:
        return list(csv.DictReader(fh))

dump = core.safe_json_dump  # atomic, NaN-safe JSON writer

if __name__ == '__main__':
    # match the REAL boom convention (hyphen -> space), verified against statmenu.json keys
    assert fn("Amon-Ra St. Brown") == "amon ra st brown", fn("Amon-Ra St. Brown")
    assert fn("Jaxon Smith-Njigba") == "jaxon smith njigba", fn("Jaxon Smith-Njigba")
    assert fn("Michael Pittman Jr.") == "michael pittman", fn("Michael Pittman Jr.")
    assert team('BLT') == 'BAL' and team('CLV') == 'CLE' and team('HST') == 'HOU'
    assert team('ARZ') == 'ARI' and team('LA') == 'LAR' and team('KC') == 'KC'
    assert num('95%') == 95.0 and num('1,234') == 1234.0 and num('') is None and num('x', -1) == -1
    print("boomutil self-test OK: fn==core.fn (hyphen->space) / team(+FP aliases) / num")
