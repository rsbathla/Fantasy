#!/usr/bin/env python3
"""Ingest SIS DataHub QB passing EPA vs MAN vs ZONE coverage (passing_man.csv / passing_zone.csv).

For each board QB we add:
  qb_epa_man, qb_epa_zone   -- PER-ATTEMPT EPA (EPA column / Att column) vs that coverage family.
  qb_boom_man, qb_boom_zone -- raw Boom% vs that coverage family.
  qb_man_zone_delta = qb_epa_man - qb_epa_zone  (+ve = better vs MAN, the man-beater QB read).

Per-attempt normalization: the SIS leaderboard gives total EPA + Att per split, so EPA/Att is the
natural rate (directly parallel to the RECEIVING template's rec_man_zone_delta = EPA/tgt vs MAN - vs
ZONE). If a split has Att<=0 we fall back to the raw EPA difference (documented in meta). Team column
uses SIS nicknames (mapped, but QBs join on name only). Rows for "2 teams" (traded) are skipped.
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
        if str(r.get('Team','')).strip()=='2 teams': continue   # traded -> ambiguous, skip
        att=num(r.get('Att')); epa=num(r.get('EPA'))
        epa_att=round(epa/att,4) if (epa is not None and att and att>0) else None
        out[fn(r['Player'])]={'att':att,'epa':epa,'epa_att':epa_att,'boom':pct(r.get('Boom%'))}
    return out
MAN=load(core.P('sis_value/passing_man.csv')); Z=load(core.P('sis_value/passing_zone.csv'))
feats=list(csv.DictReader(open(core.P('features.csv'),encoding='utf-8')))
n=ndelta=0
for f in feats:
    if f['pos']!='QB': continue
    k=fn(f['name']); m=MAN.get(k); z=Z.get(k)
    if not (m or z): continue
    n+=1
    if m:
        if m['epa_att'] is not None: f['qb_epa_man']=m['epa_att']
        if m['boom'] is not None: f['qb_boom_man']=m['boom']
    if z:
        if z['epa_att'] is not None: f['qb_epa_zone']=z['epa_att']
        if z['boom'] is not None: f['qb_boom_zone']=z['boom']
    # man/zone delta: PER-ATTEMPT EPA difference (preferred); fall back to raw EPA diff
    if m and z and m['epa_att'] is not None and z['epa_att'] is not None:
        f['qb_man_zone_delta']=round(m['epa_att']-z['epa_att'],4); ndelta+=1
    elif m and z and m['epa'] is not None and z['epa'] is not None:
        f['qb_man_zone_delta']=round(m['epa']-z['epa'],4); ndelta+=1   # rare fallback (no Att)
cols=[]
for f in feats:
    for c in f:
        if c not in cols: cols.append(c)
with open(core.P('features.csv'),'w',newline='',encoding='utf-8') as fh:
    w=csv.DictWriter(fh,fieldnames=cols); w.writeheader(); [w.writerow(f) for f in feats]
core.safe_json_dump({'meta':{'n':len(feats),'cols':cols,'added':'SIS QB man/zone: qb_epa_man/zone (EPA/att), qb_boom_man/zone, qb_man_zone_delta (per-att EPA, +=man-beater)'},'players':feats}, core.P('features.json'))
print("QB man/zone -> %d QBs (delta on %d) | total cols %d"%(n,ndelta,len(cols)))
d={fn(f['name']):f for f in feats}
print("QB man-vs-zone per-att EPA edge (+ = better vs MAN):")
for nm in ["Bo Nix","Josh Allen","Joe Burrow","Jared Goff","Caleb Williams"]:
    f=d.get(fn(nm),{}); print("  %-16s man=%s zone=%s delta=%s | boom man=%s zone=%s"%(nm,f.get('qb_epa_man'),f.get('qb_epa_zone'),f.get('qb_man_zone_delta'),f.get('qb_boom_man'),f.get('qb_boom_zone')))
