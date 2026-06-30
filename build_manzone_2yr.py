#!/usr/bin/env python3
"""Build a 2-year (2024+2025) man/zone confidence overlay from FantasyPoints
'Receiving Man vs. Zone' data (boom/fp_manzone_2yr.csv, pulled programmatically
from the FP Data Suite API).

WHY THIS EXISTS (the empirical finding that motivated it):
  YoY stability of the man/zone read, n=121 WR/TE with >=40 man & zone routes BOTH years:
    overall YPRR  r = 0.59
    man   YPRR    r = 0.47
    zone  YPRR    r = 0.48
    MAN-ZONE DELTA r = 0.18   <-- the actual "man-beater / zone-beater" signal
    single-high   r = 0.53
    two-high      r = 0.42
  i.e. a player's man-vs-zone *differential* (what the coverage lever rests on) barely
  persists year to year. Man & zone efficiency individually persist only moderately, and
  mostly because GOOD PLAYERS ARE GOOD VS BOTH (overall r=0.59 > either split). So a
  single-season "man-beater" label is largely noise.

WHAT WE DO ABOUT IT:
  - Blend 2024+2025 route-weighted (halves the sampling error).
  - Only call a coverage lean SOLID when it is CONSISTENT: the player leaned the SAME
    direction in BOTH seasons by a meaningful margin. Otherwise it's a TENDENCY.
  Output: boom/manzone_2yr.json keyed by 'First Last'.
"""
import csv, json, os
H = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(H, 'boom', 'fp_manzone_2yr.csv')
OUT = os.path.join(H, 'boom', 'manzone_2yr.json')

LEAN = 0.30  # min |man-zone YPRR| gap in a season to count as a real lean that year

def f(x):
    try: return float(x)
    except: return None

def wavg(v1, n1, v2, n2):
    n1 = n1 or 0; n2 = n2 or 0
    if n1 + n2 == 0: return None
    return ((v1 or 0)*n1 + (v2 or 0)*n2) / (n1 + n2)

def main():
    rows = list(csv.DictReader(open(SRC)))
    out = {}
    n_consistent = 0
    for r in rows:
        m24r,m24y = f(r['m24r']),f(r['m24y']); z24r,z24y = f(r['z24r']),f(r['z24y'])
        m25r,m25y = f(r['m25r']),f(r['m25y']); z25r,z25y = f(r['z25r']),f(r['z25y'])
        man2y = wavg(m24y,m24r,m25y,m25r); zon2y = wavg(z24y,z24r,z25y,z25r)
        if man2y is None or zon2y is None: continue
        d24 = (m24y - z24y) if (m24y is not None and z24y is not None) else None
        d25 = (m25y - z25y) if (m25y is not None and z25y is not None) else None
        delta2y = man2y - zon2y
        # consistent = same-sign meaningful lean in BOTH seasons
        consistent = (d24 is not None and d25 is not None
                      and abs(d24) >= LEAN and abs(d25) >= LEAN
                      and (d24 > 0) == (d25 > 0))
        if consistent: n_consistent += 1
        name = f"{r['fn']} {r['n']}".strip()
        out[name] = {
            'pos': r['pos'], 'team': r['tm'],
            'man2y': round(man2y,3), 'zon2y': round(zon2y,3),
            'delta2y': round(delta2y,3),
            'man_routes_2y': int((m24r or 0)+(m25r or 0)),
            'zone_routes_2y': int((z24r or 0)+(z25r or 0)),
            'd24': round(d24,3) if d24 is not None else None,
            'd25': round(d25,3) if d25 is not None else None,
            'consistent': consistent,
            # the honest read the dossier should use:
            #   man-beater  -> consistent & delta2y>0
            #   zone-beater -> consistent & delta2y<0
            #   else        -> 'mixed' (treat as no coverage lever / tendency only)
            'read': ('man-beater' if (consistent and delta2y > 0)
                     else 'zone-beater' if (consistent and delta2y < 0)
                     else 'mixed'),
            'tier': 'solid' if consistent else 'tendency',
        }
    json.dump(out, open(OUT,'w'), indent=0)
    man = [k for k,v in out.items() if v['read']=='man-beater']
    zon = [k for k,v in out.items() if v['read']=='zone-beater']
    print(f"manzone_2yr.json: {len(out)} players, {n_consistent} with a CONSISTENT 2-yr lean "
          f"({len(man)} man-beaters, {len(zon)} zone-beaters), {len(out)-n_consistent} mixed/noisy.")
    print("consistent man-beaters:", ", ".join(sorted(man)) or "(none)")
    print("consistent zone-beaters:", ", ".join(sorted(zon)) or "(none)")

if __name__ == '__main__':
    main()
