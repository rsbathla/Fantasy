#!/usr/bin/env python3
"""
analysis_combos.py — (a) regularization sweep on the matchup layer (overfit-aware fix for the
backtest finding that the multipliers slightly hurt cross-player AUC), (b) NOVEL teammate
stack-correlation (best-ball relevant, never computed), (c) vacated-targets opportunity scan
(a real, unused signal sitting in ffdataroma).
"""
import json, os, glob
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); B = os.path.join(HERE, 'boom')

# ---------- (a) MULTIPLIER SHRINKAGE SWEEP ----------
gl = json.load(open(f"{B}/gamelog.json"))
FLAGS = {}
for pos in ('QB', 'RB', 'WR', 'TE', 'DST'):
    for k, v in json.load(open(f"{B}/flags_{pos}.json")).items():
        FLAGS[k] = {'pos': pos, 'base': (v.get('base') or 0) / 100.0}
def cap(x, lo, hi): return max(lo, min(hi, x))
def setup_mult(pos, g):
    m = 1.0; pp = g.get('opp_passp'); rp = g.get('opp_runp')
    if pos in ('QB', 'WR', 'TE'):
        if pp is not None:
            if pp <= 30: m *= 1.35
            elif pp <= 45: m *= 1.15
            elif pp >= 70: m *= 0.74
            elif pp >= 55: m *= 0.88
        if pp is not None and rp is not None and rp >= 60 and pp <= 45: m *= 1.15
        if g.get('dome'): m *= 1.05
        if g.get('home'): m *= 1.03
    elif pos == 'RB':
        if rp is not None:
            if rp <= 30: m *= 1.32
            elif rp <= 45: m *= 1.13
            elif rp >= 70: m *= 0.76
            elif rp >= 55: m *= 0.89
        if pp is not None and rp is not None and pp >= 60 and rp <= 45: m *= 1.13
        if g.get('home'): m *= 1.03
    elif pos == 'DST':
        oq = g.get('opp_off_q'); qq = g.get('opp_qb_q')
        if oq is not None:
            if oq <= 30: m *= 1.40
            elif oq <= 45: m *= 1.15
            elif oq >= 70: m *= 0.70
            elif oq >= 55: m *= 0.86
        if qq is not None and qq <= 35: m *= 1.12
        if g.get('home'): m *= 1.05
    return m
rows = []
for k, games in gl.items():
    meta = FLAGS.get(k)
    if not meta or not games or meta['base'] <= 0: continue
    for g in games:
        if 'boom' not in g: continue
        rows.append((meta['base'], setup_mult(meta['pos'], g), int(g['boom'])))
base = np.array([r[0] for r in rows]); mult = np.array([r[1] for r in rows]); boom = np.array([r[2] for r in rows])
def auc(score, y):
    pos = score[y == 1]; neg = score[y == 0]
    if not len(pos) or not len(neg): return float('nan')
    allv = np.concatenate([pos, neg]); order = np.argsort(allv, kind='mergesort')
    ranks = np.empty(len(allv)); ranks[order] = np.arange(1, len(allv) + 1)
    s = allv[order]; i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and s[j + 1] == s[i]: j += 1
        if j > i: ranks[order[i:j + 1]] = (i + 1 + j + 1) / 2
        i = j + 1
    return float((ranks[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))
print("=== (a) MATCHUP-MULTIPLIER SHRINKAGE SWEEP  m' = 1 + lambda*(m-1) ===")
print("    lambda=0 is base-only; lambda=1 is the current shipped model")
print(f"    {'lambda':>7} {'AUC':>7} {'Brier':>7}")
for lam in (0.0, 0.25, 0.5, 0.75, 1.0):
    msh = 1 + lam * (mult - 1)
    p = np.clip(base * msh, 0.01, 0.80)
    print(f"    {lam:>7.2f} {auc(p, boom):>7.3f} {np.mean((p-boom)**2):>7.4f}")
print()

# ---------- (b) NOVEL: TEAMMATE STACK CORRELATION (best-ball) ----------
g = pd.read_parquet('pipeline/player_games.parquet')
THR = {'QB': 26.0, 'RB': 22.0, 'WR': 20.2, 'TE': 16.3}
def ipos(r):
    if r.pass_att >= 10: return 'QB'
    if r.carries >= 8 and r.carries >= r.rec: return 'RB'
    return 'WRTE'
g['ipos'] = g.apply(ipos, axis=1)
qb_dk, w1_dk, qb_boom, w1_boom, both = [], [], [], [], 0
qbn = 0
for (tm, sn, wk), grp in g.groupby(['team', 'season', 'week']):
    qbs = grp[grp.ipos == 'QB']
    pcs = grp[grp.ipos == 'WRTE']
    if qbs.empty or pcs.empty: continue
    qb = qbs.sort_values('pass_att').iloc[-1]
    w1 = pcs.sort_values('dk').iloc[-1]
    qb_dk.append(qb.dk); w1_dk.append(w1.dk)
    qbb = int(qb.dk >= THR['QB']); wbb = int(w1.dk >= THR['WR'])
    qb_boom.append(qbb); w1_boom.append(wbb); qbn += 1
    if qbb and wbb: both += 1
qb_dk = np.array(qb_dk); w1_dk = np.array(w1_dk); qb_boom = np.array(qb_boom); w1_boom = np.array(w1_boom)
r = float(np.corrcoef(qb_dk, w1_dk)[0, 1])
p_w1 = w1_boom.mean()
p_w1_given_qb = w1_boom[qb_boom == 1].mean() if (qb_boom == 1).sum() else float('nan')
p_w1_given_noqb = w1_boom[qb_boom == 0].mean() if (qb_boom == 0).sum() else float('nan')
print("=== (b) NOVEL: QB <-> top pass-catcher STACK CORRELATION (2024-25, per team-game) ===")
print(f"    team-games: {qbn}")
print(f"    Pearson r(QB DK, WR1 DK)           = {r:.3f}")
print(f"    P(WR1 booms)                       = {p_w1:.3f}")
print(f"    P(WR1 booms | QB booms)            = {p_w1_given_qb:.3f}")
print(f"    P(WR1 booms | QB does NOT boom)    = {p_w1_given_noqb:.3f}")
print(f"    stack-boom lift (QB boom vs not)   = {p_w1_given_qb/max(p_w1_given_noqb,1e-9):.2f}x")
# WR-WR (run-it-back within same team, secondary pass catcher)
ww_r = []
for (tm, sn, wk), grp in g.groupby(['team', 'season', 'week']):
    pcs = grp[grp.ipos == 'WRTE'].sort_values('dk', ascending=False)
    if len(pcs) >= 2: ww_r.append((pcs.iloc[0].dk, pcs.iloc[1].dk))
if ww_r:
    a = np.array([x[0] for x in ww_r]); b = np.array([x[1] for x in ww_r])
    print(f"    Pearson r(WR1 DK, WR2 DK same team)= {np.corrcoef(a,b)[0,1]:.3f}  (negative => they cannibalize)")
print()

# ---------- (c) VACATED-TARGETS OPPORTUNITY SCAN (unused signal) ----------
print("=== (c) VACATED TARGETS — a real signal in ffdataroma NOT wired into the boom model ===")
vt_files = glob.glob(os.path.join(os.path.dirname(HERE), 'ffdataroma_draft_guide_export', 'ffdataroma', 'csv', 'vacated-targets*players*.csv'))
if vt_files:
    vt = pd.read_csv(vt_files[0])
    print(f"    file: {os.path.basename(vt_files[0])}  rows={len(vt)} cols={list(vt.columns)[:8]}")
    print(vt.head(8).to_string())
else:
    print("    (vacated-targets players file not found at expected path)")
