#!/usr/bin/env python3
"""
build_matchup_notes.py
Produces matchup_notes.json for all 272 games across 18 weeks.
All data sourced from real files — no fabrication.
"""

import json
import os
from collections import defaultdict

# ── File paths ────────────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.abspath(__file__))
SCHEDULE_PATH = os.path.join(BASE, "boom", "schedule2026.json")
DFS_PATH = os.path.join(BASE, "dfs_season_baseline.json")
DEF_PROFILE_PATH = os.path.join(BASE, "boom", "defensive_profile.json")
OFF_PROFILE_PATH = os.path.join(BASE, "offense_profile.json")
TEAM_CEILING_PATH = os.path.join(BASE, "team_ceiling.json")
OUTPUT_PATH = os.path.join(BASE, "matchup_notes.json")


# ── Loaders ───────────────────────────────────────────────────────────────────
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Step 3: env_tier from total ───────────────────────────────────────────────
def env_tier(total):
    if total is None:
        return None
    if total >= 50:
        return "elite"
    if total >= 47:
        return "high"
    if total >= 43:
        return "mid"
    return "low"


# ── Step 4: Attack angle from defensive_profile ───────────────────────────────
def build_attack_angle(opp_team, def_profile):
    """Return a readable 1-sentence attack angle for the OPPOSING team's defense."""
    dp = def_profile.get(opp_team, {})
    funnels = dp.get("funnels", [])
    eng = dp.get("eng2026", {})
    lean_2025 = dp.get("lean_2025", "")
    lean_2026 = dp.get("lean_2026", "")

    pass_cov_pctl = eng.get("pass_cov_pctl")
    run_def_pctl = eng.get("run_def_pctl")
    pass_rush_pctl = eng.get("pass_rush_pctl")

    parts = []

    # Shift note
    shift_note = ""
    for f in funnels:
        if "[SHIFT" in f:
            shift_note = f
            break

    # Primary funnel detection
    has_run_funnel = any(
        "RUN funnel" in f or "soft vs run" in f for f in funnels
    )
    has_pass_funnel = any(
        "PASS funnel" in f or "soft vs pass" in f for f in funnels
    )
    has_te_funnel = any(
        "TE funnel" in f or "soft vs TE" in f for f in funnels
    )
    has_elite_rush = any("elite pass rush" in f for f in funnels)
    has_wr1_funnel = any("WR1 funnel" in f for f in funnels)
    has_slot_funnel = any("SLOT funnel" in f for f in funnels)
    has_outside_funnel = any("OUTSIDE funnel" in f for f in funnels)
    has_wr_fortress = any("WR fortress" in f for f in funnels)
    has_te_fortress = any("TE fortress" in f for f in funnels)

    # Build primary axis sentence
    attack_clauses = []

    if has_run_funnel:
        attack_clauses.append("RBs into soft run defense")
    if has_pass_funnel:
        attack_clauses.append("WRs/TEs vs soft pass coverage")
    if has_te_funnel and not has_pass_funnel:
        attack_clauses.append("TE is primary attack axis (soft vs TE)")
    if has_wr1_funnel:
        attack_clauses.append("top WR vs beatable top CB")
    if has_slot_funnel:
        attack_clauses.append("slot WR exploitable")
    if has_outside_funnel:
        attack_clauses.append("boundary WRs exploitable")
    if has_elite_rush:
        attack_clauses.append("pass rush limits QB ceiling; check-down volume up")

    # eng2026 soft-spot augmentation
    if pass_cov_pctl is not None and pass_cov_pctl < 20:
        if not has_pass_funnel:
            attack_clauses.append(
                f"very soft pass coverage (pass_cov_pctl={pass_cov_pctl:.0f})"
            )
    if run_def_pctl is not None and run_def_pctl < 25:
        if not has_run_funnel:
            attack_clauses.append(
                f"very soft run defense (run_def_pctl={run_def_pctl:.0f})"
            )

    # fortress / avoid notes
    avoid_clauses = []
    if has_wr_fortress:
        avoid_clauses.append("WRs depressed (WR fortress)")
    if has_te_fortress:
        avoid_clauses.append("TEs depressed (TE fortress)")

    # Lean shift
    shift_str = ""
    if lean_2025 and lean_2026 and lean_2025 != lean_2026:
        shift_str = f" [defense shifted from {lean_2025} → {lean_2026}]"

    if attack_clauses:
        attack = (
            f"{opp_team} D: "
            + "; ".join(attack_clauses)
            + (f"; avoid: {', '.join(avoid_clauses)}" if avoid_clauses else "")
            + shift_str
        )
    elif avoid_clauses:
        attack = (
            f"{opp_team} D: fortress mode — "
            + ", ".join(avoid_clauses)
            + shift_str
        )
    else:
        attack = f"{opp_team} D: neutral — no clear funnel exposed" + shift_str

    return attack


# ── Step 6: Offense identity labels ──────────────────────────────────────────
def off_id_label(pass_rate):
    if pass_rate is None:
        return "unknown"
    if pass_rate >= 56:
        return f"pass-heavy ({pass_rate:.1f}%)"
    if pass_rate >= 52:
        return f"pass-leaning ({pass_rate:.1f}%)"
    if pass_rate >= 48:
        return f"balanced ({pass_rate:.1f}%)"
    return f"run-leaning ({pass_rate:.1f}%)"


def pace_label(pctl):
    if pctl is None:
        return "avg-pace"
    if pctl >= 65:
        return "fast"
    if pctl >= 55:
        return "up-tempo"
    if pctl >= 40:
        return "avg-pace"
    return "slow"


# ── Step 7 & 8: Note and stack_take ──────────────────────────────────────────
def build_note(game_str, home_team, away_team, total, tier,
               fav, imp_home, imp_away,
               home_smash, away_smash,
               home_attack, away_attack,
               home_off_id, away_off_id,
               home_pace, away_pace):
    """Build 2-4 sentence note."""
    sentences = []

    # Sentence 1: total + tier context
    if total is not None:
        tier_str = f"Total {total:.1f} ({tier})"
        sentences.append(tier_str + ".")
    else:
        sentences.append("Total unknown (DFS data unavailable for this game).")
        return " ".join(sentences)

    # Sentence 2: favored side + implied edge
    if fav and imp_home is not None and imp_away is not None:
        diff = abs(imp_home - imp_away)
        fav_imp = imp_home if fav == home_team else imp_away
        dog_imp = imp_away if fav == home_team else imp_home
        dog = away_team if fav == home_team else home_team
        sentences.append(
            f"{fav} implied {fav_imp:.1f} vs {dog} {dog_imp:.1f} ({diff:.1f}-pt edge)."
        )

    # Sentence 3: attack angles and smash players
    attack_parts = []
    if home_attack:
        hs = f"{', '.join(home_smash[:2])}" if home_smash else "no clear smash spot"
        attack_parts.append(
            f"{home_team} attacks {home_attack.split(':', 1)[-1].strip()} [{hs}]"
        )
    if away_attack:
        as_ = f"{', '.join(away_smash[:2])}" if away_smash else "no clear smash spot"
        attack_parts.append(
            f"{away_team} attacks {away_attack.split(':', 1)[-1].strip()} [{as_}]"
        )
    if attack_parts:
        sentences.append("; ".join(attack_parts) + ".")

    # Sentence 4: pace / script context
    pace_parts = []
    if home_pace and home_off_id:
        pace_parts.append(f"{home_team}: {home_off_id}, {home_pace}")
    if away_pace and away_off_id:
        pace_parts.append(f"{away_team}: {away_off_id}, {away_pace}")
    if pace_parts:
        sentences.append("Offenses — " + " | ".join(pace_parts) + ".")

    return " ".join(sentences)


def build_stack_take(tier, home_team, away_team, imp_home, imp_away,
                     home_smash, away_smash):
    """One-liner stack recommendation."""
    if tier is None:
        return "Insufficient data to evaluate."

    # Determine lead side by implied score
    if imp_home is not None and imp_away is not None:
        if imp_home >= imp_away:
            lead, bring = home_team, away_team
            lead_smash = home_smash
        else:
            lead, bring = away_team, home_team
            lead_smash = away_smash
        lead_names = f" ({', '.join(lead_smash[:2])})" if lead_smash else ""
    else:
        lead, bring = home_team, away_team
        lead_smash = home_smash
        lead_names = f" ({', '.join(lead_smash[:2])})" if lead_smash else ""

    if tier == "elite":
        return (
            f"Elite game stack; lead {lead}{lead_names}, bring back {bring} WR/TE"
        )
    if tier == "high":
        return f"Solid stack game; {lead} preferred{lead_names}"
    if tier == "mid":
        return f"Moderate stack interest; {lead} side has edge{lead_names}"
    # low
    return f"Fade both offenses in DFS; low total suppresses ceilings"


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    # Load all data sources
    schedule = load_json(SCHEDULE_PATH)
    dfs_baseline = load_json(DFS_PATH)
    def_profile = load_json(DEF_PROFILE_PATH)
    off_profile = load_json(OFF_PROFILE_PATH)
    team_ceiling = load_json(TEAM_CEILING_PATH)

    # ── Step 1: Build weekly game list from schedule ──────────────────────────
    # weekly_games[wk] = list of (pair, home_team, away_team)
    weekly_games = defaultdict(dict)  # wk -> {pair: (home, away)}

    for team, games in schedule.items():
        for g in games:
            opp = g["opp"]
            if opp == "BYE":
                continue
            wk = str(g["wk"])
            pair = tuple(sorted([team, opp]))
            if pair in weekly_games[wk]:
                continue  # already recorded

            if g["home"]:
                home_team, away_team = team, opp
            else:
                home_team, away_team = opp, team

            weekly_games[wk][pair] = (home_team, away_team)

    # ── Step 2: Index DFS players by week → team ────────────────────────────
    # dfs_by_week_team[wk][team] = list of player dicts
    dfs_by_week_team = defaultdict(lambda: defaultdict(list))
    for wk, wdata in dfs_baseline["weeks"].items():
        for p in wdata["players"]:
            dfs_by_week_team[wk][p["team"]].append(p)

    # ── Build output ─────────────────────────────────────────────────────────
    output_weeks = {}

    for wk in sorted(weekly_games.keys(), key=lambda x: int(x)):
        games_this_week = []

        for pair, (home_team, away_team) in weekly_games[wk].items():
            # ── DFS totals + implied scores ──────────────────────────────────
            home_players = dfs_by_week_team[wk].get(home_team, [])
            away_players = dfs_by_week_team[wk].get(away_team, [])

            # Get game total (same for both sides)
            total = None
            for p in home_players + away_players:
                if p.get("total") is not None:
                    total = p["total"]
                    break

            # Implied scores per side
            imp_home = None
            for p in home_players:
                if p.get("imp") is not None:
                    imp_home = p["imp"]
                    break

            imp_away = None
            for p in away_players:
                if p.get("imp") is not None:
                    imp_away = p["imp"]
                    break

            # ── env_tier ────────────────────────────────────────────────────
            tier = env_tier(total)

            # ── Favored side ─────────────────────────────────────────────────
            fav = None
            spread_read = None
            if imp_home is not None and imp_away is not None:
                if imp_home > imp_away:
                    fav = home_team
                    diff = imp_home - imp_away
                    spread_read = f"{home_team} +{diff:.1f} implied edge"
                elif imp_away > imp_home:
                    fav = away_team
                    diff = imp_away - imp_home
                    spread_read = f"{away_team} +{diff:.1f} implied edge"
                else:
                    fav = None
                    spread_read = "Pick'em"

            # ── Step 4: Attack angles ─────────────────────────────────────────
            # home offense attacks away defense
            home_attack = build_attack_angle(away_team, def_profile)
            # away offense attacks home defense
            away_attack = build_attack_angle(home_team, def_profile)

            # ── Step 5: Top smash players per side ───────────────────────────
            def top_smash(players):
                smash_ps = [p for p in players if p.get("n_smash", 0) >= 1]
                smash_ps.sort(key=lambda p: p.get("edge_score", 0), reverse=True)
                return [p["name"] for p in smash_ps[:3]]

            home_smash = top_smash(home_players)
            away_smash = top_smash(away_players)

            # ── Step 6: Offense identity ──────────────────────────────────────
            home_op = off_profile.get(home_team, {})
            away_op = off_profile.get(away_team, {})

            home_pass_rate = home_op.get("pass_rate")
            away_pass_rate = away_op.get("pass_rate")
            home_pace_pctl = (home_op.get("pace") or {}).get("pctl")
            away_pace_pctl = (away_op.get("pace") or {}).get("pctl")

            home_off_id = off_id_label(home_pass_rate)
            away_off_id = off_id_label(away_pass_rate)
            home_pace_str = pace_label(home_pace_pctl)
            away_pace_str = pace_label(away_pace_pctl)

            # ── Step 7: Generate note ─────────────────────────────────────────
            game_str = f"{away_team} @ {home_team}"
            note = build_note(
                game_str, home_team, away_team, total, tier,
                fav, imp_home, imp_away,
                home_smash, away_smash,
                home_attack, away_attack,
                home_off_id, away_off_id,
                home_pace_str, away_pace_str,
            )

            # ── Step 8: Stack take ────────────────────────────────────────────
            stack_take = build_stack_take(
                tier, home_team, away_team, imp_home, imp_away,
                home_smash, away_smash,
            )

            # ── Assemble game record ──────────────────────────────────────────
            game_record = {
                "game": game_str,
                "teams": [away_team, home_team],
                "sides": {
                    home_team: {
                        "attack": home_attack,
                        "smash": home_smash,
                        "off_id": home_off_id,
                        "pace": home_pace_str,
                    },
                    away_team: {
                        "attack": away_attack,
                        "smash": away_smash,
                        "off_id": away_off_id,
                        "pace": away_pace_str,
                    },
                },
                "note": note,
                "stack_take": stack_take,
            }

            # Only add total/env_tier/fav/spread_read when DFS data present
            if total is not None:
                game_record["total"] = total
                game_record["env_tier"] = tier
            if fav is not None:
                game_record["fav"] = fav
            if spread_read is not None:
                game_record["spread_read"] = spread_read

            games_this_week.append(game_record)

        # Sort by total desc within week (games without total go last)
        games_this_week.sort(
            key=lambda g: g.get("total", -1), reverse=True
        )

        output_weeks[wk] = {"games": games_this_week}

    # ── Assemble final output ─────────────────────────────────────────────────
    output = {
        "_meta": {
            "built": "2026-07-03",
            "source": (
                "dfs_season_baseline.json + boom/schedule2026.json + "
                "boom/defensive_profile.json + offense_profile.json + team_ceiling.json"
            ),
            "surfaces": ["dfs"],
        },
        "weeks": output_weeks,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    # ── Report ────────────────────────────────────────────────────────────────
    total_games = sum(len(w["games"]) for w in output_weeks.values())
    print(f"matchup_notes.json written to {OUTPUT_PATH}")
    print(f"Total game notes: {total_games}")
    print("\nPer-week game counts:")
    for wk in sorted(output_weeks.keys(), key=lambda x: int(x)):
        cnt = len(output_weeks[wk]["games"])
        print(f"  Week {wk:>2}: {cnt} games")


if __name__ == "__main__":
    main()
