# FLAG-BASED, PLAYER-BY-PLAYER CEILING (BOOM) MODEL — agent brief

## What we're building & why
Replacing a crude boom model. User's exact asks:
- Boom must NOT be "1.5× the player's own projection" (that punished high-floor studs — Gibbs
  projects ~20 so he'd need 30+). **FIXED**: boom = a position spike threshold derived strictly
  (avg of the 85th pctl and mean+1SD of each position's STARTABLE-TIER weekly scoring; the two
  anchors agree within 8%). Thresholds (DK PPR points), NOT scaled to the player's own proj:
      QB 26.0 · RB 22.0 · WR 20.2 · TE 16.3 · DST 13.9
- "Look at ALL stats and find UNIQUE COMBINATIONS that let a player boom. The more flags we have,
  the higher the probability of a ceiling game. Not every stat needs to be present."
- **PLAYER BY PLAYER** — each player gets HIS OWN flag set from HIS actual stats. Do NOT apply one
  blanket template to a whole position. A 14.0-aDOT deep burner and a 9.0-aDOT volume slot are
  both WRs but must come out with DIFFERENT flags and DIFFERENT activators.

## The model (one sentence)
Ceiling probability in a week = the player's regularized base ceiling rate, multiplied UP by each
independent boom-enabling flag that lights up that week (skill × matchup × environment) and DOWN
by suppressors. More flags lit ⇒ higher probability. No single flag is required.

Three flag layers: (1) **skill** = intrinsic to the player, set/raise his base, each names the
matchup that AMPLIFIES it; (2) **matchup** = per opponent; (3) **environment** = per game (dome/home).

## Use boom_lib.py (already written — import it)
```
from boom_lib import load, players, reg_base, prob, label, write, cap, SWING
sm, gl, sch, de, bd = load()       # statmenu, gamelog, schedule2026, defense2026, boomdef
posbase = bd['posbase']            # {'QB':.114,'RB':.187,'WR':.178,'TE':.182,'DST':.159}
keys = players(sm, 'WR')           # statmenu keys for this position, ADP-sorted
b = reg_base(sm[k], posbase)       # regularized base rate (None if <4 games history)
p = prob(base, [1.35, 1.2, 1.1])   # base × lit multipliers, capped to [0.01, 0.80]
lab = label(p, base)               # 'SMASH' / 'GOOD' / 'NEU' / 'TOUGH'
write('WR', data)                  # verify-retry write -> boom/flags_WR.json
```
For DST, opponent-offense quality is in a separate file:
```
import json, os; OPP = json.load(open(os.path.join(os.path.dirname(__file__),'boom','opp_offense.json')))
# OPP[TEAM] = {"off_q":0-100 (higher=better offense=TOUGHER for DST),"qb":"Name","qb_q":0-100,
#               "ol_q":0-100 (opponent OFFENSIVE-LINE strength; LOW=weak OL=easy sacks),"pblock":0-100 (pass-protection)}
```

## Foundation schemas (bestball/boom/)
**statmenu.json[key]** (key = normalized name; DST keys look like "dst_buf"):
```
{"name","pos","team","adp","base_boom":0.857|null,"n_games":7,"boom_games":6,
 "fus":{value_pctl,ceiling_pctl,spike_pctl,boom_pctl,route_eff_pctl,coverage_proof_pctl,run_eff_pctl,
        rec_eff_pctl,separation_pctl,yac_pctl,rush_eff_pctl,explosive_pctl,protection_pctl,oline_pctl,
        matchup_pctl,adv_pctl,sis_value_pctl},          # 0-100 pctls, some missing per player
 "adot":{aDOT,TPRR,surplus_TPRR,routes},                 # {} for ~75% of players (96 have it)
 "yaco":{YACoe,MTFoe},                                    # yards-after-catch over expected
 "usage":{carry_pg,carry_share,ypc,tgt_share,catch_rate,ypt,dk_pg,routes_pg,rz_share,tgt_pg,rush_share}, # shares 0-1
 "role":"WR1|RB committee|...",
 "sis":{...},          # WR/TE:{YPRR,TPRR_w,airyard_pct,tgt_share_w,eff_combined,FP_RR}; RB:{MTF_att,success,ypc,yaco_pct,tgts_g,rush_fd_att}; often {}
 "def":{covp,runp,manp,sackp,man_rate,sack_rate,tiers}}   # DST ONLY: the unit's OWN profile
 "adv2":{...}}   # 2-SEASON (2024+25) advanced profile, present for ~304 skill players (None=rookie/no history)
#   WR/TE: {g, aDOT, ay_share(0-100), tgt_share(0-100), catch(0-100), ypt, rec_pg, recyd_pg, td_pg, yptouch}
#   RB   : {g, carry_share(0-100), ypc, rush_pg, rushyd_pg, tgt_share(0-100), ypt, rec_pg, recyd_pg, td_pg, yptouch}
#   QB   : {g, patt_pg, ypa, ptd_pg, int_pg, rush_pg, rushyd_pg, rushtd_g}
# WIRE 2-YR ADVANCED INTO FLAGS: when adv2 exists, PREFER its 2-season values for the matching flag
# thresholds (aDOT, target/carry share, YPC, YPT, air-yards share, yards/touch, QB rushing) and CITE the
# 2-yr value + games in the flag detail (e.g. "2yr aDOT 12.7 over 28g, 37% air-yd share"). Single-season
# charting (separation/route_eff/YPRR/explosive/YAC from fus) stays as-is until a 2024 charting pull lands.

 "chart2":{...}}  # ★NEW★ TWO-SEASON (2024+2025) FantasyPoints CHARTING, present for 248 skill players (None=rookie/no-charting).
#   Use chart2['blend'] (games-weighted 2-yr) and CITE it (e.g. "2yr YPRR 3.75, TPRR 0.37 over 27g (FP charting)").
#   WR/TE blend: {g, aDOT, tprr, yprr, ypt, catch, yac_rec, yaco_rec, mtf_rec, fr_pct(1st-read%), deep_pct, contested_pct, ay_share, slot_pct, wide_pct, threat, fp_rr}
#   RB blend   : {g, ypc, mtf_att, yaco_att, ybco_att(yds-before-contact/att), success, stuff, exp_run(explosive-run%), i5_pct(inside-5 carry share), td_rate}
#   QB blend(2024 only): {g, aDOT, deep_pct, cpoe, press_pct, ttt(time-to-throw), scrm(scrambles), oneread_pct, acc_pct}
# ★ WIRE 2-YR CHARTING INTO THE CHARTING FLAGS (this is the 2024 charting the user asked for):
#   - WR/TE separator/route flag: prefer chart2.blend YPRR + TPRR + contested_pct + fr_pct over single-season fusion; CITE 2-yr.
#   - WR/TE deep flag: prefer chart2.blend aDOT + ay_share + deep_pct; CITE 2-yr.   - YAC flag: chart2.blend yac_rec + mtf_rec.
#   - WR/TE alignment: slot_pct/wide_pct tells you slot vs boundary (affects man/zone + nickel reads).
#   - RB explosive flag: chart2.blend exp_run + mtf_att + ybco_att ; goal-line: i5_pct + td_rate ; efficiency: success/ypc.
#   - QB: chart2.blend press_pct (how he handles pressure), ttt, scrm, deep_pct, cpoe (accuracy over expected).
#   Single-season fusion percentiles stay as a fallback when chart2 is absent (rookies).
```
**gamelog.json[key]** — 2025 active games (skill: proj≥8) for EMPIRICAL confirmation:
```
[{"wk":16,"opp":"PIT","home":true,"dome":true,"wind":null,"precip":null,"proj":23.4,"act":22.8,
  "boom":0,"opp_passp":52,"opp_runp":19}, ...]            # boom=1 if act>=position threshold
# DST gamelog entries instead carry: "opp_off_q","opp_qb_q" (the offense they faced)
```
**schedule2026.json[TEAM]** — full season 18 weeks: `[{"wk":1,"opp":"NO","home":true,"dome":true},{"wk":8,"opp":"BYE","home":null,"dome":null},...]`
**defense2026.json[TEAM]** — the defense a skill player FACES (opponent):
```
{"covp":19,"runp":32,"manp":77,"sackp":68,"man_rate":22.7,"sack_rate":6.5,"tiers":{"QB":"TOUGH","RB":"AVG","WR":"TOUGH","TE":"SOFT"}}
```
covp/runp = pass/run defense percentile (higher = TOUGHER). manp = man-coverage rate pctl. sackp =
pass-rush pctl. tiers = per-position points-allowed tier SOFT(good for offense)/AVG/TOUGH.

## Multiplier guidance (keep calibrated to SWING — don't let products explode)
SWING soft/tough ratios: QB 3.2×, RB 1.8×, WR 2.2×, TE 4.1×, DST 5.0×. Cap a fully-favorable
product near that ratio. Suggested per-flag mults:
- Soft position tier (tiers[pos]=='SOFT' or covp/runp ≤30): ×1.30–1.40 ; TOUGH (≥70): ×0.70–0.78
- Pass-funnel (runp≥60 & covp≤45) for pass-catchers/QB: ×1.18 ; Run-funnel (covp≥60 & runp≤45) for RB: ×1.18
- Man-heavy (manp≥68) AND separator/short-aDOT winner: ×1.18 ; Zone (manp≤32) AND route-tech/YAC: ×1.12
- Weak pass-rush (sackp≤30) AND deep/aDOT player: ×1.15 ; Heavy rush (sackp≥75) AND weak O-line (oline_pctl≤35): ×0.85
- Dome AND deep/explosive (aDOT≥12 or explosive_pctl≥70): ×1.08
- Use ONLY flags that apply to THIS player (his actual stats). Don't give a volume slot the deep-ball flag.

## OUTPUT — write build_flags_<POS>.py → boom/flags_<POS>.json, keyed by statmenu key:
```
{"<key>": {
  "name","pos","team","adp",
  "base": <int %>, "hist": <bool>, "n_games":<int>, "boom_games":<int>,
  "skill_flags": [ {"f":"Deep-ball winner","d":"aDOT 14.2 + explosive 92nd pctl","amp":"single-high / weak deep-D / dome / clean pocket"}, ... 3–6 PLAYER-SPECIFIC with REAL numbers ],
  "line": "<one plain-language sentence: the unique combination that unlocks HIS ceiling>",
  "weeks": [ {"wk":1,"opp":"NO","home":true,"dome":true,"p":31,"lab":"SMASH","lit":4,"of":6,
              "flags":["soft WR tier","pass-funnel","man-heavy (sep edge)","dome"]}, ... ALL 18 (BYE -> lab:"BYE",p:null,lit:0,flags:[]) ],
  "empirical": "<from 2025 gamelog: # ceiling games + the conditions they clustered in, with counts>"
}}
```
- `base`: reg_base×100 (int). If reg_base is None (history <4 games): base = posbase[pos]×(0.75+0.5×ceiling_pctl/100), capped [0.06,0.45]; hist=false. (For DST with no ceiling_pctl, seed from its own def percentiles: sackp/covp.)
- `of` = # activatable conditions you defined for this player; `lit` = # met that week.
- `p` = prob(base,[lit mults])×100 (int). BYE: p=null,lab="BYE".
- `empirical`: from gamelog[key] — how many boom games and whether they over-index on home/dome/soft pass (opp_passp≤35)/soft run (opp_runp≤35). For DST use opp_off_q≤35. If low history, say so.

## POSITION FLAG LIBRARIES (starting points — EXHAUST beyond these, player by player)
### QB
- Rushing QB (usage.carry_pg≥5) → designed-run/scramble floor+ceiling (the dominant QB ceiling driver); amp: most scripts, esp. man-heavy (scramble lanes), soft run box, red zone.
- Deep/explosive (fus.explosive_pctl≥70 or strong ceiling_pctl) → big-play passing; amp: weak pass-rush (sackp≤30 = clean pocket), dome, weak deep coverage (covp≤30).
- Protected pocket (fus.oline_pctl≥70 / protection_pctl) → time to throw; suppressor when sackp≥75 AND oline low.
- Pass volume / supporting cast (high proj, matchup_pctl) → ceiling vs pass-funnel + negative script (trailing) + soft pass tier.
- Suppressors: tough pass D (covp≥70, tiers QB TOUGH), heavy rush + weak protection, run-funnel.
### RB
- Explosive/big-play (fus.explosive_pctl≥70, usage.ypc high, sis.MTF_att/yaco_pct) → home-run ceiling; amp: light boxes (runp≤35), soft run tier, pass-funnel (opp sells out vs pass).
- Receiving back (usage.tgt_share≥0.12 / ypt / sis.tgts_g / role) → PPR ceiling + script-proof; amp: pass-funnel, negative script (check-downs), soft-vs-RB-receiving, man (RB-LB mismatch).
- Goal-line/RZ (usage.rush_share/carry_share high, rz_share, sis.rush_fd_att) → TD ceiling; amp: soft run tier near goal, positive script (favored).
- Workhorse volume (usage.carry_pg≥16, carry_share≥0.55) → floor→ceiling vs soft run D.
- O-line/run-eff (fus.oline_pctl, run_eff_pctl) → amp vs soft run D.
- Suppressors: tough run D (runp≥70, tiers RB TOUGH), committee (low carry_share & no receiving), negative script for early-down-only backs.
### WR
- Deep/aDOT (adot.aDOT≥12, sis.airyard_pct high, fus.explosive_pctl) → big-play ceiling; amp: weak pass-rush (clean pocket), weak deep-D (covp≤30), dome, soft WR tier.
- Separator (fus.separation_pctl≥65, adot.TPRR/surplus_TPRR high) → wins vs man; amp: man-heavy (manp≥68), soft WR tier.
- Route-tech / YPRR (fus.route_eff_pctl≥65, sis.YPRR/eff_combined) → wins vs zone; amp: zone (manp≤32).
- YAC (fus.yac_pctl≥70, yaco.YACoe high) → ceiling on short catches; amp: zone, soft tier.
- Volume / target hog (usage.tgt_share≥0.25, tgt_pg, sis.tgt_share_w) → ceiling vs pass-funnel + negative script.
- Red zone (usage.rz_share) → TD ceiling vs soft tier.
- Suppressors: tough WR tier (covp≥70, tiers WR TOUGH), man-heavy if low separation, deep+heavy-rush+weak-OL.
### TE
- Volume (usage.tgt_share≥0.18, tgt_pg, sis.eff_combined) → ceiling vs pass-funnel + soft TE tier.
- Red zone / TD (usage.rz_share, fus.boom_pctl) → TEs are TD-dependent; amp: soft TE tier (tiers TE SOFT), positive script near goal.
- Seam/explosive (fus.explosive_pctl, yac_pctl, adot.aDOT) → big-play; amp: zone (seam), weak rush, dome.
- Coverage-proof / route (fus.route_eff_pctl, coverage_proof_pctl, rec_eff_pctl) → wins vs man (TE-on-LB/S); amp: man-heavy.
- Suppressors: tough TE tier (tiers TE TOUGH), very low target share (pure TD variance), heavy rush.
### DST (use statmenu['dst_xxx']['def'] for the unit + OPP[opp] for the offense faced each week)
- TRENCH MATCHUP — the core DST sack/pressure/turnover driver (the user explicitly wants this): own DEFENSIVE-LINE pass-rush (def.sackp) vs the opponent's OFFENSIVE LINE (OPP[opp].ol_q, OPP[opp].pblock). Strong own rush (def.sackp≥60) AND weak opp OL (OPP[opp].ol_q≤35) = high sack + pressure + strip-sack/INT ceiling — light this STRONGLY (×1.3-1.45). A strong opp OL (ol_q≥70) suppresses it (×0.75). Make own-DL-strength and opp-OL-weakness SEPARATE flags so a unit with both lit scores higher than one with only one.
- (own pass-rush even vs avg OL still matters: def.sackp≥75 → ×1.15 standalone)
- Ball-hawk coverage (def.covp≥65) → INTs, low yards; amp: facing low qb_q / weak offense.
- Stout run D (def.runp≥65) → forces opponent one-dimensional (pass) → more sack/INT chances.
- Matchup (DOMINANT for DST): facing a weak offense (OPP[opp].off_q≤35) and/or low-quality QB (qb_q≤35) → low points allowed + giveaways = the biggest DST ceiling driver. Strong offense (off_q≥70) = suppressor.
- Script: big favorite (own off_q≥65 AND opp off_q≤40) → opp passes when trailing → sacks/INTs.
- Home + dome: minor positive (crowd-noise false starts/sacks).
- Suppressors: facing a top-8 offense (off_q≥75) or elite QB (qb_q≥80).
- DST skill_flags describe the UNIT's strengths (pass rush / coverage / run-stop) with real percentiles; weeks light up mostly on the opponent (off_q/qb_q) + own-unit fit + script.

## RULES (user is strict)
1. PLAYER BY PLAYER — derive each player's flags from HIS stats; no blanket position template.
2. EXHAUST THE STATS — use every relevant field; find the UNIQUE combination per player. "Very basic" = failure.
3. GROUNDED — every skill flag cites a real number from statmenu/OPP.
4. FULL SEASON — all 18 weeks from schedule2026 (handle BYE).
5. Calibrate to SWING; boom_lib caps prob at 0.80.

## VERIFY before finishing (report these)
- Run the script; print: #players, #with hist, avg skill_flags/player, confirm every player has 18 weeks.
- Spot-check 3 NAMED players: print base, skill_flags, line, one SMASH week + one TOUGH week with lit flags;
  confirm flags make football sense AND differ across the 3 (proves player-by-player, not templated).
- Confirm flags_<POS>.json written + valid JSON (re-load it).

## ★ EXTRA SIGNALS (NEW — wire these in this pass)
statmenu[k] now also has (and load `boom/team_env.json` = TENV[team] for OPPONENT lookups per week):
- **'rz'** (WR/TE only, 173 players; None otherwise): {rz_tgt_share (% of targets inside-20), ez_tgt_share (% in end zone), ez_td (2yr end-zone TDs), ez_td_pg, g}.
- **'team_env'** (own team): {pace_pctl (0-100, own offense plays/game 2yr), plays_pg, env_idx (0-100 scoring environment), off_q, win_total}.
- TENV[opp] (from team_env.json) = same dict for the weekly opponent.

WIRE:
- **RED-ZONE / TD flag (WR/TE)**: high rz['rz_tgt_share'] (≥18) or ez_tgt_share (≥6) or ez_td_pg (≥0.35) = TD-equity ceiling (central for TE + boundary WR). CITE 2-yr (e.g. "2yr 17% inside-20 target share, 9% end-zone share, 8 EZ TDs over 33g"). Amp vs soft position tier + favored script.
- **ENV / SHOOTOUT (per week, all pos)**: own team_env.env_idx ≥70 → high-scoring offense (a standing ceiling raiser — note in the boom line). Per week, amplify (×1.08) when own env_idx≥65 AND opp soft pass-D (covp≤35) = shootout setup.
- **PACE (per week)**: own pace_pctl≥65 AND TENV[opp].pace_pctl≥50 → fast game, more plays (×1.08). Both slow (≤35) → ×0.95.
- **SCRIPT (per week)**: d = own win_total − TENV[opp].win_total. Favored (d≥2.5): RB carry/goal-line ×1.10, pass-catchers ~neutral. Underdog (d≤−2.5): WR/QB pass volume ×1.10 (more attempts trailing); early-down-only RB ×0.93.
- **COVERAGE SHELL (deep-WR proxy, per week)**: a deep WR (chart2.blend deep_pct≥18 or aDOT≥12) gets ×1.10 vs man-heavy (manp≥68) defenses — man≈single-high = deep one-on-ones. (True single/two-high rate would need a FP defense export; man_rate is the local proxy — note it.)
Keep the per-week favorable product calibrated to SWING; CITE the new signals in the lit-flag labels / skill_flags.

## ★ DEFENSE COVERAGE SHELL (NEW — REAL single/two-high; replaces the def_man_rate proxy)
Load boom/defense_shell.json = SHELL[TEAM] = {man, c2, c3, c4, c6, single_high (=man%+Cover3% = one deep safety),
two_high (=Cover2%+Cover4%+Cover6% = two deep safeties), single_high_pctl (0-100, higher=more single-high)}.
All 32 defenses present. Per week, look up SHELL[opp] (opp from schedule2026[team][wk].opp):
- **DEEP WR** (chart2.blend deep_pct≥18 OR aDOT≥12 OR strong air-yards/explosive deep profile): vs SINGLE-HIGH defense
  (single_high_pctl≥65) → ×1.12 and CITE the real rate ("single-high shell, opp X% Cover-1/3 → deep one-on-ones");
  vs TWO-HIGH (single_high_pctl≤35) → ×0.90 ("two-high brackets the deep ball"). THIS REPLACES the old man_rate proxy
  in the deep flag — use SHELL, cite the real single-high %.
- **Separator / man-winning WR** (high separation/TPRR/contested): vs high man% (within single-high) → ×1.10 (one-on-one win).
- **Slot/possession WR & seam TE**: vs TWO-HIGH (single_high_pctl≤35) → ×1.06 (soft underneath / middle-of-field-open opens up).
- **Coverage-proof TE on LB/S in man**: vs single-high man-heavy → ×1.08.
Fallback to man_rate only if SHELL[opp] missing (won't happen). Source: FantasyPoints QB Coverage Matchup (2024 charting).

## ★ COVERAGE SPECIALIST (NEW — the single scheme a player beats the league at)
statmenu[k]['cspec'] (107 WR/TE/QB; None otherwise) = {best ("Cover-3"), best_key ("c3"), z, val, lg, ratio, profile{man,c2,c3,c4,c6}}.
Also SHELL['_LEAGUE'] = league-mean usage per coverage {man,c2,c3,c4,c6} (from defense_shell.json).
WIRE (WR/TE/QB):
- SKILL FLAG when cspec present: "Coverage specialist — crushes {best} ({ratio}x league, z={z})". (describes WHY: this is his standout scheme.)
- PER-WEEK activation: let sh=SHELL[opp]; if sh[cspec.best_key] >= SHELL['_LEAGUE'][cspec.best_key] + 3 (opp runs his best coverage notably above average) → ×1.10 (×1.13 if cspec.z>=2.0), lit flag "faces {best}-heavy D (opp X% vs lg Y%) — his best scheme". This is a clean, high-signal matchup boost: a Cover-3 killer vs a Cover-3-heavy defense.
- Only for players with cspec; best_key maps directly to SHELL[opp] man/c2/c3/c4/c6 usage %.
