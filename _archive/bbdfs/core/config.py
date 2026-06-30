"""config — ONE home for the weights / thresholds the audit found scattered.

The audit counted >190 float literals across fusion (31), dfs_scenarios (61),
gameplan (18), draft_assistant (19), decision_tree (32), playoff_overlay (17), with
the SAME conceptual weight (e.g. 'ceiling importance') set independently in >=4 files
(fusion 0.75, gameplan 0.50, draft_assistant 0.42). Tuning one never propagated.

Import these instead of hard-coding. During migration, each engine swaps its private
literal for the corresponding name here; where the live values differ, reconcile to ONE
value and note it. Values marked (RECONCILE) are the current consolidation defaults —
confirm against the live module before flipping the import in that engine.
"""

# --- shared scoring weights (RECONCILE: fusion 0.75 / gameplan 0.50 / draft_assistant 0.42) ---
CEILING_WEIGHT = 0.50
SPIKE_WEIGHT = 0.25
ADV_WEIGHT = 0.25

# --- best-ball pick blend (engine/decision_tree: 0.6*dTitle + 0.4*dAdv) ---
BB_TITLE_W = 0.60
BB_ADV_W = 0.40

# --- gameplan team-attack weights (were 0.42/0.26/0.18/0.14) ---
ATTACK = {"ceil": 0.42, "env": 0.26, "pace": 0.18, "vac": 0.14}

# --- correlation / stacking (gameplan; spuriously-precise 3dp kept for parity) ---
R_QB_WR1 = 0.351
R_BRINGBACK = 0.159

# --- boom flag model (boom_lib.SHRINK_LAMBDA / SWING) ---
SHRINK_LAMBDA = 0.5  # backtest-calibrated; 0.25 is Brier-optimal, 0.5 ships
SWING = {
    "QB": (0.06, 0.19), "RB": (0.14, 0.25), "WR": (0.13, 0.29),
    "TE": (0.08, 0.33), "DST": (0.06, 0.30),
}

# --- DFS / playoff weekly ceiling bars (position weekly DK 'spike' threshold) ---
# (RECONCILE: confirm against dfs_scenarios.CEILING_BAR before adopting in dfs/board.py)
CEILING_BAR = {"QB": 26.0, "RB": 22.0, "WR": 22.0, "TE": 16.0, "DST": 13.0}

# --- fusion leverage thresholds (consensus hot/cold, divergence polarizing) ---
HOT_PCTL = 70.0
COLD_PCTL = 35.0
POLARIZING_DIV = 22.0

# --- platform playoff-cut rates (survival_chain: DK 50/50/10 vs UD pod-win) ---
CUT = {
    "DK": {"adv": 2.0 / 12.0, "w15": 0.50, "w16": 0.50, "w17": 0.10},
    "UD": {"adv": 2.0 / 12.0, "w15": 0.50, "w16": 0.50, "w17": 1.0 / 12.0},
}
