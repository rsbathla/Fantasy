#!/usr/bin/env python3
"""Overfit guardrail: per-signal boom-prediction stability across 2024 vs 2025.
Reconstructs each signal per season from player_games.parquet, joins per-season boom
(base2yr), and reports corr(signal,boom) in BOTH years. A signal that flips sign or
vanishes across years is overfit -> the flags built on it should be dropped/shrunk.
Re-run when 2026 data lands. Verdicts: KEEP (|r|>=.20 both, same sign) / keep-weak /
SHRINK (noise) / DROP (sign flip) / untestable(n<8)."""
import json, re, pandas as pd, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import core
def fn(n): n=str(n).strip().lower(); n=re.sub(r"\s+(jr|sr|ii|iii|iv|v)\.?$","",n); return n.replace('.','').replace("'","").replace('-',' ')
feat={str(p['pid']):((p.get('pos') or '').upper(),fn(p['name'])) for p in json.load(open(core.P('features.json')))['players'] if p.get('pid') is not None}
b2=json.load(open(core.P('boom/base2yr.json'))); g=pd.read_parquet(core.PP('player_games.parquet'))
def sigs(yr):
    d=g[g.season==yr].copy(); d['team']=d.team.map(core.norm_team)
    tt=d.groupby('team').agg(tgt=('targets','sum'),car=('carries','sum')); out={}
    for pid,gr in d.groupby('pid'):
        pid=str(pid)
        if pid not in feat: continue
        pos,nm=feat[pid]; gm=gr.week.nunique()
        if gm<6: continue
        T=tt.loc[gr.team.mode().iloc[0]]; tgt=gr.targets.sum(); car=gr.carries.sum()
        bo=b2.get(nm); gk='g%d'%(yr%100); bk='b%d'%(yr%100)
        if not bo or bo.get(gk,0)<6: continue
        out[pid]={'tgt_share':tgt/T.tgt*100 if T.tgt else 0,'carry_share':car/T.car*100 if T.car else 0,
            'aDOT':gr.air_yds.sum()/tgt if tgt else 0,'ypt':gr.rec_yds.sum()/tgt if tgt else 0,'rec_pg':gr.rec.sum()/gm,
            'td_pg':(gr.rush_td.sum()+gr.rec_td.sum())/gm,'rush_pg':gr.rush_yds.sum()/gm,'pass_att_pg':gr.pass_att.sum()/gm,
            'qb_rush_pg':gr.rush_yds.sum()/gm,'_boom':bo[bk]/bo[gk],'_pos':pos}
    return out
def corr(xs,ys):
    n=len(xs)
    if n<8: return None
    mx=sum(xs)/n;my=sum(ys)/n;sx=sum((x-mx)**2 for x in xs)**.5;sy=sum((y-my)**2 for y in ys)**.5
    return sum((x-mx)*(y-my) for x,y in zip(xs,ys))/(sx*sy) if sx and sy else None
def verdict(a,c):
    if a is None or c is None: return 'untestable'
    if (a>0)!=(c>0): return 'DROP(flip)'
    if abs(a)>=.20 and abs(c)>=.20: return 'KEEP'
    if abs(a)>=.12 and abs(c)>=.12: return 'keep-weak'
    return 'SHRINK(noise)'
if __name__=='__main__':
    s24,s25=sigs(2024),sigs(2025)
    POS={'WR':['tgt_share','aDOT','ypt','rec_pg','td_pg'],'TE':['tgt_share','ypt','rec_pg','td_pg'],
         'RB':['carry_share','rush_pg','rec_pg','td_pg'],'QB':['pass_att_pg','qb_rush_pg','td_pg']}
    for pos,sg in POS.items():
        A=[v for v in s24.values() if v['_pos']==pos];C=[v for v in s25.values() if v['_pos']==pos]
        for s in sg:
            a=corr([x[s] for x in A],[x['_boom'] for x in A]);c=corr([x[s] for x in C],[x['_boom'] for x in C])
            print(f"{pos} {s:13} {a if a is None else round(a,2)} / {c if c is None else round(c,2)}  {verdict(a,c)}")
