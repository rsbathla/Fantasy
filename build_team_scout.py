#!/usr/bin/env python3
"""Per-team SCOUTING dashboard (irrespective of best ball). Fuses our pipeline (offense personnel +
usage + projection, defense ratings/tiers/scheme) with a web layer (2026 coaching, win totals, moves,
outlook) into a self-contained, browseable, sortable HTML for all 32 teams. -> team_scout.html"""
import json, csv, re, os
HERE = os.path.dirname(os.path.abspath(__file__)); DL = os.path.dirname(HERE)
def P(f): return os.path.join(HERE, f)
def R(rel):
    """Resolve a data path robust to repo-beside-Downloads (sandbox) vs repo-inside-Downloads layouts.
    Also falls back to the repo top-level by basename (some inputs moved out of dfs_review/out/)."""
    base = os.path.basename(rel)
    for c in (os.path.join(DL, rel), os.path.join(HERE, rel), os.path.join(HERE, base)):
        if os.path.exists(c): return c
    return os.path.join(DL, rel)
def fn(n):
    n = str(n).strip().lower(); n = re.sub(r'\s+(jr|sr|ii|iii|iv|v)\.?$', '', n)
    return n.replace('.', '').replace("'", "").replace('-', ' ')
def num(x, d=None):
    try: return float(x)
    except Exception: return d
def rows(f):
    p = P(f)
    return list(csv.DictReader(open(p, encoding='utf-8'))) if os.path.exists(p) else []
TEAMS = {'ARI':'Arizona Cardinals','ATL':'Atlanta Falcons','BAL':'Baltimore Ravens','BUF':'Buffalo Bills','CAR':'Carolina Panthers','CHI':'Chicago Bears','CIN':'Cincinnati Bengals','CLE':'Cleveland Browns','DAL':'Dallas Cowboys','DEN':'Denver Broncos','DET':'Detroit Lions','GB':'Green Bay Packers','HOU':'Houston Texans','IND':'Indianapolis Colts','JAX':'Jacksonville Jaguars','KC':'Kansas City Chiefs','LAC':'Los Angeles Chargers','LAR':'Los Angeles Rams','LV':'Las Vegas Raiders','MIA':'Miami Dolphins','MIN':'Minnesota Vikings','NE':'New England Patriots','NO':'New Orleans Saints','NYG':'New York Giants','NYJ':'New York Jets','PHI':'Philadelphia Eagles','PIT':'Pittsburgh Steelers','SEA':'Seattle Seahawks','SF':'San Francisco 49ers','TB':'Tampa Bay Buccaneers','TEN':'Tennessee Titans','WAS':'Washington Commanders'}
TMAP = {'LA':'LAR','JAC':'JAX','WSH':'WAS','ARZ':'ARI','GNB':'GB','KAN':'KC','SFO':'SF','TAM':'TB','NWE':'NE','NOR':'NO'}
def tm(t): t = str(t).strip().upper(); return TMAP.get(t, t)
DIV = {'BUF':'AFC East','MIA':'AFC East','NE':'AFC East','NYJ':'AFC East','BAL':'AFC North','CIN':'AFC North','CLE':'AFC North','PIT':'AFC North','HOU':'AFC South','IND':'AFC South','JAX':'AFC South','TEN':'AFC South','DEN':'AFC West','KC':'AFC West','LV':'AFC West','LAC':'AFC West','DAL':'NFC East','NYG':'NFC East','PHI':'NFC East','WAS':'NFC East','CHI':'NFC North','DET':'NFC North','GB':'NFC North','MIN':'NFC North','ATL':'NFC South','CAR':'NFC South','NO':'NFC South','TB':'NFC South','ARI':'NFC West','LAR':'NFC West','SF':'NFC West','SEA':'NFC West'}

WEB = {t['team']: t for t in json.load(open(P('web_teams.json'), encoding='utf-8'))}
L2 = {fn(r['name']): r for r in rows('pipeline/layer2_player_params.csv')} if os.path.exists(P('pipeline/layer2_player_params.csv')) else {fn(r['name']): r for r in rows('../pipeline/layer2_player_params.csv')}
FUS = {fn(r['name']): r for r in rows('fusion_table.csv')}
QS = {fn(r['name']): r for r in rows('qual_summary.csv')}
TN = {tm(r['team']): r.get('team_note', '') for r in rows('team_notes.csv') if r.get('team_note')}
DM = json.load(open(R("dfs_review/out/defense_2026_matchup.json")))
DEFP = json.load(open(R("dfs_review/out/defense.json")))
COV = {tm(r['team']): r for r in rows('defense_coverage.csv')}
BM = json.load(open(P('boom/boom_marks.json'), encoding='utf-8')) if os.path.exists(P('boom/boom_marks.json')) else {}  # boom ceiling marks
import glob as _glob
ADPTEAM = {}
_dk = sorted(_glob.glob(f"{DL}/DkPreDraftRankings*.csv")) or sorted(_glob.glob(P("DkPreDraftRankings*.csv")))
if _dk:
    for _r in csv.DictReader(open(_dk[-1], encoding='utf-8')):
        _nm = _r.get('Name'); _t = (_r.get('Team') or '').strip()
        if _nm and _t: ADPTEAM[fn(_nm)] = _t

# --- defense percentiles (higher Points Saved = tougher unit) ---
import bisect
covs = sorted(v['cov'] for v in DM.values()); runs = sorted(v['run'] for v in DM.values())
def pctl(sv, x): return round(100 * bisect.bisect_left(sv, x) / max(1, len(sv) - 1))
mr = sorted(num(r['def_man_rate']) for r in COV.values()); sk = sorted(num(r['def_sack_rate']) for r in COV.values())

# --- offense: collect players per team from the board ---
sp = rows('draft_board_signals.csv')
teamoff = {t: {'QB': [], 'RB': [], 'WR': [], 'TE': []} for t in TEAMS}
proj_all = []
for r in sp:
    nm = r['name']; k = fn(nm); pos = (r.get('pos') or '').upper()
    t0 = (ADPTEAM.get(k) or r.get('team') or '').strip(); t = tm(t0)
    if t not in teamoff or pos not in teamoff[t]:
        continue
    proj = num(r.get('proj_pg')); p95 = num(r.get('p95')); padp = num(r.get('adp'))
    l2 = L2.get(k, {}); fr = FUS.get(k, {}); q = QS.get(k, {})
    share = None
    if pos == 'RB' and l2.get('carry_share'): share = round(num(l2['carry_share']) * 100)
    elif pos in ('WR', 'TE') and l2.get('tgt_share'): share = round(num(l2['tgt_share']) * 100)
    note = str(q.get('summary', '') or '')[:110]
    teamoff[t][pos].append({'n': nm, 'adp': round(padp, 1) if padp else None, 'proj': round(proj, 1) if proj else None,
        'ceil': round(p95) if p95 else None, 'role': str(l2.get('role', '') or ''), 'share': share, 'note': note, 'boom': ({'badge': BM[k]['badge'], 'tier': BM[k]['tier']} if k in BM else None)})
    if proj: proj_all.append((t, pos, proj))

# team offense strength = sum of best starters' proj (QB1 + RB1-2 + WR1-3 + TE1)
def off_strength(t):
    o = teamoff[t]; vals = []
    for pos in ('QB', 'RB', 'WR', 'TE'):
        for p in o[pos]:
            if p.get('adp'): vals.append(max(0.0, 240.0 - p['adp']))   # ADP-value (current) of skill talent
    vals.sort(reverse=True)
    return sum(vals[:8])
offs = sorted(off_strength(t) for t in TEAMS)

DATA = []
for t in TEAMS:
    o = teamoff[t]
    for pos in o: o[pos].sort(key=lambda p: (p['adp'] if p.get('adp') else 9999))
    dm = DM.get(t, {}); covp = pctl(covs, dm.get('cov', 0)) if dm else None; runp = pctl(runs, dm.get('run', 0)) if dm else None
    sc = COV.get(t, {}); manp = pctl(mr, num(sc.get('def_man_rate'))) if sc else None; sackp = pctl(sk, num(sc.get('def_sack_rate'))) if sc else None
    tiers = {p: (DEFP.get(t, {}).get(p, {}) or {}).get('tier', '') for p in ('QB', 'RB', 'WR', 'TE')}
    w = WEB.get(t, {})
    note = re.sub(r'\.\.\.\s*wait.*$', '.', str(TN.get(t, '') or ''))  # clean any stray artifact
    defout = re.sub(r'\.\.\.\s*wait.*$', '.', str(w.get('defense_outlook', '') or ''))
    off_rating = round(100 * bisect.bisect_left(offs, off_strength(t)) / 31)
    def_rating = round((covp + runp) / 2) if (covp is not None and runp is not None) else None
    DATA.append({'t': t, 'nm': TEAMS[t], 'div': DIV.get(t, ''),
        'hc': w.get('hc', ''), 'oc': w.get('oc', ''), 'dc': w.get('dc', ''), 'wt': w.get('win_total_2026'),
        'offR': off_rating, 'defR': def_rating,
        'off': o, 'covp': covp, 'runp': runp, 'manp': manp, 'sackp': sackp, 'tiers': tiers,
        'adds': w.get('key_additions', []) or [], 'loss': w.get('key_losses', []) or [],
        'offout': str(w.get('offense_outlook', '') or ''), 'defout': defout, 'note': note})

cov = {'teams': len(DATA), 'web': sum(1 for d in DATA if d['hc']), 'def': sum(1 for d in DATA if d['defR'] is not None)}
print('coverage:', json.dumps(cov))
html = open(P('_team_scout_template.html'), encoding='utf-8').read()
html = html.replace('__DATA__', json.dumps(DATA, ensure_ascii=False))
import ctx_panel; html = ctx_panel.inject(html)   # 4-layer NFL Pro EPA drilldown (click the EPA chip on a player row)
# verify-write
for attempt in range(3):
    with open(P('team_scout.html'), 'w', encoding='utf-8') as fh:
        fh.write(html); fh.flush(); os.fsync(fh.fileno())
    with open(P('team_scout.html'), encoding='utf-8') as fh:
        back = fh.read()
    if len(back) == len(html) and back.rstrip().endswith('</html>'):
        print('wrote team_scout.html', len(html), 'bytes (verified)'); break
else:
    print('WARN: write not verified')
