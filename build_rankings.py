#!/usr/bin/env python3
"""Rankings board: merged_rankings_2026 (ADP-anchored blend of fusion+ceiling+clay+playoff+ADP)
enriched with our model reads -> rankings_2026.csv + rankings.html (sortable draft board)."""
import csv, json, os, re, core, datetime
def fn(n): n=str(n).strip().lower(); n=re.sub(r'\s+(jr|sr|ii|iii|iv|v)\.?$','',n); return ' '.join(n.replace('.','').replace("'","").replace('-',' ').split())
def num(x):
    try: return float(x)
    except: return None
MR=list(csv.DictReader(open(core.P('pipeline/merged_rankings_2026.csv'),encoding='utf-8')))
fus={fn(p['name']):p for p in json.load(open(core.P('fusion.json')))['players']}
boom=json.load(open(core.P('boom/boom_marks.json'))) if os.path.exists(core.P('boom/boom_marks.json')) else {}
sig={fn(r['name']):r for r in csv.DictReader(open(core.P('draft_board_signals.csv'),encoding='utf-8'))}
intel={fn(p['name']):p for p in (json.load(open(core.P('intel_data.json'))).get('players',[]) if os.path.exists(core.P('intel_data.json')) else [])}
_FL=(json.load(open(core.P('flags_2026.json'))).get('players',{}) if os.path.exists(core.P('flags_2026.json')) else {})
FLG={fn(v['name']):v for v in _FL.values()}  # data-backed risk flags (total/playoff/avail/adj)
def cons(p):
    c=(p or {}).get('consensus'); return c.get('mean') if isinstance(c,dict) else c
rows=[]; posn={}
for m in MR:
    k=fn(m['Name']); pos=m['Position']; posn[pos]=posn.get(pos,0)+1
    fp=fus.get(k); bm=boom.get(k); s=sig.get(k,{}); it=intel.get(k,{})
    up=[u for u in (it.get('upside') or []) if u.get('group')=='model'][:2]
    rows.append({'rank':int(float(m['merged_rank'])),'pos':pos,'posrank':posn[pos],'name':m['Name'],'team':m['Team'],
        'adp':round(num(m['ADP']),1) if num(m['ADP']) is not None else None,
        'edge':int(float(m['vs_adp'])) if m.get('vs_adp') not in (None,'','nan') else None,
        'proj':round(num(s.get('proj_pg')),1) if num(s.get('proj_pg')) is not None else None,
        'ceil':(bm or {}).get('ceiling_pct'),'cons':round(cons(fp)) if cons(fp) is not None else None,
        'flags':(fp or {}).get('flags',[])[:2],'up':[u['dim'] for u in up],
        'nsrc':int(float(m.get('n_sources') or 0)),
        'ft':(FLG.get(k) or {}).get('total'),'fp':(FLG.get(k) or {}).get('playoff'),'av':(FLG.get(k) or {}).get('avail'),'adj':(FLG.get(k) or {}).get('adj_pg')})
# enriched CSV
with open(core.P('rankings_2026.csv'),'w',newline='') as fh:
    w=csv.writer(fh); w.writerow(['rank','pos','posrank','name','team','adp','edge_vs_adp','proj_pg','ceiling_pct','consensus','flags_total','flags_playoff','avail','adj_proj_pg','model_flags','upside'])
    for r in rows: w.writerow([r['rank'],r['pos'],r['posrank'],r['name'],r['team'],r['adp'],r['edge'],r['proj'],r['ceil'],r['cons'],r.get('ft'),r.get('fp'),r.get('av'),r.get('adj'),'; '.join(r['flags']),' '.join(r['up'])])
blob=json.dumps(rows,ensure_ascii=False).replace('<','\\u003c'); built=datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
HTML=r'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Rankings 2026</title><style>
:root{--bg:#0a0e16;--bg2:#0c1320;--panel:#111a2b;--line:#1d2a40;--line2:#26354f;--ink:#e9eef7;--ink2:#aebbd0;--ink3:#7488a6;--accent:#5b9dff;--good:#5fd08a;--bad:#ff8c8c;--warn:#e0b25c;--mono:ui-monospace,Menlo,Consolas,monospace}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:13px/1.45 -apple-system,Segoe UI,Roboto,sans-serif}
.top{padding:10px 16px;border-bottom:1px solid var(--line);display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.top h1{font-size:16px;margin:0}.sub{color:var(--ink3);font-size:11.5px;font-family:var(--mono)}
.ctl{margin-left:auto;display:flex;gap:6px;align-items:center}
.fb{font-size:12px;font-weight:700;padding:4px 10px;border:1px solid var(--line2);border-radius:7px;cursor:pointer;color:var(--ink2)}.fb.on{background:var(--accent);color:#0a0e16;border-color:var(--accent)}
input{background:#0c1320;color:var(--ink);border:1px solid var(--line2);border-radius:8px;padding:6px 10px;font-size:13px}
table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:6px 9px;border-bottom:1px solid var(--line)}
th{position:sticky;top:0;background:var(--bg2);font-size:10.5px;text-transform:uppercase;letter-spacing:.5px;color:var(--ink3);cursor:pointer;user-select:none}
td.r,th.r{text-align:right;font-family:var(--mono)}
tr:hover td{background:rgba(91,157,255,.06)}
.pos{font-family:var(--mono);font-size:11px;color:var(--accent)}
.edge.up{color:var(--good);font-weight:700}.edge.dn{color:var(--bad);font-weight:700}
.bar{display:inline-block;height:7px;border-radius:4px;background:linear-gradient(90deg,#2f6b48,var(--good));vertical-align:middle}
.fl{font-size:10.5px;color:var(--warn)}.up{font-size:10px;color:var(--good);font-family:var(--mono)}
.nm{font-weight:600}
</style></head><body>
<div class="top"><h1>2026 Rankings</h1><span class="sub">__N__ players · ADP-anchored blend of fusion + ceiling + Clay + playoff overlay · built __BUILT__ · &#9873; total risk flags, &#9670;PO = affects playoffs (W15-17), &rarr; = availability-adjusted proj/g</span>
<div class="ctl"><span class="fb on" data-p="ALL">ALL</span><span class="fb" data-p="QB">QB</span><span class="fb" data-p="RB">RB</span><span class="fb" data-p="WR">WR</span><span class="fb" data-p="TE">TE</span><input id="q" placeholder="search"></div></div>
<table id="t"><thead><tr>
<th class="r" data-k="rank">Rank</th><th data-k="pos">Pos</th><th class="nm" data-k="name">Player</th><th data-k="team">Tm</th>
<th class="r" data-k="adp">ADP</th><th class="r" data-k="edge">Edge</th><th class="r" data-k="proj">Proj/g</th><th class="r" data-k="ceil">Ceil%</th><th class="r" data-k="cons">Cons</th><th class="r" data-k="ft" title="total risk flags">&#9873;</th><th class="r" data-k="fp" title="flags affecting fantasy playoffs (W15-17)">&#9670;PO</th><th data-k="flags">Model flags / upside</th>
</tr></thead><tbody id="tb"></tbody></table>
<script>
const D=__DATA__; let pf='ALL',q='',sk='rank',sd=1;
const esc=s=>(s==null?'':String(s)).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
function render(){let r=D.filter(x=>(pf==='ALL'||x.pos===pf)&&(!q||(x.name+' '+x.team).toLowerCase().includes(q)));
 r.sort((a,b)=>{let va=a[sk],vb=b[sk];va=va==null?(sd>0?1e9:-1e9):va;vb=vb==null?(sd>0?1e9:-1e9):vb;return (va>vb?1:va<vb?-1:0)*sd;});
 document.getElementById('tb').innerHTML=r.map(x=>{
  const e=x.edge==null?'':(x.edge>0?`<span class="edge up">+${x.edge}</span>`:(x.edge<0?`<span class="edge dn">${x.edge}</span>`:'0'));
  const ceil=x.ceil==null?'':`<span class="bar" style="width:${Math.round(x.ceil/2)}px"></span> ${x.ceil}`;
  const fl=(x.flags||[]).map(f=>`<span class="fl">${esc(f)}</span>`).join(' · ')+((x.up||[]).length?` <span class="up">▲${x.up.map(esc).join(' ')}</span>`:'');
  const ftc=x.ft?`<span style="color:var(--bad);font-weight:700">${x.ft}</span>`:'';
  const fpc=x.fp?`<span style="color:var(--warn);font-weight:700">${x.fp}</span>`:'';
  const adjp=(x.av!=null&&x.av<1)?` <span style="color:var(--bad)" title="availability-adjusted proj/g">&rarr;${x.adj}</span>`:'';
  return `<tr><td class="r">${x.rank}</td><td class="pos">${esc(x.pos)}${x.posrank}</td><td class="nm">${esc(x.name)}<span class="ctxchip" data-ctx-name="${esc(x.name)}" data-ctx-pos="${esc(x.pos)}">EPA</span></td><td>${esc(x.team)}</td><td class="r">${x.adp??''}</td><td class="r">${e}</td><td class="r">${x.proj??''}${adjp}</td><td class="r">${ceil}</td><td class="r">${x.cons??''}</td><td class="r">${ftc}</td><td class="r">${fpc}</td><td>${fl}</td></tr>`;}).join('');}
document.querySelectorAll('.fb').forEach(b=>b.onclick=()=>{pf=b.dataset.p;document.querySelectorAll('.fb').forEach(z=>z.classList.toggle('on',z===b));render();});
document.querySelectorAll('th[data-k]').forEach(h=>h.onclick=()=>{const k=h.dataset.k;if(sk===k)sd*=-1;else{sk=k;sd=(k==='name'||k==='pos'||k==='team')?1:1;}render();});
document.getElementById('q').oninput=e=>{q=e.target.value.toLowerCase();render();};
render();
</script></body></html>'''
HTML=HTML.replace('__DATA__',blob).replace('__N__',str(len(rows))).replace('__BUILT__',built)
import ctx_panel; HTML=ctx_panel.inject(HTML)   # 4-layer NFL Pro EPA drilldown (click the EPA chip)
open(core.P('rankings.html'),'w',encoding='utf-8').write(HTML)
print(f"rankings.html + rankings_2026.csv: {len(rows)} players")
print("\nTop 12:")
for r in rows[:12]: print(f"  {r['rank']:>3} {r['pos']}{r['posrank']:<2} {r['name']:22} {r['team']:3} ADP {r['adp']!s:>5} edge {r['edge']:+d} proj {r['proj']} ceil {r['ceil']}")
