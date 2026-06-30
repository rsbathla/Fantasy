#!/usr/bin/env python3
"""Per-player tweet feed from the auto-ingester DBs (tweet-bot_3 + _2). Matches tweets to every
board player by name (guarding ambiguous surnames), ranks by recency x engagement x source tier,
keeps the top N, writes player_tweets.json keyed by normalized name. Re-run after each daily ingest."""
import sqlite3, json, re, os
from datetime import datetime
HERE=os.path.dirname(os.path.abspath(__file__)); DL=os.path.dirname(HERE)
DBS=[f"{DL}/tweet-bot_3/tweets.db", f"{DL}/tweet-bot_2/tweets.db", f"{DL}/tweet-bot_1/tweets.db"]
TOPN=30
def fn(n):
    n=str(n).strip().lower(); n=re.sub(r'\s+(jr|sr|ii|iii|iv|v)\.?$','',n); return n.replace('.','').replace("'","").replace('-',' ')
def parse_dt(v):
    if not v: return datetime(1970,1,1)
    for f in ("%a %b %d %H:%M:%S %z %Y",):
        try: return datetime.strptime(v,f).replace(tzinfo=None)
        except Exception: pass
    try: return datetime.fromisoformat(str(v).replace("Z","+00:00")).replace(tzinfo=None)
    except Exception: return datetime(1970,1,1)

# ---- board players ----
import csv
board=list(csv.DictReader(open(f"{HERE}/draft_board_signals.csv",encoding='utf-8')))
players=[(r['name'], r.get('pos',''), r.get('team','')) for r in board if r.get('name')]
last2full={}; lastcount={}
for nm,pos,tm in players:
    parts=[p for p in fn(nm).split() if p]; 
    if not parts: continue
    ln=parts[-1]; lastcount[ln]=lastcount.get(ln,0)+1
# common-word / shorthand surnames that are NOT safe to match alone
COMMON={'downs','brown','white','hill','moore','jones','smith','love','james','mason','price','ward','young',
        'rice','allen','watson','wilson','johnson','williams','taylor','adams','robinson','harris','davis',
        'bell','reed','dell','warren','cook','mitchell','golden','st','jr','sr'}
def ambiguous(ln): return (ln in COMMON) or (lastcount.get(ln,0)>1)

# ---- pull tweets (originals; drop pure retweets) ----
rows=[]; seen=set()
for db in DBS:
    if not os.path.exists(db): continue
    con=sqlite3.connect(db)
    has_src = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='sources'").fetchone() is not None
    q=("SELECT t.id,t.handle,t.text,t.created_at,t.url,t.like_count,t.retweet_count,t.is_retweet,"
       +("s.reliability_tier" if has_src else "NULL")+" FROM tweets t"
       +(" LEFT JOIN sources s ON s.handle=t.handle" if has_src else ""))
    for tid,handle,text,ca,url,likes,rts,isrt,tier in con.execute(q):
        if tid in seen: continue
        seen.add(tid)
        if isrt: continue
        if not text or text.strip().startswith("RT @"): continue
        rows.append({'id':tid,'handle':handle,'text':text,'dt':parse_dt(ca),
                     'likes':int(likes or 0),'rts':int(rts or 0),'url':url,'tier':(tier or 'C')})
    con.close()
print(f"  loaded {len(rows)} unique original tweets")

# ---- match tweets to players ----
TIERW={'A':1.0,'B':0.8,'C':0.6}
feed={}
for nm,pos,tm in players:
    k=fn(nm); parts=[p for p in k.split() if p]
    if not parts: continue
    ln=parts[-1]; fnm=parts[0]
    hits=[]
    full=" ".join(parts)
    for tw in rows:
        tl=" "+re.sub(r'[^a-z0-9 ]',' ',tw['text'].lower())+" "
        if full and (" "+full+" ") in tl:           # full name = always safe
            hits.append(tw); continue
        if len(ln)>2 and (" "+ln+" ") in tl:          # last-name hit
            if ambiguous(ln):                          # ambiguous -> require first name/initial too
                if (" "+fnm+" ") in tl or (" "+fnm[0]+" ") in tl or (tm and (" "+tm.lower()+" ") in tl):
                    hits.append(tw)
            else:
                hits.append(tw)
    if not hits: continue
    # rank: recency(days) blended with engagement + tier; newest & most-liked first
    now=datetime.utcnow()
    def score(tw):
        age=max(0,(now-tw['dt']).days); rec=1.0/(1+age/14.0)
        eng=(tw['likes']+2*tw['rts'])**0.5
        return rec*2.0 + eng*0.02 + TIERW.get(tw['tier'],0.6)
    hits.sort(key=score,reverse=True)
    out=[]
    for tw in hits[:TOPN]:
        out.append({'date':tw['dt'].strftime('%b %d'),'handle':tw['handle'],'tier':tw['tier'],
                    'likes':tw['likes'],'text':tw['text'],'url':tw['url']})
    feed[k]={'n':len(hits),'tweets':out}
json.dump(feed,open(f"{HERE}/player_tweets.json",'w',encoding='utf-8'),ensure_ascii=False)
print(f"  wrote player_tweets.json: {len(feed)} players with >=1 tweet")
# validation
for nm in ["Josh Downs","Brandon Aiyuk","D'Andre Swift","Puka Nacua"]:
    f=feed.get(fn(nm))
    if f:
        print(f"\n  {nm}: {f['n']} tweets matched, showing top {len(f['tweets'])}:")
        for t in f['tweets'][:3]: print(f"     [{t['date']} @{t['handle']} {t['likes']}♥] {t['text'][:90]}")
    else: print(f"\n  {nm}: (no tweets)")
