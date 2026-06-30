#!/usr/bin/env python3
"""Render standalone intel.html (data embedded) — Players + Teams modes."""
import json, os, core, datetime
D=json.load(open(core.P('intel_data.json')))
blob=json.dumps(D,ensure_ascii=False).replace('<','\\u003c')
built=datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
HTML=r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Intel</title><style>
:root{--bg:#0a0e16;--bg2:#0c1320;--panel:#111a2b;--line:#1d2a40;--line2:#26354f;--ink:#e9eef7;--ink2:#aebbd0;--ink3:#7488a6;--accent:#5b9dff;--good:#5fd08a;--warn:#e0b25c;--bad:#ff8c8c;--mono:ui-monospace,Menlo,Consolas,monospace}
*{box-sizing:border-box}html,body{margin:0;height:100%}body{background:var(--bg);color:var(--ink);font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}
.top{padding:9px 16px;border-bottom:1px solid var(--line);display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.top h1{font-size:16px;margin:0}.top .sub{color:var(--ink3);font-size:12px;font-family:var(--mono);margin-left:auto}
.mode{display:flex;gap:5px}.mbtn{font-size:12px;font-weight:700;padding:4px 12px;border:1px solid var(--line2);border-radius:7px;cursor:pointer;color:var(--ink2)}.mbtn.on{background:var(--accent);color:#0a0e16;border-color:var(--accent)}
.wrap{display:grid;grid-template-columns:270px 1fr;height:calc(100vh - 44px)}
.list{border-right:1px solid var(--line);overflow:auto;background:var(--bg2)}
.search{position:sticky;top:0;background:var(--bg2);padding:9px;border-bottom:1px solid var(--line)}
.search input{width:100%;background:#0c1320;color:var(--ink);border:1px solid var(--line2);border-radius:8px;padding:8px 10px;font-size:13px}
.prow{padding:7px 11px;border-bottom:1px solid var(--line);cursor:pointer;display:flex;justify-content:space-between;gap:6px;align-items:baseline}
.prow:hover{background:rgba(91,157,255,.08)}.prow.sel{background:rgba(91,157,255,.16)}
.prow .pn{font-weight:600;font-size:13px}.prow .pp{color:var(--ink3);font-size:10.5px;font-family:var(--mono)}.prow .tn{font-family:var(--mono);font-size:10px;color:var(--accent)}
.detail{overflow:auto;padding:16px 20px}
.dh{font-size:22px;font-weight:800}.dh .m{color:var(--ink3);font-family:var(--mono);font-size:13px;font-weight:400;margin-left:8px}
.reads{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}
.kv{background:linear-gradient(180deg,var(--panel),var(--bg2));border:1px solid var(--line);border-radius:9px;padding:6px 10px;min-width:70px}
.kv .k{font-size:9px;text-transform:uppercase;letter-spacing:.5px;color:var(--ink3);font-weight:700}.kv .v{font-size:15px;font-weight:800;font-family:var(--mono)}.kv .v small{font-size:10px;color:var(--ink3)}
.bl{font-size:10.5px;text-transform:uppercase;letter-spacing:.8px;color:var(--ink3);font-weight:700;margin:15px 0 7px}
.sub2{font-size:11px;color:var(--ink3);font-weight:600;margin:8px 0 5px}
.up{display:flex;gap:7px;flex-wrap:wrap}
.upc{border-radius:7px;padding:4px 9px;font-size:12px;font-weight:700;border:1px solid}.upM{background:rgba(95,208,138,.10);border-color:rgba(95,208,138,.5);color:var(--good)}.upO{background:rgba(224,178,92,.08);border-color:rgba(224,178,92,.4);color:var(--warn)}
.upc .pp{font-family:var(--mono);font-weight:800}.upc .st{font-size:9.5px;color:var(--ink3);margin-left:3px}
.note{font-size:13px;color:var(--ink2);background:rgba(91,157,255,.06);border-left:3px solid var(--accent);padding:8px 11px;border-radius:6px;margin:8px 0}
.shift{color:#0a0e16;background:var(--warn);font-size:10px;font-weight:800;border-radius:4px;padding:1px 6px}
.bt{display:grid;grid-template-columns:120px 1fr;gap:9px;align-items:start;border-top:1px solid var(--line2);padding:7px 0}
.bt .vd{font-size:10.5px;font-weight:800;border-radius:5px;padding:3px 6px;text-align:center;height:fit-content}
.vSUP{background:var(--good);color:#0a0e16}.vMIX{background:var(--warn);color:#0a0e16}.vNOT{background:var(--bad);color:#0a0e16}.vUNT{background:#2a3850;color:var(--ink2)}
.bt .dim{font-weight:700;text-transform:capitalize}.bt .meta{font-size:11px;color:var(--ink3);font-family:var(--mono)}.bt .stab{font-size:11px;color:var(--ink2)}.bt .by{font-size:10.5px;color:var(--ink3)}
.tabs{display:flex;gap:6px;margin:14px 0 4px}.tab{font-size:12px;font-weight:700;padding:4px 11px;border:1px solid var(--line2);border-radius:7px;cursor:pointer;color:var(--ink2)}.tab.on{background:var(--accent);color:#0a0e16;border-color:var(--accent)}
.pchip{display:inline-block;font-size:11.5px;border:1px solid var(--line2);border-radius:6px;padding:2px 8px;margin:2px 4px 2px 0;cursor:pointer;color:var(--ink2)}.pchip:hover{border-color:var(--accent);color:var(--ink)}.pchip .pp{font-family:var(--mono);color:var(--ink3);font-size:10px}
.rk{display:inline-block;font-size:11px;background:#1f2733;border-radius:3px;padding:1px 6px;margin:2px 5px 2px 0;font-family:var(--mono)}
.tw{border-top:1px solid var(--line2);padding:9px 0}.tw.ins{border-left:3px solid var(--accent);padding-left:10px;background:rgba(91,157,255,.04)}
.tw .h{display:flex;gap:8px;align-items:baseline;flex-wrap:wrap;font-size:12px}.tw .hd{font-weight:700;color:var(--ink)}.tw .rn{color:var(--ink3)}.tw .mt{color:var(--ink3);font-family:var(--mono);font-size:11px;margin-left:auto}
.tw .tx{font-size:13px;color:var(--ink2);white-space:pre-wrap;margin-top:3px}.tw a{color:var(--accent);text-decoration:none;font-size:11px}
.insb{font-size:9px;font-weight:800;background:var(--accent);color:#0a0e16;border-radius:3px;padding:0 5px}
.tier{font-size:9px;font-weight:800;border-radius:3px;padding:0 4px}.tA{background:var(--good);color:#0a0e16}.tB{background:var(--warn);color:#0a0e16}.tC{background:#2a3850;color:var(--ink2)}
.muted{color:var(--ink3)}
</style></head><body>
<div class="top"><h1>Intel</h1><div class="mode"><span class="mbtn on" id="mP">Players</span><span class="mbtn" id="mT">Teams</span></div><span class="sub">__N__ players · __NT__ teams · built __BUILT__</span></div>
<div class="wrap"><div class="list"><div class="search"><input id="q" placeholder="search"></div><div id="plist"></div></div><div class="detail" id="detail"><div class="muted">Select.</div></div></div>
<script>
const D=__DATA__; let mode='players',sel=null,tw='about';
const esc=s=>(s==null?'':String(s)).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const vcl=v=>v&&v.indexOf('SUPPORTED')>=0?'vSUP':(v==='MIXED'?'vMIX':(v==='NOT SUPPORTED'?'vNOT':'vUNT'));
const tname=a=>(Object.entries({ARI:'Cardinals',ATL:'Falcons',BAL:'Ravens',BUF:'Bills',CAR:'Panthers',CHI:'Bears',CIN:'Bengals',CLE:'Browns',DAL:'Cowboys',DEN:'Broncos',DET:'Lions',GB:'Packers',HOU:'Texans',IND:'Colts',JAX:'Jaguars',KC:'Chiefs',LAC:'Chargers',LAR:'Rams',LV:'Raiders',MIA:'Dolphins',MIN:'Vikings',NE:'Patriots',NO:'Saints',NYG:'Giants',NYJ:'Jets',PHI:'Eagles',PIT:'Steelers',SEA:'Seahawks',SF:'49ers',TB:'Buccaneers',TEN:'Titans',WAS:'Commanders'}).find(([k])=>k===a)||[a,a])[1];
function setMode(m){mode=m;sel=null;document.getElementById('mP').classList.toggle('on',m==='players');document.getElementById('mT').classList.toggle('on',m==='teams');document.getElementById('detail').innerHTML='<div class="muted">Select.</div>';rlist('');}
document.getElementById('mP').onclick=()=>setMode('players');document.getElementById('mT').onclick=()=>setMode('teams');
function rlist(q){q=(q||'').toLowerCase();const el=document.getElementById('plist');
 if(mode==='players'){const rows=D.players.filter(p=>!q||(p.name+' '+p.team+' '+p.pos).toLowerCase().includes(q));
  el.innerHTML=rows.map(p=>`<div class="prow ${p.name===sel?'sel':''}" data-n="${esc(p.name)}"><span><span class="pn">${esc(p.name)}</span> <span class="pp">${esc(p.pos)}</span></span><span class="tn">${p.n_about?('▸'+p.n_about):''} ${esc(p.team||'')}</span></div>`).join('');
  el.querySelectorAll('.prow').forEach(r=>r.onclick=()=>{sel=r.dataset.n;tw='about';rlist(document.getElementById('q').value);pcard(sel);});}
 else{const rows=D.teams.filter(t=>!q||(t.team+' '+tname(t.team)).toLowerCase().includes(q));
  el.innerHTML=rows.map(t=>`<div class="prow ${t.team===sel?'sel':''}" data-n="${esc(t.team)}"><span class="pn">${esc(t.team)} <span class="pp">${esc(tname(t.team))}</span></span><span class="tn">▸${t.n_tweets}</span></div>`).join('');
  el.querySelectorAll('.prow').forEach(r=>r.onclick=()=>{sel=r.dataset.n;rlist(document.getElementById('q').value);tcard(sel);});}}
function twHTML(list){return list.length?list.map(t=>`<div class="tw ${t.dims&&t.dims.length?'ins':''}"><div class="h"><span class="tier t${t.tier}">${esc(t.tier)}</span><span class="hd">@${esc(t.handle)}</span><span class="rn">${esc(t.name||'')}</span>${t.dims&&t.dims.length?` <span class="insb">🔍 ${t.dims.map(esc).join(' ')}</span>`:''}<span class="mt">${esc(t.date)} · ♥${t.likes}</span></div><div class="tx">${esc(t.text)}</div><a href="${esc(t.url)}" target="_blank">open ↗</a></div>`).join(''):'<div class="muted">none.</div>';}
const kv=(k,v,sm)=>v==null||v===''?'':`<div class="kv"><div class="k">${k}</div><div class="v">${v}${sm?` <small>${sm}</small>`:''}</div></div>`;
function pcard(n){const p=D.players.find(x=>x.name===n);if(!p)return;const r=p.reads||{};
 let h=`<div class="dh" data-ctx-host>${esc(p.name)}<span class="m">${esc(p.pos)} · ${esc(p.team||'')}</span><span class="ctxchip" data-ctx-name="${esc(p.name)}" data-ctx-pos="${esc(p.pos)}">EPA + CONTEXT</span></div>`;
 h+=`<div class="reads">${kv('ADP',r.adp!=null?Math.round(r.adp):'')}${kv('Proj/g',r.proj!=null?(+r.proj).toFixed(1):'')}${kv('Consensus',r.consensus)}${kv('Matchup',r.matchup)}${kv('Ceiling%',r.ceiling_pct)}${r.best_opp?kv('Best wk','W'+r.best_wk,esc(r.best_opp)):''}</div>`;
 const um=(p.upside||[]).filter(u=>u.group==='model'),uo=(p.upside||[]).filter(u=>u.group==='off');
 if(um.length||uo.length||p.team_note){h+=`<div class="bl">Upside</div>`;
  if(um.length)h+=`<div class="sub2">Model drivers — reliable (in projection)</div><div class="up">`+um.map(u=>`<span class="upc upM" title="${esc(u.note)}">${esc(u.dim.replace('_',' '))} <span class="pp">${u.pctl}th</span><span class="st">${esc(u.stability)}</span></span>`).join('')+`</div>`;
  if(uo.length)h+=`<div class="sub2">Off-model upside — did NOT clear significance; flavor, not in projection</div><div class="up">`+uo.map(u=>`<span class="upc upO" title="${esc(u.note)}">${esc(u.dim.replace('_',' '))} <span class="pp">${u.pctl}th</span><span class="st">${esc(u.stability)}</span></span>`).join('')+`</div>`;
  if(p.team_note)h+=`<div class="note">${esc(p.team_note)}</div>`;}
 if((p.backtests||[]).length){h+=`<div class="bl">Claim backtest — analyst takes vs our data + reliability</div>`+p.backtests.map(b=>`<div class="bt"><div class="vd ${vcl(b.verdict)}">${esc(b.verdict)}</div><div><span class="dim">${esc(b.dim.replace('_',' '))}</span> <span class="meta">${b.pctl==null?'no data':b.pctl+'th pctile'}</span> <span class="muted">· stability <b>${esc(b.stability)}</b></span> <span class="stab">${esc(b.note)}</span><div class="by">by ${b.by.map(x=>'@'+esc(x)).join(', ')}</div></div></div>`).join('');}
 h+=`<div class="tabs"><span class="tab ${tw==='about'?'on':''}" data-t="about">About (${p.n_about})</span><span class="tab ${tw==='comp'?'on':''}" data-t="comp">Comparables (${p.n_comp})</span></div><div>${twHTML(tw==='about'?p.about:p.comp)}</div>`;
 document.getElementById('detail').innerHTML=h;
 document.querySelectorAll('.tab').forEach(t=>t.onclick=()=>{tw=t.dataset.t;pcard(n);});}
function tcard(a){const t=D.teams.find(x=>x.team===a);if(!t)return;const o=t.stats.offense,d=t.stats.defense,c=t.stats.coord;
 let h=`<div class="dh">${esc(a)}<span class="m">${esc(tname(a))}</span></div>`;
 h+=`<div class="bl">Offense — environment</div><div class="reads">${kv('Pace',o.pace!=null?o.pace+'th':'')}${kv('Plays/g',o.plays!=null?o.plays.toFixed(1):'')}${kv('Pass rate',o.pass_rate!=null?o.pass_rate+'%':'',o.rk_passrate?'#'+o.rk_passrate:'')}${kv('Total TD/g',o.total_td!=null?o.total_td.toFixed(2):'',o.rk_td?'#'+o.rk_td:'')}${kv('Win total',o.win_total)}${kv('Env idx',o.env)}${kv('Off Q',o.off_q)}</div>`;
 const shift=d.lean25&&d.lean26&&d.lean25!==d.lean26;
 h+=`<div class="bl">Defense — 2026 engine (roster-adjusted)</div><div class="reads">${kv('Cov pctl',d.cov!=null?Math.round(d.cov):'',d.cov25!=null?'25:'+Math.round(d.cov25):'')}${kv('Rush pctl',d.rush!=null?Math.round(d.rush):'',d.rush25!=null?'25:'+Math.round(d.rush25):'')}${kv('Run pctl',d.run!=null?Math.round(d.run):'',d.run25!=null?'25:'+Math.round(d.run25):'')}</div>`;
 if(d.lean26)h+=`<div class="sub2">Funnel lean: <b>${esc(d.lean26)}</b> (2026)${shift?` <span class="shift">⚠ SHIFT from ${esc(d.lean25)} '25</span>`:''}</div>`;
 if((d.funnels||[]).length)h+=`<div class="note">${d.funnels.map(esc).join(' · ')}</div>`;
 if(c&&(c.oc||c.dc))h+=`<div class="sub2">Coordinators: ${c.oc?'OC '+esc(c.oc):''}${c.dc?'  ·  DC '+esc(c.dc):''}</div>`;
 if(d.dc_scheme&&d.dc_scheme.scheme)h+=`<div class="note">New DC — <b>${esc(d.dc_scheme.name||'')}</b>: ${esc(d.dc_scheme.scheme)}${d.dc_scheme.man26!=null?` (proj man ${d.dc_scheme.man25}→${d.dc_scheme.man26}%)`:''}</div>`;
 if(d.cb1)h+=`<div class="sub2">CB1: <b>${esc(d.cb1.name||'')}</b> cov ${d.cb1.cov} (${esc(d.cb1.tier||'')}) → WR1 funnel: <b>${esc(d.cb1.wr1_funnel||'')}</b></div>`;
 if((d.rookies||[]).length){h+=`<div class="sub2">2026 defensive rookies</div><div>`+d.rookies.map(r=>`<span class="rk">${esc(r.pl)} ${esc(r.pos)} ${esc(r.rd)}</span>`).join('')+`</div>`;}
 if((d.moves||[]).length){h+=`<div class="sub2">Key defensive moves</div><div>`+d.moves.map(m=>`<span class="rk">${esc(m.pl)} ${esc(m.fr)}→${esc(m.to)}</span>`).join('')+`</div>`;}
 if(t.note)h+=`<div class="note">${esc(t.note)}</div>`;
 if((t.players||[]).length){h+=`<div class="bl">Key players</div><div>`+t.players.map(p=>`<span class="pchip" data-n="${esc(p.name)}">${esc(p.name)} <span class="pp">${esc(p.pos)}${p.adp?' · '+Math.round(p.adp):''}</span></span>`).join('')+`</div>`;}
 h+=`<div class="bl">Team tweets (${t.n_tweets}) — newest first</div>${twHTML(t.tweets)}`;
 document.getElementById('detail').innerHTML=h;
 document.querySelectorAll('.pchip').forEach(ch=>ch.onclick=()=>{setMode('players');sel=ch.dataset.n;tw='about';document.getElementById('mP').classList.add('on');document.getElementById('mT').classList.remove('on');rlist('');pcard(sel);});}
document.getElementById('q').oninput=e=>rlist(e.target.value);
rlist('');
</script></body></html>'''
HTML=HTML.replace('__DATA__',blob).replace('__N__',str(D['meta']['n'])).replace('__NT__',str(D['meta'].get('nteams',0))).replace('__BUILT__',built)
import ctx_panel; HTML=ctx_panel.inject(HTML)   # 4-layer NFL Pro EPA drilldown (click the EPA chip in player detail)
open(core.P('intel.html'),'w',encoding='utf-8').write(HTML)
print("intel.html written:",round(len(HTML)/1024),"KB")
