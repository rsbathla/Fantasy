#!/usr/bin/env python3
"""Per-player COVERAGE SPECIALIST.

WR/TE: now 2-SEASON (2024+2025) from the FantasyPoints "Receiving Man vs. Zone" exports
(receivingManVsZone_2024.csv + _2025.csv) — per-player FP/RR vs Man / Zone / Single-High /
Two-High, routes-weighted across both seasons, then ranked as a LEAGUE PERCENTILE (the user's
method) within position. Bigger, cleaner buckets + 2 seasons => far more stable than the old
1-season 5-coverage matchup tool (which was season-locked to 2025 and small-sample per cover).

QB: unchanged — qbCoverageMatchupExport (Cover-2/3/4/6, 2025); no 2024 QB man/zone tool exists.

best_key in {man,zone,single_high,two_high} (WR/TE) or {man,c2,c3,c4,c6} (QB) maps to
defense_shell usage so it activates vs defenses that run that shell heavily.
"""
import csv, json, os, bisect, statistics as st
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__)); DL = os.path.dirname(HERE); B = os.path.join(HERE, 'boom')
from boomutil import fn, num
MIN_RT = 50; PCTL_FLAG = 80; CO_MARGIN = 8
NM = {'man':'Man','zone':'Zone','single_high':'Single-High','two_high':'Two-High',
      'c2':'Cover-2','c3':'Cover-3','c4':'Cover-4','c6':'Cover-6'}
# Man vs Zone positional cols (0-idx): 6-9 OVERALL,10-13 MAN,14-17 ZONE,18-21 SINGLE,22-25 TWO (RTE,TPRR,YPRR,FP/RR)
MZ = {'man':(10,13),'zone':(14,17),'single_high':(18,21),'two_high':(22,25)}

def parse_mz(files):
    agg = {}
    for f in files:
        p = os.path.join(DL, f)
        if not os.path.exists(p): continue
        for r in list(csv.reader(open(p, encoding='utf-8-sig')))[1:]:
            if len(r) < 26: continue
            k = fn(r[1]); a = agg.setdefault(k, {'name': r[1], 'pos': r[3], 'rt': defaultdict(float), 'w': defaultdict(float)})
            a['pos'] = r[3]
            for bk,(rt_i,fp_i) in MZ.items():
                rt = num(r[rt_i]); fp = num(r[fp_i])
                if rt and fp is not None: a['rt'][bk]+=rt; a['w'][bk]+=fp*rt
    out = []
    for k,a in agg.items():
        vals = {bk: a['w'][bk]/a['rt'][bk] for bk in MZ if a['rt'][bk] >= MIN_RT}
        if len(vals) >= 3: out.append((a['name'], a['pos'], vals, {bk:round(a['rt'][bk]) for bk in a['rt']}))
    return out

def pctl(xs, x):
    lo=bisect.bisect_left(xs,x); hi=bisect.bisect_right(xs,x); return 100.0*(lo+hi)/2/len(xs)

def specialize(recs, keys):
    dist={}; lg={}
    for bk in keys:
        xs=sorted(v[bk] for _,_,v,_ in recs if bk in v)
        if len(xs)>=10: dist[bk]=xs; lg[bk]=st.mean(xs)
    out={}
    for nm,pos,vals,rts in recs:
        pc={bk:pctl(dist[bk],vals[bk]) for bk in vals if bk in dist}
        if not pc: continue
        best=max(pc,key=pc.get)
        if pc[best]>=PCTL_FLAG:
            co=sorted([bk for bk in pc if pc[bk]>=pc[best]-CO_MARGIN and pc[bk]>=70], key=lambda b:pc[b], reverse=True)
            out[fn(nm)]={'name':nm,'pos':pos,'best':' & '.join(NM[b] for b in co[:2]),'best_key':best,'best_keys':co[:3],
                         'pctl':round(pc[best]),'val':round(vals[best],2),'lg':round(lg[best],2),
                         'ratio':round(vals[best]/lg[best],2) if lg[best] else None,'routes':rts.get(best,0),
                         'profile':{b:round(vals[b],2) for b in vals},'pctls':{b:round(pc[b]) for b in pc}}
    return out

# WR/TE — 2 season man-vs-zone
mz = parse_mz(["receivingManVsZone_2024.csv","receivingManVsZone_2025.csv"])
out = {}
out.update(specialize([r for r in mz if r[1]=='WR'], list(MZ)))
out.update(specialize([r for r in mz if r[1]=='TE'], list(MZ)))

# QB — unchanged (2025 cover-matchup, Cover-2/3/4/6)
def parse_qb():
    rows=list(csv.reader(open(os.path.join(DL,"qbCoverageMatchupExport.csv"),encoding='utf-8-sig')))[1:]
    perf={'c2':19,'c3':23,'c4':27,'c6':31,'man':15}; use={'c2':18,'c3':22,'c4':26,'c6':30,'man':14}; vol=7
    recs=[]
    for r in rows:
        if len(r)<=max(max(perf.values()),vol): continue
        tot=num(r[vol]) or 0; vals={}
        for bk in perf:
            p=num(r[perf[bk]]); u=num(r[use[bk]])
            if p is not None and u is not None and (tot*u/100)>=25: vals[bk]=p
        if len(vals)>=3: recs.append((r[1],'QB',vals,{}))
    return recs
out.update(specialize(parse_qb(), ['man','c2','c3','c4','c6']))

json.dump(out, open(f"{B}/cover_spec.json",'w'), ensure_ascii=False)
sm=json.load(open(f"{B}/statmenu.json")); hit=0
for k,v in sm.items():
    if k in out: v['cspec']=out[k]; hit+=1
json.dump(sm, open(f"{B}/statmenu.json",'w'), ensure_ascii=False)
from collections import Counter
print(f"coverage specialists: {len(out)} (statmenu {hit}) | spread:", Counter(v['best_key'] for v in out.values()).most_common())
for nm in ['George Pickens','Puka Nacua',"Ja'Marr Chase",'Nico Collins','Trey McBride']:
    c=out.get(fn(nm))
    if c: print(f"  {nm:16} -> {c['best']:20} pctl={c['pctl']} ratio={c['ratio']}x routes={c['routes']}")
