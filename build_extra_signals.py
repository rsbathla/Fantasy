#!/usr/bin/env python3
"""Adds RED-ZONE (player), PACE + ENVIRONMENT/SCRIPT (team) signals to the foundation.
- rz (WR/TE): 2-yr inside-20 & end-zone target share + EZ TDs from FP receiving exports (2024 agg + 2025 per-game).
- team_env.json per team: pace_pctl (own offense plays/game, 2yr from game logs), env_idx (scoring environment =
  off_q blended with landscape season-avg implied total, percentile), win_total (for per-week script).
Coverage-shell is handled in-flag via def_man_rate (single-high proxy) — no new data file.
"""
import csv, json, os, re, bisect
from collections import defaultdict
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); DL = os.path.dirname(HERE); B = os.path.join(HERE, 'boom')
from boomutil import fn, team as tm, num   # was: local fn/TMAP/tm/num (audit B3 dedup)
FPADV = os.path.join(HERE, 'NFL-master', 'FP_ADVANCED')  # in-repo FP advanced exports (both years, aggregate)
def dr(p): return list(csv.DictReader(open(os.path.join(FPADV, p), encoding='utf-8-sig')))

# ---------- RED ZONE (WR/TE), 2-yr ----------
rz_tot = defaultdict(lambda: {'i20':0.0,'ez':0.0,'eztd':0.0,'tgt':0.0,'g':0})
for _f in ("receiving_2024.csv", "receiving_2025.csv"):   # both season aggregates now (was 2024 agg + 2025 per-game)
    for r in dr(_f):
        k=fn(r['Name']); rz_tot[k]['i20']+=num(r.get('i20 TGT')) or 0; rz_tot[k]['ez']+=num(r.get('EZTGT')) or 0
        rz_tot[k]['eztd']+=num(r.get('EZTD')) or 0; rz_tot[k]['tgt']+=num(r.get('TGT')) or 0; rz_tot[k]['g']+=num(r.get('G')) or 0
RZ={}
for k,t in rz_tot.items():
    if t['tgt']>=10:
        RZ[k]={'rz_tgt_share':round(100*t['i20']/t['tgt']),'ez_tgt_share':round(100*t['ez']/t['tgt']),
               'ez_td':round(t['eztd']),'ez_td_pg':round(t['eztd']/max(1,t['g']),2),'g':round(t['g'])}

# ---------- PACE (team offense plays/game, 2-yr) ----------
g=pd.read_parquet(f"{HERE}/pipeline/player_games.parquet"); g=g[g.week<=18].copy()
g['plays']=g.pass_att.fillna(0)+g.carries.fillna(0)
tp=g.groupby(['season','team','week']).plays.sum().reset_index()
pace=tp.groupby('team').plays.mean()  # 2-yr avg plays/game
paces=sorted(pace.values)
def pctl(sv,x): return round(100*bisect.bisect_left(sv,x)/max(1,len(sv)-1))
PACE={tm(t):{'plays_pg':round(v,1),'pace_pctl':pctl(paces,v)} for t,v in pace.items()}

# ---------- ENVIRONMENT (scoring) + win totals ----------
oo=json.load(open(f"{B}/opp_offense.json"))           # off_q per team (2026 board)
ls=json.load(open(f"{DL}/dfs_review/out/landscape.json"))
imp=defaultdict(list)
for wk,blk in ls.items():
    if not isinstance(blk,dict): continue
    for t in blk.get('teams',[]):
        if t.get('implied') is not None: imp[tm(t['team'])].append(t['implied'])
impavg={t:sum(v)/len(v) for t,v in imp.items() if v}
imps=sorted(impavg.values())
web={tm(t['team']):t for t in json.load(open(f"{B if os.path.exists(B+'/web_teams.json') else HERE}/web_teams.json"))} if os.path.exists(f"{HERE}/web_teams.json") else {}
wt={tm(t['team']):num(t.get('win_total_2026')) for t in json.load(open(f"{HERE}/web_teams.json"))}

TEAM_ENV={}
for t in PACE:
    offq=oo.get(t,{}).get('off_q',50)
    limp=pctl(imps,impavg[t]) if t in impavg else None
    env=round((offq + (limp if limp is not None else offq))/2)
    TEAM_ENV[t]={'pace_pctl':PACE[t]['pace_pctl'],'plays_pg':PACE[t]['plays_pg'],
                 'env_idx':env,'off_q':offq,'win_total':wt.get(t)}
json.dump(TEAM_ENV, open(f"{B}/team_env.json",'w'), ensure_ascii=False)

# ---------- augment statmenu ----------
sm=json.load(open(f"{B}/statmenu.json")); hit_rz=0
for k,v in sm.items():
    if k in RZ and v['pos'] in ('WR','TE'): v['rz']=RZ[k]; hit_rz+=1
    te=TEAM_ENV.get(v.get('team'))
    if te: v['team_env']=te
json.dump(sm, open(f"{B}/statmenu.json",'w'), ensure_ascii=False)
json.dump(RZ, open(f"{B}/redzone.json",'w'), ensure_ascii=False)

print(f"red-zone WR/TE: {len(RZ)} players ({hit_rz} into statmenu) | team_env: {len(TEAM_ENV)} teams")
print("PACE fastest:", sorted(TEAM_ENV.items(), key=lambda x:-x[1]['pace_pctl'])[:4][0:4] and [(t,d['plays_pg']) for t,d in sorted(TEAM_ENV.items(),key=lambda x:-x[1]['pace_pctl'])[:4]])
print("ENV best:", [(t,d['env_idx']) for t,d in sorted(TEAM_ENV.items(),key=lambda x:-x[1]['env_idx'])[:5]])
for nm in ['Ja\'Marr Chase','Trey McBride','Puka Nacua']:
    r=RZ.get(fn(nm)); 
    if r: print(f"  {nm}: rz_tgt_share={r['rz_tgt_share']}% ez_tgt_share={r['ez_tgt_share']}% ez_td={r['ez_td']} over {r['g']}g")
