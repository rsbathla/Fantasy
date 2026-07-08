#!/usr/bin/env python3
"""fetch_tendencies.py — pull nflverse play-by-play and compute the play-caller tendency fields
our offense_profile.json is missing (identified in DIVERGENCE_DOCKET_2026.md).

RUN ON YOUR MAC (the cloud sandbox can't reach nflverse):
    pip install pandas pyarrow requests --break-system-packages   # if needed
    python3 fetch_tendencies.py            # seasons 2023-2025

COMPUTES per team-season (writes data/nflverse/tendencies_2023_2025.json + .csv):
  uc_rate        under-center rate on dropbacks (1 - shotgun) — the Hurts/Daniels/Barkley lever
  gl_pass_rate   pass rate inside the opponent 10 (goal-line tendency — Kubiak vs McCarthy)
  gl_proe        pass rate over expected inside the 10 (uses nflfastR xpass)
  proe           overall PROE (cross-check vs data/fantasypoints/proe_offense_2025.csv)
  bf_tgt_share   share of team targets going to RBs (backfield receiving pie)
  i5_rb_share    share of team carries inside the 5 going to RBs (vs QB keepers)
  pace_s         seconds per play, neutral situations (score within 8, Q1-3)

STILL NEEDS FPDS EXPORTS (not in public pbp — pull from fpds.fantasypoints.com):
  during-snap motion rate (team + player)   <- the article's headline cheat code
  designed targets & screens by team        <- Bijan/Achane/Etienne mechanism
  route participation % by player           <- the 70/75/80% breakout gates
  1D/RR by player
Drop those exports in data/fantasypoints/ and I'll wire them into offense_profile.json.
"""
import io, json, os, sys

try:
    import pandas as pd
    import requests
except ImportError:
    sys.exit("pip install pandas pyarrow requests --break-system-packages")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "nflverse")
os.makedirs(OUT, exist_ok=True)
SEASONS = [2023, 2024, 2025]
PBP = "https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{y}.parquet"
ROST = "https://github.com/nflverse/nflverse-data/releases/download/weekly_rosters/roster_weekly_{y}.parquet"

def get_parquet(url, cache):
    path = os.path.join(OUT, cache)
    if not os.path.exists(path):
        print(f"  downloading {cache} ...", flush=True)
        r = requests.get(url, timeout=300, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        open(path, "wb").write(r.content)
    return pd.read_parquet(path)

rows = []
for y in SEASONS:
    print(f"season {y}")
    pbp = get_parquet(PBP.format(y=y), f"pbp_{y}.parquet")
    ros = get_parquet(ROST.format(y=y), f"roster_{y}.parquet")
    pos = (ros.drop_duplicates("gsis_id")[["gsis_id", "position"]]
              .set_index("gsis_id")["position"].to_dict())
    pbp = pbp[pbp.season_type == "REG"]
    off = pbp[pbp.posteam.notna() & pbp.play_type.isin(["pass", "run"])].copy()
    off["is_pass"] = (off.play_type == "pass").astype(int)
    off["rb_target"] = off.receiver_player_id.map(pos).eq("RB") & (off.play_type == "pass")
    off["rb_carry"] = off.rusher_player_id.map(pos).eq("RB") & (off.play_type == "run")

    for tm, g in off.groupby("posteam"):
        db = g[g.is_pass == 1]
        uc = 1 - g[g.qb_dropback == 1].shotgun.mean() if "shotgun" in g else None
        gl = g[g.yardline_100 <= 10]
        gl_pass = gl.is_pass.mean() if len(gl) else None
        gl_proe = (gl.is_pass - gl.xpass).mean() if ("xpass" in gl and len(gl)) else None
        proe = (g.is_pass - g.xpass).mean() if "xpass" in g else None
        tgt = g[g.play_type == "pass"]
        bf_tgt = tgt.rb_target.sum() / max(len(tgt), 1)
        i5 = g[(g.yardline_100 <= 5) & (g.play_type == "run")]
        i5_rb = i5.rb_carry.sum() / max(len(i5), 1) if len(i5) else None
        neutral = g[(g.score_differential.abs() <= 8) & (g.qtr <= 3)]
        pace = None
        if "game_seconds_remaining" in neutral and len(neutral) > 50:
            n = neutral.sort_values(["game_id", "play_id"])
            dt = n.groupby("game_id").game_seconds_remaining.diff(-1)
            pace = float(dt[(dt > 0) & (dt < 60)].mean())
        rows.append(dict(season=y, team=tm,
                         uc_rate=round(float(uc), 3) if uc is not None else None,
                         gl_pass_rate=round(float(gl_pass), 3) if gl_pass is not None else None,
                         gl_proe=round(float(gl_proe), 3) if gl_proe is not None else None,
                         proe=round(float(proe), 3) if proe is not None else None,
                         bf_tgt_share=round(float(bf_tgt), 3),
                         i5_rb_share=round(float(i5_rb), 3) if i5_rb is not None else None,
                         pace_s=round(pace, 1) if pace else None))
    print(f"  {y}: {off.posteam.nunique()} teams")

df = pd.DataFrame(rows)
df.to_csv(os.path.join(OUT, "tendencies_2023_2025.csv"), index=False)
json.dump(rows, open(os.path.join(OUT, "tendencies_2023_2025.json"), "w"), indent=1)
print(f"\nwrote {len(rows)} team-seasons -> data/nflverse/tendencies_2023_2025.{{csv,json}}")
print("zip data/nflverse and attach it in chat, and I'll fold the fields into offense_profile.json")
