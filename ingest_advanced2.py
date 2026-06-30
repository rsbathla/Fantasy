#!/usr/bin/env python3
"""Phase 2 enrichment: add the FP-correlated signals that were missing -
route types + deep-route share (WR/TE), receiving efficiency (YPT/TPRR/YPRR incl RB),
QB rushing yds/g + deep-ball share + ANY/A + scrambles (game-outcome layers), RB outside-run share + rec yds/g."""
import core, pandas as pd, glob, os, csv
NFL=core.find_data('NFL-master','FP','2025')
fn=core.fn; nt=core.norm_team
def W(g,col,wt):  # weighted avg
    s=g[wt].sum(); return (g[col]*g[wt]).sum()/s if s else None
# ---------- route types (WR/TE/RB receiving) ----------
DEEP={'Go-Fly','Post','Corner'}
rt=pd.concat([pd.read_csv(f).assign(_rt=os.path.basename(f)[:-4]) for f in glob.glob(f'{NFL}/Receiving/RouteType/*.csv')],ignore_index=True)
rprof={}
for k,g in rt.groupby(rt['Name'].map(fn)):
    rte=g['RTE'].sum(); tgt=g['TGT'].sum(); yds=g['YDS'].sum(); deep=g[g['_rt'].isin(DEEP)]['RTE'].sum(); fd=g['1D'].sum() if '1D' in g.columns else 0
    rprof[k]={'route_yprr':round(yds/rte,2) if rte else None,'route_ypt':round(yds/tgt,1) if tgt else None,
        'route_tprr':round(tgt/rte,3) if rte else None,'deep_route_sh':round(deep/rte*100,1) if rte else None,
        'fd_rr':round(fd/rte,3) if rte else None}
# ---------- QB deep ball + ANY/A + scrambles ----------
deep=pd.read_csv(f'{NFL}/Passing/TargetDirection_SD/Deep.csv'); short=pd.read_csv(f'{NFL}/Passing/TargetDirection_SD/Short.csv')
deep['k']=deep['Name'].map(fn); short['k']=short['Name'].map(fn)
qprof={}
for k in set(deep.k)|set(short.k):
    da=deep[deep.k==k]['ATT'].sum(); sa=short[short.k==k]['ATT'].sum(); tot=da+sa
    dy=W(deep[deep.k==k],'YPA','ATT')
    qprof[k]={'deep_ball_sh':round(da/tot*100,1) if tot else None,'deep_ypa':round(dy,1) if dy else None}
pc=pd.concat([pd.read_csv(f) for f in glob.glob(f'{NFL}/Passing/CoverageType/*.csv')],ignore_index=True); pc['k']=pc['Name'].map(fn)
for k,g in pc.groupby('k'):
    anya=W(g,'ANY/A','DB'); qprof.setdefault(k,{})['qb_anya']=round(anya,2) if anya else None
    if 'SCRM' in g.columns: qprof[k]['qb_scramble']=int(g['SCRM'].sum())
# ---------- RB rush direction (outside share) ----------
rdp=pd.concat([pd.read_csv(f).assign(_d=os.path.basename(f)[:-4]) for f in glob.glob(f'{NFL}/Rushing/RushDirectionPooled/*.csv')],ignore_index=True)
rdir={}
for k,g in rdp.groupby(rdp['Name'].map(fn)):
    tot=g['ATT'].sum(); end=g[g['_d']=='End']['ATT'].sum()
    rdir[k]={'outside_run_sh':round(end/tot*100,1) if tot else None}
# ---------- QB rush yds/g + RB rec yds/g (player_games via canonical join) ----------
ag,IDX,SH=core.build_usage_index()
# ---------- merge ----------
feats=list(csv.DictReader(open(core.P('features.csv'),encoding='utf-8')))
nr=nq=nrb=0
for f in feats:
    k=fn(f['name']); pos=f['pos']; tm=nt(f['team'])
    if pos in ('WR','TE','RB') and rprof.get(k):
        nr+=1
        for kk in ('route_yprr','route_ypt','route_tprr','deep_route_sh','fd_rr'): f[kk]=rprof[k][kk]
    if pos=='QB':
        if qprof.get(k):
            nq+=1
            for kk in ('deep_ball_sh','deep_ypa','qb_anya','qb_scramble'):
                if kk in qprof[k]: f[kk]=qprof[k][kk]
        u=core.match_usage(f['name'],'QB',tm,IDX)
        if u is not None: f['qb_rush_ypg']=round(float(u['rushyd_pg']),1)
    if pos=='RB':
        nrb+=1
        u=core.match_usage(f['name'],'RB',tm,IDX)
        if u is not None: f['rb_rec_ypg']=round(float(u['recyd_pg']),1); f['rb_rec_pg']=round(float(u['rec_pg']),1)
        if rdir.get(k): f['outside_run_sh']=rdir[k]['outside_run_sh']
cols=[]
for f in feats:
    for c in f:
        if c not in cols: cols.append(c)
with open(core.P('features.csv'),'w',newline='',encoding='utf-8') as fh:
    w=csv.DictWriter(fh,fieldnames=cols); w.writeheader(); [w.writerow(f) for f in feats]
core.safe_json_dump({'meta':{'n':len(feats),'cols':cols,'enriched':'+route-types +pass-direction +QB-rushing/ANYA/scramble +RB-receiving +rush-direction'},'players':feats}, core.P('features.json'))
print("now %d cols | route prof %d, QB layers %d, RB %d"%(len(cols),nr,nq,nrb))
d={fn(f['name']):f for f in feats}
for nm in ["Josh Allen","Jalen Hurts","Ja'Marr Chase","Jahmyr Gibbs","Brock Bowers","Tyreek Hill"]:
    f=d.get(fn(nm),{})
    print(" %-18s deepRoute%%=%s routeYPRR=%s YPT=%s TPRR=%s | qb_rushYPG=%s deepBall%%=%s ANYA=%s scrm=%s | rbRecYPG=%s outRun%%=%s"%(
        nm,f.get('deep_route_sh'),f.get('route_yprr'),f.get('route_ypt'),f.get('route_tprr'),f.get('qb_rush_ypg'),f.get('deep_ball_sh'),f.get('qb_anya'),f.get('qb_scramble'),f.get('rb_rec_ypg'),f.get('outside_run_sh')))
