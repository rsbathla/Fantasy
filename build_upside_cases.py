#!/usr/bin/env python3
"""build_upside_cases.py — a STANDALONE per-player UPSIDE CASE (outside best-ball): for every
player, the situations that unlock a ceiling game, grounded in BOTH the flag model (ceiling
skills + amplifying matchup/coverage/environment conditions + ceiling killers) AND his actual
2025 boom games broken down by the conditions that were present.

Inputs: boom/flags_<POS>.json (recipe), boom/gamelog.json (2025 evidence), boom/cover_spec.json,
boom/boom_marks.json. Output: upside_cases.html (self-contained, searchable).
"""
import json, os, re
from collections import defaultdict
B = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'boom')

GL = json.load(open(f"{B}/gamelog.json"))
CS = json.load(open(f"{B}/cover_spec.json")) if os.path.exists(f"{B}/cover_spec.json") else {}
SPECIAL = {'Coverage specialist', 'Premium QB stack partner'}

def atomize(amp):
    """Split an amp field on TOP-LEVEL '/' or ';' only (never inside parentheses, so
    '(manp>=68, 78% boundary / single coverage)' stays one atom)."""
    out, depth, cur = [], 0, ''
    for ch in (amp or ''):
        if ch == '(':
            depth += 1; cur += ch
        elif ch == ')':
            depth = max(0, depth - 1); cur += ch
        elif ch in '/;' and depth == 0:
            if cur.strip(): out.append(cur.strip())
            cur = ''
        else:
            cur += ch
    if cur.strip(): out.append(cur.strip())
    return [a for a in out if len(a) > 2]

def stem(fl):
    s = re.sub(r'\([^)]*\)', '', fl)                 # drop parentheticals (numbers live here)
    s = re.sub(r'\b\d+(st|nd|rd|th)?\b', '', s)
    return re.sub(r'\s+', ' ', s).strip(' +-—')

def softness(pctl):  # opponent defense pctl: higher = tougher
    if pctl is None: return None
    return 'soft' if pctl <= 33 else ('tough' if pctl >= 67 else 'avg')

def split(games, label, cond):
    sub = [g for g in games if cond(g)]
    if not sub: return None
    b = sum(g['boom'] for g in sub)
    return {'label': label, 'booms': b, 'games': len(sub), 'rate': round(100 * b / len(sub))}

cases = {}
for pos in ('QB', 'RB', 'WR', 'TE', 'DST'):
    d = json.load(open(f"{B}/flags_{pos}.json"))
    for k, v in d.items():
        base = v.get('base') or 0
        sfs = v.get('skill_flags', [])
        # --- recipe: ceiling skills + amplifiers + killers ---
        skills = [{'f': f['f'], 'd': f.get('d', '')} for f in sfs if f['f'] not in SPECIAL]
        amps, seen = [], set()
        for f in sfs:
            if f['f'] in SPECIAL: continue
            for a in atomize(f.get('amp', '')):
                key = re.sub(r'\([^)]*\)', '', a).lower().strip()
                if key and key not in seen:
                    seen.add(key); amps.append(a)
        cspec = next((f for f in sfs if f['f'] == 'Coverage specialist'), None)
        stack = next((f for f in sfs if f['f'] == 'Premium QB stack partner'), None)
        # data-driven killers: week-flags whose mean week-p sits well below his base
        fp = defaultdict(list)
        for w in v['weeks']:
            if w.get('p') is None: continue
            for fl in w.get('flags', []):
                fp[fl].append(w['p'])
        pvals = sorted(w['p'] for w in v['weeks'] if w.get('p') is not None)
        med = pvals[len(pvals) // 2] if pvals else 0
        # killers = GENUINE suppressor conditions only (the model's negative-multiplier flags).
        # A positive activator (e.g. "man-heavy + separation edge", "clean pocket activates...")
        # can appear in a low-scoring week when OTHER suppressors are present; it must NOT be
        # called a killer. Gate on suppressor patterns AND confirm it sat below his median week.
        SUPP = ('tough ', 'heavy rush', 'tight man', 'shadow', 'slow game', 'big favorite',
                'bracket', 'limits', 'run-stuff', 'stout run')
        POS = ('+', 'activates', 'his best scheme', 'softens', 'wins', 'big play', 'one-on-one')
        kill, kseen = [], set()
        for fl, ps in sorted(fp.items(), key=lambda x: sum(x[1]) / len(x[1])):
            mp = sum(ps) / len(ps); low = fl.lower()
            is_supp = any(sp in low for sp in SUPP) and not any(pp in low for pp in POS)
            if len(ps) >= 1 and is_supp and mp < med:
                st = stem(fl)
                if st and st.lower() not in kseen and len(st) > 3:
                    kseen.add(st.lower()); kill.append(st)
        # --- 2025 evidence ---
        games = [g for g in GL.get(k, []) if 'boom' in g]
        ev = None
        if games:
            n = len(games); booms = sum(g['boom'] for g in games)
            sp = []
            sp.append(split(games, 'Home', lambda g: g.get('home') is True))
            sp.append(split(games, 'Away', lambda g: g.get('home') is False))
            sp.append(split(games, 'Dome', lambda g: g.get('dome') is True))
            sp.append(split(games, 'Outdoor', lambda g: g.get('dome') is False))
            if pos == 'DST':
                sp.append(split(games, 'vs weak offense', lambda g: (g.get('opp_off_q') or 50) <= 33))
                sp.append(split(games, 'vs strong offense', lambda g: (g.get('opp_off_q') or 50) >= 67))
            else:
                sp.append(split(games, 'vs soft pass-D', lambda g: softness(g.get('opp_passp')) == 'soft'))
                sp.append(split(games, 'vs tough pass-D', lambda g: softness(g.get('opp_passp')) == 'tough'))
                if pos == 'RB':
                    sp.append(split(games, 'vs soft run-D', lambda g: softness(g.get('opp_runp')) == 'soft'))
                    sp.append(split(games, 'vs tough run-D', lambda g: softness(g.get('opp_runp')) == 'tough'))
            sp = [s for s in sp if s and s['games'] >= 2]
            # insight: best split (>=2 games) with rate above overall, biggest sample tiebreak
            base_rate = 100 * booms / n
            cand = [s for s in sp if s['rate'] > base_rate]
            cand.sort(key=lambda s: (-s['rate'], -s['games']))
            insight = ''
            if cand:
                c = cand[0]
                insight = f"his ceiling games skewed {c['label'].lower()} ({c['booms']}/{c['games']})"
            boomg = [{'wk': g['wk'], 'opp': g['opp'], 'act': g['act'],
                      'home': g.get('home'), 'dome': g.get('dome'),
                      'd': (('vs ' + (softness(g.get('opp_passp')) or '?') + ' pass-D') if pos != 'DST'
                            else ('vs ' + (softness(g.get('opp_off_q')) or '?') + ' offense'))}
                     for g in sorted(games, key=lambda x: -x['act']) if g['boom']]
            ev = {'n': n, 'booms': booms, 'rate': round(base_rate), 'splits': sp,
                  'boom_games': boomg, 'insight': insight}
        # --- narrative ---
        nm = v.get('name'); team = v.get('team')
        top_sk = ', '.join(s['f'].lower() for s in skills[:2]) or 'his role'
        top_amp = '; '.join(amps[:3]) if amps else 'favorable matchups'
        nar = f"{nm} ({pos}, {team}) reaches a ceiling game about {base}% of weeks. The upside is built on {top_sk}. It comes alive on: {top_amp}."
        if cspec: nar += f" He {cspec['d'][:80]}."
        if ev: nar += f" In 2025 he boomed {ev['booms']}/{ev['n']} ({ev['rate']}%)" + (f" — {ev['insight']}." if ev['insight'] else ".")
        if kill: nar += f" Ceiling fades against: {kill[0]}."
        if v.get('team') == 'FA':
            nar = f"{nm} ({pos}) is an UNSIGNED free agent — the prior-role upside case below applies once he lands a 2026 team. " + nar.split('. ', 1)[-1]
        # de-templated, PLAYER-SPECIFIC "Booms when": lead with HIS proven 2025 conditions +
        # his specific coverage scheme + stack, then the model amplifiers (so no two players read alike)
        booms_when = []
        if ev:
            for sp_ in ev['splits']:
                if sp_['rate'] > ev['rate'] and sp_['games'] >= 2 and sp_['booms'] >= 2:
                    booms_when.append(f"{sp_['label']} \u2014 boomed {sp_['booms']}/{sp_['games']} in 2025")
        if cspec:
            _sch = (CS.get(k) or {}).get('best') or ''
            _pc = (CS.get(k) or {}).get('pctl')
            if _sch:
                booms_when.append(f"vs {_sch} defenses" + (f" ({_pc}th pctl)" if _pc else ""))
        if stack:
            _qb = re.search(r'tied to (.+?) \(QB base', stack['d'])
            if _qb:
                booms_when.append(f"when {_qb.group(1)} is also in a plus spot")
        for a in amps:
            if len(booms_when) >= 12:
                break
            booms_when.append(a)
        cases[k] = {'name': nm, 'pos': pos, 'team': team, 'ceiling': base,
                    'tier': ('ELITE' if base >= 35 else 'HIGH' if base >= 22 else 'MID' if base >= 12 else 'LOW'),
                    'fa': v.get('team') == 'FA',
                    'skills': skills, 'amps': booms_when, 'killers': kill,
                    'cspec': ({'scheme': (CS.get(k) or {}).get('best'), 'ratio': (CS.get(k) or {}).get('ratio'),
                               'd': cspec['d']} if cspec else None),
                    'stack_qb': (re.search(r'tied to (.+?) \(QB base', stack['d']).group(1) if stack and re.search(r'tied to (.+?) \(QB base', stack['d']) else None),
                    'ev': ev, 'narrative': nar}

json.dump(cases, open(f"{B}/upside_cases.json", 'w'), ensure_ascii=False, indent=0)
withev = sum(1 for c in cases.values() if c['ev'])
print(f"upside_cases.json: {len(cases)} players, {withev} with 2025 evidence")
for nm in ('jamarr chase', 'puka nacua', 'bijan robinson'):
    c = cases.get(nm)
    if c: print(f"  {c['name']}: ceil {c['ceiling']}% | {len(c['amps'])} amps, {len(c['killers'])} killers | ev {c['ev']['booms']}/{c['ev']['n'] if c['ev'] else '-'}")

# ============================== RENDER STANDALONE HTML ==============================
HTML = r'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Upside Cases — what unlocks each player's ceiling</title>
<style>
:root{--bg:#0e1116;--bg2:#141923;--panel:#171d28;--panel2:#1e2533;--line:#283042;--ink:#e8edf5;--ink2:#aeb9cc;--ink3:#7d8aa0;--acc:#5fd08a;--blue:#7fb2ff;--amber:#e6b36a;--mono:ui-monospace,SFMono-Regular,Menlo,monospace}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}
header{padding:14px 20px;border-bottom:1px solid var(--line);background:linear-gradient(180deg,var(--bg2),var(--bg));position:sticky;top:0;z-index:5}
h1{margin:0;font-size:18px}.sub{color:var(--ink3);font-size:12px;margin-top:2px}
.controls{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap;align-items:center}
#q{flex:1;min-width:200px;background:var(--panel);border:1px solid var(--line);color:var(--ink);border-radius:8px;padding:8px 12px;font-size:14px}
.chip{cursor:pointer;border:1px solid var(--line);background:var(--panel);color:var(--ink2);padding:5px 11px;border-radius:20px;font-size:12px;font-weight:600}
.chip.on{background:var(--acc);color:#06210f;border-color:var(--acc)}
.wrap{display:grid;grid-template-columns:300px 1fr;gap:0;height:calc(100vh - 96px)}
.list{overflow-y:auto;border-right:1px solid var(--line);background:var(--bg2)}
.prow{display:flex;align-items:center;gap:8px;padding:8px 14px;cursor:pointer;border-bottom:1px solid rgba(40,48,66,.5)}
.prow:hover{background:var(--panel)}.prow.sel{background:var(--panel2);box-shadow:inset 3px 0 0 var(--acc)}
.prow .nm{flex:1;font-weight:600;font-size:13px}.prow .pos{font-family:var(--mono);font-size:10px;color:var(--ink3)}
.cbar{width:46px;height:6px;border-radius:3px;background:var(--line);overflow:hidden}.cbar i{display:block;height:100%;background:var(--acc)}
.cval{font-family:var(--mono);font-size:11px;width:30px;text-align:right;color:var(--ink2)}
.detail{overflow-y:auto;padding:22px 28px}
.dh{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}.dh .nm{font-size:26px;font-weight:800}
.dh .meta{font-family:var(--mono);color:var(--ink3);font-size:13px}
.big{margin-left:auto;text-align:right}.big .v{font-size:34px;font-weight:800;font-family:var(--mono)}.big .l{font-size:11px;color:var(--ink3);text-transform:uppercase;letter-spacing:.05em}
.tier{display:inline-block;font-size:10px;font-weight:700;padding:2px 8px;border-radius:5px;font-family:var(--mono)}
.tier.ELITE{background:rgba(46,160,90,.18);color:var(--acc)}.tier.HIGH{background:rgba(70,130,220,.2);color:var(--blue)}.tier.MID{background:rgba(180,180,60,.15);color:#d6d67a}.tier.LOW{background:var(--panel2);color:var(--ink3)}.tier.FA{background:rgba(200,140,40,.18);color:var(--amber)}
.nar{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--acc);border-radius:8px;padding:14px 16px;margin:16px 0;font-size:15px;line-height:1.6}
.sec{margin:18px 0}.sec h3{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--ink3);margin:0 0 8px}
.chips{display:flex;flex-wrap:wrap;gap:6px}.tag{background:var(--panel2);border:1px solid var(--line);border-radius:6px;padding:4px 9px;font-size:12px;color:var(--ink2)}
.tag.amp{border-color:rgba(46,160,90,.35);color:#bfe9cf;background:rgba(46,160,90,.08)}
.tag.kill{border-color:rgba(220,90,90,.35);color:#f0b9b9;background:rgba(220,90,90,.08)}
.skill{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px 12px;margin-bottom:6px}
.skill .f{font-weight:700;font-size:13px}.skill .d{color:var(--ink3);font-size:12px;font-family:var(--mono);margin-top:2px}
.callout{background:rgba(46,160,90,.1);border:1px solid rgba(46,160,90,.3);border-radius:8px;padding:10px 12px;margin-bottom:8px;font-size:13px}
.callout.blue{background:rgba(70,130,220,.1);border-color:rgba(70,130,220,.3)}
.splits{display:flex;flex-direction:column;gap:5px;max-width:520px}
.sp{display:grid;grid-template-columns:130px 1fr 64px;align-items:center;gap:10px;font-size:12px}
.sp .lab{color:var(--ink2)}.sp .bar{height:14px;background:var(--line);border-radius:3px;overflow:hidden}.sp .bar i{display:block;height:100%;background:var(--blue)}
.sp .bar i.hot{background:var(--acc)}.sp .n{font-family:var(--mono);color:var(--ink3);text-align:right}
.games{display:flex;flex-direction:column;gap:4px;margin-top:8px}
.g{display:grid;grid-template-columns:54px 60px 1fr;gap:10px;font-size:12px;font-family:var(--mono);padding:4px 0;border-bottom:1px solid rgba(40,48,66,.5)}
.g .pts{color:var(--acc);font-weight:700}.g .ctx{color:var(--ink3)}
.muted{color:var(--ink3);font-style:italic;font-size:13px}
</style></head><body>
<header><h1>Upside Cases <span style="color:var(--ink3);font-weight:400">— what unlocks each player's ceiling game</span></h1>
<div class="sub" id="sub"></div>
<div class="controls"><input id="q" placeholder="search any player…" autocomplete="off">
<span class="chip on" data-pos="ALL">All</span><span class="chip" data-pos="QB">QB</span><span class="chip" data-pos="RB">RB</span><span class="chip" data-pos="WR">WR</span><span class="chip" data-pos="TE">TE</span><span class="chip" data-pos="DST">DST</span></div>
</header>
<div class="wrap"><div class="list" id="list"></div><div class="detail" id="detail"></div></div>
<script>
const D=__DATA__;
const KEYS=Object.keys(D).sort((a,b)=>(D[b].ceiling||0)-(D[a].ceiling||0));
let state={pos:'ALL',q:'',sel:null};
const E=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!=null)e.textContent=x;return e;};
function esc(s){const d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML;}
document.getElementById('sub').textContent=KEYS.length+" players · ceiling recipe (flag model) + 2025 boom-game evidence · "+Object.values(D).filter(c=>c.ev).length+" with 2025 game data";
function renderList(){
  const L=document.getElementById('list');L.innerHTML='';
  const ks=KEYS.filter(k=>(state.pos==='ALL'||D[k].pos===state.pos)&&(!state.q||D[k].name.toLowerCase().includes(state.q)));
  ks.forEach(k=>{const c=D[k];const r=E('div','prow'+(k===state.sel?' sel':''));
    r.innerHTML=`<span class="nm">${esc(c.name)}</span><span class="pos">${c.pos} ${c.fa?'·FA':'·'+esc(c.team)}</span>`;
    const bar=E('div','cbar');const i=E('i');i.style.width=Math.min(100,c.ceiling)+'%';bar.appendChild(i);
    r.appendChild(bar);r.appendChild(E('span','cval',c.ceiling+'%'));
    r.onclick=()=>{state.sel=k;renderList();renderDetail();};L.appendChild(r);});
  if(!ks.includes(state.sel)&&ks.length){state.sel=ks[0];renderDetail();}
}
function bars(splits,rate){
  const w=E('div','splits');
  splits.forEach(s=>{const row=E('div','sp');row.appendChild(E('span','lab',s.label));
    const b=E('div','bar');const i=E('i');if(s.rate>rate)i.classList.add('hot');i.style.width=Math.max(3,s.rate)+'%';b.appendChild(i);
    row.appendChild(b);row.appendChild(E('span','n',s.booms+'/'+s.games+' = '+s.rate+'%'));w.appendChild(row);});
  return w;
}
function renderDetail(){
  const c=D[state.sel];const d=document.getElementById('detail');if(!c){d.innerHTML='';return;}
  d.innerHTML='';
  const h=E('div','dh');h.setAttribute('data-ctx-host','');
  h.innerHTML=`<span class="nm">${esc(c.name)}</span><span class="meta">${c.pos} · ${c.fa?'UNSIGNED FA':esc(c.team)}</span> <span class="tier ${c.fa?'FA':c.tier}">${c.fa?'FREE AGENT':c.tier+' CEILING'}</span> <span class="ctxchip" data-ctx-name="${esc(c.name)}" data-ctx-pos="${esc(c.pos)}">EPA + CONTEXT</span>`;
  const big=E('div','big');big.innerHTML=`<div class="v">${c.ceiling}%</div><div class="l">ceiling rate</div>`;h.appendChild(big);
  d.appendChild(h);
  const nar=E('div','nar');nar.textContent=c.narrative;d.appendChild(nar);
  // booms when
  if(c.amps&&c.amps.length){const s=E('div','sec');s.appendChild(E('h3',null,'🚀 Booms when'));
    const ch=E('div','chips');c.amps.slice(0,14).forEach(a=>ch.appendChild(E('span','tag amp',a)));s.appendChild(ch);d.appendChild(s);}
  // specialist / stack
  if(c.cspec&&c.cspec.scheme){const s=E('div','sec');const co=E('div','callout');co.innerHTML=`🎯 <b>Coverage specialist:</b> crushes <b>${esc(c.cspec.scheme)}</b>${c.cspec.ratio?` (${c.cspec.ratio}× league)`:''} — feast weeks come against defenses that run it heavily.`;s.appendChild(co);d.appendChild(s);}
  if(c.stack_qb){const s=E('div','sec');const co=E('div','callout blue');co.innerHTML=`🔗 <b>Stack multiplier:</b> ceiling tied to <b>${esc(c.stack_qb)}</b> — his biggest games come when the QB is also in a plus spot.`;s.appendChild(co);d.appendChild(s);}
  // skills
  if(c.skills&&c.skills.length){const s=E('div','sec');s.appendChild(E('h3',null,'🧬 Ceiling skills (the raw material)'));
    c.skills.forEach(sk=>{const b=E('div','skill');b.innerHTML=`<div class="f">${esc(sk.f)}</div><div class="d">${esc(sk.d)}</div>`;s.appendChild(b);});d.appendChild(s);}
  // killers
  {const s=E('div','sec');s.appendChild(E('h3',null,'🧊 Ceiling killers'));
   if(c.killers&&c.killers.length){const ch=E('div','chips');c.killers.slice(0,8).forEach(k=>ch.appendChild(E('span','tag kill',k)));s.appendChild(ch);}
   else s.appendChild(E('div','muted','Matchup-proof — no condition meaningfully suppressed his ceiling.'));
   d.appendChild(s);}
  // 2025 evidence
  const s=E('div','sec');s.appendChild(E('h3',null,'📊 2025 proof'));
  if(c.ev){
    s.appendChild(E('div',null,'')).innerHTML=`<div style="font-size:13px;margin-bottom:8px">Boomed <b style="color:var(--acc);font-family:var(--mono)">${c.ev.booms}/${c.ev.n}</b> games (${c.ev.rate}%). ${c.ev.insight?'<span class="muted">'+esc(c.ev.insight)+'</span>':''}</div>`;
    if(c.ev.splits&&c.ev.splits.length)s.appendChild(bars(c.ev.splits,c.ev.rate));
    if(c.ev.boom_games&&c.ev.boom_games.length){const g=E('div','games');
      c.ev.boom_games.forEach(bg=>{const r=E('div','g');r.innerHTML=`<span>Wk ${bg.wk}</span><span class="pts">${bg.act}</span><span class="ctx">${bg.home?'home':'@'} ${esc(bg.opp)}${bg.dome?' · dome':''} · ${esc(bg.d)}</span>`;g.appendChild(r);});
      const gh=E('h3',null,'Boom games (best first)');gh.style.marginTop='10px';s.appendChild(gh);s.appendChild(g);}
  } else s.appendChild(E('div','muted','No 2025 game data (rookie / no qualifying games).'));
  d.appendChild(s);
}
document.getElementById('q').addEventListener('input',e=>{state.q=e.target.value.toLowerCase().trim();renderList();});
document.querySelectorAll('.chip').forEach(ch=>ch.onclick=()=>{document.querySelectorAll('.chip').forEach(x=>x.classList.remove('on'));ch.classList.add('on');state.pos=ch.dataset.pos;renderList();});
state.sel=KEYS[0];renderList();renderDetail();
</script></body></html>'''

blob = json.dumps(cases, ensure_ascii=False, separators=(',', ':'))
out = HTML.replace('__DATA__', blob)
import ctx_panel; out = ctx_panel.inject(out)   # 4-layer NFL Pro EPA drilldown (click the EPA chip in the detail header)
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'upside_cases.html')
for _ in range(3):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(out); f.flush(); os.fsync(f.fileno())
    if len(open(path, encoding='utf-8').read()) == len(out) and out.rstrip().endswith('</html>'):
        print(f"wrote upside_cases.html {round(len(out)/1024)} KB (verified)"); break
else:
    print("WARN: write not verified")
