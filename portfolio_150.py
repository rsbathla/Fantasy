#!/usr/bin/env python3
"""portfolio_150.py — Ramneik's idea, made testable:

  "sim the games based on distribution of outputs, build lineups off that with the
   rules we have, and see if we can create 150 strong lineups to win."

Pipeline per slate:
  1. simulate W correlated worlds (contest_sim machinery: pair_rho + lognormal)
  2. WORLD-CHAMPION candidates: in each sampled world, greedily build the
     highest-scoring legal DK lineup (roster template + salary + QB-stack repair) —
     a world where MIA blows up yields a MIA-stack champion, so the candidate pool
     automatically expresses the outcome distribution
  3. score every candidate against an ownership-sampled field WITH the dupe tax
  4. select 150 by greedy WIN-COVERAGE: maximize the number of worlds in which at
     least one portfolio lineup beats the entire sampled field (EV as tiebreak) —
     150 lineups spread across the distribution of outcomes, not 150 clones of one view
  5. BACKTEST: score the same field sample on the slate's ACTUAL points, estimate each
     portfolio lineup's real-world placement, pay it through the real payout curve,
     and put the P&L next to rsbathla's REAL P&L in that exact contest
     (calibration check: sampled cash-line score vs the contest's true cashLine)
"""
import argparse, csv, glob, json, os, sys
from collections import defaultdict
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from contest_sim import (load_slate, simulate_worlds, sample_field, payout_curve, FL_DIR)

DATA = os.path.join(HERE, 'data', 'fantasylabs')
SLOTS = {'QB': 1, 'RB': 2, 'WR': 3, 'TE': 1, 'DST': 1}          # + 1 FLEX (RB/WR/TE)
CAP = 50000


def contest_row(date_s, lo=19, hi=26):
    """cid + cashLine for the flagship Milly that load_slate(tier='20') picks."""
    best = None
    for r in csv.DictReader(open(os.path.join(DATA, 'contest_meta.csv'))):
        if r['date'] != date_s or r['slate'] != 'main':
            continue
        if 'millionaire' not in r['contestName'].lower():
            continue
        try:
            e = float(r['entryCost'])
        except ValueError:
            continue
        if not (lo <= e <= hi):
            continue
        if best is None or int(r['contestSize']) > int(best['contestSize']):
            best = r
    return best


def world_champion(pool, wpts, sal, rng):
    """Greedy max-points legal lineup for one world; QB-stack repair after fill."""
    order = np.argsort(-wpts)
    need = dict(SLOTS); flex = 1
    picks, tot = [], 0
    min_sal = {'QB': 4000, 'RB': 3000, 'WR': 3000, 'TE': 2500, 'DST': 2000}
    for i in order:
        if len(picks) == 9:
            break
        p = pool[i]
        take = None
        if need.get(p.pos, 0) > 0:
            take = p.pos
        elif flex and p.pos in ('RB', 'WR', 'TE'):
            take = 'FLEX'
        if take is None:
            continue
        rem_slots = 8 - len(picks)
        rem_min = 2500 * rem_slots
        if tot + sal[i] + rem_min > CAP:
            continue
        picks.append(int(i)); tot += sal[i]
        if take == 'FLEX':
            flex = 0
        else:
            need[take] -= 1
    if len(picks) < 9:
        return None
    # stack repair: QB must carry >=1 same-team pass-catcher (the ruleset's floor)
    qb = next(i for i in picks if pool[i].pos == 'QB')
    mates = [i for i in picks if i != qb and pool[i].team == pool[qb].team
             and pool[i].pos in ('WR', 'TE', 'RB')]
    if not mates:
        cands = [i for i in range(len(pool)) if i not in picks
                 and pool[i].team == pool[qb].team and pool[i].pos in ('WR', 'TE')]
        if not cands:
            return None
        best_in = max(cands, key=lambda i: wpts[i])
        outs = sorted((i for i in picks if pool[i].pos == pool[best_in].pos and i != qb),
                      key=lambda i: wpts[i])
        for out in outs:
            if tot - sal[out] + sal[best_in] <= CAP:
                picks[picks.index(out)] = int(best_in)
                tot += sal[best_in] - sal[out]
                break
        else:
            return None
    return tuple(sorted(picks))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', required=True)
    ap.add_argument('--tier', default='20')
    ap.add_argument('--worlds', type=int, default=2000)
    ap.add_argument('--field', type=int, default=3000)
    ap.add_argument('--champ-worlds', type=int, default=1000)
    ap.add_argument('--n', type=int, default=150)
    ap.add_argument('--json-out')
    A = ap.parse_args()

    pool, meta, _ = load_slate(A.date, tier=A.tier)
    if pool is None:
        sys.exit(f"no tier-{A.tier} contest on {A.date}")
    W, F, N = A.worlds, A.field, A.n
    payout_at, pool_total, first, places = payout_curve(meta)
    sal = np.array([p.salary for p in pool])
    acts = np.array([p.actual for p in pool])
    pts = simulate_worlds(pool, W)
    rng = np.random.default_rng(7)

    # ---- 2) world-champion candidates ----
    seen = {}
    widx = rng.choice(W, size=min(A.champ_worlds, W), replace=False)
    for w in widx:
        lu = world_champion(pool, pts[:, w], sal, rng)
        if lu:
            seen[lu] = seen.get(lu, 0) + 1
    cands = np.array([list(l) for l in seen], dtype=np.int32)
    print(f"{A.date}  '{meta['name'][:40]}'  ${meta['entry']:.0f} x {meta['size']:,}",
          file=sys.stderr)
    print(f"  {len(widx)} champion worlds -> {len(cands)} distinct candidates",
          file=sys.stderr)

    # ---- 3) score vs field with dupe tax ----
    field = sample_field(pool, F, sharp_frac=0.15 if meta['entry'] < 300 else 0.55)
    fs = np.sort(pts[field.reshape(-1)].reshape(F, 9, W).sum(axis=1), axis=0)
    cs = pts[cands.reshape(-1)].reshape(len(cands), 9, W).sum(axis=1)
    scale = meta['size'] / F
    fkeys = defaultdict(int)
    for row in field:
        fkeys[frozenset(row.tolist())] += 1
    dupes = np.array([fkeys.get(frozenset(c.tolist()), 0) * scale for c in cands])
    C = len(cands)
    urng = np.random.default_rng(99)
    U = urng.uniform(size=(C, W))
    r = np.empty((C, W))
    for wix in range(W):
        r[:, wix] = F - np.searchsorted(fs[:, wix], cs[:, wix], side='right')
    place = np.maximum((r + U) * scale, 1.0)
    pay = np.vectorize(payout_at)(place) / (1 + dupes)[:, None]
    ev = pay.mean(axis=1)
    win = (r >= F)                                     # beats the whole sampled field

    # ---- 4) greedy win-coverage selection of N ----
    covered = np.zeros(W, dtype=bool)
    chosen = []
    ev_rank = np.argsort(-ev)
    for _ in range(min(N, C)):
        gain = win[:, ~covered].sum(axis=1).astype(float)
        gain[chosen] = -1
        gain += ev / (abs(first) + 1)                  # EV as tiebreak
        pick = int(np.argmax(gain))
        chosen.append(pick)
        covered |= win[pick]
    chosen = np.array(chosen)
    port_ev = ev[chosen].sum()
    # portfolio P(at least one lineup beats the field) per world
    p_takedown = covered.mean()
    cost = meta['entry'] * len(chosen)
    print(f"  sim: portfolio EV ${port_ev:,.0f} on ${cost:,.0f} "
          f"({(port_ev-cost)/cost*100:+.0f}% ROI) | P(beat entire field sample in a world) "
          f"{p_takedown*100:.1f}%", file=sys.stderr)

    # ---- 5) backtest on ACTUALS ----
    fact = np.sort(acts[field.reshape(-1)].reshape(F, 9).sum(axis=1))
    cact = acts[cands[chosen].reshape(-1)].reshape(len(chosen), 9).sum(axis=1)
    ra = F - np.searchsorted(fact, cact, side='right')
    pa = np.maximum((ra + urng.uniform(size=len(chosen))) * scale, 1.0)
    real_pay = np.array([payout_at(x) for x in pa]) / (1 + dupes[chosen])
    real_pnl = real_pay.sum() - cost
    cash_cut = fact[max(0, int(F - places / scale))]   # sampled score at the cash line
    row = contest_row(A.date)
    # NB: FL's cashLine = NUMBER OF PAID ENTRIES (a count), not a points cutoff
    cl = float(row['cashLine']) if row and row.get('cashLine') else None
    his = None
    if row:
        for up in glob.glob(os.path.join(DATA, 'users', f"{A.date}_{row['contestId']}_rsbathla.json")):
            rec = json.load(open(up))
            for h in rec.get('hits', []):
                hr = h.get('record') or {}
                if hr.get('totalEntryCost'):
                    his = {'in': hr['totalEntryCost'], 'out': hr.get('totalWinning', 0),
                           'n': hr.get('totalRosters')}
                    break
            if his:
                break
    print(f"  backtest: best lineup {cact.max():.1f} pts (est place {pa.min():,.0f}) | "
          f"portfolio real P&L ${real_pnl:+,.0f}", file=sys.stderr)
    cl_s = f"{cl:,.0f} paid places ({cl/meta['size']*100:.0f}%)" if cl else "?"
    print(f"  calibration: parametric paid-places {places:,.0f} "
          f"({places/meta['size']*100:.0f}%) vs real {cl_s}; "
          f"sampled cash-cut score {cash_cut:.1f}", file=sys.stderr)
    if his:
        print(f"  rsbathla real: {his['n']} entries ${his['in']:,.0f} in -> "
              f"${his['out']:,.0f} out (${his['out']-his['in']:+,.0f})", file=sys.stderr)
    if A.json_out:
        json.dump({'date': A.date, 'ev': float(port_ev), 'cost': float(cost),
                   'p_takedown': float(p_takedown), 'real_pnl': float(real_pnl),
                   'best_act': float(cact.max()), 'cash_cut': float(cash_cut),
                   'cashline': cl, 'his': his,
                   'lineups': [[pool[i].name for i in cands[c]] for c in chosen[:10]]},
                  open(A.json_out, 'w'))


if __name__ == '__main__':
    main()
