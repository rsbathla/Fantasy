# 2024 Charting Pull Plan — to make the SKILL FLAGS two-season

## Status today
- **Base ceiling rate**: 2-season (2024+2025) + 2026 projection prior. DONE.
- **Efficiency/usage advanced** (aDOT, air-yards share, target/carry share, YPT, YPC, yards/touch,
  TD rate, QB rushing): 2-season, derived from `player_games.parquet`. DONE, wired into flags
  (270/403 players cite 2-yr values).
- **Charting advanced** (the gap this plan fills): separation, YPRR-with-routes, TPRR, man/zone
  coverage splits, YAC-over-expected, broken/missed tackles, route-type/run-type splits. These
  still rest on **single-season** snapshots (the 2025 FantasyPoints/SIS sheets). No 2024 charting
  exists locally.

## Why agents can't pull it from here
The sandbox has **no network route** to the providers (`data.fantasypoints.com`,
`sisdatahub.com`, `sportsinfosolutions.com` all fail DNS). The authenticated pull must run in
**your** environment. (Also: `NFL-master/fp_playwright_puller.py` has your FantasyPoints
email+password hardcoded in plaintext, lines ~2234-2235 — move those to env vars `FP_USERNAME`/
`FP_PASSWORD` and rotate the password.)

## What to pull for 2024 (mirror the 2025 structure)
Pull the SAME tables the 2025 pipeline uses, but for the **2024 season**:

| Source table | Drives which flags | Existing 2025 location |
|---|---|---|
| Receiving by coverage (man/zone), route-level | WR/TE separator, route-tech/YPRR, TPRR, air-yard%, target share | `NFL-master/AGG_COVERAGE_SHEETS_WR_LAST6/` |
| SIS DataHub receiving (Routes, Tgts, Catchable, Air Yards, YAC, YAContact, Brkn/Missed Tkls) | YPRR, YAC-over-expected, catch quality, separation proxy | `NFL-master/SIS DataHub - NFL.csv` (has 2023 → 2024 available) |
| Passing by coverage (man/zone) | QB pocket/clean-vs-pressure, coverage-beating | `NFL-master/AGG_COVERAGE_SHEETS_QB_LAST6/` |
| Rushing by run-type + direction | RB run-scheme fit, gap/zone, MTF | `NFL-master/AGG_RUSHDIRECTIONPOOLED_SHEETS_RB_LAST6/`, `AGG_MASTER_ALL_RUNTYPES_WITH_TARGETS.csv` |
| Pass/Rush Defense allowed (optional) | opponent context (note: defense is roster-volatile yr/yr) | `dfs_review/.../defense*.json` |

Want **full-2024-season** (not last-6) aggregates so the 2-yr blend is a clean season+season average.

## Three ways to run it (pick one)
1. **You run the puller** (simplest): move creds to env vars, then run the FantasyPoints puller
   targeting the 2024 season → it writes `FP/2024/...`. I'll first add a `--season 2024` selector
   to the puller (needs the page visible to find the season control — do it via option 2 or send
   me a screenshot of the FantasyPoints season filter).
2. **Authorize Claude-in-Chrome** on your logged-in FantasyPoints / SIS DataHub tab — I drive the
   season filter + exports table-by-table (reading your own authenticated session; no creds handled).
3. **Manual export**: from SIS DataHub, export the 2024 receiving/rushing/passing CSVs and drop
   them in `NFL-master/` — I ingest from there.

## Ingest + integrate (ready once 2024 files land — I build these on arrival)
1. `build_sis2024_agg.py` → normalize 2024 pulls into the same schema as the 2025 AGG sheets.
2. `charting_2yr.py` → blend 2024+2025 charting per player (games-weighted) into 2-yr
   separation / YPRR / TPRR / coverage-split / YAC-oe signals; write `boom/charting2yr.json`.
3. Update `AGENT_BRIEF` charting section to point flags at the 2-yr charting; re-run the 4 skill
   flag agents ONCE (so charting + efficiency are both 2-season in one pass).
4. Rebuild `player_explorer.html` + jsdom validate.

## My recommendation
Option 2 (Claude-in-Chrome on your authenticated session) is the cleanest — no credential
handling, I can navigate the season filter and export each table, and I see the page to map the
controls. Say the word and grant the Chrome extension access to the FantasyPoints/SIS tab.
