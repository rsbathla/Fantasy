"""bb/correlation — stacking & correlation primitives, consolidated.

The audit found stacking logic spread across 4 files (gameplan, engine/decision_tree,
draft_assistant, pipeline/survival_chain.anchor_game) with the correlation constants
restated each time. This is the one home; the constants come from core.config.
"""
from .. import core

R_QB_WR1 = core.config.R_QB_WR1
R_BRINGBACK = core.config.R_BRINGBACK


def stack_bonus(my_roster, candidate, *, qb_wr1=R_QB_WR1, bringback=R_BRINGBACK):
    """Marginal correlation bonus for adding `candidate` to `my_roster`.

    Items are dicts with at least {pos, team, opp}. Returns a small additive bonus:
      + qb_wr1     if candidate is a pass-catcher stacking my QB (or vice-versa)
      + bringback  if candidate is a pass-catcher on my QB's opponent (bring-back)
    """
    bonus = 0.0
    qbs = [p for p in my_roster if p.get("pos") == "QB"]
    catchers_by_team = {}
    for p in my_roster:
        if p.get("pos") in ("WR", "TE"):
            catchers_by_team.setdefault(p.get("team"), []).append(p)

    if candidate.get("pos") in ("WR", "TE"):
        if any(q.get("team") == candidate.get("team") for q in qbs):
            bonus += qb_wr1
        if any(q.get("opp") == candidate.get("team") for q in qbs):
            bonus += bringback
    elif candidate.get("pos") == "QB":
        same = catchers_by_team.get(candidate.get("team"), [])
        bonus += qb_wr1 * min(len(same), 2) * 0.5
        opp_catchers = catchers_by_team.get(candidate.get("opp"), [])
        bonus += bringback * min(len(opp_catchers), 1)
    return round(bonus, 3)
