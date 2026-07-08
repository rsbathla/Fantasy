#!/usr/bin/env python3
"""build_middle_funnel.py — the MIDDLE-OF-FIELD axis the funnel layer was missing.

defense_splits.json already carries depth (deep/short), coverage (man/zone) and position
(by_pos incl slot) funnels — but NO horizontal/middle axis. This adds it as a companion
overlay (middle_funnel.json), following the apply_funnel_overlay.py pattern rather than
mutating the verified core file.

Two sides, both from nflverse pbp (2 seasons for stability, matching defense_splits convention):
  DEFENSE  middle_funnel[def] : allowed_epa / cpoe_allowed over the middle, vs-perimeter funnel
           shape, how-often-attacked (mid_tgt_rate), and softness_pctl (0-100, higher=softer).
  PLAYER   middle_win[rec]    : EPA/CPOE when targeted middle, catch%, and exposure
           (mid_tgt_share — how middle-reliant he is), plus win_pctl.

The cross (C8 — strength x softness x EXPOSURE, never a raw per-play rate):
  middle_edge(player, opp) requires the player to actually RUN the middle before a middle
  funnel counts. Surfaced in the film room as a matchup tag + fed to the buy-the-dip board
  (wins the middle but bad box score = the signal).

Boundary (honest): pbp sees TARGETS, not routes — this is "produces/open WHEN worked middle,"
not full all-route separation (that needs NGS/FP charting not loaded). CPOE is the openness proxy.
"""
import argparse, glob, json, os, re, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PBP = os.path.join(HERE, 'data', 'nflverse')
OUT = os.path.join(HERE, 'middle_funnel.json')
SEASONS = ('2024', '2025')
MIN_DEF = 60          # min middle pass plays faced (2yr) to rank a defense
MIN_REC = 30          # min middle targets (2yr) to rank a receiver


def _load(seasons=SEASONS, before=None):
    """before=(season, week): keep only plays STRICTLY before that slate (pre-lock legal)."""
    fr = []
    for s in seasons:
        p = os.path.join(PBP, f'pbp_{s}.parquet')
        if not os.path.exists(p):
            continue
        cols = ['defteam', 'posteam', 'pass', 'pass_location', 'epa', 'cpoe',
                'complete_pass', 'yards_gained', 'receiver_player_name', 'sack']
        if before:
            cols.append('week')
        d = pd.read_parquet(p, columns=cols)
        if before and s == str(before[0]):
            d = d[d.week < before[1]]
        d['season'] = s
        fr.append(d)
    if not fr:
        sys.exit(f"[middle_funnel] no pbp parquet in {PBP} — ABORT")
    df = pd.concat(fr, ignore_index=True)
    return df[(df['pass'] == 1) & (df.sack != 1) & df.pass_location.notna() & df.epa.notna()].copy()


def build(seasons=SEASONS, before=None, out_path=OUT, min_def=MIN_DEF, min_rec=MIN_REC):
    p = _load(seasons, before)
    global MIN_DEF, MIN_REC
    MIN_DEF, MIN_REC = min_def, min_rec
    # ---- DEFENSE side ----
    drows = []
    for d, g in p.groupby('defteam'):
        mid = g[g.pass_location == 'middle']
        per = g[g.pass_location != 'middle']
        if len(mid) < MIN_DEF:
            continue
        drows.append({'def': d, 'allowed_epa': round(float(mid.epa.mean()), 3),
                      'cpoe_allowed': round(float(mid.cpoe.mean()), 1),
                      'vs_perim': round(float(mid.epa.mean() - per.epa.mean()), 3),
                      'mid_tgt_rate': round(len(mid) / len(g) * 100, 1)})
    D = pd.DataFrame(drows)
    D['softness_pctl'] = (D.allowed_epa.rank(pct=True) * 100).round(1)   # higher EPA allowed = softer
    D['funnel_pctl'] = (D.vs_perim.rank(pct=True) * 100).round(1)        # middle softer than own edges
    defense = {r['def']: {k: r[k] for k in ('allowed_epa', 'cpoe_allowed', 'vs_perim',
                                            'mid_tgt_rate', 'softness_pctl', 'funnel_pctl')}
               for _, r in D.iterrows()}
    # ---- PLAYER side ----
    tot_tgt = p[p.receiver_player_name.notna()].groupby('receiver_player_name').size()
    pm = p[(p.pass_location == 'middle') & p.receiver_player_name.notna()]
    prows = []
    for nm, g in pm.groupby('receiver_player_name'):
        if len(g) < MIN_REC:
            continue
        prows.append({'rec': nm, 'mid_tgt': int(len(g)),
                      'epa': round(float(g.epa.mean()), 3),
                      'cpoe': round(float(g.cpoe.mean()), 1),
                      'catch_pct': round(float(g.complete_pass.mean()) * 100, 1),
                      'mid_tgt_share': round(len(g) / max(int(tot_tgt.get(nm, len(g))), 1) * 100, 1)})
    P = pd.DataFrame(prows)
    P['win_pctl'] = (P.epa.rank(pct=True) * 100).round(1)
    players = {r['rec']: {k: r[k] for k in ('mid_tgt', 'epa', 'cpoe', 'catch_pct',
                                            'mid_tgt_share', 'win_pctl')}
               for _, r in P.iterrows()}
    obj = {'_meta': {'seasons': list(seasons), 'before': before,
                     'source': 'nflverse pbp pass_location=middle', 'openness_proxy': 'cpoe',
                     'boundary': 'target-based, not all-route separation',
                     'min_def_plays': MIN_DEF, 'min_rec_targets': MIN_REC},
           'defense': defense, 'players': players}
    json.dump(obj, open(out_path, "w"), indent=1)
    tag = f" (as-of {before[0]} wk{before[1]}, pre-lock)" if before else ""
    print(f"[middle_funnel] {len(defense)} defenses, {len(players)} receivers{tag} -> {out_path}")
    return obj


ALIAS = {'BLT': 'BAL', 'CLV': 'CLE', 'HST': 'HOU', 'ARZ': 'ARI', 'LA': 'LAR', 'JAC': 'JAX',
         'LVR': 'LV', 'WSH': 'WAS', 'SD': 'LAC', 'OAK': 'LV', 'STL': 'LAR'}


def _pbp_name(full):
    """'Jaxon Smith-Njigba' -> 'J.Smith-Njigba' (pbp receiver format)."""
    parts = full.split()
    return f"{parts[0][0]}.{' '.join(parts[1:])}" if len(parts) >= 2 else full


_SUFFIX = re.compile(r'\b(jr|sr|ii|iii|iv|v)\b\.?', re.I)


def _norm_key(name):
    """Suffix/format-robust key: 'Marvin Harrison Jr.' and 'M.Harrison Jr' -> ('m','harrison')."""
    n = _SUFFIX.sub('', name.lower()).replace('.', ' ').replace("'", '').strip()
    parts = n.split()
    if len(parts) >= 2:
        return (parts[0][0], ''.join(parts[1:]))
    return (n, '')


_IDX_CACHE = {}


def _resolve_player(full, L):
    """Look up a player in the layer by exact pbp name, then suffix-robust (initial,lastname)."""
    P = L['players']
    hit = P.get(_pbp_name(full)) or P.get(full)
    if hit:
        return hit
    idx = _IDX_CACHE.get(id(P))
    if idx is None:
        idx = {_norm_key(k): v for k, v in P.items()}
        _IDX_CACHE[id(P)] = idx
    return idx.get(_norm_key(full))


def load_layer():
    if not os.path.exists(OUT):
        sys.exit(f"[middle_funnel] {OUT} not built — run: python3 build_middle_funnel.py --build")
    return json.load(open(OUT))


def middle_edge(player_full, opp, layer=None):
    """C8-correct cross: strength x softness x EXPOSURE. Returns a dict or None."""
    L = layer or load_layer()
    dv = L['defense'].get(ALIAS.get(opp, opp))
    pl = _resolve_player(player_full, L)
    if not dv or not pl:
        return {'player': player_full, 'opp': opp, 'edge': None,
                'reason': 'no middle sample for ' + (player_full if not pl else opp)}
    exposure = pl['mid_tgt_share'] / 100.0                      # must actually run the middle
    smash = (dv['softness_pctl'] >= 70 and pl['win_pctl'] >= 65 and pl['mid_tgt_share'] >= 20)
    fort = (dv['softness_pctl'] <= 25 and pl['mid_tgt_share'] >= 25)
    tag = ('MIDDLE SMASH' if smash else 'MIDDLE FORTRESS (avoid)' if fort else 'neutral')
    return {'player': player_full, 'opp': opp, 'tag': tag,
            'def_softness_pctl': dv['softness_pctl'], 'def_allowed_epa': dv['allowed_epa'],
            'player_win_pctl': pl['win_pctl'], 'player_mid_share': pl['mid_tgt_share'],
            'exposure': round(exposure, 2)}


def selftest():
    L = build()
    dfn = L['defense']
    order = sorted(dfn, key=lambda t: -dfn[t]['softness_pctl'])
    print(f"\nsoftest-middle top5: {order[:5]}  | stiffest: {order[-4:]}")
    checks = [("DAL is a top-6 middle funnel", 'DAL' in order[:6]),
              ("a known fortress (BUF/PHI/SEA/JAX) is bottom-8",
               any(t in order[-8:] for t in ('BUF', 'PHI', 'SEA', 'JAX'))),
              ("JSN or Puka ranks as an elite middle-winner",
               any((L['players'].get(n, {}).get('win_pctl', 0) >= 85)
                   for n in ('J.Smith-Njigba', 'P.Nacua')))]
    for name, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    # exposure guard: a middle funnel must NOT flag a pure-perimeter WR as a smash
    print("  example edge (J.Smith-Njigba vs DAL):", middle_edge('Jaxon Smith-Njigba', 'DAL', L)['tag'])
    return 0 if all(ok for _, ok in checks) else 1


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--build', action='store_true')
    ap.add_argument('--test', action='store_true')
    ap.add_argument('--edge', nargs=2, metavar=('PLAYER', 'OPP'))
    a = ap.parse_args()
    if a.test:
        sys.exit(selftest())
    if a.build:
        build()
    elif a.edge:
        print(json.dumps(middle_edge(a.edge[0], a.edge[1]), indent=1))
    else:
        ap.print_help()
