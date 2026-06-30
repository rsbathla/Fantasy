#!/usr/bin/env python3
"""Optimize the rookie blend weight W against a real 2025 preseason baseline (FantasyPros ADP).
For the 2025 rookie cohort (2024 college ceiling + 2025 ADP + actual 2025 NFL boom), grid-search
W in (1-W)*ADP + W*college and measure rank-correlation with realized boom. Bootstraps the optimal
W to show how well the data actually pins it down. Honest test of: does college add to ADP?"""
import core, csv, json, random
from build_rookie_profiles import build_season
random.seed(11)

def cohort_pctl(vals):
    pres=[v for v in vals if v is not None]; out=[None]*len(vals); n=len(pres)
    for i,v in enumerate(vals):
        if v is None: continue
        less=sum(1 for x in pres if x<v); eq=sum(1 for x in pres if x==v); out[i]=(less+0.5*eq)/n*100
    return out

def spearman(xs,ys):
    def rk(a):
        o=sorted(range(len(a)),key=lambda i:a[i]); r=[0.0]*len(a); i=0
        while i<len(a):
            j=i
            while j<len(a) and a[o[j]]==a[o[i]]: j+=1
            for k in range(i,j): r[o[k]]=(i+j-1)/2.0
            i=j
        return r
    rx,ry=rk(xs),rk(ys); n=len(xs); mx=sum(rx)/n; my=sum(ry)/n
    nu=sum((rx[i]-mx)*(ry[i]-my) for i in range(n))
    de=(sum((rx[i]-mx)**2 for i in range(n))*sum((ry[i]-my)**2 for i in range(n)))**0.5
    return nu/de if de else 0.0

adp={core.fn(r['name']):float(r['adp']) for r in csv.DictReader(open('sis_value/fp_adp_2025.csv',encoding='utf-8'))}
b=json.load(open('boom/base2yr.json',encoding='utf-8'))
rk={k:v for k,v in b.items() if (not v.get('g24')) and (v.get('g25') or 0)>=4}
p24=build_season('2024')
coh=[(p24[k]['name'],p24[k]['ceiling_pctl'],adp[k],(rk[k].get('b25') or 0)/rk[k]['g25'])
     for k in p24 if k in rk and k in adp and p24[k].get('ceiling_pctl') is not None and p24[k]['pos'] in ('WR','TE','RB')]
col_p=cohort_pctl([c[1] for c in coh]); adp_p=cohort_pctl([-c[2] for c in coh]); boom=[c[3] for c in coh]
Ws=[round(i/20,2) for i in range(21)]
def rho_at(W,idx):
    comb=[(1-W)*adp_p[i]+W*col_p[i] for i in idx]; return spearman(comb,[boom[i] for i in idx])
full=list(range(len(coh)))
curve={W:round(rho_at(W,full),3) for W in Ws}
bestW=max(Ws,key=lambda W:curve[W])
argm=[]
for _ in range(2000):
    idx=[random.randrange(len(coh)) for _ in range(len(coh))]
    argm.append(max(Ws,key=lambda W:rho_at(W,idx)))
argm.sort(); med=argm[len(argm)//2]; lo=argm[int(.25*len(argm))]; hi=argm[int(.75*len(argm))]
res={'n':len(coh),'rho_adp_only':curve[0.0],'rho_college_only':curve[1.0],'rho_best':curve[bestW],
     'best_W':bestW,'bootstrap_argmaxW_median':med,'bootstrap_argmaxW_IQR':[lo,hi],'curve':curve}
core.safe_json_dump(res, core.P('boom/rookie_weight_opt.json'))
print(f"n={len(coh)} rookies | rho ADP-only(W=0)={curve[0.0]} | college-only(W=1)={curve[1.0]} | best W={bestW} (rho={curve[bestW]})")
print(f"bootstrap optimal-W: median={med}, IQR=[{lo},{hi}]  (wide IQR => data does NOT pin W)")
print("curve W:rho =", {k:v for k,v in curve.items() if k in (0.0,0.1,0.2,0.3,0.4,0.5,0.7,1.0)})
