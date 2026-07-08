#!/usr/bin/env python3
"""retro_pipeline.py — the walk-forward weekly process (see RETRO_PIPELINE.md).

Composes the existing pieces into one standing pipeline that runs identically on 2025
(historical, the rehearsal) and 2026 (live). Four stages:
  1 INGEST     ingest_worklist(S,N)  -> the per-source fetch plan for week N's window
                                        (agent runs the article WebFetches; Mac runs video/pods)
  2 AS-OF      as-of data layers built with before=(S,N)  (no look forward)
  3 SYNTHESIZE assemble_prelock(S,N) -> the pre-lock decision pack (data + film signals)
  4 VALIDATE   validate_week(S,N)    -> grade the pack vs actuals (rehearsal only)

The article fetch itself is agent/tool work (WebSearch/WebFetch aren't callable from a script),
so Stage 1 EMITS the work list; everything else is code. In 2026 the same work list is run live.
"""
import csv, glob, json, os, re, sys
import build_middle_funnel as mf
import build_asof as ao
import analyst_retro as ar

HERE = os.path.dirname(os.path.abspath(__file__))
FL = os.path.join(HERE, 'data', 'fantasylabs', 'players')

# ---- Stage 1: the SOURCE MANIFEST (repeatable ingestion, not ad-hoc) ----
SOURCES = {
    'benjaminsolak':  {'tier': 'article', 'q': 'Ben Solak week {N} {S} NFL takeaways'},
    'yardspergretch': {'tier': 'article', 'q': 'Stealing Signals week {N} {S}'},
    'pff_fantasy':    {'tier': 'article', 'q': 'PFF week {N} {S} fantasy recap takeaways'},
    'fantasypts':     {'tier': 'article', 'q': 'Fantasy Points data charter notes week {N} {S}'},
    'mattharmon_byb': {'tier': 'article', 'q': 'Matt Harmon Yahoo week {N} {S} takeaways'},
    'brettkollmann':  {'tier': 'video',   'q': 'Brett Kollmann week {N} {S} film'},
    'scottbarrettdfb':{'tier': 'article', 'q': 'Scott Barrett week {N} {S} fantasy'},
}


def _season(date):
    y, m = int(date[:4]), int(date[5:7]); return y if m >= 8 else y - 1


def window(season, week):
    return ar.inter_week_window(season, week)   # (after wkN-1 Sunday .. before wkN Sunday lock)


def ingest_worklist(season, week):
    """Stage 1: what to fetch for this week's window, per source. Agent/Mac executes; results
    normalize to retro_raw/{season}/wk{week}/. Identical call shape in 2026 (live)."""
    lo, hi = window(season, week - 0) if week > 1 else (None, None)
    plan = {'season': season, 'week': week, 'window': [lo, hi],
            'retro_raw': f'retro_raw/{season}/wk{week}/', 'sources': []}
    for h, s in SOURCES.items():
        plan['sources'].append({'handle': h, 'tier': s['tier'],
                                'query': s['q'].format(N=week, S=season),
                                'run_by': 'agent(WebFetch)' if s['tier'] == 'article'
                                          else 'mac(brain_video.py)' if s['tier'] == 'video'
                                          else 'twitterapi.io'})
    return plan


# ---- Stage 2/3: as-of layers + synthesis ----
_OPP = re.compile(r'snap|route|share|volume|workload|job|committee|vacat|waiver|buy|usage|touch|carr|target|role|start|phased|distribut', re.I)
_FILM = re.compile(r'matchup|coverage|separation|shadow|protection|scheme|alignment|won|poise|accuracy|arm|ball skill|efficien|missed tackle|designed|ass |rating|open', re.I)
_INJ = re.compile(r'injur|hurt|questionable|\bout\b|ankle|hamstring|calf|neck|shoulder|concuss', re.I)


def _cat(q):
    return 'opportunity' if _OPP.search(q) else 'film' if _FILM.search(q) else 'injury' if _INJ.search(q) else 'other'


def _slate_wrte(date):
    best, size = None, -1
    for p in glob.glob(os.path.join(FL, f'{date}_main_*.csv')):
        r0 = next(csv.DictReader(open(p)))
        if int(r0['contestSize']) > size:
            size, best = int(r0['contestSize']), p
    return [(r['name'], r['pos'], r['team'], r['opp']) for r in csv.DictReader(open(best))
            if r['pos'] in ('WR', 'TE', 'RB', 'QB')] if best else []


def _resolve_usage(nm, U):
    hit = U.get(mf._pbp_name(nm)) or U.get(nm)
    if hit:
        return hit
    idx = {mf._norm_key(k): v for k, v in U.items()}
    return idx.get(mf._norm_key(nm))


def assemble_prelock(date, week):
    """Stage 3 HOLISTIC: environment + full matchup + role + middle + film, all as-of (no look
    forward). One read per player composed from the whole factor stack, not a single axis."""
    season = _season(date)
    seasons = tuple(str(y) for y in range(2024, season + 1))
    A = ao.build(season, week)                                   # environment + matchup + usage as-of
    O, D, U = A['offense'], A['defense'], A['usage']
    L = mf.build(seasons=seasons, before=(season, week),
                 out_path=f'/tmp/mid_{season}_wk{week}.json', min_def=40, min_rec=15)
    signals = ar.build_week(season, week) or {}
    T = lambda x: mf.ALIAS.get(x, x)
    pack = {}
    for nm, pos, tm, opp in _slate_wrte(date):
        off, dfn = O.get(T(tm)), D.get(T(opp))
        use = _resolve_usage(nm, U)
        entry = {'pos': pos, 'tm': tm, 'opp': opp}
        # ENVIRONMENT (his offense)
        if off:
            entry['env'] = {'pace_pctl': off.get('plays_pg_pctl'), 'proe': off.get('proe'),
                            'off_epa_pctl': off.get('off_epa_pctl')}
        # MATCHUP (opp defense, routed to his position)
        if dfn:
            vs = dfn.get(f'vs_{pos}_softpctl') if pos in ('WR', 'TE', 'RB') else None
            entry['matchup'] = {'vs_pos_softpctl': vs, 'pass_soft_pctl': dfn.get('pass_epa_softpctl'),
                                'deep_soft': dfn.get('deep_epa_softpctl'),
                                'short_soft': dfn.get('short_epa_softpctl')}
        # ROLE / opportunity
        if use:
            rising = use['tgt_share_recent'] > 100 / max(len(str(use)), 1) and use['tgt_share_recent'] >= use['tgt_share']
            entry['role'] = {'tgt_share': use['tgt_share'], 'ay_share': use['ay_share'],
                             'rz_tgt': use['rz_tgt'],
                             'trend': 'rising' if use['tgt_share_recent'] > use['tgt_share'] else 'steady/down'}
        # MIDDLE axis
        e = mf.middle_edge(nm, opp, L)
        if e.get('tag', '').startswith('MIDDLE'):
            entry['middle'] = e['tag']
        # FILM / analyst
        sig = signals.get(nm)
        if sig:
            cats = {}
            for h, st in sig['by_handle'].items():
                q = next((qq for qq in sig['quotes'] if h in qq), '')
                cats.setdefault(_cat(q), []).append(f"@{h}:{st}")
            entry['analyst'] = {'stance': sig['sentiment'], 'signals': cats}
        # composite headline: soft position matchup + good env + real/ rising role (+film corroboration)
        m = entry.get('matchup', {}).get('vs_pos_softpctl')
        ev = entry.get('env', {}).get('off_epa_pctl')
        rl = entry.get('role', {}).get('tgt_share', 0)
        score = sum([(m or 0) >= 65, (ev or 0) >= 60, rl >= 20,
                     entry.get('middle') == 'MIDDLE SMASH',
                     entry.get('analyst', {}).get('stance') == 'bullish'])
        entry['read'] = ('SMASH LEAN' if score >= 3 else
                         'AVOID LEAN' if ((m is not None and m <= 25) and rl >= 18) or
                                         entry.get('middle') == 'MIDDLE FORTRESS (avoid)' else 'neutral')
        pack[nm] = entry
    return pack


def validate_week(date, week, horizon=1):
    """Stage 4 (rehearsal): grade middle-smash tags vs next-week ceiling (placeholder hook)."""
    return ar.score_analysts(_season(date), week, horizon)


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--worklist', nargs=2, metavar=('SEASON', 'WEEK'), type=int)
    ap.add_argument('--prelock', nargs=2, metavar=('DATE', 'WEEK'))
    a = ap.parse_args()
    if a.worklist:
        print(json.dumps(ingest_worklist(*a.worklist), indent=1, default=str))
    elif a.prelock:
        pk = assemble_prelock(a.prelock[0], int(a.prelock[1]))
        smash = [(n, v) for n, v in pk.items() if v['read'] == 'SMASH LEAN']
        print(f"\nHOLISTIC PRE-LOCK PACK {a.prelock[0]} wk{a.prelock[1]} — {len(pk)} players | "
              f"{len(smash)} SMASH LEAN (env x matchup x role x middle x film)\n")
        for nm, v in sorted(smash, key=lambda kv: -(kv[1].get('role', {}).get('tgt_share', 0))):
            e = v.get('env', {}); mm = v.get('matchup', {}); rl = v.get('role', {})
            print(f"  {nm:<19}{v['pos']} {v['tm']}v{v['opp']:<4} | "
                  f"env pace{e.get('pace_pctl','-')}/PROE{e.get('proe','-')}/epa{e.get('off_epa_pctl','-')} | "
                  f"vs-{v['pos']} soft {mm.get('vs_pos_softpctl','-')}pct | "
                  f"role {rl.get('tgt_share','-')}%({rl.get('trend','?')}) | "
                  f"{v.get('middle','')} {('film:'+v['analyst']['stance']) if v.get('analyst') else ''}")
    else:
        ap.print_help()
