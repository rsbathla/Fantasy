#!/usr/bin/env python3
"""Underdog Best Ball board: improved blend (half-PPR proj + fusion + playoff-ceiling + conviction
+ sim ceiling) anchored to UNDERDOG ADP. Output = a draft cheat-sheet (UD has no pre-load upload).
Weights tilt to ceiling/playoff vs DK because BBM playoffs are win-or-go-home (1/14, 1/12 each week)."""
import pandas as pd, numpy as np, re, os
HERE=os.path.dirname(os.path.abspath(__file__)); DL=os.path.dirname(os.path.dirname(HERE)); BB=os.path.dirname(HERE)
def fn(n):
    n=str(n).strip().lower(); n=re.sub(r'\s+(jr|sr|ii|iii|iv|v)\.?$','',n); n=n.replace('.','').replace("'","").replace('-',' '); return ' '.join(n.split())
import glob
def _latest(*pats):
    h=[x for q in pats for x in glob.glob(q)]
    return max(h, key=os.path.getmtime) if h else pats[0]   # newest by mtime (was: wrong alphabetical sort)
UD=_latest(f"{DL}/Underdog Downloadable Rankings*.csv")
ADP_CAP=6
# name, file, value_col, kind, weight
SRC=[
 ("ud_proj",   f"{BB}/pipeline/clay_2026_ud.csv","ud_pg","proj",0.26),   # half-PPR projection (UD-native)
 ("ours_ceil", f"{BB}/draft_board_signals.csv","p95","proj",0.16),       # simulated ceiling (relative)
 ("fusion",    f"{BB}/fusion_table.csv","consensus","proj",0.16),        # 22-signal model consensus
 ("playoff",   f"{BB}/engine/playoff_overlay.csv","playoff_up","proj",0.14), # W15-17 ceiling (UD rewards more)
 ("conviction",f"{BB}/qual_signal.csv","qual_score","proj",0.10),        # analyst conviction
]
def col_for(f):
    d=pd.read_csv(f); 
    nc='name' if 'name' in d.columns else ('Name' if 'Name' in d.columns else d.columns[0]); return d,nc
frames=[]; weights={}
for name,f,vc,kind,w in SRC:
    if not os.path.exists(f): print(f"  skip {name}: missing {f}"); continue
    d,nc=col_for(f); d=d[[nc,vc]].dropna(); d.columns=['name','val']; d['key']=d['name'].map(fn); d=d.drop_duplicates('key')
    d[name]=d['val'].rank(ascending=False,method='min')   # all proj-like: higher=better
    frames.append(d[['key',name]]); weights[name]=w
    print(f"  loaded {name}: {len(d)} ({w})")
# Underdog market (ADP anchor)
ud=pd.read_csv(UD); ud.columns=[c.strip().strip('"') for c in ud.columns]; ud['key']=ud['Name'].map(fn)
ud=ud.rename(columns={'ADP':'ud_adp','Position':'pos','Team':'team','OVR Rank':'ud_ovr'})
ud['ud_adp']=pd.to_numeric(ud['ud_adp'],errors='coerce')
udm=ud[['key','Name','pos','team','ud_adp']].drop_duplicates('key')
udm['ud_adp_rank']=udm['ud_adp'].rank(method='first')
frames.append(udm[['key']].assign(ud_adp_src=udm['ud_adp_rank'])); weights['ud_adp_src']=0.18

M=frames[0]
for fr in frames[1:]: M=M.merge(fr,on='key',how='outer')
cols=list(weights); W=np.array([weights[c] for c in cols]); R=M[cols].values
mask=~np.isnan(R); wmat=np.where(mask,W,0.0); wsum=wmat.sum(1)
M['score']=np.nansum(np.where(mask,R*W,0.0),1)/np.where(wsum>0,wsum,np.nan)
M['n_sources']=mask.sum(1)
M=M.merge(udm,on='key',how='left')
M=M[M['ud_adp'].notna()]                      # keep only real UD players (draftable pool)
M=M.sort_values(['score','ud_adp']).reset_index(drop=True)
M['opinion_rank']=M.index+1
# cap deviation from UD ADP so the board stays draftable
cur=M['opinion_rank'].astype(float).copy()
for _ in range(6):
    dev=(cur-M['ud_adp_rank']).clip(-ADP_CAP,ADP_CAP)
    cur=pd.Series(np.where(M['ud_adp_rank'].notna(),M['ud_adp_rank']+dev,cur),index=M.index).rank(method='first')
M['ud_rank']=cur.astype(int)
M=M.sort_values('ud_rank').reset_index(drop=True)
M['value']=(M['ud_adp_rank']-M['ud_rank']).round(0)     # +ve = we're higher than UD market
M['round']=((M['ud_rank']-1)//12+1)
udpg=pd.read_csv(f"{BB}/pipeline/clay_2026_ud.csv"); udpg['key']=udpg['name'].map(fn)
M=M.merge(udpg[['key','ud_pg']],on='key',how='left')
out=M[['ud_rank','Name','pos','team','ud_adp','value','ud_pg','round','opinion_rank','n_sources']].rename(columns={'Name':'name'})
out.to_csv(f"{BB}/ud_cheatsheet.csv",index=False)
print(f"\nwrote {BB}/ud_cheatsheet.csv  ({len(out)} players)")
print("\nTop 15 (UD half-PPR board):")
print(out.head(15).to_string(index=False))
print("\nBiggest UP vs UD market (our edge):")
print(out[out.n_sources>=3].sort_values('value',ascending=False)[['name','pos','team','ud_adp','ud_rank','value']].head(8).to_string(index=False))
