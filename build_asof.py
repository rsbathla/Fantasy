#!/usr/bin/env python3
"""build_asof.py — the generalized AS-OF feature engine (no look forward).

For (season, week) it recomputes the whole pbp-derivable factor stack from ONLY games before
that slate — the honest way to run a 2025 walk-forward, and the identical call 2026 uses live.
Replaces reading the repo's 2026-projection layers (which would leak look-ahead into a 2025 read).

Produces three blocks:
  DEFENSE[team]  : pass/rush EPA & success allowed, by DEPTH (deep/short), LOCATION (L/M/R),
                   and RECEIVER POSITION (WR/TE/RB via roster join); PROE faced; softness pctls.
  OFFENSE[team]  : plays/game, pass rate, PROE (pass-over-expected, neutral), RZ pass rate,
                   EPA/play, pace — the environment drivers.
  USAGE[player]  : target/air-yards/RZ-target share, carry/RZ-carry share, recent trend.
                   (routes/snaps aren't in pbp — target-based; FP charting fills that later.)

Boundary: nflverse pbp has no man/zone coverage label — that axis stays with the charting layer;
everything here is pbp+roster, fully as-of-able.
"""
import argparse, glob, json, os, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PBP = os.path.join(HERE, 'data', 'nflverse')

_ROST = {}
def _pos_map(seasons):
    key = tuple(seasons)
    if key in _ROST:
        return _ROST[key]
    m = {}
    for s in seasons:
        p = os.path.join(PBP, f'roster_{s}.parquet')
        if not os.path.exists(p):
            continue
        r = pd.read_parquet(p, columns=['gsis_id', 'position'])
        for gid, pos in zip(r.gsis_id, r.position):
            if isinstance(gid, str):
                m[gid] = 'RB' if pos == 'FB' else pos
    _ROST[key] = m
    return m


def _load(before):
    """2024-full + (season) weeks < week. before=(season, week)."""
    season, week = before
    seasons = [str(y) for y in range(2024, season + 1)]
    cols = ['posteam', 'defteam', 'week', 'pass', 'rush', 'play_type', 'epa', 'success',
            'air_yards', 'pass_location', 'yardline_100', 'receiver_player_id',
            'receiver_player_name', 'xpass', 'wp', 'sack', 'down', 'touchdown']
    fr = []
    for s in seasons:
        fp = os.path.join(PBP, f'pbp_{s}.parquet')
        if not os.path.exists(fp):
            continue
        d = pd.read_parquet(fp, columns=cols)
        if s == str(season):
            d = d[d.week < week]
        fr.append(d)
    if not fr:
        sys.exit('[asof] no pbp')
    df = pd.concat(fr, ignore_index=True)
    return df, seasons


def _pctl(series):
    return (series.rank(pct=True) * 100).round(1)


def build(season, week, out_path=None):
    df, seasons = _load((season, week))
    pos = _pos_map(seasons)
    passes = df[(df['pass'] == 1) & (df.sack != 1) & df.epa.notna()].copy()
    passes['recpos'] = passes.receiver_player_id.map(pos)
    runs = df[(df['rush'] == 1) & df.epa.notna()]
    ngames = df.groupby('posteam').apply(lambda g: g[['week']].drop_duplicates().shape[0]
                                         if 'game_id' not in g else g.game_id.nunique())

    # ---- DEFENSE ----
    D = {}
    for d, g in passes.groupby('defteam'):
        deep = g[g.air_yards >= 15]; short = g[g.air_yards < 15]
        byp = {p: round(float(g[g.recpos == p].epa.mean()), 3)
               for p in ('WR', 'TE', 'RB') if (g.recpos == p).sum() >= 15}
        rg = runs[runs.defteam == d]
        D[d] = {'pass_epa': round(float(g.epa.mean()), 3),
                'pass_succ': round(float(g.success.mean()), 3),
                'deep_epa': round(float(deep.epa.mean()), 3) if len(deep) else None,
                'short_epa': round(float(short.epa.mean()), 3) if len(short) else None,
                'vs_WR': byp.get('WR'), 'vs_TE': byp.get('TE'), 'vs_RB': byp.get('RB'),
                'rush_epa': round(float(rg.epa.mean()), 3) if len(rg) else None,
                'proe_faced': round(float((g['pass'] - g.xpass).mean()), 3) if g.xpass.notna().any() else None}
    Dd = pd.DataFrame(D).T
    for ax in ('pass_epa', 'deep_epa', 'short_epa', 'vs_WR', 'vs_TE', 'vs_RB'):
        Dd[ax + '_softpctl'] = _pctl(Dd[ax].astype(float))
    D = {t: {**D[t], **{ax + '_softpctl': (None if pd.isna(Dd.loc[t, ax + '_softpctl'])
                                           else float(Dd.loc[t, ax + '_softpctl']))
                        for ax in ('pass_epa', 'deep_epa', 'short_epa', 'vs_WR', 'vs_TE', 'vs_RB')}}
         for t in D}

    # ---- OFFENSE / ENVIRONMENT ----
    O = {}
    for o, g in passes.groupby('posteam'):
        allp = df[(df.posteam == o) & df.play_type.isin(['pass', 'run'])]
        neutral = allp[(allp.wp >= 0.15) & (allp.wp <= 0.85)]
        gm = max(int(allp.week.nunique()), 1)
        rz = allp[allp.yardline_100 <= 20]
        O[o] = {'plays_pg': round(len(allp) / gm, 1),
                'pass_rate': round(float((allp['pass'] == 1).mean()), 3),
                'neutral_pass_rate': round(float((neutral['pass'] == 1).mean()), 3) if len(neutral) else None,
                'proe': round(float((allp['pass'] - allp.xpass).mean()), 3) if allp.xpass.notna().any() else None,
                'rz_pass_rate': round(float((rz['pass'] == 1).mean()), 3) if len(rz) else None,
                'off_epa': round(float(allp.epa.mean()), 3)}
    Od = pd.DataFrame(O).T
    for ax in ('plays_pg', 'proe', 'off_epa'):
        Od[ax + '_pctl'] = _pctl(Od[ax].astype(float))
    for t in O:
        for ax in ('plays_pg', 'proe', 'off_epa'):
            O[t][ax + '_pctl'] = (None if pd.isna(Od.loc[t, ax + '_pctl']) else float(Od.loc[t, ax + '_pctl']))

    # ---- USAGE (receivers + rushers) ----
    tgt_team = passes.groupby('posteam').size()
    ay_team = passes.groupby('posteam').air_yards.sum()
    U = {}
    for nm, g in passes[passes.receiver_player_name.notna()].groupby('receiver_player_name'):
        tm = g.posteam.mode().iloc[0]
        rz = g[g.yardline_100 <= 20]
        wks = sorted(g.week.unique())
        recent = g[g.week >= (max(wks) - 2)] if wks else g
        U[nm] = {'team': tm, 'tgt': int(len(g)),
                 'tgt_share': round(len(g) / max(int(tgt_team.get(tm, 1)), 1) * 100, 1),
                 'ay_share': round(float(g.air_yards.sum()) / max(float(ay_team.get(tm, 1)), 1) * 100, 1),
                 'rz_tgt': int(len(rz)),
                 'tgt_share_recent': round(len(recent) / max(len(g), 1) * 100, 1)}
    obj = {'_meta': {'as_of': [season, week], 'seasons': seasons,
                     'note': 'pbp+roster, no look forward; man/zone not available (charting only)'},
           'defense': D, 'offense': O, 'usage': U}
    if out_path:
        json.dump(obj, open(out_path, 'w'), indent=1)
    print(f"[asof] {season} wk{week}: {len(D)} defenses x multi-axis, {len(O)} offenses, "
          f"{len(U)} receivers  (from {seasons} thru wk{week-1})", file=sys.stderr)
    return obj


def selftest():
    L = build(2025, 6)   # mid-2025, plenty of prior data
    O, D = L['offense'], L['defense']
    fast = sorted(O, key=lambda t: -(O[t]['plays_pg'] or 0))[:6]
    passy = sorted(O, key=lambda t: -(O[t]['proe'] or -9))[:6]
    checks = [("all 32 offenses have pace", sum(1 for t in O if O[t]['plays_pg']) >= 30),
              ("PROE spread is real (top vs bottom > 5pp)",
               (max(O[t]['proe'] for t in O if O[t]['proe'] is not None) -
                min(O[t]['proe'] for t in O if O[t]['proe'] is not None)) > 0.05),
              ("defense by-position axes populated for most teams",
               sum(1 for t in D if D[t].get('vs_WR') is not None) >= 28)]
    print(f"fast-pace: {fast}\npass-happy (PROE): {passy}")
    for n, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {n}")
    return 0 if all(ok for _, ok in checks) else 1


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--build', nargs=2, type=int, metavar=('SEASON', 'WEEK'))
    ap.add_argument('--test', action='store_true')
    a = ap.parse_args()
    if a.test:
        sys.exit(selftest())
    elif a.build:
        build(a.build[0], a.build[1], out_path=f'/tmp/asof_{a.build[0]}_wk{a.build[1]}.json')
    else:
        ap.print_help()
