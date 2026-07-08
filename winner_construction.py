#!/usr/bin/env python3
"""winner_construction.py — what constructions actually populate the TOP of GPPs?

Reads data/fantasylabs/stacks_full/*.json (from `fl_puller.py --restacks`), which carry
FL's stack exposures at tiers {1, 10, 20, 100} = top-1% / top-10% / top-20% / full field,
plus a player id -> (name, pos, team) map.

Per contest & tier it measures (units = % of that tier's lineups):
  qb+1 / qb+2 / qb+3plus : team stacks anchored by the QB, by number of teammates
  qb_any                 : any QB team stack  ->  naked_est = 100 - qb_any
  bringback_qb           : game stacks with the QB AND at least one opponent
  bringback_noqb         : both sides of a game stacked, no QB in the combo
  team_noqb              : non-QB same-team mini-stacks (WR+WR, RB+DST, ...)

Then the construction EDGE = top-1% value minus full-field value, aggregated by
season x contest bucket ($20 milly / high-stakes milly / wildcat / single-entry-ish
main / smaller slates / showdown). Writes construction_summary.csv next to the data.

Sanity guard: if sum(QB-anchored stack %) > 115 for a tier, FL is double-counting
sub-stacks and naked_est is untrustworthy -> flagged, excluded from naked aggregation.
"""
import csv, glob, json, os, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = None
for cand in (os.path.join(HERE, 'data', 'fantasylabs'), os.path.join('data', 'fantasylabs')):
    if os.path.isdir(cand):
        DATA = cand
        break
if not DATA:
    sys.exit("no data/fantasylabs directory found")
SDIR = os.path.join(DATA, 'stacks_full')
TIERS = ('1', '10', '20', '100')


def season_of(d):
    y, m = int(d[:4]), int(d[5:7])
    return y if m >= 8 else y - 1


def bucket(rec):
    name = (rec.get('contestName') or '').lower()
    cost = float(rec.get('entryCost') or 0)
    slate = rec.get('slate') or ''
    if slate == 'showdown':
        return 'showdown'
    if slate not in ('main',):
        return 'smaller'
    if 'millionaire' in name:
        return 'milly$20' if cost <= 30 else ('millyHIGH' if cost >= 300 else 'millyMID')
    if 'wildcat' in name or cost == 333:
        return 'wildcat'
    if 'single entry' in name or 'thunderdome' in name:
        return 'single'
    return 'mainOther'


def classify(rec):
    """-> {tier: {class: pct}} for one contest, or None if unusable."""
    pmap = {}
    for pid, v in (rec.get('players') or {}).items():
        pmap[pid] = (v[1], v[2])                     # (pos, team)
    if not pmap:
        return None
    out = {}
    for kind, blk in (('team', rec.get('teamStacks') or {}),
                      ('game', rec.get('gameStacks') or {})):
        for tier, tblk in blk.items():
            if tier not in TIERS:
                continue
            stacks = (tblk or {}).get('teamStacksObject') or (tblk or {}).get('gameStacksObject') \
                     or {k: v for k, v in (tblk or {}).items() if isinstance(v, dict)}
            agg = out.setdefault(tier, defaultdict(float))
            for key, s in stacks.items():
                if not isinstance(s, dict):
                    continue
                pids = s.get('players') or key.split(':')
                if pids and ':' not in str(pids[0]):   # key-split fallback: re-join id:slot
                    raw = key.split(':')
                    pids = [f"{raw[i]}:{raw[i+1]}" for i in range(0, len(raw) - 1, 2)]
                pct = float(s.get('stackPerc') or 0)
                poss = [pmap.get(p, (None, None))[0] for p in pids]
                teams = {pmap.get(p, (None, None))[1] for p in pids} - {None}
                has_qb = 'QB' in poss
                if kind == 'team':
                    if has_qb:
                        n = len(pids) - 1
                        agg['qb+1' if n == 1 else ('qb+2' if n == 2 else 'qb+3plus')] += pct
                        agg['qb_any'] += pct
                    else:
                        agg['team_noqb'] += pct
                else:
                    if len(teams) >= 2:
                        agg['bringback_qb' if has_qb else 'bringback_noqb'] += pct
                    else:
                        agg['game_oneside'] += pct
    return out or None


def main():
    files = sorted(glob.glob(os.path.join(SDIR, '*.json')))
    if not files:
        sys.exit(f"no stacks_full/*.json yet — run:  python3 fl_puller.py --restacks --all-types")
    rows = []
    flagged = 0
    for fp in files:
        try:
            rec = json.load(open(fp))
        except Exception:
            continue
        tiers = classify(rec)
        if not tiers:
            continue
        b = bucket(rec)
        s = season_of(rec['date'])
        for tier, agg in tiers.items():
            ok_naked = agg.get('qb_any', 0) <= 115
            if not ok_naked:
                flagged += 1
            row = {'date': rec['date'], 'season': s, 'bucket': b, 'tier': tier,
                   'contestId': rec['contestId'], 'entry': rec['entryCost'],
                   'size': rec['contestSize'], 'naked_ok': int(ok_naked)}
            for k in ('qb+1', 'qb+2', 'qb+3plus', 'qb_any', 'team_noqb',
                      'bringback_qb', 'bringback_noqb', 'game_oneside'):
                row[k] = round(agg.get(k, 0.0), 2)
            row['naked_est'] = round(max(0.0, 100 - agg.get('qb_any', 0.0)), 2) if ok_naked else ''
            rows.append(row)
    outp = os.path.join(DATA, 'construction_summary.csv')
    with open(outp, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(files)} contests -> {len(rows)} tier-rows -> {outp}  "
          f"({flagged} tier-rows failed the naked sanity guard)")

    # ---- aggregate: top-1% MINUS full-field, by season x bucket ----
    key = lambda r: (r['season'], r['bucket'], r['contestId'])
    by_c = defaultdict(dict)
    for r in rows:
        by_c[key(r)][r['tier']] = r
    METRICS = ('qb+1', 'qb+2', 'qb+3plus', 'naked_est', 'bringback_qb', 'team_noqb')
    agg = defaultdict(lambda: defaultdict(list))
    for (season, b, cid), tiers in by_c.items():
        t1, t100 = tiers.get('1'), tiers.get('100')
        if not (t1 and t100):
            continue
        for m in METRICS:
            a, z = t1.get(m), t100.get(m)
            if a in ('', None) or z in ('', None):
                continue
            agg[(season, b)][m].append((float(a), float(z)))
    print(f"\n{'season':<7}{'bucket':<11}{'n':>4} | " +
          ' | '.join(f"{m:>16}" for m in METRICS))
    print(f"{'':<22} | " + ' | '.join(f"{'top1%  field':>16}" for _ in METRICS))
    for (season, b) in sorted(agg):
        vals = agg[(season, b)]
        n = max((len(v) for v in vals.values()), default=0)
        cells = []
        for m in METRICS:
            v = vals.get(m)
            if v:
                a = sum(x for x, _ in v) / len(v)
                z = sum(y for _, y in v) / len(v)
                cells.append(f"{a:5.1f} vs {z:5.1f}")
            else:
                cells.append(' ' * 14)
        print(f"{season:<7}{b:<11}{n:>4} | " + ' | '.join(f"{c:>16}" for c in cells))
    print("\n(each cell: mean % of top-1% lineups vs mean % of the full field carrying that")
    print(" construction — the GAP is what the winners do differently.)")


if __name__ == '__main__':
    main()
