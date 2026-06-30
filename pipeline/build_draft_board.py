import pandas as pd, numpy as np, json, re, os, glob
HERE=os.path.dirname(os.path.abspath(__file__)); DL=os.path.dirname(os.path.dirname(HERE))
def _latest(*pats):
    h=[x for q in pats for x in glob.glob(q)]
    return max(h, key=os.path.getmtime) if h else pats[0]   # newest by mtime (was: wrong alphabetical sort)
NAME2AB=None
def fn(n):
    n=str(n).strip().lower(); n=re.sub(r'\s+(jr|sr|ii|iii|iv|v)\.?$','',n); n=n.replace('.','').replace("'","").replace('-',' '); return ' '.join(n.split())

adp=pd.read_csv(_latest(f"{DL}/DkPreDraftRankings*.csv", f"{DL}/Downloads/DkPreDraftRankings*.csv", f"{DL}/uploads/DkPreDraftRankings*.csv", f"{DL}/../uploads/DkPreDraftRankings*.csv"))
adp=adp[['Name','Position','ADP','Team']].dropna(subset=['ADP']).copy(); adp['Team']=adp['Team'].replace({'LA':'LAR'})
adp['key']=adp['Name'].map(fn)
clay=pd.read_csv('clay_2026.csv'); clay['key']=clay['name'].map(fn)
sim=pd.read_csv('player_sim_distributions.csv'); sim['key']=sim['name'].map(fn)
BYE=json.load(open('byes_2026.json'))
games17={}
for a,b in [tuple(g) for g in json.load(open('games_by_week.json'))['17']]:
    games17[a]=f"{a}@{b}"; games17[b]=f"{a}@{b}"
# also W15/W16 opp
sched={int(w):{} for w in [15,16,17]}
for w in [15,16,17]:
    for a,b in [tuple(g) for g in json.load(open('games_by_week.json'))[str(w)]]:
        sched[w][a]=b; sched[w][b]=a
blow=pd.read_csv('w17_blowup_rank.csv')  # game, p99, p99_rank
blow_tier={}
for _,r in blow.iterrows():
    for tm in r['game'].split('+'): blow_tier[tm]=int(r['p99_rank'])

rows=[]
for _,a in adp.iterrows():
    k=a['key']; c=clay[clay.key==k]; s=sim[sim.key==k]
    tm=a['Team']; pos=a['Position']
    proj=float(c['dk_pg'].iloc[0]) if len(c) else np.nan
    p95=float(s['p95'].iloc[0]) if len(s) else np.nan
    cv=float(s['cv'].iloc[0]) if len(s) else np.nan
    spike=float(s['spike_pct'].iloc[0]) if len(s) else np.nan
    rows.append(dict(name=a['Name'],key=k,pos=pos,team=tm,adp=a['ADP'],
        proj_pg=proj, p95=p95, cv=cv, spike=spike, bye=BYE.get(tm),
        w15_opp=sched[15].get(tm), w16_opp=sched[16].get(tm), w17_game=games17.get(tm),
        w17_blowup_rank=blow_tier.get(tm,99)))
B=pd.DataFrame(rows)
# position-relative percentiles for advancement (proj) and ceiling (p95)
for col,new in [('proj_pg','adv_pct'),('p95','ceil_pct')]:
    B[new]=B.groupby('pos')[col].rank(pct=True)
B.to_csv('draft_board_signals.csv',index=False)
print("draft_board_signals.csv:", len(B), "players")
print(B[B.proj_pg.notna()].sort_values('proj_pg',ascending=False)[['name','pos','team','adp','proj_pg','p95','cv','bye','w17_game','w17_blowup_rank']].head(8).to_string(index=False))
