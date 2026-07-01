#!/usr/bin/env python3
"""Render the 2026 flag-adjusted big board (a viewable cheat sheet) from flag_ranks.json.

Overall + by position. Each row: model (flag-adjusted) rank, the delta vs market, player, boom%,
flag breadth, 2026 playoff-week matchup, and the flags/prose that drive the nudge. Self-contained
HTML (no external deps, no browser storage)."""
import json, os, html
import core

HERE = os.path.dirname(os.path.abspath(__file__))


def _lines():
    """player-key -> one-line rationale prose from the flag files."""
    out = {}
    for pos in ('QB', 'RB', 'WR', 'TE'):
        p = os.path.join(HERE, 'boom', f'flags_{pos}.json')
        if not os.path.exists(p):
            continue
        for k, r in json.load(open(p, encoding='utf-8')).items():
            if isinstance(r, dict) and r.get('line'):
                out[core.fn(r.get('name', k))] = r['line']
    return out


def _delta_cell(d):
    if d > 0:
        return f'<span class="up">▲ {d}</span>'
    if d < 0:
        return f'<span class="dn">▼ {-d}</span>'
    return '<span class="fl">·</span>'


def build():
    data = json.load(open(os.path.join(HERE, 'flag_ranks.json'), encoding='utf-8'))
    meta = data['_meta']
    players = list(data['players'].items())
    lines = _lines()
    rows_js = []
    for key, p in players:
        rows_js.append({
            'adj': p['adj_rank'], 'pos': p['pos'], 'name': p['name'], 'team': p.get('team') or '',
            'mkt': p['mkt_rank'], 'delta': p['delta'], 'boom': int(round(p['boom_pctl'])),
            'nflags': p['n_flags'], 'posrank': p['adj_pos_rank'],
            'pmq': int(round(p['pmq_pctl'])), 'flag_score': p['flag_score'],
            'flags': ", ".join(p.get('top_flags') or []),
            'why': lines.get(key, ''),
        })
    rows_js.sort(key=lambda z: z['adj'])

    w = meta['weights']
    sub = (f"ADP-anchored flag nudge · market rank is the backbone, flags move a player at most "
           f"±{int(meta['cap_spots'])} spots · boom {int(w['boom']*100)}% / flag breadth "
           f"{int(w['flags']*100)}% / 2026 playoff matchup {int(w['playoff_mq']*100)}% · "
           f"{meta['n_players']} players")

    doc = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>2026 Best Ball Big Board — flag-adjusted</title>
<style>
:root{{--bg:#0b0f17;--panel:#141c2b;--line:#26324a;--ink:#e8eef9;--ink2:#9fb0d0;--up:#4ade80;--dn:#f87171;--accent:#5b9dff;}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 -apple-system,Segoe UI,Roboto,sans-serif}}
.wrap{{max-width:1080px;margin:0 auto;padding:22px 16px 60px}}
h1{{font-size:22px;margin:0 0 4px}} .sub{{color:var(--ink2);font-size:12.5px;margin-bottom:16px}}
.tabs{{display:flex;gap:6px;flex-wrap:wrap;margin:14px 0}}
.tab{{padding:6px 14px;border:1px solid var(--line);border-radius:20px;background:var(--panel);color:var(--ink2);cursor:pointer;font-size:13px}}
.tab.on{{background:var(--accent);color:#04070d;border-color:var(--accent);font-weight:600}}
.search{{width:100%;padding:9px 12px;background:var(--panel);border:1px solid var(--line);border-radius:8px;color:var(--ink);margin-bottom:10px;font-size:13px}}
table{{width:100%;border-collapse:collapse}}
th,td{{text-align:left;padding:8px 9px;border-bottom:1px solid var(--line);vertical-align:top}}
th{{color:var(--ink2);font-weight:600;font-size:11.5px;text-transform:uppercase;letter-spacing:.4px;position:sticky;top:0;background:var(--bg)}}
td.n{{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}}
.rk{{font-weight:700;font-size:15px}} .pos{{color:var(--ink2);font-size:12px}}
.up{{color:var(--up);font-weight:600}} .dn{{color:var(--dn);font-weight:600}} .fl{{color:var(--ink2)}}
.mkt{{color:var(--ink2);font-variant-numeric:tabular-nums}}
.flags{{color:var(--accent);font-size:12px}} .why{{color:var(--ink2);font-size:11.5px;margin-top:2px}}
.boom{{font-variant-numeric:tabular-nums}} .bhi{{color:var(--up)}} .blo{{color:var(--dn)}}
.name{{font-weight:600}} .posrk{{color:var(--ink2);font-size:11px;margin-left:5px}}
</style></head><body><div class="wrap">
<h1>2026 Best Ball Big Board</h1>
<div class="sub">{html.escape(sub)}</div>
<div class="tabs" id="tabs">
  <div class="tab on" data-p="ALL">Overall</div><div class="tab" data-p="QB">QB</div>
  <div class="tab" data-p="RB">RB</div><div class="tab" data-p="WR">WR</div><div class="tab" data-p="TE">TE</div>
</div>
<input class="search" id="q" placeholder="filter by name / team…">
<table><thead><tr>
<th>Rank</th><th>Δ mkt</th><th>Player</th><th class="n">Mkt</th><th class="n">Boom</th>
<th class="n">Flags</th><th class="n">PO MQ</th><th>Why (top flags)</th>
</tr></thead><tbody id="tb"></tbody></table>
</div>
<script>
const ROWS={json.dumps(rows_js)};
const tb=document.getElementById('tb'), q=document.getElementById('q');
let pos='ALL';
function boomCls(b){{return b>=66?'bhi':(b<=33?'blo':'')}}
function dcell(d){{return d>0?`<span class="up">▲ ${{d}}</span>`:(d<0?`<span class="dn">▼ ${{-d}}</span>`:'<span class="fl">·</span>')}}
function render(){{
  const term=q.value.trim().toLowerCase();
  const rows=ROWS.filter(r=>(pos==='ALL'||r.pos===pos)
     && (!term || (r.name+' '+r.team).toLowerCase().includes(term)));
  tb.innerHTML=rows.map(r=>`<tr>
    <td class="n"><span class="rk">${{pos==='ALL'?r.adj:r.posrank}}</span></td>
    <td class="n">${{dcell(r.delta)}}</td>
    <td><span class="name">${{r.name}}</span> <span class="pos">${{r.pos}} · ${{r.team}}</span>
        ${{r.why?`<div class="why">${{r.why.replace(/</g,'&lt;')}}</div>`:''}}</td>
    <td class="n mkt">${{r.mkt}}</td>
    <td class="n boom ${{boomCls(r.boom)}}">${{r.boom}}</td>
    <td class="n">${{r.nflags}}</td>
    <td class="n">${{r.pmq}}</td>
    <td class="flags">${{r.flags||''}}</td></tr>`).join('');
}}
document.querySelectorAll('.tab').forEach(t=>t.onclick=()=>{{
  document.querySelectorAll('.tab').forEach(x=>x.classList.remove('on'));
  t.classList.add('on'); pos=t.dataset.p; render();
}});
q.oninput=render; render();
</script></body></html>"""
    out = os.path.join(HERE, 'big_board_2026.html')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(doc)
    print(f"big_board_2026.html: {len(players)} players, {len(doc)//1024} KB")


if __name__ == '__main__':
    build()
