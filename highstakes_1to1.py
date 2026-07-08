#!/usr/bin/env python3
"""highstakes_1to1.py — the high-stakes fork simulated at TRUE field size.

MEGA fields are 300-800 entries and $555 fields 2-5K, so unlike the 147K Milly we can
simulate every single opponent — no tail extrapolation, the post-mortem's biggest
failure mode is gone.

For each slate: sim W worlds -> sample the REAL number of opponents -> drop in a
K-lineup portfolio per construction mode (fade grid) with SELF-COMPETITION handled
(my j-th best lineup's place = field rank + j) -> exact EV, ROI, P(win the contest).
Sweep K over {1,5,10,19,36,75,150} to price the marginal bullet.

Checkpointed per slate: hs11_ckpt_{tier}_{season}.json
"""
import argparse, json, os, sys
from collections import defaultdict
import glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from contest_sim import load_slate, simulate_worlds, sample_field, payout_curve, FL_DIR
from portfolio_150 import world_champion

ap = argparse.ArgumentParser()
ap.add_argument('--tier', default='mega', choices=['mega', '555'])
ap.add_argument('--season', type=int, default=2024)
ap.add_argument('--worlds', type=int, default=2000)
A = ap.parse_args()

KS = (1, 5, 10, 19, 36, 75, 150)
LAMS = (0.0, 3.0, 6.0, 10.0, 15.0) if A.tier == 'mega' else (0.0, 3.0, 6.0, 10.0, 15.0, 20.0)
SHARP = 0.80 if A.tier == 'mega' else 0.45

def _season(d):
    y, m = int(d[:4]), int(d[5:7])
    return y if m >= 8 else y - 1

DATES = sorted({os.path.basename(p).split('_')[0]
                for p in glob.glob(os.path.join(FL_DIR, '*_main_*.csv'))
                if _season(os.path.basename(p).split('_')[0]) == A.season})

CKPT = os.path.join(HERE, f'hs11_ckpt_{A.tier}_{A.season}.json')
res = {'dates': [], 'agg': {}}                    # agg[mode][K] = list of (roi, pwin, ev)
if os.path.exists(CKPT):
    res = json.load(open(CKPT))
    print(f"resuming: {len(res['dates'])} slates done", file=sys.stderr)

W = A.worlds
for d in DATES:
    if d in res['dates']:
        continue
    try:
        pool, meta, _ = load_slate(d, tier=A.tier)
    except SystemExit:
        continue
    if pool is None or sum(p.pos == 'QB' for p in pool) < 5:
        continue
    payout_at, pool_total, first, places = payout_curve(meta)
    size = meta['size']
    F = max(size - max(KS), 50)                   # opponents after my max bullets
    pts = simulate_worlds(pool, W)
    field = sample_field(pool, F, sharp_frac=SHARP)
    fs = np.sort(pts[field.reshape(-1)].reshape(F, 9, W).sum(axis=1), axis=0)
    # fast candidate pool: jittered greedy on (proj - lam*own), 150 distinct per fade mode
    # (gen_candidates runs an ILP per lineup — 750 solves/slate is why v1 timed out)
    sal = np.array([p.salary for p in pool])
    proj = np.array([p.proj for p in pool]); own = np.array([p.own for p in pool])
    rng = np.random.default_rng(11)
    cands, tags = [], []
    for lam in LAMS:
        base = proj - lam * own * 10
        got = set(); tries = 0
        while len(got) < max(KS) and tries < max(KS) * 5:
            tries += 1
            lu = world_champion(pool, base + rng.normal(0, 2.0, len(pool)), sal, rng)
            if lu and lu not in got:
                got.add(lu)
                cands.append(list(lu)); tags.append(f'fade{lam:g}')
    cands = np.array(cands, dtype=np.int32)
    cs = pts[cands.reshape(-1)].reshape(len(cands), 9, W).sum(axis=1)
    PAY = np.array([payout_at(i) for i in range(1, size + 2)])   # place -> $ lookup
    def pay_of(place):
        return PAY[np.clip(place, 1, size).astype(np.int64) - 1]
    # every candidate's field rank in every world (vectorized per world, done once)
    r_all = np.empty_like(cs)
    for wix in range(W):
        r_all[:, wix] = F - np.searchsorted(fs[:, wix], cs[:, wix], side='right')
    solo_ev = pay_of(r_all + 1.0).mean(axis=1)
    for mode in sorted(set(tags)):
        if not mode.startswith('fade'):
            continue
        ix = np.array([i for i, t in enumerate(tags) if t == mode])
        ix = ix[np.argsort(-solo_ev[ix])]         # best bullets first
        for K in KS:
            kx = ix[:min(K, len(ix))]
            fr = np.sort(r_all[kx], axis=0)       # ascending: my best lineup first
            place = fr + np.arange(len(kx))[:, None] + 1.0     # self-competition
            ev = pay_of(place).sum(axis=0).mean()
            pwin = float((fr[0] == 0).mean())     # my best beats the entire field
            cost = meta['entry'] * len(kx)
            m = res['agg'].setdefault(mode, {}).setdefault(str(K), [])
            m.append([(ev - cost) / cost, pwin, ev])
    res['dates'].append(d)
    json.dump(res, open(CKPT, 'w'))
    print(f"  {d}  ${meta['entry']:>5,.0f} x {size:>6,}  '{meta['name'][:30]}'", file=sys.stderr,
          flush=True)

print(f"\n{'='*100}\n1:1 FIELD SIM — {A.tier} tier, {A.season} season, {len(res['dates'])} slates, "
      f"{W} worlds, TRUE field size\n{'='*100}")
print(f"{'mode':<8}" + ''.join(f"{'K='+str(k):>13}" for k in KS))
for mode in sorted(res['agg'], key=lambda m: float(m[4:])):
    cells = []
    for K in KS:
        v = res['agg'][mode].get(str(K))
        if v:
            roi = np.mean([x[0] for x in v]); pw = np.mean([x[1] for x in v])
            cells.append(f"{roi*100:+5.0f}%/{pw*100:4.1f}")
        else:
            cells.append('')
    print(f"{mode:<8}" + ''.join(f"{c:>13}" for c in cells))
print("\n(cell = mean ROI / P(win the whole contest) per slate; bullets ranked by solo EV,")
print(" self-competition priced: your j-th best lineup finishes j places behind your best.)")
