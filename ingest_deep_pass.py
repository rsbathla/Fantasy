#!/usr/bin/env python3
"""2-yr QB deep-passing rate -> boom/deep_pass.json.
Reads FantasyPoints Passing/TargetDirection_SD Deep.csv + Short.csv across ALL available years
(2024+2025), sums deep vs short attempts per QB, and computes deep-throw RATE = deepATT/(deep+short)
plus deep Y/A. A high, STABLE deep rate is the QB analogue of a WR vertical lever: it turns single-high /
soft-deep shells into ceiling spots. Percentile is taken among QBs with a real 2-yr sample."""
import csv, os, json, glob, re
HERE = os.path.dirname(os.path.abspath(__file__))
def fn(n):
    n = str(n).strip().lower(); n = re.sub(r'\s+(jr|sr|ii|iii|iv|v)\.?$', '', n)
    return n.replace('.', '').replace("'", "").replace('-', ' ').strip()
def num(x):
    try: return float(str(x).replace('%', '').replace(',', '').strip())
    except Exception: return None

# locate NFL-master/FP (same resolution as ingest_coverage.py)
roots = []
try:
    import core
    try: roots.append(os.path.dirname(core.find_data('NFL-master', 'FP', '2025')))
    except Exception: pass
except Exception: pass
roots += [os.path.join(os.path.dirname(HERE), 'NFL-master', 'FP'), os.path.join(HERE, 'NFL-master', 'FP')]
base = next((r for r in roots if r and os.path.isdir(r)), None)

agg = {}
if base:
    for y in sorted(glob.glob(os.path.join(base, '*'))):
        cd = os.path.join(y, 'Passing', 'TargetDirection_SD')
        for depth, fname in (('deep', 'Deep.csv'), ('short', 'Short.csv')):
            f = os.path.join(cd, fname)
            if not os.path.exists(f): continue
            for r in csv.DictReader(open(f, encoding='utf-8-sig')):
                if (r.get('POS') or '').upper() != 'QB': continue
                k = fn(r.get('Name', '')); att = num(r.get('ATT'))
                if not k or not att: continue
                a = agg.setdefault(k, {'name': r['Name'], 'deep_att': 0.0, 'short_att': 0.0, 'deep_yds': 0.0})
                a[depth + '_att'] += att
                if depth == 'deep': a['deep_yds'] += (num(r.get('YDS')) or 0)

out = {}
rated = []
for k, a in agg.items():
    tot = a['deep_att'] + a['short_att']
    if tot < 100:  # need a real 2-yr pass sample
        continue
    rate = 100 * a['deep_att'] / tot
    out[k] = {'name': a['name'], 'deep_rate': round(rate, 1),
              'deep_att': round(a['deep_att']), 'deep_ypa': round(a['deep_yds'] / a['deep_att'], 1) if a['deep_att'] else None}
    rated.append((k, rate))
rates = sorted(r for _, r in rated)
for k, rate in rated:
    out[k]['deep_pctl'] = round(100 * sum(1 for x in rates if x <= rate) / len(rates))

os.makedirs(os.path.join(HERE, 'boom'), exist_ok=True)
json.dump(out, open(os.path.join(HERE, 'boom', 'deep_pass.json'), 'w'), ensure_ascii=False, indent=1)
print(f"ingest_deep_pass: {len(out)} QBs (base={base})")
for nm in ['Josh Allen', 'Matthew Stafford', 'Jordan Love', 'Patrick Mahomes', 'Jared Goff']:
    v = out.get(fn(nm))
    if v: print(f"  {nm:18s} deep_rate={v['deep_rate']}% (pctl {v['deep_pctl']}) deep_ypa={v['deep_ypa']} att={v['deep_att']}")
