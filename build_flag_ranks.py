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
# Weights rebalanced 2026-07-02 (was 0.50/0.25/0.25). The p95-ceiling percentile is r=0.87 with
# market rank (alone it re-derives R2=0.78 of positional ADP order; only ~22% of its variance is
# market-orthogonal), so at 0.50 half the composite just restated ADP and the deltas collapsed
# (mean |delta| 1.4, max 6, nobody near the cap). Traits/season-matchup are ~62% market-orthogonal
# (r ~ -0.60). 0.30/0.35/0.35 lets the divergent signals carry the composite's non-market content
# while ceiling still anchors, and the movers stay football-defensible; trait weights >=0.40 start
# fading year-2 breakout WRs on rookie-year charting, and a 2025 point-in-time backtest (2025 ADP +
# 2024-only charting vs realized 2025 boom rate) showed no component beats the market by enough to
# earn dominance, so the two orthogonal signals are weighted symmetrically. Revert = 0.50/0.25/0.25.
W_CEIL, W_TRAIT, W_MATCH = 0.30, 0.35, 0.35
# Best Ball Mania has TWO gates: weeks 1-14 you must finish top-2 of 12 to ADVANCE, then weeks 15-17
# are elimination weeks you must spike to WIN. The matchup term therefore spans the WHOLE season
# (a rough weeks-1-14 schedule can end your season before the playoffs ever matter), with the
# do-or-die playoff weeks tilted heavier per-week. (wk18 is unused in Best Ball Mania.)
REGULAR_WEEKS = set(range(1, 15))   # 1-14: accumulate to advance
PLAYOFF_WEEKS = {15, 16, 17}        # 15-17: elimination weeks to win
PLAYOFF_TILT = 1.5                  # each playoff week counts 1.5x a regular-season week in the season matchup
# --- SCHEME-FIT lever (added 2026-07-02): coverage-specialist skill x 2026 opponent coverage ---
# boom/scheme_fit.json 'season' (build_scheme_fit.py: differential coverage skill x how far the 2026
# slate tilts toward it, playoff-tilted like smq) nudges the season-matchup PERCENTILE before it
# enters the composite. BOUNDED: linear at SF_SCALE pctl-points per unit fit, hard-capped at
# +/-SF_PCTL_CAP pctl (typ. season fit |0.01| -> ~3 pctl; pool max ~0.035 -> capped ~10-12). It can
# tilt the matchup grade for a genuine specialist, never swamp the schedule grade (raw smq_pctl kept
# alongside for transparency). Revert = set SF_SCALE to 0.
SF_PCTL_CAP = 12.0
SF_SCALE = 300.0


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
            reg = [w.get('p') for w in wks if isinstance(w, dict) and w.get('wk') in REGULAR_WEEKS and w.get('p') is not None]
            pl  = [w.get('p') for w in wks if isinstance(w, dict) and w.get('wk') in PLAYOFF_WEEKS and w.get('p') is not None]
            rmq = statistics.mean(reg) if reg else None            # weeks 1-14 (advance)
            pmq = statistics.mean(pl) if pl else None              # weeks 15-17 (win)
            # season matchup = whole-schedule mean, playoff weeks tilted heavier per-week
            _num = sum(reg) + PLAYOFF_TILT * sum(pl)
            _den = len(reg) + PLAYOFF_TILT * len(pl)
            smq = (_num / _den) if _den else (pmq if pmq is not None else rmq)
            out[core.fn(r.get('name', k))] = {
                'n_flags': len(r.get('skill_flags') or []),
                'rmq': rmq, 'pmq': pmq, 'smq': smq,
                'top_flags': [f.get('f') for f in (r.get('skill_flags') or [])[:4] if f.get('f')],
            }
    return out


def _pctl(vals, x):
    xs = [v for v in vals if v is not None]
    if x is None or len(xs) < 2:
        return None
    return round(100.0 * sum(1 for y in xs if y < x) / len(xs), 1)


def scheme_fit():
    """key -> season scheme-fit (boom/scheme_fit.json); {} when the artifact is absent."""
    path = os.path.join(HERE, 'boom', 'scheme_fit.json')
    if not os.path.exists(path):
        return {}
    return {k: v.get('season') for k, v in
            (json.load(open(path, encoding='utf-8')).get('players') or {}).items()}


def build():
    fwd = forward_signals()
    tr = flag_traits()
    sf = scheme_fit()
    players = []
    for key, t in tr.items():
        f = fwd.get(key)
        if not f:
            continue                     # not draftable / no forward line -> not on the board
        players.append({'key': key, 'name': f['name'], 'pos': f['pos'], 'team': f['team'],
                        'adp': f['adp'], 'ceil': f['ceil'], 'proj': f['proj'],
                        'n_flags': t['n_flags'], 'rmq': t['rmq'], 'pmq': t['pmq'], 'smq': t['smq'],
                        'top_flags': t['top_flags']})

    by_pos = {}
    for p in players:
        by_pos.setdefault(p['pos'], []).append(p)
    for pos, grp in by_pos.items():
        ceils = [p['ceil'] for p in grp]
        projs = [p['proj'] for p in grp]
        nflg = [p['n_flags'] for p in grp]
        smqs = [p['smq'] for p in grp]
        rmqs = [p['rmq'] for p in grp]
        pmqs = [p['pmq'] for p in grp]
        for p in grp:
            # forward UPSIDE percentile: p95 ceiling where modeled, else the mean-projection percentile
            up = _pctl(ceils, p['ceil']) if p['ceil'] is not None else _pctl(projs, p['proj'])
            tp = _pctl(nflg, p['n_flags'])
            mp = _pctl(smqs, p['smq'])          # matchup component now = full-season (advance + win)
            # scheme-fit lever: bounded nudge on the season-matchup percentile (see SF_* constants)
            sfv = sf.get(p['key'])
            sf_adj = max(-SF_PCTL_CAP, min(SF_PCTL_CAP, sfv * SF_SCALE)) if sfv is not None else 0.0
            mp_eff = max(0.0, min(100.0, mp + sf_adj)) if mp is not None else None
            comps = []
            if up is not None:
                comps.append((W_CEIL, (up - 50) / 50.0))
            if tp is not None:
                comps.append((W_TRAIT, (tp - 50) / 50.0))
            if mp_eff is not None:
                comps.append((W_MATCH, (mp_eff - 50) / 50.0))
            wsum = sum(w for w, _ in comps) or 1.0
            score = sum(w * c for w, c in comps) / wsum      # reweighted over present components
            # keep reg-season + playoff percentiles alongside the season matchup for transparency
            p['ceil_pctl'], p['trait_pctl'] = up, tp
            p['smq_pctl'], p['rmq_pctl'], p['pmq_pctl'] = mp, _pctl(rmqs, p['rmq']), _pctl(pmqs, p['pmq'])
            p['scheme_fit'] = sfv
            p['sf_adj'] = round(sf_adj, 1)
            p['smq_pctl_adj'] = round(mp_eff, 1) if mp_eff is not None else None
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
        'name', 'pos', 'team', 'adp', 'ceil', 'n_flags', 'rmq', 'pmq', 'smq',
        'ceil_pctl', 'trait_pctl', 'smq_pctl', 'rmq_pctl', 'pmq_pctl',
        'scheme_fit', 'sf_adj', 'smq_pctl_adj', 'flag_score', 'nudge',
        'adj_order', 'mkt_rank', 'adj_rank', 'adj_pos_rank', 'delta', 'top_flags')}
        for p in players}
    meta = {'n_players': len(players), 'cap_spots': CAP,
            'weights': {'ceiling': W_CEIL, 'traits': W_TRAIT, 'season_mq': W_MATCH},
            'matchup': {'regular_weeks': '1-14 (advance: top-2 of 12)', 'playoff_weeks': '15-17 (win)',
                        'playoff_tilt': PLAYOFF_TILT,
                        'note': 'matchup component = full-season schedule mean with playoff weeks tilted %.1fx; '
                                'rmq/pmq kept separately for transparency' % PLAYOFF_TILT},
            'scheme_fit': {'scale_pctl_per_fit': SF_SCALE, 'cap_pctl': SF_PCTL_CAP,
                           'note': 'season matchup pctl nudged by boom/scheme_fit.json season fit '
                                   '(coverage-specialist x 2026 opponent coverage tendency), '
                                   'capped +/-%.0f pctl; raw smq_pctl kept; revert = SF_SCALE 0' % SF_PCTL_CAP},
            'note': 'Forward-looking ADP-anchored nudge: 2026 p95 ceiling + portable traits + 2026 '
                    'SEASON matchup (weeks 1-14 advance + 15-17 win, playoff-tilted). No backward boom '
                    'rate. Bounded +/-CAP spots off market ADP.'}
    core.safe_json_dump({'_meta': meta, 'players': out}, os.path.join(HERE, 'flag_ranks.json'), indent=1)

    print(f"flag_ranks.json: {len(players)} players | FORWARD (ceil {int(W_CEIL*100)}/traits "
          f"{int(W_TRAIT*100)}/season-mq {int(W_MATCH*100)}, playoff-tilt {PLAYOFF_TILT}) | CAP +/-{CAP:.0f}")
    print("\nBIGGEST RISERS (2026 upside says earlier than market):")
    for p in sorted(players, key=lambda z: -z['delta'])[:10]:
        print(f"  +{p['delta']:>2}  {p['name']:<22} {p['pos']} mkt#{p['mkt_rank']:>3} -> #{p['adj_rank']:<3} "
              f"(ceil {p['ceil_pctl']:.0f} / traits {p['trait_pctl']:.0f} / smq {p['smq_pctl'] if p['smq_pctl'] is not None else '-'})")
    print("\nBIGGEST FADERS (2026 upside says later than market):")
    for p in sorted(players, key=lambda z: z['delta'])[:10]:
        print(f"  {p['delta']:>3}  {p['name']:<22} {p['pos']} mkt#{p['mkt_rank']:>3} -> #{p['adj_rank']:<3} "
              f"(ceil {p['ceil_pctl']:.0f} / traits {p['trait_pctl']:.0f} / smq {p['smq_pctl'] if p['smq_pctl'] is not None else '-'})")


if __name__ == '__main__':
    build()
