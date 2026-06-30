#!/usr/bin/env python3
import pandas as pd, numpy as np, argparse, re, os
B=pd.read_csv('draft_board_signals.csv')
def fn(n):
    n=str(n).strip().lower(); n=re.sub(r'\s+(jr|sr|ii|iii|iv|v)\.?$','',n); n=n.replace('.','').replace("'","").replace('-',' '); return ' '.join(n.split())
KEY={fn(n):n for n in B['name']}
B['key']=B['name'].map(fn)
def resolve(lst):
    out=[]
    for x in lst:
        x=x.strip()
        if not x: continue
        k=fn(x)
        if k in KEY: out.append(k)
        else:
            c=[kk for kk in KEY if k in kk or kk in k]
            if c: out.append(c[0])
    return out
def _cg(g):
    if not isinstance(g,str): return None
    p=g.replace('+','@').split('@'); return '@'.join(sorted(x.strip() for x in p if x.strip()))
TARGET={'QB':3,'RB':6,'WR':9,'TE':3}

ap=argparse.ArgumentParser()
ap.add_argument('--pick',type=float,default=999); ap.add_argument('--mine',default=''); ap.add_argument('--gone',default='')
ap.add_argument('--anchor-used',default=''); ap.add_argument('--portfolio',default=''); ap.add_argument('--n',type=int,default=10); ap.add_argument('--json',action='store_true')
a=ap.parse_args()
mine=resolve(a.mine.split(',')); gone=set(resolve(a.gone.split(',')))
anchors_used=[x.strip() for x in a.anchor_used.split(',') if x.strip()]; anchors_used_c=[_cg(x) for x in anchors_used]
HAVE_PORTFOLIO=bool(a.portfolio)
TARG={}
if os.path.exists('anchor_allocation_900.csv'):
    for _,rr in pd.read_csv('anchor_allocation_900.csv').iterrows(): TARG[_cg(rr['game'])]=rr.get('entries_of_900',rr.get('entries',0))
USED={}
if a.portfolio:
    if os.path.exists(a.portfolio):
        for _,rr in pd.read_csv(a.portfolio).iterrows(): USED[_cg(str(rr.iloc[0]))]=float(rr.iloc[1])
    else:
        for tok in a.portfolio.split(','):
            if ':' in tok: g,c=tok.split(':'); USED[_cg(g)]=float(c)
NEED={g:max(0.0,(t-USED.get(g,0))/t) for g,t in TARG.items() if t}

mineB=B[B.key.isin(mine)]
my_pos=mineB['pos'].value_counts().to_dict(); my_byes=mineB['bye'].value_counts().to_dict()
my_w17=mineB['w17_game'].value_counts().to_dict(); my_team=mineB['team'].value_counts().to_dict()
have_anchor=any(c>=2 for c in my_w17.values())
taken=set(mine)|gone; avail=B[~B.key.isin(taken)].copy()

def score(r):
    s=0.0; tag=[]
    ceil=r['ceil_pct'] if pd.notna(r['ceil_pct']) else .2; adv=r['adv_pct'] if pd.notna(r['adv_pct']) else .2
    s+=0.42*ceil+0.23*adv
    base=r['merged_rank'] if pd.notna(r.get('merged_rank')) else r['adp']
    if a.pick<900 and pd.notna(base):
        fell=a.pick-base                       # fell past OUR board rank = value; negative = reach vs our board
        if fell>=8: s+=0.10; tag.append(f"val+{fell:.0f}")
        elif fell<=-12: s-=min(0.08+0.005*(-fell-12),0.55); tag.append(f"REACH{-fell:.0f}")
    g=r['w17_game']
    if g and isinstance(g,str) and '@' in g:
        t1,t2=g.split('@'); cand=r['team']; other=t2 if cand==t1 else t1
        mc=my_team.get(cand,0); mo=my_team.get(other,0); ingame=mc+mo
        cg=_cg(g); need=NEED.get(cg,.5); tail=max(0,(17-r['w17_blowup_rank'])/16.)
        if ingame>=2:
            if ingame>=5: s-=0.10; tag.append(f"overstack {g}")
            elif mo>=1 and mc==0: s+=0.19; tag.append(f"★2-side {g}")
            elif mc>=2 and mo==0: s+=0.03; tag.append(f"1-sided→need {other}")
            else: s+=0.13; tag.append(f"build {g}")
        elif ingame==1 and not have_anchor:
            s+=0.10+0.10*need*(.5+tail); tag.append((f"→commit {g}(need{need*100:.0f}%)") if HAVE_PORTFOLIO else f"→commit {g}#{int(r['w17_blowup_rank'])}")
        elif ingame==0 and not have_anchor and (r['w17_blowup_rank']<=10 or need>.6):
            s+=0.05+0.08*need*(.5+tail); tag.append((f"seed {g}(need{need*100:.0f}%)") if HAVE_PORTFOLIO else f"seed {g}#{int(r['w17_blowup_rank'])}")
        if cg in anchors_used_c: s-=0.05; tag.append("dup-anchor")
    if pd.notna(r['bye']):
        sub=mineB[mineB['bye']==r['bye']]; tc=sub['team'].value_counts().to_dict()
        tc[r['team']]=tc.get(r['team'],0)+1
        excess=sum(tc.values())-max(tc.values())          # players beyond your biggest stack on that bye
        if excess>=2: s-=0.14; tag.append(f"✗BYE{int(r['bye'])}-pileup")
    if pd.isna(r['p95']) or pd.isna(r['proj_pg']): s-=0.18; tag.append('no-proj')
    nd=TARGET.get(r['pos'],0)-my_pos.get(r['pos'],0)
    if nd>=3: s+=0.08; tag.append(f"need{r['pos']}")
    elif nd<=0: s-=0.10; tag.append(f"{r['pos']}full")
    if pd.notna(r['cv']) and r['cv']>=.95 and r['pos']=='WR': tag.append("boom")
    return s, " · ".join(tag)

avail[['score','tags']]=avail.apply(lambda r: pd.Series(score(r)),axis=1)
top=avail.sort_values('score',ascending=False).head(a.n).reset_index(drop=True)

# ---------- clean output ----------
pc=lambda p: f"{my_pos.get(p,0)} {p}"
def _byedesc(b,c):
    sub=mineB[mineB['bye']==b]; top=sub['team'].value_counts()
    return f"W{int(b)}×{c}" + (f"({top.index[0]} stk)" if len(top) and top.iloc[0]>=2 and top.iloc[0]==c else "")
byes=", ".join(_byedesc(b,c) for b,c in sorted(my_byes.items()) if pd.notna(b))
clu=[]
for b in mineB['bye'].dropna().unique():
    sub=mineB[mineB['bye']==b]
    if len(sub)-sub['team'].value_counts().max()>=2: clu.append(f"W{int(b)}")
gr={}                                   # game -> blowup rank
for _,rr in B.iterrows():
    if isinstance(rr['w17_game'],str): gr[rr['w17_game']]=rr['w17_blowup_rank']
anchor_line="(none yet — seeding)"
real=[(g,c) for g,c in my_w17.items() if c>=2 and isinstance(g,str)]
ones=[g for g,c in my_w17.items() if c==1 and isinstance(g,str)]
if real:
    g,c=max(real,key=lambda x:x[1]); anchor_line=f"{g}  ({c} pieces — complete 2-sided)"
elif ones:
    g=min(ones,key=lambda x:gr.get(x,99)); anchor_line=f"{g} #{int(gr.get(g,99))}  (best of your {len(ones)} 1-piece games — commit here)"
if a.json:
    import json as _j
    _cols=['name','pos','team','merged_rank','adp','proj_pg','p95','bye','tags','w15_opp','w16_opp','w17_game','w17_blowup_rank']
    _rr=B.assign(_x=B['proj_pg'].rank(ascending=False,method='min')).set_index('key')['_x'].to_dict()
    _rec=[]
    for _,_r in top.iterrows():
        _o={}
        for _k in _cols:
            _v=_r[_k] if _k in _r else None
            _v=_v.item() if hasattr(_v,'item') else _v
            _o[_k]=(None if (isinstance(_v,float) and pd.isna(_v)) else _v)
        _o['reg_rank']=(int(_rr[_r['key']]) if (_r.get('key') in _rr and pd.notna(_rr.get(_r.get('key')))) else None); _rec.append(_o)
    print(_j.dumps({"pick":float(a.pick),"qb":int(my_pos.get("QB",0)),"rb":int(my_pos.get("RB",0)),"wr":int(my_pos.get("WR",0)),"te":int(my_pos.get("TE",0)),"anchor":anchor_line,"cands":_rec},default=str)); sys.exit(0)
print("\n"+"="*64)
print(f" PICK {a.pick:.0f}   ·   {pc('QB')}  {pc('RB')}  {pc('WR')}  {pc('TE')}")
print(f" Anchor: {anchor_line}")
print(f" Byes: {byes if byes else '—'}"+(f"   ⚠ CLUSTER {','.join(clu)}" if clu else ""))
print("="*64)
t0=top.iloc[0] if len(top) else None
print(f" → TAKE: {t0['name']} ({t0['pos']} {t0['team']})  —  {t0['tags']}\n")
print(f" {'#':<2}{'PLAYER':<19}{'POS':<4}{'TM':<4}{'RK':>4}{'ADP':>4}{'PROJ':>5}{'CEIL':>5}{'BY':>3}   WHY")
for i,r in top.iterrows():
    rk='-' if pd.isna(r.get('merged_rank')) else f"{r['merged_rank']:.0f}"
    pj='-' if pd.isna(r['proj_pg']) else f"{r['proj_pg']:.1f}"
    by='-' if pd.isna(r['bye']) else f"{int(r['bye'])}"
    cl='-' if pd.isna(r['p95']) else f"{r['p95']:.0f}"
    print(f" {i+1:<2}{r['name'][:18]:<19}{r['pos']:<4}{str(r['team']):<4}{rk:>4}{r['adp']:>4.0f}{pj:>5}{cl:>5}{by:>3}   {r['tags']}")
print()
