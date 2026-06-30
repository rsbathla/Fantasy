#!/usr/bin/env python3
"""build_defense_splits.py — the DEFENSE side of DFS split-parity.

For each of the 32 defenses, compute ALLOWED receiving efficiency on the SAME axes the player
profiles use (vs man / vs zone / deep / short / by position group), so a player's strength on an
axis can be lined up against the defense's softness on that exact axis ("WR strong vs man" ->
"defense soft vs man" = a smash spot). Output: defense_splits.json (per team, val + 0-100 percentile
where HIGHER percentile = SOFTER = better matchup for the offense).

Sources (real charting, 2025; 2024 folded in for stability where present):
  - FP_SWEEP/<yr>/Defense_Receiving/coverageScheme/{Cover 0,1,2 Man | Cover 2,3,4,6}.csv  -> vs man / vs zone allowed YPR
  - FP_SWEEP/<yr>/Defense_Receiving/depthOfTarget/{1_9,20_99}.csv                          -> short / deep allowed YPR
  - boom/defensive_profile.json                                                            -> FPAA allowed by position group + funnels + leans
  - boom/defense_shell.json                                                                -> coverage shell (single/two-high, man rate)
  - defense.json                                                                           -> unit percentiles (cov/rush/run)
"""
import core, pandas as pd, numpy as np, glob, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
def J(p): return json.load(open(os.path.join(HERE, p), encoding='utf-8')) if os.path.exists(os.path.join(HERE, p)) else {}
ab = core.team_abbr
MAN_COV = ['Cover 0', 'Cover 1', 'Cover 2 Man']
ZONE_COV = ['Cover 2', 'Cover 3', 'Cover 4', 'Cover 6']
YRS = ['2025', '2024']
YC = 'opponentStatsReceivingYardsTotal'; RC = 'opponentStatsReceivingRoutesTotal'
TC = 'opponentStatsReceivingTargetsTotal'; RECC = 'opponentStatsReceivingReceptionsTotal'

def _team_of(row):
    loc = str(row.get('teamLocation', '')).strip(); nick = str(row.get('teamNickname', '')).strip()
    return core.team_abbr((loc + ' ' + nick).strip()) or core.team_abbr(nick)

def _sum_cov(folder_glob, files):
    """Sum yards & routes across the given coverage files, per team -> {abbr:(yards,routes,tgts)}."""
    agg = {}
    for cov in files:
        for yr in YRS:
            p = f'{HERE}/NFL-master/FP_SWEEP/{yr}/{folder_glob}/{cov}.csv'
            if not os.path.exists(p):
                continue
            d = pd.read_csv(p)
            for _, r in d.iterrows():
                t = _team_of(r)
                if not t:
                    continue
                y = pd.to_numeric(r.get(YC), errors='coerce'); rt = pd.to_numeric(r.get(RC), errors='coerce')
                tg = pd.to_numeric(r.get(TC), errors='coerce')
                if pd.isna(y) or pd.isna(rt):
                    continue
                a = agg.setdefault(t, [0.0, 0.0, 0.0])
                a[0] += y; a[1] += rt; a[2] += (0 if pd.isna(tg) else tg)
    return agg

def _depth(files):
    """depthOfTarget bucket(s) -> {abbr:(yards,routes)}."""
    agg = {}
    for f in files:
        for yr in YRS:
            p = f'{HERE}/NFL-master/FP_SWEEP/{yr}/Defense_Receiving/depthOfTarget/{f}.csv'
            if not os.path.exists(p):
                continue
            d = pd.read_csv(p)
            for _, r in d.iterrows():
                t = _team_of(r)
                if not t:
                    continue
                y = pd.to_numeric(r.get(YC), errors='coerce'); rt = pd.to_numeric(r.get(RC), errors='coerce')
                if pd.isna(y) or pd.isna(rt):
                    continue
                a = agg.setdefault(t, [0.0, 0.0]); a[0] += y; a[1] += rt
    return agg

def ratio(agg):
    return {t: (v[0] / v[1]) for t, v in agg.items() if v[1] > 0}

man = ratio(_sum_cov('Defense_Receiving/coverageScheme', MAN_COV))
zone = ratio(_sum_cov('Defense_Receiving/coverageScheme', ZONE_COV))
deep = ratio(_depth(['20_99']))
short = ratio(_depth(['1_9']))

dprof = J('boom/defensive_profile.json')
dshell = J('boom/defense_shell.json')
dunit = J('defense.json')
units = dunit.get('teams', dunit) if isinstance(dunit, dict) else {}

def pctl(d, higher_softer=True):
    """0-100 percentile across teams. higher_softer: more allowed -> higher pctl (better for offense)."""
    items = [(t, v) for t, v in d.items() if v is not None]
    items.sort(key=lambda kv: kv[1])
    n = len(items); out = {}
    for i, (t, v) in enumerate(items):
        p = 100.0 * i / (n - 1) if n > 1 else 50.0
        out[t] = round(p if higher_softer else 100 - p, 1)
    return out

man_p, zone_p, deep_p, short_p = pctl(man), pctl(zone), pctl(deep), pctl(short)

TEAMS = sorted(set(list(man) + list(zone) + list(deep) + list(short) + list(dprof)))
out = {}
for t in TEAMS:
    prof = dprof.get(t, {}); fpaa = prof.get('dvoa_fpaa', {}); shell = dshell.get(t, {})
    u = units.get(t, {})
    rec = {
        'vs_man': {'allowed_ypr': round(man[t], 3), 'softness_pctl': man_p.get(t)} if t in man else None,
        'vs_zone': {'allowed_ypr': round(zone[t], 3), 'softness_pctl': zone_p.get(t)} if t in zone else None,
        'deep': {'allowed_ypr': round(deep[t], 3), 'softness_pctl': deep_p.get(t)} if t in deep else None,
        'short': {'allowed_ypr': round(short[t], 3), 'softness_pctl': short_p.get(t)} if t in short else None,
        # FPAA = fantasy points above average ALLOWED to that position group (higher = softer)
        'by_pos': {k: fpaa.get(k) for k in ('qb', 'rb', 'wr', 'te', 'wr1', 'wr2', 'slot') if k in fpaa} or None,
        'shell': {'man_rate': shell.get('man'),
                  'single_high': shell.get('single_high'), 'two_high': shell.get('two_high')} if shell else None,
        'units': {'pass_cov_pctl': u.get('pass_cov_pctl'), 'pass_rush_pctl': u.get('pass_rush_pctl'),
                  'run_def_pctl': u.get('run_def_pctl')} if u else None,
        'funnels': prof.get('funnels'), 'lean_2026': prof.get('lean_2026'),
        # NOTE: defensive_profile.json's `dc` field is unreliable (scrambled/incomplete) — omitted here
        # rather than surface a wrong coordinator name. Coaching lives in the coaching dossier.
    }
    out[t] = {k: v for k, v in rec.items() if v is not None}

json.dump(out, open(os.path.join(HERE, 'defense_splits.json'), 'w'), indent=1)
print(f"defense_splits.json: {len(out)} teams | man {len(man)} zone {len(zone)} deep {len(deep)} short {len(short)} | fpaa {sum(1 for t in out if out[t].get('by_pos'))}")
# spot check: softest vs man and vs deep (best WR matchups)
softm = sorted(man.items(), key=lambda kv: -kv[1])[:4]
softd = sorted(deep.items(), key=lambda kv: -kv[1])[:4]
print("softest vs MAN (WR-vs-man smash):", [(t, round(v, 2)) for t, v in softm])
print("softest DEEP (vertical smash):   ", [(t, round(v, 2)) for t, v in softd])
