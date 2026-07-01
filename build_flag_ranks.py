#!/usr/bin/env python3
"""Flag-informed, ADP-anchored rank nudge.

Turns the per-player flag work (boom/flags_{QB,RB,WR,TE}.json) into a BOUNDED nudge on top of
market ADP -- the "ADP-anchored" choice: the market is the backbone, flags only move a player a
few spots. Deliberately a SEPARATE layer from the fusion consensus (so we don't double-count the
signals fusion already blends); this nudges MARKET ADP, nothing internal.

Per player, within his own position, we score three flag-derived components:
  1. boom base-rate      (`base`)               -- the upside signal the system drafts on
  2. skill-flag breadth  (len(`skill_flags`))   -- how many distinct real strengths he carries
  3. 2026 playoff matchup (mean weeks-15/16/17 `p`) -- the "upcoming season" schedule, playoff weeks
Each -> within-position percentile -> centered to [-1,1]. Weighted blend = flag_score in ~[-1,1].
nudge = -CAP * flag_score  (strong flags -> negative -> moves UP the board). CAP caps the move.

Writes flag_ranks.json keyed by core.fn(name): market rank/ADP, the components, flag_score, nudge,
adjusted order, adjusted overall + positional rank, delta vs market, and the top flag names (rationale).
"""
import json, glob, os, statistics
import core

HERE = os.path.dirname(os.path.abspath(__file__))
FLAG_FILES = {p: os.path.join(HERE, 'boom', f'flags_{p}.json') for p in ('QB', 'RB', 'WR', 'TE')}

CAP = 8.0                 # max spots a player can move off market ADP (conservative / ADP-anchored)
W_BOOM, W_FLAGS, W_PMQ = 0.50, 0.30, 0.20   # component weights (sum 1.0)
PLAYOFF_WEEKS = {15, 16, 17}


def _pmq(rec):
    """Mean matchup percentile over the fantasy-playoff weeks (15-17); None if absent."""
    wks = rec.get('weeks') or []
    ps = [w.get('p') for w in wks if isinstance(w, dict) and w.get('wk') in PLAYOFF_WEEKS and w.get('p') is not None]
    return statistics.mean(ps) if ps else None


def _pctl(vals, x):
    """Percentile (0-100) of x within vals (strictly-less convention); 50 if singleton/None."""
    xs = [v for v in vals if v is not None]
    if x is None or len(xs) < 2:
        return 50.0
    return round(100.0 * sum(1 for y in xs if y < x) / len(xs), 1)


def load_players():
    players = []
    for pos, path in FLAG_FILES.items():
        if not os.path.exists(path):
            continue
        d = json.load(open(path, encoding='utf-8'))
        for k, r in d.items():
            if not isinstance(r, dict) or r.get('adp') is None:
                continue
            players.append({
                'key': core.fn(r.get('name', k)),
                'name': r.get('name', k), 'pos': pos, 'team': r.get('team'),
                'adp': float(r['adp']),
                'boom': r.get('base'),
                'n_flags': len(r.get('skill_flags') or []),
                'pmq': _pmq(r),
                'top_flags': [f.get('f') for f in (r.get('skill_flags') or [])[:4] if f.get('f')],
            })
    return players


def build():
    players = load_players()
    # within-position percentile pools
    by_pos = {}
    for p in players:
        by_pos.setdefault(p['pos'], []).append(p)
    for pos, grp in by_pos.items():
        booms = [p['boom'] for p in grp]
        nflg = [p['n_flags'] for p in grp]
        pmqs = [p['pmq'] for p in grp]
        for p in grp:
            b = _pctl(booms, p['boom'])
            f = _pctl(nflg, p['n_flags'])
            m = _pctl(pmqs, p['pmq']) if p['pmq'] is not None else 50.0
            # center each percentile to [-1,1]
            cb, cf, cm = (b - 50) / 50.0, (f - 50) / 50.0, (m - 50) / 50.0
            score = W_BOOM * cb + W_FLAGS * cf + W_PMQ * cm      # ~[-1,1]
            p['boom_pctl'], p['flags_pctl'], p['pmq_pctl'] = b, f, m
            p['flag_score'] = round(score, 3)
            p['nudge'] = round(-CAP * score, 2)                  # strong -> negative -> up

    # market rank by ADP (cross-position); the nudge is then applied in RANK-SPOT space, so a
    # player moves at most ~CAP spots -- ADP is compressed at the tail, so nudging ADP-points there
    # would leapfrog dozens of players. Spot-space keeps it "a few spots" everywhere.
    for i, p in enumerate(sorted(players, key=lambda z: z['adp']), 1):
        p['mkt_rank'] = i
    for p in players:
        p['adj_order'] = p['mkt_rank'] + p['nudge']
    for i, p in enumerate(sorted(players, key=lambda z: z['adj_order']), 1):
        p['adj_rank'] = i
    for grp in by_pos.values():
        for i, p in enumerate(sorted(grp, key=lambda z: z['adj_order']), 1):
            p['adj_pos_rank'] = i
    for p in players:
        p['delta'] = p['mkt_rank'] - p['adj_rank']              # +ve = moved UP vs market

    out = {p['key']: {k: p[k] for k in (
        'name', 'pos', 'team', 'adp', 'boom', 'n_flags', 'pmq',
        'boom_pctl', 'flags_pctl', 'pmq_pctl', 'flag_score', 'nudge',
        'adj_order', 'mkt_rank', 'adj_rank', 'adj_pos_rank', 'delta', 'top_flags')}
        for p in players}
    meta = {'n_players': len(players), 'cap_spots': CAP,
            'weights': {'boom': W_BOOM, 'flags': W_FLAGS, 'playoff_mq': W_PMQ},
            'note': 'ADP-anchored flag nudge; bounded +/-CAP spots off market ADP. Separate layer from fusion consensus.'}
    core.safe_json_dump({'_meta': meta, 'players': out}, os.path.join(HERE, 'flag_ranks.json'), indent=1)

    movers = sorted(players, key=lambda z: z['delta'])
    print(f"flag_ranks.json: {len(players)} players | CAP +/-{CAP:.0f} spots")
    print("\nBIGGEST RISERS (flags say earlier than market):")
    for p in sorted(players, key=lambda z: -z['delta'])[:10]:
        print(f"  +{p['delta']:>2}  {p['name']:<22} {p['pos']} mkt#{p['mkt_rank']:>3} -> #{p['adj_rank']:<3} "
              f"(boom {p['boom_pctl']:.0f} / flags {p['flags_pctl']:.0f} / pmq {p['pmq_pctl']:.0f})")
    print("\nBIGGEST FADERS (flags say later than market):")
    for p in movers[:10]:
        print(f"  {p['delta']:>3}  {p['name']:<22} {p['pos']} mkt#{p['mkt_rank']:>3} -> #{p['adj_rank']:<3} "
              f"(boom {p['boom_pctl']:.0f} / flags {p['flags_pctl']:.0f} / pmq {p['pmq_pctl']:.0f})")


if __name__ == '__main__':
    build()
