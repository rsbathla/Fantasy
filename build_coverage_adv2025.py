#!/usr/bin/env python3
"""ADV-2025 coverage-scheme enrichment — post-step to build_coverage_spec.py.

Reads the 2025-season, DraftKings-scored, per-coverage-scheme player exports pulled
2026-07-07 from the FantasyPoints Data Suite "Advanced Receiving" tool
(NFL-master/FP_SWEEP/2025/Receiving/coverageScheme/<Scheme>.csv — positions RB/FB/WR/TE,
full regular season, one row per player, playDefenseCoverageSchemeParent echo verified)
plus the "Receiving Separation by Coverage" export (separation_by_coverage.json — FP
separation WIN/SCORE percentages by bucket: Man/Zone/RedZone/Cover2/3/4/6/Overall).

For every player x scheme it computes the 2025 vintage:
    rte    routes                                  (RoutesTotal)
    tprr   targets per route                       (TargetsTotal / RoutesTotal)
    adot   average depth of target                 (AverageDepthOfTarget)
    ctc    catchable-target share of targets       (TargetsCatchablePercentage)
    dk_rr  DraftKings FP per route                 (playerStatsFantasyPointsDraftKings / RoutesTotal)
    sep_win / sep_score  separation win/score %    (separation tool; only the buckets it
                                                    charts: Cover 2/3/4/6 — C0/C1/Man-C2
                                                    have no per-scheme separation bucket)

and MERGES it into boom/coverage_route_spec.json players[].schemes[<scheme>] under the
key 'adv2025' — strictly additive: existing 2yr rte/yprr/tprr/catch/adot/pctl fields are
never touched (they are 2024+2025 pooled; this block is 2025-only + DK-scoped, hence the
separate, vintage-labeled key). Players outside the spec (RBs, small-sample) are counted
and reported, not added — the spec's WR/TE percentile universe stays intact.

Scheme label map: the filter offers 12 values; the 7 charted shells merge onto the spec's
scheme keys ("Cover 2 Man" file -> spec key "Man Cover 2"). The 5 situational values
(Red Zone / Goal Line / Prevent / Bracket / Miscellaneous) are banked in FP_SWEEP but not
merged — they are situations, not shells, and the spec's scheme axis must stay clean.

FAIL-LOUD: refuses to write if any core scheme CSV parses < MIN_ROWS player rows, or if
fewer than MIN_MERGED spec players receive at least one adv2025 cell.

Run AFTER build_coverage_spec.py (that script rewrites coverage_route_spec.json from the
2yr pool and drops this block; rerun this step to restore it).
"""
import csv, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from core import fn

SRC_DIR = os.path.join(HERE, 'NFL-master', 'FP_SWEEP', '2025', 'Receiving', 'coverageScheme')
SPEC = os.path.join(HERE, 'boom', 'coverage_route_spec.json')
SEP_JSON = os.path.join(SRC_DIR, 'separation_by_coverage.json')

# CSV file -> coverage_route_spec scheme key (the 7 charted shells only)
FILE2SCHEME = {
    'Cover_0.csv': 'Cover 0', 'Cover_1.csv': 'Cover 1', 'Cover_2.csv': 'Cover 2',
    'Cover_3.csv': 'Cover 3', 'Cover_4.csv': 'Cover 4', 'Cover_6.csv': 'Cover 6',
    'Cover_2_Man.csv': 'Man Cover 2',
}
# separation tool bucket -> spec scheme key (only shells the sep tool charts)
SEPBUCKET2SCHEME = {'Cover2': 'Cover 2', 'Cover3': 'Cover 3', 'Cover4': 'Cover 4', 'Cover6': 'Cover 6'}

MIN_ROWS = 100      # per core scheme CSV: player rows parsed
MIN_MERGED = 100    # spec players that must receive >= 1 adv2025 cell
MIN_RTE_DK = 1      # dk_rr/tprr need at least 1 route (they're ratios); we keep rte raw

def num(v):
    if v is None: return None
    v = str(v).strip().replace(',', '')
    if v in ('', '-', 'null', 'None'): return None
    try: return float(v)
    except ValueError: return None

def main():
    if not os.path.isdir(SRC_DIR):
        raise SystemExit(f'build_coverage_adv2025: source dir missing: {SRC_DIR}')
    spec = json.load(open(SPEC))
    players = {p['key']: p for p in spec.get('players', []) if isinstance(p, dict) and p.get('key')}
    if not players:
        raise SystemExit('build_coverage_adv2025: coverage_route_spec.json has no players — run build_coverage_spec.py first')

    # ---- per-scheme advanced CSVs -----------------------------------------
    merged_players, missed = set(), {}
    for fname, scheme in FILE2SCHEME.items():
        path = os.path.join(SRC_DIR, fname)
        if not os.path.exists(path):
            raise SystemExit(f'build_coverage_adv2025: missing {path} — repull the coverageScheme sweep')
        rows = list(csv.DictReader(open(path, encoding='utf-8-sig')))
        if len(rows) < MIN_ROWS:
            raise SystemExit(f'build_coverage_adv2025: {fname} parsed only {len(rows)} rows (<{MIN_ROWS}) — refusing to merge a truncated pull')
        hit = 0
        for r in rows:
            season = (r.get('gameSeason') or '').strip()
            if season and season != '2025':
                raise SystemExit(f'build_coverage_adv2025: {fname} has a non-2025 row (gameSeason={season}) — wrong pull scope')
            k = fn(r.get('Name', ''))
            p = players.get(k)
            if p is None:
                missed[k] = r.get('POS', '')
                continue
            rte = num(r.get('RoutesTotal')); tgt = num(r.get('TargetsTotal'))
            dk = num(r.get('playerStatsFantasyPointsDraftKings'))
            adot = num(r.get('AverageDepthOfTarget')); ctc = num(r.get('TargetsCatchablePercentage'))
            cell = p.setdefault('schemes', {}).setdefault(scheme, {})
            if 'adv2025' in cell and cell['adv2025']:
                pass  # idempotent rerun: overwrite our own block only
            adv = {
                'rte': int(rte) if rte is not None else None,
                'tprr': round(tgt / rte, 3) if rte and tgt is not None else None,
                'adot': round(adot, 1) if adot is not None else None,
                'ctc': round(ctc, 3) if ctc is not None else None,
                'dk_rr': round(dk / rte, 3) if rte and dk is not None else None,
            }
            cell['adv2025'] = adv
            merged_players.add(k); hit += 1
        print(f'  {fname:18} -> {scheme:12}: {len(rows):4} rows, {hit:3} merged onto spec players')

    # ---- separation buckets ------------------------------------------------
    sep_hit = 0
    if os.path.exists(SEP_JSON):
        sep = json.load(open(SEP_JSON))
        for rec in sep.get('players', []):
            p = players.get(fn(rec.get('name', '')))
            if p is None: continue
            for bucket, scheme in SEPBUCKET2SCHEME.items():
                b = (rec.get('buckets') or {}).get(bucket)
                cell = (p.get('schemes') or {}).get(scheme)
                if not b or cell is None or 'adv2025' not in cell: continue
                cell['adv2025']['sep_win'] = round(b['sep_win'], 3) if b.get('sep_win') is not None else None
                cell['adv2025']['sep_score'] = round(b['sep_score'], 3) if b.get('sep_score') is not None else None
                sep_hit += 1
            # man/zone separation rollups -> player level (the shells C0/C1/MC2 have no sep bucket)
            mz = {}
            for bucket in ('Man', 'Zone'):
                b = (rec.get('buckets') or {}).get(bucket)
                if b: mz[bucket.lower()] = {'rte': b.get('rte'),
                                            'sep_win': round(b['sep_win'], 3) if b.get('sep_win') is not None else None,
                                            'sep_score': round(b['sep_score'], 3) if b.get('sep_score') is not None else None}
            if mz: p['sep2025'] = mz
    else:
        print(f'  !! separation_by_coverage.json absent — adv2025 written without sep fields')

    if len(merged_players) < MIN_MERGED:
        raise SystemExit(f'build_coverage_adv2025: only {len(merged_players)} spec players merged (<{MIN_MERGED}) — name-join broke, not writing')

    spec['adv2025'] = {
        'season': 2025, 'scoring': 'DraftKings', 'pulled': '2026-07-07',
        'source': 'FantasyPoints Data Suite receiving-advanced (coverageScheme filter) + receiving-separation-by-coverage',
        'fields': {'rte': 'routes', 'tprr': 'targets/route', 'adot': 'avg depth of target',
                   'ctc': 'catchable share of targets', 'dk_rr': 'DK FP per route',
                   'sep_win': 'separation win % of routes (C2/C3/C4/C6 only)',
                   'sep_score': 'separation score % of routes (C2/C3/C4/C6 only)'},
        'players_merged': len(merged_players),
        'not_in_spec': len(missed),
    }
    json.dump(spec, open(SPEC, 'w'), separators=(',', ':'))
    from collections import Counter
    print(f'adv2025 merge: {len(merged_players)} spec players enriched · {sep_hit} scheme-cells got separation · '
          f'{len(missed)} pulled players not in spec {Counter(missed.values()).most_common()}')
    # spot checks
    for nm in ('Puka Nacua', "Ja'Marr Chase"):
        p = players.get(fn(nm))
        if not p: print(f'  !! {nm} not found'); continue
        c3 = (p['schemes'].get('Cover 3') or {}).get('adv2025')
        c0 = (p['schemes'].get('Cover 0') or {}).get('adv2025')
        print(f'  {nm}: C3 adv2025={c3} | C0 adv2025={c0} | sep2025={p.get("sep2025")}')

if __name__ == '__main__':
    main()
