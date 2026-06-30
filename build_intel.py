#!/usr/bin/env python3
"""Intel: per-PLAYER and per-TEAM cards.
Tweets: FULL-NAME match + MLB exclusion + JOKE/PROMO filter; split about vs comparables; deduped;
per-handle capped; recency-sorted; insight-tagged (route/coverage/scheme claims) + claim backtest.
Upside = MODEL DRIVERS (stable) vs OFF-MODEL (dropped low-sig) flavor.
Teams: team-level tweets (nickname or >=2 same-team players) + ADVANCED STATS (offense env from
team_env+features; defense cov/run/rush pctl + funnel lean/SHIFT from defense.json/defensive_profile;
OC/DC + moves + rookies) + key players. Reads tweet-bot_3/tweets.db (daily auto-ingest)."""
import json, os, re, sqlite3, datetime
HERE=os.path.dirname(os.path.abspath(__file__)); import core
DB=os.path.join(HERE,'..','Downloads','tweet-bot_3','tweets.db')
def norm(s): return ' '.join(re.sub(r"[^a-z0-9 ]",' ',core.fn(s)).split())  # canonical: core.fn key + strip residual tweet punctuation (one normalizer)
def epoch(s):
    try: return datetime.datetime.strptime(s,'%a %b %d %H:%M:%S %z %Y').timestamp()
    except: return 0
def num(x):
    try: return float(x)
    except: return None
FULL2ABBR={'Arizona Cardinals':'ARI','Atlanta Falcons':'ATL','Baltimore Ravens':'BAL','Buffalo Bills':'BUF','Carolina Panthers':'CAR','Chicago Bears':'CHI','Cincinnati Bengals':'CIN','Cleveland Browns':'CLE','Dallas Cowboys':'DAL','Denver Broncos':'DEN','Detroit Lions':'DET','Green Bay Packers':'GB','Houston Texans':'HOU','Indianapolis Colts':'IND','Jacksonville Jaguars':'JAX','Kansas City Chiefs':'KC','Los Angeles Chargers':'LAC','Los Angeles Rams':'LAR','Las Vegas Raiders':'LV','Miami Dolphins':'MIA','Minnesota Vikings':'MIN','New England Patriots':'NE','New Orleans Saints':'NO','New York Giants':'NYG','New York Jets':'NYJ','Philadelphia Eagles':'PHI','Pittsburgh Steelers':'PIT','Seattle Seahawks':'SEA','San Francisco 49ers':'SF','Tampa Bay Buccaneers':'TB','Tennessee Titans':'TEN','Washington Commanders':'WAS'}
NICK={a:full.split()[-1].lower() for full,a in FULL2ABBR.items()}   # abbr -> nickname token
NICK2ABBR={v:k for k,v in NICK.items()}
# ---------- roster + reads ----------
feat=json.load(open(core.P('features.json')))['players']
ROST={core.fn(p['name']):{'name':p['name'],'team':p.get('team'),'pos':p.get('pos'),'adp':p.get('adp'),'proj':p.get('proj_pg')} for p in feat if p.get('pos') in ('QB','RB','WR','TE')}
NAMES=[(k,' '+norm(ROST[k]['name'])+' ') for k in ROST if len(norm(ROST[k]['name']))>=6]
FT={p['team']:p for p in feat if p.get('team')}   # any player per team (for tm_* offense params)
fus={core.fn(p['name']):p for p in json.load(open(core.P('fusion.json')))['players']}
boom=json.load(open(core.P('boom/boom_marks.json'))) if os.path.exists(core.P('boom/boom_marks.json')) else {}
coord=json.load(open(core.P('coordinator_notes.json'))) if os.path.exists(core.P('coordinator_notes.json')) else {}
cchg=json.load(open(core.P('coordinator_changes_2026.json'))) if os.path.exists(core.P('coordinator_changes_2026.json')) else {}
chart=json.load(open(core.P('boom/chart2yr.json'))) if os.path.exists(core.P('boom/chart2yr.json')) else {}
cspec=json.load(open(core.P('boom/cover_spec.json'))) if os.path.exists(core.P('boom/cover_spec.json')) else {}
tenv=json.load(open(core.P('boom/team_env.json'))) if os.path.exists(core.P('boom/team_env.json')) else {}
dfn=json.load(open(core.P('defense.json'))).get('teams',{}) if os.path.exists(core.P('defense.json')) else {}
dprof=json.load(open(core.P('boom/defensive_profile.json'))) if os.path.exists(core.P('boom/defensive_profile.json')) else {}
def mv(p):
    m=(p or {}).get('models',{}).get('matchup'); return m.get('pctl') if isinstance(m,dict) else m
def cons(p):
    c=(p or {}).get('consensus'); return c.get('mean') if isinstance(c,dict) else c
def pctl_table(metric):
    vals={}
    for k,v in chart.items():
        b=v.get('blend') or {}; pos=v.get('pos')
        if metric in b and b[metric] is not None and pos: vals.setdefault(pos,[]).append((k,b[metric]))
    out={}
    for pos,arr in vals.items():
        n=len(arr)
        for k,x in arr: out[k]=round(100*sum(1 for _,y in arr if y<x)/n) if n>1 else 50
    return out
PCT={m:pctl_table(m) for m in ['deep_pct','yprr','tprr','yac_rec','contested_pct','slot_pct']}
DIM={'route':('yprr','STABLE','route efficiency (yprr/tprr) replicates yr/yr (r=0.51-0.69)','model'),
 'volume':('tprr','STABLE','target rate / share persist strongly (r=0.54-0.66)','model'),
 'man':('man','MODERATE','man-coverage skill is a real repeatable trait (r=0.47)','model'),
 'slot':('slot_pct','ROLE-STABLE','alignment (slot share) is role-driven and persists','model'),
 'zone':('zone','LOW','man/zone split barely persists (delta r=0.21) — descriptive, not predictive','off'),
 'single_high':('single_high','LOW','single-high split weakly persists (lift r=0.25)','off'),
 'two_high':('two_high','NOISE','two-high split does not persist (lift r=0.19)','off'),
 'deep':('deep_pct','LEVEL-ONLY','deep role is stable but deep production->boom FLIPS sign yr/yr','off'),
 'yac':('yac_rec','WEAK','YAC only weakly persists (r~0.10-0.19)','off'),
 'contested':('contested_pct','NOISE','contested-catch rate does not persist (r~0.03-0.09)','off'),
 'run_scheme':(None,'NOISE','RB run-scheme (gap/zone) split does not persist (lift -0.18); flavor only','off')}
def dim_pctl(k,dim):
    if dim in ('man','zone','single_high','two_high'): return (cspec.get(k,{}).get('pctls') or {}).get(dim)
    src=DIM[dim][0]; return PCT.get(src,{}).get(k) if src else None
def verdict(p): return 'UNTESTABLE' if p is None else ('STRONGLY SUPPORTED' if p>=75 else ('SUPPORTED' if p>=55 else ('MIXED' if p>=40 else 'NOT SUPPORTED')))
CLAIMS=[('zone',re.compile(r'\b(zone[- ]?beater|vs\.? zone|beats? zone|against zone|zone coverage)\b',re.I)),
 ('man',re.compile(r'\b(man[- ]?beater|vs\.? man|beats? man|against man|press[- ]?man|man coverage|wins vs press)\b',re.I)),
 ('deep',re.compile(r'\b(deep threat|deep ball|vertical|downfield|field stretcher|takes the top|go route|air yards|adot)\b',re.I)),
 ('route',re.compile(r'\b(route runner|route running|crisp routes?|technician|separation|gets open|creates? separation)\b',re.I)),
 ('yac',re.compile(r'\b(yac\b|after the catch|yards after|run after catch|broken tackles?|elusive)\b',re.I)),
 ('contested',re.compile(r'\b(contested|jump ball|50[/-]?50|box out|high[- ]?point)\b',re.I)),
 ('slot',re.compile(r'\bslot\b',re.I)),
 ('single_high',re.compile(r'\b(single[- ]?high|cover[- ]?1\b|cover[- ]?3\b|one[- ]?high)\b',re.I)),
 ('two_high',re.compile(r'\b(two[- ]?high|cover[- ]?2\b|cover[- ]?4\b|cover[- ]?6\b|split safet)\b',re.I)),
 ('volume',re.compile(r'\b(target hog|target share|targets per route|tprr|alpha receiver|workhorse|bell ?cow)\b',re.I)),
 ('run_scheme',re.compile(r'\b(gap scheme|zone (?:block|scheme|concept|run)|man/?gap|inside zone|outside zone|blocking concept|duo scheme|power scheme)\b',re.I))]
MLB=re.compile(r'\b(swinging-strike|k-bb|stuff\+|location\+|siera|xfip|era\b|whiff|fastball|slider|curveball|changeup|sweeper|bullpen|innings|\bip\b|quality start|strikeout|mph\b|dodgers|mariners|orioles|astros|mets|guardians|brewers|reds|cardinals|nationals|royals|phillies)\b',re.I)
JOKE=re.compile(r'(madden|glitch|video ?game|spin move|spinning|backflip|\blol\b|\blmao\b|rofl|won my league|lost my league|my fantasy|my team (?:just )?need|need(?:ed|ing)? \d|started him|benched him|cooked me|ruined my|cost me|championship|in the (?:semis|finals)|🤣|😂)',re.I)
PROMO=re.compile(r'\b(subscribe|sub for more|new episode|full video|full article|link below|link in bio|check out|promo code|use code|giveaway|patreon|substack|sign up|join (?:the|our|my)|stream(?:ing)? (?:now|live)|out now|👇|🔗|🎟)\b',re.I)
LIST_RX=re.compile(r'(?m)(^\s*\d+[\.\)]|\b(rankings?|tiers?|top \d+|highest|most |leaders?|adp|per route run|min\.? \d+|1,?\d{3}\+? )\b)',re.I)
CMP_RX=re.compile(r'\b(over|vs\.?|versus| or )\b',re.I)
CMP2_RX=re.compile(r"[A-Z][A-Za-z.'-]+ (?:over|vs\.?|versus|or) [A-Z][A-Za-z.'-]+")
CMP3_RX=re.compile(r'\b(compared?|comparison|comparing|reminds? (?:me )?of|similar to|to that of|compare)\b',re.I)
def lowval(txt):
    if JOKE.search(txt) or PROMO.search(txt): return True
    if txt.count('@')>=3: return True
    if txt.lstrip().lower().startswith('rt @') and 'http' in txt and '?' in txt and len(txt)<175: return True
    return False
con=sqlite3.connect(DB); con.row_factory=sqlite3.Row
src={r['handle']:dict(r) for r in con.execute("select * from sources")}
hits={k:[] for k in ROST}; team_hits={a:[] for a in NICK}
for t in con.execute("select handle,author_name,text,created_at,url,like_count from tweets"):
    txt=t['text'] or ''
    if MLB.search(txt) or lowval(txt): continue
    ntxt=' '+norm(txt)+' '
    matched=[k for k,pad in NAMES if pad in ntxt]
    nteams={}
    for k in matched: nteams[ROST[k]['team']]=nteams.get(ROST[k]['team'],0)+1
    nick_teams=[NICK2ABBR[w] for w in set(ntxt.split()) if w in NICK2ABBR]
    n=len(matched)
    kind='comp' if (n>=3 or LIST_RX.search(txt) or CMP2_RX.search(txt) or CMP3_RX.search(txt) or (n==2 and CMP_RX.search(txt))) else 'about'
    dims=[d for d,rx in CLAIMS if rx.search(txt)] if kind=='about' else []
    s=src.get((t['handle'] or '').lower(),{})
    rec={'handle':t['handle'],'name':s.get('real_name') or t['author_name'],'text':txt[:600],
         'date':(t['created_at'] or '')[:16],'ep':epoch(t['created_at']),'likes':t['like_count'] or 0,
         'url':t['url'],'tier':s.get('reliability_tier') or 'C','dims':dims,'kind':kind}
    for k in matched: hits[k].append(rec)
    # team-level: explicit nickname OR >=2 same-team players
    tset=set(nick_teams)|{tm for tm,c in nteams.items() if c>=2 and tm}
    for a in tset:
        if a in team_hits: team_hits[a].append(rec)
def dedupe(rows):
    seen=set(); out=[]
    for x in sorted(rows,key=lambda x:-x['ep']):
        ck=re.sub(r'^rt @\w+:','',norm(x['text']))[:120]
        if ck in seen: continue
        seen.add(ck); out.append(x)
    return out
# ---------- per-player ----------
players=[]
for k,p in ROST.items():
    dd=dedupe(hits[k]); about=[]; hc={}
    for x in dd:
        if x['kind']!='about': continue
        hc[x['handle']]=hc.get(x['handle'],0)+1
        if hc[x['handle']]<=3 and len(about)<20: about.append(dict(x))
    comp=[dict(x) for x in dd if x['kind']=='comp'][:25]
    for x in about+comp: x.pop('ep',None)
    up=[]
    for dim,(s_,tier,note,grp) in DIM.items():
        pc=dim_pctl(k,dim)
        if pc is not None and pc>=65: up.append({'dim':dim,'pctl':pc,'group':grp,'stability':tier,'note':note})
    up.sort(key=lambda x:(x['group']!='model',-x['pctl']))
    seen={}
    for x in about:
        for d in x['dims']: seen.setdefault(d,set()).add(x['handle'])
    bt=[]
    for d,hh in seen.items():
        pc=dim_pctl(k,d); _,tier,note,_=DIM[d]; bt.append({'dim':d,'pctl':pc,'verdict':verdict(pc),'stability':tier,'note':note,'by':sorted(hh)[:5]})
    bt.sort(key=lambda x:(x['pctl'] is None,-(x['pctl'] or 0)))
    fp=fus.get(k); bm=boom.get(k)
    reads={'adp':p['adp'],'proj':p['proj'],'consensus':round(cons(fp)) if cons(fp) is not None else None,
      'matchup':round(mv(fp)) if mv(fp) is not None else None,'flags':(fp or {}).get('flags',[])[:4],
      'ceiling_pct':(bm or {}).get('ceiling_pct'),'best_wk':(bm or {}).get('best_wk'),'best_opp':(bm or {}).get('best_opp')}
    cn=coord.get(p['team']); tnote=(cn[0].get('q') if isinstance(cn,list) and cn else (cn if isinstance(cn,str) else ''))
    players.append({'name':p['name'],'team':p['team'],'pos':p['pos'],'reads':reads,'team_note':tnote,
      'upside':up,'backtests':bt,'about':about,'comp':comp,'n_about':len(about),'n_comp':len(comp),'n_insight':sum(1 for x in about if x['dims'])})
players.sort(key=lambda x:(x['reads']['adp'] is None,x['reads']['adp'] or 9999))
# ---------- per-team ----------
def teamstats(a):
    o=FT.get(a,{}); e=tenv.get(a,{}); d=dfn.get(a,{}); pr=dprof.get(a,{})
    cc=cchg.get(a,{}) if isinstance(cchg.get(a),dict) else {}
    return {'offense':{'pass_rate':num(o.get('tm_pass_rate')),'rk_passrate':num(o.get('rk_passrate')),
       'plays':num(o.get('tm_plays')),'pass_att':num(o.get('tm_pass_att')),'total_td':num(o.get('tm_total_td')),
       'rk_td':num(o.get('rk_td')),'pace':e.get('pace_pctl'),'win_total':e.get('win_total'),'env':e.get('env_idx'),'off_q':e.get('off_q')},
     'defense':{'cov':d.get('pass_cov_pctl'),'rush':d.get('pass_rush_pctl'),'run':d.get('run_def_pctl'),
       'cov25':d.get('pass_cov_pctl_2025'),'run25':d.get('run_def_pctl_2025'),'rush25':d.get('pass_rush_pctl_2025'),
       'lean25':pr.get('lean_2025'),'lean26':pr.get('lean_2026'),'funnels':pr.get('funnels',[]),
       'cb1':pr.get('cb1'),'dc_scheme':pr.get('dc'),
       'rookies':[{'pl':r[0],'pos':r[1],'rd':r[3]} for r in {x[0]:x for x in (d.get('rookies_2026') or [])}.values()],
       'moves':[{'pl':m['player'],'u':m['unit'],'fr':m['from'],'to':m['to']} for m in (d.get('moves_2026') or [])][:8]},
     'coord':{'oc':cc.get('oc_new') or cc.get('oc'),'dc':cc.get('dc_new') or cc.get('dc'),'name':cc.get('name')}}
teams=[]
for a in sorted(NICK):
    tw=[dict(x) for x in dedupe(team_hits[a])][:30]
    for x in tw: x.pop('ep',None)
    roster=sorted([pl for pl in players if pl['team']==a], key=lambda x:(x['reads']['adp'] is None,x['reads']['adp'] or 9999))
    keyp=[{'name':r['name'],'pos':r['pos'],'adp':r['reads']['adp'],'consensus':r['reads']['consensus']} for r in roster[:10]]
    cn=coord.get(a); tnote=(cn[0].get('q') if isinstance(cn,list) and cn else '')
    teams.append({'team':a,'stats':teamstats(a),'tweets':tw,'n_tweets':len(tw),'players':keyp,'note':tnote})
teams.sort(key=lambda x:x['team'])
json.dump({'players':players,'teams':teams,'meta':{'n':len(players),'nteams':len(teams),
  'with_about':sum(1 for o in players if o['n_about']),'with_upside':sum(1 for o in players if o['upside'])}},
  open(core.P('intel_data.json'),'w'),ensure_ascii=False,indent=1)
print(f"intel_data.json: {len(players)} players | {len(teams)} teams | {sum(1 for o in players if o['n_about'])} w/about")
g=next(p for p in players if 'Gibbs' in p['name']); print(f"\nGibbs about={g['n_about']} (joke/promo filtered):")
for t in g['about']: print(f"  @{t['handle']} dims={t['dims']}: {t['text'][:80]}")
det=next(t for t in teams if t['team']=='DET'); print(f"\nDET team: {det['n_tweets']} tweets | off pace={det['stats']['offense']['pace']} passrate={det['stats']['offense']['pass_rate']} | def lean26={det['stats']['defense']['lean26']}")
for t in det['tweets'][:3]: print(f"  @{t['handle']}: {t['text'][:80]}")
