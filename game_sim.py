#!/usr/bin/env python3
"""game_sim.py — Vegas-anchored GAME-SCRIPT Monte Carlo.  python3 game_sim.py [--week N]

What it is / what it is NOT (read before trusting a number):
  * NOT a from-scratch sim. The repo already has a player-level correlated Monte Carlo
    (pipeline/sim_prod.py + survival_chain.py, 12k sims, shared per-game shock). This adds the
    missing GAME-SCRIPT layer — team score -> total, margin, winner, and the dynamic pass/run
    script — which those don't emit. It reuses their core idea: two teams in a game co-move
    through a shared shock (here, a Gaussian copula).
  * ANCHORED to two Vegas facts (ground truth, ground_truth_registry.json):
      - team implied totals  -> the MEANS (so the simulated total is Vegas-consistent)
      - the spread           -> calibrates dispersion so P(favorite wins) tracks the market
  * SHAPED by our layers: team_ceiling scales each team's variance (higher ceiling = fatter
    boom/bust tail); correlation rises with the total (grounded in the DIRECTION of
    pipeline/correlation_structure.json bring-back r: 0.06 low-total -> 0.16 high-total);
    offense_profile gives the base pass/run lean the script then bends.

  * HONEST LIMIT: the means are real market numbers, but the DISPERSION, CORRELATION and
    SCRIPT-shift mappings are STATED PRIORS (NFL-empirical or user-mandated direction) — there
    are no 2026 actuals to fit yet. Every one has a REVERT/tune knob below. The sim turns
    assumptions into probabilities transparently; it does not manufacture certainty. When real
    results land, calibrate SIGMA_TEAM / RHO_* against them (TODO backtest).
"""
import json, os, argparse
import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
def J(p): return json.load(open(os.path.join(HERE, p), encoding='utf-8'))

# ---------------- STATED PRIORS (tune here; none are backtested on 2026) ----------------
N_SIM       = 40000     # sims per game
# BACKTEST-EARNED (nflverse 2021-2025, 1,424 games vs closing lines; game_sim calib 2026-07):
#   empirical sd(margin)=12.65, sd(total)=13.07, team-score corr=0.033 -> per-team SIGMA=9.1, RHO=0.033.
#   (prior guesses were SIGMA 9.5 / RHO 0.07 — RHO was ~2x too high, over-coupling the two teams.)
SIGMA_TEAM  = 9.1       # per-team single-game points SD (backtest-earned; revert-to-prior = 9.5)
K_CEIL      = 0.25      # team_ceiling modulation of SD (0.0 = revert: every team same variance)
RHO_BASE    = 0.033     # two-team score corr at league-median total (backtest-earned; was 0.07)
RHO_SLOPE   = 0.04      # +corr per 10 pts total above median (data: corr ~0 at total<45, ~0.06-0.09 at 46+)
RHO_CAP     = (0.0, 0.12)  # empirical max bucket corr ~0.09; cap tightened from 0.30
TOTAL_MEDIAN= 45.0      # from correlation_structure.json total_median
# TAIL FIX (backtest-earned): raw sd(margin) is flat across spreads, but big favorites WIN more
# reliably than a symmetric distribution implies (thin upset tail) — post-calibration the sim still
# under-called 9-13pt favorites (80 vs 84%) and 13+ (86 vs 92%). Shrink both teams' SD toward a
# mismatch-predictable outcome, ramped by |spread|, calibrated to close that gap. Revert = 0.0.
SPREAD_SHRINK = 0.12
SHOOTOUT_PTS= 51.0      # total at/above which we call it a shootout environment
GRIND_PTS   = 41.0      # total at/below which we call it a grind
LEAD_RUN    = 10        # favorite leading by >= this late => clock-control / run script
TRAIL_PASS  = 7         # trailing by >= this => comeback / pass script
SEED        = 20260703  # fixed (Date.now-free): reproducible sims

# ---------------- inputs ----------------
VEG = {}
vp = os.path.join(HERE, 'ffdataroma_draft_guide_export/ffdataroma/csv/weekly-vegas-lines.csv')
import csv
for r in csv.DictReader(open(vp, encoding='utf-8')):
    t = r['team']; wk = r['week']
    if t and wk and r.get('total'):
        try:
            VEG.setdefault(t, {})[int(wk)] = {
                'imp': float(r['teamImplied']) if r['teamImplied'] else None,
                'opp_imp': float(r['oppImplied']) if r['oppImplied'] else None,
                'total': float(r['total']) if r['total'] else None,
                'spread': float(r['spread']) if r['spread'] else None,
                'opp': r['opp'], 'home': r['isHome'] == 'true', 'dome': r['isDome'] == 'true'}
        except ValueError:
            pass
TC = {t: v.get('ceiling_score') for t, v in J('team_ceiling.json')['teams'].items() if v.get('ceiling_score') is not None}
LEAGUE_CEIL = sum(TC.values()) / len(TC)
_op = J('offense_profile.json'); OP = _op.get('teams', _op)
SCHED = J('boom/schedule2026.json')
# NOTE: game_sim depends ONLY on Vegas + team_ceiling + offense_profile — deliberately NOT on
# matchup_notes/dfs_season_baseline, so dfs_model can consume the script signal without a cycle
# (game_sim -> matchup_notes -> baseline -> dfs_model -> game_sim). The "who benefits" player
# names are attached at RENDER time (render_game_sim.py) from matchup_notes instead.

def sigma(team):
    c = TC.get(team, LEAGUE_CEIL)
    return SIGMA_TEAM * (1 + K_CEIL * (c - LEAGUE_CEIL) / LEAGUE_CEIL)

def rho_for(total):
    r = RHO_BASE + RHO_SLOPE * ((total or TOTAL_MEDIAN) - TOTAL_MEDIAN) / 10.0
    return float(np.clip(r, *RHO_CAP))

def gamma_draw(mean, sd, u):
    """Map uniforms u -> Gamma(mean, sd): right-skewed, non-negative (scores can't be < 0)."""
    mean = max(mean, 1.0); sd = max(sd, 1.0)
    k = (mean / sd) ** 2; theta = sd * sd / mean
    return stats.gamma.ppf(u, k, scale=theta)

def pace_word(pctl):
    if pctl is None: return 'average pace'
    return 'fast pace' if pctl >= 65 else ('up-tempo' if pctl >= 55 else ('average pace' if pctl >= 40 else 'slow pace'))

def sim_game(a, b, wk, rng):
    """a,b = team codes. Returns the full game-script read or None if no Vegas total."""
    va = VEG.get(a, {}).get(wk)
    if not va or va.get('total') is None or va.get('imp') is None or va.get('opp_imp') is None:
        return None
    total_v = va['total']; imp_a = va['imp']; imp_b = va['opp_imp']; spread_a = va.get('spread')
    sa, sb = sigma(a), sigma(b); rho = rho_for(total_v)
    if spread_a is not None:   # tail fix: mismatches are more predictable -> tighter score SD
        shr = 1 - SPREAD_SHRINK * min(abs(spread_a), 15) / 15
        sa *= shr; sb *= shr
    # correlated standard normals -> uniforms -> gamma marginals (Gaussian copula = the shared shock)
    cov = np.array([[1.0, rho], [rho, 1.0]])
    z = rng.multivariate_normal([0, 0], cov, size=N_SIM)
    u = stats.norm.cdf(z)
    pa = gamma_draw(imp_a, sa, u[:, 0]); pb = gamma_draw(imp_b, sb, u[:, 1])
    tot = pa + pb; margin = pa - pb   # + => team a wins

    def pct(x): return round(float(np.mean(x)) * 100, 1)
    fav, dog = (a, b) if imp_a >= imp_b else (b, a)
    mfav = margin if fav == a else -margin
    read = {
        'game': f'{a} vs {b}', 'teams': [a, b], 'wk': wk,
        'vegas': {'total': total_v, 'imp': {a: imp_a, b: imp_b}, 'spread_fav': fav,
                  'spread': abs(spread_a) if spread_a is not None else None},
        'sim': {'n': N_SIM, 'rho': round(rho, 3), 'sd': {a: round(sa, 1), b: round(sb, 1)},
                'mean_total': round(float(tot.mean()), 1), 'median_total': round(float(np.median(tot)), 1),
                'mean_pts': {a: round(float(pa.mean()), 1), b: round(float(pb.mean()), 1)}},
        'winner': {a: pct(margin > 0), b: pct(margin < 0), 'fav': fav,
                   'fav_win': pct(mfav > 0)},
        'total_dist': {'over_vegas': pct(tot > total_v), 'shootout_51plus': pct(tot >= SHOOTOUT_PTS),
                       'mid_41_51': pct((tot > GRIND_PTS) & (tot < SHOOTOUT_PTS)), 'grind_41minus': pct(tot <= GRIND_PTS)},
        'margin_dist': {'blowout_14plus': pct(np.abs(margin) >= 14), 'comfortable_9_13': pct((np.abs(margin) >= 9) & (np.abs(margin) < 14)),
                        'one_score_4_8': pct((np.abs(margin) >= 4) & (np.abs(margin) < 9), ), 'nailbiter_0_3': pct(np.abs(margin) < 4)},
        'script': {
            'fav': fav, 'dog': dog,
            'fav_control_run': pct(mfav >= LEAD_RUN),          # favorite leads big -> clock-control run script
            'dog_comeback_pass': pct(mfav >= TRAIL_PASS),       # dog trailing -> pass-to-catch-up script
            'shootout_bothpass': pct((tot >= SHOOTOUT_PTS) & (np.abs(margin) <= 8)),
            'script_pass_lean': {},   # filled below
        },
    }
    # dynamic pass-lean: base offense pass rate, bent by how often each side is ahead/behind
    for tm, other in ((fav, dog), (dog, fav)):
        base = (OP.get(tm, {}) or {}).get('pass_rate')
        if base is None: continue
        m_tm = margin if tm == a else -margin
        lead_big = float(np.mean(m_tm >= LEAD_RUN)); trail = float(np.mean(m_tm <= -TRAIL_PASS))
        eff = base - 6.0 * lead_big + 8.0 * trail   # lead -> run more; trail -> pass more (stated-prior shifts)
        read['script']['script_pass_lean'][tm] = {'base': round(base, 1), 'effective': round(eff, 1),
                                                   'lead_big_p': round(lead_big * 100), 'trail_p': round(trail * 100)}
    read['_narr'] = _narrate(read)
    return read

def _narrate(r):
    a, b = r['teams']; fav = r['script']['fav']; dog = r['script']['dog']
    td = r['total_dist']; md = r['margin_dist']; sc = r['script']
    # modal total bucket + modal margin bucket
    tbucket = max([('a shootout (51+)', td['shootout_51plus']), ('a mid-40s game', td['mid_41_51']),
                   ('a low-scoring grind (≤41)', td['grind_41minus'])], key=lambda x: x[1])
    mbucket = max([('a blowout (14+)', md['blowout_14plus']), ('a comfortable win (9–13)', md['comfortable_9_13']),
                   ('a one-score game (4–8)', md['one_score_4_8']), ('a nailbiter (≤3)', md['nailbiter_0_3'])],
                  key=lambda x: x[1])
    lead = (f"Most likely: **{fav} wins**, {mbucket[0]} the model hits {mbucket[1]:.0f}% of the time, "
            f"in what profiles as {tbucket[0]} ({tbucket[1]:.0f}%). "
            f"{fav} is favored to win {r['winner']['fav_win']:.0f}% of sims; the total clears the posted "
            f"{r['vegas']['total']:.1f} in {td['over_vegas']:.0f}%.")
    # script sentence
    parts = []
    if sc['fav_control_run'] >= 33:
        parts.append(f"{fav} pulls away by two scores in {sc['fav_control_run']:.0f}% of sims — a clock-control "
                     f"script that feeds the {fav} run game")
    if sc['dog_comeback_pass'] >= 40:
        parts.append(f"{dog} is trailing (and throwing to catch up) in {sc['dog_comeback_pass']:.0f}%")
    if sc['shootout_bothpass'] >= 20:
        parts.append(f"a both-teams-throwing shootout hits {sc['shootout_bothpass']:.0f}% — the live bring-back window")
    if parts:
        script_s = "Script read: " + "; ".join(parts) + "."
    elif td['grind_41minus'] >= 33:
        script_s = "Script read: a low-total grind — ceilings suppressed on both sides, no script edge to chase."
    else:
        script_s = ("Script read: no single script dominates — it profiles as a competitive, pass-friendly game where "
                    "neither side controls and both offenses stay aggressive; the bring-back stays live.")
    return (lead + " " + script_s).strip()

def games_for_week(wk):
    seen = set(); out = []
    for team, gl in SCHED.items():
        for g in gl:
            if g.get('wk') == wk and g.get('opp') not in ('BYE', None):
                pair = tuple(sorted([team, g['opp']]))
                if pair not in seen:
                    seen.add(pair); out.append(pair)
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--week', type=int, default=0, help='0 = all 18 weeks')
    A = ap.parse_args()
    rng = np.random.default_rng(SEED)
    weeks = [A.week] if A.week else list(range(1, 19))
    out = {'_meta': {'built_note': 'means=Vegas (implied totals+spread); dispersion/correlation/script=stated priors, not backtested',
                     'params': {'SIGMA_TEAM': SIGMA_TEAM, 'K_CEIL': K_CEIL, 'RHO_BASE': RHO_BASE,
                                'RHO_SLOPE': RHO_SLOPE, 'N_SIM': N_SIM, 'seed': SEED},
                     'anchors': 'ground_truth_registry.json: weekly-vegas-lines.csv',
                     'surfaces': ['dfs']},
           'weeks': {}}
    total_games = 0
    for wk in weeks:
        gl = []
        for a, b in games_for_week(wk):
            r = sim_game(a, b, wk, rng)
            if r: gl.append(r)
        gl.sort(key=lambda r: -r['sim']['mean_total'])
        out['weeks'][str(wk)] = {'games': gl}
        total_games += len(gl)
    json.dump(out, open(os.path.join(HERE, 'game_sim.json'), 'w'), ensure_ascii=False, indent=1)
    print(f"game_sim.json: {total_games} games across {len(weeks)} week(s) | {N_SIM} sims each")
    # console spot-check: week 1 top-3 by mean total
    w = out['weeks'].get('1', out['weeks'][str(weeks[0])])
    print(f"\nweek {weeks[0] if not (len(weeks)>1) else 1} — sim vs Vegas (win% should track the spread):")
    for g in w['games'][:5]:
        fav = g['winner']['fav']; sp = g['vegas']['spread']
        print(f"  {g['game']:12s} total sim {g['sim']['mean_total']:.1f} / vegas {g['vegas']['total']:.1f}"
              f" | {fav} win {g['winner']['fav_win']:.0f}% (spread -{sp}) | shootout {g['total_dist']['shootout_51plus']:.0f}%"
              f" blowout {g['margin_dist']['blowout_14plus']:.0f}%")

if __name__ == '__main__':
    main()
