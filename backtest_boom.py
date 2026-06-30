#!/usr/bin/env python3
"""
backtest_boom.py — END-TO-END VALIDATION of the flag-based ceiling model.

The boom model has never been scored against outcomes. This reconstructs the model's
per-game ceiling probability for every 2025 active game we have a result for, then asks
three honest questions:

  1. CALIBRATION of the base rate  -- does a player's modeled base ceiling rate match his
     realized 2025 boom frequency? (Partly in-sample: base_blended uses 2025. Reported as a
     consistency check, not an out-of-sample claim.)
  2. DISCRIMINATION of the MATCHUP+ENV layer (the leak-free, never-tested part) -- the model
     rates some games as better setups than others via opponent-defense / home / dome
     multipliers. Do the games it rates higher actually boom more? Measured pooled (AUC of p
     vs boom) AND within-player (paired good-half vs bad-half boom rate, which removes the
     player base entirely, so it isolates the matchup signal).
  3. DECISION LIFT -- top-quintile predicted games boom at X%, bottom at Y%.

Multipliers mirror boom/AGENT_BRIEF.md guidance, reconstructed from the fields gamelog.json
actually carries (opp pass/run-defense percentile, home, dome). Pure stdlib+numpy.
"""
import json, os, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); B = os.path.join(HERE, 'boom')

# ---- load model state ----
gl = json.load(open(f"{B}/gamelog.json"))
FLAGS = {}
for pos in ('QB', 'RB', 'WR', 'TE', 'DST'):
    for k, v in json.load(open(f"{B}/flags_{pos}.json")).items():
        FLAGS[k] = {'pos': pos, 'base': (v.get('base') or 0) / 100.0,
                    'nflags': len(v.get('skill_flags', []))}

def cap(x, lo, hi): return max(lo, min(hi, x))

# ---- matchup+environment multiplier, reconstructed from gamelog fields per the brief ----
def setup_mult(pos, g):
    """Product of matchup + environment multipliers for one game (skill positions).
    Uses opp pass-defense pctl (opp_passp), run-defense pctl (opp_runp), home, dome.
    Higher pctl = TOUGHER defense. This is exactly the per-week activatable layer."""
    m = 1.0
    pp = g.get('opp_passp'); rp = g.get('opp_runp')
    if pos in ('QB', 'WR', 'TE'):
        if pp is not None:
            if pp <= 30: m *= 1.35
            elif pp <= 45: m *= 1.15
            elif pp >= 70: m *= 0.74
            elif pp >= 55: m *= 0.88
        if pp is not None and rp is not None and rp >= 60 and pp <= 45:  # pass funnel
            m *= 1.15
        if g.get('dome'): m *= 1.05
        if g.get('home'): m *= 1.03
    elif pos == 'RB':
        if rp is not None:
            if rp <= 30: m *= 1.32
            elif rp <= 45: m *= 1.13
            elif rp >= 70: m *= 0.76
            elif rp >= 55: m *= 0.89
        if pp is not None and rp is not None and pp >= 60 and rp <= 45:  # run funnel
            m *= 1.13
        if g.get('home'): m *= 1.03
    return m

def dst_mult(g):
    m = 1.0
    oq = g.get('opp_off_q'); qq = g.get('opp_qb_q')  # higher = better offense = tougher for DST
    if oq is not None:
        if oq <= 30: m *= 1.40
        elif oq <= 45: m *= 1.15
        elif oq >= 70: m *= 0.70
        elif oq >= 55: m *= 0.86
    if qq is not None and qq <= 35: m *= 1.12
    if g.get('home'): m *= 1.05
    return m

# ---- build per-game prediction table ----
rows = []  # (pos, base, p_full, p_base_only, mult, boom)
per_player = {}  # key -> list of (mult, p_full, boom)
for k, games in gl.items():
    meta = FLAGS.get(k)
    if not meta or not games: continue
    base, pos = meta['base'], meta['pos']
    if base <= 0: continue
    for g in games:
        if 'boom' not in g: continue
        m = dst_mult(g) if pos == 'DST' else setup_mult(pos, g)
        p_full = cap(base * m, 0.01, 0.80)
        rows.append((pos, base, p_full, base, m, int(g['boom'])))
        per_player.setdefault(k, []).append((m, p_full, int(g['boom'])))

pos_arr = np.array([r[0] for r in rows])
base_arr = np.array([r[1] for r in rows], float)
pfull = np.array([r[2] for r in rows], float)
mult = np.array([r[4] for r in rows], float)
boom = np.array([r[5] for r in rows], int)
N = len(rows)

def auc(score, y):
    """Mann-Whitney AUC (rank-based). Returns 0.5 if degenerate."""
    y = np.asarray(y); score = np.asarray(score, float)
    pos = score[y == 1]; neg = score[y == 0]
    if len(pos) == 0 or len(neg) == 0: return float('nan')
    order = np.argsort(score, kind='mergesort')
    ranks = np.empty(len(score), float); ranks[order] = np.arange(1, len(score) + 1)
    # average ranks for ties
    s = score[order]; i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and s[j + 1] == s[i]: j += 1
        if j > i:
            ranks[order[i:j + 1]] = (i + 1 + j + 1) / 2.0
        i = j + 1
    r_pos = ranks[y == 1].sum()
    return float((r_pos - len(pos) * (len(pos) + 1) / 2.0) / (len(pos) * len(neg)))

def brier(p, y): return float(np.mean((p - y) ** 2))

print(f"=== BACKTEST: {N} player-games with a 2025 result, {len(per_player)} players ===")
print(f"overall boom rate: {boom.mean():.3f}\n")

# 1. CALIBRATION of base
print("--- (1) BASE-RATE CALIBRATION (predicted base vs realized boom rate, by base decile) ---")
print("    note: base_blended includes 2025 -> partly in-sample; this is a consistency check")
dec = np.clip((base_arr * 10).astype(int), 0, 9)
print(f"    {'base bin':>10} {'n':>5} {'mean_base':>10} {'obs_boom':>9}")
for d in range(10):
    mk = dec == d
    if mk.sum() >= 15:
        print(f"    {d/10:.1f}-{d/10+0.1:.1f}    {mk.sum():>5} {base_arr[mk].mean():>10.3f} {boom[mk].mean():>9.3f}")
# rank correlation base vs boom (player level)
pl_pred = []; pl_obs = []
for k, gs in per_player.items():
    pl_pred.append(FLAGS[k]['base']); pl_obs.append(np.mean([b for _, _, b in gs]))
pl_pred = np.array(pl_pred); pl_obs = np.array(pl_obs)
def spearman(a, b):
    ra = np.argsort(np.argsort(a)); rb = np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])
print(f"    player-level Spearman(modeled base, realized boom rate) = {spearman(pl_pred, pl_obs):.3f}\n")

# 2. DISCRIMINATION
print("--- (2) DISCRIMINATION ---")
print(f"    AUC base-only          : {auc(base_arr, boom):.3f}")
print(f"    AUC base x matchup/env : {auc(pfull, boom):.3f}   (full model)")
print(f"    AUC matchup mult alone : {auc(mult, boom):.3f}   (env layer only, base removed)")
print(f"    Brier base-only        : {brier(base_arr, boom):.3f}")
print(f"    Brier full model       : {brier(pfull, boom):.3f}")
# within-player paired test: isolate matchup signal (removes base completely)
hi_booms = hi_n = lo_booms = lo_n = 0
flips = 0
for k, gs in per_player.items():
    if len(gs) < 4: continue
    ms = np.array([m for m, _, _ in gs]); bs = np.array([b for _, _, b in gs])
    med = np.median(ms)
    hi = bs[ms > med]; lo = bs[ms <= med]
    if len(hi) and len(lo):
        hi_booms += hi.sum(); hi_n += len(hi); lo_booms += lo.sum(); lo_n += len(lo)
        if hi.mean() > lo.mean(): flips += 1
print(f"    WITHIN-PLAYER (base removed): better-setup half boom {hi_booms}/{hi_n}={hi_booms/max(hi_n,1):.3f}"
      f"  vs worse half {lo_booms}/{lo_n}={lo_booms/max(lo_n,1):.3f}")
print()

# 3. LIFT
print("--- (3) DECISION LIFT (quintiles of full-model p) ---")
q = np.argsort(pfull); n5 = N // 5
botix = q[:n5]; topix = q[-n5:]
print(f"    top-quintile p boom rate : {boom[topix].mean():.3f}  (mean p {pfull[topix].mean():.3f})")
print(f"    bot-quintile p boom rate : {boom[botix].mean():.3f}  (mean p {pfull[botix].mean():.3f})")
lift = boom[topix].mean() / max(boom[botix].mean(), 1e-9)
print(f"    lift top/bottom          : {lift:.2f}x\n")

# by position
print("--- by position (full-model AUC) ---")
for p in ('QB', 'RB', 'WR', 'TE', 'DST'):
    mk = pos_arr == p
    if mk.sum() >= 20:
        print(f"    {p:>4} n={mk.sum():>4} boom={boom[mk].mean():.3f} AUC_full={auc(pfull[mk],boom[mk]):.3f} AUC_base={auc(base_arr[mk],boom[mk]):.3f}")

out = {
    'n_player_games': N, 'n_players': len(per_player), 'overall_boom_rate': round(float(boom.mean()), 4),
    'auc_base_only': round(auc(base_arr, boom), 4), 'auc_full': round(auc(pfull, boom), 4),
    'auc_matchup_alone': round(auc(mult, boom), 4),
    'brier_base': round(brier(base_arr, boom), 4), 'brier_full': round(brier(pfull, boom), 4),
    'within_player_better_half_boom': round(hi_booms / max(hi_n, 1), 4),
    'within_player_worse_half_boom': round(lo_booms / max(lo_n, 1), 4),
    'lift_top_bottom_quintile': round(float(lift), 3),
    'top_quintile_boom': round(float(boom[topix].mean()), 4), 'bot_quintile_boom': round(float(boom[botix].mean()), 4),
    'player_base_spearman': round(spearman(pl_pred, pl_obs), 4),
}
json.dump(out, open(f"{B}/backtest_results.json", 'w'), indent=1)
print("wrote boom/backtest_results.json")
