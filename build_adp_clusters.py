#!/usr/bin/env python3
"""ADP-CLUSTER BEST-PICK BOARD -> adp_cluster_board.html.

The whole point of the flags/ceiling/matchup work: the market (ADP) sets the tiers, and the model's job
is to say WHO IS THE BEST PICK inside a cluster of players going at the same ADP. This board groups the
board into ADP clusters and, within each, ranks by the model's forward-looking composite (flag_ranks:
2026 p95 ceiling 0.30 + portable traits 0.35 + season matchup 0.35), names the model's pick, and flags
the traps (players going at that ADP the model does NOT like). Reads flag_ranks.json (no new modeling)."""
import json, os, html
H = os.path.dirname(os.path.abspath(__file__))
CLUSTER = 8   # players per ADP cluster (a draft neighborhood in a 12-team room)

fr = json.load(open(os.path.join(H, 'flag_ranks.json'), encoding='utf-8'))
players = [v for v in fr['players'].values() if v.get('adp')]
players.sort(key=lambda v: v['adp'])

# ---- cluster by ADP order, size CLUSTER; within a cluster rank by model flag_score ----
clusters = []
for i in range(0, len(players), CLUSTER):
    grp = players[i:i+CLUSTER]
    adps = [p['adp'] for p in grp]
    ranked = sorted(grp, key=lambda v: -(v.get('flag_score') or -9))
    clusters.append({'lo': round(min(adps), 1), 'hi': round(max(adps), 1), 'members': ranked})

# ---- pool percentile of flag_score: the raw composite is centered BELOW zero (median ~-0.22)
#      because the draftable pool is ceiling-skewed, so an absolute fs<0 cut would paint 62% of
#      the board red and mean nothing. Color instead by standing among ALL draftable players. ----
import bisect
fs_sorted = sorted(p['flag_score'] for p in players if p.get('flag_score') is not None)
def fs_pctl(fs):
    if fs is None or not fs_sorted: return None
    return 100.0 * bisect.bisect_right(fs_sorted, fs) / len(fs_sorted)

def score_band(pc):
    if pc is None: return 'na'
    if pc >= 80: return 'love'   # top 20% of the draftable pool
    if pc >= 55: return 'like'
    if pc >= 30: return 'meh'
    return 'fade'                # bottom 30% — normal for late picks, dim not alarming

GAP_REACH = 0.50   # flag a REACH when the cluster's best value beats them by >= this in composite

rows_json = []
for ci, c in enumerate(clusters):
    mem = c['members']
    pick = mem[0]
    pick_fs = pick.get('flag_score')
    pick_adp = pick.get('adp')
    # cluster-relative REACH = the most overpriced player in the neighborhood: among members drafted
    # at/before the pick's ADP (i.e. costing as much or more), the one the model rates LOWEST, and
    # only when that drop-off from the pick is real. A low-rated guy going LAST isn't a trap.
    early = [q for q in mem if q is not pick and q.get('adp') is not None and pick_adp is not None
             and q['adp'] <= pick_adp + 3 and q.get('flag_score') is not None]
    reach_p = min(early, key=lambda x: x['flag_score']) if early else None
    reach_ok = reach_p is not None and pick_fs is not None and (pick_fs - reach_p['flag_score'] >= GAP_REACH)
    for rank_in, p in enumerate(mem):
        fs = p.get('flag_score')
        pc = fs_pctl(fs)
        rows_json.append({
            'cluster': ci, 'lo': c['lo'], 'hi': c['hi'], 'inrank': rank_in,
            'pick': rank_in == 0, 'reach': bool(reach_ok and p is reach_p),
            'name': p['name'], 'pos': p['pos'], 'team': p.get('team'),
            'adp': round(p['adp'], 1), 'fs': round(fs, 2) if fs is not None else None,
            'pctl': round(pc) if pc is not None else None,
            'gap': round(pick_fs - fs, 2) if (fs is not None and pick_fs is not None) else None,
            'band': score_band(pc), 'ceil': p.get('ceil_pctl'), 'trait': p.get('trait_pctl'),
            'smq': p.get('smq_pctl'), 'rmq': p.get('rmq_pctl'), 'pmq': p.get('pmq_pctl'),
            'nfl': p.get('n_flags'), 'delta': p.get('delta'),
            'flags': (p.get('top_flags') or [])[:4]})
DATA = json.dumps(rows_json)
NC = len(clusters)

_tpl = open(os.path.join(H, '_adp_board_template.html'), encoding='utf-8').read()
doc = _tpl.replace('__DATA__', DATA).replace('__NC__', str(NC)).replace('__NPLAYERS__', str(len(players)))
open(os.path.join(H, 'adp_cluster_board.html'), 'w', encoding='utf-8').write(doc)
print(f"adp_cluster_board.html: {NC} clusters, {len(players)} players")
# console preview: pick vs the cluster-relative REACH (most overpriced at that ADP)
reach_by_cluster = {r['cluster']: r for r in rows_json if r.get('reach')}
for ci, c in enumerate(clusters[:12]):
    pick = c['members'][0]; rr = reach_by_cluster.get(ci)
    print(f"  ADP {c['lo']:5.1f}-{c['hi']:5.1f} | PICK {pick['name']:22} ({pick['pos']}, {pick.get('flag_score')})"
          + (f" | REACH {rr['name']} (gap -{rr['gap']})" if rr else ""))
