#!/usr/bin/env python3
"""season_sim.py — run contest_sim across every 2024 Sunday $20 Milly; aggregate by mode.

Answers, on a full season with real ownership + correlated sims + real-ish payouts:
which construction (chalk / fade-λ / archetypes) makes the most simulated MONEY —
and cross-checks with what each mode's lineups ACTUALLY scored those Sundays.
"""
import argparse, glob, json, os, sys
from collections import defaultdict
import numpy as np
from contest_sim import (load_slate, simulate_worlds, sample_field, payout_curve,
                         gen_candidates, FL_DIR)

ap = argparse.ArgumentParser()
ap.add_argument('--tier', default='20', choices=['20', 'high', 'single', 'dome', 'small23', 'small46',
                                                 '555', 'mega'],
                help="'20' = flagship Milly | 'high' = $555/$4,444 | "
                     "'single' = big single-entry | 'dome' = Thunderdome")
ap.add_argument('--season', type=int, default=2024,
                help="NFL season year (Aug-Feb spans use the starting year)")
A = ap.parse_args()

W, F, PER_MODE = 3000, 3000, 15
def _season(d):
    y, m = int(d[:4]), int(d[5:7])
    return y if m >= 8 else y - 1
DATES = sorted({os.path.basename(p).split('_')[0]
                for p in glob.glob(os.path.join(FL_DIR, '*_main_*.csv'))
                if _season(os.path.basename(p).split('_')[0]) == A.season})

LAMS = {'small23': (0.0, 6.0, 12.0, 20.0, 30.0), 'small46': (0.0, 4.0, 8.0, 14.0, 22.0)}

def sharp_frac_for(entry, tier):
    """High stakes = sharper field: assumption pending calibration, but directionally right.
    Single-entry fields play tougher per lineup (everyone submits their best build)."""
    if tier == 'dome':
        return 0.85                                  # ~30 sharks, no dead money
    if tier == 'mega':
        return 0.80                                  # 300-800 entries, essentially all pros
    base = 0.65 if entry >= 3000 else (0.40 if entry >= 300 else 0.15)
    return min(base + (0.15 if tier == 'single' else 0.0), 0.9)

agg = defaultdict(lambda: {'roi': [], 'own': [], 'cash': [], 'top01': [], 'best_act': [],
                           'best_roi': []})
ran = 0
# per-slate checkpoint: container restarts have killed multi-hour chains twice — never again
CKPT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    f'season_ckpt_{A.tier}_{A.season}.json')
done_dates = set()
if os.path.exists(CKPT):
    ck = json.load(open(CKPT))
    done_dates = set(ck['dates'])
    for t, vals in ck['agg'].items():
        agg[t].update(vals)
    ran = len(done_dates)
    print(f"  resuming from checkpoint: {ran} slates already done", file=sys.stderr)

for d in DATES:
    if d in done_dates:
        continue
    try:
        pool, meta, _ = load_slate(d, tier=A.tier)
    except SystemExit:
        continue
    min_qb = 2 if A.tier in ('small23', 'small46') else 5
    if pool is None or sum(p.pos == 'QB' for p in pool) < min_qb:
        continue
    payout_at, pool_total, first, places = payout_curve(meta)
    pts = simulate_worlds(pool, W)
    field = sample_field(pool, F, sharp_frac=sharp_frac_for(meta['entry'], A.tier))
    cands, tags = gen_candidates(pool, PER_MODE, lams=LAMS.get(A.tier, (0.0, 3.0, 6.0, 10.0, 15.0)))
    fs = pts[field.reshape(-1)].reshape(F, 9, W).sum(axis=1)
    cs = pts[cands.reshape(-1)].reshape(len(cands), 9, W).sum(axis=1)
    fs_sorted = np.sort(fs, axis=0)
    scale = meta['size'] / F
    fkeys = defaultdict(int)
    for row in field:
        fkeys[frozenset(row.tolist())] += 1
    dupes = np.array([fkeys.get(frozenset(c.tolist()), 0) * scale for c in cands])
    C = len(cands)
    pay = np.zeros(C); cash = np.zeros(C); top01 = np.zeros(C)
    urng = np.random.default_rng(99)
    for wix in range(W):
        col = fs_sorted[:, wix]
        r = F - np.searchsorted(col, cs[:, wix], side='right')
        place = np.maximum((r + urng.uniform(size=C)) * scale, 1.0)   # sub-sample placement
        for ci in range(C):
            pay[ci] += payout_at(place[ci]) / (1 + dupes[ci])
            if place[ci] <= places: cash[ci] += 1
            if place[ci] <= meta['size'] * 0.001: top01[ci] += 1
    pay /= W; cash /= W; top01 /= W
    roi = (pay - meta['entry']) / meta['entry']
    owns = np.array([sum(pool[i].own for i in c) for c in cands])
    acts = np.array([sum(pool[i].actual for i in c) for c in cands])
    for t in set(tags):
        m = np.array([i for i, x in enumerate(tags) if x == t])
        T = agg[t]                                   # (do NOT shadow the argparse namespace!)
        T['roi'].append(roi[m].mean()); T['own'].append(owns[m].mean())
        T['cash'].append(cash[m].mean()); T['top01'].append(top01[m].mean())
        T['best_act'].append(acts[m].max()); T['best_roi'].append(roi[m].max())
    ran += 1
    done_dates.add(d)
    json.dump({'dates': sorted(done_dates), 'agg': {k: v for k, v in agg.items()}},
              open(CKPT, 'w'))
    print(f"  {d}  ${meta['entry']:>4.0f} {meta['size']:>7,}  '{meta['name'][:34]}'  "
          f"chalk-roi {roi[[i for i,x in enumerate(tags) if x=='fade0']].mean()*100:.0f}%",
          file=sys.stderr, flush=True)

tier_lbl = {'20': "$20 flagship", 'high': "$555/$4,444 high-stakes",
            'single': "single-entry (main-lineup)", 'dome': "Thunderdome single-entry",
            'small23': "2-3-game slates", 'small46': "4-6-game slates",
            '555': "$555 Milly (mid-stakes)", 'mega': "$4,444 MEGA Milly"}[A.tier] \
           + f" [{A.season} season]"
print(f"\n{'='*96}\nSEASON SIM — {ran} {tier_lbl} contests | {W} worlds x {F} field each\n{'='*96}")
print(f"{'mode':<14} {'ROI':>8} {'bestROI':>9} {'cash%':>7} {'top.1%':>8} {'own':>6} "
      f"{'mean best ACTUAL':>17}")
fades = sorted((t for t in agg if t.startswith('fade')), key=lambda t: float(t[4:]))
archs = sorted(t for t in agg if t.startswith('arch:'))
order = fades + archs
for t in order:
    if t not in agg:
        continue
    A = agg[t]
    print(f"{t:<14} {np.mean(A['roi'])*100:>7.0f}% {np.mean(A['best_roi'])*100:>8.0f}% "
          f"{np.mean(A['cash'])*100:>6.1f}% {np.mean(A['top01'])*100:>7.2f}% "
          f"{np.mean(A['own'])*100:>5.0f}% {np.mean(A['best_act']):>17.1f}")
print("\n(ROI = mean simulated return per mode; bestROI = its best lineup per slate;")
print(" mean best ACTUAL = that mode's best real score per Sunday, averaged over the season.)")
