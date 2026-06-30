#!/usr/bin/env python3
"""Funnel overlay (WR) — applies the opponent-adjusted DVOA funnel as the per-week WR matchup
nudge, routed by alignment (slot WR vs boundary). Validated: base x funnel WR AUC 0.784->~0.79
out of the box; gate showed funnel AUC 0.617 vs raw opp-pctl 0.540. Conservative shrunk strength.
Post-processor: runs AFTER build_flags_WR (reads its fresh p), so it's not double-applied."""
import json, os
HERE=os.path.dirname(os.path.abspath(__file__)); B=os.path.join(HERE,'boom')
from boomutil import fn
from boom_lib import label, cap
prof=json.load(open(f'{B}/defensive_profile.json'))
align={k:v.get('align') for k,v in json.load(open(f'{B}/opportunity.json')).items()}
ALIAS={'BLT':'BAL','CLV':'CLE','HST':'HOU','ARZ':'ARI','LA':'LAR','JAC':'JAX','LVR':'LV','WSH':'WAS','SD':'LAC','OAK':'LV','STL':'LAR'}
LAM=0.6; SC=28.0; LO=0.90; HI=1.12
def fval(opp,al):
    pr=prof.get(ALIAS.get(opp,opp))
    if not pr: return None
    d=pr['dvoa_fpaa']
    return d['slot'] if al=='Slot' else ((d['wr1']+d['wr2'])/2 if al=='Wide' else d['wr'])
d=json.load(open(f'{B}/flags_WR.json')); nudged=0; pl=0
for k,p in d.items():
    al=align.get(k,'Wide'); base=(p.get('base') or 0)/100.0; touched=False
    for w in p.get('weeks',[]):
        if w.get('opp') is None or w.get('p') is None: continue
        v=fval(w['opp'],al)
        if v is None: continue
        mult=cap(1+LAM*(v/SC),LO,HI)
        if abs(mult-1)<0.03: continue
        newp=cap((w['p']/100.0)*mult,0.01,0.80)
        r=(newp/base) if base else 1.0
        w['p']=round(newp*100); w['lab']=label(newp,r); touched=True; nudged+=1
        tag=f"funnel: {w['opp']} {'soft' if mult>1 else 'tough'} vs {al} WR ({'+' if v>=0 else ''}{round(v,1)} DVOA-adj) ({'+' if mult>1 else ''}{round((mult-1)*100)}%)"
        w.setdefault('flags',[]).insert(0,tag)
    if touched: pl+=1
json.dump(d,open(f'{B}/flags_WR.json','w'),ensure_ascii=False)
print(f"funnel overlay applied: {nudged} week-nudges across {pl} WRs (LAM={LAM}, mult [{LO},{HI}])")
# spot check
v=d.get('jamarr chase')
if v:
    ex=[w for w in v['weeks'] if any('funnel' in str(f) for f in w.get('flags',[]))][:2]
    for w in ex: print(f"  Chase wk{w['wk']} vs {w['opp']}: p={w['p']}% {w['lab']} | {[f for f in w['flags'] if 'funnel' in f][0]}")
