#!/usr/bin/env python3
"""
dfs_scenarios.py  --  DraftKings DFS 2026 ceiling engine  (SOURCE-FUSION rebuild)
================================================================================

PHILOSOPHY  (this is the whole point -- read it)
------------------------------------------------
The previous engine MULTIPLIED every signal (Vegas x coverage x depth x run x
pressure) into ONE effective mean and produced a single P(ceiling). That is the
WRONG mental model: it pretends the signals are one machine and hides where they
disagree. A high Vegas line silently cancelled cool efficiency; a great matchup
papered over thin volume. You could never see *why* two players with the same
number were nothing alike.

This rebuild is a SOURCE-FUSION board, exactly like fusion.py. Each DATA SOURCE is
its OWN independent model. Each source looks ONLY at its own family of features and
emits its OWN within-POSITION ceiling read on 0-100. We then FUSE the reads -- we
display every source side by side, a consensus (mean of the available reads), a
divergence (std), and a profile string naming which sources drive vs diverge. We
NEVER multiply one source into another. Nothing here is fit or trained: every read
is a transparent within-position rank percentile over the players who actually have
that source's data.

  Five independent source-models (each a within-position 0-100 percentile):

    1. ENVIRONMENT (Vegas)   vegas_w15/16/17_imp / _total / _spread.
                             Higher implied team total => higher ceiling. Emits a
                             read PER playoff week (env_w15/16/17) AND a season-avg
                             read (environment). Pure market, no on-field data.
    2. OPPORTUNITY / VOLUME  WR/TE: tgt_share, snap_share_est (route-participation),
                                    route_tprr, man_route_sh (routes).
                             RB:    carry_share, snap_share_est (touch-opportunity),
                                    rb_rec_ypg, opportunity=(car_pg+tgt_pg) vs tm_plays.
                             QB:    tm_pass_att, qb_rush_ypg.
    3. EFFICIENCY            WR/TE: REAL SIS sis_epa_per_tgt + rec_epa_per_tgt_man
                                    (vs MAN), route_yprr, rec_epa_route, rec_yacoe,
                                    rec_separation, fd_rr, adot_adj_ypt.
                             RB:    REAL SIS sis_pe_play + sis_epa, rush efficiency
                                    (epa_real/epa_proxy), zone_succ / gap_succ.
                             QB:    REAL SIS sis_pe_play + sis_epa, qb EPA (epa_real),
                                    cpoe, qb_anya.
    4. MATCHUP               opp coverage opp_w15_man_rate x player rec_man_zone_delta
                             (REAL SIS man/zone EPA split: man-beater into man-heavy D =
                             boost, zone-beater into zone-heavy D = boost), opp_pass_def_tier /
                             team_run_def_tier, ol_pass_winrate / ol_run_winrate,
                             and pressure faced (sack_pct25).
    5. ROLE / EXPLOSIVENESS  ALL:   REAL SIS sis_boom (Boom%, up) + sis_bust (Bust%,
                                    inverted -> down).
                             WR/TE: + deep_route_sh + adot25.
                             RB:    + outside_run_sh + explosiveness proxy.
                             QB:    + deep_ball_sh + qb_rush_ypg.

  FUSION (display, never collapse): per player we output every source read, a
  `ceiling_consensus` (mean of the available source reads), a `ceiling_divergence`
  (std of them), and a plain-English `profile` ("Vegas+volume elite, efficiency
  cool" / "all five agree"). A source with NO usable data for a player ABSTAINS
  (None) -- it is excluded from that source's coverage count and from the player's
  consensus/divergence, so missing data never drags a player to the middle.

  We ALSO keep a concrete real-Vegas-anchored P(ceiling) per playoff week (p_w15/
  p_w16/p_w17) from the original lognormal(mean = proj_pg x env_mult(week), cv).
  That is the literal tournament-week probability; the FIVE source reads are the
  headline.

Note on feature names: a few names in the original spec are not in features.json;
this engine uses the closest real columns present in the 107-col store and records
the substitutions in meta.notes (qb cpoe <- cpoe, qb epa/db <- qb_anya & epa_real,
qb pressure <- sack_pct25, rb rush epa <- epa_real/epa_proxy, rb explosiveness <-
outside_run_sh + epa). Sources with no real data abstain rather than guess.

INPUTS  (READ-ONLY)
-------------------
  features.json                    enriched feature store {meta, players:[...]} (371)
  pipeline/team_volume_model.json  OPTIONAL: powers an env sanity note only

OUTPUTS  (written ONLY by this script -- overwrite)
---------------------------------------------------
  dfs_scenarios.json
  dfs_scenarios.csv
"""

import json
import math
import os

import numpy as np
import pandas as pd

import core  # shared: fn(), norm_team(), safe_json_dump()

# ------------------------------------------------------------------ paths
HERE = os.path.dirname(os.path.abspath(__file__))


def P(*parts):
    return os.path.join(HERE, *parts)


FEATURES = P("features.json")
VOL_MODEL = P("pipeline", "team_volume_model.json")
OUT_CSV = P("dfs_scenarios.csv")
OUT_JSON = P("dfs_scenarios.json")

WEEKS = ["w15", "w16", "w17"]
CEILING_BAR = {"QB": 24.0, "RB": 20.0, "WR": 20.0, "TE": 14.0}
LG_IMPLIED = 22.5            # league-average team-implied points (spec anchor)
ENV_LO, ENV_HI = 0.80, 1.25  # env multiplier clip for the lognormal P(ceiling)


# ===================================================================
# 1.  LOGNORMAL DK DISTRIBUTION  (scipy-free) -- reused for P(ceiling)
# ===================================================================
def _phi(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def lognormal_params(mean, cv):
    sigma = math.sqrt(math.log(1.0 + cv * cv))
    mu = math.log(mean) - 0.5 * sigma * sigma
    return mu, sigma


def p_exceed(mean, cv, t):
    """P(DK > t) for lognormal(mean, cv). Robust to degenerate input."""
    if mean is None or mean <= 0 or cv is None or cv <= 0 or t <= 0:
        return None
    mu, sigma = lognormal_params(mean, cv)
    if sigma <= 0:
        return 1.0 if mean > t else 0.0
    z = (math.log(t) - mu) / sigma
    return 1.0 - _phi(z)


def env_mult(imp):
    """Real Vegas environment: team-implied points vs league ~22.5, clipped so one
    extreme line cannot dominate the lognormal."""
    if imp is None:
        return 1.0
    return clip(imp / LG_IMPLIED, ENV_LO, ENV_HI)


# ===================================================================
# helpers
# ===================================================================
def _num(v):
    """Coerce to float or None. features.json stores many numbers AS STRINGS
    ('37.7') and uses '' / None / 'None' for missing -- all become None."""
    if v is None:
        return None
    if isinstance(v, str):
        s = v.strip()
        if s == "" or s.lower() == "none" or s.lower() == "nan":
            return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def clip(x, lo, hi):
    return max(lo, min(hi, x))


def zscore_blend(parts):
    """Combine a list of (value, weight, invert) intermediate drivers into ONE raw
    source score, by standardizing each driver within the supplied population and
    taking the weighted mean of the available z-scores. Drivers with no value for a
    player are skipped; if a player has NO drivers at all, returns None (abstain).

    `parts` is a list of dicts: {"col": series_of_floats, "w": weight, "invert": bool}
    where series_of_floats is a pandas Series aligned to the player index. Returns a
    pandas Series of raw blended scores (NaN where the player abstains)."""
    # standardize each driver across players that have it
    zs = []
    ws = []
    for pr in parts:
        s = pr["col"].astype(float)
        mu = s.mean(skipna=True)
        sd = s.std(skipna=True, ddof=0)
        if sd is None or not np.isfinite(sd) or sd == 0:
            z = (s - mu)  # degenerate -> all ~0 contribution
            z = z * 0.0
        else:
            z = (s - mu) / sd
        if pr.get("invert"):
            z = -z
        zs.append(z * pr["w"])
        ws.append(pr["col"].notna().astype(float) * pr["w"])
    if not zs:
        return None
    num = pd.concat(zs, axis=1).sum(axis=1, skipna=True)
    den = pd.concat(ws, axis=1).sum(axis=1, skipna=True)
    out = num / den.where(den > 0)
    # abstain (NaN) where the player had none of this source's drivers
    any_present = pd.concat([p["col"].notna() for p in parts], axis=1).any(axis=1)
    out[~any_present] = np.nan
    return out


def within_pos_pctl(raw, pos):
    """Turn a raw source score into a within-POSITION percentile on 0-100 (higher =
    better). Players whose raw score is NaN ABSTAIN -> stay NaN (no neutral fill):
    a missing source must not become a fake 50. A position with one eligible player
    maps to 50 (no spread to rank). This is the single mechanism every source uses,
    so each source is an INDEPENDENT percentile -- a player can be 90 in one and 20
    in another."""
    out = pd.Series(np.nan, index=raw.index, dtype=float)
    df = pd.DataFrame({"raw": raw, "pos": pos})
    for _, idx in df.groupby("pos").groups.items():
        present = df.loc[idx, "raw"].dropna()
        if len(present) == 0:
            continue
        if len(present) == 1:
            out.loc[present.index] = 50.0
        else:
            r = present.rank(method="average")
            out.loc[present.index] = ((r - 0.5) / len(present) * 100.0).values
    return out.round(1)


# ===================================================================
# 2.  THE FIVE INDEPENDENT SOURCE MODELS
#     Each takes the player frame, builds its OWN raw driver score from ONLY its own
#     features, and returns a within-position percentile Series (NaN = abstain).
#     No source ever reads another source's output.
# ===================================================================

# defensive-tier strings -> "softness for the offense" (Poor D = softest = best).
TIER_SOFT = {"Elite": -1.0, "Good": -0.5, "Average": 0.0, "Below Avg": 0.5, "Poor": 1.0}


def col(df, name):
    """Return a float Series for a feature column (coercing string/'' -> NaN)."""
    if name not in df.columns:
        return pd.Series(np.nan, index=df.index, dtype=float)
    return df[name].map(_num).astype(float)


def tier_series(df, name):
    """Map a defensive-tier string column to the softness scale (NaN if absent)."""
    if name not in df.columns:
        return pd.Series(np.nan, index=df.index, dtype=float)
    return df[name].map(lambda v: TIER_SOFT.get(str(v).strip()) if v not in (None, "") else None).astype(float)


def src_environment(df):
    """SOURCE 1 -- ENVIRONMENT (Vegas). Pure market read: a blend of the three
    playoff-week implied team totals (primary) with a small nudge from the game
    totals and a favorable spread. Higher implied total => more team points to
    harvest => higher ceiling. Returns the SEASON-AVG percentile plus a per-week
    percentile for W15/W16/W17. No on-field data touches this source."""
    imp = pd.concat([col(df, f"vegas_{w}_imp") for w in WEEKS], axis=1)
    tot = pd.concat([col(df, f"vegas_{w}_total") for w in WEEKS], axis=1)
    spr = pd.concat([col(df, f"vegas_{w}_spread") for w in WEEKS], axis=1)
    imp_avg = imp.mean(axis=1, skipna=True)
    tot_avg = tot.mean(axis=1, skipna=True)
    spr_avg = spr.mean(axis=1, skipna=True)
    raw = zscore_blend([
        {"col": imp_avg, "w": 0.70},                 # implied team total = the driver
        {"col": tot_avg, "w": 0.20},                 # game total (shootout context)
        {"col": spr_avg, "w": 0.10, "invert": True},  # favored (negative spread) helps
    ])
    season = within_pos_pctl(raw, df["pos"])
    perweek = {}
    for w in WEEKS:
        rw = zscore_blend([
            {"col": col(df, f"vegas_{w}_imp"), "w": 0.70},
            {"col": col(df, f"vegas_{w}_total"), "w": 0.20},
            {"col": col(df, f"vegas_{w}_spread"), "w": 0.10, "invert": True},
        ])
        perweek[w] = within_pos_pctl(rw, df["pos"])
    return season, perweek


def src_opportunity(df):
    """SOURCE 2 -- OPPORTUNITY / VOLUME. Position-specific share of the offense.
    WR/TE: target share + routes (route_tprr) + man-route share (full route tree).
    RB:    carry share + receiving volume + combined opportunity (car_pg+tgt_pg)
           relative to team plays (tm_plays).
    QB:    team pass attempts + designed rush volume (qb_rush_ypg)."""
    pos = df["pos"]
    raw = pd.Series(np.nan, index=df.index, dtype=float)

    wr = pos.isin(["WR", "TE"])
    raw_wr = zscore_blend([
        {"col": col(df, "tgt_share").where(wr), "w": 0.45},
        {"col": col(df, "snap_share_est").where(wr), "w": 0.25},  # NEW: route-participation snap estimate (opportunity on the field)
        {"col": col(df, "route_tprr").where(wr), "w": 0.20},
        {"col": col(df, "man_route_sh").where(wr), "w": 0.10},
    ])
    raw[wr] = raw_wr[wr]

    rb = pos == "RB"
    combined_opp = (col(df, "car_pg") + col(df, "tgt_pg")) / col(df, "tm_plays")
    raw_rb = zscore_blend([
        {"col": col(df, "carry_share").where(rb), "w": 0.35},
        {"col": combined_opp.where(rb), "w": 0.25},        # snaps of work per team play
        {"col": col(df, "snap_share_est").where(rb), "w": 0.20},  # NEW: touch-opportunity snap estimate
        {"col": col(df, "rb_rec_ypg").where(rb), "w": 0.20},
    ])
    raw[rb] = raw_rb[rb]

    qb = pos == "QB"
    raw_qb = zscore_blend([
        {"col": col(df, "tm_pass_att").where(qb), "w": 0.60},
        {"col": col(df, "qb_rush_ypg").where(qb), "w": 0.40},  # rush volume = extra ceiling work
    ])
    raw[qb] = raw_qb[qb]

    return within_pos_pctl(raw, pos)


def src_efficiency(df):
    """SOURCE 3 -- EFFICIENCY. How much a player does PER opportunity (orthogonal to
    volume on purpose).
    WR/TE: route_yprr, rec_epa_route, rec_yacoe, rec_separation, fd_rr, adot_adj_ypt.
    RB:    rush EPA (epa_real, with epa_proxy backfill) + zone_succ / gap_succ.
    QB:    qb EPA (epa_real), cpoe, qb_anya."""
    pos = df["pos"]
    raw = pd.Series(np.nan, index=df.index, dtype=float)

    wr = pos.isin(["WR", "TE"])
    raw_wr = zscore_blend([
        {"col": col(df, "sis_epa_per_tgt").where(wr), "w": 0.22},      # NEW: REAL SIS EPA per target (value/efficiency)
        {"col": col(df, "rec_epa_per_tgt_man").where(wr), "w": 0.12},  # NEW: REAL EPA/tgt vs MAN coverage (man-beater value)
        {"col": col(df, "route_yprr").where(wr), "w": 0.20},
        {"col": col(df, "rec_epa_route").where(wr), "w": 0.16},
        {"col": col(df, "rec_yacoe").where(wr), "w": 0.12},
        {"col": col(df, "rec_separation").where(wr), "w": 0.08},
        {"col": col(df, "fd_rr").where(wr), "w": 0.06},
        {"col": col(df, "adot_adj_ypt").where(wr), "w": 0.04},
    ])
    raw[wr] = raw_wr[wr]

    rb = pos == "RB"
    # rush EPA: prefer real, backfill with proxy where real is missing
    rush_epa = col(df, "epa_real")
    rush_epa = rush_epa.fillna(col(df, "epa_proxy"))
    succ = pd.concat([col(df, "zone_succ"), col(df, "gap_succ")], axis=1).mean(axis=1, skipna=True)
    raw_rb = zscore_blend([
        {"col": col(df, "sis_pe_play").where(rb), "w": 0.32},  # NEW: REAL SIS points-earned per play (value/efficiency)
        {"col": col(df, "sis_epa").where(rb), "w": 0.18},      # NEW: REAL SIS total EPA (value)
        {"col": rush_epa.where(rb), "w": 0.30},
        {"col": succ.where(rb), "w": 0.20},
    ])
    raw[rb] = raw_rb[rb]

    qb = pos == "QB"
    raw_qb = zscore_blend([
        {"col": col(df, "sis_pe_play").where(qb), "w": 0.28},  # NEW: REAL SIS points-earned per play (value/efficiency)
        {"col": col(df, "sis_epa").where(qb), "w": 0.12},      # NEW: REAL SIS total EPA (value)
        {"col": col(df, "epa_real").where(qb), "w": 0.25},     # qb epa/dropback (real)
        {"col": col(df, "cpoe").where(qb), "w": 0.20},         # completion % over expected
        {"col": col(df, "qb_anya").where(qb), "w": 0.15},      # adjusted net yds/attempt
    ])
    raw[qb] = raw_qb[qb]

    return within_pos_pctl(raw, pos)


def src_matchup(df):
    """SOURCE 4 -- MATCHUP. The defensive context the player runs into.
    Core (coverage-scheme-aware, not just game script): opp_w15_man_rate x
    rec_man_zone_delta -- the player's REAL SIS man/zone EPA profile interacted with the
    opponent's coverage tendency. A man-beater (delta>0) into a man-heavy D = boost; a
    man-beater into a zone-heavy D = slight fade; a zone-beater (delta<0) into a
    zone-heavy D = boost. ABSTAINS if rec_man_zone_delta or opp_w15_man_rate is missing.
    Plus opp pass-def tier (QB/WR/TE) or team run-def tier (RB), the relevant O-line win
    rate, and pressure faced (sack_pct25, QB).

    NEW (SIS team defensive profiles, each a SEPARATE within-population contribution that
    ABSTAINS when its opponent value is missing -- never filled):
      WR/TE: opp_pass_cov_pctl  -- opponent coverage-unit strength (Points Saved league
             pctl); strong coverage FADES receivers, so it is NEGATIVE-weighted (invert).
      QB:    opp_pass_rush_pctl -- opponent pass-rush strength; strong rush kills EPA, so
             it is NEGATIVE-weighted (invert); PLUS a qb_man_zone_delta x opp man-lean
             interaction (same shape as the receiver coverage-scheme term).
      RB:    opp_run_def_pctl   -- opponent run-defense strength; strong run-D FADES RBs,
             so NEGATIVE-weighted (invert); PLUS a rb_zone_gap_delta x own-team zone-run
             share (zone_run_sh) scheme-fit interaction (zone-fit RB on a zone-heavy
             offense = boost). Still ONE within-position percentile."""
    pos = df["pos"]
    raw = pd.Series(np.nan, index=df.index, dtype=float)

    man_rate = col(df, "opp_w15_man_rate")
    LG_MAN = 17.0
    man_lean = ((man_rate - LG_MAN) / 5.0).clip(-2, 2)   # +ve = man-heavy opponent
    # REAL SIS coverage-scheme profile: rec_man_zone_delta = EPA/tgt vs MAN - vs ZONE.
    # +ve = man-beater (feasts vs man, e.g. Pickens +0.66); -ve = zone-beater (feasts
    # vs zone, e.g. Bowers -0.54). Interacting it with the OPPONENT's man/zone lean is
    # the "coverage scheme, not just game script" matchup read: a man-beater into a
    # man-heavy D = boost; a man-beater into a zone-heavy D = slight fade; symmetric for
    # zone-beaters (-delta x -lean = boost vs zone-heavy D). ABSTAINS (NaN) whenever the
    # player's rec_man_zone_delta OR the opponent tendency is missing -- never filled.
    mzd = col(df, "rec_man_zone_delta")                    # +ve = man-beater, -ve = zone-beater
    cov_fit = man_lean * mzd                               # aligned strength of the coverage-scheme matchup
    # QB coverage-scheme fit: REAL SIS qb_man_zone_delta (per-att EPA vs MAN - vs ZONE,
    # +ve = man-beater QB) interacted with the SAME opponent man/zone lean. Computed as
    # ONE interaction term BEFORE percentiling (the only multiply allowed); abstains if
    # qb_man_zone_delta OR the opponent lean is missing.
    qb_mzd = col(df, "qb_man_zone_delta")
    qb_cov_fit = man_lean * qb_mzd
    # RB scheme fit: REAL SIS rb_zone_gap_delta (EPA/A on zone runs - gap runs, +ve =
    # better on zone) interacted with the RB's OWN-team zone-run share zone_run_sh (a
    # zone-fit back on a zone-heavy offense = boost). ONE interaction term computed BEFORE
    # percentiling; abstains if rb_zone_gap_delta OR zone_run_sh is missing.
    rb_zgd = col(df, "rb_zone_gap_delta")
    zsh_lean = ((col(df, "zone_run_sh") - 50.0) / 25.0).clip(-2, 2)   # +ve = zone-heavy own scheme
    rb_scheme_fit = zsh_lean * rb_zgd
    # opponent team-defense unit strengths (SIS Points Saved league pctls). Higher = a
    # STRONGER opposing unit = HARDER matchup, so each is INVERTED in the blend (a strong
    # unit fades the offensive player). NaN (no opponent mapping) -> the driver abstains.
    opp_cov  = col(df, "opp_pass_cov_pctl")
    opp_rush = col(df, "opp_pass_rush_pctl")
    opp_run  = col(df, "opp_run_def_pctl")

    wr = pos.isin(["WR", "TE"])
    raw_wr = zscore_blend([
        {"col": cov_fit.where(wr), "w": 0.40},             # coverage-scheme fit (rec_man_zone_delta x opp man/zone lean) -- the headline
        {"col": opp_cov.where(wr), "w": 0.25, "invert": True},  # NEW: opp coverage-unit strength (SIS Points Saved pctl) -- strong coverage FADES receivers
        {"col": tier_series(df, "opp_pass_def_tier").where(wr), "w": 0.20},  # softer pass D = better
        {"col": col(df, "ol_pass_winrate").where(wr), "w": 0.15},            # clean pocket = more deep shots
    ])
    raw[wr] = raw_wr[wr]

    rb = pos == "RB"
    raw_rb = zscore_blend([
        {"col": rb_scheme_fit.where(rb), "w": 0.30},        # NEW: zone/gap scheme fit (rb_zone_gap_delta x own zone_run_sh) -- zone-fit RB on zone-heavy O = boost
        {"col": opp_run.where(rb), "w": 0.25, "invert": True},  # NEW: opp run-defense strength (SIS Points Saved pctl) -- strong run-D FADES RBs
        {"col": tier_series(df, "team_run_def_tier").where(rb), "w": 0.25},  # softer run D
        {"col": col(df, "ol_run_winrate").where(rb), "w": 0.20},
    ])
    raw[rb] = raw_rb[rb]

    qb = pos == "QB"
    raw_qb = zscore_blend([
        {"col": opp_rush.where(qb), "w": 0.30, "invert": True},  # NEW: opp pass-rush strength (SIS Points Saved pctl) -- strong rush kills QB EPA, FADE
        {"col": qb_cov_fit.where(qb), "w": 0.15},                # NEW: QB coverage-scheme fit (qb_man_zone_delta x opp man/zone lean)
        {"col": tier_series(df, "opp_pass_def_tier").where(qb), "w": 0.30},
        {"col": col(df, "ol_pass_winrate").where(qb), "w": 0.15},
        {"col": col(df, "sack_pct25").where(qb), "w": 0.10, "invert": True},  # low pressure faced = better
    ])
    raw[qb] = raw_qb[qb]

    return within_pos_pctl(raw, pos)


def src_role(df):
    """SOURCE 5 -- ROLE / EXPLOSIVENESS. The shape of usage that creates the long
    tail (the boom-week alpha).
    WR/TE: deep_route_sh + adot25 (downfield role = the ceiling outcomes).
    RB:    outside_run_sh + explosiveness proxy (epa upside).
    QB:    deep_ball_sh + qb_rush_ypg (gunslinger + legs = dual ceiling paths)."""
    pos = df["pos"]
    raw = pd.Series(np.nan, index=df.index, dtype=float)

    wr = pos.isin(["WR", "TE"])
    raw_wr = zscore_blend([
        {"col": col(df, "sis_boom").where(wr), "w": 0.35},               # NEW: SIS Boom% (ceiling-game propensity, up)
        {"col": col(df, "sis_bust").where(wr), "w": 0.15, "invert": True},  # NEW: SIS Bust% (floor risk, down)
        {"col": col(df, "deep_route_sh").where(wr), "w": 0.28},
        {"col": col(df, "adot25").where(wr), "w": 0.22},
    ])
    raw[wr] = raw_wr[wr]

    rb = pos == "RB"
    expl = col(df, "epa_real").fillna(col(df, "epa_proxy"))   # explosiveness proxy
    raw_rb = zscore_blend([
        {"col": col(df, "sis_boom").where(rb), "w": 0.35},               # NEW: SIS Boom% (ceiling-game propensity, up)
        {"col": col(df, "sis_bust").where(rb), "w": 0.15, "invert": True},  # NEW: SIS Bust% (floor risk, down)
        {"col": col(df, "outside_run_sh").where(rb), "w": 0.28},   # perimeter = breakaway lanes
        {"col": expl.where(rb), "w": 0.22},
    ])
    raw[rb] = raw_rb[rb]

    qb = pos == "QB"
    raw_qb = zscore_blend([
        {"col": col(df, "sis_boom").where(qb), "w": 0.35},               # NEW: SIS Boom% (ceiling-game propensity, up)
        {"col": col(df, "sis_bust").where(qb), "w": 0.15, "invert": True},  # NEW: SIS Bust% (floor risk, down)
        {"col": col(df, "deep_ball_sh").where(qb), "w": 0.25},
        {"col": col(df, "qb_rush_ypg").where(qb), "w": 0.25},
    ])
    raw[qb] = raw_qb[qb]

    return within_pos_pctl(raw, pos)


# ===================================================================
# 3.  PROFILE STRING  (names which sources DRIVE vs DIVERGE -- never a number)
# ===================================================================
SRC_LABEL = {"environment": "Vegas", "opportunity": "volume", "efficiency": "efficiency",
             "matchup": "matchup", "role": "role"}
HOT, COLD = 70.0, 35.0


def make_profile(reads):
    """reads: dict source->read (None where abstained). Produce a plain-English
    string naming the hot (>=70) and cool (<=35) sources and flagging agreement vs
    divergence. Agreement is judged on the SPREAD of the available reads (robust to a
    single outlier via the std gate), so the named example 'all five agree' fires for
    any number of available sources >= 3 that cluster, while a player carried by one
    or two sources gets those sources named explicitly."""
    avail = {k: v for k, v in reads.items() if v is not None}
    if not avail:
        return "no source data"
    n = len(avail)
    vals = list(avail.values())
    spread = (max(vals) - min(vals)) if n > 1 else 0.0
    sd = float(np.std(vals)) if n > 1 else 0.0
    hot = [SRC_LABEL[k] for k, v in avail.items() if v >= HOT]
    cold = [SRC_LABEL[k] for k, v in avail.items() if v <= COLD]
    word = "all %d" % n if n >= 4 else ("all three" if n == 3 else None)

    # all-agree cases: tight cluster (small spread OR small std) across >= 3 sources
    if word and (spread <= 20 or sd <= 8):
        if min(vals) >= 62:
            return "%s sources agree: elite across the board" % word
        if max(vals) <= 42:
            return "%s sources agree: weak across the board" % word
        return "%s sources agree: middling" % word

    parts = []
    if hot:
        parts.append(("%s elite" % "+".join(hot)) if len(hot) > 1 else ("%s elite" % hot[0]))
    if cold:
        parts.append(("%s cool" % "+".join(cold)) if len(cold) > 1 else ("%s cool" % cold[0]))
    if not parts:
        return "mixed reads, no strong driver"
    tail = " (sources DIVERGE)" if sd >= 22 else ""
    return ", ".join(parts) + tail


# ===================================================================
# 4.  MAIN
# ===================================================================
def main():
    with open(FEATURES, "r", encoding="utf-8") as f:
        feats = json.load(f)
    meta_in = feats.get("meta", {})
    players = feats["players"]
    df = pd.DataFrame(players)
    df["pos"] = df["pos"].map(lambda p: str(p).upper() if p else None)
    df["team"] = df["team"].map(core.norm_team)
    df = df[df["pos"].isin(["QB", "RB", "WR", "TE"])].reset_index(drop=True)

    # ---- run the five independent source models -------------------
    env_season, env_week = src_environment(df)
    opp = src_opportunity(df)
    eff = src_efficiency(df)
    mat = src_matchup(df)
    role = src_role(df)

    SRC = {"environment": env_season, "opportunity": opp, "efficiency": eff,
           "matchup": mat, "role": role}

    # ---- FUSE: consensus + divergence over ONLY the available reads
    read_mat = pd.DataFrame(SRC)               # one column per source, NaN = abstain
    consensus = read_mat.mean(axis=1, skipna=True).round(1)
    divergence = read_mat.std(axis=1, ddof=0, skipna=True).round(1).fillna(0.0)
    n_sources = read_mat.notna().sum(axis=1)

    # ---- concrete real-Vegas-anchored P(ceiling) per playoff week --
    proj = col(df, "proj_pg")
    cv = col(df, "cv")
    pw = {}
    for w in WEEKS:
        imp = col(df, f"vegas_{w}_imp")
        bar = df["pos"].map(CEILING_BAR)
        pw[w] = [
            p_exceed(pr * env_mult(im) if (pr is not None and im is not None)
                     else (pr if pr is not None else None), c, b)
            if (pr is not None and c is not None) else None
            for pr, c, im, b in zip(proj, cv, imp, bar)
        ]

    # ---- assemble player records ----------------------------------
    def f1(x):
        return None if (x is None or (isinstance(x, float) and not np.isfinite(x))) else round(float(x), 1)

    out_players = []
    for i in range(len(df)):
        r = df.iloc[i]
        reads = {k: f1(SRC[k].iloc[i]) for k in SRC}
        reads_week = {w: f1(env_week[w].iloc[i]) for w in WEEKS}
        profile = make_profile(reads)
        cons = f1(consensus.iloc[i])
        dvg = f1(divergence.iloc[i])

        def rv(name):  # raw driver value passthrough
            return _num(r.get(name))

        drivers = {
            # environment
            "vegas_w15_imp": rv("vegas_w15_imp"), "vegas_w16_imp": rv("vegas_w16_imp"),
            "vegas_w17_imp": rv("vegas_w17_imp"),
            "vegas_w15_total": rv("vegas_w15_total"), "vegas_w15_spread": rv("vegas_w15_spread"),
            # opportunity
            "tgt_share": rv("tgt_share"), "route_tprr": rv("route_tprr"),
            "man_route_sh": rv("man_route_sh"), "carry_share": rv("carry_share"),
            "rb_rec_ypg": rv("rb_rec_ypg"), "car_pg": rv("car_pg"), "tgt_pg": rv("tgt_pg"),
            "tm_plays": rv("tm_plays"), "tm_pass_att": rv("tm_pass_att"),
            "qb_rush_ypg": rv("qb_rush_ypg"),
            "snap_share_est": rv("snap_share_est"),  # NEW opportunity driver
            "snap_est_basis": (r.get("snap_est_basis") or None),
            # efficiency
            "route_yprr": rv("route_yprr"), "rec_epa_route": rv("rec_epa_route"),
            "rec_yacoe": rv("rec_yacoe"), "rec_separation": rv("rec_separation"),
            "fd_rr": rv("fd_rr"), "adot_adj_ypt": rv("adot_adj_ypt"),
            "epa_real": rv("epa_real"), "epa_proxy": rv("epa_proxy"),
            "zone_succ": rv("zone_succ"), "gap_succ": rv("gap_succ"),
            "cpoe": rv("cpoe"), "qb_anya": rv("qb_anya"),
            "sis_epa": rv("sis_epa"), "sis_epa_per_tgt": rv("sis_epa_per_tgt"),  # NEW efficiency drivers (REAL SIS)
            "sis_pe_play": rv("sis_pe_play"), "rec_epa_per_tgt_man": rv("rec_epa_per_tgt_man"),
            # matchup
            "opp_w15_man_rate": rv("opp_w15_man_rate"), "man_zone_delta": rv("man_zone_delta"),
            "rec_man_zone_delta": rv("rec_man_zone_delta"),  # REAL SIS man/zone EPA delta (+ man-beater / - zone-beater)
            "rec_epa_per_tgt_zone": rv("rec_epa_per_tgt_zone"),  # REAL SIS EPA/tgt vs ZONE coverage
            "qb_man_zone_delta": rv("qb_man_zone_delta"),    # NEW REAL SIS QB per-att EPA vs MAN - vs ZONE (+ man-beater)
            "rb_zone_gap_delta": rv("rb_zone_gap_delta"),    # NEW REAL SIS RB EPA/A zone - gap (+ zone-fit)
            "zone_run_sh": rv("zone_run_sh"),                # own-team zone-run share (RB scheme-fit interaction input)
            "opp_pass_cov_pctl": rv("opp_pass_cov_pctl"),    # NEW opp coverage-unit strength (SIS Points Saved league pctl)
            "opp_pass_rush_pctl": rv("opp_pass_rush_pctl"),  # NEW opp pass-rush strength (SIS Points Saved league pctl)
            "opp_run_def_pctl": rv("opp_run_def_pctl"),      # NEW opp run-defense strength (SIS Points Saved league pctl)
            "opp_pass_def_tier": (r.get("opp_pass_def_tier") or None),
            "team_run_def_tier": (r.get("team_run_def_tier") or None),
            "ol_pass_winrate": rv("ol_pass_winrate"), "ol_run_winrate": rv("ol_run_winrate"),
            "sack_pct25": rv("sack_pct25"),
            # role / explosiveness
            "deep_route_sh": rv("deep_route_sh"), "adot25": rv("adot25"),
            "outside_run_sh": rv("outside_run_sh"), "deep_ball_sh": rv("deep_ball_sh"),
            "sis_boom": rv("sis_boom"), "sis_bust": rv("sis_bust"),  # NEW role/ceiling drivers (SIS Boom%/Bust%)
            # baseline projection used for P(ceiling)
            "proj_pg": rv("proj_pg"), "cv": rv("cv"),
        }
        drivers = {k: v for k, v in drivers.items() if v is not None}

        out_players.append({
            "name": r["name"], "pos": r["pos"], "team": r["team"],
            "sources": {
                "environment": reads["environment"],
                "environment_w15": reads_week["w15"],
                "environment_w16": reads_week["w16"],
                "environment_w17": reads_week["w17"],
                "opportunity": reads["opportunity"],
                "efficiency": reads["efficiency"],
                "matchup": reads["matchup"],
                "role": reads["role"],
            },
            "ceiling_consensus": cons,
            "ceiling_divergence": dvg,
            "n_sources": int(n_sources.iloc[i]),
            "p_w15": (round(pw["w15"][i], 4) if pw["w15"][i] is not None else None),
            "p_w16": (round(pw["w16"][i], 4) if pw["w16"][i] is not None else None),
            "p_w17": (round(pw["w17"][i], 4) if pw["w17"][i] is not None else None),
            "profile": profile,
            "drivers": drivers,
        })

    # ---- coverage per source --------------------------------------
    coverage = {k: {"n": int(SRC[k].notna().sum()), "pct": round(100.0 * SRC[k].notna().sum() / len(df), 1)}
                for k in SRC}
    coverage["environment_perweek"] = {w: {"n": int(env_week[w].notna().sum()),
                                           "pct": round(100.0 * env_week[w].notna().sum() / len(df), 1)} for w in WEEKS}
    coverage["p_ceiling"] = {w: {"n": int(sum(1 for x in pw[w] if x is not None)),
                                 "pct": round(100.0 * sum(1 for x in pw[w] if x is not None) / len(df), 1)} for w in WEEKS}

    meta = {
        "philosophy": (
            "SOURCE-FUSION, not a single refit. Each of the five DATA SOURCES is its "
            "OWN independent model and emits its OWN within-position ceiling read on "
            "0-100. The reads are FUSED for display -- every source shown side by side "
            "with a consensus (mean of available reads), a divergence (std), and a "
            "profile naming what drives vs diverges. No source is ever multiplied into "
            "another; nothing is fit or trained. A source with no usable data ABSTAINS "
            "(null) and is excluded from coverage and from the player's consensus/"
            "divergence, so missing data never drags a player to the middle."
        ),
        "sources": [
            {"key": "environment", "name": "Environment (Vegas)",
             "drivers": "vegas_w15/16/17_imp (primary), _total, _spread; season-avg + per-week reads",
             "logic": "higher implied team total => higher ceiling; pure market, no on-field data"},
            {"key": "opportunity", "name": "Opportunity / Volume",
             "drivers": "WR/TE: tgt_share, snap_share_est (route-participation), route_tprr, man_route_sh | RB: carry_share, (car_pg+tgt_pg)/tm_plays, snap_share_est (touch-opportunity), rb_rec_ypg | QB: tm_pass_att, qb_rush_ypg",
             "logic": "share of the offense the player commands (now incl. SIS route-participation / touch-opportunity snap estimate)"},
            {"key": "efficiency", "name": "Efficiency",
             "drivers": "WR/TE: sis_epa_per_tgt + rec_epa_per_tgt_man (REAL SIS value, vs-man), route_yprr, rec_epa_route, rec_yacoe, rec_separation, fd_rr, adot_adj_ypt | RB: sis_pe_play + sis_epa (REAL SIS value), rush EPA (epa_real/epa_proxy), zone_succ/gap_succ | QB: sis_pe_play + sis_epa (REAL SIS value), epa_real, cpoe, qb_anya",
             "logic": "production per opportunity, orthogonal to volume; now anchored on REAL SIS DataHub EPA/value (incl. WR/TE EPA per target vs MAN coverage)"},
            {"key": "matchup", "name": "Matchup",
             "drivers": "WR/TE: opp_w15_man_rate x rec_man_zone_delta (coverage-scheme fit) + opp_pass_cov_pctl (opp coverage Points-Saved strength, FADE) + opp_pass_def_tier + ol_pass_winrate | RB: rb_zone_gap_delta x own zone_run_sh (scheme fit) + opp_run_def_pctl (opp run-D strength, FADE) + team_run_def_tier + ol_run_winrate | QB: opp_pass_rush_pctl (opp pass-rush strength, FADE) + qb_man_zone_delta x opp man/zone lean + opp_pass_def_tier + ol_pass_winrate + sack_pct25 (pressure faced)",
             "logic": "defensive context incl. COVERAGE SCHEME + REAL SIS opponent team-defense unit strength (each a SEPARATE within-pos contribution: strong opp unit fades the player, never multiplied into another source); coverage/scheme interactions are computed BEFORE percentiling; any contribution abstains if its opponent/delta input is missing"},
            {"key": "role", "name": "Role / Explosiveness",
             "drivers": "ALL: sis_boom (SIS Boom%, up) + sis_bust (SIS Bust%, inverted/down) | WR/TE: + deep_route_sh + adot25 | RB: + outside_run_sh + explosiveness (epa) | QB: + deep_ball_sh + qb_rush_ypg",
             "logic": "usage shape that creates the long tail / boom weeks; now incl. REAL SIS ceiling-game (Boom%) propensity up and floor-game (Bust%) risk down"},
        ],
        "fusion": {
            "ceiling_consensus": "mean of the AVAILABLE source reads (display-only; reads are never collapsed into it)",
            "ceiling_divergence": "std of the available source reads (the leverage signal -- how much the sources disagree)",
            "profile": "plain-English string naming hot (>=70) and cool (<=35) sources and whether they agree/diverge",
            "p_w15/16/17": "concrete real-Vegas-anchored P(DK > position bar) from lognormal(mean=proj_pg x env_mult(week), cv); the five source reads are the headline",
        },
        "ceiling_bars": CEILING_BAR,
        "percentile_basis": "within position (QB/RB/WR/TE), rank-based midpoint, 0-100 higher=better",
        "coverage": coverage,
        "notes": (
            "INDEPENDENCE: each source is its own within-position percentile -- a player "
            "can be 90 in one source and 20 in another; reads are FUSED (shown side by "
            "side), never combined into one number. SUBSTITUTIONS (closest real columns "
            "in the 107-col store for spec names not present): qb cpoe <- cpoe; qb epa/db "
            "<- epa_real & qb_anya; qb pressure <- sack_pct25 (faced); rb rush epa <- "
            "epa_real with epa_proxy backfill; rb explosiveness <- outside_run_sh + epa "
            "(no rb_topspeed/ryoe_att in store); matchup tiers are strings (Poor..Elite) "
            "mapped to a softness scale. SIS DataHub signals folded in (2025): "
            "EFFICIENCY gained REAL sis_epa_per_tgt / sis_pe_play / sis_epa (+ WR/TE "
            "rec_epa_per_tgt_man vs MAN); ROLE gained sis_boom (ceiling propensity, up) "
            "and sis_bust (floor risk, inverted/down); OPPORTUNITY gained snap_share_est "
            "(route-participation / touch-opportunity); MATCHUP's coverage-scheme term now "
            "uses REAL SIS rec_man_zone_delta (EPA/tgt vs MAN - vs ZONE) interacted with "
            "opp_w15_man_rate (man-beater into man-heavy D = boost, zone-beater into "
            "zone-heavy D = boost), abstaining if either is null. Each remains an independent "
            "within-position percentile; SIS columns with no value ABSTAIN (never 50/0). "
            "n=%d players (QB/RB/WR/TE)." % len(df)
        ),
        "source_feature_store": (meta_in.get("source") if isinstance(meta_in, dict) else None) or "features.json",
    }

    out = {"meta": meta, "players": out_players}
    core.safe_json_dump(out, OUT_JSON, indent=2)

    # ---- CSV --------------------------------------------------------
    rows = []
    for p in out_players:
        s = p["sources"]
        rows.append({
            "name": p["name"], "pos": p["pos"], "team": p["team"],
            "env": s["environment"], "opp": s["opportunity"], "eff": s["efficiency"],
            "matchup": s["matchup"], "role": s["role"],
            "consensus": p["ceiling_consensus"], "divergence": p["ceiling_divergence"],
            "p_w15": p["p_w15"], "p_w16": p["p_w16"], "p_w17": p["p_w17"],
            "profile": p["profile"],
        })
    cols = ["name", "pos", "team", "env", "opp", "eff", "matchup", "role",
            "consensus", "divergence", "p_w15", "p_w16", "p_w17", "profile"]
    pd.DataFrame(rows)[cols].to_csv(OUT_CSV, index=False)

    return out, df, SRC, env_week, pw, coverage


# ===================================================================
# 5.  VERIFICATION  (run + print)
# ===================================================================
def _fmt(v, nd=1):
    return ("%.*f" % (nd, v)) if isinstance(v, (int, float)) else "  -- "


def verify(out, df, SRC, env_week, pw, coverage):
    P = {p["name"]: p for p in out["players"]}
    print("=" * 78)
    print("DFS SOURCE-FUSION CEILING ENGINE  --  VERIFICATION")
    print("=" * 78)
    print("\nPLAYERS: %d  (QB/RB/WR/TE)   SOURCES: 5 independent within-position models" % len(out["players"]))

    print("\nCOVERAGE PER SOURCE (players with usable data for that source):")
    for k in ["environment", "opportunity", "efficiency", "matchup", "role"]:
        c = coverage[k]
        print("   %-13s  %4d / %d   (%.1f%%)" % (k, c["n"], len(out["players"]), c["pct"]))
    pwk = coverage["environment_perweek"]
    print("   environment per-week:  " + "  ".join("%s %d (%.0f%%)" % (w.upper(), pwk[w]["n"], pwk[w]["pct"]) for w in WEEKS))
    pcc = coverage["p_ceiling"]
    print("   P(ceiling) per-week:   " + "  ".join("%s %d (%.0f%%)" % (w.upper(), pcc[w]["n"], pcc[w]["pct"]) for w in WEEKS))

    def show(name):
        p = P.get(name)
        if not p:
            print("\n  [%s not found]" % name)
            return
        s = p["sources"]
        print("\n" + "-" * 78)
        print("%s  (%s, %s)" % (p["name"], p["pos"], p["team"]))
        print("  SOURCE READS (each an independent within-%s percentile, 0-100):" % p["pos"])
        print("     environment %s   |  W15 %s  W16 %s  W17 %s"
              % (_fmt(s["environment"]), _fmt(s["environment_w15"]), _fmt(s["environment_w16"]), _fmt(s["environment_w17"])))
        print("     opportunity %s   efficiency %s   matchup %s   role %s"
              % (_fmt(s["opportunity"]), _fmt(s["efficiency"]), _fmt(s["matchup"]), _fmt(s["role"])))
        print("  FUSION:  consensus %s   divergence %s   (n_sources=%d)"
              % (_fmt(p["ceiling_consensus"]), _fmt(p["ceiling_divergence"]), p["n_sources"]))
        print("  P(ceiling):  W15 %s  W16 %s  W17 %s"
              % (_fmt(p["p_w15"], 3) if p["p_w15"] is not None else "  -- ",
                 _fmt(p["p_w16"], 3) if p["p_w16"] is not None else "  -- ",
                 _fmt(p["p_w17"], 3) if p["p_w17"] is not None else "  -- "))
        print("  PROFILE: %s" % p["profile"])

    print("\n" + "=" * 78)
    print("SIX FULL SOURCE BREAKDOWNS")
    print("=" * 78)
    showcase = ["Puka Nacua", "Christian McCaffrey", "Lamar Jackson",
                "Josh Allen", "Jalen Hurts", "Saquon Barkley"]
    for nm in showcase:
        show(nm)

    # ----- assertions / archetype checks ----------------------------
    print("\n" + "=" * 78)
    print("ARCHETYPE CHECKS")
    print("=" * 78)

    def rng(p):
        v = [x for x in p["sources"].values() if x is not None and not isinstance(x, bool)]
        # only the 5 headline sources (exclude the per-week env duplicates) for spread
        core5 = [p["sources"][k] for k in ["environment", "opportunity", "efficiency", "matchup", "role"]
                 if p["sources"][k] is not None]
        return core5

    # 1) elite-across-sources -> high consensus, LOW divergence
    for nm in ["Puka Nacua", "Christian McCaffrey"]:
        p = P.get(nm)
        if p:
            print("  [elite/consistent] %-20s consensus=%s divergence=%s  -> %s"
                  % (nm, _fmt(p["ceiling_consensus"]), _fmt(p["ceiling_divergence"]),
                     "OK (high consensus, low divergence)" if (p["ceiling_consensus"] and p["ceiling_consensus"] >= 60 and p["ceiling_divergence"] is not None and p["ceiling_divergence"] <= 22) else "see reads"))

    # 2) highest-divergence players (Vegas-dependent but cool elsewhere show here)
    pol = sorted(out["players"], key=lambda x: (x["ceiling_divergence"] or 0), reverse=True)
    print("\n  [most divergent sources -> leverage/uncertainty]")
    for p in pol[:5]:
        s = p["sources"]
        print("     %-22s (%s) div=%s  env=%s opp=%s eff=%s mat=%s role=%s | %s"
              % (p["name"], p["pos"], _fmt(p["ceiling_divergence"]),
                 _fmt(s["environment"]), _fmt(s["opportunity"]), _fmt(s["efficiency"]),
                 _fmt(s["matchup"]), _fmt(s["role"]), p["profile"]))

    # 3) pure rushing QB -> role + opportunity high
    print("\n  [rushing QBs -> role + opportunity should run high]")
    qbs = [p for p in out["players"] if p["pos"] == "QB" and p["drivers"].get("qb_rush_ypg")]
    qbs = sorted(qbs, key=lambda x: x["drivers"].get("qb_rush_ypg", 0), reverse=True)[:4]
    for p in qbs:
        s = p["sources"]
        print("     %-20s qb_rush_ypg=%.1f  role=%s opportunity=%s  (eff=%s)"
              % (p["name"], p["drivers"]["qb_rush_ypg"], _fmt(s["role"]), _fmt(s["opportunity"]), _fmt(s["efficiency"])))

    # 4) prove independence: a player high in one source, low in another
    print("\n  [independence proof: sources are SEPARATE percentiles]")
    found = 0
    for p in out["players"]:
        core5 = {k: p["sources"][k] for k in ["environment", "opportunity", "efficiency", "matchup", "role"]
                 if p["sources"][k] is not None}
        if len(core5) >= 4:
            hi = max(core5.items(), key=lambda kv: kv[1])
            lo = min(core5.items(), key=lambda kv: kv[1])
            if hi[1] >= 85 and lo[1] <= 25:
                print("     %-22s (%s)  %s=%.0f  but  %s=%.0f   (90-in-one, 20-in-another)"
                      % (p["name"], p["pos"], hi[0], hi[1], lo[0], lo[1]))
                found += 1
                if found >= 4:
                    break
    if not found:
        print("     (no extreme split found in scope)")

    print("\n" + "=" * 78)
    print("CONFIRMATION: no source is multiplied into another. Each of the five reads "
          "is an\nindependent within-position percentile; they are FUSED (displayed "
          "side by side with\nconsensus + divergence), NOT combined into a single number.")
    print("=" * 78)


if __name__ == "__main__":
    out, df, SRC, env_week, pw, coverage = main()
    verify(out, df, SRC, env_week, pw, coverage)
    print("\nWROTE:\n  %s\n  %s" % (OUT_JSON, OUT_CSV))
