#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_team_ceiling.py  ->  team_ceiling.json
=============================================================================
TEAM-CEILING SCORE: probability that an OFFENSE has a CEILING SEASON
(dramatically overperforms its projection), NOT its expected value.

This is a STANDALONE FOUNDATION LAYER for a stacking-oriented, pick-#-specific
draft board -- the "which offenses to concentrate on" read. It is deliberately
NOT wired into the rankings/pipeline. Nothing here mutates other repo files.

------------------------------------------------------------------------------
WHAT "CEILING" MEANS HERE (and why it is not EV)
------------------------------------------------------------------------------
A projection is a point estimate (expected value). A CEILING SEASON is the fat
right tail: the offense not only scores a lot, it beats its own preseason number
by a wide margin. Ceiling is about VARIANCE + UPSIDE, so the score rewards drivers
that (a) raise the mean scoring environment AND (b) inject variance / a spike-prone
target tree, and it deliberately does NOT just re-rank teams by expected points.

The theory of a ceiling season (from established fantasy/football drivers):
  * implied-total / win-total sits high or JUMPED vs prior  -> scoring ceiling
  * pace up (more plays)                                     -> more scoring reps
  * pass-rate up (passing is higher-variance than rushing)  -> fatter boom tail
  * new-OC / scheme UPGRADE (motion / vertical / pass-catch) -> variance injection
  * concentrated target tree (heavy vacated targets -> 1 alpha) -> spike-prone
  * young/ascending or returning franchise QB               -> carries the tail
  * OL improvement                                          -> whole-offense lift
  * weak OWN defense -> negative game script / shootout volume (trail + pass a lot)

------------------------------------------------------------------------------
DRIVERS & WEIGHTING RATIONALE  (transparent, per-team breakdown retained)
------------------------------------------------------------------------------
Every driver is normalized to [0,1] on its own scale, then multiplied by a weight.
Weights encode how strongly each driver has historically distinguished ceiling
offenses. They sum to 1.00 across the "core" block; two variance drivers
(scheme-upgrade, concentrated-tree) are additive KICKERS on top, because a real
ceiling season usually needs BOTH a good environment AND a variance catalyst.

  CORE ENVIRONMENT BLOCK (sums to 1.00 of the base) -- raises the mean:
    env_quality   0.30  env_idx & off_q (implied offensive strength; the ceiling
                        cannot exist without a good scoring environment)
    win_total     0.22  Vegas win total = market ceiling proxy; high totals ->
                        more leading/blowout scripts and sustained scoring
    pace          0.16  plays_pg / pace_pctl: more plays = more scoring reps =
                        fatter upside tail
    pass_rate     0.16  passing is higher-variance & higher-ceiling than rushing
    qb_ascend     0.16  young-ascending or returning franchise QB carries the tail

  VARIANCE KICKERS (added on top; these are what turn a good offense into a
  boom-prone one -- the reason ceiling != EV):
    scheme_up    +0.14  NEW OC whose install dials UP motion/vertical/pass-catch
                        (net-positive scheme_dials). Continuity or a neutral/negative
                        install earns nothing. Scheme change = variance.
    conc_tree    +0.12  concentrated target tree: heavy vacated-target % funneling
                        to one alpha -> a spike-prone tree (ceiling weeks come from
                        one player detonating, which stacks well)
    ol_improve   +0.06  OL improvement (protection/run-block adds) lifts the whole
                        offense's ceiling
    shootout     +0.08  weak OWN defense -> negative game script -> more trailing
                        pass volume & shootouts (offense on the field more)

  base_core in [0,1]; kickers add up to +0.40. raw = base_core + kickers.
  ceiling_score = 100 * squash(raw), where squash is a gentle logistic centered
  so a league-average environment with no catalysts lands near the middle of the
  pack and the tails spread. Score is reported 0-100 and read as a RELATIVE
  probability-of-ceiling ordering, not a calibrated absolute probability.

------------------------------------------------------------------------------
TIERS
------------------------------------------------------------------------------
  ELITE  ceiling  : top ~6 offenses            (concentrate stacks here)
  HIGH   ceiling  : next ~8
  MID    ceiling  : middle ~12
  LOW    ceiling  : bottom ~6 (fade for ceiling-seeking stacks)
Cut points are rank-based so the tiering is stable regardless of score compression.

------------------------------------------------------------------------------
VALIDATION  (see validate_retrodiction(); results printed at run time)
------------------------------------------------------------------------------
HONEST LIMITATION: the repo does NOT contain a team-season PRESEASON-PROJECTION
for any PAST season (no 2024 or 2025 preseason Vegas win totals / implied totals /
projected team points on disk). Therefore a TRUE "overperformed-its-projection"
retrodiction is NOT POSSIBLE from repo data -- that check is UNVALIDATED pending a
historical projection feed.

WHAT WE CAN DO (leak-free, convergent-validity only): the repo DOES contain two
seasons of REALIZED actuals -- NFL-master/FP_ADVANCED/{passing,receiving,rushing}_{2024,2025}.csv
(per-player FP, Team, Season) -- which aggregate to team-season offensive fantasy
totals. We test whether the STABLE, structural pieces of the ceiling logic (env
quality, win total, pace, pass-rate -- the pieces that describe a high-output
offensive environment) rank-correlate with which offenses actually FINISHED as
top-scoring offenses in 2024-2025. This tests "does the design point at genuinely
high-output offensive environments?" It does NOT test "does it predict beating a
projection" -- that is the part we cannot validate here. Small-sample caveats and
the projection gap are reported explicitly.
"""

import csv
import json
import math
import os
import re
import statistics
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))

TEAMS = [
    "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE", "DAL", "DEN",
    "DET", "GB", "HOU", "IND", "JAX", "KC", "LAC", "LAR", "LV", "MIA",
    "MIN", "NE", "NO", "NYG", "NYJ", "PHI", "PIT", "SEA", "SF", "TB",
    "TEN", "WAS",
]

# FP_ADVANCED / NFL Pro use some legacy team codes. Map them to our 32 canon.
CODE_FIX = {
    "ARZ": "ARI", "BLT": "BAL", "CLV": "CLE", "HST": "HOU",
    "LA": "LAR", "LAR": "LAR", "SL": "LAR", "OAK": "LV", "SD": "LAC",
    "WSH": "WAS", "JAC": "JAX", "GNB": "GB", "KAN": "KC", "NWE": "NE",
    "NOR": "NO", "SFO": "SF", "TAM": "TB",
}


# ----------------------------------------------------------------------------
# small helpers
# ----------------------------------------------------------------------------
def clamp01(x):
    return max(0.0, min(1.0, x))


def norm(x, lo, hi):
    """Linear normalize x into [0,1] given a [lo,hi] reference band."""
    if hi == lo:
        return 0.5
    return clamp01((x - lo) / (hi - lo))


def load_json(rel):
    with open(os.path.join(HERE, rel), encoding="utf-8") as f:
        return json.load(f)


# ----------------------------------------------------------------------------
# QB-ascending / OL-improvement text signals (transparent keyword flags derived
# from offense_profile 'outlook' + 'adds'/'losses'; every hit is auditable).
# A ceiling season leans on an upside QB and better protection; we read those
# from the repo's own prose rather than inventing a rating.
# ----------------------------------------------------------------------------
# FIX 2 — qb_ascend matcher hardening (two false-positive classes corrected):
#
# (a) Name-collision: CAR's outlook "Bryce Young taking a step" contains the
#     surname "young" — the old bare-substring match fired incorrectly.
#     Fix: "young" is now matched only as a standalone word via \byoung\b
#     AND we additionally skip the hit when the surrounding context contains a
#     capitalized First Last proper-name pair (e.g. "Bryce Young").  The other
#     ascension phrases ("2nd-year", "ascending", etc.) are genuine and unambiguous.
#
# (b) Returning-vet conflation: KC's outlook "Mahomes expected back" / "returns
#     as OC" hit "returns" and "expected back", giving a full ascend credit for a
#     healthy veteran — that credit belongs to injury-return context, not
#     breakout/ascension context.  Split the flag list:
#       ASCEND_POS  = young-ascending / breakout phrases  → full +0.34 weight
#       RETURN_POS  = injury-return phrases               → half  +0.17 weight
#     Documented: qb_ascend (full) vs qb_return (half, injury-return only).

ASCEND_POS = [
    "2nd-year", "second-year", "ascending", "rookie qb",
    "development", "takes a step", "step forward", "franchise qb",
]
# "young" is now matched word-boundary-only (no proper-name context);
# matched separately in qb_ascend_score().

RETURN_POS = [
    "returns", "expected back",
]

ASCEND_NEG = ["age", "aging", "recovering", "achilles", "acl", "unsettled",
              "open qb competition", "wide-open qb", "competition", "timeline"]

OL_POS = ["rebuilt line", "rebuilt o-line", "upgraded", "upgraded line",
          "o-line", "interior line", "line help", "tackle help",
          "protecting", "protection", "rebuilt interior"]

OL_ADD_KEYS = [" (g,", " (og,", " (c,", " (ot,", " (ol,", " (t,",
               " (g)", " (og)", " (c)", " (ot)"]


def _has_proper_name_young(raw_txt):
    """Return True when 'Young' appears as a surname in a Firstname Young pair
    (e.g. 'Bryce Young'), indicating a player name, not a QB-age descriptor.
    Case-insensitive match of the raw text."""
    return bool(re.search(r'\b[A-Z][a-z]+\s+Young\b', raw_txt))


def qb_ascend_score(prof):
    """0..1 upside-QB tail signal from outlook text + known ascenders.

    FIX 2 corrections applied:
    (a) 'young' matched only as a word-boundary token AND only when NOT inside a
        capitalized Firstname Young proper-name pair (name-collision fix for CAR).
    (b) RETURN_POS phrases (returns / expected back) are injury-return signals,
        not breakout/ascension signals → half weight (+0.17) to avoid over-crediting
        healthy veterans like Mahomes (qb_return flag, KC).
    """
    raw = prof.get("outlook", "") + " " + prof.get("scheme_note", "")
    txt = raw.lower()
    s = 0.0
    for kw in ASCEND_POS:
        if kw in txt:
            s += 0.34
    # (a) "young" as QB-age descriptor — word-boundary only, skip proper-name hits
    if re.search(r'\byoung\b', txt) and not _has_proper_name_young(raw):
        s += 0.34
    # (b) injury-return phrases get half weight (qb_return path)
    for kw in RETURN_POS:
        if kw in txt:
            s += 0.17  # half of 0.34 — injury-return, not breakout ascension
    for kw in ASCEND_NEG:
        if kw in txt:
            s -= 0.30
    return clamp01(0.35 + s)  # neutral baseline 0.35, prose moves it


def ol_improve_score(prof):
    """0..1 OL-improvement signal from outlook text + OL-position adds."""
    txt = prof.get("outlook", "").lower()
    s = 0.0
    for kw in OL_POS:
        if kw in txt:
            s += 0.25
    adds = " ".join(prof.get("adds", [])).lower()
    for k in OL_ADD_KEYS:
        if k in adds:
            s += 0.18
    return clamp01(s)


# FIX 1 — TITLE-ONLY CHURN BLOCKLIST (FUNNELS_2026_TEAM_NOTES.md §Comprehensive OC read):
# "Continuity — ignore the OC-title churn (no scheme change): LAR (McVay calls;
# Scheelhaase internal promo), KC (Reid calls; Bieniemy is support/reunion),
# BUF (Joe Brady, now HC, still calls), DEN (Sean Payton calls; Webb internal promo)."
# These teams have oc_new=True in coordinator_scheme_2026.json (a new coordinator
# title was assigned) but the ACTUAL PLAY-CALLER did not change — so there is no
# real scheme change, and the +0.14 variance kicker MUST NOT fire.
# The blocklist is sourced directly from FUNNELS_2026_TEAM_NOTES.md, not inferred.
_TITLE_ONLY_CHURN_TEAMS = frozenset({"LAR", "KC", "BUF"})
# DEN is NOT blocked: Davis Webb was explicitly handed play-calling duties by Payton
# (offense_profile has playcaller='Davis Webb (OC, new caller; Payton handed it off)'
# and scheme_dials={vertical:1, passcatch:1, ...}), so it is a real scheme change.


def scheme_up_score(prof, oc_new, team=None):
    """
    0..1 scheme-UPGRADE variance kicker. Only a NEW OC whose install dials UP
    motion / vertical / pass-catching earns credit; continuity or a neutral /
    run-heavy / possession install earns ~0. This is the 'variance injection'
    piece -- new scheme = wider outcome distribution.

    FIX 1 — REAL-SCHEME-CHANGE GATE (FUNNELS_2026_TEAM_NOTES.md §Comprehensive OC read):
    "Continuity — ignore the OC-title churn (no scheme change): LAR (McVay calls;
    Scheelhaase internal promo), KC (Reid calls; Bieniemy is support/reunion),
    BUF (Joe Brady, now HC, still calls)."
    These teams appear as oc_new=True in coordinator_scheme_2026.json because a new
    coordinator TITLE was filled, but the actual PLAY-CALLER is unchanged — the
    +0.14 scheme_upgrade kicker MUST NOT fire for them.
    Blocklist is sourced from FUNNELS_2026_TEAM_NOTES.md, cited above.
    All other oc_new=True teams (ARI, ATL, BAL, CAR, CHI, CLE, DEN, DET, LAC,
    LV, MIA, NYG, NYJ, PHI, PIT, SEA, TB, TEN, WAS) have a genuine new play-caller
    and are unaffected.
    """
    if not oc_new:
        return 0.0
    # GATE: block title-only churn teams (no real scheme change).
    if team in _TITLE_ONLY_CHURN_TEAMS:
        return 0.0
    dials = prof.get("scheme_dials")
    if not dials:
        # New playcaller but no explicit upside dials catalogued -> mild generic bump.
        return 0.30
    # motion + vertical + passcatch are the ceiling-positive dials; scramble is
    # QB-rush variance (small positive). Range of the sum is roughly [-3, +4].
    raw = (dials.get("motion", 0) + dials.get("vertical", 0)
           + dials.get("passcatch", 0) + 0.5 * dials.get("scramble", 0))
    return norm(raw, -1.0, 3.5)


# ----------------------------------------------------------------------------
# core builder
# ----------------------------------------------------------------------------
def build_scores():
    off = load_json("offense_profile.json")
    env = load_json("boom/team_env.json")
    coord = load_json("coordinator_scheme_2026.json")["teams"]
    dprof = load_json("boom/defensive_profile.json")

    # Reference bands for normalization, computed from the 32-team distribution
    # so the score is relative to THIS season's league (not magic constants).
    env_idx_vals = [env[t]["env_idx"] for t in TEAMS]
    offq_vals = [env[t]["off_q"] for t in TEAMS]
    win_vals = [env[t]["win_total"] for t in TEAMS]
    pace_vals = [env[t]["pace_pctl"] for t in TEAMS]
    plays_vals = [env[t]["plays_pg"] for t in TEAMS]
    pass_vals = [off[t].get("pass_rate", 50.0) for t in TEAMS]
    vac_vals = [off[t].get("vacated_tgt_pct", 0.0) for t in TEAMS]

    def band(vals):
        return (min(vals), max(vals))

    b_env, b_offq = band(env_idx_vals), band(offq_vals)
    b_win, b_pace = band(win_vals), band(pace_vals)
    b_plays, b_pass = band(plays_vals), band(pass_vals)
    b_vac = band(vac_vals)

    # weights (documented in the module docstring)
    W_ENV = 0.30
    W_WIN = 0.22
    W_PACE = 0.16
    W_PASS = 0.16
    W_QB = 0.16
    K_SCHEME = 0.14
    K_TREE = 0.12
    K_OL = 0.06
    K_SHOOT = 0.08

    out = {}
    for t in TEAMS:
        prof = off[t]
        e = env[t]
        c = coord.get(t, {})
        d = dprof.get(t, {})

        oc_new = bool(c.get("oc_new", False))

        # --- core environment drivers (each 0..1) ---
        env_q = 0.6 * norm(e["env_idx"], *b_env) + 0.4 * norm(e["off_q"], *b_offq)
        win_q = norm(e["win_total"], *b_win)
        pace_q = 0.5 * norm(e["pace_pctl"], *b_pace) + 0.5 * norm(e["plays_pg"], *b_plays)
        pass_q = norm(prof.get("pass_rate", 50.0), *b_pass)
        qb_q = qb_ascend_score(prof)

        base_core = (W_ENV * env_q + W_WIN * win_q + W_PACE * pace_q
                     + W_PASS * pass_q + W_QB * qb_q)

        # --- variance kickers (0..K each) ---
        sch = scheme_up_score(prof, oc_new, team=t)
        tree = norm(prof.get("vacated_tgt_pct", 0.0), *b_vac)
        ol = ol_improve_score(prof)
        # weak OWN pass defense -> shootout / negative script volume.
        pass_cov_pctl = d.get("eng2026", {}).get("pass_cov_pctl", 50.0)
        shoot = clamp01((100.0 - pass_cov_pctl) / 100.0)

        k_scheme = K_SCHEME * sch
        k_tree = K_TREE * tree
        k_ol = K_OL * ol
        k_shoot = K_SHOOT * shoot

        raw = base_core + k_scheme + k_tree + k_ol + k_shoot

        # gentle logistic squash centered near the middle of the achievable
        # range (base_core ~0.5 + ~0.20 of kickers). Spreads the tails, keeps
        # the score a relative probability-of-ceiling read.
        score = 100.0 / (1.0 + math.exp(-6.0 * (raw - 0.62)))

        # ---- driver breakdown (which factors flag this team) ----
        contrib = {
            "env_quality": round(W_ENV * env_q, 4),
            "win_total": round(W_WIN * win_q, 4),
            "pace": round(W_PACE * pace_q, 4),
            "pass_rate": round(W_PASS * pass_q, 4),
            "qb_ascend": round(W_QB * qb_q, 4),
            "scheme_upgrade": round(k_scheme, 4),
            "concentrated_tree": round(k_tree, 4),
            "ol_improve": round(k_ol, 4),
            "shootout_script": round(k_shoot, 4),
        }
        # human-readable flags: any driver contributing meaningfully.
        flags = []
        if env_q >= 0.66:
            flags.append("elite scoring environment")
        if win_q >= 0.66:
            flags.append(f"high win total ({e['win_total']})")
        if pace_q >= 0.62:
            flags.append(f"up-tempo ({e['plays_pg']} plays/g)")
        if pass_q >= 0.62:
            flags.append(f"pass-heavy ({prof.get('pass_rate')}%)")
        if qb_q >= 0.60:
            flags.append("ascending/returning QB")
        elif qb_q <= 0.20:
            flags.append("QB uncertainty (caps ceiling)")
        if sch >= 0.45:
            flags.append("new-OC scheme upgrade")
        if tree >= 0.60:
            flags.append(f"concentrated tree (vacated tgt {prof.get('vacated_tgt_pct')}%)")
        if ol >= 0.40:
            flags.append("OL improvement")
        if shoot >= 0.62:
            flags.append("weak own pass-D -> shootout volume")

        out[t] = {
            "ceiling_score": round(score, 1),
            "raw": round(raw, 4),
            "base_core": round(base_core, 4),
            "drivers": contrib,
            "flags": flags,
            "inputs": {
                "env_idx": e["env_idx"], "off_q": e["off_q"],
                "win_total": e["win_total"], "pace_pctl": e["pace_pctl"],
                "plays_pg": e["plays_pg"], "pass_rate": prof.get("pass_rate"),
                "vacated_tgt_pct": prof.get("vacated_tgt_pct"),
                "oc_new": oc_new, "own_pass_cov_pctl": pass_cov_pctl,
                "playcaller": prof.get("playcaller", "(continuity)"),
            },
        }

    # ---- rank-based tiers ----
    ranked = sorted(out, key=lambda t: -out[t]["ceiling_score"])
    for i, t in enumerate(ranked):
        out[t]["rank"] = i + 1
        if i < 6:
            tier = "ELITE"
        elif i < 14:
            tier = "HIGH"
        elif i < 26:
            tier = "MID"
        else:
            tier = "LOW"
        out[t]["tier"] = tier

    return out, ranked


# ----------------------------------------------------------------------------
# VALIDATION  -- leak-free convergent check against 2024/2025 realized actuals.
# (No preseason projection exists on disk for past seasons -> true overperformance
#  retrodiction is UNVALIDATED; this only tests environment-vs-realized-output.)
# ----------------------------------------------------------------------------
def _load_fp_advanced_team_totals(year):
    """Aggregate NFL-master/FP_ADVANCED/{kind}_{year}.csv -> {team: total FP}.
    Drops multi-team ('A, B') traded-player rows to avoid double counting."""
    totals = defaultdict(float)
    ok = True
    for kind in ("passing", "receiving", "rushing"):
        path = os.path.join(HERE, "NFL-master", "FP_ADVANCED", f"{kind}_{year}.csv")
        if not os.path.exists(path):
            ok = False
            continue
        with open(path, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                team = (row.get("Team") or "").strip()
                if not team or "," in team:      # skip blank + multi-team rows
                    continue
                team = CODE_FIX.get(team, team)
                if team not in TEAMS:
                    continue
                try:
                    fp = float((row.get("FP") or "0").strip() or 0.0)
                except ValueError:
                    fp = 0.0
                totals[team] += fp
    return (dict(totals) if ok else None)


def _spearman(a, b):
    """Spearman rank correlation between two equal-length lists."""
    n = len(a)
    if n < 3:
        return None

    def ranks(x):
        order = sorted(range(n), key=lambda i: x[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and x[order[j + 1]] == x[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r

    ra, rb = ranks(a), ranks(b)
    ma, mb = statistics.mean(ra), statistics.mean(rb)
    num = sum((ra[i] - ma) * (rb[i] - mb) for i in range(n))
    da = math.sqrt(sum((ra[i] - ma) ** 2 for i in range(n)))
    db = math.sqrt(sum((rb[i] - mb) ** 2 for i in range(n)))
    if da == 0 or db == 0:
        return None
    return num / (da * db)


def validate_retrodiction(scores):
    """
    Convergent-validity check (LEAK-FREE by construction, but NOT an
    overperformance test -- see caveats). We correlate the STRUCTURAL /
    environment component of the current design against which offenses
    actually finished as top scoring offenses in 2024 and 2025.

    Structural proxy = base_core minus the QB-text term (env+win+pace+pass only),
    i.e. the pieces that describe a durable high-output environment and are least
    dependent on this-year-specific prose. We do NOT use 2026 kickers here.
    """
    report = {
        "status": None,
        "note": "",
        "caveats": [],
        "seasons": {},
    }

    # Structural proxy per team (env quality + win + pace + pass; QB/kickers excluded)
    struct = {}
    for t in TEAMS:
        dr = scores[t]["drivers"]
        struct[t] = dr["env_quality"] + dr["win_total"] + dr["pace"] + dr["pass_rate"]

    any_year = False
    for year in ("2024", "2025"):
        actuals = _load_fp_advanced_team_totals(year)
        if not actuals:
            report["seasons"][year] = {"available": False}
            continue
        any_year = True
        teams_common = [t for t in TEAMS if t in actuals]
        xs = [struct[t] for t in teams_common]
        ys = [actuals[t] for t in teams_common]
        rho = _spearman(xs, ys)
        # Cleaner, LESS-CIRCULAR benchmark: Vegas win total ALONE. env_idx/off_q
        # (inside the struct proxy) are 2026 indices that partly encode 2024-2025
        # results, so struct-vs-2025 is inflated by circularity; win-total-alone
        # is the honest, market-sourced floor.
        win_only = [scores[t]["inputs"]["win_total"] for t in teams_common]
        rho_win = _spearman(win_only, ys)
        top = sorted(actuals, key=lambda t: -actuals[t])[:8]
        report["seasons"][year] = {
            "available": True,
            "n_teams": len(teams_common),
            "spearman_struct_vs_realizedFP": (round(rho, 3) if rho is not None else None),
            "spearman_winTotalAlone_vs_realizedFP": (round(rho_win, 3) if rho_win is not None else None),
            "top8_realized_offenses": [f"{t} ({round(actuals[t])})" for t in top],
        }

    if not any_year:
        report["status"] = "UNVALIDATED_NO_DATA"
        report["note"] = ("No realized team-season actuals found on disk; ceiling "
                          "design is UNVALIDATED and defended from established drivers only.")
        return report

    report["status"] = "PARTIAL_CONVERGENT_ONLY"
    report["note"] = (
        "Convergent-validity ONLY. Repo has 2024/2025 REALIZED team offensive FP "
        "(FP_ADVANCED) but NO preseason projection for any past season, so a true "
        "'overperformed-its-projection' retrodiction is NOT possible. Reported "
        "Spearman is (structural environment proxy) vs (realized team offensive FP) "
        "-- it tests whether the design points at genuinely high-output offensive "
        "environments, NOT whether it predicts BEATING a projection."
    )
    report["caveats"] = [
        "n=32 teams per season -> small sample; a few teams swing rho by ~0.05-0.10.",
        "FP_ADVANCED = QUALIFIED players only; deep bench/committee FP is truncated, "
        "so team totals slightly favor concentrated offenses.",
        "Multi-team (traded) player rows are DROPPED, so a few teams lose a partial "
        "contributor -> minor downward noise on those teams.",
        "The QUANTITY being validated is EXPECTED output alignment, not the VARIANCE / "
        "overperformance thesis that the full ceiling score (with kickers) is built on. "
        "The overperformance thesis remains UNVALIDATED pending a historical preseason "
        "projection feed (2024/2025 Vegas win totals or team point projections).",
        "CIRCULARITY: the struct proxy includes env_idx/off_q, which are 2026 preseason "
        "indices that partially encode 2024-2025 results -> struct-vs-2025 rho (~0.86) is "
        "inflated. The honest, non-circular floor is win-total-ALONE vs realized FP "
        "(~0.46 in 2024, ~0.61 in 2025): a positive, moderate relationship both years.",
    ]
    return report


# ----------------------------------------------------------------------------
def main():
    scores, ranked = build_scores()
    validation = validate_retrodiction(scores)

    payload = {
        "_meta": {
            "artifact": "team_ceiling.json",
            "what": "Per-team probability-of-CEILING-SEASON score (offense dramatically "
                    "overperforms projection) -- variance/upside read, NOT expected value.",
            "for_season": 2026,
            "n_teams": len(scores),
            "score_scale": "0-100, relative probability-of-ceiling ordering (not a "
                           "calibrated absolute probability).",
            "tiers": {"ELITE": "top 6", "HIGH": "next 8", "MID": "middle 12", "LOW": "bottom 6"},
            "drivers": [
                "env_quality (0.30)", "win_total (0.22)", "pace (0.16)",
                "pass_rate (0.16)", "qb_ascend (0.16)",
                "scheme_upgrade (+0.14)", "concentrated_tree (+0.12)",
                "ol_improve (+0.06)", "shootout_script (+0.08)",
            ],
            "sources": [
                "offense_profile.json", "boom/team_env.json",
                "coordinator_scheme_2026.json", "boom/defensive_profile.json",
            ],
            "validation": validation,
            "standalone": "Foundation layer; NOT wired into rankings/pipeline.",
            "surfaces": ["predraft", "live", "dossier"],
        },
        "teams": scores,
    }

    out_path = os.path.join(HERE, "team_ceiling.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    # ---- console summary ----
    print("=" * 72)
    print("TEAM-CEILING SCORE  (2026)  -- probability of a CEILING SEASON")
    print("=" * 72)
    tier_order = {"ELITE": 0, "HIGH": 1, "MID": 2, "LOW": 3}
    last = None
    for t in ranked:
        s = scores[t]
        if s["tier"] != last:
            print(f"\n--- {s['tier']} CEILING ---")
            last = s["tier"]
        fl = "; ".join(s["flags"][:4])
        print(f"  {s['rank']:>2}. {t:<4} {s['ceiling_score']:>5.1f}  | {fl}")

    print("\n" + "=" * 72)
    print("VALIDATION:", validation["status"])
    print("-" * 72)
    print(validation["note"])
    for yr, r in validation["seasons"].items():
        if r.get("available"):
            print(f"  {yr}: n={r['n_teams']}  rho(struct vs realized FP)="
                  f"{r['spearman_struct_vs_realizedFP']}  |  rho(win-total ALONE)="
                  f"{r['spearman_winTotalAlone_vs_realizedFP']}  <- honest floor")
            print(f"        top realized offenses: {', '.join(r['top8_realized_offenses'])}")
    if validation["caveats"]:
        print("  caveats:")
        for c in validation["caveats"]:
            print(f"    - {c}")
    print("=" * 72)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
