#!/usr/bin/env python3
"""Ingest SIS Receiving EPA vs MAN coverage (rec_epa_per_tgt_man, rec_boom_man, rec_epa_man) for WR/TE."""
import core, csv, os
fn=core.fn
def pct(x):
    try: return round(float(str(x).replace('%','').replace('"','')),1)
    except: return None
def num(x):
    try: return float(str(x).replace('"',''))
    except: return None
MAN={}
p=core.P('sis_value/receiving_man.csv')
if os.path.exists(p):
    for r in csv.DictReader(open(p,encoding='utf-8')):
        MAN[fn(r['Player'])]={'rec_epa_man':num(r.get('EPA')),'rec_epa_per_tgt_man':num(r.get('EPA Per Tgt')),'rec_boom_man':pct(r.get('Boom%'))}
feats=list(csv.DictReader(open(core.P('features.csv'),encoding='utf-8')))
n=0
for f in feats:
    k=fn(f['name'])
    if f['pos'] in ('WR','TE') and MAN.get(k):
        for kk,v in MAN[k].items():
            if v is not None: f[kk]=v
        n+=1
cols=[]
for f in feats:
    for c in f:
        if c not in cols: cols.append(c)
with open(core.P('features.csv'),'w',newline='',encoding='utf-8') as fh:
    w=csv.DictWriter(fh,fieldnames=cols); w.writeheader(); [w.writerow(f) for f in feats]
core.safe_json_dump({'meta':{'n':len(feats),'cols':cols},'players':feats}, core.P('features.json'))
print("rec vs-MAN EPA -> %d WR/TE | total cols %d"%(n,len(cols)))
