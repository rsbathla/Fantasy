#!/usr/bin/env python3
"""Parser for an Underdog (Best Ball Mania) draft-room board paste.

Underdog's copied board is less rigidly structured than DraftKings'. Rather than assume an exact
line layout, this parser is NAME-ANCHORED: it finds every board player whose name appears in the
pasted text (with abbreviated-name expansion, e.g. "J. Jefferson" -> "Justin Jefferson"), which gives
the DRAFTED set robustly across UD layout variants. Current pick = drafted + 1.

Determining which picks are YOURS is the one format-specific piece. Three ways, in priority:
  1. --mine override: caller passes the explicit list of your picks (always correct).
  2. A "your team"/username-delimited block if present in the paste (heuristic; refined once a real
     UD paste is available to lock the exact markers).
  3. Seat-based snake inference from pick order if the paste preserves pick order.

This keeps Underdog usable today (via --mine) and auto-parses once the exact UD copy format is pinned.
UD = 18 rounds, half-PPR (ud_pg projections), 18-man rosters.
"""
import re

def _norm(n):
    n = str(n).strip().lower(); n = re.sub(r'\s+(jr|sr|ii|iii|iv|v)\.?$', '', n)
    n = n.replace('.', '').replace("'", "").replace('-', ' '); return ' '.join(n.split())

_PICKNUM = re.compile(r'\b(\d{1,2})\.(\d{1,2})\b')          # round.pick like 5.07
_ABBR = re.compile(r'\b([A-Z])\.?\s*([A-Z][a-zA-Z\'\-]+)\b') # "J. Jefferson" / "J Jefferson"

def is_ud_board(text):
    """Heuristic UD detection: Underdog boards lack DK's 'On the clock: Pick N' marker and the
    QB/#/RB/#/WR/#/TE/# manager-column header. Treat as UD when DK markers are ABSENT but the text
    clearly contains drafted players (handled by the launcher's platform resolution)."""
    t = text or ''
    dk = bool(re.search(r'On the clock:\s*Pick\s*\d+', t, re.I))
    return not dk

def _build_index(board):
    """(first-initial, last-name) -> [board rows]  and  full-norm -> row, for name resolution."""
    by_abbr = {}; by_full = {}
    for p in board:
        toks = _norm(p['name']).split()
        if not toks:
            continue
        by_full[_norm(p['name'])] = p
        by_abbr.setdefault((toks[0][:1], toks[-1]), []).append(p)
    return by_abbr, by_full

def _resolve(token_name, by_abbr, by_full):
    """Resolve a found name fragment to a board player's canonical name (or None)."""
    nk = _norm(token_name)
    if nk in by_full:
        return by_full[nk]['name']
    toks = nk.split()
    if len(toks) >= 2:
        cands = by_abbr.get((toks[0][:1], toks[-1]), [])
        if len(cands) == 1:
            return cands[0]['name']
        if cands:  # ambiguous initial+last: prefer exact-length match else first
            exact = [c for c in cands if _norm(c['name']) == nk]
            return (exact or cands)[0]['name']
    return None

def parse_ud_board(text, me='', board=None, mine=None):
    board = board or []
    by_abbr, by_full = _build_index(board)
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    # --- DRAFTED set: every board player whose (full OR abbreviated) name appears in the paste ---
    drafted = []
    seen = set()
    # full-name hits anywhere in the text
    low = '\n'.join(lines)
    # match the board's _norm exactly: drop apostrophes WITHOUT inserting a space (Ja'Marr -> jamarr),
    # then turn remaining punctuation into spaces (Amon-Ra -> amon ra) so substring hits align.
    low_norm = ' ' + re.sub(r'[^a-z0-9 ]+', ' ', low.lower().replace("'", "").replace("’", "")) + ' '
    for full, p in by_full.items():
        if len(full) >= 5 and (' ' + full + ' ') in low_norm and full not in seen:
            drafted.append(p['name']); seen.add(full)
    # abbreviated-name hits ("J. Jefferson")
    for m in _ABBR.finditer(low):
        nm = _resolve(m.group(0), by_abbr, by_full)
        if nm and _norm(nm) not in seen:
            drafted.append(nm); seen.add(_norm(nm))

    # --- current pick / round ---
    picknums = [(int(a), int(b)) for a, b in _PICKNUM.findall(low)]
    cur_pick = None
    m = re.search(r'\bon the clock[^0-9]*(\d+)\b', low, re.I) or re.search(r'\bpick\s*(\d+)\b', low, re.I)
    if m:
        cur_pick = int(m.group(1))
    if cur_pick is None:
        cur_pick = len(drafted) + 1
    # Round is DERIVED from the authoritative current pick (12-team pod snake). The "Round N of 18"
    # text is the format header / repeats per round in a full paste, so it is NOT used for the
    # current round (that was the bug that pinned multi-round pastes to round 1).
    rnd = (cur_pick - 1) // 12 + 1

    # --- my roster ---
    my_roster = []
    if mine:
        want = [_norm(x) for x in mine]
        bynk = {_norm(p['name']): p['name'] for p in board}
        for w in want:
            if w in bynk:
                my_roster.append(bynk[w])
            else:
                r = _resolve(w, by_abbr, by_full)
                if r:
                    my_roster.append(r)
    elif me:
        # heuristic: lines bracketed by the username `me` (refined with a real UD paste)
        idxs = [i for i, l in enumerate(lines) if _norm(l) == _norm(me)]
        for i in idxs:
            for j in range(i + 1, min(i + 30, len(lines))):
                nm = _resolve(lines[j], by_abbr, by_full)
                if nm and _norm(nm) not in {_norm(x) for x in my_roster}:
                    my_roster.append(nm)

    counts = {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0}
    posof = {_norm(p['name']): p['pos'] for p in board}
    for n in my_roster:
        pp = posof.get(_norm(n))
        if pp in counts:
            counts[pp] += 1
    gone = {_norm(x) for x in drafted}
    available = [p['name'] for p in board if _norm(p['name']) not in gone]
    seat = ((cur_pick - 1) % 12) + 1 if cur_pick else None
    return {'pick': cur_pick, 'round': rnd, 'seat': seat, 'my_roster': my_roster,
            'counts': counts, 'available': available, 'n_drafted': len(drafted),
            'n_teams': 12, 'platform': 'UD'}

if __name__ == '__main__':
    import sys, bbengine as bb
    txt = open(sys.argv[1], encoding='utf-8', errors='replace').read()
    st = parse_ud_board(txt, sys.argv[2] if len(sys.argv) > 2 else '', bb.load_board())
    print('UD pick', st['pick'], 'round', st['round'], 'drafted', st['n_drafted'], 'mine', st['my_roster'])
