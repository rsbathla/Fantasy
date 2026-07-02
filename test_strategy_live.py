#!/usr/bin/env python3
"""Synthetic test of the strategy-live integration.

Two test scenarios:
  A. User at slot 6, 5 picks matching 6A's plan (ON PLAN).
  B. User at slot 6, WR-heavy off-plan picks (DRIFTING / OFF PLAN).

Runs engine/strategy_live.py directly WITHOUT the full run_live pipeline
(no simulation required), by constructing a minimal tree dict that mirrors
the real payload shape.

Usage:  python3 test_strategy_live.py
"""
import os, sys, json

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(HERE, 'engine')
sys.path.insert(0, ENGINE)

import strategy_live as sl

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _norm(n):
    import re
    n = str(n).strip().lower()
    n = re.sub(r"\s+(jr|sr|ii|iii|iv|v)\.?$", "", n)
    n = n.replace(".", "").replace("'", "").replace("-", " ")
    return " ".join(n.split())


def _load_board_names():
    """Load draftable player names from merged_rankings_upload.csv."""
    import pandas as pd
    path = os.path.join(HERE, 'pipeline', 'merged_rankings_upload.csv')
    df = pd.read_csv(path)
    names = df['Name'].dropna().tolist()
    return names


def _build_tree(seat, my_roster_picks, cur_round, top_branch_takes=None):
    """Build a minimal tree dict mimicking the live_tree.json payload shape.

    Parameters
    ----------
    seat : int
        Draft slot (1-12).
    my_roster_picks : list of (name, pos, team) tuples
        Players already drafted by the user (in draft order).
    cur_round : int
        Current draft round (next pick round).
    top_branch_takes : list of str, optional
        Player names in the grader's top branches (for synergy tag).
    """
    # Load available players = board minus taken
    try:
        all_names = _load_board_names()
    except Exception:
        all_names = []

    taken_norm = {_norm(n) for n, _, _ in my_roster_picks}
    board = [
        {'name': n, 'pos': 'WR', 'team': 'XXX'}
        for n in all_names
        if _norm(n) not in taken_norm
    ][:200]

    counts = {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0}
    for _, pos, _ in my_roster_picks:
        if pos in counts:
            counts[pos] += 1

    state = {
        'seat': seat,
        'round': cur_round,
        'pick': (cur_round - 1) * 12 + seat,  # approximate
        'my_roster': [n for n, _, _ in my_roster_picks],
        'roster': [{'name': n, 'pos': p, 'team': t} for n, p, t in my_roster_picks],
        'counts': counts,
    }

    branches = []
    if top_branch_takes:
        for take in top_branch_takes:
            branches.append({
                'take': take, 'pos': 'WR', 'team': 'XXX',
                'dTitle': 1.5, 'dAdv': 3.0, 'dW17': 1.0,
                'cond': f'if {take} available', 'reason': 'test branch'
            })

    tree = {
        'state': state,
        'board': board,
        'tree': {'label': f'Pick (R{cur_round})', 'branches': branches},
        'headline': {'take': top_branch_takes[0] if top_branch_takes else None,
                     'dTitle': 1.5, 'dAdv': 3.0},
        'roster_detail': [{'name': n, 'pos': p, 'team': t} for n, p, t in my_roster_picks],
    }
    return tree


# ---------------------------------------------------------------------------
# Scenario A: Slot 6, ON PLAN — 5 picks matching 6A exactly
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("SCENARIO A: Slot 6 | 5 picks matching 6A (ON PLAN expected)")
print("=" * 70)

# 6A round plan: R1=Jeanty, R2=Pickens, R3=Kyren Williams, R4=Jameson Williams, R5=Rome Odunze
roster_A = [
    ('Ashton Jeanty', 'RB', 'LV'),       # R1 primary
    ('George Pickens', 'WR', 'DAL'),      # R2 primary
    ('Kyren Williams', 'RB', 'LAR'),      # R3 primary
    ('Jameson Williams', 'WR', 'DET'),    # R4 primary
    ('Rome Odunze', 'WR', 'CHI'),         # R5 primary
]

tree_A = _build_tree(
    seat=6,
    my_roster_picks=roster_A,
    cur_round=6,
    top_branch_takes=['Dak Prescott', 'Caleb Williams']  # grader's picks (Dak = synergy for 6A)
)

result_A = sl.analyse(tree_A, HERE)

print(f"\n  Slot detected : {result_A['slot']} (expected: 6)")
bf_A = result_A.get('best_fit') or {}
print(f"  Best-fit      : {bf_A.get('id','?')} — {bf_A.get('name','?')[:50]}")
print(f"  Adherence     : {bf_A.get('adherence','?')} (expected: ON PLAN)")
print(f"  Score         : {bf_A.get('score','?'):.2f}")
print(f"  Breakdown     : {bf_A.get('score_breakdown','?')}")

print(f"\n  All strategy scores:")
for s in result_A.get('strategies', []):
    marker = " <-- BEST" if s['id'] == bf_A.get('id') else ""
    print(f"    {s['id']}: {s['score']:.2f} ({s['adherence']}){marker}")

print(f"\n  Live targets for R6 (expecting Dak Prescott + synergy):")
for t in result_A.get('live_targets', []):
    avail = "AVAIL" if t['available'] else "GONE"
    prim = "PRIMARY" if t['is_primary'] else "pivot"
    syn = " [SYNERGY]" if t['synergy'] else ""
    stk = " [STACK]" if t['stack_pick'] else ""
    tier = t.get('tier', '?')
    print(f"    {t['name']} ({t['pos']}, {t['team']}) — {avail} | {prim} | tier={tier}{stk}{syn}")

print(f"\n  Stack status:")
for ss in result_A.get('stack_status', []):
    print(f"    {ss['team']} ({ss['tier']}, score={ss['ceiling_score']})")
    print(f"      held: {ss['held']}")
    print(f"      available_remaining: {ss['available_remaining'][:3]}")
    print(f"      bringbacks: {[b['name'] for b in ss['bringbacks_available'][:3]]}")

print(f"\n  Checkpoints:")
for cp in result_A.get('checkpoints', []):
    print(f"    R{cp['round']}: target={cp['target']} current={cp['current']} at_risk={cp['at_risk']} impossible={cp['impossible']}")

print(f"\n  Floor warnings: {result_A.get('floor_warnings', [])}")
print(f"\n  Leverage note (first 120 chars): {result_A.get('leverage_pivot','')[:120]}")

# ASSERTIONS
print("\n  --- ASSERTIONS ---")
assert result_A['slot'] == 6, f"FAIL: slot={result_A['slot']} expected 6"
print("  [PASS] slot == 6")
assert bf_A.get('id') == '6A', f"FAIL: best_fit={bf_A.get('id')} expected 6A"
print("  [PASS] best_fit == 6A")
assert bf_A.get('adherence') == 'ON PLAN', f"FAIL: adherence={bf_A.get('adherence')} expected ON PLAN"
print("  [PASS] adherence == ON PLAN")
# Dak Prescott (6A R6 primary) should be in live targets
tgt_names = {t['name'] for t in result_A.get('live_targets', [])}
assert 'Dak Prescott' in tgt_names, f"FAIL: Dak Prescott not in live targets: {tgt_names}"
print("  [PASS] Dak Prescott in live targets")
# Dak synergy = True (he's in grader's top branch takes)
dak_entry = next((t for t in result_A.get('live_targets', []) if t['name'] == 'Dak Prescott'), None)
if dak_entry:
    assert dak_entry.get('synergy') == True, f"FAIL: Dak synergy={dak_entry.get('synergy')} expected True"
    print("  [PASS] Dak Prescott synergy=True")
# DAL stack should appear in stack_status (Dak is R6 stack_pick=True for 6A)
stack_teams = [ss['team'] for ss in result_A.get('stack_status', [])]
assert 'DAL' in stack_teams, f"FAIL: DAL not in stack_status: {stack_teams}"
print("  [PASS] DAL in stack_status")
print("\n  SCENARIO A: ALL ASSERTIONS PASSED")


# ---------------------------------------------------------------------------
# Scenario B: Slot 6, WR-heavy off-plan (DRIFTING/OFF PLAN expected)
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("SCENARIO B: Slot 6 | WR-heavy off-plan picks (DRIFTING or OFF PLAN)")
print("=" * 70)

# Off-plan: took WR-WR-WR-WR instead of the 6A/6B/6C plans
roster_B = [
    ('CeeDee Lamb', 'WR', 'DAL'),          # R1 — 6B pivot but not 6A/6C primary
    ('Drake London', 'WR', 'ATL'),          # R2 — not primary/pivot for most strategies
    ('Tee Higgins', 'WR', 'CIN'),           # R3 — not in 6A/6B/6C R3
    ('DeVonta Smith', 'WR', 'PHI'),         # R4 — 6A/6B pivot only (R2 pivot, wrong round)
    ('DK Metcalf', 'WR', 'SEA'),            # R5 — not in any plan
]

tree_B = _build_tree(
    seat=6,
    my_roster_picks=roster_B,
    cur_round=6,
    top_branch_takes=['Dak Prescott']
)

result_B = sl.analyse(tree_B, HERE)

print(f"\n  Slot detected : {result_B['slot']} (expected: 6)")
bf_B = result_B.get('best_fit') or {}
print(f"  Best-fit      : {bf_B.get('id','?')}")
print(f"  Adherence     : {bf_B.get('adherence','?')} (expected: DRIFTING or OFF PLAN)")
print(f"  Score         : {bf_B.get('score','?'):.2f}")

print(f"\n  All strategy scores:")
for s in result_B.get('strategies', []):
    marker = " <-- BEST" if s['id'] == bf_B.get('id') else ""
    print(f"    {s['id']}: {s['score']:.2f} ({s['adherence']}){marker}")

print(f"\n  Floor warnings: {result_B.get('floor_warnings', [])}")

print("\n  --- ASSERTIONS ---")
assert result_B['slot'] == 6, f"FAIL: slot={result_B['slot']} expected 6"
print("  [PASS] slot == 6")
assert bf_B.get('adherence') in ('DRIFTING', 'OFF PLAN'), \
    f"FAIL: adherence={bf_B.get('adherence')} expected DRIFTING or OFF PLAN"
print(f"  [PASS] adherence == {bf_B.get('adherence')} (honest drifting/off-plan detection)")
# Score should be lower than Scenario A
score_A = bf_A.get('score', 0)
score_B = bf_B.get('score', 0)
assert score_B < score_A, f"FAIL: off-plan score {score_B:.2f} >= on-plan score {score_A:.2f}"
print(f"  [PASS] off-plan score ({score_B:.2f}) < on-plan score ({score_A:.2f})")
print("\n  SCENARIO B: ALL ASSERTIONS PASSED")

print("\n" + "=" * 70)
print("ALL SYNTHETIC TESTS PASSED")
print("=" * 70)
