#!/usr/bin/env python3
"""Ingest SIS DataHub RB rushing EPA by run scheme: ZONE vs GAP (rushing_zone.csv / rushing_gap.csv).

For each board RB we add:
  rb_epa_a_zone, rb_epa_a_gap   -- the SIS 'EPA/A' (EPA per attempt) column for that run scheme.
  rb_boom_zone, rb_boom_gap     -- raw Boom% for that scheme.
  rb_zone_gap_delta = rb_epa_a_zone - rb_epa_a_gap  (+ve = better on ZONE-scheme runs).

EPA/A is already a per-attempt rate on the SIS leaderboard, so the delta is the difference of two
per-attempt EPAs (directly parallel to the receiving/QB man-zone deltas). Team uses SIS nicknames
(RBs join on name only); "2 teams" (traded) rows are skipped.
"""
import core, csv, os
fn=core.fn
def pct(x):
    try: return round(float(str(x).replace('%','').replace('"','')),1)
    except: return None
def num(x):
    try: return float(str(x).replace('"',''))
    except: return None
def load(path):
    if not os.path.exists(path): return {}
    out={}
    for r in csv.DictReader(open(path,encoding='utf-8')):
        if str(r.get('Team','')).strip()=='2 teams': continue
        out[fn(r['Player'])]={'epa_a':num(r.get('EPA/A')),'boom':pct(r.get('Boom%')),'att':num(r.get('Att'))}
    return out
ZONE=load(core.P('sis_value/rushing_zone.csv')); GAP=load(core.P('sis_value/rushing_gap.csv'))
feats=list(csv.DictReader(open(core.P('features.csv'),encoding='utf-8')))
n=ndelta=0
for f in feats:
    if f['pos']!='RB': continue
    k=fn(f['name']); z=ZONE.get(k); g=GAP.get(k)
    if not (z or g): continue
    n+=1
    if z:
        if z['epa_a'] is not None: f['rb_epa_a_zone']=z['epa_a']
        if z['boom'] is not None: f['rb_boom_zone']=z['boom']
    if g:
        if g['epa_a'] is not None: f['rb_epa_a_gap']=g['epa_a']
        if g['boom'] is not None: f['rb_boom_gap']=g['boom']
    if z and g and z['epa_a'] is not None and g['epa_a'] is not None:
        f['rb_zone_gap_delta']=round(z['epa_a']-g['epa_a'],4); ndelta+=1
cols=[]
for f in feats:
    for c in f:
        if c not in cols: cols.append(c)
with open(core.P('features.csv'),'w',newline='',encoding='utf-8') as fh:
    w=csv.DictWriter(fh,fieldnames=cols); w.writeheader(); [w.writerow(f) for f in feats]
core.safe_json_dump({'meta':{'n':len(feats),'cols':cols,'added':'SIS RB zone/gap: rb_epa_a_zone/gap (EPA/A), rb_boom_zone/gap, rb_zone_gap_delta (+=better on zone runs)'},'players':feats}, core.P('features.json'))
print("RB zone/gap -> %d RBs (delta on %d) | total cols %d"%(n,ndelta,len(cols)))
d={fn(f['name']):f for f in feats}
print("RB zone-vs-gap EPA/A edge (+ = better on ZONE runs):")
for nm in ["Bijan Robinson","Jahmyr Gibbs","Jonathan Taylor","Derrick Henry","Chase Brown"]:
    f=d.get(fn(nm),{}); print("  %-18s zone=%s gap=%s delta=%s | boom zone=%s gap=%s | own zone_run_sh=%s"%(nm,f.get('rb_epa_a_zone'),f.get('rb_epa_a_gap'),f.get('rb_zone_gap_delta'),f.get('rb_boom_zone'),f.get('rb_boom_gap'),f.get('zone_run_sh')))
