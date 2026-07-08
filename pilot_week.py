#!/usr/bin/env python3
"""pilot_week.py — walk-forward replay pilot: 2024-12-29 (NFL 2024 week 17).

A) DATA BRIEF from pre-lock-legal sources only:
   usage deltas from pbp weeks 1-16 (last-3 vs weeks 4-13), role-step screen
   (FL proj WoW), Vegas game environments (fc_games).
B) HIS WEEK from FL records: every contest entered that date, P&L, his top
   overweights vs field (names recovered by ownership-matching).
C) GRADES: did his overweights hit (z of proj-beat)? did the brief's flags hit?
D) COUNTERFACTUAL on the $10M Ultimate ($3,333 x 3,334 — his -$110,815 bet):
   true-field-size portfolios at K=19/55 for chalk / his-style fade / his-reads-
   chalk / brief-reads-chalk, graded BOTH in-sim and on the real Sunday's actuals.
"""
import csv, glob, json, os, sys
from collections import defaultdict
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from contest_sim import load_slate, simulate_worlds, sample_field, payout_curve, FL_DIR
from portfolio_150 import world_champion

DATE, PREV, WEEK = '2024-12-29', '2024-12-22', 17
DATA = os.path.join(HERE, 'data', 'fantasylabs')

def fl_pool(date_s):
    """biggest main contest's player table for a date -> {name: (proj, act, own, pos, team, sal)}"""
    best, size = None, -1
    for p in glob.glob(os.path.join(FL_DIR, f'{date_s}_main_*.csv')):
        r0 = next(csv.DictReader(open(p)))
        if int(r0['contestSize']) > size:
            size, best = int(r0['contestSize']), p
    out = {}
    for r in csv.DictReader(open(best)):
        try:
            out[r['name']] = (float(r['proj']), float(r['actual']),
                              float(r['ownership'] or 0), r['pos'], r['team'],
                              int(float(r['salary'])))
        except (ValueError, KeyError):
            continue
    return out

print(f"{'='*90}\nWALK-FORWARD PILOT — {DATE} (2024 week {WEEK})\n{'='*90}")

# ---------------- A) DATA BRIEF ----------------
pbp = pd.read_parquet(os.path.join(HERE, 'data/nflverse/pbp_2024.parquet'),
                      columns=['week', 'posteam', 'pass', 'rush', 'receiver_player_name',
                               'rusher_player_name', 'air_yards', 'yardline_100'])
pbp = pbp[pbp.week < WEEK]
def key_of(nm, team):
    if not isinstance(nm, str) or '.' not in nm:
        return None
    fi, last = nm.split('.', 1)
    return (team, fi[0].upper(), last.replace('.', '').replace(' ', '').lower())
def usage(df, namecol):
    g = df.groupby(['week', 'posteam', namecol]).size().rename('n').reset_index()
    tm = df.groupby(['week', 'posteam']).size().rename('tot').reset_index()
    g = g.merge(tm, on=['week', 'posteam'])
    g['share'] = g.n / g.tot
    return g
tg = usage(pbp[(pbp['pass'] == 1) & pbp.receiver_player_name.notna()], 'receiver_player_name')
ru = usage(pbp[(pbp['rush'] == 1) & pbp.rusher_player_name.notna()], 'rusher_player_name')
def deltas(g, namecol):
    last3 = g[g.week >= WEEK - 3].groupby(['posteam', namecol]).share.mean()
    base = g[(g.week >= 4) & (g.week < WEEK - 3)].groupby(['posteam', namecol]).share.mean()
    d = (last3 - base.reindex(last3.index).fillna(0.0)).sort_values(ascending=False)
    return d, last3
tg_d, tg_l3 = deltas(tg, 'receiver_player_name')
ru_d, ru_l3 = deltas(ru, 'rusher_player_name')

pool_now = fl_pool(DATE)
pool_prev = fl_pool(PREV)
fl_key = {}
for nm, v in pool_now.items():
    parts = nm.split()
    if len(parts) >= 2:
        fl_key[(v[4], parts[0][0].upper(), ''.join(parts[1:]).replace('.', '').replace("'", '').lower())] = nm
def to_fl(idx):
    out = []
    for (team, nmr), dv in idx.items():
        k = key_of(nmr, team)
        if k:
            k = (k[0], k[1], k[2].replace("'", ''))
            if k in fl_key:
                out.append((fl_key[k], dv))
    return out

usage_risers = [(n, d) for n, d in to_fl(tg_d.head(40)) if d >= 0.05 and pool_now[n][0] >= 6][:10]
carry_risers = [(n, d) for n, d in to_fl(ru_d.head(40)) if d >= 0.08 and pool_now[n][0] >= 6][:8]
role_steps = [(n, pool_now[n][0], pool_prev[n][0]) for n in pool_now
              if n in pool_prev and pool_prev[n][0] > 0
              and pool_now[n][0] >= max(8, 1.30 * pool_prev[n][0])]
games = {}
for r in csv.DictReader(open('/mnt/user-data/uploads/Fantasy/fc_games_all.csv.gz'.replace('.gz', ''))
                        if False else []):
    pass
import gzip, io
with gzip.open('/mnt/user-data/uploads/Fantasy/fc_games_all.csv.gz', 'rt') as fh:
    for r in csv.DictReader(fh):
        if r['period'] == f'2024-week-{WEEK}' and r['site'] == 'draftkings':
            games[r['Team']] = (float(r['game_total'] or 0), float(r['spread'] or 0))
top_games = sorted({(min(t, o) if False else v[0]) for t, v in games.items()}, reverse=True)
env = sorted(games.items(), key=lambda kv: -kv[1][0])

print("\n[A] DATA BRIEF (pre-lock legal)")
print("  usage risers (target-share, last3 vs wks4-13):")
for n, d in usage_risers:
    print(f"    {n:<22} +{d*100:4.1f}pp tgt share   proj {pool_now[n][0]:5.1f}  own {pool_now[n][2]:4.1f}%")
print("  carry risers:")
for n, d in carry_risers:
    print(f"    {n:<22} +{d*100:4.1f}pp carry share  proj {pool_now[n][0]:5.1f}  own {pool_now[n][2]:4.1f}%")
print("  role-steps (proj +30% WoW, >=8):")
for n, p1, p0 in sorted(role_steps, key=lambda x: -(x[1] / x[2]))[:10]:
    print(f"    {n:<22} proj {p0:5.1f} -> {p1:5.1f}  own {pool_now[n][2]:4.1f}%")
print("  game environments (top totals):")
seen_g = set()
for tm, (tot, spr) in env:
    if tot in seen_g or tot <= 0:
        continue
    seen_g.add(tot)
    print(f"    total {tot:4.1f}  ({tm} spread {spr:+.1f})")
    if len(seen_g) >= 5:
        break

# ---------------- B) HIS WEEK ----------------
cmeta = {r['contestId']: r for r in csv.DictReader(open(os.path.join(DATA, 'contest_meta.csv')))
         if r['date'] == DATE}
print(f"\n[B] RSBATHLA'S {DATE}")
his_over = []
tot_in = tot_out = 0.0
for p in sorted(glob.glob(os.path.join(DATA, 'users', f'{DATE}_*_rsbathla.json'))):
    cid = os.path.basename(p).split('_')[1]
    rec = json.load(open(p))
    hr = next((h['record'] for h in rec.get('hits', []) if (h.get('record') or {}).get('totalEntryCost')), None)
    if not hr:
        continue
    cm = cmeta.get(cid, {})
    tot_in += hr['totalEntryCost']; tot_out += hr.get('totalWinning', 0)
    print(f"  {cm.get('contestName','?')[:44]:<46} x{hr.get('totalRosters',0):>3} "
          f"(uniq {hr.get('uniqueRosters',0):>3})  ${hr['totalEntryCost']:>8,.0f} -> "
          f"${hr.get('totalWinning',0):>8,.0f}")
    # top overweights for the biggest MAIN contest he entered
    if cm.get('slate') == 'main' and hr.get('totalRosters', 0) >= 20:
        pl = {}
        pf = os.path.join(FL_DIR, f"{DATE}_main_{cid}.csv")
        if os.path.exists(pf):
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
                pairs.append((pid, exp, exp - lev))
        used = set()
        for pid, exp, fo in sorted(pairs, key=lambda x: -x[1]):
            best, bd = None, 9e9
            for nm, ow in pl.items():
                if nm in used:
                    continue
                d = abs(ow - fo)
                if d < bd:
                    bd, best = d, nm
            if best and bd <= 0.8:
                used.add(best)
                his_over.append((best, exp, fo))
his_over = sorted({(n, e, f) for n, e, f in his_over}, key=lambda x: -x[1])[:12]

# ---------------- C) GRADES ----------------
beats = {n: pool_now[n][1] - pool_now[n][0] for n in pool_now if pool_now[n][0] >= 5}
mu, sd = np.mean(list(beats.values())), np.std(list(beats.values()))
def z(n):
    return (beats.get(n, mu) - mu) / sd if n in beats else float('nan')
print(f"\n[C] READ GRADES (z = proj-beat that Sunday)")
print("  his top overweights:")
hits = 0
for n, e, f in his_over:
    zz = z(n)
    hits += zz >= 1
    print(f"    {n:<22} exposure {e:5.1f}%  field {f:5.1f}%  z {zz:+5.2f} {'HIT' if zz>=1 else ''}")
print(f"    -> {hits}/{len(his_over)} overweights beat proj by >=1 sigma")
bflag = [n for n, _ in usage_risers + carry_risers] + [n for n, _, _ in role_steps]
bflag = list(dict.fromkeys(bflag))[:14]
bh = sum(z(n) >= 1 for n in bflag)
print("  brief flags:")
for n in bflag:
    print(f"    {n:<22} own {pool_now[n][2]:4.1f}%  z {z(n):+5.2f} {'HIT' if z(n)>=1 else ''}")
print(f"    -> {bh}/{len(bflag)} brief flags beat proj by >=1 sigma")

# ---------------- D) MEGA COUNTERFACTUAL ----------------
print(f"\n[D] THE $10M ULTIMATE COUNTERFACTUAL ($3,333 x 3,334; his real: 55 entries, -$110,815)")
pool, meta, _ = load_slate(DATE, tier='mega')
W = 1500
size = meta['size']
payout_at, _, first, places = payout_curve(meta)
proj = np.array([p.proj for p in pool]); own = np.array([p.own for p in pool])
sal = np.array([p.salary for p in pool]); acts = np.array([p.actual for p in pool])
names = [p.name for p in pool]
his_set = {n for n, _, _ in his_over}
brief_set = set(bflag)
boost_his = np.array([1.12 if n in his_set else 1.0 for n in names])
boost_brief = np.array([1.12 if n in brief_set else 1.0 for n in names])
MODES = {'chalk': proj, 'his-style fade10': proj - 10 * own * 10,
         'his-reads chalk': proj * boost_his, 'brief-reads chalk': proj * boost_brief}
pts = simulate_worlds(pool, W)
F = size - 60
field = sample_field(pool, F, sharp_frac=0.60)
fs = np.sort(pts[field.reshape(-1)].reshape(F, 9, W).sum(axis=1), axis=0)
fact = np.sort(acts[field.reshape(-1)].reshape(F, 9).sum(axis=1))
PAY = np.array([payout_at(i) for i in range(1, size + 2)])
rng = np.random.default_rng(3)
print(f"  {'portfolio':<22} {'K':>4} {'sim ROI':>9} {'P(win)':>7} {'REAL P&L':>12}")
for tag, score in MODES.items():
    got = set()
    tries = 0
    while len(got) < 55 and tries < 350:
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
    for K in (19, 55):
        kx = order[:min(K, len(order))]
        fr = np.sort(r_all[kx], axis=0)
        place = fr + np.arange(len(kx))[:, None] + 1.0
        ev = PAY[np.clip(place, 1, size).astype(np.int64) - 1].sum(axis=0).mean()
        pwin = float((fr[0] == 0).mean())
        cost = meta['entry'] * len(kx)
        cact = acts[cands[kx].reshape(-1)].reshape(len(kx), 9).sum(axis=1)
        ra = np.sort(F - np.searchsorted(fact, cact, side='right'))
        rpl = ra + np.arange(len(kx)) + 1.0
        rpay = PAY[np.clip(rpl, 1, size).astype(np.int64) - 1].sum()
        print(f"  {tag:<22} {len(kx):>4} {(ev-cost)/cost*100:>8.0f}% {pwin*100:>6.1f}% "
              f"${rpay - cost:>+11,.0f}")
print(f"\n  week total actually: ${tot_in:,.0f} in -> ${tot_out:,.0f} out (${tot_out-tot_in:+,.0f})")
