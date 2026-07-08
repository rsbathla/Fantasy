#!/usr/bin/env python3
"""build_proe_personnel.py — add the PERSONNEL term to the 2026 PROE model.

Motivation (Ramneik's SEA question): proe_tendency_2026 = 2025 actual + coaching-carousel step,
but roster churn moves expected pass rate too — e.g., SEA losing Kenneth Walker (8% of '25 target
volume, lead rusher) is a real input the carousel can't see. Module D (team_review_data.json)
already models a personnel-driven pass-attempt delta per team (d_pa, att/g); this wires it in:

    proe_2026 = proe_2025 + carousel_adj + personnel_adj
    personnel_adj = clip(d_pa * K, ±CAP)   K=1.6 PROE-pts per pass-att/g (≈1/0.62 plays base),
                                           CAP=2.0 — bounded like the carousel assumption.

Idempotent: recomputes from base fields each run; provenance stamped in _meta.
Run:  python3 build_proe_personnel.py
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
K, CAP = 1.6, 2.0

tr = json.load(open(os.path.join(HERE, 'team_review_data.json')))
pt_path = os.path.join(HERE, 'proe_tendency_2026.json')
pt = json.load(open(pt_path))

# d_pa carries a league-wide level shift (Module D projects total volume down across the board).
# PROE is a RELATIVE stat, so demean: only above/below-league churn moves a team's PROE.
d_pas = {t: ((tr.get(t) or {}).get('delta') or {}).get('d_pa') for t in pt['teams']}
have = [v for v in d_pas.values() if v is not None]
lg_mean = sum(have) / len(have) if have else 0.0

changed = []
for team, rec in pt['teams'].items():
    d_pa = d_pas.get(team)
    if d_pa is None:
        rec['personnel_adj'] = 0.0
        rec['personnel_note'] = 'no Module D delta available'
    else:
        rel = d_pa - lg_mean
        adj = round(max(-CAP, min(CAP, rel * K)), 1)
        rec['personnel_adj'] = adj
        rec['personnel_note'] = (f"Module D d_pa {d_pa:+.1f} vs lg {lg_mean:+.1f} -> rel {rel:+.1f} "
                                 f"att/g -> {adj:+.1f} PROE pts (K={K}, cap ±{CAP})")
    new = round(rec['proe_2025'] + rec.get('carousel_adj', 0) + rec['personnel_adj'], 1)
    if new != rec.get('proe_2026'):
        changed.append((team, rec.get('proe_2026'), new, rec['personnel_adj']))
    rec['proe_2026'] = new

pt['_meta']['personnel_term'] = (f"personnel_adj = clip(d_pa*{K}, ±{CAP}) from team_review_data.json "
                                 "Module D (roster-churn pass-volume delta); added per user request "
                                 "(SEA/Walker case). Bounded assumption, provenance: build_proe_personnel.py")
json.dump(pt, open(pt_path, 'w'), indent=1)
print(f"updated {len(changed)} teams' proe_2026 (|personnel_adj|>0 or rounding):")
for t, old, new, adj in sorted(changed, key=lambda x: -abs(x[3]))[:12]:
    print(f"  {t}: {old} -> {new}  (personnel {adj:+.1f})")
print("\nSEA check:", json.dumps(pt['teams']['SEA'], indent=1))
