#!/usr/bin/env python3
"""middle_week.py — the MIDDLE-of-field matchup board for one slate, PRE-LOCK legal.

For Week N of season S, builds the middle layer from ONLY games before that slate
(Week 1 2025 => 2024 tendencies only — what you'd actually have had at lock), then crosses
every pass-catcher in the FL slate pool against its opponent defense via middle_edge (C8:
win x funnel x exposure). Prints a per-game board of MIDDLE SMASH / FORTRESS reads and flags
players with no prior middle history (rookies / new roles) — the exact spots the film/analyst
layer must fill.
"""
import csv, glob, os, sys
import build_middle_funnel as mf

HERE = os.path.dirname(os.path.abspath(__file__))
FL = os.path.join(HERE, 'data', 'fantasylabs', 'players')


def season_of(date):
    y, m = int(date[:4]), int(date[5:7])
    return y if m >= 8 else y - 1


def slate_pool(date):
    """biggest main contest that slate -> [(name,pos,team,opp)] for WR/TE."""
    best, size = None, -1
    for p in glob.glob(os.path.join(FL, f'{date}_main_*.csv')):
        r0 = next(csv.DictReader(open(p)))
        if int(r0['contestSize']) > size:
            size, best = int(r0['contestSize']), p
    out = []
    if not best:
        return out
    for r in csv.DictReader(open(best)):
        if r['pos'] in ('WR', 'TE'):
            out.append((r['name'], r['pos'], r['team'], r['opp']))
    return out


def run(date, week):
    season = season_of(date)
    # pre-lock layer: everything strictly before this slate
    seasons = tuple(str(y) for y in range(2024, season + 1))
    L = mf.build(seasons=seasons, before=(season, week),
                 out_path=os.path.join(HERE, f'/tmp/middle_asof_{season}_wk{week}.json'),
                 min_def=40, min_rec=15)                    # 1-season-ish samples => lower floors
    pool = slate_pool(date)
    if not pool:
        sys.exit(f"no FL pool for {date}")
    games = {}
    for nm, pos, tm, opp in pool:
        games.setdefault(frozenset((tm, opp)), {}).setdefault(tm, []).append((nm, pos, opp))
    print(f"\n{'='*84}\nMIDDLE MATCHUP BOARD — {date} (wk{week}), pre-lock ({seasons} thru wk{week-1})\n{'='*84}")
    nosample = []
    for gk, sides in sorted(games.items(), key=lambda kv: '-'.join(sorted(kv[0]))):
        teams = sorted(sides)
        hdr = ' vs '.join(teams)
        lines = []
        for tm in teams:
            for nm, pos, opp in sides[tm]:
                e = mf.middle_edge(nm, opp, L)
                if e.get('tag') in ('MIDDLE SMASH', 'MIDDLE FORTRESS (avoid)'):
                    lines.append(f"    {nm:<22}{pos}  vs {opp:<4} {e['tag']}  "
                                 f"(win {e['player_win_pctl']:.0f}pct, {e['player_mid_share']:.0f}% mid; "
                                 f"D soft {e['def_softness_pctl']:.0f}pct)")
                elif e.get('edge') is None and 'no middle sample for ' + nm == e.get('reason'):
                    nosample.append(nm)
        if lines:
            print(f"\n  {hdr}")
            print('\n'.join(lines))
    print(f"\n  [{len(set(nosample))} pass-catchers had NO prior middle history "
          f"(rookies/new roles) — the film/analyst layer's job to cover]")


if __name__ == '__main__':
    if len(sys.argv) == 3:
        run(sys.argv[1], int(sys.argv[2]))
    else:
        print("usage: python3 middle_week.py YYYY-MM-DD WEEK   (e.g. 2025-09-07 1)")
