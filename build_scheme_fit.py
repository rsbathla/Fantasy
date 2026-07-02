#!/usr/bin/env python3
"""SCHEME-FIT lever: coverage-SPECIALIST skill x 2026 OPPONENT coverage tendency -> boom/scheme_fit.json.

Turns boom/coverage_route_spec.json (per-WR/TE within-position YPRR percentiles vs each coverage,
2024+2025 FantasyPoints charting) into a weekly/season MATCHUP signal against each player's actual
2026 schedule (moves-aware: the player's 2026 team comes from the flags files / board, NOT his
charting team, so e.g. traded players are scored against their NEW schedule).

DEFENSE SIDE -- rebuilt fresh from the raw FP_SWEEP per-team coverage-usage sweeps (2024 + 2025),
NOT from boom/defense_shell.json: that file is a frozen single-season 2025 artifact (its source
qbCoverageMatchupExport.csv is gone; build_defense_shell.py just keeps the old JSON). Verified the
shell's rates == the 2025 FP_SWEEP rates exactly, so this is the same source, two years deep.
  rate(team, scheme) = defensive pass snaps in that scheme / all coverage-classified snaps, per year,
  blended 2/3 * 2025 + 1/3 * 2024 (scheme identity is coach-driven -> recent year dominates).
  NEW-DC 2026 teams: projected from the COORDINATOR layer (coordinator_scheme_2026.json +
  coordinator_changes_2026.json), NOT blanket-regressed. Per team:
    man/zone: a researched DC prior (conf 'blend-prior' / dc_prior_man_rate) is lambda-blended into the
      team's man rate -- ported LEAGUE-RELATIVELY, because the registry's frozen def_man_rate scale
      shares nominal units but not per-team levels with FP_SWEEP (lg 17.5 vs 26.8, Pearson r ~ -0.17).
      conf 'regress-mean' (DC tendency genuinely unknown): mirror the registry's own lambda regression
      of man_rate_adj on this table's scale. zone = 100 - man (exact complement of the 7 schemes).
    single/two-high: sourced dc_scheme prose is parsed for a shell lean ("Cover-3"/single-high vs
      "two-high"/split-field/quarters) and the leaned bucket moves halfway toward league mean + 1 sd
      (build_lever_count's shell-dial convention), pair sum preserved. blend-prior DCs with no shell
      claim keep their 2yr shell (trust the research, do NOT regress); regress-mean DCs with no claim
      get a LIGHT (30%) shell regression. Blanket 50% shrink survives ONLY as the no-data fallback.

BUCKETS (specialist cell -> defense tendency), as two complementary partitions of the same snaps:
  shell: single-high = Cover 1 + Cover 3      | two-high = Cover 2 + Cover 4 + Cover 6 + Man-Cover-2
  style: man         = Cover 0 + Cover 1 + MC2 | zone     = Cover 2 + Cover 3 + Cover 4 + Cover 6
Player bucket skill = route-weighted mean of his within-position percentiles over the QUALIFIED
(>= 25 routes) component schemes; shell buckets need >= MIN_BUCKET_RTE total, man/zone use the spec's
MAN/ZONE rollup percentile (>= MIN_ROLLUP_RTE routes). No adequate sample -> bucket skipped (no fit).

WEEKLY FIT (bounded lever, zero-sum-ish by construction):
  fit_wk = sum over adequate buckets of [(pctl-50)/50] * [(opp_rate - league_rate)/100], clamped to
  +/-WEEK_CAP. A partition (shell or style) only enters when BOTH of its complementary buckets have
  adequate sample: the two deviations are near-mirror images (man+zone=100), so a complete pair is a
  true DIFFERENTIAL (his man-vs-zone edge x the defense's man-vs-zone tilt), while a lone bucket
  would "reward" a thin-sample player whenever the schedule merely avoids his one charted weakness.
  A player equally good vs both sides nets ~0 -- only differential skill meeting a tendency-heavy
  defense moves it. Season aggregate uses the model's Best Ball Mania split: weeks 1-14 advance +
  weeks 15-17 win, playoff weeks tilted 1.5x (same as build_flag_ranks).

Consumed by build_flag_ranks.py (bounded season-matchup nudge) and build_dossier.py (SCHEME FIT card).
"""
import csv, json, os, statistics, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import core

SEASONS = (2024, 2025)
YEAR_W = {2025: 2/3, 2024: 1/3}      # blend: recent scheme identity dominates
WEEK_CAP = 0.35                      # per-week fit bound (sane range; realistic |fit| ~ 0.15)
# ---- new-DC 2026 handling (coordinator-aware; see defense_rates) ----
FALLBACK_SHRINK = 0.5                # blanket 50%-to-mean shrink: ONLY when the coordinator layer has no numbers
SHELL_SHRINK_UNKNOWN = 0.30          # LIGHT shell regression: conf 'regress-mean' + no sourced shell identity
SHELL_NUDGE_W = 0.5                  # dc_scheme shell lean: move halfway toward lg mean + 1 sd (lever_count conv.)
MAN_MAX_SHIFT = 10.0                 # bound: coordinator man projection moves a team's man bucket <= this many pts
MIN_BUCKET_RTE = 40                  # min qualified routes across a shell bucket's component schemes
MIN_ROLLUP_RTE = 60                  # min routes on the MAN/ZONE rollup cells
PLAYOFF_TILT = 1.5                   # weeks 15-17 weight in the season number (== build_flag_ranks)
REGULAR_WEEKS = set(range(1, 15)); PLAYOFF_WEEKS = {15, 16, 17}

FP_SCHEMES = ['Cover 0', 'Cover 1', 'Cover 2', 'Cover 2 Man', 'Cover 3', 'Cover 4', 'Cover 6']
# defense buckets from per-scheme rates
DEF_BUCKET = {
    'single_high': ['Cover 1', 'Cover 3'],
    'two_high':    ['Cover 2', 'Cover 4', 'Cover 6', 'Cover 2 Man'],
    'man':         ['Cover 0', 'Cover 1', 'Cover 2 Man'],
    'zone':        ['Cover 2', 'Cover 3', 'Cover 4', 'Cover 6'],
}
# player-side component schemes per shell bucket (spec cell names)
PLR_SHELL = {'single_high': ['Cover 1', 'Cover 3'],
             'two_high':    ['Cover 2', 'Cover 4', 'Cover 6', 'Man Cover 2']}
LABEL = {'single_high': 'single-high (C1/C3)', 'two_high': 'two-high (C2/C4/C6/2-man)',
         'man': 'man (C0/C1/2-man)', 'zone': 'zone (C2/C3/C4/C6)'}

# shell-identity keywords in the SOURCED dc_scheme prose (coordinator_changes_2026.json), e.g.
# TEN "heavy Cover-3 ZONE" -> single_high; PIT "two-high split-field" -> two_high; GB "3-safety looks".
SHELL_TOKENS = {
    'single_high': ('single-high', 'single high', 'cover-3', 'cover 3', 'cover-1', 'cover 1',
                    'post-safety', 'mofc'),
    'two_high':    ('two-high', 'two high', 'split-field', 'split field', 'quarters',
                    'cover-2', 'cover 2', 'cover-4', 'cover 4', 'cover-6', 'cover 6',
                    '3-safety', 'three-safety', 'big nickel'),
}


def _shell_lean(prose):
    """dc_scheme prose -> 'single_high' | 'two_high' | None (no shell claim / contradictory)."""
    s = (prose or '').lower()
    hit = {b: any(t in s for t in toks) for b, toks in SHELL_TOKENS.items()}
    if hit['single_high'] == hit['two_high']:
        return None
    return 'single_high' if hit['single_high'] else 'two_high'


def _coordinator_layer():
    """Merge the two coordinator artifacts -> (teams, changes, lambda, man league mean, man league sd).

    coordinator_scheme_2026.json teams[T]: man_rate_2025 / man_rate_adj / conf / dc_new / dc_name
      (meta: lambda + man_league_mean, i.e. the registry's own blend weight and baseline).
    coordinator_changes_2026.json[T]: dc_new / dc_name / dc_prior_man_rate / dc_scheme (sourced prose).
    KEY REPAIR: the frozen registry wrote SF under 'ers' ('49ers' -> norm_team tail), so SF never
    matched its changes-file record and was silently skipped -- repair on read (a real SF key wins)."""
    def load(fn):
        p = os.path.join(HERE, fn)
        return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}
    cs = load('coordinator_scheme_2026.json')
    raw = cs.get('teams') or {}
    teams = {k: v for k, v in raw.items() if isinstance(v, dict) and k != 'ers'}
    if isinstance(raw.get('ers'), dict):
        teams.setdefault('SF', raw['ers'])
    changes = {k: v for k, v in load('coordinator_changes_2026.json').items()
               if isinstance(v, dict) and not k.startswith('_')}
    meta = cs.get('meta') or {}
    lam = float(meta.get('lambda') or 0.5)
    man25 = [v.get('man_rate_2025') for v in teams.values() if v.get('man_rate_2025') is not None]
    c_mean = float(meta.get('man_league_mean') or (statistics.mean(man25) if man25 else 17.5))
    c_sd = statistics.pstdev(man25) if len(man25) > 1 else 0.0
    return teams, changes, lam, c_mean, c_sd


def defense_rates():
    """TEAM -> {bucket: blended 2yr rate %}; plus league means and per-team new-DC provenance."""
    per_year = {}
    for yr in SEASONS:
        snaps = {}
        for s in FP_SCHEMES:
            p = os.path.join(HERE, 'NFL-master', 'FP_SWEEP', str(yr), 'Defense_Receiving',
                             'coverageScheme', f'{s}.csv')
            for r in csv.DictReader(open(p, encoding='utf-8-sig')):
                ab = core.team_abbr(f"{r['teamLocation']} {r['teamNickname']}")
                try: sn = float(r['opponentStatsSnapsOffenseTotal'] or 0)
                except ValueError: sn = 0.0
                snaps.setdefault(ab, {})[s] = snaps.get(ab, {}).get(s, 0.0) + sn
        per_year[yr] = {}
        for ab, d in snaps.items():
            tot = sum(d.values()) or 1.0
            per_year[yr][ab] = {s: 100.0 * d.get(s, 0.0) / tot for s in FP_SCHEMES}
    teams = sorted(set(per_year[2025]) & set(per_year[2024]))
    blended = {}
    for ab in teams:
        blended[ab] = {s: sum(YEAR_W[y] * per_year[y][ab][s] for y in SEASONS) for s in FP_SCHEMES}
    # scheme rates -> bucket rates
    tbl = {ab: {b: round(sum(blended[ab][s] for s in comps), 1) for b, comps in DEF_BUCKET.items()}
           for ab in teams}
    # league means + sds from the RAW 2yr table FIRST -- the overrides below must never move the baseline
    lg = {b: round(statistics.mean(v[b] for v in tbl.values()), 1) for b in DEF_BUCKET}
    sd = {b: statistics.pstdev([v[b] for v in tbl.values()]) for b in DEF_BUCKET}

    # ---- new-DC 2026: coordinator-AWARE projection (replaces the old blanket 50% shrink) ----
    # The layer is consumed, not just its dc_new flag: DCs we actually researched (conf 'blend-prior',
    # sourced dc_scheme prose) get their identity folded in; regression to the mean fires ONLY for
    # genuinely-unknown DCs, and only on the partition(s) we lack signal for.
    coord, changes, lam, c_mean, c_sd = _coordinator_layer()
    applied, warn = {}, []
    for ab in sorted(t for t in tbl
                     if (coord.get(t) or {}).get('dc_new') or (changes.get(t) or {}).get('dc_new')):
        v, e, ch = tbl[ab], coord.get(ab) or {}, changes.get(ab) or {}
        conf = e.get('conf')
        man25, man_adj = e.get('man_rate_2025'), e.get('man_rate_adj')
        prior = ch.get('dc_prior_man_rate')
        if prior is not None:
            conf = 'blend-prior'          # researched prior wins even where the registry drifted (SF/'ers')
        elif conf == 'blend-prior' and man_adj is not None and man25 is not None and e.get('dc_new'):
            prior = (man_adj - (1.0 - lam) * man25) / lam    # invert the registry's own blend
        # cross-check the registry against its published method (man_rate_adj == blend of 2025 + prior)
        if prior is not None and man_adj is not None and man25 is not None and e.get('dc_new') \
                and abs(((1.0 - lam) * man25 + lam * prior) - man_adj) > 0.25:
            warn.append(f"{ab}: man_rate_adj {man_adj} != {1 - lam:.1f}*{man25} + {lam:.1f}*{prior}")
        old_man, old_pair = v['man'], v['single_high'] + v['two_high']   # pair sum = 100 - Cover-0 share
        # -- man/zone partition (exact complements here: the 7 scheme rates sum to 100) --
        # UNITS: the registry's man scale (frozen def_man_rate, lg ~17.5) shares nominal units but NOT
        # per-team levels with this FP_SWEEP table (lg ~26.8, Pearson r ~ -0.17) -- so its numbers are
        # ported league-RELATIVELY (z-score on the registry scale -> this table's scale), never raw.
        if prior is not None:
            tgt = lg['man'] + ((prior - c_mean) / c_sd if c_sd else 0.0) * sd['man']  # DC's own man identity
            new_man = (1.0 - lam) * old_man + lam * tgt                   # the registry's lambda blend
            man_src = 'coord-man'
        elif man_adj is not None:
            # conf 'regress-mean': man_rate_adj IS a lambda regression to the mean -- mirror it on this scale
            new_man = lg['man'] + (1.0 - lam) * (old_man - lg['man'])
            man_src = 'coord-man'
        else:
            new_man = lg['man'] + (1.0 - FALLBACK_SHRINK) * (old_man - lg['man'])     # no data: old behavior
            man_src = 'fallback'
        new_man = max(old_man - MAN_MAX_SHIFT, min(old_man + MAN_MAX_SHIFT, new_man))
        v['man'] = round(max(0.0, min(100.0, new_man)), 1)
        v['zone'] = round(100.0 - v['man'], 1)
        # -- single/two-high partition (pair sum preserved: shell edits never touch the Cover-0 share) --
        lean = _shell_lean(ch.get('dc_scheme'))
        if lean:
            other = 'two_high' if lean == 'single_high' else 'single_high'
            nl = (1.0 - SHELL_NUDGE_W) * v[lean] + SHELL_NUDGE_W * (lg[lean] + sd[lean])
            nl = max(0.0, min(old_pair, nl))
            v[lean], v[other] = round(nl, 1), round(old_pair - nl, 1)
            shell_src = 'scheme-shell'
        elif conf == 'blend-prior':
            shell_src = 'keep'            # researched DC, no shell claim in the prose -> do NOT regress
        else:
            shrink = SHELL_SHRINK_UNKNOWN if (man_adj is not None or man25 is not None) else FALLBACK_SHRINK
            for b in ('single_high', 'two_high'):
                v[b] = round(lg[b] + (1.0 - shrink) * (v[b] - lg[b]), 1)
            shell_src = 'regress-shell'
        mode = ('coord-man+scheme-shell' if (man_src == 'coord-man' and shell_src == 'scheme-shell') else
                'blend-prior' if (conf == 'blend-prior' and shell_src == 'keep') else
                'coord-man+regress-shell' if man_src == 'coord-man' else
                'regress-mean')
        v['new_dc'] = True
        applied[ab] = {'mode': mode, 'dc': e.get('dc_name') or ch.get('dc_name'), 'conf': conf,
                       'shell_lean': lean, 'man': [old_man, v['man']]}
    for w in warn:
        print(f"  [coord-layer drift] {w}")
    return tbl, lg, applied


def player_buckets(spec_player):
    """bucket -> {'pctl': within-pos pctl, 'rte': qualified routes} over adequate samples only."""
    out = {}
    sch = spec_player.get('schemes') or {}
    for b, comps in PLR_SHELL.items():
        cells = [sch[c] for c in comps if sch.get(c) and sch[c].get('q') and sch[c].get('pctl') is not None]
        rte = sum(c['rte'] for c in cells)
        if cells and rte >= MIN_BUCKET_RTE:
            out[b] = {'pctl': round(sum(c['pctl'] * c['rte'] for c in cells) / rte, 1), 'rte': rte}
    rl = spec_player.get('rollups') or {}
    for b, cell in (('man', rl.get('MAN')), ('zone', rl.get('ZONE'))):
        if cell and cell.get('q') and cell.get('pctl') is not None and cell.get('rte', 0) >= MIN_ROLLUP_RTE:
            out[b] = {'pctl': float(cell['pctl']), 'rte': cell['rte']}
    return out


PAIRS = (('single_high', 'two_high'), ('man', 'zone'))   # complementary partitions of the same snaps


def week_fit(buckets, opp_rates, lg):
    """(clamped fit, contributions[]) for one opponent. Only COMPLETE pairs count (see module doc)."""
    contribs = []
    for pair in PAIRS:
        if not all(b in buckets for b in pair):
            continue
        for b in pair:
            skill = (buckets[b]['pctl'] - 50.0) / 50.0
            dev = (opp_rates[b] - lg[b]) / 100.0
            contribs.append((b, skill * dev, opp_rates[b]))
    raw = sum(c for _, c, _ in contribs)
    return max(-WEEK_CAP, min(WEEK_CAP, raw)), contribs


def _ord(n):
    n = int(round(n)); m = n % 100
    return f"{n}{'th' if 11 <= m <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def why(contribs, buckets, lg, positive):
    """One-line football reason: the biggest same-sign bucket contribution."""
    pool = [c for c in contribs if (c[1] > 0) == positive and abs(c[1]) > 0.005]
    if not pool: return None
    b, _, rate = max(pool, key=lambda c: abs(c[1]))
    pc = buckets[b]['pctl']
    side = 'strength' if pc >= 50 else 'weakness'
    hl = 'heavy' if rate > lg[b] else 'light'
    return f"{hl} {LABEL[b]} {rate:.0f}% (lg {lg[b]:.0f}%) meets his {_ord(pc)}-pctl {side} vs it"


def build():
    tbl, lg, newdc = defense_rates()
    spec = json.load(open(os.path.join(HERE, 'boom', 'coverage_route_spec.json'), encoding='utf-8'))
    sched = json.load(open(os.path.join(HERE, 'boom', 'schedule2026.json'), encoding='utf-8'))
    # 2026 team per player (MOVES-AWARE): flags files already carry the 2026 roster placement
    team26 = {}
    for pos in ('WR', 'TE'):
        fp = os.path.join(HERE, 'boom', f'flags_{pos}.json')
        if not os.path.exists(fp): continue
        for k, r in json.load(open(fp, encoding='utf-8')).items():
            if r.get('team'):
                team26[core.fn(r.get('name', k))] = r['team']

    players, skipped = {}, {'no_bucket': 0, 'no_pair': 0, 'no_team': 0}
    for p in spec['players']:
        key = core.fn(p['name'])
        buckets = player_buckets(p)
        if not buckets:
            skipped['no_bucket'] += 1; continue
        pairs = [pr for pr in PAIRS if all(b in buckets for b in pr)]
        if not pairs:                    # only half a partition charted -> no honest differential
            skipped['no_pair'] += 1; continue
        buckets = {b: buckets[b] for pr in pairs for b in pr}
        tm = team26.get(key)
        team_src = 'flags-2026'
        if not tm:                       # not in the draftable flags pool -> last charted team (noted)
            tm = core.norm_team(__import__('boomutil').team(p.get('team') or ''))
            team_src = 'charting-2025'
        if tm not in sched:
            skipped['no_team'] += 1; continue
        weeks, reg, pl = [], [], []
        for g in sched[tm]:
            wk, opp = g.get('wk'), g.get('opp')
            if opp == 'BYE' or opp not in tbl or wk is None or wk > 17: continue
            fit, contribs = week_fit(buckets, tbl[opp], lg)
            fit = round(fit, 3)
            weeks.append({'wk': wk, 'opp': opp, 'fit': fit,
                          'why': why(contribs, buckets, lg, positive=fit >= 0),
                          'new_dc': bool(tbl[opp].get('new_dc'))})
            (reg if wk in REGULAR_WEEKS else pl).append(fit)
        if not weeks:
            skipped['no_team'] += 1; continue
        season = round((sum(reg) + PLAYOFF_TILT * sum(pl)) / (len(reg) + PLAYOFF_TILT * len(pl)), 3)
        by_fit = sorted(weeks, key=lambda w: w['fit'])
        players[key] = {
            'name': p['name'], 'pos': p['pos'], 'team': tm, 'team_src': team_src,
            'buckets': buckets,
            'elite': [e for e in (p.get('elite') or []) if e.get('kind') in ('scheme',)][:4],
            'weak':  [e for e in (p.get('weak') or []) if e.get('kind') in ('scheme',)][:4],
            'season': season,
            'regular': round(statistics.mean(reg), 3) if reg else None,
            'playoff': round(statistics.mean(pl), 3) if pl else None,
            'playoff_weeks': [w for w in weeks if w['wk'] in PLAYOFF_WEEKS],
            'best': by_fit[-2:][::-1], 'worst': by_fit[:2],
            'weeks': weeks,
        }

    meta = {'built': __import__('datetime').date.today().isoformat(),
            'seasons': list(SEASONS), 'year_weights': {str(k): round(v, 3) for k, v in YEAR_W.items()},
            'source': 'NFL-master/FP_SWEEP/{yr}/Defense_Receiving/coverageScheme (defense usage, rebuilt '
                      '2yr; boom/defense_shell.json is a frozen 2025-only artifact) + boom/coverage_route_spec.json (skill) '
                      '+ coordinator_scheme_2026.json / coordinator_changes_2026.json (new-DC 2026 projection)',
            'week_cap': WEEK_CAP, 'min_bucket_rte': MIN_BUCKET_RTE, 'min_rollup_rte': MIN_ROLLUP_RTE,
            'playoff_tilt': PLAYOFF_TILT,
            # per-team new-DC provenance (replaces the old single blanket 'new_dc_shrink'):
            #   coord-man+scheme-shell = researched man prior + shell lean parsed from sourced dc_scheme prose
            #   blend-prior            = researched man prior; no shell claim -> 2yr shell kept (NOT regressed)
            #   coord-man+regress-shell= unknown DC: registry lambda-regressed man + LIGHT (30%) shell regression
            #   regress-mean           = no coordinator data at all -> old blanket 50% shrink (fallback)
            'new_dc_teams': sorted(newdc), 'new_dc_applied': newdc,
            'new_dc_regressed': sorted(t for t, a in newdc.items() if 'regress' in a['mode']),
            'buckets': {b: DEF_BUCKET[b] for b in DEF_BUCKET}, 'league': lg,
            'formula': 'fit_wk = sum_b [(pctl_b-50)/50] * [(opp_rate_b - lg_b)/100], clamp +/-%.2f; '
                       'season = (sum W1-14 + %.1f * sum W15-17) / (n + %.1f*n_po)' % (WEEK_CAP, PLAYOFF_TILT, PLAYOFF_TILT),
            'n_players': len(players), 'skipped': skipped,
            'defense_table': tbl}
    core.safe_json_dump({'_meta': meta, 'players': players},
                        os.path.join(HERE, 'boom', 'scheme_fit.json'), indent=1)

    # ---- console verification ----
    print(f"scheme_fit.json: {len(players)} players ({skipped['no_bucket']} skipped: no adequate bucket sample; "
          f"{skipped['no_pair']} no complete pair; {skipped['no_team']} no 2026 schedule) | defenses: {len(tbl)}")
    print("new-DC 2026 (coordinator-aware):")
    for t, a in sorted(newdc.items()):
        print(f"  {t:<3} {a['mode']:<24} dc={a['dc']}"
              f"{' shell->' + a['shell_lean'] if a['shell_lean'] else ''} man {a['man'][0]}->{a['man'][1]}")
    print(f"league buckets: {lg}")
    seas = sorted(players.values(), key=lambda v: v['season'])
    import statistics as st
    allv = [v['season'] for v in players.values()]
    print(f"season fit: mean {st.mean(allv):+.3f} | sd {st.pstdev(allv):.3f} | "
          f"p5 {sorted(allv)[int(.05*len(allv))]:+.3f} p95 {sorted(allv)[int(.95*len(allv))]:+.3f} "
          f"| min {min(allv):+.3f} max {max(allv):+.3f}")
    print("\nTOP season scheme-fit:")
    for v in seas[-8:][::-1]:
        bks = ', '.join('%s:%.0f' % (b, d['pctl']) for b, d in v['buckets'].items())
        print(f"  {v['season']:+.3f}  {v['name']:<22} {v['pos']} {v['team']:<3} playoff {v['playoff']:+.3f} [{bks}]")
    print("\nBOTTOM season scheme-fit:")
    for v in seas[:8]:
        print(f"  {v['season']:+.3f}  {v['name']:<22} {v['pos']} {v['team']:<3} playoff {v['playoff']:+.3f}")
    nico = players.get('nico collins')
    if nico:
        print(f"\nNico Collins: season {nico['season']:+.3f} regular {nico['regular']:+.3f} playoff {nico['playoff']:+.3f}")
        print(f"  buckets: {nico['buckets']}")
        for w in nico['weeks']:
            print(f"   W{w['wk']:>2} {w['opp']:<3} {w['fit']:+.3f}  {w['why'] or ''}{' [new DC]' if w['new_dc'] else ''}")


if __name__ == '__main__':
    build()
