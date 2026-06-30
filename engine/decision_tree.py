"""decision_tree.py - the Best Ball 2026 pick decision-tree engine (Contract 4).

Produces the Contract-3 JSON ({state, headline, tree}) consumed by the decision
dashboard (Contract 5). It wraps the validated engine (engine/bbengine.py) and the
construction rules (docs/STRATEGY_SPEC.md):

  * value of a pick   -> bbengine.pick_values (marginal dTitle/dAdv/dW17 from the sim)
  * blended score     -> 0.6*dTitle + 0.4*dAdv  (per CONTRACTS Contract 4)
  * playoff tilt      -> + lambda(round)*playoff_up, lambda = 0.02*(round-7) for round>=8
                         (STRATEGY_SPEC S4: ignore rds 1-7, tie-break 8-10, drive 11-18)
  * construction adj  -> positional-need bonus vs build curve (QB 2-3/RB 5-6/WR 8-9/TE 2-3),
                         stack/anchor bonus (extends a QB<->pass-catcher game stack),
                         uncorrelated bye-pileup penalty (STRATEGY_SPEC S1/S2/S3)

Scale handling
--------------
bbengine.pick_values returns deltas in PERCENTAGE POINTS (e.g. dtitle=12.92 == +0.1292
title-share). The STRATEGY_SPEC tilt formula (lambda max 0.22) and the construction-bonus
constants are sized for the PROBABILITY scale (~0..0.2), so we blend on probability-scale
deltas (pv/100) - that keeps tilt/need/stack meaningful drivers rather than rounding error.
The branch JSON still reports the raw pick_values numbers (faithful to the sim); only the
internal ranking score is scale-normalized. Positional-discipline penalties (e.g. QB1 before
R6) are STRUCTURAL (large) because the spec treats them as near-hard rules that must override a
raw marginal-delta temptation, not as tiebreaks.

Marginal value OVER REPLACEMENT (CONCERN-3/CONCERN-4 fix)
---------------------------------------------------------
Naively calling pick_values on the half-built live rosters produced two pathologies the reviewer
caught: (a) mid-draft deltas were wildly inflated (dTitle +56, dAdv +22) because the field was a
sparse, uneven set of tiny rosters - one added star swings a near-empty team enormously; and (b) at
picks 1-2 every delta collapsed to ~0 because a roster with no startable lineup can't advance no
matter who you add, so the headline became arbitrary board order.

We fix both by valuing every candidate as VALUE OVER REPLACEMENT against a fair, full field:

  1. Pad ALL 12 teams (mine and every opponent) to a full, startable 18-man squad
     (FILLER_SHAPE = 2 QB / 6 RB / 8 WR / 2 TE) using REPLACEMENT-LEVEL gradeable fillers -
     the "last-starter / first-bench" tier per position (FILLER_BAND), NOT 0-proj scrubs. Padding to
     the replacement BAND (not the bottom of the board) is what gives R1 signal: a star is then a
     meaningful upgrade over a startable baseline rather than a rounding error among 17 scrubs.
  2. Value a candidate by REPLACING one same-position filler on MY roster with that candidate, keeping
     my roster size constant at 18. The resulting delta is "this real player OVER a replacement-level
     player at his position" - realistic at any draft stage and non-zero even at R1.
  3. Fillers are drawn DISJOINTLY per team (a sim name maps to exactly one team via name2team, so a
     duplicate filler name across teams would collide) and never reuse a real-drafted name.

CRN is automatic: survival_chain.chain reseeds np.random.default_rng(11) every call, so the padded
baseline and each candidate share identical draws -> clean apples-to-apples deltas. The reported
dTitle/dAdv/dW17 are these over-replacement deltas (faithful to the sim); the 0.6/0.4 blended-score
weights, playoff tilt, and construction adjustments are UNCHANGED.

Public API
----------
build_tree(board, rosters, me="rsbathla", seat=None, plies=2, pick=None, rnd=None) -> dict
    The Contract-3 decision tree. `board` = bbengine.load_board() output (list of player
    dicts). `rosters` = {team: [names]} including `me`. `seat` (1..12) is required for accurate pick
    math; if omitted it DEFAULTS to a central seat (see _infer_seat) and pick accuracy degrades.
    `pick`/`rnd` are the TRUE overall pick & round (from bbengine.parse_board); when omitted they are
    derived from seat + roster size (legacy behavior, wrong when the roster holds non-gradeable
    players). `plies=2` attaches a 1-ply look-ahead subtree (`then`) to each branch.

Performance
-----------
Sims are ~0.5-0.8s each (a padded 216-player field grades in ~0.6s at NS=1000) and we run
(1 baseline + n_candidates) sims. We set survival_chain.NS low (TREE_NS=1000), cap the shortlist
(SHORTLIST_PICK~12 at the pick, SHORTLIST_LOOKAHEAD~6 ahead), and pre-rank a cheap no-sim prelim score
so we only sim the shortlist (not all ~407 gradeable). A full 2-ply tree lands in ~20s, well under ~60s.
"""
from __future__ import annotations

import os
import sys

# Make bbengine importable no matter where this is launched from.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import bbengine as bb  # noqa: E402

# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------
TREE_NS = 1000               # survival_chain samples while tree-building (fast, stable enough)
SHORTLIST_PICK = 12          # candidates we sim at the decision pick
SHORTLIST_LOOKAHEAD = 6      # candidates we sim at the look-ahead pick
N_BRANCHES = 3               # availability branches at the decision pick (2-4 allowed by schema)
GRADED_N = 7                 # top-N available BY RANK graded for title+advancement (panel)
TEAMS = 12
ROUNDS = 18
DELTA_SCALE = 100.0          # pick_values returns percentage points; /100 -> probability scale

# Replacement-level padding (CONCERN-3/CONCERN-4): every team is padded to a full, startable 18-man
# squad so a candidate's value is measured OVER REPLACEMENT against a fair, full field.
FILLER_SHAPE = {"QB": 2, "RB": 6, "WR": 8, "TE": 2}   # 18 = a startable lineup + bench depth per team
# Per-position "replacement band": the slice of gradeable players (sorted best->worst by proj) we draw
# fillers from - roughly the last-starter / first-bench tier in a 12-team league. Padding to THIS band
# (not the 0-proj bottom of the board) is what gives a star meaningful signal even at R1: the baseline
# team is a real contender, so swapping in an elite is a true upgrade, not noise among scrubs.
FILLER_BAND = {"QB": (20, 44), "RB": (48, 120), "WR": (70, 166), "TE": (20, 44)}

# Season-long positional build curve (STRATEGY_SPEC S1).
_PLAT = os.environ.get("BB_PLATFORM", "DK").upper()
if _PLAT == "UD":
    # Best Ball Mania winner-calibrated (18 rds, half-PPR): WR-heavy / RB-light (take RB EARLY, finish
    # with fewer), cheap 2-3 QB. Src: 4for4 "How Winners Draft", Underdog Network 5-yr study, ETR.
    SEASON_TARGET = {"QB": (2, 3), "RB": (4, 6), "WR": (6, 8), "TE": (2, 3)}
else:
    SEASON_TARGET = {"QB": (2, 3), "RB": (5, 6), "WR": (8, 9), "TE": (2, 3)}
# Running "want at least this many of POS after this round" band (STRATEGY_SPEC S1 table).
RUNNING_MIN = {
    1: {"RB": 0, "WR": 0, "QB": 0, "TE": 0},
    2: {"RB": 0, "WR": 1, "QB": 0, "TE": 0},
    3: {"RB": 1, "WR": 1, "QB": 0, "TE": 0},
    4: {"RB": 1, "WR": 2, "QB": 0, "TE": 0},
    5: {"RB": 2, "WR": 3, "QB": 0, "TE": 0},
    6: {"RB": 2, "WR": 3, "QB": 0, "TE": 0},
    7: {"RB": 3, "WR": 4, "QB": 1, "TE": 0},
    8: {"RB": 3, "WR": 4, "QB": 1, "TE": 0},
    9: {"RB": 4, "WR": 5, "QB": 1, "TE": 1},
    10: {"RB": 4, "WR": 6, "QB": 1, "TE": 1},
    11: {"RB": 4, "WR": 6, "QB": 2, "TE": 1},
    12: {"RB": 5, "WR": 7, "QB": 2, "TE": 2},
    13: {"RB": 5, "WR": 7, "QB": 2, "TE": 2},
    14: {"RB": 5, "WR": 8, "QB": 2, "TE": 2},
    15: {"RB": 5, "WR": 8, "QB": 2, "TE": 2},
    16: {"RB": 6, "WR": 8, "QB": 3, "TE": 3},
    17: {"RB": 6, "WR": 9, "QB": 3, "TE": 3},
    18: {"RB": 6, "WR": 9, "QB": 3, "TE": 3},
}


# ---------------------------------------------------------------------------
# Snake-draft pick math (matches bbengine._ov_for / draft_pick.ov_for)
# ---------------------------------------------------------------------------
def _ov_for(seat, rnd, teams=TEAMS):
    """Overall pick number for (seat, round) in a snake draft."""
    return (rnd - 1) * teams + (seat if rnd % 2 == 1 else teams + 1 - seat)


DEFAULT_SEAT = 6   # central snake seat used only when the caller does not pass one


def _infer_seat(n_my_picks=None, teams=TEAMS):
    """Best-effort default seat when the caller does not pass one (CONCERN-5).

    A roster size alone cannot recover the true snake seat, so this is only a DEFAULT, not an
    inference: we return a central seat (DEFAULT_SEAT=6) so the pick/look-ahead snake math is as
    close to balanced as possible. Whenever pick accuracy matters the caller must pass `seat`
    explicitly - the live path (run_live.py) always passes bbengine.parse_board()'s detected seat,
    so it is unaffected by this fallback.
    """
    return DEFAULT_SEAT


# ---------------------------------------------------------------------------
# Board / overlay / schedule indices
# ---------------------------------------------------------------------------
def _index_board(board):
    """norm_name -> player dict, for O(1) lookups."""
    return {bb._norm(p["name"]): p for p in board}


def _games_w17():
    """team -> (away, home) for Week 17, from pipeline/games_by_week.json.

    Maps a candidate's team to its W17 game so we score game-stacks and fill state.anchor the
    same way survival_chain.anchor_game does.
    """
    import json
    path = os.path.join(os.path.dirname(_HERE), "pipeline", "games_by_week.json")
    try:
        gw = json.load(open(path, encoding="utf-8"))
    except Exception:
        return {}
    games = gw.get("17") or gw.get(17) or []
    out = {}
    for g in games:
        a, b = g[0], g[1]
        out[a] = (a, b)
        out[b] = (a, b)
    return out


# ---------------------------------------------------------------------------
# Roster summary: counts, teams-by-position, byes, current game-stacks
# ---------------------------------------------------------------------------
def _roster_summary(roster_names, bidx, w17):
    """Summarize my current roster for the construction heuristics.

    counts, qb_teams, catcher_teams, team_players, byes{week:[(name,team)]}, stack_pieces{game:n}.
    """
    counts = {"QB": 0, "RB": 0, "WR": 0, "TE": 0}
    qb_teams, catcher_teams = set(), set()
    team_players, byes, stack_pieces = {}, {}, {}
    for nm in roster_names:
        p = bidx.get(bb._norm(nm))
        if not p:
            continue
        pos, team, bye = p["pos"], p["team"], p["bye"]
        if pos in counts:
            counts[pos] += 1
        if pos == "QB":
            qb_teams.add(team)
        if pos in ("WR", "TE"):
            catcher_teams.add(team)
        team_players.setdefault(team, []).append(pos)
        if bye is not None:
            byes.setdefault(int(bye), []).append((nm, team))
        g = w17.get(team)
        if g:
            key = f"{g[0]}@{g[1]}"
            stack_pieces[key] = stack_pieces.get(key, 0) + 1
    return {"counts": counts, "qb_teams": qb_teams, "catcher_teams": catcher_teams,
            "team_players": team_players, "byes": byes, "stack_pieces": stack_pieces}


def _anchor_str(summary):
    """Our best game-stack to build, as 'AWAY@HOME' or 'none' (>=2 pieces required)."""
    best, bn = "none", 1
    for g, n in summary["stack_pieces"].items():
        if n > bn:
            bn, best = n, g
    return best


# ---------------------------------------------------------------------------
# Construction adjustments (probability-scale units, added on top of blended)
# ---------------------------------------------------------------------------
def _need_bonus(pos, rnd, counts):
    """Positional-need bonus vs the running build-curve target (STRATEGY_SPEC S1/S5).

    Positive when below the running minimum (we need it). STRUCTURAL penalties (large enough to
    override raw delta) for: over-investing past the season max; taking QB1 before R6 (the QB
    window opens R6 - a near-hard rule, since QBs have the lowest ceiling-edge so a big early
    *advancement* delta on a thin roster is a trap); any 3rd QB; and a muddy-middle 1st TE.
    """
    have = counts.get(pos, 0)
    want = RUNNING_MIN.get(rnd, RUNNING_MIN[ROUNDS]).get(pos, 0)
    deficit = want - have
    bonus = 0.0
    if deficit > 0:
        bonus += 0.020 * deficit
    smax = SEASON_TARGET[pos][1]
    if have >= smax:
        bonus -= 0.12 * (have - smax + 1)
    if pos == "QB":
        if have == 0 and rnd < 6:
            bonus -= 0.18 + 0.06 * (5 - rnd)      # R5 -0.18, R4 -0.24, ... decisive vs WR/RB value
        if have >= 2:
            bonus -= 0.12                          # discourage any 3rd QB outside the very late dart
    if pos == "TE" and have == 0 and 5 <= rnd <= 8 and want == 0:
        bonus -= 0.04
    return bonus


def _stack_bonus(pos, team, rnd, summary, w17):
    """Bonus for a pick that EXTENDS a real (correlated) game-stack (STRATEGY_SPEC S2/S4).

    Correlated: QB<->WR/TE same team, and a bring-back on the OTHER team in a game where we hold
    a QB+catcher. WR<->WR (r~0) is NOT a stack. Stacks fire in the playoffs, so the bonus grows
    with round. Over-stack penalty past 4-5 same-game pieces.
    """
    g = w17.get(team)
    if not g:
        return 0.0
    other = g[1] if g[0] == team else g[0]
    growth = 1.0 + max(0, rnd - 8) * 0.15
    _udm = 1.4 if _PLAT == "UD" else 1.0   # UD winners concentrate far harder (12/18 from 3 W17 games)
    bonus = 0.0
    if pos == "QB" and team in summary["catcher_teams"]:
        bonus += 0.030 * growth
    if pos in ("WR", "TE") and team in summary["qb_teams"]:
        bonus += 0.035 * growth
    # ONSLAUGHT: a 2nd same-team pass-catcher. Real but modest (WR-WR ~0.20 corr vs 0.43 for QB-WR);
    # grows into the playoff weeks where concentration pays, but kept small so it never funds a reach
    # (BBM data: reaching for double-stacks is slightly -EV). Bigger once the QB completes the stack.
    if pos in ("WR", "TE") and team in summary["catcher_teams"]:
        bonus += (0.020 if team in summary["qb_teams"] else 0.012) * growth
    if (other in summary["qb_teams"]) and (other in summary["catcher_teams"]) and pos in ("WR", "TE", "RB"):
        bonus += 0.020 * growth
    key = f"{g[0]}@{g[1]}"
    pieces = summary["stack_pieces"].get(key, 0)
    _ostk = 6 if _PLAT == "UD" else 4      # UD tolerates bigger onslaughts before penalizing
    if pieces >= _ostk:
        bonus -= 0.030 * (pieces - (_ostk - 1))
    return bonus * _udm


def _bye_penalty(team, bye, summary):
    """Penalty for an UNCORRELATED same-bye pileup beyond a same-team stack (STRATEGY_SPEC S3)."""
    if bye is None:
        return 0.0
    same_week = summary["byes"].get(int(bye), [])
    other_teams = {t for (_n, t) in same_week if t != team}
    if not other_teams:
        return 0.0
    return -0.015 * len(other_teams)


# ---------------------------------------------------------------------------
# Playoff tilt lambda(round)  (STRATEGY_SPEC S4)
# ---------------------------------------------------------------------------
def _lambda(rnd):
    if rnd <= 7:
        return 0.0
    base = 0.03 if _PLAT == "UD" else 0.02   # UD win-or-die finals reward playoff ceiling harder
    return base * (rnd - 7)


# ---------------------------------------------------------------------------
# Prelim (cheap, no-sim) score -> choose the shortlist to actually simulate
# ---------------------------------------------------------------------------
def _prelim_score(p, rnd, summary, w17, pick):
    """Cheap pre-sim score to choose which ~12 candidates to simulate.

    Blends board value (rank), value-vs-pick (fell past ADP), positional need, stack fit, playoff
    tilt, bye penalty. Goal: the top-N here are a sane superset of the true (post-sim) best.
    """
    pos, team = p["pos"], p["team"]
    rank = p.get("rank") or 250
    val = max(0.0, 1.0 - (rank - 1) / 250.0)
    adp = p.get("adp")
    fell = 0.0
    if adp is not None:
        fell = max(-1.0, min(1.0, (pick - adp) / 24.0))   # +ve = fell past ADP (value); -ve = reach
    need = _need_bonus(pos, rnd, summary["counts"])
    stack = _stack_bonus(pos, team, rnd, summary, w17)
    bye = _bye_penalty(team, p.get("bye"), summary)
    tilt = _lambda(rnd) * (p.get("playoff_up") or 0.0)
    return 1.20 * val + 0.35 * fell + need + stack + bye + tilt


# ---------------------------------------------------------------------------
# Final (post-sim) blended score for a candidate
# ---------------------------------------------------------------------------
def _reach_term(adp, pick):
    """ADP discipline for the FINAL pick. gap = adp - pick: >0 means the player's ADP is LATER than
    now, i.e. you could wait and still get him -> reaching -> escalating penalty. <0 means he slid
    to you (value) -> small bonus. Sized to overrule the sim on big reaches (20+ picks)."""
    if adp is None or pick is None:
        return 0.0
    gap = adp - pick
    if gap > 0:
        return -0.0045 * min(gap, 40.0)      # ~-0.09 at a 20-pick reach, ~-0.12 at 27
    return 0.0012 * min(-gap, 40.0)          # modest bonus for fallers


def _final_score(pv, p, rnd, summary, w17, pick=None):
    """Combine sim deltas (scaled to probability) with playoff tilt + construction adjustments.

    pv = {"dtitle":..,"dadv":..,"dw17":..} from bbengine.pick_values (percentage points).
    Returns the score and its components (probability scale) for transparent reasons.
    """
    dtitle, dadv, dw17 = pv["dtitle"], pv["dadv"], pv["dw17"]
    blended = 0.6 * (dtitle / DELTA_SCALE) + 0.4 * (dadv / DELTA_SCALE)
    tilt = _lambda(rnd) * (p.get("playoff_up") or 0.0)
    need = _need_bonus(p["pos"], rnd, summary["counts"])
    stack = _stack_bonus(p["pos"], p["team"], rnd, summary, w17)
    bye = _bye_penalty(p["team"], p.get("bye"), summary)
    reach = _reach_term(p.get("adp"), pick)
    score = blended + tilt + need + stack + bye + reach
    return {"score": score, "blended": blended, "tilt": tilt, "need": need,
            "stack": stack, "bye": bye, "reach": reach, "dtitle": dtitle, "dadv": dadv, "dw17": dw17}


# ---------------------------------------------------------------------------
# Replacement-level padding -> value-over-replacement (CONCERN-3 / CONCERN-4)
# ---------------------------------------------------------------------------
def _gradeable(p):
    """Only players in the sim universe move the deltas (proj present == in clay/layer2)."""
    return p.get("proj") is not None


def _replacement_pools(board):
    """Per-position lists of replacement-band filler players (display names), sorted best->worst.

    We take a slice (FILLER_BAND) out of each position's gradeable players sorted DESC by proj -
    the last-starter / first-bench tier - so padded teams are startable contenders, not scrub heaps.
    """
    bypos = {}
    for p in board:
        if _gradeable(p) and p["pos"] in FILLER_BAND:
            bypos.setdefault(p["pos"], []).append(p)
    pools = {}
    for pos, lst in bypos.items():
        lst.sort(key=lambda pp: -(pp["proj"] or 0.0))
        a, b = FILLER_BAND[pos]
        pools[pos] = [p["name"] for p in lst[a:b]]
    return pools


def _pad_field(board, rosters, me):
    """Pad every team to a full startable 18-man squad with DISJOINT replacement-level fillers.

    Returns (padded_rosters, my_fillers_by_pos) where my_fillers_by_pos[pos] is the list of filler
    names added to MY roster - the swap-out pool for value-over-replacement. Real-drafted names are
    excluded from the filler pool, and fillers are handed out disjointly across teams (a sim name maps
    to exactly one team, so duplicates would collide).
    """
    bidx = _index_board(board)
    pools = _replacement_pools(board)
    drafted = {bb._norm(n) for names in rosters.values() for n in names}
    cursor = {pos: 0 for pos in pools}

    def take(pos, k):
        out = []
        lst = pools.get(pos, [])
        while len(out) < k and cursor[pos] < len(lst):
            nm = lst[cursor[pos]]
            cursor[pos] += 1
            if bb._norm(nm) not in drafted:
                out.append(nm)
        return out

    padded, my_fillers = {}, {pos: [] for pos in FILLER_SHAPE}
    for team, names in rosters.items():
        counts = {"QB": 0, "RB": 0, "WR": 0, "TE": 0}
        keep = []
        for nm in names:
            p = bidx.get(bb._norm(nm))
            if p is not None and _gradeable(p):
                keep.append(nm)
                if p["pos"] in counts:
                    counts[p["pos"]] += 1
        squad = list(keep)
        fillers_here = {pos: [] for pos in FILLER_SHAPE}
        for pos, want in FILLER_SHAPE.items():
            f = take(pos, max(0, want - counts[pos]))
            squad += f
            fillers_here[pos] += f
        # Top any short roster up to 18 with WR depth (WR pool is deepest).
        while len(squad) < ROUNDS:
            f = take("WR", 1)
            if not f:
                break
            squad += f
            fillers_here["WR"] += f
        padded[team] = squad
        if team == me:
            my_fillers = fillers_here
    return padded, my_fillers


def _value_over_replacement(board, rosters, me, cand_names, ns):
    """{name: {dtitle,dadv,dw17}} valuing each candidate as REPLACING a same-pos filler on my roster.

    Pads ALL teams to a fair full field, grades a single padded baseline, then for each candidate
    swaps out one of my replacement-level fillers of the same position and re-grades (roster size held
    at 18). The delta is value OVER REPLACEMENT - realistic at any draft stage and non-zero at R1.
    CRN is automatic (chain reseeds a fixed rng each call). Falls back to bb.pick_values only if the
    field cannot be padded (no fillers at all).
    """
    bidx = _index_board(board)
    sc, _ = bb._load_engine_modules()
    sc.NS = ns
    padded, my_fillers = _pad_field(board, rosters, me)
    if not any(my_fillers.values()):
        # Degenerate (no fillers available) - fall back to the legacy append valuation.
        return bb.pick_values(rosters, me, cand_names, ns=ns)
    base = bb.grade(padded, me)
    bt, ba, bw = base["title_share"], base["p_adv"], base["win_W17"]
    out = {}
    for c in cand_names:
        p = bidx.get(bb._norm(c))
        pos = p["pos"] if p else "WR"
        pool = my_fillers.get(pos) or next((v for v in my_fillers.values() if v), [])
        if not pool:
            out[c] = {"dtitle": 0.0, "dadv": 0.0, "dw17": 0.0}
            continue
        drop = pool[0]
        r2 = {t: list(v) for t, v in padded.items()}
        r2[me] = [n for n in r2[me] if n != drop] + [c]
        g = bb.grade(r2, me)
        out[c] = {"dtitle": round((g["title_share"] - bt) * DELTA_SCALE, 2),
                  "dadv": round((g["p_adv"] - ba) * DELTA_SCALE, 1),
                  "dw17": round((g["win_W17"] - bw) * DELTA_SCALE, 1)}
    return out


def _evaluate_pick(board, rosters, me, available_names, rnd, pick, summary, w17, shortlist_n, ns):
    """Shortlist available gradeable candidates by prelim score, then sim them (best->worst)."""
    bidx = _index_board(board)
    pool = []
    for nm in available_names:
        p = bidx.get(bb._norm(nm))
        if p is None or not _gradeable(p):
            continue
        pool.append(p)
    pool.sort(key=lambda pp: _prelim_score(pp, rnd, summary, w17, pick), reverse=True)
    shortlist = pool[:shortlist_n]
    if not shortlist:
        return []
    names = [p["name"] for p in shortlist]
    # Value each candidate OVER REPLACEMENT against a fully-padded fair field (CONCERN-3/CONCERN-4)
    # instead of appending to the half-built live rosters (which inflated deltas and zeroed R1).
    pv = _value_over_replacement(board, rosters, me, names, ns)
    scored = []
    for p in shortlist:
        d = pv.get(p["name"], {"dtitle": 0.0, "dadv": 0.0, "dw17": 0.0})
        comp = _final_score(d, p, rnd, summary, w17, pick)
        scored.append({"name": p["name"], "pos": p["pos"], "team": p["team"],
                       "playoff_up": round(float(p.get("playoff_up") or 0.0), 3),
                       "adp": p.get("adp"), "rank": p.get("rank"),
                       "dtitle": d["dtitle"], "dadv": d["dadv"], "dw17": d["dw17"],
                       "score": comp["score"], "components": comp, "player": p})
    scored.sort(key=lambda s: s["score"], reverse=True)
    return scored


# ---------------------------------------------------------------------------
# Reason / condition text builders
# ---------------------------------------------------------------------------
def _archetype(pos, c, summary, w17):
    """Short human archetype tag for a candidate (used in cond/reason)."""
    team = c["team"]
    if pos in ("WR", "TE") and team in summary["qb_teams"]:
        return f"{pos} stack w/ our {team} QB"
    if pos == "QB" and team in summary["catcher_teams"]:
        return f"QB stack w/ our {team} pass-catcher"
    pu = c.get("playoff_up") or 0.0
    if pos == "WR" and pu >= 0.7:
        return "elite WR"
    if pos == "WR":
        return "WR"
    if pos == "RB" and pu >= 0.7:
        return "lead RB"
    if pos == "RB":
        return "RB"
    if pos == "TE":
        return "TE"
    return pos


def _reason_for(c, rnd, summary, is_fallback):
    """Compose a grounded one-line rationale from the score components + curve state."""
    comp = c["components"]
    pos = c["pos"]
    have = summary["counts"].get(pos, 0)
    lo, hi = SEASON_TARGET[pos]
    bits = [f"blended d {comp['blended']:+.3f} (dTitle {c['dtitle']:+.2f}, dAdv {c['dadv']:+.1f})",
            f"{pos} {have}->{have + 1} vs target {lo}-{hi}"]
    if comp["stack"] > 0.001:
        bits.append(f"extends a correlated game-stack (+{comp['stack']:.3f})")
    elif comp["stack"] < -0.001:
        bits.append(f"over-stack penalty ({comp['stack']:.3f})")
    if rnd >= 11 and (c.get("playoff_up") or 0) > 0:
        bits.append(f"R{rnd}: playoff_up {c['playoff_up']:.2f} primary driver (+{comp['tilt']:.3f})")
    elif 8 <= rnd <= 10 and (c.get("playoff_up") or 0) > 0:
        bits.append(f"R{rnd}: playoff_up {c['playoff_up']:.2f} tie-breaker (+{comp['tilt']:.3f})")
    if comp["bye"] < -0.001:
        bits.append(f"uncorrelated bye-pileup penalty ({comp['bye']:.3f})")
    adp = c.get("adp")
    if adp is not None:
        bits.append(f"ADP {adp:.0f}")
    head = "Catch-all best-available/fill-need: " if is_fallback else ""
    return head + "; ".join(bits) + "."


# ---------------------------------------------------------------------------
# Branch builders
# ---------------------------------------------------------------------------
def _make_branch(c, rnd, summary, w17, cond, is_fallback, then_node=None):
    br = {"cond": cond, "take": c["name"], "pos": c["pos"], "team": c["team"],
          "dTitle": round(float(c["dtitle"]), 3), "dAdv": round(float(c["dadv"]), 3),
          "dW17": round(float(c["dw17"]), 3),
          "playoff_up": round(float(c.get("playoff_up") or 0.0), 3),
          "reason": _reason_for(c, rnd, summary, is_fallback)}
    if then_node is not None:
        br["then"] = then_node
    return br


def _select_branch_candidates(scored, pick, n_branches):
    """Choose ordered branch candidates from the scored shortlist.

    Branch 1 = best-scoring candidate who MIGHT realistically still be on the board at our pick
               (ADP not far ahead of our pick). Middle = next-best of a DIFFERENT position (a
               distinct scenario, not 3 flavors of one position). Last = catch-all best-available.
    """
    if not scored:
        return []
    chosen, used = [], set()
    # Lead (headline) = the best-scored candidate, full stop. Availability is already known: the
    # decision-pick pool IS the live board, and the look-ahead pool is pre-drained by ADP. So a player
    # who FELL past his ADP onto our pick is value to headline, not a "reach" to demote. (Genuine
    # reaches - ADP far LATER than the pick - are already penalized inside the blended score via
    # _reach_term.) The old `adp >= pick - 6` cushion wrongly demoted available fallers.
    lead = scored[0]
    chosen.append(lead)
    used.add(lead["name"])
    lead_positions = {lead["pos"]}
    while len(chosen) < n_branches - 1:
        nxt = next((c for c in scored if c["name"] not in used and c["pos"] not in lead_positions), None)
        if nxt is None:
            nxt = next((c for c in scored if c["name"] not in used), None)
        if nxt is None:
            break
        chosen.append(nxt)
        used.add(nxt["name"])
        lead_positions.add(nxt["pos"])
    tail = next((c for c in scored if c["name"] not in used), None)
    if tail is not None:
        chosen.append(tail)
    elif len(chosen) < 2 and len(scored) >= 2 and scored[1]["name"] not in used:
        chosen.append(scored[1])
    return chosen[:n_branches]


# ---------------------------------------------------------------------------
# Look-ahead: best follow-up at our NEXT snake pick after a hypothetical add
# ---------------------------------------------------------------------------
def _lookahead_node(board, rosters, me, available_names, take_name, seat, this_round, w17, ns):
    """After hypothetically adding `take_name`, evaluate our NEXT snake pick (1 ply).

    Returns a node {label, branches:[best, fallback]} or None if no next pick / too few cands.
    The look-ahead's value-over-replacement baseline already INCLUDES `take_name` on my padded
    roster (r2 carries it), so its "then" deltas are measured against the same post-pick, fully
    padded field as the parent's swap baseline -> the parent and the look-ahead are on consistent,
    comparable VOR scales (both = upgrade-over-a-replacement-filler at a full 18-man field).
    """
    next_round = this_round + 1
    if next_round > ROUNDS:
        return None
    this_overall = _ov_for(seat, this_round, TEAMS)
    next_overall = _ov_for(seat, next_round, TEAMS)
    bidx = _index_board(board)
    r2 = {t: list(v) for t, v in rosters.items()}
    r2[me] = list(r2[me]) + [take_name]
    # Players still available at our NEXT pick: drop take_name AND the players the field drafts in
    # between. Between our pick at this_overall and our next at next_overall the other teams make
    # (next_overall - this_overall - 1) selections; model those as the top-ADP players coming off the
    # board, so the look-ahead never recommends players who'd realistically be gone (ADP near our pick).
    avail2 = [nm for nm in available_names if bb._norm(nm) != bb._norm(take_name)]
    gap = max(0, next_overall - this_overall - 1)
    if gap and len(avail2) > gap:
        def _adp_key(nm):
            pp = bidx.get(bb._norm(nm))
            if not pp:
                return 9999.0
            a = pp.get("adp"); r = pp.get("rank")
            return float(a) if a is not None else (float(r) if r is not None else 9999.0)
        drained = set(sorted(avail2, key=_adp_key)[:gap])
        avail2 = [nm for nm in avail2 if nm not in drained]
    summary2 = _roster_summary(r2[me], bidx, w17)
    scored = _evaluate_pick(board, r2, me, avail2, next_round, next_overall, summary2, w17,
                            SHORTLIST_LOOKAHEAD, ns)
    if not scored:
        return None
    branch_cands = _select_branch_candidates(scored, next_overall, 2)
    branches = []
    for i, c in enumerate(branch_cands):
        is_fallback = (i == len(branch_cands) - 1)
        if i == 0:
            cond = f"then take {c['name']} ({_archetype(c['pos'], c, summary2, w17)})"
        else:
            cond = f"else best available / need {c['pos']}"
        branches.append(_make_branch(c, next_round, summary2, w17, cond, is_fallback))
    if len(branches) < 2 and len(scored) >= 2:
        c = scored[1]
        branches.append(_make_branch(c, next_round, summary2, w17,
                                     f"else best available / need {c['pos']}", True))
    if len(branches) < 2:
        return None
    return {"label": f"Pick {next_overall} (R{next_round}) - look-ahead", "branches": branches}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def build_tree(board, rosters, me="rsbathla", seat=None, plies=2, pick=None, rnd=None):
    """Build the Contract-3 decision tree for the current draft state.

    board   : bbengine.load_board() output (list of player dicts).
    rosters : {team: [player names]} including `me` (field held fixed).
    me      : our team key (default 'rsbathla').
    seat    : our snake seat (1..12); DEFAULTS to a central seat if None (pick math degrades - pass it).
    plies   : 2 => attach a 1-ply look-ahead `then` to each branch; 1 => omit.
    pick    : TRUE overall pick number for this decision (from bbengine.parse_board). When given it is
              authoritative; the round is derived from it if `rnd` is also None.
    rnd     : TRUE round for this decision. If both pick and rnd are None we FALL BACK to deriving them
              from seat + roster size (legacy behavior) - which is WRONG when the roster holds
              non-gradeable players, so the live path passes both explicitly (BUG-1).

    Returns a dict matching engine/tree_schema.json: {state, headline, tree}.
    """
    if me not in rosters:
        raise KeyError(f"me={me!r} not in rosters {list(rosters)}")
    sc, _ = bb._load_engine_modules()
    sc.NS = TREE_NS
    bidx = _index_board(board)
    w17 = _games_w17()
    # 1. Current pick / round. Prefer the TRUE pick/round passed by the caller (parse_board); only
    #    fall back to roster-size derivation when neither is supplied (BUG-1: gradeable count != round
    #    when the roster contains non-gradeable players).
    my_names = list(rosters[me])
    n_my = len(my_names)
    if seat is None:
        seat = _infer_seat(n_my)
    if pick is not None:
        overall = int(pick)
        this_round = int(rnd) if rnd is not None else (overall - 1) // TEAMS + 1
    elif rnd is not None:
        this_round = int(rnd)
        overall = _ov_for(seat, this_round, TEAMS)
    else:
        # Legacy fallback: derive from how many gradeable players we own.
        this_round = n_my + 1
        if this_round > ROUNDS:
            this_round = ROUNDS
        overall = _ov_for(seat, this_round, TEAMS)
    if this_round > ROUNDS:
        this_round = ROUNDS
    # Available = full draftable universe minus everyone drafted (any team).
    drafted = {bb._norm(n) for names in rosters.values() for n in names}
    available_names = [p["name"] for p in board if bb._norm(p["name"]) not in drafted]
    summary = _roster_summary(my_names, bidx, w17)
    # 2/3. Shortlist + sim + score candidates at THIS pick.
    scored = _evaluate_pick(board, rosters, me, available_names, this_round, overall, summary, w17,
                            SHORTLIST_PICK, TREE_NS)
    if not scored:
        raise RuntimeError("no gradeable candidates available to build a tree")
    # GRADED-7: the next GRADED_N available BY RANK, each graded for title + advancement.
    # Branches stay value/availability-driven; this panel is a straight rank-ordered grade board.
    _scored_by = {bb._norm(s_['name']): s_ for s_ in scored}
    def _rkk(nm):
        pp=bidx.get(bb._norm(nm))
        try: return float(pp.get('rank')) if pp and pp.get('rank') is not None else 9999.0
        except Exception: return 9999.0
    _toprank=[nm for nm in sorted(available_names,key=_rkk)
              if bidx.get(bb._norm(nm)) and _gradeable(bidx[bb._norm(nm)])][:GRADED_N]
    _missing=[nm for nm in _toprank if bb._norm(nm) not in _scored_by]
    _extra=_value_over_replacement(board, rosters, me, _missing, TREE_NS) if _missing else {}
    graded7=[]
    for nm in _toprank:
        k=bb._norm(nm); pp=bidx.get(k) or {}; src=_scored_by.get(k) or _extra.get(nm) or {}
        dt_,da_,dw_=src.get('dtitle'),src.get('dadv'),src.get('dw17')
        graded7.append({"name":nm,"pos":pp.get("pos"),"team":pp.get("team"),
            "rank":pp.get("rank"),"adp":pp.get("adp"),"playoff_up":round(float(pp.get("playoff_up") or 0),3),
            "dtitle":round(float(dt_),2) if dt_ is not None else None,
            "dadv":round(float(da_),1) if da_ is not None else None,
            "dw17":round(float(dw_),1) if dw_ is not None else None})
    # 4. Branch on realistic availability scenarios (best -> fallback).
    branch_cands = _select_branch_candidates(scored, overall, N_BRANCHES)
    branches = []
    for i, c in enumerate(branch_cands):
        is_fallback = (i == len(branch_cands) - 1)
        arche = _archetype(c["pos"], c, summary, w17)
        if i == 0:
            cond = f"if {c['name']} ({arche}) still on board"
        elif is_fallback:
            cond = f"else best available / need {c['pos']}"
        else:
            cond = f"else if {c['name']} ({arche}) is the best value"
        # 5. Look-ahead (plies=2): best follow-up at our next snake pick.
        then_node = None
        if plies >= 2:
            then_node = _lookahead_node(board, rosters, me, available_names, c["name"], seat,
                                        this_round, w17, TREE_NS)
        branches.append(_make_branch(c, this_round, summary, w17, cond, is_fallback, then_node))
    if len(branches) < 2 and len(scored) >= 2:
        c = scored[1]
        branches.append(_make_branch(c, this_round, summary, w17,
                                     f"else best available / need {c['pos']}", True))
    branches = branches[:4]
    # 6. Headline = recommended (best top-branch) pick.
    top = branch_cands[0]
    headline = {"take": top["name"], "dTitle": round(float(top["dtitle"]), 3),
                "dAdv": round(float(top["dadv"]), 3),
                "why": _headline_why(top, this_round, summary, w17)}
    # state block.
    roster_objs = []
    for nm in my_names:
        p = bidx.get(bb._norm(nm))
        if p:
            roster_objs.append({"name": p["name"], "pos": p["pos"], "team": p["team"]})
        else:
            roster_objs.append({"name": nm, "pos": "WR", "team": "FA"})
    state = {"pick": int(overall), "round": int(this_round), "seat": int(seat),
             "roster": roster_objs, "counts": summary["counts"], "anchor": _anchor_str(summary)}
    return {"state": state, "headline": headline, "graded7": graded7,
            "tree": {"label": f"Pick {overall} (R{this_round})", "branches": branches}}


def _headline_why(c, rnd, summary, w17):
    """A crisp human rationale for the recommended pick."""
    comp = c["components"]
    pos = c["pos"]
    have = summary["counts"].get(pos, 0)
    lo, hi = SEASON_TARGET[pos]
    arche = _archetype(pos, c, summary, w17)
    if c.get("adp") is not None:
        why = f"{arche} ({c['team']}, ADP {c['adp']:.0f}). "
    else:
        why = f"{arche} ({c['team']}). "
    why += f"Best blended d on the board: dTitle {c['dtitle']:+.2f}, dAdv {c['dadv']:+.1f}"
    why += f" (score {comp['score']:+.3f}). "
    why += f"{pos} {have}->{have + 1} vs target {lo}-{hi}; "
    if comp["stack"] > 0.001:
        why += "extends our game-stack; "
    if rnd <= 7:
        why += "advancement window - volume/floor + best ceiling-value (playoff_up ignored)."
    elif rnd <= 10:
        why += f"R{rnd} - starters set, playoff_up {c['playoff_up']:.2f} as tie-breaker."
    else:
        why += f"R{rnd} - playoff-ceiling driver: playoff_up {c['playoff_up']:.2f} (W15-17 lottery)."
    return why.strip()


__all__ = ["build_tree"]
