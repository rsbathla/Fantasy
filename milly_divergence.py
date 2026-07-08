#!/usr/bin/env python3
"""milly_divergence.py — same slate, two Millys ($20 vs $555/$4,444):
(1) how differently do the two fields price ownership?
(2) how chalky / dupe-ridden is each field?
(3) did rsbathla enter the SAME lineups in both?
(4) what does the sim fade law say per tier?
=> should the 150-max $20 Milly and the high-stakes Milly get different lineups?
"""
import csv, glob, json, os, sys
from collections import defaultdict
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from contest_sim import load_slate, FL_DIR

DATA = os.path.join(HERE, 'data', 'fantasylabs')

# ---------------- (1) ownership divergence, slate by slate ----------------
DATES = sorted({os.path.basename(p).split('_')[0]
                for p in glob.glob(os.path.join(FL_DIR, '*_main_*.csv'))})
per, gaps = [], []
for d in DATES:
    try:
        p20, m20, _ = load_slate(d, tier='20')
        phi, mhi, _ = load_slate(d, tier='high')
    except SystemExit:
        continue
    if p20 is None or phi is None:
        continue
    o20 = {p.name: p.own for p in p20}
    ohi = {p.name: p.own for p in phi}
    common = [n for n in o20 if n in ohi and max(o20[n], ohi[n]) >= 0.005]
    if len(common) < 30:
        continue
    # FL sometimes stores ownership=0.0 for players it didn't compute in a given contest
    # (same family as the CPT own=0 bug). A >=5%-owned player showing EXACTLY 0 on the
    # other side is missing data, not real divergence — drop the pair; drop the slate
    # if the rot is widespread.
    suspect = [n for n in common if (o20[n] >= 0.05 and ohi[n] <= 0.002)
               or (ohi[n] >= 0.05 and o20[n] <= 0.002)]
    clean = [n for n in common if n not in set(suspect)]
    if len(suspect) > 0.2 * len([n for n in common if max(o20[n], ohi[n]) >= 0.05]):
        continue                                     # contest file too rotten to trust
    a = np.array([o20[n] for n in clean])
    b = np.array([ohi[n] for n in clean])
    c = np.corrcoef(a, b)[0, 1]
    if np.isnan(c):
        continue
    per.append({'d': d, 'n': len(clean), 'corr': c, 'mad': np.abs(a - b).mean(),
                't10_20': np.sort(a)[-10:].sum(), 't10_hi': np.sort(b)[-10:].sum(),
                'suspect': len(suspect)})
    for n, x, y in zip(clean, a, b):
        if abs(y - x) >= 0.08 and x > 0.002 and y > 0.002:
            gaps.append((d, n, x, y))

print(f"=== OWNERSHIP DIVERGENCE — {len(per)} slates with BOTH a $20 and a $555+/$4,444 Milly ===")
print(f"mean per-slate ownership correlation: {np.mean([r['corr'] for r in per]):.3f}")
print(f"mean |ownership gap| per player:      {np.mean([r['mad'] for r in per])*100:.1f}pp")
print(f"top-10 chalk concentration:  $20 field {np.mean([r['t10_20'] for r in per])*100:.0f}%"
      f"  vs  high-stakes {np.mean([r['t10_hi'] for r in per])*100:.0f}%")
by_season = defaultdict(list)
for r in per:
    y, m = int(r['d'][:4]), int(r['d'][5:7])
    by_season[y if m >= 8 else y - 1].append(r)
for s in sorted(by_season):
    rs = by_season[s]
    print(f"  {s}: {len(rs):>2} slates  corr {np.mean([r['corr'] for r in rs]):.3f}  "
          f"|gap| {np.mean([r['mad'] for r in rs])*100:.1f}pp")
hi_up = sorted([g for g in gaps if g[3] > g[2]], key=lambda g: g[2] - g[3])[:10]
lo_up = sorted([g for g in gaps if g[2] > g[3]], key=lambda g: g[3] - g[2])[:10]
print(f"\nplayers >=8pp apart between the two fields: {len(gaps)}"
      f"  (sharp-higher {sum(1 for g in gaps if g[3] > g[2])},"
      f" casual-higher {sum(1 for g in gaps if g[2] > g[3])})")
print("  chalkier in the $20 (casual) field:")
for d, n, x, y in lo_up:
    print(f"    {d}  {n:<22} $20 {x*100:4.0f}%  vs  $555+ {y*100:4.0f}%   gap {(x-y)*100:+.0f}pp")
print("  chalkier in the $555+/$4,444 (sharp) field:")
for d, n, x, y in hi_up:
    print(f"    {d}  {n:<22} $20 {x*100:4.0f}%  vs  $555+ {y*100:4.0f}%   gap {(y-x)*100:+.0f}pp")

# ---------------- (2) duplication pressure per field ----------------
CM = next((c for c in (os.path.join(DATA, 'winners', 'contest_meta.csv'),
                       os.path.join(DATA, 'contest_meta.csv')) if os.path.exists(c)), None)
d20, dhi = [], []
ctype = {}
if CM:
    for r in csv.DictReader(open(CM)):
        try:
            if r['slate'] != 'main' or 'millionaire' not in r['contestName'].lower():
                continue
            e = float(r['entryCost'])
            size, uniq = int(r['contestSize']), int(r['uniqueLineups'])
            if size <= 0 or uniq <= 0 or uniq > size:
                continue
            share = 1 - uniq / size
            if 19 <= e <= 26:
                d20.append(share); ctype[r['contestId']] = '20'
            elif e >= 300:
                dhi.append(share); ctype[r['contestId']] = 'high'
        except (KeyError, ValueError):
            continue
    print(f"\n=== DUPLICATION (share of entries that are copies of another entry) ===")
    print(f"$20 Milly:      {np.mean(d20)*100:5.1f}%   (n={len(d20)} contests)")
    print(f"$555+/$4,444:   {np.mean(dhi)*100:5.1f}%   (n={len(dhi)} contests)")

# ---------------- (3) his own lineup overlap between the two ----------------
u_by_date = defaultdict(lambda: defaultdict(set))
for p in glob.glob(os.path.join(DATA, 'users', '*_rsbathla.json')):
    parts = os.path.basename(p).split('_')
    if len(parts) < 3:
        continue
    d, cid = parts[0], parts[1]
    if not ctype.get(cid):
        continue
    try:
        rec = json.load(open(p))
    except Exception:
        continue
    lus = set()
    for h in rec.get('hits', []):                    # files wrap the record: hits[].record
        lus |= set((h.get('record') or {}).get('lineups') or {})
    if lus:
        u_by_date[d][ctype[cid]] |= lus
ovl = []
for d, tiers in sorted(u_by_date.items()):
    A, B = tiers.get('20'), tiers.get('high')
    if A and B:
        ovl.append((d, len(A), len(B), len(A & B) / min(len(A), len(B))))
if ovl:
    print(f"\n=== YOUR lineup overlap, $20 Milly vs high-stakes Milly, same slate ===")
    print(f"slates where you entered both: {len(ovl)}   "
          f"mean overlap (shared lineups / smaller pool): {np.mean([o[3] for o in ovl])*100:.0f}%")
    for d, na, nb, j in ovl:
        print(f"  {d}: {na:>3} distinct in $20, {nb:>3} in $555+  ->  overlap {j*100:3.0f}%")

# ---------------- (4) sim fade law, from season checkpoints ----------------
print(f"\n=== SIM FADE LAW (season-sim checkpoints, mean ROI by mode) ===")
for tier in ('20', 'high'):
    for season in (2021, 2022, 2023, 2024):
        p = os.path.join(HERE, f'season_ckpt_{tier}_{season}.json')
        if not os.path.exists(p):
            continue
        ck = json.load(open(p))
        modes = [(m, np.mean(v['roi'])) for m, v in ck['agg'].items() if v.get('roi')]
        if not modes:
            continue
        modes.sort(key=lambda x: -x[1])
        chalk = dict(modes).get('fade0', float('nan'))
        top3 = '  '.join(f"{m} {r*100:.0f}%" for m, r in modes[:3])
        print(f"  {'$20 ' if tier == '20' else '$555+'} {season}: chalk {chalk*100:4.0f}%  "
              f"best-> {top3}")
