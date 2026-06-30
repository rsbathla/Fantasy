#!/usr/bin/env python3
"""tighten_flags.py — make flag SETS discriminate (the user's note: too many WRs carried the
identical name-set). MODERATE tighten: the loosest skill flags lit for >60% of a position; for
each, keep it only for players genuinely top-tier on that flag's TRAIT (a statmenu metric),
bringing prevalence to ~TARGET. Players we can't measure keep the flag (don't strip the unknown).
Runs after the flag builders, before the overlay.

Note: this prunes the displayed skill-flag SET; per-week probabilities were already computed by
the builders and are not recomputed here (the dropped flags are the loosest, smallest-mult ones,
so the effect on p is negligible). A future clean version raises the thresholds in the builders.
"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__)); B = os.path.join(HERE, 'boom')
sm = json.load(open(f"{B}/statmenu.json"))
TARGET = 0.55

def adv(v, key):
    a = (v or {}).get('adv2') or {}
    return a.get(key)
def fus(v, key):
    f = (v or {}).get('fus') or {}
    return f.get(key)

# (position, flag name, metric fn higher=more deserving)
RULES = [
    ('WR', 'Deep/vertical threat',         lambda v: adv(v, 'aDOT')),
    ('WR', 'Ceiling / red-zone TD equity', lambda v: adv(v, 'td_pg')),
    ('RB', 'O-line / run-scheme efficiency', lambda v: fus(v, 'oline_pctl')),
]
for pos, flagname, metric in RULES:
    fpath = f"{B}/flags_{pos}.json"; d = json.load(open(fpath)); n = len(d)
    holders = [k for k, v in d.items() if any(f['f'] == flagname for f in v['skill_flags'])]
    prev = len(holders)
    if prev <= TARGET * n:
        print(f"{pos} '{flagname}': {prev}/{n} already <= target; skip"); continue
    measured = [(k, metric(sm.get(k))) for k in holders]
    meas = [(k, mv) for k, mv in measured if mv is not None]
    unmeasured = [k for k, mv in measured if mv is None]
    keep_n = max(0, int(round(TARGET * n)) - len(unmeasured))   # keep unmeasured + top measured
    meas.sort(key=lambda x: -x[1])
    keep = set(k for k, _ in meas[:keep_n]) | set(unmeasured)
    dropped = 0
    for k in holders:
        if k not in keep:
            d[k]['skill_flags'] = [f for f in d[k]['skill_flags'] if f['f'] != flagname]
            dropped += 1
    json.dump(d, open(fpath, 'w'), ensure_ascii=False)
    print(f"{pos} '{flagname}': {prev}/{n} ({round(100*prev/n)}%) -> kept {prev-dropped}/{n} "
          f"({round(100*(prev-dropped)/n)}%); dropped {dropped} marginal ({len(unmeasured)} unmeasured kept)")
