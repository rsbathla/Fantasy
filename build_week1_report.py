#!/usr/bin/env python3
"""build_week1_report.py — WEEK 1 2026 two-sided analysis as a designed, self-contained HTML.
Model side: game_sim.json (Vegas-anchored script MC) + sim distributions + the SAME matchup engine
build_splits.py uses for W15-17 (coverage/run points-saved percentiles + shell), pointed at Week 1
opponents. Brain side: brain_intel.json forward leans + stats-first tweet curation. Per-player
matchup cards inside every game. No ADP anywhere — DFS logic by design."""
import json, csv, re, os, html

HERE = os.path.dirname(os.path.abspath(__file__)); DL = os.path.dirname(HERE)
def fn(n):
    n = str(n).strip().lower(); n = re.sub(r"\s+(jr|sr|ii|iii|iv|v)\.?$", "", n)
    return n.replace(".", "").replace("'", "").replace("-", " ")
def num(x, d=None):
    try: return float(x)
    except Exception: return d

# ---------- matchup engine (identical logic to build_splits.py, W1 opponents) ----------
dm = json.load(open(f"{DL}/dfs_review/out/defense_2026_matchup.json"))
covs = sorted(v['cov'] for v in dm.values()); runs = sorted(v['run'] for v in dm.values())
def pctl(sv, x):
    import bisect; return round(100 * bisect.bisect_left(sv, x) / max(1, len(sv) - 1))
TMAP = {'LA':'LAR','JAC':'JAX','WSH':'WAS','ARZ':'ARI','GNB':'GB','KAN':'KC','SFO':'SF','TAM':'TB','NWE':'NE','NOR':'NO'}
def tm(t): t = str(t).strip().upper(); return TMAP.get(t, t)
DEF = {tm(t): {'covp': pctl(covs, v['cov']), 'runp': pctl(runs, v['run'])} for t, v in dm.items()}
_cov_rows = list(csv.DictReader(open(f"{HERE}/defense_coverage.csv")))
_mr = sorted(num(r['def_man_rate']) for r in _cov_rows)
_sk = sorted(num(r['def_sack_rate']) for r in _cov_rows)
SCH = {tm(r['team']): {'manp': pctl(_mr, num(r['def_man_rate'])),
                       'sackp': pctl(_sk, num(r['def_sack_rate']))} for r in _cov_rows}
DS = json.load(open(f"{HERE}/defense_splits.json"))

F = {fn(r['name']): r for r in csv.DictReader(open(f"{HERE}/fusion_table.csv"))}
S = list(csv.DictReader(open(f"{HERE}/draft_board_signals.csv")))
L2 = {fn(r['name']): r for r in csv.DictReader(open(f"{HERE}/pipeline/layer2_player_params.csv"))}
BI = json.load(open(f"{HERE}/brain_intel.json"))
BP = {fn(k): v for k, v in BI['players'].items()}
WT = {t['team']: t for t in json.load(open(f"{HERE}/web_teams.json"))}
GS = json.load(open(f"{HERE}/game_sim.json"))['weeks']['1']['games']
GW = json.load(open(f"{HERE}/pipeline/games_by_week.json"))['1']

# ---------- position-channel defensive reads (defense_splits.json) ----------
# by_pos = FPAA by position group: POSITIVE = leaks (allows more than avg), NEGATIVE = wall.
# units pctls: HIGHER = BETTER defense. vs_man/vs_zone/deep/short softness: HIGHER = SOFTER.
def dread(opp):
    d = DS.get(opp, {})
    bp = d.get('by_pos', {}); u = d.get('units', {}); sh = d.get('shell', {})
    return {
        'rb': num(bp.get('rb'), 0), 'wr': num(bp.get('wr'), 0), 'te': num(bp.get('te'), 0),
        'qb': num(bp.get('qb'), 0), 'wr1': num(bp.get('wr1'), 0), 'wr2': num(bp.get('wr2'), 0),
        'slot': num(bp.get('slot'), 0),
        'cov': num(u.get('pass_cov_pctl'), 50), 'rush': num(u.get('pass_rush_pctl'), 50),
        'rund': num(u.get('run_def_pctl'), 50),
        'man_rate': num(sh.get('man_rate'), 25), 'soft_man': num(d.get('vs_man', {}).get('softness_pctl'), 50),
        'soft_zone': num(d.get('vs_zone', {}).get('softness_pctl'), 50),
        'soft_deep': num(d.get('deep', {}).get('softness_pctl'), 50),
        'soft_short': num(d.get('short', {}).get('softness_pctl'), 50),
    }

def leak_word(v):
    if v >= 3: return f"one of the league's leakiest (+{v:.1f} FPAA)"
    if v >= 1.5: return f"leaks (+{v:.1f} FPAA)"
    if v <= -3: return f"a wall ({v:.1f} FPAA)"
    if v <= -1.5: return f"stingy ({v:.1f} FPAA)"
    return f"about average ({v:+.1f} FPAA)"

def content_tweet(b):
    """First tweet whose TEXT carries information. Kills caption-only chart titles
    ('X - every throw of 20+ air yards from a clean pocket in 2025' — the data is in the image)."""
    for x in (b.get('tw') or []):
        t = str(x.get('t', ''))
        digits = len(re.findall(r"\d+\.?\d*", t))
        if re.search(r"- every throw of|clean pocket in 20\d\d\s*$", t): continue
        if len(t) < 95 and digits <= 2: continue        # short + numberless = caption/banter
        return x
    return None

def profile(pos, f):
    g = lambda k: num((f or {}).get(k)); tags = []; ml = None
    sep, exp, rt, yac, rune = g('separation_pctl'), g('explosive_pctl'), g('route_eff_pctl'), g('yac_pctl'), g('run_eff_pctl')
    if pos in ('WR', 'TE'):
        if sep and sep >= 65: tags.append('separator'); ml = 'man'
        if rt and rt >= 65 and (not sep or sep < 65): tags.append('route-tech'); ml = 'zone'
        if exp and exp >= 65: tags.append('big-play')
        if yac and yac >= 70: tags.append('YAC')
        if not tags: tags.append('volume-dependent')
    elif pos == 'RB':
        if rune and rune >= 65: tags.append('efficient')
        if exp and exp >= 65: tags.append('big-play')
        if not tags: tags.append('volume-dependent')
    elif pos == 'QB':
        if exp and exp >= 60: tags.append('downfield')
        if not tags: tags.append('matchup-sensitive')
    return tags, ml

def verdict2(pos, opp, ml, tgt_share, carry_share, wr_rank):
    """Channel-weighted verdict: grade the matchup against the lanes THIS player scores through,
    not the defense's generic quality. Returns (chip, why-with-numbers, D-read dict)."""
    D = dread(opp)
    why = []
    if pos == 'RB':
        run_s = 2 if D['rund'] <= 35 else (-2 if D['rund'] >= 65 else 0)
        rec_s = 2 if D['rb'] >= 2.5 else (1 if D['rb'] >= 1.2 else (-2 if D['rb'] <= -2.5 else (-1 if D['rb'] <= -1.2 else 0)))
        w_rec = 0.5 if (tgt_share or 0) >= 0.12 else (0.35 if (tgt_share or 0) >= 0.08 else 0.2)
        score = (1 - w_rec) * run_s + w_rec * rec_s
        why.append(f"run front {D['rund']:.0f}th pctl")
        why.append(f"RB coverage {D['rb']:+.1f} FPAA")
    elif pos in ('WR', 'TE', 'QB'):
        cov_s = 2 if D['cov'] <= 35 else (-2 if D['cov'] >= 65 else 0)
        lane = D['te'] if pos == 'TE' else (D['qb'] if pos == 'QB' else (D['wr1'] if wr_rank == 1 else D['wr2']))
        lane_s = 1.5 if lane >= 2 else (0.7 if lane >= 1 else (-1.5 if lane <= -2 else (-0.7 if lane <= -1 else 0)))
        axis_s = 0
        if pos != 'QB' and ml == 'man' and D['man_rate'] >= 30 and D['soft_man'] >= 65: axis_s = 1
        if pos != 'QB' and ml == 'zone' and D['man_rate'] <= 22 and D['soft_zone'] >= 65: axis_s = 1
        rush_s = -1 if D['rush'] >= 85 else 0
        score = cov_s + lane_s + axis_s + rush_s
        why.append(f"coverage {D['cov']:.0f}th pctl")
        lane_nm = 'TE' if pos == 'TE' else ('QB' if pos == 'QB' else f"WR{wr_rank}")
        why.append(f"{lane_nm} lane {lane:+.1f} FPAA")
        if rush_s: why.append(f"rush {D['rush']:.0f}th")
    else:
        return ('NEU', 'no rating', D)
    chip = 'FAV' if score >= 1.4 else ('TOUGH' if score <= -1.4 else 'NEU')
    return (chip, ' · '.join(why), D)

def shell_line(opp):
    d = DS.get(opp)
    if not d: return ''
    sh = d.get('shell', {}); u = d.get('units', {})
    man = sh.get('man_rate'); sh1 = sh.get('single_high')
    soft_man = d.get('vs_man', {}).get('softness_pctl'); soft_zone = d.get('vs_zone', {}).get('softness_pctl')
    bits = []
    if man is not None: bits.append(f"{man:.0f}% man")
    if sh1 is not None: bits.append(f"{sh1:.0f}% single-high")
    if soft_man is not None and soft_zone is not None:
        weak = "softer vs man" if soft_man > soft_zone else "softer vs zone"
        bits.append(f"{weak} ({max(soft_man, soft_zone):.0f}th pctl)")
    return " · ".join(bits)

# per-game prose: model read / brain read / synthesis (condensed from the approved capsules)
P = {
"DAL,NYG": ("Highest total on the board and a coin flip (DAL 52%) with the fattest right tail: 46% shootout, a 28% blowout share that cuts both ways, and no dominant script (24% Dallas control-run vs 31% Giants comeback-pass).",
 "Dak's lean is a volume bet — “near the top of the league in passing volume stats.” CeeDee has TD regression coming (3 TDs on a 21.7% share year); Pickens raised per-route production <i>while adding routes</i>. Across the field it's the Harbaugh/Nagy debut: Dart's 18.8 sim mean is sneaky, Skattebo owned 100% of early downs in his healthy games, and Likely/Mooney arrive with a leaked 12-personnel plan.",
 "The premier stack game. Dak–CeeDee–Pickens with a Nabers or Skattebo bring-back is the straight build; Dart–Nabers–Likely is the leverage version of the same 51-point world."),
"BAL,IND": ("Baltimore wins 60% but the modal margin is one score, and the dog-comeback-pass script hits 36% — Indy trailing-and-throwing is a live, common world. Lamar leads the game (20.0 mean / 36.8 p95).",
 "Minter's HC debut with Doyle calling plays: Lamar's play-action rate fell to 20th (17.3 FPG) from 10th (25.8) — the install decides which returns. Flowers brings a 72.5%-vs-man / 85.4%-vs-zone success profile. Taylor's 412-route season is a usage inflection, with front-office intel that they “need to win games this year.” Warren was TE4 in XFP/G as a rookie; Daniel Jones is on an Achilles rehab.",
 "Taylor is script-proof: 50-point total, career-high receiving role, and his team throws in 36% of worlds. Lamar–Flowers with a Taylor bring-back; Warren is the leverage TE."),
"CIN,TB": ("Cincinnati's 27.5 implied is second-best on the slate; 65% win, “pulls away” at 35%, and Chase's p95 (46.7) is the widest elite-WR ceiling of the week.",
 "Chase's lean is target-dominance escalation — career-high TPRR. Chase Brown is a true three-down back (69/54 catches, 69.2% i10 share, 13.6% target share, 21.0 FPG when Burrow finishes). Higgins: elite per-route, snap-capped. Tampa opens the Zac Robinson (McVay-branch) era with Godwin as the WR1 question; Egbuka faded late (zero TDs final eight); Gainwell's trailing-game profile was RB7 in PPG from W11 with a 17.5% target share.",
 "Burrow–Chase(–Higgins) is the primary. Gainwell is the trailing-script RB in a 44% dog-pass game."),
"LAR,SF": ("Rams 63% with a 29% blowout share; SF-trailing is the most common script world (41%). Puka's distribution is the best on the slate (21.1 / 49.8).",
 "Puka: 34%+ TPRR two straight years and the YPRR-since-2006 chart calls it “a generational run” — with the §11 availability review the week's single biggest swing. Stafford's lean pre-buts the TD-regression take (lookahead lines project LAR for the most points in football). Kyren: three straight 250+ PPR years, RB5 in RZ expected points. SF: Kittle's Achilles is the canon's variable; CMC carries a 9/1 Signal log.",
 "The best player-spot on the slate <i>if</i> Puka plays. If Friday clouds it, Kyren and Adams absorb the equity quietly. Stafford–Puka vs a CMC bring-back is max correlation."),
"DET,NO": ("Detroit's 27.5 implied ties CIN; 73% win probability, 32% blowout share, DET-pulls-away at 41%.",
 "Gibbs' usage-athleticism cohort is himself and Bijan; the film log openly questions Montgomery's share. New Orleans is a debut lab: Kellen Moore's two-TE scheme around Shough (strong pocket-production metrics, nine starts), Etienne as the imported lead back, Olave elite-target history with cost caution.",
 "Favorite-onslaught: Gibbs/ASB builds don't need the Saints to cooperate. Leverage: Shough–Olave in the 51% dog-pass worlds."),
"PHI,WAS": ("Philadelphia 72% with a 27.0 implied; Hurts' 19.8 mean on a 0.35 CV is the narrowest elite-QB floor in the sim.",
 "New OC Mannion inherits a run-first identity: Saquon is the center of gravity until the pass game proves otherwise. DeVonta's without-Brown split (32.9% target share, 2.65 YPRR) is now his every-week reality; Lemon starts in the slot per camp intel. Washington: Blough's under-center shift is corroborated by McLaurin himself (13th YPRR, 4th in first-downs/route).",
 "Hurts–Saquon–Smith is the favorite build; Daniels' rushing floor keeps the 47% dog-pass builds honest."),
"BUF,HOU": ("The slate's oddity: Houston favored by a hair, modal world a one-score grind (36%). Allen still owns the best QB distribution on the board (22.3 / 41.9).",
 "Joe Brady's HC debut. DJ Moore arrives with 1.44/1.22 YPRR seasons and a 14.3% TPRR — “cratering TPRRs shouldn't follow him to new digs.” Kincaid's paradox: 2.79 YPRR on deliberately limited routes. Houston's rebuilt O-line is the swing factor; Nico's per-route profile showed “minor cracks”; Montgomery was #1 in man/gap rushing EPA on a team top-6 in man/gap frequency.",
 "Allen's floor doesn't need a shootout. Allen–Shakir–Kincaid is the cheap correlation; Stroud–Collins the honest other side."),
"GB,MIN": ("Effectively a pick'em (GB 53%) with a grind lean (37%); neither implied total cracks 24.",
 "The vault's verdict on the MIN QB room: “it was over the moment they signed Kyler.” Jefferson's rebound lean is full-throated — 1.88 YPRR after a career above 2.5, with target rate, YAC and film all intact. Green Bay: Jacobs carries a TD-value warning <b>and an unresolved injury-news flag</b>; Watson was 4th in YPRR on a 56th-percentile route share; Golden's runway is cleared.",
 "Thin for DFS. Kyler–Jefferson is the vault-endorsed cheap stack the moment the job is confirmed."),
"CAR,CHI": ("Chicago 57% in a one-score, grind-leaning profile (38%).",
 "Ben Johnson Year 2 absorbs the Moore trade and Dalman's retirement: Loveland already led the team in receiving from Week 8 on (92-target pace), Odunze inherits the first-read volume, and Swift — #1 among RBs in zone-concept EPA/rush — spent camp on route work “because the offense will be good.” Carolina: Tet's 10/0 Signal log vs Coker's per-route counter (2.30 vs 1.78 YPRR late); Hubbard's volume is fragile; Young appears in the vault's leap-QB EPA framework.",
 "Caleb–Loveland is the debut-scheme continuation; the usage math is the whole story."),
"ARI,LAC": ("The hammer: LAC −13 with a 29.0 implied (best on slate), 86% win, 49% blowout, and a 61% favorite-control-run script — the clearest single-script game of the week.",
 "Jim Harbaugh imported McDaniel's outside-zone for Herbert; Hampton's 3.36 yards-after-contact/attempt (best of 45 qualifiers) is the profile the script wants. McConkey's usage metrics are modest (WR32 TPRR, WR33 first-read share) — this is the rare spot where the script rescues them. Arizona: LaFleur-debut teardown, Brissett room, Jeremiyah Love as the identity, and McBride's #1 TE target share (27.4%) colliding with a 16.0 implied total.",
 "Hampton is the script's chosen one. McBride is a floor play here, not a ceiling one — volume survives blowouts, efficiency doesn't."),
"NE,SEA": ("Seattle 62% with a 29% blowout share against a grind-heavy total. JSN's sim line is the third-best WR distribution of the week.",
 "The champs open under new OC Fleury, replacing Kenneth Walker III: camp intel has Holani/Price splitting first-team reps while the vault bets against Charbonnet's January-ACL timeline. JSN's stat is historic — seven games at a 40%+ target share. New England: Maye's first-read leap (QB30 → QB1 passer rating), A.J. Brown's four straight elite-YPRR seasons against the loudest fade in the vault, and the Henderson/Stevenson split chart.",
 "Watch one report: Charbonnet. If he sits, Price opens with real work in a −3.5 favorite. Maye–Brown = metric spine + public doubt — the tournament combination."),
"ATL,PIT": ("Pittsburgh 66% in the slate's second-grindiest profile (45%).",
 "Two debuts. Atlanta: Stefanski's run-heavy install with the QB room unsettled (Tua inside track over ACL-recovering Penix); Bijan's lean stays “superstar in his prime”; Pitts is 4th in EPA-when-targeted with a 22.7% target share entering a historically TE-friendly scheme. Pittsburgh: McCarthy's West Coast around a 42-year-old Rodgers; the Pittman-vs-Metcalf argument is a genuine analyst split the sim scores a dead heat (11.6 vs 11.5) — the first-read bet leans Pittman.",
 "Bijan is matchup-proof. The Rodgers first-read pecking order is the only Week 1 question that matters here."),
"DEN,KC": ("Kansas City 61% in the week's grindiest divisional game (50% of sims under 42).",
 "Bieniemy is back and Mahomes opens off the ACL — the lean: less rushing, but passing efficiency boosted by a real run game. Walker's projected 55% rush share and 74.8% of KC's RZ carries meet a <b>TOUGH Denver run front per the matchup engine</b> — volume vs wall, with the RZ share as the TD path. Rice: “target-dominant No. 1, good bet” — 3rd in NFL target rate with zero added competition. Denver: Nix's suppression lean, Waddle top-12 in five per-route metrics on last year's 29th pass offense, Dobbins efficient.",
 "A Rice game — target dominance beats environment. Walker's Week 1 case is the goal line, not the box score between the 20s."),
"LV,MIA": ("Las Vegas 65% — remarkable for a 5.5-win-total team — in a 50% grind profile.",
 "Kubiak's wide-zone debut “likely led by rookie Mendoza,” but the vault carries Cousins “running the huddle with great command… team is comfortable” — a live starter question. Jeanty: “far more signal in the 321-touch load than noise in the per-touch efficiency.” Bowers holds the position's #1 RZ target share (39.5%) on a sub-30% inline rate. Miami is bleak: Willis, a gutted WR room, and Achane's 9/0 Signal log carrying the whole offense.",
 "Jeanty control-run is the co-signed play; Achane needs nobody's permission. The LV QB announcement moves Bowers' floor."),
"CLE,JAX": ("Jacksonville 71% and half of all sims stay under 42; the JAX-pulls-away script hits 36%.",
 "Monken's debut comes with a wide-open QB room (Sanders/Watson/Gabriel/Green) that caps every Browns pass-catcher. Judkins carries a 7/0 log — against Monken's history of rotating backfield leaders yearly. Fannin's 21.4% rookie target share was 5th among TEs. Jacksonville: Year-2 continuity, Lawrence “gushing” over Parker Washington, Tuten's 48.3% rushing success rate (3rd of 55).",
 "Lawrence–Washington is the cheapest QB–WR correlation on the slate with a direct quote behind it."),
"NYJ,TEN": ("The floor: lowest total (41.0), grindiest profile (54% under 42). Breece and Garrett Wilson hold the only real ceilings.",
 "Veteran-coordinator debuts on both sides: Reich for Glenn with Geno; Daboll for Saleh with Ward (whose aDOT “jumped three and a half yards — an adult route tree now”). Wilson posted the NFL's biggest first-read target-share increase (+12.2). Wan'Dale: 140 targets in back-to-back years, 11th in xFP/G from Week 11 on, Daboll familiarity. Pollard's TRAP lean; Tate's zone-separation flashes vs a measured prospect lean.",
 "Avoid, except as a Breece/Wilson volume island — usage like theirs survives bad totals."),
}

opp_of = {}
for a, b in GW: opp_of[a] = b; opp_of[b] = a

sig_by_team = {}
for r in S:
    sig_by_team.setdefault(tm(r['team']), []).append(r)

def esc(x): return html.escape(str(x), quote=False)

# Hand-written interpretive openers for marquee spots — ONLY claims verified against the
# leak/shell data above or the vault; the composer adds the exact numbers beneath them.
HAND = {
 'James Cook III': "The three-source receiving-role intel is the season story — and this is the wrong week to cash it: Houston takes away exactly that lane. Volume holds; the efficiency lane defers.",
 'Josh Allen': "Houston's rush is the whole problem; their coverage crack is man-side, which they rarely play. Floor via the legs — ceiling needs the line to hold.",
 'Dak Prescott': "The volume lean gets a friendly first exam: the Giants' coverage leaks at nearly every alignment, and the only real tax is their front.",
 'Javonte Williams': "The Giants' RB-coverage leak is the redemption arc for his weak receiving profile — while the ground channel draws the tougher front.",
 "Ja'Marr Chase": "The leak map points his way: the WR1 lane is open, and Tampa's man snaps — when they play them — have been their softest look against separators.",
 'Tee Higgins': "Tampa's quiet strength is exactly his alignment: WR2s have been held under water while WR1s leak. The 27.5 team implied is the counterweight to a real alignment tax.",
 'Rashee Rice': "Denver walls off perimeter alphas but stays open in the slot and short game — Rice's schemed screens-and-short usage is precisely the lane that survives elite coverage. Bet the usage; temper the yardage.",
 'Kenneth Walker III': "Two walls in one matchup: a top-shelf run front AND stingy RB coverage. The 74.8% red-zone carry share is the whole Week 1 case — touchdowns travel where yards don't.",
 'Puka Nacua': "San Francisco's soft spot is man coverage they rarely play; expect zone-heavy looks that feed the underneath volume rather than cap it. Availability (§11) is the only real question.",
 'Jaxon Smith-Njigba': "The historic target share travels regardless of shell — New England can tax the efficiency, not the funnel.",
 'Drake Maye': "Seattle's back end is the stiffest early test of the first-read leap — a prove-it spot, not a smash spot.",
 'Jonathan Taylor': "The 412-route inflection is the script hedge: in the 60% of worlds where Baltimore leads, the checkdown lane is how the volume survives.",
 'Derrick Henry': "Indy's front punishes the ground channel — which makes the minicamp screens intel the release valve worth watching this specific week.",
 'Justin Jefferson': "Green Bay lives in zone and their zone has been stingy — a one-week tax on the rebound thesis; his man-beating profile only matters on the snaps they dare it.",
 'Jalen Hurts': "Washington's zone has been among the league's most beatable — the under-center ANY/A profile gets its friendliest shell, with their rush as the counterweight.",
 'Omarion Hampton': "The cleanest script-role fit of the week: a two-score-favorite outside-zone install feeding the best after-contact profile of 45 qualified backs.",
 'Trey McBride': "Elite target share into pressure and tight middle coverage — the volume floor is intact; the ceiling needs broken plays in a 16-point offense.",
 'De\'Von Achane': "The 9/0 film log doesn't need a soft front — touches are the thesis; the front is just the tax rate.",
 'Jahmyr Gibbs': "The cohort-of-two usage profile plays anywhere; New Orleans' front only sets the volume knob.",
}

def player_card(r, opp, g, wr_rank_map):
    nm = r['name']; pos = (r.get('pos') or '').upper(); k = fn(nm)
    f = F.get(k); tags, ml = profile(pos, f)
    l2 = L2.get(k, {}); b = BP.get(k, {})
    ts = num(l2.get('tgt_share')) or 0; cs = num(l2.get('carry_share')) or 0
    wr_rank = wr_rank_map.get(k, 2)
    v, why, D = verdict2(pos, opp, ml, ts, cs, wr_rank)
    proj = num(r.get('proj_pg')); p95 = num(r.get('p95'))
    usage = ""
    if pos in ('WR', 'TE') and ts: usage = f"{ts*100:.0f}% tgt share"
    elif pos == 'RB' and cs: usage = f"{cs*100:.0f}% carries · {ts*100:.0f}% tgt"

    # ---- the WRITTEN matchup read: player's channel × opponent's exact lane × script ----
    sents = []
    if nm in HAND: sents.append(HAND[nm])
    scr = g['script']; wnr = g['winner']; me_fav = (wnr['fav'] == tm(r.get('team') or ''))
    if pos == 'RB':
        ground = ("a soft front" if D['rund'] <= 35 else ("a stout front" if D['rund'] >= 65 else "an average front"))
        rec_lane = leak_word(D['rb'])
        sents.append(f"Ground channel: {ground} ({D['rund']:.0f}th-pctl run D). Receiving channel: {opp} is {rec_lane} to RBs" +
                     (f" — meaningful for a {ts*100:.0f}% target-share back." if ts >= 0.10 else "."))
        if me_fav and scr['fav_control_run'] >= 32:
            sents.append(f"Script helps: the {scr['fav_control_run']:.0f}% control-run world is his volume case.")
        elif not me_fav and scr['dog_comeback_pass'] >= 38:
            sents.append(f"Script risk: {scr['dog_comeback_pass']:.0f}% comeback-pass worlds shift work to the receiving lane" +
                         (" he owns." if ts >= 0.10 else " — not his lane."))
    elif pos in ('WR', 'TE'):
        lane = D['te'] if pos == 'TE' else (D['wr1'] if wr_rank == 1 else D['wr2'])
        lane_nm = "TEs" if pos == 'TE' else f"WR{wr_rank}s"
        sents.append(f"His lane: {opp} is {leak_word(lane)} to {lane_nm}, inside a {D['cov']:.0f}th-pctl coverage unit.")
        if ml == 'man':
            sents.append(f"Axis: a separator vs a {D['man_rate']:.0f}%-man shell that's {D['soft_man']:.0f}th-pctl soft when it does play man.")
        elif ml == 'zone':
            sents.append(f"Axis: route-tech profile vs {100-D['man_rate']:.0f}% zone that's {D['soft_zone']:.0f}th-pctl soft.")
        if 'big-play' in tags and D['soft_deep'] >= 62:
            sents.append(f"The deep ball is live: {opp} is {D['soft_deep']:.0f}th-pctl soft downfield.")
        if D['rush'] >= 85:
            sents.append(f"Tax: a {D['rush']:.0f}th-pctl rush shortens the route tree.")
    elif pos == 'QB':
        sents.append(f"Pocket math: {D['cov']:.0f}th-pctl coverage, {D['rush']:.0f}th-pctl rush; QBs overall have {leak_word(D['qb'])} here.")
        if D['soft_man'] >= 70 and D['man_rate'] >= 28:
            sents.append(f"They man up {D['man_rate']:.0f}% and it's their soft axis ({D['soft_man']:.0f}th) — throw on it.")
        if not me_fav and scr['dog_comeback_pass'] >= 38:
            sents.append(f"Volume backstop: {scr['dog_comeback_pass']:.0f}% comeback-pass worlds.")
    read = " ".join(sents)

    lean = (b.get('fwd') or [{}])[0].get('t', '') if b.get('fwd') else ''
    tw = content_tweet(b)
    twl = f"<div class='tw'><span class='twtag'>{esc(tw.get('tg',''))}</span>{esc(tw.get('t','')[:185])}</div>" if tw else ''
    leanl = f"<div class='lean'><span class='ltag'>2026 lean</span>{esc(lean[:190])}</div>" if lean else ''
    nums = " · ".join(x for x in [f"proj <b>{proj:.1f}</b>" if proj else "", f"p95 <b>{p95:.1f}</b>" if p95 else "", usage] if x)
    return f"""<div class='pcard'>
  <div class='prow'><span class='pname'>{esc(nm)}</span><span class='pos {pos}'>{pos}</span>
    <span class='verd {v}'>{v}</span><span class='why'>{esc(why)}</span></div>
  <div class='meta'>{nums}</div>
  <div class='read'>{esc(read)}</div>
  <div class='tags'>{''.join(f"<span class='tag'>{esc(t)}</span>" for t in tags)}<span class='shell'>{esc(opp)} shell: {esc(shell_line(opp))}</span></div>
  {leanl}{twl}
</div>"""

def bar(pct, cls):
    return f"<div class='bar'><div class='fill {cls}' style='width:{pct:.0f}%'></div><span>{pct:.0f}%</span></div>"

sections = []; navs = []
for g in GS:
    a, b = g['teams']; v, s, w, td, sc = g['vegas'], g['sim'], g['winner'], g['total_dist'], g['script']
    key = f"{a},{b}" if f"{a},{b}" in P else f"{b},{a}"
    model_p, brain_p, syn_p = P.get(key, ("", "", ""))
    gid = f"g{a}{b}"
    navs.append(f"<a href='#{gid}'><b>{a}–{b}</b><span>{v['total']}</span></a>")
    def team_block(t):
        e = WT.get(t, {})
        players = sorted(sig_by_team.get(t, []), key=lambda r: -(num(r.get('proj_pg')) or 0))[:5]
        # WR alignment lane: rank this team's WRs by target share (1 = faces the WR1 treatment)
        wrs = sorted([p for p in sig_by_team.get(t, []) if (p.get('pos') or '').upper() == 'WR'],
                     key=lambda p: -(num(L2.get(fn(p['name']), {}).get('tgt_share')) or 0))
        wr_rank_map = {fn(p['name']): i + 1 for i, p in enumerate(wrs)}
        cards = ''.join(player_card(r, opp_of[t], g, wr_rank_map) for r in players)
        return f"""<div class='teamcol'>
  <div class='thead'><span class='tname'>{t}</span><span class='coach'>HC {esc(e.get('hc','?'))} · OC {esc(e.get('oc','?'))}</span><span class='wt'>win total {e.get('win_total_2026','–')}</span></div>
  {cards}</div>"""
    fav = w['fav']; spread_txt = f"{v['spread_fav']} −{v['spread']:g}"
    sections.append(f"""<section class='game' id='{gid}'>
  <div class='ghead'>
    <div class='gtitle'>{a} – {b}</div>
    <div class='gnums'><span class='ou'>O/U <b>{v['total']}</b></span><span>{spread_txt}</span>
      <span>imp {a} <b>{v['imp'][a]:g}</b> · {b} <b>{v['imp'][b]:g}</b></span>
      <span>{fav} wins <b>{w['fav_win']:.0f}%</b></span></div>
    <div class='gbars'>
      <div class='blabel'>shootout 51+</div>{bar(td['shootout_51plus'], 'hot')}
      <div class='blabel'>grind ≤41</div>{bar(td['grind_41minus'], 'cold')}
      <div class='blabel'>{sc['fav']} control-run</div>{bar(sc['fav_control_run'], 'run')}
      <div class='blabel'>{sc['dog']} comeback-pass</div>{bar(sc['dog_comeback_pass'], 'pass')}
    </div>
  </div>
  <div class='prose'>
    <p><span class='side model'>MODEL</span>{model_p}</p>
    <p><span class='side brain'>🧠 BRAIN</span>{brain_p}</p>
    <p class='syn'><span class='side synl'>PLAY</span>{syn_p}</p>
  </div>
  <div class='teams'>{team_block(a)}{team_block(b)}</div>
</section>""")

meta = BI.get('_meta', {})
html_doc = f"""<!DOCTYPE html><html><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Week 1 · 2026 — Brain × Model</title><style>
:root{{--bg:#0b0f17;--panel:#111726;--panel2:#0e1420;--line:#1e2738;--line2:#28324a;--ink:#e8edf6;
--ink2:#aab6cc;--ink3:#6b7890;--mono:'SF Mono',Consolas,monospace;--good:#34d399;--bad:#f87171;
--warn:#fbbf24;--accent:#5b9dff;--brain:#b3a6ff}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);
font:14px/1.55 -apple-system,'Segoe UI',Roboto,sans-serif}}
header{{padding:34px 28px 20px;border-bottom:1px solid var(--line);background:
radial-gradient(1200px 300px at 20% -50%,rgba(91,157,255,.16),transparent),
radial-gradient(900px 260px at 80% -40%,rgba(179,166,255,.12),transparent)}}
h1{{margin:0;font-size:26px;letter-spacing:.3px}}h1 b{{color:var(--accent)}}h1 i{{color:var(--brain);font-style:normal}}
.sub{{color:var(--ink2);margin-top:8px;max-width:110ch}}
.hbox{{margin-top:12px;font-size:12px;color:var(--ink3);border:1px dashed var(--line2);border-radius:9px;
padding:9px 12px;max-width:110ch}}
nav{{position:sticky;top:0;z-index:9;display:flex;gap:6px;overflow-x:auto;padding:10px 20px;
background:rgba(11,15,23,.92);backdrop-filter:blur(6px);border-bottom:1px solid var(--line)}}
nav a{{flex:none;display:flex;flex-direction:column;align-items:center;gap:1px;padding:6px 11px;
border:1px solid var(--line2);border-radius:9px;color:var(--ink2);text-decoration:none;font-size:11px}}
nav a b{{color:var(--ink);font-size:12px}}nav a span{{font-family:var(--mono);color:var(--accent)}}
nav a:hover{{border-color:var(--accent);color:var(--ink)}}
.game{{margin:26px auto;max-width:1240px;padding:0 20px}}
.ghead{{background:linear-gradient(180deg,var(--panel),var(--panel2));border:1px solid var(--line2);
border-radius:14px 14px 0 0;padding:16px 20px;display:grid;grid-template-columns:210px 1fr 340px;gap:14px;align-items:center}}
.gtitle{{font-size:22px;font-weight:800;letter-spacing:.5px}}
.gnums{{display:flex;flex-wrap:wrap;gap:8px 18px;color:var(--ink2);font-size:13px}}
.gnums b{{font-family:var(--mono);color:var(--ink)}}.ou b{{color:var(--warn);font-size:15px}}
.gbars{{display:grid;grid-template-columns:auto 1fr;gap:3px 10px;font-size:10.5px;color:var(--ink3);align-items:center}}
.bar{{position:relative;height:10px;background:#151d2e;border-radius:6px;overflow:hidden}}
.bar span{{position:absolute;right:5px;top:-3px;font-family:var(--mono);font-size:9.5px;color:var(--ink2)}}
.fill{{height:100%;border-radius:6px}}.fill.hot{{background:linear-gradient(90deg,#f8717155,#f87171)}}
.fill.cold{{background:linear-gradient(90deg,#5b9dff44,#5b9dff)}}
.fill.run{{background:linear-gradient(90deg,#34d39944,#34d399)}}.fill.pass{{background:linear-gradient(90deg,#fbbf2444,#fbbf24)}}
.prose{{border:1px solid var(--line2);border-top:none;padding:14px 20px;background:var(--panel2);color:var(--ink2)}}
.prose p{{margin:7px 0;max-width:125ch}}.prose .syn{{color:var(--ink)}}
.side{{display:inline-block;font-size:9.5px;font-weight:800;letter-spacing:.8px;border-radius:5px;
padding:2px 7px;margin-right:9px;vertical-align:1px}}
.side.model{{background:rgba(91,157,255,.15);color:var(--accent);border:1px solid rgba(91,157,255,.35)}}
.side.brain{{background:rgba(179,166,255,.14);color:var(--brain);border:1px solid rgba(179,166,255,.35)}}
.side.synl{{background:rgba(52,211,153,.14);color:var(--good);border:1px solid rgba(52,211,153,.35)}}
.teams{{display:grid;grid-template-columns:1fr 1fr;gap:0;border:1px solid var(--line2);border-top:none;
border-radius:0 0 14px 14px;overflow:hidden}}
.teamcol{{padding:14px 16px;background:var(--panel)}} .teamcol+.teamcol{{border-left:1px solid var(--line2)}}
.thead{{display:flex;align-items:baseline;gap:10px;margin-bottom:10px;flex-wrap:wrap}}
.tname{{font-size:17px;font-weight:800;letter-spacing:1px}}
.coach{{color:var(--ink3);font-size:11.5px}}.wt{{margin-left:auto;font-family:var(--mono);font-size:11px;color:var(--ink3)}}
.pcard{{border:1px solid var(--line);border-radius:10px;padding:9px 12px;margin-bottom:8px;background:var(--panel2)}}
.prow{{display:flex;align-items:center;gap:8px;flex-wrap:wrap}}
.pname{{font-weight:700;font-size:13.5px}}
.pos{{font-size:9px;font-weight:800;border-radius:4px;padding:1px 6px}}
.pos.QB{{background:#3b2a55;color:#c8a8ff}}.pos.RB{{background:#173b2c;color:#6ee7a8}}
.pos.WR{{background:#16324e;color:#7cc0ff}}.pos.TE{{background:#4a3517;color:#fbbf6e}}
.verd{{font-size:9.5px;font-weight:800;border-radius:4px;padding:2px 7px;letter-spacing:.5px}}
.verd.FAV{{background:rgba(52,211,153,.16);color:var(--good);border:1px solid rgba(52,211,153,.4)}}
.verd.NEU{{background:rgba(150,160,180,.12);color:var(--ink3);border:1px solid var(--line2)}}
.verd.TOUGH{{background:rgba(248,113,113,.14);color:var(--bad);border:1px solid rgba(248,113,113,.4)}}
.why{{font-size:11px;color:var(--ink3)}}
.meta{{font-family:var(--mono);font-size:11.5px;color:var(--ink2);margin-top:4px}}.meta b{{color:var(--ink)}}
.read{{margin-top:6px;font-size:12.5px;line-height:1.6;color:var(--ink)}}
.tags{{margin-top:5px;display:flex;flex-wrap:wrap;gap:5px;align-items:center}}
.tag{{font-size:9.5px;border:1px solid var(--line2);border-radius:5px;padding:1px 6px;color:var(--ink2)}}
.shell{{font-size:10px;color:var(--ink3);font-family:var(--mono)}}
.lean{{margin-top:6px;font-size:12px;color:var(--ink2);border-left:2px solid var(--brain);padding-left:8px}}
.ltag{{font-size:8.5px;font-weight:800;color:var(--brain);letter-spacing:.6px;margin-right:6px;text-transform:uppercase}}
.tw{{margin-top:5px;font-size:11.5px;color:var(--ink3)}}
.twtag{{font-size:8.5px;font-weight:800;color:#7fb5e8;letter-spacing:.5px;margin-right:6px;text-transform:uppercase}}
footer{{max-width:1240px;margin:30px auto;padding:0 20px 40px;color:var(--ink3);font-size:11.5px}}
@media(max-width:900px){{.ghead{{grid-template-columns:1fr}}.teams{{grid-template-columns:1fr}}
.teamcol+.teamcol{{border-left:none;border-top:1px solid var(--line2)}}}}
</style></head><body>
<header><h1>Week 1 · 2026 — <b>Model</b> × <i>Brain</i></h1>
<div class='sub'>Sixteen games, two engines — and one question per player: <b>is this matchup good or bad for HIS upside?</b> Every card grades the opponent against the player's actual production channels: a receiving back is graded on the RB-coverage leak, not just the run front; a WR2 on the WR2 lane, not the unit average; a separator on the man snaps, a route-tech on the zone. The written read connects role intel → the exact lane numbers (FPAA leaks, coverage/rush/run percentiles, shell) → the script, and says what it means. DFS logic throughout — totals, scripts, usage. No ADP.</div>
<div class='hbox'>Honesty box: sim means are Vegas-anchored; dispersion/correlation/script splits are stated priors, not backtested. Lines are the July 4 board — re-anchor near lock. Brain intel through {esc(meta.get('generated','')[:10])}. Verdicts are matchup priors, not projections: a TOUGH tag lowers efficiency expectation, it does not erase volume.</div>
</header>
<nav>{''.join(navs)}</nav>
{''.join(sections)}
<footer>Model: game_sim.json (40k sims/game) · player_sim_distributions.csv (12k correlated sims, Jul 5) · defense_2026_matchup.json + defense_coverage.csv + defense_splits.json (matchup engine, same logic as build_splits.py) · fusion_table.csv profiles. Brain: brain_intel.json (stats-first curation) — Stealing Signals 2026 leans + metric tweets. Coaching from the audited web_teams canon. Built July 5, 2026.</footer>
</body></html>"""

out = f"{HERE}/week1_2026_report.html"
open(out, 'w', encoding='utf-8').write(html_doc)
print(f"wrote {out} ({os.path.getsize(out)/1000:.0f} KB) · {len(GS)} games")
