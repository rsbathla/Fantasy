"""playoff_week — the SHARED best-ball playoff-week ceiling.

The audit's biggest cross-layer redundancy: dfs_scenarios.py computes real Vegas-anchored
per-week P(ceiling) for W15/16/17, while engine/playoff_overlay.py re-derives a weaker
offense-proxy version of the same thing. Two answers for the same player-week.

This is the ONE implementation. The best-ball playoff overlay and the DFS weekly board
both call it, so the playoff-week ceiling is computed a single way.

p_ceiling(mean, cv, bar, env, matchup):
    P(player's weekly DK points >= a position 'ceiling bar') under a lognormal points
    model, shifted by the week's environment (team implied total vs baseline) and the
    opponent matchup softness. Lognormal is the right shape: fantasy weekly scoring is
    right-skewed and non-negative, which is exactly the 'ceiling' tail we care about.

playoff_up(p15, p16, p17):
    aggregate the three playoff weeks with the finals weighted heaviest (the weights
    that were inside playoff_overlay).
"""
import math

__all__ = ["WEEK_W", "p_ceiling", "playoff_up"]

WEEK_W = {15: 0.25, 16: 0.30, 17: 0.45}  # finals (W17) weighted heaviest


def p_ceiling(mean, cv, bar, *, env=1.0, matchup=1.0):
    """Lognormal P(weekly points >= bar). Returns a probability in [0, 1].

    mean    : player's projected weekly points (from the sim / Clay means).
    cv      : coefficient of variation of weekly points (from the sim).
    bar     : position ceiling bar (a 'spike week' threshold).
    env     : team implied-total / baseline-total (>1 = high-scoring spot).
    matchup : soft (>1) / tough (<1) opponent multiplier.
    """
    if not mean or mean <= 0 or not cv or cv <= 0 or not bar or bar <= 0:
        return 0.0
    mu_pts = mean * env * matchup
    sigma = math.sqrt(math.log(1.0 + cv * cv))
    mu = math.log(max(mu_pts, 1e-6)) - 0.5 * sigma * sigma
    z = (math.log(bar) - mu) / sigma
    # P(X >= bar) = 1 - Phi(z) = 0.5 * erfc(z / sqrt(2))
    return max(0.0, min(1.0, 0.5 * math.erfc(z / math.sqrt(2.0))))


def playoff_up(p15, p16, p17):
    """Weighted playoff-week ceiling (finals heaviest). Inputs are P(ceiling) per week."""
    return round(WEEK_W[15] * p15 + WEEK_W[16] * p16 + WEEK_W[17] * p17, 4)
