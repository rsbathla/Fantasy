#!/usr/bin/env python3
"""Per-player BOOM-CONDITIONS splits. Classify each player's ceiling drivers (separation/explosive/
route/run-eff from fusion), then map their W15/16/17 opponents to scheme (man-rate, pass-rush) +
funnel/strength (2026 coverage vs run-def Points Saved) -> favorable/neutral/tough each week.
Output player_splits.json keyed by normalized name. Grounded in the matchup-aware ceiling work."""
import json, csv, re, os
HERE=os.path.dirname(os.path.abspath(__file__)); DL=os.path.dirname(HERE)
def fn(n):
    n=str(n).strip().lower(); n=re.sub(r'\s+(jr|sr|ii|iii|iv|v)\.?$','',n); return n.replace('.','').replace("'","").replace('-',' ')
def num(x,d=None):
    try: return float(x)
    except: return d
TMAP={'LA':'LAR','JAC':'JAX','WSH':'WAS','ARZ':'ARI','GNB':'GB','KAN':'KC','SFO':'SF','TAM':'TB','NWE':'NE','NOR':'NO'}
def tm(t): t=str(t).strip().upper(); return TMAP.get(t,t)

# ---- defense: 2026 coverage/run Points Saved -> percentiles (higher PS = tougher unit) ----
dm=json.load(open(f"{DL}/dfs_review/out/defense_2026_matchup.json"))
covs=sorted(v['cov'] for v in dm.values()); runs=sorted(v['run'] for v in dm.values())
def pctl(sortedv,x): 
    import bisect; return round(100*bisect.bisect_left(sortedv,x)/max(1,len(sortedv)-1))
DEF={}
for t,v in dm.items():
    DEF[tm(t)]={'covp':pctl(covs,v['cov']),'runp':pctl(runs,v['run'])}
# scheme: man rate + pass rush
cov=list(csv.DictReader(open(f"{HERE}/defense_coverage.csv")))
mr=sorted(num(r['def_man_rate']) for r in cov); sk=sorted(num(r['def_sack_rate']) for r in cov)
SCH={}
for r in cov: SCH[tm(r['team'])]={'manp':pctl(mr,num(r['def_man_rate'])),'sackp':pctl(sk,num(r['def_sack_rate']))}

# ---- player signals ----
F={fn(r['name']):r for r in csv.DictReader(open(f"{HERE}/fusion_table.csv"))}
S=list(csv.DictReader(open(f"{HERE}/draft_board_signals.csv")))

def profile(pos,f):
    """ceiling-driver tags from fusion percentiles"""
    g=lambda k: num((f or {}).get(k))
    tags=[]; man_lean=None
    sep,exp,rt,yac,rune=g('separation_pctl'),g('explosive_pctl'),g('route_eff_pctl'),g('yac_pctl'),g('run_eff_pctl')
    if pos in ('WR','TE'):
        if sep and sep>=65: tags.append('separator'); man_lean='man'      # wins vs tight man
        if rt and rt>=65 and (not sep or sep<65): tags.append('route-tech'); man_lean='zone'
        if exp and exp>=65: tags.append('big-play')
        if yac and yac>=70: tags.append('YAC')
        if not tags: tags.append('volume/funnel-dependent')
    elif pos=='RB':
        if rune and rune>=65: tags.append('efficient')
        if exp and exp>=65: tags.append('big-play')
        if not tags: tags.append('volume-dependent')
    elif pos=='QB':
        if exp and exp>=60: tags.append('downfield')
        if not tags: tags.append('matchup-sensitive')
    return tags, man_lean

def verdict(pos, opp, man_lean):
    d=DEF.get(opp); sc=SCH.get(opp)
    if not d: return ('?','no rating')
    why=[]; score=0
    if pos in ('WR','TE','QB'):
        cp=d['covp']
        if cp<=35: score+=2; why.append('soft pass-D')
        elif cp>=65: score-=2; why.append('tough pass-D')
        if d['runp']>=60 and cp<=45: score+=1; why.append('pass-funnel')   # stout run, leaky pass
        if sc:
            if sc['sackp']>=70: score-=1; why.append('heavy rush')
            if man_lean=='man' and sc['manp']>=66: score+=1; why.append('man-heavy (sep edge)')
            if man_lean=='zone' and sc['manp']<=33: score+=1; why.append('zone-heavy')
    elif pos=='RB':
        rp=d['runp']
        if rp<=35: score+=2; why.append('soft run-D')
        elif rp>=65: score-=2; why.append('tough run-D')
        if d['covp']>=60 and rp<=45: score+=1; why.append('run-funnel')
    v='FAV' if score>=2 else ('TOUGH' if score<=-2 else 'NEU')
    return (v, ', '.join(why[:2]) or 'neutral')

OUT={}
for r in S:
    nm=r['name']; k=fn(nm); pos=(r.get('pos') or '').upper(); myteam=tm(r.get('team') or '')
    f=F.get(k)
    tags,man_lean=profile(pos,f)
    # resolve W15/16/17 opponents
    w15=tm(r.get('w15_opp') or ''); w16=tm(r.get('w16_opp') or '')
    w17g=str(r.get('w17_game') or ''); w17=''
    if '@' in w17g:
        a,b=[tm(x) for x in w17g.split('@')]; w17=b if a==myteam else a
    weeks=[]
    for wk,opp in [('W15',w15),('W16',w16),('W17',w17)]:
        if opp and opp in DEF:
            v,why=verdict(pos,opp,man_lean); weeks.append({'wk':wk,'opp':opp,'v':v,'why':why})
    fav=sum(1 for w in weeks if w['v']=='FAV'); tough=sum(1 for w in weeks if w['v']=='TOUGH')
    if not weeks and not f: continue
    OUT[k]={'profile':tags,'man_lean':man_lean,'weeks':weeks,'fav':fav,'tough':tough}
json.dump(OUT,open(f"{HERE}/player_splits.json",'w',encoding='utf-8'),ensure_ascii=False)
print(f"wrote player_splits.json: {len(OUT)} players")
# validate archetypes
for nm in ['Puka Nacua','Tee Higgins','Alec Pierce','Jonathan Taylor','Drake London','Lamar Jackson']:
    o=OUT.get(fn(nm))
    if o:
        wk=' | '.join(f"{w['wk']} v{w['opp']} {w['v']}({w['why']})" for w in o['weeks'])
        print(f"  {nm:18} [{'+'.join(o['profile'])}] -> {o['fav']}/3 fav: {wk}")
