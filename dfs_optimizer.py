#!/usr/bin/env python3
"""
dfs_optimizer.py — DraftKings NFL Classic (GPP) lineup optimizer.

This is the executable half of STACKING_RULESET.md. It does three things:

  1. BUILD   — a pulp ILP picks a legal DK Classic roster (QB/2RB/3WR/TE/FLEX/DST,
               $50k cap) that MAXIMIZES projected points, subject to the stacking
               rules encoded as hard constraints.
  2. DIVERSIFY — it re-solves with "no-good" overlap cuts to generate a whole pool
               of structurally-different lineups (a GPP needs many darts, not one).
  3. RANK    — every candidate is scored by a *correlation-aware ceiling*
               (mean + 1.28·σ_lineup), where σ_lineup is built from the measured
               2015–2025 DK correlation structure. The stacking constraints put the
               correlation INTO each lineup; the ceiling ranking surfaces the lineups
               that used it best.

The separation is deliberate and honest: the ILP objective is expected value (you
can't linearly maximize a standard deviation), the *structure* that creates upside
is enforced by constraints, and the nonlinear ceiling is applied as a post-hoc rank.

Every rule below cites the STACKING_RULESET.md rule it enforces.

USAGE
  # Demo / backtest on a real historical DK slate (build on Proj_Score, grade on Actual_Pts):
  python3 dfs_optimizer.py --period 2024-week-10 --n 20 --pool 60

  # Live: feed your own projections CSV (name,pos,team,opp,game_id,salary,proj[,team_total,game_total])
  python3 dfs_optimizer.py --csv my_projections.csv --n 20

  # As a library:
  from dfs_optimizer import load_pool_fc, optimize, rule_report
  pool = load_pool_fc('2024-week-10')
  lineups = optimize(pool, n_lineups=20, pool_size=60)
"""
from __future__ import annotations
import argparse, csv, gzip, io, json, math, os, sys
from dataclasses import dataclass, field
from collections import defaultdict, Counter

try:
    import pulp
except ImportError:
    sys.exit("pulp is required:  pip install pulp --break-system-packages")

# ======================================================================================
# MEASURED CORRELATION STRUCTURE  (STACKING_RULESET.md — actual DK points, 2015–2025)
# ======================================================================================

# Position coefficient of variation: per-player boom spread σ = CV · projection.
# WR/TE are the spikiest single-game scorers; QB the steadiest; DST the wildest.
CV = {'QB': 0.45, 'RB': 0.65, 'WR': 0.85, 'TE': 0.90, 'DST': 1.10}

# --- SAME-TEAM pairwise correlations (the backbone of a stack) --------------------------
#   QB↔own WR by depth rank (by salary): WR1 0.35, WR2 0.30 (rising), WR3 0.18 (fading)
#   QB↔own TE 0.25 · QB↔own RB 0.10 · own WR↔WR ~0 (they cannibalize) · own RB↔RB slight −
QB_WR_BY_RANK = {1: 0.35, 2: 0.30, 3: 0.18}   # WR4+ → 0.15
QB_WR_DEEP    = 0.15

# --- OPPOSITE-TEAM (same game) correlations — "bring-back" territory --------------------
#   QB↔opp WR 0.07 (leverage, ~1/5 the same-team link) · opp WR↔WR 0.07 · opp RB↔RB −0.02
RHO_OPP = {
    frozenset(('QB', 'WR')): 0.07, frozenset(('QB', 'TE')): 0.06,
    frozenset(('QB', 'RB')): -0.05, frozenset(('QB', 'QB')): 0.10,
    frozenset(('WR', 'WR')): 0.07, frozenset(('WR', 'TE')): 0.05,
    frozenset(('RB', 'RB')): -0.02, frozenset(('WR', 'RB')): -0.02,
    frozenset(('TE', 'TE')): 0.05, frozenset(('TE', 'RB')): -0.02,
}
# DST vs the opposing offense is negative (a good D suppresses their points); a modest,
# clearly-labeled prior (the study measured skill players, not DST).
RHO_DST_OPP  = {'QB': -0.20, 'WR': -0.12, 'RB': -0.10, 'TE': -0.10, 'DST': 0.0}
RHO_DST_SAME = {'QB': 0.05, 'WR': 0.0, 'RB': 0.10, 'TE': 0.0, 'DST': 0.0}

Z_CEIL = 1.28   # ~90th-pct ceiling multiplier: lineup ceiling = mean + Z·σ_lineup

# ======================================================================================
# STACKING POLICY  (STACKING_RULESET.md rules 2, 3, 5, 8 — refresh the lists yearly)
# ======================================================================================

# Rule 3 — the +2-viable concentration list: QBs whose 2nd pass-catcher genuinely rises
P2_QBS = {'Dak Prescott', 'Jared Goff', 'Joe Burrow', 'Matthew Stafford',
          'Tua Tagovailoa', 'Brock Purdy'}
# Rule 3/8 — rushing QBs: their "second guy" is an RB → use QB+1+bring-back, cap +1
RUSH_QBS = {'Lamar Jackson', 'Jalen Hurts', 'Jayden Daniels', 'Josh Allen'}
# Rule 3 — the field overstacks these; cap at +1
OVERSTACK_QBS = {'Patrick Mahomes', 'Trevor Lawrence', 'Bryce Young',
                 'Geno Smith', 'Aaron Rodgers', 'Drake Maye'}

P2_MIN_TOTAL = 24.0    # Rule 2(b): a +2 needs the QB's team implied total ≥ 24
BRINGBACK_MIN_TOTAL = 47.0   # Rule 5: a bring-back's edge lives in high-total games only

SALARY_CAP = 50000
ROSTER = {'QB': 1, 'RB': 2, 'WR': 3, 'TE': 1, 'DST': 1}   # + 1 FLEX (RB/WR/TE) = 9

# ======================================================================================
# DATA MODEL
# ======================================================================================

@dataclass
class Player:
    name: str
    pos: str            # QB / RB / WR / TE / DST
    team: str
    opp: str
    game_id: str
    salary: int
    proj: float         # projection used to BUILD the lineup (never peeks at outcome)
    actual: float | None = None   # realized DK points — ONLY used to grade a backtest
    wr_rank: int = 0    # depth rank among own-team WRs by salary (1 = WR1)
    team_total: float | None = None
    game_total: float | None = None
    proj_own: float = 0.0   # projected GPP ownership proxy (set by estimate_ownership)

    @property
    def p2_eligible(self) -> bool:
        """May this QB anchor a +2? (Rule 2: on the concentration list AND team total ≥ 24)"""
        if self.pos != 'QB':
            return False
        if self.name in OVERSTACK_QBS or self.name in RUSH_QBS:
            return False
        tt = self.team_total if self.team_total is not None else 0.0
        return (self.name in P2_QBS) and (tt >= P2_MIN_TOTAL)


@dataclass
class Lineup:
    players: list          # list[Player], length 9
    mean: float = 0.0      # Σ projection
    sd: float = 0.0        # correlation-aware lineup standard deviation
    ceiling: float = 0.0   # mean + Z·sd  (the GPP ranking key)
    actual: float | None = None   # Σ realized points (backtest only)
    archetype: str = ''    # portfolio archetype that produced this lineup

    def salary(self):
        return sum(p.salary for p in self.players)

    def qb(self):
        return next(p for p in self.players if p.pos == 'QB')

    def key(self):
        return frozenset(id(p) for p in self.players)


# ======================================================================================
# CORRELATION → LINEUP CEILING
# ======================================================================================

def pair_rho(a: Player, b: Player) -> float:
    """Correlation between two rostered players, from the measured structure."""
    if a.game_id != b.game_id:
        return 0.0                                   # different games → independent
    if 'DST' in (a.pos, b.pos):
        dst, oth = (a, b) if a.pos == 'DST' else (b, a)
        if oth.pos == 'DST':
            return 0.0
        return (RHO_DST_SAME if dst.team == oth.team else RHO_DST_OPP).get(oth.pos, 0.0)
    if a.team == b.team:                             # ---- same team ----
        s = {a.pos, b.pos}
        if 'QB' in s and s != {'QB'}:
            oth, rank = (b, b.wr_rank) if a.pos == 'QB' else (a, a.wr_rank)
            if oth.pos == 'WR':
                return QB_WR_BY_RANK.get(rank, QB_WR_DEEP)
            if oth.pos == 'TE':
                return 0.25
            if oth.pos == 'RB':
                return 0.10
        if s == {'WR'}:          return 0.00         # own WRs cannibalize targets
        if s == {'RB'}:          return -0.10
        if s == {'WR', 'TE'}:    return 0.05
        if s == {'WR', 'RB'}:    return 0.02
        if s == {'RB', 'TE'}:    return 0.02
        return 0.0
    return RHO_OPP.get(frozenset((a.pos, b.pos)), 0.0)   # ---- opposite team, same game ----


def score_lineup(L: Lineup) -> Lineup:
    """Fill mean / sd / ceiling using the correlation-aware covariance sum."""
    ps = L.players
    sig = [CV.get(p.pos, 0.8) * max(p.proj, 0.0) for p in ps]
    mean = sum(p.proj for p in ps)
    var = sum(s * s for s in sig)
    for i in range(len(ps)):
        for j in range(i + 1, len(ps)):
            var += 2.0 * pair_rho(ps[i], ps[j]) * sig[i] * sig[j]
    L.mean = mean
    L.sd = math.sqrt(max(var, 0.0))
    L.ceiling = mean + Z_CEIL * L.sd
    if all(p.actual is not None for p in ps):
        L.actual = sum(p.actual for p in ps)
    return L


# ======================================================================================
# THE ILP  (STACKING_RULESET.md rules 1, 2, 6 as hard constraints)
# ======================================================================================

def _build_problem(pool, salary_cap, min_salary, bringback, require_stack,
                   locked=None, banned=None, bonus=None,
                   min_stack=None, max_stack=None, qb_pool=None, dueling_game=None):
    """Construct the pulp problem. Returns (prob, x) with x[i] the pick indicator.

    `bonus` (dict) adds a SMALL generation-time reward, in projection-point units, for the
    correlated structures the ruleset endorses — so the generated pool actually CONTAINS
    leverage builds for the ceiling ranker to pick from. It never relaxes a constraint, and
    the reported mean/ceiling use the honest projection (the bonus is generation-only).
        bonus = {'bringback': 1.5, 'plus2': 1.0, 'wr12': 0.5}

    Archetype levers (all optional, used by the portfolio builder):
        min_stack   : force ≥ this many own pass-catchers with the QB (0 = naked ok)
        max_stack   : cap own pass-catchers with the QB at this many (0 = force naked)
        qb_pool     : restrict the QB to this set of names (e.g. rushing QBs only)
        dueling_game: (teamA, teamB) — force ≥1 skill player from EACH side, QBs of that
                      game banned → a deliberate two-sided "naked game" leverage block
    """
    bonus = bonus or {}
    prob = pulp.LpProblem('dk_classic', pulp.LpMaximize)
    x = {i: pulp.LpVariable(f'x_{i}', cat='Binary') for i in range(len(pool))}
    idx = range(len(pool))
    P = pool
    obj_bonus = []          # (weight, aux_var) terms appended to the objective

    def by(pos):    return [i for i in idx if P[i].pos == pos]
    QBs, RBs, WRs, TEs, DSTs = map(by, ('QB', 'RB', 'WR', 'TE', 'DST'))
    flexable = RBs + WRs + TEs

    # ---- roster shape: QB1 / RB2+ / WR3+ / TE1+ / DST1 / total 9 (the extra is FLEX) ----
    prob += pulp.lpSum(x[i] for i in QBs) == 1
    prob += pulp.lpSum(x[i] for i in DSTs) == 1
    prob += pulp.lpSum(x[i] for i in RBs) >= 2
    prob += pulp.lpSum(x[i] for i in WRs) >= 3
    prob += pulp.lpSum(x[i] for i in TEs) >= 1
    prob += pulp.lpSum(x[i] for i in RBs) <= 3      # FLEX can only add one
    prob += pulp.lpSum(x[i] for i in WRs) <= 4
    prob += pulp.lpSum(x[i] for i in TEs) <= 2
    prob += pulp.lpSum(x[i] for i in flexable) == 7   # 9 − QB − DST
    prob += pulp.lpSum(x[i] for i in idx) == 9

    # ---- salary cap (and optional floor to not leave value on the table) ----
    prob += pulp.lpSum(P[i].salary * x[i] for i in idx) <= salary_cap
    if min_salary > 0:
        prob += pulp.lpSum(P[i].salary * x[i] for i in idx) >= min_salary

    # ---- group helpers by team / game ----
    team_pc = defaultdict(list)   # pass-catchers (WR/TE) by team
    team_qb = defaultdict(list)   # QBs by team
    team_rb = defaultdict(list)   # RBs by team
    for i in idx:
        if P[i].pos in ('WR', 'TE'):
            team_pc[P[i].team].append(i)
        elif P[i].pos == 'QB':
            team_qb[P[i].team].append(i)
        elif P[i].pos == 'RB':
            team_rb[P[i].team].append(i)

    BIGM = 9

    for t, qbs in team_qb.items():
        Qt  = pulp.lpSum(x[i] for i in qbs)                       # 1 if this team's QB is in
        PCt = pulp.lpSum(x[i] for i in team_pc.get(t, []))        # own pass-catchers rostered
        P2t = pulp.lpSum(x[i] for i in qbs if P[i].p2_eligible)   # 1 if a +2-eligible QB is in

        # Rule 1 — QB + 1 mandatory: if this team's QB is in, ≥1 own pass-catcher.
        if require_stack and (min_stack is None or min_stack >= 1):
            prob += PCt >= max(1, min_stack or 1) * Qt
        elif min_stack:
            prob += PCt >= min_stack * Qt
        # Rule 2 — cap the stack at +1, or +2 only for a Rule-3 QB in a 24+ total.
        prob += PCt <= 1 + P2t + BIGM * (1 - Qt)
        # archetype tightening (never loosens Rule 2): force naked (0) or exact caps
        if max_stack is not None:
            prob += PCt <= max_stack + BIGM * (1 - Qt)

        opp = P[qbs[0]].opp
        opp_pc = [i for i in idx if P[i].team == opp and P[i].pos in ('WR', 'TE')]
        gt = P[qbs[0]].game_total or 0.0

        # Rule 5 — bring-back: an opposing pass-catcher, only offered as leverage.
        if bringback == 'require' and opp_pc:
            prob += pulp.lpSum(x[i] for i in opp_pc) >= Qt

        # ---- generation-time correlation bonuses (never constraints) ----
        if bonus.get('bringback') and opp_pc and gt >= BRINGBACK_MIN_TOTAL:
            # reward a bring-back, but ONLY in a high-total game (Rule 5)
            bb = pulp.LpVariable(f'bb_{t}', cat='Binary')
            prob += bb <= Qt
            prob += bb <= pulp.lpSum(x[i] for i in opp_pc)
            obj_bonus.append(bonus['bringback'] * bb)
        if bonus.get('plus2'):
            # reward a genuine +2 for a P2-eligible QB (Rule 2/3)
            s2 = pulp.LpVariable(f's2_{t}', cat='Binary')
            prob += s2 <= P2t                 # only if a +2-eligible QB is in
            prob += 2 * s2 <= PCt             # only if ≥2 own pass-catchers
            obj_bonus.append(bonus['plus2'] * s2)
        if bonus.get('wr12'):
            # Rule 4 — prefer the stack partner be WR1/WR2, not WR3+
            top = [i for i in team_pc.get(t, [])
                   if P[i].pos == 'WR' and 1 <= P[i].wr_rank <= 2]
            if top:
                w = pulp.LpVariable(f'w12_{t}', cat='Binary')
                prob += w <= Qt
                prob += w <= pulp.lpSum(x[i] for i in top)
                obj_bonus.append(bonus['wr12'] * w)

    # Rule 6 — never roster RBs from BOTH sides of a game (they're anti-correlated).
    game_sides = defaultdict(dict)
    for t, rbs in team_rb.items():
        # find the game + opponent for this team's RBs
        if rbs:
            gid = P[rbs[0]].game_id
            game_sides[gid][t] = rbs
    for gid, sides in game_sides.items():
        if len(sides) == 2:
            (ta, ra), (tb, rb) = list(sides.items())
            z = pulp.LpVariable(f'rbside_{gid}', cat='Binary')
            prob += pulp.lpSum(x[i] for i in ra) <= 3 * z
            prob += pulp.lpSum(x[i] for i in rb) <= 3 * (1 - z)

    # ---- archetype: restrict the QB to a named pool (e.g. rushing QBs for naked builds) ----
    if qb_pool is not None:
        for i in QBs:
            if P[i].name not in qb_pool:
                prob += x[i] == 0

    # ---- archetype: force a deliberate two-sided duel on a chosen non-QB game ----
    if dueling_game is not None:
        ta, tb = dueling_game
        skill_a = [i for i in idx if P[i].team == ta and P[i].pos in ('WR', 'TE', 'RB')]
        skill_b = [i for i in idx if P[i].team == tb and P[i].pos in ('WR', 'TE', 'RB')]
        if skill_a and skill_b:
            prob += pulp.lpSum(x[i] for i in skill_a) >= 1
            prob += pulp.lpSum(x[i] for i in skill_b) >= 1
        for i in idx:                                   # QB must come from elsewhere
            if P[i].pos == 'QB' and P[i].team in (ta, tb):
                prob += x[i] == 0

    # ---- locks / bans (used by the diversification loop and manual overrides) ----
    for i in (locked or []):
        prob += x[i] == 1
    for i in (banned or []):
        prob += x[i] == 0

    # ---- objective: expected value (projection) + generation-time correlation bonus ----
    prob += pulp.lpSum(P[i].proj * x[i] for i in idx) + pulp.lpSum(obj_bonus)

    return prob, x


def _generate(pool, count, max_overlap, salary_cap, min_salary, bringback,
              require_stack, bonus, **arche):
    """Generate up to `count` diverse legal lineups via no-good overlap cuts.
    Returns [(Lineup, chosen_idx)] sorted by ceiling desc. `arche` = archetype levers."""
    prob, x = _build_problem(pool, salary_cap, min_salary, bringback, require_stack,
                             bonus=bonus, **arche)
    solver = pulp.PULP_CBC_CMD(msg=0)
    gen = []
    for _ in range(count):
        if pulp.LpStatus[prob.solve(solver)] != 'Optimal':
            break
        chosen = [i for i in range(len(pool)) if x[i].value() and x[i].value() > 0.5]
        if len(chosen) != 9:
            break
        gen.append((score_lineup(Lineup([pool[i] for i in chosen])), chosen))
        prob += pulp.lpSum(x[i] for i in chosen) <= max_overlap   # overlap cut vs this build
    gen.sort(key=lambda t: t[0].ceiling, reverse=True)
    return gen


def _select_exposure(generated, n_lineups, max_exposure):
    """Greedy exposure-capped pick from a ceiling-ranked (Lineup, idx) list."""
    out, used = [], defaultdict(int)
    cap = max(1, math.ceil(max_exposure * n_lineups))
    for L, chosen in generated:
        if len(out) >= n_lineups:
            break
        if max_exposure < 1.0 and any(used[i] >= cap for i in chosen):
            continue
        out.append(L)
        for i in chosen:
            used[i] += 1
    if len(out) < n_lineups:                       # exposure cap starved us — backfill
        have = {L.key() for L in out}
        for L, _ in generated:
            if len(out) >= n_lineups:
                break
            if L.key() not in have:
                out.append(L)
    return out[:n_lineups]


def optimize(pool, n_lineups=20, pool_size=None, max_overlap=6, min_salary=0,
             bringback='allow', require_stack=True, salary_cap=SALARY_CAP,
             max_exposure=1.0, bonus=None, verbose=False):
    """
    Single-template mode: generate a diverse pool of legal, rule-compliant lineups and
    return the top `n_lineups` by correlation-aware ceiling. (See optimize_portfolio for
    a build that spans the whole distribution of winning shapes.)
    """
    if pool_size is None:
        pool_size = max(n_lineups * 3, n_lineups)
    if bonus is None:
        bonus = {'bringback': 1.5, 'plus2': 1.0, 'wr12': 0.5}
    for i, p in enumerate(pool):
        p._i = i
    generated = _generate(pool, pool_size, max_overlap, salary_cap, min_salary,
                          bringback, require_stack, bonus)
    if verbose:
        print(f"  generated {len(generated)} diverse lineups", file=sys.stderr)
    return _select_exposure(generated, n_lineups, max_exposure)


# ======================================================================================
# MULTI-ARCHETYPE PORTFOLIO  (span the distribution of winning shapes, not one template)
# ======================================================================================
#
# The winning-structure study (winning_structures.py) shows no single lineup shape wins
# more than ~40% of weeks, and the mix shifts with the slate's game environment. So instead
# of ranking one template, we allocate the field across ARCHETYPES — each a different bet on
# how the slate breaks — then ceiling-rank within each. Default weights start from the decade
# winner distribution, tilted toward stacks (correlation is a forward-only edge that hindsight
# doesn't need), and shift by the slate's top game total.

ARCHETYPES = {
    # name            build levers (passed to _generate)                         blurb
    'naked_rush':  dict(require_stack=False, min_stack=0, max_stack=0,
                        qb_pool='RUSH', bonus={}),                    # rushing QB, no stack
    'balanced':    dict(require_stack=True, bonus={'wr12': 0.6}),     # QB+1, best value spread
    'bringback':   dict(require_stack=True, bringback='require',
                        bonus={'wr12': 0.6}),                         # QB+1 + game bring-back
    'double':      dict(require_stack=True, min_stack=2,
                        qb_pool='P2', bonus={'plus2': 1.5}),          # QB+2 onslaught (eligible)
    'game_stack':  dict(require_stack=True, min_stack=2, bringback='require',
                        qb_pool='P2', bonus={'plus2': 1.5, 'bringback': 1.5}),  # full game
    'duel':        dict(require_stack=True, bonus={'wr12': 0.4},
                        dueling_game='TOP'),                          # naked two-sided shootout
}

# base (mid-total) allocation — forward-tilted from the hindsight winner distribution
BASE_WEIGHTS = {'naked_rush': 0.22, 'balanced': 0.34, 'bringback': 0.22,
                'double': 0.08, 'game_stack': 0.08, 'duel': 0.06}


def _env_weights(pool):
    """Shift the archetype mix by the slate's game environment (top game total)."""
    totals = [p.game_total for p in pool if p.game_total is not None]
    top = max(totals) if totals else 45.0
    w = dict(BASE_WEIGHTS)
    if top >= 49:            # shootout slate → more bring-back / game-stack / double, less naked
        w = {'naked_rush': 0.15, 'balanced': 0.30, 'bringback': 0.25,
             'double': 0.12, 'game_stack': 0.12, 'duel': 0.06}
    elif top <= 44:          # grind slate → more naked (rushing-QB floor), fewer game-stacks
        w = {'naked_rush': 0.32, 'balanced': 0.36, 'bringback': 0.14,
             'double': 0.05, 'game_stack': 0.03, 'duel': 0.10}
    return w, top


def _top_game(pool):
    """The slate's highest-total game as (teamA, teamB) — the duel target."""
    best, bt = None, -1
    seen = {}
    for p in pool:
        seen.setdefault(p.game_id, (p.team, p.opp, p.game_total or 0))
    for gid, (a, b, gt) in seen.items():
        if gt > bt:
            bt, best = gt, (a, b)
    return best


def optimize_portfolio(pool, n_lineups=20, weights=None, max_overlap=7, min_salary=0,
                       salary_cap=SALARY_CAP, max_exposure=0.5, verbose=False):
    """
    Build a PORTFOLIO of lineups spread across winning archetypes, sized by how often each
    shape wins (conditioned on the slate's game environment). Returns a flat list of Lineups,
    each tagged with .archetype. Within each archetype, lineups are ceiling-ranked + diversified;
    across the whole set a global exposure cap keeps the field from collapsing onto one core.
    """
    for i, p in enumerate(pool):
        p._i = i
    rush_names = {p.name for p in pool if p.name in RUSH_QBS}
    p2_names = {p.name for p in pool if p.p2_eligible}
    top_game = _top_game(pool)
    if weights is None:
        weights, top = _env_weights(pool)
    else:
        top = max((p.game_total for p in pool if p.game_total is not None), default=45.0)

    # allocate integer lineup counts across archetypes (largest-remainder)
    raw = {k: weights.get(k, 0) * n_lineups for k in ARCHETYPES}
    alloc = {k: int(v) for k, v in raw.items()}
    while sum(alloc.values()) < n_lineups:
        k = max(ARCHETYPES, key=lambda k: raw[k] - alloc[k])
        alloc[k] += 1

    if verbose:
        print(f"  slate top total {top:.1f} → allocation " +
              ", ".join(f"{k}:{alloc[k]}" for k in ARCHETYPES if alloc[k]), file=sys.stderr)

    all_out = []
    qb_used = defaultdict(int)
    # cap QB exposure (the primary diversification axis — the QB defines the stack); a punt
    # DST/RB shared across lineups must NOT starve an archetype, so we cap QBs, not chalk.
    qb_cap = max(2, math.ceil(max_exposure * n_lineups))
    for name, spec in ARCHETYPES.items():
        want = alloc.get(name, 0)
        if want <= 0:
            continue
        lev = dict(spec)
        # resolve symbolic qb_pool / dueling_game to concrete values for this slate
        qbp = lev.pop('qb_pool', None)
        if qbp == 'RUSH':
            lev['qb_pool'] = rush_names or None      # no rushing QB on slate → unrestricted
        elif qbp == 'P2':
            lev['qb_pool'] = p2_names or None
        if lev.get('dueling_game') == 'TOP':
            lev['dueling_game'] = top_game
        require_stack = lev.pop('require_stack', True)
        bringback = lev.pop('bringback', 'allow')
        bonus = lev.pop('bonus', {})
        # infeasible archetype (e.g. 'double'/'game_stack' with no P2 QB) → skip gracefully
        if qbp == 'P2' and not p2_names:
            if verbose:
                print(f"    {name:11s} skipped (no P2-eligible QB on slate)", file=sys.stderr)
            continue
        gen = _generate(pool, want * 5, max_overlap, salary_cap, min_salary,
                        bringback, require_stack, bonus, **lev)
        # prefer QB-diverse builds, but GUARANTEE the archetype's quota (backfill if capped)
        picked, taken = [], set()
        for L, chosen in gen:                        # ceiling-ranked within archetype
            if len(picked) >= want:
                break
            qi = L.qb()._i
            if qb_used[qi] >= qb_cap:
                continue
            picked.append((L, chosen)); taken.add(id(L)); qb_used[qi] += 1
        for L, chosen in gen:                        # backfill ignoring the cap
            if len(picked) >= want:
                break
            if id(L) not in taken:
                picked.append((L, chosen)); taken.add(id(L))
        for L, chosen in picked:
            L.archetype = name
            all_out.append((L, chosen))
        if verbose:
            print(f"    {name:11s} wanted {want}, filled {len(picked)}", file=sys.stderr)

    # final ceiling ordering across the whole portfolio (keep archetype tag)
    all_out.sort(key=lambda t: t[0].ceiling, reverse=True)
    return [L for L, _ in all_out[:n_lineups]]


# ======================================================================================
# RULE COMPLIANCE REPORT  (proves the constraints actually fired)
# ======================================================================================

def audit_lineup(L: Lineup) -> dict:
    """Return a per-lineup dict describing its stack structure vs the rules."""
    qb = L.qb()
    own_pc = [p for p in L.players if p.team == qb.team and p.pos in ('WR', 'TE')]
    opp_pc = [p for p in L.players if p.team == qb.opp and p.pos in ('WR', 'TE')]
    # dueling RBs (should never happen)
    by_game = defaultdict(lambda: defaultdict(list))
    for p in L.players:
        if p.pos == 'RB':
            by_game[p.game_id][p.team].append(p)
    dueling_rb = any(len(sides) == 2 for sides in by_game.values())
    stack_n = len(own_pc)
    return {
        'qb': qb.name, 'qb_team': qb.team, 'qb_total': qb.team_total,
        'stack': f"QB+{stack_n}", 'stack_partners': [p.name for p in own_pc],
        'p2_used': stack_n >= 2, 'p2_allowed': qb.p2_eligible,
        'bringback': [p.name for p in opp_pc],
        'dueling_rb': dueling_rb,
        'salary': L.salary(), 'mean': L.mean, 'sd': L.sd,
        'ceiling': L.ceiling, 'actual': L.actual,
    }


def portfolio_summary(lineups) -> str:
    """Compositional read of the whole returned set — what structures the menu contains."""
    n = len(lineups)
    if not n:
        return "empty portfolio"
    stacks = defaultdict(int)      # QB+1 / QB+2
    bb = 0
    qbs = defaultdict(int)
    for L in lineups:
        a = audit_lineup(L)
        stacks[a['stack']] += 1
        if a['bringback']:
            bb += 1
        qbs[a['qb']] += 1
    shape = ', '.join(f"{k}: {v} ({v/n:.0%})" for k, v in sorted(stacks.items()))
    top_qbs = ', '.join(f"{q} {c}" for q, c in sorted(qbs.items(), key=lambda t: -t[1])[:5])
    lines = ["PORTFOLIO COMPOSITION", "-" * 66,
             f"  stack shape : {shape}",
             f"  bring-backs : {bb}/{n} ({bb/n:.0%})   [Rule 5: leverage in high-total games]",
             f"  unique QBs  : {len(qbs)}   most-used: {top_qbs}"]
    arch = Counter(L.archetype for L in lineups if L.archetype)
    if arch:
        amix = ', '.join(f"{k}: {v} ({v/n:.0%})" for k, v in arch.most_common())
        lines.insert(2, f"  archetypes  : {amix}")
    return "\n".join(lines)


def rule_report(lineups) -> str:
    """Human-readable proof that every returned lineup obeys the rule set."""
    lines, viol = [], 0
    for k, L in enumerate(lineups, 1):
        a = audit_lineup(L)
        flags = []
        # naked is a rule VIOLATION only when a stack was intended; the naked_rush archetype
        # (Rule 8 — rushing QB, no stack) is a legitimate, deliberate shape.
        if len(a['stack_partners']) < 1 and L.archetype != 'naked_rush':
            flags.append('NO QB+1 (naked)')
        if a['p2_used'] and not a['p2_allowed']:
            flags.append('ILLEGAL +2')
        if a['dueling_rb']:
            flags.append('DUELING RBs')
        if L.salary() > SALARY_CAP:
            flags.append('OVER CAP')
        if flags:
            viol += 1
        tag = ('  ⚠ ' + '; '.join(flags)) if flags else ''
        bb = f" | bring-back: {', '.join(a['bringback'])}" if a['bringback'] else ""
        act = f" | actual {a['actual']:.1f}" if a['actual'] is not None else ""
        arch = f"[{L.archetype}] " if L.archetype else ""
        lines.append(
            f"  #{k:<2} {arch}{a['stack']:<6} {a['qb']:<17} ({a['qb_team']}, tot {a['qb_total']})"
            f"  ${a['salary']:,}  ceil {a['ceiling']:.1f}{act}{bb}{tag}\n"
            f"        stack: {', '.join(a['stack_partners']) or '—'}")
    head = f"RULE COMPLIANCE — {len(lineups)} lineups, {viol} violation(s)\n" + "-" * 66
    return head + "\n" + "\n".join(lines)


# ======================================================================================
# DATA LOADERS
# ======================================================================================

DATA_DIR = os.environ.get('FC_DATA_DIR', '/mnt/user-data/uploads/Fantasy')

def _assign_wr_ranks(players):
    by_team = defaultdict(list)
    for p in players:
        if p.pos == 'WR':
            by_team[p.team].append(p)
    for team, ws in by_team.items():
        for rank, p in enumerate(sorted(ws, key=lambda q: -q.salary), start=1):
            p.wr_rank = rank


def load_pool_fc(period, players_gz=None, games_gz=None):
    """Load a real historical DK slate from the FantasyCruncher decade pull."""
    players_gz = players_gz or os.path.join(DATA_DIR, 'fc_players_slim.csv.gz')
    games_gz   = games_gz   or os.path.join(DATA_DIR, 'fc_games_all.csv.gz')

    totals = {}   # (period, team) -> (team_total, game_total)
    with gzip.open(games_gz, 'rt') as f:
        for r in csv.DictReader(f):
            if r['period'] == period:
                try:
                    totals[(r['period'], r['Team'])] = (float(r['team_total']),
                                                         float(r['game_total']))
                except (ValueError, KeyError):
                    pass

    pool = []
    with gzip.open(players_gz, 'rt') as f:
        for r in csv.DictReader(f):
            if r['period'] != period:
                continue
            try:
                sal = int(float(r['Salary']))
                proj = float(r['Proj_Score'])
                act = float(r['Actual_Pts'])
            except (ValueError, KeyError):
                continue
            if sal <= 0:
                continue
            tt, gt = totals.get((period, r['Team']), (None, None))
            pool.append(Player(
                name=r['PlayerName'], pos=r['PlayerPos'], team=r['Team'],
                opp=r['opp'], game_id=r['GameId'], salary=sal, proj=proj,
                actual=act, team_total=tt, game_total=gt))
    _assign_wr_ranks(pool)
    return pool


def load_pool_csv(path):
    """Load a live slate. Required cols: name,pos,team,opp,game_id,salary,proj.
    Optional: actual,team_total,game_total."""
    pool = []
    with open(path, newline='') as f:
        for r in csv.DictReader(f):
            g = lambda k, d=None: r.get(k, d)
            pool.append(Player(
                name=r['name'], pos=r['pos'].upper(), team=r['team'],
                opp=g('opp', ''), game_id=g('game_id', r.get('team', '')),
                salary=int(float(r['salary'])), proj=float(r['proj']),
                actual=float(r['actual']) if g('actual') not in (None, '') else None,
                team_total=float(r['team_total']) if g('team_total') not in (None, '') else None,
                game_total=float(r['game_total']) if g('game_total') not in (None, '') else None))
    _assign_wr_ranks(pool)
    return pool


def estimate_ownership(pool):
    """Projected GPP ownership proxy from projection + salary ONLY (no outcome leak).

    Ownership is driven by value (projected points per $1k) plus a stud-projection term; within
    each position we normalize so ownerships sum to that position's expected roster slots — which
    yields realistic levels (chalk studs ~30–45%, punts low). Sets p.proj_own in place. This is a
    proxy for measuring lineup UNIQUENESS/duplication; real contest ownership would be sharper.
    """
    SLOTS = {'QB': 1.0, 'RB': 2.4, 'WR': 3.6, 'TE': 1.2, 'DST': 1.0}   # incl. FLEX share
    BETA, GAMMA = 1.1, 0.5
    bypos = defaultdict(list)
    for p in pool:
        p.proj_own = 0.0
        bypos[p.pos].append(p)

    def z(vals):
        n = len(vals); m = sum(vals) / n
        sd = (sum((v - m) ** 2 for v in vals) / n) ** 0.5
        return [(v - m) / sd if sd > 1e-9 else 0.0 for v in vals]

    for pos, ps in bypos.items():
        act = [p for p in ps if p.proj > 0 and p.salary > 0]
        if not act:
            continue
        zp = z([p.proj / (p.salary / 1000.0) for p in act])   # points per $1k
        zr = z([p.proj for p in act])                          # raw projection (studs)
        w = [math.exp(BETA * a + GAMMA * b) for a, b in zip(zp, zr)]
        tot = sum(w); slots = SLOTS.get(pos, 1.0)
        for p, wi in zip(act, w):
            p.proj_own = min(wi / tot * slots, 0.65)
    return pool


# ======================================================================================
# CLI
# ======================================================================================

def main():
    ap = argparse.ArgumentParser(description="DK Classic GPP optimizer (STACKING_RULESET.md)")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument('--period', help="historical FC slate, e.g. 2024-week-10 (demo/backtest)")
    src.add_argument('--csv', help="live projections CSV")
    ap.add_argument('--n', type=int, default=20, help="lineups to return")
    ap.add_argument('--pool', type=int, default=None, help="lineups to generate before ranking")
    ap.add_argument('--overlap', type=int, default=6, help="max shared players between lineups")
    ap.add_argument('--min-salary', type=int, default=0)
    ap.add_argument('--bringback', choices=['off', 'allow', 'require'], default='allow')
    ap.add_argument('--no-stack', action='store_true', help="allow naked QB builds (Rule 8)")
    ap.add_argument('--exposure', type=float, default=1.0, help="max player exposure 0–1")
    ap.add_argument('--portfolio', action='store_true',
                    help="multi-archetype portfolio spanning the winning-shape distribution")
    ap.add_argument('--show', type=int, default=10, help="how many lineups to print")
    args = ap.parse_args()

    pool = load_pool_csv(args.csv) if args.csv else load_pool_fc(args.period)
    label = args.csv or args.period
    print(f"\nLoaded {len(pool)} players from {label} "
          f"({sum(p.pos=='QB' for p in pool)} QB / {sum(p.pos=='RB' for p in pool)} RB / "
          f"{sum(p.pos=='WR' for p in pool)} WR / {sum(p.pos=='TE' for p in pool)} TE / "
          f"{sum(p.pos=='DST' for p in pool)} DST)")

    if args.portfolio:
        exposure = args.exposure if args.exposure < 1.0 else 0.5
        lineups = optimize_portfolio(pool, n_lineups=args.n, max_overlap=max(args.overlap, 7),
                                     min_salary=args.min_salary, max_exposure=exposure,
                                     verbose=True)
    else:
        lineups = optimize(pool, n_lineups=args.n, pool_size=args.pool,
                           max_overlap=args.overlap, min_salary=args.min_salary,
                           bringback=args.bringback, require_stack=not args.no_stack,
                           max_exposure=args.exposure, verbose=True)
    if not lineups:
        sys.exit("No feasible lineups — loosen constraints (salary floor / overlap / stack).")

    mode = "multi-archetype portfolio" if args.portfolio else "single-template, ceiling-ranked"
    print(f"\nReturned {len(lineups)} lineups ({mode}).\n")
    print(portfolio_summary(lineups))
    print()
    print(rule_report(lineups[:args.show]))

    # backtest summary if actuals are present
    if all(L.actual is not None for L in lineups):
        acts = sorted((L.actual for L in lineups), reverse=True)
        best = max(lineups, key=lambda L: L.actual)
        print("\n" + "-" * 66)
        print(f"BACKTEST (graded on real DK points)")
        print(f"  top-ceiling lineup scored : {lineups[0].actual:.1f}")
        print(f"  best of the {len(lineups)} lineups     : {acts[0]:.1f}")
        print(f"  mean / median of the set  : {sum(acts)/len(acts):.1f} / {acts[len(acts)//2]:.1f}")
        ba = audit_lineup(best)
        arch = f"[{best.archetype}] " if best.archetype else ""
        print(f"  highest-scoring build     : {arch}{ba['stack']} {ba['qb']} → "
              f"{', '.join(ba['stack_partners'])}"
              + (f" | bring-back {', '.join(ba['bringback'])}" if ba['bringback'] else ""))
        # the GPP lesson: the tournament-winning lineup is usually NOT the top-ceiling chalk
        rank_of_best = sorted(range(len(lineups)),
                              key=lambda i: -lineups[i].ceiling).index(lineups.index(best)) + 1
        print(f"  → that lineup ranked #{rank_of_best} of {len(lineups)} by ceiling "
              f"(the winner is rarely the chalk-ceiling build)")
        if any(L.archetype for L in lineups):
            byA = defaultdict(list)
            for L in lineups:
                byA[L.archetype].append(L.actual)
            print("  outcomes by archetype (max | mean):")
            for a, vs in sorted(byA.items(), key=lambda kv: -max(kv[1])):
                print(f"      {a:11s} {max(vs):6.1f} | {sum(vs)/len(vs):5.1f}   (n={len(vs)})")

    # top lineup, full roster
    print("\n" + "-" * 66 + "\nTOP-CEILING LINEUP (full roster)")
    top = lineups[0]
    for slot_pos in ['QB', 'RB', 'WR', 'TE', 'DST']:
        for p in [q for q in top.players if q.pos == slot_pos]:
            mark = ''
            if p.team == top.qb().team and p.pos in ('WR', 'TE'):
                mark = '  ← stack'
            elif p.team == top.qb().opp and p.pos in ('WR', 'TE'):
                mark = '  ← bring-back'
            act = f"  (actual {p.actual:.1f})" if p.actual is not None else ""
            print(f"  {p.pos:<3} {p.name:<20} {p.team:<4} ${p.salary:<5} proj {p.proj:5.1f}{act}{mark}")
    print(f"  ${top.salary():,} | mean {top.mean:.1f} | sd {top.sd:.1f} | ceiling {top.ceiling:.1f}"
          + (f" | ACTUAL {top.actual:.1f}" if top.actual is not None else ""))
    print()


if __name__ == '__main__':
    main()
