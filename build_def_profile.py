#!/usr/bin/env python3
"""Defensive PROFILE + FUNNEL system (FTN DVOA-Adjusted FP Against, opponent-adjusted).
Values = fantasy pts ABOVE AVERAGE the defense allows to each position (opp-adjusted).
Positive = soft (production funnels TO it); negative = tough. WR1/WR2/slot = alignment funnel.
Branch 4: reconciled vs the normalized 2026 engine (defense.json) — keeps the validated 2025
positional dvoa_fpaa nudge, ADDS the 2026 roster-adjusted engine view + roster-shift flag + rookies."""
import json, os, statistics as st
B=os.path.join(os.path.dirname(os.path.abspath(__file__)),'boom')
import core as _core
_eng = json.load(open(_core.P('defense.json'),encoding='utf-8')).get('teams',{}) if os.path.exists(_core.P('defense.json')) else {}
_csch=json.load(open(_core.P('coordinator_scheme_2026.json'),encoding='utf-8')).get('teams',{}) if os.path.exists(_core.P('coordinator_scheme_2026.json')) else {}
_cchg=json.load(open(_core.P('coordinator_changes_2026.json'),encoding='utf-8')) if os.path.exists(_core.P('coordinator_changes_2026.json')) else {}
_cb=json.load(open(_core.P('boom/defender_grades.json'),encoding='utf-8')).get('team_cb_profile',{}) if os.path.exists(_core.P('boom/defender_grades.json')) else {}
def _eng_lean(tm):
    e=_eng.get(tm)
    if not e or e.get('pass_cov_pctl') is None or e.get('run_def_pctl') is None: return None,None
    sp=100-e['pass_cov_pctl']; sr=100-e['run_def_pctl']
    lean='PASS' if sp-sr>=15 else ('RUN' if sr-sp>=15 else 'BALANCED')
    return lean,{'pass_cov_pctl':e['pass_cov_pctl'],'run_def_pctl':e['run_def_pctl'],
                 'pass_rush_pctl':e.get('pass_rush_pctl'),'rookies':e.get('rookies_2026',[])}
RAW="""ARI -0.3 3.6 -2.5 3.3 -0.1 -0.6 -1.8
ATL 0.1 -0.1 2.8 -4.2 1.2 0.9 0.7
BAL 0.0 1.6 5.5 -1.7 4.5 -1.7 2.8
BUF -2.3 4.1 -4.1 -5.6 -0.4 -1.3 -2.4
CAR -1.6 1.8 -1.9 -0.8 2.5 -2.7 -1.7
CHI 0.9 -1.6 2.9 0.0 2.4 2.3 -1.8
CIN 2.7 6.7 -6.3 8.3 -3.6 -2.3 -0.4
CLE -2.8 -1.3 -5.3 -2.3 -2.2 -2.6 -0.4
DAL 8.1 3.1 9.5 -0.4 4.2 1.6 3.7
DEN -1.1 -3.9 -1.0 1.5 -4.0 -0.1 3.1
DET 1.7 -2.1 4.9 -0.3 0.8 0.7 3.4
GB -1.5 -3.1 0.9 -0.8 0.8 0.1 0.1
HOU -5.2 -2.7 -5.8 -1.2 -3.4 0.0 -2.4
IND 0.0 -0.8 6.2 2.7 -2.6 5.0 3.8
JAX 0.9 -2.9 3.2 2.1 2.9 0.3 0.0
KC -1.4 -2.9 -2.1 -2.0 -1.5 -0.1 -0.4
LAC -3.6 -2.6 -4.0 -2.2 0.8 -2.0 -2.8
LAR -1.1 -3.5 2.2 -1.6 2.5 -0.5 0.2
LV -0.3 2.1 3.4 -2.9 -1.2 0.6 4.0
MIA 1.8 0.7 -1.7 3.6 -0.3 -1.3 -0.1
MIN -4.6 -2.1 -8.3 -1.2 -3.7 -1.0 -3.6
NE 0.5 -2.7 -0.3 1.1 0.5 -0.9 0.0
NO -2.5 -0.9 -3.8 -1.4 -2.3 -0.9 -0.6
NYG 2.5 4.9 3.0 -2.3 2.1 1.4 -0.5
NYJ 3.0 3.0 -0.3 0.4 2.4 -0.1 -2.6
PHI -3.6 0.5 -4.8 -4.7 -4.5 2.8 -3.1
PIT 2.2 -2.6 3.5 3.2 0.7 0.4 2.4
SEA -1.6 -2.9 -3.1 2.7 -2.1 -1.0 0.0
SF 1.0 1.3 2.2 1.9 -1.0 2.0 1.1
TB 3.5 0.7 0.1 2.2 1.3 -2.0 0.9
TEN 1.9 1.6 2.1 0.0 3.3 -0.2 -1.0
WAS 2.8 2.9 3.1 2.1 0.3 3.3 -0.5"""
COLS=['qb','rb','wr','te','wr1','wr2','slot']
prof={}
for ln in RAW.splitlines():
    p=ln.split(); tm=p[0]; vals={c:float(p[i+1]) for i,c in enumerate(COLS)}
    prof[tm]={'dvoa_fpaa':vals}
def flags(v):
    f=[]
    passsoft=st.mean([v['qb'],v['wr'],v['te']])
    if passsoft-v['rb']>=2.5 and passsoft>0: f.append('PASS funnel (soft vs pass, stiffer vs run -> WR/TE/QB up)')
    if v['rb']-passsoft>=2.5 and v['rb']>0: f.append('RUN funnel (soft vs run, stiffer vs pass -> RB up)')
    if v['slot']-max(v['wr1'],v['wr2'])>=2.0 and v['slot']>0: f.append('SLOT funnel (slot WR exploitable)')
    if min(v['wr1'],v['wr2'])-v['slot']>=2.0 and max(v['wr1'],v['wr2'])>0: f.append('OUTSIDE funnel (boundary WRs exploitable)')
    if v['wr1']>=2.5: f.append('WR1 funnel (top-CB beatable)')
    if v['te']>=2.5: f.append('TE funnel (soft vs TE)')
    if v['te']<=-3.0: f.append('TE fortress (avoid TEs)')
    if v['wr']<=-4.0: f.append('WR fortress (avoid WRs)')
    return f
for tm,d in prof.items(): d['funnels']=flags(d['dvoa_fpaa'])
def _dvoa_lean(v):
    ps=st.mean([v['qb'],v['wr'],v['te']])
    return 'PASS' if ps-v['rb']>=2.5 else ('RUN' if v['rb']-ps>=2.5 else 'BALANCED')
shifts=0
for tm,d in prof.items():
    el,eng=_eng_lean(tm)
    dl=_dvoa_lean(d['dvoa_fpaa'])
    d['lean_2025']=dl; d['lean_2026']=el
    sc=_csch.get(tm,{}); ch=_cchg.get(tm,{}) if isinstance(_cchg.get(tm),dict) else {}
    if sc.get('dc_new') or ch.get('dc_new'):
        d['dc']={'name':sc.get('dc_name') or ch.get('dc_name'),'man25':sc.get('man_rate_2025'),
                 'man26':sc.get('man_rate_adj'),'scheme':ch.get('dc_scheme'),'conf':sc.get('conf')}
    cb=_cb.get(tm)
    if cb: d['cb1']={'name':cb.get('cb1'),'cov':cb.get('cb1_cov'),'tier':cb.get('cb1_tier'),'wr1_funnel':cb.get('expected_wr1_funnel')}
    if eng:
        d['eng2026']={k:eng[k] for k in ('pass_cov_pctl','run_def_pctl','pass_rush_pctl')}
        d['rookies']=eng['rookies']
    if el and el!='BALANCED' and dl!='BALANCED' and el!=dl:
        d['funnels'].insert(0,'[SHIFT 25->26] 2025 graded '+dl+'-funnel, 2026 engine projects '+el+'-funnel (roster/coordinator change)'); shifts+=1
    elif el and el!='BALANCED' and dl=='BALANCED':
        d['funnels'].append('2026 engine leans '+el+'-funnel (roster-adjusted; 2025 graded balanced)')
json.dump(prof,open(f'{B}/defensive_profile.json','w'),indent=1)
print("DEFENSIVE PROFILE + FUNNELS (2025 DVOA) + 2026 engine reconcile\n")
nf=sum(len(d['funnels']) for d in prof.values())
print(f"  32 defenses profiled, {nf} funnel flags, {shifts} roster-shift teams\n")
for tm,d in sorted(prof.items()):
    if d['funnels']: print(f"   {tm}: "+'; '.join(d['funnels']))
