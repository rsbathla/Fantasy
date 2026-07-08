#!/usr/bin/env python3
"""
contest_sim.py — GPP contest simulator (SaberSim/Stokastic-style), v1.

The backtests proved the flaw: both our optimizer modes maximize raw projection, so they build
the same ~166%-owned chalk and add no leverage. This replaces the objective. Instead of asking
"which lineup projects highest?" we ask "which lineup makes the most MONEY against the real
field?" — by simulating both:

  1. PLAYER WORLDS   correlated outcome draws using the measured 2015-25 correlation structure
                     (pair_rho from dfs_optimizer: QB-WR1 0.35, bring-back 0.07, ...), lognormal
                     marginals (right skew = booms), sd = CV[pos] * projection.
  2. THE FIELD       opponent lineups sampled from REAL Milly-Maker ownership (FantasyLabs pull),
                     stack-aware (~55% of field QBs stacked), salary-feasible.
  3. THE PAYOUT      parametric DK GPP curve fit to the contest's real metadata (prize pool,
                     first-place prize parsed from the contest name, entry fee, field size),
                     with duplicate-split on your payout.

Candidates come from the existing ILP generator at several OWNERSHIP-FADE levels
(maximize proj - lambda*ownership) plus the portfolio archetypes — then every candidate is
scored by simulated ROI / cash% / top-0.1%, which is the number that actually decides entries.

Run:  python3 contest_sim.py --slate 2024-12-08 [--worlds 4000 --field 4000 --n 150]
"""
import argparse, csv, glob, gzip, math, os, re, sys
from collections import defaultdict
import numpy as np

from dfs_optimizer import (Player, pair_rho, CV, _assign_wr_ranks, _generate, SALARY_CAP,
                           optimize_portfolio, estimate_ownership)

FL_DIR = os.environ.get('FL_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                               'data', 'fantasylabs', 'players'))
POS = {'QB': 'QB', 'RB': 'RB', 'WR': 'WR', 'TE': 'TE', 'D': 'DST', 'DST': 'DST'}


# ----------------------------------------------------------------- slate loading
_TEAMS_CACHE = {}
def _teams_in(path):
    if path not in _TEAMS_CACHE:
        with open(path) as f:
            _TEAMS_CACHE[path] = len({r['team'] for r in csv.DictReader(f) if r.get('team')})
    return _TEAMS_CACHE[path]


def load_slate(date_s, tier='20'):
    """tier: '20' flagship Milly | 'high' $555/$4,444 | 'single' | 'dome' |
    'small23' 2-3-game slates | 'small46' 4-6-game slates | 'any' biggest main."""
    if tier in ('small23', 'small46'):
        lo, hi = (4, 6) if tier == 'small23' else (7, 12)
        cands = [p for p in glob.glob(os.path.join(FL_DIR, f"{date_s}_*.csv"))
                 if '_showdown_' not in p and lo <= _teams_in(p) <= hi]
        if not cands:
            return None, None, None
        def _hdr2(p):
            return csv.DictReader(open(p)).__next__()
        path = max(cands, key=lambda p: int(_hdr2(p)['contestSize']))
        # fall through to the common reader below via a small shim
        paths = [path]
    else:
        paths = sorted(glob.glob(os.path.join(FL_DIR, f"{date_s}_main_*.csv")))
    if not paths:
        sys.exit(f"no FL main-slate file for {date_s} under {FL_DIR}")
    def _hdr(p):
        return csv.DictReader(open(p)).__next__()
    def _milly(p, lo, hi):
        h = _hdr(p)
        return 'millionaire' in h['contestName'].lower() and lo <= float(h['entryCost']) <= hi
    def _single(p, lo=0):
        h = _hdr(p)
        return 'single entry' in h['contestName'].lower() and float(h['entryCost']) >= lo
    if tier in ('small23', 'small46'):
        pick = paths                                     # already selected above
    elif tier == '20':
        pick = [p for p in paths if _milly(p, 19, 26)]
    elif tier == 'high':
        pick = [p for p in paths if _milly(p, 300, 99999)]
    elif tier == '555':                               # mid-stakes Milly (~2-5K fields)
        pick = [p for p in paths if _milly(p, 300, 1000)]
    elif tier == 'mega':                              # $2,222-$4,494 MEGA (~300-800 fields)
        pick = [p for p in paths if _milly(p, 2000, 99999)]
    elif tier == 'single':                            # the big single-entry (your "main lineup")
        pick = [p for p in paths if _single(p) and float(_hdr(p)['entryCost']) < 1000]
    elif tier == 'dome':                              # Thunderdome: $5,300 single entry vs ~30 sharks
        dome = [p for p in paths if 'thunderdome' in _hdr(p)['contestName'].lower()]
        pick = dome or [p for p in paths if _single(p, lo=1000)]   # fallback: biggest $1k+ single
    else:
        pick = []
    path = (max(pick, key=lambda p: int(_hdr(p)['contestSize'])) if pick
            else max(paths, key=lambda p: int(_hdr(p)['contestSize'])))
    if tier in ('20', 'high', 'single', 'dome', '555', 'mega') and not pick:
        return None, None, None                      # this date has no such contest
    meta = None
    pool, gid = [], {}
    for r in csv.DictReader(open(path)):
        if meta is None:
            meta = {'name': r['contestName'], 'entry': float(r['entryCost']),
                    'size': int(r['contestSize'])}
        pos = POS.get(r['pos'])
        if not pos:
            continue
        try:
            sal = int(float(r['salary'])); proj = float(r['proj'])
            act = float(r['actual']); own = float(r['ownership'] or 0)
        except (KeyError, ValueError):
            continue
        if sal <= 0 or proj <= 0:
            continue
        g = gid.setdefault(tuple(sorted((r['team'], r['opp']))), str(len(gid)))
        p = Player(name=r['name'], pos=pos, team=r['team'], opp=r['opp'], game_id=g,
                   salary=sal, proj=proj, actual=act)
        p.own = max(own, 0.05) / 100.0          # floor: someone plays everyone
        pool.append(p)
    _assign_wr_ranks(pool)
    return pool, meta, path


# ----------------------------------------------------------------- correlated player worlds
def simulate_worlds(pool, W, seed=7):
    """(n_players x W) matrix of simulated DK points. Correlations from pair_rho (PSD-repaired),
    lognormal marginals for skill players (right skew), normal for DST."""
    n = len(pool)
    C = np.eye(n)
    for i in range(n):
        for j in range(i + 1, n):
            r = pair_rho(pool[i], pool[j])
            if r:
                C[i, j] = C[j, i] = r
    w, V = np.linalg.eigh(C)                    # PSD repair (pairwise matrix isn't exactly PSD)
    C = V @ np.diag(np.clip(w, 1e-6, None)) @ V.T
    d = np.sqrt(np.diag(C)); C = C / np.outer(d, d)
    L = np.linalg.cholesky(C + 1e-9 * np.eye(n))
    rng = np.random.default_rng(seed)
    Z = L @ rng.standard_normal((n, W))
    pts = np.empty((n, W), dtype=np.float32)
    for i, p in enumerate(pool):
        m = p.proj; cv = CV.get(p.pos, 0.8)
        if p.pos == 'DST':
            pts[i] = np.maximum(m + cv * m * Z[i], -4.0)
        else:                                    # lognormal with mean m, sd cv*m
            s2 = math.log(1 + cv * cv)
            pts[i] = m * np.exp(math.sqrt(s2) * Z[i] - s2 / 2)
    return pts


# ----------------------------------------------------------------- field simulation
SLOTS = ['QB', 'RB', 'RB', 'WR', 'WR', 'WR', 'TE', 'FLEX', 'DST']

def sample_field(pool, F, p_stack=0.55, seed=11, sharp_frac=0.15):
    """F field lineups -> (F x 9) index array.

    (1-sharp_frac) are CASUAL: ownership-weighted, stack-aware ~55%, salary-feasible.
    sharp_frac are SHARP: greedy randomized value builds (proj-per-$ softmax, stack forced 80%,
    $48.5k+ spent) — the regs/optimizer users every real field contains. Without them the field
    is too soft and every good lineup shows inflated ROI."""
    rng = np.random.default_rng(seed)
    idx_by = defaultdict(list)
    for i, p in enumerate(pool):
        idx_by[p.pos].append(i)
    flex_pool = idx_by['RB'] + idx_by['WR'] + idx_by['TE']
    w = {k: np.array([pool[i].own for i in v]) for k, v in idx_by.items()}
    w = {k: v / v.sum() for k, v in w.items()}
    wf = np.array([pool[i].own for i in flex_pool]); wf = wf / wf.sum()
    team_pc = defaultdict(list)
    for i, p in enumerate(pool):
        if p.pos in ('WR', 'TE'):
            team_pc[p.team].append(i)

    sal = np.array([p.salary for p in pool])

    # sharp submodel: softmax over projection-value z-scores within each position
    val = np.array([p.proj / (p.salary / 1000.0) for p in pool])
    vz = (val - val.mean()) / (val.std() + 1e-9)
    wsharp = {k: np.exp(2.2 * vz[np.array(v)]) for k, v in idx_by.items()}
    wsharp = {k: v / v.sum() for k, v in wsharp.items()}
    wfs = np.exp(2.2 * vz[np.array(flex_pool)]); wfs = wfs / wfs.sum()

    n_sharp = int(F * sharp_frac)
    out = np.empty((F, 9), dtype=np.int32)
    for f in range(F):
        sharp = f < n_sharp
        pw, fw, ps = (wsharp, wfs, 0.80) if sharp else (w, wf, p_stack)
        min_sal = 48500 if sharp else 46000
        for attempt in range(6):
            picks = []

            def pick_slot(cand, wvec):
                """Weighted pick avoiding dupes; deterministic best-available fallback so a
                lineup can never come up short when weights are ultra-concentrated."""
                for _ in range(10):
                    c = rng.choice(cand, p=wvec)
                    if c not in picks:
                        return c
                for oi in np.argsort(-wvec):
                    if cand[oi] not in picks:
                        return int(cand[oi])
                return None

            qb = rng.choice(idx_by['QB'], p=pw['QB']); picks.append(qb)
            stack_pick = None
            if rng.random() < ps and team_pc[pool[qb].team]:
                tc = team_pc[pool[qb].team]
                tw = np.array([pool[i].own for i in tc]); tw = tw / tw.sum()
                stack_pick = rng.choice(tc, p=tw)
            for slot in ['RB', 'RB', 'WR', 'WR', 'WR', 'TE']:
                cand = idx_by[slot]
                if stack_pick is not None and pool[stack_pick].pos == slot and stack_pick not in picks:
                    picks.append(stack_pick); stack_pick = None; continue
                c = pick_slot(cand, pw[slot])
                if c is not None:
                    picks.append(c)
            c = pick_slot(flex_pool, fw)
            if c is not None:
                picks.append(c)
            picks.append(rng.choice(idx_by['DST'], p=pw['DST']))
            if len(set(picks)) == 9 and min_sal <= sal[picks].sum() <= SALARY_CAP:
                break
        if len(picks) < 9:                       # pool too small even for fallback — pad by value
            for oi in np.argsort(-vz):
                if oi not in picks:
                    picks.append(int(oi))
                if len(picks) == 9:
                    break
        out[f] = picks[:9]
    return out


# ----------------------------------------------------------------- payout curve
def payout_curve(meta):
    """Parametric DK GPP payout: first prize parsed from the contest name; power-law places;
    ~22% of the field cashes at >=1.5x entry; total = prize pool implied by the name."""
    name, entry, size = meta['name'], meta['entry'], meta['size']
    mpool = re.search(r'\$([\d.]+)([MK])', name)
    pool_total = (float(mpool.group(1)) * (1e6 if mpool.group(2) == 'M' else 1e3)) if mpool \
        else entry * size * 0.85
    mfirst = re.search(r'\[\$([\d.]+)([MK]) to 1st', name)
    first = (float(mfirst.group(1)) * (1e6 if mfirst.group(2) == 'M' else 1e3)) if mfirst else pool_total * 0.2
    places = max(int(0.22 * size), 10)
    min_cash = 1.5 * entry
    lo, hi = 0.3, 3.0                            # solve power alpha: sum(first*k^-a) = pool
    for _ in range(60):
        a = (lo + hi) / 2
        tot = first * np.arange(1, places + 1, dtype=np.float64) ** (-a)
        tot = np.maximum(tot, min_cash).sum()
        if tot > pool_total:
            lo = a
        else:
            hi = a
    pay = np.maximum(first * np.arange(1, places + 1, dtype=np.float64) ** (-(lo + hi) / 2), min_cash)
    def payout_at(place):                        # continuous place (1-based float)
        k = int(min(max(place, 1), places + 1))
        return float(pay[k - 1]) if k <= places else 0.0
    return payout_at, pool_total, first, places


# ----------------------------------------------------------------- candidate generation
def gen_candidates(pool, per_mode=25, lams=(0.0, 3.0, 6.0, 10.0, 15.0)):
    """ILP candidates at several ownership-fade levels + the portfolio archetypes."""
    cands, tags = [], []
    orig = [(p.proj,) for p in pool]
    for lam in lams:                             # points sacrificed per 100% total ownership
        for p in pool:
            p.proj = max(p.proj - lam * p.own * 100 / 100 * 1.0, 0.01) if lam else p.proj
        # NOTE: own is a fraction; lam*own*100/100 == lam*own -> lam points per 100% own
        gen = _generate(pool, per_mode, 6, SALARY_CAP, 48500, 'allow', True,
                        {'bringback': 1.0, 'plus2': 0.7, 'wr12': 0.4})
        for p, (o,) in zip(pool, orig):
            p.proj = o
        for L, chosen in gen:
            cands.append(chosen); tags.append(f"fade{int(lam)}")
    try:
        port = optimize_portfolio(pool, n_lineups=per_mode, max_overlap=7, max_exposure=0.5)
        name_ix = {id(p): i for i, p in enumerate(pool)}
        for L in port:
            cands.append([name_ix[id(p)] for p in L.players]); tags.append(f"arch:{L.archetype}")
    except Exception:
        pass
    seen, out, outt = set(), [], []
    for c, t in zip(cands, tags):
        k = frozenset(c)
        if k not in seen and len(c) == 9:
            seen.add(k); out.append(c); outt.append(t)
    return np.array(out, dtype=np.int32), outt


# ----------------------------------------------------------------- the simulation
def run(date_s, W, F, per_mode, seed=7):
    pool, meta, path = load_slate(date_s)
    print(f"slate {date_s}: {len(pool)} players | contest '{meta['name']}' "
          f"(${meta['entry']:.0f}, {meta['size']:,} entries)")
    payout_at, pool_total, first, places = payout_curve(meta)
    print(f"payout model: ${pool_total/1e6:.2f}M pool, ${first/1e6:.2f}M to 1st, "
          f"{places:,} places cash ({places/meta['size']:.0%})")

    pts = simulate_worlds(pool, W, seed)
    print(f"simulated {W} correlated worlds")
    field = sample_field(pool, F, seed=seed + 1)
    fowns = np.array([sum(pool[i].own for i in row) for row in field])
    print(f"sampled field of {F} lineups (mean total ownership {fowns.mean()*100:.0f}%)")

    cands, tags = gen_candidates(pool, per_mode)
    print(f"generated {len(cands)} unique candidates "
          f"({', '.join(sorted(set(tags), key=tags.index))})")

    fs = pts[field.reshape(-1)].reshape(F, 9, W).sum(axis=1)         # field scores F x W
    cs = pts[cands.reshape(-1)].reshape(len(cands), 9, W).sum(axis=1)  # candidate scores C x W
    fs_sorted = np.sort(fs, axis=0)

    # dupes: exact matches in sampled field, scaled to real size (+ chalk-product floor)
    fkeys = defaultdict(int)
    for row in field:
        fkeys[frozenset(row.tolist())] += 1
    scale = meta['size'] / F
    dupes = np.array([fkeys.get(frozenset(c.tolist()), 0) * scale for c in cands])

    size = meta['size']
    C = len(cands)
    pay_avg = np.zeros(C); cash = np.zeros(C); top01 = np.zeros(C); top1 = np.zeros(C)
    urng = np.random.default_rng(99)
    for wix in range(W):
        col = fs_sorted[:, wix]
        r = F - np.searchsorted(col, cs[:, wix], side='right')       # 0 = beat everyone
        # beating r of F sampled lineups only bounds your percentile to a band of width
        # 1/F; draw the unresolved placement uniformly inside it (else P(1st of size) is
        # overstated by ~scale x and the $1M top prize swamps ROI)
        place = np.maximum((r + urng.uniform(size=C)) * scale, 1.0)
        for ci in range(C):
            pl = place[ci]
            pay_avg[ci] += payout_at(pl) / (1 + dupes[ci])
            if pl <= places: cash[ci] += 1
            if pl <= size * 0.001: top01[ci] += 1
            if pl <= size * 0.01: top1[ci] += 1
    pay_avg /= W; cash /= W; top01 /= W; top1 /= W
    roi = (pay_avg - meta['entry']) / meta['entry']

    owns = np.array([sum(pool[i].own for i in c) for c in cands])
    projs = np.array([sum(pool[i].proj for i in c) for c in cands])
    acts = np.array([sum(pool[i].actual for i in c) for c in cands])

    print("\n" + "=" * 100)
    print(f"SIM RESULTS — {date_s} | {W} worlds x {F}-lineup field scaled to {size:,}")
    print("=" * 100)
    print(f"{'rank':>4} {'tag':<14} {'ROI':>8} {'cash%':>7} {'top1%':>7} {'top.1%':>7} "
          f"{'own':>6} {'proj':>6} {'ACTUAL':>7}  lineup core (QB + stack)")
    order = np.argsort(-roi)
    for k, ci in enumerate(order[:15], 1):
        c = cands[ci]
        qb = next(pool[i] for i in c if pool[i].pos == 'QB')
        st = [pool[i].name for i in c if pool[i].team == qb.team and pool[i].pos in ('WR', 'TE')]
        print(f"{k:>4} {tags[ci]:<14} {roi[ci]*100:>7.0f}% {cash[ci]*100:>6.1f}% {top1[ci]*100:>6.2f}% "
              f"{top01[ci]*100:>6.2f}% {owns[ci]*100:>5.0f}% {projs[ci]:>6.1f} {acts[ci]:>7.1f}  "
              f"{qb.name} + {', '.join(st) or '—'}")

    print("\nBY CONSTRUCTION MODE (mean over candidates):")
    print(f"{'tag':<14} {'n':>3} {'ROI':>8} {'cash%':>7} {'top.1%':>7} {'own':>6} {'proj':>6} {'best ACTUAL':>11}")
    for t in sorted(set(tags), key=tags.index):
        m = np.array([i for i, x in enumerate(tags) if x == t])
        print(f"{t:<14} {len(m):>3} {roi[m].mean()*100:>7.0f}% {cash[m].mean()*100:>6.1f}% "
              f"{top01[m].mean()*100:>6.2f}% {owns[m].mean()*100:>5.0f}% {projs[m].mean():>6.1f} "
              f"{acts[m].max():>11.1f}")
    ev = (pool_total - meta['entry'] * size) / (meta['entry'] * size)
    print(f"\n(field-average ROI = rake = {ev*100:.0f}%; anything above that beats the field. "
          f"ACTUAL = what the lineup really scored that Sunday.)")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--slate', default='2024-12-08')
    ap.add_argument('--worlds', type=int, default=4000)
    ap.add_argument('--field', type=int, default=4000)
    ap.add_argument('--n', type=int, default=25, help='candidates per construction mode')
    args = ap.parse_args()
    run(args.slate, args.worlds, args.field, args.n)


if __name__ == '__main__':
    main()
