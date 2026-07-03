#!/usr/bin/env python3
"""env_blend.py — THE single sanctioned game-environment formula.

Why this module exists (PLAYBOOK.md case C5): a deliverable once ranked "best
environments" by the Vegas total ALONE, silently discarding the team-ceiling
layer (pace, pass rate, scheme change, QB ascension, shootout conditions) that
was built precisely to capture upside the market's median number misses. The
user's directive: environment = team flags/levers + O/U, never O/U alone.

Making the formula a shared import (instead of prose guidance) makes the
mistake structural: any builder that ranks environments imports this, and
integration_audit Check H fails the build if it doesn't.

Formula
-------
    blend = vegas_total + ENV_BLEND_SLOPE * (pair_ceiling_avg - league_mean_ceiling)

  * vegas_total        — the posted look-ahead O/U (ground truth; see
                         ground_truth_registry.json entry for weekly-vegas-lines.csv).
                         Vegas stays the ANCHOR: it is the market's median.
  * pair_ceiling_avg   — mean of the two teams' team_ceiling scores (0-100),
                         which encode env quality, pace, pass rate, scheme
                         upgrade, QB ascension, concentrated tree, shootout script.
  * league_mean        — computed from team_ceiling.json at import (no magic 50).
  * ENV_BLEND_SLOPE    — 0.10: the ceiling layer can move a game ~±3.5 pts
                         (about one env tier) but can never override Vegas.

Weight discipline (PLAYBOOK.md §3): ENV_BLEND_SLOPE is a STATED PRIOR, not a
backtest-earned weight — 2026 results don't exist yet to fit it. The direction
(blend, don't anchor on O/U alone) is user-mandated; the magnitude is
deliberately small and capped. REVERT FLAG: set ENV_BLEND_SLOPE = 0.0 to fall
back to pure Vegas ordering. TODO(backtest): when 2026 actuals land, test
whether blended totals out-predict closing O/U on realized game points.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
ENV_BLEND_SLOPE = 0.10   # stated prior; revert flag = 0.0; cap keeps |adj| <= ~3.5

_tc = json.load(open(os.path.join(HERE, 'team_ceiling.json'), encoding='utf-8'))['teams']
CEIL = {t: v.get('ceiling_score') for t, v in _tc.items() if v.get('ceiling_score') is not None}
LEAGUE_MEAN = round(sum(CEIL.values()) / len(CEIL), 2) if CEIL else 50.0


def ceiling_adj(team_a, team_b):
    """Team-ceiling adjustment (points) for a game between team_a and team_b.
    Missing teams contribute the league mean (adjustment 0 for a fully unknown pair)."""
    ca = CEIL.get(team_a, LEAGUE_MEAN)
    cb = CEIL.get(team_b, LEAGUE_MEAN)
    return round(ENV_BLEND_SLOPE * (((ca + cb) / 2.0) - LEAGUE_MEAN), 2)


def blend_total(vegas_total, team_a, team_b):
    """Blended environment score: Vegas O/U anchored, team-ceiling adjusted.
    Returns None if there is no Vegas total (never invent an environment)."""
    if vegas_total is None:
        return None
    return round(float(vegas_total) + ceiling_adj(team_a, team_b), 1)


if __name__ == '__main__':
    print(f"env_blend: league mean ceiling = {LEAGUE_MEAN}, slope = {ENV_BLEND_SLOPE}")
    for a, b, t in [('TB', 'CIN', 50.0), ('DAL', 'NYG', 50.5), ('ARI', 'LAC', 45.0), ('MIA', 'LV', 42.0)]:
        print(f"  {a} vs {b}: O/U {t} -> blend {blend_total(t, a, b)} (adj {ceiling_adj(a, b):+})")
