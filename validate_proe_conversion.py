#!/usr/bin/env python3
"""
validate_proe_conversion.py  —  Does pass-tendency (PROE) predict pass-catchers
over-converting the Vegas implied total, week by week, and does it replicate in a
prior year?

WHY THIS EXISTS
---------------
`env_blend.py` anchors team scoring on the Vegas total. The open question was the
*conversion* layer: given a team's implied points, do its WR/TE (pass catchers)
score MORE fantasy than the implied total alone predicts when the team is pass-lean,
and its RBs more when run-lean? PROE (Pass Rate Over Expected) is the tendency
signal. This script measures the relationship on COMPLETE per-game data and checks
whether it is (a) forward-usable and (b) stable across seasons.

DATA (all in-repo, ground-truth registered)
  pipeline/player_games.parquet        complete per-game DK points + box scores, 2024 & 2025
  data/nflverse/games_2021_2025.csv    closing Vegas lines (spread_line, total_line)
  data/fantasypoints/proe_offense_2025.csv   real FantasyPoints PROE, 2025 only

METHOD
  1. Position by season-level dominant action (QB / RB / PC=WR+TE). Spot-checked.
  2. Aggregate to TEAM-WEEK: DK by position bucket; team pass_att, carries.
  3. Vegas: implied_total, team_spread (positive = favored) per team-week.
  4. Residual = DK - E[DK | implied_total]   (per-season OLS, so residual is
     "fantasy ABOVE what the market's implied total already prices in").
  5. Real PROE (2025): season, same-week, and TRAILING (weeks < w) — trailing is the
     only forward-usable variant; same-week shares the pass-volume mechanism.
  6. PROE PROXY (both years): pass_rate - E[pass_rate | spread, implied_total].
     VALIDATED against real 2025 PROE before it is trusted for 2024.
  7. Conversion test: corr(PROE, PC_residual) + high/low tercile split, per season.

Nothing here is a 2026 projection. 2024 & 2025 are completed, actual seasons.
"""
import json
import numpy as np
import pandas as pd

PARQUET = "pipeline/player_games.parquet"
GAMES   = "data/nflverse/games_2021_2025.csv"
PROE_OFF= "data/fantasypoints/proe_offense_2025.csv"
REG_WEEKS = list(range(1, 19))   # regular season only


# ----------------------------------------------------------------------------- helpers
def ols_resid(x, y):
    """residual of y after linear fit on x; also return slope,intercept,r."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    if len(x) < 3:
        return np.full(m.shape, np.nan), (np.nan, np.nan, np.nan)
    b, a = np.polyfit(x, y, 1)            # y = b*x + a
    pred = b * x + a
    resid = np.full(m.shape, np.nan)
    resid[m] = y - pred
    r = np.corrcoef(x, y)[0, 1]
    return resid, (b, a, r)


def corr(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 3:
        return np.nan, int(m.sum())
    return float(np.corrcoef(x[m], y[m])[0, 1]), int(m.sum())


def tercile_split(df, signal, target):
    """mean target in top vs bottom tercile of signal; return (hi, lo, spread, n)."""
    d = df[[signal, target]].dropna()
    if len(d) < 15:
        return np.nan, np.nan, np.nan, len(d)
    q1, q2 = d[signal].quantile([1/3, 2/3])
    hi = d[d[signal] >= q2][target].mean()
    lo = d[d[signal] <= q1][target].mean()
    return hi, lo, hi - lo, len(d)


# ----------------------------------------------------------------------------- load
def load_team_week():
    p = pd.read_parquet(PARQUET)
    p = p[p.week.isin(REG_WEEKS)].copy()

    # position by season-level dominant action
    agg = (p.groupby(["pid", "season"])
             .agg(pa=("pass_att", "sum"), car=("carries", "sum"), tgt=("targets", "sum"))
             .reset_index())
    def _pos(r):
        if r.pa >= 50 and r.pa >= r.car and r.pa >= r.tgt:
            return "QB"
        if r.car >= r.tgt:
            return "RB"
        return "PC"
    agg["pos"] = agg.apply(_pos, axis=1)
    p = p.merge(agg[["pid", "season", "pos"]], on=["pid", "season"], how="left")

    # team-week DK by bucket (pivot) + team attempts (sum)
    dk = (p.pivot_table(index=["team", "season", "week"], columns="pos",
                        values="dk", aggfunc="sum", fill_value=0.0)
            .rename(columns={"PC": "dk_PC", "RB": "dk_RB", "QB": "dk_QB"})
            .reset_index())
    for c in ["dk_PC", "dk_RB", "dk_QB"]:
        if c not in dk:
            dk[c] = 0.0
    att = (p.groupby(["team", "season", "week"])[["pass_att", "carries"]]
             .sum().reset_index())
    tw = dk.merge(att, on=["team", "season", "week"], how="left")
    tw["pass_rate"] = tw.pass_att / (tw.pass_att + tw.carries)
    return tw


def load_vegas():
    g = pd.read_csv(GAMES)
    g = g[(g.game_type == "REG") & (g.week.isin(REG_WEEKS))].copy()
    rows = []
    for _, r in g.iterrows():
        it = r.total_line
        if pd.isna(it) or pd.isna(r.spread_line):
            continue
        # spread_line: positive = HOME favored
        rows.append(dict(team=r.home_team, season=r.season, week=r.week,
                         implied=it/2 + r.spread_line/2, spread=r.spread_line))
        rows.append(dict(team=r.away_team, season=r.season, week=r.week,
                         implied=it/2 - r.spread_line/2, spread=-r.spread_line))
    return pd.DataFrame(rows)


def load_real_proe():
    df = pd.read_csv(PROE_OFF)
    wk = [c for c in df.columns if c.startswith("w") and c[1:].isdigit()]
    long = df.melt(id_vars=["team"], value_vars=wk, var_name="week", value_name="proe")
    long["week"] = long.week.str[1:].astype(int)
    long["season"] = 2025
    long = long.dropna(subset=["proe"])
    # trailing = mean of prior weeks (forward-usable); needs >=3 prior obs
    long = long.sort_values(["team", "week"])
    long["proe_trail"] = (long.groupby("team")["proe"]
                              .transform(lambda s: s.shift(1).expanding(min_periods=3).mean()))
    season = df.set_index("team")["proe_season"].to_dict()
    long["proe_season"] = long.team.map(season)
    return long[["team", "season", "week", "proe", "proe_trail", "proe_season"]]


# ----------------------------------------------------------------------------- build
tw = load_team_week()
veg = load_vegas()
tw = tw.merge(veg, on=["team", "season", "week"], how="inner")

# residuals of position DK vs implied total, fit PER SEASON
tw["PC_resid"] = np.nan
tw["RB_resid"] = np.nan
fits = {}
for s in sorted(tw.season.unique()):
    m = tw.season == s
    tw.loc[m, "PC_resid"], fits[(s, "PC")] = ols_resid(tw.loc[m, "implied"], tw.loc[m, "dk_PC"])
    tw.loc[m, "RB_resid"], fits[(s, "RB")] = ols_resid(tw.loc[m, "implied"], tw.loc[m, "dk_RB"])

# PROE proxy (both years): pass_rate over script-expectation
tw["proe_proxy"] = np.nan
for s in sorted(tw.season.unique()):
    m = tw.season == s
    X = tw.loc[m, ["spread", "implied"]].values
    y = tw.loc[m, "pass_rate"].values
    ok = np.isfinite(y) & np.isfinite(X).all(1)
    A = np.column_stack([X[ok], np.ones(ok.sum())])
    coef, *_ = np.linalg.lstsq(A, y[ok], rcond=None)
    pred = np.full(len(y), np.nan)
    pred[ok] = A @ coef
    tw.loc[m, "proe_proxy"] = (y - pred) * 100  # to PROE-like percentage points
# trailing proxy (forward-usable)
tw = tw.sort_values(["season", "team", "week"])
tw["proe_proxy_trail"] = (tw.groupby(["season", "team"])["proe_proxy"]
                            .transform(lambda s: s.shift(1).expanding(min_periods=3).mean()))

# real PROE onto 2025 rows
rp = load_real_proe()
tw = tw.merge(rp, on=["team", "season", "week"], how="left")


# ----------------------------------------------------------------------------- report
print("=" * 78)
print("PROE -> PASS-CATCHER CONVERSION  |  complete per-game data, team-week grain")
print("=" * 78)
print(f"team-weeks: 2024={ (tw.season==2024).sum() }   2025={ (tw.season==2025).sum() }")
print(f"E[DK|implied] fit (slope pts of DK per implied pt, and r):")
for (s, pos), (b, a, r) in sorted(fits.items()):
    print(f"    {s} {pos}: slope={b:+.2f}  r={r:+.2f}")

print("\n--- STEP 1: validate the PROE proxy against real 2025 FantasyPoints PROE ---")
w25 = tw[tw.season == 2025]
c_tw, n_tw = corr(w25.proe_proxy, w25.proe)
# season-level
prox_season = w25.groupby("team").proe_proxy.mean()
real_season = w25.groupby("team").proe_season.first()
c_se, n_se = corr(prox_season.values, real_season.reindex(prox_season.index).values)
print(f"    proxy vs real PROE, team-week : r={c_tw:+.3f}  (n={n_tw})")
print(f"    proxy vs real PROE, team-season: r={c_se:+.3f}  (n={n_se})")
print("    (proxy is trustworthy for 2024 only if these are strongly positive)")

print("\n--- STEP 2: 2025 conversion, REAL PROE, three timings vs PC_resid ---")
for lab, col in [("season   PROE", "proe_season"),
                 ("same-week PROE", "proe"),
                 ("trailing  PROE", "proe_trail")]:
    c, n = corr(w25[col], w25.PC_resid)
    hi, lo, sp, ns = tercile_split(w25, col, "PC_resid")
    print(f"    {lab}: r={c:+.3f} (n={n})   PC_resid  hi={hi:+.2f} lo={lo:+.2f} spread={sp:+.2f}")

print("\n--- STEP 3: cross-year replication, PROXY PROE (same-week + trailing) ---")
for s in [2024, 2025]:
    d = tw[tw.season == s]
    c, n = corr(d.proe_proxy, d.PC_resid)
    hi, lo, sp, _ = tercile_split(d, "proe_proxy", "PC_resid")
    ct, nt = corr(d.proe_proxy_trail, d.PC_resid)
    hit, lot, spt, _ = tercile_split(d, "proe_proxy_trail", "PC_resid")
    print(f"    {s} same-week proxy: r={c:+.3f} (n={n})  PC_resid hi={hi:+.2f} lo={lo:+.2f} spread={sp:+.2f}")
    print(f"    {s} trailing  proxy: r={ct:+.3f} (n={nt})  PC_resid hi={hit:+.2f} lo={lot:+.2f} spread={spt:+.2f}")

print("\n--- STEP 4: mirror check — does run-lean predict RB over-conversion? ---")
for s in [2024, 2025]:
    d = tw[tw.season == s]
    c, n = corr(d.proe_proxy, d.RB_resid)   # expect NEGATIVE: pass-lean -> RB under
    print(f"    {s} same-week proxy vs RB_resid: r={c:+.3f} (n={n})  (expect negative)")

# persist the assembled panel for downstream wiring / re-checks
out = tw[["team","season","week","implied","spread","dk_PC","dk_RB","dk_QB",
          "PC_resid","RB_resid","pass_rate","proe_proxy","proe_proxy_trail",
          "proe","proe_trail","proe_season"]].copy()
out.to_csv("data/fantasypoints/proe_conversion_panel.csv", index=False)
print("\nwrote data/fantasypoints/proe_conversion_panel.csv "
      f"({len(out)} team-weeks, 2024+2025)")
