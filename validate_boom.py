#!/usr/bin/env python3
"""
validate_boom — the missing test layer for the boom subsystem. Exit 0 = clean, 1 = fail.

Catches the exact bug classes the audit found shipping:
  * un-interpolated f-string placeholders in any output string  (the DST {covp} bug)
  * schema drift across the 5 position flag files
  * out-of-range probabilities / wrong week counts
  * statmenu CLOBBER: augmentation keys missing from statmenu.json (foundation re-run
    without re-running the augmenters)

Run:  python3 validate_boom.py        (full)
      python3 validate_boom.py --quick (skip statmenu augmentation check)
"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); B = os.path.join(HERE, 'boom')

from flag_engine import REC_KEYS as _RK, WEEK_KEYS as _WK  # single source of the schema contract
TOP_KEYS = set(_RK)
WEEK_KEYS = set(_WK)
PLACEHOLDER = re.compile(r'\{[a-z_]+(:[^}]+)?\}')  # {covp}, {man_rate:.1f}, ...
LABELS = {'SMASH', 'GOOD', 'NEU', 'TOUGH'}
SENTINEL_LABELS = {'FA', 'BYE'}   # FA = unresolved 2026 team (valid; tracked as coverage gap)
errs = []
fa_players = []

def walk_strings(obj, path=''):
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_strings(v, path + '.' + str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_strings(v, path + '[' + str(i) + ']')

print("=== validate_boom ===")
total_players = 0
for pos in ('QB', 'RB', 'WR', 'TE', 'DST'):
    p = B + '/flags_' + pos + '.json'
    if not os.path.exists(p):
        errs.append('missing ' + p); continue
    d = json.load(open(p)); total_players += len(d)
    ph = 0
    for k, v in d.items():
        missing = TOP_KEYS - set(v)
        if missing:
            errs.append(pos + '/' + k + ': missing top keys ' + str(missing))
        for spath, s in walk_strings(v):
            if PLACEHOLDER.search(s):
                ph += 1
                if ph <= 3:
                    errs.append(pos + '/' + k + spath + ': un-interpolated placeholder -> ' + repr(s[:70]))
        b = v.get('base')
        if b is not None and not (0 <= b <= 100):
            errs.append(pos + '/' + k + ': base ' + str(b) + ' out of [0,100]')
        for sf in v.get('skill_flags', []):
            if not {'f', 'd'} <= set(sf):
                errs.append(pos + '/' + k + ': skill_flag missing f/d -> ' + str(sf))
        if v.get('team') == 'FA':
            fa_players.append(pos + '/' + k)
        wks = v.get('weeks', [])
        if len(wks) != 18:
            errs.append(pos + '/' + k + ': ' + str(len(wks)) + ' weeks (expected 18)')
        for w in wks:
            wm = WEEK_KEYS - set(w)
            if wm:
                errs.append(pos + '/' + k + ' wk' + str(w.get('wk', '?')) + ': missing week keys ' + str(wm)); break
            if w.get('lab') not in LABELS and w.get('lab') not in SENTINEL_LABELS:
                errs.append(pos + '/' + k + ' wk' + str(w.get('wk')) + ': bad label ' + repr(w.get('lab')))
            pp = w.get('p')
            if w.get('lab') not in SENTINEL_LABELS and pp is not None and not (0 <= pp <= 100):
                errs.append(pos + '/' + k + ' wk' + str(w.get('wk')) + ': p ' + str(pp) + ' out of [0,100]')
    if ph > 3:
        errs.append(pos + ': +' + str(ph - 3) + ' more un-interpolated placeholders')
    print('  flags_' + pos + '.json: ' + str(len(d)) + ' players, placeholders=' + str(ph))

if '--quick' not in sys.argv and os.path.exists(B + '/statmenu.json'):
    sm = json.load(open(B + '/statmenu.json'))
    skill = [v for v in sm.values() if v.get('pos') in ('QB', 'RB', 'WR', 'TE')]
    n = len(skill) or 1
    cov = {kk: sum(1 for v in skill if v.get(kk) is not None) for kk in
           ('base_blended', 'adv2', 'chart2', 'cspec')}
    cov['rz'] = sum(1 for v in skill if v.get('pos') in ('WR', 'TE') and v.get('rz') is not None)
    print('  statmenu augmentation coverage (clobber check):')
    for kk, c in cov.items():
        flag = '' if c > 0 else '  <-- ZERO: foundation re-run without augmenters (CLOBBER)'
        print('    ' + kk.ljust(14) + ' ' + str(c) + '/' + str(n) + ' (' + str(round(100 * c / n)) + '%)' + flag)
        if c == 0:
            errs.append("statmenu.json has NO '" + kk + "' on any skill player -> CLOBBER")

if fa_players:
    print('  COVERAGE GAP: ' + str(len(fa_players)) + " player(s) team='FA' (no 2026 schedule -> blank board): "
          + ', '.join(x.split('/')[1] for x in fa_players[:8]) + (' ...' if len(fa_players) > 8 else ''))

print()
if errs:
    print('FAIL: ' + str(len(errs)) + ' error(s)')
    for e in errs[:25]:
        print('  - ' + e)
    if len(errs) > 25:
        print('  ... +' + str(len(errs) - 25) + ' more')
    sys.exit(1)
print('PASS: ' + str(total_players) + ' players across 5 position files, schema + interpolation + ranges clean')
