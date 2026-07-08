#!/usr/bin/env python3
"""Phase 1 ingestion: enrich features.csv/json with NFL-master FP/2025 charting
(man/zone efficiency, aDOT, run-type zone/gap, QB sack%/pressure, defense coverage tendency)
and the ffdataroma team feeds (real weekly Vegas W15-17, OL blocking, pace, PA/motion, vacated)."""
import core, pandas as pd, glob, os, json, csv, numpy as np, re
NFL=core.find_data('NFL-master','FP','2025')
FF=core.find_data('ffdataroma_draft_guide_export','ffdataroma','csv')
fn=core.fn; nt=core.norm_team
MAN=['Cover 0','Cover 1','Man Cover 2']; ZONE=['Cover 2','Cover 3','Cover 4','Cover 6']
FULL2AB={'cardinals':'ARI','falcons':'ATL','ravens':'BAL','bills':'BUF','panthers':'CAR','bears':'CHI','bengals':'CIN','browns':'CLE','cowboys':'DAL','broncos':'DEN','lions':'DET','packers':'GB','texans':'HOU','colts':'IND','jaguars':'JAX','chiefs':'KC','chargers':'LAC','rams':'LAR','raiders':'LV','dolphins':'MIA','vikings':'MIN','patriots':'NE','saints':'NO','giants':'NYG','jets':'NYJ','eagles':'PHI','steelers':'PIT','seahawks':'SEA','49ers':'SF','niners':'SF','buccaneers':'TB','titans':'TEN','commanders':'WAS','washington':'WAS','football team':'WAS'}
def pnum(v):
    m=re.search(r'-?\d+\.?\d*',str(v)); return float(m.group()) if m else None
def ab(x):
    x=re.sub(r'^\d+(?=[\s.\)\]:,\-]|$)','',str(x).strip())   # strip a leading RANK number (digits then a separator/end), never digits glued to letters (protects "49ers" -> SF; was corrupting it to "ers")
    if nt(x) in {'ARI','ATL','BAL','BUF','CAR','CHI','CIN','CLE','DAL','DEN','DET','GB','HOU','IND','JAX','KC','LAC','LAR','LV','MIA','MIN','NE','NO','NYG','NYJ','PHI','PIT','SEA','SF','TB','TEN','WAS'}: return nt(x)
    xl=x.lower()
    for k,v in FULL2AB.items():
        if k in xl: return v
    return nt(x)
def loadcat(folder,sub,files):
    fr=[]
    for c in files:
        p=f'{NFL}/{folder}/{sub}/{c}.csv'
        if os.path.exists(p):
            d=pd.read_csv(p); d['_c']=c; fr.append(d)
    return pd.concat(fr,ignore_index=True) if fr else pd.DataFrame()
# ---------- receiving coverage profile (WR/TE) ----------
rec=loadcat('Receiving','CoverageType',MAN+ZONE); recprof={}
if len(rec):
    if 'aDOT' not in rec.columns:
        rec['aDOT']=(pd.to_numeric(rec.get('AY'),errors='coerce')/pd.to_numeric(rec.get('TGT'),errors='coerce')).replace([np.inf,-np.inf],np.nan).fillna(0) if ('AY' in rec.columns and 'TGT' in rec.columns) else 0
    rec['_man']=rec['_c'].isin(MAN)
    for k,g in rec.groupby(rec['Name'].map(fn)):
        m=g[g._man]; z=g[~g._man]; mr,zr=m['RTE'].sum(),z['RTE'].sum(); rte=g['RTE'].sum()
        ym=m['YDS'].sum()/mr if mr else None; yz=z['YDS'].sum()/zr if zr else None
        recprof[k]={'yprr_man':round(ym,2) if ym else None,'yprr_zone':round(yz,2) if yz else None,
            'man_route_sh':round(mr/(mr+zr)*100,1) if (mr+zr) else None,
            'adot25':round((g['aDOT']*g['RTE']).sum()/rte,1) if rte else None,
            'man_zone_delta':round(ym-yz,2) if (ym and yz) else None}
# ---------- QB pressure (sack%) ----------
qb=pd.concat([pd.read_csv(f) for f in glob.glob(f'{NFL}/Passing/CoverageType/*.csv')],ignore_index=True); qbprof={}
if 'YPA' not in qb.columns and 'Y/A' in qb.columns: qb['YPA']=pd.to_numeric(qb['Y/A'],errors='coerce')
_has_sack='SACK' in qb.columns; _has_ypa='YPA' in qb.columns
for k,g in qb.groupby(qb['Name'].map(fn)):
    db=g['DB'].sum(); qbprof[k]={'sack_pct25':(round(g['SACK'].sum()/db*100,1) if (db and _has_sack) else None),
        'ypa25':(round((g['YPA']*g['DB']).sum()/db,1) if (db and _has_ypa) else None)}
# ---------- RB run-type zone/gap ----------
ZR=['Inside Zone','Outside Zone']; rt=pd.concat([pd.read_csv(f).assign(_rt=os.path.basename(f)[:-4]) for f in glob.glob(f'{NFL}/Rushing/RunType/*.csv')],ignore_index=True); rbprof={}
for _c in ['Success %','STUFF %']:
    if _c not in rt.columns: rt[_c]=np.nan
for k,g in rt.groupby(rt['Name'].map(fn)):
    z=g[g._rt.isin(ZR)]; gp=g[~g._rt.isin(ZR)]; za,ga=z['ATT'].sum(),gp['ATT'].sum(); tot=g['ATT'].sum()
    rbprof[k]={'zone_run_sh':round(za/(za+ga)*100,1) if (za+ga) else None,
        'zone_succ':round((z['Success %']*z['ATT']).sum()/za,1) if za else None,
        'gap_succ':round((gp['Success %']*gp['ATT']).sum()/ga,1) if ga else None,
        'stuff_pct':round((g['STUFF %']*g['ATT']).sum()/tot,1) if tot else None}
# ---------- defense coverage tendency (per team) ----------
pdf=loadcat('PassingDef','CoverageType',MAN+ZONE); defcov={}
if len(pdf):
    pdf['_man']=pdf['_c'].isin(MAN); pdf['ab']=pdf['Team Name'].map(ab)
    for t,g in pdf.groupby('ab'):
        db=g['DB'].sum(); md=g[g._man]['DB'].sum()
        defcov[t]={'def_man_rate':round(md/db*100,1) if db else None,'def_sack_rate':round(g['SACK'].sum()/db*100,1) if db else None}
if defcov: pd.DataFrame([{'team':t,**v} for t,v in defcov.items()]).to_csv(core.P('defense_coverage.csv'),index=False)
# ---------- ffdataroma team feeds ----------
def rd(f): return pd.read_csv(f'{FF}/{f}.csv')
veg=rd('weekly-vegas-lines'); veg['team']=veg.team.map(nt)
VEG={}
for _,r in veg.iterrows():
    VEG.setdefault(r['team'],{})[int(r['week'])]={'total':r['total'],'spread':r['spread'],'imp':r['teamImplied']}
ol_p=rd('ol-rankings__pass-blocking'); ol_p['ab']=ol_p.Team.map(ab); OLP={r['ab']:pnum(r['Win Rate %']) for _,r in ol_p.iterrows()}
ol_r=rd('ol-rankings__run-blocking'); ol_r['ab']=ol_r.Team.map(ab); OLR={r['ab']:pnum(r['Win Rate %']) for _,r in ol_r.iterrows()}
dr=rd('def-rankings'); dr['ab']=dr.Team.map(ab); PDEF={r['ab']:r['Pass Def Tier'] for _,r in dr.iterrows()}; RDEF={r['ab']:r['Run Def Tier'] for _,r in dr.iterrows()}
pc=rd('pass-catcher-offenses'); pc['ab']=pc.Team.map(ab); PC={r['ab']:(pnum(r.iloc[3]),pnum(r.iloc[4])) for _,r in pc.iterrows()}  # PA, motion
pace=rd('pace-stats'); pace['ab']=pace.Team.map(ab); PACE={r['ab']:pnum(r.iloc[3]) for _,r in pace.iterrows()}  # plays/game
vac=rd('vacated-targets'); vac['ab']=vac.team.map(nt); VAC={r['ab']:r['vac_tgt_total'] for _,r in vac.iterrows()}
# ---------- merge onto feature spine ----------
feats=list(csv.DictReader(open(core.P('features.csv'),encoding='utf-8')))
def g3(d,k): 
    v=d.get(k); return None if v is None or (isinstance(v,float) and pd.isna(v)) else v
n_rec=n_rb=n_qb=0
for f in feats:
    k=fn(f['name']); tm=nt(f['team']); pos=f['pos']
    rp=recprof.get(k); 
    if rp and pos in ('WR','TE'):
        n_rec+=1
        for kk in ('yprr_man','yprr_zone','man_route_sh','adot25','man_zone_delta'): f[kk]=rp[kk]
    rb=rbprof.get(k)
    if rb and pos=='RB':
        n_rb+=1
        for kk in ('zone_run_sh','zone_succ','gap_succ','stuff_pct'): f[kk]=rb[kk]
    q=qbprof.get(k)
    if q and pos=='QB':
        n_qb+=1; f['sack_pct25']=q['sack_pct25']; f['ypa25']=q['ypa25']
    # team feeds
    f['ol_pass_winrate']=g3(OLP,tm); f['ol_run_winrate']=g3(OLR,tm)
    f['opp_pass_def_tier']=g3(PDEF, nt(f.get('w15') or '')); f['team_run_def_tier']=g3(RDEF,tm)
    if PC.get(tm): f['team_play_action']=PC[tm][0]; f['team_motion']=PC[tm][1]
    f['team_plays_g']=g3(PACE,tm); f['team_vacated_tgt']=g3(VAC,tm)
    # real Vegas for ceiling weeks
    for wk,lab in [(15,'w15'),(16,'w16'),(17,'w17')]:
        vv=VEG.get(tm,{}).get(wk)
        if vv: f['vegas_%s_total'%lab]=vv['total']; f['vegas_%s_imp'%lab]=vv['imp']; f['vegas_%s_spread'%lab]=vv['spread']
    # opponent coverage tendency for W15
    oc=defcov.get(nt(f.get('w15') or ''))
    if oc: f['opp_w15_man_rate']=oc['def_man_rate']
# write
cols=[]
for f in feats:
    for c in f: 
        if c not in cols: cols.append(c)
with open(core.P('features.csv'),'w',newline='',encoding='utf-8') as fh:
    w=csv.DictWriter(fh,fieldnames=cols); w.writeheader()
    for f in feats: w.writerow(f)
core.safe_json_dump({'meta':{'n':len(feats),'cols':cols,'enriched':'NFL-master FP/2025 + ffdataroma'},'players':feats}, core.P('features.json'))
print("enriched features: %d cols | rec-coverage matched %d, RB run-type %d, QB pressure %d"%(len(cols),n_rec,n_rb,n_qb))
print("Vegas teams:",len(VEG),"| OL teams:",len(OLP),"| def coverage teams:",len(defcov))
# spot checks
import json as J
d={fn(f['name']):f for f in feats}
for nm in ["Puka Nacua","Amon-Ra St. Brown","Bijan Robinson","Derrick Henry","Joe Burrow"]:
    f=d.get(fn(nm),{})
    print(" %-20s YPRRman=%s YPRRzone=%s d=%s aDOT=%s | zoneRun%%=%s zoneSucc=%s stuff=%s | sack%%=%s | OLpass=%s vegasW17tot=%s oppW15manRate=%s"%(
        nm,f.get('yprr_man'),f.get('yprr_zone'),f.get('man_zone_delta'),f.get('adot25'),f.get('zone_run_sh'),f.get('zone_succ'),f.get('stuff_pct'),f.get('sack_pct25'),f.get('ol_pass_winrate'),f.get('vegas_w17_total'),f.get('opp_w15_man_rate')))
