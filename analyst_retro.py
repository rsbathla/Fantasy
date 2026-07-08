#!/usr/bin/env python3
"""analyst_retro.py — retrospective analyst-narrative layer for the film room.

The job (§1): for a given film-room week N, gather what the tracked FILM analysts published in
the inter-week window [after week N's Sunday main -> before week N+1's Sunday main], map each
item to the players it names, and synthesize a per-player narrative to sit next to the tape
(nflverse) and the stats (FantasyPoints) in the week card.

This module is the SOURCE-AGNOSTIC half — window logic + entity mapping + synthesis + card
integration. It runs in the repo and is fully testable now. The actual CONTENT PULL (yt-dlp /
whisper / twitterapi.io) runs Mac-side via the brain pipeline and drops transcripts into
retro_raw/{season}/wk{N}/*.txt (one file per item, first line = "SOURCE\thandle\tYYYY-MM-DD\turl").

Entity rule mirrors brain_common (repo inventory, §9): a mention requires the player's FULL
name (first + last); a lone first or last name never resolves ("James" != Jordan James).

Load-bearing piece (§2/§3): the resolver. A garbled name silently corrupts every downstream
narrative, so it ships with a known-bad precision test (run:  python3 analyst_retro.py --selftest).
"""
import argparse, csv, glob, json, os, re, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
FL = os.path.join(HERE, 'data', 'fantasylabs', 'players')
GAMES = os.path.join(HERE, 'data', 'nflverse', 'games_2021_2025.csv')
RAW = os.path.join(HERE, 'retro_raw')
CARDS = os.path.join(HERE, 'weekcards')

# The film subset (confidence-labeled inventory, 2026-07-08). Pulled first per the phased plan.
FILM_HANDLES = {
    'brettkollmann': 'all-22 film breakdowns',
    'benjaminsolak': 'film + coverage charting',
    'mattharmon_byb': 'Reception Perception (route vs coverage)',
    'yardspergretch': 'Stealing Signals (film-informed usage)',
    'scottbarrettdfb': 'film/stats, matchup exploits',
    'syedschemes': 'scheme/DFS film',
    'coachspeakindex': 'coordinator tendencies',
    'sigmundbloom': 'long-form film/pod',
    'lateroundqb': 'usage + some film',
}

BULL = {'smash', 'elite', 'league-winner', 'buy', 'breakout', 'alpha', 'ascending', 'must',
        'love', 'target', 'sticky', 'workhorse', 'bellcow', 'featured', 'green light', 'ceiling',
        'wins', 'dominant', 'open', 'separation', 'uncoverable', 'monster', 'locked', 'bullish'}
BEAR = {'fade', 'avoid', 'concern', 'worry', 'trap', 'overpriced', 'chalk', 'regress', 'sell',
        'committee', 'timeshare', 'banged', 'limited', 'shadow', 'bracket', 'funnel away',
        'tough matchup', 'buried', 'phased out', 'decline', 'dud', 'bust', 'capped', 'bearish',
        'quiet'}


def _norm(s):
    s = s.replace('’', "'").replace('.', '')
    return re.sub(r'\s+', ' ', s).strip().lower()


def load_universe(season):
    """{normalized full name -> canonical name}; drops names that are a single token."""
    uni = {}
    pat = os.path.join(FL, f'{season}-*_main_*.csv')
    files = glob.glob(pat) + (glob.glob(os.path.join(FL, f'{season+1}-01-*_main_*.csv'))
                              + glob.glob(os.path.join(FL, f'{season+1}-02-*_main_*.csv')))
    for p in files:
        try:
            for r in csv.DictReader(open(p)):
                nm = (r.get('name') or '').strip()
                if len(nm.split()) >= 2:
                    uni[_norm(nm)] = nm
        except Exception:
            continue
    return uni


def sunday_mains(season):
    """{week -> latest Sunday gameday date-string} for a season."""
    wk = {}
    for r in csv.DictReader(open(GAMES)):
        if r.get('season') != str(season) or r.get('weekday') != 'Sunday':
            continue
        w = int(r['week']); d = r['gameday']
        if w not in wk or d > wk[w]:
            wk[w] = d
    return wk


def inter_week_window(season, week):
    """(start, end): day after week N's Sunday main -> week N+1's Sunday main (the lock)."""
    sm = sunday_mains(season)
    if week not in sm:
        return None, None
    start = sm[week]
    nxt = sm.get(week + 1)
    return start, nxt


def resolve(text, universe):
    """Return {canonical name: [sentence, ...]} for every FULL-name mention. Full name required."""
    hits = defaultdict(list)
    # sentence split (cheap), then per-sentence full-name substring match on normalized text
    for sent in re.split(r'(?<=[.!?])\s+|\n+', text):
        ns = _norm(sent)
        if not ns:
            continue
        for key, canon in universe.items():
            # word-boundary full-name match
            if key in ns:
                # guard: ensure it's a bounded match, not mid-word
                if re.search(r'(?<![a-z])' + re.escape(key) + r'(?![a-z])', ns):
                    hits[canon].append(sent.strip())
    return hits


def sentiment(sentences):
    """Explicit stance token (bullish/bearish/neutral) wins over the soft lexicon — the lexicon
    false-fires on recap words ('lead targets' != a bullish CALL). Lexicon is the fallback for
    raw transcripts that carry no explicit label."""
    text = ' '.join(_norm(s) for s in sentences)
    eb = len(re.findall(r'\bbullish\b', text))
    ew = len(re.findall(r'\bbearish\b', text))
    en = len(re.findall(r'\bneutral\b', text))
    if eb or ew or en:
        if eb > ew and eb >= en:
            return 'bullish', eb, ew
        if ew > eb and ew >= en:
            return 'bearish', eb, ew
        return 'neutral', eb, ew
    b = sum(1 for t in BULL if t in text)
    w = sum(1 for t in BEAR if t in text)
    return ('bullish', b, w) if b > w else ('bearish', b, w) if w > b else ('neutral', b, w)


def build_week(season, week):
    """Read retro_raw/{season}/wk{week}/*.txt -> per-player narrative dict. Fails loud if empty."""
    d = os.path.join(RAW, str(season), f'wk{week}')
    files = sorted(glob.glob(os.path.join(d, '*.txt')))
    if not files:
        print(f"[analyst_retro] NO raw items in {d} — run the Mac pull first (see --howto).",
              file=sys.stderr)
        return None
    uni = load_universe(season)
    if not uni:
        sys.exit(f"[analyst_retro] empty player universe for {season} — cannot map. ABORT.")
    per = defaultdict(lambda: defaultdict(list))          # player -> handle -> [sentences]
    for fp in files:
        lines = open(fp, encoding='utf-8', errors='ignore').read().split('\n')
        header = lines[0].split('\t') if lines and '\t' in lines[0] else ['?', os.path.basename(fp), '', '']
        src, handle = (header + ['', ''])[:2]
        body = '\n'.join(lines[1:])
        for canon, sents in resolve(body, uni).items():
            per[canon][handle].extend(sents)
    out = {}
    for canon, hs in per.items():
        handle_stance = {h: sentiment(ss)[0] for h, ss in hs.items()}   # PER-ANALYST stance
        tones = list(handle_stance.values())
        agg = max(set(tones), key=tones.count) if tones else 'neutral'
        out[canon] = {'sentiment': agg, 'by_handle': handle_stance, 'sources': sorted(hs),
                      'n_mentions': sum(len(ss) for ss in hs.values()),
                      'quotes': [f"@{h}: {ss[0][:200]}" for h, ss in list(hs.items())[:4]]}
    print(f"[analyst_retro] {len(files)} items -> {len(out)} players mapped "
          f"({sum(len(hs) for hs in per.values())} handle-mentions)", file=sys.stderr)
    return out


TOPK = {'QB': 3, 'RB': 5, 'WR': 6, 'TE': 3, 'DST': 3}


def ceiling_board(season, week):
    """The ANSWER KEY: top-K-at-position by ACTUAL on week N's Sunday main. No analyst content
    needed — pure outcomes. Each hit tagged LEVERAGE if <10% owned (the non-obvious call).
    Returns {canonical name: {pos, act, proj, own, leverage}}."""
    sm = sunday_mains(season)
    date = sm.get(week)
    if not date:
        return {}
    best, size = None, -1
    for p in glob.glob(os.path.join(FL, f'{date}_main_*.csv')):
        r0 = next(csv.DictReader(open(p)))
        if int(r0['contestSize']) > size:
            size, best = int(r0['contestSize']), p
    if not best:
        return {}
    bypos = defaultdict(list)
    for r in csv.DictReader(open(best)):
        try:
            bypos[r['pos']].append((r['name'], float(r['actual']), float(r['proj']),
                                    float(r['ownership'] or 0)))
        except (ValueError, KeyError):
            continue
    board = {}
    for pos, k in TOPK.items():
        for nm, act, proj, own in sorted(bypos.get(pos, []), key=lambda x: -x[1])[:k]:
            board[nm] = {'pos': pos, 'act': act, 'proj': proj, 'own': own, 'leverage': own < 10}
    return board


def score_analysts(season, week, horizon=1):
    """Grade each analyst's window-N BULLISH calls PREDICTIVELY — against week N+horizon's
    ceiling board, NOT week N's (grading recap content vs its own week is circular: they already
    know the result). horizon=1 = 'said it after wk N, did it hit in wk N+1'. This is the DFS
    skill: lev_recall = leverage-nukes-called / leverage-nukes-available next week. Gated on content."""
    calls = build_week(season, week)          # {player: {by_handle, ...}} — needs the pull
    if not calls:
        return None
    board = ceiling_board(season, week + horizon)
    if not board:
        sys.exit(f"[analyst_retro] no ceiling board for {season} wk{week+horizon} "
                 f"(need the following week's actuals). ABORT.")
    lev_avail = {n for n, v in board.items() if v['leverage']}
    # invert calls -> per-handle bullish player set (only bullish mentions count as a "call")
    by_handle = defaultdict(set)
    for player, v in calls.items():
        for h, st in v.get('by_handle', {}).items():      # per-analyst stance, not aggregate
            if st == 'bullish':
                by_handle[h].add(player)
    rows = []
    for h, called in by_handle.items():
        hit = called & set(board)
        lev_hit = called & lev_avail
        rows.append({'handle': h, 'n_called': len(called),
                     'ceiling_hits': len(hit), 'precision': len(hit) / max(len(called), 1),
                     'lev_hits': len(lev_hit),
                     'lev_recall': len(lev_hit) / max(len(lev_avail), 1),
                     'named': sorted(lev_hit)})
    return {'week': week, 'lev_available': sorted(lev_avail), 'analysts':
            sorted(rows, key=lambda r: (-r['lev_hits'], -r['precision']))}


def selftest():
    """Known-bad precision test for the resolver (§10). Real 2025 names + decoys."""
    uni = load_universe(2025)
    assert uni, "universe empty — need 2025 FL player files"
    FIX = (
        "SOURCE\tbrettkollmann\t2025-09-09\thttp://x\n"
        "Drake London was uncoverable on the all-22 — sticky first read, but Jamel Dean "
        "shadowed him and won two contested balls at the goal line. Elite target, brutal luck.\n"
        "Ja'Marr Chase I have concerns about — Cincinnati's protection is a trap this week, "
        "tough matchup vs that front, I'd fade.\n"
        "Michael Penix flashed a live arm. Meanwhile Jordan James is buried on the depth chart. "
        "Some guy named James did nothing. LeBron plays basketball."
    )
    body = '\n'.join(FIX.split('\n')[1:])
    hits = resolve(body, uni)
    names = set(hits)
    checks = []
    checks.append(("Drake London resolved", 'Drake London' in names))
    checks.append(("Ja'Marr Chase resolved (apostrophe)", "Ja'Marr Chase" in names))
    checks.append(("Michael Penix resolved", any('Penix' in n for n in names)))
    # precision: lone 'James' must NOT create a false Jordan James hit from that sentence,
    # but the real 'Jordan James' full mention SHOULD resolve
    checks.append(("Jordan James resolved (full name present)", 'Jordan James' in names))
    lonely = [n for n in names if n.lower() in ('james', 'drake', 'london', 'chase')]
    checks.append(("no single-token false positives", not lonely))
    london_tone = sentiment([s for s in hits.get('Drake London', [])])[0]
    chase_tone = sentiment([s for s in hits.get("Ja'Marr Chase", [])])[0]
    checks.append(("London reads bullish", london_tone == 'bullish'))
    checks.append(("Chase reads bearish", chase_tone == 'bearish'))
    ok = all(v for _, v in checks)
    for name, v in checks:
        print(f"  [{'PASS' if v else 'FAIL'}] {name}")
    print(f"\nresolver self-test: {'ALL PASS' if ok else 'FAILURES ABOVE'}  (universe {len(uni)} names)")
    return 0 if ok else 1


HOWTO = """\
RETRO CONTENT CONTRACT — the pull (Mac-side, free phase) writes one .txt per item into
retro_raw/{season}/wk{N}/ with the FIRST LINE = "SOURCE<TAB>handle<TAB>YYYY-MM-DD<TAB>url"
and the transcript/post text as the body. That's all the mapper needs.

Two honest ways to produce those files (proof case = Week 1 -> Week 2 2025; window from
`python3 analyst_retro.py --window 2025 1`  ->  2025-09-07 .. 2025-09-14):

  (A) Fastest proof — feed 3-5 specific post-Week-1 videos/pods from the film subset
      (@brettkollmann @benjaminsolak @mattharmon_byb @yardspergretch ...) to your existing
      brain_video.py (it already downloads + whisper-transcribes), then drop each transcript
      into retro_raw/2025/wk1/ with the header line above. Or just paste the URLs to me.

  (B) Automated sweep (after the proof) — a yt-dlp search puller keyed to the film subset x the
      window; I'll finalize it once (A) proves the mapping + scoring end-to-end on real content.

Film subset handles: """ + ', '.join('@' + h for h in FILM_HANDLES) + """
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--window', nargs=2, metavar=('SEASON', 'WEEK'), type=int)
    ap.add_argument('--build', nargs=2, metavar=('SEASON', 'WEEK'), type=int)
    ap.add_argument('--ceiling', nargs=2, metavar=('SEASON', 'WEEK'), type=int)
    ap.add_argument('--score', nargs=2, metavar=('SEASON', 'WEEK'), type=int)
    ap.add_argument('--howto', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    if a.ceiling:
        b = ceiling_board(*a.ceiling)
        for nm, v in sorted(b.items(), key=lambda kv: -kv[1]['act']):
            print(f"  {nm:<22}{v['pos']:<5}{v['act']:>6.1f} act  {v['own']:>5.1f}% own  "
                  f"{'LEVERAGE' if v['leverage'] else 'chalk'}")
        return
    if a.score:
        res = score_analysts(*a.score)
        print(json.dumps(res, indent=2, default=list) if res else "(no analyst content yet)")
        return
    if a.window:
        s, e = inter_week_window(a.window[0], a.window[1])
        print(f"inter-week window, {a.window[0]} wk{a.window[1]}: {s}  ->  {e}")
        return
    if a.howto:
        print(HOWTO)
        return
    if a.build:
        res = build_week(a.build[0], a.build[1])
        if res:
            print(json.dumps(res, indent=2, default=list))
        return
    ap.print_help()


if __name__ == '__main__':
    main()
