# PERSONNEL.md / personnel_changes.json — STALENESS AUDIT (2026-07-05)

**Scope:** every roster claim in `PERSONNEL.md` + `personnel_changes.json` (identical content — the .md renders the .json) that (a) moves personnel groupings (TE/FB), or (b) is leaned on by `personnel_2026_projection.json`. Every verdict below is web-verified against dated 2026 sources; nothing is graded from training priors. Follows up `PERSONNEL_2026_VERIFICATION.md` (the pass that caught Juszczyk).

**Scoreboard: 43 file claims checked → 17 STALE-OR-WRONG (7 false departures, 3 name collisions, 7 wrong destinations), 26 CORRECT.**
Plus two systemic defect classes that aren't "claims" but corrupt the same buckets: **11 missing arrivals/rookies** that the 2026 projections lean on, and **7 veterans misfiled as "rookies."**

**Root causes (both mechanical, both fixable):**
1. **`dest: "gone"` = "absent from the 2026 ADP board", not "left the roster."** FBs and blocking TEs never carry ADP, so they read as departed even when under contract. This single mechanism produced all 7 false departures — 6 of them TE/FB, the exact positions that drive 12/13/21/22 personnel.
2. **Departure rows key on first-initial + surname.** Same-initial teammates/brothers collide: K.Coleman (Keon/Kevin), J.Taylor (Jonathan/J'Mari), T.Etienne (Travis/Trevor). The star's target share gets stapled to the depth player's destination.
The antidote already exists in-repo: `audit_roster_moves.py`'s canonical join + curated registries (`ROSTER_MOVES_2026.md` had 10/10 of its news-sourced destinations confirmed by this audit). `personnel_changes.json` should be rebuilt through that join.

---

## A. FALSE DEPARTURES — flagged "gone", actually ON the 2026 roster (Juszczyk class)

| # | File claim | Verdict | Correction (source, date) |
|---|---|---|---|
| A1 | **SF: K.Juszczyk (FB, 5.5% tgt) → gone** | **STALE-WRONG** (known) | On SF 2026 roster, 14th season. Artifact of Mar-2025 cut-then-re-sign, 2-yr deal through 2026 ([NBC Bay Area, 2026-06-13](https://www.nbcsportsbayarea.com/nfl/san-francisco-49ers/kyle-juszczyk-retirement-plans/1943209/); [ESPN, Mar 2025 re-sign](https://www.espn.com/nfl/story/_/id/44261853/source-49ers-bring-back-fb-kyle-juszczyk-two-year-deal)). Projection already corrected to HOLD. |
| A2 | **CAR: M.Evans (TE Mitchell Evans, 5.0%) → gone** | **STALE-WRONG** | On CAR 2026 roster ([panthers.com roster page](https://www.panthers.com/team/players-roster/mitchell-evans/), [ESPN player page](https://www.espn.com/nfl/player/_/id/4683243/mitchell-evans), both live 2026-07-05). 2025 5th-rounder; never left. |
| A3 | **DET: B.Wright (TE Brock Wright, 4.0%) → gone** | **STALE-WRONG** | Under contract with DET through 2026 — 2024–26 extension signed 2024-04-03, $3.31M 2026 base, UFA only after 2026 ([Spotrac contract page](https://www.spotrac.com/nfl/player/_/id/72851/brock-wright), accessed 2026-07-05; [ESPN player page](https://www.espn.com/nfl/player/_/id/4242392/brock-wright) = DET #89). |
| A4 | **MIN: J.Oliver (TE Josh Oliver, 4.1%) → gone** | **STALE-WRONG** | Signed a 3-yr, $23.25M **extension** with MIN in June 2025 ([ESPN](https://www.espn.com/nfl/story/_/id/45485798/vikings-sign-te-josh-oliver-3-year-2325-contract-extension); [Star Tribune](https://www.startribune.com/vikings-tight-end-josh-oliver-contract-extension-minicamp-nfl-news/601365967)); on the [2026 Vikings roster](https://www.vikings.com/team/players-roster/josh-oliver/splits/2026/reg/). |
| A5 | **ARI: E.Higgins (TE Elijah Higgins, 6.0%) → gone** | **STALE-WRONG** | On ARI 2026 roster — team offseason profile published for 2026 ([Yahoo/Cards Wire ARI TE 2026 offseason profile](https://sports.yahoo.com/articles/arizona-cardinals-te-elijah-higgins-122811508.html); [azcardinals.com roster](https://www.azcardinals.com/team/players-roster/elijah-higgins/), live 2026-07-05). |
| A6 | **LAR: D.Allen (TE Davis Allen, 4.7%) → gone** | **STALE-WRONG** | On LAR 2026 90-man roster, competing in a "crowded tight end room" ([SI Rams 90-man preview, 2026](https://www.si.com/nfl/rams/onsi/rams-davis-allen-roster-preview-2026); [therams.com roster](https://www.therams.com/team/players-roster/davis-allen/)). Matters: LAR is the league's #1 13-personnel team — TE bodies are the projection's premise. |
| A7 | **NYJ: J.Ruckert (TE Jeremy Ruckert, 6.9%) → gone** | **STALE-WRONG** | **Extended** by NYJ, 2-yr/$10M ([ESPN](https://www.espn.com/nfl/story/_/id/47334852/source-jets-extend-te-jeremy-ruckert-2-year-10m-deal), late 2025); on NYJ 2026 roster, #89 ([NFL.com player page](https://www.nfl.com/players/jeremy-ruckert/), accessed 2026-07-05; [newyorkjets.com, 2026-01-09](https://www.newyorkjets.com/news/jets-jeremy-ruckert-feel-we-have-the-right-pieces-01-09-2026)). |

**6 of 7 are TE/FB.** Exactly the failure mode the SF projection hit.

## B. NAME COLLISIONS — star's share stapled to a depth player's move

| # | File claim | Verdict | Correction (source, date) |
|---|---|---|---|
| B1 | **BUF: K.Coleman (12.2%) → MIA** | **WRONG — collision** | **Keon** Coleman is on BUF ([NFL.com player page](https://www.nfl.com/players/keon-coleman/), accessed 2026-07-05; [NFL.com — Beane "shut down trade interest… His best year is yet to come"](https://www.nfl.com/news/bills-gm-brandon-beane-shut-down-trade-interest-in-wr-keon-coleman-his-best-year-is-yet-to-come)). The BUF→MIA mover is **Kevin Coleman Jr.** (depth WR; repo cross-source consensus). BUF's true vacated volume ≈ 4.6%, not 16.8%. |
| B2 | **IND: J.Taylor (9.4%) → JAX** | **WRONG-AS-DISPLAYED — collision** | **Jonathan** Taylor is on IND ([colts.com roster](https://www.colts.com/team/players-roster/jonathan-taylor/); [colts.com — named to 2026 Pro Bowl](https://www.colts.com/news/colts-running-back-jonathan-taylor-guard-quenton-nelson-2026-pro-bowl); [Yahoo 2026 Colts RB preview](https://sports.yahoo.com/articles/colts-rb-preview-jonathan-taylor-110049940.html)). The IND→JAX mover is **J'Mari** Taylor (repo consensus). File contradicts itself: same team's beneficiaries list Jonathan Taylor (11.8% tgt) staying. |
| B3 | **JAX: T.Etienne (9.1%) → CAR** | **WRONG — collision** | Two Etiennes left JAX: **Travis** Etienne Jr. signed with **NO** ([ESPN, Mar 2026](https://www.espn.com/nfl/story/_/id/48154728/source-ex-jaguars-rb-travis-etienne-jr-sign-saints); [neworleanssaints.com](https://www.neworleanssaints.com/news/travis-etienne-jr-running-back-nfl-free-agency-2026-saints-roster-moves)); **Trevor** Etienne went to **CAR** (repo consensus). The row fuses Travis-sized share with Trevor's destination; JAX departures are missing one Etienne either way. |

## C. WRONG DESTINATIONS — really left, but "gone" hides a signing the league-wide picture needs

| # | File claim | Verdict | Correction (source, date) |
|---|---|---|---|
| C1 | **CHI: D.Moore (16.0%) → gone** | **WRONG DEST** | Traded to **BUF** for a mid-round pick ([NFL.com](https://www.nfl.com/news/bears-trading-wr-dj-moore-to-bills-for-mid-round-draft-pick); [ESPN, Mar 2026](https://www.espn.com/nfl/story/_/id/48111983/bills-agree-trade-acquire-bears-wr-dj-moore-sources-say); [buffalobills.com official](https://www.buffalobills.com/news/buffalo-bills-officially-acquire-wide-receiver-dj-moore-from-bears-via-trade)). |
| C2 | **TB: M.Evans (11.4%) → gone** | **WRONG DEST** | Signed with **SF**, ending 12-year TB tenure ([NFL.com](https://www.nfl.com/news/mike-evans-to-sign-with-49ers-ending-12-year-tenure-with-buccaneers); [ESPN, Mar 2026](https://www.espn.com/nfl/story/_/id/48155046/star-wr-mike-evans-leaving-buccaneers-sign-49ers)). |
| C3 | **KC: M.Brown (13.4%) → gone** | **WRONG DEST** | Signed with **PHI**, 1-yr up to $6.5M ([NFL.com](https://www.nfl.com/news/marquise-brown-eagles-sign-wr-one-year-deal); [NBC PFT](https://www.nbcsports.com/nfl/profootballtalk/rumor-mill/news/eagles-sign-wide-receiver-marquise-hollywood-brown)). |
| C4 | **NYG: D.Bellinger (5.3%) → gone** | **WRONG DEST** | Signed with **TEN** ([tennesseetitans.com](https://www.tennesseetitans.com/news/titans-sign-tight-end-daniel-bellinger); [ProFootballRumors, 2026-03](https://www.profootballrumors.com/2026/03/titans-to-sign-te-daniel-bellinger)). TEN's own 12-up projection cites this signing — and TEN's arrivals bucket doesn't have him (see E2). |
| C5 | **NE: A.Hooper (TE, 5.5%) → gone** | **WRONG DEST** | Signed with **ATL** ([atlantafalcons.com](https://www.atlantafalcons.com/news/atlanta-falcons-sign-te-austin-hooper); [98.5 The Sports Hub, 2026-03-09](https://985thesportshub.com/2026/03/09/patriots-tight-end-signs-elsewhere-in-free-agency-austin-hooper/)). Strengthens ATL's 12-up call; missing from ATL arrivals (E3). |
| C6 | **MIA: J.Hill (TE Julian Hill, 4.5%) → gone** | **WRONG DEST** | Signed with **NE**; now on IR, out for 2026 ([Boston Globe, 2026-06-02](https://www.bostonglobe.com/2026/06/02/sports/julian-hill-patriots-injured-reserve/); [boston.com, 2026-06-01](https://www.boston.com/sports/new-england-patriots/2026/06/01/new-england-patriots-injury-update-julian-hill-nfl-football-tight-end/)). This injury is the stated premise of NE's mild-down (more-11) projection. |
| C7 | **CLE: J.Ford (RB Jerome Ford, 6.1%) → gone** | **WRONG DEST** | Signed 1-yr with **WAS** ([commanders.com](https://www.commanders.com/news/commanders-sign-jerome-ford); [wusa9](https://www.wusa9.com/article/sports/nfl/washington-commanders/commanders-sign-jerome-ford-from-cleveland-browns/65-7ffc04de-e025-48fe-98b2-398bac7039dc)). Missing from WAS arrivals (E8). |

*Label nit (same bucket, lesser sin):* **MIA: T.Hill → gone** and **LAC: K.Allen → gone** should read **FA** — Tyreek was released ([NFL.com](https://www.nfl.com/news/dolphins-releasing-five-time-all-pro-wr-tyreek-hill); [ESPN, Feb 2026](https://www.espn.com/nfl/story/_/id/47948025/miami-dolphins-cut-tyreek-hill-answering-biggest-questions-injury-whats-next)) and unsigned ([FantasyLife, 2026-03-18](https://www.fantasylife.com/articles/fantasy/best-remaining-unsigned-nfl-free-agents-deebo-samuel-stefon-digg)); Keenan Allen's deal expired and he's unsigned ([PFN, June 2026](https://www.profootballnetwork.com/why-keenan-allen-free-agent-remains-unsigned-nfl-offseason-june-2026/)). The file uses "FA" for identical cases (Diggs, Ertz, Waller).

## D. WEB-CONFIRMED CORRECT (the claim held up)

| File claim | Confirmation (source, date) |
|---|---|
| BAL: I.Likely (8.8%) → NYG | [giants.com](https://www.giants.com/news/isaiah-likely-signing-2026-nfl-free-agency-baltimore-ravens-john-harbaugh-tight-end-coastal-carolina); [ESPN](https://www.espn.com/nfl/story/_/id/48173860/new-york-giants-free-agency-acquisition-isaiah-likely-reshapes-offense-baltimore-ravens-john-harbaugh); [baltimoreravens.com](https://www.baltimoreravens.com/news/isaiah-likely-signing-new-york-giants-ravens-free-agent-tight-end) (Mar 2026) |
| CLE: D.Njoku (9.1%) → LAC | [chargers.com](https://www.chargers.com/news/david-njoku-justin-herbert-free-agency-contract); [NFL.com](https://www.nfl.com/news/nfl-network-chargers-agree-to-terms-with-te-david-njoku) (Mar 2026) |
| LAC arrival: Charlie Kolar (BAL) | [chargers.com agree-to-terms](https://www.chargers.com/news/agree-to-terms-charlie-kolar-2026); [Heavy — 3yr/$24.3M](https://heavy.com/sports/nfl/los-angeles-chargers/chargers-sign-charlie-kolar-three-years/) |
| DET arrival: Tyler Conklin (LAC) | [Pride of Detroit](https://www.prideofdetroit.com/detroit-lions-news/159527/detroit-lions-signing-veteran-tight-end-tyler-conklin) (1-yr; their analysis: "opens door for 13 personnel packages") |
| CIN: N.Fant (6.7%) → NO | [neworleanssaints.com agree-to-terms](https://www.neworleanssaints.com/news/noah-fant-tight-end-nfl-free-agency-2026-saints-roster-moves) (2026 FA) |
| TEN: C.Okonkwo (15.5%) → WAS | [commanders.com — 3-yr deal](https://www.commanders.com/news/commanders-sign-te-chig-okonkwo); [Hogs Haven](https://www.hogshaven.com/nfl-free-agency/405025/washington-commanders-free-agency-commanders-agree-to-three-year-deal-with-te-chig-okonkwo) |
| WAS: Z.Ertz (16.7%) → FA | Unsigned late offseason ([PFN](https://www.profootballnetwork.com/why-is-zach-ertz-still-a-free-agent-why-the-3-time-pro-bowler-remains-unsigned-late-in-nfl-offseason/)); plans to play, torn-ACL clearance ~Wk1 ([NFL.com, Feb 2026](https://www.nfl.com/news/zach-ertz-plans-to-play-in-2026-torn-acl-cleared-week-1)) |
| MIA: D.Waller (7.5%) → FA | Unsigned ([Heavy](https://heavy.com/sports/nfl/miami-dolphins/darren-waller-free-agent-news-ranking/); [PFN, Mar 2026](https://www.profootballnetwork.com/darren-waller-free-agency-march-2026/); MIA return "a long shot" — [SI](https://www.si.com/nfl/dolphins/onsi/news/why-agent-didn-t-close-door-on-waller-return-to-miami-and-why-it-s-a-long-shot-01kk93a2d1jt)) |
| PIT: J.Smith (Jonnu, 10.7%) → FA | Released by PIT, $7M cap save ([NFL.com](https://www.nfl.com/news/steelers-releasing-te-jonnu-smith-in-move-that-will-save-7m-on-salary-cap); still FA with reunion chatter — [SteelerNation, 2026-05-01](https://www.steelernation.com/2026/05/01/steelers-spark-backlash-jonnu-smith)) |
| NE: S.Diggs (20.4%) → FA | Released 2026-03-04 ([NFL.com](https://www.nfl.com/news/stefon-diggs-patriots-release-wr-one-season); [ESPN](https://www.espn.com/nfl/story/_/id/48102428/source-patriots-release-wr-stefon-diggs-one-season)); unsigned ([boston.com, 2026-05-11](https://www.boston.com/sports/new-england-patriots/2026/05/11/stefon-diggs-nfl-football-new-england-patriots-free-agency/)) |
| WAS: D.Samuel (22.9%) → FA | Contract voided ([NBC PFT](https://www.nbcsports.com/nfl/profootballtalk/rumor-mill/news/deebo-samuels-contract-voids-hell-count-12m-against-commanders-cap-and-hit-free-agency)); unsigned ([PFN](https://www.profootballnetwork.com/deebo-samuel-sr-free-agent-unsigned/); [ESPN remaining-FA fits, ~June 2026](https://www.espn.com/nfl/story/_/id/48751416/2026-nfl-best-team-fits-remaining-free-agents-samuel-bosa-diggs)) |
| BAL: D.Hopkins (9.5%) → FA | Unsigned, "not close to a deal" ([PFR, 2026-06](https://www.profootballrumors.com/2026/06/wr-deandre-hopkins-not-close-to-free-agent-deal); [PFN, June 2026](https://www.profootballnetwork.com/why-deandre-hopkins-free-agent-unsigned-nfl-offseason-june-2026/)) |
| MIA: J.Waddle (21.5%) → DEN | Draft-weekend trade incl. a 2026 1st ([NFL.com, Apr 2026](https://www.nfl.com/news/dolphins-trading-wr-jaylen-waddle-to-broncos-for-draft-picks-including-2026-first-rounder); [denverbroncos.com](https://www.denverbroncos.com/news/broncos-acquire-wr-jaylen-waddle-in-trade-with-dolphins)) |
| PHI: A.Brown (25.8%) → NE | Trade ([patriots.com](https://www.patriots.com/news/patriots-acquire-wr-a-j-brown-in-a-trade-with-the-philadelphia-eagles); [ESPN/Barnwell](https://www.espn.com/nfl/story/_/id/48912173/2026-nfl-offseason-aj-brown-trade-patriots-eagles-receiver-draft-picks-barnwell)) |
| GB: R.Doubs (19.4%) → NE | 4-yr deal ([NFL.com](https://www.nfl.com/news/romeo-doubs-patriots-sign-former-packers-wr-four-year-contract); [boston.com, 2026-03-12](https://www.boston.com/sports/new-england-patriots/2026/03/12/new-england-patriots-romeo-doubs-wide-receiver-green-bay-packers-free-agency/)) |
| IND: M.Pittman (19.2%) → PIT | Trade + 3-yr/$59M ext ([colts.com](https://www.colts.com/news/colts-acquire-2026-sixth-round-pick-in-trade-with-pittsburgh-steelers-for-wide-receiver-michael-pittman-jr-2026-seventh-round-pick); [NFL.com](https://www.nfl.com/news/michael-pittman-jr-trade-steelers-colts); [Post-Gazette, 2026-03-09](https://www.post-gazette.com/sports/steelers/2026/03/09/michael-pittman-trade-nfl-news-indianapolis-colts-pittsburgh/stories/202603090058)) |
| NYG: W.Robinson (28.5%) → TEN | 4-yr/$78M ([NFL.com](https://www.nfl.com/news/titans-signing-ex-giants-wr-wan-dale-robinson-to-four-year-78-million-deal)) |
| SEA: K.Walker (7.7%) → KC | 3-yr/$45M, SB LX MVP ([NFL.com](https://www.nfl.com/news/chiefs-signing-ex-seahawks-rb-kenneth-walker-iii-mvp-of-super-bowl-lx); [Fox News](https://www.foxnews.com/sports/super-bowl-mvp-kenneth-walker-misses-seahawks-ring-ceremony-signing-45m-deal-chiefs.amp)) |
| DET: D.Montgomery (5.3%) → HOU | Trade for OL Juice Scruggs + picks ([NFL.com](https://www.nfl.com/news/david-montgomery-trade-texans-lions-juice-scruggs); [ESPN](https://www.espn.com/nfl/story/_/id/48081713/sources-texans-trade-draft-pick-lions-rb-david-montgomery)) |
| HOU: C.Kirk (10.8%) → SF | [49ers Webzone, 2026-03-19](https://www.49erswebzone.com/articles/199826-offseason-juszczyk-excited-george-kittle/) (with Evans); repo cross-source consensus |
| SF: J.Jennings (16.7%) → MIN | 1-yr ([NFL.com](https://www.nfl.com/news/vikings-signing-ex-49ers-wr-jauan-jennings-to-one-year-8-million-deal); [ESPN](https://www.espn.com/nfl/story/_/id/48707658/vikings-jauan-jennings-agree-1-year-deal-worth-13m)) |
| SF: K.Bourne (9.1%) → ARI | repo cross-source consensus (dk+ffdataroma+clay+signals+features+flags); not independently news-verified |
| MIN: A.Thielen (7.7%) → gone | CORRECT — retired ([vikings.com official](https://www.vikings.com/news/adam-thielen-retirement-career-captain-munnerlyn-new-role-coaching); [NBC PFT — retirement deals for Thielen AND FB C.J. Ham](https://www.nbcsports.com/nfl/profootballtalk/rumor-mill/news/adam-thielen-c-j-ham-sign-retirement-deals-with-vikings)) |
| CAR: H.Renfrow (5.0%) → gone | CORRECT — released 2026-01-06 ([panthers.com](https://www.panthers.com/news/panthers-activate-david-moore-release-two-players-hunter-renfrow-demani-richardson); [WBTV, 2026-01-06](https://www.wbtv.com/2026/01/06/panthers-release-former-clemson-star-player-who-made-inspiring-nfl-comeback/)); no 2026 signing found |
| ATL arrival: Tua Tagovailoa (MIA) | 1-yr ([ESPN](https://www.espn.com/nfl/story/_/id/48156219/sources-qb-tua-tagovailoa-sign-1-year-deal-falcons); [NFL.com](https://www.nfl.com/news/falcons-to-sign-qb-tua-tagovailoa-to-one-year-minimum-contract)) |
| MIN arrival: Kyler Murray (ARI) | ARI release + MIN 1-yr min ([NFL.com](https://www.nfl.com/news/vikings-sign-kyler-murray-one-year-deal-release-cardinals); [PFR, 2026-03](https://www.profootballrumors.com/2026/03/cardinals-release-qb-kyler-murray)) |
| NYJ arrival: Geno Smith (LV) | Trade, late-round pick swap ([ESPN](https://www.espn.com/nfl/story/_/id/48164552/sources-jets-get-their-qb-trade-raiders-geno-smith); [newyorkjets.com, 2026-03-11](https://www.newyorkjets.com/news/jets-acquire-quarterback-geno-smith-trade-raiders-03-11-2026)) |
| NO arrival: Travis Etienne Jr. (JAX) | [ESPN, Mar 2026](https://www.espn.com/nfl/story/_/id/48154728/source-ex-jaguars-rb-travis-etienne-jr-sign-saints); [NFL.com](https://www.nfl.com/news/rb-travis-etienne-on-signing-with-hometown-saints-it-was-more-than-a-cherry-on-top) |
| NYJ rookie: TE Kenyon Sadiq | R1, #16 overall ([newyorkjets.com](https://www.newyorkjets.com/news/kenyon-sadiq-nfl-draft-tight-end-oregon); signed [2026-05-07](https://www.newyorkjets.com/news/kenyon-sadiq-signs-rookie-contract-05-07-2026)) |
| ARI rookie: RB Jeremiyah Love | #3 overall ([NFL.com](https://www.nfl.com/news/jeremiyah-love-cardinals-no-3-overall-pick-2026-nfl-draft); [azcardinals.com](https://www.azcardinals.com/news/cardinals-select-jeremiyah-love-in-first-round-of-2026-draft)) |
| LV rookie: QB Fernando Mendoza | #1 overall ([raiders.com](https://www.raiders.com/news/fernando-mendoza-no-1-overall-pick-raiders-quarterback-2026-nfl-draft-indiana-football); [ESPN](https://www.espn.com/nfl/story/_/id/48574585/raiders-take-fernando-mendoza-no-1-pick-nfl-draft)) |
| NO rookie: WR Jordyn Tyson | #8 overall ([NFL.com](https://www.nfl.com/news/2026-nfl-draft-saints-pick-arizona-state-wr-jordyn-tyson-with-no-8-overall-selection); [neworleanssaints.com](https://www.neworleanssaints.com/news/jordyn-tyson-saints-draft-pick-2026)) |
| Roster-present premises: Kyle Pitts (ATL), Tank Dell (HOU), Keon Coleman (BUF), Jonathan Taylor (IND) | Pitts: tag then 3-yr/$53M ext ([NFL.com tag](https://www.nfl.com/news/kyle-pitts-falcons-franchise-tag-tight-end); [atlantafalcons.com ext](https://www.atlantafalcons.com/news/atlanta-falcons-kyle-pitts-contract-extension)). Dell: on HOU, return not rushed ([click2houston, 2026-04-21](https://www.click2houston.com/sports/2026/04/21/texans-wont-rush-tank-dell-return-timeline-excited-to-see-tank-when-its-his-time-to-play-football/)). Coleman/Taylor: see B1/B2. |

## E. MISSING arrivals/rookies that 2026 personnel projections LEAN ON (file gaps, all web-confirmed real)

| # | Team bucket missing | The verified fact | Why it matters |
|---|---|---|---|
| E1 | **NYG arrivals: FB Patrick Ricard** | Signed w/ NYG ~2026-03-11 ([giants.com](https://www.giants.com/news/patrick-ricard-signed-2026-nfl-free-agency-john-harbaugh-baltimore-ravens-fullback-maine-pro-bowl-all-pro); [Big Blue View](https://www.bigblueview.com/new-york-giants-news/156641/patrick-ricard-signing-fullback-john-harbaugh-baltimore-ravens-nfl-free-agency)) | BAL-down AND NYG-up projections both cite Ricard; he exists only in brain quotes, not in the roster file |
| E2 | **TEN arrivals: TE Daniel Bellinger** | [tennesseetitans.com](https://www.tennesseetitans.com/news/titans-sign-tight-end-daniel-bellinger) (Mar 2026) | TEN 12-up projection's named enabler |
| E3 | **ATL arrivals: TE Austin Hooper** | [atlantafalcons.com](https://www.atlantafalcons.com/news/atlanta-falcons-sign-te-austin-hooper) (~2026-03-09) | Third veteran TE behind Pitts/Woerner — strengthens ATL 12-up |
| E4 | **HOU arrivals: TE Foster Moreau** | 2-yr/$6.3M ([click2houston, 2026-03-11](https://www.click2houston.com/sports/2026/03/11/source-texans-signing-veteran-tight-end-foster-moreau/); [ESPN](https://www.espn.com/nfl/story/_/id/48177372/source-ex-saints-te-foster-moreau-sign-texans)) | HOU 12-up projection's TE-investment leg |
| E5 | **HOU rookies: TE Marlin Klein** | R2 #59, Michigan ([houstontexans.com draft class](https://www.houstontexans.com/news/2026-houston-texans-full-draft-class)) | The "2nd-round TE" the projection cites |
| E6 | **LAC arrivals: FB Alec Ingold** | Released by MIA 3/6, LAC 2-yr/$7.5M ([ESPN, 2026-03-08](https://www.espn.com/nfl/story/_/id/48148992/chargers-agree-multiyear-deal-free-agent-alec-ingold)) | LAC 21-personnel projection's named enabler |
| E7 | **NO rookies: TE Oscar Delp** | R3 #73, Georgia ([neworleanssaints.com](https://www.neworleanssaints.com/news/oscar-delp-saints-draft-pick-2026)) | NO 12-up projection cites Delp by name |
| E8 | **WAS arrivals: RB Jerome Ford** | 1-yr ([commanders.com](https://www.commanders.com/news/commanders-sign-jerome-ford)) | Pairs with C7; WAS backfield math |
| E9 | **PHI arrivals: WR Marquise Brown** | 1-yr/$6.5M ([NFL.com](https://www.nfl.com/news/marquise-brown-eagles-sign-wr-one-year-deal)) | Mild counterweight to PHI's "third-WR case weakens" 12-up rationale |
| E10 | **DEN rookies: TE Justin Joly (R5), TE Dallen Bentley (R7)** | [ESPN, 2026-05-13](https://www.espn.com/nfl/story/_/id/48745630/denver-broncos-more-production-tight-ends-2026-season-justin-joly) | DEN TE-tilt rationale |
| E11 | **MIA arrivals: TE Ben Sims** | 1-yr, replaces Julian Hill ([SI/All Dolphins, 2026-03-16](https://www.si.com/nfl/dolphins/onsi/news/examining-what-could-or-might-not-happen-at-fullback-01kkt89xkvhm)) | MIA-down landing spot (H-back looks) |

*Also untracked anywhere: MIN FB C.J. Ham retired ([NBC PFT](https://www.nbcsports.com/nfl/profootballtalk/rumor-mill/news/adam-thielen-c-j-ham-sign-retirement-deals-with-vikings)) — a real FB subtraction the file never saw because Ham had no target share.*

## F. "Rookies" bucket misclassifications (veterans with no 2025 usage on the new team)

| Team | Listed as "rookie" | Reality |
|---|---|---|
| SF | Mike Evans | 12-year vet, FA signing (C2) |
| SF | Brandon Aiyuk | Veteran under contract; missed 2025 injured; **live July-2026 standoff w/ release chatter** ([ESPN, July 2026](https://www.espn.com/nfl/story/_/id/49002414/brandon-aiyuk-appears-imply-49ers-scared-release-him); [PFR, 2026-07](https://www.profootballrumors.com/2026/07/49ers-wr-brandon-aiyuk-lashes-out-at-commanders-qb-jayden-daniels)) — watch item for SF 11-personnel depth |
| BUF | DJ Moore | Veteran trade acquisition (C1) |
| MIA | Malik Willis | Veteran QB — Slowik's starter ([NFL.com](https://www.nfl.com/news/dolphins-oc-bobby-slowik-malik-willis-can-spin-the-ball-all-over-the-field)) |
| LAC | Keaton Mitchell | Veteran FA from BAL, 2-yr ([NFL.com](https://www.nfl.com/news/keaton-mitchell-chargers-adding-ex-ravens-speedster-mike-mcdaniel)) |
| HOU | Tank Dell | Veteran returning from injury (on HOU roster) |
| CAR | Jonathon Brooks | Veteran (2024 R2) returning from injury — not individually web-checked, classification flag only |

---

## Exact entries to fix

**`personnel_changes.json` (`teams.<TEAM>.offense`) — and the mirrored sentence in `PERSONNEL.md`:**

1. `SF.departures` — DELETE `{K.Juszczyk → gone}` (on roster; recompute `vac_tgt` 31.3 → ~25.8)
2. `CAR.departures` — DELETE `{M.Evans → gone}` (Mitchell Evans on roster; `vac_tgt` 20.0 → ~15.0)
3. `DET.departures` — DELETE `{B.Wright → gone}` (under contract thru 2026; `vac_tgt` 14.8 → ~10.8)
4. `MIN.departures` — DELETE `{J.Oliver → gone}` (extended thru 2027; `vac_tgt` 22.8 → ~18.7)
5. `ARI.departures` — DELETE `{E.Higgins → gone}` (on roster; `vac_tgt` 23.6 → ~17.6)
6. `LAR.departures` — DELETE `{D.Allen → gone}` (on 90-man; `vac_tgt` 4.7 → ~0)
7. `NYJ.departures` — DELETE `{J.Ruckert → gone}` (extended 2yr/$10M; `vac_tgt` 40.5 → ~33.6)
8. `BUF.departures` — REPLACE `{K.Coleman 12.2 → MIA}` with `{Kevin Coleman Jr. → MIA}` at his true (near-zero) share; Keon Coleman stays (`vac_tgt` 16.8 → ~4.6)
9. `IND.departures` — RENAME `J.Taylor` → `J'Mari Taylor` (and re-derive his true share; Jonathan Taylor must not read as departed)
10. `JAX.departures` — SPLIT `{T.Etienne → CAR}` into `{Travis Etienne Jr. → NO}` (the ~9% share) + `{Trevor Etienne → CAR}` (his true share)
11. `CHI.departures` — `D.Moore.dest`: gone → **BUF**
12. `TB.departures` — `M.Evans.dest`: gone → **SF**
13. `KC.departures` — `M.Brown.dest`: gone → **PHI**
14. `NYG.departures` — `D.Bellinger.dest`: gone → **TEN**
15. `NE.departures` — `A.Hooper.dest`: gone → **ATL**
16. `MIA.departures` — `J.Hill.dest`: gone → **NE (IR, out 2026)**
17. `CLE.departures` — `J.Ford.dest`: gone → **WAS**
18. `MIA.departures` — `T.Hill.dest`: gone → **FA**; `LAC.departures` — `K.Allen.dest`: gone → **FA**
19. ADD arrivals: `NYG` +Patrick Ricard (FB, BAL) · `TEN` +Daniel Bellinger (TE, NYG) · `ATL` +Austin Hooper (TE, NE) · `HOU` +Foster Moreau (TE, NO) · `LAC` +Alec Ingold (FB, MIA) · `MIA` +Ben Sims (TE, GB) · `WAS` +Jerome Ford (RB, CLE) · `PHI` +Marquise Brown (WR, KC)
20. ADD rookies: `HOU` +Marlin Klein (TE, R2/59) · `NO` +Oscar Delp (TE, R3/73) · `DEN` +Justin Joly (TE, R5), Dallen Bentley (TE, R7)
21. RECLASSIFY from `rookies` to `arrivals`: SF Mike Evans (TB) · BUF DJ Moore (CHI) · MIA Malik Willis (GB) · LAC Keaton Mitchell (BAL); tag SF Brandon Aiyuk / HOU Tank Dell / CAR Jonathon Brooks as `returning_vet`, not rookie
22. `SF` beneficiaries/prose — Kittle: add Achilles caveat (Wk1 game-time decision; Yahoo/49ersWebzone 5/26/26), already reflected in the projection

**`PERSONNEL.md` prose lines to rewrite (same facts as above):** ARI line 24 (drop E.Higgins-gone), BUF line 77 (Keon), CAR line 94 (drop M.Evans-gone), CHI line 111 (D.Moore→BUF), CLE line 145 (J.Ford→WAS), DET line 196 (drop B.Wright-gone), IND line 251 (J'Mari), JAX line 268 (Etienne split), KC line 285 (M.Brown→PHI), LAC line 302 (K.Allen→FA), LAR line 321 (drop D.Allen-gone), MIA line 358 (T.Hill→FA; J.Hill→NE), MIN line 377 (drop J.Oliver-gone), NE line 394 (A.Hooper→ATL), NYG line 428 (D.Bellinger→TEN), NYJ line 445 (drop J.Ruckert-gone), SF line 517 (drop Juszczyk-gone; Evans/Aiyuk not rookies), TB line 534 (M.Evans→SF); plus the arrival/rookie additions per E1–E11.

## Projection impact (what actually changes in `personnel_2026_projection.json`)

- **No 2026 heavy-direction call FLIPS** on these corrections — SF (the one that would have) was already fixed on 7/5.
- **Strengthened by corrections:** DET up (TE room = LaPorta + Conklin + **Wright**, not minus-Wright) · LAR hold (13P TE bodies incl. **Davis Allen** intact) · NYJ up (Sadiq R1 + Mason Taylor + **Ruckert extended**) · ARI hold/12-up (McBride + Reiman + **Higgins** intact) · ATL up (add **Hooper** to Pitts/Woerner) · MIN hold (keeps **Oliver**, its 12-personnel blocker — offsetting the untracked **C.J. Ham** retirement).
- **Verified premises (no change needed):** BAL down (Likely + Ricard gone — both confirmed) · LAC up (Njoku + Kolar + Ingold in) · WAS up (Okonkwo in / Ertz out) · TEN up (Bellinger real) · NO up (Fant + Delp real) · HOU up (Moreau + R2 Klein real) · NE down (Julian Hill IR confirmed) · MIA down (Waddle/Hill/Waller/Ingold exits confirmed).
- **Narrative-level fixes:** BUF vacated targets 16.8% → ~4.6% (Keon stays — any "vacated-volume" lift for BUF pass-catchers is overstated) · PHI 12-up is mildly softened by the missing Hollywood Brown arrival · SF Aiyuk standoff is a live 11-personnel watch item.

## Not checked (declared, per scope)

Low-share, personnel-neutral rows were not individually web-verified: ARI M.Carter/Z.Knight · ATL D.Sills · BUF T.Shavers · DEN L.Humphrey/T.Badie · NYJ I.Williams/J.Reynolds · WAS J.McNichols/C.Moore · NO K.Austin · PIT M.Valdes-Scantling · TEN V.Jefferson · TB S.Shepard · LV T.Lockett · NO B.Cooks · KC K.Hunt (FA per repo consensus) · the WR/RB arrival long tail carrying repo cross-source consensus (JuJu Smith-Schuster, C.Austin, Dortch, Bourne, Raymond, Dotson, Zaccheaus, Atwell, Tolbert, Westbrook-Ikhine, Nailor, Allgeier, Rodriguez, D.Brown, E.Wilson, Pacheco, Cousins, Fields, Gainwell, R.White, Wicks, Metchie, A.Mitchell) · true-rookie long tail (Branch, Brooks-class flags above excepted, Concepcion, Boston, J.Coleman, E.Johnson, Willis→see F, Lemon, Bernard, Price, Stribling, Tate, Singleton, A.Williams, O.Cooper). **Caution:** given the 7-for-7 false-positive rate on ADP-invisible "gone" players, treat every unchecked low-share "gone" as unverified, not as confirmed-departed.
