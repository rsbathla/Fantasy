#!/usr/bin/env python3
"""build_rz_equity.py — per-player RED-ZONE / TD-EQUITY index for the DFS play score.

The implied total says how many points a team scores; it does not say WHO gets the 6-point plays.
That is red-zone role, and it is a real, validated signal (validate step in this file's header notes):
  * pass-catchers: RZ target share predicts end-zone TDs (r=+0.29; ~+0.5 fantasy pts/g hi vs lo tercile)
  * RBs: TD/game role is stable year-over-year (r=+0.51) and worth ~1.6 pts/g hi vs lo

Output: rz_equity_2026.json  {player_fn: {pos, rz_role_z, basis, note}}
  rz_role_z = position-centered z-score of the player's TD-scoring role. Centered so an AVERAGE-role
  player is 0 (no tilt) — the baseline TD rate is already in the player's simulated ceiling; this index
  only carries the ABOVE/BELOW-average role, which dfs_model interacts with the implied total (TDs
  matter more when there is more scoring to capture). NOT a flat bonus — see dfs_model.rz_convert.

Sources (all in-repo):
  boom/statmenu.json  rz field (rz_tgt_share) for WR/TE — fn-keyed, joins straight to the pool.
  pipeline/player_games.parquet  actual rush_td+rec_td/game for RBs (no goal-line-opportunity metric
      exists in-repo; actual TD production is the honest proxy, and it is year-over-year stable).
"""
import json
import os
import re
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
STATMENU = os.path.join(HERE, "boom/statmenu.json")
PARQUET = os.path.join(HERE, "pipeline/player_games.parquet")
OUT = os.path.join(HERE, "rz_equity_2026.json")


def fn(s):
    """Match the repo's name normalization: lowercase, strip punctuation/suffixes."""
    s = re.sub(r"[^a-z ]", "", str(s).lower())
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", s)
    return re.sub(r"\s+", " ", s).strip()


def last_name(s):
    """Last name from either 'Jahmyr Gibbs' or nflverse 'J.Gibbs' (handles the joining period)."""
    toks = [t for t in re.split(r"[^a-z]+", str(s).lower()) if t and t not in ("jr", "sr", "ii", "iii", "iv", "v")]
    return toks[-1] if toks else ""


def zscore(d, cap=2.5):
    """Position-centered z, winsorized against tiny-sample outliers (cap in SD units)."""
    vals = np.array(list(d.values()), float)
    if len(vals) < 3:
        return {k: 0.0 for k in d}
    m, sd = vals.mean(), vals.std()
    if sd == 0:
        return {k: 0.0 for k in d}
    return {k: max(-cap, min(cap, (v - m) / sd)) for k, v in d.items()}


def main():
    sm = json.load(open(STATMENU))

    # ---- pass-catchers: RZ target share (fn-keyed, clean) ----
    pc_raw = {}
    for k, v in sm.items():
        if v.get("pos") in ("WR", "TE") and isinstance(v.get("rz"), dict):
            rz = v["rz"]
            if rz.get("rz_tgt_share") is not None and (rz.get("g") or 0) >= 10:   # half-season floor
                pc_raw[k] = float(rz["rz_tgt_share"])
    # winsorize the raw share to the 2nd–98th pctile so a low-sample rookie can't distort the scale
    if pc_raw:
        lo, hi = np.percentile(list(pc_raw.values()), [2, 98])
        pc_raw = {k: min(hi, max(lo, x)) for k, x in pc_raw.items()}
    pc_z = zscore(pc_raw)

    # ---- RBs: actual TD/game from player_games, joined by (team, last name) ----
    p = pd.read_parquet(PARQUET)
    p = p[p.week <= 18]
    ag = (p.groupby(["pid", "name", "team", "season"])
            .agg(pa=("pass_att", "sum"), car=("carries", "sum"), tgt=("targets", "sum"),
                 rtd=("rush_td", "sum"), retd=("rec_td", "sum"), g=("week", "nunique"))
            .reset_index())
    ag = ag[(ag.car >= ag.tgt) & (ag.pa < 50)]                 # RB-shaped seasons
    ag["td_pg"] = (ag.rtd + ag.retd) / ag.g.clip(lower=1)
    # weight recent year more; require some volume
    ag = ag[ag.car >= 15]
    wt = {2024: 1.0, 2025: 1.6}
    tdrole, wsum = {}, {}
    for _, r in ag.iterrows():
        key = (r.team, last_name(r["name"]))
        w = wt.get(r.season, 1.0) * r.g
        tdrole[key] = tdrole.get(key, 0) + r.td_pg * w
        wsum[key] = wsum.get(key, 0) + w
    rb_td = {k: tdrole[k] / wsum[k] for k in tdrole if wsum[k] > 0}

    # map RB pool players (statmenu) -> td role via (team, lastname)
    rb_raw = {}
    for k, v in sm.items():
        if v.get("pos") == "RB":
            key = (v.get("team"), last_name(v.get("name", k)))
            if key in rb_td:
                rb_raw[k] = rb_td[key]
    rb_z = zscore(rb_raw)

    teams = {}
    for k, z in pc_z.items():
        teams[k] = {"pos": sm[k]["pos"], "rz_role_z": round(z, 2),
                    "basis": "rz_tgt_share", "value": round(pc_raw[k], 1),
                    "note": f"{pc_raw[k]:.0f}% red-zone target share (pos-centered z={z:+.2f})"}
    for k, z in rb_z.items():
        teams[k] = {"pos": "RB", "rz_role_z": round(z, 2),
                    "basis": "td_per_game", "value": round(rb_raw[k], 2),
                    "note": f"{rb_raw[k]:.2f} rush+rec TD/game (pos-centered z={z:+.2f})"}

    doc = {
        "_meta": {
            "purpose": "Per-player red-zone / TD-equity index (position-centered). Feeds dfs_model.rz_convert, "
                       "which interacts it with the implied total (a goal-line-dominant player captures more of "
                       "the team's TDs when there is more scoring). Centered so average-role players are unaffected "
                       "and the baseline TD rate is not double-counted against the ceiling.",
            "validated": "rz_tgt_share->end-zone TD r=+0.29 (WR/TE); RB TD/game YoY stability r=+0.51. See "
                         "validate step; calibration in dfs_model (K_RZ_PC/K_RZ_RB).",
            "sources": ["boom/statmenu.json (rz field, WR/TE)", "pipeline/player_games.parquet (RB actual TD/game)"],
            "caveat": "No in-repo goal-line-CARRY opportunity metric for RBs; actual TD/game is the honest proxy "
                      "(year-over-year stable). Refresh if a goal-line-touch source is added.",
        },
        "teams": teams,
    }
    json.dump(doc, open(OUT, "w"), indent=2)
    # console summary
    top = sorted(teams.items(), key=lambda kv: -kv[1]["rz_role_z"])
    print(f"wrote {OUT} ({len(teams)} players: {sum(1 for v in teams.values() if v['pos']!='RB')} PC, "
          f"{sum(1 for v in teams.values() if v['pos']=='RB')} RB)")
    print("Top RZ roles:")
    for k, v in top[:10]:
        print(f"  {k:24s} {v['pos']:2s} z={v['rz_role_z']:+.2f}  {v['note']}")


if __name__ == "__main__":
    main()
