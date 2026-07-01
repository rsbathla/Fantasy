#!/usr/bin/env python3
"""Build draft_board_signals.csv -- one row per ADP'd 2026 player with projection/ceiling/spike.

Root-cause fix (was: silent join misses): projections are joined via the ONE shared name resolver
(core.resolve), which recovers first-name variants the old exact-match dropped -- "Kenneth Walker III"
<-> Clay "Ken Walker III", "Cam Ward" <-> "Cameron Ward", "Chig Okonkwo" <-> "Chigoziem Okonkwo" --
while STILL refusing unsafe guesses (Keenan != Kaytron). Players genuinely absent from Clay get a
projection imputed from a position-aware, isotonic ADP->proj curve (proj_src='adp_curve'); anyone left
without one is written to a join report so a miss is never silent again. Robust to absent optional
inputs (schedule / blow-up / merged-rank files) so a partial data drop can't crash the build."""
import os, sys, json, glob, bisect
import pandas as pd, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
if REPO not in sys.path:
    sys.path.insert(0, REPO)
import core


def _read_adp():
    """ADP universe: a present DkPreDraftRankings*.csv if one exists, else the canonical dk_adp.csv."""
    hits = [h for q in (f"{REPO}/DkPreDraftRankings*.csv", f"{REPO}/uploads/DkPreDraftRankings*.csv")
            for h in glob.glob(q)]
    df = pd.read_csv(max(hits, key=os.path.getmtime)) if hits else pd.read_csv(os.path.join(REPO, 'dk_adp.csv'))
    df = df[['Name', 'Position', 'ADP', 'Team']].dropna(subset=['ADP']).copy()
    df['Team'] = df['Team'].replace({'LA': 'LAR'})
    return df


def _index(df, pos_col='pos'):
    return core.build_name_index((r['name'], r.get(pos_col)) for _, r in df.iterrows())


def _schedule():
    def _load(name):
        p = os.path.join(HERE, name)
        return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}
    byes, gbw = _load('byes_2026.json'), _load('games_by_week.json')
    sched = {w: {} for w in (15, 16, 17)}; games17 = {}
    for w in (15, 16, 17):
        for a, b in [tuple(g) for g in gbw.get(str(w), [])]:
            sched[w][a] = b; sched[w][b] = a
            if w == 17:
                games17[a] = games17[b] = f"{a}@{b}"
    return byes, sched, games17


def _blowup():
    p = os.path.join(HERE, 'w17_blowup_rank.csv')
    out = {}
    if os.path.exists(p):
        for _, r in pd.read_csv(p).iterrows():
            for tm in str(r['game']).split('+'):
                out[tm] = int(r['p99_rank'])
    return out


def _merged_ranks():
    p = os.path.join(HERE, 'merged_rankings_upload.csv')
    if not os.path.exists(p):
        return {}
    m = pd.read_csv(p).dropna(subset=['Name'])
    rank = {}
    for i, (_, r) in enumerate(m.iterrows(), 1):
        rank.setdefault(core.fn(r['Name']), i)
    return rank


def _impute_proj(B):
    """Fill proj_pg for clay-absent players from a per-position isotonic (non-increasing) ADP->proj
    curve fit on players who have both; global fallback where a position is thin. Returns count."""
    by = {}
    for _, r in B[B.proj_pg.notna() & B.adp.notna()].iterrows():
        by.setdefault(r['pos'], []).append((float(r['adp']), float(r['proj_pg'])))
    anchors = {}
    for pos, prs in by.items():
        prs.sort(); a = [x for x, _ in prs]; p = [y for _, y in prs]
        for i in range(1, len(p)):
            p[i] = min(p[i], p[i - 1])
        anchors[pos] = (a, p)
    allp = sorted(x for pp in by.values() for x in pp)
    ga = [x for x, _ in allp]; gp = [y for _, y in allp]
    for i in range(1, len(gp)):
        gp[i] = min(gp[i], gp[i - 1])

    def interp(a, p, x):
        if not a:
            return None
        if x <= a[0]:
            return p[0]
        if x >= a[-1]:
            return p[-1]
        j = bisect.bisect_left(a, x)
        return p[j - 1] + (p[j] - p[j - 1]) * (x - a[j - 1]) / (a[j] - a[j - 1]) if a[j] != a[j - 1] else p[j - 1]

    n = 0
    for i, r in B.iterrows():
        if pd.isna(r['proj_pg']) and pd.notna(r['adp']):
            a, p = anchors.get(r['pos'], (None, None))
            v = interp(a, p, float(r['adp'])) if a else interp(ga, gp, float(r['adp']))
            if v is not None:
                B.at[i, 'proj_pg'] = round(float(v), 2); B.at[i, 'proj_src'] = 'adp_curve'; n += 1
    return n


def main():
    adp = _read_adp()
    clay = pd.read_csv(os.path.join(HERE, 'clay_2026.csv'))
    sim = pd.read_csv(os.path.join(HERE, 'player_sim_distributions.csv'))
    clay_idx, sim_idx = _index(clay), _index(sim)
    clay_row = {r['name']: r for _, r in clay.iterrows()}
    sim_row = {r['name']: r for _, r in sim.iterrows()}
    byes, sched, games17 = _schedule(); blow = _blowup(); mrank = _merged_ranks()

    stats = {'clay_exact': 0, 'clay_canon': 0, 'clay_missing': 0, 'sim_hit': 0}
    misses = []; rows = []
    for _, a in adp.iterrows():
        nm, pos, tm = a['Name'], a['Position'], a['Team']
        cn = core.resolve(nm, pos, clay_idx)
        sn = core.resolve(nm, pos, sim_idx)
        proj = float(clay_row[cn]['dk_pg']) if cn is not None and pd.notna(clay_row[cn]['dk_pg']) else np.nan
        if cn is not None:
            stats['clay_exact' if core.fn(cn) == core.fn(nm) else 'clay_canon'] += 1
        else:
            stats['clay_missing'] += 1; misses.append((nm, pos, tm))
        p95 = cv = spike = np.nan
        if sn is not None:
            s = sim_row[sn]; stats['sim_hit'] += 1
            p95 = float(s['p95']) if pd.notna(s['p95']) else np.nan
            cv = float(s['cv']) if pd.notna(s['cv']) else np.nan
            spike = float(s['spike_pct']) if pd.notna(s['spike_pct']) else np.nan
        rows.append(dict(name=nm, pos=pos, team=tm, adp=float(a['ADP']),
                         proj_pg=proj, p95=p95, cv=cv, spike=spike,
                         proj_src=('clay' if cn is not None else None),
                         bye=byes.get(tm), w15_opp=sched[15].get(tm), w16_opp=sched[16].get(tm),
                         w17_game=games17.get(tm), w17_blowup_rank=blow.get(tm, 99),
                         merged_rank=mrank.get(core.fn(nm))))
    B = pd.DataFrame(rows)
    n_imp = _impute_proj(B)
    for col, new in [('proj_pg', 'adv_pct'), ('p95', 'ceil_pct')]:
        B[new] = B.groupby('pos')[col].rank(pct=True)
    B = B[['name', 'pos', 'team', 'adp', 'proj_pg', 'p95', 'cv', 'spike', 'bye', 'w15_opp',
           'w16_opp', 'w17_game', 'w17_blowup_rank', 'adv_pct', 'ceil_pct', 'merged_rank', 'proj_src']]
    # Write to the REPO ROOT, where run_live/_load_signals and the other consumers read it (inputs are
    # read HERE-relative from pipeline/, so this is cwd-independent and single-sourced).
    B.to_csv(os.path.join(REPO, 'draft_board_signals.csv'), index=False)

    still = stats['clay_missing'] - n_imp
    rep = os.path.join(HERE, 'draft_board_join_report.txt')
    with open(rep, 'w', encoding='utf-8') as f:
        f.write(f"draft_board_signals.csv — join report ({len(B)} players)\n")
        f.write(f"clay proj : exact={stats['clay_exact']}  canon-recovered={stats['clay_canon']}  "
                f"imputed(adp_curve)={n_imp}  still-blank={still}\n")
        f.write(f"sim p95   : hit={stats['sim_hit']}  blank={len(B) - stats['sim_hit']}\n\n")
        f.write("players with NO Clay projection (imputed from ADP curve unless noted):\n")
        for nm, pos, tm in sorted(misses):
            f.write(f"  {nm} ({pos}, {tm})\n")
    print(f"draft_board_signals.csv: {len(B)} players | clay exact {stats['clay_exact']} "
          f"+canon {stats['clay_canon']} +imputed {n_imp} (still-blank {still}) | sim {stats['sim_hit']} "
          f"| report: {os.path.basename(rep)}")


if __name__ == '__main__':
    main()
