#!/usr/bin/env python3
"""Build all-position college Value profiles for the rookie model (2024 + 2025).

Reads the staged SIS CFB Value CSVs (receiving/rushing/passing, both seasons), assigns a
primary position (QB<-passing, WR/TE<-receiving Pos, RB<-rushing), computes a within-position
college-ceiling percentile from Points Earned + EPA + Boom%, applies the 2026-board draft-
eligibility filter (board ADP = draft-capital proxy), and writes boom/rookie_college_profile.json
(all positions; supersedes the WR/TE-only build). Pure CSV/JSON — no parquet/pyarrow needed.
"""
import core, csv, json, os, collections

def CFB(f): return core.P(os.path.join('sis_value', 'cfb', f))

def num(x):
    try: return float(str(x).replace('%', '').replace(',', '').replace('"', '').strip())
    except (TypeError, ValueError): return None

def load_value(fname):
    p = CFB(fname)
    return list(csv.DictReader(open(p, encoding='utf-8'))) if os.path.exists(p) else []

def pctl(vals):
    """Within-list mid-rank percentile (0-100); None abstains and stays None."""
    present = [v for v in vals if v is not None]
    out = [None] * len(vals); n = len(present)
    if n == 0: return out
    for i, v in enumerate(vals):
        if v is None: continue
        less = sum(1 for x in present if x < v); eq = sum(1 for x in present if x == v)
        out[i] = round((less + 0.5 * eq) / n * 100, 1)
    return out

def build_season(season):
    """Return {fnkey: {name, team(college), pos, pe, epa, boom, *_pctl, ceiling_pctl}} for one season."""
    rec = load_value(f'cfb_receiving_value_{season}.csv')
    rush = load_value(f'cfb_rushing_value_{season}.csv')
    pas = load_value(f'cfb_passing_value_{season}.csv')
    P = {}
    def row(r, pos):
        return {'name': r['Player'].strip(), 'team': (r.get('Team') or '').strip(), 'pos': pos,
                'pe': num(r.get('Points Earned')), 'epa': num(r.get('EPA')), 'boom': num(r.get('Boom%'))}
    for r in pas:                                   # QB <- passing
        if r.get('Player'): P[core.fn(r['Player'])] = row(r, 'QB')
    for r in rec:                                   # WR/TE <- receiving (skip RBs/QBs)
        if not r.get('Player'): continue
        k = core.fn(r['Player'])
        if k in P and P[k]['pos'] == 'QB': continue
        pos = (r.get('Pos') or 'WR').strip().upper()
        if pos == 'RB': continue                    # pass-catching RB -> handled as RB below
        if pos not in ('WR', 'TE'): pos = 'WR'
        P[k] = row(r, pos)
    for r in rush:                                  # RB <- rushing (only if not already QB/WR/TE)
        if not r.get('Player'): continue
        k = core.fn(r['Player'])
        if k in P: continue
        P[k] = row(r, 'RB')
    bypos = collections.defaultdict(list)
    for k, v in P.items(): bypos[v['pos']].append(k)
    for pos, ks in bypos.items():
        for m in ('pe', 'epa', 'boom'):
            for k, p in zip(ks, pctl([P[k][m] for k in ks])): P[k][m + '_pctl'] = p
        for k in ks:
            comps = [P[k][m + '_pctl'] for m in ('pe', 'epa', 'boom') if P[k].get(m + '_pctl') is not None]
            P[k]['ceiling_pctl'] = round(sum(comps) / len(comps), 1) if comps else None
    return P

def load_board():
    """2026 best-ball board -> {fnkey: {adp, pos, team}} (draft-eligibility + capital proxy)."""
    b = {}
    p = core.P(os.path.join('analysis', 'merged_rankings_2026.csv'))
    if os.path.exists(p):
        for r in csv.DictReader(open(p, encoding='utf-8')):
            if r.get('Name'): b[core.fn(r['Name'])] = {'adp': num(r.get('ADP')), 'pos': r.get('Position'), 'team': r.get('Team')}
    return b

def main():
    p24, p25 = build_season('2024'), build_season('2025')
    board = load_board()
    players = {}
    for k in set(p24) | set(p25):
        a, b = p24.get(k), p25.get(k)
        base = b or a
        bd = board.get(k)
        players[k] = {
            'name': base['name'], 'college': base.get('team'), 'pos': base['pos'],
            'ceiling_pctl_2025': (b or {}).get('ceiling_pctl'),
            'ceiling_pctl_2024': (a or {}).get('ceiling_pctl'),
            's2025': {m: b[m] for m in ('pe', 'epa', 'boom', 'ceiling_pctl')} if b else None,
            's2024': {m: a[m] for m in ('pe', 'epa', 'boom', 'ceiling_pctl')} if a else None,
            'draft_eligible_2026': bd is not None,
            'board_adp': (bd or {}).get('adp'),
        }
    elig = sum(1 for v in players.values() if v['draft_eligible_2026'])
    out = {'source': 'SIS CFB Value (rec/rush/pass) 2024+2025; eligibility=merged_rankings_2026',
           'n_players': len(players), 'n_draft_eligible_2026': elig,
           'pos_counts': dict(collections.Counter(v['pos'] for v in players.values())),
           'players': players}
    core.safe_json_dump(out, core.P(os.path.join('boom', 'rookie_college_profile.json')))
    print(f"rookie_college_profile.json: {len(players)} players "
          f"({out['pos_counts']}), {elig} draft-eligible for 2026")
    return players

if __name__ == '__main__':
    main()
