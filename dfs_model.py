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
import env_blend   # THE sanctioned environment formula: Vegas O/U x team_ceiling (PLAYBOOK C5)
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

# ---- game-script multiplier (from game_sim.py) — STATED PRIORS, revert with K_SCRIPT_*=0.0 ----
# Given the same environment (implied total), HOW the points come — run vs pass — depends on game
# flow: a lead back cashes when his team controls with a lead; a WR/QB cash when their team trails
# or the game shoots out. game_sim quantifies both; this tilts the play score by that script fit.
# Not backtested on 2026 (no actuals); capped so it refines rather than dominates. (PLAYBOOK: env
# is implied total; this is the orthogonal run/pass split, so it is NOT double-counting.)
# REVERTED 2026-07 to 0.0 — the 2025 position x script backtest (boom/gamelog actuals vs nflverse
# closing lines) showed the stated-prior tilt DOUBLE-COUNTS implied total and is MIS-SIGNED for
# favorites: after removing implied total, a 10+ favorite RB scores -1.1 BELOW its team-total
# prediction (blowout starter-rest), not above. Only dog pass-catchers show a small (+1.1) real
# residual. Plumbing retained; coefficients zeroed pending PROE-based recalibration via the same
# implied-total-isolation method. Revert-to-prior: K_SCRIPT_RB=0.35, K_SCRIPT_PASS=0.30.
K_SCRIPT_RB   = 0.0
K_SCRIPT_PASS = 0.0
SCRIPT_CAP    = 0.12   # |script_mult - 1| ceiling
_gs = J('game_sim.json')
SCRIPT = {}   # team -> {lead_big, trail, shootout} for THIS week
for _g in (_gs.get('weeks', {}).get(str(WK), {}) or {}).get('games', []):
    _sh = _g.get('script', {}).get('shootout_bothpass', 15)
    for _tm, _d in _g.get('script', {}).get('script_pass_lean', {}).items():
        SCRIPT[_tm] = {'lead_big': _d.get('lead_big_p', 25), 'trail': _d.get('trail_p', 25), 'shootout': _sh}

def script_mult(pos, team):
    sc = SCRIPT.get(team)
    if not sc: return 1.0
    if pos == 'RB':
        tilt = sc['lead_big'] - 25                                     # lead big -> more carries
        if tilt < 0:
            tilt *= 0.5   # trailing dings RBs only HALF: pass-catching backs stay involved (v1 limit:
                          # not yet role-aware; a pure early-down back loses more than a receiving back)
        m = 1 + K_SCRIPT_RB * tilt / 100.0
    else:  # QB/WR/TE
        pass_tilt = (sc['trail'] - 25) + 0.4 * (sc['shootout'] - 15)    # trail/shootout -> more pass volume
        m = 1 + K_SCRIPT_PASS * pass_tilt / 100.0
    return max(1 - SCRIPT_CAP, min(1 + SCRIPT_CAP, m))

# ---- PROE pass/run CONVERSION multiplier (calibrated: validate_proe_conversion.py) ----
# The env term (implied total) sets a team's points; PROE reallocates WITHIN the team: on a
# pass-over-expected offense the WR/TE convert MORE fantasy than the total alone implies and the RBs
# LESS — run-lean is the mirror. Calibrated on COMPLETE 2024+2025 per-game data (team-week grain),
# residualized on implied total so it is ORTHOGONAL to the env term (NOT double-counting, PLAYBOOK
# C5), and REPLICATED across both seasons (trailing corr +0.12/+0.14; RB mirror -0.34/-0.37).
# Coefficients = forward-usable (trailing) DK slope / position-group DK baseline:
#   PC(WR/TE) +0.674/45.2 = +0.015    RB -0.285/22.6 = -0.013    QB +0.289/17.0 -> +0.010 (shrunk:
#   single-year, weaker r=+0.14). Input: proe_tendency_2026.json = 2025 ACTUAL + bounded carousel
# assumption. Capped so it refines, never dominates. This is the validated replacement for the
# reverted, mis-signed script_mult (K_SCRIPT_*=0).
K_PROE_PC = 0.015    # WR/TE: +0.674 DK/pt / 45.2 base; script-FLAT (slopes +0.55..+0.76), stays static
K_PROE_RB = -0.011   # RB NON-LED baseline: -0.23 DK/pt / 22.6 base (was -0.013 = script-avg; re-based)
K_PROE_QB = 0.010    # QB shrunk (single-year, r=+0.14)
PROE_CAP  = 0.12
# --- RB script coupling (validate_proe_conversion.py interaction probe) ---------------------------
# The RB conversion is the one piece that is SCRIPT-dependent: the RB slope roughly DOUBLES when a
# team actually LEADS (-0.43 DK/pt led vs -0.23 close/trailed) — low-PROE favorites pound the rock in
# a lead (RB resid +7.0), high-PROE favorites keep throwing (RB resid -2.9). Data shows trailing ~=
# close, so amplification is ONE-SIDED: baseline off a lead, scaled UP by the sim's projected lead_big_p.
# This is where game_sim's script distribution finally feeds player scoring. Center = observed
# lead_big_p mean (~22); LEAD_AMP set so a heavy favorite (~40) gets ~1.8x the RB tilt; capped 2x.
SCRIPT_CENTER = 22.0
LEAD_AMP      = 0.8
LEAD_AMP_CAP  = 2.0
_pt = J('proe_tendency_2026.json').get('teams', {})
PROE_2026 = {ab(t): d.get('proe_2026') for t, d in _pt.items()}

def _rb_lead_amp(team):
    """RB-tilt amplifier from the sim's projected lead_big_p; 1.0 off a lead, up to LEAD_AMP_CAP."""
    lb = (SCRIPT.get(team) or SCRIPT.get(ab(team)) or {}).get('lead_big', SCRIPT_CENTER)
    return min(LEAD_AMP_CAP, 1.0 + LEAD_AMP * max(0.0, (lb - SCRIPT_CENTER) / SCRIPT_CENTER))

def proe_convert(pos, team):
    """WR/TE up, RB down (amplified when the sim projects a lead), QB up-small as team PROE rises."""
    p = PROE_2026.get(ab(team))
    if p is None:
        return 1.0
    if pos == 'RB':
        k = K_PROE_RB * _rb_lead_amp(team)
    elif pos == 'QB':
        k = K_PROE_QB
    else:
        k = K_PROE_PC
    m = 1 + k * p
    return max(1 - PROE_CAP, min(1 + PROE_CAP, m))

# ---- Red-zone / TD-equity multiplier (build_rz_equity.py; validated) --------------------------
# The implied total sets team points; RZ role sets WHO gets the 6-point plays. Validated: RZ target
# share -> end-zone TDs (r=+0.29, WR/TE); RB TD/game is YoY-stable (r=+0.51). Wired as an INTERACTION
# with the implied total (not a flat bonus): a goal-line-dominant player captures MORE of the team's
# TDs when there is more scoring to capture, and nothing when the team is implied low. Centered so
# average-role players are unaffected and the baseline TD rate (already in the ceiling) is not
# double-counted. RB steeper than PC (backs are more TD-dependent). Capped so it refines, not dominates.
K_RZ_PC = 0.025
K_RZ_RB = 0.040
RZ_CAP  = 0.10
_rz = J('rz_equity_2026.json').get('teams', {})
RZ_Z = {fn(k): v.get('rz_role_z') for k, v in _rz.items()}

def rz_convert(pos, name, imp):
    """TD-equity tilt scaled by the implied total; 1.0 for average-role players or low-total teams."""
    z = RZ_Z.get(fn(name))
    if z is None or imp is None:
        return 1.0
    k = K_RZ_RB if pos == 'RB' else (K_RZ_PC if pos in ('WR', 'TE') else 0.0)
    if k == 0.0:
        return 1.0
    env_scale = max(0.0, min(1.5, (imp - 21) / 7.0))   # TDs matter only when there is scoring to capture
    m = 1 + k * z * env_scale
    return max(1 - RZ_CAP, min(1 + RZ_CAP, m))
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

# League-average man-coverage rate — baseline for frequency-weighting the man/zone edges.
# A player's man-beating strength only cashes as often as the defense actually PLAYS man; a
# heavy-zone defense (e.g. SF ~20% man) makes a man edge far less actionable than raw softness
# implies, and vice-versa for a high-man defense (e.g. NYG ~37%).
_mrs = [(v.get('shell') or {}).get('man_rate') for v in defs.values() if isinstance(v, dict)]
_mrs = [x for x in _mrs if x is not None]
AVG_MAN = round(sum(_mrs) / len(_mrs), 1) if _mrs else 26.0

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
                # frequency-weight man/zone by how often THIS defense actually plays that coverage
                mr = (d.get('shell') or {}).get('man_rate')
                freq_w = 1.0; cov_rate = None
                if mr is not None and label in ('vs Man', 'vs Zone'):
                    if label == 'vs Man':
                        cov_rate = mr; freq_w = mr / AVG_MAN if AVG_MAN else 1.0
                    else:  # vs Zone: complement of man rate
                        cov_rate = 100 - mr; freq_w = (100 - mr) / (100 - AVG_MAN) if AVG_MAN < 100 else 1.0
                    freq_w = max(0.3, min(1.8, freq_w))
                strong = pp >= 60; soft = dd >= 60
                score = round((pp / 100.0) * (dd / 100.0) * 100 * freq_w, 1)
                # a coverage-axis smash requires the defense to play that coverage at least ~average often
                smash = bool(strong and soft and freq_w >= 0.8)
                e = {'axis': label, 'player_pctl': round(pp, 0), 'def_soft_pctl': round(dd, 0),
                     'score': score, 'smash': smash}
                if cov_rate is not None:
                    e['cov_rate'] = round(cov_rate, 0); e['freq_w'] = round(freq_w, 2)
                edges.append(e)
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
    # weekly play score: ceiling-anchored, matchup-tilted, environment (implied total)-aware, then
    # PROE-CONVERTED (run/pass reallocation within the team — validate_proe_conversion.py). script_mult
    # is retained plumbing but zeroed (reverted, mis-signed); proe_convert is the validated replacement.
    base = (ceil or (proj * 2.2 if proj else 0)) or 0
    smult = script_mult(pos, team)
    pconv = proe_convert(pos, team)
    rzm = rz_convert(pos, name, imp)
    play = round(base * (1 + edge_score / 250.0) * (1 + ((imp or 21) - 21) / 60.0) * smult * pconv * rzm, 1)
    players.append({'name': name, 'pos': pos, 'team': team, 'opp': opp, 'home': home, 'dome': dome,
                    'proj': proj, 'ceil': ceil, 'total': total, 'imp': imp,
                    'edges': edges, 'n_smash': len(smash), 'edge_score': edge_score,
                    'quals': quals[:4], 'script_mult': round(smult, 3),
                    'proe_mult': round(pconv, 3), 'rz_mult': round(rzm, 3), 'play': play})

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
# environment rank = BLENDED score (Vegas anchor + team-ceiling upside conditions), never O/U alone
for g in games.values():
    a, b = g['teams']
    g['blend'] = env_blend.blend_total(g['total'], a, b)
anchor_games = sorted([g for g in games.values() if g['total']], key=lambda g: -(g['blend'] or 0))[:6]

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
       'env_note': 'anchor_games ranked by blend (Vegas O/U + team_ceiling adj, env_blend.py); total = raw posted O/U',
       'anchor_games': [{'g': f"{a} vs {b}", 'total': gg['total'], 'blend': gg['blend']} for (a, b), gg in
                        sorted(games.items(), key=lambda kv: -(kv[1].get('blend') or 0))[:8] if gg['total']]}
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
