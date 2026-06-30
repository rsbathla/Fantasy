#!/usr/bin/env python3
"""Ingest SIS DataHub DEFENSE leaderboards (pass_defense / pass_rush / run_defense) -> TEAM
defensive profiles, then attach OPPONENT-defense strength percentiles onto each offensive player.

WHAT IT BUILDS
--------------
1. Per-team aggregate of player-level 'Points Saved' for each unit (sum over that team's
   leaderboard defenders -- the meaningful contributors; SIS lists ~top-200 per unit):
     team_pass_cov_strength  = sum pass_defense Points Saved  (higher = better coverage)
     team_pass_cov_epatgt    = target-weighted avg EPA/Tgt allowed (NEGATIVE = good coverage)
     team_pass_rush_strength = sum pass_rush  Points Saved
     team_run_def_strength   = sum run_defense Points Saved
   Each *_strength is converted to a LEAGUE PERCENTILE across the 32 teams (0-100, higher=better):
     opp/team _pass_cov_pctl, _pass_rush_pctl, _run_def_pctl  (these are TEAM percentiles).

2. defense.json: the 32 team profiles + the top-3 contributors per unit per team (so turnover /
   who-drives-the-unit can be reasoned about on the dashboard).

3. Attaches to every OFFENSIVE player their UPCOMING-OPPONENT defensive percentiles, using the SAME
   W15 opponent mapping the store already uses for opp_w15_man_rate (the player's `w15` column IS the
   opponent team code, normalized via core.norm_team):
     opp_pass_cov_pctl, opp_pass_rush_pctl, opp_run_def_pctl
   ABSTAINS (leaves the column unset/null) when there is no W15 opponent mapping.

This is MODEL FUSION: percentiles are within the 32-team population; nothing is multiplied or fit;
a missing opponent simply abstains.
"""
import core, csv, os, collections
fn=core.fn; nt=core.norm_team
# SIS NICKNAME -> feature-store team code (verified: all 32 map, 0 unmapped).
NICK={'cardinals':'ARI','falcons':'ATL','ravens':'BAL','bills':'BUF','panthers':'CAR','bears':'CHI',
 'bengals':'CIN','browns':'CLE','cowboys':'DAL','broncos':'DEN','lions':'DET','packers':'GB',
 'texans':'HOU','colts':'IND','jaguars':'JAX','chiefs':'KC','chargers':'LAC','rams':'LAR','raiders':'LV',
 'dolphins':'MIA','vikings':'MIN','patriots':'NE','saints':'NO','giants':'NYG','jets':'NYJ','eagles':'PHI',
 'steelers':'PIT','seahawks':'SEA','49ers':'SF','niners':'SF','buccaneers':'TB','titans':'TEN',
 'commanders':'WAS','football team':'WAS'}
def nick(t):
    return NICK.get(str(t).strip().lower())
def num(x):
    try: return float(str(x).replace('%','').replace('"',''))
    except: return None

def load_unit(path, ps_col):
    """Return {code: {'ps':sum_points_saved, 'players':[(name,pos,ps,extra...)]}} skipping '2 teams'."""
    teams=collections.defaultdict(lambda: {'ps':0.0,'players':[]})
    if not os.path.exists(path): return teams
    for r in csv.DictReader(open(path,encoding='utf-8')):
        if str(r.get('Team','')).strip()=='2 teams': continue
        code=nick(r.get('Team'))
        if not code: continue
        ps=num(r.get(ps_col))
        rec={'name':r.get('Player'),'pos':(r.get('Pos.') or '').strip(),'ps':round(ps,1) if ps is not None else None,
             'epatgt':num(r.get('EPA/Tgt')),'tgts':num(r.get('Tgts'))}
        teams[code]['ps']+=(ps or 0.0); teams[code]['players'].append(rec)
    return teams

COV =load_unit(core.P('sis_value/pass_defense.csv'),'Points Saved')
RUSH=load_unit(core.P('sis_value/pass_rush.csv'),'Points Saved')
RUN =load_unit(core.P('sis_value/run_defense.csv'),'Points Saved')

ALL_TEAMS=sorted(set(COV)|set(RUSH)|set(RUN))

# target-weighted avg EPA/Tgt allowed per team (negative = good coverage)
cov_epatgt={}
for code,d in COV.items():
    num_=0.0; den=0.0
    for p in d['players']:
        if p['epatgt'] is not None and p['tgts'] is not None:
            num_+=p['epatgt']*p['tgts']; den+=p['tgts']
    cov_epatgt[code]=round(num_/den,4) if den>0 else None

def league_pctl(valmap, invert=False):
    """League percentile across teams (0-100). invert=True means LOWER raw is better."""
    items=[(t,v) for t,v in valmap.items() if v is not None]
    if not items: return {}
    vals=sorted(v for _,v in items)
    import bisect
    out={}
    n=len(vals)
    for t,v in items:
        # average-rank midpoint percentile
        lo=bisect.bisect_left(vals,v); hi=bisect.bisect_right(vals,v)
        rank=(lo+hi+1)/2.0   # 1-based average rank
        p=(rank-0.5)/n*100.0
        out[t]=round(100.0-p,1) if invert else round(p,1)
    return out

cov_str ={t:round(d['ps'],1) for t,d in COV.items()}
rush_str={t:round(d['ps'],1) for t,d in RUSH.items()}
run_str ={t:round(d['ps'],1) for t,d in RUN.items()}
cov_pctl =league_pctl(cov_str)
rush_pctl=league_pctl(rush_str)
run_pctl =league_pctl(run_str)

def top3(d):
    return sorted([p for p in d['players'] if p['ps'] is not None], key=lambda p:p['ps'], reverse=True)[:3]

# ---- defense.json team profiles + contributors ----
team_profiles={}
for code in ALL_TEAMS:
    team_profiles[code]={
        'team':code,
        'pass_cov_strength':cov_str.get(code),  'pass_cov_pctl':cov_pctl.get(code),  'pass_cov_epatgt':cov_epatgt.get(code),
        'pass_rush_strength':rush_str.get(code),'pass_rush_pctl':rush_pctl.get(code),
        'run_def_strength':run_str.get(code),   'run_def_pctl':run_pctl.get(code),
        'top_coverage':[{'name':p['name'],'pos':p['pos'],'ps':p['ps'],'epatgt':p['epatgt']} for p in top3(COV.get(code,{'players':[]}))],
        'top_pass_rush':[{'name':p['name'],'pos':p['pos'],'ps':p['ps']} for p in top3(RUSH.get(code,{'players':[]}))],
        'top_run_def':[{'name':p['name'],'pos':p['pos'],'ps':p['ps']} for p in top3(RUN.get(code,{'players':[]}))],
    }
defense_doc={'meta':{'n_teams':len(team_profiles),
    'source':'SIS DataHub 2025: pass_defense + pass_rush + run_defense Points Saved aggregated per team',
    'fields':{'pass_cov_strength':'sum player Points Saved (coverage), higher=better',
              'pass_cov_epatgt':'target-weighted avg EPA/Tgt allowed, NEGATIVE=good coverage',
              'pass_rush_strength':'sum player Points Saved (pass rush), higher=better',
              'run_def_strength':'sum player Points Saved (run defense), higher=better',
              '*_pctl':'league percentile across 32 teams (0-100, higher=better unit)',
              'top_*':'top-3 contributors per unit by Points Saved (turnover-relevant)'},
    'note':'TEAM percentiles over the 32-team population; nothing multiplied or fit; per-defender contributors stored so turnover can be reasoned about.'},
    'teams':team_profiles}
core.safe_json_dump(defense_doc, core.P('defense.json'), indent=2)

# ---- attach OPPONENT defense pctls onto offensive players (same W15 mapping as opp_w15_man_rate) ----
feats=list(csv.DictReader(open(core.P('features.csv'),encoding='utf-8')))
nopp=0
for f in feats:
    if f['pos'] not in ('QB','RB','WR','TE'): continue
    opp=nt(f.get('w15') or '')   # the player's W15 column IS the opponent team code (parallels opp_w15_man_rate)
    prof=team_profiles.get(opp)
    if not prof: continue   # no opponent mapping -> ABSTAIN (leave columns unset)
    got=False
    if prof.get('pass_cov_pctl')  is not None: f['opp_pass_cov_pctl']=prof['pass_cov_pctl']; got=True
    if prof.get('pass_rush_pctl') is not None: f['opp_pass_rush_pctl']=prof['pass_rush_pctl']; got=True
    if prof.get('run_def_pctl')   is not None: f['opp_run_def_pctl']=prof['run_def_pctl']; got=True
    if prof.get('pass_cov_epatgt')is not None: f['opp_pass_cov_epatgt']=prof['pass_cov_epatgt']
    if got: nopp+=1

cols=[]
for f in feats:
    for c in f:
        if c not in cols: cols.append(c)
with open(core.P('features.csv'),'w',newline='',encoding='utf-8') as fh:
    w=csv.DictWriter(fh,fieldnames=cols); w.writeheader(); [w.writerow(f) for f in feats]
core.safe_json_dump({'meta':{'n':len(feats),'cols':cols,'added':'opponent (W15) defense pctls: opp_pass_cov_pctl/opp_pass_rush_pctl/opp_run_def_pctl (+epatgt); abstain if no opp'},'players':feats}, core.P('features.json'))

print("defense.json: %d teams | offensive players w/ opp-defense pctls: %d | total feature cols %d"%(len(team_profiles),nopp,len(cols)))
# rankings
def rank(valmap, n=3, rev=True):
    return sorted([(t,v) for t,v in valmap.items() if v is not None], key=lambda kv:kv[1], reverse=rev)[:n]
print("Top-3 PASS-RUSH teams (sum Points Saved):", rank(rush_str))
print("Top-3 COVERAGE teams (sum Points Saved):", rank(cov_str))
print("Top-3 RUN-DEF teams (sum Points Saved):", rank(run_str))
