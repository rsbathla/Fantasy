#!/usr/bin/env python3
"""COVERAGE-SCHEME & ROUTE SPECIALIST builder.

NEW capability (distinct from build_cover_spec.py, which only does coarse Man/Zone/
Single-High/Two-High rollups from the ManVsZone export): this reads the per-SCHEME
charting (Cover 0/1/2/3/4/6, Man Cover 2) and per-ROUTE charting (Comeback..Slant)
from NFL-master/FP/{2024,2025}/Receiving/{CoverageType,RouteType}/*.csv, pools the
two seasons per WR/TE, computes YPRR / TPRR / catch% / YAC-per-rec per scheme and
per route, converts YPRR to a WITHIN-POSITION percentile (WR vs WR, TE vs TE), and
tags each player's specializations (elite >= 85th pctl, weak <= 20th) on adequate
samples only (RTE >= 25 pooled in that cell; percentile pools need >= 12 qualifiers).

Outputs:
  boom/coverage_route_spec.json      -- the computed spec (players + meta)
  coverage_route_specialist.html     -- self-contained dark explorer (player profile
                                        view + "who's elite at X" leaderboard)

NOTE / future hook (NOT wired in, per guardrails): each player's `elite` / `weak`
lists here (e.g. {"kind":"scheme","key":"Cover 3","pctl":94}) are exactly the shape
the dossier's per-player tag chips consume. build_dossier.py could later join
boom/coverage_route_spec.json on the same fn(name) key and surface e.g.
"C3 SPECIALIST 94th" chips next to the existing man/zone tags. Left un-wired.

Scheme grouping context: Cover 1 = man single-high; Cover 3 = zone single-high;
Cover 0 = pure man (no deep help); Cover 2/4/6 = two-high zones; Man Cover 2 = man
under two-deep.  Rollups: MAN = C0 + C1 + Man C2;  ZONE = C2 + C3 + C4 + C6.
"""
import csv, json, os, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from core import fn  # repo's canonical name normalization so names join across files

YEARS = ('2024', '2025')
SCHEMES = ['Cover 0', 'Cover 1', 'Cover 2', 'Cover 3', 'Cover 4', 'Cover 6', 'Man Cover 2']
ROUTES = ['Comeback', 'Corner', 'Curl', 'Flat', 'Go-Fly', 'In', 'Out', 'Post', 'Screen', 'Slant']
MAN_SET = {'Cover 0', 'Cover 1', 'Man Cover 2'}
ZONE_SET = {'Cover 2', 'Cover 3', 'Cover 4', 'Cover 6'}

MIN_RTE = 25          # pooled 2yr routes required in a coverage-scheme cell to qualify
MIN_RTE_ROUTE = 20    # route-type cells are structurally thinner (a Post is one route of many); 20 pooled
MIN_RTE_OVERALL = 100 # pooled routes for the overall (all-scheme) percentile
MIN_PEERS = 12        # a (pos, cell) needs >= this many qualifiers to rank at all
ELITE_P = 85
WEAK_P = 20

def num(v):
    v = (v or '').strip().replace(',', '')
    if v in ('', '-'): return 0
    try: return int(v)
    except ValueError:
        try: return float(v)
        except ValueError: return 0

def read_cell(kind, cell):
    """Pool one scheme/route CSV across both seasons -> {fnkey: sums}."""
    pool = {}
    for yr in YEARS:
        p = os.path.join(HERE, 'NFL-master', 'FP', yr, 'Receiving', kind, cell + '.csv')
        if not os.path.exists(p):
            print(f'  !! missing {p}'); continue
        for r in csv.DictReader(open(p, encoding='utf-8-sig')):
            pos = (r.get('POS') or '').strip().upper()
            if pos not in ('WR', 'TE'): continue
            k = fn(r['Name'])
            a = pool.setdefault(k, {'name': r['Name'].strip(), 'team': r['Team'].strip(),
                                    'pos': pos, 'rte': 0, 'tgt': 0, 'rec': 0,
                                    'yds': 0, 'ay': 0, 'yac': 0})
            a['rte'] += num(r['RTE']); a['tgt'] += num(r['TGT']); a['rec'] += num(r['REC'])
            a['yds'] += num(r['YDS']); a['ay'] += num(r['AY']); a['yac'] += num(r['YAC'])
            a['name'] = r['Name'].strip(); a['team'] = r['Team'].strip(); a['pos'] = pos  # latest yr wins
    return pool

def rates(a):
    rte, tgt, rec = a['rte'], a['tgt'], a['rec']
    return {
        'rte': rte, 'tgt': tgt, 'rec': rec, 'yds': a['yds'], 'yac': a['yac'],
        'yprr': round(a['yds'] / rte, 3) if rte else None,
        'tprr': round(tgt / rte, 3) if rte else None,
        'catch': round(rec / tgt, 3) if tgt else None,
        'yac_rec': round(a['yac'] / rec, 2) if rec else None,
        'adot': round(a['ay'] / tgt, 1) if tgt else None,
    }

def pctl_rank(vals):
    """value -> percentile (0-100, mean-rank for ties) within the list."""
    sv = sorted(vals); n = len(sv)
    out = {}
    for v in set(sv):
        lo = 0
        while lo < n and sv[lo] < v: lo += 1
        hi = lo
        while hi < n and sv[hi] == v: hi += 1
        out[v] = round(100.0 * (lo + 0.5 * (hi - lo)) / n)
    return out

def main():
    # ---- ingest every cell -------------------------------------------------
    cells = {}   # cellkey -> {fnkey: raw sums}
    for s in SCHEMES: cells['S|' + s] = read_cell('CoverageType', s)
    for rt in ROUTES: cells['R|' + rt] = read_cell('RouteType', rt)

    # ---- assemble players --------------------------------------------------
    players = {}
    for ck, pool in cells.items():
        for k, a in pool.items():
            p = players.setdefault(k, {'key': k, 'name': a['name'], 'team': a['team'],
                                       'pos': a['pos'], 'schemes': {}, 'routes': {},
                                       'rollups': {}, 'overall': None})
            p['name'], p['team'], p['pos'] = a['name'], a['team'], a['pos']
            kind, cell = ck.split('|', 1)
            (p['schemes'] if kind == 'S' else p['routes'])[cell] = rates(a)

    # rollups (MAN / ZONE) + overall from the scheme sums
    for k, p in players.items():
        for label, group in (('MAN', MAN_SET), ('ZONE', ZONE_SET), ('OVERALL', set(SCHEMES))):
            agg = {'rte': 0, 'tgt': 0, 'rec': 0, 'yds': 0, 'ay': 0, 'yac': 0}
            for s in group:
                raw = cells['S|' + s].get(k)
                if raw:
                    for f in agg: agg[f] += raw[f]
            r = rates(agg)
            if label == 'OVERALL': p['overall'] = r
            else: p['rollups'][label] = r

    # ---- percentiles within position, per cell -----------------------------
    meta_cells = {}
    def rank_cell(getter, cellname, min_rte):
        for pos in ('WR', 'TE'):
            qual = [(k, getter(p)) for k, p in players.items()
                    if p['pos'] == pos and getter(p) and getter(p)['rte'] >= min_rte]
            mk = f'{pos}|{cellname}'
            if len(qual) < MIN_PEERS:
                meta_cells[mk] = {'nq': len(qual), 'ranked': False}
                for _, c in qual: c['q'] = True; c['pctl'] = None
                continue
            pr = pctl_rank([c['yprr'] for _, c in qual])
            ys = sorted(c['yprr'] for _, c in qual)
            meta_cells[mk] = {'nq': len(qual), 'ranked': True,
                              'max': ys[-1], 'med': ys[len(ys)//2],
                              'p85': ys[min(len(ys)-1, int(0.85*len(ys)))]}
            for _, c in qual:
                c['q'] = True; c['pctl'] = pr[c['yprr']]
        # mark unqualified
        for k, p in players.items():
            c = getter(p)
            if c and 'q' not in c: c['q'] = False; c['pctl'] = None

    for s in SCHEMES:  rank_cell(lambda p, s=s: p['schemes'].get(s), 'S|' + s, MIN_RTE)
    for rt in ROUTES:  rank_cell(lambda p, rt=rt: p['routes'].get(rt), 'R|' + rt, MIN_RTE_ROUTE)
    for rl in ('MAN', 'ZONE'): rank_cell(lambda p, rl=rl: p['rollups'].get(rl), 'RL|' + rl, MIN_RTE)
    rank_cell(lambda p: p['overall'], 'OVR', MIN_RTE_OVERALL)

    # ---- specializations ----------------------------------------------------
    for p in players.values():
        elite, weak = [], []
        for kind, d in (('scheme', p['schemes']), ('route', p['routes'])):
            for cell, c in d.items():
                if not c.get('q') or c.get('pctl') is None: continue
                tag = {'kind': kind, 'key': cell, 'pctl': c['pctl'],
                       'yprr': c['yprr'], 'rte': c['rte']}
                if c['pctl'] >= ELITE_P: elite.append(tag)
                elif c['pctl'] <= WEAK_P: weak.append(tag)
        p['elite'] = sorted(elite, key=lambda t: -t['pctl'])
        p['weak'] = sorted(weak, key=lambda t: t['pctl'])

    # keep players with at least one qualified cell (drops sub-25-route noise)
    keep = [p for p in players.values()
            if any(c.get('q') for c in list(p['schemes'].values()) +
                   list(p['routes'].values()) + list(p['rollups'].values()))]
    keep.sort(key=lambda p: -(p['overall']['rte'] if p['overall'] else 0))

    out = {
        'built': __import__('datetime').date.today().isoformat(),
        'seasons': [int(y) for y in YEARS],
        'min_rte': MIN_RTE, 'min_rte_route': MIN_RTE_ROUTE, 'min_rte_overall': MIN_RTE_OVERALL,
        'min_peers': MIN_PEERS, 'elite_pctl': ELITE_P, 'weak_pctl': WEAK_P,
        'schemes': SCHEMES, 'routes': ROUTES,
        'scheme_groups': {'MAN': sorted(MAN_SET), 'ZONE': sorted(ZONE_SET)},
        'cells': meta_cells,
        'players': keep,
    }
    os.makedirs(os.path.join(HERE, 'boom'), exist_ok=True)
    jp = os.path.join(HERE, 'boom', 'coverage_route_spec.json')
    json.dump(out, open(jp, 'w'), separators=(',', ':'))
    print(f'wrote {jp} ({os.path.getsize(jp)//1024} KB)')

    # ---- console validation -------------------------------------------------
    nwr = sum(1 for p in keep if p['pos'] == 'WR'); nte = len(keep) - nwr
    print(f'players kept: {len(keep)} ({nwr} WR, {nte} TE) | cells: {len(SCHEMES)} schemes + {len(ROUTES)} routes + MAN/ZONE rollups')
    thin = [k for k, m in meta_cells.items() if not m.get('ranked')]
    print('unranked (thin) pos-cells:', thin or 'none')
    nico = next((p for p in keep if p['key'] == fn('Nico Collins')), None)
    if nico:
        c3 = nico['schemes'].get('Cover 3')
        print(f"VALIDATE Nico Collins vs Cover 3: RTE={c3['rte']} YDS={c3['yds']} "
              f"YPRR={c3['yprr']} pctl={c3['pctl']} (q={c3['q']}, "
              f"of {meta_cells['WR|S|Cover 3']['nq']} qualified WRs)")
        print('  elite tags:', [(t['key'], t['pctl']) for t in nico['elite']])
        print('  weak tags :', [(t['key'], t['pctl']) for t in nico['weak']])
    else:
        print('VALIDATE: Nico Collins NOT FOUND — check name join')
    # a few leaderboards for the report
    def top(cellkind, cell, pos, n=5):
        rows = [(p['name'], d['yprr'], d['pctl'], d['rte'])
                for p in keep if p['pos'] == pos
                for d in [(p['schemes'] if cellkind == 'S' else p['routes']).get(cell)]
                if d and d.get('q') and d.get('pctl') is not None]
        return sorted(rows, key=lambda r: -r[1])[:n]
    for label, kind, cell, pos in (('WR vs Cover 3', 'S', 'Cover 3', 'WR'),
                                   ('WR vs Cover 1 (man)', 'S', 'Cover 1', 'WR'),
                                   ('WR vs Cover 0 (blitz-man)', 'S', 'Cover 0', 'WR'),
                                   ('WR vs 2-high (Cover 4)', 'S', 'Cover 4', 'WR'),
                                   ('TE vs Cover 3', 'S', 'Cover 3', 'TE'),
                                   ('WR Post routes', 'R', 'Post', 'WR'),
                                   ('WR Go/Fly routes', 'R', 'Go-Fly', 'WR'),
                                   ('WR Slant routes', 'R', 'Slant', 'WR'),
                                   ('TE Corner routes', 'R', 'Corner', 'TE'),
                                   ('WR Screen routes', 'R', 'Screen', 'WR')):
        print(f'  TOP {label}: ' + '; '.join(f'{n_} {y:.2f} yprr p{pc} n={rt}' for n_, y, pc, rt in top(kind, cell, pos)))
    render_html(out)

# ============================ HTML EXPLORER =================================
def render_html(data):
    payload = json.dumps(data, separators=(',', ':')).replace('</', '<\\/')
    html = TEMPLATE.replace('__DATA__', payload)
    hp = os.path.join(HERE, 'coverage_route_specialist.html')
    open(hp, 'w').write(html)
    print(f'wrote {hp} ({os.path.getsize(hp)//1024} KB)')

TEMPLATE = r'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Coverage &amp; Route Specialist</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
:root{--bg:#0e1016;--p1:#161922;--p2:#1c2030;--p3:#232838;--ln:#262b3a;--tx:#e7ebf3;
--mut:#9aa3b6;--mut2:#697084;--acc:#7aa2ff;--elite:#3fd68f;--elite-d:#123626;
--weak:#ff8273;--weak-d:#3a1f1d;--wr:#3b8ef0;--te:#e8a33d;
--mono:'JetBrains Mono',ui-monospace,monospace;--disp:'Space Grotesk',Inter,sans-serif}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--tx);font:13px/1.5 Inter,-apple-system,sans-serif}
.top{display:flex;align-items:center;gap:18px;padding:16px 24px 14px;border-bottom:1px solid var(--ln);flex-wrap:wrap}
.top h1{font-family:var(--disp);font-weight:700;font-size:22px;letter-spacing:-.03em;margin:0;white-space:nowrap}
.top h1 em{font-style:normal;color:var(--elite)}
.klabel{font-family:var(--mono);font-size:9.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--mut2)}
.top .sub{font-family:var(--mono);font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--mut2)}
.modes{display:flex;gap:6px;margin-left:auto}
.mbtn{font-family:var(--mono);font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--mut);
background:var(--p1);border:1px solid var(--ln);border-radius:9px;padding:8px 14px;cursor:pointer}
.mbtn.on{color:#0c0e13;background:var(--elite);border-color:var(--elite);font-weight:600}
.wrap{display:grid;grid-template-columns:284px 1fr;height:calc(100vh - 61px)}
.side{border-right:1px solid var(--ln);overflow-y:auto;background:var(--p1)}
.sticky{position:sticky;top:0;background:var(--p1);padding:12px;border-bottom:1px solid var(--ln);z-index:4}
.sticky input{width:100%;background:var(--p2);border:1px solid var(--ln);color:var(--tx);border-radius:9px;
padding:9px 11px;font:12.5px Inter,sans-serif;outline:none}
.sticky input:focus{border-color:var(--acc)}
.pf{display:flex;gap:4px;margin-top:8px}
.pf span{flex:1;text-align:center;padding:5px 0;font-family:var(--mono);font-size:9.5px;letter-spacing:.1em;
font-weight:600;border:1px solid var(--ln);border-radius:7px;color:var(--mut);cursor:pointer}
.pf span.on{color:#0c0e13;background:var(--acc);border-color:var(--acc)}
.prow{padding:8px 13px;border-bottom:1px solid #1d2130;cursor:pointer;display:flex;align-items:center;gap:8px}
.prow:hover{background:var(--p2)}
.prow.sel{background:rgba(63,214,143,.09);box-shadow:inset 2px 0 0 var(--elite)}
.prow .nm{font-weight:600;font-size:12.5px;flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.prow .mt{font-family:var(--mono);font-size:9px;color:var(--mut2);letter-spacing:.05em}
.pos{font-family:var(--mono);font-size:8.5px;font-weight:600;border-radius:4px;padding:2px 5px;color:#0c0e13;letter-spacing:.06em}
.pos.WR{background:var(--wr)}.pos.TE{background:var(--te)}
.ndot{font-family:var(--mono);font-size:9px;color:var(--mut2)}
.main{overflow-y:auto;padding:20px 26px 60px}
.hd{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;margin-bottom:4px}
.hd h2{font-family:var(--disp);font-weight:700;font-size:30px;letter-spacing:-.035em;margin:0}
.hd .meta{font-family:var(--mono);font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;color:var(--mut)}
.chips{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0 20px}
.chip{font-family:var(--mono);font-size:10px;letter-spacing:.1em;text-transform:uppercase;font-weight:600;
padding:6px 11px;border-radius:999px;border:1px solid}
.chip.e{color:var(--elite);background:var(--elite-d);border-color:rgba(63,214,143,.35)}
.chip.w{color:var(--weak);background:var(--weak-d);border-color:rgba(255,130,115,.3)}
.chip.n{color:var(--mut);background:var(--p1);border-color:var(--ln)}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:18px}
@media(max-width:1100px){.cols{grid-template-columns:1fr}}
.card{background:var(--p1);border:1px solid var(--ln);border-radius:14px;padding:16px 18px 14px}
.card h3{font-family:var(--mono);font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:var(--mut);
margin:0 0 4px;font-weight:600}
.card .hint{font-family:var(--mono);font-size:9px;letter-spacing:.08em;color:var(--mut2);margin-bottom:12px}
.brow{display:grid;grid-template-columns:104px 1fr 176px;gap:10px;align-items:center;padding:6px 0;border-bottom:1px solid #1b1f2c}
.brow:last-child{border-bottom:none}
.brow.rollup{background:rgba(122,162,255,.04);border-radius:8px;padding:6px 8px;margin:2px -8px}
.blab{font-family:var(--mono);font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:var(--mut);white-space:nowrap}
.track{height:14px;background:var(--p2);border-radius:7px;overflow:hidden;position:relative}
.fill{height:100%;border-radius:7px;background:#39415c}
.fill.m{background:linear-gradient(90deg,#39415c,#4a5578)}
.fill.e{background:linear-gradient(90deg,#1e7a52,var(--elite))}
.fill.w{background:linear-gradient(90deg,#8a3d33,var(--weak))}
.fill.lo{background:repeating-linear-gradient(45deg,#262b3a 0 6px,#1c2030 6px 12px)}
.bnums{display:flex;align-items:center;gap:8px;justify-content:flex-end}
.yv{font-family:var(--mono);font-size:12px;font-weight:600;min-width:44px;text-align:right}
.yv.e{color:var(--elite)}.yv.w{color:var(--weak)}
.pc{font-family:var(--mono);font-size:9px;font-weight:600;letter-spacing:.05em;border-radius:5px;padding:2px 5px;min-width:34px;text-align:center}
.pc.e{color:#0c0e13;background:var(--elite)}.pc.w{color:#0c0e13;background:var(--weak)}
.pc.m{color:var(--mut);background:var(--p3)}.pc.lo{color:var(--mut2);background:transparent;border:1px dashed var(--ln)}
.nn{font-family:var(--mono);font-size:9px;color:var(--mut2);min-width:46px;text-align:right}
.foot{font-family:var(--mono);font-size:9px;letter-spacing:.08em;color:var(--mut2);margin-top:22px;border-top:1px solid var(--ln);padding-top:10px;line-height:1.9}
/* leaderboard */
.lb-pick{margin-bottom:16px}
.lb-pick .grp{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin:6px 0}
.cellbtn{font-family:var(--mono);font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:var(--mut);
background:var(--p1);border:1px solid var(--ln);border-radius:8px;padding:6px 10px;cursor:pointer}
.cellbtn.on{color:#0c0e13;background:var(--elite);border-color:var(--elite);font-weight:600}
.lbhead{display:flex;align-items:baseline;gap:12px;margin:18px 0 10px}
.lbhead h2{font-family:var(--disp);font-weight:700;font-size:24px;letter-spacing:-.03em;margin:0}
table{width:100%;border-collapse:collapse}
th{font-family:var(--mono);font-size:9px;letter-spacing:.14em;text-transform:uppercase;color:var(--mut2);
text-align:right;padding:6px 8px;border-bottom:1px solid var(--ln);font-weight:600}
th.l{text-align:left}
td{padding:7px 8px;border-bottom:1px solid #1b1f2c;text-align:right;font-family:var(--mono);font-size:11.5px;color:var(--mut)}
td.l{text-align:left;font-family:Inter,sans-serif;font-size:12.5px;font-weight:600;color:var(--tx)}
td .tm{font-family:var(--mono);font-size:9px;color:var(--mut2);margin-left:7px;letter-spacing:.05em}
tr.el td.l{color:var(--elite)}
td.yy{color:var(--tx);font-weight:600}
.minitrack{display:inline-block;width:120px;height:10px;background:var(--p2);border-radius:5px;overflow:hidden;vertical-align:middle;margin-right:8px}
.minitrack i{display:block;height:100%;border-radius:5px}
.rk{color:var(--mut2)}
tr:hover td{background:rgba(122,162,255,.04)}
tr{cursor:pointer}
</style></head><body>
<div class="top">
  <h1>COVERAGE &amp; ROUTE <em>SPECIALIST</em></h1>
  <div class="sub" id="subline"></div>
  <div class="modes">
    <button class="mbtn" id="mb-player" onclick="setMode('player')">Player Profile</button>
    <button class="mbtn" id="mb-elite" onclick="setMode('elite')">Who&rsquo;s Elite At&hellip;</button>
  </div>
</div>
<div class="wrap" id="wrap">
  <div class="side" id="side">
    <div class="sticky">
      <input id="q" placeholder="Search player&hellip;" oninput="renderList()">
      <div class="pf" id="pf">
        <span data-p="ALL" class="on" onclick="setPos('ALL')">ALL</span>
        <span data-p="WR" onclick="setPos('WR')">WR</span>
        <span data-p="TE" onclick="setPos('TE')">TE</span>
      </div>
    </div>
    <div id="plist"></div>
  </div>
  <div class="main" id="main"></div>
</div>
<script>
const D = __DATA__;
const byKey = {}; D.players.forEach(p=>byKey[p.key]=p);
let mode='player', pos='ALL', selKey=D.players[0].key, lbCell={kind:'S',key:'Cover 3'};
const RL_LABEL={MAN:'ALL MAN',ZONE:'ALL ZONE'};
const fmt=(v,d=2)=>v==null?'—':v.toFixed(d);
document.getElementById('subline').textContent =
  D.seasons.join('+')+' pooled · '+D.players.length+' WR/TE · min '+D.min_rte+' rt/scheme, '+D.min_rte_route+' rt/route · pctl within position';

function metaFor(pos,kind,key){ const mk = pos+'|'+(kind==='RL'?'RL|'+key:(kind==='OVR'?'OVR':kind+'|'+key)); return D.cells[mk]||{}; }
function cls(c){ if(!c||!c.q) return 'lo'; if(c.pctl==null) return 'm'; if(c.pctl>=D.elite_pctl) return 'e'; if(c.pctl<=D.weak_pctl) return 'w'; return 'm'; }

function setMode(m){ mode=m; location.hash=''; render(); }
function setPos(p){ pos=p; document.querySelectorAll('#pf span').forEach(s=>s.classList.toggle('on',s.dataset.p===p)); renderList(); if(mode==='elite') renderMain(); }
function pick(k){ selKey=k; if(mode!=='player'){mode='player';} render(); }

function renderList(){
  const q=(document.getElementById('q').value||'').toLowerCase();
  const rows=D.players.filter(p=>(pos==='ALL'||p.pos===pos)&&(!q||p.name.toLowerCase().includes(q)));
  document.getElementById('plist').innerHTML=rows.slice(0,400).map(p=>{
    const o=p.overall||{}, top=p.elite[0];
    return `<div class="prow ${p.key===selKey&&mode==='player'?'sel':''}" onclick="pick('${p.key}')">
      <span class="pos ${p.pos}">${p.pos}</span>
      <span class="nm">${p.name}<div class="mt">${p.team} · ${o.rte||0} RT${top?` · ${top.key.toUpperCase()} ${top.pctl}TH`:''}</div></span>
      <span class="ndot">${o.yprr!=null?o.yprr.toFixed(2):''}</span></div>`;
  }).join('');
}

function bar(label,c,posn,kind,key,rollup){
  const m=metaFor(posn,kind,key), mx=m.max||3.5;
  const k=cls(c);
  const w=c&&c.yprr!=null?Math.max(2,Math.min(100,100*c.yprr/mx)):0;
  const pcHtml=!c||!c.rte?'<span class="pc lo">—</span>':
    (!c.q?'<span class="pc lo">LOW N</span>':
     (c.pctl==null?'<span class="pc lo">UNRANKED</span>':`<span class="pc ${k}">${c.pctl}th</span>`));
  return `<div class="brow ${rollup?'rollup':''}">
    <div class="blab">${label}</div>
    <div class="track"><div class="fill ${c&&c.q?k:'lo'}" style="width:${w}%"></div></div>
    <div class="bnums"><span class="yv ${c&&c.q?k:''}">${c&&c.yprr!=null?c.yprr.toFixed(2):'—'}</span>${pcHtml}<span class="nn">n=${c?c.rte:0}</span></div>
  </div>`;
}

function renderPlayer(){
  const p=byKey[selKey]; if(!p){document.getElementById('main').innerHTML='';return;}
  const o=p.overall||{};
  const chips=[...p.elite.slice(0,5).map(t=>`<span class="chip e">${t.key} · ${t.pctl}th</span>`),
               ...p.weak.slice(0,3).map(t=>`<span class="chip w">${t.key} · ${t.pctl}th</span>`)];
  if(!chips.length) chips.push('<span class="chip n">No elite/weak cells at sample threshold</span>');
  const sch=D.schemes.map(s=>bar(s.replace('Cover ','COVER '),p.schemes[s],p.pos,'S',s,false)).join('')
    + ['MAN','ZONE'].map(rl=>bar(RL_LABEL[rl],p.rollups[rl],p.pos,'RL',rl,true)).join('');
  const rts=D.routes.map(r=>bar(r,p.routes[r],p.pos,'R',r,false)).join('');
  document.getElementById('main').innerHTML=`
    <div class="hd"><h2>${p.name}</h2>
      <span class="pos ${p.pos}">${p.pos}</span>
      <span class="meta">${p.team} · ${o.rte||0} routes ${D.seasons.join('+')} · overall ${fmt(o.yprr)} YPRR${o.pctl!=null?' ('+o.pctl+'th)':''}</span></div>
    <div class="chips">${chips.join('')}</div>
    <div class="cols">
      <div class="card"><h3>Coverage-Scheme Profile</h3>
        <div class="hint">YPRR by defensive shell · bar scaled to ${p.pos} qualified max · pctl vs ${p.pos}s</div>${sch}</div>
      <div class="card"><h3>Route Profile</h3>
        <div class="hint">YPRR by route type · bar scaled to ${p.pos} qualified max · pctl vs ${p.pos}s</div>${rts}</div>
    </div>
    <div class="foot">SOURCE: FANTASYPOINTS CHARTING · FP/{2024,2025}/RECEIVING/{COVERAGETYPE,ROUTETYPE} · POOLED 2 SEASONS.
    MINT = ELITE (≥${D.elite_pctl}TH PCTL) · CORAL = WEAK (≤${D.weak_pctl}TH) · HATCHED = LOW SAMPLE (UNDER ${D.min_rte} SCHEME / ${D.min_rte_route} ROUTE ROUTES — DISCOUNT IT).
    C1 = MAN SINGLE-HIGH · C3 = ZONE SINGLE-HIGH · C0 = PURE MAN · C2/C4/C6 = TWO-HIGH ZONE · MC2 = MAN TWO-DEEP.</div>`;
}

function renderElite(){
  const isS=lbCell.kind==='S', isR=lbCell.kind==='R';
  const cellName=lbCell.kind==='RL'?RL_LABEL[lbCell.key]:lbCell.key;
  const btn=(kind,key,lab)=>`<button class="cellbtn ${lbCell.kind===kind&&lbCell.key===key?'on':''}" onclick='setCell("${kind}","${key}")'>${lab||key}</button>`;
  const picker=`<div class="lb-pick card">
    <div class="grp"><span class="klabel" style="min-width:70px">Schemes</span>${D.schemes.map(s=>btn('S',s)).join('')}${btn('RL','MAN','MAN ROLLUP')}${btn('RL','ZONE','ZONE ROLLUP')}</div>
    <div class="grp"><span class="klabel" style="min-width:70px">Routes</span>${D.routes.map(r=>btn('R',r)).join('')}</div></div>`;
  const rows=[];
  for(const p of D.players){
    if(pos!=='ALL'&&p.pos!==pos) continue;
    const c=lbCell.kind==='S'?p.schemes[lbCell.key]:lbCell.kind==='R'?p.routes[lbCell.key]:p.rollups[lbCell.key];
    if(c&&c.q&&c.pctl!=null) rows.push([p,c]);
  }
  rows.sort((a,b)=>b[1].yprr-a[1].yprr);
  const mWR=metaFor('WR',lbCell.kind,lbCell.key), mTE=metaFor('TE',lbCell.kind,lbCell.key);
  const mx=Math.max(mWR.max||0,mTE.max||0)||3.5;
  const body=rows.slice(0,30).map(([p,c],i)=>{
    const k=cls(c);
    const col=k==='e'?'var(--elite)':k==='w'?'var(--weak)':'#4a5578';
    return `<tr class="${k==='e'?'el':''}" onclick="pick('${p.key}')">
      <td class="rk">${i+1}</td>
      <td class="l">${p.name}<span class="tm">${p.team}</span></td>
      <td><span class="pos ${p.pos}">${p.pos}</span></td>
      <td class="yy"><span class="minitrack"><i style="width:${Math.min(100,100*c.yprr/mx)}%;background:${col}"></i></span>${c.yprr.toFixed(2)}</td>
      <td><span class="pc ${k}">${c.pctl}th</span></td>
      <td>${fmt(c.tprr)}</td>
      <td>${c.catch!=null?Math.round(c.catch*100)+'%':'—'}</td>
      <td>${fmt(c.yac_rec,1)}</td>
      <td>${c.adot!=null?c.adot.toFixed(1):'—'}</td>
      <td>${c.rte}</td></tr>`;
  }).join('');
  const nq=(pos==='ALL'?(mWR.nq||0)+(mTE.nq||0):(pos==='WR'?mWR.nq||0:mTE.nq||0));
  document.getElementById('main').innerHTML=picker+`
    <div class="lbhead"><h2>Elite vs ${cellName}${isR?' routes':''}</h2>
      <span class="meta klabel">${nq} qualified ${pos==='ALL'?'WR/TE':pos+'s'} · min ${isR?D.min_rte_route:D.min_rte} routes · sorted by YPRR</span></div>
    <div class="card" style="padding:6px 12px">
    <table><thead><tr><th>#</th><th class="l">Player</th><th>Pos</th><th>YPRR</th><th>Pctl</th><th>TPRR</th><th>Catch%</th><th>YAC/Rec</th><th>aDOT</th><th>Routes</th></tr></thead>
    <tbody>${body}</tbody></table></div>
    <div class="foot">PCTL IS WITHIN-POSITION (WR VS WR, TE VS TE) EVEN WHEN LIST IS MIXED. CLICK A ROW FOR THE PLAYER PROFILE.
    MINT ROWS = ≥${D.elite_pctl}TH PCTL SPECIALISTS AT ${cellName.toUpperCase()}.</div>`;
}
function setCell(kind,key){ lbCell={kind,key}; renderMain(); }

function renderMain(){ mode==='player'?renderPlayer():renderElite(); }
function render(){
  document.getElementById('mb-player').classList.toggle('on',mode==='player');
  document.getElementById('mb-elite').classList.toggle('on',mode==='elite');
  document.getElementById('side').style.display=mode==='player'?'block':'none';
  document.getElementById('wrap').style.gridTemplateColumns=mode==='player'?'284px 1fr':'1fr';
  renderList(); renderMain();
  if(mode==='player'){ const s=document.querySelector('.prow.sel'); if(s) s.scrollIntoView({block:'center'}); }
}
// deep links: #player=<fnkey with -> or #elite=<cellkey>&kind=S|R|RL&pos=WR
(function(){
  const h=decodeURIComponent(location.hash.slice(1));
  if(h.startsWith('player=')){ const k=h.slice(7).replace(/-/g,' '); if(byKey[k]){selKey=k;mode='player';} }
  else if(h.startsWith('elite=')){
    mode='elite';
    const ps=new URLSearchParams(h);
    const key=ps.get('elite'), kind=ps.get('kind')||'S', pp=ps.get('pos');
    if(key) lbCell={kind,key};
    if(pp) { pos=pp; document.querySelectorAll('#pf span').forEach(s=>s.classList.toggle('on',s.dataset.p===pp)); }
  }
  render();
})();
</script></body></html>'''

if __name__ == '__main__':
    main()
