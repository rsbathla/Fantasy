# FantasyPoints Data Suite — Exhaustive Sweep Catalog

Banked player-split data pulled from the FantasyPoints Data Suite via your authenticated session 
(the page's own bearer header was reused, never read). Two seasons: **2024 and 2025**. 
Data lives under `NFL-master/FP/` (the 6 pipeline splits) and `NFL-master/FP_SWEEP/` (exploratory).

Each split file is one value of one filter dimension: `<dimension>/<value>.csv`, one row per player, 
with **all** FantasyPoints stat fields for that tool. Enum values are FP's internal codes (label mapping 
noted where known). `true` = the filter-on subset of a binary (the complement is the rest of the population).

---

## 1. Pipeline splits — `NFL-master/FP/` (validated, wired into the engine)

These six feed the Best Ball pipeline today and were verified against known player totals.

| Dimension | Tool | Parameter path | 2024 vals | 2025 vals |
|---|---|---|---|---|
| Receiving/CoverageType | Receiving | `$$play.defense.coverageScheme.parent (labels: Cover 0-6, Man Cover 2)` | 7 | 7 |
| Receiving/RouteType | Receiving | `$$play.pass.targetedRoute.parent (codes 0-9 = Screen/Flat/Slant/Comeback/Curl/Out/In/Corner/Post/Go)` | 10 | 10 |
| Passing/CoverageType | Passing | `$$play.defense.coverageScheme.parent` | 7 | 7 |
| Passing/TargetDirection_SD | Passing | `$$play.pass.depthOfTarget (between; Deep=20+, Short=<20)` | 2 | 2 |
| Rushing/RunType | Rushing | `$$play.offense.primaryConcept.playConceptId (codes 1-10 = Inside/Outside Zone, Man-Duo, Power, Counter, Trap, Triple Option, Draw, Trick-WR, Fullback)` | 9 | 10 |
| Rushing/RushDirectionPooled | Rushing | `$$play.rush.rushLocation.rushLocationId (codes 1-7 pooled -> End/Guard/Tackle/Center)` | 4 | 4 |

---

## 2. Passing sweep — QB (10 dimensions)

Banked under `NFL-master/FP_SWEEP/<year>/Passing/<dimension>/<value>.csv`.

| Dimension | Type | Parameter path | Values (2025) | Flag |
|---|---|---|---|---|
| dropbackType | enum | `$$play.pass.dropbackType.dropbackTypeId` | 1(76), 2(68), 3(57), 4(69), 5(69) | AttemptsTotal unreliable (codes 2,5) |
| outOfPocket | binary | `$$play.pass.outOfPocket` | true(71) |  |
| passLocation | enum (L/M/R x ...) | `$$play.pass.passLocation.passLocationId` | 1(68), 2(57), 3(70), 4(75), 5(72), 6(72) |  |
| passResult | enum | `$$play.pass.passResult.passResultId` | 1(75), 2(75), 3(61), 4(68), 5(66) |  |
| playAction | binary | `$$play.pass.playAction` | true(74) | AttemptsTotal unreliable |
| qbPressured | binary | `$$play.pass.qbPressured` | true(74) | AttemptsTotal unreliable |
| screenPass | binary | `$$play.pass.screenPass` | true(71) |  |
| targetedRead | enum | `$$play.pass.targetedRead.targetedReadId` | 1(76), 2(68), 3(69), 4(71), 5(61) |  |
| throwAccuracy | enum | `$$play.pass.throwAccuracy.throwAccuracyId` | 1(65), 2(70), 3(58), 4(65), 5(75), 6(66), 7(61), 8(66), 9(64) |  |
| throwType | enum | `$$play.pass.throwType.throwTypeId` | 1(53), 2(49), 3(66), 4(74), 5(59), 6(69), 7(18), 8(71), 9(67) |  |

---

## 3. Receiving sweep — WR/TE/RB (11 dimensions)

Banked under `NFL-master/FP_SWEEP/<year>/Receiving/<dimension>/<value>.csv`.

| Dimension | Type | Parameter path | Values (2025) | Flag |
|---|---|---|---|---|
| depthOfTarget | range (4 bins: <=0,1-9,10-19,20+) | `$$play.pass.depthOfTarget` | -99_0(467), 10_19(468), 1_9(489), 20_99(447) |  |
| dropbackType | enum | `$$play.pass.dropbackType.dropbackTypeId` | 1(500), 2(429), 3(348), 4(411), 5(450) |  |
| outOfPocket | binary | `$$play.pass.outOfPocket` | true(477) |  |
| passLocation | enum (L/M/R x ...) | `$$play.pass.passLocation.passLocationId` | 1(430), 2(384), 3(441), 4(486), 5(473), 6(487) |  |
| passResult | enum | `$$play.pass.passResult.passResultId` | 1(492), 2(491), 3(365), 4(428), 5(424) |  |
| playAction | binary | `$$play.pass.playAction` | true(483) |  |
| qbPressured | binary | `$$play.pass.qbPressured` | true(491) |  |
| screenPass | binary | `$$play.pass.screenPass` | true(390) |  |
| targetedRead | enum | `$$play.pass.targetedRead.targetedReadId` | 1(493), 2(460), 3(456), 4(390), 5(393) |  |
| throwAccuracy | enum | `$$play.pass.throwAccuracy.throwAccuracyId` | 1(419), 2(476), 3(335), 4(392), 5(478), 6(417), 7(384), 8(415), 9(419) |  |
| throwType | enum | `$$play.pass.throwType.throwTypeId` | 1(286), 2(128), 3(437), 4(489), 5(378), 6(380), 7(78), 8(470), 9(411) |  |
| coverageScheme | enum (LABEL values, not codes) | `$$play.defense.coverageScheme.parent` | Cover_0(382), Cover_1(482), Cover_2(474), Cover_2_Man(311), Cover_3(499), Cover_4(483), Cover_6(455), Red_Zone(385), Goal_Line(55), Prevent(185), Bracket(252), Miscellaneous(19) | 2025 only, pulled 2026-07-07; positions RB/FB/WR/TE; DK scoring (`playerStatsFantasyPointsDraftKings` cross-checked = grid FP under DraftKings). Wire values are the labels themselves. The 7 shells feed `build_coverage_adv2025.py` -> `boom/coverage_route_spec.json` adv2025 blocks; the 5 situational values (Red Zone/Goal Line/Prevent/Bracket/Misc) are banked, unwired. |

**Companion (same folder):** `coverageScheme/separation_by_coverage.json` — the dedicated
`receiving-separation-by-coverage` tool (2025, 519 players RB/FB/WR/TE). Per-player separation
WIN%/SCORE% + TPRR/YPRR by bucket `Man / Zone / RedZone / Cover2 / Cover3 / Cover4 / Cover6 / Overall`.
Note: separation is NOT in the receiving-advanced export at all (no per-player sep column exists there),
and the sep tool has no C0/C1/Man-C2 buckets — per-scheme separation exists only for C2/C3/C4/C6.

---

## 4. Data-quality flags

FantasyPoints returns some stat fields **inconsistently under certain splits** (the value disagrees with 
internally-related fields). Distrust these specific field/split combinations:

- **Passing `AttemptsTotal`** is unreliable under `playAction=true`, `qbPressured=true`, and `dropbackType` codes 2 & 5 
  (median 26-89% deviation from Yards/YPA-implied attempts). These are scramble/rollout/pressure situations. 
  Dropbacks, Yards, and YPA in those same files are consistent and usable.
- **Receiving sweep:** no inconsistencies detected (Receptions <= Targets <= Routes holds across all 94 splits).

## 5. Available but NOT pulled (parameter not yet mapped)

These dashboard filters exist but their parameters aren't probe-discoverable and the rushing/receiving filter 
UI freezes under automation, so they were skipped. Each can be pulled on request with one hand-mapped click:

- **Rushing:** Men in the Box, DB Count, Read Option, Scramble, Yards Before Contact
- **Receiving-specific:** Individual Coverage, Alignment (Side), Alignment (Position), Contested Target, Blitzed, Blitz Count
- **Generic situational** (every tool): Down, Quarter, Half, Formation, Personnel, Motion, Score, Field Position — standard filters, not charting splits

## 6. How more gets pulled

Season & position are set in the request body (`filterMatch`), so any dimension pulls both years for the right 
positions automatically once its parameter path + type (enum `in` / range `between` / binary `eq`) is known. 
Parameters are play-level and shared across tools. The full puller + background-runner is reusable.

_Generated from the swept data on disk. Pipeline splits: 40 values (2025). 
Sweep CSVs: 180 files across both seasons._
---

## 7. Defense views — `FP_SWEEP/<year>/Defense_Receiving/` (NEW)

Per-team-defense receiving production **allowed**, sliced by the same play dimensions. 32 rows per file 
(one per defense), `opponentStats*` fields = what that defense gives up. Endpoint: `/team/defense/receiving-advanced`. 
This is matchup/funnel fuel — e.g. *receiving YPRR allowed in Cover 3 by defense*.

| Dimension | Parameter path | Values (2025) |
|---|---|---|
| coverageScheme | (same play-level path as player view) | Cover 0, Cover 1, Cover 2 Man, Cover 2, Cover 3, Cover 4, Cover 6 |
| depthOfTarget | (same play-level path as player view) | -99_0, 10_19, 1_9, 20_99 |
| dropbackType | (same play-level path as player view) | 1, 2, 3, 4, 5 |
| outOfPocket | (same play-level path as player view) | true |
| passLocation | (same play-level path as player view) | 1, 2, 3, 4, 5, 6 |
| passResult | (same play-level path as player view) | 1, 2, 3, 4, 5 |
| playAction | (same play-level path as player view) | true |
| qbPressured | (same play-level path as player view) | true |
| screenPass | (same play-level path as player view) | true |
| targetedRead | (same play-level path as player view) | 1, 2, 3, 4, 5 |
| targetedRoute | (same play-level path as player view) |  |
| throwAccuracy | (same play-level path as player view) | 1, 2, 3, 4, 5, 6, 7, 8, 9 |
| throwType | (same play-level path as player view) | 1, 2, 3, 4, 5, 6, 7, 8, 9 |

_Passing-defense and rushing-defense views (same method, separate pages) not yet pulled._

## 8. Defense_Passing — `FP_SWEEP/<year>/Defense_Passing/` (partial)

Per-team-defense passing production **allowed**, sliced by the same dimensions (coverage, throwType, passLocation, dropbackType, passResult, throwAccuracy, targetedRead, depth, play-action, pressure, screen, out-of-pocket). 32 rows per file, `opponentStatsPassing*` = allowed. Endpoint `/team/defense/passing-advanced`.

**Status: 2024 complete (12 dims); 2025 interrupted by FP server rate-limiting** — to be finished after a cooldown.
