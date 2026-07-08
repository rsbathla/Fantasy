#!/usr/bin/env python3
"""week_replay.py — walk-forward replay of one 2024-season week (generalized pilot).

Usage: python3 week_replay.py --date 2024-11-24
Writes weekcards/{date}.json and prints the week card.
Pre-lock-legal brief (pbp usage deltas through week N-1, proj role-steps, Vegas),
his actual contests/exposures, read grades, true-field-size counterfactuals on the
mega/$555 tiers he entered that day.
"""
import argparse, csv, glob, gzip, json, os, sys
from collections import defaultdict
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from contest_sim import load_slate, simulate_worlds, sample_field, payout_curve, FL_DIR
from portfolio_150 import world_champion

ap = argparse.ArgumentParser()
ap.add_argument('--date', required=True)
ap.add_argument('--worlds', type=int, default=1200)
A = ap.parse_args()
DATE = A.date
SEASON = str(int(DATE[:4]) if int(DATE[5:7]) >= 8 else int(DATE[:4]) - 1)
DATA = os.path.join(HERE, 'data', 'fantasylabs')
CARDS = os.path.join(HERE, 'weekcards')
os.makedirs(CARDS, exist_ok=True)

# ---- week number from nflverse games ----
WEEK = None
for r in csv.DictReader(open(os.path.join(HERE, 'data/nflverse/games_2021_2025.csv'))):
    if r.get('gameday') == DATE and r.get('season') == SEASON:
        WEEK = int(r['week']); break
if WEEK is None:
    sys.exit(f"no {SEASON}-season games on {DATE}")

# ---- prior main date ----
mains = sorted({os.path.basename(p).split('_')[0]
                for p in glob.glob(os.path.join(FL_DIR, '*_main_*.csv'))})
prevs = [d for d in mains if d < DATE]
PREV = prevs[-1] if prevs else None

def fl_pool(date_s):
    best, size = None, -1
    for p in glob.glob(os.path.join(FL_DIR, f'{date_s}_main_*.csv')):
        r0 = next(csv.DictReader(open(p)))
        if int(r0['contestSize']) > size:
            size, best = int(r0['contestSize']), p
    out = {}
    if not best:
        return out
    for r in csv.DictReader(open(best)):
        try:
            out[r['name']] = (float(r['proj']), float(r['actual']),
                              float(r['ownership'] or 0), r['pos'], r['team'])
        except (ValueError, KeyError):
            continue
    return out

pool_now, pool_prev = fl_pool(DATE), (fl_pool(PREV) if PREV else {})
card = {'date': DATE, 'week': WEEK}
print(f"{'='*88}\nWEEK REPLAY — {DATE} (2024 wk {WEEK})\n{'='*88}")

# ---------------- A) BRIEF ----------------
pbp = pd.read_parquet(os.path.join(HERE, f'data/nflverse/pbp_{SEASON}.parquet'),
                      columns=['week', 'posteam', 'pass', 'rush',
                               'receiver_player_name', 'rusher_player_name'])
pbp = pbp[pbp.week < WEEK]
def usage(df, col):
    g = df.groupby(['week', 'posteam', col]).size().rename('n').reset_index()
    tm = df.groupby(['week', 'posteam']).size().rename('tot').reset_index()
    g = g.merge(tm, on=['week', 'posteam']); g['share'] = g.n / g.tot
    return g
def deltas(g, col):
    lo = max(1, WEEK - 3)
    last3 = g[g.week >= lo].groupby(['posteam', col]).share.mean()
    base = g[(g.week >= 2) & (g.week < lo)].groupby(['posteam', col]).share.mean()
    return (last3 - base.reindex(last3.index).fillna(0.0)).sort_values(ascending=False)
tg_d = deltas(usage(pbp[(pbp['pass'] == 1) & pbp.receiver_player_name.notna()], 'receiver_player_name'),
              'receiver_player_name')
ru_d = deltas(usage(pbp[(pbp['rush'] == 1) & pbp.rusher_player_name.notna()], 'rusher_player_name'),
              'rusher_player_name')
fl_key = {}
for nm, v in pool_now.items():
    parts = nm.split()
    if len(parts) >= 2:
        fl_key[(v[4], parts[0][0].upper(),
                ''.join(parts[1:]).replace('.', '').replace("'", '').lower())] = nm
def to_fl(idx):
    out = []
    for (team, nmr), dv in idx.items():
        if not isinstance(nmr, str) or '.' not in nmr:
            continue
        fi, last = nmr.split('.', 1)
        k = (team, fi[0].upper(), last.replace('.', '').replace(' ', '').replace("'", '').lower())
        if k in fl_key:
            out.append((fl_key[k], float(dv)))
    return out
usage_risers = [(n, d) for n, d in to_fl(tg_d.head(50)) if d >= 0.05 and pool_now[n][0] >= 6][:10]
carry_risers = [(n, d) for n, d in to_fl(ru_d.head(50)) if d >= 0.10 and pool_now[n][0] >= 6][:6]
role_steps = [(n, pool_now[n][0], pool_prev[n][0]) for n in pool_now
              if n in pool_prev and pool_prev[n][0] > 0
              and pool_now[n][0] >= max(8, 1.30 * pool_prev[n][0])][:10]
envs = []
try:
    with gzip.open('/mnt/user-data/uploads/Fantasy/fc_games_all.csv.gz', 'rt') as fh:
        for r in csv.DictReader(fh):
            if r['period'] == f'{SEASON}-week-{WEEK}' and r['site'] == 'draftkings' and int(r.get('is_home') or 0):
                envs.append((float(r['game_total'] or 0), r['Team'], float(r['spread'] or 0)))
except Exception:
    pass
envs = sorted(envs, reverse=True)[:5]
print("\n[A] BRIEF")
for lbl, rows in (('tgt-share risers', usage_risers), ('carry risers', carry_risers)):
    print(f"  {lbl}:")
    for n, d in rows:
        print(f"    {n:<24} +{d*100:4.1f}pp  proj {pool_now[n][0]:5.1f}  own {pool_now[n][2]:4.1f}%")
print("  role-steps (proj +30% WoW):")
for n, p1, p0 in sorted(role_steps, key=lambda x: -(x[1] / max(x[2], .1))):
    print(f"    {n:<24} {p0:5.1f} -> {p1:5.1f}  own {pool_now[n][2]:4.1f}%")
if envs:
    print("  top game totals: " + ', '.join(f"{t:.0f} ({tm} {s:+.0f})" for t, tm, s in envs))

# ---------------- B) HIS DAY ----------------
cmeta = {r['contestId']: r for r in csv.DictReader(open(os.path.join(DATA, 'contest_meta.csv')))
         if r['date'] == DATE}
print(f"\n[B] HIS CONTESTS")
tot_in = tot_out = 0.0
his_exp = {}
his_tier = {}
for p in sorted(glob.glob(os.path.join(DATA, 'users', f'{DATE}_*_rsbathla.json'))):
    cid = os.path.basename(p).split('_')[1]
    rec = json.load(open(p))
    hr = next((h['record'] for h in rec.get('hits', [])
               if (h.get('record') or {}).get('totalEntryCost')), None)
    if not hr:
        continue
    cm = cmeta.get(cid, {})
    tot_in += hr['totalEntryCost']; tot_out += hr.get('totalWinning', 0)
    name_l = (cm.get('contestName') or '').lower()
    e = float(cm.get('entryCost') or 0)
    if cm.get('slate') == 'main' and 'millionaire' in name_l:
        tier = 'mega' if e >= 2000 else ('555' if e >= 300 else '20')
        t0 = his_tier.get(tier)
        if not t0 or hr['totalEntryCost'] > t0['in']:
            his_tier[tier] = {'n': hr.get('totalRosters', 0), 'in': hr['totalEntryCost'],
                              'out': hr.get('totalWinning', 0)}
    print(f"  {(cm.get('contestName') or '?')[:42]:<44} x{hr.get('totalRosters',0):>3} "
          f"${hr['totalEntryCost']:>8,.0f} -> ${hr.get('totalWinning',0):>8,.0f}")
    # exclude SINGLE-mode contests (one lineup cloned) from the read merge — their 9
    # players all read "100% exposure" and pollute his_over with phantom locks
    tot_r, uq_r = hr.get('totalRosters', 0), hr.get('uniqueRosters', 0)
    exps_all = [float(v.get('playerExposure') or 0) for v in (hr.get('exposures') or {}).values()
                if v and v.get('playerExposure') is not None]
    n100 = sum(1 for e in exps_all if e >= 99.5)
    single_mode = (uq_r == 1) or (uq_r and tot_r and uq_r / tot_r <= 0.2) or n100 >= 8
    if cm.get('slate') != 'main' or tot_r < 20 or single_mode:
        continue
    pf = os.path.join(FL_DIR, f"{DATE}_main_{cid}.csv")
    if not os.path.exists(pf):
        continue
    pl = {}
    for r in csv.DictReader(open(pf)):
        try:
            pl[r['name']] = float(r['ownership'] or 0)
        except ValueError:
            continue
    pairs = []
    for pid, v in (hr.get('exposures') or {}).items():
        try:
            exp = float(v.get('playerExposure') or 0)
            lev = float(v.get('playerLeverage') or 0)
        except (TypeError, ValueError):
            continue
        if exp >= 15:
            pairs.append((exp, exp - lev))
    used = set()
    for exp, fo in sorted(pairs, reverse=True):
        best, bd = None, 9e9
        for nm, ow in pl.items():
            if nm in used:
                continue
            d = abs(ow - fo)
            if d < bd:
                bd, best = d, nm
        if best and bd <= 0.8:
            used.add(best)
            if exp > his_exp.get(best, (0, 0))[0]:
                his_exp[best] = (exp, fo)
print(f"  WEEK TOTAL: ${tot_in:,.0f} -> ${tot_out:,.0f}  (${tot_out-tot_in:+,.0f})")

# ---------------- C) GRADES ----------------
beats = {n: pool_now[n][1] - pool_now[n][0] for n in pool_now if pool_now[n][0] >= 5}
mu, sd = np.mean(list(beats.values())), np.std(list(beats.values()))
def z(n):
    return (beats[n] - mu) / sd if n in beats else float('nan')
over = sorted(his_exp.items(), key=lambda kv: -kv[1][0])[:12]
print(f"\n[C] READ GRADES")
oh = 0
for n, (e, f) in over:
    zz = z(n)
    oh += (zz >= 1)
    print(f"    HIS  {n:<24} exp {e:5.1f}% field {f:5.1f}%  z {zz:+5.2f}{'  HIT' if zz>=1 else ''}")
bflag = list(dict.fromkeys([n for n, _ in usage_risers + carry_risers] +
                           [n for n, _, _ in role_steps]))[:14]
bh = sum(z(n) >= 1 for n in bflag if n in beats)
for n in bflag:
    print(f"    BRIEF {n:<23} own {pool_now[n][2]:4.1f}%  z {z(n):+5.2f}{'  HIT' if z(n)>=1 else ''}")
print(f"    -> his {oh}/{len(over)} hit >=1z | brief {bh}/{len(bflag)}")

# ---------------- D) COUNTERFACTUALS (true-size tiers only) ----------------
cfs = []
W = A.worlds
his_set = {n for n, _ in over}
brief_set = set(bflag)
for tier in ('mega', '555'):
    if tier not in his_tier:
        continue
    try:
        pool, meta, _ = load_slate(DATE, tier=tier)
    except SystemExit:
        continue
    if pool is None:
        continue
    payout_at, _, first, places = payout_curve(meta)
    size = meta['size']
    proj = np.array([p.proj for p in pool]); own = np.array([p.own for p in pool])
    sal = np.array([p.salary for p in pool]); acts = np.array([p.actual for p in pool])
    names = [p.name for p in pool]
    b_his = np.array([1.12 if n in his_set else 1.0 for n in names])
    b_brf = np.array([1.12 if n in brief_set else 1.0 for n in names])
    lam = 0.0 if tier == 'mega' else 8.0
    MODES = {'dial': proj - lam * own * 10, 'his-reads dial': proj * b_his - lam * own * 10,
             'brief-reads dial': proj * b_brf - lam * own * 10,
             'his-style f10': proj - 10 * own * 10}
    pts = simulate_worlds(pool, W)
    hn = min(his_tier[tier]['n'], 150)
    Kd = 19 if tier == 'mega' else 36
    F = max(size - max(hn, Kd), 50)
    field = sample_field(pool, F, sharp_frac=0.75 if tier == 'mega' else 0.5)
    fs = np.sort(pts[field.reshape(-1)].reshape(F, 9, W).sum(axis=1), axis=0)
    fact = np.sort(acts[field.reshape(-1)].reshape(F, 9).sum(axis=1))
    PAY = np.array([payout_at(i) for i in range(1, size + 2)])
    rng = np.random.default_rng(5)
    print(f"\n[D] {tier.upper()} counterfactual  '{meta['name'][:36]}' ${meta['entry']:,.0f} x {size:,} "
          f"| his real: x{his_tier[tier]['n']} ${his_tier[tier]['out']-his_tier[tier]['in']:+,.0f}")
    for tag, score in MODES.items():
        got, tries = set(), 0
        while len(got) < max(hn, Kd) and tries < 300:
            tries += 1
            lu = world_champion(pool, score + rng.normal(0, 2.0, len(pool)), sal, rng)
            if lu:
                got.add(lu)
        cands = np.array([list(l) for l in got], dtype=np.int32)
        cs = pts[cands.reshape(-1)].reshape(len(cands), 9, W).sum(axis=1)
        r_all = np.empty_like(cs)
        for wix in range(W):
            r_all[:, wix] = F - np.searchsorted(fs[:, wix], cs[:, wix], side='right')
        solo = PAY[np.clip(r_all + 1, 1, size).astype(np.int64) - 1].mean(axis=1)
        order = np.argsort(-solo)
        for K in sorted({Kd, hn}):
            kx = order[:min(K, len(order))]
            fr = np.sort(r_all[kx], axis=0)
            place = fr + np.arange(len(kx))[:, None] + 1.0
            ev = PAY[np.clip(place, 1, size).astype(np.int64) - 1].sum(axis=0).mean()
            cost = meta['entry'] * len(kx)
            cact = acts[cands[kx].reshape(-1)].reshape(len(kx), 9).sum(axis=1)
            ra = np.sort(F - np.searchsorted(fact, cact, side='right'))
            rpay = PAY[np.clip(ra + np.arange(len(kx)) + 1.0, 1, size).astype(np.int64) - 1].sum()
            row = {'tier': tier, 'mode': tag, 'K': int(len(kx)),
                   'sim_roi': float((ev - cost) / cost), 'real_pnl': float(rpay - cost)}
            cfs.append(row)
            print(f"    {tag:<18} K{len(kx):>3}  sim {row['sim_roi']*100:>+5.0f}%   real ${row['real_pnl']:>+11,.0f}")

card.update({'week_in': tot_in, 'week_out': tot_out,
             'his_over': [(n, e, f, float(z(n))) for n, (e, f) in over],
             'his_hits': int(oh), 'brief_flags': [(n, float(pool_now[n][2]), float(z(n))) for n in bflag],
             'brief_hits': int(bh), 'his_tier': his_tier, 'counterfactuals': cfs})
json.dump(card, open(os.path.join(CARDS, f'{DATE}.json'), 'w'))
print(f"\ncard -> weekcards/{DATE}.json")
