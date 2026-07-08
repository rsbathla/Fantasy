#!/usr/bin/env python3
"""backtest_correlation.py — calibrate the PLAYER-LEVEL bring-back correlation (QB vs opposing WR1)
to the empirical total-split in correlation_structure.json.

Target (nflverse, correlation_structure.json.bringback_qb_oppwr1):
    all r=0.129 (n=910) · high_total r=0.159 (n=440) · low_total r=0.062 (n=470) · median total 45.0

Mechanism under test: replace survival_chain's FULLY-shared per-game shock (both teams get the
identical g -> one fixed bring-back for every game) with PARTIAL sharing
        g_team = sqrt(rho)*g_shared + sqrt(1-rho)*g_own,     corr(g_A,g_B) = rho
where rho rises with the game total. This leaves INTRA-team correlation untouched (both a team's
QB and WR1 still ride the same g_team) and bends only the cross-team bring-back.

Stage 1 here MEASURES: current intra qb_wr1 (sanity vs 0.351), and the rho -> bring-back transfer
function across the real 2026 matchups. Calibration (stage 2) uses that transfer function.
Run from the pipeline/ dir:  python3 backtest_correlation.py
"""
import numpy as np, pandas as pd, json, os, sys
import warnings; warnings.filterwarnings('ignore')

# pull gen_team + pp + tp + SG/ST from the production sim (the pre-distribution prelude only)
exec(open('sim_prod.py').read().split("# build distribution")[0])
print(f"loaded sim_prod prelude: SG(shared-shock)={SG} ST(team-shock)={ST} | {len(pp)} players, {len(tp)} teams")

# ---- real 2026 unique matchups ----
games = json.load(open('games_by_week.json'))
pairs = set()
for w, gl in games.items():
    for a, b in gl:
        if a in tp.index and b in tp.index:
            pairs.add(tuple(sorted((a, b))))
pairs = sorted(pairs)

def qb_of(t):
    q = pp[(pp.team == t) & (pp.role == 'QB')]
    return q.iloc[0]['name'] if len(q) else None
def wr1_of(t):
    w = pp[(pp.team == t) & (pp.role == 'WR') & (pp.tgt_share > 0)]
    return w.sort_values('tgt_share', ascending=False).iloc[0]['name'] if len(w) else None
QB = {t: qb_of(t) for t in tp.index}
WR1 = {t: wr1_of(t) for t in tp.index}
print(f"unique 2026 matchups: {len(pairs)} | teams with QB+WR1 identified: "
      f"{sum(1 for t in tp.index if QB[t] and WR1[t])}/{len(tp.index)}")

def _corr(x, y):
    if x.std() < 1e-9 or y.std() < 1e-9:
        return np.nan
    return float(np.corrcoef(x, y)[0, 1])

def slate_bringback(rho, sample, n, seed):
    """mean corr(QB_a, WR1_b) across both directions of each matchup, at cross-team sharing rho."""
    rng = np.random.default_rng(seed)
    cs = []
    for a, b in sample:
        gsh = rng.normal(0, 1, n)
        gA = np.sqrt(rho) * gsh + np.sqrt(1 - rho) * rng.normal(0, 1, n)
        gB = np.sqrt(rho) * gsh + np.sqrt(1 - rho) * rng.normal(0, 1, n)
        ga = gen_team(a, n, gA, rng)
        gb = gen_team(b, n, gB, rng)
        if QB[a] in ga and WR1[b] in gb:
            cs.append(_corr(ga[QB[a]], gb[WR1[b]]))
        if QB[b] in gb and WR1[a] in ga:
            cs.append(_corr(gb[QB[b]], ga[WR1[a]]))
    cs = [c for c in cs if c == c]
    return float(np.mean(cs)), len(cs)

def slate_intra(sample, n, seed):
    """mean intra-team corr(QB, WR1) — invariant to cross-team rho; sanity vs qb_wr1=0.351."""
    rng = np.random.default_rng(seed)
    cs = []
    for a, b in sample:
        gsh = rng.normal(0, 1, n)
        for t in (a, b):
            g = gsh if t == a else rng.normal(0, 1, n)
            gt = gen_team(t, n, g, rng)
            if QB[t] in gt and WR1[t] in gt:
                cs.append(_corr(gt[QB[t]], gt[WR1[t]]))
    cs = [c for c in cs if c == c]
    return float(np.mean(cs)), len(cs)

# stage 1: transfer function on a representative sample of matchups
SAMPLE = pairs[::max(1, len(pairs)//60)][:60]   # ~60 spread across the slate
N = 9000
print(f"\n=== STAGE 1: transfer function (sample={len(SAMPLE)} matchups, n={N}/game) ===")
intra, ni = slate_intra(SAMPLE, N, 101)
print(f"intra-team qb_wr1 (sim)      = {intra:.3f}   [target 0.351, n={ni} pairings]")

print(f"\n  rho (cross-team shock)  ->  sim bring-back (QB vs oppWR1)")
grid = [0.0, 0.25, 0.5, 0.75, 1.0]
xf = []
for rho in grid:
    c, ncnt = slate_bringback(rho, SAMPLE, N, 202)
    xf.append((rho, c))
    print(f"    rho={rho:.2f}   ->  {c:.3f}   (n={ncnt} directed pairs)")

# fit bringback ~ a + b*rho (near-linear: corr(g_A,g_B)=rho scales the shared component)
rr = np.array([r for r, _ in xf]); cc = np.array([c for _, c in xf])
b1, b0 = np.polyfit(rr, cc, 1)
print(f"\n  linear transfer:  bringback ≈ {b0:.4f} + {b1:.4f}·rho   (max at rho=1: {b0+b1:.3f})")

# store for stage 2
json.dump({"intra_qb_wr1": intra, "transfer": {"a": b0, "b": b1},
           "grid": xf, "sample_n": len(SAMPLE), "N": N},
          open('_corr_backtest_stage1.json', 'w'), indent=1)
print("\nwrote _corr_backtest_stage1.json")
