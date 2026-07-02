#!/usr/bin/env python3
"""Tier-weighted per-week "ceiling-levers stacked" count.

For every player, map his ceiling levers (built in build_dossier.py, each tagged solid/tendency) onto his
ACTUAL 2026 weekly opponents (boom/schedule2026.json) and score how favorable each week is:

  weekly_score = sum over activated levers of  tier_weight * activation_intensity

  tier_weight:  solid = 1.0,  tendency = 0.5
  activation_intensity in [0,1] = how strongly the opponent's trait turns the lever ON
     (e.g. a man-beater vs the #1 man-coverage defense ~ 1.0; vs a zone team ~ 0).

Opponent activators (all already in the repo, 2026-projected where available):
  - man rate:        coordinator_scheme_2026.json teams[T].man_rate_adj
  - coverage shells: boom/defense_shell.json  (man%, single_high%, two_high%) [new-DC teams regressed to mean]
  - tackling allowed: boom/defense_tackling.json (elusive activator) [new-DC teams regressed to mean]
  - unit strength:   defense.json teams[T]     (pass_cov_pctl, pass_rush_pctl, run_def_pctl ; higher = tougher)
                     [new-DC teams: pass_rush_pctl blended toward the coordinator 2026 sack projection
                      (coordinator_scheme_2026.json sack_rate_adj), conf-gated + bounded -- see SACK_COORD_W]

Lever -> activator mapping (mechanism):
  man_beater / qb_man / contested / scramble_qb / gets_open_man  -> opponent plays a lot of MAN
  zone_beater                                                    -> opponent plays a lot of ZONE (low man)
  vertical / deep                                                -> opponent single-high heavy + soft deep coverage
  slot / boundary                                               -> opponent weak coverage unit (beatable CBs/nickel)
  passcatch_rb                                                  -> opponent two-high / light boxes (checkdowns open)
  redzone                                                       -> opponent weak overall defense (TD-soft)
  shootout                                                      -> weak opponent pass D (+ dome) => high total
  (motion / soft_slate are not single-opponent-activated -> excluded from the weekly count)

Output: writes p['lever_cal'] (per-week) and p['lever_sum'] back into dossier_data.json, and a standalone
lever_count.json. Run AFTER build_dossier.py, BEFORE render_dossier.py.
"""
import json, os, statistics
H = os.path.dirname(os.path.abspath(__file__))
def J(p):
    fp=os.path.join(H,p)
    return json.load(open(fp,encoding='utf-8')) if os.path.exists(fp) else None

# ---- canonical team codes (reconcile FP / shell / schedule variants) ----
NORM={'ARZ':'ARI','BLT':'BAL','CLV':'CLE','HST':'HOU','JAC':'JAX','LA':'LAR','OAK':'LV','SD':'LAC','WSH':'WAS','SL':'LAR','LVR':'LV'}
def nt(t):
    if not t: return t
    t=str(t).upper(); return NORM.get(t,t)

SCHED={nt(k):v for k,v in (J('boom/schedule2026.json') or {}).items()}
SHELL={nt(k):v for k,v in (J('boom/defense_shell.json') or {}).items()}
_cs=J('coordinator_scheme_2026.json') or {}
COORD={nt(k):v for k,v in (_cs.get('teams') or {}).items()}
_df=J('defense.json') or {}
DEF={nt(k):v for k,v in (_df.get('teams') or {}).items()}
# opponent implied-total ENVIRONMENT (team_env.json blends off_q with real Vegas-derived implied totals) -> shootout activator
ENV={nt(k):v.get('env_idx') for k,v in (J('boom/team_env.json') or {}).items() if isinstance(v,dict)}
# per-defense missed-tackles-allowed (FantasyPoints 2025 Defense rushing) -> elusive-RB activator
TACK={nt(k):v.get('leaky_pctl') for k,v in (J('boom/defense_tackling.json') or {}).items() if isinstance(v,dict) and v.get('leaky_pctl') is not None}
def tackLeaky(t):
    v=TACK.get(t); return None if v is None else v/100.0

# ---- 2026 DC-scheme DIRECTIONAL shell adjustment (web-verified scheme_2026.json) -------------------
# New-DC teams: push 2025 shells toward the researched scheme lean (single/two-high dials, up OR down).
# Known-neutral DC (all dials 0) -> keep 2025. No scheme entry (truly unknown) -> regress to mean.
SCHEME=J('scheme_2026.json') or {}
NONUSABLE=set((J('boom/roster_flags_2026.json') or {}).get('non_usable',{}).keys())  # verified out for 2026
SCHDEF={nt(k):(v.get('def') or {}) for k,v in SCHEME.items() if isinstance(v,dict)}
DCNEW={t for t,v in COORD.items() if isinstance(v,dict) and v.get('dc_new')}
if os.environ.get('NOADJ'): DCNEW=set()
def _lam(t): return 0.5 if (COORD.get(t) or {}).get('conf')=='regress-mean' else 0.3
# ---- coordinator-aware PRESSURE (2026 sack projection -> pass_rush_pctl), new-DC teams only --------
# coordinator_scheme_2026.json sack_rate_adj is the per-team 2026 sack projection (blend with the DC's
# prior-stop sack rate when researched, else 2025 regressed to league mean -- build_coordinator_scheme.py).
# defense.json pass_rush_pctl is roster-aware but scheme-BLIND, so for DCNEW teams we pull it toward the
# coordinator projection, consuming sack_rate_adj the same way man_rate_adj is consumed above/below:
#   * ported LEAGUE-RELATIVELY: sack_rate_adj -> its rank percentile on the registry's own scale (units
#     of a frozen sack-rate table never touch the pctl scale raw);
#   * conf-GATED: pull weight = SACK_COORD_W * (1-lambda_conf) -> researched 'blend-prior' DCs (lam .3)
#     pull 0.7x, unknown 'regress-mean' DCs (lam .5) pull 0.5x of SACK_COORD_W;
#   * BOUNDED: the shift is capped at +/-SACK_PCTL_CAP percentile points (a refinement, not a rewrite;
#     pass_rush_pctl only tempers the shootout lever via passD_strength, so the lever effect is small).
# REVERT: set SACK_COORD_W=0.0 -> pass_rush_pctl stays roster-only (exact prior behavior). NOADJ=1 also
# disables it together with every other new-DC adjustment.
SACK_COORD_W=0.5     # coordinator weight on the pressure blend (0 = off -> pre-wiring behavior)
SACK_PCTL_CAP=12.0   # max percentile-point move of pass_rush_pctl
_sk_vals=sorted(v for v in ((COORD.get(x) or {}).get('sack_rate_adj') for x in SCHED) if v is not None)
def _ms(key):
    vs=[SHELL[t][key] for t in SHELL if isinstance(SHELL[t],dict) and SHELL[t].get(key) is not None]
    return (sum(vs)/len(vs), (statistics.pstdev(vs) if len(vs)>1 else 0.0)) if vs else (None,None)
_M={k:_ms(k) for k in ('single_high','two_high')}
_ndir=0; _nreg=0; _nsack=0
for t in DCNEW:
    has=t in SCHDEF; d=SCHDEF.get(t) or {}
    _mr=(COORD.get(t) or {}).get('man_rate_adj'); _md=d.get('man',0) if has else 0   # refine regressed man-rate toward researched lean
    if _mr is not None and _md!=0:
        COORD[t]['man_rate_adj']=round(_mr+_md*4.0,1)
    for key in ('single_high','two_high'):
        m,sd=_M[key]
        if m is None or not (isinstance(SHELL.get(t),dict) and SHELL[t].get(key) is not None): continue
        if has:
            dial=d.get(key,0)
            if dial!=0:
                tgt=m+dial*(sd or 0.0); SHELL[t][key]=round(0.5*SHELL[t][key]+0.5*tgt,1); _ndir+=1
            # dial==0 -> known-neutral, keep 2025
        else:
            SHELL[t][key]=round(m+(1-_lam(t))*(SHELL[t][key]-m),1); _nreg+=1
    if TACK.get(t) is not None:  # tackling = personnel-driven -> conf-weighted regress toward median
        TACK[t]=round(50+(1-_lam(t))*(TACK[t]-50))
    _sk=(COORD.get(t) or {}).get('sack_rate_adj'); _pr=(DEF.get(t) or {}).get('pass_rush_pctl')  # coordinator-aware pressure
    if SACK_COORD_W and _sk is not None and _pr is not None and _sk_vals:
        _skP=100.0*sum(1 for x in _sk_vals if x<=_sk)/len(_sk_vals)   # league-relative port of the 2026 sack projection
        _shift=max(-SACK_PCTL_CAP,min(SACK_PCTL_CAP,SACK_COORD_W*(1-_lam(t))*(_skP-_pr)))
        DEF[t]['pass_rush_pctl']=round(_pr+_shift,1); _nsack+=1
print(f"[dc-scheme] {len(DCNEW)} new-DC teams: {_ndir} shell-dials pushed toward researched lean, {_nreg} regressed (unknown), {_nsack} pass_rush_pctl sack-blended (w={SACK_COORD_W})") if __name__=='__main__' else None

def pctls(vals):
    """value -> percentile (0..1) within the league, by rank."""
    xs=sorted(v for v in vals if v is not None)
    if not xs: return lambda v:0.5
    def f(v):
        if v is None: return 0.5
        c=sum(1 for x in xs if x<=v); return c/len(xs)
    return f
# league percentile functions for opponent traits
manP   = pctls([ (COORD.get(t) or {}).get('man_rate_adj') for t in SCHED ])
shP    = pctls([ (SHELL.get(t) or {}).get('single_high') for t in SCHED ])
thP    = pctls([ (SHELL.get(t) or {}).get('two_high')    for t in SCHED ])
envP   = pctls([ ENV.get(t) for t in SCHED ])   # opponent high-total environment percentile
# defense.json pctls are already 0..100 (higher = tougher). weakness = 1 - pctl/100.
def covWeak(t):   v=(DEF.get(t) or {}).get('pass_cov_pctl');  return None if v is None else 1-v/100.0
def rushStr(t):   v=(DEF.get(t) or {}).get('pass_rush_pctl'); return None if v is None else v/100.0
def runWeak(t):   v=(DEF.get(t) or {}).get('run_def_pctl');   return None if v is None else 1-v/100.0
def passD_strength(t):   # 0..1, higher = tougher pass D (avg of coverage + pass-rush strength). Tempers the shootout: an elite D caps a high-total game.
    cw=covWeak(t); rs=rushStr(t); parts=[x for x in ((1-cw) if cw is not None else None, rs) if x is not None]
    return sum(parts)/len(parts) if parts else 0.5
def manRate(t):   return (COORD.get(t) or {}).get('man_rate_adj')
def shellSH(t):   return (SHELL.get(t) or {}).get('single_high')
def shellTH(t):   return (SHELL.get(t) or {}).get('two_high')

def lever_type(txt):
    s=txt.lower()
    if 'wins vs man' in s or 'man-beater' in s or ('man lean' in s): return 'man_beater'
    if 'handles man coverage' in s: return 'qb_man'
    if 'more efficient vs zone' in s or 'zone-beater' in s or 'zone lean' in s: return 'zone_beater'
    if 'wins separation vs man' in s: return 'gets_open_man'
    if 'contested-catch winner' in s: return 'contested'
    if 'scrambling qb' in s: return 'scramble_qb'
    if 'elusive' in s and 'missed tackles' in s: return 'elusive_rb'
    if 'vertical' in s or 'big-play' in s or 'deep' in s: return 'vertical'
    if 'slot' in s or 'nickel' in s: return 'slot'
    if 'boundary' in s or 'perimeter' in s: return 'boundary'
    if 'red-zone' in s or 'red zone' in s: return 'redzone'
    if 'pass-catching back' in s or 'pass catching back' in s: return 'passcatch_rb'
    if 'shootout' in s: return 'shootout'
    if 'motion weapon' in s: return 'motion'
    if 'soft slate' in s: return 'softslate'
    if 'struggles vs man' in s: return 'qb_man_neg'
    return 'other'

# how strongly opponent T activates a lever type -> intensity in [0,1] (None if no data)
def intensity(typ, T):
    if typ in ('man_beater','qb_man','contested','scramble_qb','gets_open_man'):
        mr=manRate(T); return None if mr is None else manP(mr)
    if typ=='zone_beater':
        mr=manRate(T); return None if mr is None else 1-manP(mr)
    if typ=='vertical':
        sh=shellSH(T); cw=covWeak(T)
        parts=[x for x in (shP(sh) if sh is not None else None, cw) if x is not None]
        return sum(parts)/len(parts) if parts else None
    if typ in ('slot','boundary'):
        return covWeak(T)
    if typ=='passcatch_rb':
        th=shellTH(T); cw=covWeak(T)
        parts=[x for x in (thP(th) if th is not None else None, cw) if x is not None]
        return sum(parts)/len(parts) if parts else None
    if typ=='redzone':
        cw=covWeak(T); rw=runWeak(T)
        parts=[x for x in (cw,rw) if x is not None]
        return sum(parts)/len(parts) if parts else None
    if typ=='shootout':
        e=envP(ENV.get(T))        # opponent's implied-total environment (coverage-scheme-independent)...
        return None if e is None else round(e*(1-0.5*passD_strength(T)),4)   # ...tempered by opp pass-D strength: an elite D (LAR/DET/HOU) caps the shootout
    if typ=='elusive_rb':
        tl=tackLeaky(T); return tl if tl is not None else runWeak(T)  # leaky tackling (real MTF-allowed); fallback run-def
    return None  # motion/softslate/other -> not single-opponent activated

TIER={'solid':1.0,'tendency':0.5}
ACT_MIN=0.5     # opponent must be in the favorable half for a lever to "activate"
SMASH=1.5       # weekly score >= SMASH  => flagged smash week

def main():
    dd=J('dossier_data.json')
    if not dd: print('no dossier_data.json'); return
    standalone={}
    n_players=0; n_levered=0
    for t in dd['teams']:
        team=nt(t.get('team'))
        sched=SCHED.get(team) or []
        for p in t['players']:
            if p.get('name') in NONUSABLE: continue  # 2026 non-usable (verified)
            n_players+=1
            levers=p.get('levers') or []
            # keep only single-opponent-activatable levers
            act_levers=[]
            for lv in levers:
                typ=lever_type(lv['t']);
                if typ in ('motion','softslate','other','qb_man_neg'): continue
                act_levers.append({'type':typ,'tier':lv.get('c','tendency'),'t':lv['t']})
            cal=[]
            for g in sched:
                opp=nt(g.get('opp')); wk=g.get('wk')
                wkact=[]; score=0.0
                for al in act_levers:
                    inten=intensity(al['type'],opp)
                    if inten is None or inten<ACT_MIN: continue
                    w=TIER.get(al['tier'],0.5)*inten
                    score+=w; wkact.append({'type':al['type'],'tier':al['tier'],'i':round(inten,2),'w':round(w,2)})
                cal.append({'wk':wk,'opp':opp,'home':g.get('home'),'dome':g.get('dome'),
                            'score':round(score,2),'n':len(wkact),'active':wkact})
            scored=[c for c in cal if c['score']>0]
            if act_levers: n_levered+=1
            scores=[c['score'] for c in cal]
            playoff=[c['score'] for c in cal if c['wk'] in (15,16,17)]
            summ={'n_levers':len(act_levers),
                  'mean':round(sum(scores)/len(scores),2) if scores else 0,
                  'peak':round(max(scores),2) if scores else 0,
                  'smash_weeks':sorted([c['wk'] for c in cal if c['score']>=SMASH]),
                  'playoff_mean':round(sum(playoff)/len(playoff),2) if playoff else 0,
                  'best_wks':[{'wk':c['wk'],'opp':c['opp'],'score':c['score']} for c in sorted(scored,key=lambda x:-x['score'])[:3]]}
            p['lever_cal']=cal; p['lever_sum']=summ
            if act_levers:
                standalone[p['name']]={'pos':p.get('pos'),'team':team,'rank':p.get('rank'),
                    'levers':[{'type':a['type'],'tier':a['tier']} for a in act_levers],'summary':summ}
    json.dump(dd, open(os.path.join(H,'dossier_data.json'),'w'), ensure_ascii=False, indent=1)
    json.dump({'players':standalone,'meta':{'tier_weights':TIER,'act_min':ACT_MIN,'smash':SMASH,'n':len(standalone)}},
              open(os.path.join(H,'lever_count.json'),'w'), ensure_ascii=False, indent=1)
    # report
    top=sorted(standalone.items(), key=lambda kv: -kv[1]['summary']['playoff_mean'])[:12]
    print(f"lever_count: {n_players} players, {n_levered} with activatable levers.")
    print("Top playoff-week lever stacks (W15-17 mean tier-weighted score):")
    for nm,v in top:
        print(f"  {v['summary']['playoff_mean']:.2f}  {nm} ({v['pos']},{v['team']}) "
              f"peak {v['summary']['peak']} smash {v['summary']['smash_weeks']}")

if __name__=='__main__':
    main()
