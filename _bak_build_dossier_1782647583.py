#!/usr/bin/env python3
"""Per-TEAM scouting dossier (study format) — FULL per-player detail.
Joins every player-level source we have (fusion 20+ signals + consensus, draft_board ceiling/vol/
playoff schedule, playoff_overlay per-week, merged_rankings rank/edge, qual conviction, intel
upside/backtests/about/flags) into one rich record per player, ALL players per team.
Output: dossier_data.json -> render_dossier.py."""
import json, os, math, core
import pandas as pd
def J(p):
    p=core.P(p); return json.load(open(p,encoding='utf-8')) if os.path.exists(p) else {}
def C(*paths):
    for p in paths:
        q=core.P(p)
        if os.path.exists(q): return pd.read_csv(q)
    return pd.DataFrame()
fn=core.fn
ID=J('intel_data.json'); GP=J('gameplan.json'); CC=J('coordinator_changes_2026.json')
FUS=C('fusion_table.csv'); DBS=C('draft_board_signals.csv'); OVL=C('engine/playoff_overlay.csv')
MR=C('pipeline/merged_rankings_2026.csv','merged_rankings_2026.csv'); QUAL=C('qual_signal.csv')
def idx(df,col='name'):
    if df.empty: return {}
    df=df.copy(); df['_k']=df[col].map(fn); return {r['_k']:r for _,r in df.iterrows()}
FU=idx(FUS); DB=idx(DBS); OV=idx(OVL); QL=idx(QUAL,'name')
MRk={fn(r['Name']):r for _,r in MR.iterrows()} if not MR.empty else {}
IPL={fn(p['name']):p for p in ID.get('players',[])}
TEAMS={t['team']:t for t in ID.get('teams',[])}
STACK={s.get('team'):s for s in GP.get('stacks',[]) if s.get('team')}
DIV={'BUF':'AFC East','MIA':'AFC East','NE':'AFC East','NYJ':'AFC East','BAL':'AFC North','CIN':'AFC North','CLE':'AFC North','PIT':'AFC North','HOU':'AFC South','IND':'AFC South','JAX':'AFC South','TEN':'AFC South','DEN':'AFC West','KC':'AFC West','LAC':'AFC West','LV':'AFC West','DAL':'NFC East','NYG':'NFC East','PHI':'NFC East','WAS':'NFC East','CHI':'NFC North','DET':'NFC North','GB':'NFC North','MIN':'NFC North','ATL':'NFC South','CAR':'NFC South','NO':'NFC South','TB':'NFC South','ARI':'NFC West','LAR':'NFC West','SEA':'NFC West','SF':'NFC West'}
FULL={'ARI':'Arizona Cardinals','ATL':'Atlanta Falcons','BAL':'Baltimore Ravens','BUF':'Buffalo Bills','CAR':'Carolina Panthers','CHI':'Chicago Bears','CIN':'Cincinnati Bengals','CLE':'Cleveland Browns','DAL':'Dallas Cowboys','DEN':'Denver Broncos','DET':'Detroit Lions','GB':'Green Bay Packers','HOU':'Houston Texans','IND':'Indianapolis Colts','JAX':'Jacksonville Jaguars','KC':'Kansas City Chiefs','LAC':'Los Angeles Chargers','LAR':'Los Angeles Rams','LV':'Las Vegas Raiders','MIA':'Miami Dolphins','MIN':'Minnesota Vikings','NE':'New England Patriots','NO':'New Orleans Saints','NYG':'New York Giants','NYJ':'New York Jets','PHI':'Philadelphia Eagles','PIT':'Pittsburgh Steelers','SEA':'Seattle Seahawks','SF':'San Francisco 49ers','TB':'Tampa Bay Buccaneers','TEN':'Tennessee Titans','WAS':'Washington Commanders'}
SIG_GROUPS=[('Value & projection',[('market_pctl','Market/ADP'),('value_pctl','Value'),('proj_pctl','Projection'),('adv_pctl','Advancement'),('ceiling_pctl','Ceiling'),('spike_pctl','Spike-week'),('boom_pctl','Boom'),('sis_value_pctl','SIS value')]),
  ('Receiving skill',[('route_eff_pctl','Route eff'),('rec_eff_pctl','Rec eff'),('separation_pctl','Separation'),('yac_pctl','YAC'),('explosive_pctl','Explosive'),('coverage_proof_pctl','Coverage-proof')]),
  ('Rushing',[('run_eff_pctl','Run eff'),('rush_eff_pctl','Rush eff')]),
  ('Context',[('oline_pctl','O-line'),('protection_pctl','Protection'),('matchup_pctl','Matchup'),('coachspeak_pctl','Coachspeak')])]
def num(x):
    try:
        f=float(x); return None if math.isnan(f) else f
    except: return None
def r1(x): n=num(x); return round(n,1) if n is not None else None
def ri(x): n=num(x); return int(round(n)) if n is not None else None
def splitflags(x):
    if isinstance(x,list): return x
    if isinstance(x,str): return [s.strip() for s in x.split(';') if s.strip()]
    return []
def player_record(k):
    fu=FU.get(k); ip=IPL.get(k); db=DB.get(k); ov=OV.get(k); mr=MRk.get(k); ql=QL.get(k)
    if fu is None and ip is None: return None
    name=(fu['name'] if fu is not None else ip['name'])
    pos=(fu['pos'] if fu is not None else ip.get('pos'))
    reads=(ip or {}).get('reads',{})
    rank=ri(mr['merged_rank']) if mr is not None else (ri(fu['merged_rank']) if fu is not None else None)
    vs_adp=ri(mr['vs_adp']) if mr is not None else None
    # signals (non-null fusion percentiles, grouped)
    sig=[]
    if fu is not None:
        for gname,cols in SIG_GROUPS:
            cells=[(lab,ri(fu[c])) for c,lab in cols if c in fu and num(fu[c]) is not None]
            if cells: sig.append({'group':gname,'cells':[{'label':l,'pctl':v} for l,v in cells]})
    playoff=None
    if db is not None or ov is not None:
        playoff={'w15_opp':(db['w15_opp'] if db is not None and pd.notna(db['w15_opp']) else None),
                 'w16_opp':(db['w16_opp'] if db is not None and pd.notna(db['w16_opp']) else None),
                 'w17_game':(db['w17_game'] if db is not None and pd.notna(db['w17_game']) else None),
                 'blowup':ri(db['w17_blowup_rank']) if db is not None else None,
                 'bye':ri(db['bye']) if db is not None else None,
                 'playoff_up':r1(ov['playoff_up']) if ov is not None else None,
                 'w15_up':r1(ov['w15_up']) if ov is not None else None,
                 'w16_up':r1(ov['w16_up']) if ov is not None else None,
                 'w17_up':r1(ov['w17_up']) if ov is not None else None}
    return {'name':name,'pos':pos,'rank':rank,'adp':r1(reads.get('adp') or (fu['adp'] if fu is not None else None)),
        'vs_adp':vs_adp,'consensus':ri(fu['consensus']) if fu is not None else reads.get('consensus'),
        'divergence':ri(fu['divergence']) if fu is not None else None,'n_votes':ri(fu['n_votes']) if fu is not None else None,
        'flags':splitflags(fu['flags']) if fu is not None else (reads.get('flags') or []),
        'proj':{'pg':r1(db['proj_pg']) if db is not None else r1(reads.get('proj')),
                'ceiling':r1(db['p95']) if db is not None else None,'cv':r1(db['cv']) if db is not None else None,
                'spike':ri(db['spike']) if db is not None else None,'adv_pct':ri(num(db['adv_pct'])*100) if db is not None and num(db['adv_pct']) is not None else None,
                'ceil_pct':ri(num(db['ceil_pct'])*100) if db is not None and num(db['ceil_pct']) is not None else None,
                'matchup':reads.get('matchup'),'best_wk':reads.get('best_wk'),'best_opp':reads.get('best_opp')},
        'playoff':playoff,'signals':sig,
        'upside':(ip or {}).get('upside',[]),'backtests':(ip or {}).get('backtests',[]),
        'qual':r1(ql['qual_score']) if ql is not None else None,
        'about':[{'handle':x['handle'],'date':x['date'],'text':x['text'][:280]} for x in ((ip or {}).get('about') or [])[:3]]}
# universe = every key across fusion + intel
ALLK=set(FU)|set(IPL)
rec_by_team={}
for k in ALLK:
    r=player_record(k)
    if not r: continue
    fu=FU.get(k); ip=IPL.get(k)
    tm=(fu['team'] if fu is not None else ip.get('team'))
    rec_by_team.setdefault(tm,[]).append(r)

# ---- boom/bust + strength/weakness derivation (grounded in our signals + stability framework) ----
import statistics as _st
_cvs={'QB':[],'RB':[],'WR':[],'TE':[]}
for _t,_ps in rec_by_team.items():
    for _p in _ps:
        c=_p['proj'].get('cv')
        if c is not None and _p['pos'] in _cvs: _cvs[_p['pos']].append(c)
def _cvthr(pos):
    a=sorted(_cvs.get(pos,[]))
    if len(a)<6: return (None,None)
    return (a[int(len(a)*0.35)], a[int(len(a)*0.70)])
CVTHR={p:_cvthr(p) for p in _cvs}
def _sig(p):
    d={}
    for g in p.get('signals',[]):
        for c in g['cells']: d[c['label']]=c['pctl']
    return d
def _updim(p,dim):
    return next((u for u in (p.get('upside') or []) if u['dim']==dim),None)
FLAG_BOOM={'BOOM MERCHANT':('genuine spike-week ceiling','solid'),
 'EFFICIENCY EDGE':('elite efficiency on his touches','solid'),
 'CONSENSUS STUD':('every model signal agrees — high floor & ceiling','solid')}
FLAG_BUST={'EMPTY CALORIES':('piles up yards without TDs — touchdown-dependent ceiling','solid'),
 'FLOOR RISK':('low weekly floor — bust weeks are frequent','solid'),'EFFICIENCY TRAP':('efficiency likely unsustainable — due to regress','solid'),
 'MARKET DARLING':('ADP is ahead of the data — priced for perfection','solid'),'MARKET FADE':('market values him above our model','solid'),
 'POLARIZING':('signals disagree — unusually wide outcome range','tendency')}
def boom_bust_player(p,ident,is_alpha=False):
    pos=p['pos']; fl=set(p.get('flags') or []); s=_sig(p); boom=[]; bust=[]
    def add(L,t,c):
        if not any(t==x['t'] for x in L): L.append({'t':t,'c':c})
    def dpct(d):
        u=_updim(p,d); return (u.get('pctl') or 0) if u else 0
    def dmodel(d):
        u=_updim(p,d); return bool(u and u.get('group')=='model')
    # ---- intrinsic profile (player traits, matchup-independent) ----
    for f in (p.get('flags') or []):
        if f in FLAG_BOOM: add(boom,*FLAG_BOOM[f])
        if f in FLAG_BUST: add(bust,*FLAG_BUST[f])
    lo,hi=CVTHR.get(pos,(None,None)); cv=p['proj'].get('cv')
    if cv is not None and lo is not None:
        if cv<=lo: add(boom,'steady week to week (low volatility = high floor)','solid')
        if cv>=hi: add(bust,'boom-or-bust — volatile week to week','solid')
    vol=_updim(p,'volume')
    if vol and vol.get('group')=='model' and (vol.get('pctl') or 0)>=70: add(boom,'heavy projected target/touch share — usage-driven','solid')
    if vol and (vol.get('pctl') or 100)<=30: add(bust,'light projected usage / committee — capped floor','solid')
    if s.get('Separation',0)>=70 or s.get('Route eff',0)>=72: add(boom,'separates vs any coverage — only an elite shadow corner slows him','solid')
    deep=_updim(p,'deep')
    if deep and deep.get('group')=='off' and (deep.get('pctl') or 0)>=80: add(bust,'leans on deep production, which flips year to year','tendency')
    cont=_updim(p,'contested')
    if cont and (cont.get('pctl') or 0)>=80 and s.get('Separation',100)<=45: add(bust,'depends on contested catches — regression risk','tendency')
    # ---- opponent characteristics (what kind of defense boosts / limits HIM) ----
    if pos in ('WR','TE'):
        if 'MAN-BEATER' in fl or (dmodel('man') and dpct('man')>=70): add(boom,'vs man coverage (press/man) — wins one-on-one','solid')
        if dpct('zone')>=75: add(boom,'vs zone coverage — settles into soft spots','tendency')
        if s.get('Explosive',0)>=70 or dpct('deep')>=78:
            add(boom,'vs single-high / aggressive shells that allow deep shots','tendency')
            add(bust,'vs two-high coverage that caps the deep ball','tendency')
        if s.get('YAC',0)>=70 or dpct('yac')>=78: add(boom,'vs zone & soft underneath — room after the catch','tendency')
        if is_alpha:
            add(boom,'vs defenses with a beatable WR1 corner (WR1 funnel)','tendency')
            add(bust,'when a defense shadows him with a shutdown CB1','tendency')
        m=s.get('Matchup')
        if m is not None and m>=70: add(boom,'soft slate of opposing coverages this season','tendency')
        if m is not None and m<=28: add(bust,'brutal slate of opposing coverages this season','tendency')
    elif pos=='RB':
        if s.get('Explosive',0)>=70 or s.get('Run eff',0)>=70 or s.get('Rush eff',0)>=70:
            add(boom,'vs light boxes & soft run fronts','solid'); add(bust,'vs stout interior lines & stacked boxes','solid')
        if 'RB-ZONE-SCHEME' in fl: add(boom,'behind zone blocking vs flowing / over-pursuing fronts','solid')
        if 'RB-GAP-SCHEME' in fl: add(boom,'on gap/power runs vs undersized fronts','solid')
        if s.get('Rec eff',0)>=55 or dpct('yac')>=60: add(boom,'vs defenses soft to RB receiving (coverage LBs)','solid')
        m=s.get('Matchup')
        if m is not None and m>=70: add(boom,'soft slate of opposing run defenses this season','tendency')
        if m is not None and m<=28: add(bust,'tough slate of opposing run defenses this season','tendency')
    elif pos=='QB':
        if dmodel('man') and dpct('man')>=70: add(boom,'vs man coverage — scramble & extension lanes open','solid')
        if s.get('Protection',100)<=30: add(bust,'vs heavy pass rush / blitz (shaky protection)','solid')
        if s.get('Explosive',0)>=70 or dpct('deep')>=78: add(bust,'vs two-high shells that take away the deep ball','tendency')
        m=s.get('Matchup')
        if m is not None and m>=70: add(boom,'soft slate of opposing pass defenses this season','tendency')
        if m is not None and m<=30: add(bust,'tough slate of opposing pass defenses this season','tendency')
    return {'boom':boom[:6],'bust':bust[:6]}

def team_profile(i,d):
    S=[];W=[];ob=[];obu=[]
    rp=i.get('rk_passrate')
    if rp and rp<=8: S.append('pass-heavy offense (top-8 pass rate)')
    if rp and rp>=25: W.append('run-first offense (bottom-8 pass rate) — limited pass volume')
    if i.get('pace') and i['pace']>=70: S.append(f"fast pace ({i['pace']}th pctl) — more plays & volume")
    if i.get('pace') and i['pace']<=30: W.append(f"slow pace ({i['pace']}th pctl) — fewer plays")
    if i.get('env') and i['env']>=62: S.append(f"high implied team totals (env {i['env']})")
    if i.get('env') and i['env']<=40: W.append(f"low implied totals (env {i['env']}) — few shootouts")
    if i.get('win_total') and i['win_total']>=11: S.append(f"strong favorite ({i['win_total']} win total)")
    if i.get('win_total') and i['win_total']<=6.5: W.append(f"projected to trail often ({i['win_total']} wins)")
    if d.get('rush') is not None and d['rush']>=75: S.append(f"elite pass rush ({int(d['rush'])} pctl)")
    if d.get('cov') is not None and d['cov']>=75: S.append(f"strong coverage ({int(d['cov'])} pctl)")
    if d.get('cov') is not None and d['cov']<=30: W.append(f"soft coverage ({int(d['cov'])} pctl) — gives up passing production")
    if d.get('run') is not None and d['run']<=30: W.append(f"soft run defense ({int(d['run'])} pctl)")
    passy=bool(rp and rp<=12); runny=bool(rp and rp>=22)
    if passy and i.get('env') and i['env']>=58: ob.append('shootouts / high-total games — WR/TE/QB volume spikes')
    if i.get('pace') and i['pace']>=65: ob.append('up-tempo games — extra possessions for everyone')
    if runny: ob.append('with a lead — workhorse RB carries & goal-line work')
    if i.get('win_total') and i['win_total']>=10.5: ob.append('as favorites — sustained drives & early-down passing')
    if i.get('env') and i['env']<=42: obu.append('low-total grind games — muted ceilings across the board')
    if i.get('pace') and i['pace']<=30: obu.append('slow pace = fewer plays = lower weekly volume')
    if runny: obu.append('positive scripts kill WR volume (team milks the clock)')
    if passy and i.get('off_q') and i['off_q']<=45: obu.append('volume without efficiency — empty passing stats')
    return {'strengths':S[:6],'weaknesses':W[:6],'off_boom':ob[:4],'off_bust':obu[:4]}

POSORD={'QB':0,'RB':1,'WR':2,'TE':3}
out=[]
for tm in sorted(TEAMS):
    t=TEAMS[tm]; o=t['stats']['offense']; d=t['stats']['defense']; cc=CC.get(tm,{}) if isinstance(CC.get(tm),dict) else {}
    lean25,lean26=d.get('lean25'),d.get('lean26')
    shift=bool(lean25 and lean26 and lean25!='BALANCED' and lean26!='BALANCED' and lean25!=lean26)
    soft_lean=bool(lean25=='BALANCED' and lean26 in ('PASS','RUN'))
    _funn=[f for f in (d.get('funnels') or []) if not f.startswith('[SHIFT') and not f.startswith('2026 engine leans')][:4]
    ident={'oc_new':bool(cc.get('oc_new')),'oc':cc.get('oc_name') or cc.get('oc'),'dc_new':bool(cc.get('dc_new')),
           'dc':(d.get('dc_scheme') or {}).get('name') or cc.get('dc_name'),'dc_scheme':(d.get('dc_scheme') or {}).get('scheme'),
           'pace':o.get('pace'),'pass_rate':o.get('pass_rate'),'rk_passrate':o.get('rk_passrate'),'plays':o.get('plays'),
           'total_td':o.get('total_td'),'rk_td':o.get('rk_td'),'win_total':o.get('win_total'),'env':o.get('env'),'off_q':o.get('off_q'),
           'lean25':lean25,'lean26':lean26,'shift':shift,'soft_lean':soft_lean,'funnels':_funn}
    players=rec_by_team.get(tm,[])
    players.sort(key=lambda p:(POSORD.get(p['pos'],9),(p['rank'] if p['rank'] else 9999),(p['adp'] if p['adp'] else 9999)))
    _wrs=[pp for pp in players if pp['pos']=='WR' and pp['rank']]
    _alpha=min(_wrs,key=lambda x:x['rank'])['name'] if _wrs else None
    for _pp in players: _pp['bb']=boom_bust_player(_pp,ident,is_alpha=(_pp['pos']=='WR' and _pp['name']==_alpha))
    deff={'cov':d.get('cov'),'rush':d.get('rush'),'run':d.get('run'),'cb1':d.get('cb1'),
          'rookies':(d.get('rookies') or [])[:6],'moves':(d.get('moves') or [])[:6]}
    sk=STACK.get(tm); stack=({'qb':sk.get('qb'),'pieces':sk.get('pieces',[])} if sk else None)
    intel=[{'handle':x['handle'],'date':x['date'],'text':x['text'][:240]} for x in (t.get('tweets') or [])[:5]]
    # ---- study questions ----
    quiz=[]
    def lt(l): return {'PASS':'PASS-funnel (soft vs pass -> opp WR/TE/QB up)','RUN':'RUN-funnel (soft vs run -> opp RB up)','BALANCED':'balanced'}.get(l,l or 'n/a')
    _ln=lt(lean26)
    if shift: _ln+=f'  [FLIPPED from {lean25} in 2025 - re-learn this one]'
    elif soft_lean: _ln+=f'  (2025 balanced; 2026 engine now leans {lean26})'
    quiz.append({'q':f'2026 defensive funnel lean for {tm}?','a':_ln})
    if ident['oc_new'] or ident['dc_new']:
        bits=[]
        if ident['oc_new']: bits.append(f"new OC {ident['oc']}" if ident['oc'] else "new OC (TBD)")
        if ident['dc_new']: bits.append((f"new DC {ident['dc']}" if ident['dc'] else "new DC (TBD)")+(f" - {ident['dc_scheme']}" if ident['dc_scheme'] else ''))
        quiz.append({'q':f'Coaching changes for {tm} in 2026?','a':'; '.join(bits) or 'continuity'})
    else: quiz.append({'q':f'Coaching changes for {tm} in 2026?','a':'No new OC/DC (continuity)'})
    quiz.append({'q':f'{tm} pace + pass-rate?','a':f"pace {o.get('pace')}th pctl, pass rate {o.get('pass_rate')}% (rank #{int(o['rk_passrate']) if o.get('rk_passrate') else '?'})"})
    quiz.append({'q':f'{tm} implied environment?','a':f"win total {o.get('win_total')}, env idx {o.get('env')}, off quality {o.get('off_q')}"})
    if deff['cb1']: quiz.append({'q':f'{tm} CB1 + WR1 funnel?','a':f"{deff['cb1'].get('name')} ({deff['cb1'].get('tier')}, cov {deff['cb1'].get('cov')}) -> WR1 {deff['cb1'].get('wr1_funnel')}"})
    if players:
        tgt=min(players,key=lambda p:p['rank'] if p['rank'] else 9999)
        quiz.append({'q':f'Highest-ranked {tm} player on our board?','a':f"{tgt['name']} (our #{tgt['rank']}, ADP {tgt['adp']}, consensus {tgt['consensus']})"})
    if stack: quiz.append({'q':f'The {tm} best-ball stack?','a':f"{stack['qb']} + "+", ".join([p for p in stack['pieces'] if p!=stack['qb']][:3])})
    prof=team_profile(ident,deff)
    _ol=[_sig(pp).get('O-line') for pp in players if _sig(pp).get('O-line') is not None]
    if _ol:
        _m=_st.median(_ol)
        if _m>=68: prof['strengths'].append(f'strong O-line / pass protection ({int(_m)} pctl)')
        elif _m<=32: prof['weaknesses'].append(f'shaky O-line / pass protection ({int(_m)} pctl)')
    out.append({'team':tm,'name':FULL.get(tm,tm),'division':DIV.get(tm,''),'note':t.get('note'),'profile':prof,
        'identity':ident,'players':players,'defense':deff,'stack':stack,'intel':intel,'quiz':quiz})
json.dump({'teams':out,'meta':{'n':len(out),'n_players':sum(len(x['players']) for x in out)}},
          open(core.P('dossier_data.json'),'w'),ensure_ascii=False,indent=1)
print(f"dossier_data.json: {len(out)} teams, {sum(len(x['players']) for x in out)} player records")
