#!/usr/bin/env python3
"""Ingest SIS DataHub 'Value' exports (EPA, Points-Earned/play, Positive%, PAR, Boom%, Bust%)
pulled via the user's authenticated Download. QB<-passing_value, RB<-rushing_value. Boom/Bust = ceiling/floor rates."""
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
        out[fn(r['Player'])]={'sis_epa':num(r.get('EPA')),'sis_pe_play':num(r.get('PE Per Play')),
            'sis_positive':pct(r.get('Positive%')),'sis_par':num(r.get('PAR')),
            'sis_boom':pct(r.get('Boom%')),'sis_bust':pct(r.get('Bust%'))}
    return out
PASS=load(core.P('sis_value/passing_value.csv')); RUSH=load(core.P('sis_value/rushing_value.csv'))
feats=list(csv.DictReader(open(core.P('features.csv'),encoding='utf-8')))
nq=nr=0
for f in feats:
    k=fn(f['name']); pos=f['pos']
    src = PASS.get(k) if pos=='QB' else (RUSH.get(k) if pos=='RB' else None)
    if src:
        for kk,v in src.items():
            if v is not None: f[kk]=v
        if pos=='QB': nq+=1
        else: nr+=1
cols=[]
for f in feats:
    for c in f:
        if c not in cols: cols.append(c)
with open(core.P('features.csv'),'w',newline='',encoding='utf-8') as fh:
    w=csv.DictWriter(fh,fieldnames=cols); w.writeheader(); [w.writerow(f) for f in feats]
core.safe_json_dump({'meta':{'n':len(feats),'cols':cols,'added':'SIS Value: EPA/PE-per-play/Positive%/PAR/Boom%/Bust%'},'players':feats}, core.P('features.json'))
print("SIS Value merged -> QB %d, RB %d | total cols %d"%(nq,nr,len(cols)))
d={fn(f['name']):f for f in feats}
for nm in ["Bo Nix","Josh Allen","Bijan Robinson","Derrick Henry"]:
    f=d.get(fn(nm),{}); print(" %-16s sisEPA=%s PE/play=%s Boom%%=%s Bust%%=%s PAR=%s"%(nm,f.get('sis_epa'),f.get('sis_pe_play'),f.get('sis_boom'),f.get('sis_bust'),f.get('sis_par')))
