# FUNNEL 2026 AUDIT — do the 2025-vintage defensive funnels survive the 2026 rosters?

_Audited 2026-07-05. Question: for each of the 32 defenses, does the funnel graded from 2025 data
(boom/defensive_profile.json FPAA + nflpro_2025.json NGS alignment charting) still describe the
2026 unit after free agency, trades, the draft, and coordinator changes?_

**Sources, in authority order (per ground_truth_registry):**
1. Repo verified layers: `boom/defensive_profile.json` (2025 FPAA funnels + leans), `nflpro_2025.json`
   (NGS per-alignment soft percentiles, attacker view: HIGH = softer), `defense.json` (2026 engine:
   snap-weighted SIS reweighted onto 2026 rosters; `*_pctl_2025` vs `*_pctl` = the computed 2025→2026
   unit shift, HIGH = stronger unit), the curated defensive MOVES registry in `reweight_defense_2026.py`
   (source-URL'd), `web_teams.json`, `coordinator_changes_2026.json` / `coordinator_scheme_2026.json`,
   `COACHING_CHANGES_2026.md` (registered ground truth), `DEFENSE_CURRENCY_AUDIT.md`.
2. Web search (July 2026), used only to confirm/deny specific 2026 moves and rookie roles the layers
   disagreed on or were thin on. Every web-confirmed fact below says so. Anything not confirmable is
   marked **[unconfirmed]**.

**Reading conventions:** FPAA + = soft lane (target it). NGS `soft_pctl` high = soft. Engine pctl
high = strong unit (so cov 92→20 = coverage collapsed). Verdicts: **HOLDS** (2025 funnel still
valid) / **TIGHTENS** (soft lane closing) / **OPENS** (lane widening or new lane) / **SHIFTS**
(lane moves — flip of lean or lane relocation).

---

## 1. Summary table — all 32

| Team | 2025 funnel (2025 evidence) | 2026 verdict | Conf | One-line reason |
|---|---|---|---|---|
| ARI | RUN + TE funnel | **SHIFTS → PASS** | med | Run D firms (8→36 pctl, Wingard) while coverage stays bottom-3 (11) and rush loses Campbell/Tomlinson |
| ATL | TE fortress (+ RUN lean) | HOLDS | high | Bates/Watts shell intact = TE fortress; rush still 14th pctl → RB lean emerges; Elliss loss the only crack |
| BAL | WR1 funnel | **TIGHTENS** | high | Awuzie CB1 + Minter ~81%-zone two-high + Hendrickson/Campbell (rush 5→55) close the WR1 lane |
| BUF | RUN funnel; WR/TE fortress | HOLDS | high | Run D worse (33→23), coverage reloaded (CJGJ/Stone/Alford) — RB lane stays THE lane; slot a hair softer post-Taron |
| CAR | RUN + WR1 funnel | HOLDS | med-high | Run D still bottom (2→8) despite Phillips/Lloyd; WR1-funnel flag was already contradicted by Jackson/Horn shadow data |
| CHI | PASS + OUTSIDE funnel | **SHIFTS → RUN** | high | Edmunds→NYG + Byard→NE crater run D (95→27); Bush/Bryant/Thieneman lift coverage — flips to RBs |
| CIN | RUN + TE funnel; WR fortress | **SHIFTS → PASS** | high | Coverage to dead last (11→2, CTB out) while D.Lawrence firms the run front (52→64); TE lane stays open |
| CLE | WR fortress | **OPENS → PASS funnel** | high | Garrett→LAR + Newsome→JAX gut coverage (92→20); run D 92nd — fortress dissolves into a pass funnel |
| DAL | PASS + WR1 funnel (sieve) | **TIGHTENS** | med | Downs #11 + Quinnen (deadline) + Gary + Durant/Thompson; Bland EXTENDED (not lost) — sieve → merely soft |
| DEN | SLOT funnel | HOLDS | med-high | Zero secondary moves; McMillian tendered + in extension talks — slot remains the only crease vs Surtain boundary |
| DET | PASS + SLOT funnel | **TIGHTENS** | high | Arnold (liability) released, Ya-Sin kept, McCreary added, Joseph/Branch healthy — cov 48→86 |
| GB | (none) | HOLDS | med | No 2025 funnel to invalidate; Gannon low-blitz front-four; Gary out / Hargrave-St-Juste in; mild RB lean (48→39) |
| HOU | WR fortress | HOLDS | high | No material defensive changes; every unit 70th+ pctl — stay away |
| IND | PASS + TE funnel | **TIGHTENS** | med-high | Full season of Sauce Gardner (engine doesn't credit) + CTB tighten the boundary; slot/TE stay the entries |
| JAX | PASS + WR1 funnel | **SHIFTS → RUN** | med | 2025 pass-funnel grade contradicted by NGS fortress data anyway; Lloyd/Wingard exits soften run D (70→42), cov 89th |
| KC | (none, balanced) | **OPENS (mild)** | med | McDuffie/Watson/Cook secondary gutted; Delane #6 + Kohou quality but rookie variance = pass lane softer |
| LAC | WR fortress | HOLDS | med-high | Fortress personnel intact (Still/Jackson/James); run D still 30th pctl — RUN-funnel lean is the play |
| LAR | WR1 funnel | **TIGHTENS** | high | McDuffie ($124M) + Watson + Sneed rebuild the CB room; Garrett lifts rush 58→86 — WR1 lane closes |
| LV | SLOT funnel | **SHIFTS slot→boundary** | high | Taron Johnson trade closes the slot; total coverage still bottom-5 (17) — soft lane relocates outside/deep |
| MIA | TE funnel | **OPENS → sieve** | high | Kohou (slot)→KC, Minkah→NYJ, Chubb→BUF; rush dead last (2) — TE lane holds AND everything else softens |
| MIN | WR fortress | HOLDS | high | Flores continuity, Pierre added, rush 95th — fortress |
| NE | PASS funnel (weak 2025 signal) | **TIGHTENS** | med | Byard + Dre'Mont Jones onto a 95th-pctl coverage — the marginal pass lane closes; near-fortress |
| NO | (none) | **OPENS → sieve** | high | Alontae Taylor→TEN (engine still credits him) + Demario Davis→NYJ; run D 5th pctl — RB smash + soft coverage |
| NYG | RUN funnel | **SHIFTS → PASS** | med-high | Dexter Lawrence→CIN; Reese #5 + Edmunds hold run D; coverage still 30th (Flott out; registry's Oweh/Cross "adds" are FALSE — both signed WAS) |
| NYJ | OUTSIDE funnel | **OPENS** | high | Run D →98th (Onyemata/Sweat/Davis/Belton) + boundary still Wright/Thomas/rookie — forced-pass profile widens the WR lane; Minkah only trims the deep middle |
| PHI | RUN funnel; WR/TE fortress | **TIGHTENS** | med-high | Run D firms (39→55), Woolen/Epps deepen the fortress, Greenard offsets Phillips — RB lane narrows |
| PIT | PASS + TE funnel | **TIGHTENS** | med | Graham two-high + Dean/Ramsey secondary + 89th-pctl rush shrink the pass/TE lanes; Dugger out is the caveat |
| SEA | TE funnel | **SHIFTS → RUN lean** | med | Woolen→PHI (engine stale: cov 64 overstated) + Bryant→CHI + Mafe→CIN; TE lane persists, boundary softens, profile drifts run-funnel |
| SF | (none; 2026 PASS lean) | **SHIFTS → PASS/slot** | med-high | Warner/Bosa (+Greenlaw, +Odighizuwa trade) firm run D (45→83); coverage mediocre with 94th-pctl-soft slot; Morris adds man |
| TB | (none) | **OPENS → sieve** | high | Lavonte David RETIRED + Dean→PIT + Hall→HOU: cov 36→5, run 86→17 — both lanes open |
| TEN | WR1 funnel | **SHIFTS WR1→general PASS** | med | Alontae Taylor ($58M, missing from engine) + Flott close the WR1 lane, but run D →95th + Bradley Cover-3 funnel volume to pass |
| WAS | (none; sieve) | **TIGHTENS (mild)** | med | Oweh 4yr/$100M + Nick Cross + Styles #7 (registry had Oweh/Cross at NYG — corrected) — still soft everywhere, just less historic |

**Counts: SHIFTS 9 · TIGHTENS 9 · OPENS 6 · HOLDS 8.**

---

## 2. SHIFTS — the lane moved (act on these first)

### CHI — PASS/OUTSIDE funnel → RUN funnel (high confidence)
- **2025:** FPAA wr1 +2.4 / wr2 +2.3 / slot −1.8 = boundary-soft pass funnel; NGS mostly disagrees on softness (wide 16th) but agrees run was stout (rush soft_pctl 65 only mid). FPAA run-side: rb −1.6 (tough).
- **2026 changes (verified):** LB Tremaine Edmunds → NYG (Sun-Times, 3yr/$36M) and S Kevin Byard → NE (NFL.com, 1yr/$9M — the NFL INT leader). Backfills: Devin Bush (CHI, cov PS 18.6) + S Coby Bryant (from SEA). Drafted S Dillon Thieneman #25 overall (Oregon — web-confirmed pick).
- **Engine:** run_def 95.3→26.6 (a ~69-pctl collapse, biggest in the league); cov 51.6→67.2.
- **Verdict: SHIFTS to RUN funnel.** Two verified second-level losses take the run D from elite to bad while the coverage adds/rookies lift the pass side. Target RBs vs CHI, stop auto-targeting boundary WRs.

### CIN — RUN+TE funnel → PASS funnel, TE lane persists (high confidence)
- **2025:** FPAA rb +6.7, te +8.3 (league-worst TE lane), wr −6.3 fortress. NGS partially disagrees on the WR fortress (short 100, slot 90, PA 90 all soft) but agrees on TE (tight 97) and run (rush 87).
- **2026 changes (verified):** Trey Hendrickson → BAL (4yr/$112M). Dexter Lawrence traded IN from NYG for the #10 pick (+1yr/$28M ext — NFL.com/bengals.com). Kyle Dugger signed (web-confirmed, ex-PIT, 1yr — box/big-nickel S). CB Cam Taylor-Britt → IND (colts.com). Boye Mafe + Jonathan Allen in. Logan Wilson was already traded (CIN→DAL 2025 deadline, later waived) — the LB coverage hole stays.
- **Engine:** cov 10.9→1.6 (dead last), rush 42.2→23.4, run 51.6→64.1.
- **Verdict: SHIFTS to PASS funnel.** The run front firms behind Lawrence while the secondary got worse — the WR-fortress flag is dead. TE funnel HOLDS (no LB coverage fix). Target WRs and TEs; downgrade the auto-RB read.

### LV — SLOT funnel closes; soft lane relocates to boundary/deep (high confidence)
- **2025:** FPAA slot +4.0 (league-high) vs wr1 −1.2; NGS agrees (slot soft_pctl 84, and wide 84 too).
- **2026 changes (verified):** Taron Johnson acquired via trade from BUF (raiders.com/NFL.com pick-swap) — a top-tier nickel who takes the slot lane away by himself. Front-seven adds Kwity Paye, Quay Walker, Nakobe Dean. Rookie CBs Treydan Stukes R2 / Jermod McCoy R4 [engine-registered, roles unconfirmed].
- **Engine:** cov 32.8→17.2 overall (still bad), run 98.4→85.9, rush 20.3→10.9. `lean_2026 = PASS`.
- **Verdict: SHIFTS.** Slot-funnel dead — do NOT carry LV as a slot-WR smash. The pass lane survives but moves to boundary WRs and TEs (weak overall coverage + no pass rush + elite-ish run D).

### NYG — RUN funnel → PASS funnel (med-high confidence)
- **2025:** FPAA rb +4.9 (soft run), slot −0.5; NGS rush soft_pctl 100 (softest run D charting in the league) — sources agree.
- **2026 changes (verified):** Dexter Lawrence traded to CIN for the #10 pick (giants.com). LB Arvell Reese drafted #5 overall (Ohio State, "position-less" range — giants.com) + Tremaine Edmunds signed. CB Cor'Dale Flott → TEN. **Registry correction:** `reweight_defense_2026.py` lists Odafe Oweh and Nick Cross to NYG — both actually signed with WASHINGTON (NFL.com: Oweh 4yr/$100M; Rapoport: Cross 2yr/$14M). NYG's engine rush/run numbers carry small false credits.
- **Engine:** run 92.2→67.2, cov 23.4→29.7 (still bottom-third), rush 76.6 (Burns/Carter elite even minus the false Oweh credit). New DC Dennard Wilson (attacking, DB-coach).
- **Verdict: SHIFTS to PASS funnel.** Reese/Edmunds patch the run lane, the CB room is still the entry point, and the pass rush forces drop-back volatility — boom/bust WR target, not an RB lane anymore.

### TEN — WR1 funnel → general PASS funnel (med confidence)
- **2025:** FPAA wr1 +3.3 with everything mediocre; NGS says everything was soft (wide 94, deep 94, tight 90, slot 87) — NGS graded TEN a full sieve, broader than the FPAA WR1 flag.
- **2026 changes (verified):** CB Alontae Taylor signed 3yr/$58M ($42M gtd — tennesseetitans.com/Spotrac) — **missing from the engine entirely** (it still credits him to NO). CB Cor'Dale Flott in (titans site). Front: John Franklin-Myers + Jermaine Johnson II + Keldric Faulk #31 overall (Auburn, web-confirmed) next to Simmons. New DC Gus Bradley (heavy Cover-3 zone, low man).
- **Engine:** cov 4.7→42.2 (understated — add Taylor), run 64.1→95.3, rush 67.2→57.8.
- **Verdict: SHIFTS.** The specific WR1 lane narrows (Taylor/Flott are real boundary upgrades), but the structure — elite run D + zone-heavy Bradley + still-average secondary — funnels opponent volume to the pass. Treat as a volume pass funnel, not an efficiency WR1 funnel.

### SEA — TE funnel → RUN-lean with a softening boundary (med confidence)
- **2025:** FPAA te +2.7 the only soft lane; NGS agrees directionally (tight 65 softest of its pass splits; wide 3 = boundary fortress; rush soft_pctl 0 = elite run D... note NGS run and FPAA rb −2.9 agree run was elite).
- **2026 changes (verified):** CB Riq Woolen → PHI (NFL.com 1yr/$15M) — **engine stale: still counts Woolen's cov PS 26.8 for SEA** (listed "assumed-staying" in DEFENSE_CURRENCY_AUDIT). S/nickel Coby Bryant → CHI. EDGE Boye Mafe → CIN. Adds: Dante Fowler, Noah Igbinoghene [web-only, depth]. Josh Jobe re-signed [web].
- **Engine:** cov 85.9→64.1 (real number is lower with Woolen removed), rush 39.1→73.4, run 29.7→48.4. `lean_2026 = RUN`.
- **Verdict: SHIFTS.** TE lane persists (Ernest Jones/Drake Thomas LB coverage unchanged), but the 2025 "boundary fortress" claim is no longer safe — two starting corners left. Softer overall coverage + still-good run D = drift toward balanced/run-funnel with a cracked boundary.

### SF — balanced → PASS/slot funnel (med-high confidence)
- **2025:** No funnel flagged (FPAA all mild); NGS: slot soft_pctl 94 and deep 90 = the slot/deep charting was already soft; tight 0 (TEs erased).
- **2026 changes (verified):** Osa Odighizuwa acquired by trade from DAL for a 3rd (ESPN/49ers.com) — **not in the engine's move map** (upside unpriced). Fred Warner + Nick Bosa return from injury (engine recovery entries, 2024-rate × 0.65). Dre Greenlaw back [web-only, unconfirmed by engine]. New DC Raheem Morris: notably MORE man + 5-plus-rusher aggression vs Saleh's zone (coordinator layer).
- **Engine:** run 45.3→82.8, rush 29.7→48.4, cov 57.8→54.7 (mediocre). `lean_2026 = PASS`.
- **Verdict: SHIFTS to PASS funnel, slot the entry.** Front-seven health + Odighizuwa wall off the run; the secondary is the untouched, mediocre unit and its 2025 slot charting was 94th-pctl soft. Slot WRs vs SF move up. Morris' man-rate bump adds WR-vs-CB variance.

### ARI — RUN+TE funnel → PASS funnel (med confidence)
- **2025:** FPAA rb +3.6 / te +3.3, wr −2.5. NGS **disagrees on the pass fortress**: wide 87, short 90, deep 84, tight 87 all soft (charting saw a bad pass D; engine cov pctl 1.6 in 2025 sides with NGS).
- **2026 changes (verified):** Losses: Calais Campbell → BAL (ravens.com), Dalvin Tomlinson + Jalen Thompson (S → DAL) out. Add: S Andrew Wingard (JAX→ARI, registry). Rookie DT Kaleb Proctor R4 [engine]. No DC change (Rallis stays under new HC LaFleur).
- **Engine:** run 7.8→35.9, rush 92.2→79.7, cov 1.6→10.9 (still bottom-3). `lean_2026 = PASS` (engine SHIFT flag).
- **Verdict: SHIFTS to PASS funnel.** The run lane firms modestly while the coverage stays among the league's worst and the interior rush thins — WR/TE the 2026 lane. Confidence med: the flip rests on the engine reweight more than on marquee adds.

### JAX — PASS+WR1 funnel → RUN funnel (med confidence)
- **2025:** FPAA wr +3.2 / wr1 +2.9 said pass funnel — but NGS said the opposite (slot 3, wide 10, deep 6 = top-5 stingy charting) and the engine's 2025 cov pctl was 98.4. **The two 2025 sources conflict; the 2025 PASS-funnel grade was probably never real.**
- **2026 changes (verified):** LB Devin Lloyd → CAR (3yr/$45M, NFL.com), S Andrew Wingard → ARI, CB swap Tyson Campbell out / Greg Newsome II in (registry, corner-for-corner). Jourdan Lewis (2025 signing) still the nickel.
- **Engine:** cov 98.4→89.1 (still elite), run 70.3→42.2, rush 51.6→39.1.
- **Verdict: SHIFTS to RUN funnel** (also retro-corrects a bad 2025 grade). Lloyd/Wingard exits soften the second level; coverage remains elite — RB lane opens, WR lanes stay closed.

---

## 3. TIGHTENS — 2025 soft lanes closing (fade the stale read)

### BAL — WR1 funnel closes (high confidence)
- **2025:** FPAA wr1 +4.5 / slot +2.8; NGS deep 77 soft, rest mid — agree on a beatable top-CB/deep profile.
- **2026 (verified):** Trey Hendrickson 4yr/$112M (NFL.com) + Calais Campbell return fix a 4.7-pctl pass rush → 54.7. Chidobe Awuzie now CB1 (registry, conf flag noted), Jaylinn Hawkins depth. Scheme: HC **Jesse Minter calls the defense** (Weaver holds the DC title — user-confirmed layer): ~81% zone, split-field two-high, low blitz — the exact shell that suppresses WR1/deep shots.
- **Engine:** cov 45.3→76.6. **Fade the 2025 "BAL WR1 smash" read entirely.**

### LAR — WR1 funnel closes (high confidence)
- **2025:** FPAA wr1 +2.5, everything else tough; the funnel was literally the CB room.
- **2026 (verified):** Trent McDuffie traded in from KC for 4 picks + 4yr/$124M ext (therams.com/ESPN); Jaylen Watson signed (therams.com); L'Jarius Sneed in (registry). Myles Garrett traded in (ESPN) — rush 57.8→85.9.
- The 2025 lane was "beat the corner"; the corner is now McDuffie with Garrett up front. **WR1 funnel dead.** Only caveat: Sneed's 2025 SIS was negative (−6.9 PS) — the WR2 side is the lesser lock.

### DET — PASS/SLOT funnel closes (high confidence)
- **2025:** FPAA slot +3.4 / wr +4.9; NGS milder (wide 71 the softest split). Cause was identifiable: Terrion Arnold's coverage + injured safeties.
- **2026 (verified):** Arnold RELEASED (mid-2026, legal case — currency-audit verified, web-sourced). Rock Ya-Sin re-upped (registry), Roger McCreary signed 1yr (ESPN; Lions coach floated him as the Arnold replacement — slot/outside flex). Kerby Joseph + Brian Branch back healthy (recovery entries + known-gaps note: engine still under-credits a healthy Joseph).
- **Engine:** cov 48.4→85.9, run 54.7→79.7. The slot lane (Branch healthy at nickel) closes. DET drifts back toward fortress.

### IND — PASS funnel tightens at the boundary; slot/TE remain the entry (med-high confidence)
- **2025:** FPAA wr2 +5.0 / slot +3.8 / te +2.7 but wr1 −2.6 — the funnel was "anyone but the WR1" (Sauce Gardner arrived mid-season via the Nov 2025 trade: 2 firsts + Adonai Mitchell, colts.com).
- **2026 (verified):** Full season of Sauce — **the engine gives IND no credit for him** (not in top_coverage; split-season SIS artifact). Cam Taylor-Britt signed (colts.com, Anarumo reunion). Kenny Moore II still the nickel.
- **Engine:** cov 14.1→35.9 (understated), run 17.2→70.3 (mostly rookie-prior-driven: CJ Allen R2, A.J. Haulcy R3, Boettcher R4 [engine-registered]— treat that jump as low-confidence).
- Boundary WR2 lane tightens materially; slot vs an aging Moore and the TE lane are what's left of the 2025 read.

### DAL — PASS/WR1 sieve tightens toward balanced (med confidence)
- **2025:** League-worst everything: FPAA qb +8.1 / wr +9.5 / wr1 +4.2 / slot +3.7; NGS wide+deep 100, ALL 100. Both sources agree: total sieve.
- **2026 (verified):** S Caleb Downs drafted #11 overall after a trade-up (NFL.com) — rangy middle-of-field eraser aimed exactly at the deep/slot lanes. Quinnen Williams was acquired at the 2025 deadline (ESPN — **engine misses him entirely**, its DAL rating keys him to NYJ 2025). Rashan Gary traded in (CBS). Cobie Durant + Jalen Thompson + P.J. Locke in. **Corrections:** DaRon Bland did NOT leave — 4yr/$92M extension (dallascowboys.com); web_teams' "loss" is wrong. Osa Odighizuwa DID leave (→SF trade, ESPN) — engine still credits him to DAL.
- **Engine:** cov 17.2→23.4 / run 4.7→10.9 — still bad, but the engine's stale credits/misses roughly cancel and the verified adds are all pass-defense-shaped. Still targetable, no longer the league's free square. New DC Christian Parker.

### PHI — RUN funnel narrows; fortress deepens (med-high confidence)
- **2025:** FPAA rb +0.5 soft-ish vs wr −4.8 / te −4.7 / slot −3.1 fortress; NGS agrees (slot 0, ALL 3; run mid 39).
- **2026 (verified):** Riq Woolen 1yr/$15M (NFL.com) + Marcus Epps [web-only] stack an already-elite secondary (Mitchell/DeJean). Jonathan Greenard in (registry) for Jaelan Phillips (→CAR $120M). Jonathan Jones (slot CB) in [registry-only, unconfirmed second source].
- **Engine:** run 39.1→54.7, cov 73.4. The RB lane — the one thing PHI gave up — narrows. Downgrade the "RBs vs PHI" auto-read; fortress everywhere else.

### PIT — PASS/TE funnel tightens (med confidence)
- **2025:** FPAA te +3.2 / slot +2.4 / wr +3.5; NGS deep 81 the soft spot.
- **2026 (verified):** New DC Patrick Graham — two-high split-field, press corners, NOT a heavy blitzer (coordinator layer, blend-prior) — structurally anti-deep/anti-TE-seam. Jamel Dean signed (SI), Jalen Ramsey retained (2025 trade), Darnell Savage [web-only]. Kyle Dugger left (→CIN, ESPN). Rush 64.1→89.1 with Watt/Highsmith/Herbig.
- Caveat: Graham prior is a scheme projection, not 2025 observed — med confidence. The TE seam vs LBs is the likeliest residual lane.

### NE — marginal 2025 PASS funnel closes (med confidence)
- **2025:** The PASS-funnel flag was thin (FPAA qb +0.5 / te +1.1) and NGS disagreed (ALL 32nd pctl = tough). Weak-signal grade to begin with.
- **2026 (verified):** Kevin Byard 1yr/$9M (NFL.com — led NFL in INTs 2025) + Dre'Mont Jones 3yr (ESPN; the registry's conf=False is now resolved — both web-confirmed). Cov holds at 95.3.
- Treat NE as a coverage fortress with only the rush (32.8) as a crack.

### WAS — sieve tightens mildly (med confidence)
- **2025:** No funnel because everything was soft: NGS tight 100 / wide 97 / short 94 / rush 90; FPAA all positive. League's biggest smash spot.
- **2026 (verified):** **Registry corrections found in this audit:** Odafe Oweh signed with WAS 4yr/$100M (NFL.com) and Nick Cross signed with WAS 2yr/$14M (NFL.com/Rapoport) — the defensive MOVES registry has both at NYG, so the engine's WAS numbers (rush 20.3, run 1.6) are missing two real adds. Also verified: Sonny Styles drafted #7 overall (LB, Ohio State — NFL.com), K'Lavon Chaisson, Amik Robertson, Tim Settle in. **web_teams' "Dexter Lawrence to WAS" is FALSE** (he's CIN — bengals.com).
- Net: pass rush materially better (Oweh+Chaisson+Styles), coverage still bad (Cross is a run-D safety, cov PS −7.0). Downgrade WAS from "historic sieve" to "soft, especially through the air" — but it stays a target.

---

## 4. OPENS — lanes widening (new/free money vs the 2025 read)

### CLE — WR fortress dissolves → PASS funnel (high confidence)
- **2025:** FPAA wr −5.3 / wr1 −2.2 / wr2 −2.6 fortress; NGS agrees (wide 6, ALL 6, rush 3 — elite everything).
- **2026 (verified):** Myles Garrett traded to LAR (ESPN blockbuster; Jared Verse back the other way). Greg Newsome II swapped to JAX for Tyson Campbell (registry). Quincy Williams in (negative cov PS). Rookie S Emmanuel McNeil-Warren R2 [engine].
- **Engine:** cov 92.2→20.3 — the single biggest funnel-relevant collapse in the league. Run D stays 92nd (Schwesinger/Campbell-of-run-D types stay). New DC Mike Rutenberg.
- **The 2025 "avoid WRs vs CLE" rule is dead.** WRs (esp. vs Campbell/whoever plays across Ward) are now the lane; run into it stays hard.

### TB — no funnel → sieve (high confidence)
- **2025:** Balanced-mediocre (FPAA qb +3.5 the worst number; NGS PA 94 / slot 68 soft-ish).
- **2026 (verified):** Lavonte David RETIRED (ESPN/buccaneers.com, March 2026 — 14 seasons). Jamel Dean → PIT (SI). Logan Hall → HOU (registry). Adds: Alex Anzalone (SIS cov PS −4.0 / run −8.1 — a downgrade at David's spot), Al-Quadin Muhammad, rookie EDGE Rueben Bain Jr. R1 + LB Josiah Trotter R2 [engine; Bain web-corroborated via web_teams].
- **Engine:** cov 35.9→4.7 AND run 85.9→17.2 — both lanes open at once. Bowles' blitz-heavy shell without David/Dean = boom lane for WRs (esp. vs pressure) and RBs. Smash spot.

### NYJ — OUTSIDE funnel widens into a full pass funnel (high confidence)
- **2025:** FPAA wr1 +2.4 / slot −2.6 (outside-soft after the Nov 2025 Sauce Gardner trade to IND); NGS goes further — slot 97 / short 97 / PA 100 / ALL 94 all soft.
- **2026 (verified):** Run D loaded: David Onyemata, T'Vondre Sweat (TEN→NYJ, registry; web_teams' "loss" label is a data error), Demario Davis, Dane Belton (run PS 12.5) — engine run 73.4→98.4. Minkah Fitzpatrick traded in for a 7th + 3yr/$40M ext (NFL.com). EDGE David Bailey drafted #2 overall (newyorkjets.com). Boundary NOT upgraded: Nahshon Wright + Azareye'h Thomas + D'Angelo Ponds R2.
- **Verdict: OPENS.** Elite run D + bottom-third coverage = classic forced-pass funnel; the boundary lane from 2025 stays and total pass volume against them rises. Minkah caps the deep middle only (his 2025 SIS cov was −4.8, and he's one man).

### NO — no funnel → sieve, and the engine is stale on it (high confidence)
- **2025:** Quietly decent everywhere (FPAA all negative).
- **2026 (verified):** CB Alontae Taylor → TEN 3yr/$58M (tennesseetitans.com) — **engine still lists him in NO's top_coverage (false credit)**, so NO's cov 14.1 is optimistic. Demario Davis → NYJ (registry). Cameron Jordan re-signed for a farewell year (June 2026, neworleanssaints.com — web_teams' "loss" resolved: he stays). Kaden Elliss in from ATL.
- **Engine:** run 20.3→4.7, cov 42.2→14.1 (real: lower). RB lane bottom-2 + a McKinstry-led secondary minus its best corner = sieve. Target RBs first, WRs second.

### MIA — TE funnel holds AND the rest opens (high confidence)
- **2025:** FPAA te +3.6; NGS tight 84 agrees; slot 77 also soft.
- **2026 (verified):** Nickel Kader Kohou → KC (chiefs.com) — the slot lane loses its defender. Minkah → NYJ (trade). Bradley Chubb → BUF (NFL.com). Jalen Ramsey already gone (2025 Steelers trade). R1 CB Chris Johnson #27 (miamidolphins.com) + LB Jacob Rodriguez R2 [engine].
- **Engine:** rush 10.9→1.6 (league-worst), cov 26.6→39.1 (rookie-inflated). First-year DC Sean Duggan, teardown roster. TE funnel stands (LB room unfixed: Brooks + rookies), slot opens post-Kohou, and no pass rush protects any of it.

### KC — balanced → mild pass-lane opening (med confidence)
- **2025:** No funnel — everything −0.1 to −2.9 FPAA; NGS only PA 97 soft.
- **2026 (verified):** Trent McDuffie traded to LAR for 4 picks (chiefs.com/ESPN); Jaylen Watson → LAR (therams.com); Bryan Cook → CIN (registry). In: CB Mansoor Delane #6 overall after a trade-up (NFL.com), nickel Kader Kohou (chiefs.com), S Alohi Gilman.
- **Engine:** cov 60.9→48.4. Spagnuolo scheme constant. Replacing an All-Pro CB + starting CB + starting S with a rookie #6 pick + journeyman nickel = more WR-side variance than any 2025 number shows. Not a smash — an "no longer auto-fade KC coverage" note, esp. early season vs the rookie corner.

---

## 5. HOLDS — 2025 funnel still valid (terse)

- **ATL (high):** TE fortress holds — Jessie Bates III + Xavier Watts both retained (cov 92nd pctl). Losses (Elliss→NO, Onyemata→NYJ) hit the front, not the shell. Rush still 14th pctl → the engine's RUN-funnel lean is live (run 32.8). Rookies: CB Avieon Terrell R2 #48 (falcons.com) + LB Harold Perkins Jr. (falcons.com video; **absent from engine rookie table — pressure role unpriced/unconfirmed**).
- **BUF (high):** RUN funnel + WR/TE fortress hold. Run D actually softens further (33→23; Bosa UFA, engine still lists Rousseau correctly — his 2025 "loss" in web_teams contradicts his March-2025 4yr/$80M extension and no 2026 move was found: treat web_teams as wrong). Coverage churn is lateral: Taron Johnson traded (→LV) but nickel Dee Alford signed (Yahoo: "Falcons nickelback, 3-year deal") + CJGJ + Geno Stone. Slot is a modest quality downgrade — a crack, not a lane. Rookie CB Davison Igbinosun R2 [engine-only].
- **CAR (med-high):** RUN funnel holds — run 1.6→7.8 still bottom-5 despite verified Jaelan Phillips (4yr/$120M) + Devin Lloyd (3yr/$45M) adds (single NFL.com source covers both). The 2025 WR1-funnel flag was internally contradicted (FPAA +2.5 vs Mike Jackson "shutdown" shadow grade + Horn) — carry it at low weight, unchanged.
- **DEN (med-high):** SLOT funnel holds — the only soft FPAA lane (+3.1) belongs to nickel Ja'Quan McMillian's assignment area, and DEN made zero secondary moves (McMillian 2nd-round-tendered, extension talks — Mile High Sports/PFR). Everything else is a fortress (cov 98.4). Ignore the engine's PASS→RUN lean flip — both lanes are tough; slot is the entry.
- **GB (med):** No 2025 funnel; nothing in 2026 creates one confidently. Gannon DC (low blitz, front-four). Gary→DAL offset by Hargrave/Colby Wooden; St-Juste + Zaire Franklin in; Quay Walker out. Mild RB lean (run 48→39) worth a note, not a funnel.
- **HOU (high):** WR fortress holds — zero starter movement (only Blankenship/Hall depth adds), every unit 70th+ pctl, Stingley/Lassiter/Anderson/Hunter all retained. Avoid.
- **LAC (med-high):** WR fortress holds (Still/Jackson/James intact, cov 79.7) and the RUN-funnel lean firms (run 29.7, rush down post-Mack-aging/Oweh-departure). New DC Chris O'Leary is a Minter-tree continuity promotion. Target RBs, avoid WRs.
- **MIN (high):** WR fortress holds — Flores continuity, rush 89→95, plus CB James Pierre (registry). The only 2025 crack (NGS deep 97) persists behind a blitz-heavy shell: deep shots or nothing.

---

## 6. Layer corrections surfaced by this audit (fix upstream)

**Registry errors (reweight_defense_2026.py MOVES):**
1. `'odafe oweh': to NYG` — **WRONG.** Signed WAS, 4yr/$100M (NFL.com, web-verified). NYG rush over-credited, WAS under-credited.
2. `'nick cross': to NYG` — **WRONG.** Signed WAS, 2yr/$14M (NFL.com video/Rapoport). Same misread of the same NFL.com roundup URL.

**Engine stale credits (false "assumed-staying"):**
3. Riq Woolen counted for SEA (cov PS 26.8) — signed PHI 1yr/$15M (NFL.com).
4. Alontae Taylor counted for NO (top_coverage) — signed TEN 3yr/$58M (tennesseetitans.com).
5. Osa Odighizuwa counted for DAL (top_pass_rush) — traded to SF for a 3rd (ESPN/49ers.com).

**Engine missing credits:**
6. Quinnen Williams (NYJ→DAL, Nov 2025 deadline trade, ESPN) — absent from DAL's unit.
7. Sauce Gardner (NYJ→IND, Nov 2025 trade, colts.com) — absent from IND's top_coverage (split-season SIS artifact); IND cov understated.
8. Dre Greenlaw → SF [web_teams only — **unconfirmed**, verify before crediting].

**web_teams.json errors:**
9. WAS key_additions "Dexter Lawrence (DT, trade)" — false; he's CIN (bengals.com). (WAS's Oweh add, previously contradicted by the registry, is in fact CORRECT.)
10. DAL key_losses "DaRon Bland (CB)" — false; extended 4yr/$92M (dallascowboys.com).
11. BUF key_losses "Greg Rousseau (EDGE)" — contradicted by his March-2025 4yr/$80M extension; no 2026 move found. Treat as error.
12. NYJ key_losses "T'Vondre Sweat (DL)" — backwards; he ARRIVED from TEN (registry + engine).
13. NYG defense_outlook prose contains an unresolved mid-edit artifact ("...led by Dexter Lawrence... wait Abdul Carter").

**Known 2025-source disagreements to carry forward (not errors, but grade-confidence dampeners):**
- JAX: FPAA pass-funnel vs NGS/engine fortress — sided with NGS/engine.
- ARI: FPAA WR-tough vs NGS everything-soft — sided with NGS/engine.
- CAR: FPAA WR1-soft vs shadow-CB shutdown grades — flagged low-weight.
- NE: FPAA mild pass-funnel vs NGS tough — the 2025 flag was weak-signal.

---

## 7. VERIFICATION RESULTS — 2026-07-05 (web-verified against primary sources, then applied)

All 12 contested corrections from §6 were **web-verified against primary sources** (NFL.com, team sites, ESPN) before any layer was touched. **Result: 12 / 12 confirmed.** The fable audit was accurate on every count.

**reweight_defense_2026.py MOVES — corrected (2 fixes + 6 additions), engine re-run, A/B-validated:**
| Player | Was | Corrected to | Source | Engine effect (clean A/B) |
|---|---|---|---|---|
| Odafe Oweh | NYG | **WAS** (4yr/$100M) | nfl.com | WAS rush +25 · NYG rush −34 |
| Nick Cross | NYG | **WAS** (2yr/$14M) | nfl.com | (folded into above) |
| Riq Woolen | — (stale SEA) | **PHI** (1yr/$15M) | nfl.com | PHI cov +, SEA cov −12.5 |
| Alontae Taylor | — (stale NO) | **TEN** (3yr/$58M) | titans.com | TEN cov +31 · NO cov −6, run −12.5 |
| Osa Odighizuwa | — (stale DAL) | **SF** (trade, 3rd) | espn.com | credited SF rush (sub-quantum) |
| Quinnen Williams | — (missing) | **DAL** (Nov-25 trade) | nfl.com | credited DAL rush 11.1 PS |
| Sauce Gardner | — (missing) | **IND** (Nov-25 trade) | colts.com | IND cov +6.2 PS (see caveat) |
| Dre Greenlaw | — | **SF** (1yr/$7.5M) | nfl.com | not in SIS → honest zero-floor |

**web_teams.json — 5 errors corrected:** WAS drop phantom "Dexter Lawrence add" (he's CIN); DAL drop "Bland loss" (extended 4yr/$92M); BUF drop "Rousseau loss" (extended 4yr/$80M); NYJ drop "Sweat loss" (he ARRIVED from TEN, now listed as an add); NYG add "Dexter Lawrence (trade to CIN)" loss + fixed the mid-edit outlook artifact.

**Funnel leans that flipped after the correction** (boom/defensive_profile.json re-run): **TEN pass→balanced**, **NO balanced→pass**, **DAL balanced→run**, **IND pass→balanced**. WAS pass-rush jumped 20→73 pctl (Oweh); NYG fell 77→52 (Oweh/Cross out).

**Caveats carried forward (honest, not fabricated):**
- **IND coverage is UNDERSTATED.** Sauce Gardner's 2025 was a disrupted NYJ→IND split, so his SIS coverage Points Saved is only 6.2 — a full healthy season would grade far higher than the reweight can show. IND's engine coverage (4.7 pctl) is a floor, not a true 2026 read. Weight the funnel accordingly.
- **Dre Greenlaw** is absent from the SIS Points Saved source, so the engine credits SF nothing for him (replacement-level floor) — correct per the no-fabrication rule, but SF's true LB run/coverage is a touch better than the number.
