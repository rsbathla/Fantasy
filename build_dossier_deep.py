#!/usr/bin/env python3
"""build_dossier_deep.py — the COMPREHENSIVE per-player dossier (learn as much as possible).

Aggregates EVERY source we have into one deep profile per player, rendered as a searchable
master-detail page (dossier_deep.html):
  identity/archetype · projections & market · real NFL Pro EPA & efficiency · full situational
  profile (all percentiles, strengths & weaknesses) · scheme fit & opportunity · 18-week matchup
  calendar · ceiling levers/signals/upside · risk flags & claim backtests · TWEETS (with links) ·
  VIDEO mentions.
Sources: dossier_data.json, player_profiles.json, cc_context.json, intel_data.json (tweets),
video_notes.csv (video), nfl_pro_epa via cc_context.
"""
import core, json, os, csv, datetime
import ctx_panel
HERE = os.path.dirname(os.path.abspath(__file__))
def J(p):
    fp = os.path.join(HERE, p)
    return json.load(open(fp, encoding='utf-8')) if os.path.exists(fp) else {}
fn = core.fn

dd = J('dossier_data.json')
profiles = J('player_profiles.json') if os.path.exists(os.path.join(HERE, 'player_profiles.json')) else J('profiles/player_profiles.json')
ctx = J('cc_context.json')
intel = J('intel_data.json')
# tweets per player from intel
TW = {}
for p in (intel.get('players') or []):
    if p.get('about'):
        TW[fn(p['name'])] = {'about': p['about'], 'comp': p.get('comp', []),
                             'n_about': p.get('n_about'), 'backtests': p.get('backtests', []), 'news': []}
# LIVE X layer (x_dossier_refresh.py -> x_live.json, fed by the X MCP). Prefer live posts; split news.
xlive = J('x_live.json')
xnar = J('x_narrative.json')   # analysis layer: synthesized "what analysts are saying" per player
xmedia = (J('x_media.json') or {}).get('by_player', {})   # indexed+summarized articles/videos per player
for fk, posts in (xlive.get('players') or {}).items():
    cur = TW.setdefault(fk, {'about': [], 'comp': [], 'backtests': [], 'news': []})
    live_news = [p for p in posts if (p.get('kind') == 'news')]
    live_tw = [p for p in posts if (p.get('kind') != 'news')]
    pref = {(t.get('text') or '')[:60] for t in live_tw}
    cur['about'] = live_tw + [t for t in cur.get('about', []) if (t.get('text') or '')[:60] not in pref]
    cur['news'] = (cur.get('news') or []) + live_news
    cur['n_about'] = len(cur['about'])
# video notes
VID = {}
vp = os.path.join(HERE, 'video_notes.csv')
if os.path.exists(vp):
    for r in csv.DictReader(open(vp, encoding='utf-8')):
        VID[fn(r['name'])] = {'note': r.get('video_note', ''), 'n_clips': r.get('n_clips')}

# flatten dossier_data players
DDP = {}
teams = dd.get('teams', [])
teams = teams if isinstance(teams, list) else list(teams.values())
for t in teams:
    for p in (t.get('players') or []):
        DDP[fn(p['name'])] = p

# build the comprehensive record per player (union of every key by fn-name)
keys = set(DDP) | set(fn(n) for n in profiles) | set(ctx)
players = []
prof_by_fn = {fn(n): {'name': n, **v} for n, v in profiles.items()}
for k in keys:
    dp = DDP.get(k, {})
    pr = prof_by_fn.get(k, {})
    cx = ctx.get(k, {})
    name = dp.get('name') or pr.get('name')
    if not name:
        continue
    pos = dp.get('pos') or pr.get('pos'); team = dp.get('team') or pr.get('team')
    if pos not in ('QB', 'RB', 'WR', 'TE'):
        continue
    rec = {
        'name': name, 'pos': pos, 'team': team,
        'rank': dp.get('rank'), 'adp': dp.get('adp'), 'vs_adp': dp.get('vs_adp'),
        'proj': (dp.get('proj') or {}).get('pg') if isinstance(dp.get('proj'), dict) else dp.get('proj'),
        'proj_detail': dp.get('proj') if isinstance(dp.get('proj'), dict) else None,
        'adj_pg': dp.get('adj_pg'), 'posrank': dp.get('proj_posrank'),
        'consensus': dp.get('consensus'), 'divergence': dp.get('divergence'),
        'flags': dp.get('flags'), 'risk_flags': dp.get('risk_flags'), 'flags_playoff': dp.get('flags_playoff'),
        'levers': dp.get('levers'), 'signals': dp.get('signals'), 'upside': dp.get('upside'),
        'backtests': (TW.get(k, {}).get('backtests') or dp.get('backtests')),
        'qual': dp.get('qual'), 'align': dp.get('align'), 'motion': dp.get('motion'),
        'cov': dp.get('cov'), 'rz': dp.get('rz'), 'oline': dp.get('oline'),
        'lever_cal': dp.get('lever_cal'), 'lever_sum': dp.get('lever_sum'), 'playoff': dp.get('playoff'),
        # real EPA + 4-layer context
        'splits': cx.get('splits'), 'scheme': cx.get('scheme'), 'opp': cx.get('opp'), 'matchup': cx.get('matchup'),
        # full situational percentiles
        'situations': pr.get('situations'), 'trend': pr.get('trend'),
        # tweets + video + synthesized analyst narrative
        'tweets': TW.get(k, {}).get('about'), 'n_tweets': TW.get(k, {}).get('n_about'),
        'news': TW.get(k, {}).get('news'),
        'analyst_take': xnar.get(k),
        'media': xmedia.get(k),
        'video': VID.get(k, {}).get('note'), 'n_clips': VID.get(k, {}).get('n_clips'),
    }
    players.append(rec)

players.sort(key=lambda p: (p['rank'] if p.get('rank') else 9999))
built = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
import math
def _clean(o):
    if isinstance(o, float):
        return None if (math.isnan(o) or math.isinf(o)) else o
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_clean(v) for v in o]
    return o
blob = json.dumps(_clean(players), ensure_ascii=False, allow_nan=False).replace('<', '\\u003c')
n_tw = sum(1 for p in players if p.get('tweets')); n_vid = sum(1 for p in players if p.get('video'))
n_epa = sum(1 for p in players if p.get('splits'))

HTML = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Player Dossier — Deep</title><style>
:root{--bg:#0e1016;--p1:#161922;--p2:#1c2030;--ln:#262b3a;--tx:#e7ebf3;--mut:#9aa3b6;--mut2:#697084;--acc:#7aa2ff;--qb:#e0567a;--rb:#37b87a;--wr:#3b8ef0;--te:#e8a33d;--good:#37b87a;--warn:#e8a33d;--bad:#e0567a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:13px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif}
.wrap{display:grid;grid-template-columns:280px 1fr;height:100vh}
.list{border-right:1px solid var(--ln);overflow-y:auto;background:var(--p1)}
.search{position:sticky;top:0;background:var(--p1);padding:10px;border-bottom:1px solid var(--ln);z-index:5}
.search input{width:100%;background:var(--p2);border:1px solid var(--ln);color:var(--tx);border-radius:8px;padding:8px 10px}
.pf{display:flex;gap:3px;margin-top:7px}.pf span{flex:1;text-align:center;padding:4px;font-size:10px;font-weight:700;border:1px solid var(--ln);border-radius:6px;color:var(--mut);cursor:pointer}.pf span.on{color:#0c0e13;background:var(--acc)}
.prow{padding:7px 11px;border-bottom:1px solid var(--ln);cursor:pointer;display:flex;justify-content:space-between;align-items:center;gap:8px}
.prow:hover{background:var(--p2)}.prow.sel{background:rgba(122,162,255,.12);border-left:2px solid var(--acc)}
.prow .nm{font-weight:600;font-size:12.5px}.prow .mt{font-size:10px;color:var(--mut2)}
.pos{font-size:8.5px;font-weight:800;border-radius:3px;padding:1px 4px;color:#0c0e13}.pos.QB{background:var(--qb)}.pos.RB{background:var(--rb)}.pos.WR{background:var(--wr)}.pos.TE{background:var(--te)}
.detail{overflow-y:auto;padding:18px 24px}
.dh{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;border-bottom:1px solid var(--ln);padding-bottom:10px;margin-bottom:6px}
.dh h1{font-size:21px;margin:0}.dh .meta{color:var(--mut)}
.sec{margin:16px 0}.sec h3{font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--acc);margin:0 0 8px;border-bottom:1px solid var(--ln);padding-bottom:4px}
.kv{display:inline-flex;flex-direction:column;background:var(--p1);border:1px solid var(--ln);border-radius:8px;padding:6px 11px;margin:0 7px 7px 0;min-width:84px}
.kv .k{font-size:9.5px;color:var(--mut2);text-transform:uppercase;letter-spacing:.3px}.kv .v{font-size:15px;font-weight:700;font-family:ui-monospace,Menlo,monospace}
.kv .v.g{color:var(--good)}.kv .v.b{color:var(--bad)}.kv .v.w{color:var(--warn)}
.barrow{display:flex;align-items:center;gap:8px;font-size:11.5px;padding:2px 0}.barrow .lab{width:230px;color:var(--mut)}.bar{flex:1;height:9px;background:var(--p2);border-radius:5px;overflow:hidden;max-width:240px}.bar>i{display:block;height:100%}.barrow .pv{width:34px;text-align:right;font-family:ui-monospace,monospace;font-weight:600}
.chip{display:inline-block;background:var(--p2);border:1px solid var(--ln);border-radius:7px;padding:3px 9px;margin:2px;font-size:11px}
.chip.g{border-color:rgba(55,184,122,.5)}.chip.b{border-color:rgba(224,86,122,.5)}.chip.w{border-color:rgba(232,163,61,.5)}
.tweet{background:var(--p1);border:1px solid var(--ln);border-left:2px solid var(--acc);border-radius:8px;padding:8px 11px;margin:6px 0;font-size:12px}
.tweet .h{color:var(--acc);font-weight:600;font-size:11px}.tweet .m{color:var(--mut2);font-size:10px}.tweet a{color:var(--acc)}
.vid{background:var(--p1);border:1px solid var(--ln);border-left:2px solid var(--te);border-radius:8px;padding:9px 12px;font-size:12px;color:var(--mut);line-height:1.6}
.wkcal{display:flex;flex-wrap:wrap;gap:3px}.wk{width:30px;text-align:center;font-size:9px;border-radius:4px;padding:3px 0;color:#0b0d12;font-weight:700}.wk .w{font-size:8px;opacity:.7;color:#0b0d12}
.note{color:var(--mut);font-size:11.5px}.muted{color:var(--mut2)}.empty{color:var(--mut2);font-style:italic;font-size:11.5px}
</style>__CTXCSS__</head><body>
<div class="wrap">
<div class="list"><div class="search"><input id="q" placeholder="Search __N__ players…"><div class="pf" id="pf"></div></div><div id="plist"></div></div>
<div class="detail" id="detail"><div class="empty" style="padding:40px">Select a player to see their full dossier — projections, real EPA, situational profile, scheme fit, weekly matchup, ceiling levers, risk flags, tweets, and video mentions.</div></div>
</div>
<script>
const P=__DATA__;
const esc=s=>String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
const hm=v=>{if(v==null)return 'var(--p2)';const h=Math.max(0,Math.min(120,v*1.2));return `hsl(${h},58%,44%)`;};
const posb=p=>`<span class="pos ${p}">${p}</span>`;
let st={q:'',pos:'ALL',sel:null};
const POS=['ALL','QB','RB','WR','TE'];
const pfh=document.getElementById('pf');POS.forEach(p=>{const s=document.createElement('span');s.textContent=p;s.className=(p==='ALL'?'on':'');s.onclick=()=>{st.pos=p;[...pfh.children].forEach(c=>c.classList.toggle('on',c.textContent===p));rlist();};pfh.appendChild(s);});
function rlist(){const el=document.getElementById('plist');
 let r=P.filter(p=>(st.pos==='ALL'||p.pos===st.pos)&&(!st.q||p.name.toLowerCase().includes(st.q)));
 el.innerHTML=r.map((p,i)=>`<div class="prow ${p.name===st.sel?'sel':''}" data-n="${esc(p.name)}"><span><span class="nm">${esc(p.name)}</span> ${posb(p.pos)}</span><span class="mt">${p.team||''}${p.rank?' · #'+p.rank:''}</span></div>`).join('');
 el.querySelectorAll('.prow').forEach(d=>d.onclick=()=>{st.sel=d.dataset.n;rlist();render(P.find(x=>x.name===st.sel));});}
document.getElementById('q').oninput=e=>{st.q=e.target.value.toLowerCase();rlist();};
function kv(k,v,cls){return v==null||v===''?'':`<div class="kv"><span class="k">${k}</span><span class="v ${cls||''}">${v}</span></div>`;}
function bars(sits,filterKeys){if(!sits)return '';const items=Object.entries(sits).filter(([k,v])=>v&&v.pct!=null).sort((a,b)=>b[1].pct-a[1].pct);
 return items.map(([k,v])=>`<div class="barrow"><span class="lab">${esc(v.metric||k)}</span><span class="bar"><i style="width:${v.pct}%;background:${hm(v.pct)}"></i></span><span class="pv">${Math.round(v.pct)}</span></div>`).join('');}
function render(p){if(!p)return;let h='';
 h+=`<div class="dh"><h1>${esc(p.name)}</h1> ${posb(p.pos)} <span class="meta">${p.team||''}${p.rank?' · rank #'+p.rank:''}${p.adp?' · ADP '+(+p.adp).toFixed(1):''}${p.posrank?' · '+p.pos+p.posrank:''}</span> <span class="ctxchip" data-ctx-name="${esc(p.name)}" data-ctx-pos="${p.pos}">4-LAYER CONTEXT</span></div>`;
 // projections & market
 h+=`<div class="sec"><h3>Projections & market</h3>${kv('Proj/g',p.proj!=null?(+p.proj).toFixed(1):null)}${kv('Adj/g',p.adj_pg!=null?(+p.adj_pg).toFixed(1):null)}${kv('ADP',p.adp!=null?(+p.adp).toFixed(1):null)}${kv('vs ADP',p.vs_adp!=null?((p.vs_adp>0?'+':'')+p.vs_adp):null,p.vs_adp>0?'g':p.vs_adp<0?'b':'')}${kv('Consensus',p.consensus)}${kv('Divergence',p.divergence,p.divergence>=22?'w':'')}</div>`;
 // real EPA
 const s=p.splits;
 if(s){let e='';
  if(p.pos==='WR'||p.pos==='TE'||(s.rec_epa_route!=null)){e+=kv('Rec EPA/rt',s.rec_epa_route,s.rec_epa_route>0?'g':'b')+kv('Sep',s.rec_separation)+kv('CROE',s.rec_croe,s.rec_croe>0?'g':'b')+kv('YACOE',s.rec_yacoe)+kv('YPRR man',s.yprr_man)+kv('YPRR zone',s.yprr_zone);}
  if(p.pos==='QB'){e+=kv('EPA/DB',s.qb_epa_db,s.qb_epa_db>0.1?'g':s.qb_epa_db<0?'b':'')+kv('CPOE',s.qb_cpoe,s.qb_cpoe>0?'g':'b')+kv('Press%',s.qb_pressure_rate,s.qb_pressure_rate>35?'b':'')+kv('aNY/A',s.qb_anya);}
  if(p.pos==='RB'){e+=kv('Rush EPA/att',s.rush_epa_att,s.rush_epa_att>-0.02?'g':'b')+kv('RYOE/att',s.ryoe_att,s.ryoe_att>0.5?'g':'')+kv('zone run%',s.zone_run_sh)+kv('top spd',s.rb_topspeed);}
  let yoy='';if(s.yoy)yoy=`<div class="note" style="margin-top:5px">${esc(s.yoy.label)} trajectory: ${s.yoy.y2024} → ${s.yoy.y2025} <b style="color:${s.yoy.delta>0?'var(--good)':'var(--bad)'}">${s.yoy.delta>0?'▲+':'▼'}${Math.abs(s.yoy.delta)}</b></div>`;
  h+=`<div class="sec"><h3>Real NFL Pro EPA & efficiency</h3>${e}${yoy}</div>`;}
 // situational profile
 if(p.situations&&Object.keys(p.situations).length)h+=`<div class="sec"><h3>Situational profile — where they win (percentile vs position)</h3>${bars(p.situations)}</div>`;
 // scheme fit & opportunity
 if(p.scheme||p.opp){let so='';const sc=p.scheme||{};if(sc.playcaller)so+=`<div class="note"><b>2026 caller:</b> ${esc(sc.playcaller)}</div>`;if(sc.fit)so+=`<div>${sc.fit.map(c=>`<span class="chip g">${esc(c)}</span>`).join('')}</div>`;if(sc.note)so+=`<div class="note">${esc(sc.note)}</div>`;
  const o=p.opp||{};if(o.route_pct!=null)so+=`<div class="note" style="margin-top:6px">route ${o.route_pct}% · ${esc(o.align||'')} · tgt share ${o.tgt_share||'–'}% · team vacated ${o.team_vacated_tgt||'–'}%</div>`;
  if(o.self_moves)so+=`<div class="note">${o.self_moves.map(m=>(m.dir==='added'?'➕ brings ':'➖ vacates ')+((m.tgts||0)+'t '+(m.rush||0)+'r')).join(' · ')}</div>`;
  h+=`<div class="sec"><h3>Scheme fit & opportunity</h3>${so||'<span class=empty>continuity / no scheme change tracked</span>'}</div>`;}
 // weekly matchup calendar
 if(p.lever_cal&&p.lever_cal.length){h+=`<div class="sec"><h3>18-week matchup calendar (ceiling-lever intensity; greener = better spot)</h3><div class="wkcal">`+
  p.lever_cal.map((v,i)=>{const sc=(v&&v.score!=null)?v.score:0;const op=(v&&v.opp)?v.opp:'';return `<div class="wk" style="background:${hm(Math.min(100,sc*45))}" title="wk ${v.wk||i+1} vs ${op}: ${sc}"><div class="w">W${v.wk||i+1}</div>${sc.toFixed(1)}<div class="w">${esc(op)}</div></div>`;}).join('')+`</div></div>`;}
 // matchup (W15-17 from ctx)
 if(p.matchup&&p.matchup.weeks){const m=p.matchup;h+=`<div class="sec"><h3>Playoff matchup (W15-17, ${m.metric==='run'?'run D':'coverage'} softness)</h3>`+m.weeks.map(w=>`<span class="chip">W${w.wk} @${esc(w.opp)}: ${w.val}</span>`).join('')+` <span class="note">avg ${m.avg} ${m.avg<40?'(soft)':m.avg>65?'(tough)':''}</span></div>`;}
 // levers / upside / signals
 if(p.levers&&p.levers.length)h+=`<div class="sec"><h3>Ceiling levers</h3>${p.levers.map(l=>`<span class="chip ${l.c==='solid'?'g':'w'}">${esc(l.t)}${l.c?` <span class=muted>(${esc(l.c)})</span>`:''}</span>`).join('')}</div>`;
 if(p.upside&&p.upside.length)h+=`<div class="sec"><h3>Upside drivers</h3>${p.upside.map(u=>`<span class="chip ${u.group==='model'?'g':''}">${esc((u.dim||'').replace(/_/g,' '))} ${u.pctl!=null?u.pctl+'th':''} <span class=muted>${esc(u.stability||'')}</span></span>`).join('')}</div>`;
 // risk flags
 const rf=p.risk_flags||p.flags;if(rf&&rf.length)h+=`<div class="sec"><h3>Risk flags${p.flags_playoff?` · ${p.flags_playoff} hit the playoffs`:''}</h3>${(Array.isArray(rf)?rf:[]).map(f=>`<span class="chip b">${esc(typeof f==='string'?f:(f.q||f.note||JSON.stringify(f)))}</span>`).join('')}</div>`;
 // backtests
 if(p.backtests&&p.backtests.length)h+=`<div class="sec"><h3>Analyst-claim backtests (claim vs our data)</h3>`+p.backtests.map(b=>`<div class="note" style="margin:3px 0"><b style="color:${/STRONG|SUPPORT/i.test(b.verdict)?'var(--good)':/NOT|REJECT/i.test(b.verdict)?'var(--bad)':'var(--warn)'}">${esc(b.verdict)}</b> — ${esc((b.dim||'').replace(/_/g,' '))} ${b.pctl!=null?'('+b.pctl+'th)':''}: ${esc(b.note||'')} ${b.by?'<span class=muted>— '+b.by.map(x=>'@'+esc(x)).join(', ')+'</span>':''}</div>`).join('')+`</div>`;
 // synthesized analyst narrative — what people are saying -> the player's forming profile
 if(p.analyst_take){const a=p.analyst_take;const sc={bullish:'var(--good)',bearish:'var(--bad)',mixed:'var(--warn)',neutral:'var(--mut)'}[a.sentiment]||'var(--mut)';h+=`<div class="sec"><h3>🧠 What analysts are saying</h3><div class="note" style="border-left:3px solid ${sc};padding-left:10px"><span style="color:${sc};font-weight:800;text-transform:uppercase;font-size:10px;letter-spacing:.5px">${esc(a.sentiment||'')}</span> <span class="muted">· ${a.n_src} mapped post${a.n_src===1?'':'s'}${a.handles&&a.handles.length?' · '+a.handles.map(x=>'@'+esc(x)).join(', '):''}</span><div style="margin-top:5px">${esc(a.take||'')}</div>${a.themes&&a.themes.length?'<div style="margin-top:6px">'+a.themes.map(t=>`<span class="chip">${esc(t)}</span>`).join('')+'</div>':''}</div></div>`;}
 // breaking news (live X news/trends)
 if(p.news&&p.news.length)h+=`<div class="sec"><h3>📰 Breaking news & trends (live)</h3>`+p.news.slice(0,8).map(t=>`<div class="tweet" style="border-left-color:var(--warn)"><span class="h" style="color:var(--warn)">@${esc(t.handle||'')}</span> <span class="m">${esc(t.date||'')}</span><div>${esc(t.text||'')}</div>${t.url?`<a href="${esc(t.url)}" target="_blank">link →</a>`:''}</div>`).join('')+`</div>`;
 // tweets
 if(p.tweets&&p.tweets.length)h+=`<div class="sec"><h3>Tweets & analyst mentions (${p.n_tweets||p.tweets.length})${p.tweets[0]&&p.tweets[0].source==='x_mcp'?' · live':''}</h3>`+p.tweets.slice(0,20).map(t=>`<div class="tweet"><span class="h">@${esc(t.handle||t.name||'')}</span> <span class="m">${esc(t.date||'')}${t.likes?' · '+t.likes+'♥':''}</span><div>${esc(t.text||'')}</div>${t.url?`<a href="${esc(t.url)}" target="_blank">link →</a>`:''}</div>`).join('')+`</div>`;
 // indexed + summarized articles / videos / podcasts (the media layer)
 if(p.media&&p.media.length){const ic={article:'📄',video:'🎬',podcast:'🎙️'};h+=`<div class="sec"><h3>Articles &amp; video (indexed)</h3>`+p.media.map(mi=>`<div class="note" style="border-left:3px solid var(--acc);padding-left:10px;margin:6px 0"><div><span style="font-weight:700">${ic[mi.type]||'🔗'} ${esc(mi.title||'')}</span> <span class="muted">· @${esc(mi.by||'')} · ${esc(mi.summary_src||'')}</span></div><div style="margin-top:4px">${esc(mi.summary||'')}</div>${mi.url?`<a href="${esc(mi.url)}" target="_blank">open →</a>`:''}</div>`).join('')+`</div>`;}
 // video
 if(p.video)h+=`<div class="sec"><h3>Video mentions${p.n_clips?` (${p.n_clips} clips)`:''}</h3><div class="vid">${esc(p.video)}</div></div>`;
 document.getElementById('detail').innerHTML=h;
}
rlist();
</script>__CTXJS__</body></html>'''
html = (HTML.replace('__N__', str(len(players))).replace('__DATA__', blob)
        .replace('__CTXCSS__', ctx_panel.css()).replace('__CTXJS__', ctx_panel.script()))
open(os.path.join(HERE, 'dossier_deep.html'), 'w', encoding='utf-8').write(html)
print(f"wrote dossier_deep.html ({len(html)//1024} KB) — {len(players)} players | tweets {n_tw} · video {n_vid} · EPA {n_epa}")
