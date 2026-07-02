#!/usr/bin/env python3
"""Build cc_context.json — the per-player 4-layer context that the command center drilldown renders.
Layers (all from REAL pulled data, never asserted):
  1. SPLITS   — situational man/zone YPRR + real NFL Pro EPA (Rec EPA/route, EPA/DB, RYOE/att,
                separation, YACOE, CROE, pressure) + 2024->2025 trajectory (YoY) from nfl_pro_epa.json
  2. SCHEME   — 2026 playcaller fit: scheme_2026.json dials (motion/vertical/passcatch/scramble) + note
  3. OPP      — opportunity/vacated: route share + alignment (opportunity.json) + team vacated targets
                + this player's own added/vacated targets (vacated-targets__players.csv)
  4. MATCHUP  — fantasy-playoff (W15-17) opponent defense strength from defense_2026_matchup.json
Keyed by core.fn(name). Pure local assembly; no auth, no fabrication."""
import core, csv, json, os, re
fn = core.fn
HERE = os.path.dirname(os.path.abspath(__file__))
def J(p): return json.load(open(os.path.join(HERE, p), encoding='utf-8'))

# ---------- inputs ----------
feats = list(csv.DictReader(open(core.P('features.csv'), encoding='utf-8')))
scheme = J('scheme_2026.json')
opp = J('boom/opportunity.json')
matchup = json.load(open(core.find_data('dfs_review', 'out', 'defense_2026_matchup.json'), encoding='utf-8'))  # parent-level fresh copy (core.find_data), matching sync_boom_defense / boom_foundation / build_splits — not the stale repo-local copy
nflpro = J('nfl_pro_epa.json')

# vacated targets at the player level (NJ feed)
VAC_PLAYER = {}
vp = 'ffdataroma_draft_guide_export/ffdataroma/csv/vacated-targets__players.csv'
if os.path.exists(core.P(vp)):
    for r in csv.DictReader(open(core.P(vp), encoding='utf-8')):
        VAC_PLAYER.setdefault(fn(r['name']), []).append(r)

def num(v):
    if v in (None, '', 'None'): return None
    try: return float(v)
    except: return None

# ---------- build NFL Pro YoY index (key -> {2025:{...}, 2024:{...}}) per category ----------
ARR = {'receiving': 'rows', 'passing': 'rows', 'rushing': 'rows'}
YOY = {}  # fn(name) -> {'cat':..., '2025':row, '2024':row}
for season in ('2025', '2024'):
    for cat in ('receiving', 'passing', 'rushing'):
        for row in nflpro['seasons'][season][cat]['rows']:
            k = fn(row.get('displayName', ''))
            YOY.setdefault(k, {'cat': cat}).setdefault(season, row)

def yoy_metric(k):
    """Return the headline per-unit efficiency metric for 2025 and 2024 + delta, with a label."""
    e = YOY.get(k)
    if not e: return None
    cat = e['cat']
    def per(season):
        r = e.get(season)
        if not r: return None
        if cat == 'receiving':
            rt = r.get('rt') or 0
            return round(r['epa'] / rt, 3) if rt else None
        if cat == 'passing':
            return round(r.get('epaDb'), 3) if r.get('epaDb') is not None else None
        if cat == 'rushing':
            return round(r.get('epaAtt'), 3) if r.get('epaAtt') is not None else None
    lab = {'receiving': 'Rec EPA/route', 'passing': 'EPA/dropback', 'rushing': 'Rush EPA/att'}[cat]
    a, b = per('2025'), per('2024')
    d = round(a - b, 3) if (a is not None and b is not None) else None
    return {'label': lab, 'y2025': a, 'y2024': b, 'delta': d}

# ---------- matchup: parse W15-17 opponent from the schedule-encoded w15/w16/w17 cells ----------
def opp_of(cell, team):
    """w-cells look like 'DAL' (vs DAL) or 'LAR@TB' (player's team LAR at TB -> opp TB). Return opp code or None."""
    if not cell: return None
    cell = cell.strip()
    if cell.upper() in ('BYE', 'OUT', ''): return None
    if '@' in cell:
        a, b = cell.split('@', 1)
        a, b = core.norm_team(a.strip()), core.norm_team(b.strip())
        tm = core.norm_team(team)
        return b if a == tm else (a if b == tm else b)
    return core.norm_team(cell)

# ---------- assemble ----------
ctx = {}
for f in feats:
    nm = f['name']; k = fn(nm); pos = f['pos']; tm = core.norm_team(f['team'])

    # ---- Layer 1: SPLITS ----
    splits = {'pos': pos}
    if pos in ('WR', 'TE', 'RB'):
        for c in ('yprr_man', 'yprr_zone', 'man_zone_delta', 'man_route_sh', 'adot25',
                  'rec_epa_route', 'rec_separation', 'rec_yacoe', 'rec_croe',
                  'route_yprr', 'route_tprr', 'deep_route_sh'):
            v = num(f.get(c))
            if v is not None: splits[c] = v
    if pos == 'QB':
        for c in ('qb_epa_db', 'qb_cpoe', 'qb_ttt', 'qb_pressure_rate', 'sack_pct25',
                  'ypa25', 'qb_anya', 'deep_ball_sh', 'qb_scramble', 'qb_rush_ypg'):
            v = num(f.get(c))
            if v is not None: splits[c] = v
    if pos == 'RB':
        # success-rate metrics from FP RunType are empty (=0) in the reduced sandbox FP data;
        # a true 0% success is implausible, so treat exact-zero as missing rather than show a
        # misleading 0.00 (these repopulate from the full FP charting on a --full run).
        _zero_is_missing = {'zone_succ', 'gap_succ', 'stuff_pct'}
        for c in ('zone_run_sh', 'zone_succ', 'gap_succ', 'stuff_pct',
                  'rush_epa_att', 'ryoe_att', 'rb_topspeed', 'rb_rec_ypg', 'outside_run_sh'):
            v = num(f.get(c))
            if v is not None and not (c in _zero_is_missing and v == 0):
                splits[c] = v
    yy = yoy_metric(k)
    if yy: splits['yoy'] = yy

    # ---- Layer 2: SCHEME (playcaller fit) ----
    # only an OFFENSIVE play-caller change is relevant to a skill player; teams present in
    # scheme_2026 for a DEFENSE-only change (off = continuity) carry null playcaller/empty dials
    # -> treat as continuity (no scheme block; front-end shows the continuity message).
    sc = scheme.get(tm)
    if sc and not (sc.get('playcaller') or sc.get('off')):
        sc = None
    scheme_blk = None
    if sc:
        scheme_blk = {'playcaller': sc.get('playcaller'), 'note': sc.get('note'),
                      'dials': sc.get('off', {})}
        # human fit cues: which of THIS player's strengths the 2026 caller amplifies
        d = sc.get('off', {}); cues = []
        if pos in ('WR', 'TE'):
            if d.get('motion') == 1: cues.append('+motion (scheme separation)')
            if d.get('vertical') == 1: cues.append('+vertical (aDOT/ceiling)')
            if d.get('vertical') == -1: cues.append('-vertical (shorter aDOT)')
        if pos == 'RB':
            if d.get('passcatch') == 1: cues.append('+RB pass game (receiving role)')
        if pos == 'QB':
            if d.get('scramble') == -1: cues.append('-scramble (more pocket)')
            if d.get('vertical') == 1: cues.append('+vertical (downfield)')
        if cues: scheme_blk['fit'] = cues

    # ---- Layer 3: OPP (opportunity / vacated) ----
    opp_blk = {}
    op = opp.get(k)
    if op:
        for c in ('route_pct', 'routes_2yr', 'align', 'align_pct'):
            if op.get(c) is not None: opp_blk[c] = op[c]
    tv = num(f.get('team_vacated_tgt'))
    if tv is not None: opp_blk['team_vacated_tgt'] = tv
    ts = num(f.get('tgt_share'));
    if ts is not None: opp_blk['tgt_share'] = ts
    if VAC_PLAYER.get(k):
        moves = []
        for r in VAC_PLAYER[k]:
            moves.append({'dir': r.get('direction'), 'tgts': num(r.get('targets')),
                          'rush': num(r.get('rushes')), 'from': r.get('priorTeam'), 'to': r.get('currentTeam')})
        opp_blk['self_moves'] = moves

    # ---- Layer 4: MATCHUP (W15-17 opponent defense) ----
    metric = 'run' if pos == 'RB' else 'cov'
    wk = []
    for lab in ('w15', 'w16', 'w17'):
        o = opp_of(f.get(lab), tm)
        if o and o in matchup:
            wk.append({'wk': lab[1:], 'opp': o, 'val': round(matchup[o].get(metric), 1) if matchup[o].get(metric) is not None else None})
    matchup_blk = None
    if wk:
        vals = [w['val'] for w in wk if w['val'] is not None]
        matchup_blk = {'metric': metric, 'weeks': wk,
                       'avg': round(sum(vals) / len(vals), 1) if vals else None}

    rec = {}
    if len(splits) > 1: rec['splits'] = splits
    if scheme_blk: rec['scheme'] = scheme_blk
    if opp_blk: rec['opp'] = opp_blk
    if matchup_blk: rec['matchup'] = matchup_blk
    if rec:
        rec['pos'] = pos
        ctx[k] = rec

json.dump(ctx, open(core.P('cc_context.json'), 'w'), ensure_ascii=False)

# ---------- coverage report + direction sanity ----------
n_sp = sum(1 for v in ctx.values() if 'splits' in v)
n_sc = sum(1 for v in ctx.values() if 'scheme' in v)
n_op = sum(1 for v in ctx.values() if 'opp' in v)
n_mt = sum(1 for v in ctx.values() if 'matchup' in v)
n_yoy = sum(1 for v in ctx.values() if v.get('splits', {}).get('yoy'))
print(f"cc_context.json: {len(ctx)} players | splits {n_sp} · scheme {n_sc} · opp {n_op} · matchup {n_mt} · YoY {n_yoy}")
top = sorted(matchup.items(), key=lambda kv: -(kv[1].get('cov') or 0))[:5]
bot = sorted(matchup.items(), key=lambda kv: (kv[1].get('cov') or 0))[:5]
print("matchup direction — strongest cov (toughest):", [f"{t}:{v['cov']}" for t, v in top])
print("                  — weakest cov (softest):   ", [f"{t}:{v['cov']}" for t, v in bot])
for nm in ['Puka Nacua', "Ja'Marr Chase", 'Bijan Robinson', 'Josh Allen']:
    k = fn(nm); r = ctx.get(k, {})
    sp = r.get('splits', {}); mt = r.get('matchup', {}); sc = r.get('scheme', {})
    print(f"  {nm:18s} yoy={sp.get('yoy')} | playoff {mt.get('metric')} avg={mt.get('avg')} | caller={sc.get('playcaller','—')}")
