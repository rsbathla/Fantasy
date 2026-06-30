#!/usr/bin/env python3
"""Generate a real one-line prose summary for EVERY mentioned player via the Claude API.
Matches full name OR distinctive last name (shared surnames require the full name), gate = >=1 tweet.
One-time: pip install anthropic ; set ANTHROPIC_API_KEY.  Run: python build_qual_summary.py  (--dry previews, no API)."""
import os,re,csv,json,glob,sys,time,collections
HERE=os.path.dirname(os.path.abspath(__file__))
def fn(n):
    n=str(n).strip().lower(); n=re.sub(r'\s+(jr|sr|ii|iii|iv|v)\.?$','',n); n=n.replace('.','').replace("'","").replace('-',' '); return ' '.join(n.split())
STOP=set("brown williams smith jones johnson davis miller wilson moore taylor thomas jackson white harris hill allen young walker wright king scott green adams hall mitchell carter evans watson bell cook gray james reed price love robinson chase hunter likely worthy brooks mason branch flowers rice ward dell lamb tate moss".split())
board=[r['name'] for r in csv.DictReader(open(os.path.join(HERE,'draft_board_signals.csv'),encoding='utf-8')) if r.get('name')]
sur=collections.Counter(fn(n).split()[-1] for n in board if fn(n).split())
def matcher(nm):
    t=[x for x in fn(nm).split() if x not in {'jr','sr','ii','iii','iv','v'}]; L=t[-1]; full={" ".join(t)}
    if len(t)>=2:
        full.add(t[0]+" "+L); ini="".join(x for x in t[:-1] if len(x)==1)
        if len(ini)>=2: full.add(ini+" "+L)
    lastok=(L not in STOP and sur[L]==1 and len(L)>=5)
    return L,full,lastok
PL=[(n,)+matcher(n) for n in board]
tw=sorted(glob.glob(os.path.join(os.path.dirname(HERE),'tweet-bot*','tweets_export.jsonl')))
rows=[json.loads(l) for l in open(tw[-1],encoding='utf-8')] if tw else []
agg={}
for r in rows:
    if r.get('is_retweet'): continue
    raw=re.sub(r'\s+',' ',(r.get('text') or '')).strip(); t=" "+fn(raw)+" "
    for nm,L,full,lastok in PL:
        if (lastok and (" "+L+" ") in t) or any((" "+p+" ") in t for p in full):
            agg.setdefault(nm,{'h':set(),'tw':[]}); agg[nm]['h'].add(r.get('handle')); agg[nm]['tw'].append((r.get('reliability_tier') or 'Z',r.get('handle'),raw[:200]))
gated={nm:a for nm,a in agg.items() if len(a['tw'])>=1}
def prompt_for(nm,a):
    tws=sorted(a['tw'],key=lambda x:(x[0],-len(x[2])))[:10]
    body="\n".join("- @%s: %s"%(h,x) for _,h,x in tws)
    return ("You are a sharp fantasy-football best-ball analyst. In ONE sentence (max 35 words), synthesize the 2026 outlook for %s. "
            "Lead with bullish / bearish / mixed, name the main driver and the key risk. Concrete, no filler. Return only the sentence.\n\nTakes:\n%s"%(nm,body))
print("board players:",len(board),"| players with coachspeak (will summarize):",len(gated),"| no mentions:",len(board)-len(gated))
if '--dry' in sys.argv:
    import random; k=[x for x in ['Jared Goff','Jakobi Meyers','Matthew Golden'] if x in gated][0]
    print("\n--- sample prompt (%s, %d tweets) ---\n%s"%(k,len(gated[k]['tw']),prompt_for(k,gated[k])[:600])); sys.exit(0)
import anthropic
client=anthropic.Anthropic(); MODEL=os.environ.get('QUAL_MODEL','claude-haiku-4-5-20251001'); out=[]
for i,(nm,a) in enumerate(sorted(gated.items())):
    try:
        m=client.messages.create(model=MODEL,max_tokens=90,messages=[{"role":"user","content":prompt_for(nm,a)}]); s=m.content[0].text.strip().replace('\n',' ')
    except Exception as e: s=""; print("  ! %s: %s"%(nm,e))
    q=sorted(a['tw'],key=lambda x:(x[0],-len(x[2])))[0][2] if a['tw'] else ""
    out.append((nm,s,q)); 
    if (i+1)%25==0: print("  %d/%d"%(i+1,len(gated)))
    time.sleep(0.12)
with open(os.path.join(HERE,'qual_summary.csv'),'w',newline='',encoding='utf-8') as f:
    w=csv.writer(f); w.writerow(['name','summary','top_quote']); [w.writerow(r) for r in out]
print("wrote qual_summary.csv with",len(out),"AI syntheses")
