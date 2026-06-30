#!/usr/bin/env python3
"""build_stack_overlay.py — Rec 3: stack-aware overlay (the model's missing correlation layer).

The backtest found same-game correlation the player-by-player model ignores: when a QB booms,
his top pass-catcher booms 76% vs 34% otherwise (2.27x lift), and same-team WR1/WR2 are
positively correlated (r=0.51). This adds, for each WR/TE:
  - a 'Premium QB stack partner' SKILL flag when his primary same-team QB has a high base rate
  - a modest per-week co-boost (+ a week flag) when that QB is ALSO in a plus setup that week

Deliberately small multipliers (consistent with the shrink lesson). Runs AFTER the flag
builders, BEFORE the explorer. Guarded: aborts if flags already stacked (re-run builders first).
"""
import json, os
from boom_lib import label, cap  # reuse shrink-aware labeling

HERE = os.path.dirname(os.path.abspath(__file__)); B = os.path.join(HERE, 'boom')
QB_PREMIUM = 22                       # QB base >= this => premium stack partner (~top 11 QBs)
WK_BOOST = {'SMASH': 1.06, 'GOOD': 1.03}
STACK_F = "Premium QB stack partner"

qb = json.load(open(f"{B}/flags_QB.json"))
qb_by_team = {}
for k, v in qb.items():
    t = v.get('team')
    if not t or t == 'FA':
        continue
    if t not in qb_by_team or v['base'] > qb_by_team[t]['base']:
        qb_by_team[t] = {'name': v['name'], 'base': v['base'],
                         'weeks': {w['wk']: w for w in v['weeks']}}

for pos in ('WR', 'TE'):
    path = f"{B}/flags_{pos}.json"
    d = json.load(open(path))
    if any(f.get('f') == STACK_F for v in d.values() for f in v.get('skill_flags', [])):
        print(f"{pos}: already stacked -> re-run build_flags_{pos}.py first; SKIPPING"); continue
    nflag = nboost = 0
    for k, v in d.items():
        t = v.get('team'); qbt = qb_by_team.get(t)
        if not qbt or qbt['base'] < QB_PREMIUM:
            continue
        v['skill_flags'].append({
            'f': STACK_F,
            'd': (f"ceiling tied to {qbt['name']} (QB base {qbt['base']}); when the QB throws well "
                  f"this pass game booms together (measured 2.27x stack lift, 2024-25)"),
            'amp': "weeks his QB is also in a plus matchup"})
        nflag += 1
        base = v['base'] / 100.0
        for w in v['weeks']:
            if w.get('lab') in ('FA', 'BYE'):
                continue
            w['of'] = w.get('of', 0) + 1                      # stack flag now an applicable consideration
            qw = qbt['weeks'].get(w['wk'])
            if qw and qw.get('lab') in WK_BOOST:
                m = WK_BOOST[qw['lab']]
                p_new = cap((w['p'] / 100.0) * m, 0.01, 0.80)
                w['p'] = round(p_new * 100)
                w['lab'] = label(p_new, base)
                w['lit'] = w.get('lit', 0) + 1
                w['flags'].append(f"{qbt['name']} also in plus spot (stack)")
                nboost += 1
    json.dump(d, open(path, 'w'), ensure_ascii=False)
    print(f"{pos}: stack skill flag on {nflag} players, per-week co-boost fired {nboost} times")
