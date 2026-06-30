"""Canonical player-name normalization.

Replaces ~20 hand-rolled fn()/_norm() copies (fusion, dfs_scenarios, boom_foundation,
boom_base2yr, adv2yr, build_chart2yr, build_player_*, build_team_scout, build_splits,
dashboard, team_dashboard, team_review_build, draft_assistant, engine/bbengine,
engine/dk_parse, survival_chain, command_center, and the pipeline builders).

Single source of truth: the proven `core.fn`, re-exported here so the package owns the
public name. Do NOT redefine `fn` anywhere else — import it from here.
"""
import core as _core

# 'A.J. Brown Jr.' -> 'aj brown' ; the ONE normalizer used for every join/dedupe.
fn = _core.fn


def canon(name, team=None):
    """Stable identity key for a player.

    fn(name) alone collides for shared-normalized names (A.J. Brown vs Amon-Ra St.
    Brown both -> 'aj brown' only after suffix strip differs — the true collision
    resolution lives in core.match_usage). `canon` adds the team code to make a
    display/dedupe key that is stable across sources.
    """
    key = fn(name)
    return f"{key}|{_core.norm_team(team)}" if team else key
