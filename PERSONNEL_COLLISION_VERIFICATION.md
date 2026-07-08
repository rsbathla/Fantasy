# PERSONNEL_COLLISION_VERIFICATION.md

**Purpose:** Web-verify the corrected roster-move data after fixing the first-initial name-collision bug ("K. Coleman" merged Keon Coleman + Kevin Coleman Jr.; "J. Taylor" merged Jonathan Taylor + J'Mari Taylor), which had corrupted vacated-target/vacated-volume calculations.

**Verification date:** 2026-07-05 (all facts below are 2026-offseason facts, verified via live web sources — no training priors used as evidence).

---

## Verdict summary

| Player | 2026 Team | Corrected record says | Verdict |
|---|---|---|---|
| Keon Coleman (WR) | **Buffalo Bills** | Stayed in BUF (no departure) | **CONFIRMED** |
| Kevin Coleman Jr. (WR) | **Miami Dolphins** | Moved, destination MIA | **CONFIRMED (destination)** — but see origin flag: he is a 2026 MIA draft pick, **never a Bill** |
| Jonathan Taylor (RB) | **Indianapolis Colts** | Stayed in IND (no departure) | **CONFIRMED** |
| J'Mari Taylor (RB) | **Jacksonville Jaguars** | Moved, destination JAX | **CONFIRMED (destination)** — but see origin flag: he is a 2026 JAX undrafted free agent, **never a Colt** |

**Bottom line for the vacated-volume model:** Keon Coleman's Buffalo targets and Jonathan Taylor's Indianapolis carries are **NOT vacated** — the correction is right. Additionally, note that neither Kevin Coleman Jr. nor J'Mari Taylor vacated *any* NFL volume anywhere: both entered the league in April 2026 (draft pick / UDFA). Any record modeling them as "Buffalo → Miami" or "Indianapolis → Jacksonville" departures is a residual artifact of the collision — they were in college (Missouri / Virginia) in 2025.

---

## 1. Keon Coleman (WR) — Buffalo Bills — CONFIRMED STAYED

Corrected record verified: Keon Coleman did **not** depart Buffalo; he is on the Bills for 2026.

| # | Source | Specific claim | Date | Why it matters |
|---|---|---|---|---|
| 1 | [buffalobills.com roster page](https://www.buffalobills.com/team/players-roster/keon-coleman/) | Listed on the Bills' current roster: WR, #0, 3 years experience, drafted by BUF 33rd overall in 2024; full 2025 game log (38 rec / 404 yds / 4 TD) | Live team page (accessed 2026-07-05) | Team primary source: he is a current Bill — no vacated BUF targets |
| 2 | [NFL.com — Beane shuts down trade interest](https://www.nfl.com/news/bills-gm-brandon-beane-shut-down-trade-interest-in-wr-keon-coleman-his-best-year-is-yet-to-come) | Bills GM Brandon Beane rejected multiple offseason trade inquiries: "We shut those down. Our intention is for Keon to be here… His best year is yet to come here in 2026." | 2026-04-27 | League-owned outlet, on-record GM quote: trade interest existed but was refused — he stayed |
| 3 | [UPI — Bills 'shut down' trade talks](https://www.upi.com/Sports_News/NFL/2026/04/27/Buffalo-Bills-shut-down-trade-Keon-Coleman/1971777307306/) | Independent wire-service report of the same trade-talk shutdown | 2026-04-27 | Second, independent outlet corroborating no departure |
| 4 | [NFL.com — 'make or break' 2026](https://www.nfl.com/news/bills-wr-keon-coleman-describes-2026-season-as-make-or-break) | Coleman is on the 2026 Bills roster; new HC Joe Brady: "I made sure when I got the job he knew he was going to be here" | 2026-05-19 | Post-draft, 2026-dated confirmation he's in Buffalo's 2026 plans |
| 5 | [ESPN player page](https://www.espn.com/nfl/player/_/id/4635008/keon-coleman) | Team: Buffalo Bills; WR #0; status Active | Live (accessed 2026-07-05) | Independent database corroboration |
| 6 | [Wikipedia — Keon Coleman](https://en.wikipedia.org/wiki/Keon_Coleman) | BUF 2024, BUF 2025; signed 4-year rookie contract 2024-06-12 (runs through 2027) | Accessed 2026-07-05 | Contract term covers 2026 — consistent with staying |

**Noise, resolved:** There *was* real offseason churn around him — owner Terry Pegula's January 2026 press-conference comments and multiple trade-speculation pieces ([heavy.com](https://heavy.com/sports/nfl/buffalo-bills/insider-keon-coleman-trade-return/), [ESPN trade-market simulation](https://www.espn.com/nfl/story/_/id/48816864/2026-nfl-offseason-trade-offers-best-deals-coleman-kmet-richardson-thibodeaux), [SI fantasy mock destinations](https://www.si.com/onsi/fantasy/trade-analysis/nfl-fantasy-football-mock-trade-scenarios-destinations-keon-coleman)). All of it is speculation/rumor; the on-record GM statement (source 2) and the live roster page (source 1) settle it: **no transaction occurred.** This rumor volume is plausibly what made the collision bug look believable.

---

## 2. Kevin Coleman Jr. (WR) — Miami Dolphins — DESTINATION CONFIRMED (origin flag)

Corrected record verified in part: his 2026 team is **Miami**. The expected origin ("Buffalo →") is **refuted** — he was never on the Bills.

| # | Source | Specific claim | Date | Why it matters |
|---|---|---|---|---|
| 1 | [miamidolphins.com draft-day-3 announcement](https://www.miamidolphins.com/news/miami-adds-seven-players-in-the-final-day-of-the-2026-nfl-draft) | "Miami took its third wideout of the draft in Missouri wide receiver Kevin Coleman Jr. (177th overall)" — Round 5, 2026 NFL Draft | 2026-04-25 | Team primary source: he entered the NFL via the 2026 draft, selected by Miami — not via a Buffalo departure |
| 2 | [miamidolphins.com — Fast Facts: Kevin Coleman Jr.](https://www.miamidolphins.com/news/fast-facts-kevin-coleman-jr) | 5th round, pick 177, 2026 draft; college path Jackson State → Louisville → Mississippi State → Missouri; no prior NFL teams | 2026-04-29 | Documents he was in college through 2025 — he had no NFL volume to vacate anywhere |
| 3 | [miamidolphins.com roster page](https://www.miamidolphins.com/team/players-roster/kevin-coleman-jr/) | On the Dolphins' current roster: WR, #83, Missouri, Rookie (R) | Live (accessed 2026-07-05) | Team primary source for his 2026 team = MIA |
| 4 | [Wikipedia — Kevin Coleman Jr.](https://en.wikipedia.org/wiki/Kevin_Coleman_Jr.) | Career timeline: Jackson State 2022, Louisville 2023, Mississippi State 2024, Missouri 2025; NFL: Miami Dolphins 2026–present; **no Buffalo stint** | Accessed 2026-07-05 | Whole-career check: never a Bill at any point |
| 5 | [miamidolphins.com draft press conference transcript](https://www.miamidolphins.com/news/transcript-wr-kevin-coleman-jr-nfl-draft-day-3-apr-28) | Introduced as a Dolphins draft selection | 2026-04-28 | Additional team-primary corroboration of the draft acquisition |

**Origin flag (important for the fix):** The corrected departure record reportedly asserts "Kevin Coleman Jr.: Buffalo → Miami." The **Miami** half is correct; the **Buffalo** half is not supported by any source. A targeted transaction search for "Kevin Coleman" + Buffalo Bills returned zero connections (only generic team transaction indexes: [buffalobills.com/transactions](https://www.buffalobills.com/team/transactions/), [ESPN Bills transactions](https://www.espn.com/nfl/team/transactions/_/name/buf/buffalo-bills)). He was at Missouri in 2025 and was drafted by Miami in April 2026. **If the record still books "vacated Buffalo targets" from him, that is residual corruption — the real vacated-target answer for this pair is: Keon's BUF targets are not vacated, and Kevin Jr. vacated nothing (rookie).** The phantom "BUF → MIA" move is exactly the artifact a first-initial merge would produce ("K. Coleman" on BUF in 2025 + "K. Coleman" on MIA in 2026).

**Adjacent-collision hygiene note:** Miami also signed LB **Seth Coleman** to a reserve/future contract on 2026-01-21 ([miamidolphins.com](https://www.miamidolphins.com/news/dolphins-sign-coleman-to-futures-contract)) — a different player, different position, different initial; verified not to be conflatable with Kevin Coleman Jr.

---

## 3. Jonathan Taylor (RB) — Indianapolis Colts — CONFIRMED STAYED

Corrected record verified: Jonathan Taylor did **not** depart Indianapolis; he is on the Colts for 2026.

| # | Source | Specific claim | Date | Why it matters |
|---|---|---|---|---|
| 1 | [colts.com roster page](https://www.colts.com/team/players-roster/jonathan-taylor/) | Listed on the Colts' current roster: RB, #28, 7 years experience; 2026 Pro Bowler; led NFL with 18 rush TD in 2025 (1,585 yds); recent offseason media availability saying he wants to "remain a Colt for life" | Live team page (accessed 2026-07-05) | Team primary source: current Colt — no vacated IND rush/target volume |
| 2 | [Spotrac contract page](https://www.spotrac.com/nfl/player/_/id/47636/jonathan-taylor) | Under contract with Indianapolis **through 2026** (3-yr/$42M extension signed 2023-10-07); 2026 cap hit $15,562,000; free agency 2027; transaction history shows only IND deals, no departure | Live (accessed 2026-07-05) | Independent contract-registry proof he is bound to IND for 2026 |
| 3 | [ESPN — contract-years story](https://www.espn.com/nfl/story/_/id/49002856/jonathan-taylor-quenton-nelson-deforest-buckner-indianapolis-colts-entering-contract-years) | Taylor is entering the **final year of his contract with the Colts in 2026**; rushed for 1,585 yds / league-leading 18 TD in 2025; HC Shane Steichen: "It's hard to take him off the field when he's running so good" | 2026-06-10 | 2026-dated national reporting placing him on IND for 2026 |
| 4 | [ESPN player page](https://www.espn.com/nfl/player/_/id/4242335/jonathan-taylor) | Team: Indianapolis Colts; RB #28; status Active | Live (accessed 2026-07-05) | Independent database corroboration |

**Noise, resolved:** July 2026 headlines like "Colts trade star running back Jonathan Taylor to NFC contender…" ([atozsports](https://atozsports.com/nfl/indianapolis-colts-news/indianapolis-colts-trade-star-running-back-jonathan-taylor-to-nfc-contender-in-espns-latest-bold-predictions-for-the-2026-season/), 2026-07-03; syndicated to [Yahoo](https://sports.yahoo.com/articles/indianapolis-colts-trade-star-running-165226460.html)/[Yardbarker](https://www.yardbarker.com/nfl/articles/indianapolis_colts_trade_star_running_back_jonathan_taylor_to_nfc_contender_in_espns_latest_bold_predictions_for_the_2026_season/s1_17313_44023429)) are **ESPN "bold predictions" — explicitly hypothetical** (a Ben Solak prediction of a possible pre-deadline trade to Chicago). The article itself states Taylor remains a Colt as of publication. **No trade has occurred.** Flagging because a naive headline scraper would misparse these as a transaction — the same failure mode this verification exists to guard against.

---

## 4. J'Mari Taylor (RB) — Jacksonville Jaguars — DESTINATION CONFIRMED (origin flag)

Corrected record verified in part: his 2026 team is **Jacksonville**. The expected origin ("Indianapolis →") is **refuted** — he was never on the Colts.

| # | Source | Specific claim | Date | Why it matters |
|---|---|---|---|---|
| 1 | [jaguars.com roster page](https://www.jaguars.com/team/players-roster/j-mari-taylor/) | On the Jaguars' current roster: RB, #30, Rookie; college Virginia (after four seasons at NC Central); **"Signed by Jacksonville as an undrafted free agent on 4/26/26"** | Live team page (accessed 2026-07-05) | Team primary source: acquisition type (UDFA) and exact date — direct college-to-JAX path, no prior NFL team |
| 2 | [SI (Virginia team site)](https://www.si.com/college/virginia/football/virginia-rb-j-mari-taylor-signs-with-the-jacksonville-jaguars-as-an-undrafted-free-agent-01kq1471zjz9) | Went undrafted in the 2026 NFL Draft; signed with Jacksonville as a UDFA; 1,062 rush yds and ACC-leading 14 rush TD at Virginia in 2025; **no Colts mention** | 2026-04-26 | Independent, contemporaneous report of the actual transaction |
| 3 | [ESPN player page](https://www.espn.com/nfl/player/_/id/4713118/jmari-taylor) | Team: Jacksonville Jaguars; RB #30; Active; Rookie; college Virginia; no Colts association anywhere on page | Live (accessed 2026-07-05) | Independent database corroboration of 2026 team = JAX |
| 4 | [Pro-Football-Reference](https://www.pro-football-reference.com/players/T/TaylJM00.htm) | Team: Jacksonville Jaguars; colleges NC Central and Virginia; **no Indianapolis Colts anywhere in profile/transactions** | Live (accessed 2026-07-05) | Career-history registry: JAX is his only NFL team |
| 5 | [jaguars.com feature](https://www.jaguars.com/news/rookie-rb-looking-to-prove-himself-i-ve-always-been-an-underdog) | Team-site feature on the rookie RB fighting for a roster spot | 2026 offseason | Team-primary confirmation he is in JAX's 2026 camp picture |

**Origin flag (important for the fix):** The corrected departure record reportedly asserts "J'Mari Taylor: Indianapolis → Jacksonville." The **Jacksonville** half is correct; the **Indianapolis** half is not supported by any source. A targeted search for "J'Mari Taylor" + Colts signed/waived returned zero connections. His timeline: NC Central 2020–2024 → Virginia 2025 → undrafted → signed by Jacksonville 2026-04-26. **He vacated no Indianapolis volume because he never had any.** The phantom "IND → JAX" move is the "J. Taylor" first-initial artifact (Jonathan on IND 2025 + J'Mari on JAX 2026).

**Weak-source note:** [Wikipedia's J'Mari Taylor article](https://en.wikipedia.org/wiki/J%27Mari_Taylor) currently covers only his college career (through Virginia 2025) and has not been updated with NFL info — treated as lagging, not contradictory; the four sources above settle his NFL status.

---

## Conflicts, uncertainty, and how they were resolved

1. **Keon Coleman trade rumors (Jan–Apr 2026):** Real rumors, real trade inquiries — resolved by on-record GM statement (2026-04-27) refusing them and by his presence on the live BUF roster page. **Confirmed fact: no transaction.** Rumor ≠ move.
2. **Jonathan Taylor "trade" headlines (July 2026):** ESPN *bold-predictions* content, explicitly hypothetical; the article itself affirms he is a Colt. **Confirmed fact: no transaction.** Contract (Spotrac) binds him to IND through 2026.
3. **Expected origins of the two movers (task expectation: "Buffalo → Miami" and "Indianapolis → Jacksonville") vs. reality:** Both destination teams check out exactly; both origins are refuted. Kevin Coleman Jr. and J'Mari Taylor are 2026 **league entrants** (R5 pick #177 / UDFA), not intra-NFL movers. This is stated as verified fact (team-site acquisition records + career registries), not inference. **Action item for the dataset:** ensure the corrected records do not book any 2025 Buffalo/Indianapolis volume as "vacated by" these two players — the collision's phantom moves must be deleted, not merely re-attributed.
4. **No unresolved uncertainty remains** on the single question asked (each player's 2026 team). All four are corroborated by ≥3 independent sources, at least one of which is a team-primary source in every case.

## Self-critique gap round (log)

- **Gap:** initial Bills/ESPN pages showed 2025-season data without an explicit 2026-dated statement for Keon Coleman. → **Closed** with NFL.com articles dated 2026-04-27 and 2026-05-19.
- **Gap:** possibility of a brief, unreported Buffalo stint for Kevin Coleman Jr. (e.g., UDFA-then-waived path). → **Closed:** he was in college (Missouri) in 2025 and drafted by Miami in April 2026; targeted BUF-transaction search returned nothing; Wikipedia/team bio list no prior NFL team. Impossible timeline for a BUF stint.
- **Gap:** possibility J'Mari Taylor signed with Indianapolis post-draft and was waived/claimed by JAX. → **Closed:** jaguars.com states he was signed by Jacksonville as a UDFA on 4/26/26 (the weekend the draft ended); SI report of the same date says he signed with JAX; PFR shows JAX as his only team; targeted Colts search returned nothing.
- **Gap:** "Dolphins sign Coleman to futures contract" headline could imply another Coleman transaction muddying the picture. → **Closed:** that is LB **Seth** Coleman (2026-01-21), a different player.
- **Gap:** Spotrac page for J'Mari Taylor returned HTTP 403 (single failed fetch). → **Mitigated:** contract/acquisition corroborated instead by jaguars.com (primary), SI, ESPN, and PFR. No claim in this document rests on the unfetched page.
- **Gap:** Wikipedia lag on J'Mari Taylor's NFL status. → **Noted explicitly** as a lagging source; not used for any NFL-status claim.
- **Contradictions found:** none on 2026 team assignments. Speculative trade content for both stars identified and classified as non-transactions.

## Method

Searches and fetches executed 2026-07-05 against team sites (buffalobills.com, miamidolphins.com, colts.com, jaguars.com), league media (NFL.com), contract registries (Spotrac), career registries (Pro-Football-Reference, ESPN), wire services (UPI), and credentialed beat/team outlets (SI team sites). Forums/social media were not used as evidence. Every 2026 fact above is post-training-cutoff and was web-verified; nothing rests on model priors.
