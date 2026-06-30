#!/usr/bin/env python3
"""Build a comprehensive PER-TEAM dashboard: every draftable player grouped by NFL team,
with all four layers — Data, Upside, Best-ball, Qualitative. Self-contained HTML."""
import csv,json,re,os
HERE=os.path.dirname(os.path.abspath(__file__))
def P(f): return os.path.join(HERE,f)
def fn(n):
    n=str(n).strip().lower(); n=re.sub(r'\s+(jr|sr|ii|iii|iv|v)\.?$','',n)
    n=n.replace('.','').replace("'","").replace('-',' '); return ' '.join(n.split())
def rows(f):
    p=P(f)
    return list(csv.DictReader(open(p,encoding='utf-8'))) if os.path.exists(p) else []
def num(x,d=None):
    try: return float(x)
    except: return d
TEAMS={'ARI':'Arizona Cardinals','ATL':'Atlanta Falcons','BAL':'Baltimore Ravens','BUF':'Buffalo Bills','CAR':'Carolina Panthers','CHI':'Chicago Bears','CIN':'Cincinnati Bengals','CLE':'Cleveland Browns','DAL':'Dallas Cowboys','DEN':'Denver Broncos','DET':'Detroit Lions','GB':'Green Bay Packers','HOU':'Houston Texans','IND':'Indianapolis Colts','JAX':'Jacksonville Jaguars','KC':'Kansas City Chiefs','LAC':'Los Angeles Chargers','LAR':'Los Angeles Rams','LV':'Las Vegas Raiders','MIA':'Miami Dolphins','MIN':'Minnesota Vikings','NE':'New England Patriots','NO':'New Orleans Saints','NYG':'New York Giants','NYJ':'New York Jets','PHI':'Philadelphia Eagles','PIT':'Pittsburgh Steelers','SEA':'Seattle Seahawks','SF':'San Francisco 49ers','TB':'Tampa Bay Buccaneers','TEN':'Tennessee Titans','WAS':'Washington Commanders'}
TEAMS['FA']='Free Agents — unsigned at snapshot'
TMAP={'LA':'LAR','JAC':'JAX','WSH':'WAS','ARZ':'ARI','GNB':'GB','KAN':'KC','SFO':'SF','TAM':'TB','NWE':'NE','NOR':'NO'}
ADPTEAM={fn(r['Name']):(r.get('Team') or '').strip() for r in rows('dk_adp.csv')}
# ---- load layers keyed by fn(name) ----
QS={fn(r['name']):r for r in rows('qual_summary.csv')}
VID={fn(r['name']):r['video_note'] for r in rows('video_notes.csv') if r.get('video_note')}
BB={fn(r['name']):r['bestball_note'] for r in rows('bestball_notes.csv') if r.get('bestball_note')}
SIG={fn(r['name']):r for r in rows('qual_signal.csv')}
OV={}
for r in rows('overlays.csv'):
    OV.setdefault(fn(r['name']),[]).append((r.get('type','').strip(),r.get('note','').strip()))
TN={ (TMAP.get(r['team'],r['team'])):r['team_note'] for r in rows('team_notes.csv') if r.get('team_note')}
BM=json.load(open(P('boom/boom_marks.json'),encoding='utf-8')) if os.path.exists(P('boom/boom_marks.json')) else {}  # boom ceiling marks
# ---- spine ----
sp=rows('draft_board_signals.csv')
# reg-season rank by projected pts/game (overall)
proj=[(fn(r['name']),num(r.get('proj_pg'))) for r in sp]
order=sorted([x for x in proj if x[1] is not None],key=lambda x:-x[1])
REG={k:i+1 for i,(k,v) in enumerate(order)}
players=[]
for r in sp:
    nm=r['name']; k=fn(nm); _t0=(ADPTEAM.get(k) or (r.get('team') or '')).strip(); tm=TMAP.get(_t0,_t0)
    p95=num(r.get('p95')); adp=num(r.get('adp')); rk=num(r.get('merged_rank'))
    ov=OV.get(k,[]); qsrow=QS.get(k); sig=SIG.get(k)
    cv=num(r.get('cv')); 
    tags=[]
    if p95 and p95>=33: tags.append('α-ceiling')
    if cv and cv>=1.0 and r.get('pos') in ('WR','TE'): tags.append('boom')
    if rk and adp and rk<=adp-8: tags.append('value')
    if rk and adp and rk>=adp+10: tags.append('reach-risk')
    if ov: tags.append('risk')
    players.append({
      'n':nm,'p':r.get('pos'),'t':tm,
      'adp':round(adp,1) if adp else None,'rk':int(rk) if rk else None,
      'cl':round(p95) if p95 else None,'clp':round(num(r.get('ceil_pct'),0)*100),
      'rr':REG.get(k),'ap':round(num(r.get('adv_pct'),0)*100),
      'sp':round(num(r.get('spike'),0)*100,1) if r.get('spike') else None,
      'cv':round(cv,2) if cv else None,
      'pg':round(num(r.get('proj_pg'),0),1) if r.get('proj_pg') else None,
      'by':int(num(r.get('bye'),0)) if r.get('bye') else None,
      'w15':r.get('w15_opp'),'w16':r.get('w16_opp'),'w17':r.get('w17_game'),'tl':int(num(r.get('w17_blowup_rank'),0)) if r.get('w17_blowup_rank') else None,
      'sm':(qsrow or {}).get('summary',''),'q':(qsrow or {}).get('top_quote',''),
      'bb':BB.get(k,''),'vd':VID.get(k,''),
      'ov':[{'ty':t,'no':n} for t,n in ov],
      'qs':round(num((sig or {}).get('qual_score'),0),2) if sig else None,
      'boom':({'badge':BM[k]['badge'],'tier':BM[k]['tier']} if k in BM else None),
    })
for pl in players:
    if pl['t']=='FA': pl['w15']=pl['w16']=pl['w17']=None; pl['tl']=None
# ---- group by team ----
teamobj={}
for pl in players:
    t=pl['t']
    if t not in teamobj:
        teamobj[t]={'t':t,'nm':TEAMS.get(t,t),'by':pl['by'],'w15':pl['w15'],'w16':pl['w16'],'w17':pl['w17'],'tl':pl['tl'],'note':TN.get(t,''),'players':[]}
    teamobj[t]['players'].append(pl)
for t in teamobj.values():
    t['players'].sort(key=lambda x:(x['rk'] if x['rk'] else 9999))
    t['best']=t['players'][0]['rk'] if t['players'] else 9999
    t['nplay']=len(t['players'])
for t in teamobj.values():
    t['nalpha']=sum(1 for p in t['players'] if p['cl'] and p['cl']>=33)
teamlist=sorted(teamobj.values(),key=lambda x:(10**9 if x['t']=='FA' else x['best']))
DATA=json.dumps(teamlist,ensure_ascii=False)
cov={'players':len(players),'teams':len(teamlist),
 'sum':sum(1 for p in players if p['sm']),'vid':sum(1 for p in players if p['vd']),
 'bb':sum(1 for p in players if p['bb']),'ov':sum(1 for p in players if p['ov']),
 'teamnotes':sum(1 for t in teamlist if t['note'])}
print("coverage:",json.dumps(cov))
tpl=open(P('_team_template.html'),encoding='utf-8').read()
out=tpl.replace('__DATA__',DATA).replace('__COV__',json.dumps(cov))
import ctx_panel; out=ctx_panel.inject(out)   # 4-layer NFL Pro EPA drilldown (click the EPA chip on a player row)
open(P('team_dashboard.html'),'w',encoding='utf-8').write(out)
print("wrote team_dashboard.html  bytes:",os.path.getsize(P('team_dashboard.html')))
# spot checks
for tm in ['CIN','SF','DET']:
    o=teamobj.get(tm)
    if o: print(" %s: %d players, best rk %s, teamnote %s, top3: %s"%(tm,o['nplay'],o['best'],'Y' if o['note'] else 'n',", ".join(p['n'] for p in o['players'][:3])))
