# 2026 Personnel Projection — Adversarial Verification (5 Low-Confidence Calls)

**Run:** 2026-07-05. Scope: the 5 teams flagged in `PERSONNEL_2026_BRAIN_PROJECTION.md` / `personnel_2026_projection.json` as resting on hire/roster inference (DEN, CAR, SF, MIA, NE). Every 2026 coordinator/play-caller/roster claim was re-verified against live web sources (all post-training-cutoff facts). Evidence below is split **WEB-CONFIRMED** vs **STILL INFERENCE**.

**Scoreboard: 4 CONFIRM (2 strengthened, 2 upgraded), 1 REFUTE (SF).**

| Team | Original call | Verdict | Corrected 2026 direction | Confidence after |
|---|---|---|---|---|
| DEN | HOLD (11; mild 12 tilt) — conf LOW | **CONFIRM** | hold — 11 base, mild 12/TE-production tilt | **medium** (was low) |
| CAR | HOLD (11) — conf LOW, registry conflict | **CONFIRM** (conflict resolved) | hold — 11-dominant | **medium** (was low) |
| SF | DOWN (21 engine collapses, Juszczyk gone) — conf MED | **REFUTE** | **HOLD heavy (~rank-5); 21 intact; early-season mix tilts 21/11 over 12 (Kittle risk)** | **high** on premise; medium on mix |
| MIA | DOWN (21/22 collapse → 11/12) — conf MED | **CONFIRM (strengthened)** | down — 21/22 collapses, lands 11/12 | **high** (was medium) |
| NE | DOWN mild (more 11) — caller unresolved, conf MED | **CONFIRM** (caller resolved: McDaniels) | down mild — 11 lean; reversal trigger = veteran TE add | **high** (was medium) |

---

## DEN — Denver Broncos

**Original:** HOLD (76.7% 11 baseline), mild 12 tilt possible. Flagged: rests on Webb hire + soft "TEs more involved" chatter, no grouping intel. Confidence LOW.

**VERDICT: CONFIRM.**

**WEB-CONFIRMED:**
- **Davis Webb is the 2026 OC AND play-caller; Payton handed it off** — [NFL.com, 2026-02-24](https://www.nfl.com/news/broncos-coach-sean-payton-handing-play-calling-duties-to-new-oc-davis-webb) ("It's not something I would do if I didn't think it will help our team" — Payton); corroborated by [ESPN](https://www.espn.com/nfl/story/_/id/48025767/sean-payton-says-oc-davis-webb-broncos-playcaller) and [9News/Klis](https://www.9news.com/article/sports/nfl/denver-broncos/mike-klis/denver-broncos-head-coach-sean-payton-hands-over-offensive-play-calling-to-offensive-cordinator-davis-webb/73-1e94fc15-b536-43bf-934e-fa11fa60e85a).
- **The "TEs more involved" chatter is real organizational intent, not just beat noise** — [ESPN, 2026-05-13](https://www.espn.com/nfl/story/_/id/48745630/denver-broncos-more-production-tight-ends-2026-season-justin-joly): 2025 TE room = "most glaring weakness" (3 TDs, 26th in receiving yards); Engram had 64% of the room's receptions (50-461-1); re-signed Trautman, Adkins, Krull; **drafted Justin Joly (R5, "move" TE) and Dallen Bentley (R7, in-line)**; Payton optimistic about boosting TE production.
- **Jaylen Waddle acquired from MIA** (draft-weekend trade, picks incl. a 2026 1st) — [NFL.com, April 2026](https://www.nfl.com/news/dolphins-trading-wr-jaylen-waddle-to-broncos-for-draft-picks-including-2026-first-rounder), [denverbroncos.com](https://www.denverbroncos.com/news/broncos-acquire-wr-jaylen-waddle-in-trade-with-dolphins) — a vertical-11 counterweight to any TE lean.

**STILL INFERENCE:** No source anywhere gives a 2026 grouping plan (no 12/13-personnel quote). The TE investment is late-round depth + production intent, not a two-TE identity; brain's own 6/16 counterpoint (Engram, 32, likely stays a rotation behind a re-signed Trautman + two drafted TEs) caps the 12 leg.

**Corrected call:** unchanged — **HOLD** the 76.7% 11 baseline, emphasis 11 with a mild 12/TE-production tilt. **Confidence: LOW → MEDIUM** (caller verified; TE-intent verified; grouping still unspecified).

---

## CAR — Carolina Panthers

**Original:** HOLD (79.1% 11). Flagged: hire-only inference + registry conflict (`coordinator_changes_2026.json` has no CAR entry; `scheme_2026.json` lists Idzik as a new caller). Confidence LOW.

**VERDICT: CONFIRM — and the registry conflict is fully resolved.**

**WEB-CONFIRMED:**
- **Brad Idzik calls Carolina's plays in 2026; Canales handed them off** — [panthers.com (team announcement)](https://www.panthers.com/news/dave-canales-offensive-coordinator-brad-idzik-to-call-plays-in-2026); [AP via WPTF, 2026-02-24](https://www.wptf.com/2026/02/24/panthers-coach-dave-canales-hands-over-offensive-play-calling-duties-to-coordinator-brad-idzik/); [ESPN, 2026-02-27](https://www.espn.com/nfl/story/_/id/48033768/nfl-carolina-panthers-brad-idzik-dave-canales-playcalling) (Idzik: "expand our playbook a little bit more" — no personnel specifics).
- **Why both local files were "right":** the CBS registry tracks new coordinator **hires** — Idzik has been CAR's OC since 2024, so no CAR entry is correct; `scheme_2026.json` tracks **play-caller changes** — Idzik as a new caller is also correct. Not a data error; two different registries.
- **No 12-personnel investment:** CAR made no TE upgrade — Canales: "I'm super confident in the room"; Tremble spring hype but has never topped 250 receiving yards — [Yahoo, 2026-06-11](https://sports.yahoo.com/articles/panthers-te-tommy-tremble-distancing-183822382.html). Same Canales wide-zone family (more motion, short aDOT per scheme file/ESPN framing).

**STILL INFERENCE:** The hold itself — there is no 2026 grouping quote in either direction, anywhere. The no-TE-investment datapoint mildly supports staying 11-dominant.

**Corrected call:** unchanged — **HOLD**, emphasis 11 (79.1% 11 baseline). **Confidence: LOW → MEDIUM** (caller identity verified; personnel direction remains a no-signal hold).

---

## SF — San Francisco 49ers

**Original:** DOWN — "FB Kyle Juszczyk is gone → the 26.3% 21-personnel engine loses its fullback," emphasis shifts 11/12. Flagged: roster-only inference, no brain quote. Confidence MEDIUM.

**VERDICT: REFUTE — the premise is false. Juszczyk is on the 2026 roster.**

**WEB-CONFIRMED:**
- **Juszczyk is a 49er in 2026, entering his 14th NFL season**, saying "I just want to continue this thing as long as I possibly can" — [NBC Sports Bay Area, 2026-06-13](https://www.nbcsportsbayarea.com/nfl/san-francisco-49ers/kyle-juszczyk-retirement-plans/1943209/); also active/quoted with the team in March — [49ers Webzone, 2026-03-19](https://www.49erswebzone.com/articles/199826-offseason-juszczyk-excited-george-kittle/).
- **Source of the error:** the March 2025 cut-then-re-sign week — released ([ESPN, March 2025](https://www.espn.com/nfl/story/_/id/44199544/san-francisco-49ers-inform-fullback-kyle-juszczyk-being-released)) then brought back on a **two-year deal covering 2025-26** ([ESPN, March 2025](https://www.espn.com/nfl/story/_/id/44261853/source-49ers-bring-back-fb-kyle-juszczyk-two-year-deal), [49ers.com](https://www.49ers.com/news/49ers-re-sign-fb-kyle-juszczyk-to-two-year-deal)). `PERSONNEL.md`'s "K.Juszczyk → gone" is a stale-transaction artifact.
- **Kittle IS back but with early-season risk:** tore his **Achilles in the Wild Card win over PHI (Jan 2026)**; doctor-cited 9-12-month recovery ([Yahoo](https://sports.yahoo.com/articles/george-kittle-injury-doctor-confirms-005537956.html)); targeting Week 1 (Australia opener) but "nothing is guaranteed... it'll be a game-time decision" — [49ers Webzone, 2026-05-26](https://www.49erswebzone.com/articles/200884-george-kittle-availability-achilles-recovery/).
- **Caller continuity:** Klay Kubiak retained as OC, **Shanahan still calls plays** — [PFT/NBC Sports, Jan 2026](https://www.nbcsports.com/nfl/profootballtalk/rumor-mill/news/klay-kubiak-will-be-the-49ers-oc-kyle-shanahan-will-still-call-plays), [ProFootballRumors, 2026-01](https://www.profootballrumors.com/2026/01/kyle-shanahan-49ers-will-not-allow-lateral-move-for-oc-klay-kubiak).
- WR adds Mike Evans + Christian Kirk confirmed (Juszczyk praising both — [49ers Webzone, 2026-03-19](https://www.49erswebzone.com/articles/199826-offseason-juszczyk-excited-george-kittle/)).

**STILL INFERENCE:** How the mix moves if Kittle misses/eases in — 2025 precedent (Kittle out early, SF leaned on the FB) suggests 21/11 absorbs it, not 12.

**CORRECTED CALL: heavy HOLD (stay ~rank-5 / ~41%), 21-personnel engine INTACT.** Emphasis 21/11. If Kittle is limited early, 21 if anything firms up; Evans/Kirk are only a mild 11 counterweight. Watch: Juszczyk is 35 in a contract year — a **2027** cliff, not a 2026 one. **Confidence: HIGH on the reversed premise; MEDIUM on the exact mix.**

---

## MIA — Miami Dolphins

**Original:** DOWN — McDaniel's FB-built 21/22 (25.6% combined) collapses with McDaniel + Ingold gone; Slowik lands the offense on 11/12. Flagged: 21/22-down leg was coach-departure inference, no MIA-specific quote. Confidence MEDIUM.

**VERDICT: CONFIRM — and upgrade. Every inferred leg is now directly sourced.**

**WEB-CONFIRMED:**
- **Slowik is MIA's 2026 OC and play-caller under new HC Jeff Hafley** (promoted from pass-game coordinator) — [ESPN](https://www.espn.com/nfl/story/_/id/47717683/source-dolphins-promote-bobby-slowik-offensive-coordinator), [CBS Sports, 2026-06-09](https://www.cbssports.com/fantasy/football/news/dolphins-2026-fantasy-football-outlook-offensive-coordinator-bobby-slowik/) ("play-caller Bobby Slowik"; West Coast base; HOU 59% pass; RBs only 16% of targets).
- **Ingold was RELEASED by Miami (2026-03-06) and signed with LAC (2yr/$7.5M) to follow McDaniel — who is confirmed as the Chargers' OC** — [ESPN, 2026-03-08](https://www.espn.com/nfl/story/_/id/48148992/chargers-agree-multiyear-deal-free-agent-alec-ingold): "He played the past four seasons in Miami under Mike McDaniel, who is now the Chargers' offensive coordinator."
- **The FB role is not being replaced:** "the top fullbacks have all signed"; **"In Slowik's second year in Houston... he did not utilize a fullback. Plenty of 12 personnel (one running back, two tight ends), but no regular fullback"**; blocking TE **Ben Sims signed (1 yr) to replace Julian Hill**; expect "more of an H-back/F role" — [SI/All Dolphins, 2026-03-16](https://www.si.com/nfl/dolphins/onsi/news/examining-what-could-or-might-not-happen-at-fullback-01kkt89xkvhm). Miami's only FB on the roster is UDFA **DJ Herman — a converted linebacker** with 27 career college offensive snaps — [AtoZ Sports, 2026-05-11](https://atozsports.com/nfl/miami-dolphins-news/the-miami-dolphins-have-finally-added-a-fullback-to-their-2026-roster-but-theres-a-catch/).
- **WR/room gutting confirmed:** Waddle traded to DEN for picks — [NFL.com, April 2026](https://www.nfl.com/news/dolphins-trading-wr-jaylen-waddle-to-broncos-for-draft-picks-including-2026-first-rounder); Malik Willis is the QB Slowik is building around ([NFL.com](https://www.nfl.com/news/dolphins-oc-bobby-slowik-malik-willis-can-spin-the-ball-all-over-the-field)).

**STILL INFERENCE:** The precise "2024 HOU ran 12P at 31.5% (3rd-highest)" figure (local @coachspeakindex note) was not independently re-verified — but SI's "plenty of 12 personnel" confirms the direction the number was carrying.

**Corrected call:** unchanged — **heavy DOWN from 42.8%/#4; 21/22 collapses; emphasis 11/12** (12 via Dulcich/Sims H-back looks). **Confidence: MEDIUM → HIGH.**

---

## NE — New England Patriots

**Original:** DOWN mild (more 11; "lost Julian Hill — plan was 12"), reversal trigger = veteran TE add. Flagged: 2026 play-caller not in the CBS registry (profiles said Josh McDaniels, unverified). Confidence MEDIUM.

**VERDICT: CONFIRM — caller resolved: Josh McDaniels, returning (registry gap explained).**

**WEB-CONFIRMED:**
- **Josh McDaniels is NE's OC and play-caller in 2026 — and was in 2025** — [patriots.com coaches roster](https://www.patriots.com/team/coaches-roster/josh-mcdaniels); [NBC Sports Boston, 2026-06-26](https://www.nbcsportsboston.com/nfl/new-england-patriots/play-caller-rankings-2026-josh-mcdaniels/793012/): rose 11th → **4th** in play-caller rankings, **AP NFL Assistant of the Year** after NE finished 2nd in points, 2nd in EPA/play, 1st in EPA/pass in 2025. **Registry gap resolved:** the CBS file lists new **2026 hires**; McDaniels is a returning 2025 hire, so NE correctly has no entry.
- **His personnel tendency is diversity, not an 11-only identity:** "He changed personnel groupings at the drop of a hat, using two backs, two tight ends and a fullback" — [NBC Sports Boston, 2026-06-26](https://www.nbcsportsboston.com/nfl/new-england-patriots/play-caller-rankings-2026-josh-mcdaniels/793012/). So the projected 11-lean is situational (injury/roster), not schematic.
- **Julian Hill (the 12-personnel blocking TE, signed from MIA) is OUT FOR THE SEASON** — knee injury, placed on IR — [Boston Globe, 2026-06-02](https://www.bostonglobe.com/2026/06/02/sports/julian-hill-patriots-injured-reserve/), [boston.com, 2026-06-01](https://www.boston.com/sports/new-england-patriots/2026/06/01/new-england-patriots-injury-update-julian-hill-nfl-football-tight-end/). Confirms the brain's premise ("lost" = season-ending injury). The veteran-TE-add drumbeat is real ([Pats Pulpit training-camp piece](https://www.patspulpit.com/new-england-patriots-analysis/130616/tight-end-depth-julian-hill-injury-training-camp)).
- **The WR room got the capital, supporting the 11 lean:** traded for **A.J. Brown** from PHI ([patriots.com](https://www.patriots.com/news/patriots-acquire-wr-a-j-brown-in-a-trade-with-the-philadelphia-eagles), [ESPN/Barnwell trade analysis](https://www.espn.com/nfl/story/_/id/48912173/2026-nfl-offseason-aj-brown-trade-patriots-eagles-receiver-draft-picks-barnwell)) and signed **Romeo Doubs to a 4-year (~$80M) deal** ([NFL.com](https://www.nfl.com/news/romeo-doubs-patriots-sign-former-packers-wr-four-year-contract), [boston.com, 2026-03-12](https://www.boston.com/sports/new-england-patriots/2026/03/12/new-england-patriots-romeo-doubs-wide-receiver-green-bay-packers-free-agency/)).

**STILL INFERENCE:** Magnitude. The "will do more 11 bc they lost Julian Hill — plan was 12" line is single-beat sourcing (@dhananizain 6/16-17, local); with a grouping-diverse caller and a 21=12.6% FB package in the 2025 baseline, this is a mild tilt, not a collapse.

**Corrected call:** unchanged — **DOWN mild, emphasis 11** (12 recovers if they add a veteran TE; that trigger stands). **Confidence: MEDIUM → HIGH** (caller + injury + WR-investment all verified).

---

## Residual unverifiables / data-hygiene notes

1. **`PERSONNEL.md` SF row is corrupted**: "K.Juszczyk → gone" (false — 2-yr deal through 2026) and "rookies: Mike Evans, Brandon Aiyuk" (both veterans; Schefter chatter says Aiyuk may be CUT near camp, per local brain 2026 note). Treat that file's departure/rookie buckets as unreliable without a second source.
2. **Exact 2024 HOU 12P rate (31.5%, 3rd)** — direction web-confirmed (SI 3/16/26: "plenty of 12 personnel"), exact figure remains locally sourced only.
3. **DEN/CAR grouping percentages for 2026** — no public plan exists in either direction; both holds are defaults, now standing on verified caller + roster facts rather than nothing.
4. **NE dc note (brain metadata "Zak Kuhr")** — a 6/12 tweet calls Kuhr the LB coach; defensive side not in scope, but don't cite the brain's NE DC field without checking.
