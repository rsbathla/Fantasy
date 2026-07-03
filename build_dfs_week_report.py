#!/usr/bin/env python3
"""build_dfs_week_report.py — a polished SINGLE-WEEK DFS report in the design-system palette
(ui/COMPONENTS.md).

Reproducible AND grounded: it does not free-write. It reuses the prose helpers from
build_dfs_weekly_breakdown.py (upside_paragraph, game_prose, stack_templates) — where every factual
clause traces to a pulled data field — and lays them into the HTML report template. It surfaces the
validated PROE pass/run conversion (dfs_model.proe_convert) as a per-player lever pill.

    python3 build_dfs_week_report.py --week 1   ->  dfs_week1_report.html
"""
import argparse
import html
import json
import os
import re

import build_dfs_weekly_breakdown as bd   # reuse the grounded data + prose helpers

HERE = os.path.dirname(os.path.abspath(__file__))
POSCOLOR = {'QB': 'var(--qb)', 'RB': 'var(--rb)', 'WR': 'var(--wr)', 'TE': 'var(--te)'}
TEAM_FULL = bd.TEAM_FULL


def _soft_phrase(p):
    """Translate a defensive-softness percentile into plain English (numbers kept)."""
    if p is None:
        return None
    p = int(p)
    if p <= 6:   return f"{bd.ordinal(p)}-percentile — one of the very softest in the league"
    if p <= 15:  return f"{bd.ordinal(p)}-percentile — among the softest in the league"
    if p <= 30:  return f"{bd.ordinal(p)}-percentile — soft and exploitable"
    if p <= 45:  return f"{bd.ordinal(p)}-percentile — a shade below average"
    return None


def _parse_attack(attack):
    """Pull the structured softness signals out of the terse attack string."""
    d = {'pass': None, 'run': None, 'te_soft': False, 'wr_fortress': False, 'shift': None}
    if not attack:
        return d
    m = re.search(r'pass_cov_pctl=(\d+)', attack); d['pass'] = int(m.group(1)) if m else None
    m = re.search(r'run_def_pctl=(\d+)', attack); d['run'] = int(m.group(1)) if m else None
    d['te_soft'] = 'soft vs TE' in attack
    d['wr_fortress'] = 'WR fortress' in attack
    m = re.search(r'shifted from (\w+) . (\w+)', attack)
    d['shift'] = (m.group(1), m.group(2)) if m else None
    return d


def _first_names(names, n=2):
    return names[:n]


def holistic_game_narrative(mn, sim):
    """A plain-English 'here is what is happening' read that surfaces the sim output and ties the
    projected script to who benefits — numbers kept, jargon translated."""
    teams = sim['teams']
    veg = sim['vegas']; fav = veg['spread_fav']
    dog = teams[0] if teams[1] == fav else teams[1]
    imp, total, spread = veg['imp'], veg['total'], veg['spread']
    win, td, md, scr = sim['winner'], sim['total_dist'], sim['margin_dist'], sim['script']
    pl = scr.get('script_pass_lean', {})
    S = []

    # 1. the setup — who the market favors and by how much
    S.append(f"<b>The setup.</b> {TEAM_FULL.get(fav, fav)} is implied for {bd.f1(imp.get(fav))} and "
             f"favored by {bd.f1(spread)}; {TEAM_FULL.get(dog, dog)} sits at {bd.f1(imp.get(dog))}. "
             f"Posted total {bd.f1(total)}" +
             (f", which our ceiling blend nudges to {bd.f1(mn.get('blend'))}." if mn.get('blend') else "."))

    # 2. the sim read — the holistic 40k-sim output in plain language
    shoot, ov = td.get('shootout_51plus', 0), td.get('over_vegas', 0)
    blow, nail = md.get('blowout_14plus', 0), md.get('nailbiter_0_3', 0)
    shape = ("a shootout" if shoot >= 40 else "a mid-range game" if shoot >= 28 else "a lower-scoring grind")
    control = ("controls the game more than it buries it" if blow < 35
               else "has real blowout equity")
    S.append(f"<b>How the sim sees it.</b> Run 40,000 times, this profiles as {shape} — it clears 51 "
             f"points {shoot:.0f}% of the time and tops the posted total in {ov:.0f}%. {fav} wins "
             f"{win.get(fav, 0):.0f}% of sims, but it's a two-score blowout in only {blow:.0f}% and a "
             f"one-score game or closer in { md.get('one_score_4_8',0)+nail:.0f}%, so {fav} {control}.")

    # 3. the script -> who benefits (the payoff: sim script x PROE conversion)
    fcr, dcp = scr.get('fav_control_run', 0), scr.get('dog_comeback_pass', 0)
    fav_pass = (bd.PT.get(fav, {}) or {}).get('proe_2026')
    fav_lean = 'pass-lean' if (fav_pass or 0) > 1 else ('run-lean' if (fav_pass or 0) < -1 else 'balanced')
    script_bit = (f"<b>The script, and who it feeds.</b> The most common path is {fav} pulling ahead "
                  f"({fcr:.0f}% of sims lead-and-control) while {dog} trails and throws to catch up "
                  f"({dcp:.0f}%). ")
    if (fav_pass or 0) > 2:
        script_bit += (f"But {fav} is {fav_lean} (PROE {fav_pass:+.0f}) — one of the offenses that keeps "
                       f"throwing even with a lead, so the fantasy stays with the passing game rather than "
                       f"the back even in a control script. ")
    elif (fav_pass or 0) < -2:
        script_bit += (f"And {fav} is {fav_lean} (PROE {fav_pass:+.0f}), so a lead means the back eats "
                       f"clock-killing carries — the RB is the script's biggest beneficiary. ")
    script_bit += f"{dog} trailing and passing is what puts its receivers in play as a bring-back."
    S.append(script_bit)

    # 4. how to attack — translate the matchup softness, name the plays
    sides = mn.get('sides') or {}
    for side, blk in sides.items():
        a = _parse_attack(blk.get('attack', ''))
        offid = blk.get('off_id', ''); pace = blk.get('pace', '')
        sm = _first_names(blk.get('smash') or [])
        pieces = []
        sp = _soft_phrase(a['pass'])
        if sp:
            pieces.append(f"a secondary grading {sp}")
        if a['te_soft']:
            pieces.append("a defense that leaks to tight ends")
        sr = _soft_phrase(a['run'])
        if sr and not sp:
            pieces.append(f"a run defense grading {sr}")
        opp = dog if side == fav else fav
        if pieces:
            seg = (f"<b>{side}</b> ({offid}, {pace} pace) attacks {'; '.join(pieces)}")
            if a['shift']:
                seg += f" (that {opp} defense has shifted {a['shift'][0].lower()}→{a['shift'][1].lower()} on the carousel)"
            if sm:
                seg += f" — the plays are {', '.join(sm)}"
            if a['wr_fortress']:
                seg += "; note their WRs are muted (opponent locks the perimeter), so it is a TE/RB read"
            S.append(seg + ".")

    # 5. the build
    if mn.get('stack_take'):
        S.append(f"<b>Build.</b> {mn['stack_take']}.")
    return " ".join(S)


def sim_strip(sim):
    """A glanceable row of the key 40k-sim numbers."""
    win, td, md, scr = sim['winner'], sim['total_dist'], sim['margin_dist'], sim['script']
    fav, dog = scr.get('fav'), scr.get('dog')

    def chip(lbl, val, cls=''):
        return f'<span class="chip {cls}"><span class="cl">{lbl}</span>{val}</span>'

    c = [
        chip(f'{fav} win', f"{win.get(fav, 0):.0f}%"),
        chip('shootout 51+', f"{td.get('shootout_51plus', 0):.0f}%",
             'good' if td.get('shootout_51plus', 0) >= 40 else ''),
        chip('blowout 14+', f"{md.get('blowout_14plus', 0):.0f}%"),
        chip('nailbiter ≤3', f"{md.get('nailbiter_0_3', 0):.0f}%"),
        chip(f'{fav} control-run', f"{scr.get('fav_control_run', 0):.0f}%"),
        chip(f'{dog} comeback-pass', f"{scr.get('dog_comeback_pass', 0):.0f}%"),
    ]
    return '<div class="simstrip">' + ''.join(c) + '</div>'


def md_b(s):
    """Render a prose string: **bold** -> <b>, everything else HTML-escaped."""
    out, i = [], 0
    for m in re.finditer(r'\*\*(.+?)\*\*', s):
        out.append(html.escape(s[i:m.start()]))
        out.append('<b>' + html.escape(m.group(1)) + '</b>')
        i = m.end()
    out.append(html.escape(s[i:]))
    return ''.join(out)


def conv_pill(p):
    """A small colored pill for the pass/run conversion multiplier; '' if negligible."""
    pm = p.get('proe_mult')
    if pm is None or abs(pm - 1.0) < 0.015:
        return ''
    pct = (pm - 1.0) * 100
    cls = 'good' if pm > 1 else 'bad'
    arrow = '▲' if pm > 1 else '▼'
    return f'<span class="pill {cls}">conv {arrow} ×{pm:.2f} ({pct:+.0f}%)</span>'


def env_adj_pill(g):
    bl, tot = g.get('blend'), g.get('total')
    if bl is None or tot is None:
        return ''
    d = bl - tot
    if abs(d) < 0.05:
        return ''
    cls = 'good' if d > 0 else 'muted'
    return f'<span class="pill {cls}">ceiling adj {d:+.1f}</span>'


STYLE = """
:root{
  --bg:#f5f7fa;--surface:#ffffff;--surface-2:#eef2f7;
  --text:#16202c;--muted:#5a6b7d;--muted-2:#8a97a6;--line:#d7dde6;
  --accent:#2f6dbf;--accent-soft:#4ea1ff;--good:#2f9e6b;--warn:#c8791f;--bad:#c8456a;--info:#3b8ef0;
  --qb:#e0567a;--rb:#37b87a;--wr:#3b8ef0;--te:#e8a33d;
  --radius:12px;--radius-sm:6px;
  --font:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:var(--font);
  font-size:16px;line-height:1.62;-webkit-font-smoothing:antialiased}
.wrap{max-width:900px;margin:0 auto;padding:0 22px 96px}
.sheet{background:var(--surface);margin-top:26px;border:1px solid var(--line);
  border-radius:var(--radius);padding:44px 52px 52px;box-shadow:0 1px 3px rgba(20,40,60,.05)}
.kicker{font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--accent);
  font-weight:700;margin:0 0 6px}
h1{font-size:40px;line-height:1.08;letter-spacing:-.02em;margin:0 0 10px;font-weight:800}
.dateline{color:var(--muted);font-size:14.5px;margin:0 0 20px}
.rule{height:4px;background:linear-gradient(90deg,var(--accent),var(--accent-soft));
  border-radius:2px;margin:0 0 26px;width:100%}
.lead{font-size:18.5px;line-height:1.6;color:#25323f;margin:0 0 8px}
h2{font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);
  font-weight:700;margin:46px 0 4px;padding-top:22px;border-top:1px solid var(--line)}
h2 .sub{display:block;text-transform:none;letter-spacing:normal;font-size:24px;
  color:var(--text);font-weight:800;margin-top:7px;line-height:1.2}
p{margin:11px 0}
.muted{color:var(--muted)}
.callout{background:var(--surface-2);border:1px solid var(--line);border-left:4px solid var(--accent);
  border-radius:var(--radius-sm);padding:16px 20px;margin:20px 0;font-size:15px}
.callout b{color:var(--text)}
.env{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;padding:12px 0;border-bottom:1px solid var(--line)}
.env .g{font-weight:800;font-size:17px}
.env .n{color:var(--accent);font-weight:700}
.card{border:1px solid var(--line);border-radius:var(--radius);padding:16px 20px;margin:14px 0;
  background:var(--surface)}
.card .hd{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:4px}
.rankno{font-size:13px;font-weight:800;color:var(--muted-2);min-width:26px}
.pname{font-size:18px;font-weight:800;letter-spacing:-.01em}
.pos{font-size:11px;font-weight:800;color:#fff;padding:2px 7px;border-radius:20px;letter-spacing:.02em}
.play{margin-left:auto;font-weight:800;font-size:16px;color:var(--accent)}
.play .lbl{font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted-2);font-weight:700;margin-right:5px}
.body{font-size:14.7px;color:#2a3846;margin-top:6px}
.pill{display:inline-block;font-size:11.5px;font-weight:700;padding:2px 8px;border-radius:20px;
  margin-left:2px;border:1px solid var(--line);vertical-align:middle}
.pill.good{background:rgba(47,158,107,.12);color:var(--good);border-color:rgba(47,158,107,.3)}
.pill.bad{background:rgba(200,69,106,.12);color:var(--bad);border-color:rgba(200,69,106,.3)}
.pill.muted{background:var(--surface-2);color:var(--muted)}
.gg{padding:10px 0;border-bottom:1px solid var(--line);font-size:14.7px}
.gcard{border:1px solid var(--line);border-radius:var(--radius);padding:16px 20px;margin:14px 0;background:var(--surface)}
.ghd{font-weight:800;font-size:17px;margin-bottom:10px}
.simstrip{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:13px}
.chip{background:var(--surface-2);border:1px solid var(--line);border-radius:var(--radius-sm);
  padding:5px 11px;font-size:13.5px;font-weight:800;color:var(--text);text-align:center}
.chip .cl{display:block;font-size:10px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted-2);font-weight:700;margin-bottom:1px}
.chip.good{border-color:rgba(47,158,107,.4);background:rgba(47,158,107,.09)}
.gbody{font-size:14.7px;color:#2a3846;line-height:1.66}
.gbody b{color:var(--text)}
.stack{padding:8px 0;font-size:15px;border-bottom:1px solid var(--line)}
.foot{margin-top:40px;padding-top:18px;border-top:2px solid var(--line);font-size:13px;color:var(--muted)}
"""


def build(week):
    swk = str(week)
    players = sorted(bd.SB[swk]['players'], key=lambda p: -p['play'])
    games = bd.MN[swk]['games']
    anchors = bd.SB[swk]['anchor_games']
    hi = anchors[:3]
    gm_by_key = {bd.game_key(x['game']): x for x in games}

    # game-script sim output for this week, indexed by team pair
    gs_games = {}
    try:
        _gs = json.load(open(os.path.join(HERE, 'game_sim.json'), encoding='utf-8'))
        for g in _gs.get('weeks', {}).get(swk, {}).get('games', []):
            gs_games[frozenset(g['teams'])] = g
    except Exception:
        pass

    # environment landscape
    tiers = {'elite': 0, 'high': 0, 'mid': 0, 'low': 0}
    for g in games:
        t = g.get('env_tier') or bd.env_tier_of(g.get('total'))
        if t in tiers:
            tiers[t] += 1

    P = []
    P.append(f'<!doctype html><html lang="en"><head><meta charset="utf-8">')
    P.append('<meta name="viewport" content="width=device-width, initial-scale=1">')
    P.append(f'<title>Week {week} · 2026 DFS Report</title><style>{STYLE}</style></head><body>')
    P.append('<div class="wrap"><div class="sheet">')

    # masthead
    P.append('<div class="kicker">2026 DFS · Forward-Looking Baseline</div>')
    tag = ' — Fantasy Playoffs' if week in (15, 16, 17) else ''
    P.append(f'<h1>Week {week}{tag}</h1>')
    P.append(f'<div class="dateline">Built {bd.BUILT} · anchored on posted look-ahead Vegas O/U, '
             f'blended with team ceiling, converted by team pass/run tendency</div>')
    P.append('<div class="rule"></div>')
    P.append(f'<p class="lead">{len(games)} games. Environments ranked by the blended score '
             f'(Vegas O/U anchored, team-ceiling adjusted), then each player scored on ceiling × '
             f'matchup edge × implied total × <b>pass/run conversion</b> — so talent, matchup, '
             f'environment, and how a team routes its points all separate the plays.</p>')

    # what's-new callout (the conversion lever)
    P.append('<div class="callout"><b>New this week — the pass/run conversion lever.</b> The implied '
             'total says how many points a team scores; a team\'s <b>PROE</b> (pass-rate-over-expected) '
             'tendency says where they go. Measured on complete 2024+2025 games (and it replicates across '
             'both years), a pass-lean offense routes fantasy <i>above</i> the total\'s expectation to its '
             'WR/TE and away from RBs — the mirror on run-lean teams. The RB side roughly doubles when the '
             'game-script sim projects a lead (clock-kill), <i>unless</i> the offense is high-PROE (those '
             'coaches keep throwing when up). Shown as a <span class="pill good">conv ▲</span> / '
             '<span class="pill bad">conv ▼</span> pill below; capped at ±12% so it refines, never dominates.</div>')

    # best environments
    P.append('<h2>Best environments<span class="sub">Where a correlated build has the most room</span></h2>')
    for g in hi:
        gm = gm_by_key.get(bd.game_key(g['g']))
        take = f" {bd.md_b(gm['stack_take'])}" if False else ''
        bl = g.get('blend'); tot = g.get('total')
        env = (f'blended <span class="n">{bd.f1(bl)}</span> (O/U {bd.f1(tot)})'
               if bl is not None else f'O/U <span class="n">{bd.f1(tot)}</span>')
        P.append(f'<div class="env"><span class="g">{html.escape(g["g"])}</span>'
                 f'<span>{env}</span>{env_adj_pill(g)}</div>')

    # who we like
    P.append('<h2>Who we like<span class="sub">The upside case, lever by lever</span></h2>')
    for i, p in enumerate(players[:10], start=1):
        pos = p['pos']; color = POSCOLOR.get(pos, 'var(--muted)')
        P.append('<div class="card"><div class="hd">')
        P.append(f'<span class="rankno">{i}</span>')
        P.append(f'<span class="pname">{html.escape(p["name"])}</span>')
        P.append(f'<span class="pos" style="background:{color}">{pos}</span>')
        P.append(f'<span class="muted">{html.escape(p["team"])} vs {html.escape(p.get("opp") or "—")}</span>')
        P.append(conv_pill(p))
        P.append(f'<span class="play"><span class="lbl">play</span>{bd.f1(p["play"])}</span>')
        P.append('</div>')
        P.append(f'<div class="body">{md_b(bd.upside_paragraph(p, i))}</div>')
        P.append('</div>')

    # stacks
    tpls = bd.stack_templates(week)
    if tpls:
        P.append('<h2>How to build it<span class="sub">QB-anchored stack templates</span></h2>')
        for t in tpls:
            P.append(f'<div class="stack">{md_b(t)}</div>')

    # game by game — the holistic sim read
    P.append('<h2>Game by game<span class="sub">Every game simulated 40,000 times — the holistic read</span></h2>')
    P.append('<p class="muted" style="font-size:14px;margin:0 0 6px">Ordered by blended environment. Each '
             'game shows the sim\'s glanceable numbers — win probability, how often it becomes a shootout or '
             'a blowout, and the projected script — then a plain read of what is happening and who it feeds.</p>')
    for g in sorted(games, key=lambda x: -(x.get('blend') or x.get('total') or 0)):
        sim = gs_games.get(frozenset(g.get('teams', [])))
        P.append('<div class="gcard">')
        head = html.escape(g['game']) + f' · <span class="muted">O/U {bd.f1(g.get("total"))}'
        if g.get('blend'):
            head += f' → blend {bd.f1(g.get("blend"))}'
        head += f' ({g.get("env_tier","")})</span>'
        P.append(f'<div class="ghd">{head}</div>')
        if sim:
            P.append(sim_strip(sim))
            P.append(f'<div class="gbody">{holistic_game_narrative(g, sim)}</div>')
        else:
            P.append(f'<div class="gbody">{md_b(bd.game_prose(g))}</div>')
        P.append('</div>')

    # footer / methodology pointer
    P.append('<div class="foot">Forward-looking projections, not results — no live 2026 slates, salaries, '
             'or ownership exist yet. Every factual clause traces to a model layer (env_blend, game_sim, '
             'defense_splits, team_ceiling, flag_ranks, proe_tendency_2026). Pass/run conversion calibrated '
             'in validate_proe_conversion.py; full 18-week prose in dfs_weekly_breakdown.md.</div>')

    P.append('</div></div></body></html>')
    return '\n'.join(P)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--week', type=int, default=1)
    a = ap.parse_args()
    out = os.path.join(HERE, f'dfs_week{a.week}_report.html')
    open(out, 'w', encoding='utf-8').write(build(a.week))
    print(f'wrote {out} ({os.path.getsize(out):,} bytes) — week {a.week}')


if __name__ == '__main__':
    main()
