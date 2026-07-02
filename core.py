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

# --- ONE fuzzy name resolver (first-name variants: ken/kenneth, cam/cameron, chig/chigoziem). -------
# The ALGORITHM lives here; the CALLER supplies the candidate set (Clay names, sim names, ...), so the
# engine AND the pipeline share one authority with no import cycle. Exact fn() match wins; otherwise,
# among candidates with the SAME last token AND token count, keep first-name-COMPATIBLE ones (+ same
# pos when known) and accept ONLY IF EXACTLY ONE survives -- else None (never an unsafe guess). This
# recovers ken/kenneth, cam/cameron, josh/joshua while rejecting keenan/kaytron, jmari/jonathan.
def _lev(a,b):
    if a==b: return 0
    if len(a)<len(b): a,b=b,a
    prev=list(range(len(b)+1))
    for i,ca in enumerate(a,1):
        cur=[i]+[0]*len(b)
        for j,cb in enumerate(b,1): cur[j]=min(prev[j]+1,cur[j-1]+1,prev[j-1]+(ca!=cb))
        prev=cur
    return prev[-1]
def first_compatible(f1,f2):
    """True iff two first names are likely the same person: prefix (ken/kenneth), shared first 3
    letters (nick/nicholas), or edit distance <= 1. Empty -> False."""
    if not f1 or not f2: return False
    if f1==f2 or f1.startswith(f2) or f2.startswith(f1): return True
    if len(f1)>=3 and len(f2)>=3 and f1[:3]==f2[:3]: return True
    return _lev(f1,f2)<=1
def build_name_index(pairs):
    """pairs: iterable of (display_name, pos|None) from the source you'll join AGAINST. Returns an
    opaque index for resolve(). Built once, reused for every lookup (O(1) exact, O(#same-last-name) fuzzy)."""
    n2d={}; by_last=collections.defaultdict(list); pos_of={}
    for disp,pos in pairs:
        nk=fn(disp)
        if not nk: continue
        n2d.setdefault(nk,disp)
        p=nk.split(); by_last[(len(p),p[-1])].append((nk,disp))
        if pos is not None: pos_of.setdefault(disp,pos)
    return {'n2d':n2d,'by_last':by_last,'pos':pos_of}
def resolve(name,pos,index):
    """Board name -> the matching display name in `index`, or None (no unsafe guess). Safe by design:
    exact fn() match, else same-last-name + same-token-count + first-compatible (+ same pos) + unique."""
    k=fn(name)
    if not k: return None
    if k in index['n2d']: return index['n2d'][k]
    p=k.split()
    cands=index['by_last'].get((len(p),p[-1]),[])
    compat=[disp for nk,disp in cands if first_compatible(p[0],nk.split()[0])]
    if pos is not None: compat=[d for d in compat if index['pos'].get(d)==pos]
    return compat[0] if len(compat)==1 else None

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
        # normalize the index key EXACTLY as fn()/match_usage does -- incl. hyphen->space -- so
        # hyphenated surnames (Smith-Njigba, Valdes-Scantling, ...) key on the true last token and
        # actually match the board side instead of silently missing the usage join.
        nm=str(r['name']).replace('.',' ').replace("'",' ').replace('-',' ').lower().split()
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
    if len(r)>1 and r[0]['team']!=tm and r[1]['team']!=tm and abs(sc(r[0])-sc(r[1]))<0.08:
        # Scores tie and NEITHER candidate is on the board team -> a mover changed teams, so the team
        # tiebreak can't fire (this dropped DJ Moore=CHI-vs-CAR, Mike Evans=TB-vs-CAR). Break the tie by
        # dominant 2025 opportunity: the real fantasy player carries a clear starter-level role. Accept
        # ONLY when that gap is decisive (>=40 opp, >=6 games, >=1.8x the runner-up); else None (no guess).
        # position-aware volume: a WR/TE is defined by TARGETS (using tgt+car here would let a
        # carry-heavy same-name hybrid like Taysom Hill outrank a WR like Tyreek Hill -> false match).
        opp=(lambda x:(x.get('tgt') or 0)) if posg=='WRTE' else (lambda x:(x.get('tgt') or 0)+(x.get('car') or 0))
        rv=sorted(cc,key=opp,reverse=True); top,sec=rv[0],rv[1]
        if opp(top)>=40 and (top.get('g') or 0)>=6 and opp(top)>=1.8*max(opp(sec),1): return top
        return None
    return r[0]
