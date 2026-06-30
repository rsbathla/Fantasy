"""dfs/matchup — the holistic per-player / per-matchup view.

Assembles, for one player, the matchup-relevant signals (opponent defense tiers, coverage
fit, efficiency, opportunity, environment) into a single card — the "holistic view of each
player and matchup" the DFS model is for. Pure read over the shared feature store; no
private parsing or percentile copies.
"""
import pandas as pd

from .. import core

CARD_FIELDS = {
    "efficiency": ["sis_epa", "rec_epa_route", "rush_epa_att", "route_yprr"],
    "matchup": ["opp_pass_cov_pctl", "opp_run_def_pctl", "opp_pass_rush_pctl"],
    "opportunity": ["snap_share_est", "route_tprr", "tgt_share", "car_pct"],
    "coverage_fit": ["rec_man_zone_delta", "rec_epa_man", "rec_epa_zone"],
}


def player_card(name, ff=None):
    """Return a dict of {section: {field: value}} for one player, plus identity. Missing
    fields are omitted (abstain), never faked."""
    ff = ff or core.load_features()
    key = core.fn(name)
    df = ff.df
    row = df[df["name"].map(core.fn) == key]
    if row.empty:
        return {"name": name, "found": False}
    r = row.iloc[0]
    card = {"name": r.get("name"), "pos": r.get("pos"), "team": r.get("team"), "found": True}
    for section, fields in CARD_FIELDS.items():
        vals = {}
        for f in fields:
            if f in df.columns:
                v = pd.to_numeric(pd.Series([r.get(f)]), errors="coerce").iloc[0]
                if pd.notna(v):
                    vals[f] = round(float(v), 3)
        if vals:
            card[section] = vals
    return card


if __name__ == "__main__":
    import sys
    who = sys.argv[1] if len(sys.argv) > 1 else "Puka Nacua"
    import json
    print(json.dumps(player_card(who), indent=2))
