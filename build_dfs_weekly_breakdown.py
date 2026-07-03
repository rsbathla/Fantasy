#!/usr/bin/env python3
"""build_dfs_weekly_breakdown.py — the WRITTEN per-week DFS breakdown.

This is deliberately NOT a dashboard. It reads the already-built forward-looking
layers and emits actual prose you can read week by week:

  dfs_season_baseline.json  -> weekly play scores, edges, anchor games (env)
  matchup_notes.json        -> per-game attack angles / pace / stack takes
  cc_context.json           -> per-player trait splits, scheme fit, vacated opportunity
  team_ceiling.json         -> team season-ceiling tier + drivers
  flag_ranks.json           -> season board flags + ceiling/trait/matchup percentiles

Every factual clause traces to one of those fields — nothing is asserted or
invented. Output: dfs_weekly_breakdown.md  (then render_dfs_weekly_pdf.py -> PDF).

Forward-looking basis (see the METHODOLOGY section it writes): environments are
ranked by the BLENDED score from env_blend.py — the posted look-ahead Vegas O/U
(weekly-vegas-lines.csv, TRUE market numbers; provenance in ground_truth_registry.json)
anchored, then adjusted by the two teams' ceiling conditions (team_ceiling.json:
pace, pass rate, scheme upgrade, QB ascension, shootout script). Never O/U alone
(PLAYBOOK C5). The per-player play score is ceiling x frequency-weighted matchup
edge x implied total.
"""
import core, json, os
fn = core.fn
HERE = os.path.dirname(os.path.abspath(__file__))
def J(p): return json.load(open(os.path.join(HERE, p), encoding='utf-8'))

SB = J('dfs_season_baseline.json')['weeks']
MN = J('matchup_notes.json')['weeks']
CC = J('cc_context.json')
TC = J('team_ceiling.json')['teams']
_FR = J('flag_ranks.json')
FR_META = _FR['_meta']
FLAG_IDX = {fn(v['name']): v for v in _FR['players'].values()}   # fn-normalized (resolves Ja'Marr/St. Brown)
BUILT = J('matchup_notes.json')['_meta'].get('built', '')

TEAM_FULL = {  # for readable game headers where useful
    'ARI':'Arizona','ATL':'Atlanta','BAL':'Baltimore','BUF':'Buffalo','CAR':'Carolina',
    'CHI':'Chicago','CIN':'Cincinnati','CLE':'Cleveland','DAL':'Dallas','DEN':'Denver',
    'DET':'Detroit','GB':'Green Bay','HOU':'Houston','IND':'Indianapolis','JAX':'Jacksonville',
    'KC':'Kansas City','LV':'Las Vegas','LAC':'L.A. Chargers','LAR':'L.A. Rams','MIA':'Miami',
    'MIN':'Minnesota','NE':'New England','NO':'New Orleans','NYG':'N.Y. Giants','NYJ':'N.Y. Jets',
    'PHI':'Philadelphia','PIT':'Pittsburgh','SF':'San Francisco','SEA':'Seattle','TB':'Tampa Bay',
    'TEN':'Tennessee','WAS':'Washington'}

def f1(x):
    try: return f"{float(x):.1f}"
    except: return None

def ordinal(n):
    """1 -> 1st, 2 -> 2nd, 72 -> 72nd, 81 -> 81st, 11 -> 11th."""
    n = int(round(float(n)))
    suf = 'th' if 10 <= n % 100 <= 20 else {1:'st',2:'nd',3:'rd'}.get(n % 10, 'th')
    return f"{n}{suf}"

def game_key(s):
    """Normalize 'DAL vs NYG' or 'DAL @ NYG' to a frozenset of team codes for matching."""
    return frozenset(t.strip() for t in s.replace(' vs ', '|').replace(' @ ', '|').split('|') if t.strip())

def env_tier_of(total):
    if total is None: return None
    t = float(total)
    if t >= 50: return 'elite'
    if t >= 47: return 'high'
    if t >= 43: return 'mid'
    return 'low'

# ---------------------------------------------------------------- per-player upside prose
def _flag_phrase(flags):
    """Turn the season board flags into a short readable clause."""
    if not flags: return None
    fs = [f.split('(')[0].strip().rstrip('.') for f in flags[:3]]
    return ", ".join(fs)

def upside_paragraph(p, rank_in_week):
    """A flowing, fully-grounded upside case for one liked player this week."""
    name, pos, team, opp = p['name'], p['pos'], p['team'], p.get('opp')
    fl = FLAG_IDX.get(fn(name), {})
    ct = CC.get(fn(name), {})
    tcr = TC.get(team, {})
    sc = (ct.get('scheme') or {})
    op = (ct.get('opp') or {})
    sp = (ct.get('splits') or {})

    # --- lead-in (varies by weekly rank so the section doesn't read templated) ---
    vs = f"vs {opp}" if opp else "(bye/no game)"
    if rank_in_week == 1:
        lead = f"**{name}** ({pos}, {team} {vs}) is our top play of the week."
    elif rank_in_week <= 3:
        lead = f"**{name}** ({pos}, {team} {vs}) is a headliner this week."
    else:
        lead = f"**{name}** ({pos}, {team} {vs})."

    # --- this-week environment (the variable) ---
    env = []
    tot, imp = p.get('total'), p.get('imp')
    if tot is not None:
        tier = env_tier_of(tot)
        env.append(f"the game projects at {f1(tot)} ({tier} environment)")
    if imp is not None:
        env.append(f"{team} is implied for {f1(imp)} points")
    env_sent = ("This week " + ", ".join(env) + ".") if env else ""

    # --- this-week matchup edge (the differentiator) ---
    smash = [e for e in p.get('edges', []) if e.get('smash')]
    edge_sent = ""
    if smash:
        parts = []
        for e in smash[:2]:
            ax = e['axis']
            if e.get('player_pctl') is not None and e.get('def_soft_pctl') is not None:
                parts.append(f"his {ordinal(e['player_pctl'])}-pctl {ax.lower()} profile meets {opp}, which grades {ordinal(e['def_soft_pctl'])}-pctl soft on that same axis")
            elif e.get('def_soft_pctl') is not None:
                parts.append(f"{opp} grades {ordinal(e['def_soft_pctl'])}-pctl soft on {ax.lower()}")
            elif e.get('fpaa') is not None:
                parts.append(f"{opp} bleeds {e['fpaa']:+.1f} fantasy pts vs the position ({ax.lower()})")
        if parts:
            edge_sent = "The matchup lines up: " + "; ".join(parts) + f" — {len(smash)} smash edge{'s' if len(smash)!=1 else ''} flagged."
    elif p.get('edge_score'):
        edge_sent = f"No outright smash edge this week (edge score {f1(p['edge_score'])}); the case is ceiling and environment, not matchup."

    # --- the season-long case (the constant): team ceiling + player flags + percentiles ---
    season = []
    tier = tcr.get('tier'); tflags = tcr.get('flags') or []
    if tier in ('ELITE', 'HIGH'):
        drv = f" ({tflags[0]})" if tflags else ""
        season.append(f"{team} grades {tier} for season ceiling{drv}")
    ceil_pctl = fl.get('ceil_pctl'); trait_pctl = fl.get('trait_pctl')
    if ceil_pctl is not None:
        cp = f"{ordinal(ceil_pctl)}-pctl ceiling"
        if trait_pctl is not None: cp += f" on a {ordinal(trait_pctl)}-pctl trait base"
        season.append(cp)
    season_sent = ("Season case: " + "; ".join(season) + ".") if season else ""

    # --- opportunity + scheme levers ---
    lev = []
    tgt = op.get('tgt_share'); car = fl.get('car_sh'); vac = op.get('team_vacated_tgt')
    if tgt is not None and pos in ('WR','TE'): lev.append(f"{f1(tgt)}% target share")
    if car is not None and pos == 'RB': lev.append(f"{f1(car)}% of the backfield carries")
    if vac is not None and vac >= 40: lev.append(f"heavy vacated opportunity in the offense ({team} vacated-target index {vac:.0f})")
    yoy = sp.get('yoy')
    if yoy and yoy.get('delta') is not None and yoy['delta'] > 0:
        lev.append(f"{yoy['label']} up {yoy['delta']:+.3f} year-over-year")
    if sc.get('fit'):
        lev.append("scheme fit — " + sc['fit'][0])
    lever_sent = ("Levers: " + "; ".join(lev) + ".") if lev else ""

    # --- board flags line ---
    fp = _flag_phrase(fl.get('top_flags'))
    flag_sent = f"Board flags: {fp}." if fp else ""

    body = " ".join(s for s in [lead, env_sent, edge_sent, season_sent, lever_sent, flag_sent] if s)
    return body

# ---------------------------------------------------------------- per-game prose
def game_prose(g):
    game = g['game']; tot = g.get('total'); tier = g.get('env_tier'); bl = g.get('blend')
    head = f"**{game}**"
    bits = []
    if tot is not None:
        env = f"O/U {f1(tot)} ({tier})" + (f", blend {f1(bl)}" if bl is not None and abs(bl - tot) >= 0.05 else "")
        bits.append(env)
    if g.get('spread_read'): bits.append(g['spread_read'])
    lead = head + " — " + "; ".join(bits) + "." if bits else head + "."
    sides = []
    for side, blk in (g.get('sides') or {}).items():
        atk = (blk.get('attack') or '').strip()
        off = blk.get('off_id'); pace = blk.get('pace'); sm = blk.get('smash') or []
        desc = []
        if off: desc.append(off)
        if pace: desc.append(f"{pace} pace")
        descstr = f" — {', '.join(desc)}" if desc else ""
        # `side` is the attacking offense; `atk` already names the defense it targets (e.g. "DAL D: ...")
        if atk:
            seg = f"{side}{descstr} — attacks {atk}"
        else:
            seg = f"{side}{descstr}"
        if sm: seg += f". Smash: {', '.join(sm[:3])}"
        sides.append(seg.rstrip('.') + ".")
    take = f"Build: {g['stack_take']}." if g.get('stack_take') else ""
    return " ".join([lead] + sides + ([take] if take else []))

# ---------------------------------------------------------------- stack templates (reconstructed)
def stack_templates(wk):
    """Rebuild the QB-anchored stack templates from the week's players + anchor games."""
    players = SB[str(wk)]['players']
    anchors = SB[str(wk)]['anchor_games'][:4]
    by = {}
    for p in players:
        by.setdefault((p['team'], p['pos']), []).append(p)
    for k in by: by[k].sort(key=lambda x: -x['play'])
    out = []
    for ag in anchors:
        g = ag['g']; tot = ag['total']
        try: a, b = g.replace(' vs ', ' @ ').split(' @ ')
        except ValueError: continue
        qbs = by.get((a,'QB'), []) + by.get((b,'QB'), [])
        qbs.sort(key=lambda x: -x['play'])
        if not qbs: continue
        qb = qbs[0]; qbt = qb['team']; oppt = b if qbt == a else a
        catchers = (by.get((qbt,'WR'), []) + by.get((qbt,'TE'), []))
        catchers.sort(key=lambda x: -x['play'])
        cs = [c['name'] for c in catchers[:2]]
        bb = (by.get((oppt,'WR'), []) + by.get((oppt,'TE'), []))
        bb.sort(key=lambda x: -x['play'])
        high = (tot or 0) >= 45
        line = f"**{g}** (total {f1(tot)}): anchor **{qb['name']}** ({qbt})"
        if cs: line += " + " + " & ".join(cs)
        if high and bb:
            line += f", bring back **{bb[0]['name']}** ({oppt})"
            line += " — high total, correlated bring-back plays."
        else:
            line += " — total under ~45, skip the bring-back and keep it a clean same-team stack."
        out.append(line)
    return out

# ---------------------------------------------------------------- week section
def week_section(wk):
    swk = str(wk)
    players = sorted(SB[swk]['players'], key=lambda p: -p['play'])
    games = MN[swk]['games']
    anchors = SB[swk]['anchor_games']
    # environment landscape
    tiers = {'elite':0,'high':0,'mid':0,'low':0}
    for g in games:
        t = g.get('env_tier') or env_tier_of(g.get('total'))
        if t in tiers: tiers[t] += 1
    dome = sorted({tuple(sorted([p['team'], p['opp']])) for p in SB[swk]['players'] if p.get('dome') and p.get('opp')})
    hi = anchors[:3]   # already blend-ranked by dfs_model (Vegas O/U + team-ceiling adj)
    lo = sorted([g for g in games if g.get('total')], key=lambda g: g.get('blend', g['total']))[:2]

    L = []
    tag = " — Fantasy Playoffs" if wk in (15,16,17) else (" — Best-Ball Championship" if wk == 17 else "")
    L.append(f"\n\n## Week {wk}{tag}\n")

    # 1. the slate
    slate = (f"**The slate.** {len(games)} games. "
             f"The environment board tilts {tiers['elite']} elite / {tiers['high']} high / "
             f"{tiers['mid']} mid / {tiers['low']} low by projected total. ")
    if hi:
        slate += ("Scoring concentrates in " +
                  ", ".join(f"{g['g']} (blend {f1(g.get('blend') or g['total'])})" for g in hi) + "; ")
    if lo:
        slate += ("the thinnest environments are " +
                  ", ".join(f"{g['game']} ({f1(g['total'])})" for g in lo) + ". ")
    if dome:
        slate += f"Dome/indoor games (pace + weather-proof): {', '.join(a+'/'+b for a,b in dome)}."
    L.append(slate)

    # 2. best environments (BLEND-ranked: posted Vegas O/U anchor + team-ceiling adjustment)
    L.append(f"\n**Best environments — and how we rank them.** Ranked by the blended environment "
             f"score: the posted look-ahead Vegas O/U anchored, then adjusted for the two teams' "
             f"season-ceiling conditions (pace, pass rate, scheme, QB — see methodology). "
             f"They are where a concentrated, correlated build has the most room to spike:")
    gm_by_key = {game_key(x['game']): x for x in games}
    for g in hi:
        gm = gm_by_key.get(game_key(g['g']))
        take = f" {gm['stack_take']}." if gm and gm.get('stack_take') else ""
        fav = f" {gm['spread_read']}." if gm and gm.get('spread_read') else ""
        bl = g.get('blend')
        env = (f"blended {f1(bl)} (O/U {f1(g['total'])}, ceiling adj {bl - g['total']:+.1f})"
               if bl is not None else f"O/U {f1(g['total'])}")
        L.append(f"\n- **{g['g']}** — {env}.{fav}{take}")

    # 3. who we like
    L.append(f"\n\n**Who we like, and the upside case.** The play score behind this ranking is "
             f"ceiling x this-week matchup edge x implied team total — so it blends talent, matchup, and "
             f"environment, not the Vegas total alone. For each, the *constant* is season-long ceiling/flags "
             f"and the *variable* is this week's matchup and environment:")
    for i, p in enumerate(players[:10], start=1):
        L.append(f"\n{i}. " + upside_paragraph(p, i))

    # 4. stacks
    tpls = stack_templates(wk)
    if tpls:
        L.append(f"\n\n**How to build it (stack templates).** Winner structure is a QB + 1–2 same-team "
                 f"catchers, with an opponent bring-back only when the total is high (~45+):")
        for t in tpls:
            L.append(f"\n- {t}")

    # 5. game by game (blend-ordered; raw O/U shown on every line)
    L.append(f"\n\n**Game by game.**")
    for g in sorted(games, key=lambda x: -(x.get('blend') or x.get('total') or 0)):
        L.append(f"\n- {game_prose(g)}")

    return "\n".join(L)

# ---------------------------------------------------------------- methodology / front matter
def methodology():
    w = FR_META.get('weights', {})
    return f"""# 2026 DFS — Written Weekly Breakdowns (Forward-Looking Baseline)

*A written, week-by-week read of the 2026 season: the best scoring environments, the players we
like and exactly why, how to stack each week, and a note on every game. Built {BUILT} from the
model layers — every factual clause traces to a pulled data field; nothing here is asserted.*

---

## How to read this — and what we're assuming (the transparency layer)

Because it is the offseason (mid-2026), there are **no live in-season slates, salaries, or posted
game lines yet**. Everything here is *forward-looking* off the model's projection layers. Six things
drive what you read below, and it's worth being explicit about each:

**1. Where "best environments" come from — two ingredients, blended.** The anchor is the **posted
look-ahead Vegas O/U** for every 2026 game (`weekly-vegas-lines.csv`, ffdataroma's pull of the real
posted totals, cross-checked against a sportsbook screenshot — see `ground_truth_registry.json`).
These are true market numbers, and Vegas stays the anchor because the market's median is hard to beat.
But we do NOT rank environments on the O/U alone: each game gets a **team-ceiling adjustment**
(`env_blend.py`) from the team_ceiling layer — pace, pass rate, scheme upgrade, QB ascension,
concentrated target tree, shootout script — the upside conditions a median market number
under-expresses. The adjustment is deliberately small (slope 0.10, ~±3.5 points max, a stated prior
with a revert flag), so the blend can re-order comparable games but never override Vegas. Both numbers
are always shown. When in-season lines post, the same field refreshes and the blend sharpens.

**2. The per-player play score is NOT the total alone.** Each player's weekly play score is
`ceiling x (1 + matchup_edge/250) x (1 + (implied_total - 21)/60)`. Three levers: the player's own
**ceiling** (simulated 95th-percentile week), this week's **matchup edge**, and the **environment**
(implied team total). A big projected total lifts everyone in the game, but talent and matchup still
separate the plays. That is why the "who we like" list is not just the players in the highest-total game.

**3. What a "matchup edge / smash" is.** Real charting percentiles — a receiver's man-coverage, zone,
or deep strength; a back's run-game profile — lined up against **this week's opponent** defense's
softness on the *same axis* (`defense_splits.json`). When a player who is strong on an axis (>=60th
pctl) meets a defense soft on that same axis (>=60th pctl), we flag a **smash** edge. It is the one
part of the read that changes every week as opponents change.

**4. What the season board flags mean.** Each featured player carries "board flags" — the season-long
reasons we like them, from the composite (weights: ceiling {w.get('ceiling')}, traits {w.get('traits')},
season-matchup {w.get('season_mq')}; RBs also weight opportunity). Flags like *workhorse volume*,
*explosive / big-play ceiling*, *separator / route-winner*, *elite pass volume* are the durable case;
the weekly matchup is the timing.

**5. Team ceiling.** Each team carries a **season-ceiling tier** (ELITE / HIGH / MID / LOW) built from
scoring environment, pace, pass rate, QB ascension, scheme change, and shootout script. This year's
ELITE offenses: CHI, CIN, DAL, DET, KC, TB. HIGH: ARI, BAL, LAC, LAR, NE, NYG, PHI, SF. A player in an
ELITE/HIGH offense inherits ceiling the model rewards.

**6. The caveats, stated plainly.** These are projections, not results. No live slates or salaries
exist yet, so there is no salary-based value or ownership leverage here — that layer arrives when
DraftKings/FanDuel post 2026 slates. Player pools reflect current roster/depth assumptions and will
move with camp news, injuries, and role changes. Refresh when real lines and slates post.

---

## The levers, defined

- **Environment** — the projected game total and the team's implied total. Higher = more scoring to
  distribute = higher weekly ceiling for everyone in the game.
- **Matchup smash** — player-strong-axis meets defense-soft-axis (same axis), from real charting. The
  weekly differentiator.
- **Team ceiling** — the offense's season-ceiling tier and its drivers (pace, pass rate, scheme, QB).
- **Board flags** — the season-long, durable reasons a player has upside (volume, big-play, route wins,
  red-zone/TD role), independent of any single week.
- **Trait percentiles** — where the player's ceiling and underlying traits rank leaguewide (from the
  composite): a 95th-pctl ceiling on a high trait base is a real weekly-tournament weapon.
- **Opportunity** — target share (WR/TE), backfield carry share (RB), and the offense's *vacated-target
  index* — the sum of departed players' prior usage, so it can read above 100 when a team lost more than
  one high-usage pass-catcher. It measures opportunity up for grabs, not one player's share. Volume is
  the floor under the ceiling.
- **Scheme fit** — where the 2026 playcaller amplifies a specific skill (motion separation, vertical
  aDOT, RB pass-game usage).

---
"""

# ---------------------------------------------------------------- assemble
def main():
    parts = [methodology()]
    for wk in range(1, 19):
        parts.append(week_section(wk))
    md = "\n".join(parts).rstrip() + "\n"
    out = os.path.join(HERE, 'dfs_weekly_breakdown.md')
    open(out, 'w', encoding='utf-8').write(md)
    nwords = len(md.split())
    print(f"dfs_weekly_breakdown.md: {len(md):,} chars | ~{nwords:,} words | 18 weeks")
    # quick coverage sanity
    for wk in (1, 9, 17):
        n_feat = min(10, len(SB[str(wk)]['players']))
        print(f"  week {wk}: {len(MN[str(wk)]['games'])} games, {n_feat} featured plays")

if __name__ == '__main__':
    main()
