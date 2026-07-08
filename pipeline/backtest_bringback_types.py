#!/usr/bin/env python3
"""backtest_bringback_types.py — "which bring-back?" study.

The ceiling calibration (backtest_correlation.py) anchored on QB vs the opposing WR1 — but WR1 is
exactly the bring-back you often can't afford. This measures the sim's QB<->opposing-receiver
correlation under the rules you'd ACTUALLY use, on the real 2026 slate:

  WR1 / WR2 / WR3 / TE1     depth by target share (layer2)
  ANY (tgt-weighted, flat)  bring back "whoever" on the opposing team
  best-matchup (proj, ceil) the opposing pass-catcher your model PROJECTS highest that game
                            (dfs_season_baseline.json — the matchup/funnel layer's own pick)

Correlation is measured at rho=1 (fully-shared reference = today's ceiling); under the wired
rho(total) every definition scales by the SAME rho(total), so the LEVEL comparison here holds at
any total. Run from pipeline/:  python3 backtest_bringback_types.py
"""
import numpy as np, pandas as pd, json, re, os
import warnings; warnings.filterwarnings('ignore')
exec(open('sim_prod.py').read().split("# build distribution")[0])   # gen_team, pp, tp

def _norm(n):
    n=str(n).strip().lower(); n=re.sub(r'\s+(jr|sr|ii|iii|iv|v)\.?$','',n)
    return n.replace('.','').replace("'","").replace('-',' ')
NM={_norm(n):n for n in pp['name']}

# depth chart by target share (layer2)
rec=pp[(pp.role.isin(['WR','TE']))&(pp.tgt_share>0)].copy()
def depth(team):
    d=rec[rec.team==team].sort_values('tgt_share',ascending=False)
    wr=d[d.role=='WR']['name'].tolist(); te=d[d.role=='TE']['name'].tolist()
    return {'WR1':wr[0] if len(wr)>0 else None,'WR2':wr[1] if len(wr)>1 else None,
            'WR3':wr[2] if len(wr)>2 else None,'TE1':te[0] if te else None,
            'ALL':d[['name','tgt_share']].values.tolist()}
DEP={t:depth(t) for t in tp.index}
def qb_of(t):
    q=pp[(pp.team==t)&(pp.role=='QB')]; return q.iloc[0]['name'] if len(q) else None
QB={t:qb_of(t) for t in tp.index}

# best-matchup + game totals from the projection/matchup layer
base=json.load(open('../dfs_season_baseline.json'))['weeks']
BEST={}   # (stack_team, opp_team) -> {'proj':name,'ceil':name,'total':T}  (opp receiver vs stack_team D)
for w,blk in base.items():
    for pl in blk['players']:
        opp=pl.get('opp'); tm=pl.get('team'); pos=pl.get('pos')
        if pos not in ('WR','TE') or not opp: continue
        key=(opp,tm)                     # stacking OPP's QB -> bring back this receiver (tm) vs OPP D
        cn=NM.get(_norm(pl['name']))
        if cn is None: continue
        b=BEST.setdefault(key,{'proj':(-1,None),'ceil':(-1,None),'total':pl.get('total')})
        if (pl.get('proj') or 0)>b['proj'][0]: b['proj']=(pl['proj'],cn)
        if (pl.get('ceil') or 0)>b['ceil'][0]: b['ceil']=(pl['ceil'],cn)

pairs=sorted({tuple(sorted((a,b))) for w,gl in json.load(open('games_by_week.json')).items()
              for a,b in gl if a in tp.index and b in tp.index})
def _c(x,y): return np.nan if (x.std()<1e-9 or y.std()<1e-9) else float(np.corrcoef(x,y)[0,1])

N=8000; rng=np.random.default_rng(303)
acc={k:[] for k in ['WR1','WR2','WR3','TE1','ANY_wt','ANY_flat','best_proj','best_ceil']}
acc_hi={k:[] for k in acc}; acc_lo={k:[] for k in acc}
bm_is_wr1=[]; bm_rank=[]
for a,b in pairs:
    g=rng.normal(0,1,N)                    # rho=1 reference (today's shared shock)
    ga=gen_team(a,N,g,rng); gb=gen_team(b,N,g,rng)
    for stack,opp,out_qb,out_rec in [(a,b,ga,gb),(b,a,gb,ga)]:
        qn=QB[stack]
        if qn not in out_qb: continue
        q=out_qb[qn]; d=DEP[opp]
        tot=BEST.get((stack,opp),{}).get('total')
        hi = tot is not None and tot>45.0; lo = tot is not None and tot<45.0
        def rec_corr(nm): return _c(q,out_rec[nm]) if (nm and nm in out_rec) else np.nan
        vals={'WR1':rec_corr(d['WR1']),'WR2':rec_corr(d['WR2']),'WR3':rec_corr(d['WR3']),'TE1':rec_corr(d['TE1'])}
        # ANY across all opposing pass-catchers present in the sim
        allc=[(nm,sh,rec_corr(nm)) for nm,sh in d['ALL'] if nm in out_rec]
        allc=[(nm,sh,c) for nm,sh,c in allc if c==c]
        if allc:
            cs=np.array([c for _,_,c in allc]); wts=np.array([sh for _,sh,_ in allc])
            vals['ANY_flat']=float(cs.mean()); vals['ANY_wt']=float((cs*wts).sum()/wts.sum())
        bm=BEST.get((stack,opp),{})
        vals['best_proj']=rec_corr(bm.get('proj',(None,None))[1])
        vals['best_ceil']=rec_corr(bm.get('ceil',(None,None))[1])
        # does best-matchup pick the WR1? and what depth rank?
        bpn=bm.get('proj',(None,None))[1]
        if bpn:
            bm_is_wr1.append(1 if bpn==d['WR1'] else 0)
            ranks=[nm for nm,_ in d['ALL']]
            bm_rank.append(ranks.index(bpn)+1 if bpn in ranks else np.nan)
        for k,v in vals.items():
            if v==v:
                acc[k].append(v)
                if hi: acc_hi[k].append(v)
                if lo: acc_lo[k].append(v)

def m(L): return (float(np.mean(L)),len(L)) if L else (float('nan'),0)
print("=== BRING-BACK TYPE COMPARISON (QB vs opposing receiver, rho=1 reference correlation) ===")
print(f"    {len(pairs)} unique 2026 matchups, both directions, n={N}/game\n")
print(f"  {'definition':22s} {'corr':>7} {'vs WR1':>8} {'high-tot':>9} {'low-tot':>8}   note")
order=['WR1','WR2','WR3','TE1','ANY_wt','ANY_flat','best_proj','best_ceil']
notes={'WR1':'the expensive stud (calibration anchor)','WR2':'2nd target share','WR3':'3rd target share',
       'TE1':'the tight end','ANY_wt':'whoever, target-weighted','ANY_flat':'truly any pass-catcher',
       'best_proj':'model top PROJECTION that game','best_ceil':'model top CEILING that game'}
wr1m=m(acc['WR1'])[0]
for k in order:
    mm,n=m(k and acc[k]); him=m(acc_hi[k])[0]; lom=m(acc_lo[k])[0]
    rel=f"{(mm/wr1m-1)*100:+.0f}%" if wr1m else ""
    print(f"  {k:22s} {mm:>7.3f} {rel:>8} {him:>9.3f} {lom:>8.3f}   {notes[k]}")
print(f"\n  best-matchup (by projection) picks the WR1 in {np.nanmean(bm_is_wr1)*100:.0f}% of games; "
      f"mean opposing depth-rank chosen = {np.nanmean(bm_rank):.1f}")
print("\n  NOTE: correlation here is game-ENVIRONMENT structural (target-share loading). The sim does")
print("  NOT add matchup-conditional correlation, so 'best matchup' only differs from WR1 by which")
print("  target-share tier it lands in — the funnel layer boosts the receiver's MEAN, not its corr.")
