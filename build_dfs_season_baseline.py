#!/usr/bin/env python3
"""
build_dfs_season_baseline.py

Runs dfs_model.py for weeks 1..18, reads dfs_week.json after each run,
trims players, and accumulates into dfs_season_baseline.json.
"""

import json
import subprocess
import sys
import os

SCRIPT_DIR = "/root/bestball/bestball"
MODEL_SCRIPT = os.path.join(SCRIPT_DIR, "dfs_model.py")
WEEK_JSON = os.path.join(SCRIPT_DIR, "dfs_week.json")
OUTPUT_JSON = os.path.join(SCRIPT_DIR, "dfs_season_baseline.json")

PLAYER_FIELDS = {
    "name", "pos", "team", "opp", "play", "edge_score",
    "n_smash", "imp", "total", "ceil", "proj", "rank",
    "pos_rank", "home", "dome", "edges", "script_mult", "proe_mult", "rz_mult"
}

TOP_N_BY_PLAY = 60


def trim_players(players):
    """
    Keep top 60 by play score PLUS all with n_smash >= 1.
    Trim each player to only the required fields.
    """
    # Sort by play descending to identify top 60
    sorted_players = sorted(players, key=lambda p: p.get("play", 0), reverse=True)
    top60_names = {p["name"] for p in sorted_players[:TOP_N_BY_PLAY]}

    kept = []
    for p in players:
        if p["name"] in top60_names or p.get("n_smash", 0) >= 1:
            trimmed = {k: v for k, v in p.items() if k in PLAYER_FIELDS}
            kept.append(trimmed)

    return kept


def run_week(week_num):
    """
    Run dfs_model.py --week N. Returns (success, error_msg).
    """
    cmd = ["python3", MODEL_SCRIPT, "--week", str(week_num)]
    print(f"  Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=SCRIPT_DIR
        )
        if result.returncode != 0:
            stderr_snippet = result.stderr[-500:] if result.stderr else "(no stderr)"
            return False, f"Exit code {result.returncode}: {stderr_snippet}"
        return True, None
    except subprocess.TimeoutExpired:
        return False, "Timed out after 300s"
    except Exception as e:
        return False, str(e)


def read_week_json():
    """Read and return parsed dfs_week.json, or raise on error."""
    with open(WEEK_JSON, "r") as f:
        return json.load(f)


def main():
    weeks_data = {}
    succeeded = []
    failed = []
    meta_built = "2026-07-03"  # fallback; will try to pull from week 1 json
    week1_built_checked = False

    for week in range(1, 19):
        print(f"\n[Week {week}/18]")
        ok, err = run_week(week)

        if not ok:
            print(f"  FAILED: {err}")
            failed.append((week, err))
            continue

        # Read the JSON written by the model
        try:
            data = read_week_json()
        except Exception as e:
            print(f"  ERROR reading dfs_week.json: {e}")
            failed.append((week, f"JSON read error: {e}"))
            continue

        # Grab built field from week 1 for _meta
        if not week1_built_checked:
            week1_built_checked = True
            built_val = data.get("built")
            if built_val:
                meta_built = built_val
                print(f"  _meta.built set from week 1 json: {meta_built}")
            else:
                print(f"  week 1 built=null in JSON, using fallback: {meta_built}")

        n_players = data.get("n_players", len(data.get("players", [])))
        players_raw = data.get("players", [])
        anchor_games = data.get("anchor_games", [])

        players_trimmed = trim_players(players_raw)
        n_kept = len(players_trimmed)
        n_smash_count = sum(1 for p in players_trimmed if p.get("n_smash", 0) >= 1)

        weeks_data[str(week)] = {
            "n_players": n_players,
            "anchor_games": anchor_games,
            "players": players_trimmed,
        }

        print(f"  OK — n_players={n_players}, kept={n_kept} (smash>0: {n_smash_count}), anchor_games={len(anchor_games)}")
        succeeded.append(week)

    # Build final structure
    output = {
        "_meta": {
            "built": meta_built,
            "surfaces": ["dfs"]
        },
        "weeks": weeks_data
    }

    with open(OUTPUT_JSON, "w") as f:
        json.dump(output, f, separators=(",", ":"))

    file_size = os.path.getsize(OUTPUT_JSON)

    print("\n" + "=" * 60)
    print(f"Succeeded weeks: {succeeded}")
    if failed:
        print(f"Failed weeks:    {[(w, e[:80]) for w, e in failed]}")
    else:
        print("Failed weeks:    none")
    print(f"Output file:     {OUTPUT_JSON}")
    print(f"File size:       {file_size:,} bytes ({file_size / 1024:.1f} KB)")
    print("=" * 60)

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
