# 2026 Offensive Personnel Projection — Brain + New-OC Overlay

**Method.** Baseline = **2025 FantasyPoints personnel actuals** (`personnel_2026.json` → `fp_personnel_mix` / `fp_heavy_rate_2025`; "heavy" = non-11 rate). 2026 OC/new-hire status = `coordinator_changes_2026.json` (CBS-sourced, verified). Play-caller reality (OC title vs who actually calls) = `PLAYCALLER_PROFILES_2026.md` / `scheme_2026.json`. Personnel intel = `brain_intel.json` (analyst tweets, quoted with handle+date). **Directions only — no invented 2026 percentages.** Machine-readable version: `personnel_2026_projection.json`.

**League macro** (vault): *"We're going from ~10 teams that felt comfortable in 12/13 personnel to nearly 2/3s of the league chasing it."* The tide is rising league-wide — a "hold" team can still drift heavier with the league.

---

## Summary — biggest projected 2026 personnel shifts

| Team | 2026 OC (new?) | Caller | 2025 heavy% | 2026 dir | One-line why |
|---|---|---|---|---|---|
| **WAS** | David Blough (NEW) | Blough | 30.6 (rk16) | **UP** | Brain: 12P "a lot closer to even vs 11 — the identity of their offense" (Chig + Sinnott) |
| **LAC** | Mike McDaniel (NEW) | McDaniel | 26.5 (rk25) | **UP** | "Favors 12 and 13"; Njoku+Kolar = 3-TE sets; ESPN: 21P because of Ingold |
| **NYG** | Matt Nagy (NEW) | Nagy | 25.2 (rk17) | **UP** | Likely + Theo Johnson = "plenty of 12"; "12 and 13 coming at you"; Ricard bully ball |
| **HOU** | Nick Caley (ret.) | Caley | 13.7 (rk31) | **UP** | "Drum beat on more 12 and 13" — 2025 low was a TE-injury artifact; 2nd-rd TE + Moreau |
| **LV** | Janocko (NEW, title) | **Kubiak (HC)** | 36.2 (rk10) | **UP** | "Will use 12 personnel a lot… might be 22"; Kubiak multi-TE (Bowers joker, Mayer Y) |
| **BAL** | Declan Doyle (NEW) | Doyle | 58.3 (rk1) | **DOWN** | Lost Monken (12P architect), Likely AND FB Ricard → "could mean more 11 personnel" |
| **PIT** | Angelichio (NEW, title) | **McCarthy (HC)** | 46.8 (rk2) | **DOWN** | "McCarthy historically an 11 personnel coach" (80%+ 3-WR in DAL); 13P identity leaves w/ A.Smith |
| **MIA** | Bobby Slowik (NEW) | Slowik | 42.8 (rk4) | **DOWN** | McDaniel's FB-built 21/22 leaves with him (Ingold→LAC); Slowik lands on 12/11 |
| **ATL** | Tommy Rees (NEW) | Rees/Stefanski | 39.8 (rk8) | **UP** | "Expected to run a lot of 12" — Pitts AND Woerner listed co-starters |
| **DET** | Drew Petzing (NEW) | Petzing | 26.7 (rk19) | **UP** | Petzing's ARI was 3rd in 13P last two years; Conklin added behind LaPorta |
| **TEN** | Brian Daboll (NEW) | Daboll | 19.7 (rk28) | **UP** | Paid Bellinger to reunite w/ Daboll; "more 12 than people think" (no 13 depth) |
| **CHI** | Press Taylor (NEW, title) | **Ben Johnson** | 40.2 (rk9) | **UP** | "We will see a lot of 13 personnel this year"; ESPN: more 13 w/ Loveland moved around |
| **SF** | (no OC change) | Shanahan | 41.1 (rk5) | **DOWN** | Juszczyk gone → the 26.3% 21-personnel engine loses its fullback (roster inference) |
| **SEA** | Brian Fleury (NEW) | Fleury | 36.5 (rk7) | **UP** (mild) | "More 21 personnel in 2026"; "more 2 back sets"; Arroyo opens 12/13 |
| **ARI** | Hackett (NEW, title) | **M. LaFleur (HC)** | 45.6 (rk6) | **HOLD** (12↑ 13↓) | LaFleur name-drops Reiman → more 12; Petzing's 13P leaves for DET |

Other movers (medium confidence): **NYJ up** (Sadiq+Mason Taylor 12P), **NO up** (Kellen Moore two-TE + Delp/Fant), **JAX up** (12/13 "to 15th vs 20th"), **CIN up** (12 if Erick All healthy), **PHI up mild** (ESPN 12P note, Stowers doubts), **NE down mild** (lost Julian Hill, 12 plan → 11).

---

# NEW-OC / NEW-PLAY-CALLER TEAMS (21 oc_new per registry)

> Registry nuance (PLAYCALLER_PROFILES_2026.md): for **BUF, KC, LAR, CHI** the OC title changed but the 2025 play-caller stayed — treat those as continuity. For **ARI, CLE, LV, PIT** the OC on record does NOT call plays — a new HC does.

## WAS — Washington Commanders — OC David Blough (NEW, first-time caller) — **UP** — confidence: HIGH
- **2025 baseline (FP):** heavy 30.6% (rk 16) — 11=69.4%, 12=20.2%, 13=4.7%.
- **2026 projection:** heavy **UP**, emphasis **12**. The single most explicit personnel quote in the brain: *"Will use 12 Personnel a lot more — 'a lot closer to even' vs 11 Personnel — they want to use it as the identity of their offense (Chig + Ben Sinnott key in pass game)"* (@dhananizain 6/15). Backed by *"Commanders likely lean more into 12 personnel (Ben Johnson influence)"* (@dhananizain 6/8) and Blough-scheme notes (*"Play action for Jayden… Increased importance / stronger usage of Ben Sinnott"*). Roster fit: traded-in TE Chig Okonkwo (PERSONNEL.md), plus scheme_2026 "more under-center/balanced."
- **Caveat:** first-time caller — intent is concrete, execution unproven.

## LAC — Los Angeles Chargers — OC Mike McDaniel (NEW) — **UP** — confidence: HIGH
- **2025 baseline (FP):** heavy 26.5% (rk 25) — 11=73.5%, 10=6.7%, 12=6.2%, 21=5.3% (Roman-era gadget shape).
- **2026 projection:** heavy **UP**, emphasis **12/13/21**. Brain says: *"McDaniel does favor 12 and 13 personnel… a path to both Gadsden and Njoku playing quite a lot"* (@32beatwriters 5/29); *"The addition of Njoku allows the Chargers to get into pure three-tight-end sets… Kolar, Njoku and Gadsden all on the field together"* (@dhananizain 5/28); ESPN: *"Chargers to deploy 21 personnel bc of Alec Ingold"* (@dhananizain 6/10); *"the heavy-personnel/McDaniel[s] stuff is exclusively good for Ladd… maybe QJ gets a boost"* (@ihartitz 5/15). His 2025 MIA blueprint: 21=18.3%, 22=7.3%.
- **Roster fit:** LAC imported Njoku AND Kolar this offseason (PERSONNEL.md) plus FB Ingold. The clearest multi-source heavy-up case in the league.

## NYG — New York Giants — OC Matt Nagy (NEW, calls plays) — **UP** — confidence: HIGH
- **2025 baseline (FP):** heavy 25.2% (rk 17) — 11=74.8%, 12=23.7%, **13=0.7%**.
- **2026 projection:** heavy **UP**, emphasis **12/13/21**. Brain drumbeat: *"Pairing Likely with Theo Johnson will result in the Giants deploying plenty of 12 personnel packages"*; *"leaning on a lot of two and three-tight-end sets this season — 12 and 13 Personnel coming at you"* (@dhananizain 6/22); slot WR Calvin Austin *"won't be featured much in this offense"* (7/3); and ex-BAL FB **Patrick Ricard signed** — *"Giants want to go bully ball, which is probably their best path given who their WRs are behind Nabers."*
- **Roster fit:** Likely (BAL), Ricard (BAL), Theo Johnson — the brain signal is roster/beat-driven, stronger than any Nagy-tree prior.

## BAL — Baltimore Ravens — OC Declan Doyle (NEW, first-time) — **DOWN** — confidence: HIGH
- **2025 baseline (FP):** heavy **58.3% — #1 in the NFL** — 12=42.9%, 11=41.7%, 21=10.7%.
- **2026 projection:** heavy **DOWN**, emphasis **11**. The league's heaviest offense lost its three pillars: 12P architect Monken (now CLE HC — he ran BAL's 12P at a top-3 rate, @corbin_young21 6/29), TE2 Isaiah Likely (NYG) and FB Patrick Ricard (NYG). Brain: *"Losing both Patrick Ricard and Isaiah Likely in free agency could mean more 11 personnel. It'll probably be dependent on if they feel good about one of Sarratt or La[ne]…"* (@tejfbanalytics 5/21). Doyle arrives from Payton-tree DEN, which was 76.7% 11 in 2025 (inference on landing spot).
- **Caveat:** BAL will still be heavier than league average (Henry, Andrews); the call is direction, not a collapse to average. First-time caller widens error bars (profiles flag Monken→Doyle as a downgrade risk).

## PIT — Pittsburgh Steelers — OC Brian Angelichio (NEW title; **HC Mike McCarthy calls**) — **DOWN** — confidence: HIGH
- **2025 baseline (FP):** heavy **46.8% — #2** — 11=53.2%, 12=29.5%, 13=13.6% (#2 in 13P per @sumersports).
- **2026 projection:** heavy **DOWN**, emphasis **11** (12 resilient, 13 falls hardest). Brain: *"Mike McCarthy historically been an 11 personnel coach. Threw out of 3+ WR sets more than 80% of the time in final two years with DAL. However, expecting decently more 2-TE sets from McCarthy in PIT. With Pat Freiermuth and Darnell Washington…"* (@adamlevitan 6/4). McCarthy himself: *"Year One… you may tilt one way or the other"* — he's running Washington on Freiermuth's routes, so *"could operate in more 12P than originally expected"* (@dhananizain 6/2, 6/10).
- **Net read:** the Arthur-Smith 13P identity leaves; roster keeps 12 meaningful; overall heavy falls from #2.

## LV — Las Vegas Raiders — OC Andrew Janocko (NEW title; **HC Klint Kubiak calls**) — **UP** — confidence: HIGH
- **2025 baseline (FP):** heavy 36.2% (rk 10) — 11=63.8%, 12=31.3%, 13=4.5%.
- **2026 projection:** heavy **UP**, emphasis **12/13/22**. Brain: *"Raiders will use 12 personnel a lot — they are excited about their heavy sets (Raiders version this year might be 22 personnel). Brock Bowers will be the focal point"* (@dhananizain 6/19); *"Kubiak, who relies on multi-tight end sets in 12 or 13 personnel, has his 'joker' TE in Bowers and the traditional 'Y' in Mayer"* (6/20); *"Kubiak's propensity to run heavy personnel could open up a pretty big role for Mayer"* (@ffdataroma 6/21). scheme_2026: "wide-zone, heavy motion + 12-personnel, deep PA bootlegs."
- **Fit:** rookie QB Mendoza supports a conservative, heavy Year 1 (profiles).

## ATL — Atlanta Falcons — OC Tommy Rees (NEW, in HC Stefanski's system) — **UP** — confidence: HIGH
- **2025 baseline (FP):** heavy 39.8% (rk 8) — 11=60.2%, 12=27.5%, 21=9.4%.
- **2026 projection:** heavy **UP**, emphasis **12**. Brain: *"With the introduction of Kevin Stefanski and Tommy Rees, the Falcons are expected to run a lot of 12 personnel"* (@dhananizain 6/15); starting lineup lists *"TE: Kyle Pitts AND Charlie Woerner — 'The Falcons are going to be running a lot of 12-personnel'"* (6/20); *"If they do use a lot of 12 with Woerner… TPRR for London, Pitts, and Bijan is going to be very high"* (7/1). Profiles: Stefanski = #1 under-center, wide-zone + heavy PA, TE-friendly (Pitts headline beneficiary).

## DET — Detroit Lions — OC Drew Petzing (NEW) — **UP** — confidence: HIGH
- **2025 baseline (FP):** heavy 26.7% (rk 19) — 11=73.3%, 12=16.9%, 20=3.8%, 13=2.4%.
- **2026 projection:** heavy **UP**, emphasis **12/13**. The coordinator's own personnel history is the evidence: *"with Drew Petzing, the Cardinals were 3rd in 13 personnel usage over the last two seasons — huge drop off to the 4th team"* (@joshnorris 6/4, the LaPorta upside case). Profiles: "legit heavy under-center + play-action." Roster: added TE Tyler Conklin.
- **Caveat:** watch whether Ben-Johnson-era explosiveness survives Petzing's more conservative ARI tendencies (profiles).

## TEN — Tennessee Titans — OC Brian Daboll (NEW) — **UP** — confidence: HIGH
- **2025 baseline (FP):** heavy 19.7% (rk 28) — 11=80.3%, 12=15.5%.
- **2026 projection:** heavy **UP**, emphasis **12** (explicitly NOT 13). Brain, three dates: *"The Titans paid FA TE Daniel Bellinger handsomely to reunite with Daboll… The Titans lack the depth to go 13p with any regularity"* (6/6); *"Tennessee paid Bellinger real money… he's going to play a big part in this operation"* (6/8); *"More speculation that the Titans will use 12 Personnel more often than people think"* (6/9). Also: Bellinger "siphons routes like he did to Theo Johnson last year" (Helm note). Daboll's 2025 NYG ran 12 at 23.7% (FP) — consistent moderate-12 profile.

## SEA — Seattle Seahawks — OC Brian Fleury (NEW, first-time; Kubiak → LV) — **UP (mild)** — confidence: HIGH
- **2025 baseline (FP):** heavy 36.5% (rk 7) — 11=63.5%, 12=23.7%, 21=6.9%.
- **2026 projection:** heavy **UP mildly**, emphasis **21/12**. Brain: *"More 21 personnel for Seahawks in 2026 — could be an interesting schematic tweak"* (@dhananizain 7/2); *"Focus even more on outside zone. More 2 back sets & slip motion. Potentially more usage of the TEs (Fleury was a TE coach)"* (6/13); *"Elijah Arroyo helps open up 12 & 13 personnel"*; heavy sets expected *"at Kupp's expense"* (@rotostreetwolf 6/12). Fleury arrives from SF — the league's biggest 21-personnel offense.
- **Caveat:** the caller is unproven (JSN downgrade-risk flag in profiles) — but the personnel direction itself is multi-sourced.

## ARI — Arizona Cardinals — OC Nathaniel Hackett (NEW title; **HC Mike LaFleur calls**) — **HOLD** (12↑ / 13↓) — confidence: HIGH
- **2025 baseline (FP):** heavy 45.6% (rk 6) — 11=54.4%, 12=33.0%, 13=11.8%.
- **2026 projection:** heavy **HOLD** at elite level; mix shifts **13 → 12**. Brain: *"Mike LaFleur keeps name dropping Tip Reiman, signaling more 12 personnel in 2026"* (@dhananizain 6/16); the projected starting offense is literally *listed in 12 personnel* (Brissett–Love–MHJ/Wilson–McBride+Reiman, 6/19). Meanwhile the 13P architecture belonged to Petzing, who left for DET (@joshnorris 6/4). Do NOT model this as Hackett's offense (profiles).

## MIA — Miami Dolphins — OC Bobby Slowik (NEW, under new HC Hafley) — **DOWN** — confidence: MEDIUM
- **2025 baseline (FP):** heavy 42.8% (rk 4) — 11=57.2%, **21=18.3%, 22=7.3%** (McDaniel's FB-built shape), 12=13.1%.
- **2026 projection:** heavy **DOWN**, emphasis shifts to **11/12**. The 21/22 structure leaves with McDaniel (now LAC OC) and FB Ingold (ESPN cites him as the reason **LAC** will run 21). Slowik's own last stop is the landing spot: *"The 2024 Houston Texans ran 12 personnel at the 3rd highest rate in the NFL at 31.5%"* (@coachspeakindex, via PERSONNEL.md) and he is ideologically run-committed (@RyanJ_Heath 6/24). WR room gutted (44% of targets vacated) — the roster can't support 3-WR volume anyway.
- **FLAG:** no MIA-specific 2026 personnel quote — 21/22-down is coach/roster inference; the 12 landing spot is Slowik's documented history.

## CLE — Cleveland Browns — OC Travis Switzer (NEW title; **HC Todd Monken calls**) — **HOLD** — confidence: MEDIUM
- **2025 baseline (FP):** heavy 47.9% (rk 3) — 11=52.1%, 12=41.8%.
- **2026 projection:** **HOLD** at a high level, slight 11 drift. Monken's own record keeps 12 alive: *"As the Ravens' OC, Monken had the Ravens using 12-Personnel at the third-highest rate (35.9%)"* (@corbin_young21 6/29). But Njoku left for LAC (9% of targets) and Monken's Air-Coryell adds vertical/WR flavor — Fannin becomes the every-down TE. Two heavy-12 regimes hand off; level stays high, ceiling comes down a touch.

## NYJ — New York Jets — OC Frank Reich (NEW) — **UP** — confidence: MEDIUM
- **2025 baseline (FP):** heavy 21.3% (rk 24) — 11=78.7%, 12=15.0%.
- **2026 projection:** heavy **UP**, emphasis **12**. Brain: *"With Kenyon Sadiq and Mason Taylor, expecting a healthy amount of 2 WR sets"* (Omar Cooper "an 11 personnel starter" only) (@dhananizain 6/6). Reich's scheme leans RB/TE motion + quick game for Geno (scheme_2026). Two young TEs are the personnel engine; 40% of targets vacated makes the shift easy to implement.

## PHI — Philadelphia Eagles — OC Sean Mannion (NEW, first-time) — **UP (mild)** — confidence: MEDIUM
- **2025 baseline (FP):** heavy 23.4% (rk 20) — 11=76.6%, 12=19.5%.
- **2026 projection:** heavy **UP mildly**, emphasis **12**. ESPN (via brain): *"Eagles to do more 12 personnel with Eli Stowers (seam stretcher) and Dallas Goedert"* (@dhananizain 6/10); A.J. Brown's exit (26% of targets) weakens the 3-WR case. **Counterweight in the same corpus:** Stowers *"unlikely to play much in 2026… needs a lot of work as a blocker"*, "Mundt is the TE2 over Stowers" — so cap the bump.
- **Caveat:** first-time caller; signal and counter-signal from the same corpus.

## DEN — Denver Broncos — OC Davis Webb (NEW caller; Payton handed it off) — **HOLD** — confidence: LOW
- **2025 baseline (FP):** heavy 23.3% (rk 26) — 11=76.7%, 12=11.7%.
- **2026 projection:** **HOLD** (mild 12 tilt possible). No grouping-specific brain signal — only soft chatter: *"TEs should be more involved in the offense this year"* + faster pace (@dhananizain 6/7), Engram the clear TE1 and *"more usage YoY"* (6/10-11), more deep play-action (6/19). Webb's spread/Air-Raid roots point the other way (scheme_2026).
- **FLAG: projection rests on the coordinator hire + soft TE chatter only — no personnel-grouping intel.**

## TB — Tampa Bay Buccaneers — OC Zac Robinson (NEW, McVay branch) — **HOLD** — confidence: MEDIUM
- **2025 baseline (FP):** heavy 14.9% (rk 30) — 11=85.1%, 12=9.3%.
- **2026 projection:** **HOLD** 11-dominant (shave the forced 12). Brain: *"Went 12 personnel heavy in 2025 due to necessity/roster — would not expect the same in 2026 due to better WR depth"* (@dhananizain 6/22) — note the FP season-long baseline shows TB was only 14.9% heavy, so read that as "the injury-stretch 12 goes away." Robinson's own quote puts Egbuka at the Z (@benjaminsolak) — a 3-WR identity with Godwin back.

## BUF — Buffalo Bills — OC Pete Carmichael Jr. (NEW **title only** — Joe Brady still calls) — **HOLD** — confidence: MEDIUM
- **2025 baseline (FP):** heavy 19.6% (rk 21) — 11=80.4%, 12=9.1%.
- **2026 projection:** **HOLD.** Brain: *"Joe Brady will still call plays and have final say… I'm expecting very little changes in the Bills offense"* (@dhananizain 6/5). Carmichael's fingerprint is James Cook receiving usage ("think Alvin Kamara"), not groupings. 2026 ≈ 2025.

## KC — Kansas City Chiefs — OC Eric Bieniemy (NEW **title only** — Andy Reid calls) — **HOLD** — confidence: MEDIUM
- **2025 baseline (FP):** heavy 35.8% (rk 12) — 11=64.2%, 12=28.8%.
- **2026 projection:** **HOLD.** Reid continuity (profiles: "support/reunion hire"). Brain has usage chatter only (*"bieniemy will make the KC O more RB centric"* @sigmundbloom) and *"largely the same personnel as last season"* (@ihartitz). No grouping signal.

## LAR — Los Angeles Rams — OC Nathan Scheelhaase (NEW **title only** — McVay calls) — **HOLD** — confidence: MEDIUM
- **2025 baseline (FP):** heavy 26.9% (rk 18) — 11=73.1%, **13=19.5%** (12=7.3%) — the league's 13-personnel outlier (@sumersports' cut has them #1 at 30.5%).
- **2026 projection:** **HOLD** the 13-led identity ("basically just the Rams and Bears" have the bodies for 13 — @RyanJ_Heath 5/21; the rookie TE "makes their 12 feel like 11"). One regression caveat: the late-2025 heavy lean was *"somewhat out of necessity bc Puka was hobbled"* (@dhananizain 5/26) — a healthy WR room drifts a few points back toward 11.

## CHI — Chicago Bears — OC Press Taylor (NEW **title only** — Ben Johnson calls) — **UP** — confidence: HIGH
- **2025 baseline (FP):** heavy 40.2% (rk 9) — 11=59.8%, 12=30.5% (6th-highest), 13=7.4%.
- **2026 projection:** heavy **UP**, emphasis **13** (then 12). Brain: *"'We will see a lot of 13 personnel this year' from the Bears"* (the open question is the lone-WR role / Odunze load management); ESPN: *"Bears to play more 13 personnel with Loveland lined up out wide, slot, or in-line"* (6/10); profiles: Johnson's 13-personnel multi-TE identity (Loveland + Kmet). Not a scheme change — a year-2 deepening.

---

# RETURNING-OC TEAMS (2026 ≈ 2025 baseline unless the brain says otherwise)

## HOU — Houston Texans — OC Nick Caley (returning) — **UP** — confidence: HIGH ⚠️ biggest returning-OC mover
- **2025 baseline (FP):** heavy **13.7% (rk 31)** — 11=86.3%, 12=8.6%.
- **2026 projection:** heavy **UP**, emphasis **12** (some 13). The 2025 number was an artifact: *"The Texans could not do that in 2025 because they were thin at TE after losing Brevin Jordan in the preseason"*; now a *"drum beat on more 12 and 13 personnel from Houston across various platforms with the TE room healthier (and a draft pick)"* (@dhananizain 6/9, 6/12, 6/26 — "Caley wants TEs to be on the field," more balanced run/pass); *"Texans — just ~74 passes last season in 2WR looks or less, spent a 2nd round pick on a TE and signed Foster Moreau"* (@joshnorris 6/5). The 2024 Texans (under Slowik) ran 12P at 31.5% — the org has been there before.

## JAX — Jacksonville Jaguars — Liam Coen (HC, returning caller) — **UP (moderate)** — confidence: MEDIUM
- **2025 baseline (FP):** heavy 19.2% (rk 29) — 11=80.8%, 12=15.2%.
- **2026 projection:** heavy **UP moderately**, emphasis **12/13**. Brain: *"Up 12/13 personnel to 15th in lg vs 20th in 2025 — still primarily 11"* (@dhananizain 6/14); 13P single-receiver looks floated as the Travis Hunter integration path (@mattharmon_byb 5/21). Counterweight: *"the Jaguars are not about to sideline their deep group of wide receivers — Coen loves airing the ball out."* Rise is real but capped.

## NO — New Orleans Saints — Kellen Moore (HC, returning caller) — **UP** — confidence: MEDIUM
- **2025 baseline (FP):** heavy 20.8% — 11=79.2%, 12=15.8%.
- **2026 projection:** heavy **UP**, emphasis **12**. Canon: *"HC Kellen Moore calls plays in a heavy two-TE scheme"* (personnel_2026.json). Brain: *"Oscar Delp is back — a guy who can help unlock more 12 personnel for the Saints"* (@dhananizain 6/16); added Noah Fant. Roster is finally catching up to the scheme.

## CIN — Cincinnati Bengals — returning staff — **UP (mild)** — confidence: MEDIUM
- **2025 baseline (FP):** heavy 31.2% (rk 14) — 11=68.8%, 12=27.0%.
- **2026 projection:** heavy **UP mildly**, emphasis **12** — health-gated: *"utilizing more 12 personnel: Erick All is viewed as critical to unlocking this given his versatility (if he can remain healthy)"* (@dhananizain 6/29). Motivation is documented: *"Bengals heavy personnel dropback game is bad — they draw base defense less than anyone in it."*

## NE — New England Patriots — registry gap (profiles: Josh McDaniels — **verify live**) — **DOWN (mild)** — confidence: MEDIUM
- **2025 baseline (FP):** heavy 37.1% (rk 11) — 11=62.9%, 12=20.1%, 21=12.6%.
- **2026 projection:** heavy **DOWN mildly**, emphasis **11**. Brain: *"Will do more 11 personnel bc they lost Julian Hill — plan was 12…"* (@dhananizain 6/16); *"They wanted to do more 12 personnel this season and losing Julian Hill hurt those plans"* (articles keep suggesting a veteran TE add — that signing would flip this back to hold).
- **FLAG:** NE's 2026 play-caller was NOT captured by the CBS registry; profiles repeatedly praise the Josh McDaniels + Drake Maye setup but say verify before citing.

## SF — San Francisco 49ers — Kyle Shanahan (no OC change; new DC only) — **DOWN** — confidence: MEDIUM
- **2025 baseline (FP):** heavy 41.1% (rk 5) — 11=58.9%, **21=26.3%**, 12=9.7%.
- **2026 projection:** heavy **DOWN**, emphasis shifts to **11/12**. **FB Kyle Juszczyk is gone** (modeled departures, PERSONNEL.md) — he was the fulcrum of the league's biggest 21-personnel share. WR adds (Christian Kirk + rookie WRs) point 11-ward.
- **FLAG: roster inference only — no brain personnel quote for SF.** Shanahan has always carried a FB; if they add one, revert to hold.

## DAL — Dallas Cowboys — Brian Schottenheimer yr 2 (no OC change) — **HOLD** — confidence: MEDIUM
- **2025 baseline (FP):** heavy 22.1% (rk 23) — 11=77.9%, 12=13.9%.
- **2026 projection:** **HOLD.** Brain affirms the identity: *"The Cowboys ranked fifth in their usage of 11-Personnel… sixth-most efficient in EPA per pass out of 11"* (@corbin_young21). No change signal.

## GB — Green Bay Packers — Matt LaFleur (no OC change) — **HOLD** — confidence: MEDIUM
- **2025 baseline (FP):** heavy 30.4% (rk 15) — 11=69.6%, 12=27.1%. Continuity; no personnel-grouping brain signal. Already a top-10 12-personnel team.

## IND — Indianapolis Colts — Shane Steichen (returning) — **HOLD** — confidence: MEDIUM
- **2025 baseline (FP):** heavy 29.3% (rk 13) — 11=70.7%, 12=23.4%, 13=5.5% (#4 in 13P per @sumersports). Tyler Warren year 2 keeps 12 central; no 2026 change signal.

## MIN — Minnesota Vikings — Kevin O'Connell (returning) — **HOLD** — confidence: MEDIUM
- **2025 baseline (FP):** heavy 21.3% (rk 22) — 11=78.7%, 12=13.7%. No personnel signal; Kyler Murray changes the QB, not the groupings, absent other intel.

## CAR — Carolina Panthers — registry: no change (scheme file: Brad Idzik new caller) — **HOLD** — confidence: LOW
- **2025 baseline (FP):** heavy 20.9% (rk 27) — 11=79.1%, 12=14.3%.
- **2026 projection:** **HOLD.** Same Canales wide-zone family either way (more motion, short aDOT, RB screens per scheme_2026).
- **FLAG:** source conflict — `coordinator_changes_2026.json` (the anchor) has no CAR entry, but `scheme_2026.json`/profiles list Idzik as a new 2026 caller. No personnel-grouping intel; hire-only inference.

---

## Reliability appendix

**Strong brain personnel signal (direct 2026 grouping quotes):** WAS, LAC, NYG, LV, ATL, TEN, HOU, CHI, PIT, BAL, ARI, SEA, DET (coordinator's own 13P record), TB, NE, NYJ, JAX, CIN, NO, PHI (with counter-signal), CLE (Monken 12P record), DAL (identity affirmation), LAR (identity + regression caveat).

**Inferred from hire/roster only (no team-specific personnel quote) — treat as low/medium:** DEN (hire + soft TE chatter), CAR (hire only, registry conflict), SF (roster inference — Juszczyk), MIA (coach-departure/roster inference + Slowik's HOU 12P history), BUF/KC/GB/MIN/IND (continuity holds, no signal needed).

**Known data tensions (flagged, FP is the anchor):** TB "went 12-heavy in 2025" vs FP 14.9% heavy (read: injury stretches); @sumersports 13P leaderboard (route/snap cut) vs FP participation mix (LAR 30.5% vs 19.5%, PIT 14.2% vs 13.6%); BAL FB spelled "Patrick Richard" in one tweet = Patrick Ricard.
