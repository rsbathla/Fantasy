#!/usr/bin/env python3
"""Ingest SIS Receiving Value (WR/TE Boom%/Bust%/EPA/EPA-per-tgt) + quantify a snap-share ESTIMATE
(route participation for pass-catchers, touch-opportunity share for RBs; true snap counts aren't on the SIS leaderboard)."""
import core, csv, os
fn=core.fn
def pct(x):
    try: return round(float(str(x).replace('%','').replace('"','')),1)
    except: return None
def num(x):
    try: return float(str(x).replace('"',''))
    except: return None
REC={}
p=core.P('sis_value/receiving_value.csv')
if os.path.exists(p):
    for r in csv.DictReader(open(p,encoding='utf-8')):
        REC[fn(r['Player'])]={'sis_epa':num(r.get('EPA')),'sis_epa_per_tgt':num(r.get('EPA Per Tgt')),
            'sis_positive':pct(r.get('Positive%')),'sis_par':num(r.get('PAR')),
            'sis_boom':pct(r.get('Boom%')),'sis_bust':pct(r.get('Bust%'))}
feats=list(csv.DictReader(open(core.P('features.csv'),encoding='utf-8')))
def f2(x):
    try: return float(x)
    except: return None
nrec=nsnap=0
for f in feats:
    k=fn(f['name']); pos=f['pos']
    if pos in ('WR','TE') and REC.get(k):
        for kk,v in REC[k].items():
            if v is not None: f[kk]=v
        nrec+=1
    elif pos=='RB' and REC.get(k):  # RB receiving as secondary (don't clobber rushing sis_epa)
        if REC[k].get('sis_boom') is not None: f['sis_rec_boom']=REC[k]['sis_boom']
        if REC[k].get('sis_epa_per_tgt') is not None: f['sis_rec_epa_per_tgt']=REC[k]['sis_epa_per_tgt']
    # snap-share ESTIMATE
    tmp=f2(f.get('tm_plays')); tgtpg=f2(f.get('tgt_pg')); carpg=f2(f.get('car_pg')); tprr=f2(f.get('route_tprr'))
    if tmp and tmp>0:
        if pos in ('WR','TE') and tgtpg and tprr and tprr>0:
            routes_g=tgtpg/tprr; f['snap_share_est']=round(min(100,routes_g/tmp*100),1); f['snap_est_basis']='route-participation'; nsnap+=1
        elif pos=='RB' and (carpg or tgtpg):
            f['snap_share_est']=round(min(100,((carpg or 0)+(tgtpg or 0))/tmp*100),1); f['snap_est_basis']='touch-opportunity'; nsnap+=1
cols=[]
for f in feats:
    for c in f:
        if c not in cols: cols.append(c)
with open(core.P('features.csv'),'w',newline='',encoding='utf-8') as fh:
    w=csv.DictWriter(fh,fieldnames=cols); w.writeheader(); [w.writerow(f) for f in feats]
core.safe_json_dump({'meta':{'n':len(feats),'cols':cols},'players':feats}, core.P('features.json'))
print("Receiving Value -> %d WR/TE | snap-share est -> %d players | total cols %d"%(nrec,nsnap,len(cols)))
# show RB run-type already present + a few receiver Boom/Bust + snap est
d={fn(f['name']):f for f in feats}
print("\nRB run-type (already ingested earlier):")
for nm in ["Bijan Robinson","Derrick Henry","Jahmyr Gibbs"]:
    f=d.get(fn(nm),{}); print("  %-16s zone_run%%=%s zone_succ=%s gap_succ=%s stuff%%=%s | snap_est=%s(%s)"%(nm,f.get('zone_run_sh'),f.get('zone_succ'),f.get('gap_succ'),f.get('stuff_pct'),f.get('snap_share_est'),f.get('snap_est_basis')))
print("\nReceivers Boom/Bust + snap est:")
for nm in ["Puka Nacua","Ja'Marr Chase","Brock Bowers","Trey McBride"]:
    f=d.get(fn(nm),{}); print("  %-18s sisEPA=%s EPA/tgt=%s Boom%%=%s Bust%%=%s | snap_est=%s%%(%s)"%(nm,f.get('sis_epa'),f.get('sis_epa_per_tgt'),f.get('sis_boom'),f.get('sis_bust'),f.get('snap_share_est'),f.get('snap_est_basis')))
