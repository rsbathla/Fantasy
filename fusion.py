#!/usr/bin/env python3
"""
fusion.py - MODEL FUSION for DraftKings NFL Best Ball / DFS 2026.

PHILOSOPHY (unchanged): FUSION, not overfitting. We keep what EACH model / signal
says about every player as a WITHIN-POSITION percentile (0-100, higher = better),
and surface where the signals AGREE (low divergence) vs DIVERGE (high divergence /
leverage flags). We compute a display-only `consensus` (mean of the *available real*
votes) and a `divergence` (std of those votes), but we NEVER collapse the individual
model columns into one blended number -- the per-model reads and their spread are the
product. A MISSING signal -> that vote ABSTAINS (it is excluded from the player's
consensus/divergence and from coverage), it is never silently scored 50.

This re-run consumes the fully-enriched feature store (features.json, 107 cols) which
now carries REAL play-by-play EPA + NGS tracking metrics (2025 full season). It KEEPS
the original votes and UPGRADES / ADDS efficiency dimensions on the REAL data:

  ORIGINAL VOTES (kept):
    market      <- adp                 (lower = better, inverted)
    value       <- merged_rank         (lower = better, inverted)
    proj        <- proj_pg             (higher = better)
    ceiling     <- p95 magnitude + spike frequency (higher = better)
    spike       <- spike               (boom-week frequency, displayed separately)
    adv         <- adv_pct             (advance-rate, higher = better)
    coachspeak  <- qual_signal/qual_score if present, else abstain
    route_eff   (WR/TE) <- max(yprr_man, yprr_zone)        best-of route efficiency (kept)
    coverage_proof (WR/TE) <- 100 - scaled|man_zone_delta| + man_route_sh context (kept)
    run_eff     (RB)    <- share-weighted(zone_succ, gap_succ) - stuff_pct        (kept)
    oline       (all)   <- ol_pass_winrate (QB/pass-catchers) | ol_run_winrate (RB)  [team]
    matchup     (ctx)   <- season SoS from OUR 2026 defense.json: mean opp pass_cov_pctl
                           (QB/WR/TE) | mean opp run_def_pctl (RB) over the full schedule
                           (softer schedule = better). REWIRED off third-party ffdataroma tiers.

  UPGRADED / NEW on the now-REAL EPA + NGS data (2025 full season talent prior):
    protection  (QB)  <- REAL qb_epa_db (EPA/dropback, PRIMARY) + qb_cpoe + qb_anya
                         + qb_epa_man + qb_epa_zone (REAL SIS per-att EPA vs MAN/ZONE)
                         + inverted qb_pressure_rate (lower pressure = better). This
                         REPLACES the old ANY/A-only sack%/ypa proxy as the QB
                         efficiency vote (the vote key stays `protection`).
    rec_eff     (WR/TE) <- REAL rec_epa_route (Rec EPA/route, PRIMARY) + route_yprr
                           + fd_rr (first downs / route = chain-mover) + adot_adj_ypt.
    separation  (WR/TE) <- REAL rec_separation (NGS avg separation = getting open), OWN vote.
    yac         (WR/TE/RB) <- REAL rec_yacoe (YAC over expected = after the catch).
    rush_eff    (RB)  <- REAL rush_epa_att (Rush EPA/att, PRIMARY) + ryoe_att (rush yds
                         over expected / att).
    explosive   (WR/RB) <- deep_route_sh (WR deep-route share) / rb_topspeed (RB
                           breakaway top-speed count).

  NEW on REAL SIS DataHub signals (2025), each its own within-position vote / fold:
    sis_value   (all)   <- REAL sis_epa (total EPA / value). Own vote, abstains if null.
    boom        (all)   <- REAL sis_boom (Boom% = ceiling-game rate). Own vote.
    rec_eff     (WR/TE) <- ALSO folds rec_epa_per_tgt_man (REAL EPA/target vs MAN) AND
                           rec_epa_per_tgt_zone (REAL EPA/target vs ZONE) alongside
                           rec_epa_route + yprr + fd_rr + adot (averaged into the same vote).
  NEW flags:
    BOOM MERCHANT  -- sis_boom top-quartile (within pos) AND market <= 55.
    FLOOR RISK     -- sis_bust top-quartile (within pos) AND market >= 60.
    MAN-BEATER     -- rec_man_zone_delta top-quartile of non-null deltas (feasts vs MAN).
    ZONE-BEATER    -- rec_man_zone_delta bottom-quartile of non-null deltas (feasts vs ZONE).
    QB-MAN-BEATER  -- qb_man_zone_delta top-quartile of non-null QB deltas (per-att EPA better vs MAN).
    QB-ZONE-BEATER -- qb_man_zone_delta bottom-quartile of non-null QB deltas (per-att EPA better vs ZONE).
    RB-ZONE-SCHEME -- rb_zone_gap_delta top-quartile of non-null RB deltas (EPA/A better on ZONE runs).
    RB-GAP-SCHEME  -- rb_zone_gap_delta bottom-quartile of non-null RB deltas (EPA/A better on GAP runs).

Each composite vote is the MEAN of the within-position percentiles of its REAL
available components: a null component abstains inside the composite, and the whole
vote abstains only when EVERY component is null. Each vote is a within-position
percentile (QB/RB/WR/TE) so cross-position comparison is fair. A player MISSING a
signal is EXCLUDED from that signal's coverage and from his own consensus/divergence;
the displayed percentile column is neutral-filled to 50 ONLY so the column is NaN-free,
but that 50 never enters an aggregate (raw-presence masks gate everything).

Inputs (READ-ONLY):
  features.json   ({meta, players:[...]})  -- the unified feature store (THE spine, 371)
  qual_signal.csv (coachspeak source; name,qual_score,...; ~86 players)
  ffdataroma_draft_guide_export/ffdataroma/csv/metric-correlations__{pos}_high-volume.csv
                  (OPTIONAL: if readable, used to justify which efficiency metrics
                   predict next-year fantasy; otherwise votes are weighted equally and
                   weights_note says so)

Outputs (written by THIS script only):
  fusion_table.csv   tidy, one row per player, all columns
  fusion.json        {meta:{coverage, notes, ...}, players:[...]}
"""

import os
import json
import csv as _csv

import numpy as np
import pandas as pd

import core  # shared: fn, norm_team, safe_json_dump, P()

HERE = os.path.dirname(os.path.abspath(__file__))


def P(*parts):
    return os.path.join(HERE, *parts)


NEUTRAL = 50.0

# Defensive-tier strings -> higher = better matchup FOR THE OFFENSE (i.e. a weaker
# defense is a better matchup). "Poor" defense -> best matchup -> highest rank.
# NOTE (Branch 3): TIER_RANK / ffdataroma tiers are no longer the matchup source — the
# matchup vote now derives from OUR 2026 projected defense via season_sos(). Kept for ref.
TIER_RANK = {"Elite": 1, "Good": 2, "Average": 3, "Below Avg": 4, "Poor": 5}


def season_sos():
    """Strength-of-schedule from OUR 2026 projected defense (defense.json), averaged over
    each team's full 2026 schedule (weeks 1-17). Returns {team: {'cov':.., 'run':..}} where
    each value is the mean opponent unit percentile (higher = TOUGHER schedule). This replaces
    the third-party ffdataroma tier so the matchup vote is coherent with the rest of the 2026
    model, opponent-correct, and stable (17 opponents, not a single week). Abstains (None) when
    a team's schedule or our defense pctls are unavailable."""
    try:
        dj = json.load(open(P("defense.json"), encoding="utf-8"))
    except Exception:
        return {}
    teams = dj.get("teams", dj)
    FULL2ABBR = {'Arizona Cardinals':'ARI','Atlanta Falcons':'ATL','Baltimore Ravens':'BAL','Buffalo Bills':'BUF','Carolina Panthers':'CAR','Chicago Bears':'CHI','Cincinnati Bengals':'CIN','Cleveland Browns':'CLE','Dallas Cowboys':'DAL','Denver Broncos':'DEN','Detroit Lions':'DET','Green Bay Packers':'GB','Houston Texans':'HOU','Indianapolis Colts':'IND','Jacksonville Jaguars':'JAX','Kansas City Chiefs':'KC','Los Angeles Chargers':'LAC','Los Angeles Rams':'LAR','Las Vegas Raiders':'LV','Miami Dolphins':'MIA','Minnesota Vikings':'MIN','New England Patriots':'NE','New Orleans Saints':'NO','New York Giants':'NYG','New York Jets':'NYJ','Philadelphia Eagles':'PHI','Pittsburgh Steelers':'PIT','Seattle Seahawks':'SEA','San Francisco 49ers':'SF','Tampa Bay Buccaneers':'TB','Tennessee Titans':'TEN','Washington Commanders':'WAS'}
    def _code(x):
        x = str(x or "").replace("@", "").replace("vs", "").strip()
        return core.norm_team(FULL2ABBR.get(x, x))
    DEF = {t: {"cov": v.get("pass_cov_pctl"), "run": v.get("run_def_pctl")}
           for t, v in teams.items()}
    sched_path = next((P(c) for c in ("pipeline/schedule_2026.csv", "schedule_2026.csv")
                       if os.path.exists(P(c))), None)
    if not sched_path:
        return {}
    out = {}
    for r in _csv.DictReader(open(sched_path, encoding="utf-8")):
        tm = _code(r.get("Team", ""))
        opps = []
        for w in range(1, 18):  # weeks 1-17 (fantasy regular season + playoffs)
            cell = str(r.get(f"Week {w}", "") or "").replace("@", "").replace("vs", "").strip()
            if not cell or cell.upper() in ("BYE", "NAN", ""):
                continue
            opps.append(_code(cell))
        cov = [DEF[o]["cov"] for o in opps if o in DEF and DEF[o]["cov"] is not None]
        run = [DEF[o]["run"] for o in opps if o in DEF and DEF[o]["run"] is not None]
        out[tm] = {"cov": (sum(cov) / len(cov) if cov else None),
                   "run": (sum(run) / len(run) if run else None)}
    return out

# which positions each position-specific signal applies to (rest apply to all four).
# Used for CSV blanking + in-scope NaN verification.
APPLIES = {
    "route_eff_pctl": {"WR", "TE"},
    "coverage_proof_pctl": {"WR", "TE"},
    "rec_eff_pctl": {"WR", "TE"},
    "separation_pctl": {"WR", "TE"},
    "yac_pctl": {"WR", "TE", "RB"},
    "run_eff_pctl": {"RB"},
    "rush_eff_pctl": {"RB"},
    "explosive_pctl": {"WR", "RB"},
    "protection_pctl": {"QB"},
}


def within_pos_pctl(df, value_col, pos_col="pos", invert=False, neutral=NEUTRAL):
    """Within-position rank -> (0,100], higher input -> higher pct (unless invert).

    Players whose raw value is NaN are EXCLUDED from the ranking (so absent reads
    don't distort the live scale) and THEN filled to the neutral midpoint, per the
    "missing signal -> neutral 50 for that vote" policy. So the returned percentile
    column is itself NaN-free; whether a player's read is REAL vs a neutral fill is
    tracked separately (raw-presence masks) for coverage and consensus/divergence.
    A position with a single eligible player maps that player to `neutral`.
    """
    out = pd.Series(np.nan, index=df.index, dtype=float)
    vals = pd.to_numeric(df[value_col], errors="coerce")
    if invert:
        vals = -vals  # smaller raw -> larger ranked value -> higher pct
    for _, idx in df.groupby(pos_col).groups.items():
        present = vals.loc[idx].dropna()
        if len(present) == 0:
            continue
        if len(present) == 1:
            out.loc[present.index] = neutral
        else:
            r = present.rank(method="average")
            out.loc[present.index] = ((r - 0.5) / len(present) * 100.0).values
    # missing-but-applicable players -> neutral midpoint (NaN-free output)
    return out.fillna(neutral).round(2)


def within_pos_pctl_series(df, raw, pos_col="pos", invert=False):
    """Like within_pos_pctl but takes a raw Series and returns a NaN-PRESERVING
    percentile (absent -> NaN, NOT neutral-filled). Used as the building block for
    composite votes, where a missing COMPONENT must abstain inside the mean rather
    than pull it toward 50.
    """
    out = pd.Series(np.nan, index=df.index, dtype=float)
    vals = pd.to_numeric(raw, errors="coerce")
    if invert:
        vals = -vals
    for _, idx in df.groupby(pos_col).groups.items():
        present = vals.loc[idx].dropna()
        if len(present) == 0:
            continue
        if len(present) == 1:
            out.loc[present.index] = NEUTRAL
        else:
            r = present.rank(method="average")
            out.loc[present.index] = ((r - 0.5) / len(present) * 100.0).values
    return out.round(2)  # NaN preserved where absent


def composite_vote(df, components, scope=None):
    """Build a composite percentile vote from REAL components.

    components: list of (raw_col, invert) -- each ranked within position (NaN-safe),
                then averaged ROW-WISE skipping absent components.
    scope:      optional set of positions the vote applies to; rows outside scope are
                forced to NaN (structural N/A, not a real abstention).

    Returns (vote_pctl_neutralfilled, real_mask) where:
      vote_pctl_neutralfilled : NaN-free column for display (absent-but-applicable -> 50)
      real_mask               : True where AT LEAST ONE component was REAL (the vote
                                actually voted) -- this gates coverage + consensus/div.
    """
    parts = []
    for col, inv in components:
        if col in df.columns:
            parts.append(within_pos_pctl_series(df, df[col], invert=inv))
    if not parts:
        empty = pd.Series(np.nan, index=df.index, dtype=float)
        return empty.fillna(NEUTRAL), pd.Series(False, index=df.index)
    mat = pd.concat(parts, axis=1)
    raw_vote = mat.mean(axis=1, skipna=True)           # absent components abstain
    real_mask = mat.notna().any(axis=1)                # vote voted iff >=1 real component
    if scope is not None:
        in_scope = df["pos"].isin(scope)
        raw_vote = raw_vote.where(in_scope)
        real_mask = real_mask & in_scope
    # re-rank the composite within position so the vote sits on the same 0..100 scale
    vote = within_pos_pctl_series(df, raw_vote)
    real_mask = real_mask & vote.notna()
    return vote.fillna(NEUTRAL).round(2), real_mask


def scaled_abs_within_pos(df, value_col, pos_col="pos"):
    """|value| min-max scaled to 0..100 WITHIN position (0 = smallest |delta|).

    Used for coverage_proof: a small |man_zone_delta| (player beats both man & zone
    about equally) should score HIGH, so we return 100 - scaled. NaN -> NaN (caller
    neutral-fills + excludes from coverage).
    """
    out = pd.Series(np.nan, index=df.index, dtype=float)
    a = pd.to_numeric(df[value_col], errors="coerce").abs()
    for _, idx in df.groupby(pos_col).groups.items():
        present = a.loc[idx].dropna()
        if len(present) == 0:
            continue
        lo, hi = present.min(), present.max()
        if hi == lo:
            out.loc[present.index] = 50.0
        else:
            out.loc[present.index] = ((present - lo) / (hi - lo) * 100.0).values
    return out


def main():
    # -----------------------------------------------------------------
    # Load the feature store (THE spine) + coachspeak source
    # -----------------------------------------------------------------
    with open(P("features.json"), encoding="utf-8") as f:
        store = json.load(f)
    meta_in = store.get("meta", {}) if isinstance(store, dict) else {}
    df = pd.DataFrame(store["players"])
    n_board = len(df)

    # numeric coercion for the vote inputs (string-typed in the store). Includes the
    # original proxy fields AND the now-REAL EPA / NGS columns.
    num_cols = [
        "adp", "merged_rank", "proj_pg", "p95", "spike", "adv_pct",
        # original WR/TE / RB / QB proxy efficiency
        "yprr_man", "yprr_zone", "man_route_sh", "man_zone_delta",
        "zone_succ", "gap_succ", "zone_run_sh", "stuff_pct",
        "sack_pct25", "ypa25", "ol_pass_winrate", "ol_run_winrate",
        # REAL QB EPA / pressure
        "qb_epa_db", "qb_cpoe", "qb_anya", "qb_pressure_rate",
        # REAL WR/TE receiving efficiency + NGS
        "rec_epa_route", "route_yprr", "fd_rr", "adot_adj_ypt",
        "rec_separation", "rec_yacoe", "deep_route_sh",
        # REAL RB rushing efficiency + speed
        "rush_epa_att", "ryoe_att", "rb_topspeed",
        # REAL SIS DataHub value/ceiling signals
        "sis_epa", "sis_boom", "sis_bust", "rec_epa_per_tgt_man",
        # REAL SIS man/zone coverage split
        "rec_epa_per_tgt_zone", "rec_man_zone_delta",
        # NEW: REAL SIS QB man/zone split + RB zone/gap split
        "qb_epa_man", "qb_epa_zone", "qb_man_zone_delta",
        "rb_epa_a_zone", "rb_epa_a_gap", "rb_zone_gap_delta",
    ]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # coachspeak: the feature store has no qual field, so source it from qual_signal.csv
    # ("qual_signal if present else abstain"). Covered players are ranked only against
    # each other within position; uncovered players abstain (excluded from cons/div).
    qual = {}
    if os.path.exists(P("qual_signal.csv")):
        with open(P("qual_signal.csv"), encoding="utf-8") as f:
            for row in _csv.DictReader(f):
                try:
                    qual[row["name"]] = float(row["qual_score"])
                except (TypeError, ValueError):
                    pass
    df["qual_signal"] = df["name"].map(qual)

    # -----------------------------------------------------------------
    # OPTIONAL: ffdataroma metric-correlations -> justify which efficiency metrics
    # predict next-year fantasy. If unreadable, weight votes equally and SAY SO.
    # -----------------------------------------------------------------
    corr_dir = P("ffdataroma_draft_guide_export", "ffdataroma", "csv")
    corr_notes = []
    corr_found = False
    for pos in ["WR", "RB", "TE", "QB"]:
        fp = os.path.join(corr_dir, "metric-correlations__%s_high-volume.csv" % pos)
        if os.path.exists(fp):
            try:
                pd.read_csv(fp)
                corr_found = True
                corr_notes.append("%s:%s" % (pos, os.path.basename(fp)))
            except Exception:
                pass
    if corr_found:
        weights_note = (
            "Efficiency metrics justified by ffdataroma metric-correlations "
            "(%s). Votes still displayed separately and weighted equally in "
            "consensus/divergence (fusion shows each signal, never collapses)."
            % "; ".join(corr_notes)
        )
    else:
        weights_note = (
            "ffdataroma_draft_guide_export/ffdataroma/csv/metric-correlations__{pos}_"
            "high-volume.csv was NOT present/readable in this tree, so we did NOT "
            "down/up-weight any efficiency metric on a measured next-year predictive "
            "basis -- ALL votes are weighted EQUALLY in consensus/divergence. Each vote "
            "is always displayed separately regardless; consensus is a mean and "
            "divergence a std over only the available REAL votes per player. NOTE: "
            "protection(EPA) / rec_eff / separation / yac / rush_eff / explosive (and "
            "the kept route_eff / coverage_proof / run_eff) are 2025 FULL-SEASON EPA + "
            "NGS metrics, used as a talent PRIOR on the player, not a guaranteed 2026 "
            "forecast."
        )

    # =================================================================
    # MODEL PERCENTILES (each within position, higher = better)
    # =================================================================
    # --- ORIGINAL VOTES ---
    df["market_pctl"] = within_pos_pctl(df, "adp", invert=True)
    df["value_pctl"] = within_pos_pctl(df, "merged_rank", invert=True)
    df["proj_pctl"] = within_pos_pctl(df, "proj_pg", invert=False)
    df["p95_pctl"] = within_pos_pctl(df, "p95", invert=False)
    df["spike_pctl"] = within_pos_pctl(df, "spike", invert=False)
    # ceiling = magnitude-led (p95) with a lighter boom-frequency nudge (spike).
    W_P95, W_SPIKE = 0.75, 0.25
    df["ceiling_pctl"] = (W_P95 * df["p95_pctl"] + W_SPIKE * df["spike_pctl"]).round(2)
    df["adv_pctl"] = within_pos_pctl(df, "adv_pct", invert=False)
    df["coachspeak_pctl"] = within_pos_pctl(df, "qual_signal", invert=False)

    # --- KEPT: route_eff (WR/TE) = best-of route efficiency (legacy yprr man/zone) ---
    df["route_eff_raw"] = df[["yprr_man", "yprr_zone"]].max(axis=1)
    df["route_eff_pctl"] = within_pos_pctl(df, "route_eff_raw", invert=False)

    # --- KEPT: coverage_proof (WR/TE) = scheme versatility (legacy man-zone delta) ---
    cp_base = 100.0 - scaled_abs_within_pos(df, "man_zone_delta")
    mrs_pctl = within_pos_pctl(df, "man_route_sh", invert=False)
    cp = 0.80 * cp_base + 0.20 * mrs_pctl
    cp[cp_base.isna()] = np.nan  # no delta -> no coverage_proof read
    df["coverage_proof_raw"] = cp
    df["coverage_proof_pctl"] = within_pos_pctl(df, "coverage_proof_raw", invert=False)

    # --- KEPT: run_eff (RB) = share-weighted run success minus stuffs (legacy) ---
    zsh = (df["zone_run_sh"] / 100.0).clip(0, 1)
    gsh = 1.0 - zsh
    blend = df["zone_succ"] * zsh + df["gap_succ"].fillna(df["zone_succ"]) * gsh
    df["run_eff_raw"] = blend - df["stuff_pct"]
    need = df["zone_succ"].isna() | df["stuff_pct"].isna() | df["zone_run_sh"].isna()
    df.loc[need, "run_eff_raw"] = np.nan
    df["run_eff_pctl"] = within_pos_pctl(df, "run_eff_raw", invert=False)

    # =================================================================
    # UPGRADED / NEW REAL-DATA VOTES (each = mean of within-pos percentiles of its
    # available REAL components; abstains only when ALL components are null).
    # =================================================================
    # --- UPGRADE: protection (QB) = REAL EPA/dropback PRIMARY + cpoe + anya +
    #     inverted pressure_rate. Replaces the ANY/A-only sack%/ypa proxy. ---
    df["protection_pctl"], protection_real = composite_vote(
        df,
        [("qb_epa_db", False),        # PRIMARY: EPA per dropback (higher better)
         ("qb_cpoe", False),          # completion % over expected (higher better)
         ("qb_anya", False),          # adjusted net yards / attempt (higher better)
         ("qb_epa_man", False),       # NEW (REAL SIS): per-att EPA vs MAN coverage (higher better)
         ("qb_epa_zone", False),      # NEW (REAL SIS): per-att EPA vs ZONE coverage (higher better)
         ("qb_pressure_rate", True)], # pressure rate (LOWER better -> invert)
        scope={"QB"},
    )
    # keep a representative "raw" presence signal for legacy gates/printing
    df["protection_raw"] = df["qb_epa_db"]

    # --- NEW: rec_eff (WR/TE) = REAL Rec EPA/route PRIMARY + yprr + fd/route + adot-adj ypt ---
    df["rec_eff_pctl"], rec_eff_real = composite_vote(
        df,
        [("rec_epa_route", False),        # PRIMARY: receiving EPA per route (higher better)
         ("rec_epa_per_tgt_man", False),  # NEW (REAL SIS): receiving EPA/target vs MAN coverage (higher better)
         ("rec_epa_per_tgt_zone", False), # NEW (REAL SIS): receiving EPA/target vs ZONE coverage (higher better)
         ("route_yprr", False),           # yards per route run (higher better)
         ("fd_rr", False),                # first downs per route = chain-mover (higher better)
         ("adot_adj_ypt", False)],        # aDOT-adjusted yards per target (higher better)
        scope={"WR", "TE"},
    )
    df["rec_eff_raw"] = df["rec_epa_route"]

    # --- NEW: separation (WR/TE) = REAL NGS average separation (getting open), OWN vote ---
    df["separation_pctl"], separation_real = composite_vote(
        df, [("rec_separation", False)], scope={"WR", "TE"},
    )
    df["separation_raw"] = df["rec_separation"]

    # --- NEW: yac (WR/TE/RB) = REAL YAC over expected (after the catch) ---
    df["yac_pctl"], yac_real = composite_vote(
        df, [("rec_yacoe", False)], scope={"WR", "TE", "RB"},
    )
    df["yac_raw"] = df["rec_yacoe"]

    # --- NEW: rush_eff (RB) = REAL Rush EPA/att PRIMARY + rush yds over expected/att ---
    df["rush_eff_pctl"], rush_eff_real = composite_vote(
        df,
        [("rush_epa_att", False),     # PRIMARY: rush EPA per attempt (higher better)
         ("ryoe_att", False)],        # rush yds over expected / att (higher better)
        scope={"RB"},
    )
    df["rush_eff_raw"] = df["rush_epa_att"]

    # --- NEW: explosive (WR/RB) = deep-route share (WR) / breakaway top-speed count (RB) ---
    df["explosive_raw"] = np.where(
        df["pos"] == "WR", df["deep_route_sh"],
        np.where(df["pos"] == "RB", df["rb_topspeed"], np.nan),
    )
    df["explosive_pctl"], explosive_real = composite_vote(
        df, [("explosive_raw", False)], scope={"WR", "RB"},
    )

    # --- NEW: sis_value (all) = REAL SIS total EPA (value); its OWN within-pos vote ---
    df["sis_value_pctl"], sis_value_real = composite_vote(
        df, [("sis_epa", False)],  # REAL SIS EPA/value (higher better)
    )
    df["sis_value_raw"] = df["sis_epa"]

    # --- NEW: boom (all) = REAL SIS Boom% (ceiling-game rate); its OWN within-pos vote ---
    df["boom_pctl"], boom_real = composite_vote(
        df, [("sis_boom", False)],  # REAL SIS Boom% (higher better -> more ceiling games)
    )
    df["boom_raw"] = df["sis_boom"]

    # --- KEPT: oline (all) = pass-pro win-rate for QB/pass-catchers, run win-rate for RB ---
    df["oline_raw"] = np.where(df["pos"] == "RB", df["ol_run_winrate"], df["ol_pass_winrate"])
    df["oline_pctl"] = within_pos_pctl(df, "oline_raw", invert=False)

    # --- REWIRED (Branch 3): matchup (ctx) = season strength-of-schedule from OUR 2026
    #     projected defense (defense.json), opponent-correct per position:
    #       RB        -> mean opponent run_def_pctl over the schedule
    #       QB/WR/TE  -> mean opponent pass_cov_pctl over the schedule
    #     Replaces the third-party ffdataroma tier AND fixes the RB bug (it used the RB's
    #     OWN team_run_def_tier, not the opponent's). matchup_raw = schedule DIFFICULTY
    #     (higher = tougher); invert=True so a SOFTER schedule scores higher (better matchup).
    SOS = season_sos()
    def sos_for(r):
        s = SOS.get(r.get("team"))
        if not s:
            return np.nan
        v = s["run"] if r["pos"] == "RB" else s["cov"]
        return v if v is not None else np.nan
    df["matchup_raw"] = df.apply(sos_for, axis=1)             # higher = tougher schedule
    df["matchup_pctl"] = within_pos_pctl(df, "matchup_raw", invert=True)  # softer = better vote

    # =================================================================
    # Coverage tracking (real, non-null INPUTS, before any neutral fill)
    # =================================================================
    def cov(col, mask=None):
        s = df[col]
        m = s.notna() if mask is None else (s.notna() & mask)
        return int(m.sum())

    is_pc = df["pos"].isin(["WR", "TE"])
    is_rb = df["pos"] == "RB"
    is_qb = df["pos"] == "QB"
    is_wr = df["pos"] == "WR"
    is_pc_rb = df["pos"].isin(["WR", "TE", "RB"])

    coverage = {
        # original
        "market_adp": cov("adp"),
        "value_merged_rank": cov("merged_rank"),
        "proj_pg": cov("proj_pg"),
        "ceiling_p95": cov("p95"),
        "spike": cov("spike"),
        "adv_pct": cov("adv_pct"),
        "coachspeak_qual_signal": cov("qual_signal"),
        "route_eff_WRTE": cov("route_eff_raw", is_pc),
        "coverage_proof_WRTE": cov("coverage_proof_raw", is_pc),
        "run_eff_RB": cov("run_eff_raw", is_rb),
        "oline_all": cov("oline_raw"),
        "matchup_ctx": cov("matchup_raw"),
        # UPGRADED / NEW REAL votes (count = vote actually voted, i.e. >=1 real component)
        "protection_EPA_QB": int(protection_real.sum()),
        "rec_eff_WRTE": int(rec_eff_real.sum()),
        "separation_WRTE": int(separation_real.sum()),
        "yac_WRTE_RB": int(yac_real.sum()),
        "rush_eff_RB": int(rush_eff_real.sum()),
        "explosive_WR_RB": int(explosive_real.sum()),
        # NEW REAL SIS votes
        "sis_value_all": int(sis_value_real.sum()),
        "boom_all": int(boom_real.sum()),
        # component-level coverage for the REAL votes (transparency)
        "_components": {
            "qb_epa_db": cov("qb_epa_db", is_qb),
            "qb_cpoe": cov("qb_cpoe", is_qb),
            "qb_anya": cov("qb_anya", is_qb),
            "qb_pressure_rate": cov("qb_pressure_rate", is_qb),
            "rec_epa_route_WRTE": cov("rec_epa_route", is_pc),
            "route_yprr_WRTE": cov("route_yprr", is_pc),
            "fd_rr_WRTE": cov("fd_rr", is_pc),
            "adot_adj_ypt_WRTE": cov("adot_adj_ypt", is_pc),
            "rec_separation_WRTE": cov("rec_separation", is_pc),
            "rec_yacoe_WRTE_RB": cov("rec_yacoe", is_pc_rb),
            "rush_epa_att_RB": cov("rush_epa_att", is_rb),
            "ryoe_att_RB": cov("ryoe_att", is_rb),
            "deep_route_sh_WR": cov("deep_route_sh", is_wr),
            "rb_topspeed_RB": cov("rb_topspeed", is_rb),
            "sis_epa_all": cov("sis_epa"),
            "sis_boom_all": cov("sis_boom"),
            "sis_bust_all": cov("sis_bust"),
            "rec_epa_per_tgt_man_WRTE": cov("rec_epa_per_tgt_man", is_pc),
            "rec_epa_per_tgt_zone_WRTE": cov("rec_epa_per_tgt_zone", is_pc),
            "rec_man_zone_delta_WRTE": cov("rec_man_zone_delta", is_pc),
            "qb_epa_man_QB": cov("qb_epa_man", is_qb),
            "qb_epa_zone_QB": cov("qb_epa_zone", is_qb),
            "qb_man_zone_delta_QB": cov("qb_man_zone_delta", is_qb),
            "rb_zone_gap_delta_RB": cov("rb_zone_gap_delta", is_rb),
        },
        "_n_players": n_board,
        "_pos_counts": df["pos"].value_counts().to_dict(),
    }

    # =================================================================
    # consensus + divergence over ONLY the AVAILABLE REAL votes per player.
    # A neutral-50 fill for a missing signal must not pull a player's consensus to the
    # middle nor shrink his divergence, so we mask each vote to where its raw input
    # actually exists, and aggregate row-wise over the present ones.
    # =================================================================
    # (vote key, pctl column, raw-presence mask). For composite REAL votes the mask is
    # the "vote actually voted" mask returned by composite_vote. ceiling keyed on p95.
    vote_specs = [
        ("market", "market_pctl", df["adp"].notna()),
        ("value", "value_pctl", df["merged_rank"].notna()),
        ("proj", "proj_pctl", df["proj_pg"].notna()),
        ("ceiling", "ceiling_pctl", df["p95"].notna()),
        ("spike", "spike_pctl", df["spike"].notna()),
        ("adv", "adv_pctl", df["adv_pct"].notna()),
        ("coachspeak", "coachspeak_pctl", df["qual_signal"].notna()),
        ("route_eff", "route_eff_pctl", df["route_eff_raw"].notna()),
        ("coverage_proof", "coverage_proof_pctl", df["coverage_proof_raw"].notna()),
        ("run_eff", "run_eff_pctl", df["run_eff_raw"].notna()),
        ("protection", "protection_pctl", protection_real),
        ("rec_eff", "rec_eff_pctl", rec_eff_real),
        ("separation", "separation_pctl", separation_real),
        ("yac", "yac_pctl", yac_real),
        ("rush_eff", "rush_eff_pctl", rush_eff_real),
        ("explosive", "explosive_pctl", explosive_real),
        ("oline", "oline_pctl", df["oline_raw"].notna()),
        ("matchup", "matchup_pctl", df["matchup_raw"].notna()),
        ("sis_value", "sis_value_pctl", sis_value_real),
        ("boom", "boom_pctl", boom_real),
    ]

    # matrix of votes where present, NaN where absent -> nanmean / nanstd row-wise.
    vote_present = pd.DataFrame(index=df.index)
    for key, col, mask in vote_specs:
        vote_present[key] = df[col].where(mask)

    df["consensus"] = vote_present.mean(axis=1, skipna=True).round(2)
    # population std (ddof=0) over available votes; single-vote rows -> 0.0.
    df["divergence"] = vote_present.std(axis=1, ddof=0).round(2).fillna(0.0)
    df["_n_votes"] = vote_present.notna().sum(axis=1).astype(int)

    # =================================================================
    # Leverage FLAGS. Built from per-model percentiles so divergence is explainable.
    # =================================================================
    # position-appropriate REAL-EPA efficiency read for the new flags:
    #   WR/TE -> max(rec_eff, route_eff, coverage_proof, separation);
    #   RB    -> max(rush_eff, run_eff, yac);
    #   QB    -> protection (EPA).
    def eff_read(r):
        if r["pos"] in ("WR", "TE"):
            vals = [v for v, m in [
                (r["rec_eff_pctl"], rec_eff_real.loc[r.name]),
                (r["route_eff_pctl"], pd.notna(r["route_eff_raw"])),
                (r["coverage_proof_pctl"], pd.notna(r["coverage_proof_raw"])),
                (r["separation_pctl"], separation_real.loc[r.name]),
            ] if m]
            return max(vals) if vals else np.nan
        if r["pos"] == "RB":
            vals = [v for v, m in [
                (r["rush_eff_pctl"], rush_eff_real.loc[r.name]),
                (r["run_eff_pctl"], pd.notna(r["run_eff_raw"])),
                (r["yac_pctl"], yac_real.loc[r.name]),
            ] if m]
            return max(vals) if vals else np.nan
        if r["pos"] == "QB":
            return r["protection_pctl"] if protection_real.loc[r.name] else np.nan
        return np.nan
    df["eff_read"] = df.apply(eff_read, axis=1)

    # the REAL-EPA efficiency read (rec_eff for WR/TE, rush_eff for RB, protection/EPA
    # for QB) -- this is what EFFICIENCY TRAP weak-EPA test and EFFICIENCY EDGE judge.
    def real_epa_read(r):
        if r["pos"] in ("WR", "TE"):
            return r["rec_eff_pctl"] if rec_eff_real.loc[r.name] else np.nan
        if r["pos"] == "RB":
            return r["rush_eff_pctl"] if rush_eff_real.loc[r.name] else np.nan
        if r["pos"] == "QB":
            return r["protection_pctl"] if protection_real.loc[r.name] else np.nan
        return np.nan
    df["real_epa_read"] = df.apply(real_epa_read, axis=1)

    # separation read (WR/TE only) for SEPARATION KING.
    df["sep_read"] = np.where(
        df["pos"].isin(["WR", "TE"]) & separation_real,
        df["separation_pctl"], np.nan,
    )

    # NEW: SIS boom read (all, the boom vote pctl where the vote actually voted) for
    # BOOM MERCHANT, and a SIS bust read (RAW Bust% rate, present where sis_bust real)
    # for FLOOR RISK. Bust is a FLOOR-RISK rate, so it is NOT a "higher=better" vote --
    # we keep the raw rate and flag its top quartile directly.
    df["boom_read"] = np.where(boom_real, df["boom_pctl"], np.nan)
    df["bust_read"] = pd.to_numeric(df["sis_bust"], errors="coerce")  # raw Bust% (higher = more floor risk)

    # NEW: coverage-scheme talent/matchup descriptor read. rec_man_zone_delta =
    # EPA/tgt vs MAN - vs ZONE (REAL SIS). +ve = man-beater (feasts vs man, e.g. Pickens
    # +0.66); -ve = zone-beater (feasts vs zone, e.g. Bowers -0.54). It is a SIGNED
    # descriptor, not a higher=better vote, so (like bust) we keep the raw signed value
    # and flag the top quartile (MAN-BEATER) / bottom quartile (ZONE-BEATER) of the
    # NON-NULL deltas directly. NaN where the player has no man/zone split (abstains -- no flag).
    df["mzdelta_read"] = pd.to_numeric(df.get("rec_man_zone_delta"), errors="coerce") \
        if "rec_man_zone_delta" in df.columns else pd.Series(np.nan, index=df.index)
    # NEW: QB coverage-scheme descriptor read. qb_man_zone_delta = per-att EPA vs MAN -
    # vs ZONE (REAL SIS). +ve = QB-MAN-BEATER (better vs man, e.g. Burrow +0.29); -ve =
    # QB-ZONE-BEATER (better vs zone, e.g. Allen -0.26). Signed descriptor (like the WR
    # mz delta), so we keep the raw value and flag top/bottom quartile of NON-NULL QB
    # deltas. NaN where the QB has no man/zone split (abstains -- no flag).
    df["qb_mzdelta_read"] = pd.to_numeric(df.get("qb_man_zone_delta"), errors="coerce") \
        if "qb_man_zone_delta" in df.columns else pd.Series(np.nan, index=df.index)
    # NEW: RB run-scheme descriptor read. rb_zone_gap_delta = EPA/A on zone runs - gap
    # runs (REAL SIS). +ve = RB-ZONE-SCHEME (better on zone, e.g. Bijan +0.13); -ve =
    # RB-GAP-SCHEME (better on gap, e.g. J.Taylor -0.26). Signed descriptor; keep raw and
    # flag top/bottom quartile of NON-NULL RB deltas. NaN where no zone/gap split.
    df["rb_zgdelta_read"] = pd.to_numeric(df.get("rb_zone_gap_delta"), errors="coerce") \
        if "rb_zone_gap_delta" in df.columns else pd.Series(np.nan, index=df.index)

    # de-fragment the frame once after the many vote/read column inserts above (no-op
    # for values; just collapses the block-manager so the groupby/apply below don't warn).
    df = df.copy()

    # the per-position efficiency / EPA / separation top-/bottom-quartile thresholds.
    df["_eff_q75"] = df.groupby("pos")["eff_read"].transform(lambda s: s.quantile(0.75))
    df["_eff_q25"] = df.groupby("pos")["eff_read"].transform(lambda s: s.quantile(0.25))
    df["_epa_q75"] = df.groupby("pos")["real_epa_read"].transform(lambda s: s.quantile(0.75))
    df["_epa_q25"] = df.groupby("pos")["real_epa_read"].transform(lambda s: s.quantile(0.25))
    df["_sep_q75"] = df.groupby("pos")["sep_read"].transform(lambda s: s.quantile(0.75))
    # NEW: SIS boom (pctl) + bust (raw rate) top-quartile thresholds, within position.
    df["_boom_q75"] = df.groupby("pos")["boom_read"].transform(lambda s: s.quantile(0.75))
    df["_bust_q75"] = df.groupby("pos")["bust_read"].transform(lambda s: s.quantile(0.75))
    # NEW: man/zone delta quartile gates over the NON-NULL deltas (all WR/TE). Top
    # quartile (>= q75) = MAN-BEATER; bottom quartile (<= q25) = ZONE-BEATER. A single
    # pooled gate over non-null deltas matches the descriptor's "top/bottom quartile of
    # non-null deltas" definition (the deltas are WR/TE-only, so pooled == within-pos here).
    _mzd_nonnull = df["mzdelta_read"].dropna()
    MZD_Q75 = float(_mzd_nonnull.quantile(0.75)) if len(_mzd_nonnull) else np.nan
    MZD_Q25 = float(_mzd_nonnull.quantile(0.25)) if len(_mzd_nonnull) else np.nan
    # NEW: QB man/zone delta quartile gates over the NON-NULL QB deltas (QB-only, so
    # pooled == within-pos). Top quartile = QB-MAN-BEATER; bottom = QB-ZONE-BEATER.
    _qmzd_nonnull = df["qb_mzdelta_read"].dropna()
    QMZD_Q75 = float(_qmzd_nonnull.quantile(0.75)) if len(_qmzd_nonnull) else np.nan
    QMZD_Q25 = float(_qmzd_nonnull.quantile(0.25)) if len(_qmzd_nonnull) else np.nan
    # NEW: RB zone/gap delta quartile gates over the NON-NULL RB deltas (RB-only).
    # Top quartile = RB-ZONE-SCHEME; bottom = RB-GAP-SCHEME.
    _rzgd_nonnull = df["rb_zgdelta_read"].dropna()
    RZGD_Q75 = float(_rzgd_nonnull.quantile(0.75)) if len(_rzgd_nonnull) else np.nan
    RZGD_Q25 = float(_rzgd_nonnull.quantile(0.25)) if len(_rzgd_nonnull) else np.nan

    def make_flags(r):
        flags = []
        mkt, ceil, adv = r["market_pctl"], r["ceiling_pctl"], r["adv_pctl"]
        div = r["divergence"]
        covered = bool(pd.notna(r["p95"]))  # has a real sim/ceiling read
        eff = r["eff_read"]
        has_eff = pd.notna(eff)
        epa = r["real_epa_read"]
        has_epa = pd.notna(epa)
        sep = r["sep_read"]
        has_sep = pd.notna(sep)
        boom = r["boom_read"]
        has_boom = pd.notna(boom)
        bust = r["bust_read"]
        has_bust = pd.notna(bust)
        mzd = r["mzdelta_read"]
        has_mzd = pd.notna(mzd)
        qmzd = r["qb_mzdelta_read"]
        has_qmzd = pd.notna(qmzd)
        rzgd = r["rb_zgdelta_read"]
        has_rzgd = pd.notna(rzgd)

        model_love = max(ceil, adv)
        models_cool = (ceil + adv) / 2.0

        # ---- ORIGINAL flags (sim-coverage gated) ----
        # MARKET FADE: efficiency/ceiling >> market.
        if covered and model_love >= 55 and (model_love - mkt) >= 8:
            flags.append("MARKET FADE")
        # MARKET DARLING: market >> efficiency+adv.
        if covered and mkt >= 60 and (mkt - models_cool) >= 20:
            flags.append("MARKET DARLING")
        # CONSENSUS STUD: every CORE OPINION model top-quartile (>=75). Scoped to the
        # talent/value/projection axes (market, value, proj, ceiling, adv, coachspeak)
        # plus the position's primary efficiency read -- deliberately NOT spike (a
        # boom-frequency / variance axis) nor oline/matchup (TEAM context). Only REAL
        # (raw-present) votes count; uncovered ones are skipped.
        core_keys = {"market", "value", "proj", "ceiling", "adv", "coachspeak"}
        core_votes = [r[col] for key, col, m in vote_specs
                      if key in core_keys and bool(m.loc[r.name])]
        if pd.notna(eff):
            core_votes.append(eff)  # position efficiency must also be elite
        if covered and len(core_votes) >= 5 and all(v >= 75 for v in core_votes):
            flags.append("CONSENSUS STUD")
        # POLARIZING: votes disagree a lot.
        if covered and div > 22:
            flags.append("POLARIZING")

        # ---- efficiency-leverage flags ----
        # EFFICIENCY EDGE: pos efficiency top-quartile but market only mid.
        if has_eff and eff >= r["_eff_q75"] and 30 <= mkt <= 70:
            flags.append("EFFICIENCY EDGE")
        # EMPTY CALORIES: market/ceiling high but efficiency low (bottom quartile).
        if has_eff and max(mkt, ceil) >= 65 and eff <= r["_eff_q25"]:
            flags.append("EMPTY CALORIES")

        # ---- NEW REAL-EPA / NGS flags ----
        # SEPARATION KING: elite REAL separation (top-quartile) but a COOL market
        # (market <= 55) -- a get-open profile the room isn't paying for yet.
        if has_sep and sep >= r["_sep_q75"] and mkt <= 55:
            flags.append("SEPARATION KING")
        # EFFICIENCY TRAP: LOVED by the market (market high) but WEAK on REAL EPA
        # (real-EPA read bottom-quartile). Distinct from EMPTY CALORIES: this judges
        # the REAL play-by-play EPA specifically (rec_epa/route, rush_epa/att,
        # qb_epa/dropback), not the legacy proxy or ceiling.
        if has_epa and mkt >= 60 and epa <= r["_epa_q25"]:
            flags.append("EFFICIENCY TRAP")

        # ---- NEW SIS boom/bust flags ----
        # BOOM MERCHANT: REAL SIS Boom% top-quartile (ceiling-game propensity) but a
        # COOL market (market <= 55) -- a tournament ceiling the room isn't paying up for.
        if has_boom and boom >= r["_boom_q75"] and mkt <= 55:
            flags.append("BOOM MERCHANT")
        # FLOOR RISK: REAL SIS Bust% top-quartile (floor-game propensity) on a player the
        # market LOVES (market >= 60) -- a chalky pick with a quietly high dud rate.
        if has_bust and bust >= r["_bust_q75"] and mkt >= 60:
            flags.append("FLOOR RISK")

        # ---- NEW SIS coverage-scheme descriptors (talent/matchup, WR/TE) ----
        # MAN-BEATER: rec_man_zone_delta strongly POSITIVE (top quartile of non-null
        # deltas) -- feasts vs MAN coverage (e.g. George Pickens +0.66). Pairs with a
        # man-heavy DFS opponent for a boost.
        if has_mzd and pd.notna(MZD_Q75) and mzd >= MZD_Q75:
            flags.append("MAN-BEATER")
        # ZONE-BEATER: rec_man_zone_delta strongly NEGATIVE (bottom quartile of non-null
        # deltas) -- feasts vs ZONE coverage (e.g. Brock Bowers -0.54). Pairs with a
        # zone-heavy DFS opponent for a boost.
        if has_mzd and pd.notna(MZD_Q25) and mzd <= MZD_Q25:
            flags.append("ZONE-BEATER")

        # ---- NEW SIS QB coverage-scheme descriptors (QB) ----
        # QB-MAN-BEATER: qb_man_zone_delta top quartile of non-null QB deltas -- per-att
        # EPA much better vs MAN (e.g. Joe Burrow +0.29). Pairs with a man-heavy DFS opp.
        if has_qmzd and pd.notna(QMZD_Q75) and qmzd >= QMZD_Q75:
            flags.append("QB-MAN-BEATER")
        # QB-ZONE-BEATER: qb_man_zone_delta bottom quartile -- per-att EPA much better vs
        # ZONE (e.g. Josh Allen -0.26). Pairs with a zone-heavy DFS opponent.
        if has_qmzd and pd.notna(QMZD_Q25) and qmzd <= QMZD_Q25:
            flags.append("QB-ZONE-BEATER")

        # ---- NEW SIS RB run-scheme descriptors (RB) ----
        # RB-ZONE-SCHEME: rb_zone_gap_delta top quartile of non-null RB deltas -- EPA/A
        # much better on ZONE runs (e.g. Bijan +0.13). Fits a zone-blocking offense.
        if has_rzgd and pd.notna(RZGD_Q75) and rzgd >= RZGD_Q75:
            flags.append("RB-ZONE-SCHEME")
        # RB-GAP-SCHEME: rb_zone_gap_delta bottom quartile -- EPA/A much better on GAP/
        # power runs (e.g. Jonathan Taylor -0.26). Fits a gap/power-blocking offense.
        if has_rzgd and pd.notna(RZGD_Q25) and rzgd <= RZGD_Q25:
            flags.append("RB-GAP-SCHEME")
        return flags

    df["flags_list"] = df.apply(make_flags, axis=1)
    df["flags"] = df["flags_list"].apply(lambda xs: "; ".join(xs))

    # =================================================================
    # Per-position applicability: omit a model key from JSON if N/A for the position.
    #   WR/TE: route_eff, coverage_proof, rec_eff, separation, yac
    #   RB:    run_eff, rush_eff, yac
    #   WR/RB: explosive
    #   QB:    protection
    #   all:   market, value, proj, ceiling, spike, adv, coachspeak, oline, matchup
    # =================================================================
    def models_for(r):
        pos = r["pos"]
        m = {
            "market": float(r["market_pctl"]),
            "value": float(r["value_pctl"]),
            "proj": float(r["proj_pctl"]),
            "ceiling": float(r["ceiling_pctl"]),
            "spike": float(r["spike_pctl"]),
            "adv": float(r["adv_pctl"]),
            "coachspeak": float(r["coachspeak_pctl"]),
            "oline": float(r["oline_pctl"]),
            "matchup": float(r["matchup_pctl"]),
            "sis_value": float(r["sis_value_pctl"]),  # REAL SIS EPA/value (all positions)
            "boom": float(r["boom_pctl"]),            # REAL SIS Boom% rate (all positions)
        }
        if pos in ("WR", "TE"):
            m["route_eff"] = float(r["route_eff_pctl"])
            m["coverage_proof"] = float(r["coverage_proof_pctl"])
            m["rec_eff"] = float(r["rec_eff_pctl"])        # REAL Rec EPA/route primary
            m["separation"] = float(r["separation_pctl"])  # REAL NGS separation
            m["yac"] = float(r["yac_pctl"])                # REAL YAC over expected
            if pos == "WR":
                m["explosive"] = float(r["explosive_pctl"])  # deep-route share
        if pos == "RB":
            m["run_eff"] = float(r["run_eff_pctl"])
            m["rush_eff"] = float(r["rush_eff_pctl"])      # REAL Rush EPA/att primary
            m["yac"] = float(r["yac_pctl"])                # REAL YAC over expected
            m["explosive"] = float(r["explosive_pctl"])    # breakaway top-speed count
        if pos == "QB":
            m["protection"] = float(r["protection_pctl"])  # REAL EPA/dropback primary
        return m

    # =================================================================
    # Build tidy fusion_table.csv (one row per player, ALL columns)
    # =================================================================
    table_cols = [
        "name", "pos", "team", "adp", "merged_rank",
        "market_pctl", "value_pctl", "proj_pctl", "ceiling_pctl", "spike_pctl",
        "adv_pctl", "coachspeak_pctl",
        "route_eff_pctl", "coverage_proof_pctl", "run_eff_pctl",
        "rec_eff_pctl", "separation_pctl", "yac_pctl", "rush_eff_pctl",
        "explosive_pctl", "protection_pctl", "oline_pctl", "matchup_pctl",
        "sis_value_pctl", "boom_pctl",
        "consensus", "divergence", "_n_votes", "flags",
    ]
    table = df[table_cols].copy()
    # Blank the position-INAPPLICABLE efficiency cells for display (a QB has no
    # rec_eff; a WR has no rush_eff). These are left empty in the CSV (NOT neutral 50)
    # so a structural N/A is never mistaken for a real mid read. Applicable-but-missing
    # cells stay at the neutral 50 fill, per the missing-signal policy.
    for col, keep in APPLIES.items():
        table.loc[~table["pos"].isin(keep), col] = np.nan
    table = table.sort_values("merged_rank", na_position="last").reset_index(drop=True)
    table.rename(columns={"_n_votes": "n_votes"}, inplace=True)
    table.to_csv(P("fusion_table.csv"), index=False)

    # =================================================================
    # Build fusion.json (omit a model key if N/A for that position)
    # =================================================================
    players = []
    for _, r in df.sort_values("merged_rank", na_position="last").iterrows():
        players.append({
            "name": r["name"],
            "pos": r["pos"],
            "team": r["team"],
            "adp": None if pd.isna(r["adp"]) else round(float(r["adp"]), 2),
            "models": models_for(r),
            "consensus": float(r["consensus"]),
            "divergence": float(r["divergence"]),
            "flags": list(r["flags_list"]),
        })

    notes = (
        "REAL-DATA RE-RUN. The feature store now carries REAL play-by-play EPA + NGS "
        "tracking metrics (2025 full season). The QB efficiency vote `protection` is "
        "now built on REAL qb_epa_db (EPA/dropback, primary) + qb_cpoe + qb_anya + "
        "inverted qb_pressure_rate, REPLACING the old ANY/A-only sack%/ypa proxy. New "
        "WR/TE/RB votes were added on REAL data: rec_eff (rec_epa_route primary + "
        "route_yprr + fd_rr + adot_adj_ypt), separation (rec_separation, own vote), "
        "yac (rec_yacoe), rush_eff (rush_epa_att primary + ryoe_att), explosive "
        "(deep_route_sh WR / rb_topspeed RB). Legacy route_eff / coverage_proof / "
        "run_eff / oline / matchup and the original opinion votes are KEPT. Two flags "
        "were added: SEPARATION KING (elite REAL separation, cool market) and "
        "EFFICIENCY TRAP (loved by market, weak REAL EPA). THIS RE-RUN folds in REAL "
        "SIS DataHub signals (2025): two NEW votes -- sis_value (sis_epa, total EPA/value) "
        "and boom (sis_boom, Boom%/ceiling-game rate), each its own within-position vote -- "
        "plus rec_epa_per_tgt_man AND rec_epa_per_tgt_zone (REAL SIS EPA/target vs MAN / vs "
        "ZONE coverage) folded into the rec_eff vote; and FOUR NEW flags -- BOOM MERCHANT "
        "(SIS Boom% top-quartile, market <=55), FLOOR RISK (SIS Bust% top-quartile, market "
        ">=60), MAN-BEATER (rec_man_zone_delta top-quartile of non-null deltas, feasts vs "
        "MAN) and ZONE-BEATER (rec_man_zone_delta bottom-quartile, feasts vs ZONE). Each signal is its own "
        "within-position percentile shown side by side; consensus is the mean and "
        "divergence the std over ONLY the available REAL votes; nothing is collapsed "
        "or refit. A missing signal ABSTAINS (it is not scored 50 in any aggregate). "
        "CAVEAT: EPA/NGS are 2025 full-season values used as a TALENT PRIOR, not a "
        "guaranteed 2026 forecast; QB EPA (~42), RB rushing EPA (~75) and WR/TE "
        "receiving EPA (~170) cover only volume-qualified players, so lower-snap "
        "players legitimately abstain on those votes."
    )

    meta = {
        "generated": "2026-06-19",
        "philosophy": (
            "Model fusion, not overfitting. Each model/signal's read is kept as a "
            "within-position percentile (0-100, higher=better). consensus (mean) and "
            "divergence (std) are display-only and computed over ONLY the available "
            "real votes; the per-model columns are the product. Divergence is the signal. "
            "A missing signal ABSTAINS (never silently 50 in any aggregate)."
        ),
        "notes": notes,
        "weights_note": weights_note,
        "source": (meta_in.get("source") if isinstance(meta_in, dict) else None) or "features.json",
        "n_players": int(n_board),
        "positions": df["pos"].value_counts().to_dict(),
        "percentile_basis": "within position (QB/RB/WR/TE), rank-based midpoint",
        "missing_input_policy": (
            "Players missing a signal ABSTAIN on that vote: excluded from that signal's "
            "coverage count and from their own consensus/divergence (which use only the "
            "available real votes). The displayed percentile column is neutral-filled to "
            "50 only so the column is NaN-free; that 50 never enters an aggregate. "
            "Composite REAL votes (protection/rec_eff/rush_eff) abstain only when ALL "
            "their components are null; a null component abstains inside the mean. "
            "Efficiency / EPA / separation flags require a real read for the position. "
            "The NEW SIS votes (sis_value<-sis_epa, boom<-sis_boom) abstain when their SIS "
            "column is null; BOOM MERCHANT / FLOOR RISK require a real sis_boom / sis_bust "
            "value for the position (null SIS = no flag, never 50/0). "
            "CSV leaves position-inapplicable cells blank (not 50)."
        ),
        "efficiency_data_window": (
            "REAL EPA + NGS, 2025 FULL SEASON, used as a TALENT PRIOR not a 2026 "
            "forecast: protection<-qb_epa_db/cpoe/anya/pressure_rate; rec_eff<-"
            "rec_epa_route/route_yprr/fd_rr/adot_adj_ypt; separation<-rec_separation; "
            "yac<-rec_yacoe; rush_eff<-rush_epa_att/ryoe_att; explosive<-deep_route_sh"
            "(WR)/rb_topspeed(RB). NEW REAL SIS DataHub (2025): sis_value<-sis_epa; "
            "boom<-sis_boom (Boom%); FLOOR RISK uses sis_bust (Bust%); rec_eff also "
            "folds rec_epa_per_tgt_man (EPA/tgt vs MAN) + rec_epa_per_tgt_zone (EPA/tgt vs "
            "ZONE); MAN-BEATER/ZONE-BEATER flags use rec_man_zone_delta (EPA/tgt vs MAN - vs "
            "ZONE). Kept proxies: route_eff(yprr "
            "man/zone), coverage_proof(man-zone), run_eff(zone/gap success & stuff%)."
        ),
        "models": {
            "market": "adp inverted (lower ADP better)",
            "value": "merged_rank inverted (lower rank better)",
            "proj": "proj_pg (higher better)",
            "ceiling": "0.75*p95_pctl + 0.25*spike_pctl (magnitude-led; higher better)",
            "spike": "spike-week boom-frequency percentile (displayed separately)",
            "adv": "adv_pct advance-rate (higher better)",
            "coachspeak": "qual_signal/qual_score if present else abstain (higher better)",
            "route_eff": "WR/TE: max(yprr_man, yprr_zone) best-of route efficiency (legacy proxy, kept)",
            "coverage_proof": ("WR/TE: 100 - scaled|man_zone_delta| blended 0.8/0.2 with "
                               "man_route_sh context (legacy proxy, kept)"),
            "run_eff": "RB: zone_run_sh-weighted(zone_succ, gap_succ) - stuff_pct (legacy proxy, kept)",
            "protection": ("QB: REAL composite -- qb_epa_db (EPA/dropback, PRIMARY) + "
                           "qb_cpoe + qb_anya + inverted qb_pressure_rate. Replaces the "
                           "old ANY/A-only sack%/ypa proxy."),
            "rec_eff": ("WR/TE: REAL composite -- rec_epa_route (Rec EPA/route, PRIMARY) "
                        "+ rec_epa_per_tgt_man (REAL SIS EPA/target vs MAN coverage) "
                        "+ rec_epa_per_tgt_zone (REAL SIS EPA/target vs ZONE coverage) + route_yprr "
                        "+ fd_rr (first downs/route = chain-mover) + adot_adj_ypt."),
            "separation": "WR/TE: REAL rec_separation (NGS avg separation = getting open), own vote.",
            "yac": "WR/TE/RB: REAL rec_yacoe (YAC over expected = after the catch).",
            "rush_eff": ("RB: REAL composite -- rush_epa_att (Rush EPA/att, PRIMARY) + "
                         "ryoe_att (rush yds over expected / att)."),
            "explosive": "WR: deep_route_sh (deep-route share) | RB: rb_topspeed (breakaway top-speed count).",
            "oline": "ol_pass_winrate (QB/WR/TE) | ol_run_winrate (RB) [team context]",
            "matchup": ("season SoS from OUR 2026 defense.json: mean opp pass_cov_pctl "
                        "(QB/WR/TE) | mean opp run_def_pctl (RB) over the schedule; "
                        "softer schedule = higher (better matchup). Rewired off ffdataroma tiers."),
            "sis_value": "ALL: REAL SIS sis_epa (total EPA / value); own within-position vote (higher better).",
            "boom": "ALL: REAL SIS sis_boom (Boom% = ceiling-game rate); own within-position vote (higher better).",
        },
        "model_applicability": {
            "all": ["market", "value", "proj", "ceiling", "spike", "adv",
                    "coachspeak", "oline", "matchup", "sis_value", "boom"],
            "WR_TE_only": ["route_eff", "coverage_proof", "rec_eff", "separation"],
            "WR_TE_RB": ["yac"],
            "RB_only": ["run_eff", "rush_eff"],
            "WR_RB": ["explosive"],
            "QB_only": ["protection"],
        },
        "coverage": coverage,
        "flag_definitions": {
            "_coverage_gate": ("Original flags require a real ceiling read (p95 present). "
                               "Efficiency / EPA / separation flags require a real read for "
                               "the position."),
            "MARKET FADE": "max(ceiling,adv) >= 55 and (max(ceiling,adv) - market) >= 8 (efficiency/ceiling >> market)",
            "MARKET DARLING": "market >= 60 and (market - mean(ceiling,adv)) >= 20 (market >> efficiency+adv)",
            "CONSENSUS STUD": ">=5 real core votes and ALL of them >= 75 (everything high)",
            "POLARIZING": "divergence > 22 (high disagreement)",
            "EFFICIENCY EDGE": "pos efficiency (best real read) >= pos 75th pct but 30 <= market <= 70",
            "EMPTY CALORIES": "max(market,ceiling) >= 65 but pos efficiency (best real read) <= pos 25th pct",
            "SEPARATION KING": ("WR/TE: REAL rec_separation pctl >= pos 75th pct AND market <= 55 "
                                "(elite get-open profile the market isn't paying for)"),
            "EFFICIENCY TRAP": ("market >= 60 but REAL EPA read (rec_epa/route for WR/TE, rush_epa/att "
                                "for RB, qb_epa/dropback for QB) <= pos 25th pct (loved by market, weak REAL EPA)"),
            "BOOM MERCHANT": ("REAL SIS Boom% (boom vote pctl) >= pos 75th pct AND market <= 55 "
                              "(high ceiling-game propensity the market isn't paying up for)"),
            "FLOOR RISK": ("REAL SIS Bust% (raw rate) >= pos 75th pct AND market >= 60 "
                           "(market darling with a quietly high floor-game / dud rate)"),
            "MAN-BEATER": ("REAL SIS rec_man_zone_delta (EPA/tgt vs MAN - vs ZONE) >= 75th pct "
                           "of non-null deltas (WR/TE talent/matchup descriptor: feasts vs MAN "
                           "coverage; pairs with a man-heavy opponent)"),
            "ZONE-BEATER": ("REAL SIS rec_man_zone_delta <= 25th pct of non-null deltas (WR/TE "
                            "talent/matchup descriptor: feasts vs ZONE coverage; pairs with a "
                            "zone-heavy opponent)"),
            "QB-MAN-BEATER": ("REAL SIS qb_man_zone_delta (per-att EPA vs MAN - vs ZONE) >= 75th pct "
                              "of non-null QB deltas (QB throws much better vs MAN; pairs with a "
                              "man-heavy opponent)"),
            "QB-ZONE-BEATER": ("REAL SIS qb_man_zone_delta <= 25th pct of non-null QB deltas (QB "
                               "throws much better vs ZONE; pairs with a zone-heavy opponent)"),
            "RB-ZONE-SCHEME": ("REAL SIS rb_zone_gap_delta (EPA/A zone runs - gap runs) >= 75th pct "
                               "of non-null RB deltas (RB is more productive on ZONE-scheme runs; "
                               "fits a zone-blocking offense)"),
            "RB-GAP-SCHEME": ("REAL SIS rb_zone_gap_delta <= 25th pct of non-null RB deltas (RB is "
                              "more productive on GAP/power runs; fits a gap-blocking offense)"),
        },
    }

    core.safe_json_dump({"meta": meta, "players": players}, P("fusion.json"), indent=2)

    # =================================================================
    # VERIFICATION (run + PRINT)
    # =================================================================
    print("=" * 84)
    print("FUSION VERIFICATION  (REAL EPA + NGS re-run on enriched feature store)")
    print("=" * 84)
    print("feature-store players (spine) : %d" % n_board)
    print("fusion_table rows             : %d" % len(table))
    print("rows match board?             : %s" % (len(table) == n_board))
    if not corr_found:
        print("metric-correlations file      : NOT FOUND -> votes weighted EQUALLY (noted in meta.weights_note)")
    else:
        print("metric-correlations file      : found (%d pos) -> used in weights_note" % len(corr_notes))

    pctl_cols = [
        "market_pctl", "value_pctl", "proj_pctl", "ceiling_pctl", "spike_pctl",
        "adv_pctl", "coachspeak_pctl", "route_eff_pctl", "coverage_proof_pctl",
        "run_eff_pctl", "rec_eff_pctl", "separation_pctl", "yac_pctl",
        "rush_eff_pctl", "explosive_pctl", "protection_pctl", "oline_pctl", "matchup_pctl",
        "sis_value_pctl", "boom_pctl",
    ]
    # Each position-specific signal leaves cross-position cells BLANK in the CSV. The
    # guarantee is: no NaN WITHIN the positions a signal applies to.
    nan_in_scope = {}
    structural_na = {}
    for c in pctl_cols:
        keep = APPLIES.get(c, {"QB", "RB", "WR", "TE"})
        in_scope = table["pos"].isin(keep)
        nan_in_scope[c] = int(table.loc[in_scope, c].isna().sum())
        structural_na[c] = int(table.loc[~in_scope, c].isna().sum())
    total_nan = sum(nan_in_scope.values())
    print("NaN in any percentile (in-scope): %d  <- must be 0" % total_nan)
    if total_nan:
        print("   ", {k: v for k, v in nan_in_scope.items() if v})
    print("structural cross-pos N/A cells  : %d (blank-by-design)" % sum(structural_na.values()))
    print("consensus NaN                 : %d" % int(table["consensus"].isna().sum()))
    print("divergence NaN                : %d" % int(table["divergence"].isna().sum()))
    vals = table[pctl_cols].values
    vmin = np.nanmin(vals)
    vmax = np.nanmax(vals)
    print("all percentiles within [0,100]: %s  (min=%.2f, max=%.2f)" % (bool(vmin >= 0 and vmax <= 100), vmin, vmax))

    print("\n--- coverage (real non-null votes, before neutral fill) ---")
    pos_n = coverage["_pos_counts"]
    denom = {
        "route_eff_WRTE": pos_n.get("WR", 0) + pos_n.get("TE", 0),
        "coverage_proof_WRTE": pos_n.get("WR", 0) + pos_n.get("TE", 0),
        "rec_eff_WRTE": pos_n.get("WR", 0) + pos_n.get("TE", 0),
        "separation_WRTE": pos_n.get("WR", 0) + pos_n.get("TE", 0),
        "yac_WRTE_RB": pos_n.get("WR", 0) + pos_n.get("TE", 0) + pos_n.get("RB", 0),
        "run_eff_RB": pos_n.get("RB", 0),
        "rush_eff_RB": pos_n.get("RB", 0),
        "explosive_WR_RB": pos_n.get("WR", 0) + pos_n.get("RB", 0),
        "protection_EPA_QB": pos_n.get("QB", 0),
    }
    for k, v in coverage.items():
        if k.startswith("_"):
            continue
        d = denom.get(k, n_board)
        print("  %-24s: %d/%d" % (k, v, d))
    print("  -- REAL-vote components --")
    for k, v in coverage["_components"].items():
        print("      %-22s: %d" % (k, v))

    show_cols = pctl_cols + ["consensus", "divergence", "n_votes", "flags"]

    def show_player(label, name):
        row = table[table["name"] == name]
        print("\n### %s: %s" % (label, name))
        if row.empty:
            print("   (not found)")
            return
        r = row.iloc[0]
        adp_str = "NA" if pd.isna(r["adp"]) else ("%.1f" % r["adp"])
        print("   pos=%s team=%s adp=%s merged_rank=%s" % (r["pos"], r["team"], adp_str, r["merged_rank"]))
        for c in show_cols:
            v = r[c]
            v = "NA" if (isinstance(v, float) and pd.isna(v)) else v
            print("   %-20s: %s" % (c, v))

    print("\n" + "=" * 84)
    print("ARCHETYPES  (full percentile rows so the divergence is visible)")
    print("=" * 84)

    # (a) a REAL-EPA standout the market UNDERRATES: real-EPA read top-quartile, biggest
    #     (real_epa - market) positive gap.
    cand = df[df["real_epa_read"].notna()].copy()
    cand["gap"] = cand["real_epa_read"] - cand["market_pctl"]
    cand = cand[cand["real_epa_read"] >= cand["_epa_q75"]]
    if not cand.empty:
        a_name = cand.sort_values("gap", ascending=False).iloc[0]["name"]
    else:
        a_name = df.sort_values("real_epa_read", ascending=False).iloc[0]["name"]
    show_player("(a) REAL-EPA STANDOUT the market underrates", a_name)

    # (b) an EFFICIENCY TRAP (high market, weak real EPA) -- biggest (market - real_epa).
    trap = df[df["flags"].str.contains("EFFICIENCY TRAP")].copy()
    if not trap.empty:
        trap["trap_gap"] = trap["market_pctl"] - trap["real_epa_read"]
        b_name = trap.sort_values("trap_gap", ascending=False).iloc[0]["name"]
        show_player("(b) EFFICIENCY TRAP (high market, weak REAL EPA)", b_name)
    else:
        print("\n### (b) EFFICIENCY TRAP: none flagged")

    # (c) a SEPARATION KING.


if __name__ == "__main__":
    main()
