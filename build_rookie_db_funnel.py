#!/usr/bin/env python3
"""Rookie-aware WR funnel input: grade incoming 2026 rookie DBs from 2025 college pass-defense.

A 2026 rookie corner who steps into a starting role tightens his NFL team's pass funnel — but
the funnel currently grades secondaries off 2025 NFL data, so it has a blind spot for rookies
(no NFL sample). This builds college coverage grades for those DBs so the funnel can see them.
Completing the funnel ADJUSTMENT needs the 2026 defensive-draft mapping (rookie DB -> NFL team),
which best-ball boards omit; the grades are ready to apply once that mapping is supplied.
"""
import core, csv, json, os

def CFB(f): return core.P(os.path.join('sis_value', 'cfb', f))
def num(x):
    try: return float(str(x).replace('%', '').replace(',', '').replace('"', '').strip())
    except (TypeError, ValueError): return None
def col(r, *names):
    for n in names:
        if n in r: return r[n]
    return None
def pctl(vals, invert=False):
    present = [v for v in vals if v is not None]; out = [None] * len(vals); n = len(present)
    if n == 0: return out
    for i, v in enumerate(vals):
        if v is None: continue
        less = sum(1 for x in present if x < v); eq = sum(1 for x in present if x == v)
        p = (less + 0.5 * eq) / n * 100
        out[i] = round(100 - p if invert else p, 1)
    return out

def main():
    rows = list(csv.DictReader(open(CFB('cfb_passdef_value_2025.csv'), encoding='utf-8')))
    ps = [num(col(r, 'Points Saved')) for r in rows]
    epat = [num(col(r, 'EPA/Tgt', 'EPA Per Tgt')) for r in rows]
    ps_p = pctl(ps)                 # more Points Saved = better coverage
    epa_p = pctl(epat, invert=True)  # lower EPA/target allowed = better coverage
    out = {}
    for i, r in enumerate(rows):
        nm = col(r, 'Player')
        if not nm: continue
        comps = [x for x in (ps_p[i], epa_p[i]) if x is not None]
        out[core.fn(nm)] = {
            'name': nm.strip(), 'college': (col(r, 'Team') or '').strip(),
            'pos': (col(r, 'Pos.', 'Pos') or 'DB').strip(),
            'points_saved': num(col(r, 'Points Saved')),
            'epa_per_tgt': num(col(r, 'EPA/Tgt', 'EPA Per Tgt')),
            'coverage_pctl_2025': round(sum(comps) / len(comps), 1) if comps else None,
        }
    core.safe_json_dump({'note': '2025 college pass-defense coverage grades for incoming 2026 rookie DBs. '
                                 'Funnel use: a rookie DB who STARTS tightens his NFL team pass funnel; '
                                 'completing the adjustment needs the 2026 defensive-draft mapping (DB -> NFL team), '
                                 'which best-ball boards omit. Grades are ready to apply once that mapping is supplied.',
                         'n': len(out), 'dbs': out}, core.P('boom/rookie_db_grades.json'))
    top = sorted(out.values(), key=lambda r: -(r['coverage_pctl_2025'] or 0))[:10]
    print(f"rookie_db_grades.json: {len(out)} college DBs graded (2025)")
    for r in top: print(f"   {r['name']:24} {r['college']:18} cov_pctl={r['coverage_pctl_2025']}")

if __name__ == '__main__':
    main()
