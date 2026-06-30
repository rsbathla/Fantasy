import os
import pdfplumber, re, pandas as pd, numpy as np
pdf=pdfplumber.open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),"NFLDK2026_CS_ClayProjections2026 (1).pdf"))

TEAMMAP={'BLT':'BAL','CLV':'CLE','ARZ':'ARI','HST':'HOU','LA':'LAR'}  # Clay codes -> standard
QB_COLS=['posrk','ff_pt','g','p_att','comp','p_yds','p_td','int','sk','carry','ru_yds','ru_td']
SK_COLS=['posrk','ff_pt','g','carry','ru_yds','ru_td','targ','rec','re_yd','re_td','car_pct','targ_pct']
SECT={35:('QB',QB_COLS),36:('RB',SK_COLS),37:('RB',SK_COLS),38:('RB',SK_COLS),
      39:('WR',SK_COLS),40:('WR',SK_COLS),41:('WR',SK_COLS),42:('WR',SK_COLS),43:('WR',SK_COLS),
      44:('TE',SK_COLS),45:('TE',SK_COLS)}

def num(x):
    x=x.replace('%','').replace(',','')
    try: return float(x)
    except: return np.nan

rows=[]
for pno,(pos,cols) in SECT.items():
    p=pdf.pages[pno-1]; txt=p.extract_text() or ""
    for ln in txt.split('\n'):
        toks=ln.split()
        if len(toks) < len(cols)+2: continue
        # trailing len(cols) tokens must be numeric-ish
        tail=toks[-len(cols):]
        if not all(re.match(r'^-?[\d,.]+%?$', t) for t in tail): continue
        team=toks[-(len(cols)+1)]
        if not re.match(r'^[A-Z]{2,3}$', team): continue
        name=' '.join(toks[:-(len(cols)+1)])
        if name.lower() in ('quarterback','running back','wide receiver','tight end'): continue
        rec={'name':name,'team':TEAMMAP.get(team,team),'pos':pos}
        for c,v in zip(cols,tail): rec[c]=num(v)
        rows.append(rec)

df=pd.DataFrame(rows).drop_duplicates(['name','pos'])
# fill skill/QB cols
for c in set(QB_COLS+SK_COLS):
    if c not in df: df[c]=np.nan
df=df.fillna({c:0 for c in ['carry','ru_yds','ru_td','targ','rec','re_yd','re_td','p_att','comp','p_yds','p_td','int','sk']})

# DK full PPR season points from components
def bonus(y,thr): return np.where(y>=thr,3.0,0.0)
df['dk_season']=(df['rec']*1 + df['re_yd']*0.1 + df['re_td']*6
              + df['ru_yds']*0.1 + df['ru_td']*6
              + df['p_yds']*0.04 + df['p_td']*4 - df['int']*1
              + bonus(df['re_yd']/df['g'].replace(0,np.nan)*0,100)*0)  # season bonus handled per-game later
df['g']=df['g'].replace(0,np.nan)
df['dk_pg']=df['dk_season']/df['g']
df=df.sort_values('dk_pg',ascending=False)
df.to_csv('clay_2026.csv',index=False)

print("parsed players:", len(df), "| by pos:", df['pos'].value_counts().to_dict())
print("\n=== STUD CHECK: top 15 by DK pts/game ===")
print(df[['name','team','pos','g','dk_pg','targ','carry','re_yd','ru_yds']].head(15).to_string(index=False,
      formatters={'dk_pg':lambda x:f'{x:.1f}'}))
print("\n=== sanity: any inversions? bottom of top-50 ===")
print(df[['name','team','pos','dk_pg']].iloc[45:52].to_string(index=False,formatters={'dk_pg':lambda x:f'{x:.1f}'}))
