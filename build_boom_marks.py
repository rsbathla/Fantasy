#!/usr/bin/env python3
"""build_boom_marks.py — ONE canonical per-player 'boom marks' export the other dashboards
consume, so the boom model stays the single source of ceiling truth (no re-deriving).

Reads the 5 flags_<POS>.json (post shrink + stack overlay + FA mark) and cover_spec.json,
emits boom/boom_marks.json keyed by normalized name. Each entry:
  pos, team, name,
  ceiling_pct  (season boom probability, 0-100),
  best_p, best_wk, best_opp, best_lab   (the player's single best week),
  smash, good, tough                    (count of each week grade),
  stack (bool), stack_qb,               (Premium QB stack partner)
  fa (bool),                            (unsigned free agent)
  cspec, cspec_ratio,                   (coverage specialist scheme vs league)
  nflags
"""
import json, os, re
from boomutil import fn
B = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'boom')

cspec = json.load(open(f"{B}/cover_spec.json")) if os.path.exists(f"{B}/cover_spec.json") else {}
marks = {}
collisions = 0
for pos in ('QB', 'RB', 'WR', 'TE', 'DST'):
    d = json.load(open(f"{B}/flags_{pos}.json"))
    for k, v in d.items():
        wks = [w for w in v['weeks'] if w.get('lab') not in ('BYE', 'FA') and w.get('p') is not None]
        labs = [w['lab'] for w in wks]
        best = max(wks, key=lambda w: w['p']) if wks else None
        sf = v.get('skill_flags', [])
        stack = next((f for f in sf if f.get('f') == 'Premium QB stack partner'), None)
        stack_qb = None
        if stack:
            m = re.search(r'tied to (.+?) \(QB base', stack.get('d', ''))
            stack_qb = m.group(1) if m else None
        cs = cspec.get(k) or {}
        entry = {
            'pos': pos, 'team': v.get('team'), 'name': v.get('name'),
            'ceiling_pct': v.get('base'),
            'best_p': best['p'] if best else None,
            'best_wk': best['wk'] if best else None,
            'best_opp': best['opp'] if best else None,
            'best_lab': best['lab'] if best else ('FA' if v.get('team') == 'FA' else None),
            'smash': labs.count('SMASH'), 'good': labs.count('GOOD'), 'tough': labs.count('TOUGH'),
            'stack': bool(stack), 'stack_qb': stack_qb,
            'fa': v.get('team') == 'FA',
            'cspec': cs.get('best'), 'cspec_ratio': cs.get('ratio'),
            'nflags': len(sf),
        }
        # ready-to-render badge + color tier (so dashboards render uniformly)
        if entry['fa']:
            entry['badge'] = 'FA - unsigned'; entry['tier'] = 'FA'
        else:
            parts = [str(entry['ceiling_pct']) + '% ceil']
            if entry['best_lab']: parts.append('best ' + entry['best_lab'])
            if entry['smash']: parts.append(str(entry['smash']) + ' SMASH wk')
            if entry['stack_qb']: parts.append('stack:' + entry['stack_qb'])
            if entry['cspec']: parts.append(entry['cspec'] + ' specialist')
            entry['badge'] = ' \u00b7 '.join(parts)
            cp = entry['ceiling_pct'] or 0
            entry['tier'] = 'ELITE' if cp >= 35 else ('HIGH' if cp >= 22 else ('MID' if cp >= 12 else 'LOW'))
        key = k
        if key in marks:                       # cross-position name collision -> pos-suffix
            collisions += 1
            key = k + '|' + pos
        marks[key] = entry

json.dump(marks, open(f"{B}/boom_marks.json", 'w'), ensure_ascii=False, indent=0)
nstack = sum(1 for m in marks.values() if m['stack'])
nfa = sum(1 for m in marks.values() if m['fa'])
print(f"boom_marks.json: {len(marks)} players ({collisions} name collisions pos-suffixed), "
      f"{nstack} stacks, {nfa} FA")
# spot check
for nm in ('jamarr chase', 'puka nacua', 'stefon diggs'):
    if nm in marks:
        m = marks[nm]
        print(f"  {m['name']:20} ceil={m['ceiling_pct']}% best=W{m['best_wk']}/{m['best_lab']} "
              f"SMASH×{m['smash']} stack={m['stack_qb']} fa={m['fa']} cspec={m['cspec']}")
