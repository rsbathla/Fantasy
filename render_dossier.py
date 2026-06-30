#!/usr/bin/env python3
"""Render dossier.html: clean, professional, team-by-team scouting dossier with FULL per-player
detail (expandable cards) + a Challenge (quiz) mode."""
import json, os, core, datetime
D=json.load(open(core.P('dossier_data.json')))
blob=json.dumps(D,ensure_ascii=False).replace('<','\\u003c')
built=datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
HTML=r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>2026 Team Dossiers</title><style>
:root{--bg:#0b0f17;--bg2:#0e1320;--card:#121a29;--card2:#0f1626;--line:#1e2a3d;--line2:#2a3a52;--ink:#eef2f8;--ink2:#aab8cc;--ink3:#6f819b;--accent:#5b9dff;--good:#5fd08a;--warn:#e6b34d;--bad:#ff8585;--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
*{box-sizing:border-box}html,body{margin:0;height:100%}
body{background:var(--bg);color:var(--ink);font:14px/1.55 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
.top{padding:11px 18px;border-bottom:1px solid var(--line);display:flex;gap:14px;align-items:center;flex-wrap:wrap;background:var(--bg2)}
.top h1{font-size:15px;margin:0;letter-spacing:.3px;font-weight:800}
.top .sub{color:var(--ink3);font-size:11.5px;font-family:var(--mono)}
.modes{margin-left:auto;display:flex;gap:6px}
.mbtn{font-size:12px;font-weight:700;padding:5px 13px;border:1px solid var(--line2);border-radius:8px;cursor:pointer;color:var(--ink2);background:transparent}
.mbtn.on{background:var(--accent);color:#08101e;border-color:var(--accent)}
.wrap{display:grid;grid-template-columns:212px 1fr;height:calc(100vh - 46px)}
.nav{border-right:1px solid var(--line);overflow:auto;background:var(--bg2);padding:6px 0}
.navsrch{padding:8px 9px}.navsrch input{width:100%;background:#0b1018;color:var(--ink);border:1px solid var(--line2);border-radius:8px;padding:7px 9px;font-size:12.5px}
.divh{font-size:9.5px;text-transform:uppercase;letter-spacing:1px;color:var(--ink3);font-weight:800;padding:10px 12px 3px}
.trow{padding:5px 12px;cursor:pointer;font-size:13px;display:flex;justify-content:space-between;align-items:center;border-left:2px solid transparent}
.trow:hover{background:rgba(91,157,255,.08)}.trow.sel{background:rgba(91,157,255,.14);border-left-color:var(--accent)}
.trow .ab{font-family:var(--mono);font-weight:700}.trow .nm{color:var(--ink3);font-size:11px}
.pane{overflow:auto;padding:22px 30px;max-width:1060px}
.dh{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;border-bottom:1px solid var(--line);padding-bottom:12px;margin-bottom:4px}
.dh .ab{font-size:30px;font-weight:900;letter-spacing:-.5px}.dh .nm{font-size:16px;color:var(--ink2)}.dh .dv{font-size:11px;color:var(--ink3);font-family:var(--mono);margin-left:auto}
.badges{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0}
.badge{border:1px solid var(--line2);border-radius:8px;padding:5px 11px;font-size:12px;background:var(--card2)}
.badge b{font-family:var(--mono)}
.badge.pass{border-color:rgba(91,157,255,.5);color:var(--accent)}.badge.run{border-color:rgba(95,208,138,.5);color:var(--good)}
.badge.shift{border-color:var(--warn);color:var(--warn)}
.sec{margin:22px 0 6px;font-size:11px;text-transform:uppercase;letter-spacing:1.1px;color:var(--ink3);font-weight:800;border-bottom:1px solid var(--line);padding-bottom:5px;display:flex;justify-content:space-between;align-items:center}
.sec .tools{font-weight:700;letter-spacing:0;text-transform:none}
.tbtn{font-size:11px;color:var(--accent);background:transparent;border:1px solid var(--line2);border-radius:6px;padding:3px 9px;cursor:pointer;margin-left:6px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(118px,1fr));gap:9px;margin:10px 0}
.kv{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px 11px}
.kv .k{font-size:9.5px;text-transform:uppercase;letter-spacing:.5px;color:var(--ink3);font-weight:700}
.kv .v{font-size:17px;font-weight:800;font-family:var(--mono);margin-top:1px}.kv .v small{font-size:10px;color:var(--ink3);font-weight:600}
.note{font-size:13px;color:var(--ink2);background:rgba(91,157,255,.06);border-left:3px solid var(--accent);padding:9px 12px;border-radius:7px;margin:8px 0}
.shiftnote{background:rgba(230,179,77,.08);border-left-color:var(--warn);color:var(--warn)}
.posgrp{margin:14px 0 4px;font-size:11px;font-weight:800;color:var(--accent);font-family:var(--mono);letter-spacing:.5px}
/* player card */
.pc{background:var(--card2);border:1px solid var(--line);border-radius:11px;margin:7px 0;overflow:hidden}
.psum{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:10px 13px;cursor:pointer}
.psum:hover{background:rgba(91,157,255,.05)}
.prk{font-family:var(--mono);font-size:12px;color:var(--ink3);min-width:34px}
.pnm{font-weight:800;font-size:14.5px;min-width:150px}
.ppos{font-family:var(--mono);font-size:10px;font-weight:700;border:1px solid var(--line2);border-radius:5px;padding:1px 5px;color:var(--ink2)}
.pmeta{font-family:var(--mono);font-size:11.5px;color:var(--ink3)}
.edge{font-family:var(--mono);font-size:11.5px;font-weight:700}.edge.up{color:var(--good)}.edge.dn{color:var(--bad)}
.cons{display:flex;align-items:center;gap:6px;margin-left:auto}
.consbar{width:74px;height:7px;border-radius:4px;background:#0b1018;border:1px solid var(--line2);overflow:hidden}
.consbar i{display:block;height:100%}
.consv{font-family:var(--mono);font-size:11.5px;font-weight:700}
.exp{color:var(--ink3);font-size:12px;font-family:var(--mono)}
.pflags{display:flex;gap:5px;flex-wrap:wrap;width:100%;margin-top:2px}
.fchip{font-size:9.5px;font-weight:700;border:1px solid var(--line2);border-radius:5px;padding:1px 6px;color:var(--warn)}
.risksum{font-size:11px;font-weight:800;font-family:var(--mono);border:1px solid var(--bad);border-radius:6px;padding:1px 7px;color:var(--bad);margin-left:6px}
.risksum .po{color:var(--warn)}
.rkflags{display:flex;flex-direction:column;gap:4px;margin:4px 0}
.rkf{font-size:11.5px;padding:3px 8px;border-radius:6px;border-left:3px solid var(--line2);background:rgba(255,133,133,.05);color:var(--ink2)}
.rkf.s3{border-left-color:var(--bad)}.rkf.s2{border-left-color:var(--warn)}.rkf.s1{border-left-color:var(--ink3)}
.rkf .po{font-size:9px;font-weight:800;color:var(--warn);border:1px solid var(--warn);border-radius:4px;padding:0 4px;margin-left:6px}
.rkf .cd{font-family:var(--mono);font-weight:700;color:var(--ink);margin-right:6px}
.adjpg{color:var(--bad);font-weight:800}
.pdetail{display:none;border-top:1px solid var(--line);padding:11px 13px 14px;background:var(--card)}
.pc.open .pdetail{display:block}.pc.open .exp{color:var(--accent)}
.dlab{font-size:9.5px;text-transform:uppercase;letter-spacing:.7px;color:var(--ink3);font-weight:800;margin:12px 0 5px}
.dlab:first-child{margin-top:0}
.siggrp{margin:6px 0}
.sgh{font-size:10px;color:var(--ink3);font-weight:700;margin:6px 0 3px}
.sigrow{display:grid;grid-template-columns:repeat(auto-fill,minmax(168px,1fr));gap:5px 14px}
.sig{display:flex;align-items:center;gap:7px;font-size:11.5px}
.sl{color:var(--ink2);min-width:78px}.sb{flex:1;height:6px;border-radius:3px;background:#0b1018;border:1px solid var(--line2);overflow:hidden}
.sb i{display:block;height:100%}.sv{font-family:var(--mono);font-size:11px;min-width:20px;text-align:right;color:var(--ink2)}
.up{border-top:1px solid var(--line);padding:5px 0;font-size:12px;display:flex;gap:8px;flex-wrap:wrap;align-items:baseline}
.up:first-of-type{border-top:none}.updim{font-weight:700;font-family:var(--mono);min-width:84px}
.tier{font-size:9px;font-weight:800;border-radius:4px;padding:1px 5px;border:1px solid var(--line2)}
.tier.STABLE{color:var(--good);border-color:rgba(95,208,138,.5)}.tier.MODERATE{color:var(--accent)}
.tier.LOW,.tier.NOISE,.tier.LEVEL-ONLY{color:var(--ink3)}
.upnote{color:var(--ink3);font-size:11.5px;flex:1;min-width:200px}
.bt{border-top:1px solid var(--line);padding:5px 0;font-size:12px}
.verd{font-size:9.5px;font-weight:800;border-radius:4px;padding:1px 6px;margin-right:6px}
.verd.S{color:var(--good);border:1px solid rgba(95,208,138,.5)}.verd.M{color:var(--warn);border:1px solid rgba(230,179,77,.5)}.verd.W{color:var(--bad);border:1px solid rgba(255,133,133,.4)}
.grp-model{color:var(--good)}.grp-off{color:var(--ink3)}
.tw{border-top:1px solid var(--line);padding:7px 0;font-size:12px}.tw:first-of-type{border-top:none}
.tw .h{color:var(--ink3);font-family:var(--mono);font-size:11px}.tw .tx{color:var(--ink2);margin-top:2px;white-space:pre-wrap}
.pl{display:flex;gap:9px;align-items:baseline;flex-wrap:wrap;padding:6px 0;border-top:1px solid var(--line)}
.pl:first-of-type{border-top:none}.pl .nm{font-weight:700;min-width:155px}.pl .mt{font-family:var(--mono);font-size:11.5px;color:var(--ink3)}
.chip{font-size:10px;font-weight:700;border:1px solid var(--line2);border-radius:5px;padding:1px 6px;color:var(--good)}
.stk{font-size:14px}.stk b{color:var(--accent)}
.qwrap{max-width:760px}
.qcard{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:15px 17px;margin:12px 0}
.qq{font-size:15px;font-weight:700}.qa{margin-top:10px;font-size:14px;color:var(--good);display:none}.qa.show{display:block}
.qbtn{margin-top:10px;font-size:12px;font-weight:700;color:var(--accent);background:transparent;border:1px solid var(--line2);border-radius:7px;padding:5px 11px;cursor:pointer}
.qbar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:6px}
.muted{color:var(--ink3)}
.levwrap{margin:6px 0}
.levi{font-size:12.5px;color:var(--ink);padding:6px 10px;border-left:3px solid var(--good);margin:5px 0;background:rgba(95,208,138,.06);border-radius:0 7px 7px 0}
.levhint{font-size:11px;color:var(--ink3);margin:2px 0 6px}

.qprof{font-size:12.5px;color:var(--ink2);margin:2px 0 6px}
.qprof b{color:var(--ink)}
.qtrait{display:inline-block;font-size:10.5px;font-weight:700;border:1px solid var(--line2);border-radius:5px;padding:1px 7px;margin:2px 4px 2px 0;color:var(--accent)}
.qclaim{font-size:11.5px;color:var(--good);margin-top:5px}
.qnote{font-size:11px;color:var(--ink3);margin-top:3px}

.bbwrap{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:9px 0}
.bbcol{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:9px 12px}
.bbh{font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.6px;margin-bottom:5px}
.bbh.boom{color:var(--good)}.bbh.bust{color:var(--bad)}
.bbi{font-size:12px;color:var(--ink2);padding:4px 0;border-top:1px solid var(--line)}
.bbi:first-of-type{border-top:none}
.tend{font-size:9px;font-weight:700;color:var(--ink3);border:1px solid var(--line2);border-radius:4px;padding:0 4px;margin-left:6px}
@media(max-width:760px){.bbwrap{grid-template-columns:1fr}}

@media print{.nav,.top .modes{display:none}.wrap{grid-template-columns:1fr;height:auto}.pane{max-width:none}.pdetail{display:block !important}}
</style></head><body>
<div class="top"><h1>2026 TEAM DOSSIERS</h1><span class="sub">__N__ teams &middot; __NP__ players &middot; built __BUILT__ &middot; &#9873; total risk flags, &#9670; = affects fantasy playoffs (W15-17)</span>
<div class="modes"><span class="mbtn on" id="mD">Dossier</span><span class="mbtn" id="mQ">Challenge</span></div></div>
<div class="wrap">
  <div class="nav"><div class="navsrch"><input id="q" placeholder="search team"></div><div id="navlist"></div></div>
  <div class="pane" id="pane"><div class="muted">Select a team.</div></div>
</div>
<script>
const D=__DATA__; let mode='dossier', sel=null;
const esc=s=>(s==null?'':String(s)).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const lname=n=>{n=String(n||'').replace(/\s+(jr|sr|ii|iii|iv|v)\.?$/i,'');const p=n.split(' ');return p[p.length-1]||n;};
const T=()=>D.teams; const byTeam=a=>T().find(t=>t.team===a);
const DIVS=['AFC East','AFC North','AFC South','AFC West','NFC East','NFC North','NFC South','NFC West'];
const pcol=v=>v==null?'var(--ink3)':(v>=80?'var(--good)':v>=60?'#86c98f':v>=40?'var(--ink2)':v>=20?'var(--warn)':'var(--bad)');
function nav(q){q=(q||'').toLowerCase();const el=document.getElementById('navlist');let h='';
 DIVS.forEach(dv=>{const ts=T().filter(t=>t.division===dv&&(!q||(t.team+' '+t.name).toLowerCase().includes(q)));
  if(!ts.length)return; h+=`<div class="divh">${dv}</div>`;
  ts.forEach(t=>{h+=`<div class="trow ${t.team===sel?'sel':''}" data-t="${t.team}"><span class="ab">${t.team}</span><span class="nm">${esc(t.name.split(' ').slice(-1)[0])} &middot; ${t.players.length}</span></div>`;});});
 el.innerHTML=h; el.querySelectorAll('.trow').forEach(r=>r.onclick=()=>{sel=r.dataset.t;nav(document.getElementById('q').value);show();});}
function kv(k,v,sm){return v==null||v===''?'':`<div class="kv"><div class="k">${k}</div><div class="v">${v}${sm?` <small>${sm}</small>`:''}</div></div>`;}
function bar(v){return `<span class="sb"><i style="width:${v==null?0:v}%;background:${pcol(v)}"></i></span>`;}
function playerCard(p){
 const edge=p.vs_adp==null?'':`<span class="edge ${p.vs_adp>0?'up':(p.vs_adp<0?'dn':'')}">${p.vs_adp>0?'+':''}${p.vs_adp} vs ADP</span>`;
 let h=`<div class="pc" data-ctx-host><div class="psum"><span class="prk">${p.rank?'#'+p.rank:'—'}</span><span class="ppos">${esc(p.pos)}</span><span class="pnm">${esc(p.name)}</span><span class="ctxchip" data-ctx-name="${esc(p.name)}" data-ctx-pos="${esc(p.pos)}">EPA</span>`
  +`<span class="pmeta">ADP ${p.adp!=null?Math.round(p.adp):'—'}</span>${edge}`
  +(p.flags_total?`<span class="risksum" title="${p.flags_total} total risk flag(s)${p.flags_playoff?'; '+p.flags_playoff+' affect the fantasy playoffs (W15-17)':''}">&#9873;${p.flags_total}${p.flags_playoff?` <span class="po">&#9670;${p.flags_playoff}</span>`:''}</span>`:'')
  +`<span class="cons">${p.consensus!=null?`<span class="consbar"><i style="width:${p.consensus}%;background:${pcol(p.consensus)}"></i></span><span class="consv">${p.consensus}</span>`:''}<span class="exp">▸</span></span>`;
 if((p.flags||[]).length)h+=`<div class="pflags">`+p.flags.map(f=>`<span class="fchip">${esc(f)}</span>`).join('')+`</div>`;
 h+=`</div><div class="pdetail">`;
 const rf=p.risk_flags||[];
 if(rf.length){
  h+=`<div class="dlab">Risk flags &mdash; &#9873; ${p.flags_total} total &middot; &#9670; ${p.flags_playoff||0} playoff (W15-17)</div><div class="rkflags">`;
  h+=rf.map(f=>`<div class="rkf s${f.sev}"><span class="cd">${esc(f.code)}</span>${esc(f.label)}${f.playoff?'<span class="po">PLAYOFF</span>':''}</div>`).join('');
  h+=`</div>`;
  if(p.avail!=null&&p.avail<1)h+=`<div class="qnote">Availability-adjusted projection <span class="adjpg">${p.adj_pg}</span> pts/g (${Math.round(p.avail*100)}% of ${(p.proj||{}).pg}) &mdash; projection position-rank ${p.proj_posrank} &rarr; <b>${p.adj_posrank}</b> (data-backed games-missed overlay).</div>`;
 }
 const qp=p.quant||{}; const ql=p.qual_profile||{};
 h+=`<div class="dlab">Quantitative profile</div><div class="qprof"><b>${esc(qp.archetype||"—")}</b>${qp.line?" &middot; "+esc(qp.line):""}</div>`;
 if((ql.traits&&ql.traits.length)||ql.claim||ql.note){
  h+=`<div class="dlab">Qualitative profile</div><div class="qprof">`;
  if(ql.traits&&ql.traits.length)h+=ql.traits.map(x=>`<span class="qtrait">${esc(x)}</span>`).join(" ");
  if(ql.claim)h+=`<div class="qclaim">Backtested claim: ${esc(ql.claim)}</div>`;
  if(ql.note)h+=`<div class="qnote">${esc(ql.note)}</div>`;
  h+=`</div>`;
 }
 const bb=p.bb||{};
 if((bb.boom&&bb.boom.length)||(bb.bust&&bb.bust.length)){
  h+=`<div class="dlab">Booms when / Busts when</div><div class="bbwrap">`;
  h+=`<div class="bbcol"><div class="bbh boom">&#9650; Booms when</div>`+(bb.boom||[]).map(x=>`<div class="bbi">${esc(x.t)}${x.c==='tendency'?'<span class="tend">tendency</span>':''}</div>`).join('')+`</div>`;
  h+=`<div class="bbcol"><div class="bbh bust">&#9660; Busts when</div>`+(bb.bust||[]).map(x=>`<div class="bbi">${esc(x.t)}${x.c==='tendency'?'<span class="tend">tendency</span>':''}</div>`).join('')+`</div></div>`;
 }
 const lv=p.levers||[];
 if(lv.length){
  h+=`<div class="dlab">Ceiling levers — matchup conditions that unlock a top week</div>`;
  h+=`<div class="levhint">a ceiling gets likely when several stack in one matchup; <span class="tend">tendency</span> = lower-confidence split</div><div class="levwrap">`;
  h+=lv.map(x=>`<div class="levi">${esc(x.t)}${x.c==="tendency"?' <span class="tend">tendency</span>':""}</div>`).join("");
  h+=`</div>`;
 }
  // matchup-lever calendar (tier-weighted per-week ceiling score vs 2026 schedule)
 const lc=p.lever_cal||[]; const ls=p.lever_sum||{};
 if(lc.length && ls.n_levers){
  h+=`<div class="dlab">Matchup-lever calendar &mdash; tier-weighted ceiling score by week (solid 1 / tendency 0.5 &times; how favorable the opponent is)</div>`;
  const mx=Math.max(1.5,...lc.map(c=>c.score));
  h+=`<div style="display:flex;gap:3px;align-items:flex-end;flex-wrap:wrap;margin:5px 0 7px">`+lc.map(c=>{const hh=Math.max(4,Math.round(44*c.score/mx)); const sm=c.score>=1.5; const col=sm?'var(--good)':(c.score>0?'var(--accent)':'var(--line2)'); return `<div title="W${c.wk} vs ${c.opp} &mdash; score ${c.score} [${c.active.map(a=>a.type+' '+a.i).join(', ')||'none'}]" style="width:27px;text-align:center;font-size:9px;color:var(--ink3);font-family:var(--mono)"><div style="height:${hh}px;background:${col};border-radius:2px;margin-bottom:2px;opacity:${c.score>0?1:.45}"></div>${c.wk}<br>${esc(c.opp)}</div>`;}).join('')+`</div>`;
  h+=`<div style="font-size:12px;color:var(--ink2);margin-bottom:4px">season mean <b>${ls.mean}</b> &middot; peak <b>${ls.peak}</b> &middot; playoff W15&ndash;17 mean <b style="color:var(--good)">${ls.playoff_mean}</b>${(ls.smash_weeks&&ls.smash_weeks.length)?` &middot; smash weeks <b style="color:var(--good)">${ls.smash_weeks.join(', ')}</b>`:''} <span style="color:var(--ink3)">(${ls.n_levers} levers)</span></div>`;
 }
 // projection & shape
 const pr=p.proj||{};
 h+=`<div class="dlab">Projection &amp; shape</div><div class="grid">`
  +kv('Proj pts/g',pr.pg)+kv('Ceiling p95',pr.ceiling)+kv('Volatility',pr.cv!=null?pr.cv:'',pr.cv!=null?'CV':'')
  +kv('Spike wk%',pr.spike!=null?pr.spike+'%':'')+kv('Advance %',pr.adv_pct!=null?pr.adv_pct:'',pr.adv_pct!=null?'pos pctl':'')
  +kv('Ceiling %',pr.ceil_pct!=null?pr.ceil_pct:'',pr.ceil_pct!=null?'pos pctl':'')+kv('Conviction',p.qual)+`</div>`;
 // playoff
 const pf=p.playoff||{};
 if(pf.w15_opp||pf.w17_game||pf.playoff_up!=null){
  h+=`<div class="dlab">Playoff outlook (W15–17)</div><div class="grid">`
   +kv('Playoff up',pf.playoff_up)+kv('W15',pf.w15_up,pf.w15_opp?'vs '+esc(pf.w15_opp):'')+kv('W16',pf.w16_up,pf.w16_opp?'vs '+esc(pf.w16_opp):'')
   +kv('W17',pf.w17_up,pf.w17_game?esc(pf.w17_game):'')+kv('W17 blowup',pf.blowup!=null&&pf.blowup<99?'#'+pf.blowup:'')+kv('Bye',pf.bye)+`</div>`;}
 // signals
 if((p.signals||[]).length){h+=`<div class="dlab">Signal breakdown (within-position pctl)</div>`;
  p.signals.forEach(g=>{h+=`<div class="siggrp"><div class="sgh">${esc(g.group)}</div><div class="sigrow">`
   +g.cells.map(c=>`<span class="sig"><span class="sl">${esc(c.label)}</span>${bar(c.pctl)}<span class="sv" style="color:${pcol(c.pctl)}">${c.pctl}</span></span>`).join('')+`</div></div>`;});}
 // upside notes
 if((p.upside||[]).length){h+=`<div class="dlab">Upside traits (model-driver vs descriptive)</div>`;
  p.upside.forEach(u=>{h+=`<div class="up"><span class="updim grp-${u.group}">${esc(u.dim)} ${u.pctl!=null?'· '+u.pctl:''}</span>`
   +`<span class="tier ${esc(u.stability||'')}">${esc(u.stability||'')}</span><span class="upnote">${esc(u.note||'')}</span></div>`;});}
 // backtests
 if((p.backtests||[]).length){h+=`<div class="dlab">Backtested claims</div>`;
  p.backtests.forEach(b=>{const vc=/STRONG/.test(b.verdict)?'S':(/MIX|PARTIAL|WEAK/i.test(b.verdict)?'M':(/NOT|REJECT|UNSUP/i.test(b.verdict)?'W':'M'));
   h+=`<div class="bt"><span class="verd ${vc}">${esc(b.verdict)}</span><b>${esc(b.dim)}</b>${b.by&&b.by.length?` <span class="muted">— @${b.by.map(esc).join(', @')}</span>`:''}<div class="muted" style="margin-top:2px">${esc(b.note||'')}</div></div>`;});}
 // matchup + intel
 if(pr.best_wk||pr.best_opp)h+=`<div class="dlab">Best matchup</div><div class="muted" style="font-size:12px">Week ${esc(pr.best_wk)} vs ${esc(pr.best_opp)}${pr.matchup!=null?` · matchup score ${pr.matchup}`:''}</div>`;
 if((p.about||[]).length){h+=`<div class="dlab">Intel (tweets about ${esc(lname(p.name))})</div>`
   +p.about.map(x=>`<div class="tw"><span class="h">@${esc(x.handle)} · ${esc(x.date)}</span><div class="tx">${esc(x.text)}</div></div>`).join('');}
 h+=`</div></div>`; return h;}
function dossier(t){const i=t.identity,d=t.defense;
 let h=`<div class="dh"><span class="ab">${t.team}</span><span class="nm">${esc(t.name)}</span><span class="dv">${esc(t.division)}</span></div>`;
 const lc=i.lean26==='PASS'?'pass':(i.lean26==='RUN'?'run':'');
 h+=`<div class="badges">`;
 if(i.lean26)h+=`<span class="badge ${lc}">Funnel: <b>${esc(i.lean26)}</b></span>`;
 if(i.shift)h+=`<span class="badge shift">&#9888; FLIPPED from ${esc(i.lean25)} '25</span>`;
 if(i.win_total!=null)h+=`<span class="badge">Win total <b>${i.win_total}</b></span>`;
 if(i.pace!=null)h+=`<span class="badge">Pace <b>${i.pace}</b>th</span>`;
 if(i.pass_rate!=null)h+=`<span class="badge">Pass <b>${i.pass_rate}%</b>${i.rk_passrate?` (#${Math.round(i.rk_passrate)})`:''}</span>`;
 const fr=t.flag_rollup||{};
 if(fr.total)h+=`<span class="badge" style="border-color:var(--bad);color:var(--bad)">&#9873; <b>${fr.total}</b> risk flags &middot; <span style="color:var(--warn)">&#9670;${fr.playoff} PO</span> &middot; ${fr.n_flagged} players</span>`;
 h+=`</div>`;
 h+=`<div class="sec">Identity &amp; coaching</div><div class="grid">`;
 h+=kv('Plays/g',i.plays!=null?(+i.plays).toFixed(1):'')+kv('Total TD/g',i.total_td!=null?(+i.total_td).toFixed(2):'',i.rk_td?'#'+Math.round(i.rk_td):'')+kv('Env idx',i.env)+kv('Off quality',i.off_q);
 h+=`</div>`;
 if(i.oc_new||i.dc_new){let c=[];if(i.oc_new)c.push(`New OC: <b>${esc(i.oc||'TBD')}</b>`);if(i.dc_new)c.push(`New DC: <b>${esc(i.dc||'TBD')}</b>${i.dc_scheme?` &mdash; ${esc(i.dc_scheme)}`:''}`);
   h+=`<div class="note">${c.join('<br>')}</div>`;}
 if(i.shift)h+=`<div class="note shiftnote">&#9888; Funnel FLIPPED 2025&rarr;2026 (${esc(i.lean25)}&rarr;${esc(i.lean26)}) &mdash; one of only 6 hard flips; re-learn it.</div>`;
 else if(i.soft_lean)h+=`<div class="note">2025 graded balanced; the 2026 engine now leans <b>${esc(i.lean26)}</b> (roster-adjusted) &mdash; a mild tilt.</div>`;
 if(t.note)h+=`<div class="note">${esc(t.note)}</div>`;
 const tp=t.profile||{};
 if(tp.strengths||tp.weaknesses){
  h+=`<div class="sec">Team profile &mdash; strengths &amp; weaknesses</div><div class="bbwrap">`;
  h+=`<div class="bbcol"><div class="bbh boom">Strengths</div>`+((tp.strengths||[]).length?tp.strengths.map(x=>`<div class="bbi">${esc(x)}</div>`).join(''):`<div class="bbi muted">&mdash; none flagged</div>`)+`</div>`;
  h+=`<div class="bbcol"><div class="bbh bust">Weaknesses</div>`+((tp.weaknesses||[]).length?tp.weaknesses.map(x=>`<div class="bbi">${esc(x)}</div>`).join(''):`<div class="bbi muted">&mdash; none flagged</div>`)+`</div></div>`;
  if((tp.off_boom||[]).length||(tp.off_bust||[]).length){
   h+=`<div class="bbwrap" style="margin-top:9px">`;
   h+=`<div class="bbcol"><div class="bbh boom">&#9650; Offense booms when</div>`+(tp.off_boom||[]).map(x=>`<div class="bbi">${esc(x)}</div>`).join('')+`</div>`;
   h+=`<div class="bbcol"><div class="bbh bust">&#9660; Offense busts when</div>`+(tp.off_bust||[]).map(x=>`<div class="bbi">${esc(x)}</div>`).join('')+`</div></div>`;
  }
 }
 // roster
 h+=`<div class="sec">Roster &mdash; full detail (${t.players.length})<span class="tools"><button class="tbtn" id="expall">Expand all</button><button class="tbtn" id="colall">Collapse</button></span></div>`;
 let lastpos=null;
 t.players.forEach(p=>{if(p.pos!==lastpos){h+=`<div class="posgrp">${esc(p.pos)}</div>`;lastpos=p.pos;}h+=playerCard(p);});
 // defense
 h+=`<div class="sec">Defense &amp; funnels (what opponents exploit)</div><div class="grid">`;
 h+=kv('Coverage',d.cov!=null?Math.round(d.cov):'','pctl')+kv('Pass rush',d.rush!=null?Math.round(d.rush):'','pctl')+kv('Run def',d.run!=null?Math.round(d.run):'','pctl');
 h+=`</div>`;
 if((i.funnels||[]).length)h+=`<div class="note">${i.funnels.map(esc).join(' &middot; ')}</div>`;
 if(d.cb1)h+=`<div class="pl"><span class="nm">CB1: ${esc(d.cb1.name)}</span><span class="mt">cov ${d.cb1.cov} (${esc(d.cb1.tier)}) &rarr; WR1 funnel: ${esc(d.cb1.wr1_funnel)}</span></div>`;
 if((d.rookies||[]).length)h+=`<div style="margin-top:6px"><span class="muted" style="font-size:11px">2026 D rookies: </span>`+d.rookies.map(r=>`<span class="chip" style="color:var(--ink2)">${esc(r.pl)} ${esc(r.pos)} ${esc(r.rd)}</span>`).join(' ')+`</div>`;
 if(t.stack){h+=`<div class="sec">Best-ball stack</div><div class="stk"><b>${esc(t.stack.qb)}</b> + ${t.stack.pieces.filter(p=>p!==t.stack.qb).map(esc).join(', ')}</div>`;}
 if((t.intel||[]).length){h+=`<div class="sec">Latest team intel</div>`+t.intel.map(x=>`<div class="tw"><span class="h">@${esc(x.handle)} &middot; ${esc(x.date)}</span><div class="tx">${esc(x.text)}</div></div>`).join('');}
 return h;}
function quiz(t){
 let h=`<div class="dh"><span class="ab">${t.team}</span><span class="nm">${esc(t.name)} &mdash; Challenge</span><span class="dv">${esc(t.division)}</span></div>`;
 h+=`<div class="qbar"><span class="muted">Test yourself, then reveal. </span><button class="qbtn" id="revall">Reveal all</button> <button class="qbtn" id="rndteam">Random team &#10227;</button></div><div class="qwrap">`;
 (t.quiz||[]).forEach((qz,i)=>{h+=`<div class="qcard"><div class="qq">${i+1}. ${esc(qz.q)}</div><div class="qa" id="qa${i}">${esc(qz.a)}</div><button class="qbtn" data-i="${i}">Reveal</button></div>`;});
 h+=`</div>`; return h;}
function show(){const t=sel?byTeam(sel):null;const pane=document.getElementById('pane');
 if(!t){pane.innerHTML='<div class="muted">Select a team.</div>';return;}
 pane.innerHTML = mode==='dossier'?dossier(t):quiz(t);
 if(mode==='dossier'){
   pane.querySelectorAll('.psum').forEach(s=>s.onclick=()=>s.parentElement.classList.toggle('open'));
   const ea=document.getElementById('expall'); if(ea)ea.onclick=()=>pane.querySelectorAll('.pc').forEach(c=>c.classList.add('open'));
   const ca=document.getElementById('colall'); if(ca)ca.onclick=()=>pane.querySelectorAll('.pc').forEach(c=>c.classList.remove('open'));
 } else {
   pane.querySelectorAll('.qbtn[data-i]').forEach(b=>b.onclick=()=>{const a=document.getElementById('qa'+b.dataset.i);a.classList.toggle('show');b.textContent=a.classList.contains('show')?'Hide':'Reveal';});
   const ra=document.getElementById('revall'); if(ra)ra.onclick=()=>pane.querySelectorAll('.qa').forEach(a=>a.classList.add('show'));
   const rt=document.getElementById('rndteam'); if(rt)rt.onclick=()=>{sel=T()[Math.floor(Math.random()*T().length)].team;nav(document.getElementById('q').value);show();};
 }}
document.getElementById('mD').onclick=()=>{mode='dossier';document.getElementById('mD').classList.add('on');document.getElementById('mQ').classList.remove('on');show();};
document.getElementById('mQ').onclick=()=>{mode='quiz';document.getElementById('mQ').classList.add('on');document.getElementById('mD').classList.remove('on');if(!sel)sel=T()[0].team;nav('');show();};
document.getElementById('q').oninput=e=>nav(e.target.value);
nav('');
</script></body></html>'''
HTML=HTML.replace('__DATA__',blob).replace('__N__',str(D['meta']['n'])).replace('__NP__',str(D['meta'].get('n_players',''))).replace('__BUILT__',built)
import ctx_panel; HTML=ctx_panel.inject(HTML)   # 4-layer NFL Pro EPA drilldown (click the EPA chip on a player card)
open(core.P('dossier.html'),'w',encoding='utf-8').write(HTML)
print("dossier.html written:",round(len(HTML)/1024),"KB")
