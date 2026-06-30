#!/usr/bin/env python3
"""Unified DK Best Ball / DFS 2026 command center -> command_center.html (source-fusion DFS)."""
import json,os,math,datetime
HERE=os.path.dirname(os.path.abspath(__file__))
def _clean(o):
    """NaN/Inf -> None so the embedded JS object literal stays valid JSON (NaN is not valid JSON)."""
    if isinstance(o,float): return None if (math.isnan(o) or math.isinf(o)) else o
    if isinstance(o,dict): return {k:_clean(v) for k,v in o.items()}
    if isinstance(o,(list,tuple)): return [_clean(v) for v in o]
    return o
def J(f): return json.load(open(os.path.join(HERE,f),encoding='utf-8'))
fusion=J('fusion.json'); dfs=J('dfs_scenarios.json'); gp=J('gameplan.json'); per=J('personnel_changes.json'); dfn=J('defense.json'); dprof=(J('boom/defensive_profile.json') if os.path.exists(os.path.join(HERE,'boom','defensive_profile.json')) else {})
import re
def _fn(n):
    n=str(n).strip().lower(); n=re.sub(r"\s+(jr|sr|ii|iii|iv|v)\.?$","",n)
    return " ".join(n.replace(".","").replace("'","").replace("-"," ").split())
BM=J('boom/boom_marks.json') if os.path.exists(os.path.join(HERE,'boom','boom_marks.json')) else {}
def _bm(nm):
    b=BM.get(_fn(nm)); return {'badge':b['badge'],'tier':b['tier']} if b else None
# 4-layer per-player context (situational splits + real NFL Pro EPA · playcaller scheme fit · vacated/opportunity · W15-17 matchup)
CTX=J('cc_context.json') if os.path.exists(os.path.join(HERE,'cc_context.json')) else {}
fp=[{'n':p['name'],'p':p['pos'],'t':p['team'],'adp':p.get('adp'),'m':p.get('models',{}),
     'c':round(p.get('consensus') or 0),'d':round(p.get('divergence') or 0),'f':p.get('flags',[]),'boom':_bm(p['name'])} for p in fusion['players']]
dp=[{'n':p['name'],'p':p['pos'],'t':p['team'],'src':p.get('sources') or {},
     'c':round(p.get('ceiling_consensus') or 0),'d':round(p.get('ceiling_divergence') or 0),
     'pw17':round((p.get('p_w17') or 0)*100),'prof':p.get('profile','')} for p in dfs['players']]
def _top1(lst):
    return (lst[0] if lst else None)
deff=[{'t':v['team'],'cov':v.get('pass_cov_pctl'),'covs':v.get('pass_cov_strength'),'covepa':v.get('pass_cov_epatgt'),
       'rush':v.get('pass_rush_pctl'),'rushs':v.get('pass_rush_strength'),'run':v.get('run_def_pctl'),'runs':v.get('run_def_strength'),
       'cov25':v.get('pass_cov_pctl_2025'),'rush25':v.get('pass_rush_pctl_2025'),'run25':v.get('run_def_pctl_2025'),
       'tcov':_top1(v.get('top_coverage')),'trush':_top1(v.get('top_pass_rush')),'trun':_top1(v.get('top_run_def')),
       'moves':[{'pl':m['player'],'u':m['unit'],'fr':m['from'],'to':m['to'],'ps':m['ps'],'conf':m.get('conf',True)} for m in v.get('moves_2026',[])],
       'rk':list({rk[0]:{'pl':rk[0],'pos':rk[1],'rd':rk[3]} for rk in (v.get('rookies_2026') or [])}.values()),
       'funnel':dprof.get(v['team'],{}).get('funnels',[]),'lean25':dprof.get(v['team'],{}).get('lean_2025'),'lean26':dprof.get(v['team'],{}).get('lean_2026'),'dc':dprof.get(v['team'],{}).get('dc'),'cb1':dprof.get(v['team'],{}).get('cb1')}
      for v in dfn['teams'].values()]
DATA={'fusion':fp,'dfs':{'players':dp},'tiers':gp['draft_tiers'],'teampri':gp['team_priority'],'stacks':gp['stacks'],
      'personnel':per['teams'],'coverage':per['coverage'],'defense':deff,'ctx':CTX,
      'meta':{'players':len(fp),'dfs':len(dp),'stacks':len(gp['stacks']),'defense':len(deff),
              'ctx':len(CTX),'ctx_layers':4}}
_blob=json.dumps(_clean(DATA),ensure_ascii=False,allow_nan=False).replace('<','\\u003c')
_built=datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
html=open(os.path.join(HERE,'_cc_template.html'),encoding='utf-8').read().replace('__DATA__',_blob).replace('__BUILT__',_built)
open(os.path.join(HERE,'command_center.html'),'w',encoding='utf-8').write(html)
print("wrote",os.path.getsize(os.path.join(HERE,'command_center.html')),"bytes")
