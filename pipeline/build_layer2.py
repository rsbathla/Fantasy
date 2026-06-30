import pandas as pd, numpy as np, re, warnings
warnings.filterwarnings('ignore')
SRC='clay_6_10'   # labeled, swappable mean source

def norm(n):
    if not isinstance(n,str): return None
    n=n.strip().lower(); n=re.sub(r'\s+(jr|sr|ii|iii|iv|v)\.?$','',n)
    n=n.replace("'","").replace('.',' ').replace('-',' '); p=n.split()
    return p[0][0]+'.'+p[-1] if len(p)>=2 else (p[0] if p else None)

clay=pd.read_csv('clay_2026.csv')
clay['key']=clay['name'].map(norm)
clay['g']=clay['g'].replace(0,np.nan).fillna(17)

skill=clay[clay['pos'].isin(['RB','WR','TE'])].copy()
qb=clay[clay['pos']=='QB'].copy()

# ---- TEAM PARAMS: raw-normalized team volume (incl QB rushing) ----
tt=skill.groupby('team').agg(rec_tgt=('targ','sum'), rec_yd=('re_yd','sum'), rec_td=('re_td','sum'),
                             sk_carry=('carry','sum'), sk_ruyd=('ru_yds','sum'), sk_rutd=('ru_td','sum')).reset_index()
tq=qb.groupby('team').agg(qb_patt=('p_att','sum'), qb_pyd=('p_yds','sum'), qb_ptd=('p_td','sum'),
                          qb_int=('int','sum'), qb_carry=('carry','sum'), qb_ruyd=('ru_yds','sum'),
                          qb_rutd=('ru_td','sum')).reset_index()
team=tt.merge(tq,on='team',how='outer').fillna(0)
# team season volumes (use QB pass attempts as canonical team pass volume; targets ~ attempts)
team['team_pass_att']=team['qb_patt']
team['team_pass_yds']=team['qb_pyd']
team['team_pass_td']=team['qb_ptd']
team['team_int']=team['qb_int']
team['team_carries']=team['sk_carry']+team['qb_carry']   # incl QB rushing -> the coherence fix
team['team_rush_yds']=team['sk_ruyd']+team['qb_ruyd']
team['team_rush_td']=team['sk_rutd']+team['qb_rutd']
team['g']=17
for c in ['team_pass_att','team_pass_yds','team_pass_td','team_int','team_carries','team_rush_yds','team_rush_td']:
    team[c+'_pg']=team[c]/team['g']
team_out=team[['team','team_pass_att_pg','team_pass_yds_pg','team_pass_td_pg','team_int_pg',
               'team_carries_pg','team_rush_yds_pg','team_rush_td_pg']].copy()
team_out['source']=SRC
team_out.to_csv('layer2_team_params.csv',index=False)

# ---- WEEKLY CV from Component 1 (measured structural variance) ----
us=pd.read_parquet('usage_shares.parquet')   # has name, season, metric, cv, mean, n
us['key']=us['name'].map(norm)
# take most-recent-season cv per key/metric with n>=6
us=us[us['n']>=6].sort_values('season').drop_duplicates(['key','metric'],keep='last')
cv_t=us[us['metric']=='tgt_share'].set_index('key')['cv'].to_dict()
cv_c=us[us['metric']=='carry_share'].set_index('key')['cv'].to_dict()
# position-archetype fallback CV (median of measured)
pos_cv_t=us[us['metric']=='tgt_share']['cv'].median()
pos_cv_c=us[us['metric']=='carry_share']['cv'].median()

# ---- PLAYER PARAMS ----
rows=[]
for _,r in clay.iterrows():
    pos=r['pos']; tm=r['team']; g=r['g']; k=r['key']
    trow=team[team['team']==tm]
    rec={'name':r['name'],'key':k,'team':tm,'pos':pos,'g':g,'source':SRC,'dk_pg':r['dk_pg']}
    if pos=='QB':
        rec.update(dict(role='QB',
            pass_att_pg=r['p_att']/g, ypa=r['p_yds']/max(r['p_att'],1), comp_rate=r['comp']/max(r['p_att'],1),
            pass_td_rate=r['p_td']/max(r['p_att'],1), int_rate=r['int']/max(r['p_att'],1),
            carry_pg=r['carry']/g, ypc=r['ru_yds']/max(r['carry'],1), rush_td_rate=r['ru_td']/max(r['carry'],1)))
        rec['tgt_share']=0.0; rec['carry_share']=0.0
        rec['cv_tgt']=np.nan; rec['cv_carry']=cv_c.get(k,pos_cv_c)
        rec['var_src_carry']='measured' if k in cv_c else 'archetype'
    else:
        tpa=float(trow['team_pass_att']) if len(trow) and float(trow['team_pass_att'])>0 else np.nan
        tca=float(trow['team_carries']) if len(trow) and float(trow['team_carries'])>0 else np.nan
        # raw-normalized shares (targets/team pass att ; carries/team carries incl QB)
        rec['tgt_share']=r['targ']/tpa if tpa==tpa else 0.0
        rec['carry_share']=r['carry']/tca if tca==tca else 0.0
        rec.update(dict(role=pos,
            catch_rate=r['rec']/max(r['targ'],1), ypt=r['re_yd']/max(r['targ'],1),
            rec_td_per_tgt=r['re_td']/max(r['targ'],1),
            carry_pg=r['carry']/g, ypc=r['ru_yds']/max(r['carry'],1) if r['carry']>0 else 0.0,
            rush_td_rate=r['ru_td']/max(r['carry'],1) if r['carry']>0 else 0.0))
        rec['cv_tgt']=cv_t.get(k,pos_cv_t); rec['cv_carry']=cv_c.get(k,pos_cv_c) if r['carry']>0 else np.nan
        rec['var_src_tgt']='measured' if k in cv_t else 'archetype'
    rows.append(rec)
pp=pd.DataFrame(rows)
pp.to_csv('layer2_player_params.csv',index=False)

# ---- report ----
print(f"Layer 2 built  (source={SRC})")
print(f"  player params: {len(pp)}  | team params: {len(team_out)}")
meas=pp[pp['pos']!='QB']['var_src_tgt'].value_counts().to_dict()
print(f"  WR/RB/TE target-CV source: {meas}  (measured = has nflfastR history; archetype = rookie/mover fallback)")
print(f"  archetype-fallback target CV = {pos_cv_t:.3f} ; carry CV = {pos_cv_c:.3f}")
print("\n  team volume sanity (per game):")
print(f"    pass_att {team_out['team_pass_att_pg'].mean():.1f}  carries {team_out['team_carries_pg'].mean():.1f}  pass_yds {team_out['team_pass_yds_pg'].mean():.0f}  pass_td {team_out['team_pass_td_pg'].mean():.2f}")
print("\n  sample player params:")
cols=['name','team','pos','tgt_share','carry_share','ypt','catch_rate','cv_tgt']
samp=pp[pp['name'].isin(['DeVonta Smith','A.J. Brown','Saquon Barkley','Jaxson Dart','Trey McBride'])]
print(samp[['name','team','pos','tgt_share','carry_share','ypt','cv_tgt']].to_string(index=False,
      formatters={'tgt_share':lambda x:f'{x:.3f}','carry_share':lambda x:f'{x:.3f}','ypt':lambda x:f'{x:.2f}','cv_tgt':lambda x:f'{x:.2f}'}))
