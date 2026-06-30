#!/usr/bin/env python3
"""dfs_model.py — the weekly DFS model.  python3 dfs_model.py --week N

For a given week it produces, for every fantasy-relevant player:
  * the MATCHUP EDGE — the player's statistically-significant strengths (man/zone/deep/slot/by-position
    percentiles from real charting) lined up against THIS WEEK's opponent defense's softness on the
    SAME axes (defense_splits.json). Where player-strong meets defense-soft = a green edge.
  * the QUALITATIVE levers (scheme/playcaller/opportunity from cc_context) — good-to-know, not stat-sig.
  * a WHO-TO-PLAY weekly score (ceiling x matchup edge).
And it builds LINEUP-CONSTRUCTION TEMPLATES from winner structure (STRATEGY_SPEC + real correlations):
  stack a QB with 1-2 same-team catchers + an opponent bring-back in a HIGH-TOTAL game, concentrate one
  anchor game with 4-5 correlated pieces, pair with leverage/ceiling darts.

Offseason note (June 2026): in-season slates don't exist yet, so the model runs on the projection /
Vegas / matchup basis and is week-parameterized — point it at any week; it reads that week's opponents
and Vegas totals. Output: dfs_week.html + dfs_week.json.
"""
import core, pandas as pd, numpy as np, json, os, argparse, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
def J(p):
    fp = os.path.join(HERE, p)
    return json.load(open(fp, encoding='utf-8')) if os.path.exists(fp) else {}
fn = core.fn; ab = core.team_abbr

ap = argparse.ArgumentParser()
ap.add_argument('--week', type=int, default=15, help="NFL week (1-18). Default 15 (fantasy playoffs).")
ap.add_argument('--pos', default=None, help="optional position filter for the console summary")
A = ap.parse_args()
WK = A.week

# ---------- inputs (self-provision the defense split-parity layer if missing) ----------
if not os.path.exists(os.path.join(HERE, 'defense_splits.json')):
    import subprocess, sys as _s
    subprocess.run([_s.executable, os.path.join(HERE, 'build_defense_splits.py')])
defs = J('defense_splits.json')
sched = J('boom/schedule2026.json')
profiles = J('profiles/player_profiles.json')
ctx = J('cc_context.json')
corr = J('pipeline/correlation_structure.json')
feat = list(pd.read_csv(os.path.join(HERE, 'features.csv')).to_dict('records'))
# weekly Vegas totals (team-week) for shootout / bring-back logic
VEG = {}
vp = os.path.join(HERE, 'ffdataroma_draft_guide_export/ffdataroma/csv/weekly-vegas-lines.csv')
if os.path.exists(vp):
    for r in pd.read_csv(vp).to_dict('records'):
        t = ab(r.get('team')); wk = r.get('week')
        if t and pd.notna(wk):
            VEG.setdefault(t, {})[int(wk)] = {'total': r.get('total'), 'imp': r.get('teamImplied'), 'spread': r.get('spread')}

def opp_of(team, wk):
    for g in sched.get(team, []):
        if g.get('wk') == wk:
            return g.get('opp'), g.get('home'), g.get('dome')
    return None, None, None

# player-axis (profile situation key) -> defense-axis (defense_splits key) for split-parity line-up
REC_AXES = [
    ('vs Man', 'rec_vs_man', 'vs_man'),
    ('vs Zone', 'rec_vs_zone', 'vs_zone'),
    ('Deep', 'rec_deep_routes', 'deep'),
    ('Deep', 'rec_deep', 'deep'),
]

def player_pct(prof, key):
    s = (prof.get('situations') or {}).get(key)
    return s.get('pct') if s else None

def edges_for(name, pos, team, opp):
    """Return (edges, best_axis) lining the player's strengths vs the opp defense's softness."""
    prof = profiles.get(name) or profiles.get(name.title()) or {}
    d = defs.get(opp, {})
    edges = []
    if pos in ('WR', 'TE'):
        used = set()
        for label, pkey, dkey in REC_AXES:
            if label in used:
                continue
            pp = player_pct(prof, pkey)
            dd = (d.get(dkey) or {}).get('softness_pctl')
            if pp is not None and dd is not None:
                strong = pp >= 60; soft = dd >= 60
                score = round((pp / 100.0) * (dd / 100.0) * 100, 1)
                edges.append({'axis': label, 'player_pctl': round(pp, 0), 'def_soft_pctl': round(dd, 0),
                              'score': score, 'smash': bool(strong and soft)})
                used.add(label)
        # position-group FPAA allowed (soft to this position)
        bypos = d.get('by_pos') or {}
        fp = bypos.get('wr1' if pos == 'WR' else 'te', bypos.get(pos.lower()))
        if fp is not None:
            edges.append({'axis': f'{pos} fantasy pts allowed', 'player_pctl': None,
                          'def_soft_pctl': None, 'fpaa': fp, 'score': round(max(0, fp) * 4, 1),
                          'smash': fp >= 2.5})
    elif pos == 'RB':
        u = d.get('units') or {}; rd = u.get('run_def_pctl')
        if rd is not None:
            soft = 100 - rd  # low run-def pctl = soft run D = good RB matchup
            edges.append({'axis': 'Run defense', 'player_pctl': None, 'def_soft_pctl': round(soft, 0),
                          'score': round(soft, 1), 'smash': soft >= 60})
        bypos = d.get('by_pos') or {}
        if bypos.get('rb') is not None:
            edges.append({'axis': 'RB fantasy pts allowed', 'fpaa': bypos['rb'],
                          'score': round(max(0, bypos['rb']) * 4, 1), 'smash': bypos['rb'] >= 2.5})
    elif pos == 'QB':
        u = d.get('units') or {}; pc = u.get('pass_cov_pctl'); pr = u.get('pass_rush_pctl')
        if pc is not None:
            edges.append({'axis': 'Pass coverage', 'def_soft_pctl': round(100 - pc, 0),
                          'score': round(100 - pc, 1), 'smash': (100 - pc) >= 60})
        if pr is not None:
            edges.append({'axis': 'Pass rush (lower=safer)', 'def_soft_pctl': round(100 - pr, 0),
                          'score': round((100 - pr) * 0.5, 1), 'smash': False})
    edges.sort(key=lambda e: -e['score'])
    return edges

def num(v):
    try:
        f = float(v); return f if f == f else None
    except Exception:
        return None

# ---------- per-player weekly read ----------
players = []
for f in feat:
    name = f.get('name'); pos = f.get('pos'); team = ab(f.get('team'))
    if pos not in ('QB', 'RB', 'WR', 'TE'):
        continue
    opp, home, dome = opp_of(team, WK)
    proj = num(f.get('proj_pg'))
    if proj is None or proj < 4:
        continue   # playable floor: skip unprojected / deep-bench names (no stale dk_max25 fallback)
    ceil = num(f.get('p95')) or round(proj * 2.3, 1)   # ceiling from sim p95, else proj-scaled (NOT dk_max25)
    veg = VEG.get(team, {}).get(WK, {})
    total = num(veg.get('total')); imp = num(veg.get('imp'))
    edges = edges_for(name, pos, team, opp) if opp else []
    smash = [e for e in edges if e.get('smash')]
    edge_score = round(sum(e['score'] for e in edges[:3]) / 3, 1) if edges else 0
    # qualitative levers
    c = ctx.get(fn(name), {})
    sc = c.get('scheme') or {}
    quals = []
    if sc.get('fit'):
        quals += sc['fit']
    if sc.get('playcaller'):
        quals.append('caller: ' + sc['playcaller'].split('(')[0].strip())
    opp_blk = c.get('opp') or {}
    if (opp_blk.get('team_vacated_tgt') or 0) and opp_blk['team_vacated_tgt'] > 40:
        quals.append(f"{opp_blk['team_vacated_tgt']:.0f}% team tgts vacated")
    # weekly play score: ceiling-anchored, matchup-tilted, environment (implied total)-aware
    base = (ceil or (proj * 2.2 if proj else 0)) or 0
    play = round(base * (1 + edge_score / 250.0) * (1 + ((imp or 21) - 21) / 60.0), 1)
    players.append({'name': name, 'pos': pos, 'team': team, 'opp': opp, 'home': home, 'dome': dome,
                    'proj': proj, 'ceil': ceil, 'total': total, 'imp': imp,
                    'edges': edges, 'n_smash': len(smash), 'edge_score': edge_score,
                    'quals': quals[:4], 'play': play})

players.sort(key=lambda p: -p['play'])
for i, p in enumerate(players):
    p['rank'] = i + 1
    p['pos_rank'] = sum(1 for q in players[:i + 1] if q['pos'] == p['pos'])

# ---------- lineup-construction templates from winner structure ----------
# rank candidate "anchor games" by combined implied total (shootout = bring-back territory)
games = {}
for p in players:
    if not p['opp']:
        continue
    key = tuple(sorted([p['team'], p['opp']]))
    g = games.setdefault(key, {'teams': key, 'total': p['total'], 'players': []})
    g['players'].append(p)
anchor_games = sorted([g for g in games.values() if g['total']], key=lambda g: -(g['total'] or 0))[:6]

def best(team, pos, n=1):
    pool = [p for p in players if p['team'] == team and p['pos'] == pos]
    return pool[:n]

templates = []
for g in anchor_games[:4]:
    a, b = g['teams']
    qb = (best(a, 'QB') + best(b, 'QB'))
    qb = sorted(qb, key=lambda p: -p['play'])[:1]
    if not qb:
        continue
    qbt = qb[0]['team']; oppt = b if qbt == a else a
    catchers = sorted(best(qbt, 'WR', 3) + best(qbt, 'TE', 1), key=lambda p: -p['play'])[:2]
    bringback = sorted(best(oppt, 'WR', 2) + best(oppt, 'TE', 1), key=lambda p: -p['play'])[:1]
    high_total = (g['total'] or 0) >= (corr.get('bringback_qb_oppwr1', {}).get('total_median', 45) or 45)
    templates.append({
        'anchor_game': f"{a} vs {b}", 'total': g['total'], 'high_total': high_total,
        'qb': qbt, 'qb_player': qb[0]['name'],
        'stack': [c['name'] for c in catchers],
        'bringback': bringback[0]['name'] if (bringback and high_total) else None,
        'shape': 'QB + 2 same-team catchers' + (' + opponent bring-back (high total)' if (bringback and high_total) else ' (low total: skip bring-back)'),
    })

WINNER_RULES = [
    ("Anchor one game", "Concentrate 4-5 correlated pieces on a SINGLE game you expect to spike (~+15% finals tail at equal mean). Don't scatter."),
    ("Stack the QB", "QB + 1-2 same-team pass-catchers is the core engine (real corr: QB-WR1 r=0.35, QB-WR2 r=0.34, QB-TE strong; WR-WR ~0)."),
    ("Bring back only in shootouts", "Add an opponent pass-catcher ONLY when the game total is high (bring-back r=0.16 in high-total vs 0.06 low). Median total ~45."),
    ("Stop at 4-5 pieces", "Past 4-5 same-game pieces you buy redundant variance and starve roster needs."),
    ("Ceiling over floor", "Single-week DFS pays the right tail. Prefer high-CV/spike WR & rushing QBs over safe-floor chalk where leverage matters."),
]

out = {'week': WK, 'built': None, 'n_players': len(players),
       'players': players, 'templates': templates, 'winner_rules': WINNER_RULES,
       'anchor_games': [{'g': f"{a} vs {b}", 'total': gg['total']} for (a, b), gg in
                        sorted(games.items(), key=lambda kv: -(kv[1]['total'] or 0))[:8] if gg['total']]}
json.dump(out, open(os.path.join(HERE, 'dfs_week.json'), 'w'), ensure_ascii=False)
print(f"dfs_week.json: week {WK} | {len(players)} players | {len(templates)} lineup templates | anchor games {len(out['anchor_games'])}")
top = [p for p in players if not A.pos or p['pos'] == A.pos][:12]
print(f"\nTop plays, week {WK} (play score · pos · vs opp · smash edges):")
for p in top:
    sm = ' '.join(f"{e['axis']}" for e in p['edges'] if e.get('smash'))[:48]
    print(f"  {p['rank']:>2} {p['name']:22s} {p['pos']} vs {p['opp'] or '—':3s}  play={p['play']:>5}  edge={p['edge_score']:>4}  {('SMASH: '+sm) if sm else ''}")

# render the weekly page (one command -> dfs_week.html)
import subprocess, sys as _sys
subprocess.run([_sys.executable, os.path.join(HERE, 'render_dfs_week.py')])
