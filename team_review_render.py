#!/usr/bin/env python3
"""Turn grounded per-team numbers into a per-LAYER analytical review -> team_review_rendered.json"""
import json,os,re
HERE=os.path.dirname(os.path.abspath(__file__))
D=json.load(open(os.path.join(HERE,'team_review_data.json'),encoding='utf-8'))
LG=D.pop('_league')
import os as _os
COORD=json.load(open(_os.path.join(HERE,'coordinator_notes.json'),encoding='utf-8')) if _os.path.exists(_os.path.join(HERE,'coordinator_notes.json')) else {}
def ordn(n):
    if n is None: return '?'
    n=int(n); 
    if 10<=n%100<=20: s='th'
    else: s={1:'st',2:'nd',3:'rd'}.get(n%10,'th')
    return f"{n}{s}"
def J(P):
    return '. '.join((x[:1].upper()+x[1:]) for x in P if x)+'.'
def hi(r,a=8,b=24): return 'high' if r and r<=a else ('low' if r and r>=b else 'mid')
def clean(q):
    if not q: return ''
    q=re.sub(r'https?://\S+','',q); q=re.sub(r'[^\x00-\x7F]+',' ',q)
    q=re.sub(r'\s+',' ',q).strip().strip('"').strip(); return q
def best_quote(raw):
    '''first clean, full-sentence segment + @handle attribution; skip list/spam.'''
    if not raw: return None
    for seg in raw.split(' | '):
        m=re.search(r'\(@([\w]+)\)\s*$',seg); h=m.group(1) if m else None
        q=clean(seg[:m.start()] if m else seg)
        if len(q)<40 or len(q)>210: continue
        if any(x in q for x in ('Sub for more','Picks List','targets in drafts','RT @','Starting in Rd')): continue
        if q.count(' - ')>=3 or len(re.findall(r'ADP\)',q))>=2: continue
        if q[-1] not in '.!?': continue
        return (q.rstrip('.'),h)
    return None
def wr_te(pls): return [p for p in pls if p['pos'] in ('WR','TE')]
def alpha(pls): return [p for p in pls if p['p95'] and p['p95']>=33]

def verdict(t):
    s=t['script']; a=alpha(t['players']); top=t['players'][0] if t['players'] else None
    if not s:  # FA
        return f"{t['name']} are an unsigned-player bucket in this snapshot — landing spot drives everything, so treat the ceiling numbers below as talent, not opportunity."
    env=[]
    env.append('pass-first' if s['rk_passrate']<=10 else ('run-leaning' if s['rk_passrate']>=24 else 'balanced'))
    env.append('high-volume' if s['rk_plays']<=10 else ('low-snap' if s['rk_plays']>=24 else 'average-pace'))
    score='a top scoring offense' if s['rk_td']<=8 else ('a muted scoring offense' if s['rk_td']>=24 else 'a middle scoring offense')
    return (f"A {', '.join(env)} attack and {score} ({s['total_td']} implied TD/g, {ordn(s['rk_td'])}). "
            f"{len(a)} alpha-ceiling player{'s' if len(a)!=1 else ''} (p95≥33); best board asset is {top['name']} at #{top['rk']}.")

def L_script(t):
    s=t['script']
    if not s: return None
    stat=(f"{s['plays_pg']} plays/g ({ordn(s['rk_plays'])}) · {s['pass_att_pg']} pass att ({ordn(s['rk_passvol'])}) · "
          f"{s['pass_rate']}% pass rate ({ordn(s['rk_passrate'])}) · {s['pass_yds_pg']} pass yds ({ordn(s['rk_passyds'])}) · "
          f"{s['carries_pg']} carries ({ordn(s['rk_carries'])}) · {s['rush_yds_pg']} rush yds ({ordn(s['rk_rushyds'])}) · {s['total_td']} TD/g ({ordn(s['rk_td'])})")
    pr=s['pass_rate']; parts=[]
    if s['rk_passrate']<=8: parts.append(f"This is a genuinely pass-first script — {pr}% pass rate against a {LG['passrate']:.0f}% league mean — so the receiving corps, not the backfield, is where the fantasy points concentrate")
    elif s['rk_passrate']>=24: parts.append(f"A run-leaning script ({pr}% pass vs {LG['passrate']:.0f}% league) tilts value toward the backfield and compresses the passing pie")
    else: parts.append(f"A balanced script ({pr}% pass) spreads opportunity without a strong structural lean either way")
    if s['rk_plays']<=10: parts.append(f"and the pace is real — {s['plays_pg']} snaps/g ({ordn(s['rk_plays'])}) manufactures extra possessions for everyone")
    elif s['rk_plays']>=24: parts.append(f"but the deliberate pace ({s['plays_pg']} snaps/g, {ordn(s['rk_plays'])}) caps the raw opportunity to go around")
    lead=parts[0]+(", "+parts[1] if len(parts)>1 and parts[1][:1].islower() else "")
    if s['rk_td']<=8: score=f"Most important for best ball: {s['total_td']} implied TD/g ({ordn(s['rk_td'])}) is a top-tier scoring environment that raises every weekly ceiling"
    elif s['rk_td']>=24: score=f"The {ordn(s['rk_td'])}-ranked scoring rate ({s['total_td']} TD/g) is the cap here — touchdown-dependent ceilings get harder to hit"
    else: score=f"Scoring sits mid-pack ({s['total_td']} TD/g, {ordn(s['rk_td'])})"
    return ('Volume & script', stat, lead[:1].upper()+lead[1:]+'. '+score+'.')

def L_usage(t):
    pls=t['players']; used=[p for p in pls if p.get('u_g')]
    if not used: return ('Usage & opportunity (2025 PBP)', None, "No meaningful 2025 NFL snaps among the draftable group — this room is rookies and projection, so opportunity is a bet, not a measurement.")
    wt=[p for p in used if p['pos'] in ('WR','TE') and p.get('tgtshare')]
    rbs=[p for p in used if p['pos']=='RB']
    parts=[]; stat=[]
    if wt:
        lead=max(wt,key=lambda x:x['tgtshare'])
        stab='rock-steady' if (lead.get('tgtshare_cv') or 1)<=0.33 else ('volatile' if (lead.get('tgtshare_cv') or 1)>=0.5 else 'fairly stable')
        depth='downfield' if (lead.get('u_adot') or 0)>=12 else ('short-area' if (lead.get('u_adot') or 99)<=8 else 'all-levels')
        parts.append(f"{lead['name']}{mv(lead)} is the focal point — a {lead['tgtshare']}% target share in 2025 ({stab}, cv {lead.get('tgtshare_cv')}), at a {lead.get('u_adot')}-yard aDOT ({depth} routes), peaking at {lead.get('u_dkmax')} DK in his best week")
        others=[p for p in wt if p is not lead and p['tgtshare']>=15]
        if others: parts.append("secondary volume goes to "+", ".join(f"{p['name']} ({p['tgtshare']}%)" for p in sorted(others,key=lambda x:-x['tgtshare'])[:2]))
        for p in sorted(wt,key=lambda x:-x['tgtshare'])[:3]: stat.append(f"{p['name']} {p['tgtshare']}% tgt / aDOT {p.get('u_adot')} / max {p.get('u_dkmax')}")
    if rbs:
        wrk=max(rbs,key=lambda x:x.get('u_carpg') or 0)
        if wrk.get('u_carpg'):
            role='a true workhorse' if wrk['u_carpg']>=15 else ('a committee back' if wrk['u_carpg']<11 else 'the lead of a rotation')
            pass_d=f", and he caught {wrk.get('u_recpg')} balls/g" if (wrk.get('u_recpg') or 0)>=3 else ", with a thin receiving role"
            parts.append(f"In the backfield {wrk['name']}{mv(wrk)} profiled as {role} ({wrk['u_carpg']} carries/g{pass_d}); ceiling week {wrk.get('u_dkmax')} DK")
            stat.append(f"{wrk['name']} {wrk['u_carpg']} car/g, {wrk.get('u_recpg')} rec/g, max {wrk.get('u_dkmax')}")
    inj=[p for p in used if (p.get('u_g') or 17)<=9 and p['pos']!='RB']
    if inj: parts.append("small-sample caveat: "+", ".join(f"{p['name']} ({p['u_g']}g)" for p in inj[:2])+" missed time, so the rates ride a partial season")
    return ('Usage & opportunity (2025 PBP)', ' · '.join(stat) if stat else None, J(parts))

def L_ceiling(t):
    a=sorted(alpha(t['players']),key=lambda x:-x['p95'])
    if not a:
        best=max(t['players'],key=lambda x:x['p95'] or 0) if t['players'] else None
        return ('Ceiling & upside', None, f"No alpha-ceiling (p95≥33) bats here — the top spike is {best['name']} at p95 {best['p95']} ({best.get('spike')}% spike weeks). In a top-2-advance pod this is a ceiling-light room you lean on for value, not for the league-winning week." if best else "Thin.")
    stat=' · '.join(f"{p['name']} p95 {p['p95']} ({p.get('spike')}% spike)" for p in a[:5])
    lead=a[0]
    txt=(f"{len(a)} players clear the alpha-ceiling bar, led by {lead['name']} (p95 {lead['p95']}, hits a spike week {lead.get('spike')}% of the time). "
         f"This is the currency that wins best ball — these are the weekly outcomes that drag a lineup into the 90th percentile. ")
    boom=[p for p in a if (p.get('cv') or 0)>=1.0]
    if boom: txt+="Highest-variance (boom/bust) of the group: "+", ".join(p['name'] for p in boom[:3])+" — exactly the volatility you want on a bench that only counts its best weeks."
    return ('Ceiling & upside', stat, txt)

def L_adv(t):
    pls=[p for p in t['players'] if p.get('adv') is not None]
    if not pls: return None
    hi_adv=sorted(pls,key=lambda x:-x['adv'])[:3]
    spikey=[p for p in pls if (p.get('spike') or 0)>=18 and (p.get('adv') or 100)<=80]
    txt=(f"Advancement is the binding gate in a 12-team/top-2 pod — the players who actually bank points week to week. "
         f"Best regular-season equity: "+", ".join(f"{p['name']} ({p['adv']}%)" for p in hi_adv)+". ")
    if spikey: txt+="Pure spike profiles (big ceiling, thinner advancement floor): "+", ".join(p['name'] for p in spikey[:3])+" — useful as upside dart-throws, not as the backbone of the grind."
    return ('Regular-season value (advancement)', None, txt)

def L_stack(t):
    if t['team']=='FA': return None
    pls=t['players']; qb=next((p for p in pls if p['pos']=='QB'),None)
    wrs=[p for p in wr_te(pls) if p['p95']]; wrs.sort(key=lambda x:-(x['p95'] or 0))
    w17=t.get('w17') or ''; tl=t.get('tl')
    opp=None
    m=re.match(r'([A-Z]{2,3})@([A-Z]{2,3})',w17 or '')
    if m: opp=m.group(2) if m.group(1)==t['team'] else m.group(1)
    parts=[]
    if qb and wrs:
        parts.append(f"The stack spine is {qb['name']} + {wrs[0]['name']}" + (f" / {wrs[1]['name']}" if len(wrs)>1 else "") +
                     f" — QB-WR1 correlation runs r≈0.35 league-wide, so pairing them converts one good game script into two scoring lineups")
    elif wrs:
        parts.append(f"No draftable QB in range, so this is a bring-back/catcher source rather than a primary stack origin; {wrs[0]['name']} is the piece")
    if w17:
        tail = 'a top-tier blow-up game' if (tl or 99)<=6 else ('a mid-tier finals game' if (tl or 99)<=12 else 'a lower-variance finals game')
        parts.append(f"The Week 17 finals slot is {w17} — {tail} (tail rank #{tl}); "+(f"the natural bring-back is a {opp} pass-catcher to play both sides of that game" if opp else "build it two-sided"))
    parts.append(f"byes fall in Week {t.get('bye')}, and the playoff run is W15 vs {t.get('w15')}, W16 vs {t.get('w16')}")
    return ('Stacking & the Week 17 finals', None, J(parts))

def L_coach(t):
    bits=[]
    if t['note']:
        tn=clean(t['note'].split(' | ')[0])
        cut=max(tn.rfind('.'),tn.rfind('!'),tn.rfind('?'))
        if cut>60: tn=tn[:cut]
        if len(tn)>30: bits.append(('the team',tn[:300].rstrip('.'),None))
    for p in t['players']:
        if len(bits)>=4: break
        bq=best_quote(p.get('bb')) or best_quote(p.get('vid'))
        if bq: bits.append((p['name'],bq[0],bq[1]))
    if not bits: return ('Coachspeak & film', None, "No clean beat-writer or film notes survived the per-player filter for this room — lean on the quantitative layers above.")
    txt=' '.join((f"On {who}: \u201c{q}\u201d" + (f" (@{h})." if h else ".")) for who,q,h in bits)
    return ('Coachspeak & film', None, txt)

def L_plan(t):
    pls=t['players']; 
    if not pls: return None
    vals=[p for p in pls if p['rk'] and p['adp'] and p['rk']<=p['adp']-8]
    reaches=[p for p in pls if p['rk'] and p['adp'] and p['rk']>=p['adp']+10]
    a=sorted(alpha(pls),key=lambda x:x['rk'] or 999)
    anchor=a[0] if a else pls[0]
    parts=[f"Anchor the team around {anchor['name']} (board #{anchor['rk']}, ADP {anchor['adp']})"]
    if len(a)>1: parts.append("with "+", ".join(p['name'] for p in a[1:3])+" as the correlated ceiling pieces")
    if vals: parts.append("board-vs-market values to exploit: "+", ".join(f"{p['name']} (#{p['rk']} vs ADP {p['adp']})" for p in sorted(vals,key=lambda x:x['rk'])[:3]))
    if reaches: parts.append("let the market overpay for "+", ".join(p['name'] for p in reaches[:2]))
    if len(parts)>1 and parts[1].startswith('with'): parts=[parts[0]+', '+parts[1]]+parts[2:]
    return ('Best-ball plan', None, J(parts))

def L_risk(t):
    flags=[]
    for p in t['players']:
        for o in p.get('ov',[]): flags.append(f"{p['name']} — {clean(o)}")
    s=t['script']
    if s and s['rk_carries']>=24 and s['rk_passrate']<=10:
        flags.append("structural: a pass-first, low-carry script makes the backfield a committee/touchdown-variance bet")
    if not flags: return ('Risks & flags', None, "No specific risk overlays on this group; the main risk is generic (price vs the field).")
    return ('Risks & flags', None, ' • '.join(flags[:6]))

def player_table(t):
    rows=[]
    for p in t['players'][:9]:
        u = (f"{p['tgtshare']}% tgt" if p.get('tgtshare') else (f"{p['u_carpg']} car/g" if p.get('u_carpg') else ('rookie/NA')))
        rows.append([str(p['rk'] or ''),p['name'],p['pos'],str(p['adp'] or ''),str(p['p95'] or ''),
                     (str(p['spike'])+'%' if p['spike'] is not None else ''),(str(p['adv'])+'%' if p['adv'] is not None else ''),u])
    return {'headers':['Brd','Player','Pos','ADP','Ceil','Spike','Adv','2025 use'],'rows':rows}

NRM={'LA':'LAR','JAC':'JAX','WSH':'WAS'}
def na(x): return NRM.get(x,x) if x else x
def mv(p): return f" (2025 with {na(p['u_team25'])})" if p.get('mover') else ""
def L_outlook(t):
    d=t.get('delta')
    if not d: return None
    parts=[]
    cn=COORD.get(t['team'])
    if cn:
        q=cn[0]['q'].strip().rstrip('.'); h=cn[0]['h']
        parts.append(f"Scheme watch \u2014 \u201c{q}\u201d (@{h})")
    if d.get('d_pa') is not None:
        dpa=d['d_pa']; lean=("leaning more pass-heavy than 2025" if dpa>=1.5 else ("projected for lower pass volume / more run than 2025" if dpa<=-1.5 else "holding steady on pass volume"))
        parts.append(f"Volume shift: Clay projects {t['script']['pass_att_pg']} pass att/g in 2026 vs {d['act_pa']} actual in 2025 ({'+' if dpa>=0 else ''}{dpa}) \u2014 {lean}")
    if d.get('vac_tgt') is not None and d.get('departures'):
        vt=d['vac_tgt']; mag=("major turnover" if vt>=35 else ("meaningful turnover" if vt>=20 else "a largely intact target tree"))
        deps=", ".join(f"{nm} ({sh}%, {('to '+na(dst)) if dst not in ('gone',) else 'gone'})" for nm,sh,dst in d['departures'][:4])
        parts.append(f"Vacated opportunity: ~{vt}% of the 2025 target volume turned over ({mag}) \u2014 out: {deps}")
    arr=[f"{nm} (from {na(ot)})" for nm,ot in d.get('arrivals',[]) if ot]; rk=d.get('rookies',[])
    if arr or rk:
        seg="In: "+("; ".join(arr) if arr else "no veteran additions of note")
        if rk: seg+="  ·  rookies: "+", ".join(rk[:4])
        parts.append(seg)
    dl=[p for p in t['players'] if p.get('d_pg') is not None][:4]
    if dl:
        ds=[]
        for p in dl:
            dpg=p['d_pg']; dr=("trending up" if dpg>=2 else ("projected to regress" if dpg<=-2 else "roughly steady")); mvr=(f", joins from {na(p['u_team25'])}" if p.get('mover') else "")
            ds.append(f"{p['name']} {p['proj']}/g proj vs {p['u_dkmean']}/g in 2025 ({'+' if dpg>=0 else ''}{dpg}, {dr}{mvr})")
        parts.append("Player deltas (2025 actual \u2192 2026 projection): "+"; ".join(ds))
    return ('2026 outlook: what changes', None, J(parts)) if parts else None
order=sorted([t for k,t in D.items()],key=lambda t:(10**9 if t['team']=='FA' else min([p['rk'] or 9999 for p in t['players']] or [9999])))
rendered=[]
for t in order:
    layers=[L_script(t),L_usage(t),L_outlook(t),L_ceiling(t),L_adv(t),L_stack(t),L_coach(t),L_plan(t),L_risk(t)]
    layers=[l for l in layers if l]
    rendered.append({'team':t['team'],'name':t['name'],'verdict':verdict(t),'table':player_table(t),
                     'layers':[{'label':l[0],'stat':l[1],'read':l[2]} for l in layers]})
json.dump({'teams':rendered,'league':LG},open(os.path.join(HERE,'team_review_rendered.json'),'w',encoding='utf-8'),ensure_ascii=False,indent=0)
print("rendered teams:",len(rendered))
# sample one team's prose to eyeball quality
import textwrap
t=rendered[0]
print("\n########",t['name'],"########\nVERDICT:",t['verdict'])
for l in t['layers']:
    print("\n--",l['label'],"--")
    if l['stat']: print("  [stat]",l['stat'][:160])
    print(textwrap.fill(l['read'],150))
