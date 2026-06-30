#!/usr/bin/env python3
"""Ingest SIS Receiving EPA vs ZONE + compute the man-vs-zone EPA/tgt DELTA (the coverage matchup edge)."""
import core, csv, os
fn=core.fn
def pct(x):
    try: return round(float(str(x).replace('%','').replace('"','')),1)
    except: return None
def num(x):
    try: return float(str(x).replace('"',''))
    except: return None
Z={}
p=core.P('sis_value/receiving_zone.csv')
if os.path.exists(p):
    for r in csv.DictReader(open(p,encoding='utf-8')):
        Z[fn(r['Player'])]={'rec_epa_zone':num(r.get('EPA')),'rec_epa_per_tgt_zone':num(r.get('EPA Per Tgt')),'rec_boom_zone':pct(r.get('Boom%'))}
feats=list(csv.DictReader(open(core.P('features.csv'),encoding='utf-8')))
def f2(x):
    try: return float(x)
    except: return None
n=0
for f in feats:
    k=fn(f['name'])
    if f['pos'] in ('WR','TE') and Z.get(k):
        for kk,v in Z[k].items():
            if v is not None: f[kk]=v
        man=f2(f.get('rec_epa_per_tgt_man')); zone=Z[k].get('rec_epa_per_tgt_zone')
        if man is not None and zone is not None:
            f['rec_man_zone_delta']=round(man-zone,3)   # +=feasts vs man, -=feasts vs zone
        n+=1
cols=[]
for f in feats:
    for c in f:
        if c not in cols: cols.append(c)
with open(core.P('features.csv'),'w',newline='',encoding='utf-8') as fh:
    w=csv.DictWriter(fh,fieldnames=cols); w.writeheader(); [w.writerow(f) for f in feats]
core.safe_json_dump({'meta':{'n':len(feats),'cols':cols},'players':feats}, core.P('features.json'))
print("rec ZONE + man/zone delta -> %d WR/TE | total cols %d"%(n,len(cols)))
d={fn(f['name']):f for f in feats}
print("man-vs-zone EPA/tgt edge (+ = feasts vs man):")
for nm in ["Puka Nacua","Ja'Marr Chase","George Pickens","Brock Bowers","Amon-Ra St. Brown"]:
    f=d.get(fn(nm),{}); print("  %-18s man=%s zone=%s delta=%s | boom man=%s zone=%s"%(nm,f.get('rec_epa_per_tgt_man'),f.get('rec_epa_per_tgt_zone'),f.get('rec_man_zone_delta'),f.get('rec_boom_man'),f.get('rec_boom_zone')))
