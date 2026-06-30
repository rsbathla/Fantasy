import pandas as pd, numpy as np, json, re, sys, os
import warnings; warnings.filterwarnings('ignore')
exec(open('sim_prod.py').read().split("# build distribution")[0])  # gen_team, pp, tp
games_by_week={int(w):[tuple(g) for g in v] for w,v in json.load(open('games_by_week.json')).items()}
BYE=json.load(open('byes_2026.json')); NS=4000
name2team=dict(zip(pp['name'],pp['team'])); name2pos=dict(zip(pp['name'],pp['pos']))
def _norm(n):
    n=str(n).strip().lower(); n=re.sub(r'\s+(jr|sr|ii|iii|iv|v)\.?$','',n); n=n.replace('.','').replace("'","").replace('-',' '); return ' '.join(n.split())
NORM2CLAY={}; 
for cn in pp['name']: NORM2CLAY.setdefault(_norm(cn),cn)
# CONFIG: playoff cut rates (proxy for DK Milly field cuts; relative ranking robust to these)
# platform-aware playoff cuts. DK Milly: top-50/50/10. Underdog BBM VII: win your pod each week
# (W15 top 1/14, W16 top 1/12), then a 667-team W17 finals -> far more ceiling-dependent.
if os.environ.get('BB_PLATFORM','DK').upper()=='UD':
    CUT={'W15':1-1/14.0,'W16':1-1/12.0,'W17':0.90}
else:
    CUT={'W15':0.50,'W16':0.50,'W17':0.90}

def gen_weeks(rng, weeks):
    tl=list(tp.index); nW=len(weeks); gz={t:np.zeros((NS,nW)) for t in tl}
    for wi,w in enumerate(weeks):
        play=set()
        for (a,b) in games_by_week[w]:
            g=rng.normal(0,1,NS)
            if a in gz: gz[a][:,wi]=g; play.add(a)
            if b in gz: gz[b][:,wi]=g; play.add(b)
        for t in tl:
            if t not in play: gz[t][:,wi]=rng.normal(0,1,NS)
    out={}
    for t in tl:
        g=gen_team(t,NS*nW,gz[t].ravel(),rng); out[t]={nm:a.reshape(NS,nW) for nm,a in g.items()}
    return out

def lineup(players, wk, weeks, apply_bye):
    byq={'QB':[],'RB':[],'WR':[],'TE':[]}; held={}
    for nm in players:
        cn=NORM2CLAY.get(_norm(nm)); 
        if cn is None: continue
        tm=name2team.get(cn); pos=name2pos.get(cn); arr=wk.get(tm,{}).get(cn)
        if arr is None or pos not in byq: continue
        a=arr.copy()
        if apply_bye and BYE.get(tm) in weeks: a[:,weeks.index(BYE[tm])]=0.0
        byq[pos].append(a); held[cn]=tm
    def topk(lst,k):
        if not lst: return np.zeros((NS,len(weeks))), np.zeros((0,NS,len(weeks)))
        S=np.sort(np.stack(lst,0),0)[::-1]; return S[:k].sum(0),S[k:]
    qb,_=topk(byq['QB'],1); rb2,rr=topk(byq['RB'],2); wr3,wr=topk(byq['WR'],3); te1,tr=topk(byq['TE'],1)
    rest=[x for x in [rr,wr,tr] if len(x)]; flex=np.max(np.concatenate(rest,0),0) if rest else np.zeros((NS,len(weeks)))
    return qb+rb2+wr3+te1+flex, held

def anchor_game(held, week):
    # which W17 matchup holds the most of this roster's players
    best=None;bn=0
    for (a,b) in games_by_week[week]:
        n=sum(1 for cn,tm in held.items() if tm in (a,b))
        if n>bn: bn=n; best=(a,b)
    return (f"{best[0]}@{best[1]}",bn) if best else ("none",0)

def chain(rosters, me='rsbathla'):
    rng=np.random.default_rng(11)
    advW=list(range(1,15)); wkA=gen_weeks(rng,advW)
    season={t:lineup(pl,wkA,advW,True)[0].sum(1) for t,pl in rosters.items()}
    teams=list(rosters); M=np.stack([season[t] for t in teams],1); order=np.argsort(-M,1)
    padv={t:(((np.array(teams)[order[:,0]]==t)|(np.array(teams)[order[:,1]]==t)).mean()) for t in teams}
    wk=gen_weeks(rng,[15,16,17])
    L={}; H={}
    for t in teams:
        lp,held=lineup(rosters[t],wk,[15,16,17],False); L[t]=lp; H[t]=held
    res=[]
    for wi,wk_name in [(0,'W15'),(1,'W16'),(2,'W17')]:
        field=np.concatenate([L[t][:,wi] for t in teams]); 
    # survival probs
    fields={wi:np.concatenate([L[t][:,wi] for t in teams]) for wi in (0,1,2)}
    bars={wi:np.percentile(fields[wi],CUT[nm]*100) for wi,nm in [(0,'W15'),(1,'W16'),(2,'W17')]}
    rows=[]
    for t in teams:
        s15=(L[t][:,0]>bars[0]).mean(); s16=(L[t][:,1]>bars[1]).mean(); w17=(L[t][:,2]>bars[2]).mean()
        title=padv[t]*s15*s16*w17
        ag,an=anchor_game(H[t],17)
        rows.append((t,padv[t],s15,s16,w17,title,ag,an))
    df=pd.DataFrame(rows,columns=['team','p_adv','surv_W15','surv_W16','win_W17','title_eq','W17_anchor','anchor_pieces'])
    df['title_share']=df['title_eq']/df['title_eq'].sum()
    return df.sort_values('title_share',ascending=False)

if __name__=='__main__':
    rf=sys.argv[1]; me=sys.argv[2] if len(sys.argv)>2 else 'rsbathla'
    df=chain(json.load(open(rf)),me)
    print(f"=== {rf}: FULL SURVIVAL CHAIN (advance x W15 x W16 x W17) ===\n")
    print(f"  {'team':16s} {'P(adv)':>6} {'W15':>5} {'W16':>5} {'W17':>5} {'title%':>6}  anchor")
    for _,r in df.iterrows():
        s=' <YOU' if r['team']==me else ''
        print(f"  {r['team']:16s} {r.p_adv*100:5.0f}% {r.surv_W15*100:4.0f}% {r.surv_W16*100:4.0f}% {r.win_W17*100:4.0f}% {r.title_share*100:5.1f}%  {r.W17_anchor}({r.anchor_pieces}){s}")
    df.to_csv(rf.replace('rosters','chain').replace('.json','.csv'),index=False)
