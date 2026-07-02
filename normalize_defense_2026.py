#!/usr/bin/env python3
"""NORMALIZED 2026 defense (replaces the raw Points-Saved SUM with a snap-weighted RATE, + rookies).

WHY: summing 'Points Saved' rewarded depth/volume and transplanted a counting stat earned in a
player's OLD role. Instead, team unit quality = snap-weighted mean of PAA-per-play (Points Above
Average per snap) over the projected 2026 roster -- a player's QUALITY (rate) travels, weighted by
his projected SNAPS (role). Movers carry rate+snaps to their 2026 team. Rookies are folded in via a
draft-round prior (snaps + rate) calibrated to the 2025 rookie class ('NFL effect by draft round'),
blended with college grade for DBs.

DATA LIMITATIONS (documented honestly):
- SIS unit files are top-200 leaderboards for ONE season (2025); rookie sample is 9-14/unit -> the
  round curves are SHRUNK/smoothed priors, not fitted cells. Adding 2024 (needs a SIS NFL pull) and
  full rosters would sharpen them.
- 2026 draft pull truncated at round 5 (rds 6-7 add negligible projected snaps).
Outputs: defense.json (canonical pctls now rate+rookie based; *_rate_2026 + *_pctl_2025 reference +
rookies_2026 + moves_2026) and re-maps opponent pctls onto offensive players (same as the old stage).
"""
import core, csv, os, json, bisect, statistics as st
from collections import defaultdict
# ---- reuse the curated MOVES map + helpers from reweight_defense_2026 (exec head only, no writes) ----
_src=open(core.P('reweight_defense_2026.py'),encoding='utf-8').read().split('UNITS=')[0]
_ns={}; exec(_src,_ns)
MOVES=_ns['MOVES']; nick=_ns['nick']; NICK=_ns['NICK']; fn=core.fn
KNOWN_GAPS=_ns.get('KNOWN_GAPS',[])   # players absent from SIS source; documented, not fabricated
def num(x):
    try: return float(str(x).replace('%','').replace('"',''))
    except: return None
ALL_TEAMS=sorted(set(NICK.values()))

# unit -> (csv, snap column). rate = Points Above Avg / snaps (consistent across units).
UNITS={'coverage':('sis_value/pass_defense.csv','Cov. Snaps'),
       'pass_rush':('sis_value/pass_rush.csv','Pass Snaps'),
       'run_def':('sis_value/run_defense.csv','Rush Snaps')}
POS2UNITS={'CB':['coverage','run_def'],'DB':['coverage','run_def'],'S':['coverage','run_def'],
 'FS':['coverage','run_def'],'SS':['coverage','run_def'],'LB':['run_def','coverage'],
 'ILB':['run_def','coverage'],'MLB':['run_def','coverage'],'OLB':['pass_rush','run_def'],
 'EDGE':['pass_rush','run_def'],'DE':['pass_rush','run_def'],'DT':['run_def','pass_rush'],
 'DL':['run_def','pass_rush'],'NT':['run_def','pass_rush']}

draft26=[r for r in csv.DictReader(open(core.P('sis_value/draft_2026.csv')))]
draft25={fn(r['player']):r for r in csv.DictReader(open(core.P('sis_value/draft_2025.csv')))}
draft24={fn(r['player']):int(r['round']) for r in csv.DictReader(open(core.P('sis_value/draft_2024.csv')))}
dbgrades=json.load(open(core.P('boom/rookie_db_grades.json')))['dbs']  # college coverage grades

# ---- PFF de-pollution for the pass-rush unit ----------------------------------------------------
# SIS's pass-rush leaderboard mixes in off-ball LBs (Tyrel Dodson, Jack Campbell) and DBs whose per-rush
# PAA distorts team pass-rush ratings, and SIS position labels are unreliable (Brian Burns / Van Ginkel
# are edges tagged 'LB'). PFF's `position` (ED=edge, DI=interior) is authoritative -> keep ONLY true
# rushers. 99% of the SIS leaderboard joins to PFF; players absent from PFF fall back to their SIS label.
PFFPOS={}
# PFF 2025 per-unit snaps (to tell an INJURED absence from a healthy one) + 2024 per-unit grades
# (to catch elite blind-spots absent from SIS both years). unit -> (grade col, snap col).
_PFFCOL={'coverage':('grades_coverage_defense','snap_counts_coverage'),
         'pass_rush':('grades_pass_rush_defense','snap_counts_pass_rush'),
         'run_def':('grades_run_defense','snap_counts_run_defense')}
PFF25_SNAPS={}   # key -> {unit: snaps} in 2025
PFF24=  {}       # key -> {'pos':.., 'team':.., unit: grade..} in 2024
for _yr in ('2024','2025'):
    _pf=core.P(f'NFL-master/PFF/{_yr}/defense.csv')
    if os.path.exists(_pf):
        for r in csv.DictReader(open(_pf,encoding='utf-8-sig')):
            k=fn(r['player']); PFFPOS[k]=r['position']
            if _yr=='2025':
                PFF25_SNAPS[k]={u:(num(r.get(sc)) or 0) for u,(gc,sc) in _PFFCOL.items()}
                PFF25_SNAPS[k]['total']=num(r.get('snap_counts_defense')) or 0   # player-level: injured or not
            else:
                PFF24[k]={'name':r['player'],'pos':r['position'],'team':r.get('team_name','')}
                for u,(gc,sc) in _PFFCOL.items():
                    PFF24[k][u]=num(r.get(gc)); PFF24[k][u+'_sn']=num(r.get(sc)) or 0
_SIS_DL={'DE','DT','DL','NT','EDGE','OLB','ED','DI'}
def is_pass_rusher(p):
    pp=PFFPOS.get(p['key'])
    if pp: return pp in ('ED','DI')
    return (p.get('pos') or '').upper() in _SIS_DL   # not in PFF -> trust the SIS position label

def load_unit(path,snapcol):
    rows=list(csv.DictReader(open(core.P(path),encoding='utf-8')))
    # C1 FIX: some SIS exports (notably 2025 pass_rush) put a PER-RUSH RATE under the 'Points Above Avg'
    # header instead of the season COUNTING value. A season counting-PAA leaderboard always has
    # |max| >> 1; a per-play rate is < ~0.2. Detect and DON'T divide a rate by snaps a second time
    # (the old code did, collapsing every 2025 pass-rusher — incl. Myles Garrett — to ~0.0002).
    _paa=[v for v in (num(r.get('Points Above Avg')) for r in rows) if v is not None]
    already_rate = bool(_paa) and max(abs(v) for v in _paa) < 2.0
    if already_rate:
        print(f"  [C1] {os.path.basename(path)}: 'Points Above Avg' is already per-play (max|PAA|={max(abs(v) for v in _paa):.3f}) -> used directly as rate")
    out=[]
    for r in rows:
        snaps=num(r.get(snapcol)); paa=num(r.get('Points Above Avg'))
        if not snaps or paa is None: continue
        raw=str(r.get('Team','')).strip(); code='2T' if raw=='2 teams' else nick(raw)
        out.append({'key':fn(r['Player']),'name':r['Player'],'team2025':code,'pos':(r.get('Pos.') or '').strip(),
                    'snaps':snaps,'paa':paa,'rate':(paa if already_rate else paa/snaps),
                    'epatgt':num(r.get('EPA/Tgt')),'tgts':num(r.get('Tgts'))})
    return out

# ---- rookie round curves from BOTH classes (2024+2025). FINDING: snaps-by-round is stable, but
# rookie production RATE is NOT (2024 class outperformed, 2025 underperformed) -> use ONE pooled
# rookie rate (~league avg, capped at the current vet baseline), not an overfit per-round gradient. ----
def rookie_curves(p25, p24):
    vet_rate=st.median([p['rate'] for p in p25])
    by=defaultdict(list)
    for p in p25:
        d=draft25.get(p['key'])
        if d: by[int(d['round'])].append(p)
    for p in p24:
        d=draft24.get(p['key'])
        if d: by[int(d)].append(p)
    allrk=[p for ps in by.values() for p in ps]
    base_snaps=st.median([p['snaps'] for p in allrk]) if allrk else 300
    rk_rate=min(st.median([p['rate'] for p in allrk]) if allrk else vet_rate, vet_rate)  # pooled, capped
    cur={}
    for rd in range(1,8):
        ps=by.get(rd,[]); n=len(ps)
        sn=(sum(p['snaps'] for p in ps)+4*base_snaps)/(n+4)   # shrink snaps toward overall (k=4)
        cur[rd]={'snaps':sn,'rate':rk_rate,'n':n}             # rate = single pooled value (round not predictive)
    for rd in range(2,8): cur[rd]['snaps']=min(cur[rd]['snaps'],cur[rd-1]['snaps'])  # monotone snaps
    return cur,vet_rate

RES={}; CURVES={}; MOVELOG=defaultdict(list)
# ---- 2024-STARTER RECOVERY (fixes the arbitrary top-200 dropout cliff; league-wide, one rule) ----
# A player who was a real 2024 SIS starter but is ABSENT from SIS-2025 gets zero under blend2yr (which
# only helps players present in 2025). If his 2025 sample is inadequate (injured / DNP) his last VALID
# reading is 2024 -> fold it back at a HAIRCUT (injury-return regression). If he played a FULL 2025 yet
# SIS omits him, SIS's current read stands (flag the PFF disagreement, don't cherry-pick 2024).
SNAP_MIN_REC={'coverage':400,'pass_rush':300,'run_def':300}  # "real 2024 starter" by snaps
REC_GRADE_MIN=74.0     # recover only players PFF rated a GOOD 2024 starter (aligns with the audit; kills marginals)
INJ_TOTAL_MAX=500      # < this many TOTAL 2025 def snaps (player-level ~half season) => injured/DNP => recover
HAIRCUT=0.65           # keep 65% of the 2024 above-avg rate (injury-return discount; user-chosen)
BLINDSPOT_GRADE=82.0   # PFF-elite in 2024 yet absent from SIS BOTH years => flag (can't recover honestly)
RECOVERED=defaultdict(list); FLAGGED=[]; SIS_KEYS={}
PFF2MODEL={'ARZ':'ARI','BLT':'BAL','CLV':'CLE','HST':'HOU','LA':'LAR'}
def pteam(t): return PFF2MODEL.get(t,t)
# H3 FIX: a player's 2026 QUALITY = snap-weighted blend of his 2024+2025 rate (regresses an
# injury-shortened or down season toward his larger-sample year); his 2026 ROLE (snaps) = his
# healthy-season snap count (an injured season shouldn't shrink a signed starter's projected volume).
# Applied to the CANONICAL 2026 roster only; the *_pctl_2025 baseline stays pure-2025. Falls back to
# single-season when a player isn't in the other year's top-200 leaderboard (honest: no fabrication).
def blend2yr(p, by24):
    q=by24.get(p['key'])
    if not q: return p['rate'], p['snaps']
    s24,s25=q['snaps'],p['snaps']
    rate=(q['rate']*s24 + p['rate']*s25)/(s24+s25) if (s24+s25) else p['rate']
    return rate, max(s24,s25)
for unit,(path,snapcol) in UNITS.items():
    players=load_unit(path,snapcol)
    p24=load_unit(path.replace('.csv','_2024.csv'),snapcol)
    if unit=='pass_rush':   # PFF de-pollution: a team's pass rush is defined by EDGE/INTERIOR rushers,
        _n0=len(players)    # not off-ball LBs/DBs who happen to blitz. Drop the non-rushers (both years).
        players=[p for p in players if is_pass_rusher(p)]; p24=[p for p in p24 if is_pass_rusher(p)]
        print(f"  [PFF] pass_rush: kept {len(players)}/{_n0} true edge/interior rushers (dropped off-ball LB/DB)")
    by24={q['key']:q for q in p24}
    SIS_KEYS[unit]={'y25':{p['key'] for p in players},'y24':set(by24)}
    cur,vet_rate=rookie_curves(players,p24); CURVES[unit]=cur
    # 2026 roster per team: vets (moved) + rookies
    ros25=defaultdict(list); ros26=defaultdict(list); rookies_added=defaultdict(list)
    for p in players:
        c=p['team2025']
        if c and c!='2T': ros25[c].append(p)          # baseline = pure 2025
        br,bs=blend2yr(p,by24)                          # canonical 2026 = 2yr quality + healthy role
        pb={**p,'rate':br,'snaps':bs}
        mv=MOVES.get(p['key'])
        if mv:
            if mv['to'] in ('RETIRED','UFA'): continue
            q=dict(pb); q['from']=c; ros26[mv['to']].append(q)
            MOVELOG[mv['to']].append({'player':pb['name'],'unit':unit,'from':c,'to':mv['to'],'ps':round(pb['rate']*pb['snaps'],1),'conf':mv.get('conf',True)})
        elif c and c!='2T': ros26[c].append(pb)
    # add 2026 rookies
    for r in draft26:
        pos=r['pos'].upper(); units=POS2UNITS.get(pos)
        if not units or unit not in units: continue
        rd=int(r['round']); team=r['team']
        if team not in ALL_TEAMS: continue
        sn=CURVES[unit][rd]['snaps']; rt=CURVES[unit][rd]['rate']
        # secondary unit -> half the snaps
        if units.index(unit)==1: sn*=0.5
        # DB college blend for coverage
        if unit=='coverage' and pos in ('CB','S','DB','FS','SS'):
            g=dbgrades.get(fn(r['player']))
            if g and g.get('coverage_pctl_2025') is not None:
                rt=rt+((g['coverage_pctl_2025']-50)/50.0)*0.004   # +/-0.004 max college nudge
        rk={'key':fn(r['player']),'name':r['player'],'pos':pos,'snaps':sn,'rate':rt,
            'epatgt':None,'tgts':None,'rookie':True,'round':rd}
        ros26[team].append(rk); rookies_added[team].append((r['player'],pos,unit,'R%d'%rd,round(rt,4)))
    # ---- recover 2024 starters absent from SIS-2025 (injured/DNP) at a haircut; flag healthy-omitted ----
    p2025_keys={p['key'] for p in players}
    for key,q in by24.items():
        if key in p2025_keys: continue                     # in 2025 SIS -> blend2yr already handles him
        if q['snaps'] < SNAP_MIN_REC[unit]: continue       # not a real 2024 starter (by SIS snaps)
        g24=(PFF24.get(key) or {}).get(unit)               # gate on PFF-verified 2024 quality (aligns w/ audit)
        if g24 is None or g24 < REC_GRADE_MIN: continue    # only genuinely good starters -> no near-replacement churn
        if q['rate'] <= 0: continue                        # SIS rated him BELOW avg in 2024 -> nothing good to restore (avoids importing a negative that would tank the team)
        mv=MOVES.get(key); dest=mv['to'] if mv else q['team2025']
        if dest in ('UFA','RETIRED') or not dest or dest=='2T': continue   # off a 2026 roster
        tot25=(PFF25_SNAPS.get(key) or {}).get('total',0); snaps25=(PFF25_SNAPS.get(key) or {}).get(unit,0)
        if tot25 < INJ_TOTAL_MAX:                           # played < ~half of 2025 (injured/DNP) => RECOVER 2024
            rr=q['rate']*HAIRCUT
            ros26[dest].append({'key':key,'name':q['name'],'pos':q.get('pos',''),'snaps':q['snaps'],
                                'rate':rr,'epatgt':q.get('epatgt'),'tgts':q.get('tgts'),'recovered':True})
            MOVELOG[dest].append({'player':q['name'],'unit':unit,'from':dest,'to':dest,
                                  'ps':round(rr*q['snaps'],1),'conf':True,'recovered_from_2024':True})
            RECOVERED[unit].append({'player':q['name'],'team':dest,'rate_2024':round(q['rate'],4),
                'rate_used':round(rr,4),'snaps_2024':round(q['snaps']),'snaps_2025':int(snaps25),'haircut':HAIRCUT})
        else:                                               # healthy full 2025 but SIS-omitted => flag only
            FLAGGED.append({'player':q['name'],'team':dest,'unit':unit,'snaps_2025':int(snaps25),
                'kind':'healthy_but_SIS_omitted',
                'reason':'played a full 2025 (%d unit snaps) yet SIS Points Saved ranks him outside the top-200; SIS/PFF disagree. Left as-is so his current SIS read stands (2024 not cherry-picked).'%int(snaps25)})
    def wmean(roster):
        sw=sum(x['snaps'] for x in roster); 
        return (sum(x['rate']*x['snaps'] for x in roster)/sw) if sw else None
    def epatgt(roster):
        nu=sum((x['epatgt'] or 0)*(x['tgts'] or 0) for x in roster if x.get('epatgt') is not None and x.get('tgts'))
        de=sum((x['tgts'] or 0) for x in roster if x.get('epatgt') is not None and x.get('tgts'))
        return round(nu/de,4) if de else None
    rate25={t:wmean(ros25[t]) for t in ALL_TEAMS if ros25[t]}
    rate26={t:wmean(ros26[t]) for t in ALL_TEAMS if ros26[t]}
    RES[unit]={'rate25':rate25,'rate26':rate26,'ros26':ros26,'rookies':rookies_added,
               'epat26':{t:epatgt(ros26[t]) for t in ALL_TEAMS} if unit=='coverage' else {}}

# ---- pure BLIND SPOTS: PFF-elite 2024 starters absent from SIS BOTH years (Joseph-class). Can't recover
#      without fabricating (no SIS reading either year) -> flag with the real PFF evidence, one rule for all. ----
_U_ELIG={'coverage':{'CB','S','LB'},'pass_rush':{'ED','DI'},'run_def':{'DI','ED','LB','S','CB'}}
_seen_blind=set()
for key,g in PFF24.items():
    best=None
    for unit in UNITS:
        if g['pos'] not in _U_ELIG[unit]: continue
        gr=g.get(unit)
        if gr is None or gr < BLINDSPOT_GRADE: continue
        if (g.get(unit+'_sn') or 0) < SNAP_MIN_REC[unit]: continue   # real 2024 starter only (kill small-sample PFF noise)
        sk=SIS_KEYS.get(unit,{})
        if key in sk.get('y24',set()) or key in sk.get('y25',set()): continue   # SIS has him -> not blind
        if best is None or gr>best[1]: best=(unit,gr)
    if not best or key in _seen_blind: continue
    _seen_blind.add(key)
    mv=MOVES.get(key); dest=mv['to'] if mv else pteam(g.get('team',''))
    if dest in ('UFA','RETIRED'): continue                 # off a 2026 roster
    snaps25=(PFF25_SNAPS.get(key) or {}).get(best[0],0)
    FLAGGED.append({'player':g.get('name',key),'team':dest,'unit':best[0],
        'kind':'blind_spot_both_years','pff_grade_2024':round(best[1],1),'snaps_2025':int(snaps25),
        'reason':'PFF-elite in 2024 (grade %.1f) but absent from SIS Points Saved in BOTH 2024 and 2025 (SIS structurally misses this profile); no SIS reading exists to fold in without fabricating.'%best[1]})

def pctl(valmap):
    items=[(t,v) for t,v in valmap.items() if v is not None]; vals=sorted(v for _,v in items); n=len(vals); o={}
    for t,v in items:                                   # Hazen plotting-position percentile (ties -> mid-rank)
        lo=bisect.bisect_left(vals,v); hi=bisect.bisect_right(vals,v); rank=(lo+hi+1)/2.0; o[t]=round((rank-0.5)/n*100,1)
    return o
P={}
for unit in UNITS:
    P[unit]={'p25':pctl(RES[unit]['rate25']),'p26':pctl(RES[unit]['rate26'])}

# ---- write defense.json (canonical = 2026 rate+rookie pctls) ----
old=_ns['_load_old_defense']() if '_load_old_defense' in _ns else {}
def top3(roster): return sorted(roster,key=lambda p:-p['rate']*p['snaps'])[:3]
def fmt3(roster): return [{'name':p['name'],'pos':p['pos'],'ps':round(p['rate']*p['snaps'],1),'rate':round(p['rate'],4),'snaps':round(p['snaps'])} for p in top3(roster)]
teams={}
for t in ALL_TEAMS:
    cov=P['coverage']; rush=P['pass_rush']; run=P['run_def']
    teams[t]={'team':t,
      'pass_cov_pctl':cov['p26'].get(t),'pass_cov_pctl_2025':cov['p25'].get(t),'pass_cov_rate_2026':round(RES['coverage']['rate26'].get(t),4) if RES['coverage']['rate26'].get(t) is not None else None,
      'pass_rush_pctl':rush['p26'].get(t),'pass_rush_pctl_2025':rush['p25'].get(t),'pass_rush_rate_2026':round(RES['pass_rush']['rate26'].get(t),4) if RES['pass_rush']['rate26'].get(t) is not None else None,
      'run_def_pctl':run['p26'].get(t),'run_def_pctl_2025':run['p25'].get(t),'run_def_rate_2026':round(RES['run_def']['rate26'].get(t),4) if RES['run_def']['rate26'].get(t) is not None else None,
      'pass_cov_epatgt':RES['coverage']['epat26'].get(t),
      'pass_cov_strength':round(RES['coverage']['rate26'].get(t),4) if RES['coverage']['rate26'].get(t) is not None else None,
      'pass_rush_strength':round(RES['pass_rush']['rate26'].get(t),4) if RES['pass_rush']['rate26'].get(t) is not None else None,
      'run_def_strength':round(RES['run_def']['rate26'].get(t),4) if RES['run_def']['rate26'].get(t) is not None else None,
      'rookies_2026':RES['coverage']['rookies'].get(t,[])+RES['pass_rush']['rookies'].get(t,[])+RES['run_def']['rookies'].get(t,[]),
      'top_coverage':fmt3(RES['coverage']['ros26'].get(t,[])),
      'top_pass_rush':fmt3(RES['pass_rush']['ros26'].get(t,[])),
      'top_run_def':fmt3(RES['run_def']['ros26'].get(t,[])),
      'moves_2026':MOVELOG.get(t,[]),
    }
doc={'meta':{'n_teams':len(teams),
  'method':'team unit strength = SNAP-WEIGHTED MEAN of PAA-per-play over the projected 2026 roster (movers carry rate+snaps to 2026 team; rookies via draft-round prior calibrated to 2025 class + DB college blend). Replaces the raw Points-Saved SUM. 32-team Hazen percentiles.',
  'rookie_curves':{u:{rd:{'snaps':round(c[rd]['snaps']),'rate':round(c[rd]['rate'],4),'n_obs':c[rd]['n']} for rd in range(1,6)} for u,c in CURVES.items()},
  'limitations':['SIS = top-200 leaderboard, 2025 only; rookie n=9-14/unit -> round curves are shrunk priors','2024 NFL Value (2nd rookie class) needs a SIS pull','2026 draft truncated at rd5'],
  'known_gaps':KNOWN_GAPS,   # curated notes (e.g. Kerby Joseph detail)
  'recovered_2024_starters':{u:RECOVERED[u] for u in RECOVERED},  # injured-2025 starters folded back from 2024 SIS at HAIRCUT
  'recovery_policy':{'haircut':HAIRCUT,'snap_min_2024':SNAP_MIN_REC,'grade_min_2024':REC_GRADE_MIN,'inj_total_snaps_2025_max':INJ_TOTAL_MAX,
     'rule':'A player who was a GOOD 2024 starter (PFF>=%.0f, >=snap_min snaps) with a POSITIVE SIS 2024 rate, absent from SIS-2025 and having played <%d total 2025 def snaps (injured/DNP), is folded onto his 2026 team at 2024 rate x %.2f. Healthy-but-SIS-omitted -> flagged not recovered; PFF-elite absent both SIS years -> flagged.'%(REC_GRADE_MIN,INJ_TOTAL_MAX,HAIRCUT)},
  'currency_flags':FLAGGED,   # players the model can't credit (healthy-but-SIS-omitted + blind-spots) — documented, not fabricated
  'fields':{'*_pctl':'canonical 2026 rate+rookie percentile (higher=tougher)','*_pctl_2025':'2025 no-moves rate baseline','*_rate_2026':'snap-weighted mean PAA/play','rookies_2026':'folded-in rookies (name,pos,round,proj_rate)'}},
  'teams':teams}
core.safe_json_dump(doc,core.P('defense.json'),indent=2)
# ---- re-map opponent 2026 pctls onto offensive players (W15 opp), same as the prior stage ----
nt=core.norm_team
feats=list(csv.DictReader(open(core.P('features.csv'),encoding='utf-8'))); nopp=0
for f in feats:
    if f.get('pos') not in ('QB','RB','WR','TE'): continue
    prof=teams.get(nt(f.get('w15') or ''))
    if not prof: continue
    got=False
    if prof.get('pass_cov_pctl') is not None: f['opp_pass_cov_pctl']=prof['pass_cov_pctl']; got=True
    if prof.get('pass_rush_pctl') is not None: f['opp_pass_rush_pctl']=prof['pass_rush_pctl']; got=True
    if prof.get('run_def_pctl') is not None: f['opp_run_def_pctl']=prof['run_def_pctl']; got=True
    if prof.get('pass_cov_epatgt') is not None: f['opp_pass_cov_epatgt']=prof['pass_cov_epatgt']
    if got: nopp+=1
cols=[]
for f in feats:
    for c in f:
        if c not in cols: cols.append(c)
with open(core.P('features.csv'),'w',newline='',encoding='utf-8') as fh:
    w=csv.DictWriter(fh,fieldnames=cols); w.writeheader(); [w.writerow(f) for f in feats]
core.safe_json_dump({'meta':{'n':len(feats),'cols':cols,'added':'opp W15 2026 NORMALIZED (rate+rookie) defense pctls'},'players':feats},core.P('features.json'))
print("opponent pctls re-mapped onto %d offensive players"%nopp)
print("defense.json written (normalized rate + rookies).")
print("\nrookie round curves (snaps | PAA/play):")
for u in UNITS:
    print(f"  {u}: "+" ".join(f"R{rd}={CURVES[u][rd]['snaps']:.0f}/{CURVES[u][rd]['rate']:+.4f}" for rd in range(1,6)))
