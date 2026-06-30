#!/usr/bin/env python3
"""PLAYER EXPLORER (flag-based boom model): click a player -> (1) ceiling profile = base ceiling
rate + plain-language boom thesis + HIS player-specific skill flags, (2) full-season matchup board
(all 18 weeks, which flags light up each week + ceiling prob), (3) every ingested tweet (FULL text),
plus usage/role + model card + film. Now includes 32 DST units. Self-contained HTML."""
import json, csv, re, os, glob
HERE = os.path.dirname(os.path.abspath(__file__)); DL = os.path.dirname(HERE)
def P(f): return os.path.join(HERE, f)
def fn(n):
    n = str(n).strip().lower(); n = re.sub(r'\s+(jr|sr|ii|iii|iv|v)\.?$', '', n)
    return n.replace('.', '').replace("'", "").replace('-', ' ')
def num(x, d=None):
    try: return round(float(x), 2)
    except Exception: return d
def rows(f):
    p = P(f); return list(csv.DictReader(open(p, encoding='utf-8'))) if os.path.exists(p) else []
def load(f):
    p = P(f); return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}
TMAP = {'LA':'LAR','JAC':'JAX','WSH':'WAS','ARZ':'ARI','GNB':'GB','KAN':'KC','SFO':'SF','TAM':'TB','NWE':'NE','NOR':'NO'}
def tm(t): t = str(t).strip().upper(); return TMAP.get(t, t)

FLAGS = {}
for pos in ['QB', 'RB', 'WR', 'TE', 'DST']:
    FLAGS.update(load(f'boom/flags_{pos}.json'))
TW = load('player_tweets.json')
BASE2 = load('boom/base2yr.json')
ADV2 = load('boom/adv2.json')
CHART2 = load('boom/chart2yr.json')
RZ = load('boom/redzone.json')
TENV = load('boom/team_env.json')
CSPEC = load('boom/cover_spec.json')
FUS = {fn(r['name']): r for r in rows('fusion_table.csv')}
L2 = {fn(r['name']): r for r in (rows('pipeline/layer2_player_params.csv') or rows('../pipeline/layer2_player_params.csv'))}
VID = {fn(r['name']): r.get('video_note', '') for r in rows('video_notes.csv') if r.get('video_note')}
CONV = {fn(r['name']): r for r in rows('qual_signal.csv')}
QS = {fn(r['name']): r for r in rows('qual_summary.csv')}
DKT = {}
_dk = sorted(glob.glob(f"{DL}/DkPreDraftRankings*.csv"))
if _dk:
    for r in csv.DictReader(open(_dk[-1], encoding='utf-8')):
        if r.get('Name') and r.get('Team'): DKT[fn(r['Name'])] = r['Team'].strip()

MODELKEYS = [('value_pctl','Value'),('ceiling_pctl','Ceiling'),('spike_pctl','Spike'),('boom_pctl','Boom'),
    ('run_eff_pctl','Run-eff'),('rec_eff_pctl','Rec-eff'),('route_eff_pctl','Route'),('separation_pctl','Separation'),
    ('yac_pctl','YAC'),('explosive_pctl','Explosive'),('oline_pctl','O-line'),('matchup_pctl','Matchup')]
USEKEYS = [('carry_pg','car/g'),('carry_share','car sh'),('ypc','ypc'),('tgt_share','tgt sh'),('catch_rate','catch'),('ypt','ypt'),('dk_pg','pts/g')]

def tweets(k):
    tw = TW.get(k)
    return ((tw or {}).get('n', 0),
            [{'d': x['date'], 'h': x['handle'], 't': str(x['text']), 'l': x['likes']} for x in (tw or {}).get('tweets', [])])

def usage_model(k):
    f = FUS.get(k); u = L2.get(k); model = None; usage = None
    if f:
        model = {lbl: num(f.get(kk)) for kk, lbl in MODELKEYS if num(f.get(kk)) is not None}
        model['_c'] = num(f.get('consensus')); model['_n'] = num(f.get('n_votes'))
    if u:
        usage = {lbl: (round(num(u.get(kk)) * 100) if 'share' in kk or kk == 'catch_rate' else num(u.get(kk)))
                 for kk, lbl in USEKEYS if num(u.get(kk)) is not None}
        usage['role'] = str(u.get('role', '') or '')
    return usage, model

def mkobj(nm, pos, team, adp, fl, k):
    usage, model = usage_model(k); ntw, tw = tweets(k); q = QS.get(k); cv = CONV.get(k)
    return {'n': nm, 'pos': pos, 'team': team, 'adp': num(adp),
        'base': (fl.get('base') if fl else None), 'hist': (fl.get('hist') if fl else None),
        'g2': BASE2.get(k,{}).get('g2'), 'b2': BASE2.get(k,{}).get('b2'),
        'g24': BASE2.get(k,{}).get('g24'), 'b24': BASE2.get(k,{}).get('b24'),
        'g25': BASE2.get(k,{}).get('g25'), 'b25': BASE2.get(k,{}).get('b25'),
        'bh2': BASE2.get(k,{}).get('base_hist2'), 'bproj': BASE2.get(k,{}).get('base_proj'), 'hist2': BASE2.get(k,{}).get('hist2'),
        'adv2': ADV2.get(k),
        'c2': (CHART2.get(k,{}) or {}).get('blend'), 'c2g': [(CHART2.get(k,{}) or {}).get('g24'),(CHART2.get(k,{}) or {}).get('g25')],
        'rz': RZ.get(k), 'tenv': TENV.get(team), 'cspec': CSPEC.get(k),
        'ng': (fl.get('n_games') if fl else None), 'bg': (fl.get('boom_games') if fl else None),
        'sflags': (fl.get('skill_flags', []) if fl else []), 'line': (fl.get('line') if fl else None),
        'fw': (fl.get('weeks', []) if fl else []), 'emp': (fl.get('empirical') if fl else None),
        'usage': usage, 'model': model, 'film': (str(VID.get(k, ''))[:420] or None),
        'conv': (num(cv.get('qual_score')) if cv else None),
        'outlook': (str((q or {}).get('summary', '') or '') or None),
        'ntw': ntw, 'tw': tw}

players = []; seen = set()
for r in rows('draft_board_signals.csv'):
    nm = r['name']; k = fn(nm); pos = (r.get('pos') or '').upper()
    if pos not in ('QB', 'RB', 'WR', 'TE'): continue
    team = tm(DKT.get(k) or r.get('team') or '')
    players.append(mkobj(nm, pos, team, num(r.get('adp')), FLAGS.get(k), k)); seen.add(k)
dst = []
for k, fl in FLAGS.items():
    if fl.get('pos') != 'DST' or k in seen: continue
    dst.append(mkobj(fl['name'], 'DST', fl.get('team', ''), None, fl, k))
dst.sort(key=lambda p: -(p['base'] or 0))
players.sort(key=lambda p: (p['adp'] if p['adp'] else 9999))
players += dst

cov = {'players': len(players), 'withflags': sum(1 for p in players if p['sflags']),
       'tweets': sum(1 for p in players if p['tw']), 'dst': len(dst)}
print('coverage:', json.dumps(cov))
html = open(P('_player_explorer_template.html'), encoding='utf-8').read().replace('__DATA__', json.dumps(players, ensure_ascii=False, separators=(',', ':')))
import ctx_panel; html = ctx_panel.inject(html)   # 4-layer NFL Pro EPA drilldown (click the EPA chip in the detail header)
for attempt in range(3):
    with open(P('player_explorer.html'), 'w', encoding='utf-8') as fh:
        fh.write(html); fh.flush(); os.fsync(fh.fileno())
    with open(P('player_explorer.html'), encoding='utf-8') as fh: back = fh.read()
    if len(back) == len(html) and back.rstrip().endswith('</html>'):
        print('wrote player_explorer.html', round(len(html) / 1024), 'KB (verified)'); break
else:
    print('WARN: write not verified')
