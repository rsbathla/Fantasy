#!/usr/bin/env python3
"""TWO-SEASON (2024+2025) ADVANCED/EFFICIENCY profile per player, grounded in player_games.parquet.
Run AFTER boom_base2yr.py. Derives the advanced metrics the box-score data supports across BOTH
seasons (so flags/aDOT/share aren't single-season noise):
  WR/TE: games, aDOT, air-yards share, target share, catch rate, YPT, yards/touch, rec/g, recyd/g, TD/g
  RB   : games, carry share, target share, YPC, YPT, yards/touch, rush/g, rushyd/g, rec/g, TD/g
  QB   : games, pass att/g, YPA, passTD/g, INT/g, rush/g, rushyd/g, rushTD/g
Shares use per-week team totals (handles mid-season team changes). Writes boom/adv2.json and
augments statmenu[key]['adv2']. (Charting metrics — separation/YPRR/SIS coverage — remain
single-season; the repo has no 2024 charting source.)
"""
import json, os, re
import pandas as pd
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__)); B = os.path.join(HERE, 'boom')
def fn(n):
    n = str(n).strip().lower(); n = re.sub(r'\s+(jr|sr|ii|iii|iv|v)\.?$', '', n)
    return n.replace('.', '').replace("'", "").replace('-', ' ')
def last_full(n):
    f = fn(n); p = f.split(); return (p[0][0] if p else ''), (p[-1] if p else f)
def parse_parq(name):
    name = str(name).strip()
    if len(name) >= 2 and name[1] == '.': ini = name[0].lower(); rest = name[2:]
    else:
        parts = name.split(); ini = (parts[0][0].lower() if parts else ''); rest = (parts[-1] if parts else name)
    last = re.sub(r'\s+(jr|sr|ii|iii|iv|v)\.?$', '', rest.strip().lower()).replace('.', '').replace("'", "").replace('-', ' ').strip()
    return ini, (last.split()[-1] if last.split() else last)
TMAP = {'LA':'LAR','JAC':'JAX','WSH':'WAS','ARZ':'ARI','GNB':'GB','KAN':'KC','SFO':'SF','TAM':'TB','NWE':'NE','NOR':'NO'}
def tmn(t): t = str(t).strip().upper(); return TMAP.get(t, t)
def f1(x): 
    try: return round(float(x), 1)
    except Exception: return None
def f2(x):
    try: return round(float(x), 2)
    except Exception: return None

sm = json.load(open(f"{B}/statmenu.json"))
g = pd.read_parquet(f"{HERE}/pipeline/player_games.parquet"); g = g[g.week <= 18].copy()
def drow(r):
    if (r['pass_att'] or 0) >= 10: return 'QB'
    if (r['carries'] or 0) >= (r['targets'] or 0) and (r['carries'] or 0) >= 5: return 'RB'
    if (r['targets'] or 0) >= 1: return 'WR'
    if (r['carries'] or 0) >= 1: return 'RB'
    return None
def startable(r, pos):
    if pos == 'QB': return (r['pass_att'] or 0) >= 15
    if pos == 'RB': return (r['carries'] or 0) + (r['targets'] or 0) >= 8
    if pos == 'WR': return (r['targets'] or 0) >= 4
    if pos == 'TE': return (r['targets'] or 0) >= 3
    return False
g['ini'] = g['name'].map(lambda x: parse_parq(x)[0]); g['last'] = g['name'].map(lambda x: parse_parq(x)[1]); g['rpos'] = g.apply(drow, axis=1)
# per-week team totals for share denominators
tw = defaultdict(lambda: defaultdict(float))
for r in g.to_dict('records'):
    k = (tmn(r['team']), r['season'], r['week'])
    tw[k]['tgt'] += (r['targets'] or 0); tw[k]['car'] += (r['carries'] or 0); tw[k]['ay'] += (r['air_yds'] or 0)
idx = defaultdict(list)
for r in g.to_dict('records'): idx[(r['ini'], r['last'])].append(r)

adv = {}
for key, v in sm.items():
    pos = v['pos']
    if pos == 'DST': continue
    cand = idx.get(last_full(v['name']), [])
    pc = [r for r in cand if r['rpos'] == pos or (pos in ('WR', 'TE') and r['rpos'] == 'WR')]
    bypid = defaultdict(list)
    for r in pc: bypid[r['pid']].append(r)
    if not bypid: continue
    teamq = tmn(v.get('team', '')); tmatch = [pid for pid, rs in bypid.items() if any(tmn(r['team']) == teamq for r in rs)]
    chosen = tmatch[0] if len(tmatch) == 1 else max(bypid, key=lambda pid: sum(1 for r in bypid[pid] if startable(r, pos)))
    rs = [r for r in bypid[chosen] if startable(r, pos)]
    if not rs: continue
    n = len(rs)
    S = lambda c: sum((r[c] or 0) for r in rs)
    tgt, rec, recyd, rectd = S('targets'), S('rec'), S('rec_yds'), S('rec_td')
    ay, car, rushyd, rushtd = S('air_yds'), S('carries'), S('rush_yds'), S('rush_td')
    patt, pyd, ptd, ints = S('pass_att'), S('pass_yds'), S('pass_td'), S('ints')
    tsh = [r['targets']/tw[(tmn(r['team']),r['season'],r['week'])]['tgt'] for r in rs if tw[(tmn(r['team']),r['season'],r['week'])]['tgt']]
    csh = [r['carries']/tw[(tmn(r['team']),r['season'],r['week'])]['car'] for r in rs if tw[(tmn(r['team']),r['season'],r['week'])]['car']]
    aysh = [r['air_yds']/tw[(tmn(r['team']),r['season'],r['week'])]['ay'] for r in rs if tw[(tmn(r['team']),r['season'],r['week'])]['ay']]
    a = {'g': n}
    if pos == 'QB':
        a.update({'patt_pg': f1(patt/n), 'ypa': f2(pyd/patt) if patt else None, 'ptd_pg': f2(ptd/n),
                  'int_pg': f2(ints/n), 'rush_pg': f1(car/n), 'rushyd_pg': f1(rushyd/n), 'rushtd_g': f2(rushtd/n)})
    else:
        a.update({'aDOT': f1(ay/tgt) if tgt else None, 'ay_share': round(100*sum(aysh)/len(aysh)) if aysh else None,
                  'tgt_share': round(100*sum(tsh)/len(tsh)) if tsh else None,
                  'catch': round(100*rec/tgt) if tgt else None, 'ypt': f1(recyd/tgt) if tgt else None,
                  'rec_pg': f1(rec/n), 'recyd_pg': f1(recyd/n), 'td_pg': f2((rectd+rushtd)/n),
                  'yptouch': f1((recyd+rushyd)/(rec+car)) if (rec+car) else None})
        if pos == 'RB':
            a.update({'carry_share': round(100*sum(csh)/len(csh)) if csh else None, 'ypc': f1(rushyd/car) if car else None,
                      'rush_pg': f1(car/n), 'rushyd_pg': f1(rushyd/n)})
    adv[key] = a; v['adv2'] = a

json.dump(adv, open(f"{B}/adv2.json", 'w'), ensure_ascii=False)
json.dump(sm, open(f"{B}/statmenu.json", 'w'), ensure_ascii=False)
sk = [k for k, v in sm.items() if v['pos'] != 'DST']
print(f"2-yr advanced profiles built: {len(adv)} of {len(sk)} skill players")
for nm in ['Brian Thomas Jr.', 'Puka Nacua', 'Jahmyr Gibbs', 'Josh Allen', 'Trey McBride']:
    a = adv.get(fn(nm))
    if a: print(f"  {nm:20s} ({a['g']}g): " + ", ".join(f"{k} {a[k]}" for k in a if k != 'g' and a[k] is not None))
