#!/usr/bin/env python3
"""Shared core for the Best Ball / DFS toolkit: ONE canonical name->pid join, ONE team
normalization, NaN-safe atomic JSON IO. All modules import from here (kills the 5 duplicate fn()/norm_team copies)."""
import os,re,json,math,tempfile,collections,difflib
import pandas as pd
HERE=os.path.dirname(os.path.abspath(__file__)); PIPE=os.path.join(HERE,'pipeline')
def P(f): return os.path.join(HERE,f)
def PP(f): return os.path.join(PIPE,f)
DL=os.path.dirname(HERE)  # the user's Downloads folder (the repo's parent)
def find_data(*rel):
    """Resolve a data path that lives near the repo, robust to layout: repo-inside-Downloads
    (the user's machine) vs repo-beside-Downloads (a sandbox mount). Returns the first existing
    candidate, else the Downloads-relative guess. Replaces the stale hardcoded sandbox paths."""
    for c in (os.path.join(DL,*rel), os.path.join(DL,'Downloads',*rel), os.path.join(HERE,*rel)):
        if os.path.exists(c): return c
    return os.path.join(DL,*rel)
TMAP={'LA':'LAR','JAC':'JAX','WSH':'WAS','ARZ':'ARI','GNB':'GB','KAN':'KC','SFO':'SF','TAM':'TB','NWE':'NE','NOR':'NO'}
def norm_team(t): t=(str(t) if t is not None else '').strip(); return TMAP.get(t,t)
def fn(n):
    n=str(n).strip().lower(); n=re.sub(r'\s+(jr|sr|ii|iii|iv|v)\.?$','',n)
    n=n.replace('.','').replace("'","").replace('-',' '); return ' '.join(n.split())
# --- canonical team mapping: full name OR alias OR code -> code. Replaces 16 copy-pasted maps. ---
FULL2ABBR={'Arizona Cardinals':'ARI','Atlanta Falcons':'ATL','Baltimore Ravens':'BAL','Buffalo Bills':'BUF','Carolina Panthers':'CAR','Chicago Bears':'CHI','Cincinnati Bengals':'CIN','Cleveland Browns':'CLE','Dallas Cowboys':'DAL','Denver Broncos':'DEN','Detroit Lions':'DET','Green Bay Packers':'GB','Houston Texans':'HOU','Indianapolis Colts':'IND','Jacksonville Jaguars':'JAX','Kansas City Chiefs':'KC','Los Angeles Chargers':'LAC','Los Angeles Rams':'LAR','Las Vegas Raiders':'LV','Miami Dolphins':'MIA','Minnesota Vikings':'MIN','New England Patriots':'NE','New Orleans Saints':'NO','New York Giants':'NYG','New York Jets':'NYJ','Philadelphia Eagles':'PHI','Pittsburgh Steelers':'PIT','Seattle Seahawks':'SEA','San Francisco 49ers':'SF','Tampa Bay Buccaneers':'TB','Tennessee Titans':'TEN','Washington Commanders':'WAS'}
def team_abbr(x):
    """Full team name OR alias OR code -> canonical code (ARI, KC, ...). One source of truth."""
    x=(str(x) if x is not None else '').strip()
    return FULL2ABBR.get(x) or norm_team(x)
import glob as _glob
def latest(*patterns):
    """Most-recently-MODIFIED file matching any pattern. Robust vs alphabetical glob sort
    (which picked 'X.csv' over 'X (2).csv' = the OLDER file). Replaces the 3 copied _latest()."""
    hits=[h for q in patterns for h in _glob.glob(q)]
    return max(hits, key=os.path.getmtime) if hits else (patterns[0] if patterns else None)
def _clean(o):
    if isinstance(o,float): return None if (math.isnan(o) or math.isinf(o)) else o
    if isinstance(o,dict): return {k:_clean(v) for k,v in o.items()}
    if isinstance(o,(list,tuple)): return [_clean(v) for v in o]
    return o
def safe_json_dump(obj,path,indent=0):
    """NaN/Inf -> null, atomic write (tmp+rename) so a crash never leaves a truncated file."""
    obj=_clean(obj); d=os.path.dirname(path) or '.'
    fd,tmp=tempfile.mkstemp(dir=d,suffix='.tmp')
    with os.fdopen(fd,'w',encoding='utf-8') as f: json.dump(obj,f,ensure_ascii=False,allow_nan=False,indent=indent)
    os.replace(tmp,path)
def build_usage_index():
    """2025 PBP aggregates per pid + a (surname,initial) index + usage shares. Built ONCE, reused by all."""
    g=pd.read_parquet(PP('player_games.parquet')); g25=g[g.season==2025].copy()
    ag=g25.groupby('pid').agg(name=('name','first'),team=('team',lambda s:s.mode().iloc[0] if len(s.mode()) else s.iloc[0]),
        g=('week','count'),tgt=('targets','sum'),rec=('rec','sum'),recyd=('rec_yds','sum'),air=('air_yds','sum'),
        car=('carries','sum'),ruyd=('rush_yds','sum'),pa=('pass_att','sum'),rtd=('rush_td','sum'),retd=('rec_td','sum'),
        dkmean=('dk','mean'),dkmax=('dk','max'),dkstd=('dk','std')).reset_index()
    ag['team']=ag['team'].map(norm_team); ag['adot']=(ag.air/ag.tgt).where(ag.tgt>0)
    for c,s in [('tgt_pg','tgt'),('car_pg','car'),('rec_pg','rec'),('recyd_pg','recyd'),('rushyd_pg','ruyd')]: ag[c]=ag[s]/ag.g
    ag['td_pg']=(ag.rtd+ag.retd)/ag.g
    def ipos(r): return 'QB' if r.pa>=100 else ('RB' if (r.car>=60 and r.car>=r.rec) else 'WRTE')
    ag['ipos']=ag.apply(ipos,axis=1)
    IDX=collections.defaultdict(list)
    for _,r in ag.iterrows():
        nm=str(r['name']).replace('.',' ').replace("'",' ').lower().split()
        if len(nm)>=2: IDX[(nm[-1],nm[0][0])].append(r)
    us=pd.read_parquet(PP('usage_shares.parquet')); us=us[us.season==2025]
    SH={m:{p:(mn,cv) for p,mn,cv in zip(s.pid,s['mean'],s['cv'])} for m,s in [(m,us[us.metric==m]) for m in ('tgt_share','carry_share')]}
    return ag,IDX,SH
def _full(s): s=str(s).replace('.',' ').replace("'",' ').lower(); return ' '.join(s.split())
def match_usage(bname,pos,tm,IDX):
    """THE canonical join (pos-strict + name-similarity + team tiebreak). Fixes A.J.Brown=Amon-Ra,
    Jeremiyah Love=Jordan Love collisions. Returns the agg row or None (no guess)."""
    parts=fn(bname).split()
    if len(parts)<2: return None
    c=IDX.get((parts[-1],parts[0][0]),[])
    if not c: return None
    posg='QB' if pos=='QB' else ('RB' if pos=='RB' else 'WRTE')
    cc=[x for x in c if x['ipos']==posg]
    if not cc:
        same=[x for x in c if x['team']==tm]; return same[0] if len(same)==1 else None
    if len(cc)==1: return cc[0]
    bfull=fn(bname)
    def sc(x): return (1 if x['team']==tm else 0)+difflib.SequenceMatcher(None,bfull,_full(x['name'])).ratio()
    r=sorted(cc,key=sc,reverse=True)
    if len(r)>1 and r[0]['team']!=tm and r[1]['team']!=tm and abs(sc(r[0])-sc(r[1]))<0.08: return None
    return r[0]
