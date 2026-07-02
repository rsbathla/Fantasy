#!/usr/bin/env python3
"""Standalone sortable 'ceiling-lever stack' board (the count, league-wide).
Reads lever_count.json (per-player tier-weighted weekly scores) + dossier_data.json (proj/rank/adp),
writes lever_board.html — a self-contained, sortable, filterable table.

IMPORTANT framing: this ranks MATCHUP-LEVER FAVORABILITY (how often a player's stable ceiling levers get
turned on by his 2026 opponents), tier-weighted by confidence. It is NOT a talent ranking — read it
alongside projection. A low-ADP player on a soft slate with several tendency levers can rank high here.
"""
import json, os, html
H=os.path.dirname(os.path.abspath(__file__))
def J(p):
    fp=os.path.join(H,p); return json.load(open(fp,encoding='utf-8')) if os.path.exists(fp) else {}
lc=J('lever_count.json'); dd=J('dossier_data.json')
proj={}
for t in dd.get('teams',[]):
    for p in t['players']:
        proj[p['name']]={'rank':p.get('rank'),'adp':p.get('adp'),'pg':(p.get('proj') or {}).get('pg'),
                         'ceiling':(p.get('proj') or {}).get('ceiling')}
LBL={'man_beater':'man-beater','gets_open_man':'wins-vs-man','zone_beater':'zone-beater','vertical':'vertical',
 'slot':'slot','boundary':'boundary','contested':'contested','redzone':'red-zone','passcatch_rb':'pass-ct-back',
 'scramble_qb':'scramble','elusive_rb':'elusive','elusive':'elusive','shootout':'shootout','qb_man':'qb-vs-man'}
rows=[]
for name,v in (lc.get('players') or {}).items():
    s=v['summary']; pr=proj.get(name,{})
    lt=' '.join(sorted({LBL.get(l['type'],l['type']) for l in v['levers']}))
    rows.append({'name':name,'pos':v.get('pos'),'team':v.get('team'),'rank':pr.get('rank'),'adp':pr.get('adp'),
        'pg':pr.get('pg'),'nlev':s['n_levers'],'mean':s['mean'],'po':s['playoff_mean'],'peak':s['peak'],
        'smash':len(s['smash_weeks']),'smashwk':','.join(map(str,s['smash_weeks'])),'lt':lt})
rows.sort(key=lambda r:(-(r['po'] or 0), -(r['peak'] or 0)))
data=json.dumps(rows)
meta=lc.get('meta',{})
doc=f"""<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Ceiling-Lever Stack Board — 2026</title>
<style>
:root{{--bg:#0b0f17;--card:#121a29;--line:#1e2a3d;--line2:#2a3a52;--ink:#eef2f8;--ink2:#aab8cc;--ink3:#6f819b;--accent:#5b9dff;--good:#5fd08a;--warn:#e6b34d}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:13px/1.5 -apple-system,Segoe UI,Roboto,Arial,sans-serif}}
.wrap{{max-width:1200px;margin:0 auto;padding:18px}}
h1{{font-size:19px;margin:0 0 3px}}.sub{{color:var(--ink3);font-size:12px;margin-bottom:12px;max-width:820px}}
.controls{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}}
.controls button,.controls input{{background:var(--card);color:var(--ink);border:1px solid var(--line2);border-radius:7px;padding:6px 11px;font-size:12px;cursor:pointer}}
.controls button.on{{background:var(--accent);color:#08101e;border-color:var(--accent);font-weight:700}}
table{{width:100%;border-collapse:collapse;font-size:12.5px}}
th,td{{text-align:left;padding:6px 9px;border-bottom:1px solid var(--line)}}
th{{position:sticky;top:0;background:var(--card);cursor:pointer;user-select:none;color:var(--ink2);font-size:11px;text-transform:uppercase;letter-spacing:.5px}}
th:hover{{color:var(--accent)}}
td.num,th.num{{text-align:right;font-variant-numeric:tabular-nums}}
tr:hover{{background:rgba(91,157,255,.06)}}
.bar{{display:inline-block;height:8px;background:var(--good);border-radius:2px;vertical-align:middle;margin-right:6px}}
.lt{{color:var(--ink3);font-size:11px}}.pos{{color:var(--accent);font-weight:700}}
.smash{{color:var(--good);font-weight:700}}
</style></head><body><div class=wrap>
<h1>Ceiling-Lever Stack Board &mdash; 2026</h1>
<div class=sub>Tier-weighted count of how often each player's <b>stability-audited</b> FantasyPoints ceiling levers get
turned on by his actual 2026 opponents (solid&times;1.0, tendency&times;0.5, scaled by opponent favorability).
This is <b>matchup-lever favorability, not talent</b> &mdash; read it next to projection. Smash week = weekly score &ge; {meta.get('smash',1.5)}.
Click headers to sort.</div>
<div class=controls>
<button data-pos=ALL class=on>All</button><button data-pos=WR>WR</button><button data-pos=RB>RB</button>
<button data-pos=TE>TE</button><button data-pos=QB>QB</button>
<input id=q placeholder="filter name/team..." style="flex:1;min-width:160px">
</div>
<table id=t><thead><tr>
<th data-k=name>Player</th><th data-k=pos>Pos</th><th data-k=team>Tm</th>
<th class=num data-k=rank>Rk</th><th class=num data-k=pg>Pj/g</th><th class=num data-k=nlev>Levers</th>
<th class=num data-k=mean>Szn</th><th class=num data-k=po>Playoff</th><th class=num data-k=peak>Peak</th>
<th class=num data-k=smash>Smash</th><th data-k=lt>Lever types</th></tr></thead><tbody></tbody></table>
</div><script>
const D={data};let pos='ALL',sk='po',sd=-1;
const tb=document.querySelector('#t tbody'),q=document.getElementById('q');
const mx=Math.max(...D.map(r=>r.po||0))||1;
function draw(){{let r=D.filter(x=>(pos==='ALL'||x.pos===pos)&&((x.name+' '+x.team).toLowerCase().includes(q.value.toLowerCase())));
r.sort((a,b)=>{{let A=a[sk],B=b[sk];if(typeof A==='string'){{A=A||'';B=B||'';return sd*A.localeCompare(B);}}return sd*(((A||0)-(B||0)));}});
tb.innerHTML=r.map(x=>`<tr><td>${{x.name}}<span class="ctxchip" data-ctx-name="${{x.name}}" data-ctx-pos="${{x.pos||''}}">EPA</span></td><td class=pos>${{x.pos||''}}</td><td>${{x.team||''}}</td>
<td class=num>${{x.rank??''}}</td><td class=num>${{x.pg??''}}</td><td class=num>${{x.nlev}}</td>
<td class=num>${{x.mean}}</td><td class=num><span class=bar style="width:${{Math.round(46*(x.po||0)/mx)}}px"></span>${{x.po}}</td>
<td class=num>${{x.peak}}</td><td class=num smash>${{x.smash}}<span class=lt> (${{x.smashwk}})</span></td>
<td class=lt>${{x.lt}}</td></tr>`).join('');}}
document.querySelectorAll('th').forEach(th=>th.onclick=()=>{{const k=th.dataset.k;if(sk===k)sd=-sd;else{{sk=k;sd=(k==='name'||k==='pos'||k==='team'||k==='lt')?1:-1;}}draw();}});
document.querySelectorAll('.controls button').forEach(b=>b.onclick=()=>{{pos=b.dataset.pos;document.querySelectorAll('.controls button').forEach(x=>x.classList.remove('on'));b.classList.add('on');draw();}});
q.oninput=draw;draw();
</script></body></html>"""
import ctx_panel; doc=ctx_panel.inject(doc)   # 4-layer NFL Pro EPA drilldown (click the EPA chip)
open(os.path.join(H,'lever_board.html'),'w',encoding='utf-8').write(doc)
print('lever_board.html written:',len(doc)//1024,'KB,',len(rows),'players')
