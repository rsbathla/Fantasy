# NFL Situational Data — Master Catalog

Multi-source player & team situational data for 2024 + 2025, pulled through the user's own
authenticated browser sessions (each site's own request headers were reused; auth tokens were
never read, printed, or stored). Built to answer: **which situations does each player succeed or
struggle in**, and to support matchup / opportunity / coaching-change analysis.

All data lives under `NFL-master/`. Player situational **profiles** (the headline deliverable) are
under `profiles/`.

---

## 1. PFF Premium Stats — `NFL-master/PFF/<year>/`  (26 CSVs)

Player-level, names + team + position included. Source: `premium.pff.com/api/v1/facet/{base}/{view}`.

**Base facets** (one row per player, full stat surface):
- `passing.csv` — QB grades, BTT/TWP rate, aDOT, EPA, pressure-to-sack, time-to-throw, accuracy (48 cols)
- `receiving.csv` — YPRR, grades, YAC/rec, contested catch rate, slot/wide/inline snaps & rates, aDOT, EPA (51 cols)
- `rushing.csv` — elusive rating, breakaway %, YCO/att, gap vs zone attempts, grades, receiving YPRR (50 cols)
- `defense.csv` — every defender, coverage/pass-rush/run grades, pressures, stops (59 cols)
- `punting.csv`

**Sub-report views** (situational splits, very wide):
- `passing_depth.csv` (558 cols) — every metric × depth bucket (behind-LOS/short/medium/deep) × field third (L/C/R)
- `passing_pressure.csv` — pressure vs no-pressure, blitz vs no-blitz splits
- `passing_concept.csv` — play-action vs non-PA, screen vs non-screen
- `receiving_depth.csv` (509 cols) — receiving production by target depth × field third
- `receiving_concept.csv` — slot / wide / screen splits
- `receiving_scheme.csv` — **vs Man vs Zone** (man_yprr, zone_yprr, man/zone grades, QB rating when targeted)
- `defense_coverage.csv`, `defense_run.csv` — defender coverage & run splits

---

## 2. FTN Fantasy (DVOA/charting) — `NFL-master/FTN/<year>/`  (12 CSVs)

Joined by player GSIS id across stat-groups, names attached via repo roster map.
Source: `…execute-api…/Statshub/statshub/{category}/{role}/{group}` (POST).
`{category}` = passing / rushing / receiving; `{role}` = player / defense.

Each `<category>_<role>.csv` merges all available groups:
- **analytics**: DVOA, DYAR, EPA
- **efficiency**: catchable targets, contested rec, created catches, drops, explosive, success rate, missed tackles
- **coverage**: man/zone/slot/inline/out-wide route & yards, **stepSeparation**, wideOpen/tightCoverage, single-high/two-high
- **airYards** + **deep**: air yards, catchable/dropped/prayer yards, deep targets/rec/yards/TD
- **redZone**: red-zone & end-zone targets/TDs
- **pressure** / **turnover** (passing)

FTN's stat-groups *are* the situational breakdowns (delivered as joined columns).

---

## 3. FantasyPoints — `NFL-master/FP/` (79) + `NFL-master/FP_SWEEP/` (398)

**Pipeline splits** (`FP/<year>/…`, wired into the Best Ball engine):
Passing & Receiving CoverageType, Receiving RouteType (10 routes), Rushing RunType (10 concepts),
Rushing RushDirectionPooled, Passing TargetDirection.

**Exhaustive sweep** (`FP_SWEEP/<year>/…`):
- Passing (10 dims) & Receiving (11 dims) player splits: dropbackType, passLocation, passResult,
  playAction, qbPressured, screenPass, targetedRead, throwAccuracy, throwType, depthOfTarget.
- **Defense_Receiving** (13 dims, both seasons) — receiving production allowed by each defense, by coverage/route/depth/etc.
- **Defense_Passing** (12 dims, both seasons — 2025 salvaged this session) — passing allowed by each defense.
- **Defense_Rushing** (base table, both seasons) — rushing allowed by each defense (YPA, success%, stuff%, YBCO, EXP run%).
  Dimensional rush splits (by concept/direction) need a charting-context request the base call lacks — available on request.

Data-quality flag (carried from sweep): PFF `AttemptsTotal`/FP passing attempt counts are unreliable
under play-action / pressure / scramble dropback types; yards & per-attempt rates in those splits are fine.

---

## 4. Player Situational Profiles — `profiles/`

- `PLAYER_PROFILES.md` — readable, per player: situations they **excel** in vs **struggle** in (percentile vs positional peers), with year-over-year trend on the headline efficiency metric. 273 players (QB/RB/WR/TE).
- `situational_percentiles.csv` — full matrix: player × 46 situations (percentile 0–100).
- `profiles_summary.csv` — quick-scan strengths/weaknesses per player.
- `player_profiles.json` — structured, for downstream use.
- Built by `build_profiles.py` (re-runnable). Method: per situational efficiency metric, rank players
  within position among those clearing a volume threshold → percentile; high = succeeds, low = struggles.

Situations covered — WR/TE: vs man, vs zone, slot, wide, deep ball, deep vs short routes, separation,
contested, YAC, aDOT, drop rate, red-zone, DVOA/success. RB: elusiveness, breakaway, YCO/att, inside vs
outside zone vs gap, MTF, receiving, rush DVOA. QB: under pressure, clean pocket, vs blitz, deep ball,
play-action, BTT/TWP rate, accuracy, aDOT, time-to-throw, DVOA.
