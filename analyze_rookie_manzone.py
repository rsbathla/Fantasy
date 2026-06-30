#!/usr/bin/env python3
"""Man vs zone read for rookie pass-catchers.
Part 1: do rookie WR/TE boom more facing MAN-heavy or ZONE-heavy defenses? (rookie-games tagged
        with opponent season man-rate from defense_coverage.csv)
Part 2: are the rookies themselves man-beaters or zone-beaters, and which boom more? (cover_spec.json
        per-player man/zone percentiles + season boom rate b25/g25 from base2yr)
Caveats: opponent man-rate is a season-level team avg (proxy, not per-snap); rookie samples are thin.
"""
import core, csv, json, collections

b2 = json.load(open(core.P('boom/base2yr.json'), encoding='utf-8'))
rookies = {k: v for k, v in b2.items() if (not v.get('g24')) and (v.get('g25') or 0) > 0}
gl = json.load(open(core.P('boom/gamelog.json'), encoding='utf-8'))
sm = json.load(open(core.P('boom/statmenu.json'), encoding='utf-8'))
cs = json.load(open(core.P('boom/cover_spec.json'), encoding='utf-8'))
cs = cs if isinstance(cs, dict) and 'man' not in cs else cs
defcov = {core.norm_team(r['team']): float(r['def_man_rate'])
          for r in csv.DictReader(open(core.P('defense_coverage.csv'), encoding='utf-8')) if r.get('def_man_rate')}

# ---------- Part 1: opponent scheme -> rookie boom ----------
rows = []
for k in rookies:
    if k not in gl or not isinstance(gl[k], list): continue
    if (sm.get(k, {}) or {}).get('pos') not in ('WR', 'TE'): continue
    for g in gl[k]:
        mr = defcov.get(core.norm_team(g.get('opp')))
        if g.get('boom') is None or mr is None: continue
        rows.append((mr, int(g['boom'])))
rows.sort()
print(f"=== Part 1: rookie WR/TE games vs opponent man-rate (n={len(rows)} games) ===")
if len(rows) >= 12:
    med = rows[len(rows)//2][0]
    zone_heavy = [b for mr, b in rows if mr <= med]   # low man-rate = zone-heavy opp
    man_heavy = [b for mr, b in rows if mr > med]
    print(f"  vs ZONE-heavy D (opp man<= {med:.1f}%): boom={sum(zone_heavy)/len(zone_heavy):.3f}  n={len(zone_heavy)}")
    print(f"  vs MAN-heavy  D (opp man>  {med:.1f}%): boom={sum(man_heavy)/len(man_heavy):.3f}  n={len(man_heavy)}")

# ---------- Part 2: rookie man/zone aptitude (cover_spec) ----------
print(f"\n=== Part 2: rookie WR/TE man/zone profile (cover_spec) ===")
recs = []
for k, v in rookies.items():
    c = cs.get(k)
    if not c or c.get('pos') not in ('WR', 'TE'): continue
    pc = c.get('pctls') or {}
    g25 = v.get('g25') or 0; boom = (v.get('b25') or 0) / g25 if g25 else None
    recs.append({'name': c.get('name', k), 'best': c.get('best'), 'best_key': c.get('best_key'),
                 'man_pctl': pc.get('man'), 'zone_pctl': pc.get('zone'), 'boom': boom, 'g25': g25})
print(f"  rookie WR/TE in cover_spec: {len(recs)}")
bk = collections.Counter(r['best_key'] for r in recs if r['best_key'])
print(f"  'best vs' coverage counts: {dict(bk)}")
mp = [r['man_pctl'] for r in recs if r['man_pctl'] is not None]
zp = [r['zone_pctl'] for r in recs if r['zone_pctl'] is not None]
if mp and zp:
    print(f"  mean man-coverage pctl = {sum(mp)/len(mp):.0f} | mean zone-coverage pctl = {sum(zp)/len(zp):.0f}")
# boom by aptitude
def avg(xs): return sum(xs)/len(xs) if xs else None
zb = [r['boom'] for r in recs if r['best_key'] in ('zone', 'two_high') and r['boom'] is not None and r['g25'] >= 4]
mb = [r['boom'] for r in recs if r['best_key'] in ('man', 'single_high') and r['boom'] is not None and r['g25'] >= 4]
print(f"  season boom rate: zone-beater rookies={avg(zb)} (n={len(zb)}) | man-beater rookies={avg(mb)} (n={len(mb)})")
print("  top rookie zone-beaters:", [r['name'] for r in sorted(recs, key=lambda r:-(r['zone_pctl'] or 0))[:5]])
print("  top rookie man-beaters: ", [r['name'] for r in sorted(recs, key=lambda r:-(r['man_pctl'] or 0))[:5]])
