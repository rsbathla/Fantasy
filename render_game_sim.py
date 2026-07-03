#!/usr/bin/env python3
"""render_game_sim.py — written per-game script breakdowns from game_sim.json.
  python3 render_game_sim.py [--week N]   -> game_sim_week{N}.html
Pure formatter of the sim output; no model logic here. Distribution shown first (neutral),
then the most-likely script and who it favors (C10: notes before conclusions)."""
import json, os, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser(); ap.add_argument('--week', type=int, default=1, help='0 = every week in one document'); A = ap.parse_args()
WK = A.week
SIM = json.load(open(os.path.join(HERE, 'game_sim.json'), encoding='utf-8'))
P = SIM['_meta']['params']
# who-benefits names are attached HERE (render time) from matchup_notes, keeping game_sim.py
# free of the matchup_notes/baseline dependency that would otherwise create a cycle with dfs_model.
_MN_ALL = json.load(open(os.path.join(HERE, 'matchup_notes.json'), encoding='utf-8'))['weeks']

def who_benefits(g, wk):
    a, b = g['teams']; sc = g['script']; fav = sc['fav']; dog = sc['dog']
    mn_by = {frozenset(x.get('teams', [])): x for x in _MN_ALL.get(str(wk), {}).get('games', [])}
    gm = mn_by.get(frozenset((a, b))); sides = (gm or {}).get('sides', {})
    out = []
    if sc['fav_control_run'] >= 33:
        out.append(('%s clock-control' % fav, sc['fav_control_run'], '%s lead RB / run game' % fav, sides.get(fav, {}).get('smash', [])[:2]))
    if sc['dog_comeback_pass'] >= 40:
        out.append(('%s comeback pass' % dog, sc['dog_comeback_pass'], '%s pass-catchers' % dog, sides.get(dog, {}).get('smash', [])[:2]))
    if sc['shootout_bothpass'] >= 20:
        out.append(('shootout / bring-back', sc['shootout_bothpass'], 'both pass games + bring-back', sides.get(a, {}).get('smash', [])[:1] + sides.get(b, {}).get('smash', [])[:1]))
    if not out:
        if g['total_dist']['grind_41minus'] >= 33:
            out.append(('low-total grind', g['total_dist']['grind_41minus'], 'fade — ceilings suppressed', []))
        else:
            out.append(('competitive / both pass', g['total_dist']['over_vegas'], 'both pass games + bring-back live',
                        sides.get(a, {}).get('smash', [])[:1] + sides.get(b, {}).get('smash', [])[:1]))
    return out

def bar(segments):
    """segments = [(label, pct, color)]; returns a stacked horizontal bar + legend."""
    cells = "".join(
        f'<div class="seg" style="width:{max(p,0):.1f}%;background:{c}" title="{lab} {p:.0f}%">'
        f'{f"{p:.0f}%" if p>=11 else ""}</div>' for lab, p, c in segments if p > 0)
    leg = " · ".join(f'<span class="lg"><i style="background:{c}"></i>{lab} {p:.0f}%</span>' for lab, p, c in segments if p > 0)
    return f'<div class="barwrap"><div class="bar">{cells}</div><div class="leg">{leg}</div></div>'

ACC, ACCD, INFO, WARN, BAD, GOOD, MUT = '#2f6dbf', '#1d3a5f', '#3b8ef0', '#c8791f', '#c8456a', '#2f9e6b', '#8a97a6'

def esc(s): return (s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('**', '')

def game_block(g, wk):
    a, b = g['teams']; v = g['vegas']; s = g['sim']; w = g['winner']; td = g['total_dist']; md = g['margin_dist']
    fav = w['fav']; dog = a if fav == b else b
    line = f"O/U {v['total']:.1f} · {fav} −{v['spread']:.1f}" if v.get('spread') else f"O/U {v['total']:.1f}"
    winner_bar = bar([(f'{fav} win', w['fav_win'], ACC), (f'{dog} win', 100 - w['fav_win'], MUT)])
    total_bar = bar([('Shootout 51+', td['shootout_51plus'], BAD), ('Mid 41–51', td['mid_41_51'], INFO), ('Grind ≤41', td['grind_41minus'], MUT)])
    margin_bar = bar([('Blowout 14+', md['blowout_14plus'], ACCD), ('Comfortable 9–13', md['comfortable_9_13'], INFO),
                      ('One-score 4–8', md['one_score_4_8'], WARN), ('Nailbiter ≤3', md['nailbiter_0_3'], GOOD)])
    # narrative (strip ** bold markers -> <b>)
    narr = esc(g['_narr']).replace('Most likely:', '<b>Most likely:</b>').replace('Script read:', '<br><b>Script read:</b>')
    # who benefits (computed at render from matchup_notes + script probs)
    ben = ""
    for script_lab, p, lean, nms in who_benefits(g, wk):
        names = (" — " + ", ".join(nms)) if nms else ""
        ben += (f'<div class="ben"><span class="chip">{esc(script_lab)} · {p:.0f}%</span> '
                f'<b>{esc(lean)}</b>{esc(names)}</div>')
    pl = g['script'].get('script_pass_lean', {})
    passrow = ""
    if pl:
        cells = []
        for tm, d in pl.items():
            arrow = '▲' if d['effective'] > d['base'] else ('▼' if d['effective'] < d['base'] else '■')
            col = BAD if d['effective'] > d['base'] else (GOOD if d['effective'] < d['base'] else MUT)
            cells.append(f'<span class="pl"><b>{tm}</b> pass {d["base"]:.0f}%<span style="color:{col}"> {arrow} {d["effective"]:.0f}%</span> '
                         f'<span class="mut">(leads big {d["lead_big_p"]:.0f}% · trails {d["trail_p"]:.0f}%)</span></span>')
        passrow = '<div class="passlean">Script-adjusted pass lean: ' + " &nbsp;|&nbsp; ".join(cells) + '</div>'
    return f"""
  <div class="game">
    <div class="gh"><span class="gt">{a} vs {b}</span> <span class="gv">{line} · sim total {s['mean_total']:.1f} · ρ {s['rho']:.2f}</span></div>
    <div class="grid">
      <div class="lab">Winner</div>{winner_bar}
      <div class="lab">Total shape</div>{total_bar}
      <div class="lab">Margin shape</div>{margin_bar}
    </div>
    <p class="narr">{narr}</p>
    {passrow}
    <div class="bens">{ben}</div>
  </div>"""

if WK == 0:
    weeks = sorted(SIM['weeks'].keys(), key=int)
    blocks = "\n".join(f'<h2 class="wkh">Week {w}</h2>\n' + "\n".join(game_block(g, int(w)) for g in SIM['weeks'][w]['games']) for w in weeks)
    title = "All 18 Weeks"; head_wk = "Every Game, Every Week"
else:
    weeks = [str(WK)]
    blocks = "\n".join(game_block(g, WK) for g in SIM['weeks'][str(WK)]['games'])
    title = f"Week {WK}"; head_wk = f"Week {WK} — How Each Game Plays Out"
html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{title} · Game-Script Sim</title>
<style>
:root{{--bg:#f5f7fa;--surface:#fff;--surface-2:#eef2f7;--text:#16202c;--muted:#5a6b7d;--line:#d7dde6;--accent:#2f6dbf;--accent-soft:#4ea1ff;}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--text);
font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;font-size:16px;line-height:1.6}}
.wrap{{max-width:900px;margin:0 auto;padding:0 22px 90px}}
.sheet{{background:var(--surface);margin-top:26px;border:1px solid var(--line);border-radius:12px;padding:42px 50px 48px;box-shadow:0 1px 3px rgba(20,40,60,.05)}}
.kicker{{font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--accent);font-weight:700;margin:0 0 6px}}
h1{{font-size:38px;line-height:1.08;letter-spacing:-.02em;margin:0 0 10px;font-weight:800}}
.dateline{{color:var(--muted);font-size:14.5px;margin:0 0 20px}}
.rule{{height:4px;background:linear-gradient(90deg,var(--accent),var(--accent-soft));border-radius:2px;margin:0 0 22px}}
.method{{background:var(--surface-2);border-radius:8px;padding:16px 20px;font-size:13.5px;color:#2b3742;margin:0 0 10px}}
.method b{{color:var(--text)}}
.game{{padding:20px 0 18px;border-bottom:1px solid var(--line)}} .game:last-child{{border-bottom:none}}
.gh{{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin-bottom:12px}}
.gt{{font-size:20px;font-weight:800;letter-spacing:-.01em}} .gv{{color:var(--muted);font-weight:600;font-size:13.5px;font-variant-numeric:tabular-nums}}
.grid{{display:grid;grid-template-columns:92px 1fr;gap:7px 12px;align-items:center;margin-bottom:12px}}
.lab{{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:700;text-align:right}}
.barwrap{{}} .bar{{display:flex;height:22px;border-radius:5px;overflow:hidden;background:var(--surface-2)}}
.seg{{display:flex;align-items:center;justify-content:center;color:#fff;font-size:11px;font-weight:800;min-width:0;transition:none}}
.leg{{margin-top:3px;font-size:11px;color:var(--muted)}} .lg{{margin-right:2px}} .lg i{{display:inline-block;width:8px;height:8px;border-radius:2px;margin-right:3px;vertical-align:middle}}
.narr{{font-size:15px;line-height:1.55;margin:12px 0 8px}}
.passlean{{font-size:12.5px;color:var(--muted);background:var(--surface-2);border-radius:6px;padding:8px 12px;margin:8px 0}}
.pl{{white-space:nowrap}} .mut{{color:#9aa3b6}}
.bens{{margin-top:8px}} .ben{{font-size:13.5px;margin:4px 0}}
.chip{{display:inline-block;font-size:10.5px;font-weight:800;letter-spacing:.03em;padding:2px 8px;border-radius:999px;background:#e7f0fb;color:var(--accent);border:1px solid #c6ddf5;margin-right:6px}}
.wkh{{font-size:26px;font-weight:800;color:#fff;background:var(--accent);border-radius:8px;padding:8px 16px;margin:34px 0 6px;letter-spacing:-.01em}}
@media print{{body{{background:#fff}}.sheet{{border:none;box-shadow:none;margin:0;padding:0}}.game{{break-inside:avoid}}.wkh{{break-before:page}}}}
</style></head><body><div class="wrap"><div class="sheet">
  <p class="kicker">2026 DFS · Game-Script Monte Carlo</p>
  <h1>{head_wk}</h1>
  <p class="dateline">{P['N_SIM']:,} sims/game · Vegas-anchored means &amp; win probability · offseason edition</p>
  <div class="rule"></div>
  <div class="method"><b>How to read this.</b> Each game is simulated {P['N_SIM']:,} times. The two things that are
  <b>real</b>: the team means come from the posted Vegas implied totals, and the spread calibrates the win
  probability (a −7.5 favorite wins ~72% here because that is what the market implies). Everything shaped on top —
  the spread of outcomes (SD {P['SIGMA_TEAM']}, ceiling-modulated), the two teams' co-movement (ρ rising with the
  total), and the pass/run script shifts — are <b>stated priors</b> anchored to NFL-empirical dispersion, not fit to
  2026 results (none exist yet). So trust the <i>ordering and the shape</i>; treat any single percentage as
  "what these assumptions imply," not a measured frequency. The distribution is shown first; the most-likely script
  read follows it.</div>
{blocks}
</div></div></body></html>"""

fn_out = 'game_sim_all.html' if WK == 0 else f'game_sim_week{WK}.html'
out = os.path.join(HERE, fn_out)
open(out, 'w', encoding='utf-8').write(html)
ngames = sum(len(SIM['weeks'][w]['games']) for w in weeks)
print(f"{fn_out}: {ngames} games across {len(weeks)} week(s), {len(html):,} bytes")
