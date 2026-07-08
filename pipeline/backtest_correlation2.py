#!/usr/bin/env python3
"""backtest_correlation2.py — stage 2: calibrate rho(total), and quantify the SG lever.

Stage 1 established (on the real 2026 slate): transfer is ~linear, bringback ≈ 0.123·rho, so the
FULLY-shared ceiling at SG=0.31 is 0.122 — on the empirical 'all' (0.129) but BELOW high_total
(0.159). Intra qb_wr1 also sims 0.307 vs 0.351. Both say the shared-shock magnitude is a touch low.

This stage:
  (A) sweeps SG -> (intra qb_wr1, fully-shared bring-back ceiling); finds SG* giving intra≈0.351.
  (B) two calibrations of rho(total)=clip(a+b*(total-45),0,1):
        MINIMAL  — SG=0.31 fixed: matches low exactly, high plateaus at the 0.122 ceiling (honest gap)
        JOINT    — SG=SG*:        matches low AND high, and fixes the intra under-shoot
  (C) pulls REAL 2026 game totals, computes the high/low bucket centers, fits rho(total),
      and validates the slate-weighted average against the 'all' target 0.129.
Run from pipeline/:  python3 backtest_correlation2.py
"""
import numpy as np, pandas as pd, json, os, csv
import warnings; warnings.filterwarnings('ignore')

_src = open('sim_prod.py').read().split("# build distribution")[0]
exec(_src)   # gen_team, pp, tp, SG, ST ...

games = json.load(open('games_by_week.json'))
pairs = sorted({tuple(sorted((a, b))) for w, gl in games.items() for a, b in gl
                if a in tp.index and b in tp.index})
def qb_of(t):
    q = pp[(pp.team == t) & (pp.role == 'QB')]; return q.iloc[0]['name'] if len(q) else None
def wr1_of(t):
    w = pp[(pp.team == t) & (pp.role == 'WR') & (pp.tgt_share > 0)]
    return w.sort_values('tgt_share', ascending=False).iloc[0]['name'] if len(w) else None
QB = {t: qb_of(t) for t in tp.index}; WR1 = {t: wr1_of(t) for t in tp.index}
SAMPLE = pairs[::max(1, len(pairs)//60)][:60]
N = 9000

def _corr(x, y):
    return np.nan if (x.std() < 1e-9 or y.std() < 1e-9) else float(np.corrcoef(x, y)[0, 1])

def measure(sg, rho, seed=202):
    """(intra qb_wr1, cross-team bring-back) at shared-shock weight sg and cross-team sharing rho."""
    global SG
    SG = sg
    rng = np.random.default_rng(seed)
    intra, cross = [], []
    for a, b in SAMPLE:
        gsh = rng.normal(0, 1, N)
        gA = np.sqrt(rho) * gsh + np.sqrt(1 - rho) * rng.normal(0, 1, N)
        gB = np.sqrt(rho) * gsh + np.sqrt(1 - rho) * rng.normal(0, 1, N)
        ga = gen_team(a, N, gA, rng); gb = gen_team(b, N, gB, rng)
        for t, gt in ((a, ga), (b, gb)):
            if QB[t] in gt and WR1[t] in gt:
                intra.append(_corr(gt[QB[t]], gt[WR1[t]]))
        if QB[a] in ga and WR1[b] in gb: cross.append(_corr(ga[QB[a]], gb[WR1[b]]))
        if QB[b] in gb and WR1[a] in ga: cross.append(_corr(gb[QB[b]], ga[WR1[a]]))
    f = lambda L: float(np.nanmean(L))
    return f(intra), f(cross)

# ---- (A) SG lever: intra + fully-shared ceiling vs SG ----
print("=== (A) SG lever (rho=1 fully shared) ===")
print(f"  {'SG':>5} {'intra_qb_wr1':>13} {'bringback_max':>14}")
sgrid = [0.28, 0.31, 0.34, 0.37, 0.40]
rows = []
for sg in sgrid:
    it, cr = measure(sg, 1.0)
    rows.append((sg, it, cr)); print(f"  {sg:>5.2f} {it:>13.3f} {cr:>14.3f}")
sgv = np.array([r[0] for r in rows]); itv = np.array([r[1] for r in rows]); crv = np.array([r[2] for r in rows])
# SG* for intra target 0.351 (linear interp on the sweep)
SG_STAR = float(np.interp(0.351, itv, sgv))
bbmax_031 = float(np.interp(0.31, sgv, crv))
bbmax_star = float(np.interp(SG_STAR, sgv, crv))
print(f"\n  SG* (intra->0.351) = {SG_STAR:.3f} | bringback ceiling: SG=0.31 -> {bbmax_031:.3f}, SG*={SG_STAR:.2f} -> {bbmax_star:.3f}")

# ---- real 2026 totals -> bucket centers ----
VP = '../ffdataroma_draft_guide_export/ffdataroma/csv/weekly-vegas-lines.csv'
tot_by_pair = {}
if os.path.exists(VP):
    for r in csv.DictReader(open(VP, encoding='utf-8')):
        t, opp, wk, tot = r.get('team'), r.get('opp'), r.get('week'), r.get('total')
        if t and opp and tot:
            try: tot_by_pair[(tuple(sorted((t, opp))), wk)] = float(tot)
            except ValueError: pass
totals = np.array(sorted(tot_by_pair.values()))
MED = 45.0
hi = totals[totals > MED]; lo = totals[totals < MED]
hi_c, lo_c = float(hi.mean()), float(lo.mean())
print(f"\n=== 2026 totals: {len(totals)} games | median target {MED} | "
      f"high-bucket mean {hi_c:.1f} (n={len(hi)}) · low-bucket mean {lo_c:.1f} (n={len(lo)}) ===")

def rho_line(bbmax):
    """rho(total)=clip(a+b*(total-45),0,1) hitting bringback low=0.062@lo_c, high=min(0.159,bbmax)@hi_c."""
    tgt_lo, tgt_hi = 0.062, min(0.159, bbmax)
    rho_lo = np.clip(tgt_lo / bbmax, 0, 1); rho_hi = np.clip(tgt_hi / bbmax, 0, 1)
    b = (rho_hi - rho_lo) / (hi_c - lo_c)
    a = rho_lo - b * (lo_c - MED)          # a is rho at total=MED
    return a, b, rho_lo, rho_hi, tgt_hi

def validate(bbmax, a, b):
    """slate-weighted mean bring-back if each game uses rho(total)."""
    bb = []
    for tot in totals:
        rho = float(np.clip(a + b * (tot - MED), 0, 1))
        bb.append(bbmax * rho)             # transfer ~ linear through origin
    return float(np.mean(bb)), float(np.mean([bbmax*np.clip(a+b*(t-MED),0,1) for t in hi])), \
           float(np.mean([bbmax*np.clip(a+b*(t-MED),0,1) for t in lo]))

print("\n=== (B/C) rho(total) calibrations ===")
for label, sg, bbmax in [("MINIMAL (SG=0.31)", 0.31, bbmax_031), (f"JOINT (SG*={SG_STAR:.3f})", SG_STAR, bbmax_star)]:
    a, b, rlo, rhi, tgt_hi = rho_line(bbmax)
    allm, him, lom = validate(bbmax, a, b)
    print(f"\n  {label}:")
    print(f"    rho(total) = clip({a:.3f} + {b:.4f}·(total-45), 0, 1)   [rho@median={a:.3f}]")
    print(f"    anchors: low total {lo_c:.1f}->rho {rlo:.2f}->bb {bbmax*rlo:.3f} (target 0.062) | "
          f"high {hi_c:.1f}->rho {rhi:.2f}->bb {bbmax*rhi:.3f} (target {tgt_hi:.3f})")
    print(f"    slate validation: mean bring-back {allm:.3f} (target 0.129) | "
          f"high-bucket {him:.3f} (0.159) | low-bucket {lom:.3f} (0.062)")

json.dump({"SG_STAR": SG_STAR, "bbmax_031": bbmax_031, "bbmax_star": bbmax_star,
           "hi_c": hi_c, "lo_c": lo_c, "n_games": len(totals)},
          open('_corr_backtest_stage2.json', 'w'), indent=1)
print("\nwrote _corr_backtest_stage2.json")
