import pandas as pd, numpy as np, os, warnings; warnings.filterwarnings('ignore')
pp=pd.read_csv('layer2_player_params.csv'); tp=pd.read_csv('layer2_team_params.csv').set_index('team')
K,SG,ST,SP,SPR=8,0.31,0.27,1.0,0.9   # SPR = rush yardage noise
_plat=os.environ.get('BB_PLATFORM','DK').upper()
_col=os.environ.get('BB_PROJ_COL') or ('ud_pg' if _plat=='UD' else 'dk_pg')   # scoring column follows the platform (UD -> half-PPR)
if _col not in pp.columns:                                                    # never KeyError on a missing projection col (F3 fix)
    warnings.warn(f"[sim_prod] projection column '{_col}' absent -> falling back to dk_pg (rebuild layer2 for UD scoring)"); _col='dk_pg'
clay=pp.set_index('name')[_col].to_dict()

def gen_team(team,n,Gz,rng):
    """return dict name->DK array (skill incl rec+rush, + QB), calibrated to Clay means"""
    out={}
    T=tp.loc[team]
    teamz=rng.normal(0,1,n); vol=np.exp(SG*Gz+ST*teamz-0.5*(SG**2+ST**2))
    # ---- receiving (WR/TE/RB with targets) ----
    rc=pp[(pp.team==team)&(pp.role.isin(['WR','TE','RB']))&(pp.tgt_share>0)].copy()
    if len(rc):
        sh=rc['tgt_share'].values; sh=sh/sh.sum()
        ypt=np.clip(np.nan_to_num(rc['ypt'].values,nan=8.),1,30); cr=np.clip(np.nan_to_num(rc['catch_rate'].values,nan=.65),.3,.95)
        tdr=np.clip(np.nan_to_num(rc['rec_td_per_tgt'].values,nan=.05),.005,.25)
        W=rng.dirichlet(K*sh,size=n); rel=ypt/(sh@ypt); ysh=W*rel; ysh=ysh/ysh.sum(1,keepdims=True)
        pn=np.exp(SP*rng.normal(0,1,(n,len(sh)))-0.5*SP**2)
        ry=ysh*(T['team_pass_yds_pg']*vol)[:,None]*pn
        tg=W*(T['team_pass_att_pg']*np.exp(0.3*ST*teamz))[:,None]; rec=tg*cr
        ps=sh*tdr; ps/=ps.sum(); TD=rng.poisson(np.clip(ps[None,:]*(T['team_pass_td_pg']*vol)[:,None],0,None))
        recdk=rec+ry*0.1+TD*6+3.0*(ry>=100)            # DK +3 bonus for 100+ receiving yards (per sim, per receiver)
        for i,nm in enumerate(rc['name'].values): out[nm]=out.get(nm,0)+recdk[:,i]
        qb_py=T['team_pass_yds_pg']*vol; qb_ptd=TD.sum(1)
    else:
        qb_py=T['team_pass_yds_pg']*vol; qb_ptd=rng.poisson(np.clip(T['team_pass_td_pg']*vol,0,None))
    # ---- rushing (RB/QB/WR with carries) ----
    ru=pp[(pp.team==team)&(pp.carry_share>0)].copy()
    if len(ru):
        csh=ru['carry_share'].values; csh=csh/csh.sum()
        ypc=np.clip(np.nan_to_num(ru['ypc'].values,nan=4.2),2,7); rtd=np.clip(np.nan_to_num(ru['rush_td_rate'].values,nan=.03),.002,.15)
        volr=np.exp(0.18*rng.normal(0,1,n)-0.5*0.18**2)   # rushing less volatile, ~script independent
        Wc=rng.dirichlet(max(K,10)*csh,size=n)
        pnr=np.exp(SPR*rng.normal(0,1,(n,len(csh)))-0.5*SPR**2)
        ruy=Wc*(T['team_rush_yds_pg']*volr)[:,None]*pnr
        cs=csh*rtd; cs/=cs.sum(); rTD=rng.poisson(np.clip(cs[None,:]*(T['team_rush_td_pg']*volr)[:,None],0,None))
        rudk=ruy*0.1+rTD*6+3.0*(ruy>=100)              # DK +3 bonus for 100+ rushing yards (per sim, per rusher)
        for i,nm in enumerate(ru['name'].values): out[nm]=out.get(nm,0)+rudk[:,i]
    # ---- QB ----
    qrow=pp[(pp.team==team)&(pp.role=='QB')]
    if len(qrow):
        q=qrow.iloc[0]; qint=rng.poisson(0.65,n)
        qcar=q['carry_pg']; qruy=qcar*q['ypc']*np.exp(0.4*rng.normal(0,1,n)-0.08); qrtd=rng.poisson(np.clip(qcar*q['rush_td_rate'],0,None),n)  # size=n: draw per-sim, not once (was scalar -> zeroed the QB rush-TD tail)
        assert np.ndim(qrtd)==1 and len(qrtd)==n, "TRIPWIRE: qrtd collapsed to a scalar (a size=n was dropped) — this silently zeroes the QB rush-TD ceiling while the mean stays calibrated. See SIM_DEEP_AUDIT.md."
        qdk=qb_py*0.04+qb_ptd*4-qint+qruy*0.1+qrtd*6+3.0*(qb_py>=300)+3.0*(qruy>=100)  # DK +3 bonuses: 300+ pass yds, 100+ QB rush yds
        out[q['name']]=out.get(q['name'],0)+qdk
    # ---- calibrate each to Clay mean (linear scale: keeps CV & corr) ----
    for nm in list(out):
        cm=clay.get(nm,np.nan); rm=out[nm].mean()
        if cm==cm and rm>0.5: out[nm]=out[nm]*(cm/rm)
    return out

# build distribution table for all players
rng=np.random.default_rng(3); N=12000
rows=[]
for team in tp.index:
    g=gen_team(team,N,rng.normal(0,1,N),rng)
    for nm,arr in g.items():
        rows.append(dict(name=nm,team=team,mean=arr.mean(),cv=arr.std()/max(arr.mean(),.1),
            p50=np.percentile(arr,50),p85=np.percentile(arr,85),p95=np.percentile(arr,95),
            spike_pct=(arr>=1.5*arr.mean()).mean()))
dist=pd.DataFrame(rows).merge(pp[['name','pos']],on='name',how='left').sort_values('mean',ascending=False)
dist.to_csv('player_sim_distributions.csv',index=False)
print("per-player sim distributions:",len(dist))
print("\n=== top 14 by sim mean (calibrated to Clay) ===")
print(dist.head(14)[['name','team','pos','mean','p50','p85','p95','cv']].to_string(index=False,
   formatters={c:(lambda x:f'{x:.1f}') for c in ['mean','p50','p85','p95']}|{'cv':lambda x:f'{x:.2f}'}))
# re-validate correlation on calibrated output
def cc(team,a,b):
    g=gen_team(team,8000,rng.normal(0,1,8000),rng)
    return np.corrcoef(g[a],g[b])[0,1] if a in g and b in g else float('nan')
chase="Ja'Marr Chase"
print("\n=== correlation still holds post-calibration ===")
print("  PHI Hurts-DeVonta: %.3f"%cc('PHI','Jalen Hurts','DeVonta Smith'))
print("  CIN Burrow-Chase:  %.3f"%cc('CIN','Joe Burrow',chase))
print("  LAR Stafford-Nacua:%.3f"%cc('LAR','Matthew Stafford','Puka Nacua'))
