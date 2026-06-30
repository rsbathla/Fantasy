"""flags/config — per-position flag tables (the position-specific SEMANTICS).

This is where the ~879 inline thresholds the audit found scattered through the 5 builders
(RB 266, QB 199, TE 195, WR 171, DST 48) move to: one declarative table per position. Each
FlagSpec.test reads a ctx dict = the player's season fields merged with the current week's
matchup/env fields.

WR is provided as a complete worked example. QB/RB/TE/DST are ported by transcribing each
builder's if-cascade into FlagSpec rows (see bbdfs/MIGRATION.md) — the engine and grading
are already shared, so porting is data entry, not logic. Multipliers below are illustrative
starting values pinned to the SWING targets in core.config; reconcile to the live builders'
exact multipliers during the parity migration.
"""
from .engine import FlagSpec, SKILL, MATCHUP, ENV, SUPPRESSOR

# --- WR: worked example -------------------------------------------------------
WR = [
    # skill (player/season)
    FlagSpec("ALPHA_TARGET", SKILL, lambda c: (c.get("tgt_share") or 0) >= 0.26, 1.18, "alpha target share"),
    FlagSpec("YPRR_ELITE", SKILL, lambda c: (c.get("route_yprr") or 0) >= 2.4, 1.15, "elite YPRR"),
    FlagSpec("DEEP_THREAT", SKILL, lambda c: (c.get("adot") or 0) >= 13.0, 1.10, "deep aDOT"),
    FlagSpec("RZ_ROLE", SKILL, lambda c: (c.get("rz_tgt_share") or 0) >= 0.20, 1.12, "red-zone role"),
    FlagSpec("SEPARATOR", SKILL, lambda c: (c.get("rec_separation") or 0) >= 3.0, 1.08, "wins separation"),
    # matchup (per week)
    FlagSpec("SOFT_COVERAGE", MATCHUP, lambda c: (c.get("opp_pass_cov_pctl") or 50) <= 30, 1.15, "soft coverage"),
    FlagSpec("PASS_FUNNEL", MATCHUP, lambda c: (c.get("opp_wr1_funnel") or 0) >= 70, 1.12, "pass funnel D"),
    FlagSpec("MAN_BEATER", MATCHUP,
             lambda c: (c.get("rec_man_zone_delta") or 0) > 0 and (c.get("opp_man_rate") or 0) >= 0.34,
             1.10, "man-beater vs man-heavy D"),
    # environment (per week, Vegas)
    FlagSpec("HIGH_TOTAL", ENV, lambda c: (c.get("week_total") or 0) >= 48, 1.10, "high total"),
    FlagSpec("SHOOTOUT", ENV,
             lambda c: abs(c.get("week_spread") or 0) <= 3 and (c.get("week_total") or 0) >= 47,
             1.08, "tight, high total"),
    # suppressors (per week, down-multiplier)
    FlagSpec("SHADOW_CB", SUPPRESSOR, lambda c: (c.get("opp_shadow_cb") or 0) == 1, 0.88, "travels with shadow CB"),
    FlagSpec("LOW_TOTAL", SUPPRESSOR, lambda c: (c.get("week_total") or 99) <= 39, 0.90, "low total"),
    FlagSpec("BLOWOUT_DOG", SUPPRESSOR, lambda c: (c.get("week_spread") or 0) >= 10, 0.92, "heavy underdog script"),
]

# --- placeholders to port from the legacy builders (see MIGRATION.md) ---------
QB = []   # port from build_flags_QB.py (199 thresholds): rush upside, stack, pace, soft pass D, dome, total
RB = []   # port from build_flags_RB.py (266 thresholds): workload, GL role, soft run front, game script
TE = []   # port from build_flags_TE.py (195 thresholds): route rate, RZ role, soft seam/LB coverage
DST = []  # port from build_flags_DST.py (48 thresholds): opp turnover-prone, sack matchup, home, weather

CONFIGS = {"WR": WR, "QB": QB, "RB": RB, "TE": TE, "DST": DST}
