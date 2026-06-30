#!/usr/bin/env python3
"""render_dfs_week.py — dfs_week.json -> dfs_week.html (self-contained weekly DFS page).
Who-to-play ranked board (with matchup edges player-strength-vs-defense-softness on the SAME axes),
the qualitative levers, lineup-construction templates from winner structure, and a defense-splits
reference. Click any player for the shared 4-layer context drilldown."""
import json, os, datetime
import ctx_panel
HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, 'dfs_week.json'), encoding='utf-8'))
defs = json.load(open(os.path.join(HERE, 'defense_splits.json'), encoding='utf-8'))
built = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
blob = json.dumps(D, ensure_ascii=False).replace('<', '\\u003c')
dblob = json.dumps(defs, ensure_ascii=False).replace('<', '\\u003c')

HTML = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DFS Weekly Model — Week __WK__</title><style>
:root{--bg:#0e1016;--p1:#161922;--p2:#1c2030;--ln:#262b3a;--tx:#e7ebf3;--mut:#9aa3b6;--mut2:#697084;--acc:#7aa2ff;--qb:#e0567a;--rb:#37b87a;--wr:#3b8ef0;--te:#e8a33d;--good:#37b87a;--warn:#e8a33d;--bad:#e0567a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:13px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif}
.wrap{max-width:1240px;margin:0 auto;padding:0 16px 80px}
header{position:sticky;top:0;z-index:40;background:rgba(14,16,22,.97);backdrop-filter:blur(8px);border-bottom:1px solid var(--ln);padding:12px 0 0}
h1{font-size:17px;margin:0 0 2px}.sub{color:var(--mut);font-size:12px;margin-bottom:9px}
.tabs{display:flex;gap:4px}.tab{padding:9px 15px;font-size:13px;font-weight:600;color:var(--mut);cursor:pointer;border-bottom:2px solid transparent}
.tab.on{color:var(--tx);border-bottom-color:var(--acc)}.tab:hover{color:var(--tx)}
.panel{display:none}.panel.on{display:block}
.ctl{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:12px 0}
input.q{flex:1;min-width:160px;background:var(--p2);border:1px solid var(--ln);color:var(--tx);border-radius:8px;padding:7px 10px}
.pf{padding:5px 9px;font-size:11px;font-weight:700;border:1px solid var(--ln);border-radius:7px;color:var(--mut);cursor:pointer;background:var(--p1)}.pf.on{color:#0c0e13}
.pf.QB.on{background:var(--qb)}.pf.RB.on{background:var(--rb)}.pf.WR.on{background:var(--wr)}.pf.TE.on{background:var(--te)}.pf.ALL.on{background:var(--acc)}
table{width:100%;border-collapse:collapse;font-size:12px}th,td{padding:5px 7px;text-align:center;border-bottom:1px solid var(--ln);white-space:nowrap}
th{position:sticky;top:96px;background:var(--p1);cursor:pointer;color:var(--mut);font-size:10.5px;text-transform:uppercase;letter-spacing:.3px;z-index:5}
td.l,th.l{text-align:left}tr:hover td{background:rgba(122,162,255,.05)}
.pos{font-size:9px;font-weight:800;border-radius:4px;padding:1px 5px;color:#0c0e13}.pos.QB{background:var(--qb)}.pos.RB{background:var(--rb)}.pos.WR{background:var(--wr)}.pos.TE{background:var(--te)}
.hm{border-radius:4px;font-weight:600;color:#0b0d12;min-width:30px;padding:2px 6px;display:inline-block}
.edge{font-size:9px;font-weight:700;border-radius:4px;padding:1px 5px;margin:1px;display:inline-block}.edge.smash{background:rgba(55,184,122,.2);color:var(--good)}.edge.ok{background:rgba(150,160,180,.14);color:var(--mut)}
.q{font-size:9.5px;color:var(--warn);background:rgba(232,163,61,.12);border-radius:4px;padding:1px 5px;margin:1px;display:inline-block}
.card{background:var(--p1);border:1px solid var(--ln);border-radius:12px;padding:14px 16px;margin:10px 0}
.gh{font-size:14px;font-weight:700;margin-bottom:8px}.gh .tot{color:var(--warn);font-size:12px;margin-left:8px}
.chip{display:inline-block;background:var(--p2);border:1px solid var(--ln);border-radius:7px;padding:3px 9px;margin:2px;font-size:11px}
.chip.qb{border-color:var(--qb)}.chip.bb{border-color:var(--warn)}
.rule{display:flex;gap:10px;padding:7px 0;border-bottom:1px solid var(--ln)}.rule b{color:var(--acc);min-width:200px;display:inline-block}
.legend{font-size:11.5px;color:var(--mut2);margin:10px 0;padding:9px 12px;background:var(--p1);border:1px solid var(--ln);border-radius:8px;line-height:1.5}
.legend b{color:var(--tx)}.muted{color:var(--mut2)}
</style>__CTXCSS__</head><body>
<header><div class="wrap"><h1>DFS Weekly Model — Week __WK__</h1>
<div class="sub">__N__ players · matchup edge = your statistically-significant strengths vs THIS week's defense softness on the same axes · click a player for the 4-layer context · built __BUILT__</div>
<div class="tabs"><div class="tab on" data-t="plays">Who to play</div><div class="tab" data-t="lineups">Lineup templates</div><div class="tab" data-t="def">Defense splits</div></div>
</div></header>
<div class="wrap">
<div class="panel on" id="plays">
  <div class="legend">Each player's <b>matchup edge</b> lines up their real charting strengths (man/zone/deep/slot percentiles) against <b>this week's opponent defense's softness on the SAME axis</b>. A <span class="edge smash">green SMASH</span> = player-strong meets defense-soft. <b>Play</b> = ceiling-anchored, matchup- and implied-total-tilted weekly score. <span class="q">Amber</span> = qualitative levers (scheme/opportunity), good-to-know but not stat-significant. The defense data is the same-keyed split-parity layer (defense_splits).</div>
  <div class="ctl"><input class="q" id="q" placeholder="Search player…"><span id="pf"></span></div>
  <div style="overflow:auto"><table id="t"></table></div>
</div>
<div class="panel" id="lineups">
  <div class="legend">Lineup construction from <b>winner structure</b> (STRATEGY_SPEC + real 2024-25 correlations). Anchor ONE game, stack the QB with 1-2 same-team catchers, add an opponent <b>bring-back only in high-total (shootout) games</b> (bring-back r=0.16 high-total vs 0.06 low). Stop at 4-5 correlated pieces. These templates are built from this week's top plays in the highest-total games.</div>
  <div id="tmpl"></div>
  <h3 style="margin:18px 0 6px">Winner rules</h3><div class="card" id="rules"></div>
</div>
<div class="panel" id="def">
  <div class="legend">Per-defense <b>softness</b> on each axis (higher percentile = softer = better for the offense). This is the same split-parity layer the matchup edge reads. Sort to find the week's smash spots by axis.</div>
  <div class="ctl"><input class="q" id="dq" placeholder="Search team…"></div>
  <div style="overflow:auto"><table id="dt"></table></div>
</div>
</div>
<script>
const D=__DATA__, DEFS=__DEFS__;
const esc=s=>String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
const hm=v=>{if(v==null)return 'transparent';const h=Math.max(0,Math.min(120,v*1.2));return `hsl(${h},58%,44%)`;};
const posb=p=>`<span class="pos ${p}">${p}</span>`;
document.querySelectorAll('.tab').forEach(t=>t.onclick=()=>{document.querySelectorAll('.tab').forEach(x=>x.classList.remove('on'));t.classList.add('on');document.querySelectorAll('.panel').forEach(p=>p.classList.remove('on'));document.getElementById(t.dataset.t).classList.add('on');});
const POS=['ALL','QB','RB','WR','TE'];let st={pos:'ALL',q:'',sort:'play',dir:-1};
function pf(){const h=document.getElementById('pf');h.innerHTML='';POS.forEach(p=>{const b=document.createElement('span');b.className='pf '+p+(p===st.pos?' on':'');b.textContent=p;b.onclick=()=>{st.pos=p;draw();};h.appendChild(b);});}
function edgeHTML(e){const lab=e.fpaa!=null?`${e.axis} (+${e.fpaa})`:`${e.axis}${e.def_soft_pctl!=null?' '+Math.round(e.def_soft_pctl):''}`;return `<span class="edge ${e.smash?'smash':'ok'}">${esc(lab)}</span>`;}
function draw(){
  let r=D.players.filter(p=>(st.pos==='ALL'||p.pos===st.pos)&&(!st.q||p.name.toLowerCase().includes(st.q)));
  r.sort((a,b)=>((a[st.sort]==null?-1:a[st.sort])-(b[st.sort]==null?-1:b[st.sort]))*st.dir);
  let h='<tr><th class="l" data-k="name">Player</th><th>Pos</th><th>Opp</th><th data-k="total">Total</th><th data-k="play">Play</th><th data-k="edge_score">Edge</th><th class="l">Matchup edges (strength vs soft D)</th><th class="l">Qualitative</th></tr>';
  r.forEach(p=>{const ctxhas=window.CTXPANEL&&window.CTXPANEL.has?'':'';
   h+=`<tr data-ctx-host><td class="l"><b>${esc(p.name)}</b> <span class="muted">${p.team}</span> <span class="ctxchip" data-ctx-name="${esc(p.name)}" data-ctx-pos="${p.pos}">CTX</span></td><td>${posb(p.pos)}</td><td>${esc(p.opp||'—')}${p.home===false?' @':''}</td><td>${p.total??''}</td><td><span class="hm" style="background:${hm(p.play)}">${p.play}</span></td><td><span class="hm" style="background:${hm(p.edge_score)}">${p.edge_score}</span></td><td class="l">${(p.edges||[]).slice(0,4).map(edgeHTML).join('')}</td><td class="l">${(p.quals||[]).map(q=>`<span class="q">${esc(q)}</span>`).join('')}</td></tr>`;});
  document.getElementById('t').innerHTML=h;
  document.getElementById('t').querySelectorAll('th[data-k]').forEach(th=>th.onclick=()=>{const k=th.dataset.k;if(st.sort===k)st.dir*=-1;else{st.sort=k;st.dir=k==='name'?1:-1;}draw();});
}
document.getElementById('q').oninput=e=>{st.q=e.target.value.toLowerCase();draw();};
// lineup templates
let lh='';(D.templates||[]).forEach(t=>{lh+=`<div class="card"><div class="gh">${esc(t.anchor_game)} <span class="tot">total ${t.total??'—'} ${t.high_total?'· SHOOTOUT':'· low-total'}</span></div>
 <div><span class="chip qb"><b>QB</b> ${esc(t.qb_player)} <span class="muted">${t.qb}</span></span> ${(t.stack||[]).map(s=>`<span class="chip">${esc(s)}</span>`).join('')} ${t.bringback?`<span class="muted">+ bring-back →</span> <span class="chip bb">${esc(t.bringback)}</span>`:''}</div>
 <div class="muted" style="margin-top:6px;font-size:11px">${esc(t.shape)}</div></div>`;});
document.getElementById('tmpl').innerHTML=lh||'<div class="muted">No high-total anchor games found for this week.</div>';
document.getElementById('rules').innerHTML=(D.winner_rules||[]).map(r=>`<div class="rule"><b>${esc(r[0])}</b><span>${esc(r[1])}</span></div>`).join('');
// defense splits table
let ds={q:''};
function ddraw(){const teams=Object.keys(DEFS).filter(t=>!ds.q||t.toLowerCase().includes(ds.q)).sort();
 let h='<tr><th class="l">Team</th><th>Soft vs Man</th><th>Soft vs Zone</th><th>Soft Deep</th><th>Soft Short</th><th>WR pts allowed</th><th>TE pts allowed</th><th>RB pts allowed</th><th class="l">Funnels</th></tr>';
 const cell=(o)=>{const v=o&&o.softness_pctl;return v==null?'<span class="muted">–</span>':`<span class="hm" style="background:${hm(v)}">${Math.round(v)}</span>`;};
 const fp=(v)=>v==null?'<span class="muted">–</span>':`<span class="hm" style="background:${hm(Math.max(0,Math.min(100,50+v*8)))}">${v>0?'+':''}${v}</span>`;
 teams.forEach(t=>{const d=DEFS[t],bp=d.by_pos||{};h+=`<tr><td class="l"><b>${t}</b></td><td>${cell(d.vs_man)}</td><td>${cell(d.vs_zone)}</td><td>${cell(d.deep)}</td><td>${cell(d.short)}</td><td>${fp(bp.wr1??bp.wr)}</td><td>${fp(bp.te)}</td><td>${fp(bp.rb)}</td><td class="l muted" style="white-space:normal;max-width:320px;font-size:10.5px">${(d.funnels||[]).join(' · ')}</td></tr>`;});
 document.getElementById('dt').innerHTML=h;}
document.getElementById('dq').oninput=e=>{ds.q=e.target.value.toLowerCase();ddraw();};
pf();draw();ddraw();
</script>__CTXJS__</body></html>'''

html = (HTML.replace('__WK__', str(D['week'])).replace('__N__', str(D['n_players']))
        .replace('__BUILT__', built).replace('__DATA__', blob).replace('__DEFS__', dblob)
        .replace('__CTXCSS__', ctx_panel.css()).replace('__CTXJS__', ctx_panel.script()))
open(os.path.join(HERE, 'dfs_week.html'), 'w', encoding='utf-8').write(html)
print(f"wrote dfs_week.html ({len(html)//1024} KB) — week {D['week']}, {D['n_players']} players")
