#!/usr/bin/env python3
"""Phase 3: close the remaining top-7 FP-correlated gaps -
Rec Yards/Game (RB/WR/TE), CPOE (QB), aDOT-Adj Yds/Target (residual of YPT on aDOT).
EPA is NOT in the exported offense files (no NFL PBP on disk), so an explicit proxy is recorded."""
import core, pandas as pd, glob, os, csv, numpy as np
NFL=core.find_data('NFL-master','FP','2025'); fn=core.fn; nt=core.norm_team
ag,IDX,SH=core.build_usage_index()
# CPOE (QB), weighted by dropbacks
pc=pd.concat([pd.read_csv(f) for f in glob.glob(f'{NFL}/Passing/CoverageType/*.csv')],ignore_index=True); pc['k']=pc['Name'].map(fn)
CPOE={}
for k,g in pc.groupby('k'):
    db=g['DB'].sum()
    if 'CPOE' in g.columns and db: CPOE[k]=round((g['CPOE']*g['DB']).sum()/db,2)
feats=list(csv.DictReader(open(core.P('features.csv'),encoding='utf-8')))
# fit expected YPT ~ aDOT across receivers (to strip the deep-shot premium)
pts=[(float(f['adot25']),float(f['route_ypt'])) for f in feats if f.get('adot25') not in (None,'') and f.get('route_ypt') not in (None,'')]
b1,b0=(np.polyfit([p[0] for p in pts],[p[1] for p in pts],1) if len(pts)>10 else (0,0))
nadd={'recyd_pg':0,'cpoe':0,'adot_adj_ypt':0,'epa_proxy':0}
for f in feats:
    k=fn(f['name']); pos=f['pos']; tm=nt(f['team'])
    if pos in ('RB','WR','TE'):
        u=core.match_usage(f['name'],pos,tm,IDX)
        if u is not None: f['recyd_pg']=round(float(u['recyd_pg']),1); nadd['recyd_pg']+=1
        if f.get('adot25') not in (None,'') and f.get('route_ypt') not in (None,''):
            f['adot_adj_ypt']=round(float(f['route_ypt'])-(b0+b1*float(f['adot25'])),2); nadd['adot_adj_ypt']+=1
        # EPA/snap & EPA/touch proxies (raw EPA unavailable): receiving uses YPRR
        if f.get('route_yprr') not in (None,''): f['epa_proxy']=f['route_yprr']; f['epa_proxy_src']='YPRR'; nadd['epa_proxy']+=1
    if pos=='QB':
        if CPOE.get(k) is not None: f['cpoe']=CPOE[k]; nadd['cpoe']+=1
        if f.get('qb_anya') not in (None,''): f['epa_proxy']=f['qb_anya']; f['epa_proxy_src']='ANY/A'; nadd['epa_proxy']+=1
cols=[]
for f in feats:
    for c in f:
        if c not in cols: cols.append(c)
with open(core.P('features.csv'),'w',newline='',encoding='utf-8') as fh:
    w=csv.DictWriter(fh,fieldnames=cols); w.writeheader(); [w.writerow(f) for f in feats]
core.safe_json_dump({'meta':{'n':len(feats),'cols':cols},'players':feats}, core.P('features.json'))
print("added:",nadd,"| total cols:",len(cols))
