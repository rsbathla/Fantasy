"""dfs/board — the DFS board, built on the SAME shared core as best ball.

Source list is matchup + environment + efficiency + opportunity (vs best ball's
ceiling/spike/value/advancement). Output adds per-week P(ceiling) for the requested weeks
via the shared core.playoff_week model, so the holistic per-matchup view and the best-ball
playoff overlay come from one implementation.
"""
import pandas as pd

from .. import core

EFFICIENCY = ["sis_epa", "rec_epa_route", "rush_epa_att", "route_yprr", "yprr_man"]
MATCHUP = ["opp_pass_cov_pctl", "opp_run_def_pctl", "opp_pass_rush_pctl"]
OPP_SHARE = ["snap_share_est", "route_tprr", "tgt_share", "car_pct"]


def _first(df, names):
    for n in names:
        if n in df.columns:
            s = pd.to_numeric(df[n], errors="coerce")
            if s.notna().any():
                return s
    return None


def _present(df, names):
    return [pd.to_numeric(df[c], errors="coerce") for c in names if c in df.columns]


def build_board(ff=None, weeks=(15, 16, 17)):
    """DFS board DataFrame: identity + fused matchup/efficiency/opportunity board +
    leverage + per-week P(ceiling) for `weeks`."""
    ff = ff or core.load_features()
    df = ff.df.reset_index(drop=True)
    pos = df["pos"]
    ss = core.SourceSet(pos)

    eff = _present(df, EFFICIENCY)
    if eff:
        ss.add_blend("efficiency", eff)
    for c in MATCHUP:  # softer opponent percentile -> better spot; invert at adoption if the
        if c in df.columns:  # column's polarity is "higher = tougher" (document per column)
            ss.add(c.replace("opp_", "").replace("_pctl", ""), pd.to_numeric(df[c], errors="coerce"))
    opp = _present(df, OPP_SHARE)
    if opp:
        ss.add_blend("opportunity", opp)

    board = core.fuse_board(ss)
    out = pd.concat([df[["name", "pos", "team"]], board], axis=1)
    out["leverage"] = [",".join(t) for t in core.leverage_flags(board)]

    mean = _first(df, ["proj_pg", "mean_pg"])
    cv = _first(df, ["cv", "cv_pg"])
    bars = df["pos"].map(core.config.CEILING_BAR).fillna(20.0)
    for wk in weeks:
        env_col = f"vegas_w{wk}_imp"
        env = pd.to_numeric(df[env_col], errors="coerce") / 24.0 if env_col in df.columns else None
        ps = []
        for i in range(len(df)):
            m = float(mean.iloc[i]) if mean is not None and pd.notna(mean.iloc[i]) else None
            c = float(cv.iloc[i]) if cv is not None and pd.notna(cv.iloc[i]) else None
            e = float(env.iloc[i]) if env is not None and pd.notna(env.iloc[i]) else 1.0
            ps.append(round(core.p_ceiling(m, c, float(bars.iloc[i]), env=e), 3) if (m and c) else 0.0)
        out[f"p_w{wk}"] = ps
    return out.sort_values("consensus", ascending=False).reset_index(drop=True)


if __name__ == "__main__":
    b = build_board()
    print(f"DFS board: {len(b)} players")
    print(b.head(12).to_string(index=False))
