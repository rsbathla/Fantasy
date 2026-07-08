#!/usr/bin/env python3
"""Grounded per-team 2026 analytics across ALL layers -> team_review_data.json."""
import json,re,os,csv,collections
import pandas as pd, numpy as np
HERE=os.path.dirname(os.path.abspath(__file__)); PIPE=os.path.join(HERE,'pipeline')
def P(f): return os.path.join(HERE,f)
def PP(f): return os.path.join(PIPE,f)
def fn(n):
    n=str(n).strip().lower(); n=re.sub(r'\s+(jr|sr|ii|iii|iv|v)\.?$','',n); n=n.replace('.','').replace("'","").replace('-',' '); return ' '.join(n.split())
def rows(f):
    p=P(f); return list(csv.DictReader(open(p,encoding='utf-8'))) if os.path.exists(p) else []
TEAMS={'ARI':'Arizona Cardinals','ATL':'Atlanta Falcons','BAL':'Baltimore Ravens','BUF':'Buffalo Bills','CAR':'Carolina Panthers','CHI':'Chicago Bears','CIN':'Cincinnati Bengals','CLE':'Cleveland Browns','DAL':'Dallas Cowboys','DEN':'Denver Broncos','DET':'Detroit Lions','GB':'Green Bay Packers','HOU':'Houston Texans','IND':'Indianapolis Colts','JAX':'Jacksonville Jaguars','KC':'Kansas City Chiefs','LAC':'Los Angeles Chargers','LAR':'Los Angeles Rams','LV':'Las Vegas Raiders','MIA':'Miami Dolphins','MIN':'Minnesota Vikings','NE':'New England Patriots','NO':'New Orleans Saints','NYG':'New York Giants','NYJ':'New York Jets','PHI':'Philadelphia Eagles','PIT':'Pittsburgh Steelers','SEA':'Seattle Seahawks','SF':'San Francisco 49ers','TB':'Tampa Bay Buccaneers','TEN':'Tennessee Titans','WAS':'Washington Commanders'}
TMAP={'LA':'LAR','JAC':'JAX','WSH':'WAS','ARZ':'ARI','GNB':'GB','KAN':'KC','SFO':'SF','TAM':'TB','NWE':'NE','NOR':'NO'}
def norm_team(t): t=(t or '').strip(); return TMAP.get(t,t)
# team script
tp=pd.read_csv(PP('layer2_team_params.csv')); tp['team']=tp['team'].map(norm_team)
tp['plays_pg']=tp.team_pass_att_pg+tp.team_carries_pg
tp['pass_rate']=tp.team_pass_att_pg/tp.plays_pg
tp['total_td']=tp.team_pass_td_pg+tp.team_rush_td_pg
def ranks(col,asc=False): r=tp[col].rank(ascending=asc,method='min'); return {t:int(v) for t,v in zip(tp.team,r)}
RK={c:ranks(c) for c in ['team_pass_att_pg','pass_rate','team_pass_yds_pg','team_carries_pg','team_rush_yds_pg','total_td','plays_pg']}
TS={r.team:r for _,r in tp.iterrows()}
LEAGUE={'plays':tp.plays_pg.mean(),'passatt':tp.team_pass_att_pg.mean(),'passrate':tp.pass_rate.mean()*100,'td':tp.total_td.mean(),'passyd':tp.team_pass_yds_pg.mean(),'rushyd':tp.team_rush_yds_pg.mean()}
# 2025 usage by pid
g=pd.read_parquet(PP('player_games.parquet')); g25=g[g.season==2025].copy()
ag=g25.groupby('pid').agg(name=('name','first'),team=('team',lambda s:s.mode().iloc[0] if len(s.mode()) else s.iloc[0]),
    g=('week','count'),tgt=('targets','sum'),rec=('rec','sum'),recyd=('rec_yds','sum'),air=('air_yds','sum'),
    car=('carries','sum'),ruyd=('rush_yds','sum'),pa=('pass_att','sum'),dkmean=('dk','mean'),dkmax=('dk','max')).reset_index()
ag['adot']=(ag.air/ag.tgt).where(ag.tgt>0)
ag['tgt_pg']=ag.tgt/ag.g; ag['car_pg']=ag.car/ag.g; ag['recyd_pg']=ag.recyd/ag.g; ag['rec_pg']=ag.rec/ag.g; ag['rushyd_pg']=ag.ruyd/ag.g; ag['pa_pg']=ag.pa/ag.g
def ipos(r): return 'QB' if r.pa>=100 else ('RB' if (r.car>=60 and r.car>=r.rec) else 'WRTE')
ag['team']=ag['team'].map(norm_team)
ag['ipos']=ag.apply(ipos,axis=1)
us=pd.read_parquet(PP('usage_shares.parquet')); us=us[(us.season==2025)&(us.metric=='tgt_share')]
TSHpid={p:(m,c) for p,m,c in zip(us.pid,us['mean'],us['cv'])}
IDX=collections.defaultdict(list)
for _,r in ag.iterrows():
    # H2 FIX: hyphen->space (as core.build_usage_index does) so hyphenated surnames key on the TRUE last
    # token. Without it the index stored 'smith-njigba' while the lookup asks for 'njigba' -> silent miss
    # (Jaxon Smith-Njigba ADP 5.4, Croskey-Merritt, Smith-Schuster, Lambert-Smith, Westbrook-Ikhine).
    nm=str(r['name']).replace('.',' ').replace("'",' ').replace('-',' ').strip().lower().split()
    if len(nm)>=2: IDX[(nm[-1],nm[0][0])].append(r)
import difflib
def _full(s): s=str(s).replace('.',' ').replace("'",' ').lower(); return ' '.join(s.split())
def match_usage(bname,pos,tm):
    parts=fn(bname).split()
    if len(parts)<2: return None
    c=IDX.get((parts[-1],parts[0][0]),[])
    if not c: return None
    posg='QB' if pos=='QB' else ('RB' if pos=='RB' else 'WRTE')
    cc=[x for x in c if x['ipos']==posg]
    if not cc:                                   # no same-position candidate
        same=[x for x in c if x['team']==tm]     # recover only if exactly one shares the 2026 team
        return same[0] if len(same)==1 else None
    if len(cc)==1: return cc[0]
    bfull=fn(bname)
    def sc(x): return (1 if x['team']==tm else 0)+difflib.SequenceMatcher(None,bfull,_full(x['name'])).ratio()
    r=sorted(cc,key=sc,reverse=True)
    if len(r)>1 and r[0]['team']!=tm and r[1]['team']!=tm and abs(sc(r[0])-sc(r[1]))<0.08: return None
    return r[0]
# sim + qual
sd=pd.read_csv(PP('player_sim_distributions.csv')); SIM={fn(n):r for n,r in zip(sd.name,sd.to_dict('records'))}
ADPTEAM={fn(r['Name']):norm_team(r.get('Team')) for r in rows('dk_adp.csv')}
QS={fn(r['name']):r for r in rows('qual_summary.csv')}
VID={fn(r['name']):r['video_note'] for r in rows('video_notes.csv') if r.get('video_note')}
BB={fn(r['name']):r['bestball_note'] for r in rows('bestball_notes.csv') if r.get('bestball_note')}
OV={}
for r in rows('overlays.csv'): OV.setdefault(fn(r['name']),[]).append('%s: %s'%(r.get('type','').strip(),r.get('note','').strip()))
TN={norm_team(r['team']):r['team_note'] for r in rows('team_notes.csv') if r.get('team_note')}
# 2025 team actual volume + departures (vacated opportunity)
ta=g25.groupby('team').agg(wk=('week','nunique'),pa=('pass_att','sum'),car=('carries','sum')).reset_index()
TA={r['team']:(r['pa']/r['wk'],r['car']/r['wk']) for _,r in ta.iterrows()}
PIDNAME={r['pid']:r['name'] for _,r in ag.iterrows()}; PIDT25={r['pid']:r['team'] for _,r in ag.iterrows()}
sp=rows('draft_board_signals.csv')
proj=sorted([(fn(r['name']),float(r['proj_pg'])) for r in sp if r.get('proj_pg')],key=lambda x:-x[1])
REG={k:i+1 for i,(k,v) in enumerate(proj)}
def F(x): 
    try: return round(float(x),1)
    except: return None
MATCHEDPID={}
teams={}
for r in sp:
    nm=r['name']; k=fn(nm); tm=ADPTEAM.get(k) or norm_team(r.get('team'))
    if not tm: continue
    u=match_usage(nm,r.get('pos'),tm); sim=SIM.get(k,{}); tsh=TSHpid.get(u['pid']) if u is not None else None
    if u is not None: MATCHEDPID[u['pid']]=tm
    pl={'name':nm,'pos':r.get('pos'),'adp':F(r.get('adp')),'rk':int(float(r['merged_rank'])) if r.get('merged_rank') else None,
        'p95':round(float(r['p95'])) if r.get('p95') else None,'spike':round(float(r['spike'])*100,1) if r.get('spike') else None,
        'cv':round(float(r['cv']),2) if r.get('cv') else None,'adv':round(float(r['adv_pct'])*100) if r.get('adv_pct') else None,
        'reg':REG.get(k),'bye':int(float(r['bye'])) if r.get('bye') else None,
        'w15':r.get('w15_opp'),'w16':r.get('w16_opp'),'w17':r.get('w17_game'),'tl':int(float(r['w17_blowup_rank'])) if r.get('w17_blowup_rank') else None,
        'qsum':(QS.get(k) or {}).get('summary','')[:260],'vid':VID.get(k,'')[:220],'bb':BB.get(k,'')[:220],'ov':OV.get(k,[]),'proj':F(r.get('proj_pg'))}
    if u is not None:
        pl.update({'u_g':int(u['g']),'u_tgtpg':F(u['tgt_pg']),'u_adot':F(u['adot']) if pd.notna(u['adot']) else None,
            'u_carpg':F(u['car_pg']),'u_recydpg':F(u['recyd_pg']),'u_recpg':F(u['rec_pg']),'u_rushydpg':F(u['rushyd_pg']),
            'u_papg':F(u['pa_pg']),'u_dkmean':F(u['dkmean']),'u_dkmax':F(u['dkmax']),
            'tgtshare':round(tsh[0]*100,1) if tsh else None,'tgtshare_cv':round(tsh[1],2) if tsh and pd.notna(tsh[1]) else None})
        pl['u_team25']=u['team']; pl['mover']=(u['team']!=tm)
        if pl.get('proj') is not None and pl.get('u_dkmean') is not None: pl['d_pg']=round(pl['proj']-pl['u_dkmean'],1)
    teams.setdefault(tm,[]).append(pl)
TEAMTGT={t:gr.tgt.sum() for t,gr in ag.groupby('team')}     # vacated from actual target COUNTS (bounded)
def _abbr(full):
    import re
    p=[x for x in re.sub(r"\b(jr|sr|ii|iii|iv|v)\b","",str(full).lower()).replace("."," ").replace("'","").split() if x]
    return (p[0][0],p[-1]) if len(p)>=2 else (str(full).lower(),str(full).lower())
# returning 2026 players per team (abbreviated PBP-name key) — used to catch name-collision "departures":
# an abbreviated 2025 name (e.g. "K.Coleman") that matches a RETURNING starter is that starter's usage,
# NOT a departure (fixes Keon vs Kevin Coleman Jr., Jonathan vs J'Mari Taylor). Canonical-join guard.
_RETURNING={tm:{_abbr(p['name']) for p in pls if not p.get('mover')} for tm,pls in teams.items()}
departures=collections.defaultdict(list)
for _,row in ag.iterrows():
    t25=row['team']; tt=TEAMTGT.get(t25,0)
    if not t25 or tt<50 or row['tgt']<1: continue
    share=row['tgt']/tt*100
    if share<4: continue
    if _abbr(row['name']) in _RETURNING.get(t25,()): continue   # collision w/ returning starter -> not a departure
    t26=MATCHEDPID.get(row['pid'])
    if t26!=t25: departures[t25].append((row['name'],round(share,1),t26 or 'gone'))
for kk in departures: departures[kk].sort(key=lambda x:-x[1])
out={}
for tm,pls in teams.items():
    pls.sort(key=lambda x:x['rk'] or 9999); ts=TS.get(tm); script=None
    if ts is not None:
        script={k:(round(float(getattr(ts,a)),b)) for k,a,b in [('pass_att_pg','team_pass_att_pg',1),('pass_yds_pg','team_pass_yds_pg',1),('pass_td_pg','team_pass_td_pg',2),('carries_pg','team_carries_pg',1),('rush_yds_pg','team_rush_yds_pg',1),('rush_td_pg','team_rush_td_pg',2),('plays_pg','plays_pg',1),('total_td','total_td',2)]}
        script['pass_rate']=round(ts.pass_rate*100,1)
        for nk,rc in [('rk_passvol','team_pass_att_pg'),('rk_passrate','pass_rate'),('rk_passyds','team_pass_yds_pg'),('rk_carries','team_carries_pg'),('rk_rushyds','team_rush_yds_pg'),('rk_td','total_td'),('rk_plays','plays_pg')]: script[nk]=RK[rc][tm]
    delta=None
    if tm!='FA':
        ta25=TA.get(tm); deps=departures.get(tm,[])
        delta={'act_pa':round(ta25[0],1) if ta25 else None,'act_car':round(ta25[1],1) if ta25 else None,
               'vac_tgt':round(sum(d[1] for d in deps),1),'departures':deps[:4],
               'arrivals':[(p['name'],p.get('u_team25')) for p in pls if p.get('mover')][:6],
               'rookies':[p['name'] for p in pls if not p.get('u_g') and (p['rk'] or 999)<=200][:6]}
        if script and ta25: delta['d_pa']=round(script['pass_att_pg']-ta25[0],1); delta['d_car']=round(script['carries_pg']-ta25[1],1)
    out[tm]={'team':tm,'name':TEAMS.get(tm,tm),'note':TN.get(tm,''),'script':script,'delta':delta,
        'bye':pls[0]['bye'] if tm!='FA' else None,'w15':pls[0]['w15'] if tm!='FA' else None,'w16':pls[0]['w16'] if tm!='FA' else None,'w17':pls[0]['w17'] if tm!='FA' else None,'tl':pls[0]['tl'] if tm!='FA' else None,
        'players':pls,'nalpha':sum(1 for p in pls if p['p95'] and p['p95']>=33)}
out['_league']=LEAGUE
json.dump(out,open(P('team_review_data.json'),'w',encoding='utf-8'),ensure_ascii=False,indent=0)
print("wrote json bytes:",os.path.getsize(P('team_review_data.json')),"teams:",len([k for k in out if not k.startswith('_')]))
# verify usage join
for tm in ['CIN','BAL','PHI']:
    print("\n%s:"%tm)
    for p in out[tm]['players'][:4]:
        print("  %-20s %s rk%s p95%s | tgtSh %s%%(cv%s) aDOT %s tgt/g %s car/g %s dkmax %s g%s"%(p['name'],p['pos'],p['rk'],p['p95'],p.get('tgtshare'),p.get('tgtshare_cv'),p.get('u_adot'),p.get('u_tgtpg'),p.get('u_carpg'),p.get('u_dkmax'),p.get('u_g')))
