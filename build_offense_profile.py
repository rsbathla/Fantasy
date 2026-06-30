#!/usr/bin/env python3
"""build_offense_profile.py — the OFFENSE scheme-identity dossier (all 32 teams).

Fixes the gap where the dossier had only a one-line identity + a team-motion field that was null for
all 32. Builds a real per-offense scheme profile from charting + environment data:
  * RUN SCHEME identity (zone vs gap) — aggregated from FP RunType attempts (Inside/Outside Zone vs
    Power/Man-Duo/Counter/Trap). This is the missing scheme signal.
  * PACE / plays (team_env), PASS RATE (features tm_pass_rate), motion & play-action where charted.
  * PLAY-CALLER + 2026 scheme dials (scheme_2026), environment (env index, win total), key adds/losses.
Output: offense_profile.json (per team) — a fundamental "who is this offense" object.
"""
import core, pandas as pd, numpy as np, glob, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
def J(p):
    fp = os.path.join(HERE, p)
    return json.load(open(fp, encoding='utf-8')) if os.path.exists(fp) else {}
# charting-source team aliases that core.team_abbr doesn't fold (would split a team's data otherwise)
_ALIAS = {'BLT': 'BAL', 'CLV': 'CLE', 'HST': 'HOU', 'ARZ': 'ARI', 'LA': 'LAR', 'WSH': 'WAS', 'JAC': 'JAX', 'OAK': 'LV', 'SD': 'LAC', 'STL': 'LAR'}
VALID = {'ARI', 'ATL', 'BAL', 'BUF', 'CAR', 'CHI', 'CIN', 'CLE', 'DAL', 'DEN', 'DET', 'GB', 'HOU', 'IND', 'JAX', 'KC', 'LAC', 'LAR', 'LV', 'MIA', 'MIN', 'NE', 'NO', 'NYG', 'NYJ', 'PHI', 'PIT', 'SEA', 'SF', 'TB', 'TEN', 'WAS'}
def ab(x):
    a = core.team_abbr(x); return _ALIAS.get(a, a)

ZONE = ['Inside Zone', 'Outside Zone']
GAP = ['Power', 'Man-Duo', 'Counter', 'Trap']

def runtype_share():
    """Per-team zone vs gap rushing attempts (2024+2025) -> {team:{zone_rate, n_att}}."""
    agg = {}
    for scheme, files in [('zone', ZONE), ('gap', GAP)]:
        for yr in ['2025', '2024']:
            for f in files:
                p = f'{HERE}/NFL-master/FP/{yr}/Rushing/RunType/{f}.csv'
                if not os.path.exists(p):
                    continue
                d = pd.read_csv(p)
                tc = next((c for c in d.columns if c.lower() in ('team', 'tm')), None)
                ac = next((c for c in d.columns if c.upper() in ('ATT', 'ATTEMPTS', 'CAR')), None)
                if not tc or not ac:
                    continue
                for _, r in d.iterrows():
                    t = ab(r.get(tc))
                    a = pd.to_numeric(r.get(ac), errors='coerce')
                    if t and pd.notna(a):
                        x = agg.setdefault(t, {'zone': 0.0, 'gap': 0.0})
                        x[scheme] += a
    out = {}
    for t, v in agg.items():
        tot = v['zone'] + v['gap']
        if tot > 0:
            out[t] = {'zone_rate': round(100 * v['zone'] / tot, 1), 'n_att': int(tot)}
    return out

run = runtype_share()
env = J('boom/team_env.json')
scheme = J('scheme_2026.json')
web = {ab(t.get('team')): t for t in J('web_teams.json')} if isinstance(J('web_teams.json'), list) else {}
personnel = J('personnel_changes.json')
feat = pd.read_csv(os.path.join(HERE, 'features.csv'))
TEAM = {}
for t, g in feat.groupby('team'):
    a = ab(t)
    TEAM[a] = {
        'pass_rate': float(g['tm_pass_rate'].iloc[0]) if 'tm_pass_rate' in g and pd.notna(g['tm_pass_rate'].iloc[0]) else None,
        'plays': float(g['tm_plays'].iloc[0]) if 'tm_plays' in g and pd.notna(g['tm_plays'].iloc[0]) else None,
        'motion': float(g['team_motion'].iloc[0]) if 'team_motion' in g and pd.notna(g['team_motion'].iloc[0]) else None,
        'pa': float(g['team_play_action'].iloc[0]) if 'team_play_action' in g and pd.notna(g['team_play_action'].iloc[0]) else None,
        'vacated': float(g['team_vacated_tgt'].iloc[0]) if 'team_vacated_tgt' in g and pd.notna(g['team_vacated_tgt'].iloc[0]) else None,
    }

ALL = sorted(VALID)   # exactly the 32 NFL teams (alias variants already folded by ab())

def pctl_map(vals):
    items = sorted([(k, v) for k, v in vals.items() if v is not None], key=lambda kv: kv[1])
    n = len(items); return {k: round(100 * i / (n - 1), 0) if n > 1 else 50 for i, (k, v) in enumerate(items)}

pace_p = pctl_map({t: (env.get(t, {}) or {}).get('pace_pctl') for t in ALL})
zone_p = pctl_map({t: run.get(t, {}).get('zone_rate') for t in ALL})

def identity(t):
    e = env.get(t, {}) or {}; tm = TEAM.get(t, {}); rr = run.get(t, {})
    bits = []
    pace = e.get('pace_pctl')
    if pace is not None:
        bits.append('up-tempo' if pace >= 66 else ('slow-paced' if pace <= 33 else 'average-pace'))
    pr = tm.get('pass_rate')
    if pr is not None:
        bits.append('pass-heavy' if pr >= 57 else ('run-leaning' if pr <= 48 else 'balanced'))
    zr = rr.get('zone_rate')
    if zr is not None:
        bits.append('wide/zone-run' if zr >= 60 else ('gap/power-run' if zr <= 45 else 'mixed-run'))
    env_idx = e.get('env_idx'); wt = e.get('win_total')
    tail = []
    if env_idx is not None:
        tail.append(f"env {round(env_idx)}")
    if wt is not None:
        tail.append(f"{wt} win total")
    sc = scheme.get(t, {})
    head = (sc.get('playcaller', '').split('(')[0].strip() + ' — ') if sc.get('playcaller') else ''
    return head + ', '.join(bits) + (' offense' if bits else 'offense') + (f" ({'; '.join(tail)})" if tail else '')

out = {}
for t in ALL:
    e = env.get(t, {}) or {}; tm = TEAM.get(t, {}); rr = run.get(t, {}); sc = scheme.get(t, {}); w = web.get(t, {})
    out[t] = {
        'identity': identity(t),
        'pace': {'pctl': e.get('pace_pctl'), 'plays_pg': e.get('plays_pg'), 'rank_band': pace_p.get(t)},
        'pass_rate': tm.get('pass_rate'),
        'run_scheme': {'zone_rate': rr.get('zone_rate'), 'lean': ('zone' if (rr.get('zone_rate') or 50) >= 60 else 'gap' if (rr.get('zone_rate') or 50) <= 45 else 'mixed'), 'softness_band': zone_p.get(t)} if rr else None,
        'motion': tm.get('motion'), 'play_action': tm.get('pa'),
        'environment': {'env_idx': e.get('env_idx'), 'off_q': e.get('off_q'), 'win_total': e.get('win_total')},
        'vacated_tgt_pct': tm.get('vacated'),
        'playcaller': sc.get('playcaller'), 'scheme_dials': sc.get('off'), 'scheme_note': sc.get('note'),
        'outlook': w.get('offense_outlook'),
        'adds': (w.get('key_additions') or w.get('additions')),
        'losses': (w.get('key_losses') or w.get('losses')),
    }
    out[t] = {k: v for k, v in out[t].items() if v is not None}

json.dump(out, open(os.path.join(HERE, 'offense_profile.json'), 'w'), ensure_ascii=False, indent=1)
n_run = sum(1 for t in out if out[t].get('run_scheme'))
n_caller = sum(1 for t in out if out[t].get('playcaller'))
print(f"offense_profile.json: {len(out)} teams | run-scheme {n_run} | playcaller {n_caller} | motion {sum(1 for t in out if out[t].get('motion') is not None)}")
for t in ['DET', 'SF', 'BAL', 'KC', 'PHI']:
    if t in out:
        print(f"  {t}: {out[t]['identity']}")
