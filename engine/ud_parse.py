#!/usr/bin/env python3
"""Parser for an Underdog (Best Ball Mania) draft-room board paste.

Real UD copy format (validated against a live board): a left gutter of round numbers (1..18), then a
block PER TEAM:
    USERNAME
    QB0 / RB2 / WR3 / TE0          (current position counts, POS immediately followed by the count)
    <name> / <overall#> / "POS - TEAM (bye)" / <round.pick>   x N drafted players
    <overall#> / <round.pick>      x remaining empty slots
"On the clock..." marks the team currently picking.

Parsing is ANCHORED on the distinctive "POS - TEAM (bye)" line: for each such line the player NAME is
two lines above, the overall pick one line above, the round.pick one line below. Each player is
attributed to the most recent USERNAME block. The user's roster = the --seat block (matched by
username), else the team On The Clock. Falls back to name-anchored extraction if the structured
format isn't detected. UD = 18 rounds, half-PPR (ud_pg).
"""
import re

def _norm(n):
    n = str(n).strip().lower(); n = re.sub(r'\s+(jr|sr|ii|iii|iv|v)\.?$', '', n)
    n = n.replace('.', '').replace("'", "").replace('-', ' '); return ' '.join(n.split())

_POSTEAM = re.compile(r'^(QB|RB|WR|TE|K|DST)\s*[-–]\s*([A-Za-z]{2,3})\s*\((\d+)\)\s*$')
_COUNT = re.compile(r'^(QB|RB|WR|TE)\s*(\d+)\s*$')
_RPICK = re.compile(r'^\d{1,2}\.\d{1,2}\s*$')
_INT = re.compile(r'^\d{1,3}\s*$')
_ABBR = re.compile(r'\b([A-Z])\.?\s*([A-Z][a-zA-Z\'\-]+)\b')

def is_ud_board(text):
    t = text or ''
    if re.search(r'On the clock:\s*Pick\s*\d+', t, re.I):   # that's the DK marker
        return False
    return bool(_POSTEAM.search('\n'.join(t.splitlines()))) or ('On the clock' in t) or bool(re.search(r'of\s*18\b', t))

def _build_index(board):
    by_abbr = {}; by_full = {}
    for p in board:
        toks = _norm(p['name']).split()
        if not toks:
            continue
        by_full[_norm(p['name'])] = p
        by_abbr.setdefault((toks[0][:1], toks[-1]), []).append(p)
    return by_abbr, by_full

def _resolve(name, pos, team, by_abbr, by_full):
    nk = _norm(name)
    if nk in by_full:
        return by_full[nk]['name']
    toks = nk.split()
    if len(toks) >= 2:
        cands = by_abbr.get((toks[0][:1], toks[-1]), [])
        if team:
            t = [c for c in cands if c.get('team') == team]
            if len(t) == 1:
                return t[0]['name']
            cands = t or cands
        if pos:
            pp = [c for c in cands if c.get('pos') == pos]
            cands = pp or cands
        if cands:
            return cands[0]['name']
    return None

def _is_username(line, nxt4):
    if not line or _INT.match(line) or _RPICK.match(line) or _POSTEAM.match(line) or _COUNT.match(line):
        return False
    return all(_COUNT.match(x or '') for x in nxt4)

def parse_ud_board(text, me='', board=None, mine=None):
    board = board or []
    by_abbr, by_full = _build_index(board)
    raw = [l.strip() for l in text.splitlines()]
    lines = raw  # keep blanks out
    lines = [l for l in lines if l != '']
    n = len(lines)

    # --- locate team blocks (username + QB#/RB#/WR#/TE#) ---
    blocks = []  # (start_index, username, counts)
    for i in range(n - 4):
        if _is_username(lines[i], lines[i + 1:i + 5]):
            counts = {}
            for j in range(i + 1, i + 5):
                m = _COUNT.match(lines[j]); counts[m.group(1)] = int(m.group(2))
            blocks.append((i, lines[i], counts))
    block_starts = [b[0] for b in blocks]

    def block_of(idx):
        owner = None
        for (si, user, _c) in blocks:
            if si <= idx:
                owner = user
            else:
                break
        return owner

    # --- structured parse: anchor on "POS - TEAM (bye)" ---
    rosters = {}   # username -> [resolved names]
    drafted = []
    for j in range(n):
        m = _POSTEAM.match(lines[j])
        if not m:
            continue
        pos, team, bye = m.group(1), m.group(2).upper(), m.group(3)
        name = lines[j - 2] if j - 2 >= 0 else None
        # guard: name line must not itself be a number / pick / count
        if not name or _INT.match(name) or _RPICK.match(name) or _COUNT.match(name) or _POSTEAM.match(name):
            name = lines[j - 1] if (j - 1 >= 0 and not _INT.match(lines[j - 1])) else None
        if not name:
            continue
        full = _resolve(name, pos, team, by_abbr, by_full)
        owner = block_of(j)
        if full:
            drafted.append(full)
            if owner:
                rosters.setdefault(owner, []).append(full)

    # de-dup each roster preserving order
    for u in rosters:
        seen = set(); rosters[u] = [x for x in rosters[u] if not (x in seen or seen.add(x))]

    # --- current pick / on-the-clock team ---
    otc_user = None; cur_pick = None
    for j, l in enumerate(lines):
        if re.search(r'On the clock', l, re.I):
            otc_user = block_of(j)
            # the next round.pick line is the current pick slot
            for k in range(j, min(j + 3, n)):
                if _RPICK.match(lines[k]):
                    rr, pp = lines[k].split('.')
                    cur_pick = (int(rr) - 1) * max(2, len(blocks)) + int(pp)
                    break
            break
    if cur_pick is None:
        cur_pick = len(drafted) + 1
    teams = len(blocks) or 12
    rnd = (cur_pick - 1) // teams + 1

    # --- fallback: if structured parse found nothing, name-anchor the whole text ---
    if not drafted:
        low = ' ' + re.sub(r'[^a-z0-9 ]+', ' ', '\n'.join(lines).lower().replace("'", "")) + ' '
        seen = set()
        for full, p in by_full.items():
            if len(full) >= 5 and (' ' + full + ' ') in low and full not in seen:
                drafted.append(p['name']); seen.add(full)
        cur_pick = len(drafted) + 1; rnd = (cur_pick - 1) // teams + 1

    # --- whose roster is mine ---
    my_user = None
    if mine:  # explicit override always wins
        my_roster = []
        for x in mine:
            r = _resolve(x, None, None, by_abbr, by_full) or (by_full.get(_norm(x), {}) or {}).get('name')
            if r:
                my_roster.append(r)
    else:
        if me:
            for u in rosters:
                if _norm(u).replace(' ', '') == _norm(me).replace(' ', ''):
                    my_user = u; break
        if not my_user:
            my_user = otc_user
        my_roster = rosters.get(my_user, []) if my_user else []

    counts = {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0}
    posof = {_norm(p['name']): p['pos'] for p in board}
    for nm in my_roster:
        pp = posof.get(_norm(nm))
        if pp in counts:
            counts[pp] += 1
    gone = {_norm(x) for x in drafted}
    available = [p['name'] for p in board if _norm(p['name']) not in gone]
    # snake seat: position within the round, reversed on even rounds (UD "R.P" P is the round position)
    _R = (cur_pick - 1) // teams + 1; _P = (cur_pick - 1) % teams + 1
    seat = (_P if _R % 2 == 1 else (teams - _P + 1)) if cur_pick else None
    return {'pick': cur_pick, 'round': rnd, 'seat': seat, 'my_roster': my_roster,
            'my_user': my_user, 'on_the_clock': otc_user, 'counts': counts,
            'available': available, 'n_drafted': len(drafted), 'n_teams': teams,
            'all_rosters': rosters, 'platform': 'UD'}

if __name__ == '__main__':
    import sys, bbengine as bb
    txt = open(sys.argv[1], encoding='utf-8', errors='replace').read()
    st = parse_ud_board(txt, sys.argv[2] if len(sys.argv) > 2 else '', bb.load_board())
    print('teams', st['n_teams'], '| drafted', st['n_drafted'], '| pick', st['pick'], 'round', st['round'])
    print('on the clock:', st['on_the_clock'], '| my_user:', st['my_user'])
    print('my roster:', st['my_roster'], st['counts'])
    print('all rosters:', {u: len(r) for u, r in st['all_rosters'].items()})
