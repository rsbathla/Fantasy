#!/usr/bin/env python3
"""Unified, data-backed FLAGS layer for the 2026 best-ball model.

For every player it computes risk flags (each tagged playoff-relevant or not), a TOTAL flag count,
a PLAYOFF flag count, a data-backed availability multiplier, and an availability-adjusted projection
-> then measures the resulting rank movement.

DEFINITIONS (documented in FLAGS_LAYER.md):
  TOTAL flags   = every risk on the player: injury/availability, new-OC scheme suppression, weak OL
                  capping a deep lever, durability, roster (unsigned / not-usable), tough W15-17 slate.
  PLAYOFF flags = ONLY risks that specifically threaten the fantasy-playoff window (NFL Weeks 15-17):
                  an injury NOT projected healthy by the playoffs, a tough W15-17 opponent slate,
                  matchup-levers that go cold in W15-17, a W15-17 bye, or a season-killing roster issue
                  (out all year). Early-season injuries that resolve before December and season-wide
                  scheme/OL risks (not *worse* in the playoffs) count toward TOTAL but NOT PLAYOFF.

Every input is real/verified or a transparent modeling parameter (see ASSUMPTIONS_AUDIT.md):
  - injury availability multipliers: boom/roster_flags_2026.json 'availability' (cited June-2026 research)
  - OL tiers: boom/oline_2026.json (web-verified, replaces the broken fusion oline_pctl)
  - scheme dials: scheme_2026.json (web-verified play-callers)
  - opponent defense + schedule: defense.json + boom/schedule2026.json (verified)

Reads dossier_data.json (AFTER build_dossier + build_lever_count). Writes risk_flags / flags_total /
flags_playoff / avail / adj_pg / proj_posrank / adj_posrank / posrank_delta back into each player,
team-level flag_rollup, plus standalone flags_2026.json and flag_rank_delta.csv.
Run AFTER build_lever_count.py, BEFORE build_lever_board / build_rankings / render_dossier.
"""
import json, os, csv, core
from collections import defaultdict
H=os.path.dirname(os.path.abspath(__file__))
def J(p):
    q=core.P(p); return json.load(open(q,encoding='utf-8')) if os.path.exists(q) else {}
fn=core.fn

# ---- tunable thresholds (modeling parameters, not facts) ----
PO_SLATE_TOUGH=64    # mean opp unit pctl (higher=tougher) over W15-17 to flag a hard playoff slate
PO_SLATE_HARD=72     # >= this -> severity 2
OL_TIER_WEAK=2       # OL tier <= this caps the deep/vertical lever
PO_COLD_RATIO=0.6    # playoff_mean < ratio*season_mean -> levers go cold in the playoffs
PO_COLD_MINMEAN=0.4  # only flag cold playoff levers if the player actually has a real season signal

DD=J('dossier_data.json')
RF=J('boom/roster_flags_2026.json')
SCH=J('scheme_2026.json')
OL=(J('boom/oline_2026.json').get('teams') or {})
DEF=(J('defense.json').get('teams') or {})
NORM={'ARZ':'ARI','BLT':'BAL','CLV':'CLE','HST':'HOU','JAC':'JAX','LA':'LAR','OAK':'LV','SD':'LAC','WSH':'WAS','LVR':'LV'}
def nt(t):
    t=str(t or '').upper(); return NORM.get(t,t)
SCHED={nt(k):v for k,v in (J('boom/schedule2026.json') or {}).items()}

AVAIL_FN={fn(k):v for k,v in (RF.get('availability') or {}).items()}
NONUSE_FN={fn(k) for k in (RF.get('non_usable') or {}).keys()}
FA_FN={fn(k) for k in (RF.get('free_agents_unsigned_confirmed') or {}).keys()}

def lever_dialkey(t):
    tl=t.lower()
    if 'vertical' in tl or 'big-play' in tl or 'deep' in tl: return 'vertical'
    if 'pass-catching back' in tl or 'pass catching back' in tl: return 'passcatch'
    if 'scrambling qb' in tl or 'scramble' in tl: return 'scramble'
    if 'motion' in tl: return 'motion'
    return None
def is_vertical(t):
    tl=t.lower(); return ('vertical' in tl or 'big-play' in tl or 'deep' in tl)

def playoff_slate(team,pos):
    """mean opponent-unit toughness pctl over W15-17 (higher=tougher); + opp list."""
    opps=[g['opp'] for g in SCHED.get(team,[]) if g.get('wk') in (15,16,17) and g.get('opp') not in (None,'BYE')]
    key='run_def_pctl' if pos=='RB' else 'pass_cov_pctl'
    vals=[(DEF.get(nt(o)) or {}).get(key) for o in opps]; vals=[v for v in vals if v is not None]
    return (sum(vals)/len(vals) if vals else None), opps
def playoff_bye(team):
    for g in SCHED.get(team,[]):
        if g.get('opp')=='BYE' and g.get('wk') in (15,16,17): return g['wk']
    return None

players=[]
for t in DD.get('teams',[]):
    tm=t['team']
    so=(SCH.get(tm) or {}).get('off') or {}
    olrec=(OL.get(tm) or {}); oltier=olrec.get('tier')
    for p in t['players']:
        k=fn(p['name']); pos=p['pos']; flags=[]; avail=1.0
        # 1) injury / availability (cited)
        av=AVAIL_FN.get(k)
        if av:
            avail=av.get('avail_mult',1.0); pok=av.get('playoff_ok',True); verdict=av.get('verdict','')
            sev=3 if avail<=0.5 else (2 if avail<0.85 else 1)
            flags.append({'code':'INJ','label':"injury: %s (~%s g lost, avail %d%%)"%(verdict.replace('_',' ').lower(),av.get('games_missed_mid'),round(avail*100)),
                          'cat':'availability','sev':sev,'playoff':(not pok)})
            if av.get('durability'):
                flags.append({'code':'DUR','label':'elevated re-injury / durability risk','cat':'durability','sev':1,'playoff':False})
        # 2) roster: non-usable / unsigned (out all year -> playoff too)
        if k in NONUSE_FN:
            flags.append({'code':'OUT','label':'not a usable 2026 asset (transaction unresolved)','cat':'roster','sev':3,'playoff':True}); avail=0.0
        if k in FA_FN:
            flags.append({'code':'FA','label':'unsigned free agent (no 2026 team yet)','cat':'roster','sev':3,'playoff':True})
        # 3) new-OC scheme suppresses one of his levers (season-wide -> total only)
        if so:
            for x in (p.get('levers') or []):
                dk=lever_dialkey(x.get('t',''))
                if dk and so.get(dk,0)<0:
                    flags.append({'code':'SCH','label':'new-OC scheme reduces %s usage'%dk,'cat':'scheme','sev':2,'playoff':False}); break
        # 4) weak OL caps the deep lever (season-wide -> total only)
        if oltier is not None and oltier<=OL_TIER_WEAK and any(is_vertical(x.get('t','')) for x in (p.get('levers') or [])):
            flags.append({'code':'OL','label':'below-average OL (tier %d) caps the deep-shot lever'%oltier,'cat':'oline','sev':1,'playoff':False})
        # 5) playoff-window risks (W15-17)
        tough,opps=playoff_slate(tm,pos); po_slate=False
        if tough is not None and tough>=PO_SLATE_TOUGH:
            unit='run' if pos=='RB' else 'pass'; po_slate=True
            flags.append({'code':'PO-SLATE','label':'tough W15-17 slate (opp %s D ~%d pctl: %s)'%(unit,round(tough),', '.join(opps)),
                          'cat':'playoff','sev':2 if tough>=PO_SLATE_HARD else 1,'playoff':True})
        ls=p.get('lever_sum') or {}
        if (not po_slate) and ls.get('n_levers') and (ls.get('mean') or 0)>=PO_COLD_MINMEAN and ls.get('playoff_mean') is not None and ls['playoff_mean']<PO_COLD_RATIO*ls['mean']:
            flags.append({'code':'PO-COLD','label':'matchup levers cool in W15-17 (season %s -> playoff %s)'%(ls['mean'],ls['playoff_mean']),'cat':'playoff','sev':1,'playoff':True})
        pbye=playoff_bye(tm)
        if pbye:
            flags.append({'code':'PO-BYE','label':'team bye in W%d (playoff window)'%pbye,'cat':'playoff','sev':2,'playoff':True})

        total=len(flags); po=sum(1 for f in flags if f['playoff'])
        pg=(p.get('proj') or {}).get('pg')
        adj=round(pg*avail,1) if (pg is not None and avail is not None) else pg
        p['risk_flags']=flags; p['flags_total']=total; p['flags_playoff']=po
        p['avail']=round(avail,2); p['adj_pg']=adj
        players.append({'k':k,'name':p['name'],'pos':pos,'team':tm,'rank':p.get('rank'),'pg':pg,'adj':adj,
                        'avail':avail,'total':total,'po':po,'flags':flags,'p':p})

# ---- rank movement: position rank by projection, raw proj vs availability-adjusted ----
bypos=defaultdict(list)
for pl in players:
    if pl['pg'] is not None: bypos[pl['pos']].append(pl)
movers=[]
for pos,arr in bypos.items():
    raw=sorted(arr,key=lambda x:-x['pg']); adj=sorted(arr,key=lambda x:-(x['adj'] if x['adj'] is not None else x['pg']))
    rr={id(x):i+1 for i,x in enumerate(raw)}; ar={id(x):i+1 for i,x in enumerate(adj)}
    for x in arr:
        a,b=rr[id(x)],ar[id(x)]
        x['p']['proj_posrank']=a; x['p']['adj_posrank']=b; x['p']['posrank_delta']=a-b
        x['proj_posrank']=a; x['adj_posrank']=b
        if x['avail']<1.0: movers.append((pos,x['name'],x['team'],a,b,b-a,x['pg'],x['adj'],round(x['avail'],2),x['total'],x['po']))
movers.sort(key=lambda r:(-abs(r[5]), r[0]))

# ---- team rollups ----
for t in DD.get('teams',[]):
    fl=[p for p in t['players'] if p.get('flags_total')]
    t['flag_rollup']={'n_flagged':len(fl),
        'total':sum(p.get('flags_total',0) for p in t['players']),
        'playoff':sum(p.get('flags_playoff',0) for p in t['players']),
        'players':[{'name':p['name'],'pos':p['pos'],'total':p['flags_total'],'po':p['flags_playoff']} for p in fl]}

# ---- write back dossier_data.json ----
DD.setdefault('meta',{})['flags_built']=True
json.dump(DD,open(core.P('dossier_data.json'),'w',encoding='utf-8'),ensure_ascii=False)

# ---- standalone flags_2026.json (keyed by normalized name; for the rankings board) ----
out={}
for pl in players:
    out[pl['k']]={'name':pl['name'],'pos':pl['pos'],'team':pl['team'],'rank':pl['rank'],
        'total':pl['total'],'playoff':pl['po'],'avail':round(pl['avail'],2),'pg':pl['pg'],'adj_pg':pl['adj'],
        'proj_posrank':pl.get('proj_posrank'),'adj_posrank':pl.get('adj_posrank'),
        'flags':[{'code':f['code'],'label':f['label'],'sev':f['sev'],'cat':f['cat'],'playoff':f['playoff']} for f in pl['flags']]}
cat_counts=defaultdict(int);
for pl in players:
    for f in pl['flags']: cat_counts[f['cat']]+=1
meta={'n_players':len(players),'n_flagged':sum(1 for pl in players if pl['total']),
      'n_playoff_flagged':sum(1 for pl in players if pl['po']),
      'total_flags':sum(pl['total'] for pl in players),'playoff_flags':sum(pl['po'] for pl in players),
      'by_category':dict(cat_counts),
      'params':{'PO_SLATE_TOUGH':PO_SLATE_TOUGH,'PO_SLATE_HARD':PO_SLATE_HARD,'OL_TIER_WEAK':OL_TIER_WEAK,'PO_COLD_RATIO':PO_COLD_RATIO},
      'note':'TOTAL=all risks; PLAYOFF=risks specific to NFL W15-17. avail=data-backed availability multiplier; adj_pg=proj.pg*avail.'}
json.dump({'meta':meta,'players':out},open(core.P('flags_2026.json'),'w',encoding='utf-8'),ensure_ascii=False,indent=0)

# ---- flag_rank_delta.csv (every projection-rank mover from availability) ----
with open(core.P('flag_rank_delta.csv'),'w',newline='',encoding='utf-8') as fh:
    w=csv.writer(fh); w.writerow(['pos','name','team','proj_posrank','adj_posrank','spots_moved(+=fell)','proj_pg','adj_pg','avail','flags_total','flags_playoff'])
    for r in movers: w.writerow(r)

print("flags_2026.json: %d players, %d flagged (%d with playoff flags), %d total flags (%d playoff)"%(
    meta['n_players'],meta['n_flagged'],meta['n_playoff_flagged'],meta['total_flags'],meta['playoff_flags']))
print("by category:",dict(cat_counts))
print("\nAvailability-driven projection-rank movers (%d):"%len(movers))
for r in movers[:20]:
    print("  %-3s %-22s %-3s  pos-rank %2d -> %2d  (%+d)  proj %s -> %s  avail %.2f"%(r[0],r[1],r[2],r[3],r[4],r[5],r[6],r[7],r[8]))
print("\nMost-flagged players (total):")
for pl in sorted(players,key=lambda x:-x['total'])[:12]:
    if pl['total']: print("  %-22s %-3s %-3s  total %d  playoff %d  | %s"%(pl['name'],pl['pos'],pl['team'],pl['total'],pl['po'],'; '.join(f['code'] for f in pl['flags'])))
