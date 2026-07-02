#!/usr/bin/env python3
"""build_stack_menu.py -- Per-team STACK MENU: every draftable QB-stack a drafter could
assemble from each NFL offense, priced in draft capital, with Week-17 bring-back options.

This is a MENU (enumeration + light scoring), NOT a decision layer.
A strategy generator consumes it in the next phase.

Rules encoded from WINNING_STRUCTURE.md (TARGET SHAPE section, §2.1):
  STACK_TYPES:
    - skinny : QB + 1 same-team pass-catcher   (advance +16.8% vs 16.7% base)
    - standard: QB + 2 same-team pass-catchers  (advance +17.2% -- sweet spot for buildability)
    - heavy   : QB + 3 same-team pass-catchers  (advance +19.4% -- biggest regular-season bump)
  REACHING PENALTY: drafting stack pieces *above* their ADP flips advance negative
    (skinny reached = 11.9%, heavy reached = 5.0%). Stack pieces must come AT OR BELOW
    market price -- a reached piece is flagged via value_ct.
  QB TIMING: ADP > 96 (round 9+) = "late QB leverage" [SOURCED: BBM VI optimal zero QB
    through R13; "QB window" ~ADP 85-116].
  PASS-CATCHING RBs: excluded from stack enumeration (no tgt_sh threshold in flag_ranks.json
    to reliably separate pass-catchers from pure rushers at scale; RB-QB correlation is ≈ -0.04
    per PlayerProfiler -- essentially uncorrelated). Documented exclusion: stack WR/TE only.
  WEEK-17 BRINGBACK correlation: +0.09 to +0.10 at ceiling (Underdog Network). Modest but real
    for championship-week game-stacks; enumerated here, weighted lightly (0.15) in stack_score.

INPUTS:
  flag_ranks.json    -- players{}: name, pos, team, adp, adj_rank, mkt_rank
  team_ceiling.json  -- per-team ceiling_score, tier
  boom/schedule2026.json -- per-team week-by-week opponent list

OUTPUT: stack_menu.json
"""

import json
import math
import datetime
from collections import defaultdict

# ── CONSTANTS FROM WINNING_STRUCTURE.md ────────────────────────────────────────
# Source: §2.1 advance-rate ladder [SOURCED: PlayerProfiler / David Zacharias, BBM data]
STACK_TYPES = {
    "skinny":   {"pass_catchers": 1, "advance_pct": 16.8},  # QB+1
    "standard": {"pass_catchers": 2, "advance_pct": 17.2},  # QB+2 -- sweet spot
    "heavy":    {"pass_catchers": 3, "advance_pct": 19.4},  # QB+3 -- max regular-season bump
}

# ADP ceiling for roster-eligible players (18-round draft, ~1 pick/team beyond R18 depth)
ADP_CEIL = 220  # any player with adp > 220 is undraftable at price

# Top-N pass-catchers per team to consider for stack enumeration
TOP_PC_N = 5

# Rounds per draft (12-team)
PICKS_PER_ROUND = 12

# QB "late" threshold: ADP > 96 => round 9+ [SOURCED: WINNING_STRUCTURE.md §2.4 / §1 TARGET SHAPE]
QB_LATE_ADP = 96  # round 8.x; research finds R8-13 is the optimal QB window

# Top stacks to keep per team in output (ordered by stack_score desc)
TOP_STACKS_N = 12

# Top pass-catchers of W17 opponent to include in bringback list
BRINGBACK_N = 4

# Stack score formula (transparent, documented -- generator does real evaluation):
#   0.5 * (ceiling_score/100)     -- team offensive ceiling (dominant term)
#   0.2 * (value_ct / stack_size) -- fraction of members adj_rank <= mkt_rank (model likes at price)
#   0.15 * (1 if qb_late else 0)  -- late-QB leverage bonus [SOURCED: §2.4]
#   0.15 * (w17_game_env/100)     -- crude championship-week game-environment proxy
# NOTE: score is for ORDERING the menu only, not for absolute EV comparison.
SCORE_WEIGHTS = {
    "ceiling":     0.50,
    "value":       0.20,
    "qb_late":     0.15,
    "w17_env":     0.15,
}

# PASS-CATCHING RB EXCLUSION RATIONALE:
# QB->RB1 correlation ≈ -0.04; QB->RB2 ≈ +0.15 [SOURCED: PlayerProfiler].
# flag_ranks.json has tgt_sh (target share %) for some RBs, but many are None and the
# threshold for "pass-catching RB" (e.g., tgt_sh >= 15%) is not universally populated.
# Decision: exclude all RBs from stack enumeration. This matches the empirical finding
# that the RB is essentially uncorrelated with his own QB for stack purposes.
# Pass-catching RBs that happen to be WR-like assets are a rounding error at ADP ≤ 220.

def load_json(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def round_est(adp: float) -> int:
    """Estimated draft round: ceil(adp / 12). ADP 1-12 = R1, 13-24 = R2, etc."""
    return math.ceil(adp / PICKS_PER_ROUND)


def build_stack_menu():
    # ── 1. Load inputs ──────────────────────────────────────────────────────────
    flag_data = load_json("flag_ranks.json")
    tc_data = load_json("team_ceiling.json")
    schedule = load_json("boom/schedule2026.json")

    players_raw = flag_data["players"]

    # ── 2. Compute market_rank (rank of adp ascending over ALL board players) ──
    # NOTE: flag_ranks.json already carries mkt_rank; we recompute from scratch to
    # guarantee it matches the spec (rank of adp ascending over all 376 board players).
    sorted_by_adp = sorted(players_raw.values(), key=lambda p: p["adp"])
    for rank, p in enumerate(sorted_by_adp, start=1):
        p["_market_rank"] = rank  # computed fresh; avoids reliance on stored mkt_rank

    # ── 3. Bucket players by team + position ────────────────────────────────────
    # QBs and WR/TE pass-catchers only; ADP <= 220
    team_qbs: dict[str, list] = defaultdict(list)
    team_pcs: dict[str, list] = defaultdict(list)  # pass-catchers (WR/TE)

    for p in players_raw.values():
        if p["adp"] > ADP_CEIL:
            continue
        pos = p["pos"]
        team = p["team"]
        if pos == "QB":
            team_qbs[team].append(p)
        elif pos in ("WR", "TE"):
            team_pcs[team].append(p)
        # RBs excluded -- see PASS-CATCHING RB EXCLUSION RATIONALE above

    # Sort within team by adp ascending
    for team in team_qbs:
        team_qbs[team].sort(key=lambda p: p["adp"])
    for team in team_pcs:
        team_pcs[team].sort(key=lambda p: p["adp"])

    # ── 4. Build Week-17 opponent map ───────────────────────────────────────────
    w17_opp: dict[str, str] = {}
    for team, weeks in schedule.items():
        for wk in weeks:
            if wk["wk"] == 17:
                w17_opp[team] = wk["opp"]
                break

    # ── 5. Enumerate stacks and build output ────────────────────────────────────
    all_teams = tc_data["teams"]
    output_teams = {}
    total_stacks = 0
    stacks_value_ct_2plus = 0

    for team in sorted(all_teams.keys()):
        tc = all_teams[team]
        ceiling_score = tc["ceiling_score"]
        tier = tc["tier"]

        qbs = team_qbs.get(team, [])
        pcs = team_pcs.get(team, [])
        top_pcs = pcs[:TOP_PC_N]  # top-5 pass-catchers by ADP

        opp = w17_opp.get(team, "BYE")
        opp_ceiling = all_teams.get(opp, {}).get("ceiling_score", 0.0)

        # w17_game_env: mean of both teams' ceiling_scores (crude game-environment proxy).
        # Documented: this is a rough matchup-quality proxy, not a true game-script model.
        # Higher = both teams likely to be in a high-scoring, pass-heavy environment.
        if opp and opp in all_teams:
            w17_game_env = (ceiling_score + opp_ceiling) / 2.0
        else:
            w17_game_env = ceiling_score  # BYE or unknown: fallback to own ceiling

        # Bringback: opponent's top-4 pass-catchers by ADP
        opp_pcs_all = team_pcs.get(opp, []) if opp else []
        bringback = []
        for opp_pc in opp_pcs_all[:BRINGBACK_N]:
            bringback.append({
                "name": opp_pc["name"],
                "pos": opp_pc["pos"],
                "adp": round(opp_pc["adp"], 1),
                "adj_rank": opp_pc["adj_rank"],
            })

        # Enumerate stacks
        stacks = []
        for qb in qbs:
            qb_adp = qb["adp"]
            qb_late = qb_adp > QB_LATE_ADP
            qb_market_rank = qb["_market_rank"]
            qb_adj_rank = qb["adj_rank"]

            for stype, sdef in STACK_TYPES.items():
                n_pc = sdef["pass_catchers"]
                if len(top_pcs) < n_pc:
                    continue  # not enough pass-catchers on the board for this team

                # Enumerate all combinations of n_pc pass-catchers from top_pcs
                from itertools import combinations
                for pc_combo in combinations(top_pcs, n_pc):
                    members = [qb] + list(pc_combo)
                    stack_size = len(members)

                    # value_ct: members where adj_rank <= market_rank (model likes at price).
                    # FIX 4: uses <= (consistent with build_slot_paths.py value_flag).
                    # Definition: "model ranks the player at or better than market price."
                    value_ct = sum(
                        1 for m in members
                        if m["adj_rank"] <= m["_market_rank"]
                    )

                    # Round estimates and cost
                    rounds_each = [round_est(m["adp"]) for m in members]
                    total_rounds_cost = sum(rounds_each)
                    latest_round = max(rounds_each)

                    # Stack score (formula per spec -- ordering only)
                    stack_score = (
                        SCORE_WEIGHTS["ceiling"]  * (ceiling_score / 100.0) +
                        SCORE_WEIGHTS["value"]    * (value_ct / stack_size) +
                        SCORE_WEIGHTS["qb_late"]  * (1.0 if qb_late else 0.0) +
                        SCORE_WEIGHTS["w17_env"]  * (w17_game_env / 100.0)
                    )

                    member_records = []
                    for m, r in zip(members, rounds_each):
                        member_records.append({
                            "name": m["name"],
                            "pos": m["pos"],
                            "adp": round(m["adp"], 1),
                            "adj_rank": m["adj_rank"],
                            "market_rank": m["_market_rank"],
                            "round_est": r,
                        })

                    stacks.append({
                        "stack_type": stype,
                        "qb_name": qb["name"],
                        "qb_adp": round(qb_adp, 1),
                        "qb_late": qb_late,
                        "members": member_records,
                        "stack_size": stack_size,
                        "total_rounds_cost": total_rounds_cost,
                        "latest_round": latest_round,
                        "value_ct": value_ct,
                        "stack_score": round(stack_score, 4),
                    })

                    total_stacks += 1
                    if value_ct >= 2:
                        stacks_value_ct_2plus += 1

        # Sort stacks by stack_score desc, take top N
        stacks.sort(key=lambda s: -s["stack_score"])
        top_stacks = stacks[:TOP_STACKS_N]

        output_teams[team] = {
            "ceiling_score": ceiling_score,
            "tier": tier,
            "w17_opp": opp,
            "w17_opp_ceiling": opp_ceiling,
            "w17_game_env": round(w17_game_env, 2),
            "bringback": bringback,
            "n_qbs_on_board": len(qbs),
            "n_pcs_on_board": len(pcs),
            "stacks": top_stacks,
        }

    # Sort teams by ceiling_score desc (per spec)
    output_teams_sorted = dict(
        sorted(output_teams.items(), key=lambda kv: -kv[1]["ceiling_score"])
    )

    # ── 6. Build output JSON ─────────────────────────────────────────────────────
    out = {
        "_meta": {
            "artifact": "stack_menu.json",
            "built": datetime.date.today().isoformat(),
            "description": (
                "Per-team STACK MENU: every draftable QB-stack (skinny/standard/heavy) "
                "from each NFL offense, priced in draft capital, with Week-17 bring-back options. "
                "Menu (enumeration + light scoring) -- strategy generator consumes next phase."
            ),
            "rules_from_WINNING_STRUCTURE_md": {
                "source_section": "§1 TARGET SHAPE + §2.1 STACKING",
                "stack_types": {
                    "skinny":   "QB + 1 same-team pass-catcher (WR/TE); advance ~+16.8% [SOURCED]",
                    "standard": "QB + 2 same-team pass-catchers; advance ~+17.2% [SOURCED] -- sweet spot",
                    "heavy":    "QB + 3 same-team pass-catchers; advance ~+19.4% [SOURCED] -- max bump",
                },
                "reaching_penalty": (
                    "Stack pieces MUST come at or below market price. Reaching flips advance negative "
                    "(skinny reached=11.9%, heavy reached=5.0%) [SOURCED: PlayerProfiler / Zacharias]. "
                    "value_ct counts members where adj_rank <= market_rank (model agrees at price)."
                ),
                "qb_late_threshold": (
                    f"QB ADP > {QB_LATE_ADP} (round 9+) flagged as qb_late=True. "
                    "WINNING_STRUCTURE.md §2.4: late QB is leverage -- BBM VI optimal was zero QB "
                    "through R13; elite QBs (R1-4) advanced 14.3% (below 16.7% base) [SOURCED: 4for4]."
                ),
                "pass_catcher_scope": (
                    "WR and TE only. RBs excluded: QB->RB1 correlation ≈ -0.04 (essentially "
                    "uncorrelated) [SOURCED: PlayerProfiler]. Pass-catching RBs excluded because "
                    "tgt_sh is not reliably populated for all RBs in flag_ranks.json and the "
                    "signal uplift is marginal relative to WR/TE stack value."
                ),
                "w17_bringback_correlation": (
                    "WR1->opposing WR1 ceiling correlation ≈ +0.09 to +0.10 [SOURCED: Underdog Network]. "
                    "Modest but real for championship-week game-stacks. Listed as bring-back options."
                ),
                "n_stacks_target": (
                    "2-3 QB stacks per roster, ~3-5 offenses concentrated [SOURCED: §2.1 + §2.2]. "
                    "This menu surfaces all options; the generator selects the best 2-3."
                ),
            },
            "scoring_formula": {
                "description": "stack_score orders the menu only; NOT an absolute EV measure.",
                "formula": (
                    "0.50*(ceiling_score/100) + 0.20*(value_ct/stack_size) "
                    "+ 0.15*(1 if qb_late else 0) + 0.15*(w17_game_env/100)"
                ),
                "terms": {
                    "ceiling_score/100": "team offensive ceiling probability (dominant weight)",
                    "value_ct/stack_size": "fraction of members model likes at price",
                    "qb_late": "late-QB leverage bonus per WINNING_STRUCTURE.md §2.4",
                    "w17_game_env/100": "crude mean-ceiling proxy for W17 game environment",
                },
            },
            "surfaces": ["predraft", "live"],
            "adp_ceil": ADP_CEIL,
            "picks_per_round": PICKS_PER_ROUND,
            "top_pcs_per_team": TOP_PC_N,
            "top_stacks_kept": TOP_STACKS_N,
            "bringback_n": BRINGBACK_N,
            "inputs": [
                "flag_ranks.json (players: name, pos, team, adp, adj_rank, mkt_rank)",
                "team_ceiling.json (ceiling_score, tier)",
                "boom/schedule2026.json (week-17 opponent)",
            ],
            "stats": {
                "total_stacks_enumerated": total_stacks,
                "stacks_value_ct_ge2": stacks_value_ct_2plus,
                "teams_with_stacks": sum(1 for t in output_teams.values() if t["stacks"]),
            },
        },
        "teams": output_teams_sorted,
    }

    with open("stack_menu.json", "w") as f:
        json.dump(out, f, indent=2)

    # ── 7. Console verification ──────────────────────────────────────────────────
    print("=" * 72)
    print("STACK MENU BUILD COMPLETE")
    print("=" * 72)
    print(f"Total stacks enumerated : {total_stacks:,}")
    print(f"Stacks with value_ct>=2 : {stacks_value_ct_2plus:,}")
    print()

    # Top-8 teams by best stack_score
    team_best = []
    for team, td in output_teams_sorted.items():
        if td["stacks"]:
            best = td["stacks"][0]
            team_best.append((team, td["ceiling_score"], td["tier"], best))

    team_best.sort(key=lambda x: -x[3]["stack_score"])

    print("TOP-8 TEAMS BY BEST STACK SCORE:")
    print(f"{'Team':<5} {'Ceiling':>7} {'Tier':<7} {'Score':>6}  Stack")
    print("-" * 72)
    for team, cs, tier, best in team_best[:8]:
        qb = best["qb_name"]
        pieces = [m["name"] for m in best["members"] if m["pos"] != "QB"]
        rounds = [m["round_est"] for m in best["members"]]
        piece_str = " + ".join(pieces)
        round_str = "R" + "+R".join(str(r) for r in rounds)
        print(
            f"{team:<5} {cs:>7.1f} {tier:<7} {best['stack_score']:>6.4f}  "
            f"{qb} + {piece_str}  ({round_str})"
        )

    print()
    print("FADE-TIER CONTRAST (1 team, lowest ceiling_score):")
    fade_team = min(output_teams.items(), key=lambda kv: kv[1]["ceiling_score"])
    fade_name, fade_data = fade_team
    fade_best = fade_data["stacks"][0] if fade_data["stacks"] else None
    if fade_best:
        qb = fade_best["qb_name"]
        pieces = [m["name"] for m in fade_best["members"] if m["pos"] != "QB"]
        print(
            f"  {fade_name} ({fade_data['tier']}) ceiling={fade_data['ceiling_score']:.1f}  "
            f"best_score={fade_best['stack_score']:.4f}  "
            f"{qb} + {' + '.join(pieces)}"
        )

    print()
    print("stack_menu.json written.")
    print()


if __name__ == "__main__":
    build_stack_menu()
