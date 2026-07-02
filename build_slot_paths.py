#!/usr/bin/env python3
"""
build_slot_paths.py -> slot_paths.json

"What is actually gettable from each draft slot" engine for a 12-team, 18-round BBM snake draft
(216 total picks).

AVAILABILITY MODEL
==================
P(player with ADP `a` is still available at overall pick N) = 1 - Phi((N - a) / sd(a))

where:
    Phi     = standard normal CDF
    sd(a)   = max(3.0, 0.12 * a)

The standard deviation grows linearly with ADP to reflect that late-round picks have much higher
variance than early ones (a pick-6 player going 1-3 slots early/late vs a pick-100 player
swinging 15+ spots). The 3.0 floor prevents the earliest picks from having implausibly tight
distributions (real drafts have some variance even at pick 1 due to team-specific strategies).

LIMITS OF THIS MODEL
====================
1. No injury news: the availability distribution assumes a healthy, static board; news-driven
   crashes or surges are not reflected.
2. No room-specific hot/cold streaks: real-time pick runs (positional runs, QB frenzies) compress
   or expand availability faster than the normal CDF model predicts.
3. Point-in-time: the model is built on a single ADP snapshot; ADP drift over the draft season is
   not tracked.
4. Assumes independence: in practice, a positional run at picks N-5 through N-2 means several
   players' p_avail collapses together; the model treats each player independently.

DECISION ZONE DEFINITION
=========================
For each slot x round, a candidate is in the decision zone when:
    p_avail(this_pick) >= 0.35   AND   p_avail(next_slot_pick) <= 0.90

Meaning: gettable now (35%+ chance), but there is real risk of losing them before the next turn
(i.e., next-turn availability drops to 90% or below). For round 18 (no next pick), only the
p_avail(this_pick) >= 0.35 filter applies.

The threshold 0.35 is the "genuine contention" floor — below it the player is likely already
gone. The 0.90 ceiling on next-pick filters out players who are so available that taking them now
is a non-decision (you could easily wait). Together they define the true "act now or probably lose
them" window.

FIX 3 — BACK-TO-BACK TURN EXCLUSION:
When a slot's next pick is <=2 picks away (i.e., both picks of a back-to-back turn happen in
consecutive overall picks), the p_next <= 0.90 urgency filter is SKIPPED for the current pick.
At a turn (e.g. slot 12: picks 12->13), the next pick is only 1 pick away — any player gettable
now is equally gettable on the very next pick, so requiring p_next<=0.90 would exclude obvious
targets like A.J. Brown (ADP ~9, 99% available at both picks). The two back-to-back picks are
effectively one decision window.

SIMPLEST DEFENSIBLE CHOICES
============================
- Board ADP is used as the spine for pick-availability calculations (flag_ranks.json `adp` field).
- UD ADP is attached per player where a name-match exists via core.fn() (exact normalized join,
  no fuzzy guessing for this lookup), for display purposes only.
- Market rank is defined as rank ascending by board ADP (1 = lowest ADP = most coveted).
- value_flag = adj_rank <= market_rank (model ranks the player AT OR BETTER THAN the market).
  FIX 4: unified to <= to match stack_menu.py (which already used <=). The definition is:
  "model agrees this player is at or above their market price" — consistent across both files.
- For ties in adj_rank ordering, secondary sort is by name (deterministic output).
"""
import os
import sys
import json
import math
import datetime
import csv

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Imports from canonical core
# ---------------------------------------------------------------------------
sys.path.insert(0, HERE)
from core import fn, safe_json_dump, norm_team

# ---------------------------------------------------------------------------
# Normal CDF via math.erfc (stdlib, no scipy dependency)
# ---------------------------------------------------------------------------
def normal_cdf(x):
    """Standard normal CDF Phi(x) = P(Z <= x)."""
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


def sd(adp):
    """Pick-variance model: sd grows linearly with ADP, floor at 3.0."""
    return max(3.0, 0.12 * adp)


def p_avail(adp, pick_n):
    """Probability the player (ADP=adp) is still available at overall pick N.

    P = 1 - Phi((N - adp) / sd(adp))

    When pick_n < adp (pick is before the player's ADP), p_avail > 0.5 (probably still there).
    When pick_n == adp, p_avail == 0.5.
    When pick_n >> adp, p_avail -> 0 (almost certainly gone).
    """
    return 1.0 - normal_cdf((pick_n - adp) / sd(adp))


# ---------------------------------------------------------------------------
# Snake draft: pick numbers for each slot across 18 rounds
# ---------------------------------------------------------------------------
def snake_picks(n_teams=12, n_rounds=18):
    """Return dict {slot (1..n_teams): [pick_number, ...]} for a snake draft.

    Round r (1-indexed), slot s (1..n_teams):
      Odd round:  overall pick = (r-1)*n_teams + s
      Even round: overall pick = (r-1)*n_teams + (n_teams + 1 - s)
    """
    picks = {s: [] for s in range(1, n_teams + 1)}
    for r in range(1, n_rounds + 1):
        for s in range(1, n_teams + 1):
            if r % 2 == 1:  # odd round: left to right
                overall = (r - 1) * n_teams + s
            else:            # even round: right to left
                overall = (r - 1) * n_teams + (n_teams + 1 - s)
            picks[s].append(overall)
    return picks


# ---------------------------------------------------------------------------
# Load inputs
# ---------------------------------------------------------------------------
def load_board():
    """Load flag_ranks.json players dict."""
    path = os.path.join(HERE, 'flag_ranks.json')
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    return data['players']


def load_ud_adp():
    """Load Underdog ADP CSV: {fn(name): float adp}.

    The CSV has headers: name, position, adp.
    Join key is core.fn() normalized name (exact match only, no fuzzy guessing).
    """
    path = os.path.join(
        HERE, 'ffdataroma_draft_guide_export', 'ffdataroma', 'csv', 'underdog-adp.csv'
    )
    ud = {}
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = fn(row['name'])
            try:
                ud[key] = float(row['adp'])
            except (ValueError, KeyError):
                pass
    return ud


def load_team_ceiling():
    """Load team_ceiling.json: {team_abbr: {ceiling_score, tier, ...}}."""
    path = os.path.join(HERE, 'team_ceiling.json')
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    return data['teams']


def load_schedule():
    """Load schedule2026.json: {team: [{wk, opp, home, dome}, ...]}.

    Returns {team: week_17_opponent}.
    """
    path = os.path.join(HERE, 'boom', 'schedule2026.json')
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    w17 = {}
    for team, weeks in data.items():
        for w in weeks:
            if w.get('wk') == 17:
                w17[team] = w.get('opp', '')
                break
    return w17


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------
def main():
    N_TEAMS = 12
    N_ROUNDS = 18
    TOP_BOARD = 216   # picks in the draft
    ZONE_TOP = 14     # max candidates per decision zone
    P_AVAIL_MIN = 0.35   # minimum availability at THIS pick to enter zone
    P_NEXT_MAX = 0.90    # maximum availability at NEXT pick to enter zone (genuine urgency)

    # --- load inputs ---
    players_raw = load_board()
    ud_adp_map = load_ud_adp()
    team_ceiling = load_team_ceiling()
    w17_map = load_schedule()

    # --- sort board by ADP (ascending); assign market_rank ---
    players_sorted = sorted(
        players_raw.values(),
        key=lambda p: (p['adp'] if p['adp'] is not None else 9999, p['name'])
    )

    # market_rank: position in ADP-ascending order (1-indexed); ties broken by name
    for mrank, p in enumerate(players_sorted, 1):
        p['_market_rank'] = mrank

    # --- UD ADP coverage: how many of the top-216 board players have a UD ADP ---
    top_216 = players_sorted[:TOP_BOARD]
    ud_hits = 0
    for p in top_216:
        key = fn(p['name'])
        if key in ud_adp_map:
            ud_hits += 1
    ud_coverage_pct = round(100.0 * ud_hits / len(top_216), 1)

    print(f"UD ADP coverage: {ud_hits}/{len(top_216)} top-216 board players have a UD ADP "
          f"({ud_coverage_pct}%)")

    # --- build lookup tables for fast candidate evaluation ---
    # For each player, pre-build: adp, adj_rank, market_rank, team, pos, ud_adp, team_ceiling_tier, w17_opp
    candidates_pool = []
    for p in top_216:
        team = norm_team(p.get('team', ''))
        key = fn(p['name'])
        ud = ud_adp_map.get(key)   # None if no UD ADP found

        tc = team_ceiling.get(team, {})
        tier = tc.get('tier', None) if isinstance(tc, dict) else None

        w17_opp = w17_map.get(team, None)

        candidates_pool.append({
            'name': p['name'],
            'pos': p.get('pos', ''),
            'team': team,
            'adp': round(p['adp'], 3),
            'ud_adp': round(ud, 3) if ud is not None else None,
            'adj_rank': p['adj_rank'],
            'market_rank': p['_market_rank'],
            'team_ceiling_tier': tier,
            'w17_opp': w17_opp,
        })

    # --- compute snake pick lists ---
    slot_picks = snake_picks(N_TEAMS, N_ROUNDS)

    # sanity check: every pick 1..216 appears exactly once per round across all slots
    all_picks = [pk for picks in slot_picks.values() for pk in picks]
    assert sorted(all_picks) == list(range(1, N_TEAMS * N_ROUNDS + 1)), \
        "Snake pick sanity FAIL: 1..216 not covered exactly once"
    # per-round check
    for r in range(1, N_ROUNDS + 1):
        round_picks = sorted(slot_picks[s][r - 1] for s in range(1, N_TEAMS + 1))
        expected = list(range((r - 1) * N_TEAMS + 1, r * N_TEAMS + 1))
        assert round_picks == expected, f"Round {r} pick mismatch: {round_picks} != {expected}"
    print("Sanity check PASSED: every slot has 18 picks; picks 1..216 covered once per round.")

    # --- build slot_paths output ---
    slots_out = {}
    all_player_names_seen = set()

    for slot in range(1, N_TEAMS + 1):
        picks = slot_picks[slot]  # list of 18 overall pick numbers
        rounds_out = {}

        for r_idx, this_pick in enumerate(picks):
            r = r_idx + 1

            # next pick for this slot (for the urgency filter)
            if r < N_ROUNDS:
                next_pick = picks[r_idx + 1]
            else:
                next_pick = None  # round 18: no next turn

            # FIX 3: back-to-back turn detection.
            # When the next slot pick is <=2 overall picks away (e.g., slot 12 picks
            # 12->13, or slot 1 picks 24->25), both picks are effectively one decision
            # window — skip the p_next urgency filter for the current pick so that
            # obvious top targets (A.J. Brown, Chase, etc.) are not excluded.
            is_near_turn = (next_pick is not None and (next_pick - this_pick) <= 2)

            # --- build decision zone ---
            zone = []
            for cand in candidates_pool:
                adp = cand['adp']
                pa_this = p_avail(adp, this_pick)

                if pa_this < P_AVAIL_MIN:
                    continue  # almost certainly gone

                if next_pick is not None:
                    pa_next = p_avail(adp, next_pick)
                    if not is_near_turn and pa_next > P_NEXT_MAX:
                        continue  # still easily gettable next turn; not urgent
                        # (urgency filter skipped at back-to-back turn picks: FIX 3)
                else:
                    pa_next = None  # round 18: skip urgency filter

                # value_flag: model ranks this player AT OR BETTER THAN market rank.
                # FIX 4: unified to <= (adj_rank <= market_rank) to match stack_menu.py.
                # Both files now use the same "model likes at market price or better" definition.
                value_flag = cand['adj_rank'] <= cand['market_rank']

                zone.append({
                    'name': cand['name'],
                    'pos': cand['pos'],
                    'team': cand['team'],
                    'adp': cand['adp'],
                    'ud_adp': cand['ud_adp'],
                    'adj_rank': cand['adj_rank'],
                    'p_avail': round(pa_this, 4),
                    'p_next': round(pa_next, 4) if pa_next is not None else None,
                    'team_ceiling_tier': cand['team_ceiling_tier'],
                    'w17_opp': cand['w17_opp'],
                    'value_flag': value_flag,
                })

            # sort zone: best adj_rank first (lower = better), then by name for determinism
            zone.sort(key=lambda x: (x['adj_rank'], x['name']))

            # keep top ZONE_TOP
            zone = zone[:ZONE_TOP]

            for z in zone:
                all_player_names_seen.add(z['name'])

            rounds_out[str(r)] = zone

        slots_out[str(slot)] = {
            'picks': picks,
            'rounds': rounds_out,
        }

    # --- build _meta ---
    meta = {
        'model': 'availability = 1 - Phi((N - adp) / sd(adp)); sd(a) = max(3.0, 0.12*a)',
        'model_params': {
            'p_avail_min': P_AVAIL_MIN,
            'p_next_max': P_NEXT_MAX,
            'sd_formula': 'max(3.0, 0.12 * adp)',
            'zone_top_k': ZONE_TOP,
        },
        'ud_adp_coverage': {
            'top_216_with_ud_adp': ud_hits,
            'top_216_total': len(top_216),
            'coverage_pct': ud_coverage_pct,
        },
        'draft_format': {
            'n_teams': N_TEAMS,
            'n_rounds': N_ROUNDS,
            'total_picks': N_TEAMS * N_ROUNDS,
            'format': 'snake',
        },
        'built_date': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'board_source': 'flag_ranks.json (adj_rank + adp)',
        'ud_adp_source': 'ffdataroma_draft_guide_export/ffdataroma/csv/underdog-adp.csv',
        'team_ceiling_source': 'team_ceiling.json',
        'schedule_source': 'boom/schedule2026.json',
        'surfaces': ['predraft'],
    }

    output = {
        '_meta': meta,
        'slots': slots_out,
    }

    out_path = os.path.join(HERE, 'slot_paths.json')
    safe_json_dump(output, out_path, indent=0)
    print(f"Wrote {out_path}")

    # --- console verification ---
    print()
    print("=" * 60)
    print("CONSOLE VERIFICATION")
    print("=" * 60)

    # Spot-check slots 1, 6, 12 for rounds 1..3 (top 5 candidates each)
    for slot in [1, 6, 12]:
        print(f"\nSlot {slot} (round-1 pick: {slot_picks[slot][0]}):")
        for r in range(1, 4):
            rdata = slots_out[str(slot)]['rounds'][str(r)]
            pick_n = slot_picks[slot][r - 1]
            print(f"  Round {r} (pick #{pick_n})  -> {len(rdata)} candidates in zone")
            for i, c in enumerate(rdata[:5]):
                vf = '*' if c['value_flag'] else ' '
                p_next_str = 'N/A' if c['p_next'] is None else f"{c['p_next']:.3f}"
                print(f"    {i+1}. {vf}{c['name']:25s} pos={c['pos']:2s} "
                      f"adp={c['adp']:6.1f} adj_rank={c['adj_rank']:3d} "
                      f"p_avail={c['p_avail']:.3f} p_next={p_next_str}")

    print()
    print(f"Total distinct players appearing in any decision zone: {len(all_player_names_seen)}")
    print(f"UD ADP coverage: {ud_hits}/{len(top_216)} ({ud_coverage_pct}%)")

    # Final sanity re-checks
    n_slots = len(slots_out)
    n_rounds_per_slot = [len(v['rounds']) for v in slots_out.values()]
    assert n_slots == N_TEAMS, f"Expected {N_TEAMS} slots, got {n_slots}"
    assert all(r == N_ROUNDS for r in n_rounds_per_slot), \
        f"Not all slots have {N_ROUNDS} rounds: {n_rounds_per_slot}"
    print(f"Sanity: {n_slots} slots x {N_ROUNDS} rounds each = OK")


if __name__ == '__main__':
    main()
