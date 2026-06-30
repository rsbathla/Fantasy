#!/usr/bin/env python3
"""build_home.py — home.html, the single landing page (kills the 13-dashboard fragmentation).
One door routing to the three products + a unified dossier (player / offense / defense / coaching)."""
import json, os, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
def J(p):
    fp = os.path.join(HERE, p)
    return json.load(open(fp, encoding='utf-8')) if os.path.exists(fp) else {}
off = J('offense_profile.json'); dfn = J('defense_splits.json')
scheme = J('scheme_2026.json')
built = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

# coaching: per-team playcaller + dials (from scheme_2026) for the coaching tab
coach = {t: {'playcaller': v.get('playcaller'), 'off': v.get('off'), 'note': v.get('note'),
             'dc': v.get('dc'), 'def_note': v.get('def_note')}
         for t, v in scheme.items() if t != '_meta'}

oblob = json.dumps(off, ensure_ascii=False).replace('<', '\\u003c')
dblob = json.dumps(dfn, ensure_ascii=False).replace('<', '\\u003c')
cblob = json.dumps(coach, ensure_ascii=False).replace('<', '\\u003c')

HTML = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Fantasy Command — Home</title><style>
:root{--bg:#0e1016;--p1:#161922;--p2:#1c2030;--ln:#262b3a;--tx:#e7ebf3;--mut:#9aa3b6;--mut2:#697084;--acc:#7aa2ff;--qb:#e0567a;--rb:#37b87a;--wr:#3b8ef0;--te:#e8a33d;--good:#37b87a;--warn:#e8a33d;--bad:#e0567a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:13px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:0 16px 80px}
header{padding:22px 0 6px}h1{font-size:22px;margin:0 0 3px}.sub{color:var(--mut);font-size:13px}
.tabs{display:flex;gap:4px;margin:18px 0 10px;flex-wrap:wrap;border-bottom:1px solid var(--ln)}
.tab{padding:9px 15px;font-size:13px;font-weight:600;color:var(--mut);cursor:pointer;border-bottom:2px solid transparent}
.tab.on{color:var(--tx);border-bottom-color:var(--acc)}.tab:hover{color:var(--tx)}
.panel{display:none}.panel.on{display:block}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:8px 0}@media(max-width:820px){.grid3{grid-template-columns:1fr}}
.tool{background:linear-gradient(180deg,var(--p2),var(--p1));border:1px solid var(--ln);border-radius:14px;padding:18px}
.tool h2{margin:0 0 6px;font-size:16px}.tool .tag{font-size:10px;font-weight:800;letter-spacing:.4px;text-transform:uppercase;color:var(--acc)}
.tool p{color:var(--mut);font-size:12.5px;margin:8px 0}
.tool code{display:block;background:#0a0c12;border:1px solid var(--ln);border-radius:7px;padding:7px 9px;font-size:11.5px;color:#cfe0ff;margin:8px 0;overflow:auto}
.btn{display:inline-block;background:var(--acc);color:#08121f;font-weight:700;text-decoration:none;border-radius:8px;padding:7px 13px;font-size:12px;margin:4px 6px 0 0}
.btn.alt{background:var(--p2);color:var(--tx);border:1px solid var(--ln)}
.links{margin-top:10px}.links a{color:var(--acc);font-size:11.5px;margin-right:12px;text-decoration:none}.links a:hover{text-decoration:underline}
.ctl{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:12px 0}
input.q{flex:1;min-width:160px;background:var(--p2);border:1px solid var(--ln);color:var(--tx);border-radius:8px;padding:7px 10px}
table{width:100%;border-collapse:collapse;font-size:12px}th,td{padding:5px 7px;text-align:center;border-bottom:1px solid var(--ln);white-space:nowrap}
th{background:var(--p1);cursor:pointer;color:var(--mut);font-size:10.5px;text-transform:uppercase;letter-spacing:.3px}
td.l,th.l{text-align:left}tr:hover td{background:rgba(122,162,255,.05)}
.hm{border-radius:4px;font-weight:600;color:#0b0d12;min-width:28px;padding:2px 6px;display:inline-block}
.legend{font-size:11.5px;color:var(--mut2);margin:10px 0;padding:9px 12px;background:var(--p1);border:1px solid var(--ln);border-radius:8px;line-height:1.5}
.legend b{color:var(--tx)}.muted{color:var(--mut2)}.dial{font-size:9px;font-weight:700;border-radius:4px;padding:1px 5px;margin:1px;display:inline-block}.dial.up{background:rgba(55,184,122,.18);color:var(--good)}.dial.dn{background:rgba(224,86,122,.18);color:var(--bad)}.dial.nz{background:rgba(150,160,180,.12);color:var(--mut2)}
.card{background:var(--p1);border:1px solid var(--ln);border-radius:11px;padding:12px 14px;margin:8px 0}
</style></head><body>
<header><div class="wrap"><h1>Fantasy Command Center</h1><div class="sub">One home for the three tools · best-ball draft · weekly DFS · the dossier · built __BUILT__</div></div></header>
<div class="wrap">
<div class="tabs"><div class="tab on" data-t="home">Tools</div><div class="tab" data-t="off">Offense dossier</div><div class="tab" data-t="def">Defense dossier</div><div class="tab" data-t="coach">Coaching</div></div>

<div class="panel on" id="home">
 <div class="grid3">
  <div class="tool"><div class="tag">Goal 1</div><h2>Best Ball Draft</h2>
   <p>Paste your DraftKings <b>or</b> Underdog board — it auto-detects the platform and shows the best pick, optimized for <b>advancement rate × playoff (W15-17) title odds</b>, aware of your roster construction.</p>
   <code>python3 draft.py clip --seat &lt;you&gt;<br>python3 draft.py Board.txt --platform ud --mine "Pick A|Pick B"</code>
   <a class="btn" href="decision_dashboard.html">Open last draft result →</a>
   <div class="links"><a href="rankings.html">Rankings board</a><a href="lever_board.html">Ceiling levers</a><a href="upside_cases.html">Upside cases</a></div></div>
  <div class="tool"><div class="tag">Goal 2</div><h2>DFS Weekly</h2>
   <p>For any week: each player's <b>statistically-significant matchup edge</b> (their charting strengths vs that week's defense softness on the <b>same axes</b>), the qualitative levers, who to play, and <b>lineup templates from winner structure</b>.</p>
   <code>python3 dfs_model.py --week 15</code>
   <a class="btn" href="dfs_week.html">Open weekly model →</a>
   <div class="links"><a href="command_center.html">Command center</a><a href="player_explorer.html">Player explorer</a></div></div>
  <div class="tool"><div class="tag">Goal 3</div><h2>The Dossier</h2>
   <p>Everything we have on every <b>player, offense, defense, and coach</b> in one place — so you can learn as much as possible and know <b>who to press</b>. The deep player dossier aggregates projections, real EPA, the full situational profile, scheme fit, the 18-week matchup calendar, ceiling levers, risk flags, <b>tweets and video mentions</b>. Offense/defense/coaching are in the tabs above.</p>
   <a class="btn" href="dossier_deep.html">Deep player dossier →</a>
   <div class="links"><a href="dossier.html">Team dossier</a><a href="intel.html">Intel cards</a><a href="team_scout.html">Team scout</a></div></div>
 </div>
 <div class="legend">Every player view (here and in each tool) opens the same <b>4-layer context drilldown</b>: situational splits + real NFL Pro EPA · 2026 playcaller fit · vacated/opportunity · W15-17 matchup. The weekly "who to play" board <i>is</i> the by-week "who to press" pivot — sort by edge for the slate's smash spots.</div>
</div>

<div class="panel" id="off">
 <div class="legend">Per-offense <b>scheme identity</b> (all 32): pace, pass-rate, <b>run scheme (zone vs gap, from real RunType attempts)</b>, motion/play-action where charted, 2026 play-caller + scheme dials, environment. The "who is this offense" object.</div>
 <div class="ctl"><input class="q" id="oq" placeholder="Search team…"></div>
 <div style="overflow:auto"><table id="ot"></table></div>
</div>

<div class="panel" id="def">
 <div class="legend">Per-defense <b>softness by axis</b> (higher percentile = softer = better for the offense) — the same split-parity layer the DFS matchup edge reads. Sort to find who to attack on each axis.</div>
 <div class="ctl"><input class="q" id="dq" placeholder="Search team…"></div>
 <div style="overflow:auto"><table id="dt"></table></div>
</div>

<div class="panel" id="coach">
 <div class="legend">2026 play-callers and scheme dials (motion/vertical/pass-catch/scramble ∈ {−1,0,+1}; only where the caller genuinely changed — continuity teams omit dials by design). The coach→scheme→player-impact layer.</div>
 <div id="cl"></div>
</div>
</div>
<script>
const OFF=__OFF__, DEF=__DEF__, COACH=__COACH__;
const esc=s=>String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
const hm=v=>{if(v==null)return 'transparent';const h=Math.max(0,Math.min(120,v*1.2));return `hsl(${h},58%,44%)`;};
document.querySelectorAll('.tab').forEach(t=>t.onclick=()=>{document.querySelectorAll('.tab').forEach(x=>x.classList.remove('on'));t.classList.add('on');document.querySelectorAll('.panel').forEach(p=>p.classList.remove('on'));document.getElementById(t.dataset.t).classList.add('on');});
// offense table
let oq='';function odraw(){const ts=Object.keys(OFF).filter(t=>!oq||t.toLowerCase().includes(oq)||(OFF[t].identity||'').toLowerCase().includes(oq)).sort();
 let h='<tr><th class="l">Team</th><th class="l">Identity</th><th>Pace pctl</th><th>Pass%</th><th>Zone-run%</th><th>Motion</th><th>PA</th><th>Env</th><th class="l">2026 caller</th></tr>';
 ts.forEach(t=>{const o=OFF[t],rs=o.run_scheme||{},e=o.environment||{},pc=o.pace||{};h+=`<tr><td class="l"><b>${t}</b></td><td class="l muted" style="white-space:normal;max-width:340px">${esc(o.identity)}</td><td>${pc.pctl!=null?`<span class="hm" style="background:${hm(pc.pctl)}">${Math.round(pc.pctl)}</span>`:'–'}</td><td>${o.pass_rate!=null?o.pass_rate:'–'}</td><td>${rs.zone_rate!=null?rs.zone_rate:'–'}</td><td>${o.motion!=null?o.motion:'<span class=muted>–</span>'}</td><td>${o.play_action!=null?o.play_action:'<span class=muted>–</span>'}</td><td>${e.env_idx!=null?Math.round(e.env_idx):'–'}</td><td class="l muted" style="white-space:normal;max-width:200px;font-size:11px">${esc((o.playcaller||'').split('(')[0])}</td></tr>`;});
 document.getElementById('ot').innerHTML=h;}
document.getElementById('oq').oninput=e=>{oq=e.target.value.toLowerCase();odraw();};
// defense table
let dq='';function ddraw(){const ts=Object.keys(DEF).filter(t=>!dq||t.toLowerCase().includes(dq)).sort();
 const cell=o=>{const v=o&&o.softness_pctl;return v==null?'<span class=muted>–</span>':`<span class="hm" style="background:${hm(v)}">${Math.round(v)}</span>`;};
 const fp=v=>v==null?'<span class=muted>–</span>':`<span class="hm" style="background:${hm(Math.max(0,Math.min(100,50+v*8)))}">${v>0?'+':''}${v}</span>`;
 let h='<tr><th class="l">Team</th><th>Soft vs Man</th><th>Soft vs Zone</th><th>Soft Deep</th><th>Soft Short</th><th>WR pts</th><th>TE pts</th><th>RB pts</th><th class="l">Funnels</th></tr>';
 ts.forEach(t=>{const d=DEF[t],bp=d.by_pos||{};h+=`<tr><td class="l"><b>${t}</b></td><td>${cell(d.vs_man)}</td><td>${cell(d.vs_zone)}</td><td>${cell(d.deep)}</td><td>${cell(d.short)}</td><td>${fp(bp.wr1??bp.wr)}</td><td>${fp(bp.te)}</td><td>${fp(bp.rb)}</td><td class="l muted" style="white-space:normal;max-width:320px;font-size:10.5px">${(d.funnels||[]).join(' · ')}</td></tr>`;});
 document.getElementById('dt').innerHTML=h;}
document.getElementById('dq').oninput=e=>{dq=e.target.value.toLowerCase();ddraw();};
// coaching
function dchip(l,v){if(v==null)return '';const c=v>0?'up':v<0?'dn':'nz',a=v>0?'▲':v<0?'▼':'•';return `<span class="dial ${c}">${l} ${a}</span>`;}
let ch='';Object.keys(COACH).sort().forEach(t=>{const c=COACH[t],o=c.off||{};ch+=`<div class="card"><b>${t}</b> — ${esc(c.playcaller||'')}${o&&Object.keys(o).length?` <span style="margin-left:6px">${dchip('Mot',o.motion)}${dchip('Vert',o.vertical)}${dchip('Pass',o.passcatch)}${dchip('Scr',o.scramble)}</span>`:''}${c.note?`<div class="muted" style="font-size:11.5px;margin-top:4px">${esc(c.note)}</div>`:''}${c.def_note?`<div class="muted" style="font-size:11px;margin-top:3px">DEF: ${esc(c.def_note)}</div>`:''}</div>`;});
document.getElementById('cl').innerHTML=ch;
odraw();ddraw();
</script></body></html>'''
html = (HTML.replace('__BUILT__', built).replace('__OFF__', oblob).replace('__DEF__', dblob).replace('__COACH__', cblob))
open(os.path.join(HERE, 'home.html'), 'w', encoding='utf-8').write(html)
print(f"wrote home.html ({len(html)//1024} KB) — offense {len(off)} · defense {len(dfn)} · coaching {len(coach)}")
