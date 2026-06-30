#!/usr/bin/env python3
"""Rich pick dashboard. DK board (clip/file) -> engine recs (JSON) -> win-Δ (top N)
-> qual summary + tweets + overlays -> writes pick_dashboard.html and opens it.
Usage: python dashboard.py clip --seat rsbathla   (or a Board.txt path)  [--n 10]"""
import re,sys,os,json,argparse,subprocess,webbrowser,csv,glob,shutil
import pandas as pd
HERE=os.path.dirname(os.path.abspath(__file__)); PIPE=os.path.join(HERE,'pipeline')
def fn(n):
    n=str(n).strip().lower(); n=re.sub(r'\s+(jr|sr|ii|iii|iv|v)\.?$','',n); n=n.replace('.','').replace("'","").replace('-',' '); return ' '.join(n.split())
def san(s): return ''.join(c for c in str(s if s is not None else '') if c in '\t\n' or ord(c)>=32)
ap=argparse.ArgumentParser(); ap.add_argument('board'); ap.add_argument('--seat',required=True)
ap.add_argument('--n',type=int,default=10); ap.add_argument('--teams',type=int,default=12); ap.add_argument('--ns',type=int,default=1200)
a=ap.parse_args()
def read_clip():
    if shutil.which('pbpaste'): return subprocess.run(['pbpaste'],capture_output=True,text=True).stdout
    if shutil.which('powershell'): return subprocess.run(['powershell','-NoProfile','-Command','Get-Clipboard'],capture_output=True,text=True).stdout
    import pyperclip; return pyperclip.paste()
txt=read_clip() if a.board.lower()=='clip' else open(a.board,errors='ignore').read()
txt=txt.replace(chr(13)+chr(10),chr(10)).replace(chr(13),chr(10))
heads=re.findall(r'\n([A-Za-z0-9_\.]+)\s*\nQB\s*\n\d+\s*\nRB\s*\n\d+\s*\nWR\s*\n\d+\s*\nTE\s*\n\d+', txt)
if a.seat.isdigit(): seat=int(a.seat)
elif a.seat in heads: seat=heads.index(a.seat)+1
else: seat=next((i+1 for i,h in enumerate(heads) if a.seat.lower() in h.lower()),None)
if seat is None: raise SystemExit("seat %s not found in %s"%(a.seat,heads))
T=a.teams
def ov_for(s,r): return (r-1)*T+(s if r%2==1 else T+1-s)
def seat_of(o):
    r=(o-1)//T+1; p=o-(r-1)*T; return p if r%2==1 else T+1-p
named=re.findall(r'(\d+)\.(\d+)\s*\n\s*(\d+)\s*\n\s*(.+?)\s*icon\s*\n\s*(QB|RB|WR|TE)\s*\n\s*([A-Z]{2,3})\s*\n\s*\(BYE', txt)
bypick={}
if named:
    for rnd,inr,ov,name,pos,team in named: bypick[int(ov)]=name.strip()
else:
    af=next((os.path.join(HERE,x) for x in ("dk_adp.csv","DkPreDraftRankings.csv") if os.path.exists(os.path.join(HERE,x))),None) or ((sorted(glob.glob(os.path.join(HERE,"DkPreDraftRankings*.csv")))+[None])[0])
    picks=sorted(set((int(o),p,t) for _,_,o,p,t in re.findall(r'(\d+)\.(\d+)\s*\n\s*(\d+)\s*\n\s*(QB|RB|WR|TE)\s*\n\s*([A-Z]{2,3})', txt)))
    if af and os.path.exists(af):
        adp=pd.read_csv(af); adp=adp[['Name','Position','ADP','Team']].dropna(subset=['ADP']); adp['Team']=adp['Team'].replace({'LA':'LAR'}); taken=set()
        for o,pos,team in picks:
            c=adp[(adp.Position==pos)&(adp.Team==team)&(~adp.Name.isin(taken))]
            if len(c): nm=c.assign(d=(c.ADP-o).abs()).sort_values('d').iloc[0]['Name']; taken.add(nm); bypick[o]=nm
rosters={}
for o,nm in bypick.items():
    s=seat_of(o); h=heads[s-1] if s-1<len(heads) else "seat%d"%s; rosters.setdefault(h,[]).append(nm)
me=heads[seat-1] if seat-1<len(heads) else a.seat; rosters.setdefault(me,[])
my_ov={ov_for(seat,r) for r in range(1,21)}
mine=[bypick[o] for o in sorted(my_ov) if o in bypick]
next_pick=min([o for o in sorted(my_ov) if o not in bypick] or [(max(bypick)+1) if bypick else seat])
gone=list(bypick.values())
ej=subprocess.run([sys.executable,os.path.join(HERE,'draft_assistant.py'),'--pick',str(next_pick),'--mine',",".join(mine),'--gone',",".join(gone),'--n','24','--json'],capture_output=True,text=True,cwd=HERE)
try: obj=json.loads(ej.stdout)
except Exception: obj={"cands":[],"qb":0,"rb":0,"wr":0,"te":0,"anchor":""}
cset=obj.get('cands',[])
rowsE=[{'name':c.get('name'),'pos':c.get('pos'),'team':(c.get('team') if c.get('team') and c.get('team')!='nan' else 'FA'),'rk':(int(c['merged_rank']) if c.get('merged_rank') is not None else None),'ceil':(round(c['p95']) if c.get('p95') is not None else None),'tags':san(c.get('tags','')),'regrank':(int(c['reg_rank']) if c.get('reg_rank') is not None else None),'w15':c.get('w15_opp'),'w16':c.get('w16_opp'),'w17':c.get('w17_game'),'tail':(int(c['w17_blowup_rank']) if c.get('w17_blowup_rank') is not None else None),'bye':(int(c['bye']) if c.get('bye') is not None else None)} for c in cset]
roster_str="%d QB  %d RB  %d WR  %d TE"%(obj.get('qb',0),obj.get('rb',0),obj.get('wr',0),obj.get('te',0)); anchor=san(obj.get('anchor',''))
cands=[r['name'] for r in rowsE[:a.n]]
base,wdel={"title":0,"adv":0,"w17":0},{}
if cands:
    os.chdir(PIPE); sys.path.insert(0,PIPE)
    import win_delta as wd
    base,wdel=wd.win_deltas(rosters,me,cands,ns=a.ns); os.chdir(HERE)
def loadcsv(p):
    d={}
    if os.path.exists(p):
        for r in csv.DictReader(open(p,encoding='utf-8')): d[fn(r['name'])]=r
    return d
OV=loadcsv(os.path.join(HERE,'overlays.csv')); QS=loadcsv(os.path.join(HERE,'qual_summary.csv')); VID=loadcsv(os.path.join(HERE,'video_notes.csv')); BBN=loadcsv(os.path.join(HERE,'bestball_notes.csv'))
TEAMN={}
_tp=os.path.join(HERE,'team_notes.csv')
if os.path.exists(_tp):
    import csv as _c
    for _r in _c.DictReader(open(_tp,encoding='utf-8')): TEAMN[_r['team']]=_r['team_note']
_STOP=set('brown williams smith jones johnson davis miller wilson moore taylor thomas jackson white harris hill allen young walker wright king scott green adams hall mitchell carter evans watson bell cook gray james reed price love robinson chase hunter likely worthy brooks mason branch flowers rice ward dell lamb tate moss'.split())
NOTES={}; tw=sorted(glob.glob(os.path.join(os.path.dirname(HERE),'tweet-bot*','tweets_export.jsonl')))
if tw and cands:
    BULL=re.compile(r"breakout|smash|ceiling|upside|\bbuy\b|\btarget|sleeper|\bvalue\b|\bwr1\b|\brb1\b|elite|\bstud\b|\bboom\b")
    BEAR=re.compile(r"avoid|\bfade|\bbust\b|committee|concern|injur|\bhurt\b|\bsit\b|regress|declin|suspend|\bjail\b|\btrap\b|downgrade|out for|miss")
    def pats(nm):
        t=[x for x in fn(nm).split() if x not in {'jr','sr','ii','iii','iv','v'}]; L=t[-1]; p={" ".join(t)}
        if len(t)>=2:
            p.add(t[0]+" "+L); ini="".join(x for x in t[:-1] if len(x)==1)
            if len(ini)>=2: p.add(ini+" "+L)
        return L,p
    pl=[(c,)+pats(c) for c in cands]
    for r in (json.loads(l) for l in open(tw[-1],encoding='utf-8')):
        if r.get('is_retweet'): continue
        raw=san(re.sub(r'\s+',' ',r.get('text','')).strip()); tn=" "+fn(raw)+" "
        nb=len(BULL.findall(tn)); nr=len(BEAR.findall(tn))
        if nb==nr: continue
        for c,L,P in pl:
            if (((" "+L+" ") in tn and len(L)>=5 and L not in _STOP) or any((" "+p+" ") in tn for p in P)): NOTES.setdefault(c,[]).append([r.get('reliability_tier'),'up' if nb>nr else 'dn',san(r.get('handle')),raw[:150]])
    for c in list(NOTES): NOTES[c]=sorted(NOTES[c],key=lambda x:(x[0]!='A',-len(x[3])))[:3]
def humanize(r):
    t=r.get('tags','') or ''; seg=[]
    m=re.search(r'val\+(\d+)',t);  seg.append('fell %s past board value'%m.group(1)) if m else None
    m=re.search(r'REACH(\d+)',t);   seg.append('a reach (%s spots early)'%m.group(1)) if m else None
    m=re.search(r'2-side (\S+)',t); seg.append('completes your %s stack (bring-back)'%m.group(1)) if m else None
    m=re.search(r'commit (\S+)',t); seg.append('commits your %s anchor'%m.group(1)) if m else None
    m=re.search(r'seed ([A-Z@]+)',t);seg.append('seeds the %s game'%m.group(1)) if m else None
    if 'boom' in t: seg.append('high-ceiling boom profile')
    m=re.search(r'need(QB|RB|WR|TE)',t); seg.append('fills a %s need'%m.group(1)) if m else None
    m=re.search(r'(QB|RB|WR|TE)full',t); seg.append('%s already full'%m.group(1)) if m else None
    if 'BYE' in t: seg.append('bye-week pileup risk')
    body=', '.join(seg) if seg else 'no standout board edge'
    return '%s/%s - %s (structural read; no coachspeak in corpus).'%(r.get('pos'),r.get('team'),body)
data=[]
for i,r in enumerate(rowsE):
    k=fn(r['name'])
    data.append({**r,'idx':i+1,'qsum':(san(QS.get(k,{}).get('summary','')) or humanize(r)),'quote':san(QS.get(k,{}).get('top_quote','')),'ov':san(OV.get(k,{}).get('note','')),'ovt':OV.get(k,{}).get('type',''),'notes':NOTES.get(r['name'],[]),'video':san(VID.get(k,{}).get('video_note','')),'bbnote':san(BBN.get(k,{}).get('bestball_note','')),'teamnote':san(TEAMN.get(r['team'],'')),'wd':wdel.get(r['name'])})
ranked=sorted([d for d in data if d.get('wd') is not None], key=lambda d:-d['wd']['dtitle']) or list(data)
def _clean(d): return d.get('ovt') not in ('trap','risk')
rec=next((d for d in ranked if _clean(d)), (ranked[0] if ranked else None))
verdict='No candidates parsed - re-copy the board (Ctrl+A) and re-run.'
if rec:
    counts={'QB':obj.get('qb',0),'RB':obj.get('rb',0),'WR':obj.get('wr',0),'TE':obj.get('te',0)}
    need=[p for p in ['QB','TE','RB','WR'] if counts.get(p,0)==0]
    why=[]
    if rec['pos'] in need: why.append("you're 0-%s"%rec['pos'])
    if rec.get('wd'): why.append('+%.2f%% title'%rec['wd']['dtitle'])
    ql=(rec.get('qsum') or '').split(' ')[0].lower()
    if ql in ('bullish','bearish','mixed'): why.append('coachspeak %s'%ql)
    if rec.get('ovt')=='age': why.append('age-flagged')
    top=ranked[0] if ranked else None; pv=''
    if top and (top is not rec) and top.get('ovt') in ('trap','risk'): pv=' (engine #1 %s is %s-flagged - pivot)'%(top['name'],top['ovt'])
    nxt=[p for p in need if p!=rec['pos']]; after=(' Then %s.'%'/'.join(nxt)) if nxt else ''
    verdict='TAKE %s (%s/%s) - %s.%s%s'%(rec['name'],rec['pos'],rec['team'],', '.join(why) if why else (rec.get('qsum') or '')[:80],pv,after)
verdict=san(verdict)
PAGE=open(os.path.join(HERE,'_dash_template.html'),encoding='utf-8').read()
html=PAGE.replace('__DATA__',json.dumps(data,ensure_ascii=True)).replace('__ROSTER__',roster_str).replace('__ANCHOR__',anchor).replace('__PICK__',str(next_pick)).replace('__N__',str(a.n)).replace('__BASE__',json.dumps(base)).replace('__VERDICT__',verdict)
import ctx_panel; html=ctx_panel.inject(html)   # 4-layer NFL Pro EPA drilldown (click the EPA chip on a pick row)
op=os.path.join(HERE,'pick_dashboard.html'); open(op,'w',encoding='utf-8').write(html)
print("wrote",op,"| pick",next_pick,"| cands",len(rowsE),"| roster",roster_str)
if not rowsE: print("WARNING: 0 candidates. engine stderr:",ej.stderr[:300])
try: webbrowser.open('file://'+op)
except Exception: pass
