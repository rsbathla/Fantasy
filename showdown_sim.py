#!/usr/bin/env python3
"""showdown_sim.py — DK Showdown (Captain-mode) contest simulator.

Answers R9's question with sim evidence: which captain strategy makes money —
  chalk        stud CPT + chalk FLEX          (baseline)
  fade-flex    stud CPT + contrarian FLEX     (what actual winners look like)
  weird-cpt    low-owned CPT + chalk FLEX     (Ramneik's historical pattern)
  weird-both   low-owned CPT + contrarian FLEX

CPT field ownership is NOT in FL data (zeroed). Bridge: cpt_own ~ flex_own^alpha, alpha fit from
Ramneik's own contest records (his exposures store true CPT-slot ownership via exp - leverage).

Run:  python3 showdown_sim.py --season 2024        (season table, checkpointed)
      python3 showdown_sim.py --date 2024-09-19    (one slate)
"""
import argparse, csv, glob, json, math, os, sys
from collections import defaultdict
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from contest_sim import CV, payout_curve
from dfs_optimizer import Player, pair_rho

PDIR = os.path.join(HERE, 'data', 'fantasylabs', 'players')
UDIR = os.path.join(HERE, 'data', 'fantasylabs', 'users')
CVX = dict(CV); CVX['K'] = 0.70
SAL_CAP = 50000

# ---------------------------------------------------------------- alpha calibration
def calibrate_alpha():
    pairs = []
    for fp in glob.glob(os.path.join(UDIR, '*_rsbathla.json')):
        try:
            j = json.load(open(fp))
        except Exception:
            continue
        rec = j.get('hits', [{}])[0].get('record', {})
        exps = rec.get('exposures') or {}
        by_base = defaultdict(dict)
        for e in exps.values():
            pid = str(e.get('playerId', ''))
            if ':' not in pid:
                continue
            base, slot = pid.rsplit(':', 1)
            fown = (e.get('playerExposure') or 0) - (e.get('playerLeverage') or 0)
            by_base[base][slot] = fown
        for base, d in by_base.items():
            f0, f1 = d.get('0'), d.get('1')
            if f0 and f1 and f0 > 2 and f1 > 0.2:
                pairs.append((f0, f1))
    if len(pairs) < 30:
        return 1.6, len(pairs)
    x = np.log([p[0] / 100 for p in pairs]); y = np.log([p[1] / 100 for p in pairs])
    alpha = float(np.polyfit(x, y, 1)[0])
    return max(1.0, min(alpha, 3.0)), len(pairs)

# ---------------------------------------------------------------- slate loading
def load_showdown(date_s):
    best, bp = None, None
    for f in glob.glob(os.path.join(PDIR, f'{date_s}_showdown_*.csv')):
        h = csv.DictReader(open(f)).__next__()
        pool_sz = int(h['contestSize']) * max(float(h['entryCost']), 0.25)   # ~prize pool
        if best is None or pool_sz > best:
            best, bp = pool_sz, f
    if not bp:
        return None, None
    rows = list(csv.DictReader(open(bp)))
    h = rows[0]
    meta = {'name': h['contestName'], 'entry': float(h['entryCost']), 'size': int(h['contestSize'])}
    byname = defaultdict(list)
    for r in rows:
        try:
            byname[r['name']].append(r)
        except Exception:
            pass
    pool, gid = [], 'G'
    for nm, rs in byname.items():
        rs.sort(key=lambda r: float(r['salary'] or 0))
        fx = rs[0]; cp = rs[-1] if len(rs) > 1 else None
        try:
            sal = int(float(fx['salary'])); proj = float(fx['proj'])
            act = float(fx['actual']); own = float(fx['ownership'] or 0)
        except ValueError:
            continue
        if sal <= 0 or proj <= 0:
            continue
        pos = {'D': 'DST'}.get(fx['pos'], fx['pos'])
        if pos not in ('QB', 'RB', 'WR', 'TE', 'DST', 'K'):
            continue
        p = Player(name=nm, pos=pos, team=fx['team'], opp=fx['opp'], game_id=gid,
                   salary=sal, proj=proj, actual=act)
        p.own = max(own, 0.05) / 100
        p.cpt_sal = int(float(cp['salary'])) if cp else int(sal * 1.5)
        pool.append(p)
    return pool, meta

# ---------------------------------------------------------------- correlated worlds
def rho2(a, b):
    if 'K' in (a.pos, b.pos):
        k, o = (a, b) if a.pos == 'K' else (b, a)
        if o.pos == 'K':
            return 0.0
        return 0.15 if k.team == o.team and o.pos == 'QB' else (0.08 if k.team == o.team else -0.05)
    return pair_rho(a, b)

def worlds(pool, W, seed=7):
    n = len(pool)
    C = np.eye(n)
    for i in range(n):
        for j in range(i + 1, n):
            r = rho2(pool[i], pool[j])
            if r:
                C[i, j] = C[j, i] = r
    w, V = np.linalg.eigh(C)
    C = V @ np.diag(np.clip(w, 1e-6, None)) @ V.T
    d = np.sqrt(np.diag(C)); C = C / np.outer(d, d)
    L = np.linalg.cholesky(C + 1e-9 * np.eye(n))
    rng = np.random.default_rng(seed)
    Z = L @ rng.standard_normal((n, W))
    pts = np.empty((n, W), dtype=np.float32)
    for i, p in enumerate(pool):
        m, cv = p.proj, CVX.get(p.pos, 0.8)
        if p.pos in ('DST',):
            pts[i] = np.maximum(m + cv * m * Z[i], -4.0)
        else:
            s2 = math.log(1 + cv * cv)
            pts[i] = m * np.exp(math.sqrt(s2) * Z[i] - s2 / 2)
    return pts

# ---------------------------------------------------------------- field + candidates
def cpt_probs(pool, alpha):
    w = np.array([p.own ** alpha for p in pool])
    return w / w.sum()

def sample_field(pool, F, alpha, seed=11, sharp=0.25):
    rng = np.random.default_rng(seed)
    n = len(pool)
    cp = cpt_probs(pool, alpha)
    fw = np.array([p.own for p in pool]); fw = fw / fw.sum()
    val = np.array([p.proj / p.salary for p in pool])
    vz = (val - val.mean()) / (val.std() + 1e-9)
    sw = np.exp(1.8 * vz); sw = sw / sw.sum()
    sal = np.array([p.salary for p in pool]); csal = np.array([p.cpt_sal for p in pool])
    out = np.empty((F, 6), dtype=np.int32)
    for f in range(F):
        sharp_entry = f < int(F * sharp)
        pw = sw if sharp_entry else fw
        for _ in range(8):
            c = rng.choice(n, p=cp)
            picks = [c]
            while len(picks) < 6:
                x = rng.choice(n, p=pw)
                if x not in picks:
                    picks.append(x)
            tot = csal[picks[0]] + sal[picks[1:]].sum()
            if 46000 <= tot <= SAL_CAP:
                break
        out[f] = picks
    return out

def gen_candidates(pool, per_mode=20, seed=5):
    """Four captain strategies x per_mode lineups each (greedy fills with jitter)."""
    rng = np.random.default_rng(seed)
    n = len(pool)
    proj = np.array([p.proj for p in pool]); own = np.array([p.own for p in pool])
    sal = np.array([p.salary for p in pool]); csal = np.array([p.cpt_sal for p in pool])
    boom = np.array([p.pos in ('WR', 'RB') for p in pool])
    stud_cpts = np.argsort(-(proj * (1 + 0.3 * boom)))[:6]           # boom-position studs
    weird_cpts = [i for i in np.argsort(-proj) if own[i] < 0.10][:10]
    # (cpt pool, fade-lambda for FLEX 1-3 "core", fade-lambda for FLEX 4-5 "tail")
    # weird-tail = R9's winner shape: captain the stud, chalk core, weird last two FLEX
    modes = {'chalk': (stud_cpts, 0.0, 0.0), 'fade-flex': (stud_cpts, 8.0, 8.0),
             'weird-cpt': (weird_cpts, 0.0, 0.0), 'weird-both': (weird_cpts, 8.0, 8.0),
             'weird-tail': (stud_cpts, 0.0, 8.0),
             'mild-tail': (stud_cpts, 0.0, 3.5)}    # R9 winner shape at gentler depth
    cands, tags = [], []
    for tag, (cpts, lam_core, lam_tail) in modes.items():
        if len(cpts) == 0:
            continue
        sc_core = proj - lam_core * own * 10
        sc_tail = proj - lam_tail * own * 10
        for k in range(per_mode):
            c = int(cpts[k % len(cpts)])
            jitter = rng.normal(0, 1.5, n)
            order_c = np.argsort(-(sc_core + jitter))
            order_t = np.argsort(-(sc_tail + jitter))
            picks, tot = [c], csal[c]
            for phase_order, upto in ((order_c, 4), (order_t, 6)):
                for i in phase_order:
                    if len(picks) >= upto:
                        break
                    if i in picks or tot + sal[i] > SAL_CAP:
                        continue
                    remaining = 5 - (len(picks) - 1)
                    if tot + sal[i] + (remaining - 1) * 2200 > SAL_CAP:
                        continue
                    picks.append(int(i)); tot += sal[i]
            # salary upgrade pass: contrarian fills come out cheap — swap up until competitive
            guard = 0
            while len(picks) == 6 and tot < 43000 and guard < 20:
                guard += 1
                ci = min(picks[1:], key=lambda i: sal[i])
                ups = [i for i in order_t if i not in picks
                       and 0 < sal[i] - sal[ci] <= SAL_CAP - tot]
                if not ups:
                    break
                picks[picks.index(ci)] = int(ups[0]); tot += sal[ups[0]] - sal[ci]
            if len(picks) == 6 and tot >= 40000:
                cands.append(picks); tags.append(tag)
    # dedupe
    seen, oc, ot = set(), [], []
    for c, t in zip(cands, tags):
        k = (c[0], frozenset(c[1:]))
        if k not in seen:
            seen.add(k); oc.append(c); ot.append(t)
    return np.array(oc, dtype=np.int32), ot

# ---------------------------------------------------------------- run
def run_slate(date_s, W, F, alpha, per_mode=20):
    pool, meta = load_showdown(date_s)
    if not pool or len(pool) < 20:
        return None
    payout_at, pool_total, first, places = payout_curve(meta)
    pts = worlds(pool, W)
    field = sample_field(pool, F, alpha)
    cands, tags = gen_candidates(pool, per_mode)
    if not len(cands):
        return None
    def score(mat):
        base = pts[mat[:, 1:].reshape(-1)].reshape(len(mat), 5, W).sum(axis=1)
        return base + 1.5 * pts[mat[:, 0]]
    fs = np.sort(score(field), axis=0)
    cs = score(cands)
    scale = meta['size'] / F
    C = len(cands)
    # dupe tax (was MISSING pre-v2, inflating chalk): CPT-aware lineup keys, field-sample
    # collision rate scaled to contest size — every payout is split 1/(1+dupes)
    fkeys = {}
    for row in field:
        k = (int(row[0]), frozenset(row[1:].tolist()))
        fkeys[k] = fkeys.get(k, 0) + 1
    dupes = np.array([fkeys.get((int(c[0]), frozenset(c[1:].tolist())), 0) * scale
                      for c in cands])
    pay = np.zeros(C); cash = np.zeros(C); top1 = np.zeros(C)
    urng = np.random.default_rng(99)
    for wix in range(W):
        r = F - np.searchsorted(fs[:, wix], cs[:, wix], side='right')
        place = np.maximum((r + urng.uniform(size=C)) * scale, 1.0)
        for ci in range(C):
            pay[ci] += payout_at(place[ci]) / (1 + dupes[ci])
            if place[ci] <= places: cash[ci] += 1
            if place[ci] <= meta['size'] * 0.01: top1[ci] += 1
    pay /= W; cash /= W; top1 /= W
    roi = (pay - meta['entry']) / meta['entry']
    out = {}
    for t in set(tags):
        m = [i for i, x in enumerate(tags) if x == t]
        out[t] = dict(roi=float(roi[m].mean()), cash=float(cash[m].mean()),
                      top1=float(top1[m].mean()),
                      cpt_own=float(np.mean([pool[cands[i][0]].own for i in m])),
                      cowin=float(dupes[m].mean()))   # expected co-holders of the same lineup
    return out, meta

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--season', type=int)
    ap.add_argument('--date')
    ap.add_argument('--worlds', type=int, default=3000)
    ap.add_argument('--field', type=int, default=3000)
    a = ap.parse_args()
    alpha, npairs = calibrate_alpha()
    print(f"CPT-ownership bridge: cpt_own ~ flex_own^{alpha:.2f} "
          f"(fit on {npairs} of Ramneik's CPT/FLEX pairs)", file=sys.stderr)
    if a.date:
        res = run_slate(a.date, a.worlds, a.field, alpha)
        if not res:
            sys.exit("no showdown that date")
        out, meta = res
        print(f"\n{a.date}  '{meta['name'][:44]}'")
        for t, v in sorted(out.items(), key=lambda kv: -kv[1]['roi']):
            print(f"  {t:>10}: ROI {v['roi']*100:>6.0f}%  cash {v['cash']*100:4.1f}%  "
                  f"top1% {v['top1']*100:4.2f}%  cptOwn {v['cpt_own']*100:4.1f}%")
        return
    def sea(d):
        y, m = int(d[:4]), int(d[5:7]); return y if m >= 8 else y - 1
    dates = sorted({os.path.basename(p).split('_')[0]
                    for p in glob.glob(os.path.join(PDIR, '*_showdown_*.csv'))
                    if sea(os.path.basename(p).split('_')[0]) == a.season})
    ck_path = os.path.join(HERE, f'showdown_ckpt3_{a.season}.json')   # v3: +mild-tail, +cowin
    agg = defaultdict(lambda: defaultdict(list)); done = set()
    if os.path.exists(ck_path):
        ck = json.load(open(ck_path)); done = set(ck['dates'])
        for t, vals in ck['agg'].items():
            for k, v in vals.items():
                agg[t][k] = v
        print(f"  resuming: {len(done)} slates done", file=sys.stderr)
    for d in dates:
        if d in done:
            continue
        res = run_slate(d, a.worlds, a.field, alpha)
        if not res:
            continue
        out, meta = res
        for t, v in out.items():
            for k, x in v.items():
                agg[t][k].append(x)
        done.add(d)
        json.dump({'dates': sorted(done), 'agg': {t: dict(v) for t, v in agg.items()}},
                  open(ck_path, 'w'))
        print(f"  {d} '{meta['name'][:34]}' chalk {out.get('chalk',{}).get('roi',0)*100:.0f}%",
              file=sys.stderr, flush=True)
    print(f"\nSHOWDOWN SIM — {len(done)} slates [{a.season}] | {a.worlds} worlds x {a.field} field")
    print(f"{'mode':>10} {'ROI':>8} {'cash%':>7} {'top1%':>7} {'cptOwn':>7}")
    import statistics as st
    for t in ('chalk', 'fade-flex', 'weird-cpt', 'weird-both'):
        if t in agg and agg[t]['roi']:
            print(f"{t:>10} {st.mean(agg[t]['roi'])*100:>7.0f}% "
                  f"{st.mean(agg[t]['cash'])*100:>6.1f}% {st.mean(agg[t]['top1'])*100:>6.2f}% "
                  f"{st.mean(agg[t]['cpt_own'])*100:>6.1f}%")

if __name__ == '__main__':
    main()
