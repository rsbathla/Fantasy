#!/usr/bin/env python3
"""high_autopsy.py — where does the −28% on $2.29M of main-slate $555/$4,444 Millys live?

Splits: season · entry stake · SINGLE-vs-MULTI mode · loss concentration.
Skill-in-fork: his top-1% lineup hit-rate vs the 1% baseline, and his ownership
deviation vs what THAT contest's top-1% winners ran (both computable without any
id->name join: his record carries exposure AND leverage, winners CSVs carry
top_pct AND field_ownership).
Hand-me-down test: same-slate $20/high lineup overlap vs his ROI in the high contest.
"""
import csv, glob, json, os
from collections import defaultdict
import numpy as np

DATA = 'data/fantasylabs'

# ---- type main-slate Millys by stake ----
ctype, meta_by_cid = {}, {}
for r in csv.DictReader(open(os.path.join(DATA, 'contest_meta.csv'))):
    try:
        if r['slate'] != 'main' or 'millionaire' not in r['contestName'].lower():
            continue
        e = float(r['entryCost'])
        if 19 <= e <= 26:
            ctype[r['contestId']] = '20'
        elif e >= 300:
            ctype[r['contestId']] = 'high'
        meta_by_cid[r['contestId']] = r
    except (KeyError, ValueError):
        continue

def season_of(d):
    y, m = int(d[:4]), int(d[5:7])
    return y if m >= 8 else y - 1

rows = []
his_lineups = defaultdict(lambda: defaultdict(set))       # date -> tier -> hashes
for p in sorted(glob.glob(os.path.join(DATA, 'users', '*_rsbathla.json'))):
    parts = os.path.basename(p).split('_')
    d, cid = parts[0], parts[1]
    t = ctype.get(cid)
    if not t:
        continue
    rec = json.load(open(p))
    hr = None
    for h in rec.get('hits', []):
        r0 = h.get('record') or {}
        if r0.get('totalEntryCost'):
            hr = r0
            break
    if not hr:
        continue
    his_lineups[d][t] |= set(hr.get('lineups') or {})
    if t != 'high':
        continue
    tot, uniq = hr.get('totalRosters', 0), hr.get('uniqueRosters', 0)
    mode = 'SINGLE' if (uniq == 1 or (tot and uniq / tot <= 0.20) or tot <= 5) else 'MULTI'
    exps = hr.get('exposures') or {}
    devs, wts = [], []
    for pid, v in exps.items():
        try:
            exp = float(v.get('playerExposure') or 0)
            lev = float(v.get('playerLeverage') or 0)
        except (TypeError, ValueError):
            continue
        if exp <= 0:
            continue
        devs.append(abs(lev))                              # |exposure - field_own|
        wts.append(exp)
    his_dev = float(np.average(devs, weights=wts)) if devs else None
    # winners' deviation in the SAME contest
    wdev = None
    wp = os.path.join(DATA, 'winners', f'{d}_main_{cid}.csv')
    if os.path.exists(wp):
        wd, ww = [], []
        for r in csv.DictReader(open(wp)):
            if str(r.get('tier_top_pct')) not in ('1', '1.0'):
                continue
            try:
                tp = float(r['top_pct']); fo = float(r['field_ownership'] or 0)
            except (TypeError, ValueError):
                continue
            if tp <= 0:
                continue
            wd.append(abs(tp - fo)); ww.append(tp)
        if wd:
            wdev = float(np.average(wd, weights=ww))
    cm = meta_by_cid.get(cid, {})
    rows.append({'date': d, 'cid': cid, 'season': season_of(d),
                 'entry': float(cm.get('entryCost', 0) or 0),
                 'in': hr['totalEntryCost'], 'out': hr.get('totalWinning', 0),
                 'n': tot, 'uniq': uniq, 'mode': mode,
                 'cash': hr.get('lineupsCashing', 0), 'p1': hr.get('lineupsInPercentile1', 0),
                 'p10': hr.get('lineupsInPercentile10', 0),
                 'his_dev': his_dev, 'win_dev': wdev})

print(f"=== HIS 52 HIGH-STAKES MAIN MILLYS — {len(rows)} records ===\n")
def block(rs, lbl):
    i = sum(r['in'] for r in rs); o = sum(r['out'] for r in rs)
    n = sum(r['n'] for r in rs)
    print(f"{lbl:<26} {len(rs):>3} contests {n:>5} entries  ${i:>9,.0f} -> ${o:>9,.0f}  "
          f"ROI {(o-i)/i*100:+6.1f}%")

for s in sorted({r['season'] for r in rows}):
    block([r for r in rows if r['season'] == s], f"season {s}")
print()
for e in sorted({r['entry'] for r in rows}):
    block([r for r in rows if r['entry'] == e], f"${e:,.0f} entry")
print()
for m in ('MULTI', 'SINGLE'):
    block([r for r in rows if r['mode'] == m], f"{m} mode")

# skill-in-fork
mult = [r for r in rows if r['mode'] == 'MULTI']
tot_lu = sum(r['n'] for r in mult)
p1 = sum(r['p1'] for r in mult); p10 = sum(r['p10'] for r in mult)
cash = sum(r['cash'] for r in mult)
print(f"\n=== SKILL IN FORK (MULTI weeks, {tot_lu} lineups) ===")
print(f"top-1% hit rate:  {p1/tot_lu*100:.2f}%   (baseline 1.00%)")
print(f"top-10% hit rate: {p10/tot_lu*100:.1f}%   (baseline 10.0%)")
print(f"cash rate:        {cash/tot_lu*100:.1f}%   (typical line ~20-23%)")
hd = [r['his_dev'] for r in mult if r['his_dev'] is not None]
wd = [r['win_dev'] for r in mult if r['win_dev'] is not None]
print(f"his ownership deviation:     {np.mean(hd):.1f}pp (exposure-weighted)")
print(f"winners' deviation (same contests): {np.mean(wd):.1f}pp")

# loss concentration
rows.sort(key=lambda r: r['out'] - r['in'])
print("\nworst 5 contests:")
for r in rows[:5]:
    print(f"  {r['date']}  ${r['entry']:,.0f} x{r['n']:>3} ({r['mode']}): "
          f"${r['in']:,.0f} -> ${r['out']:,.0f}  ({r['out']-r['in']:+,.0f})")
print("best 5 contests:")
for r in rows[-5:]:
    print(f"  {r['date']}  ${r['entry']:,.0f} x{r['n']:>3} ({r['mode']}): "
          f"${r['in']:,.0f} -> ${r['out']:,.0f}  ({r['out']-r['in']:+,.0f})")

# hand-me-down test: same-slate lineup overlap vs high-contest ROI
print("\n=== HAND-ME-DOWN TEST (slates where he entered BOTH millys, MULTI in high) ===")
pairs = []
for r in rows:
    if r['mode'] != 'MULTI':
        continue
    l20, lhi = his_lineups[r['date']].get('20'), his_lineups[r['date']].get('high')
    if l20 and lhi:
        ov = len(l20 & lhi) / min(len(l20), len(lhi))
        pairs.append((ov, (r['out'] - r['in']) / r['in'], r['date'], len(lhi)))
hi_ov = [p for p in pairs if p[0] >= 0.9]
lo_ov = [p for p in pairs if p[0] < 0.9]
for lbl, ps in (('overlap >=90% (clones of $20 build)', hi_ov),
                ('overlap <90% (differentiated)', lo_ov)):
    if ps:
        print(f"  {lbl:<38} {len(ps):>2} slates  mean ROI {np.mean([p[1] for p in ps])*100:+6.1f}%")
