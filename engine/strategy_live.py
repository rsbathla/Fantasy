"""strategy_live.py — Strategy analysis layer for the live draft tool.

Given a live_tree payload (as produced by run_live.py / bbengine.enrich),
computes which of the 3 slot strategies the user is following, live targets
for the current round, stack status, checkpoint tracking, and floor warnings.

Public API
----------
analyse(tree: dict, repo_root: str) -> dict
    Returns strategy_panel dict (see module docstring for full schema).
"""

from __future__ import annotations

import os
import re
import json

# ---------------------------------------------------------------------------
# Module-level caches for loaded JSON files.
# ---------------------------------------------------------------------------
_SB_CACHE: dict = {}   # strategy_board.json keyed by repo_root
_TC_CACHE: dict = {}   # team_ceiling.json
_SM_CACHE: dict = {}   # stack_menu.json


# ---------------------------------------------------------------------------
# Name normalization  (identical to bbengine._norm — kept standalone).
# ---------------------------------------------------------------------------

def _norm(n: str) -> str:
    """Lower, strip suffixes (Jr/Sr/II/III/IV/V), replace ./'-' with space, collapse spaces."""
    n = str(n).strip().lower()
    n = re.sub(r"\s+(jr|sr|ii|iii|iv|v)\.?$", "", n)
    n = n.replace(".", "").replace("'", "").replace("-", " ")
    return " ".join(n.split())


# ---------------------------------------------------------------------------
# JSON loaders (cached per repo_root).
# ---------------------------------------------------------------------------

def _load_strategy_board(repo_root: str) -> dict:
    if repo_root in _SB_CACHE:
        return _SB_CACHE[repo_root]
    path = os.path.join(repo_root, "strategy_board.json")
    with open(path, encoding="utf-8", errors="replace") as fh:
        data = json.load(fh)
    _SB_CACHE[repo_root] = data
    return data


def _load_team_ceiling(repo_root: str) -> dict:
    """Return dict mapping team code -> {ceiling_score, tier, ...}."""
    if repo_root in _TC_CACHE:
        return _TC_CACHE[repo_root]
    path = os.path.join(repo_root, "team_ceiling.json")
    with open(path, encoding="utf-8", errors="replace") as fh:
        data = json.load(fh)
    # If top-level has a 'teams' key, use it; otherwise use top-level directly
    # skipping _meta.
    if "teams" in data:
        teams = data["teams"]
    else:
        teams = {k: v for k, v in data.items()
                 if k != "_meta" and isinstance(v, dict) and "ceiling_score" in v}
    _TC_CACHE[repo_root] = teams
    return teams


def _load_stack_menu(repo_root: str) -> dict:
    """Return data['teams'] from stack_menu.json."""
    if repo_root in _SM_CACHE:
        return _SM_CACHE[repo_root]
    path = os.path.join(repo_root, "stack_menu.json")
    with open(path, encoding="utf-8", errors="replace") as fh:
        data = json.load(fh)
    teams = data.get("teams", {})
    _SM_CACHE[repo_root] = teams
    return teams


# ---------------------------------------------------------------------------
# Slot detection.
# ---------------------------------------------------------------------------

def _detect_slot(state: dict) -> int | None:
    """Detect draft slot (1-12) from state dict."""
    # Direct seat key
    seat = state.get("seat")
    if seat is not None:
        try:
            return int(seat)
        except (TypeError, ValueError):
            pass

    # Derive from pick + round using 12-team snake order
    pick = state.get("pick")
    rnd = state.get("round")
    if pick is None or rnd is None:
        return None
    try:
        pick = int(pick)
        rnd = int(rnd)
    except (TypeError, ValueError):
        return None

    position_in_round = (pick - 1) % 12 + 1
    if rnd % 2 == 1:
        slot = position_in_round
    else:
        slot = 13 - position_in_round
    return slot


# ---------------------------------------------------------------------------
# Roster helpers.
# ---------------------------------------------------------------------------

def _roster_names(state: dict) -> list[str]:
    """Return list of player name strings from state['roster'] or state['my_roster']."""
    roster = state.get("roster") or state.get("my_roster") or []
    names = []
    for item in roster:
        if isinstance(item, dict):
            names.append(item.get("name", ""))
        else:
            names.append(str(item))
    return names


# ---------------------------------------------------------------------------
# Strategy fit scoring.
# ---------------------------------------------------------------------------

_CHECKPOINT_ROUNDS = [5, 7, 9, 13, 18]


def _nearest_checkpoint_at_or_before(cur_round: int) -> int | None:
    """Return the highest checkpoint round that is <= cur_round, or None."""
    result = None
    for cp in _CHECKPOINT_ROUNDS:
        if cp <= cur_round:
            result = cp
    return result


def _next_checkpoint_after(cur_round: int) -> int | None:
    """Return the lowest checkpoint round that is > cur_round, or None."""
    for cp in _CHECKPOINT_ROUNDS:
        if cp > cur_round:
            return cp
    return None


def _score_strategy(strategy: dict, roster_names: list[str], cur_round: int, counts: dict) -> float:
    """Score a strategy against the current roster + position shape."""
    score = 0.0

    # Per-pick scoring
    for pick_idx, name in enumerate(roster_names):
        player_round = pick_idx + 1  # round 1 for first pick, etc.
        rnd_data = strategy.get("rounds", {}).get(str(player_round), {})
        norm_name = _norm(name)

        # Primary match → +2
        for p in rnd_data.get("primary", []):
            if _norm(p.get("name", "")) == norm_name:
                score += 2
                break
        else:
            # Pivot match → +1 (only if not already primary)
            for p in rnd_data.get("pivots", []):
                if _norm(p.get("name", "")) == norm_name:
                    score += 1
                    break

    # Position shape proximity
    cp_round = _nearest_checkpoint_at_or_before(cur_round)
    if cp_round is not None:
        checkpoints = strategy.get("checkpoints", {})
        cp_data = checkpoints.get(str(cp_round), {})
        if cp_data:
            positions = ["QB", "RB", "WR", "TE"]
            total_diff = 0
            for pos in positions:
                target = int(cp_data.get(pos, 0))
                current = int(counts.get(pos, 0))
                total_diff += abs(current - target)
            # max possible difference: assume each could differ by cp_round picks
            max_diff = max(cp_round * len(positions), 1)
            shape_score = 1.0 - (total_diff / max_diff) * 0.5
            score += 0.3 * shape_score

    return score


def _adherence_label(score: float) -> str:
    if score >= 4:
        return "ON PLAN"
    if score >= 2:
        return "DRIFTING"
    return "OFF PLAN"


def _score_breakdown(strategy: dict, roster_names: list[str], cur_round: int, counts: dict) -> str:
    """Human-readable breakdown of how the score was computed."""
    parts = []
    primary_hits = []
    pivot_hits = []

    for pick_idx, name in enumerate(roster_names):
        player_round = pick_idx + 1
        rnd_data = strategy.get("rounds", {}).get(str(player_round), {})
        norm_name = _norm(name)
        in_primary = any(_norm(p.get("name", "")) == norm_name for p in rnd_data.get("primary", []))
        in_pivot = any(_norm(p.get("name", "")) == norm_name for p in rnd_data.get("pivots", []))
        if in_primary:
            primary_hits.append(f"{name}(R{player_round})")
        elif in_pivot:
            pivot_hits.append(f"{name}(R{player_round})")

    if primary_hits:
        parts.append(f"Primary matches (+2 each): {', '.join(primary_hits)}")
    if pivot_hits:
        parts.append(f"Pivot matches (+1 each): {', '.join(pivot_hits)}")

    cp_round = _nearest_checkpoint_at_or_before(cur_round)
    if cp_round is not None:
        checkpoints = strategy.get("checkpoints", {})
        cp_data = checkpoints.get(str(cp_round), {})
        if cp_data:
            gaps = {pos: counts.get(pos, 0) - int(cp_data.get(pos, 0))
                    for pos in ["QB", "RB", "WR", "TE"]}
            gap_str = " ".join(f"{pos}:{'+' if g >= 0 else ''}{g}" for pos, g in gaps.items())
            parts.append(f"Shape vs R{cp_round} checkpoint ({gap_str})")

    return "; ".join(parts) if parts else "No roster yet"


# ---------------------------------------------------------------------------
# Live targets.
# ---------------------------------------------------------------------------

def _collect_synergy_names(tree: dict) -> set:
    """Collect normalized names of grader top picks for synergy tagging."""
    synergy = set()
    branches = tree.get("tree", {}).get("branches", [])
    for branch in branches:
        take = branch.get("take", "")
        if take:
            synergy.add(_norm(take))
    # Also check headline
    headline_take = tree.get("headline", {}).get("take", "")
    if headline_take:
        synergy.add(_norm(headline_take))
    return synergy


def _build_live_targets(strategy: dict, cur_round: int, available_set: set,
                         team_ceiling: dict, synergy_names: set) -> list[dict]:
    """Build live_targets list for the best-fit strategy at cur_round."""
    rnd_data = strategy.get("rounds", {}).get(str(cur_round), {})
    targets = []

    for player in rnd_data.get("primary", []):
        targets.append(_make_target_entry(player, True, available_set, team_ceiling, synergy_names))

    for player in rnd_data.get("pivots", []):
        targets.append(_make_target_entry(player, False, available_set, team_ceiling, synergy_names))

    return targets


def _make_target_entry(player: dict, is_primary: bool, available_set: set,
                        team_ceiling: dict, synergy_names: set) -> dict:
    name = player.get("name", "")
    team = player.get("team", "")
    tc_info = team_ceiling.get(team, {})
    return {
        "name": name,
        "pos": player.get("pos", ""),
        "team": team,
        "adp": player.get("adp"),
        "tier": tc_info.get("tier"),
        "ceiling_score": tc_info.get("ceiling_score"),
        "available": _norm(name) in available_set,
        "is_primary": is_primary,
        "stack_pick": bool(player.get("stack_pick", False)),
        "synergy": _norm(name) in synergy_names,
    }


# ---------------------------------------------------------------------------
# Stack status.
# ---------------------------------------------------------------------------

def _identify_stack_teams(strategy: dict) -> list[str]:
    """Return ordered unique list of team codes from stack_pick=True rounds (primary target)."""
    seen = []
    rounds = strategy.get("rounds", {})
    for rk in sorted(rounds.keys(), key=lambda x: int(x)):
        rdata = rounds[rk]
        if rdata.get("stack_pick"):
            primary = rdata.get("primary", [])
            if primary:
                team = primary[0].get("team", "")
                if team and team not in seen:
                    seen.append(team)
    return seen


def _build_stack_status(strategy: dict, roster_norm_names: set, available_set: set,
                          stack_menu: dict, team_ceiling: dict) -> list[dict]:
    """Build stack_status list for all identified stack teams."""
    stack_teams = _identify_stack_teams(strategy)
    results = []

    for team in stack_teams:
        tc_info = team_ceiling.get(team, {})
        team_menu = stack_menu.get(team, {})

        # Collect all stack members from all stacks for this team
        all_members: list[dict] = []
        for stack in team_menu.get("stacks", []):
            for member in stack.get("members", []):
                # Deduplicate by normalized name
                if not any(_norm(m.get("name", "")) == _norm(member.get("name", ""))
                            for m in all_members):
                    all_members.append(member)

        held = [m["name"] for m in all_members if _norm(m.get("name", "")) in roster_norm_names]
        remaining = [m["name"] for m in all_members if _norm(m.get("name", "")) not in roster_norm_names]
        available_remaining = [n for n in remaining if _norm(n) in available_set]

        # Bringbacks available (in available_set, sorted by adp)
        bringbacks_raw = team_menu.get("bringback", [])
        bringbacks_available = [
            {"name": b["name"], "adp": b.get("adp"), "pos": b.get("pos", "")}
            for b in bringbacks_raw
            if _norm(b.get("name", "")) in available_set
        ]
        bringbacks_available.sort(key=lambda x: x["adp"] if x["adp"] is not None else 9999)

        results.append({
            "team": team,
            "tier": tc_info.get("tier", "?"),
            "ceiling_score": tc_info.get("ceiling_score"),
            "held": held,
            "remaining": remaining,
            "available_remaining": available_remaining,
            "bringbacks_available": bringbacks_available,
        })

    return results


# ---------------------------------------------------------------------------
# Checkpoint tracker.
# ---------------------------------------------------------------------------

def _build_checkpoints(strategy: dict, cur_round: int, counts: dict) -> list[dict]:
    """Build checkpoint tracker list (future checkpoints only)."""
    checkpoints_data = strategy.get("checkpoints", {})
    positions = ["QB", "RB", "WR", "TE"]
    results = []

    for cp_str in ["5", "7", "9", "13", "18"]:
        cp_round = int(cp_str)
        if cp_round <= cur_round:
            continue  # only future checkpoints

        cp_target = checkpoints_data.get(cp_str, {})
        if not cp_target or not isinstance(cp_target, dict):
            continue

        # Filter to only position keys
        target = {pos: int(cp_target.get(pos, 0)) for pos in positions}
        current = {pos: int(counts.get(pos, 0)) for pos in positions}
        gaps = {pos: target[pos] - current[pos] for pos in positions}
        rounds_remaining = cp_round - cur_round

        at_risk = [pos for pos in positions
                   if gaps[pos] > 0 and gaps[pos] >= rounds_remaining]
        impossible = [pos for pos in positions if gaps[pos] > rounds_remaining]

        results.append({
            "round": cp_round,
            "target": target,
            "current": current,
            "gaps": gaps,
            "rounds_remaining": rounds_remaining,
            "at_risk": at_risk,
            "impossible": impossible,
        })

    return results


# ---------------------------------------------------------------------------
# Floor warnings.
# ---------------------------------------------------------------------------

def _build_floor_warnings(strategy: dict, cur_round: int, roster_names: list[str],
                            counts: dict) -> list[str]:
    """Generate floor warning messages from strategy checkpoints.floors_ok."""
    checkpoints = strategy.get("checkpoints", {})
    floors_ok = checkpoints.get("floors_ok", {})
    rb1_round_target = checkpoints.get("rb1_round")
    qb1_round_target = checkpoints.get("qb1_round")
    te1_round_target = checkpoints.get("te1_round")
    warnings = []

    # rb1_by_R7: has user drafted RB in first 7 rounds?
    if "rb1_by_R7" in floors_ok and floors_ok["rb1_by_R7"]:
        if cur_round > 7 and counts.get("RB", 0) == 0:
            warnings.append("FLOOR MISSED: No RB drafted through R7 (rb1_by_R7 floor violated)")
        elif cur_round > 7:
            pass  # ok, they have an RB
        elif cur_round <= 7:
            rb_count = counts.get("RB", 0)
            if rb_count == 0:
                rounds_left_for_r7 = 7 - cur_round + 1
                if rounds_left_for_r7 <= 0:
                    warnings.append("FLOOR RISK: No RB yet; R7 deadline for rb1_by_R7 has passed")
                else:
                    warnings.append(f"FLOOR WATCH: Need RB by R7 ({rounds_left_for_r7} rounds left)")

    # qb_late: QB round should be >= 5 (drafted late)
    if "qb_late" in floors_ok and floors_ok["qb_late"]:
        qb_count = counts.get("QB", 0)
        if qb_count > 0:
            # Find what round QB was taken (find first QB in roster)
            qb_pick_round = None
            for idx, name in enumerate(roster_names):
                # We'd need pos info here; approximate by assuming checkpoints give QB round
                pass
            if qb1_round_target is not None and isinstance(qb1_round_target, (int, float)):
                # We can't easily get QB draft round without pos info, so check via checkpoints
                pass
        # If QB taken very early (round < 5) — this is hard to check without pos,
        # use counts + current round as a proxy
        if qb_count >= 1 and cur_round <= 4:
            warnings.append("FLOOR RISK: QB appears drafted before R5 (qb_late floor at risk)")

    # te_late_or_leverage: TE round >= 9
    if "te_late_or_leverage" in floors_ok and floors_ok["te_late_or_leverage"]:
        te_count = counts.get("TE", 0)
        if te_count >= 1 and cur_round <= 8:
            warnings.append("FLOOR RISK: TE appears drafted before R9 (te_late_or_leverage floor at risk)")

    return warnings


# ---------------------------------------------------------------------------
# Safe empty defaults.
# ---------------------------------------------------------------------------

def _empty_result(slot=None, error=None) -> dict:
    return {
        "slot": slot,
        "slot_detected": slot is not None,
        "strategies": [],
        "best_fit": None,
        "live_targets": [],
        "stack_status": [],
        "checkpoints": [],
        "floor_warnings": [],
        "leverage_pivot": "",
        "error": error,
    }


# ---------------------------------------------------------------------------
# Main entry point.
# ---------------------------------------------------------------------------

def analyse(tree: dict, repo_root: str) -> dict:
    """Analyse the live draft tree against slot strategies.

    Parameters
    ----------
    tree : dict
        The live_tree payload produced by run_live.py (keys: state, board, tree, headline, ...).
    repo_root : str
        Absolute path to the bestball/ repo root (contains strategy_board.json etc.).

    Returns
    -------
    dict
        strategy_panel with keys: slot, slot_detected, strategies, best_fit, live_targets,
        stack_status, checkpoints, floor_warnings, leverage_pivot, error.
    """
    # ------------------------------------------------------------------
    # Load JSON data files.
    # ------------------------------------------------------------------
    try:
        strategy_board = _load_strategy_board(repo_root)
    except Exception as exc:
        return {**_empty_result(),
                "error": f"strategy_board.json not found at {repo_root}: {exc}"}

    try:
        team_ceiling = _load_team_ceiling(repo_root)
    except Exception as exc:
        return {**_empty_result(),
                "error": f"team_ceiling.json not found at {repo_root}: {exc}"}

    try:
        stack_menu = _load_stack_menu(repo_root)
    except Exception as exc:
        return {**_empty_result(),
                "error": f"stack_menu.json not found at {repo_root}: {exc}"}

    # ------------------------------------------------------------------
    # Extract state.
    # ------------------------------------------------------------------
    state = tree.get("state", {})
    cur_round = int(state.get("round", 1))
    counts = {pos: int(state.get("counts", {}).get(pos, 0)) for pos in ["QB", "RB", "WR", "TE"]}

    # Roster: list of name strings
    roster_names = _roster_names(state)
    roster_norm = {_norm(n) for n in roster_names}

    # Board: set of available player normalized names
    board = tree.get("board", [])
    available_set = {_norm(p.get("name", "")) for p in board if p.get("name")}

    # Synergy names from grader
    synergy_names = _collect_synergy_names(tree)

    # ------------------------------------------------------------------
    # Slot detection.
    # ------------------------------------------------------------------
    slot = _detect_slot(state)
    if slot is None:
        return {**_empty_result(slot=None, error="slot undetectable"),
                "slot_detected": False}

    # ------------------------------------------------------------------
    # Get strategies for this slot.
    # ------------------------------------------------------------------
    slots_data = strategy_board.get("slots", {})
    slot_data = slots_data.get(str(slot), {})
    strategies_list = slot_data.get("strategies", [])
    leverage_pivot = slot_data.get("leverage_pivot", "")

    if not strategies_list:
        return {**_empty_result(slot=slot, error=f"No strategies found for slot {slot}"),
                "slot_detected": True,
                "leverage_pivot": leverage_pivot}

    # ------------------------------------------------------------------
    # Score all strategies.
    # ------------------------------------------------------------------
    scored = []
    for strat in strategies_list:
        score = _score_strategy(strat, roster_names, cur_round, counts)
        scored.append((strat, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    best_strat, best_score = scored[0]

    strategies_summary = [
        {
            "id": s.get("id", ""),
            "name": s.get("name", ""),
            "score": round(sc, 3),
            "adherence": _adherence_label(sc),
        }
        for s, sc in scored
    ]

    adherence = _adherence_label(best_score)

    best_fit = {
        "id": best_strat.get("id", ""),
        "name": best_strat.get("name", ""),
        "archetype": best_strat.get("archetype", ""),
        "thesis": (best_strat.get("thesis", "") or "")[:250],
        "score": round(best_score, 3),
        "adherence": adherence,
        "score_breakdown": _score_breakdown(best_strat, roster_names, cur_round, counts),
    }

    # ------------------------------------------------------------------
    # Live targets for current round.
    # ------------------------------------------------------------------
    live_targets = _build_live_targets(
        best_strat, cur_round, available_set, team_ceiling, synergy_names
    )

    # ------------------------------------------------------------------
    # Stack status.
    # ------------------------------------------------------------------
    stack_status = _build_stack_status(
        best_strat, roster_norm, available_set, stack_menu, team_ceiling
    )

    # ------------------------------------------------------------------
    # Checkpoints.
    # ------------------------------------------------------------------
    checkpoints = _build_checkpoints(best_strat, cur_round, counts)

    # ------------------------------------------------------------------
    # Floor warnings.
    # ------------------------------------------------------------------
    floor_warnings = _build_floor_warnings(best_strat, cur_round, roster_names, counts)

    # ------------------------------------------------------------------
    # Assemble and return.
    # ------------------------------------------------------------------
    return {
        "slot": slot,
        "slot_detected": True,
        "strategies": strategies_summary,
        "best_fit": best_fit,
        "live_targets": live_targets,
        "stack_status": stack_status,
        "checkpoints": checkpoints,
        "floor_warnings": floor_warnings,
        "leverage_pivot": leverage_pivot,
        "error": None,
    }
