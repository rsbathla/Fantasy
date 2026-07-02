#!/usr/bin/env python3
"""Render dossier.html: clean, professional, team-by-team scouting dossier with FULL per-player
detail (expandable cards) + a Challenge (quiz) mode."""
import json, os, core, datetime
D=json.load(open(core.P('dossier_data.json')))
blob=json.dumps(D,ensure_ascii=False).replace('<','\\u003c')
built=datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
HTML=r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>2026 Team Dossiers</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
/* ---- Deep Enterprise Green system — DARK theme (green identity on near-black) ---- */
:root{--green:#003c33;--green2:#0a4d43;--mint:#4fd08a;
--canvas:#0a0f0d;--panel:#0b1210;--near:#eef2f5;
/* accent wash (was pale-green #edfce9) -> dark green tint */
--palegreen:rgba(79,208,138,.10);
--cardbg:#111a18;--cardbg2:#0f1815;--track:#0b1a16;
--hair:#22332e;--border:#1f2c28;--cardb:#1a2723;
--slate:#8ea3a0;--muted:#7a8f8b;
--coral:#ff7759;--softcoral:#ffad9b;--dcoral:#ff8f70;--blue:#5b9dff;
--disp:'Space Grotesk',Inter,ui-sans-serif,system-ui;--body:Inter,Arial,ui-sans-serif,system-ui;
--mono:'Space Grotesk',ui-monospace,Menlo,monospace;
/* legacy token aliases (JS + inline styles reference these) — bright mint for values/highlights */
--bg:var(--canvas);--bg2:var(--panel);--card:var(--cardbg);--card2:var(--cardbg2);
--line:var(--border);--line2:var(--hair);
--ink:#eef2f5;--ink2:var(--slate);--ink3:var(--muted);
--accent:var(--mint);--good:var(--mint);--warn:var(--coral);--bad:var(--coral)}
*{box-sizing:border-box}html,body{margin:0;height:100%}
body{background:var(--canvas);color:var(--ink);font:14px/1.55 var(--body);-webkit-font-smoothing:antialiased}
/* ---- deep green product band ---- */
.top{padding:0 20px;height:54px;background:var(--green);color:#fff;display:flex;gap:14px;align-items:center}
.top h1{font-family:var(--disp);font-size:16px;margin:0;letter-spacing:-.2px;font-weight:600;color:#fff;white-space:nowrap}
.top .sub{color:rgba(255,255,255,.62);font-size:10.5px;font-family:var(--mono);text-transform:uppercase;letter-spacing:.28px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.modes{margin-left:auto;display:flex;gap:8px}
.mbtn{font-size:12.5px;font-weight:500;padding:6px 16px;border:1px solid rgba(255,255,255,.35);border-radius:30px;cursor:pointer;color:rgba(255,255,255,.8);background:transparent;font-family:var(--body);transition:.12s}
.mbtn:hover{border-color:#fff;color:#fff}
.mbtn.on{background:#fff;color:var(--green);border-color:#fff;font-weight:600}
.wrap{display:grid;grid-template-columns:224px 1fr;height:calc(100vh - 54px)}
/* ---- team nav ---- */
.nav{border-right:1px solid var(--border);overflow:auto;background:var(--panel);padding:6px 0}
.navsrch{padding:10px 10px 6px}.navsrch input{width:100%;background:var(--cardbg);color:var(--ink);border:1px solid var(--hair);border-radius:8px;padding:7px 10px;font-size:12.5px;font-family:var(--body);outline:none}
.navsrch input::placeholder{color:var(--muted)}
.navsrch input:focus{border-color:var(--mint)}
.divh{font-family:var(--mono);font-size:9.5px;text-transform:uppercase;letter-spacing:1px;color:var(--muted);font-weight:600;padding:12px 14px 4px}
.trow{padding:6px 14px;cursor:pointer;font-size:13px;display:flex;justify-content:space-between;align-items:center;border-left:2px solid transparent}
.trow:hover{background:rgba(79,208,138,.06)}.trow.sel{background:var(--palegreen);border-left-color:var(--mint)}
.trow .ab{font-family:var(--mono);font-weight:600;letter-spacing:.28px;color:var(--near)}.trow .nm{color:var(--muted);font-size:11px}
.pane{overflow:auto;padding:28px 34px 64px;max-width:1060px}
/* ---- team header ---- */
.dh{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;border-bottom:1px solid var(--border);padding-bottom:14px;margin-bottom:6px}
.dh .ab{font-family:var(--disp);font-size:44px;font-weight:500;letter-spacing:-1.2px;line-height:1;color:var(--near)}
.dh .nm{font-family:var(--disp);font-size:18px;letter-spacing:-.2px;color:var(--slate)}
.dh .dv{font-family:var(--mono);font-size:10.5px;text-transform:uppercase;letter-spacing:.6px;color:var(--muted);margin-left:auto}
.badges{display:flex;gap:8px;flex-wrap:wrap;margin:16px 0}
.badge{border:1px solid var(--hair);border-radius:30px;padding:5px 13px;font-size:12.5px;background:var(--cardbg);color:var(--ink)}
.badge b{font-family:var(--mono);letter-spacing:.28px}
.badge.pass{border-color:rgba(91,157,255,.45);color:var(--blue)}.badge.run{border-color:rgba(79,208,138,.4);color:var(--mint)}
.badge.shift{border-color:var(--softcoral);color:var(--dcoral)}
.sec{margin:26px 0 8px;font-family:var(--mono);font-size:11px;text-transform:uppercase;letter-spacing:1.1px;color:var(--mint);font-weight:600;border-bottom:1px solid var(--border);padding-bottom:6px;display:flex;justify-content:space-between;align-items:center}
.sec .tools{font-weight:500;letter-spacing:0;text-transform:none}
.tbtn{font-size:11.5px;color:var(--ink);background:var(--cardbg);border:1px solid var(--hair);border-radius:30px;padding:4px 12px;cursor:pointer;margin-left:6px;font-family:var(--body)}
.tbtn:hover{border-color:var(--mint);color:var(--mint)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(118px,1fr));gap:9px;margin:10px 0}
.kv{background:var(--cardbg);border:1px solid var(--border);border-radius:12px;padding:9px 12px}
.kv .k{font-family:var(--mono);font-size:9px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);font-weight:600}
.kv .v{font-size:17px;font-weight:600;font-family:var(--disp);letter-spacing:-.3px;margin-top:2px;color:var(--near)}.kv .v small{font-size:10px;color:var(--muted);font-weight:500}
.note{font-size:13px;color:var(--ink);background:var(--palegreen);border-left:3px solid var(--mint);padding:10px 13px;border-radius:8px;margin:8px 0}
.shiftnote{background:rgba(255,119,89,.08);border-left-color:var(--coral);color:var(--dcoral)}
.posgrp{margin:16px 0 4px;font-family:var(--mono);font-size:11px;font-weight:600;color:var(--mint);letter-spacing:.6px;text-transform:uppercase}
/* player card */
.pc{background:var(--cardbg2);border:1px solid var(--border);border-radius:16px;margin:8px 0;overflow:hidden}
.psum{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:11px 15px;cursor:pointer}
.psum:hover{background:rgba(79,208,138,.05)}
.prk{font-family:var(--mono);font-size:12px;color:var(--muted);min-width:34px}
.pnm{font-family:var(--disp);font-weight:500;font-size:15.5px;letter-spacing:-.2px;min-width:150px;color:var(--near)}
.ppos{font-family:var(--mono);font-size:9.5px;font-weight:600;text-transform:uppercase;letter-spacing:.3px;border:1px solid var(--hair);border-radius:4px;padding:1px 5px;color:var(--slate)}
.pmeta{font-family:var(--mono);font-size:11.5px;color:var(--muted)}
.edge{font-family:var(--mono);font-size:11.5px;font-weight:600}.edge.up{color:var(--mint)}.edge.dn{color:var(--dcoral)}
.cons{display:flex;align-items:center;gap:6px;margin-left:auto}
.consbar{width:74px;height:6px;border-radius:9999px;background:var(--track);overflow:hidden}
.consbar i{display:block;height:100%}
.consv{font-family:var(--mono);font-size:11.5px;font-weight:600}
.exp{color:var(--muted);font-size:12px;font-family:var(--mono)}
.pflags{display:flex;gap:5px;flex-wrap:wrap;width:100%;margin-top:2px}
.fchip{font-family:var(--mono);font-size:9.5px;font-weight:600;text-transform:uppercase;letter-spacing:.3px;border:1px solid var(--hair);border-radius:5px;padding:1px 6px;color:var(--slate);background:var(--cardbg)}
.risksum{font-size:11px;font-weight:600;font-family:var(--mono);border:1px solid rgba(255,119,89,.5);border-radius:6px;padding:1px 7px;color:var(--dcoral);margin-left:6px;background:rgba(255,119,89,.08)}
.risksum .po{color:var(--coral)}
.rkflags{display:flex;flex-direction:column;gap:4px;margin:4px 0}
.rkf{font-size:11.5px;padding:4px 9px;border-radius:6px;border-left:3px solid var(--hair);background:rgba(255,119,89,.08);color:var(--ink)}
.rkf.s3{border-left-color:var(--dcoral)}.rkf.s2{border-left-color:var(--coral)}.rkf.s1{border-left-color:var(--hair)}
.rkf .po{font-family:var(--mono);font-size:9px;font-weight:600;color:var(--dcoral);border:1px solid var(--softcoral);border-radius:4px;padding:0 4px;margin-left:6px}
.rkf .cd{font-family:var(--mono);font-weight:600;color:var(--near);margin-right:6px}
.adjpg{color:var(--dcoral);font-weight:700}
.pdetail{display:none;border-top:1px solid var(--border);padding:13px 15px 16px;background:#0c1512}
.pc.open .pdetail{display:block}.pc.open .exp{color:var(--mint)}
.dlab{font-family:var(--mono);font-size:9.5px;text-transform:uppercase;letter-spacing:.7px;color:var(--muted);font-weight:600;margin:14px 0 6px}
.dlab:first-child{margin-top:0}
.siggrp{margin:6px 0}
.sgh{font-family:var(--mono);font-size:10px;color:var(--slate);font-weight:600;margin:6px 0 3px;text-transform:uppercase;letter-spacing:.4px}
.sigrow{display:grid;grid-template-columns:repeat(auto-fill,minmax(168px,1fr));gap:5px 14px}
.sig{display:flex;align-items:center;gap:7px;font-size:11.5px}
.sl{color:var(--slate);min-width:78px}.sb{flex:1;height:6px;border-radius:9999px;background:var(--track);overflow:hidden}
.sb i{display:block;height:100%}.sv{font-family:var(--mono);font-size:11px;min-width:20px;text-align:right;color:var(--slate)}
.uprow{border-top:1px solid var(--cardb);padding:6px 0;font-size:12px;display:flex;gap:8px;flex-wrap:wrap;align-items:baseline}
.uprow:first-of-type{border-top:none}.updim{font-weight:600;font-family:var(--mono);min-width:84px}
.tier{font-family:var(--mono);font-size:9px;font-weight:600;text-transform:uppercase;letter-spacing:.3px;border-radius:4px;padding:1px 5px;border:1px solid var(--hair);color:var(--slate)}
.tier.STABLE{color:var(--mint);border-color:rgba(79,208,138,.4)}.tier.MODERATE{color:var(--blue);border-color:rgba(91,157,255,.4)}
.tier.LOW,.tier.NOISE,.tier.LEVEL-ONLY{color:var(--muted)}
.upnote{color:var(--slate);font-size:11.5px;flex:1;min-width:200px}
.bt{border-top:1px solid var(--cardb);padding:6px 0;font-size:12px}
.verd{font-family:var(--mono);font-size:9.5px;font-weight:600;text-transform:uppercase;letter-spacing:.3px;border-radius:4px;padding:1px 6px;margin-right:6px}
.verd.S{color:var(--mint);border:1px solid rgba(79,208,138,.4)}.verd.M{color:var(--dcoral);border:1px solid rgba(255,143,112,.5)}.verd.W{color:var(--dcoral);border:1px solid var(--coral)}
.grp-model{color:var(--mint)}.grp-off{color:var(--muted)}
.tw{border-top:1px solid var(--cardb);padding:8px 0;font-size:12px}.tw:first-of-type{border-top:none}
.tw .h{color:var(--muted);font-family:var(--mono);font-size:10.5px;text-transform:uppercase;letter-spacing:.4px}.tw .tx{color:var(--ink);margin-top:2px;white-space:pre-wrap}
.pl{display:flex;gap:9px;align-items:baseline;flex-wrap:wrap;padding:7px 0;border-top:1px solid var(--cardb)}
.pl:first-of-type{border-top:none}.pl .nm{font-weight:600;min-width:155px;color:var(--near)}.pl .mt{font-family:var(--mono);font-size:11.5px;color:var(--muted)}
.chip{font-size:11px;font-weight:500;border:1px solid var(--hair);border-radius:8px;padding:2px 9px;color:var(--ink);background:var(--cardbg)}
.stk{font-size:15px;font-family:var(--disp);letter-spacing:-.2px}.stk b{color:var(--mint)}
.qwrap{max-width:760px}
.qcard{background:var(--cardbg);border:1px solid var(--border);border-radius:16px;padding:17px 19px;margin:14px 0}
.qq{font-family:var(--disp);font-size:15.5px;font-weight:600;letter-spacing:-.2px;color:var(--near)}
.qa{margin-top:10px;font-size:14px;color:var(--mint);display:none;background:var(--palegreen);border-left:3px solid var(--mint);border-radius:8px;padding:8px 11px}.qa.show{display:block}
.qbtn{margin-top:10px;font-size:12.5px;font-weight:500;color:var(--ink);background:var(--cardbg);border:1px solid var(--hair);border-radius:30px;padding:6px 14px;cursor:pointer;font-family:var(--body)}
.qbtn:hover{border-color:var(--mint);color:var(--mint)}
.qbar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:6px}
.muted{color:var(--muted)}
.levwrap{margin:6px 0}
.levi{font-size:12.5px;color:var(--ink);padding:7px 11px;border-left:3px solid var(--mint);margin:5px 0;background:var(--palegreen);border-radius:0 8px 8px 0}
.levhint{font-size:11px;color:var(--muted);margin:2px 0 6px}

.qprof{font-size:12.5px;color:var(--ink);margin:2px 0 6px}
.qprof b{color:var(--near)}
.qtrait{display:inline-block;font-family:var(--mono);font-size:10.5px;font-weight:600;text-transform:uppercase;letter-spacing:.3px;border:1px solid rgba(79,208,138,.35);border-radius:5px;padding:1px 7px;margin:2px 4px 2px 0;color:var(--mint);background:var(--palegreen)}
.qclaim{font-size:11.5px;color:var(--mint);margin-top:5px}
.qnote{font-size:11px;color:var(--slate);margin-top:3px}

.bbwrap{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:9px 0}
.bbcol{background:var(--cardbg);border:1px solid var(--border);border-radius:12px;padding:10px 13px}
.bbh{font-family:var(--mono);font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.6px;margin-bottom:5px}
.bbh.boom{color:var(--mint)}.bbh.bust{color:var(--dcoral)}
.bbi{font-size:12px;color:var(--ink);padding:4px 0;border-top:1px solid var(--cardb)}
.bbi:first-of-type{border-top:none}
.tend{font-family:var(--mono);font-size:9px;font-weight:600;text-transform:uppercase;color:var(--muted);border:1px solid var(--hair);border-radius:4px;padding:0 4px;margin-left:6px}
@media(max-width:760px){.bbwrap{grid-template-columns:1fr}}

/* ---- shared ctx (EPA drilldown) panel, re-themed to the DARK green system.
       ctx_panel.css() is injected AFTER this block; `body ` prefix out-specifies it. ---- */
body .ctx-injected>td{background:var(--panel)}
body .ctxwrap{background:var(--palegreen);border-top:1px solid rgba(79,208,138,.3);border-bottom:2px solid var(--mint);border-radius:12px}
body .ctxcard{background:var(--cardbg);border:1px solid var(--border);border-radius:12px;color:var(--ink);font:12px/1.5 var(--body)}
body .ctxcard h5{color:var(--mint)}
body .ctxcard h5 .ln{background:var(--palegreen);border:1px solid rgba(79,208,138,.25);color:var(--mint)}
body .ctxkv{border-bottom:1px dashed var(--cardb)}
body .ctxkv .k{color:var(--muted)}body .ctxkv .v{color:var(--ink)}
body .ctxkv .v.g{color:var(--mint)}body .ctxkv .v.b{color:var(--dcoral)}body .ctxkv .v.w{color:var(--coral)}
body .ctxdial.up{background:rgba(79,208,138,.14);color:var(--mint)}
body .ctxdial.dn{background:rgba(255,119,89,.14);color:var(--dcoral)}
body .ctxdial.nz{background:var(--cardb);color:var(--muted)}
body .ctxyoy{border-top:1px solid var(--cardb)}
body .ctxnote{color:var(--slate)}body .ctxempty{color:var(--muted)}
body .ctxcue{color:var(--mint);background:rgba(79,208,138,.14)}
body .ctxchip{color:var(--mint);background:var(--palegreen);border:1px solid rgba(79,208,138,.32)}
body .ctxchip:hover,body .ctxchip.ctx-open{background:rgba(79,208,138,.22);color:var(--mint)}
body .ctx-injected{margin:2px 0 8px}

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
const pcol=v=>v==null?'var(--ink3)':(v>=80?'var(--mint)':v>=60?'#3fa876':v>=40?'var(--slate)':v>=20?'var(--coral)':'var(--dcoral)');
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
 // scheme fit — coverage-specialist skill (2yr charting) × the 2026 opponents' coverage tendencies
 const sf=p.schemefit;
 if(sf&&(sf.season!=null)){
  const sgn=v=>v==null?'—':(v>0?'+':'')+v.toFixed(3);
  const sfc=v=>v==null?'var(--muted)':(v>=0.01?'var(--mint)':v<=-0.01?'var(--dcoral)':'var(--slate)');
  const ord=n=>{n=Math.round(n);const m=n%100;return n+((m>=11&&m<=13)?'th':({1:'st',2:'nd',3:'rd'}[n%10]||'th'));};
  h+=`<div class="dlab">Scheme fit — his coverage specialties vs the 2026 slate</div>`;
  let ch='';
  (sf.elite||[]).forEach(e=>{ch+=`<span class="qtrait" title="${e.rte} routes, ${e.yprr} YPRR">ELITE vs ${esc(e.key)} · ${ord(e.pctl)}</span> `;});
  (sf.weak||[]).forEach(e=>{ch+=`<span class="qtrait" style="color:var(--dcoral);border-color:rgba(255,119,89,.4);background:rgba(255,119,89,.08)" title="${e.rte} routes, ${e.yprr} YPRR">WEAK vs ${esc(e.key)} · ${ord(e.pctl)}</span> `;});
  if(ch)h+=`<div class="qprof">${ch}</div>`;
  const bl=Object.entries(sf.buckets||{}).map(([b,d])=>`${b.replace('_','-')} <b style="color:${pcol(d.pctl)}">${Math.round(d.pctl)}</b>`).join(' · ');
  if(bl)h+=`<div class="qnote">coverage profile (2yr YPRR pctl within position): ${bl}</div>`;
  h+=`<div style="font-size:12px;color:var(--ink2);margin:5px 0 3px">season scheme fit <b style="color:${sfc(sf.season)}">${sgn(sf.season)}</b> &middot; playoff W15–17 <b style="color:${sfc(sf.playoff)}">${sgn(sf.playoff)}</b> <span style="color:var(--ink3)">(+ = his strengths meet coverages the opponent runs a lot)</span></div>`;
  (sf.best||[]).forEach(w=>{h+=`<div class="levi">&#9650; best: W${w.wk} vs ${esc(w.opp)} <b style="color:var(--mint)">${sgn(w.fit)}</b> — ${esc(w.why||'')}${w.nd?' <span class="tend" title="new 2026 DC — 2025 tendency half-weighted">new DC</span>':''}</div>`;});
  (sf.worst||[]).forEach(w=>{h+=`<div class="levi" style="border-left-color:var(--coral);background:rgba(255,119,89,.07)">&#9660; worst: W${w.wk} vs ${esc(w.opp)} <b style="color:var(--dcoral)">${sgn(w.fit)}</b> — ${esc(w.why||'')}${w.nd?' <span class="tend" title="new 2026 DC — 2025 tendency half-weighted">new DC</span>':''}</div>`;});
  if((sf.po||[]).length)h+=`<div class="qnote">playoff weeks: ${sf.po.map(w=>`W${w.wk} ${esc(w.opp)} <b style="color:${sfc(w.fit)}">${sgn(w.fit)}</b>`).join(' &middot; ')}</div>`;
 }
  // matchup-lever calendar (tier-weighted per-week ceiling score vs 2026 schedule)
 const lc=p.lever_cal||[]; const ls=p.lever_sum||{};
 if(lc.length && ls.n_levers){
  h+=`<div class="dlab">Matchup-lever calendar &mdash; tier-weighted ceiling score by week (solid 1 / tendency 0.5 &times; how favorable the opponent is)</div>`;
  const mx=Math.max(1.5,...lc.map(c=>c.score));
  h+=`<div style="display:flex;gap:3px;align-items:flex-end;flex-wrap:wrap;margin:5px 0 7px">`+lc.map(c=>{const hh=Math.max(4,Math.round(44*c.score/mx)); const sm=c.score>=1.5; const col=sm?'var(--mint)':(c.score>0?'#3fa876':'var(--hair)'); return `<div title="W${c.wk} vs ${c.opp} &mdash; score ${c.score} [${c.active.map(a=>a.type+' '+a.i).join(', ')||'none'}]" style="width:27px;text-align:center;font-size:9px;color:var(--ink3);font-family:var(--mono)"><div style="height:${hh}px;background:${col};border-radius:2px;margin-bottom:2px;opacity:${c.score>0?1:.45}"></div>${c.wk}<br>${esc(c.opp)}</div>`;}).join('')+`</div>`;
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
  p.upside.forEach(u=>{h+=`<div class="uprow"><span class="updim grp-${u.group}">${esc(u.dim)} ${u.pctl!=null?'· '+u.pctl:''}</span>`
   +`<span class="tier ${esc(u.stability||'')}">${esc(u.stability||'')}</span><span class="upnote">${esc(u.note||'')}</span></div>`;});}
 // backtests
 if((p.backtests||[]).length){h+=`<div class="dlab">Backtested claims</div>`;
  p.backtests.forEach(b=>{const vc=/STRONG/.test(b.verdict)?'S':(/MIX|PARTIAL|WEAK/i.test(b.verdict)?'M':(/NOT|REJECT|UNSUP/i.test(b.verdict)?'W':'M'));
   h+=`<div class="bt"><span class="verd ${vc}">${esc(b.verdict)}</span><b>${esc(b.dim)}</b>${b.by&&b.by.length?` <span class="muted">— @${b.by.map(esc).join(', @')}</span>`:''}<div class="muted" style="margin-top:2px">${esc(b.note||'')}</div></div>`;});}
 // matchup + intel
 if(pr.best_wk||pr.best_opp)h+=`<div class="dlab">Best matchup</div><div class="muted" style="font-size:12px">Week ${esc(pr.best_wk)} vs ${esc(pr.best_opp)}${pr.matchup!=null?` · matchup score ${pr.matchup}`:''}</div>`;
 if((p.about||[]).length){h+=`<div class="dlab">Intel (tweets about ${esc(lname(p.name))})</div>`
   +p.about.map(x=>`<div class="tw"><span class="h">@${esc(x.handle)} · ${esc(x.date)}</span><div class="tx">${esc(x.text)}</div></div>`).join('');}
 // situational profile — where they win (PFF/FTN: man/zone, deep/short, YPRR)
 if(p.situations&&Object.keys(p.situations).length){h+=`<div class="dlab">Situational profile — where they win (percentile vs position)</div>`;
  Object.values(p.situations).forEach(s=>{if(s&&s.pct!=null)h+=`<span class="sig"><span class="sl">${esc(s.metric||'')}</span>${bar(s.pct)}<span class="sv" style="color:${pcol(s.pct)}">${Math.round(s.pct)}</span>${s.n?`<small class="muted"> (n=${Math.round(s.n)})</small>`:''}</span>`;});}
 // year-over-year trend (2024 -> 2025)
 if(p.trend&&p.trend.y2025!=null){const dd=p.trend.delta;const tc=dd>0?'var(--good)':(dd<0?'var(--bad)':'var(--ink2)');
  h+=`<div class="dlab">Trend (2024 → 2025)</div><div class="muted" style="font-size:12px">${esc(p.trend.metric||'')}: ${p.trend.y2024} → <b>${p.trend.y2025}</b> <span style="color:${tc}">(${dd>0?'+':''}${dd})</span></div>`;}
 // college production profile (recent college seasons; naturally shows for rookies / young players)
 if(p.rookie_college||p.rookie_prior){const rc=p.rookie_college||{},rp=p.rookie_prior||{};
  const cp=rc.ceiling_pctl_2025!=null?rc.ceiling_pctl_2025:rc.ceiling_pctl_2024;
  const cy=rc.ceiling_pctl_2025!=null?'':' (2024)';
  const bits=[];
  if(rc.college)bits.push(esc(rc.college));
  if(cp!=null)bits.push(`college ceiling <b>${Math.round(cp)}</b> pctl${cy}`);
  if(rp.boom_prior!=null)bits.push(`2026 rookie boom prior <b>${(rp.boom_prior*100).toFixed(0)}%</b>`);
  if(bits.length)h+=`<div class="dlab">College production</div><div class="muted" style="font-size:12px">${bits.join(' · ')}</div>`;}
 h+=`</div></div>`; return h;}
function dossier(t){const i=t.identity,d=t.defense;
 let h=`<div class="dh"><span class="ab">${t.team}</span><span class="nm">${esc(t.name)}</span><span class="dv">${esc(t.division)}</span></div>`;
 const lc=i.lean26==='PASS'?'pass':(i.lean26==='RUN'?'run':'');
 h+=`<div class="badges">`;
 if(i.lean26)h+=`<span class="badge ${lc}">Funnel: <b>${esc(i.lean26)}</b></span>`;
 if(i.shift)h+=`<span class="badge shift">&#9888; FLIPPED from ${esc(i.lean25)} '25</span>`;
 if(i.win_total!=null)h+=`<span class="badge">Win total <b>${i.win_total}</b></span>`;
 if(i.pace!=null)h+=`<span class="badge">Pace <b>${i.pace}</b> pctl</span>`;
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
 // CEILING & STACKS panel
 const cl=t.ceiling,sk=t.stacks;
 if(cl||sk){
  h+=`<div class="sec">Ceiling &amp; Stacks</div>`;
  if(cl){
   const tcol=cl.tier==='ELITE'?'var(--mint)':cl.tier==='HIGH'?'#3fa876':cl.tier==='MID'?'var(--slate)':'var(--coral)';
   const tbg=cl.tier==='ELITE'?'rgba(79,208,138,.15)':cl.tier==='HIGH'?'rgba(63,168,118,.12)':cl.tier==='MID'?'rgba(142,163,160,.10)':'rgba(255,119,89,.12)';
   h+=`<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:8px 0">`;
   h+=`<span style="font-family:var(--mono);font-size:13px;font-weight:700;padding:4px 14px;border-radius:20px;border:1px solid ${tcol};color:${tcol};background:${tbg}">${esc(cl.tier)}</span>`;
   h+=`<span class="badge">Score <b>${cl.score!=null?cl.score.toFixed(1):'—'}</b></span>`;
   h+=`<span class="badge">Rank <b>#${cl.rank!=null?cl.rank:'—'}</b> of 32</span>`;
   h+=`</div>`;
   if((cl.top_drivers||[]).length){
    h+=`<div style="display:flex;gap:6px;flex-wrap:wrap;margin:4px 0 8px">`;
    h+=(cl.top_drivers||[]).map(d=>`<span class="chip" style="color:var(--mint);border-color:rgba(79,208,138,.3)">${esc(d.label)} <b>${d.value}%</b></span>`).join('');
    h+=`</div>`;
   }
   if((cl.fade_flags||[]).length){
    h+=`<div style="font-size:11.5px;color:var(--ink2);margin:2px 0 6px">${cl.fade_flags.map(esc).join(' &middot; ')}</div>`;
   }
  }
  if(sk){
   if((sk.best_stacks||[]).length){
    h+=`<div class="dlab">Best draftable stacks</div>`;
    (sk.best_stacks||[]).forEach(s=>{
     const pcs=s.pieces||[];
     const rounds=(s.round_costs||[]).map(r=>`R${r}`).join('+');
     const val=s.value_ct!=null&&s.stack_type?`${esc(s.stack_type)} · value ${s.value_ct}/${(s.round_costs||[]).length}`:'';
     h+=`<div class="pl"><span class="nm"><b style="color:var(--mint)">${esc(s.qb||'?')}</b>${pcs.length?' + '+pcs.map(esc).join(' + '):''}</span>`;
     h+=`<span class="mt">${rounds}${s.qb_late?' · late QB':''}</span>`;
     if(val)h+=`<span class="chip">${val}</span>`;
     if(s.stack_score!=null)h+=`<span class="chip" style="color:var(--mint)">&#9650; ${s.stack_score.toFixed(3)}</span>`;
     h+=`</div>`;
    });
   }
   if(sk.w17_opp||sk.bringback){
    h+=`<div class="dlab">W17 game &amp; bring-backs</div>`;
    if(sk.w17_opp)h+=`<div style="font-size:12.5px;color:var(--ink);margin:3px 0">vs <b>${esc(sk.w17_opp)}</b>${sk.w17_game_env!=null?` &middot; game env <b style="color:var(--mint)">${sk.w17_game_env.toFixed(1)}</b>`:''}</div>`;
    if((sk.bringback||[]).length)h+=`<div style="font-size:12px;color:var(--ink2);margin:3px 0">Bring-backs: ${sk.bringback.map(esc).join(' &middot; ')}</div>`;
   }
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
