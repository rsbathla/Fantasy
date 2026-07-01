#!/usr/bin/env python3
"""Flag-informed, ADP-anchored rank nudge -- FORWARD-LOOKING.

Drafting is a forecast of the UPCOMING season, so this scores 2026-facing signals, not a player's
backward-looking historical boom rate (which is stale for anyone who changed teams -- e.g. Kenneth
Walker III -> KC -- and barely persists year-to-year anyway). It is still a BOUNDED nudge on top of
market ADP (the "ADP-anchored" choice), and still a SEPARATE layer from the fusion consensus.

Per player, within his own position, three forward/portable components:
  1. 2026 projected CEILING (p95)  -- the upside best ball pays for. Forward. From the engine board,
       which recovers first-name variants via canon() (so movers like "Ken Walker III" join). Falls
       back to the 2026 mean projection where a p95 isn't modeled, so coverage is complete.
  2. Skill-flag breadth            -- portable TRAITS (route/sep/YAC/man-zone), which carry across
       teams, from the charting flag files. This is the flag work, minus the backward boom rate.
  3. 2026 playoff-week matchup     -- mean weeks-15/16/17 matchup grade (fantasy playoffs). Forward.
Each -> within-position percentile -> centered to [-1,1]. Weighted blend (reweighted over whatever
is present) = flag_score in ~[-1,1]. nudge = -CAP*flag_score (strong -> earlier). CAP caps the move.
"""
import sys, os, json, statistics
HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (os.path.join(HERE, 'pipeline'), os.path.join(HERE, 'engine'), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import core
import bbengine as bb

CAP = 8.0                          # max spots off market rank (conservative / ADP-anchored)
W_CEIL, W_TRAIT, W_MATCH = 0.50, 0.25, 0.25
PLAYOFF_WEEKS = {15, 16, 17}


def forward_signals():
    """key -> {pos, adp, name, team, ceil, proj} from the engine board (canon name recovery + full
    projection coverage). `ceil` is the 2026 p95 ceiling; None where only a mean projection exists."""
    out = {}
    for p in bb.load_board():
        if p.get('adp') is None:
            continue
        out[core.fn(p['name'])] = {
            'pos': p['pos'], 'adp': float(p['adp']), 'name': p['name'], 'team': p.get('team'),
            'ceil': p.get('ceiling_p95'), 'proj': p.get('proj'),
        }
    return out


def flag_traits():
    """key -> {n_flags, pmq, top_flags} from the charting flag files (traits + 2026 playoff matchup)."""
    out = {}
    for pos in ('QB', 'RB', 'WR', 'TE'):
        path = os.path.join(HERE, 'boom', f'flags_{pos}.json')
        if not os.path.exists(path):
            continue
        for k, r in json.load(open(path, encoding='utf-8')).items():
            wks = r.get('weeks') or []
            ps = [w.get('p') for w in wks if isinstance(w, dict) and w.get('wk') in PLAYOFF_WEEKS and w.get('p') is not None]
            out[core.fn(r.get('name', k))] = {
                'n_flags': len(r.get('skill_flags') or []),
                'pmq': statistics.mean(ps) if ps else None,
                'top_flags': [f.get('f') for f in (r.get('skill_flags') or [])[:4] if f.get('f')],
            }
    return out


def _pctl(vals, x):
    xs = [v for v in vals if v is not None]
    if x is None or len(xs) < 2:
        return None
    return round(100.0 * sum(1 for y in xs if y < x) / len(xs), 1)


def build():
    fwd = forward_signals()
    tr = flag_traits()
    players = []
    for key, t in tr.items():
        f = fwd.get(key)
        if not f:
            continue                     # not draftable / no forward line -> not on the board
        players.append({'key': key, 'name': f['name'], 'pos': f['pos'], 'team': f['team'],
                        'adp': f['adp'], 'ceil': f['ceil'], 'proj': f['proj'],
                        'n_flags': t['n_flags'], 'pmq': t['pmq'], 'top_flags': t['top_flags']})

    by_pos = {}
    for p in players:
        by_pos.setdefault(p['pos'], []).append(p)
    for pos, grp in by_pos.items():
        ceils = [p['ceil'] for p in grp]
        projs = [p['proj'] for p in grp]
        nflg = [p['n_flags'] for p in grp]
        pmqs = [p['pmq'] for p in grp]
        for p in grp:
            # forward UPSIDE percentile: p95 ceiling where modeled, else the mean-projection percentile
            up = _pctl(ceils, p['ceil']) if p['ceil'] is not None else _pctl(projs, p['proj'])
            tp = _pctl(nflg, p['n_flags'])
            mp = _pctl(pmqs, p['pmq'])
            comps = []
            if up is not None:
                comps.append((W_CEIL, (up - 50) / 50.0))
            if tp is not None:
                comps.append((W_TRAIT, (tp - 50) / 50.0))
            if mp is not None:
                comps.append((W_MATCH, (mp - 50) / 50.0))
            wsum = sum(w for w, _ in comps) or 1.0
            score = sum(w * c for w, c in comps) / wsum      # reweighted over present components
            p['ceil_pctl'], p['trait_pctl'], p['pmq_pctl'] = up, tp, mp
            p['flag_score'] = round(score, 3)
            p['nudge'] = round(-CAP * score, 2)

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
        p['delta'] = p['mkt_rank'] - p['adj_rank']

    out = {p['key']: {k: p[k] for k in (
        'name', 'pos', 'team', 'adp', 'ceil', 'n_flags', 'pmq',
        'ceil_pctl', 'trait_pctl', 'pmq_pctl', 'flag_score', 'nudge',
        'adj_order', 'mkt_rank', 'adj_rank', 'adj_pos_rank', 'delta', 'top_flags')}
        for p in players}
    meta = {'n_players': len(players), 'cap_spots': CAP,
            'weights': {'ceiling': W_CEIL, 'traits': W_TRAIT, 'playoff_mq': W_MATCH},
            'note': 'Forward-looking ADP-anchored nudge: 2026 p95 ceiling + portable traits + 2026 '
                    'playoff matchup. No backward boom rate. Bounded +/-CAP spots off market ADP.'}
    core.safe_json_dump({'_meta': meta, 'players': out}, os.path.join(HERE, 'flag_ranks.json'), indent=1)

    print(f"flag_ranks.json: {len(players)} players | FORWARD (ceil {int(W_CEIL*100)}/traits "
          f"{int(W_TRAIT*100)}/playoff {int(W_MATCH*100)}) | CAP +/-{CAP:.0f}")
    print("\nBIGGEST RISERS (2026 upside says earlier than market):")
    for p in sorted(players, key=lambda z: -z['delta'])[:10]:
        print(f"  +{p['delta']:>2}  {p['name']:<22} {p['pos']} mkt#{p['mkt_rank']:>3} -> #{p['adj_rank']:<3} "
              f"(ceil {p['ceil_pctl']:.0f} / traits {p['trait_pctl']:.0f} / pmq {p['pmq_pctl'] if p['pmq_pctl'] is not None else '-'})")
    print("\nBIGGEST FADERS (2026 upside says later than market):")
    for p in sorted(players, key=lambda z: z['delta'])[:10]:
        print(f"  {p['delta']:>3}  {p['name']:<22} {p['pos']} mkt#{p['mkt_rank']:>3} -> #{p['adj_rank']:<3} "
              f"(ceil {p['ceil_pctl']:.0f} / traits {p['trait_pctl']:.0f} / pmq {p['pmq_pctl'] if p['pmq_pctl'] is not None else '-'})")


if __name__ == '__main__':
    build()
