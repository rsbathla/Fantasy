#!/usr/bin/env python3
"""Upside-correlation (fusion) board: which signals actually predict UPSIDE (boom)?

Correlates every feature-store signal against realized 2-yr boom rate (base2yr b2/g2, g2>=8),
within position. Separates INPUT signals (independent: efficiency/usage/matchup) from OUTPUT/market
signals (p95/spike/proj/ADP — circular, shown for reference). The ranked input signals are the
evidence for data-driven fusion weights (vs the audit-flagged hand-set ones)."""
import core, json, os

def num(x):
    try:
        if x is None or x == '': return None
        return float(x)
    except (TypeError, ValueError): return None

def spearman(xs, ys):
    pairs=[(a,b) for a,b in zip(xs,ys) if a is not None and b is not None]
    n=len(pairs)
    if n<10: return None,n
    def rank(v):
        idx=sorted(range(len(v)),key=lambda i:v[i]); r=[0.0]*len(v); i=0
        while i<len(v):
            j=i
            while j<len(v) and v[idx[j]]==v[idx[i]]: j+=1
            for k in range(i,j): r[idx[k]]=(i+j-1)/2.0
            i=j
        return r
    xs2=[p[0] for p in pairs]; ys2=[p[1] for p in pairs]
    rx,ry=rank(xs2),rank(ys2); mx=sum(rx)/n; my=sum(ry)/n
    nu=sum((rx[i]-mx)*(ry[i]-my) for i in range(n))
    de=(sum((rx[i]-mx)**2 for i in range(n))*sum((ry[i]-my)**2 for i in range(n)))**0.5
    return (round(nu/de,3) if de else 0.0), n

feat=json.load(open(core.P('features.json'),encoding='utf-8'))['players']
b2=json.load(open(core.P('boom/base2yr.json'),encoding='utf-8'))
for f in feat:
    r=b2.get(core.fn(f['name']))
    f['_boom']=(r['b2']/r['g2']) if r and (r.get('g2') or 0)>=8 else None

OUTPUTS={'p95','spike','proj_pg','adv_pct','sim_mean','p50','p85','dk_mean25','dk_max25',
         'merged_rank','reg_rank','adp','tail','dk_pg','base_boom','base_blended'}
ID={'name','pos','team','pid','team25','w15','w16','w17','opp_w15','opp_w16','opp_w17',
    'coord_scheme','mover','bye','g25','_boom'}
cols=[c for c in feat[0].keys() if c not in ID]

res={}
for pos in ['WR','RB','TE','QB','ALL']:
    pl=[f for f in feat if f['_boom'] is not None and (pos=='ALL' or f.get('pos')==pos)]
    rows=[]
    for c in cols:
        rho,n=spearman([num(p.get(c)) for p in pl],[p['_boom'] for p in pl])
        if rho is not None and n>=12:
            rows.append({'signal':c,'rho':rho,'n':n,'kind':'output' if c in OUTPUTS else 'input'})
    rows.sort(key=lambda r:-abs(r['rho']))
    res[pos]={'n_players':len(pl),'signals':rows}

core.safe_json_dump({'outcome':'realized 2-yr boom rate b2/g2 (g2>=8)',
    'note':'spearman vs boom; input=independent signal, output=projection/market (circular ref)',
    'by_pos':res}, core.P('boom/upside_correlations.json'))

for pos in ['WR','RB','TE','QB']:
    r=res[pos]
    print(f"\n=== {pos} (n={r['n_players']}) — top INPUT signals vs UPSIDE(boom) ===")
    for x in [s for s in r['signals'] if s['kind']=='input'][:12]:
        print(f"  {x['signal']:22} rho={x['rho']:+.3f}  n={x['n']}")
    out=[s for s in r['signals'] if s['kind']=='output'][:3]
    print("  [ref/circular]:", ", ".join(f"{x['signal']} {x['rho']:+.2f}" for x in out))
