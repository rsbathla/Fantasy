#!/usr/bin/env python3
"""Per-TEAM scouting dossier — INDIVIDUAL player & team profiles.
Each player is analyzed against his OWN position cohort: archetype, genuine top strengths and genuine
flaws (relative percentiles), coverage LEAN (a strength implies its complementary weakness), volatility
shape, plus the qualitative (flags/stable traits/analyst claims). Produces, per player: a quantitative
profile, a qualitative profile, and individualized booms-when / busts-when. Teams analyzed individually
too (offensive & defensive identity + script-driven boom/bust).
Output: dossier_data.json -> render_dossier.py."""
import json, os, math, statistics as _st, core
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
_SCRUB=['route_eff_pctl','rec_eff_pctl','separation_pctl','yac_pctl','explosive_pctl','coverage_proof_pctl','run_eff_pctl','rush_eff_pctl','oline_pctl','protection_pctl','coachspeak_pctl']
for _c in _SCRUB:
    if _c in FUS.columns:
        _vc=FUS[_c].round(2).value_counts()
        _fills=[v for v,nn in _vc.items() if nn>=10]
        if _fills: FUS.loc[FUS[_c].round(2).isin(_fills),_c]=float('nan')  # imputed fill -> missing (don't assert as a real weakness)
FU=idx(FUS); DB=idx(DBS); OV=idx(OVL); QL=idx(QUAL,'name')
CLY=idx(C('pipeline/clay_2026.csv','clay_2026.csv'))
_CH=J('boom/chart2yr.json'); ALIGN={fn(k):(v.get('blend') or {}) for k,v in _CH.items()} if isinstance(_CH,dict) else {}
_FT=C('features.csv'); FEAT={fn(r['name']):r for _,r in _FT.iterrows()} if (not _FT.empty and 'name' in _FT.columns) else {}
_DS=J('division_splits.json'); DSPLIT={fn(p['name']):p for p in (_DS.get('players') or [])} if isinstance(_DS,dict) else {}
MOT=J('boom/motion.json') if os.path.exists(core.P('boom/motion.json')) else {}
COV=J('boom/coverage_split.json') if os.path.exists(core.P('boom/coverage_split.json')) else {}
DEEPQB=J('boom/deep_pass.json') if os.path.exists(core.P('boom/deep_pass.json')) else {}  # 2yr QB deep-throw rate -> QB vertical lever
# PFF/FTN situational matrix (where a player wins: man/zone, deep/short, YPRR) + 2024->2025 trend,
# and rookie college-production profiles -> surfaced on the dossier card (previously main-dossier-hidden).
PROF={fn(k2):v for k2,v in (J('profiles/player_profiles.json') or {}).items()}
RKC={fn(k2):v for k2,v in ((J('boom/rookie_college_profile.json') or {}).get('players') or {}).items()}
RKPRI={fn(k2):v for k2,v in ((J('boom/rookie_prior.json') or {}).get('priors') or {}).items()}
# 2-yr (2024+2025) man/zone confidence overlay (FantasyPoints, pulled programmatically). Re-key by fn() to match k.
MZ2={fn(k2):v for k2,v in (J('boom/manzone_2yr.json') or {}).items()} if os.path.exists(core.P('boom/manzone_2yr.json')) else {}
# SCHEME FIT (build_scheme_fit.py): coverage-specialist skill x 2026 opponent coverage tendency.
# Joined by core.fn(name); only attached when the scheme-fit 2026 team matches this dossier record's
# team (both are moves-aware, so a mismatch means a stale artifact -> degrade by omission).
_SF=J('boom/scheme_fit.json') or {}
SFIT=(_SF.get('players') or {})
def _sfview(k,tm):
    v=SFIT.get(k)
    if not v or v.get('team')!=tm: return None
    pick=lambda w:{'wk':w.get('wk'),'opp':w.get('opp'),'fit':w.get('fit'),'why':w.get('why'),'nd':bool(w.get('new_dc'))}
    return {'season':v.get('season'),'playoff':v.get('playoff'),
            'buckets':{b:{'pctl':d.get('pctl'),'rte':d.get('rte')} for b,d in (v.get('buckets') or {}).items()},
            'elite':(v.get('elite') or [])[:4],'weak':(v.get('weak') or [])[:4],
            'best':[pick(w) for w in (v.get('best') or []) if (w.get('fit') or 0)>0][:2],
            'worst':[pick(w) for w in (v.get('worst') or []) if (w.get('fit') or 0)<0][:2],
            'po':[pick(w) for w in (v.get('playoff_weeks') or [])]}
# FP audit-verified extra levers (gets-open-vs-man, contested, scramble-QB, elusive-RB) keyed by fn(name)
_XL=J('boom/fp_levers_extra.json') or {}
EXTRA={}
for _typ in ('getopen_man','contested','scramble','elusive'):
    for _nm in (_XL.get(_typ) or []): EXTRA.setdefault(fn(_nm),set()).add(_typ)
# CEILING + STACKS join (team_ceiling.json + stack_menu.json -> per-team 'ceiling' + 'stacks' blocks)
_TC=J('team_ceiling.json')
_TCEILING={core.norm_team(k):v for k,v in (_TC.get('teams') or {}).items()}
_SM=J('stack_menu.json')
_SMTEAMS={core.norm_team(k):v for k,v in (_SM.get('teams') or {}).items()}
# driver label map for human-readable top-drivers
_DRIVER_LABELS={'env_quality':'Env quality','win_total':'Win total','pace':'Pace','pass_rate':'Pass rate',
  'qb_ascend':'QB ascend','scheme_upgrade':'Scheme upgrade','concentrated_tree':'Conc. tree',
  'ol_improve':'OL improve','shootout_script':'Shootout script'}
def _ceiling_block(tm):
    c=_TCEILING.get(tm)
    if not c: return None
    drivers=c.get('drivers') or {}
    top_drivers=sorted(drivers.items(),key=lambda x:-x[1])[:4]
    return {'score':c.get('ceiling_score'),'tier':c.get('tier'),'rank':c.get('rank'),
            'top_drivers':[{'label':_DRIVER_LABELS.get(k,k),'value':round(v*100,1)} for k,v in top_drivers if v>0.01],
            'fade_flags':c.get('flags') or []}
def _stacks_block(tm):
    s=_SMTEAMS.get(tm)
    if not s: return None
    best=[]
    for st in (s.get('stacks') or [])[:3]:
        pieces=[m['name'] for m in st.get('members',[]) if m.get('pos')!='QB']
        rounds=[m.get('round_est') for m in st.get('members',[])]
        best.append({'qb':st.get('qb_name'),'pieces':pieces,
                     'round_costs':rounds,'stack_score':st.get('stack_score'),
                     'stack_type':st.get('stack_type'),'value_ct':st.get('value_ct'),
                     'qb_late':st.get('qb_late')})
    bringback=[b['name'] for b in (s.get('bringback') or [])[:3]]
    return {'best_stacks':best,'w17_opp':s.get('w17_opp'),'w17_game_env':s.get('w17_game_env'),
            'bringback':bringback}
SCH=J('scheme_2026.json') or {}  # directional 2026 scheme dials (web-verified)
if os.environ.get('NOADJ'): SCH={}
_OL26=J('boom/oline_2026.json') or {}
OLINE26={k:(v.get('pctl') if isinstance(v,dict) else v) for k,v in (_OL26.get('teams') or {}).items()}  # VERIFIED 2026 OL tier->pctl (replaces unreliable fusion oline_pctl: DET was 6.6, clearly wrong)
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
    name=(fu['name'] if fu is not None else ip['name']); pos=(fu['pos'] if fu is not None else ip.get('pos'))
    tm=(fu['team'] if fu is not None else (ip or {}).get('team'))
    reads=(ip or {}).get('reads',{})
    rank=ri(mr['merged_rank']) if mr is not None else (ri(fu['merged_rank']) if fu is not None else None)
    vs_adp=ri(mr['vs_adp']) if mr is not None else None
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
                 'blowup':ri(db['w17_blowup_rank']) if db is not None else None,'bye':ri(db['bye']) if db is not None else None,
                 'playoff_up':r1(ov['playoff_up']) if ov is not None else None,'w15_up':r1(ov['w15_up']) if ov is not None else None,
                 'w16_up':r1(ov['w16_up']) if ov is not None else None,'w17_up':r1(ov['w17_up']) if ov is not None else None}
    return {'name':name,'pos':pos,'team':tm,'rank':rank,'adp':r1(reads.get('adp') or (fu['adp'] if fu is not None else None)),
        'vs_adp':vs_adp,'consensus':ri(fu['consensus']) if fu is not None else reads.get('consensus'),
        'divergence':ri(fu['divergence']) if fu is not None else None,'n_votes':ri(fu['n_votes']) if fu is not None else None,
        'flags':splitflags(fu['flags']) if fu is not None else (reads.get('flags') or []),
        'proj':{'pg':r1(db['proj_pg']) if db is not None else r1(reads.get('proj')),'ceiling':r1(db['p95']) if db is not None else None,
                'cv':r1(db['cv']) if db is not None else None,'spike':ri(db['spike']) if db is not None else None,
                'adv_pct':ri(num(db['adv_pct'])*100) if db is not None and num(db['adv_pct']) is not None else None,
                'ceil_pct':ri(num(db['ceil_pct'])*100) if db is not None and num(db['ceil_pct']) is not None else None,
                'matchup':reads.get('matchup'),'best_wk':reads.get('best_wk'),'best_opp':reads.get('best_opp'),
                'rec':ri(CLY[k]['rec']) if k in CLY else None,'targ':ri(CLY[k]['targ']) if k in CLY else None,'carry':ri(CLY[k]['carry']) if k in CLY else None},
        'playoff':playoff,'signals':sig,'upside':(ip or {}).get('upside',[]),'backtests':(ip or {}).get('backtests',[]),
        'qual':r1(ql['qual_score']) if ql is not None else None,
        'about':[{'handle':x['handle'],'date':x['date'],'text':x['text'][:280]} for x in ((ip or {}).get('about') or [])[:3]],
        'align':{'slot':r1((ALIGN.get(k) or {}).get('slot_pct')),'wide':r1((ALIGN.get(k) or {}).get('wide_pct')),'design':r1((ALIGN.get(k) or {}).get('design_pct')),'inline':r1((ALIGN.get(k) or {}).get('inline_pct')),'back':r1((ALIGN.get(k) or {}).get('back_pct'))},
        'divsplit':DSPLIT.get(k),'motion':MOT.get(k),'cov':COV.get(k),'cov2y':MZ2.get(k),'deeppass':DEEPQB.get(k),'schemefit':_sfview(k,tm),'oline':(OLINE26.get(tm) if OLINE26.get(tm) is not None else (r1(fu['oline_pctl']) if fu is not None and 'oline_pctl' in fu else None)),
        'rz':{'i20_pg':r1((ALIGN.get(k) or {}).get('i20_pg')),'ez':ri((ALIGN.get(k) or {}).get('ez_tgt')),'rate':ri((ALIGN.get(k) or {}).get('rz_tgt_rate'))},
        'situations':(PROF.get(k) or {}).get('situations'),'trend':(PROF.get(k) or {}).get('trend'),
        'rookie_college':RKC.get(k),'rookie_prior':RKPRI.get(k)}
ALLK=set(FU)|set(IPL)
rec_by_team={}
for k in ALLK:
    r=player_record(k)
    if not r: continue
    fu=FU.get(k); ip=IPL.get(k)
    tm=(fu['team'] if fu is not None else ip.get('team'))
    rec_by_team.setdefault(tm,[]).append(r)

# ============ INDIVIDUAL PROFILE ENGINE ============
_cvs={'QB':[],'RB':[],'WR':[],'TE':[]}
for _t,_ps in rec_by_team.items():
    for _p in _ps:
        c=_p['proj'].get('cv')
        if c is not None and _p['pos'] in _cvs: _cvs[_p['pos']].append(c)
def _cvthr(pos):
    a=sorted(_cvs.get(pos,[]))
    if len(a)<6: return (None,None)
    lo,hi=a[int(len(a)*0.30)],a[int(len(a)*0.72)]
    return (None,None) if lo==hi else (lo,hi)   # skip if no spread (e.g., QB)
CVTHR={p:_cvthr(p) for p in _cvs}
def _sig(p):
    d={}
    for g in p.get('signals',[]):
        for c in g['cells']: d[c['label']]=c['pctl']
    return d
def _dim(p,d): return next((u for u in (p.get('upside') or []) if u['dim']==d),None)
def _dp(p,d):
    u=_dim(p,d); return (u.get('pctl') or 0) if u else 0
def _dmodel(p,d):
    u=_dim(p,d); return bool(u and u.get('group')=='model')
def _ord(n):
    try: n=int(round(float(n)))
    except: return str(n)
    n=max(1,min(99,n))
    s='th' if 10<=n%100<=20 else {1:'st',2:'nd',3:'rd'}.get(n%10,'th')
    return f'{n}{s}'
SIG_HI={'Route eff':'wins his routes (route-running efficiency)','Rec eff':'elite receiving efficiency (yards/route)',
 'Separation':'separates at an elite rate','YAC':'dangerous after the catch (YAC)','Explosive':'explosive big-play threat',
 'Coverage-proof':'produces even into tight coverage','Run eff':'efficient — creates yards on his own',
 'Rush eff':'breaks tackles / forces missed tackles','Protection':'works behind clean protection',
 'Matchup':'soft slate of opposing defenses this season','Coachspeak':'strong coaching-staff buy-in'}
SIG_LO={'Route eff':'doesn’t consistently win routes','Rec eff':'inefficient on his targets',
 'Separation':'rarely separates — coverage-dependent','Explosive':'limited explosive-play rate (more volume than big-plays)',
 'Run eff':'inefficient runner — blocking-dependent','Protection':'pressure-prone behind shaky protection',
 'Matchup':'brutal slate of opposing defenses this season','Boom':'low spike-week rate — tame ceiling'}
REL={'WR':['Rec eff','YAC','Explosive','Coverage-proof','Matchup'],
     'TE':['Rec eff','YAC','Explosive','Coverage-proof','Matchup'],
     'RB':['Run eff','Rush eff','Explosive','Rec eff','YAC','Matchup'],
     'QB':['Protection','Matchup','Coachspeak']}
def archetype(pos,s,p):
    g=lambda k:s.get(k) or 0
    if pos in ('WR','TE'):
        if g('Projection')>=85: base='Alpha — every-down target earner'
        elif g('Separation')>=68 or g('Route eff')>=72: base='Separation technician'
        elif g('Explosive')>=70 or _dp(p,'deep')>=80: base='Vertical field-stretcher'
        elif g('YAC')>=72: base='YAC / scheme weapon'
        elif g('Coverage-proof')>=70: base='Contested-ball winner'
        elif g('Projection')<=33: base='Depth / rotational'
        else: base='Complementary piece'
        if pos=='TE':
            if g('Projection')>=80: return 'Elite receiving TE'
            if base.startswith(('Depth','Complementary')): return base
            return 'Receiving TE'
        return base
    if pos=='RB':
        rec=p['proj'].get('rec') or 0; carry=p['proj'].get('carry') or 0
        if g('Projection')>=80 and rec>=40: return 'Three-down workhorse'
        if g('Projection')>=80: return 'Lead early-down back'
        if rec>=45 and carry<170: return 'Receiving / satellite back'
        if g('Explosive')>=72 or g('Rush eff')>=72: return 'Explosive committee back'
        if g('Projection')<=33: return 'Depth / handcuff'
        return 'Committee back'
    if pos=='QB':
        tag=' (mobile / deep arm)' if _dp(p,'deep')>=75 or _dmodel(p,'man') else ''
        if g('Projection')>=88: return 'Elite QB1 producer'+tag
        if g('Ceiling')>=70 or g('Boom')>=70: return 'High-ceiling streamer'+tag
        if g('Projection')<=40: return 'Deep-bench / backup'
        return 'Mid-tier starter'+tag
    return pos
def analyze(p,ident,is_alpha=False,alpha_name=None,behind_alpha=None):
    pos=p['pos']; fl=set(p.get('flags') or []); s=_sig(p)
    boom=[]; bust=[]
    def add(L,t,c='solid'):
        if not any(t==x['t'] for x in L): L.append({'t':t,'c':c})
    proj=s.get('Projection'); ceil=s.get('Ceiling'); bm=s.get('Boom')
    # ---- value triad (consolidated so correlated signals don't triple up) ----
    triad=[v for v in (proj,ceil,bm) if v is not None]
    hi_triad=[v for v in triad if v>=70]
    if proj is not None and proj>=88: add(boom,f'elite weekly producer — {_ord(proj)} projection at the position')
    elif ceil is not None and ceil>=72: add(boom,f'genuine league-winning ceiling ({_ord(ceil)} p95)')
    elif bm is not None and bm>=72: add(boom,f'high boom-game rate ({_ord(bm)}) — frequent spike weeks')
    elif proj is not None and proj>=66: add(boom,f'solid baseline projection ({_ord(proj)})')
    # ---- coverage lean (a strength implies its complement) ----
    man_p=_dp(p,'man') if _dmodel(p,'man') else (75 if ('MAN-BEATER' in fl or 'QB-MAN-BEATER' in fl) else None)
    zone_p=_dp(p,'zone') if _dim(p,'zone') else None
    if ('ZONE-BEATER' in fl) or ('QB-ZONE-BEATER' in fl): zone_p=max(zone_p or 0,75)
    man_beat=man_p is not None and man_p>=68
    zone_beat=zone_p is not None and zone_p>=78
    cov_agnostic=False
    if pos in ('WR','TE','QB'):
        if man_beat and zone_beat:
            add(boom,'coverage-agnostic — wins vs both man and zone'); cov_agnostic=True
        elif man_beat:
            add(boom,'vs man coverage — wins one-on-one')
            if zone_p is not None and zone_p<=45: add(bust,'quieter vs disciplined zone (his edge is vs man)','tendency')
        elif zone_beat:
            add(boom,'vs zone coverage — finds the soft spots','tendency')
            if man_p is not None and man_p<=45: add(bust,'tougher vs press-man that disrupts his release','tendency')
    # route-winning composite: collapse Separation + Route eff into ONE coherent read (no contradiction)
    if pos in ('WR','TE'):
        _go=[s[k] for k in ('Separation','Route eff') if s.get(k) is not None]
        if _go:
            _gm=max(_go)
            if _gm>=70: add(boom,f'gets open & wins routes (separation/route, {_ord(_gm)})')
            elif _gm<=33 and not cov_agnostic: add(bust,f'struggles to separate / win routes ({_ord(_gm)})')
        # alignment (slot vs boundary) — role-stable usage trait (where he lines up -> which defender he draws)
        _sp=(p.get('align') or {}).get('slot')
        if _sp is not None:
            if pos=='WR':
                if _sp>=58:
                    add(boom,'works from the slot — draws the nickel/safety, sidesteps the CB1')
                    add(bust,'limited vs a strong slot/nickel defender','tendency')
                elif _sp<=38:
                    add(boom,'outside/boundary X — wins on the perimeter')
                    if not is_alpha: add(bust,'draws the opponent’s top boundary CB — shadow/press risk','tendency')
            elif pos=='TE' and _sp>=58:
                add(boom,'frequently flexed to the slot — mismatch on LBs/safeties')
                add(bust,'neutralized by a coverage LB / strong safety','tendency')
        _dz=(p.get('align') or {}).get('design')
        if _dz is not None and _dz>=12:
            add(boom,f'manufactured usage — {int(round(_dz))}% designed targets (motion / jets / screens)')
        _rzb=p.get('rz') or {}
        if _rzb.get('i20_pg') is not None and _rzb['i20_pg']>=1.1:
            add(boom,f"heavy red-zone role ({_rzb['i20_pg']} inside-20 targets/g) — TD equity",'solid')
    _mo=p.get('motion')
    if _mo and _mo.get('motion_pct') is not None:
        _mp=_mo['motion_pct']; _lf=_mo.get('motion_lift')
        if _lf is not None and _mp>=30 and _lf>=0.4: add(boom,f"more productive in motion ({_mo['yprr_motion']} vs {_mo['yprr_nomotion']} YPRR) — scheme manufactures his looks",'solid')
        elif _lf is not None and _mp>=35 and _lf<=-0.5: add(bust,f"less efficient when moved ({_mo['yprr_motion']} vs {_mo['yprr_nomotion']} YPRR in/out of motion) — motion decoy / clear-out role",'tendency')
        elif _mp>=52: add(boom,f'heavily used in pre-snap motion ({int(round(_mp))}%) — schemed free releases','solid')
    _dv=p.get('divsplit')
    if _dv and _dv.get('n_div',0)>=8:
        if _dv['d_ceil']>=0.18 or _dv['d_mean']>=4:
            add(bust,f"fewer ceiling weeks vs division rivals ({int(round(_dv['ceil_div']*100))}% in-div vs {int(round(_dv['ceil_out']*100))}% out; {_dv['mean_div']} vs {_dv['mean_out']} FP/g)",'tendency')
        elif _dv['d_mean']<=-4:
            add(boom,f"raises his game vs division rivals ({_dv['mean_div']} vs {_dv['mean_out']} FP/g)",'tendency')
    # ---- genuine skill strengths (top of HIS profile) ----
    strengths=sorted([(s[k],k) for k in REL.get(pos,[]) if s.get(k) is not None and s[k]>=66 and k in SIG_HI],reverse=True)
    for v,k in strengths[:3]: add(boom,SIG_HI[k]+f' ({_ord(v)})')
    if _dim(p,'volume') and _dmodel(p,'volume') and _dp(p,'volume')>=68: add(boom,f'heavy projected target/touch share — usage-driven ({_ord(_dp(p,"volume"))})')
    if pos=='RB' and ('RB-ZONE-SCHEME' in fl): add(boom,'fits zone-blocking runs vs flowing / over-pursuing fronts')
    if pos=='RB' and ('RB-GAP-SCHEME' in fl): add(boom,'fits gap/power runs vs undersized fronts')
    # explosive/deep amplifier (position-specific opponent characteristics)
    if _dp(p,'deep')>=78 or (s.get('Explosive') or 0)>=72:
        if pos in ('WR','TE'):
            add(boom,'vs single-high / aggressive shells that allow deep shots','tendency'); add(bust,'vs two-high coverage that caps the deep ball','tendency')
        elif pos=='RB':
            add(boom,'vs light boxes & soft run fronts'); add(bust,'vs stacked boxes & stout interior fronts')
        elif pos=='QB':
            add(bust,'vs two-high shells that take away the deep ball','tendency')
    # pass-catching backs see MORE work vs two-high / light boxes (checkdowns + targets open up)
    if pos=='RB' and (p['proj'].get('rec') or 0)>=40:
        add(boom,'vs two-high / light boxes — checkdowns & RB targets open up (receiving back)','solid')
    if is_alpha and not (((p.get('align') or {}).get('slot') or 0)>=58):  # slot alphas avoid the boundary CB1, so no shadow read
        add(boom,'vs defenses with a beatable WR1 corner','tendency'); add(bust,'when shadowed by a shutdown CB1','tendency')
    if 'BOOM MERCHANT' in fl: add(boom,'spike-week merchant — tournament ceiling')
    if 'EFFICIENCY EDGE' in fl: add(boom,'efficiency edge on his touches')
    if 'CONSENSUS STUD' in fl: add(boom,'every model signal agrees — high floor & ceiling')
    # ---- genuine flaws (bottom of HIS profile) ----
    weaks=sorted([(s[k],k) for k in REL.get(pos,[]) if s.get(k) is not None and s[k]<=33 and k in SIG_LO])
    for v,k in weaks[:3]: add(bust,SIG_LO[k]+f' ({_ord(v)})')
    if (ceil is not None and ceil<=35) and (proj is None or proj<70): add(bust,f'capped weekly ceiling ({_ord(ceil)}) — rarely wins you a week')
    if bm is not None and bm<=20: add(bust,f'very low boom rate ({_ord(bm)}) — tame week to week')
    lo,hi=CVTHR.get(pos,(None,None)); cv=p['proj'].get('cv')
    if cv is not None and lo is not None:
        if cv<=lo: add(boom,'steady week to week (low volatility = high floor)')
        if cv>=hi: add(bust,'boom-or-bust — volatile week to week')
    if _dim(p,'volume') and (_dp(p,'volume')<=30): add(bust,'light projected usage / committee — capped floor')
    if behind_alpha: add(bust,f'competes for targets behind {behind_alpha}')
    if 'EMPTY CALORIES' in fl: add(bust,'piles up yards without TDs — touchdown-dependent')
    if 'EFFICIENCY TRAP' in fl: add(bust,'efficiency likely unsustainable — due to regress')
    if 'FLOOR RISK' in fl: add(bust,'low weekly floor — bust weeks frequent')
    if 'MARKET DARLING' in fl: add(bust,'ADP ahead of the data — priced for perfection')
    if 'MARKET FADE' in fl: add(bust,'market values him above our model')
    dp=_dim(p,'deep')
    if dp and dp.get('group')=='off' and (dp.get('pctl') or 0)>=82: add(bust,'leans on deep production, which flips year to year','tendency')
    cont=_dim(p,'contested')
    if cont and (cont.get('pctl') or 0)>=82 and (s.get('Separation') or 100)<=45: add(bust,'depends on contested catches — regression risk','tendency')
    if pos=='QB' and (s.get('Protection') or 100)<=30: add(bust,'vs heavy pass rush / blitz when protection breaks down')
    # ---- fallbacks so every player has a real read ----
    if not boom:
        cand=sorted([(s[k],k) for k in REL.get(pos,[]) if s.get(k) is not None and k in SIG_HI],reverse=True)
        if cand and cand[0][0]>=50: add(boom,'his one edge: '+SIG_HI[cand[0][1]]+f' ({_ord(cand[0][0])})')
        else: add(boom,'contingent value — needs an injury/role opening ahead of him','tendency')
    if not bust:
        if proj is not None and proj>=85: add(bust,'few weaknesses — chief risk is price & a tough slate','tendency')
        else:
            cand=sorted([(s[k],k) for k in REL.get(pos,[]) if s.get(k) is not None and k in SIG_LO])
            if cand: add(bust,SIG_LO[cand[0][1]]+f' ({_ord(cand[0][0])})')
            else: add(bust,'limited standalone role','tendency')
    # ---- quantitative profile line ----
    vt=_dp(p,'volume')
    vol_tier=('elite-volume' if vt>=80 else 'heavy-volume' if vt>=60 else 'rotational-volume' if vt and vt<40 else None)
    shape=None
    if cv is not None and lo is not None: shape=('low-variance' if cv<=lo else 'high-variance' if cv>=hi else 'medium-variance')
    qbits=[]
    if proj is not None: qbits.append(f'{_ord(proj)} projection')
    if ceil is not None: qbits.append(f'{_ord(ceil)} ceiling')
    if bm is not None: qbits.append(f'{_ord(bm)} boom')
    if vol_tier: qbits.append(vol_tier)
    if shape: qbits.append(shape)
    _spq=(p.get('align') or {}).get('slot')
    if pos in ('WR','TE') and _spq is not None: qbits.append(f"{int(round(_spq))}% slot")
    _moq=p.get('motion')
    if _moq and _moq.get('motion_pct') is not None: qbits.append(f"{int(round(_moq['motion_pct']))}% motion")
    quant={'archetype':archetype(pos,s,p),'line':' · '.join(qbits)}
    # ---- qualitative profile ----
    FLAGTXT={'MAN-BEATER':'beats man','QB-MAN-BEATER':'beats man','ZONE-BEATER':'zone-beater','QB-ZONE-BEATER':'zone-beater',
     'SEPARATION KING':'elite separator','BOOM MERCHANT':'spike-week ceiling','EFFICIENCY EDGE':'efficiency edge',
     'EFFICIENCY TRAP':'efficiency may regress','EMPTY CALORIES':'yards but TD-light','FLOOR RISK':'low floor',
     'RB-ZONE-SCHEME':'zone-scheme fit','RB-GAP-SCHEME':'gap-scheme fit','CONSENSUS STUD':'consensus stud',
     'MARKET DARLING':'ADP ahead of model','MARKET FADE':'market over model','POLARIZING':'polarizing (signals split)'}
    traits=[]
    for f in (p.get('flags') or []):
        if f in FLAGTXT and FLAGTXT[f] not in traits: traits.append(FLAGTXT[f])
    for u in (p.get('upside') or []):
        if u.get('group')=='model' and u.get('stability') in ('STABLE','MODERATE'):
            tt=f"{u['dim']} ({u['stability'].lower()})"
            if tt not in traits: traits.append(tt)
    bts=p.get('backtests') or []
    claim=None
    if bts:
        b0=sorted(bts,key=lambda b:0 if 'STRONG' in (b.get('verdict') or '') else 1)[0]
        claim=f"{b0.get('verdict')} — {b0.get('dim')}"+(f" (@{', @'.join(b0.get('by') or [])})" if b0.get('by') else '')
    nab=len(p.get('about') or [])
    qnote_bits=[]
    if p.get('qual') is not None: qnote_bits.append(f"analyst conviction {p['qual']}")
    if nab: qnote_bits.append(f"{nab} recent note(s)")
    _spt=(p.get('align') or {}).get('slot'); _inl=(p.get('align') or {}).get('inline'); _dzt=(p.get('align') or {}).get('design')
    if _dzt is not None and _dzt>=12: traits.insert(0,'schemed usage')
    _motx=p.get('motion')
    if _motx and (_motx.get('motion_pct') or 0)>=52: traits.insert(0,'motion-heavy')
    if _spt is not None:
        if pos=='WR': traits.insert(0,'slot role' if _spt>=58 else ('boundary X' if _spt<=38 else 'flex alignment'))
        elif pos=='TE': traits.insert(0,'inline TE' if (_inl is not None and _inl>=45) else ('move TE (slot)' if _spt>=55 else 'flex TE'))
    qual_prof={'traits':traits[:9],'claim':claim,'note':'; '.join(qnote_bits)}
    # ---- ceiling levers: opponent-controllable splits where he shows a real edge (+ the matchup trait that activates each) ----
    lev=[]
    def addl(t,c='solid'):
        if not any(t==x['t'] for x in lev): lev.append({'t':t,'c':c})
    _cv=p.get('cov')
    if _cv and _cv.get('is_qb') and _cv.get('man_pctl') is not None:
        if _cv['man_pctl']>=70: addl(f"handles man coverage — {_cv['man_ypa']} Y/A vs man (top-tier QB) → exploit man-heavy / blitz-heavy defenses",'solid')
        elif _cv['man_pctl']<=30: addl(f"struggles vs man — {_cv['man_ypa']} Y/A vs man (bottom-tier) → fades vs man-heavy / blitz defenses",'tendency')
    _c2=p.get('cov2y')
    if _c2 and _c2.get('read'):
        # 2-yr (2024+2025) verified read: only a CONSISTENT same-direction lean both seasons counts
        if _c2['read']=='man-beater':
            addl(f"wins vs man — {_c2['man2y']} vs {_c2['zon2y']} YPRR man/zone, BOTH 2024 & 2025 → ceiling vs press / man-heavy defenses",'solid')
        elif _c2['read']=='zone-beater':
            addl(f"more efficient vs zone — {_c2['zon2y']} vs {_c2['man2y']} YPRR zone/man, both seasons (quieter vs man) → ceiling vs zone-heavy defenses",'tendency')
        # read=='mixed' -> NO coverage lever: his man/zone split is year-to-year noise (delta YoY r=0.18)
    elif _cv and not _cv.get('is_qb') and _cv.get('delta') is not None:
        # only 2025 data -> single-year, treat as a soft tendency (man/zone delta barely persists YoY)
        if _cv['delta']>=0.5: addl(f"man lean — {_cv['man_yprr']} vs {_cv['zone_yprr']} YPRR man/zone (2025 only, single-year) → man-heavy defenses",'tendency')
        elif _cv['delta']<=-0.5: addl(f"zone lean — {_cv['zone_yprr']} vs {_cv['man_yprr']} YPRR zone/man (2025 only, single-year) → zone-heavy defenses",'tendency')
    _xl=EXTRA.get(fn(p.get('name') or ''),set())
    if 'getopen_man' in _xl and pos in ('WR','TE'): addl("wins separation vs man \u2014 top-tier man-coverage separation-wins (2yr) \u2192 ceiling vs press / man-heavy defenses",'solid')
    if 'contested' in _xl and pos in ('WR','TE'): addl("contested-catch winner \u2014 high contested-target rate (2yr) \u2192 jump-ball ceiling vs press / man-heavy defenses",'tendency')
    if 'scramble' in _xl and pos=='QB': addl("scrambling QB \u2014 high scramble rate (2yr) \u2192 rushing ceiling vs man-heavy coverage (lanes open)",'solid')
    if 'elusive' in _xl and pos=='RB': addl("elusive \u2014 forces missed tackles at a high clip (2yr) \u2192 explosive ceiling vs poor-tackling / soft run fronts",'tendency')
    _mv=p.get('motion')
    if _mv and _mv.get('motion_lift') is not None and (_mv.get('motion_pct') or 0)>=30 and _mv['motion_lift']>=0.4:
        addl(f"motion weapon — {_mv['yprr_motion']} vs {_mv['yprr_nomotion']} YPRR in/out of motion → offenses that scheme him in motion",'solid')
    _al=p.get('align') or {}
    if pos=='WR' and _al.get('slot') is not None:
        if _al['slot']>=58: addl(f"slot-heavy ({int(round(_al['slot']))}%) → defenses with a weak nickel/slot CB",'solid')
        elif _al['slot']<=38: addl("boundary X → defenses with a beatable outside CB / soft single-high",'solid')
    if pos in ('WR','TE') and ((s.get('Explosive') or 0)>=70 or _dp(p,'deep')>=78):
        addl("vertical / big-play threat → single-high or aggressive shells that allow shots",'tendency')
    if pos=='QB':
        _dqb=p.get('deeppass') or {}
        if _dqb.get('deep_pctl') is not None and _dqb['deep_pctl']>=70:
            addl(f"vertical / big-play passer — {_dqb['deep_rate']}% deep-throw rate (2yr, {_ord(_dqb['deep_pctl'])} pctl among QBs) → single-high / soft-deep shells that allow shots",'tendency')
    _rzlv=p.get('rz') or {}
    if _rzlv.get('i20_pg') is not None and _rzlv['i20_pg']>=1.1:
        addl(f"red-zone target hog ({_rzlv['i20_pg']} inside-20 looks/g, {_rzlv.get('ez') or 0} end-zone) → TD/ceiling equity vs RZ-soft defenses",'solid')
    if pos=='RB' and (p['proj'].get('rec') or 0)>=40:
        addl("pass-catching back → light-box / two-high looks (checkdowns & targets open up)",'solid')
    if s.get('Matchup') is not None and s['Matchup']>=70:
        addl("soft slate — favorable opposing defenses on this year's schedule",'tendency')
    # shootout / high-total: activated per-week on the OPPONENT's implied-total environment (team_env.json,
    # which blends off_q with real Vegas-derived implied totals) — so a strong-offense opponent lifts
    # QB / pass-catcher ceiling regardless of that opponent's coverage scheme.
    _passy = (pos=='QB') or (pos in ('WR','TE') and _dp(p,'volume')>=55) or (pos=='RB' and (p['proj'].get('rec') or 0)>=40)
    if _passy:
        addl("shootout / high-total environment → opponents whose offenses drive up the game total",'solid' if pos=='QB' else 'tendency')
    # reconcile coverage reads so no player carries opposing man/zone levers (count would double-activate)
    _go=[x for x in lev if 'wins separation vs man' in x['t']]
    _mb=[x for x in lev if 'wins vs man' in x['t']]
    _zb=[x for x in lev if 'more efficient vs zone' in x['t']]
    if _go and _mb: lev=[x for x in lev if 'wins separation vs man' not in x['t']]  # redundant man reads -> keep the 2yr YPRR man-beater
    elif _go and _zb: lev=[x for x in lev if 'more efficient vs zone' not in x['t']]  # separation-vs-man (stable skill) overrides the noisier zone YPRR lean
    # ---- 2026 scheme adjustments to this player's OWN levers (directional, web-verified scheme_2026.json) ----
    _so=(SCH.get(ident.get('team')) or {}).get('off') or {}
    if _so:
        def _dialk(t):
            tl=t.lower()
            if 'motion weapon' in tl: return 'motion'
            if 'vertical' in tl or 'big-play' in tl: return 'vertical'
            if 'pass-catching back' in tl: return 'passcatch'
            if 'scrambling qb' in tl: return 'scramble'
            return None
        for x in list(lev):
            dk=_dialk(x['t'])
            if dk is None or dk not in _so: continue
            v=_so[dk]
            if v>0:
                if '(new scheme' not in x['t']: x['t']+=' (new scheme fits)'
            elif v<0:
                if dk=='vertical' and x in lev:
                    lev.remove(x); continue
                if x['c']=='solid': x['c']='tendency'
                if '(new scheme' not in x['t']: x['t']+=' (new scheme reduces this usage)'
    _ol=(None if os.environ.get('NOADJ') else p.get('oline'))   # OL pass-pro modulates deep/vertical
    if _ol is not None:
        for x in list(lev):
            tl=x['t'].lower()
            if ('vertical' in tl or 'big-play' in tl):
                if _ol<=30 and x in lev: lev.remove(x)
                elif _ol>=70 and '(OL' not in x['t']: x['t']+=' (OL holds up — time for shots)'
    p['levers']=lev[:6]
    p['quant']=quant; p['qual_profile']=qual_prof; p['bb']={'boom':boom[:8],'bust':bust[:8]}

# ============ TEAM PROFILE ============
def team_identity(i,d):
    off=[]; deff=[]
    rp=i.get('rk_passrate')
    lean='pass-leaning' if (rp and rp<=12) else ('run-leaning' if (rp and rp>=22) else 'balanced')
    pace='up-tempo' if (i.get('pace') and i['pace']>=66) else ('slow-paced' if (i.get('pace') and i['pace']<=33) else 'average-pace')
    tot='high-total' if (i.get('env') and i['env']>=60) else ('low-total' if (i.get('env') and i['env']<=40) else 'mid-total')
    mot=i.get('motion')
    mtxt=(f", {'high' if mot>=60 else 'low' if mot<=40 else 'moderate'}-motion ({int(round(mot))}%)" if mot is not None else '')
    off_line=f"{pace}, {lean} offense{mtxt} — {tot} environment (env {i.get('env')}, {i.get('win_total')} win total)"
    cv=d.get('cov'); rn=d.get('run'); rs=d.get('rush')
    dparts=[]
    if cv is not None: dparts.append(('strong' if cv>=66 else 'soft' if cv<=33 else 'average')+' coverage')
    if rn is not None: dparts.append(('stout' if rn>=66 else 'soft' if rn<=33 else 'average')+' run D')
    if rs is not None: dparts.append(('heavy' if rs>=66 else 'light' if rs<=33 else 'average')+' pass rush')
    funnel=i.get('lean26')
    def_line=', '.join(dparts)+(f" — {funnel}-funnel" if funnel and funnel!='BALANCED' else '')
    return off_line, def_line
def team_profile(i,d,players):
    S=[];W=[];ob=[];obu=[]
    rp=i.get('rk_passrate')
    if rp and rp<=8: S.append('pass-heavy offense (top-8 pass rate)')
    if rp and rp>=25: W.append('run-first offense (bottom-8 pass rate) — limited pass volume')
    if i.get('pace') and i['pace']>=70: S.append(f"fast pace ({_ord(i['pace'])} pctl) — more plays & volume")
    if i.get('pace') and i['pace']<=30: W.append(f"slow pace ({_ord(i['pace'])} pctl) — fewer plays")
    if i.get('env') and i['env']>=62: S.append(f"high implied team totals (env {i['env']})")
    if i.get('env') and i['env']<=40: W.append(f"low implied totals (env {i['env']}) — few shootouts")
    if i.get('win_total') and i['win_total']>=11: S.append(f"strong favorite ({i['win_total']} win total)")
    if i.get('win_total') and i['win_total']<=6.5: W.append(f"projected to trail often ({i['win_total']} wins)")
    if d.get('rush') is not None and d['rush']>=75: S.append(f"elite pass rush ({int(d['rush'])} pctl)")
    if d.get('cov') is not None and d['cov']>=75: S.append(f"strong coverage ({int(d['cov'])} pctl)")
    if d.get('cov') is not None and d['cov']<=30: W.append(f"soft coverage ({int(d['cov'])} pctl) — gives up passing production")
    if d.get('run') is not None and d['run']<=30: W.append(f"soft run defense ({int(d['run'])} pctl)")
    if i.get('motion') is not None:
        if i['motion']>=62: S.append(f"high pre-snap motion ({int(round(i['motion']))}%) — manufactured looks & easier reads")
        elif i['motion']<=38: W.append(f"static, low-motion scheme ({int(round(i['motion']))}%)")
    ol=[_sig(pp).get('O-line') for pp in players if _sig(pp).get('O-line') is not None]
    if ol:
        m=_st.median(ol)
        if m>=68: S.append(f"strong O-line / pass protection ({int(m)} pctl)")
        elif m<=32: W.append(f"shaky O-line / pass protection ({int(m)} pctl)")
    passy=bool(rp and rp<=12); runny=bool(rp and rp>=22)
    if passy and i.get('env') and i['env']>=58: ob.append('shootouts / high-total games — WR/TE/QB volume spikes')
    if i.get('pace') and i['pace']>=65: ob.append('up-tempo games — extra possessions for everyone')
    if runny: ob.append('with a lead — workhorse RB carries & goal-line work')
    if i.get('win_total') and i['win_total']>=10.5: ob.append('as favorites — sustained drives & early-down passing')
    if i.get('env') and i['env']<=42: obu.append('low-total grind games — muted ceilings across the board')
    if i.get('pace') and i['pace']<=30: obu.append('slow pace = fewer plays = lower weekly volume')
    if runny: obu.append('positive scripts kill WR volume (team milks the clock)')
    if passy and i.get('off_q') and i['off_q']<=45: obu.append('volume without efficiency — empty passing stats')
    oid,did=team_identity(i,d)
    return {'off_id':oid,'def_id':did,'strengths':S[:6],'weaknesses':W[:6],'off_boom':ob[:4],'off_bust':obu[:4]}

# ============ ASSEMBLE ============
POSORD={'QB':0,'RB':1,'WR':2,'TE':3}
out=[]
for tm in sorted(TEAMS):
    t=TEAMS[tm]; o=t['stats']['offense']; d=t['stats']['defense']; cc=CC.get(tm,{}) if isinstance(CC.get(tm),dict) else {}
    lean25,lean26=d.get('lean25'),d.get('lean26')
    shift=bool(lean25 and lean26 and lean25!='BALANCED' and lean26!='BALANCED' and lean25!=lean26)
    soft_lean=bool(lean25=='BALANCED' and lean26 in ('PASS','RUN'))
    _funn=[f for f in (d.get('funnels') or []) if not f.startswith('[SHIFT') and not f.startswith('2026 engine leans')][:4]
    ident={'team':tm,'oc_new':bool(cc.get('oc_new')),'oc':cc.get('oc_name') or cc.get('oc'),'dc_new':bool(cc.get('dc_new')),
           'dc':(d.get('dc_scheme') or {}).get('name') or cc.get('dc_name'),'dc_scheme':(d.get('dc_scheme') or {}).get('scheme'),
           'pace':o.get('pace'),'pass_rate':o.get('pass_rate'),'rk_passrate':o.get('rk_passrate'),'plays':o.get('plays'),
           'total_td':o.get('total_td'),'rk_td':o.get('rk_td'),'win_total':o.get('win_total'),'env':o.get('env'),'off_q':o.get('off_q'),
           'lean25':lean25,'lean26':lean26,'shift':shift,'soft_lean':soft_lean,'funnels':_funn}
    players=rec_by_team.get(tm,[])
    players.sort(key=lambda p:(POSORD.get(p['pos'],9),(p['rank'] if p['rank'] else 9999),(p['adp'] if p['adp'] else 9999)))
    _mv=[]
    for pp in players:
        fr=FEAT.get(fn(pp['name']))
        if fr is not None:
            mv=num(fr.get('team_motion')) if hasattr(fr,'get') else None
            if mv is not None: _mv.append(mv)
    ident['motion']=round(_st.median(_mv),1) if _mv else None
    deff={'cov':d.get('cov'),'rush':d.get('rush'),'run':d.get('run'),'cb1':d.get('cb1'),'rookies':(d.get('rookies') or [])[:6],'moves':(d.get('moves') or [])[:6]}
    # team-relative alpha context
    wrs=[pp for pp in players if pp['pos']=='WR' and pp['rank']]
    alpha=min(wrs,key=lambda x:x['rank']) if wrs else None
    alpha_name=alpha['name'] if alpha else None
    alpha_strong=bool(alpha and (_sig(alpha).get('Projection') or 0)>=80)
    for pp in players:
        behind = alpha_name if (alpha_strong and pp['pos']=='WR' and pp is not alpha) else None
        analyze(pp,ident,is_alpha=(pp is alpha and (_sig(alpha).get('Projection') or 0)>=72),alpha_name=alpha_name,behind_alpha=behind)
    prof=team_profile(ident,deff,players)
    sk=STACK.get(tm); stack=({'qb':sk.get('qb'),'pieces':sk.get('pieces',[])} if sk else None)
    intel=[{'handle':x['handle'],'date':x['date'],'text':x['text'][:240]} for x in (t.get('tweets') or [])[:5]]
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
    quiz.append({'q':f'{tm} offensive identity?','a':prof['off_id']})
    quiz.append({'q':f'{tm} implied environment?','a':f"win total {o.get('win_total')}, env idx {o.get('env')}, off quality {o.get('off_q')}"})
    if deff['cb1']: quiz.append({'q':f'{tm} CB1 + WR1 funnel?','a':f"{deff['cb1'].get('name')} ({deff['cb1'].get('tier')}, cov {deff['cb1'].get('cov')}) -> WR1 {deff['cb1'].get('wr1_funnel')}"})
    if players:
        tgt=min(players,key=lambda p:p['rank'] if p['rank'] else 9999)
        quiz.append({'q':f'Highest-ranked {tm} player + why he booms?','a':f"{tgt['name']} (our #{tgt['rank']}): "+'; '.join(x['t'] for x in tgt['bb']['boom'][:2])})
    if stack: quiz.append({'q':f'The {tm} best-ball stack?','a':f"{stack['qb']} + "+", ".join([p for p in stack['pieces'] if p!=stack['qb']][:3])})
    out.append({'team':tm,'name':FULL.get(tm,tm),'division':DIV.get(tm,''),'note':t.get('note'),'profile':prof,
        'identity':ident,'players':players,'defense':deff,'stack':stack,'intel':intel,'quiz':quiz,
        'ceiling':_ceiling_block(tm),'stacks':_stacks_block(tm)})
json.dump({'teams':out,'meta':{'n':len(out),'n_players':sum(len(x['players']) for x in out)}},
          open(core.P('dossier_data.json'),'w'),ensure_ascii=False,indent=1)
print(f"dossier_data.json: {len(out)} teams, {sum(len(x['players']) for x in out)} player records")
