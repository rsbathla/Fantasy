#!/usr/bin/env python3
"""TWO-SEASON history (2024+2025) + 2026 PROJECTION PRIOR -> blended base ceiling rate.
Run AFTER boom_foundation.py. Augments boom/statmenu.json with:
  g24/b24, g25/b25, g2/b2 (startable games & booms each season + combined),
  base_hist2 (2-yr empirical rate), base_proj (2026 projection-implied per-game boom rate),
  base_blended (the number the model uses) = (b2 + base_proj*K)/(g2 + K)  [proj prior is the
  shrinkage target instead of a flat position average; history dominates as games accrue].
Also writes boom/base2yr.json for the explorer to show the breakdown.

Sources: bestball/pipeline/player_games.parquet (per-week dk + usage, 2024 & 2025),
draft_board_signals.csv (proj_pg, p95 for the 2026 projection prior). Boom threshold per pos
from boom/boomdef.json. 'startable game' = a usage gate (real role), outcome-independent.
"""
import json, os, re, math, csv
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); B = os.path.join(HERE, 'boom')
def fn(n):
    n = str(n).strip().lower(); n = re.sub(r'\s+(jr|sr|ii|iii|iv|v)\.?$', '', n)
    return n.replace('.', '').replace("'", "").replace('-', ' ')
def lastname(n):
    n = fn(n); return n.split()[-1] if n.split() else n
def initial(n):
    n = fn(n); return n[0] if n else ''
def Phi(z): return 0.5 * (1 + math.erf(z / math.sqrt(2)))

SPIKE = json.load(open(f"{B}/boomdef.json"))['SPIKE']
posbase = json.load(open(f"{B}/boomdef.json")).get('posbase', {})
sm = json.load(open(f"{B}/statmenu.json"))
board = {fn(r['name']): r for r in csv.DictReader(open(f"{HERE}/draft_board_signals.csv", encoding='utf-8'))}
g = pd.read_parquet(f"{HERE}/pipeline/player_games.parquet")
g = g[g.week <= 18].copy()  # regular season + reg weeks only (drop playoff inflation noise)

# ---- usage gate: did the player have a startable role that week? (outcome-independent) ----
def derive_pos_row(r):
    if (r['pass_att'] or 0) >= 10: return 'QB'
    if (r['carries'] or 0) >= (r['targets'] or 0) and (r['carries'] or 0) >= 5: return 'RB'
    if (r['targets'] or 0) >= 1: return 'WR'   # WR/TE share gate
    if (r['carries'] or 0) >= 1: return 'RB'
    return None
def startable(r, pos):
    if pos == 'QB': return (r['pass_att'] or 0) >= 15
    if pos == 'RB': return (r['carries'] or 0) + (r['targets'] or 0) >= 8
    if pos == 'WR': return (r['targets'] or 0) >= 4
    if pos == 'TE': return (r['targets'] or 0) >= 3
    return False

# index parquet by (initial,last) -> rows, grouped by pid (pid = a unique person)
def parse_parq(name):
    name = str(name).strip()
    if len(name) >= 2 and name[1] == '.':
        ini = name[0].lower(); rest = name[2:]
    else:
        parts = name.split(); ini = (parts[0][0].lower() if parts else ''); rest = (parts[-1] if parts else name)
    last = re.sub(r'\s+(jr|sr|ii|iii|iv|v)\.?$', '', rest.strip().lower()).replace('.', '').replace("'", "").replace('-', ' ').strip()
    last = last.split()[-1] if last.split() else last
    return ini, last
g['ini'] = g['name'].map(lambda x: parse_parq(x)[0]); g['last'] = g['name'].map(lambda x: parse_parq(x)[1])
g['rpos'] = g.apply(derive_pos_row, axis=1)
from collections import defaultdict
idx = defaultdict(list)
for rec in g.to_dict('records'):
    idx[(rec['ini'], rec['last'])].append(rec)

TMAP = {'LA':'LAR','JAC':'JAX','WSH':'WAS','ARZ':'ARI','GNB':'GB','KAN':'KC','SFO':'SF','TAM':'TB','NWE':'NE','NOR':'NO'}
def tmn(t): t = str(t).strip().upper(); return TMAP.get(t, t)

def base_proj(pos, k):
    """2026 projection-implied per-game boom rate via a lognormal fit to (proj_pg mean, p95 ceiling)."""
    r = board.get(k)
    if not r: return None
    try: m = float(r['proj_pg']); q = float(r['p95'])
    except Exception: return None
    thr = SPIKE.get(pos)
    if not m or m <= 0 or not q or q <= m or not thr: return None
    a = math.log(q) - math.log(m); disc = 1.645**2 - 2 * a
    if disc <= 0:  # p95 too far from mean for a clean fit -> mild fallback
        return max(0.02, min(0.6, (m / thr) * 0.5))
    sig = 1.645 - math.sqrt(disc)
    if sig <= 0.02: sig = 0.02
    mu = math.log(m) - sig * sig / 2
    return max(0.01, min(0.80, 1 - Phi((math.log(thr) - mu) / sig)))

K = 5.0
out = {}
match = 0
for key, v in sm.items():
    pos = v['pos']
    if pos == 'DST':
        # no parquet for DST: blend 2025 history with a unit-strength prior (own pass-rush+coverage)
        d = v.get('def', {}); sk = d.get('sackp') or 50; cv = d.get('covp') or 50
        bp = max(0.03, min(0.55, posbase.get('DST', 0.16) * (0.55 + 0.9 * (sk + cv) / 200.0)))
        g25, b25 = v.get('n_games', 0), v.get('boom_games', 0)
        blended = (b25 + bp * K) / (g25 + K) if (g25 or K) else bp
        out[key] = {'g24': 0, 'b24': 0, 'g25': g25, 'b25': b25, 'g2': g25, 'b2': b25,
                    'base_hist2': round(b25 / g25, 3) if g25 else None, 'base_proj': round(bp, 3),
                    'base_blended': round(blended, 3), 'hist2': g25 >= 4}
        continue
    thr = SPIKE.get(pos); cand = idx.get((initial(v['name']), lastname(v['name'])), [])
    # keep position-consistent rows, group by pid, pick the pid matching team (any season) else most games
    pc = [r for r in cand if r['rpos'] == pos or (pos in ('WR', 'TE') and r['rpos'] == 'WR')]
    bypid = defaultdict(list)
    for r in pc: bypid[r['pid']].append(r)
    chosen = None
    if bypid:
        teamq = tmn(v.get('team', ''))
        tmatch = [pid for pid, rs in bypid.items() if any(tmn(r['team']) == teamq for r in rs)]
        if len(tmatch) == 1: chosen = tmatch[0]
        else: chosen = max(bypid, key=lambda pid: sum(1 for r in bypid[pid] if startable(r, pos)))
    g24 = b24 = g25 = b25 = 0
    if chosen:
        match += 1
        for r in bypid[chosen]:
            if not startable(r, pos): continue
            boom = 1 if (r['dk'] or 0) >= thr else 0
            if r['season'] == 2024: g24 += 1; b24 += boom
            elif r['season'] == 2025: g25 += 1; b25 += boom
    g2 = g24 + g25; b2 = b24 + b25
    bp = base_proj(pos, key)
    if bp is None: bp = posbase.get(pos, 0.15)
    blended = (b2 + bp * K) / (g2 + K)
    out[key] = {'g24': g24, 'b24': b24, 'g25': g25, 'b25': b25, 'g2': g2, 'b2': b2,
                'base_hist2': round(b2 / g2, 3) if g2 else None, 'base_proj': round(bp, 3),
                'base_blended': round(max(0.01, min(0.80, blended)), 3), 'hist2': g2 >= 4}
    v.update({'base_blended': out[key]['base_blended'], 'base_hist2': out[key]['base_hist2'],
              'base_proj': out[key]['base_proj'], 'g2': g2, 'b2': b2, 'g24': g24, 'b24': b24,
              'g25': g25, 'b25': b25, 'hist2': out[key]['hist2']})

json.dump(sm, open(f"{B}/statmenu.json", 'w'), ensure_ascii=False)
json.dump(out, open(f"{B}/base2yr.json", 'w'), ensure_ascii=False)

# ---- validation ----
skill = [k for k, v in sm.items() if v['pos'] != 'DST']
matched2yr = sum(1 for k in skill if out[k]['g2'] >= 1)
g2tot = sum(out[k]['g2'] for k in skill)
print(f"skill players: {len(skill)} | matched to 2024-25 parquet: {matched2yr} | total startable games captured: {g2tot}")
print(f"avg games/matched player: {g2tot/max(1,matched2yr):.1f} (was ~{sum(v.get('n_games',0) for v in sm.values() if v['pos']!='DST')/max(1,len(skill)):.1f} on 2025-only)")
# correlation of base_hist2 vs base_proj (do history and projection agree?)
import statistics as st
pairs = [(out[k]['base_hist2'], out[k]['base_proj']) for k in skill if out[k]['g2'] >= 6 and out[k]['base_proj']]
if len(pairs) > 10:
    xs = [a for a, b in pairs]; ys = [b for a, b in pairs]
    mx, my = st.mean(xs), st.mean(ys)
    cov = sum((a-mx)*(b-my) for a, b in pairs); dx = math.sqrt(sum((a-mx)**2 for a in xs)); dy = math.sqrt(sum((b-my)**2 for b in ys))
    print(f"corr(2yr hist, 2026 proj prior) over {len(pairs)} players w/ >=6 games: {cov/(dx*dy):.3f}")
print("\nbefore -> after (2025-only base_boom  ->  2yr+proj blended):")
for nm in ['Brian Thomas Jr.', 'Jahmyr Gibbs', 'Puka Nacua', 'Josh Allen', 'Trey McBride', 'Ja\'Marr Chase']:
    k = fn(nm); v = sm.get(k)
    if v: print(f"  {nm:20s}: 2025 {v.get('boom_games')}/{v.get('n_games')}  ->  2yr {v['b2']}/{v['g2']} ({v['b24']}/{v['g24']} '24, {v['b25']}/{v['g25']} '25) "
                f"| hist2={v['base_hist2']} proj={v['base_proj']} -> BLENDED {v['base_blended']}")
