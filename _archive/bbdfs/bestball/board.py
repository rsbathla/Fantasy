"""bb/board — the BEST-BALL board, built on the shared core.

Fuses season-long ceiling + spike + value-vs-ADP + advancement into one within-position
board (via core.fuse_board), then attaches a playoff_up overlay from the shared
core.playoff_week model. Reads columns defensively: a concept with no present column
simply abstains (and FeatureFrame.require can be used by the caller to fail loud instead).
"""
import pandas as pd

from .. import core

CEILING = ["p95", "ceiling_p95", "ceil_pct"]
SPIKE = ["spike", "spike_pct", "spike_rate"]
ADVANCE = ["adv_pct", "adv_pctl", "proj_pg"]
MEAN = ["proj_pg", "mean_pg"]
CV = ["cv", "cv_pg"]


def _first(df, names):
    for n in names:
        if n in df.columns:
            s = pd.to_numeric(df[n], errors="coerce")
            if s.notna().any():
                return s
    return None


def _playoff_overlay(df):
    """Per-player playoff ceiling via the SHARED playoff_week model. Without per-week Vegas
    columns it degrades to a flat-environment ceiling (env=1.0) — but uses the one model,
    so wiring per-week env/matchup later is a parameter, not a rewrite."""
    mean = _first(df, MEAN)
    cv = _first(df, CV)
    if mean is None or cv is None:
        return pd.Series([0.0] * len(df))
    bars = df["pos"].map(core.config.CEILING_BAR).fillna(20.0)
    ups = []
    for m, c, b in zip(mean, cv, bars):
        if m and c:
            p = core.p_ceiling(float(m), float(c), float(b))
            ups.append(core.playoff_up(p, p, p))
        else:
            ups.append(0.0)
    return pd.Series(ups)


def build_board(ff=None, *, platform="DK"):
    """Best-ball board DataFrame: identity + fused consensus/divergence + leverage +
    playoff_up + an illustrative bb_score (config-weighted blend of season ceiling and
    playoff ceiling)."""
    ff = ff or core.load_features()
    df = ff.df.reset_index(drop=True)
    pos = df["pos"]
    ss = core.SourceSet(pos)
    for label, names, invert in [("ceiling", CEILING, False), ("spike", SPIKE, False),
                                 ("advancement", ADVANCE, False)]:
        s = _first(df, names)
        if s is not None:
            ss.add(label, s, invert=invert)
    if "adp" in df.columns:  # earlier ADP = scarcer; invert so 'value' rises for later-ADP upside
        ss.add("value", pd.to_numeric(df["adp"], errors="coerce"), invert=True)

    board = core.fuse_board(ss)
    out = pd.concat([df[["name", "pos", "team"]], board], axis=1)
    out["leverage"] = [",".join(t) for t in core.leverage_flags(board)]
    out["playoff_up"] = _playoff_overlay(df)

    pu = out["playoff_up"]
    pu_scaled = (pu / (pu.max() or 1.0)) * 100.0
    w = core.config.CEILING_WEIGHT
    out["bb_score"] = (w * board["consensus"].fillna(50) + (1 - w) * pu_scaled).round(1)
    return out.sort_values("bb_score", ascending=False).reset_index(drop=True)


if __name__ == "__main__":
    b = build_board()
    print(f"BB board: {len(b)} players, {b['n_votes'].max()} max votes")
    print(b.head(12).to_string(index=False))
