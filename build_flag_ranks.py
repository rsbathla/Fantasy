#!/usr/bin/env python3
"""Flag-informed, ADP-anchored rank nudge -- FORWARD-LOOKING.

Drafting is a forecast of the UPCOMING season, so this scores 2026-facing signals, not a player's
backward-looking historical boom rate (which is stale for anyone who changed teams -- e.g. Kenneth
Walker III -> KC -- and barely persists year-to-year anyway). It is still a BOUNDED nudge on top of
market ADP (the "ADP-anchored" choice), and still a SEPARATE layer from the fusion consensus.

Per player, within his own position, three forward/portable components (+ one RB-only term):
  1. 2026 projected CEILING (p95)  -- the upside best ball pays for. Forward. From the engine board,
       which recovers first-name variants via canon() (so movers like "Ken Walker III" join). Falls
       back to the 2026 mean projection where a p95 isn't modeled, so coverage is complete.
  2. Skill-flag breadth            -- portable TRAITS (route/sep/YAC/man-zone), which carry across
       teams, from the charting flag files. This is the flag work, minus the backward boom rate.
       KEPT as a COUNT: the 2025 point-in-time backtest (backtest_composite_2025.py) found the
       count is the stronger market-orthogonal predictor (WR partial rho +0.21, perm p=.013,
       LOO-stable) vs a graded coverage-YPRR + NFL-Pro-EPA skill blend (-0.05, ns).
  3. 2026 playoff-week matchup     -- mean weeks-15/16/17 matchup grade (fantasy playoffs). Forward.
  4. OPPORTUNITY (RB only)         -- prior-season (2025) carry+target share. The one candidate that
       cleanly beat the market out-of-sample in the 2025 point-in-time backtest (see W_OPP note).
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
PLAYOFF_TILT = 1.5                  # ('flat' mode) each playoff week counts 1.5x a regular-season week
# Season-matchup WEEK WEIGHTS (proposal 2026-07-02): value the schedule the way BBMania PAYS OUT.
# Playoffs (W15-17) = 60% of the matchup term vs regular season (W1-14) = 40%; and within the 60 the
# CHAMPIONSHIP week 17 takes 30 (half), W15/W16 15 each. Rationale: the tournament is won in the W17
# final, so a strong W17 matchup is worth ~10x a single regular-season week. TRADE-OFF: concentrates
# the term on one far-out, single-opponent week -> noisier than the flat tilt, and leans harder on
# W17 opponent-defense projections that can drift by December. REVERT = MATCHUP_WEEK_MODE = 'flat'.
MATCHUP_WEEK_MODE = 'bbmania'                       # 'bbmania' = 40/60 with W17 heavy | 'flat' = PLAYOFF_TILT
REG_TOTAL = 40.0                                    # total weight spread across weeks 1-14 (2.86 each)
PLAYOFF_WEEK_W = {15: 15.0, 16: 15.0, 17: 30.0}     # sums to 60 (W17 = half the playoff weight)
def _wk_weight(wk):
    if MATCHUP_WEEK_MODE == 'flat':
        return PLAYOFF_TILT if wk in PLAYOFF_WEEKS else (1.0 if wk in REGULAR_WEEKS else 0.0)
    if wk in PLAYOFF_WEEK_W:
        return PLAYOFF_WEEK_W[wk]
    return REG_TOTAL / 14.0 if wk in REGULAR_WEEKS else 0.0
# --- SCHEME-FIT lever (added 2026-07-02): coverage-specialist skill x 2026 opponent coverage ---
# boom/scheme_fit.json 'season' (build_scheme_fit.py: differential coverage skill x how far the 2026
# slate tilts toward it, playoff-tilted like smq) nudges the season-matchup PERCENTILE before it
# enters the composite. BOUNDED: linear at SF_SCALE pctl-points per unit fit, hard-capped at
# +/-SF_PCTL_CAP pctl (typ. season fit |0.01| -> ~3 pctl; pool max ~0.035 -> capped ~10-12). It can
# tilt the matchup grade for a genuine specialist, never swamp the schedule grade (raw smq_pctl kept
# alongside for transparency). Revert = set SF_SCALE to 0.
SF_PCTL_CAP = 12.0
SF_SCALE = 300.0
# --- OPPORTUNITY term (added 2026-07-02, backtest-derived; see backtest_composite_2025.py) ---
# Point-in-time 2025 test (2024-only predictors + 2025 preseason FP ADP vs realized 2025 spike
# counts / boom rate): RB prior-season volume share (carry+tgt share) was the ONLY candidate to
# clear the market-orthogonal OUT-OF-SAMPLE bar: OOS delta rho +0.030 with 77% of 200 split-halves
# positive; ADP-partialed rho 0.29 (perm p=.016; boom-rate outcome 0.24, p=.076). FRAGILE at n=50:
# leave-one-out (Brian Robinson) drops it to 0.19 (p=.10) and the bootstrap 90% CI [-0.04,0.53]
# crosses 0 -> weighted 0.20, NOT the in-sample optimum (~0.4), and the CAP still bounds the move.
# WR/TE opportunity showed no earn (partial .075/.11, ns); QB pressure slate, RZ equity, and the
# graded cov/EPA skill blend all failed the same bar -> those stay dossier-only. The same backtest
# DEMOTED the RB trait count (2024-only proxy partial -0.22) -> W_TRAIT_POS shifts RB weight from
# traits to opportunity. Source: features.json carry_share/tgt_share (2025 season = prior year,
# the exact tested form; rookies lack it and reweight over the other terms, so no rookie penalty).
# REVERT = set W_OPP = {} and W_TRAIT_POS = {} (restores the pure 3-term 0.30/0.35/0.35 blend).
W_OPP = {'RB': 0.20}                # per-position opportunity weight; positions absent get 0
W_TRAIT_POS = {'RB': 0.15}          # per-position trait override; positions absent keep W_TRAIT


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
            wkp = [(w.get('wk'), w.get('p')) for w in wks
                   if isinstance(w, dict) and w.get('p') is not None and w.get('wk') is not None]
            reg = [p for wk, p in wkp if wk in REGULAR_WEEKS]
            pl  = [p for wk, p in wkp if wk in PLAYOFF_WEEKS]
            rmq = statistics.mean(reg) if reg else None            # weeks 1-14 (advance)
            pmq = statistics.mean(pl) if pl else None              # weeks 15-17 (win)
            # season matchup = per-week WEIGHTED mean over available weeks (see MATCHUP_WEEK_MODE:
            # bbmania -> playoffs 60% / reg 40%, W17 = 30; flat -> the old 1.5x playoff tilt)
            _num = sum(p * _wk_weight(wk) for wk, p in wkp)
            _den = sum(_wk_weight(wk) for wk, p in wkp)
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


def opportunity_shares():
    """key -> {car_sh, tgt_sh} prior-season (2025) volume shares from features.json — the exact
    form validated by backtest_composite_2025.py. {} when the artifact is absent (term abstains)."""
    path = os.path.join(HERE, 'features.json')
    if not os.path.exists(path):
        return {}
    def _num(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return None
    out = {}
    for p in json.load(open(path, encoding='utf-8')).get('players') or []:
        cs, ts = _num(p.get('carry_share')), _num(p.get('tgt_share'))
        if cs is not None or ts is not None:
            out[core.fn(p['name'])] = {'car_sh': cs, 'tgt_sh': ts}
    return out


def build():
    fwd = forward_signals()
    tr = flag_traits()
    sf = scheme_fit()
    opp = opportunity_shares()
    players = []
    for key, t in tr.items():
        f = fwd.get(key)
        if not f:
            continue                     # not draftable / no forward line -> not on the board
        o = opp.get(key) or {}
        players.append({'key': key, 'name': f['name'], 'pos': f['pos'], 'team': f['team'],
                        'adp': f['adp'], 'ceil': f['ceil'], 'proj': f['proj'],
                        'n_flags': t['n_flags'], 'rmq': t['rmq'], 'pmq': t['pmq'], 'smq': t['smq'],
                        'car_sh': o.get('car_sh'), 'tgt_sh': o.get('tgt_sh'),
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
        cars = [p['car_sh'] for p in grp]
        tgts = [p['tgt_sh'] for p in grp]
        w_opp = W_OPP.get(pos, 0.0)
        w_trait = W_TRAIT_POS.get(pos, W_TRAIT)
        for p in grp:
            # forward UPSIDE percentile: p95 ceiling where modeled, else the mean-projection percentile
            up = _pctl(ceils, p['ceil']) if p['ceil'] is not None else _pctl(projs, p['proj'])
            tp = _pctl(nflg, p['n_flags'])
            mp = _pctl(smqs, p['smq'])          # matchup component now = full-season (advance + win)
            # scheme-fit lever: bounded nudge on the season-matchup percentile (see SF_* constants)
            sfv = sf.get(p['key'])
            sf_adj = max(-SF_PCTL_CAP, min(SF_PCTL_CAP, sfv * SF_SCALE)) if sfv is not None else 0.0
            mp_eff = max(0.0, min(100.0, mp + sf_adj)) if mp is not None else None
            # opportunity percentile (backtest form: mean of within-pos carry-share + tgt-share pctls)
            op = None
            if w_opp > 0:
                op_parts = [x for x in (_pctl(cars, p['car_sh']), _pctl(tgts, p['tgt_sh'])) if x is not None]
                op = sum(op_parts) / len(op_parts) if op_parts else None
            comps = []
            if up is not None:
                comps.append((W_CEIL, (up - 50) / 50.0))
            if tp is not None:
                comps.append((w_trait, (tp - 50) / 50.0))
            if mp_eff is not None:
                comps.append((W_MATCH, (mp_eff - 50) / 50.0))
            if op is not None and w_opp > 0:
                comps.append((w_opp, (op - 50) / 50.0))
            wsum = sum(w for w, _ in comps) or 1.0
            score = sum(w * c for w, c in comps) / wsum      # reweighted over present components
            # keep reg-season + playoff percentiles alongside the season matchup for transparency
            p['ceil_pctl'], p['trait_pctl'] = up, tp
            p['smq_pctl'], p['rmq_pctl'], p['pmq_pctl'] = mp, _pctl(rmqs, p['rmq']), _pctl(pmqs, p['pmq'])
            p['scheme_fit'] = sfv
            p['sf_adj'] = round(sf_adj, 1)
            p['smq_pctl_adj'] = round(mp_eff, 1) if mp_eff is not None else None
            p['opp_pctl'] = round(op, 1) if op is not None else None
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
        'scheme_fit', 'sf_adj', 'smq_pctl_adj', 'car_sh', 'tgt_sh', 'opp_pctl',
        'flag_score', 'nudge',
        'adj_order', 'mkt_rank', 'adj_rank', 'adj_pos_rank', 'delta', 'top_flags')}
        for p in players}
    meta = {'n_players': len(players), 'cap_spots': CAP,
            'weights': {'ceiling': W_CEIL, 'traits': W_TRAIT, 'season_mq': W_MATCH},
            'weights_pos_overrides': {'traits': W_TRAIT_POS, 'opportunity': W_OPP},
            'opportunity': {'weights': W_OPP,
                            'note': 'RB-only prior-season (2025) carry+tgt share pctl '
                                    '(features.json). Earned via backtest_composite_2025.py: only '
                                    'candidate with positive OOS market-orthogonal lift (+0.030 '
                                    'rho, 77% split-halves; partial 0.29 p=.016; FRAGILE n=50). '
                                    'Revert = W_OPP {} + W_TRAIT_POS {}.'},
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
                    'rate. Bounded +/-CAP spots off market ADP.',
            'surfaces': ['predraft', 'rankings']}
    core.safe_json_dump({'_meta': meta, 'players': out}, os.path.join(HERE, 'flag_ranks.json'), indent=1)

    print(f"flag_ranks.json: {len(players)} players | FORWARD (ceil {int(W_CEIL*100)}/traits "
          f"{int(W_TRAIT*100)}/season-mq {int(W_MATCH*100)}, playoff-tilt {PLAYOFF_TILT}) | CAP +/-{CAP:.0f}"
          + (f" | RB 4-term: traits {int(W_TRAIT_POS.get('RB', W_TRAIT)*100)} + opp {int(W_OPP.get('RB',0)*100)}"
             if W_OPP else ""))
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
