#!/usr/bin/env python3
"""Phase 4: ingest the NFL Pro (pro.nfl.com) scrape -> REAL EPA + NGS metrics, season-aggregated.
QB: EPA/DB, CPOE, time-to-throw, pressure-rate-faced. Rec: Rec EPA, separation, YACOE, CROE. Rush: Rush EPA, RYOE, top speed."""
import core, pandas as pd, glob, os, csv
SCR=core.find_data('NFL-master','nfl_chat_app','app_data','nfl_pro_scraper')
fn=core.fn
def num(s): return pd.to_numeric(s.astype(str).str.replace('%','',regex=False).str.replace(',','',regex=False),errors='coerce')
def loadall(folder):
    fr=[pd.read_csv(f) for f in sorted(glob.glob(f'{SCR}/{folder}/week*_ALL.csv'))]
    return pd.concat(fr,ignore_index=True) if fr else pd.DataFrame()
def wavg(g,col,wt):  # weighted mean over season
    w=num(g[wt]); v=num(g[col]); m=(v*w).sum(); s=w.sum(); return (m/s) if s else None
def colpick(df,*names):
    for n in names:
        if n in df.columns: return n
    return None
# ---- passing (QB) ----
P=loadall('passing'); qb={}
if len(P):
    P['k']=P['Player'].map(fn)
    sep=colpick(P,'Avg. Sep','Avg Sep')
    for k,g in P.groupby('k'):
        db=num(g['DB']).sum(); epa=num(g['EPA']).sum(); qbp=num(g['QBP']).sum()
        qb[k]={'qb_epa_db':round(epa/db,3) if db else None,
               'qb_cpoe':round(wavg(g,'CPOE','DB'),2) if db else None,
               'qb_ttt':round(wavg(g,'TTT','DB'),2) if db and 'TTT' in g else None,
               'qb_pressure_rate':round(qbp/db*100,1) if db else None}
# ---- receiving (WR/TE/RB) ----
R=loadall('receiving'); rec={}
if len(R):
    R['k']=R['Player'].map(fn); sepc=colpick(R,'Avg. Sep','Avg Sep'); rte=colpick(R,'Rts','RTE')
    for k,g in R.groupby('k'):
        rts=num(g[rte]).sum(); repa=num(g['Rec EPA']).sum() if 'Rec EPA' in g else None; tgt=num(g['Tgt']).sum(); rcv=num(g['Rec']).sum()
        rec[k]={'rec_epa_route':round(repa/rts,3) if (repa is not None and rts) else None,
                'rec_separation':round(wavg(g,sepc,'Tgt'),2) if (sepc and tgt) else None,
                'rec_yacoe':round(num(g['YACOE']).sum()/rcv,2) if ('YACOE' in g and rcv) else None,
                'rec_croe':round(wavg(g,'CROE','Tgt'),1) if ('CROE' in g and tgt) else None}
# ---- rushing (RB) ----
RU=loadall('rushing'); rush={}
if len(RU):
    RU['k']=RU['Player'].map(fn); spd=colpick(RU,'20+ MPH','15+ MPH')
    for k,g in RU.groupby('k'):
        att=num(g['Att']).sum(); repa=num(g['Rush EPA']).sum() if 'Rush EPA' in g else None; ryoe=num(g['RYOE']).sum() if 'RYOE' in g else None
        rush[k]={'rush_epa_att':round(repa/att,3) if (repa is not None and att) else None,
                 'ryoe_att':round(ryoe/att,2) if (ryoe is not None and att) else None,
                 'rb_topspeed':int(num(g[spd]).sum()) if spd else None}
# ---- merge ----
feats=list(csv.DictReader(open(core.P('features.csv'),encoding='utf-8')))
n={'qb':0,'rec':0,'rush':0}
for f in feats:
    k=fn(f['name']); pos=f['pos']
    if pos=='QB' and qb.get(k):
        for kk,v in qb[k].items():
            if v is not None: f[kk]=v
        if qb[k].get('qb_epa_db') is not None: f['epa_real']=qb[k]['qb_epa_db']; f['epa_proxy_src']='EPA/DB (NFL Pro)'
        n['qb']+=1
    if pos in ('WR','TE','RB') and rec.get(k):
        for kk,v in rec[k].items():
            if v is not None: f[kk]=v
        if rec[k].get('rec_epa_route') is not None: f['epa_real']=rec[k]['rec_epa_route']; f['epa_proxy_src']='Rec EPA/route (NFL Pro)'
        n['rec']+=1
    if pos=='RB' and rush.get(k):
        for kk,v in rush[k].items():
            if v is not None: f[kk]=v
        n['rush']+=1
cols=[]
for f in feats:
    for c in f:
        if c not in cols: cols.append(c)
with open(core.P('features.csv'),'w',newline='',encoding='utf-8') as fh:
    w=csv.DictWriter(fh,fieldnames=cols); w.writeheader(); [w.writerow(f) for f in feats]
core.safe_json_dump({'meta':{'n':len(feats),'cols':cols,'source':'+ NFL Pro real EPA/NGS'},'players':feats}, core.P('features.json'))
print("REAL EPA/NGS merged -> QB %d, receivers %d, RB rush %d | total cols %d"%(n['qb'],n['rec'],n['rush'],len(cols)))
d={fn(f['name']):f for f in feats}
for nm in ["Josh Allen","Lamar Jackson","Ja'Marr Chase","Puka Nacua","Brock Bowers","Bijan Robinson"]:
    f=d.get(fn(nm),{})
    print(" %-18s | qbEPA/DB=%s CPOE=%s TTT=%s pressFaced%%=%s | recEPA/rt=%s sep=%s YACOE=%s | rushEPA/att=%s RYOE/att=%s 20mph=%s"%(
        nm,f.get('qb_epa_db'),f.get('qb_cpoe'),f.get('qb_ttt'),f.get('qb_pressure_rate'),f.get('rec_epa_route'),f.get('rec_separation'),f.get('rec_yacoe'),f.get('rush_epa_att'),f.get('ryoe_att'),f.get('rb_topspeed')))
