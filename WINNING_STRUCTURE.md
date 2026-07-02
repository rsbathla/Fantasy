# WINNING_STRUCTURE.md
## How Large-Field Best Ball Tournaments Are Actually Won — a Target Roster Shape for a Draft-Strategy Engine

**Scope:** Underdog Best Ball Mania (BBM) and comparable large-field best-ball tournaments. 18-round rosters, 12-team drafts, regular season Weeks 1-14, then three single-week elimination rounds (Weeks 15, 16, 17) with Week 17 as the winner-take-most final.

**Honesty note (read first):** Every quantitative claim below is tagged **[SOURCED]** with the URL it came from, or **[PRINCIPLE]** for community reasoning I could not tie to a retrieved statistic. Numbers are only as good as the source that published them; several key studies come from a single analyst (ETR's Mike Leone, RotoViz's Dubner) on a single tournament-year, and I flag that. Where I could not reach data (paywalls, JS-only tools), I say so in the "What I could NOT source" section rather than inventing a figure.

---

## 1. EXECUTIVE "TARGET SHAPE" SPEC (the objective a builder can encode)

This is the roster the data + principle consensus points toward. Treat each line as an objective term; the tag tells you how much weight the evidence supports.

| Element | Target | Confidence |
|---|---|---|
| **Positional counts (18 roster spots)** | **2-3 QB / 5-6 RB / 6-7 WR / 2-3 TE** | [SOURCED] — this exact envelope recurs across every winning-roster breakdown and positional study retrieved |
| **QB count & timing** | **2 or 3 QB, taken LATE** (target the "QB window," roughly ADP ~85-116 / Rounds ~8-13; zero QB before ~Round 6-8). 3-QB only if the extra QB is game-stacked. | [SOURCED] |
| **RB count & floor rule** | **5-6 RB.** Do NOT go fully Zero-RB in early drafts — **have RB1 by ~Round 7 at the absolute latest**; minimum 2 RB through Round 5. Hero-RB (one anchor RB early) is well-supported. | [SOURCED] |
| **WR count & timing** | **6-7 WR** is the peak advance band. Push WR capital early — **4-5 WR by Round 7**. Quantity-over-quality at WR. | [SOURCED] |
| **TE count & timing** | **2-3 TE, taken late** (zero TE through ~Round 11, then acquire 2-3 in Rounds ~11-13). **Avoid paying elite (Round 1-4) TE prices** — they advance *below* average. | [SOURCED] |
| **Number of stacks** | **2-3 team stacks** (QB paired with his own pass-catchers). Winning rosters concentrate, they don't run one stack or zero. | [SOURCED] |
| **Pass-catchers per stack** | **~2 per stack (QB + 2)**; a QB+3 "triple stack" shows the single biggest regular-season advance bump but is harder to build. **1-3 stacked players per QB.** | [SOURCED] |
| **Distinct offenses concentrated on** | Concentrate correlation onto **~3-5 offenses** for stacks (a real BBM VI winner used 3 stacks across 5 stack-teams). This is NOT single-game "onslaught." | [SOURCED for the winning-roster example; PRINCIPLE for it being *optimal*] |
| **Bring-back stacks** | Optional, modest value. Same-game opposing WR correlation at ceiling is only **~+0.09 to +0.10**. Use for Week-17 game-stacks, don't over-weight. | [SOURCED] |
| **Ceiling vs floor / spike-week WRs** | Bias skill players toward **high-ceiling / spike-week** profiles, especially at WR. Direct win-rate proof is thin; the strongest hard evidence is the leverage effect (low-owned ceiling hits) rather than a clean "variance beats floor" study. | [PRINCIPLE], with [SOURCED] leverage support |
| **Leverage / contrarian** | Favor **low-rostered, high-ceiling** players. Retrieved data shows enormous advance-rate lifts when a rarely-drafted player hits (Kyren Williams **+2.08x**, Puka Nacua **+1.81x** playoff odds in BBM IV). | [SOURCED] |
| **Championship weeks (15-17)** | Build for **≥13-14 "live" (still-playing, non-zero) players in Weeks 15-17**; drop below that and EV roughly halves. In **Week 17**, run **~6-9 game-stacked players** across a few matchups. | [SOURCED] |
| **Draft-slot × build interaction** | Under-evidenced. No retrieved source cleanly quantifies advance rate by draft pick #. Treat pick-specific tuning as **[PRINCIPLE]** (early picks → anchor RB/WR available; turns/late → easier to start WR/Zero-RB-lean) until better data is found. | **NOT SOURCED** — see open questions |

**One-line encodable objective:** *Maximize a roster of ~2-3 QB / 5-6 RB / 6-7 WR / 2-3 TE that (a) has RB1 by ~R7 and 4-5 WR by R7, (b) takes QBs and TEs late, (c) contains 2-3 QB-stacks of ~2 pass-catchers each across ~3-5 offenses, (d) skews skill players toward low-owned high-ceiling profiles, and (e) is engineered to keep ≥13-14 live players and 6-9 Week-17 game-stacked players into the finals.*

---

## 2. EVIDENCE BEHIND EACH ELEMENT

### 2.1 STACKING — does correlation actually lift advance/win rates?

**Yes, and it is one of the better-documented edges — but the magnitude is often overstated and comes with a "reaching" penalty.**

- **[SOURCED] Full advance-rate ladder by stack type** (PlayerProfiler / David Zacharias, using Underdog BBM data; baseline Round-1 advance ≈ 16.7%):
  - Zero stacks: **15.8%**
  - One skinny stack (QB + 1): **16.8%**
  - One double stack (QB + 2): **17.2%**
  - One triple stack (QB + 3): **19.4%**
  - Two skinny stacks: **17.9%**
  - Two double stacks: **19.8%**
  - Three skinny stacks: **20.8%**
  - **Reaching penalty:** if you draft the stack pieces *above their ADP*, it flips negative — one skinny stack reached = **11.9%**, one triple stack reached = **5%**. Source: https://www.playerprofiler.com/article/the-complete-guide-to-stacking-in-best-ball/
  - **Interpretation:** correlation helps, but a large chunk of the raw "stackers advance more" signal is confounded by *good, value-priced* players. Stack when the pieces come at or below ADP; don't burn draft capital forcing it.

- **[SOURCED] QB↔teammate correlation coefficients** (same PlayerProfiler piece): QB1→WR1 **0.43**, QB1→WR2 **0.30**, QB1→TE1 **0.27**, QB1→WR3 **0.25**, QB1→RB2 **0.15**, QB1→RB1 **−0.04**. → Stack QBs with WR1/WR2/TE1; the RB is essentially uncorrelated with his own QB. Source: https://www.playerprofiler.com/article/the-complete-guide-to-stacking-in-best-ball/

- **[SOURCED] Finals-level lift:** RotoViz's Michael Dubner found ~10,000 teams with a QB1-WR1-WR2 correlation advanced to the **finals at 2.6x** the expected rate (2023 BBM). Source (reporting Dubner): https://www.fantasylife.com/articles/best-ball/stacking-in-best-ball

- **[SOURCED] Week-17 game-stack lift:** ETR's Mike Leone (BBM III data): the ability to win a ~470-person final field can **increase ~50%** by game-stacking in Week 17, with **6-9 total game-stacked players** ideal. Sources: https://www.fantasylife.com/articles/best-ball/stacking-in-best-ball and https://establishtherun.com/strategy-how-to-win-underdogs-best-ball-mania/

- **[SOURCED] Skeptical counterweight:** One Week Season argues stacking can *reduce* a best-ball roster's spike-week upside vs. taking the best available uncorrelated players, using 2020 examples (Cousins/Thielen/Jefferson stack produced fewer combined WR1 weeks than some uncorrelated WR pairs). This is anecdotal (single season, hand-picked pairs), **not** a win-rate refutation — but it is a legitimate flag that the naive "always stack" framing is oversold. Source: https://oneweekseason.com/exposing-the-fallacies-of-stacking-in-best-ball-and-redraft/

**How many stacks / how many pass-catchers:** Data supports **2-3 stacks** (three skinny stacks = the top of the regular-season ladder at 20.8%; two double stacks 19.8%). Per-QB, **1-3 stacked pass-catchers**; **QB+2 is the sweet spot** for buildability, QB+3 for max regular-season bump. [SOURCED: PlayerProfiler ladder above; ETR "1-3 stacked players per QB" https://establishtherun.com/strategy-how-to-win-underdogs-best-ball-mania/]

### 2.2 CONCENTRATION — how many offenses; is "onslaught"/hyper-stacking real?

- **[SOURCED] Real winner shape:** The 2025 **Best Ball Mania VI winning roster** ran **3 primary stacks (all ≤3 players) across 5 stack-teams** — Saints (Olave/Shough/Juwan Johnson), 49ers (Kittle/Purdy), Panthers (McMillan/Young). It concentrated correlation onto a handful of offenses, NOT one game. Source: https://www.bestballteambuilder.com/2025-best-ball-mania-vi-winning-team/
- **[SOURCED] Field-level:** 3-QB (i.e., more-concentrated) builds have **outperformed 2-QB builds in 4 of 6 BBM years** per 4for4; and were used 35.57% of the time in BBM III. Sources: https://www.4for4.com/2026/preseason/how-winners-draft-quarterbacks-underdog-best-ball-mania and https://spikeweek.com/best-ball-tournaments-and-roster-construction-combinatorics/
- **[PRINCIPLE / NOT SOURCED] Single-game "onslaught" (5+ players from one game):** I found **no retrieved best-ball study** validating DFS-style single-game hyper-stacking as +EV in season-long best ball. The DFS "onslaught" concept exists (Steemit GPP primer) but does not transfer with evidence to this format. Treat single-game onslaught as **unsupported** for best ball; the supported form of "concentration" is *3-QB builds + 2-3 stacks + Week-17 game-stacks across a few matchups*.

**Skeptical flag:** the "3-QB is better" signal is genuinely year-dependent — see the 2021-vs-2022 reversal in §2.4. Concentration via extra QBs is a real but *unstable* edge.

### 2.3 CEILING vs FLOOR / SPIKE WEEKS

- **[PRINCIPLE] The mechanism is sound and near-universally stated:** best ball takes each player's best weekly outcomes, so weekly ceiling (spike weeks), not floor, is what scores; "you don't care about a player's floor." Sources (opinion/mechanism, no win-rate data attached): https://clubfantasyffl.com/2025/06/15/best-ball-fantasy-football-spike-weeks/ , https://www.playerprofiler.com/article/best-ball-tournament-strategy/
- **[SOURCED] The strongest *hard* evidence is via leverage, not a clean variance study:** rarely-drafted ceiling players that hit produce massive advance lifts — Kyren Williams **+2.08x**, Puka Nacua **+1.81x** playoff odds (BBM IV); only 406 of ~667k teams had both (1 in 1,668). Cooper Kupp (2021): **48% of rosters that had him made the BBM playoffs**. Sources: https://establishtherun.com/herzig-five-keys-to-winning-at-best-ball-2/ and https://www.thefantasyfootballers.com/articles/best-ball-101-win-rates-roster-construction-fantasy-football/
- **[SOURCED] Ceiling correlation is rare and additive:** only **1.1% of teams** had two WRs each score 20+ half-PPR in the same week, and WR1→WR2 same-team ceiling correlation is **+0.16** — i.e., own-team WR pairs spike together more than any other skill pairing, reinforcing WR-heavy stacking for ceiling. Source: https://underdognetwork.com/football/best-ball-research/correlation-at-ceiling-outcomes-between-teammates-and-their-opponents

**Skeptical flag:** I did **not** find a study that directly pits "high-variance WRs" vs "low-variance WRs" and reports differential win rates. The ceiling-over-floor thesis is mechanically correct and supported *indirectly* (leverage hits, spike-week rarity), but the clean head-to-head data is **not sourced**. Encode ceiling-bias as a strong prior, not a proven coefficient.

### 2.4 ONESIE LEVERAGE (QB / TE) — number and timing

**Quarterback:**
- **[SOURCED] Count:** 2 or 3 QB is optimal; **avoid 1 QB (esp. shared bye) — advanced <10% (BBM VI) vs 16.7% baseline**; avoid 4+. Same-bye-week QB pairs advanced only 14.5%. Source: https://www.4for4.com/2026/preseason/how-winners-draft-quarterbacks-underdog-best-ball-mania
- **[SOURCED] 2-QB vs 3-QB is YEAR-DEPENDENT (key skeptical point):** spikeweek's cross-year table — **2021: 2-QB 15.3% playoff / 3-QB 14.4%** (2-QB better); **2022: 2-QB 15.3% / 3-QB 17.4%** (3-QB better). 4for4 says 3-QB has won 4 of 6 years. So "3 QB is the skeleton key" is **overstated as a law** — it's a coin-flippy, correlation-dependent edge. The reconciling rule: **3-QB only pays when the extra QB is game-stacked.** Sources: https://spikeweek.com/best-ball-tournaments-and-roster-construction-combinatorics/ , https://www.4for4.com/2026/preseason/how-winners-draft-quarterbacks-underdog-best-ball-mania
- **[SOURCED] Timing / leverage:** waiting on QB has been the winning structural play — BBM VI's optimal was **zero QB through Round 13**; elite (R1-4) QBs advanced **14.3%, ~2.4% below average**. Late QBs let you spend early capital on RB/WR. Real BBM VI winner's QBs went **9.09, 13.09, 15.09** (all late). Sources: https://www.4for4.com/2026/preseason/how-winners-draft-quarterbacks-underdog-best-ball-mania , https://www.bestballteambuilder.com/2025-best-ball-mania-vi-winning-team/
  - *Caveat the source itself raises:* for a thin QB class, 4for4 suggests a mid-round "QB window" (~40% of ADP 85-116 are QBs) rather than punting to the last rounds. So "latest possible QB" is directional, not absolute.

**Tight End:**
- **[SOURCED] Count & timing:** **2-3 TE, late.** 3-TE builds have beaten 2-TE builds in regular-season points **6 straight years**; optimal was **zero TE through Round 11, then 3 TEs in Rounds 11-13.** Sources: https://www.4for4.com/2026/preseason/how-winners-draft-tight-ends-underdog-best-ball-mania , https://www.fantasypoints.com/... (Fantasy Footballers corroborates 3-TE ≈ 18% playoff advance: https://www.thefantasyfootballers.com/articles/best-ball-101-win-rates-roster-construction-fantasy-football/)
- **[SOURCED] Elite-TE leverage is NEGATIVE:** early elite TEs (Round 1-4) advanced **13.9% (≈3% below avg)**, finals **7.9%**; the whole position is dictated by a tiny number of players so single seasons (Kelce 2023) skew perceptions. The leverage play is *late TE-by-committee*, not paying up. Sources: https://www.4for4.com/2026/preseason/how-winners-draft-tight-ends-underdog-best-ball-mania , https://establishtherun.com/strategy-how-to-win-underdogs-best-ball-mania/

**Onesie leverage summary:** the edge is *structural* — punt both QB and TE, redeploy that capital into RB1-by-R7 + a WR-heavy early core, and take 2-3 of each onesie late. [SOURCED across the four "How Winners Draft" 4for4 pieces + real winner.]

### 2.5 BUILD ARCHETYPES (Zero-RB / Hero-RB / Robust-RB / WR-heavy) and advance rates

- **[SOURCED] Early-RB capital advances BEST in the most recent studied year (BBM VI), reversing the older Zero-RB tilt:**
  - Round-1 RB: **~24% advance** vs ~12% for zero-RB teams.
  - Two consecutive RBs (R1-2): **~30%** vs ~8% for skipping RB both rounds.
  - Early-round RBs (R1-3): **21.4% avg advance, 10.1% finals.**
  - Source concludes Zero-RB "rough" in BBM VI; **min 2 RB through Round 5.** Source: https://www.4for4.com/2026/preseason/how-winners-draft-running-backs-underdog-best-ball-mania
- **[SOURCED] But the hard floor is timing, not archetype label:** teams **without RB1 by Round 8 have been crushed in all 5 BBM seasons**; Zero-RB "peaked" R5-6 and craters if pushed later. Source: https://underdognetwork.com/football/best-ball-research/dont-be-dumb-when-you-draft-a-zero-rb-team-in-2025
- **[SOURCED] WR-heavy is a real edge, but avoid Round-1 WR (BBM VI):** avoiding a Round-1 WR **doubled playoff odds** vs taking one; only 3 of 16 top-3-round WRs beat average (≈half the RB hit rate). Optimal early shape was **3 RB then 4 consecutive WR (R1-7)**. WR count: **6-7 WR ≈ 20% advance vs 9-10 WR 15.7%** (don't over-stuff WR). Sources: https://www.4for4.com/2026/preseason/how-winners-draft-wide-receivers-underdog-best-ball-mania , https://underdognetwork.com/football/best-ball-research/dont-be-dumb-when-you-draft-a-zero-rb-team-in-2025
- **[SOURCED] Robust-RB has intermittent support:** RotoViz ran a "Hope for Robust RB" BBM IV review; older RotoViz work ("RB Dead Zone Lives On") is behind a paywall so the exact percentages are **not retrievable**. Directionally, robust-RB is viable when early RBs stay healthy; it failed in years of heavy early-RB injuries. Sources (headline-level only, data paywalled): https://www.rotoviz.com/2023/11/hope-for-robust-rb-best-ball-mania-iv-advance-rate-review-week-10/ , https://www.rotoviz.com/2023/10/the-rb-dead-zone-lives-on-best-ball-mania-iv-advance-rate-model-review-week-4/
- **[SOURCED] Hero-RB is the archetype the most recent real winner used:** BBM VI champ = **one anchor RB (Derrick Henry R2) + WR-heavy + late onesies**. Source: https://www.bestballteambuilder.com/2025-best-ball-mania-vi-winning-team/

**Reconciliation for the engine:** don't hard-code an archetype. Encode the *timing constraints* the data actually supports — (i) RB1 by ~R7, ≥2 RB by R5; (ii) 4-5 WR by R7; (iii) lean away from paying Round-1 WR / elite TE / elite QB prices — and let Hero-RB and moderate Zero-RB-lean emerge from where value falls. **Skeptical flag:** Zero-RB's reputation is built on 2021-2023 injury-heavy years; the single most recent studied year (BBM VI) favored early RB. Archetype edges are regime-dependent.

### 2.6 CHAMPIONSHIP / PLAYOFF WEEKS (15-17) and Week 17

- **[SOURCED] "Live players" is the dominant playoff-week lever:** rosters with **<14 live players in Week 17 saw EV nearly halved**; **>14 nearly doubled** EV. Winner Pat Kerrane had **15 live players (≈57% better odds than random)**; the BBM winner example fielded **13-18 live in Week 15**. Build for survivorship (avoid too many players whose seasons/roles die). Sources: https://establishtherun.com/strategy-how-to-win-underdogs-best-ball-mania/ , https://www.thefantasyfootballers.com/... (via the ETR "how to win" piece)
- **[SOURCED] Week-17 game-stacking is the concentrated ceiling lever:** ~**+50% win-rate lift** in a ~470-team final via Week-17 game-stacks; **6-9 game-stacked players** ideal; **11+ was worse**; **2-5 ≈ neutral**; only **15% of finalists actually rostered the ideal 6-10** (i.e., an exploitable edge because the field under-does it). Sources: https://establishtherun.com/strategy-how-to-win-underdogs-best-ball-mania/ , https://www.fantasylife.com/articles/best-ball/stacking-in-best-ball
- **[SOURCED] 2-3 game-stacked QBs specifically:** teams with 2-3 game-stacked QBs showed a "serious advantage" in Week-17 EV; **three game-stacked QBs "23% more likely than random to reach the finals," zero game-stacked QBs "26% less likely."** Source: https://establishtherun.com/strategy-how-to-win-underdogs-best-ball-mania/
- **[SOURCED] Prize concentration justifies the Week-17 focus:** Underdog BBM VII pays **13.3% of the pool to the single winner** (FFPC 24.3% to the Week-17 champ) — the final week is where the money is, so late-round Week-17 correlation is worth planning at draft time. Sources: https://www.draftsharks.com/article/week-17-best-ball-tournament-stacks , https://fantasysixpack.net/2026-best-ball-week-17-correlation-stacking-strategy/
- **[SOURCED] Bring-back (opposing-team) correlation is modest at ceiling:** WR1→opposing WR1 **+0.09**, →opposing WR2 **+0.10**, RB1→opposing TE1 **+0.08** — real but small; when a WR1 goes 25+, the opposing top WR averages 17+ with >50% odds of 16+. Use bring-backs to complete Week-17 game-stacks, not as a primary driver. Source: https://underdognetwork.com/football/best-ball-research/correlation-at-ceiling-outcomes-between-teammates-and-their-opponents

**How you plan this at draft time (encodable):** prefer stack pieces whose real-life **Week-15/16/17 NFL matchups** pair up, so a natural game-stack exists in the final; keep enough "alive into December" players to clear the 13-14 live-player bar. [PRINCIPLE for the matchup-scheduling tactic; the live-player and game-stack thresholds are SOURCED.]

### 2.7 POSITIONAL ALLOCATION — where the leverage is

- **[SOURCED] Winning-roster count envelope, corroborated by multiple independent breakdowns:**
  - Fantasy Footballers (BBM III, 450k entries): **2-3 QB / 5-6 RB / 6-9 WR / 2-3 TE**; 2-QB **17.5%**, 5-6 RB **17.1%**, 3-TE **18%** advance. https://www.thefantasyfootballers.com/articles/best-ball-101-win-rates-roster-construction-fantasy-football/
  - ETR "Strategy: How to Win": 2-3 QB, **4-RB highest EV among finalists**, WR overrepresented (but 8+ WR underperforms), **3-4 TE over-advanced**, elite TE poor. https://establishtherun.com/strategy-how-to-win-underdogs-best-ball-mania/
  - ETR 2023 Year-in-Review real teams: **6RB/5WR/2QB/3TE** (BBM IV, 22nd of 667k) and **6RB/8WR/3QB/3TE** (DK). https://establishtherun.com/best-ball-year-in-review/
  - Underdog Network 5-year cumulative targets: through R18 → **QB 2-3, RB 5-6, WR 6-7, TE 2-3**; exactly 3 startable WR has beaten average all 5 years. https://underdognetwork.com/football/best-ball-research/what-has-worked-in-all-5-years-of-best-ball-mania
  - Real BBM VI winner: **3QB/6RB/7WR/2TE** (effectively 3/5/6/2 after two dead late picks). https://www.bestballteambuilder.com/2025-best-ball-mania-vi-winning-team/
- **[SOURCED] Where the *leverage* is:** the capital you save by punting QB and TE goes into a **deeper, higher-ceiling WR room + a secure early RB anchor**. Onesie draft capital (elite QB, elite TE) is where the field *overpays* and *under-advances* (elite QB 14.3%, elite TE 13.9%, both below the 16.7% baseline). https://www.4for4.com/2026/preseason/how-winners-draft-quarterbacks-underdog-best-ball-mania , https://www.4for4.com/2026/preseason/how-winners-draft-tight-ends-underdog-best-ball-mania

---

## 3. WHAT I COULD NOT SOURCE / OPEN QUESTIONS

1. **Advance/win rate by DRAFT SLOT (pick #).** No retrieved source cleanly quantifies how build archetype interacts with early vs turn vs late draft position. This is exactly what the pick-#-specific board wants and it is the biggest evidence gap. The board should treat slot-specific tuning as a **[PRINCIPLE]** derived from ADP availability (which players can actually be reached at each slot), not from a published advance-rate-by-slot table. **Recommend building this table in-house from Underdog draft data.**

2. **A clean "high-variance vs low-variance WR" win-rate study.** The ceiling-over-floor thesis is mechanically sound and supported *indirectly* (leverage hits, spike-week rarity), but I did not retrieve a head-to-head that isolates weekly variance and reports differential advance/win rates. Encode ceiling-bias as a prior, not a measured coefficient.

3. **RotoViz's expected-advance-rate model numbers (Jake Boes / Dubner) are paywalled.** The exact Zero-RB / Hero-RB / Robust-RB advance-rate curves and the per-player expected-advance visualizations were behind a RotoViz membership wall; I could only retrieve headline framing and the 16.67% baseline. https://www.rotoviz.com/2023/10/the-rb-dead-zone-lives-on-best-ball-mania-iv-advance-rate-model-review-week-4/

4. **4for4's Advance Rate Explorer is a JS/iframe tool** (https://apps.4for4.com/UD_Player_Explorer/); WebFetch only returned the base rates (16.7% advance 2021-22, 20.8% in 2020), not the interactive stack/position breakdowns. Would need browser automation to pull those tables.

5. **ETR "Optimal Position Allocation" simulation tables** are referenced ("we simulated the Week 17 Finals...The results:") but the actual EV/win-rate/top-10 numbers were not rendered in the fetched text. https://establishtherun.com/underdog-fantasy-best-ball-optimal-position-allocation/

6. **Single-source / single-year risk.** Several load-bearing magnitudes trace to one analyst on one tournament-year: the "~50% Week-17 game-stack lift" and "6-9 game-stacked players" are Mike Leone on **BBM III**; the "2.6x QB1-WR1-WR2 finals lift" is Dubner on **2023 BBM**. Directionally consistent with everything else, but not independently replicated in what I retrieved. Do not treat these exact percentages as stable constants across years.

7. **"Onslaught"/single-game hyper-stacking in best ball: no supporting data found.** The concept is real in DFS; I found no best-ball study validating 5+-from-one-game concentration as +EV. Flagged as unsupported for this format.

---

### Source list (retrieved)
- ETR — Strategy: How to Win Underdog's Best Ball Mania: https://establishtherun.com/strategy-how-to-win-underdogs-best-ball-mania/
- ETR — Herzig: Five Keys to Winning at Best Ball (2026): https://establishtherun.com/herzig-five-keys-to-winning-at-best-ball-2/
- ETR — Best Ball Year in Review 2023: https://establishtherun.com/best-ball-year-in-review/
- ETR — Optimal Position Allocation (tables not rendered): https://establishtherun.com/underdog-fantasy-best-ball-optimal-position-allocation/
- PlayerProfiler — Complete Guide to Stacking (advance ladder + correlations): https://www.playerprofiler.com/article/the-complete-guide-to-stacking-in-best-ball/
- PlayerProfiler — Best Ball Tournament Strategy (opinion only): https://www.playerprofiler.com/article/best-ball-tournament-strategy/
- Fantasy Life — Understanding Stacking (Dubner 2.6x; Leone ~50%): https://www.fantasylife.com/articles/best-ball/stacking-in-best-ball
- 4for4 — How Winners Draft QBs / RBs / WRs / TEs (BBM VI):
  - https://www.4for4.com/2026/preseason/how-winners-draft-quarterbacks-underdog-best-ball-mania
  - https://www.4for4.com/2026/preseason/how-winners-draft-running-backs-underdog-best-ball-mania
  - https://www.4for4.com/2026/preseason/how-winners-draft-wide-receivers-underdog-best-ball-mania
  - https://www.4for4.com/2026/preseason/how-winners-draft-tight-ends-underdog-best-ball-mania
- 4for4 — Advance Rate Explorer (base rates only): https://www.4for4.com/underdog/advance-rate-explorer
- Underdog Network — What Has Worked in All 5 Years of BBM: https://underdognetwork.com/football/best-ball-research/what-has-worked-in-all-5-years-of-best-ball-mania
- Underdog Network — Don't Be Dumb Drafting Zero RB 2025: https://underdognetwork.com/football/best-ball-research/dont-be-dumb-when-you-draft-a-zero-rb-team-in-2025
- Underdog Network — Correlation at Ceiling Outcomes (teammate + bring-back coefficients): https://underdognetwork.com/football/best-ball-research/correlation-at-ceiling-outcomes-between-teammates-and-their-opponents
- Spikeweek — Roster Construction Combinatorics (2021-22 QB advance table): https://spikeweek.com/best-ball-tournaments-and-roster-construction-combinatorics/
- Spikeweek — Secrets Behind 2 Top BBM Finishes (Zero-RB winner examples): https://spikeweek.com/the-secrets-behind-2-top-best-ball-mania-finishes/
- Fantasy Footballers — Best Ball 101: Win Rates & Roster Construction (BBM III counts): https://www.thefantasyfootballers.com/articles/best-ball-101-win-rates-roster-construction-fantasy-football/
- BestBallTeamBuilder — 2025 BBM VI Winning Team full breakdown: https://www.bestballteambuilder.com/2025-best-ball-mania-vi-winning-team/
- Fantasy Points — Successful QB Strategies in Large Best Ball Tournaments (2021 anecdotal): https://www.fantasypoints.com/nfl/articles/2022/successful-qb-strategies-in-large-best-ball-tournaments
- One Week Season — Exposing the Fallacies of Stacking (skeptic): https://oneweekseason.com/exposing-the-fallacies-of-stacking-in-best-ball-and-redraft/
- ClubFantasy — Draft for Spike Weeks (mechanism, opinion): https://clubfantasyffl.com/2025/06/15/best-ball-fantasy-football-spike-weeks/
- DraftSharks — Where Best Ball Tournaments Are Won / Week-17 stacks (prize concentration): https://www.draftsharks.com/article/week-17-best-ball-tournament-stacks
- Fantasy Six Pack — 2026 Week 17 Correlation & Stacking (prize structure): https://fantasysixpack.net/2026-best-ball-week-17-correlation-stacking-strategy/
- RotoViz — RB Dead Zone / Hope for Robust RB (paywalled, headline only): https://www.rotoviz.com/2023/10/the-rb-dead-zone-lives-on-best-ball-mania-iv-advance-rate-model-review-week-4/ , https://www.rotoviz.com/2023/11/hope-for-robust-rb-best-ball-mania-iv-advance-rate-review-week-10/
