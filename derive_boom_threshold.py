#!/usr/bin/env python3
"""STRICT, principled derivation of per-position boom thresholds (no eyeballed numbers), v2.

ONE rule, applied identically to every position INCLUDING DST:
  boom = top ~15% weekly outcome within the position's STARTABLE TIER, operationalized two
  independent ways we require to AGREE within 8%:
     (a) 85th percentile of actual within the startable tier
     (b) mean + 1 standard deviation of that same distribution
  threshold = average of (a) and (b)  -> pinned by both a percentile AND a z-score anchor.

FIX vs v1: startable tier is defined position-RELATIVELY by weekly projection RANK (12-team
roster math), not a flat proj>=8 bar. A flat points bar over-filtered TE (only elite TEs clear
8 pts) and inflated the TE threshold to 17.6. Rank pools apply the SAME 'startable' concept to
all positions.  Sizes (1QB/2RB/3WR/1TE/1DST + flex + streaming margin):
  QB 16, TE 16, DST 16 ; RB 32 ; WR 44.
"""
import csv, json, os
from collections import defaultdict
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); DL = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'boom'); os.makedirs(OUT, exist_ok=True)

R = list(csv.DictReader(open(f"{DL}/dfs_review/out/boom_proj.csv", encoding='utf-8')))
POS = ['QB', 'RB', 'WR', 'TE', 'DST']
NSTART = {'QB': 16, 'RB': 32, 'WR': 44, 'TE': 16, 'DST': 16}

def rank_pool(nmap):
    byw = defaultdict(lambda: defaultdict(list))
    for r in R:
        p = r['pos'].upper()
        if p not in nmap: continue
        try: pr = float(r['proj']); ac = float(r['actual'])
        except Exception: continue
        byw[r['wk']][p].append((pr, ac, r['name']))
    out = defaultdict(list)
    for wk, pp in byw.items():
        for p, lst in pp.items():
            lst.sort(reverse=True)
            for pr, ac, nm in lst[:nmap[p]]:
                out[p].append((nm, ac))
    return out

def spearman(a, b):
    ra = np.argsort(np.argsort(a)); rb = np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])

prim = rank_pool(NSTART)
thresh = {}; prov = {}
print("=== PRINCIPLED THRESHOLD (startable tier = top-N by weekly proj) ===")
print(f"{'pos':>4} {'N':>3} {'n_obs':>6} {'mean':>6} {'sd':>5} {'p85':>6} {'mu+1sd':>7} {'agree':>6} {'THRESH':>7} {'rate':>6} {'/17g':>5}")
for p in POS:
    vals = np.array([a for _, a in prim[p]])
    mean = float(vals.mean()); sd = float(vals.std(ddof=1))
    p85 = float(np.percentile(vals, 85)); msd = mean + sd
    agree = abs(p85 - msd) / max(p85, msd) < 0.08
    th = round((p85 + msd) / 2, 1)
    rate = float((vals >= th).mean())
    thresh[p] = th
    prov[p] = {'N_startable': NSTART[p], 'n_obs': len(vals), 'mean': round(mean, 2), 'sd': round(sd, 2),
               'p85': round(p85, 1), 'mean_plus_1sd': round(msd, 1), 'anchors_agree_within_8pct': bool(agree),
               'threshold': th, 'boom_rate_startable': round(rate, 3), 'booms_per_17g': round(rate * 17, 1)}
    print(f"{p:>4} {NSTART[p]:>3} {len(vals):>6} {mean:>6.1f} {sd:>5.1f} {p85:>6.1f} {msd:>7.1f} {str(agree):>6} {th:>7.1f} {rate:>6.1%} {rate*17:>5.1f}")

def flat8(pos):
    v = []
    for r in R:
        if r['pos'].upper() != pos: continue
        try: pr = float(r['proj']); ac = float(r['actual'])
        except Exception: continue
        if pr >= 8: v.append(ac)
    return np.array(v)
te_old = flat8('TE')
print(f"\nTE DOUBLE-CHECK: old flat(proj>=8) pool n={len(te_old)} mean={te_old.mean():.1f} -> thr ~17.6 (INFLATED:")
print(f"  only elite TEs clear an 8-pt bar). New rank(top-16) pool n={len(prim['TE'])} mean={np.mean([a for _,a in prim['TE']]):.1f}")
print(f"  -> TE threshold now {thresh['TE']} (a solid TE1 week ~5/60/1), fair to mid-tier TEs.")

def player_rates(th):
    g = defaultdict(lambda: [0, 0])
    for p in ['QB', 'RB', 'WR', 'TE']:
        for nm, ac in prim[p]:
            g[nm][1] += 1; g[nm][0] += (1 if ac >= th[p] else 0)
    return {k: v[0] / v[1] for k, v in g.items() if v[1] >= 6}

def pctl_bar(pc):
    return {p: round(float(np.percentile([a for _, a in prim[p]], pc)), 1) for p in POS}

b85 = player_rates(thresh); b_lo = player_rates(pctl_bar(80)); b_hi = player_rates(pctl_bar(90))
common = [k for k in b85 if k in b_lo and k in b_hi]
print(f"\nPer-player rate ranking stability (n={len(common)} players, >=6 startable games):")
print(f"  Spearman(p85 bar, p80 bar) = {spearman([b85[k] for k in common], [b_lo[k] for k in common]):.3f}")
print(f"  Spearman(p85 bar, p90 bar) = {spearman([b85[k] for k in common], [b_hi[k] for k in common]):.3f}")

json.dump({'SPIKE': thresh,
           'rule': 'avg(85th pctl, mean+1sd) of actual within the position startable tier (top-N by weekly proj)',
           'startable_tier_sizes': NSTART, 'provenance': prov},
          open(f"{OUT}/boomdef.json", 'w'), indent=1)
print("\nLOCKED thresholds ->", thresh)
