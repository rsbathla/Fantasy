#!/usr/bin/env python3
"""build_team_preview.py — TEAM PREVIEW as designed HTML, brain × model. Parameterized:
    python3 build_team_preview.py ARI
Model side: sims/signals/fusion/statmenu env + game_sim season environment strip + defense splits.
Brain side: vault leans, SS claims, curated intel, coach canon. Hand-written reads live in PROSE
per team (ARI shipped); the data layer renders for any team."""
import json, csv, re, os, sys, html

HERE = os.path.dirname(os.path.abspath(__file__))
TEAM = (sys.argv[1] if len(sys.argv) > 1 else 'ARI').upper()

def fn(n):
    n = str(n).strip().lower(); n = re.sub(r"\s+(jr|sr|ii|iii|iv|v)\.?$", "", n)
    return n.replace(".", "").replace("'", "").replace("-", " ")
def num(x, d=None):
    try:
        f = float(x); return f if f == f else d
    except Exception: return d
def esc(x): return html.escape(str(x), quote=False)

WT = {t['team']: t for t in json.load(open(f'{HERE}/web_teams.json'))}
PERS = json.load(open(f'{HERE}/personnel_2026.json'))['teams'] if os.path.exists(f'{HERE}/personnel_2026.json') else {}
DPROF = json.load(open(f'{HERE}/boom/defensive_profile.json')) if os.path.exists(f'{HERE}/boom/defensive_profile.json') else {}
NGS = json.load(open(f'{HERE}/nflpro_2025.json'))['teams'] if os.path.exists(f'{HERE}/nflpro_2025.json') else {}
SCHEME = json.load(open(f'{HERE}/scheme_2026.json'))
SCHED = json.load(open(f'{HERE}/boom/schedule2026.json'))
SM = json.load(open(f'{HERE}/boom/statmenu.json'))
BI = json.load(open(f'{HERE}/brain_intel.json'))
BP = {fn(k): v for k, v in BI['players'].items()}
SIG = {fn(r['name']): r for r in csv.DictReader(open(f'{HERE}/draft_board_signals.csv'))}
FUS = {fn(r['name']): r for r in csv.DictReader(open(f'{HERE}/fusion_table.csv'))}
PSP = json.load(open(f'{HERE}/player_splits.json'))
DS = json.load(open(f'{HERE}/defense_splits.json'))
GS = json.load(open(f'{HERE}/game_sim.json'))['weeks']

E = WT[TEAM]; SCH = SCHEME.get(TEAM, {})
TEAM_FULL = {'ARI': 'Arizona Cardinals'}.get(TEAM, TEAM)
BT = BI['teams'].get(TEAM_FULL, {})

# ---- season environment strip from game_sim (every week the sim covers) ----
env_rows = []
for wk in sorted(GS, key=lambda x: int(x)):
    for g in GS[wk]['games']:
        if TEAM in g['teams']:
            v = g['vegas']
            opp = [t for t in g['teams'] if t != TEAM][0]
            fav = v['spread_fav']; spr = v['spread']
            line = -spr if fav == TEAM else spr
            env_rows.append({'wk': int(wk), 'opp': opp, 'total': v['total'],
                             'imp': v['imp'].get(TEAM), 'line': line})
imps = [r['imp'] for r in env_rows if r['imp']]
avg_imp = sum(imps) / len(imps) if imps else 0
dog_all = sum(1 for r in env_rows if r['line'] > 0)

# ---- players ----
players = [v for v in SM.values() if v.get('team') == TEAM and v.get('pos') != 'DST']
players.sort(key=lambda v: -(num(SIG.get(fn(v['name']), {}).get('proj_pg')) or 0))

# ============================ HAND-WRITTEN CONTENT (per team) ============================
PROSE = {'ARI': {
 'title': 'The Teardown, Priced',
 'regime': """Jonathan Gannon is out; <b>Mike LaFleur</b> arrives with the full Shanahan kit — outside zone, motion, play-action — and a stated pivot the scheme file records bluntly: <i>“Murray gone → pocket QBs.”</i> The identity is already leaking through the vault in triplicate: LaFleur “keeps name-dropping Tip Reiman, signaling more 12 personnel,” and the beat-leaked starting offense confirms it — Brissett under center, Love at back, Harrison and Wilson as the ONLY two receivers, McBride and Reiman together. Two-TE base squeezes every target toward four players. Nathaniel Hackett runs the OC title; Nick Rallis keeps the defense, which the canon calls “thin… facing one of the NFL's hardest schedules” after losing Thompson, Tomlinson and Campbell. The one piece of coach history that matters for fantasy: as Jets OC, LaFleur had rookie <b>Breece Hall at 66% snaps and 20+ touches per game by Week 4</b>. That precedent is the Jeremiyah Love bet in one sentence.""",
 'qb': """The room is Brissett with Minshew behind him and third-round rookie <b>Carson Beck</b> on a countdown. The vault's timeline intel is unusually direct: Beck “in theory could be the Week 1 starter — unlikely… very likely at some point this season,” and the quiet part said aloud: “it will all depend on how well the Cardinals do — if Arizona isn't on a path to…” A 4.5-win team completes that sentence itself. What the market is sleeping on is what <b>2025 Brissett already did for this exact pass-catching room</b> — the film log has receipts: McBride caught <b>4 TDs in three games with Brissett</b> (“showing even more ceiling”); Harrison logged a 33% TPRR, 0.79-WOPR game “loving life with Jacoby Brissett”; Wilson had <b>three separate 15+ target games</b> with him, including a two-week run of 33 targets, 25 catches, 303 yards. Whoever starts, this offense throws late and often from behind — the connection data says the catchers don't need the QB upgrade to eat.""",
 'env': """This is the part that prices everything. The lookahead board makes Arizona an underdog in <b>every single simmed game</b> — the vault chart puts them “among 3 teams favored in exactly one game all year… 6+ point underdogs in ALL of their first 11.” Average implied total: <b>~17.9 points</b>. Their own defense (11th-percentile coverage, decent rush, leaky to RBs +3.6 and TEs +3.3) guarantees the games stay throwable in both directions. The vault's framing is the thesis: <i>“All signs point toward the Cardinals playing from behind at an alarming rate once again — will Trey McBride remain the Garbage Time King of the NFL?”</i> Chronic trailing is terrible for real football and specifically fine for pass-catcher fantasy: it manufactures attempts. And then the schedule does something remarkable: the two most winnable games of the entire season — <b>NYJ −1.5 in Week 15 and LV −2.0 in Week 17</b> — land exactly on the best-ball payout weeks. Fourteen weeks of tax, then a rebate precisely when it counts.""",
 'defid': """Read it as an opponent would: throwing on Arizona is an <b>89th-percentile matchup</b> (softer than 89% of defenses), running on them a 64th — the only red light is protection, because the rush is real (<b>20th-percentile matchup</b> for opposing lines). The lane map says exactly where the points go: <b>RBs (+3.6) and TEs (+3.3) are the green lanes</b>; every wide-receiver alignment is a wall (−2.5 WRs overall). The profile engine logs the regime change explicitly: <i>2025 graded RUN-funnel → 2026 projects PASS-funnel</i> on the roster and coordinator turnover — losing Tomlinson and Campbell guts the interior while the secondary lost Thompson. So the standing DFS rule against Arizona all season: checkdowns and seams, never perimeter shots. And for Arizona's own offense it closes the loop on the garbage-time thesis: a defense this targetable through the air is the engine that manufactures McBride's fourth quarters.""",
 'verdict': """<b>The buy is McBride</b> — a 26.6% target share (No. 1 among all TEs), the garbage-time crown, documented Brissett chemistry, 12-personnel insurance on his routes, 100% advancement rate in the survival chain, and FAV pass-funnel verdicts in W15 and W17 when Arizona finally plays even games. The routes-regression lean is the one honest caution; his fusion value percentile (99) says the market is still not paying for the profile. <b>Love is a talent bet against an environment</b> — 63% carry share, the LaFleur/Breece workload precedent, 87th-percentile fusion value, but a 254-PPR projection the vault itself asks “just right or too low?” while the offense projects 17.9 points a game; the Allgeier goal-line-vulture panic is mostly noise (“his hype tape is all 50-yard TDs”). <b>Harrison is the leverage play</b>: 88th-percentile boom score and the Davante-role red-zone intel against a 21st-percentile separation grade and the route-tree overlay warning — a TD-dependent WR2/3 with weekly WR1 spikes, cheap because 2025 disappointed. <b>Wilson is the quiet conviction pick</b>: more routes than Harrison last year (601), a near-identical TPRR (.206 vs .203), the Z-role expansion intel, and the strongest Brissett connection of anyone — at an ADP three rounds later. In 12 personnel there is no WR3 to fear. <b>Depth notes:</b> Benson is a 7/2 Signal log with live trade chatter (“the team might be done with him — 5.5 YPC with very strong peripherals is being overlooked”); Conner and his league-best missed-tackle rate are rehabbing toward camp with the model carrying him near zero until the roster resolves; Bourne is a 12-personnel squeeze-out; Beck is a name to circle for late-season Wilson/McBride stacks the moment the “path” sentence completes itself. <b>DFS lens all season:</b> attack Arizona with opposing RBs and TEs (+3.6/+3.3 leaks), and treat ARI pass-catchers as trailing-script volume plays with hidden PPR floors.""",
}}
P = PROSE.get(TEAM, {})

# hand-written per-player reads (ARI)
READS = {
 'Trey McBride': "The whole thesis in one card: No. 1 TE target share in football (26.6%), the vault's “Garbage Time King” in an offense projected to trail more than anyone, two SS claims documenting the Brissett TD connection, and 12-personnel scheme insurance on his snaps. The lean's routes-regression warning is real — and priced nowhere, with fusion scoring his VALUE at the 99th percentile. W15/W17 grade FAV pass-funnel in the only two near-even games Arizona plays.",
 'Jeremiyah Love': "Elite prospect, honest situation math. The 63% carry share and three-down skill set meet the LaFleur precedent (rookie Breece: 66% snaps, 20+ touches by W4) — volume is not the question. The environment is: 17.9 implied points a game caps TD math, and the SS lean names it plus “multiple capable backups.” The Allgeier vulture scare is thin — his own tape argues explosives, not goal-line. Best-ball verdict: real, but you're paying a premium for talent the scoreboard will fight.",
 'Marvin Harrison Jr.': "The most polarized card on the team: 88th-percentile boom score and coach-intel casting him in the Davante red-zone role — against a 21st-percentile separation grade and the vault's route-tree overlay showing Adams' exact route mix would have LOWERED his TPRR. Career 1.61 YPRR keeps the Y3-leap case alive (the vault takes his side vs Odunze). Read: a spike-week WR whose TDs arrive in bunches, at a price that finally respects the risk.",
 'Michael Wilson': "The conviction sleeper. More routes than Harrison last year (601), a fractionally HIGHER TPRR (.206 vs .203), a Z-role expansion note, extension talks “going great” — and the strongest Brissett connection in the building: three 15+ target games, a 33-target/303-yard fortnight in the log. In a two-WR base offense there is no third receiver to dilute this. If Brissett starts Week 1, Wilson is the cheapest confirmed-volume WR in drafts.",
 'Jacoby Brissett': "The bridge with receipts: the film log shows this exact supporting cast producing WOPR spikes and TE touchdowns with him at the wheel in 2025. The model carries him at 12.5 a game with no ceiling — accurate for a pocket QB in a 4.5-win offense — but his fantasy relevance is as the stabilizer that makes McBride/Wilson/MHJ droppable-proof. The Minshew note (“will start if Brissett doesn't come back”) is the only wobble to monitor in camp.",
 'Carson Beck': "The countdown clock. Third-round capital, mixed reports, good sack avoidance per the lean — and vault intel that lays out the succession explicitly: unlikely Week 1, “very likely at some point this season,” tied to the team's path. On a 4.5-win team the path completes itself. Late-round QB3 logic only, but he's the name that decides whether the December version of this passing game is a rookie showcase.",
 'Tyler Allgeier': "The myth-tax on Love. The market's goal-line-vulture story runs into his own SS log (green-zone touches, yes — at Atlanta, behind Bijan) and the vault's mockery of the panic. A 24% carry-share change-of-pace with 80th-percentile boom in fusion is a name for the deepest builds only.",
 'Trey Benson': "The most interesting depth chart name nobody drafts: a 7/2 Signal log, 5.5 YPC on strong peripherals the lean says is “being overlooked,” recovering alongside Conner — and live trade chatter the vault is openly IN on. If he's moved, he matters somewhere; if he stays and heals, he's the Love insurance the Allgeier crowd thinks it's buying.",
 'James Conner': "League-best 0.30 missed tackles forced per touch over three seasons — and a model projection of functionally zero, because the roster status is unresolved while he rehabs toward camp. Age plus injury plus a rookie first-rounder behind him: the model has already written the ending; the vault keeps the receipts open.",
 'Kendrick Bourne': "The 12-personnel squeeze victim. Strong YAC profile (91st pctl), real SS claims from his 2025 role — and a scheme that fields two receivers. FA-add intrigue, roster-clogger reality.",
 'Gardner Minshew II': "Contingency QB with one vault note that matters: he starts if Brissett isn't back. Otherwise a camp-battle bystander.",
}

def w1517(k):
    sp = PSP.get(k, {})
    chips = ""
    for w in sp.get('weeks', []):
        chips += f"<span class='wk {w['v']}'>{w['wk']} v{w['opp']} <b>{w['v']}</b> <i>{esc(w['why'])}</i></span>"
    return chips

def card(v):
    nm = v['name']; k = fn(nm); pos = v.get('pos', '')
    s = SIG.get(k, {}); f = FUS.get(k, {}); b = BP.get(k, {})
    proj = num(s.get('proj_pg')); p95 = num(s.get('p95')); adp = num(v.get('adp'))
    u = v.get('usage') or {}; ad = v.get('adot') or {}
    bits = []
    if num(u.get('tgt_share')): bits.append(f"{num(u['tgt_share'])*100:.0f}% tgt share")
    if num(u.get('carry_share')): bits.append(f"{num(u['carry_share'])*100:.0f}% carries")
    if num(ad.get('TPRR')): bits.append(f"TPRR {num(ad['TPRR']):.3f}")
    if num(ad.get('aDOT')): bits.append(f"aDOT {num(ad['aDOT']):.1f}")
    fchips = ""
    for lbl, key in [("Value", 'value_pctl'), ("Ceiling", 'ceiling_pctl'), ("Boom", 'boom_pctl'), ("Route", 'route_eff_pctl'), ("Sep", 'separation_pctl'), ("YAC", 'yac_pctl')]:
        x = num(f.get(key))
        if x is None: continue
        cls = 'hi' if x >= 70 else ('lo' if x <= 30 else '')
        fchips += f"<span class='fc {cls}'>{lbl} <b>{x:.0f}</b></span>"
    lean = (b.get('fwd') or [{}])[0].get('t', '') if b.get('fwd') else ''
    claims = ''.join(f"<div class='claim'><span class='ctag'>{esc(c['s'])}</span>{esc(c['t'][:180])}</div>"
                     for c in (b.get('claims') or [])[:2])
    tws = ''
    for x in (b.get('tw') or [])[:2]:
        t = str(x.get('t', ''))
        if re.search(r"- every throw of|clean pocket in 20\d\d\s*$", t): continue
        tws += f"<div class='tw'><span class='twtag'>{esc(x.get('tg',''))}</span>{esc(t[:180])}</div>"
    nums = " · ".join(x for x in [f"proj <b>{proj:.1f}</b>" if proj else "", f"p95 <b>{p95:.1f}</b>" if p95 else "",
                                  f"ADP <b>{adp:.0f}</b>" if adp else "", " · ".join(bits)] if x)
    read = READS.get(nm, "")
    readl = f"<div class='read'>{read}</div>" if read else ""
    leanl = f"<div class='lean'><span class='ltag'>SS 2026 lean</span>{esc(lean[:230])}</div>" if lean else ''
    cnt = f"film log {b.get('n_sig',0)}/{b.get('n_noise',0)} · {b.get('n_tw',0)} tweets · {b.get('n_src',0)} sources" if b else ""
    return f"""<div class='pcard'>
  <div class='prow'><span class='pname'>{esc(nm)}</span><span class='pos {pos}'>{pos}</span><span class='bcnt'>{cnt}</span></div>
  <div class='meta'>{nums}</div>
  <div class='fchips'>{fchips}</div>
  {readl}{leanl}{claims}{tws}
  <div class='wks'>{w1517(k)}</div>
</div>"""

# environment strip bars
def env_strip():
    out = ""
    for r in env_rows:
        pct = max(6, min(100, (r['imp'] - 12) / 14 * 100)) if r['imp'] else 6
        cls = 'even' if abs(r['line']) <= 3 else ('dog' if r['line'] > 0 else 'fav')
        out += f"""<div class='ecol {cls}'><div class='ebar'><div style='height:{pct:.0f}%'></div></div>
<div class='ewk'>W{r['wk']}</div><div class='eopp'>{r['opp']}</div><div class='eline'>{'+' if r['line']>0 else ''}{r['line']:g}</div><div class='eimp'>{r['imp']:g}</div></div>"""
    return out

team_tws = ''.join(f"<div class='tw'><span class='twtag'>{esc(x['tg'])}</span>{esc(x['t'][:200])}</div>" for x in BT.get('tw', []))
d = DS.get(TEAM, {}); u = d.get('units', {}); bp = d.get('by_pos', {})

# ---- personnel identity strip (personnel_2026.json v1) ----
pe = PERS.get(TEAM, {})
def personnel_html():
    if not pe: return ""
    dirn = pe.get('direction_2026')
    arrow = {'up': "▲ MORE heavy in 2026", 'down': "▼ LESS heavy in 2026"}.get(dirn, "2026 direction: no vault evidence yet")
    ev = ''.join(f"<div class='tw'><span class='twtag'>evidence</span>{esc(q[:190])}</div>" for q in pe.get('evidence', []))
    return f"""<div class='prosebox' style='margin-top:12px'>
<b>Personnel identity (v1 — team level):</b> heavy sets <b>{pe.get('heavy_2025','–')}%</b> in 2025
(<b>#{pe.get('heavy_rank_2025','–')}</b> in the NFL) · play-action <b>{pe.get('pa_2025','–')}%</b> ·
motion <b>{pe.get('motion_2025','–')}%</b> — <span style='color:var(--good)'><b>{arrow}</b></span>.
{ev}</div>"""

# ---- defensive identity, MATCHUP VIEW: every number answers "should an offense target this?"
# Percentiles are INVERTED to attacker framing: matchup 89th pctl = 89% of defenses are a tougher
# spot (i.e., this lane is soft). GREEN = target it, RED = stay away.
def def_identity_html():
    dp = DPROF.get(TEAM, {})
    cov = num(u.get('pass_cov_pctl'), 50); rush = num(u.get('pass_rush_pctl'), 50); rund = num(u.get('run_def_pctl'), 50)
    def mchip(lbl, mval):
        cls = 'grn' if mval >= 65 else ('red' if mval <= 35 else '')
        tag = 'TARGET' if mval >= 65 else ('AVOID' if mval <= 35 else 'neutral')
        return f"<span class='chip {cls}'>{lbl} matchup <b>{mval:.0f}th pctl · {tag}</b></span>"
    rows = mchip("Pass game", 100 - cov) + mchip("Run game", 100 - rund) + mchip("Protection (vs their rush)", 100 - rush)
    sh = d.get('shell', {})
    rows += f"<span class='chip'>shell <b>{num(sh.get('man_rate'),0):.0f}% man · {num(sh.get('single_high'),0):.0f}% single-high</b></span>"
    if dp:
        rows += f"<span class='chip'>lean 2025 <b>{esc(dp.get('lean_2025','–'))}</b> → 2026 <b>{esc(dp.get('lean_2026','–'))}</b></span>"
    sm_, sz_ = num(d.get('vs_man',{}).get('softness_pctl'),50), num(d.get('vs_zone',{}).get('softness_pctl'),50)
    sd_, ss_ = num(d.get('deep',{}).get('softness_pctl'),50), num(d.get('short',{}).get('softness_pctl'),50)
    for lbl, v in [("vs man", sm_), ("vs zone", sz_), ("deep", sd_), ("short", ss_)]:
        cls = 'grn' if v >= 65 else ('red' if v <= 35 else '')
        rows += f"<span class='chip {cls}'>{lbl} <b>{v:.0f}th soft</b></span>"
    # lane chips, attacker colors: GREEN = leak = target, RED = wall = cannot target
    leak_rows = ""
    for lbl, key in [("QB", 'qb'), ("RB", 'rb'), ("WR", 'wr'), ("TE", 'te'), ("WR1", 'wr1'), ("WR2", 'wr2'), ("slot", 'slot')]:
        v = num(bp.get(key))
        if v is None: continue
        cls = 'grn' if v >= 1.5 else ('red' if v <= -1.5 else '')
        leak_rows += f"<span class='chip {cls}'>{lbl} <b>{v:+.1f}</b></span>"
    tgt = [k.upper() for k, v in bp.items() if num(v) is not None and num(v) >= 1.0]
    avd = [k.upper() for k, v in bp.items() if num(v) is not None and num(v) <= -1.0]
    plan = ""
    if tgt: plan += f"<span class='chip grn'>ATTACK VIA <b>{' · '.join(tgt)}</b></span>"
    if avd: plan += f"<span class='chip red'>DO NOT TARGET <b>{' · '.join(avd)}</b></span>"
    funnels = ''.join(f"<div class='claim'><span class='ctag' style='color:var(--warn);border-color:rgba(251,191,36,.4)'>FUNNEL</span>{esc(f)}</div>"
                      for f in dp.get('funnels', []))
    rook = ''.join(f"<div class='claim'><span class='ctag'>ADD</span>{esc(r[0])} ({esc(r[1])}, {esc(r[3])}) — {esc(r[2])}</div>"
                   for r in (dp.get('rookies') or [])[:4])
    outlook = esc(E.get('defense_outlook', ''))
    # BRAIN on this defense: curated defense tweets + the DC's own vault entry when mentioned
    dtw = ''.join(f"<div class='tw'><span class='twtag'>{esc(x['tg'])}</span>{esc(x['t'][:200])}</div>"
                  for x in BT.get('dtw', []))
    dce = BI['coaches'].get(E.get('dc', ''), {})
    dctw = ''.join(f"<div class='tw'><span class='twtag'>DC intel</span>{esc(x['t'][:200])}</div>"
                   for x in (dce.get('tw') or [])[:2])
    brain_block = (f"<div class='prosebox' style='margin-top:12px'><b>🧠 Brain on this defense:</b>{dtw}{dctw}</div>"
                   if (dtw or dctw) else
                   "<div class='legend' style='margin-top:10px'>🧠 vault carries no defense-specific intel for this team yet — the daily ingest will fill it as camp coverage starts.</div>")
    # ---- NGS AUGMENTING LAYER (nflpro_2025.json): real per-alignment charting, cross-checked vs FTN ----
    ng = NGS.get(TEAM, {})
    ngs_block = ""
    if ng:
        pp = ng.get('pass', {})
        def ngchip(lbl, key):
            e = pp.get(key)
            if not e: return ""
            sp = e['soft_pctl']; cls = 'grn' if sp >= 65 else ('red' if sp <= 35 else '')
            tag = 'TARGET' if sp >= 65 else ('AVOID' if sp <= 35 else 'neutral')
            return f"<span class='chip {cls}'>{lbl} <b>{sp}th · {tag}</b></span>"
        ngrows = "".join(ngchip(l, k) for l, k in [("Slot",'slot'),("Wide",'wide'),("Tight/TE",'tight'),
                                                   ("Deep",'deep'),("Short",'short'),("Play-action",'play_action')])
        rn = ng.get('rush', {})
        if rn: ngrows += f"<span class='chip {'grn' if rn['soft_pctl']>=65 else ('red' if rn['soft_pctl']<=35 else '')}'>Run <b>{rn['soft_pctl']}th · {'TARGET' if rn['soft_pctl']>=65 else ('AVOID' if rn['soft_pctl']<=35 else 'neutral')}</b></span>"
        # boom-bust detector: soft on EPA (>=65) but tight on separation (<=35) = covers tight, gives explosives
        bb = [k for k in ('slot','wide','tight','deep') if pp.get(k) and pp[k]['soft_pctl'] >= 65 and pp[k]['sep_pctl'] <= 35]
        bbnote = (f"<div class='legend' style='margin-top:6px'>⚡ Boom-bust lanes (covers tight, bleeds explosives): <b>{', '.join(bb)}</b> — high EPA allowed on low separation.</div>" if bb else "")
        # FTN agreement note for the alignment story
        f2 = DPROF.get(TEAM, {}).get('dvoa_fpaa', {})
        ftn_te = f2.get('te'); ngs_te = pp.get('tight', {}).get('soft_pctl')
        agree = ""
        if ftn_te is not None and ngs_te is not None:
            both_soft = ftn_te >= 1.5 and ngs_te >= 65; both_stiff = ftn_te <= -1.5 and ngs_te <= 35
            agree = ("<span class='chip grn'>NGS + FTN AGREE: TE is a green lane</span>" if both_soft else
                     ("<span class='chip red'>NGS + FTN AGREE: TE is a wall</span>" if both_stiff else
                      "<span class='chip'>NGS/FTN mixed on TE — read both</span>"))
        ngs_block = f"""<div style='margin-top:16px;border-top:1px solid var(--line);padding-top:12px'>
<div class='legend'><b style='color:var(--accent)'>NGS 2025 (Next Gen Stats)</b> — real per-alignment charting from the NFL Pro scrape, season-aggregated. Augments FTN above; percentiles are attacker-view (high = softer = target). <i>2025 actuals, same vintage caveat as FTN.</i></div>
<div class='chips' style='margin-top:8px'>{ngrows}</div>
{bbnote}
<div class='chips' style='margin-top:8px'>{agree}</div></div>"""
    return f"""<div class='legend'>Matchup view: percentiles inverted to the ATTACKER'S perspective — 89th pctl = softer than 89% of defenses. <span style='color:var(--good)'>green = target</span> · <span style='color:var(--bad)'>red = cannot target</span>.</div>
<div class='chips' style='margin-top:8px'>{rows}</div>
<div class='chips' style='margin-top:8px'><span class='chip' style='border:none;color:var(--ink3)'>FTN FPAA lanes (+ = target, − = wall):</span>{leak_rows}</div>
<div class='chips' style='margin-top:8px'>{plan}</div>
<div class='prosebox' style='margin-top:12px'><b>Canon:</b> {outlook}<br><br>{funnels}{rook}</div>
{ngs_block}
{brain_block}"""

cards = ''.join(card(v) for v in players if num(SIG.get(fn(v['name']), {}).get('proj_pg')) or fn(v['name']) in (fn(x) for x in READS))

doc = f"""<!DOCTYPE html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>{TEAM_FULL} 2026 — Team Preview</title><style>
:root{{--bg:#0b0f17;--panel:#111726;--panel2:#0e1420;--line:#1e2738;--line2:#28324a;--ink:#e8edf6;--ink2:#aab6cc;
--ink3:#6b7890;--mono:'SF Mono',Consolas,monospace;--good:#34d399;--bad:#f87171;--warn:#fbbf24;--accent:#5b9dff;--brain:#b3a6ff;
--red:#c8102e}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.6 -apple-system,'Segoe UI',Roboto,sans-serif}}
header{{padding:40px 30px 24px;border-bottom:1px solid var(--line);background:
radial-gradient(1100px 320px at 15% -40%,rgba(200,16,46,.22),transparent),
radial-gradient(900px 280px at 85% -40%,rgba(91,157,255,.12),transparent)}}
.kick{{font-size:11px;letter-spacing:2.5px;color:var(--ink3);text-transform:uppercase}}
h1{{margin:6px 0 2px;font-size:30px}}h1 span{{color:#ff5a6e}}
.subtitle{{font-size:15px;color:var(--ink2);font-style:italic}}
.chips{{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}}
.chip{{border:1px solid var(--line2);border-radius:8px;padding:5px 11px;font-size:12px;color:var(--ink2)}}
.chip b{{color:var(--ink)}} .chip.red{{border-color:rgba(248,113,113,.5);color:#ffb3bb}}
.chip.grn{{border-color:rgba(52,211,153,.5);color:#8ee7bd}}
section{{max-width:1150px;margin:26px auto;padding:0 22px}}
h2{{font-size:13px;letter-spacing:2px;text-transform:uppercase;color:var(--accent);border-bottom:1px solid var(--line);
padding-bottom:8px}}h2.brainh{{color:var(--brain)}}
.prosebox{{background:var(--panel2);border:1px solid var(--line);border-radius:12px;padding:16px 20px;color:var(--ink2);
line-height:1.7;max-width:120ch}}.prosebox b{{color:var(--ink)}}.prosebox i{{color:var(--brain)}}
.envwrap{{display:flex;gap:4px;align-items:flex-end;background:var(--panel2);border:1px solid var(--line);
border-radius:12px;padding:18px 14px 10px;overflow-x:auto}}
.ecol{{flex:1;min-width:44px;text-align:center;font-family:var(--mono);font-size:10px;color:var(--ink3)}}
.ebar{{height:90px;display:flex;align-items:flex-end;justify-content:center}}
.ebar div{{width:20px;border-radius:4px 4px 0 0;background:linear-gradient(180deg,#f87171,#7f1d1d)}}
.ecol.even .ebar div{{background:linear-gradient(180deg,#34d399,#065f46)}}
.ecol.fav .ebar div{{background:linear-gradient(180deg,#5b9dff,#1e3a8a)}}
.ewk{{margin-top:5px;color:var(--ink2)}}.eline{{color:var(--warn)}}.eimp{{color:var(--ink)}}
.legend{{font-size:11px;color:var(--ink3);margin-top:8px}}
.pcard{{border:1px solid var(--line2);border-radius:12px;padding:14px 17px;margin:12px 0;background:var(--panel)}}
.prow{{display:flex;align-items:center;gap:10px;flex-wrap:wrap}}
.pname{{font-weight:800;font-size:16px}}
.pos{{font-size:9px;font-weight:800;border-radius:4px;padding:2px 7px}}
.pos.QB{{background:#3b2a55;color:#c8a8ff}}.pos.RB{{background:#173b2c;color:#6ee7a8}}
.pos.WR{{background:#16324e;color:#7cc0ff}}.pos.TE{{background:#4a3517;color:#fbbf6e}}
.bcnt{{margin-left:auto;font-family:var(--mono);font-size:10.5px;color:var(--ink3)}}
.meta{{font-family:var(--mono);font-size:12px;color:var(--ink2);margin-top:6px}}.meta b{{color:var(--ink)}}
.fchips{{display:flex;flex-wrap:wrap;gap:6px;margin-top:7px}}
.fc{{font-family:var(--mono);font-size:10.5px;border:1px solid var(--line2);border-radius:6px;padding:2px 7px;color:var(--ink3)}}
.fc b{{color:var(--ink2)}}.fc.hi{{border-color:rgba(52,211,153,.45)}}.fc.hi b{{color:var(--good)}}
.fc.lo{{border-color:rgba(248,113,113,.45)}}.fc.lo b{{color:var(--bad)}}
.read{{margin-top:9px;font-size:13px;line-height:1.65;color:var(--ink)}}
.lean{{margin-top:8px;font-size:12.5px;color:var(--ink2);border-left:2px solid var(--brain);padding-left:9px}}
.ltag{{font-size:8.5px;font-weight:800;color:var(--brain);letter-spacing:.6px;margin-right:6px;text-transform:uppercase}}
.claim{{margin-top:6px;font-size:12px;color:var(--ink2)}}
.ctag{{font-size:8.5px;font-weight:800;color:var(--good);letter-spacing:.4px;margin-right:6px;border:1px solid rgba(52,211,153,.4);
border-radius:4px;padding:1px 5px}}
.tw{{margin-top:6px;font-size:11.5px;color:var(--ink3)}}
.twtag{{font-size:8.5px;font-weight:800;color:#7fb5e8;letter-spacing:.5px;margin-right:6px;text-transform:uppercase}}
.wks{{display:flex;flex-wrap:wrap;gap:7px;margin-top:9px}}
.wk{{font-family:var(--mono);font-size:10.5px;border:1px solid var(--line2);border-radius:6px;padding:3px 8px;color:var(--ink3)}}
.wk b{{margin:0 3px}}.wk i{{font-style:normal;color:var(--ink3)}}
.wk.FAV{{border-color:rgba(52,211,153,.5)}}.wk.FAV b{{color:var(--good)}}
.wk.TOUGH{{border-color:rgba(248,113,113,.5)}}.wk.TOUGH b{{color:var(--bad)}}
.wk.NEU b{{color:var(--ink2)}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
@media(max-width:900px){{.two{{grid-template-columns:1fr}}}}
footer{{max-width:1150px;margin:34px auto;padding:0 22px 44px;color:var(--ink3);font-size:11.5px}}
</style></head><body>
<header>
 <div class='kick'>2026 Team Preview · Brain × Model</div>
 <h1><span>{TEAM_FULL}</span></h1>
 <div class='subtitle'>{esc(P.get('title',''))}</div>
 <div class='chips'>
  <span class='chip'>HC <b>{esc(E.get('hc'))}</b></span><span class='chip'>OC <b>{esc(E.get('oc'))}</b></span>
  <span class='chip'>DC <b>{esc(E.get('dc'))}</b></span>
  <span class='chip red'>win total <b>{E.get('win_total_2026')}</b></span>
  <span class='chip red'>avg implied <b>{avg_imp:.1f} pts</b></span>
  <span class='chip red'>underdog in <b>{dog_all}/{len(env_rows)}</b> simmed games</span>
  <span class='chip'>scheme <b>{esc(SCH.get('note','')[:44])}</b></span>
  <span class='chip grn'>brain: <b>{BT.get('n_tw','–')}</b> team tweets · <b>{BT.get('n_src','–')}</b> sources</span>
 </div>
</header>

<section><h2>The Regime</h2><div class='prosebox'>{P.get('regime','')}</div>{personnel_html()}</section>

<section><h2 class='brainh'>The QB Situation — and the Brissett Receipts</h2><div class='prosebox'>{P.get('qb','')}</div></section>

<section><h2>Season Environment — every game, implied points & line</h2>
<div class='envwrap'>{env_strip()}</div>
<div class='legend'>bar height = implied team total · red = underdog · green = within a field goal · number rows: line / implied. The two green weeks are W15 and W17 — the best-ball payout window.</div>
<div class='prosebox' style='margin-top:12px'>{P.get('env','')}</div>
<div style='margin-top:10px'>{team_tws}</div>
</section>

<section><h2>Defensive Identity — strengths · weaknesses · funnels</h2>
{def_identity_html()}
{f"<div class='prosebox' style='margin-top:12px'>{P.get('defid','')}</div>" if P.get('defid') else ""}
</section>

<section><h2>The Assets — model card × brain read</h2>{cards}</section>

<section><h2 class='brainh'>Fantasy Verdict</h2><div class='prosebox'>{P.get('verdict','')}</div></section>

<footer>Model: player_sim_distributions (12k correlated sims) · draft_board_signals · fusion_table (17 signals) · statmenu env (pace {players[0].get('team_env',{}).get('pace_pctl','–') if players else '–'}th pctl · {players[0].get('team_env',{}).get('plays_pg','–') if players else '–'} plays/g · off quality {players[0].get('team_env',{}).get('off_q','–') if players else '–'}) · game_sim Vegas anchors · defense_splits (their D: coverage {u.get('pass_cov_pctl','–')}th pctl · rush {u.get('pass_rush_pctl','–')}th · run {u.get('run_def_pctl','–')}th · leaks RB {bp.get('rb','–')} / TE {bp.get('te','–')} FPAA). Brain: brain_intel.json — SS 2026 leans, film-log claims, stats-first tweets · coaching from the audited web_teams canon. Built July 5, 2026.</footer>
</body></html>"""

out = f"{HERE}/team_preview_{TEAM}.html"
open(out, 'w', encoding='utf-8').write(doc)
print(f"wrote {out} ({os.path.getsize(out)/1000:.0f} KB) · {len(players)} players · {len(env_rows)} simmed games")
