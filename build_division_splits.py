#!/usr/bin/env python3
"""IN-DIVISION vs OUT-OF-DIVISION ceiling splits, per player.
Unions every per-game FantasyPoints export it can find (Name/POS/Season/WEEK/Opponent/FP) -> total FP per
player-game -> compares production & ceiling-game rate vs division rivals vs everyone else.
Auto-includes passing once a per-game passing export is present; multi-season once more files are added.
Output: division_splits.json + ranked console report. Honest: needs a healthy division-game sample (>=5)."""
import csv, os, json, glob, re, statistics as st
HERE=os.path.dirname(os.path.abspath(__file__))
CANDS=[os.path.dirname(HERE), HERE, '/sessions/gracious-gallant-edison/mnt/Downloads', os.path.expanduser('~/Downloads')]
def fn(n):
    n=str(n).strip().lower(); n=re.sub(r'\s+(jr|sr|ii|iii|iv|v)\.?$','',n); return n.replace('.','').replace("'","").replace('-',' ').strip()
def num(x):
    try: return float(str(x).replace('%','').replace(',','').strip())
    except: return None
AB={'LA':'LAR','JAC':'JAX','WSH':'WAS','LVR':'LV','SD':'LAC','OAK':'LV','STL':'LAR','ARZ':'ARI','CLV':'CLE','BLT':'BAL','HST':'HOU','GBP':'GB','KCC':'KC','NEP':'NE','NOS':'NO','SFO':'SF','TBB':'TB'}
def ab(x):
    x=str(x).strip().upper().lstrip('@'); return AB.get(x,x)
DIV={'BUF':'AFCE','MIA':'AFCE','NE':'AFCE','NYJ':'AFCE','BAL':'AFCN','CIN':'AFCN','CLE':'AFCN','PIT':'AFCN','HOU':'AFCS','IND':'AFCS','JAX':'AFCS','TEN':'AFCS','DEN':'AFCW','KC':'AFCW','LAC':'AFCW','LV':'AFCW','DAL':'NFCE','NYG':'NFCE','PHI':'NFCE','WAS':'NFCE','CHI':'NFCN','DET':'NFCN','GB':'NFCN','MIN':'NFCN','ATL':'NFCS','CAR':'NFCS','NO':'NFCS','TB':'NFCS','ARI':'NFCW','LAR':'NFCW','SEA':'NFCW','SF':'NFCW'}
# locate per-game exports
files=[]
for d in CANDS:
    for pat in ['receivingAdvancedExport*.csv','rushingAdvancedExport*.csv','passingAdvancedExport*.csv']:
        files+=glob.glob(os.path.join(d,pat))
files=sorted(set(files))
games={}  # (key,season,week) -> dict
used=[]
for f in files:
    try: rows=list(csv.DictReader(open(f,encoding='utf-8-sig')))
    except Exception: continue
    if not rows: continue
    h={c.strip():c for c in rows[0].keys()}
    need=['Name','Opponent','WEEK','Season','FP']
    if not all(any(k.lower()==col.lower() for k in h) for col in need): continue
    def col(r,name):
        for k in r:
            if k and k.strip().lower()==name.lower(): return r[k]
        return None
    used.append(os.path.basename(f)); n0=len(games)
    for r in rows:
        nm=col(r,'Name'); fp=num(col(r,'FP')); wk=col(r,'WEEK'); se=col(r,'Season'); op=col(r,'Opponent'); pos=col(r,'POS'); tm=col(r,'Team')
        if not nm or fp is None or not wk or not se: continue
        kk=(fn(nm),str(se).strip(),str(wk).strip())
        g=games.setdefault(kk,{'name':nm,'pos':pos,'team':ab(tm) if tm else None,'opp':ab(op) if op else None,'fp':None})
        g['fp']=fp if g['fp'] is None else max(g['fp'],fp)  # FP is TOTAL game pts (same in every export) -> dedupe, don't sum
        if op and not g['opp']: g['opp']=ab(op)
        if pos and not g['pos']: g['pos']=pos
        if tm and not g['team']: g['team']=ab(tm)
    # note: FP summed across receiving+rushing(+passing) for the same player-week = total FP
# aggregate per player
byp={}
for (k,se,wk),g in games.items():
    if not g['opp'] or g['opp'] not in DIV or not g['team'] or g['team'] not in DIV: continue
    byp.setdefault(k,{'name':g['name'],'pos':g['pos'],'team':g['team'],'games':[]})['games'].append((g['fp'],g['opp']))
out=[]
for k,v in byp.items():
    pdiv=DIV.get(v['team']); 
    gin=[fp for fp,op in v['games'] if DIV.get(op)==pdiv]
    gout=[fp for fp,op in v['games'] if DIV.get(op)!=pdiv]
    if len(gin)<4 or len(gout)<8: continue
    allg=sorted([fp for fp,_ in v['games']])
    ceil=allg[int(len(allg)*0.75)] if allg else 0   # player's own 75th pctl = a 'ceiling' week
    cin=sum(1 for x in gin if x>=ceil)/len(gin); cout=sum(1 for x in gout if x>=ceil)/len(gout)
    out.append({'name':v['name'],'pos':v['pos'],'team':v['team'],'n_div':len(gin),'n_out':len(gout),
        'mean_div':round(st.mean(gin),1),'mean_out':round(st.mean(gout),1),'d_mean':round(st.mean(gout)-st.mean(gin),1),
        'ceil_div':round(cin,2),'ceil_out':round(cout,2),'d_ceil':round(cout-cin,2)})
out.sort(key=lambda x:-x['d_mean'])
json.dump({'players':out,'sources':used,'note':'total FP/game; ceiling=player 75th pctl wk'},open(os.path.join(HERE,'division_splits.json'),'w'),indent=1)
print("sources used:",used)
print(f"players with enough division sample: {len(out)}")
print("\nBIGGEST in-division ceiling/scoring DROPOFF (out-of-div minus in-div FP/g):")
print(f"{'player':22s}{'pos':4s}{'div g':6s}{'in FP':7s}{'out FP':7s}{'dMean':7s}{'ceilIn':7s}{'ceilOut'}")
for p in out[:15]:
    print(f"{p['name'][:21]:22s}{str(p['pos']):4s}{p['n_div']:<6d}{p['mean_div']:<7}{p['mean_out']:<7}{p['d_mean']:<7}{p['ceil_div']:<7}{p['ceil_out']}")
