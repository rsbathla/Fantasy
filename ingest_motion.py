#!/usr/bin/env python3
"""Ingest FantasyPoints MOTION-split exports -> boom/motion.json (per-player motion rate + in-motion lift).
FantasyPoints exports motion as a FILTER (motion vs no-motion), not a column. For each season there are two
player-level receiving aggregates whose routes sum to the full season; the smaller-route file = IN MOTION.
We pair them per season (the 'full' agg, if also present, equals the sum and is excluded), compute per player:
  motion_pct = motion routes / total routes ; plus YPRR/TPRR in motion vs not (motion 'lift').
Blended across all seasons (route-weighted). Output: boom/motion.json {key:{motion_pct,yprr_motion,yprr_nomotion,motion_lift,n_rte}}."""
import csv, os, json, glob, re
HERE=os.path.dirname(os.path.abspath(__file__))
CANDS=[os.path.dirname(HERE),HERE,'/sessions/gracious-gallant-edison/mnt/Downloads',os.path.expanduser('~/Downloads')]
def fn(n):
    n=str(n).strip().lower(); n=re.sub(r'\s+(jr|sr|ii|iii|iv|v)\.?$','',n); return n.replace('.','').replace("'","").replace('-',' ').strip()
def fl(r,k):
    try: return float(str(r.get(k,'')).replace('%','').replace(',','').strip())
    except: return None
# gather PLAYER-level season-aggregate receiving files (Season + RTE + POS, NO per-game WEEK)
aggs=[]
seen=set()
for d in CANDS:
    for f in sorted(glob.glob(os.path.join(d,'receivingAdvancedExport*.csv'))):
        bn=os.path.basename(f)
        if bn in seen: continue
        try: rows=list(csv.DictReader(open(f,encoding='utf-8-sig')))
        except Exception: continue
        if not rows: continue
        h=rows[0].keys()
        if 'WEEK' in h or 'Season' not in h or 'RTE' not in h or 'POS' not in h or 'Name' not in h: continue
        seasons=set(r['Season'] for r in rows)
        if len(seasons)!=1: continue
        se=seasons.pop(); tot=sum(fl(r,'RTE') or 0 for r in rows)
        aggs.append({'f':bn,'season':se,'tot':tot,'rows':rows}); seen.add(bn)
# group by season, find the motion pair (exclude 'full' = file whose total ~= sum of the other two)
byseason={}
for a in aggs: byseason.setdefault(a['season'],[]).append(a)
pairs=[]  # (season, motion_rows, nomotion_rows)
for se,lst in byseason.items():
    lst=sorted(lst,key=lambda x:-x['tot'])
    if len(lst)>=3 and abs(lst[0]['tot']-(lst[1]['tot']+lst[2]['tot']))/max(lst[0]['tot'],1)<0.05:
        pair=[lst[1],lst[2]]                  # lst[0] is the full aggregate -> drop
    elif len(lst)==2:
        pair=lst
    else:
        continue
    mo,no=(pair[0],pair[1]) if pair[0]['tot']<pair[1]['tot'] else (pair[1],pair[0])
    pairs.append((se,mo,no))
def idx(rows): return {fn(r['Name']):r for r in rows}
acc={}  # key -> sums
for se,mo,no in pairs:
    M=idx(mo['rows']); N=idx(no['rows'])
    for k in set(M)|set(N):
        m=M.get(k); n=N.get(k)
        mr=fl(m,'RTE') if m else 0; nr=fl(n,'RTE') if n else 0
        mr=mr or 0; nr=nr or 0
        a=acc.setdefault(k,{'name':(m or n)['Name'],'mrte':0.0,'nrte':0.0,'myds':0.0,'nyds':0.0,'mtgt':0.0,'ntgt':0.0})
        a['mrte']+=mr; a['nrte']+=nr
        if m: a['myds']+=(fl(m,'YPRR') or 0)*mr; a['mtgt']+=(fl(m,'TGT') or 0)
        if n: a['nyds']+=(fl(n,'YPRR') or 0)*nr; a['ntgt']+=(fl(n,'TGT') or 0)
out={}
for k,a in acc.items():
    tot=a['mrte']+a['nrte']
    if tot<60 or a['mrte']<20 or a['nrte']<20: continue   # real sample both sides
    mp=100*a['mrte']/tot
    ym=a['myds']/a['mrte'] if a['mrte'] else None
    yn=a['nyds']/a['nrte'] if a['nrte'] else None
    out[k]={'name':a['name'],'motion_pct':round(mp,1),'n_rte':round(tot),
            'yprr_motion':round(ym,2) if ym is not None else None,'yprr_nomotion':round(yn,2) if yn is not None else None,
            'motion_lift':round(ym-yn,2) if (ym is not None and yn is not None) else None}
os.makedirs(os.path.join(HERE,'boom'),exist_ok=True)
json.dump(out,open(os.path.join(HERE,'boom','motion.json'),'w'),ensure_ascii=False,indent=1)
print(f"ingest_motion: {len(out)} players from pairs {[(s,m['f'],n['f']) for s,m,n in pairs]}")
