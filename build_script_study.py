#!/usr/bin/env python3
"""build_script_study.py — 2025 POSITION x VEGAS-SCRIPT empirical study -> script_study.html

Answers: how does each position ACTUALLY score given the Vegas situation, and — critically —
how much of that is game script vs just team quality (which the play score already prices via the
implied total)? Joins 2025 actual fantasy (boom/gamelog.json) to nflverse closing lines
(data/nflverse/games_2021_2025.csv). Pure analysis; no fabrication. This is the backtest that
revealed the stated-prior script_mult was mis-signed (see dfs_model.py revert note).
"""
import json, csv, os
import numpy as np, pandas as pd
import core
fn = core.fn
HERE = os.path.dirname(os.path.abspath(__file__))
POSSET = ['QB', 'RB', 'WR', 'TE']

# ---------------- assemble player-game x vegas-script table ----------------
POS = {fn(r['name']): r['pos'] for r in csv.DictReader(open(os.path.join(HERE, 'features.csv'), encoding='utf-8'))}
g = pd.read_csv(os.path.join(HERE, 'data/nflverse/games_2021_2025.csv'))
g = g[(g.season == 2025) & g.home_score.notna() & g.spread_line.notna()]
NORM = {'LA': 'LAR', 'SD': 'LAC', 'OAK': 'LV', 'WSH': 'WAS', 'STL': 'LAR', 'JAC': 'JAX'}
def nmf(t): return NORM.get(t, t)
GM = {}
for _, r in g.iterrows():
    GM[(int(r.week), nmf(r.home_team))] = (r.spread_line, r.total_line)
    GM[(int(r.week), nmf(r.away_team))] = (-r.spread_line, r.total_line)
gl = json.load(open(os.path.join(HERE, 'boom/gamelog.json')))
rows = []
for pk, games in gl.items():
    pos = POS.get(fn(pk))
    if pos not in POSSET: continue
    for e in games:
        opp = nmf(str(e.get('opp', '')).upper()); wk = e.get('wk'); act = e.get('act')
        if act is None or (wk, opp) not in GM: continue
        spr, tot = GM[(wk, opp)]; ps = -spr
        rows.append((pos, ps, tot, (tot + ps) / 2.0, act))
df = pd.DataFrame(rows, columns=['pos', 'spread', 'total', 'implied', 'act'])
BASE = {p: df[df.pos == p].act.mean() for p in POSSET}
P80 = {p: df[df.pos == p].act.quantile(0.80) for p in POSSET}
N_PG = len(df)

def fav_tier(s):
    return '10+' if s >= 10 else ('7-10' if s >= 7 else ('3-7' if s >= 3 else ('pick-em' if s > -3 else ('dog 3-7' if s > -7 else 'dog 7+'))))
def tot_tier(t):
    return 'shootout 49+' if t >= 49 else ('high 46-49' if t >= 46 else ('mid 43-46' if t >= 43 else 'low <43'))
df['fav'] = df.spread.apply(fav_tier); df['ttier'] = df.total.apply(tot_tier)
FAV_ORDER = ['10+', '7-10', '3-7', 'pick-em', 'dog 3-7', 'dog 7+']
TOT_ORDER = ['shootout 49+', 'high 46-49', 'mid 43-46', 'low <43']

def cell(sub, p):
    if len(sub) < 8: return None
    return {'n': len(sub), 'mean': round(sub.act.mean(), 1),
            'lift': round((sub.act.mean() / BASE[p] - 1) * 100),
            'boom': round((sub.act >= P80[p]).mean() * 100)}

FAV = {p: {b: cell(df[(df.pos == p) & (df.fav == b)], p) for b in FAV_ORDER} for p in POSSET}
TOT = {p: {b: cell(df[(df.pos == p) & (df.ttier == b)], p) for b in TOT_ORDER} for p in POSSET}

# isolation: residual after linear fit on implied total, by favorite tier
ISO = {}
for p in POSSET:
    d = df[df.pos == p].copy(); b = np.polyfit(d.implied, d.act, 1); d['resid'] = d.act - np.polyval(b, d.implied)
    ISO[p] = {ft: (round(d[d.fav == ft].resid.mean(), 1) if (d.fav == ft).sum() >= 10 else None) for ft in FAV_ORDER}

# ---------------- render ----------------
def liftcol(v):
    if v is None: return '#8a97a6'
    return '#2f9e6b' if v >= 5 else ('#c8456a' if v <= -5 else '#5a6b7d')

def fav_table(D, title, iso=None):
    h = f'<h3>{title}</h3><table><thead><tr><th>Vegas tier</th>' + ''.join(f'<th>{p}</th>' for p in POSSET)
    if iso: h += '<th class="iso">script resid*</th>'
    h += '</tr></thead><tbody>'
    for b in FAV_ORDER:
        h += f'<tr><td class="tier">{b}</td>'
        for p in POSSET:
            c = D[p][b]
            if c: h += f'<td><b>{c["mean"]}</b> <span style="color:{liftcol(c["lift"])}">({c["lift"]:+d}%)</span><br><span class="boom">boom {c["boom"]}%</span></td>'
            else: h += '<td class="na">—</td>'
        if iso:
            vals = [iso[p][b] for p in POSSET if iso[p][b] is not None]
            avg = round(np.mean(vals), 1) if vals else None
            col = '#c8456a' if (avg is not None and avg < -0.4) else ('#2f9e6b' if (avg is not None and avg > 0.4) else '#5a6b7d')
            h += f'<td class="iso" style="color:{col}">{avg:+.1f}</td>' if avg is not None else '<td class="iso na">—</td>'
        h += '</tr>'
    return h + '</tbody></table>'

def tot_table():
    h = '<h3>By game total (the environment axis)</h3><table><thead><tr><th>Total tier</th>' + ''.join(f'<th>{p}</th>' for p in POSSET) + '</tr></thead><tbody>'
    for b in TOT_ORDER:
        h += f'<tr><td class="tier">{b}</td>'
        for p in POSSET:
            c = TOT[p][b]
            h += (f'<td><b>{c["mean"]}</b> <span style="color:{liftcol(c["lift"])}">({c["lift"]:+d}%)</span><br><span class="boom">boom {c["boom"]}%</span></td>' if c else '<td class="na">—</td>')
        h += '</tr>'
    return h + '</tbody></table>'

hd = FAV['RB']['10+']; hw = FAV['WR']['10+']; hq = FAV['QB']['10+']
html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>2025 Position x Vegas-Script Study</title><style>
:root{{--bg:#f5f7fa;--surface:#fff;--surface-2:#eef2f7;--text:#16202c;--muted:#5a6b7d;--line:#d7dde6;--accent:#2f6dbf;--accent-soft:#4ea1ff}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;font-size:16px;line-height:1.6}}
.wrap{{max-width:900px;margin:0 auto;padding:0 22px 90px}}.sheet{{background:var(--surface);margin-top:26px;border:1px solid var(--line);border-radius:12px;padding:42px 50px 48px;box-shadow:0 1px 3px rgba(20,40,60,.05)}}
.kicker{{font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--accent);font-weight:700;margin:0 0 6px}}h1{{font-size:34px;line-height:1.1;letter-spacing:-.02em;margin:0 0 10px;font-weight:800}}
.dateline{{color:var(--muted);font-size:14px;margin:0 0 20px}}.rule{{height:4px;background:linear-gradient(90deg,var(--accent),var(--accent-soft));border-radius:2px;margin:0 0 22px}}
.lead{{font-size:17px;margin:0 0 6px}}h2{{font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);font-weight:700;margin:36px 0 4px;padding-top:20px;border-top:1px solid var(--line)}}
h2 .sub{{display:block;text-transform:none;letter-spacing:normal;font-size:22px;color:var(--text);font-weight:800;margin-top:6px}}h3{{font-size:15px;margin:20px 0 6px;font-weight:800}}
p{{margin:10px 0}}.method{{background:var(--surface-2);border-radius:8px;padding:14px 18px;font-size:13.5px;color:#2b3742;margin:0 0 8px}}.method b{{color:var(--text)}}
table{{width:100%;border-collapse:collapse;margin:8px 0 6px;font-size:13px}}th{{text-align:left;color:var(--muted);font-weight:700;font-size:10.5px;letter-spacing:.05em;text-transform:uppercase;padding:6px 8px;border-bottom:2px solid var(--line)}}
td{{padding:7px 8px;border-bottom:1px solid var(--line);vertical-align:top;font-variant-numeric:tabular-nums}}td.tier{{font-weight:800;color:var(--text)}}.boom{{color:var(--muted);font-size:11px}}.na{{color:#c3ccd6}}
.iso{{background:#f7f9fc;font-weight:800;text-align:center}}.callout{{background:#fbf3e6;border-left:4px solid #c8791f;border-radius:6px;padding:14px 18px;margin:14px 0;font-size:14.5px}}
.callout b{{color:#8a5316}}@media print{{body{{background:#fff}}.sheet{{border:none;box-shadow:none;margin:0;padding:0}}table,.callout{{break-inside:avoid}}}}
</style></head><body><div class="wrap"><div class="sheet">
<p class="kicker">2026 DFS · Empirical Validation</p><h1>Position × Vegas-Script Study — 2025</h1>
<p class="dateline">{N_PG:,} player-games · actual fantasy scoring joined to nflverse closing lines · single season</p><div class="rule"></div>
<p class="lead">Does each position score the way the Vegas situation says it should — and is "game script" a real edge, or just team quality wearing a costume? This is the backtest behind the sim's script logic.</p>
<div class="method"><b>Method.</b> Every 2025 player-game (boom/gamelog.json, actual fantasy points) is tagged with its team's closing Vegas spread and total (nflverse). "Boom" = a top-20% game for that position (so 20% is the neutral baseline). The last column of each table is the key one — the <b>script residual</b>: each position's scoring after removing what its implied team total predicts. A positive residual means a genuine script tailwind; ~0 means it was all team quality (which the play score already prices via the implied total). One season, so read the shape, not the third decimal.</div>

<h2>The headline<span class="sub">"When a team is a 10+ favorite, do RBs outscore?"</span></h2>
<p>Not exactly — but they benefit the most in relative terms. As a 10+ favorite, <b>RBs get the biggest lift ({hd['lift']:+d}%</b> vs their baseline, to {hd['mean']} pts, booming {hd['boom']}% of the time), more than WRs ({hw['lift']:+d}%) and even QBs ({hq['lift']:+d}%) in percentage terms. But QBs still <i>outscore</i> RBs in raw points ({hq['mean']} vs {hd['mean']}) because QBs always do. So the honest answer: a big favorite lifts its whole offense, and RBs gain the most relative to their own norm — but that lift is mostly the offense being good, not the run script itself, as the residual column below shows.</p>

<h2>The full board<span class="sub">Every position, every Vegas tier</span></h2>
{fav_table(FAV, 'By spread (favorite → underdog)', iso=ISO)}
<p style="font-size:12px;color:#5a6b7d">*Script residual = average points above/below what the team's implied total predicts, across the four positions. Negative = the tier's skill players underperform their total (blow-out starter-rest); positive = a real script tailwind beyond team quality.</p>
{tot_table()}

<h2>What it means<span class="sub">Script is mostly team quality — and the wiring was wrong</span></h2>
<div class="callout"><b>The finding that changed the model.</b> Once you remove implied total, the pure script residual for <b>favorites is negative</b> (a 10+ favorite RB scores {ISO['RB']['10+']:+.1f} vs its team total — blow-out rest caps the volume), and the only positive residuals are <b>dog pass-catchers</b> (WR {ISO['WR']['dog 3-7']:+.1f} as a small dog — the real, but small, garbage-time effect). So the <code>script_mult</code> that boosted favored RBs was double-counting implied total and pointing the wrong way. It's been <b>reverted to zero</b>, and the properly-signed, PROE-calibrated version will be rebuilt with this exact isolation method.</p></div>
<p><b>What holds up:</b> the environment axis. Shootouts (49+) lift everyone, WRs most (+{TOT['WR']['shootout 49+']['lift']}%); low totals (&lt;43) crush skill players but not TEs (+{TOT['TE']['low <43']['lift']}%, matchup/red-zone driven). That is real and is already captured through the implied total in the play score — which is exactly why the incremental script term added little.</p>
<p><b>The takeaway for the sim:</b> implied total does the heavy lifting; game script is a small, second-order residual that only clearly favors dog pass-catchers and slightly penalizes blow-out-favorite skill players. The PROE work will measure that residual per team (coach tendency) rather than assume it.</p>
</div></div></body></html>"""

out = os.path.join(HERE, 'script_study.html')
open(out, 'w', encoding='utf-8').write(html)
json.dump({'n_player_games': N_PG, 'fav': FAV, 'tot': TOT, 'iso': ISO, 'baseline': BASE,
           '_meta': {'source': 'boom/gamelog.json (2025 actuals) x data/nflverse/games_2021_2025.csv closing lines',
                     'surfaces': ['dfs']}}, open(os.path.join(HERE, 'script_study.json'), 'w'), indent=1, default=str)
print(f"script_study.html + .json: {N_PG} player-games | 10+ fav RB lift {hd['lift']:+d}% | RB script resid @10+ = {ISO['RB']['10+']:+.1f}")
