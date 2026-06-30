#!/usr/bin/env python3
"""THE feature store: one flat row per board player, integrating every available signal.
All downstream agents (fusion, dfs, gameplan, personnel) consume features.json instead of re-deriving."""
import core, csv, pandas as pd
def num(x):
    try:
        v=float(x); return v
    except: return None
ag,IDX,SH=core.build_usage_index()
adp_team={core.fn(r['Name']):core.norm_team(r.get('Team')) for r in csv.DictReader(open(core.P('dk_adp.csv'),encoding='utf-8'))}
sim={core.fn(r['name']):r for r in csv.DictReader(open(core.PP('player_sim_distributions.csv'),encoding='utf-8'))}
clay={core.fn(r['name']):r for r in csv.DictReader(open(core.PP('clay_2026.csv'),encoding='utf-8'))}
coord=__import__('json').load(open(core.P('coordinator_notes.json'),encoding='utf-8')) if core.os.path.exists(core.P('coordinator_notes.json')) else {}
# team script + ranks (2026)
tp=pd.read_csv(core.PP('layer2_team_params.csv')); tp['team']=tp.team.map(core.norm_team)
tp['plays']=tp.team_pass_att_pg+tp.team_carries_pg; tp['pass_rate']=tp.team_pass_att_pg/tp.plays; tp['total_td']=tp.team_pass_td_pg+tp.team_rush_td_pg
RK={c:{t:int(v) for t,v in zip(tp.team,tp[c].rank(ascending=False,method='min'))} for c in ['team_pass_att_pg','pass_rate','plays','total_td']}
TS={r.team:r for _,r in tp.iterrows()}
# 2026 opponent grid (matchup identity)
sched=pd.read_csv(core.PP('schedule_2026.csv')); sched['Team']=sched['Team'].map(core.norm_team)
OPP={r['Team']:{w:str(r['Week '+str(w)]).replace('@','').replace('vs','').strip() for w in range(1,19)} for _,r in sched.iterrows()}
sp=list(csv.DictReader(open(core.P('draft_board_signals.csv'),encoding='utf-8')))
proj=sorted([(core.fn(r['name']),float(r['proj_pg'])) for r in sp if r.get('proj_pg')],key=lambda x:-x[1]); REG={k:i+1 for i,(k,v) in enumerate(proj)}
rows=[]
for r in sp:
    nm=r['name']; k=core.fn(nm); tm=adp_team.get(k) or core.norm_team(r.get('team'))
    u=core.match_usage(nm,r.get('pos'),tm,IDX); cl=clay.get(k,{}); s=sim.get(k,{}); ts=TS.get(tm)
    pid=u['pid'] if u is not None else None
    f={'name':nm,'pos':r.get('pos'),'team':tm,'pid':pid,
       'adp':num(r.get('adp')),'merged_rank':num(r.get('merged_rank')),
       'proj_pg':num(r.get('proj_pg')) if r.get('proj_pg') else num(cl.get('dk_pg')),
       'p95':num(r.get('p95')),'spike':num(r.get('spike')),'cv':num(r.get('cv')),'adv_pct':num(r.get('adv_pct')),
       'p50':num(s.get('p50')),'p85':num(s.get('p85')),'sim_mean':num(s.get('mean')),'reg_rank':REG.get(k),
       'bye':num(r.get('bye')),'w15':r.get('w15_opp'),'w16':r.get('w16_opp'),'w17':r.get('w17_game'),'tail':num(r.get('w17_blowup_rank')),
       'clay_targ_pct':num(cl.get('targ_pct')),'clay_car_pct':num(cl.get('car_pct')),
       'tm_pass_att':round(float(ts.team_pass_att_pg),1) if ts is not None else None,
       'tm_pass_rate':round(float(ts.pass_rate)*100,1) if ts is not None else None,
       'tm_plays':round(float(ts.plays),1) if ts is not None else None,
       'tm_total_td':round(float(ts.total_td),2) if ts is not None else None,
       'rk_passvol':RK['team_pass_att_pg'].get(tm),'rk_passrate':RK['pass_rate'].get(tm),'rk_td':RK['total_td'].get(tm),
       'opp_w15':OPP.get(tm,{}).get(15),'opp_w16':OPP.get(tm,{}).get(16),'opp_w17':OPP.get(tm,{}).get(17),
       'coord_scheme':(coord.get(tm,[{}])[0].get('q') if coord.get(tm) else None)}
    if u is not None:
        tsh=SH['tgt_share'].get(pid); csh=SH['carry_share'].get(pid)
        f.update({'g25':int(u['g']),
            'tgt_share':round(tsh[0]*100,1) if tsh else None,'tgt_share_cv':round(tsh[1],2) if tsh and pd.notna(tsh[1]) else None,
            'carry_share':round(csh[0]*100,1) if csh else None,'carry_share_cv':round(csh[1],2) if csh and pd.notna(csh[1]) else None,
            'adot':round(float(u['adot']),1) if pd.notna(u['adot']) else None,
            'tgt_pg':round(float(u['tgt_pg']),1),'car_pg':round(float(u['car_pg']),1),'rec_pg':round(float(u['rec_pg']),1),
            'td_pg':round(float(u['td_pg']),2),'dk_mean25':round(float(u['dkmean']),1),'dk_max25':round(float(u['dkmax']),1),
            'team25':u['team'],'mover':bool(u['team']!=tm)})
        if f['proj_pg'] is not None and f.get('dk_mean25') is not None: f['delta_pg']=round(f['proj_pg']-f['dk_mean25'],1)
    rows.append(f)
df=pd.DataFrame(rows); df.to_csv(core.P('features.csv'),index=False)
core.safe_json_dump({'meta':{'n':len(rows),'cols':list(df.columns),'note':'unified feature store - all available signals; coverage/pressure/run-type/directional NOT in source data'},'players':rows}, core.P('features.json'))
print("features rows:",len(rows),"| columns:",len(df.columns))
print("matched usage:",df.pid.notna().sum(),"| carry_share:",df.carry_share.notna().sum() if 'carry_share' in df else 0,"| aDOT:",df.adot.notna().sum() if 'adot' in df else 0,"| td_pg:",df.td_pg.notna().sum() if 'td_pg' in df else 0,"| clay_targ%:",df.clay_targ_pct.notna().sum())
for nmn in ["Ja'Marr Chase","Derrick Henry","A.J. Brown","Bijan Robinson"]:
    x=next((r for r in rows if r['name']==nmn),None)
    if x: print(" %-18s tgt%%=%s carry%%=%s aDOT=%s td/g=%s clayTgt%%=%s clayCar%%=%s oppW17=%s"%(nmn,x.get('tgt_share'),x.get('carry_share'),x.get('adot'),x.get('td_pg'),x.get('clay_targ_pct'),x.get('clay_car_pct'),x.get('opp_w17')))
