#!/usr/bin/env python3
"""build_nflpro.py — aggregate the NFL Pro (Next Gen Stats) weekly CSV dump into a season profile.
Source: nfl_pro_scraper/ (weeks 1-17, 2025 regular season). AUGMENTS the FTN matchup table — this
does NOT replace it; the defensive-identity section shows both and cross-checks them.

Defense passing splits: ALL · SLOT · WIDE · TIGHT · DEEP · INTERMEDIATE · SHORT · PLAY_ACTION.
Per team, per split we season-aggregate (volume-weighted by pass plays faced):
  epa_pass   EPA/Pass ALLOWED   — higher = softer coverage = MORE targetable
  avg_sep    separation ALLOWED — higher = softer
  ypp        pass yards/play allowed
  yacoe      YAC-over-expected allowed (sum)
  pressure   Sack% + QBP% + Blitz% (dropback-weighted) — the pass-rush dimension
Then attacker-view percentiles across the 32 teams (high allowed = high pctl = green/target).
Rushing defense (ALL): EPA/Rush allowed, RYOE allowed, Stuff%, box rates (Light/Stacked).

  python3 build_nflpro.py --raw ../nfl_pro_scraper --out nflpro_2025.json --season 2025 --xcheck
"""
import argparse, csv, glob, json, os, re

def num(x):
    try:
        return float(str(x).replace('%', '').replace('+', '').strip())
    except Exception:
        return None

TEAM_ABBR = {  # NFL Pro uses full names; map to our repo abbreviations
 'Arizona Cardinals':'ARI','Atlanta Falcons':'ATL','Baltimore Ravens':'BAL','Buffalo Bills':'BUF',
 'Carolina Panthers':'CAR','Chicago Bears':'CHI','Cincinnati Bengals':'CIN','Cleveland Browns':'CLE',
 'Dallas Cowboys':'DAL','Denver Broncos':'DEN','Detroit Lions':'DET','Green Bay Packers':'GB',
 'Houston Texans':'HOU','Indianapolis Colts':'IND','Jacksonville Jaguars':'JAX','Kansas City Chiefs':'KC',
 'Las Vegas Raiders':'LV','Los Angeles Chargers':'LAC','Los Angeles Rams':'LAR','Miami Dolphins':'MIA',
 'Minnesota Vikings':'MIN','New England Patriots':'NE','New Orleans Saints':'NO','New York Giants':'NYG',
 'New York Jets':'NYJ','Philadelphia Eagles':'PHI','Pittsburgh Steelers':'PIT','San Francisco 49ers':'SF',
 'Seattle Seahawks':'SEA','Tampa Bay Buccaneers':'TB','Tennessee Titans':'TEN','Washington Commanders':'WAS'}

PASS_SPLITS = {'ALL':'ALL','TEAM_DEFENSE_PASSING_SLOT':'slot','TEAM_DEFENSE_PASSING_WIDE':'wide',
               'TEAM_DEFENSE_PASSING_TIGHT':'tight','TEAM_DEFENSE_PASSING_DEEP':'deep',
               'TEAM_DEFENSE_PASSING_INTERMEDIATE':'intermediate','TEAM_DEFENSE_PASSING_SHORT':'short',
               'TEAM_DEFENSE_PASSING_PLAY_ACTION':'play_action'}


def read_weeks(folder, split_file):
    """All weekly rows for one split -> {team_abbr: [rowdicts]}."""
    out = {}
    for p in sorted(glob.glob(os.path.join(folder, f"week*_{split_file}.csv"))):
        for r in csv.DictReader(open(p)):
            ab = TEAM_ABBR.get((r.get('Team') or '').strip())
            if ab:
                out.setdefault(ab, []).append(r)
    return out


def agg_pass(rows):
    """Volume-weight rates by pass plays faced; sum counting stats."""
    W = sum(num(r['Pass']) or 0 for r in rows)          # pass plays faced (the weight)
    if W <= 0:
        return None
    def wmean(col):
        s = sum((num(r.get(col)) or 0) * (num(r['Pass']) or 0) for r in rows)
        return round(s / W, 3)
    drop = sum((num(r['Pass']) or 0) + (num(r.get('Sack')) or 0) for r in rows)
    def wmean_db(col):
        s = sum((num(r.get(col)) or 0) * ((num(r['Pass']) or 0) + (num(r.get('Sack')) or 0)) for r in rows)
        return round(s / drop, 1) if drop else None
    return {
        'pass_plays': int(W),
        'epa_pass': wmean('EPA/Pass'),           # higher = softer (more allowed)
        'avg_sep': wmean('Avg Sep'),             # higher = softer coverage
        'ypp': wmean('Pass YPP'),
        'yacoe': int(sum(num(r.get('YACOE')) or 0 for r in rows)),
        'sack_pct': wmean_db('Sack %'), 'qbp_pct': wmean_db('QBP %'), 'blitz_pct': wmean_db('Blitz %'),
    }


def pctl_rank(values):
    """value -> 0..100 percentile (higher value = higher pctl). Ties share the mean rank."""
    order = sorted(values)
    n = len(order)
    return {v: round(100 * (sum(1 for o in order if o < v) + sum(1 for o in order if o == v) / 2 - 0.5) / (n - 1))
            for v in set(values)} if n > 1 else {values[0]: 50}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--raw', default='../nfl_pro_scraper')
    ap.add_argument('--out', default='nflpro_2025.json')
    ap.add_argument('--season', default='2025')
    ap.add_argument('--repo', default='.')
    ap.add_argument('--xcheck', action='store_true', help='cross-check vs FTN dvoa_fpaa')
    a = ap.parse_args()
    raw = os.path.expanduser(a.raw); pd_dir = os.path.join(raw, 'PassingDefense'); rd_dir = os.path.join(raw, 'RushingDefense')

    teams = {}
    for split_file, key in PASS_SPLITS.items():
        wk = read_weeks(pd_dir, split_file)
        for ab, rows in wk.items():
            g = agg_pass(rows)
            if g:
                teams.setdefault(ab, {'season': a.season, 'pass': {}})['pass'][key] = g

    # rushing defense (ALL)
    for ab, rows in read_weeks(rd_dir, 'ALL').items():
        W = sum(num(r.get('Run')) or 0 for r in rows)
        if W <= 0 or ab not in teams:
            continue
        wm = lambda c: round(sum((num(r.get(c)) or 0) * (num(r.get('Run')) or 0) for r in rows) / W, 3)
        teams[ab]['rush'] = {'run_plays': int(W), 'epa_rush': wm('EPA/Rush'), 'ryoe_att': wm('RYOE/Att'),
                             'stuff_pct': wm('Stuff %'), 'ybco_att': wm('YBCo/Att'),
                             'light_pct': wm('Light %'), 'stacked_pct': wm('Stacked %')}

    # attacker-view percentiles per split: high EPA-allowed & high sep-allowed = softer = higher pctl
    for key in list(PASS_SPLITS.values()):
        epas = {ab: teams[ab]['pass'][key]['epa_pass'] for ab in teams if key in teams[ab].get('pass', {})}
        seps = {ab: teams[ab]['pass'][key]['avg_sep'] for ab in teams if key in teams[ab].get('pass', {})}
        er = pctl_rank(list(epas.values())); sr = pctl_rank(list(seps.values()))
        for ab in epas:
            teams[ab]['pass'][key]['soft_pctl'] = er[epas[ab]]      # target-ability from EPA allowed
            teams[ab]['pass'][key]['sep_pctl'] = sr[seps[ab]]
    # run softness pctl (high EPA-rush allowed = soft run D = targetable on the ground)
    rr = pctl_rank([teams[ab]['rush']['epa_rush'] for ab in teams if 'rush' in teams[ab]])
    for ab in teams:
        if 'rush' in teams[ab]:
            teams[ab]['rush']['soft_pctl'] = rr[teams[ab]['rush']['epa_rush']]

    out = {'_meta': {'source': 'NFL Pro / Next Gen Stats weekly scrape', 'season': a.season,
                     'weeks': '1-17', 'note': 'AUGMENTS FTN dvoa_fpaa — validating layer, not a replacement. '
                     'soft_pctl = attacker view: higher = softer = more targetable.',
                     'metrics': 'epa_pass/avg_sep/ypp ALLOWED per alignment (slot/wide/tight) + depth + play-action'},
           'teams': teams}

    # ---- cross-check vs FTN dvoa_fpaa (agreement on alignment softness) ----
    if a.xcheck:
        try:
            ftn = json.load(open(os.path.join(a.repo, 'boom', 'defensive_profile.json')))
            rows = []
            for ab in sorted(teams):
                pp = teams[ab]['pass']
                ngs_slot = pp.get('slot', {}).get('soft_pctl'); ngs_wide = pp.get('wide', {}).get('soft_pctl')
                f = ftn.get(ab, {}).get('dvoa_fpaa', {})
                # FTN slot vs outside(wr1/wr2 avg), NGS slot vs wide — do they agree which is softer?
                ftn_slot_soft = (f.get('slot', 0)) - (max(f.get('wr1', 0), f.get('wr2', 0)))
                ngs_slot_soft = (ngs_slot or 50) - (ngs_wide or 50)
                agree = (ftn_slot_soft > 0) == (ngs_slot_soft > 0)
                rows.append((ab, ngs_slot, ngs_wide, f.get('slot'), f.get('wr1'), 'agree' if agree else 'DIVERGE'))
            out['_xcheck_slot_vs_wide'] = [{'team': r[0], 'ngs_slot_pctl': r[1], 'ngs_wide_pctl': r[2],
                                            'ftn_slot_fpaa': r[3], 'ftn_wr1_fpaa': r[4], 'flag': r[5]} for r in rows]
            n_div = sum(1 for r in rows if r[5] == 'DIVERGE')
            print(f"cross-check: {len(rows)} teams · {n_div} DIVERGE on slot-vs-outside softness (NGS vs FTN)")
        except Exception as e:
            print(f"xcheck skipped: {e}")

    # FAIL-LOUD GUARD: never clobber a populated layer with an empty build. A missing/empty
    # raw scrape dir (e.g. NFL_PRO_2025 unset on this machine) yields zero teams, exit 0,
    # and blanks every Concept page's NGS section downstream (quant audit, data-loss class).
    dest = os.path.join(a.repo, a.out)
    if len(teams) < 16:
        raise SystemExit(f"FATAL: only {len(teams)} teams built (raw scrape missing/empty?) — refusing to overwrite {dest}")
    json.dump(out, open(dest, 'w'), indent=1)
    print(f"wrote {a.out}: {len(teams)} teams · {len(PASS_SPLITS)} pass splits + rush · season {a.season}")
    # readout: softest slot / tightest slot defenses
    slot = sorted([(ab, teams[ab]['pass']['slot']['soft_pctl']) for ab in teams if 'slot' in teams[ab]['pass']],
                  key=lambda x: -x[1])
    print("softest vs SLOT (target):", ", ".join(f"{ab} {p}" for ab, p in slot[:5]))
    print("stingiest vs SLOT (avoid):", ", ".join(f"{ab} {p}" for ab, p in slot[-5:]))


if __name__ == '__main__':
    main()
