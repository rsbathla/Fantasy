# Best Ball / DFS 2026 Toolkit — Corrected Architecture & Data-Integration Plan
*Senior-engineer review. Status: PLAN for approval before the build. Prepared 2026-06-18.*

---

## 0. Correction first (what changed my picture)

I originally claimed the toolkit had no coverage/pressure/run-type/directional data. **That was wrong** — it came from scoping my audit to `bestball/` and reading only the first ~2 KB of each file. A full-tree re-audit changed the picture three times, and the honest end state is:

1. **Extensive NFL advanced data exists** — but it lives in the *parent* `Downloads/` folder and the `ffdataroma_draft_guide_export/`, not inside `bestball/`. The toolkit never ingested it.
2. **The SIS player charting is 2024, Weeks 1–8** (a partial prior-year sample), while the team-level feeds (Vegas, OL, defense, scheme) are current 2026.
3. **`play_by_play_2025.rds` is WNBA**, not NFL. There is **no NFL play-by-play file in this tree**, so directional/run-gap must come from the **SIS exports**, not a PBP derive. True **man/zone coverage and QB pressure are not present anywhere** in the tree.

The lesson that drives the refactor: *the feature store was built from a narrow slice and silently ignored the richest data sitting one directory up.*

---

## 1. Corrected data inventory (signal → source → scope)

| Requested / valuable signal | Source file | Key columns | Scope / caveat | Join key |
|---|---|---|---|---|
| **Directional (depth)** | `receivingAdvancedExport.csv` | aDOT, AY Share, WIDE/SLOT/INLINE/BACK RTE% | 2024 W1–8 | Name+Team |
| **Directional / run-type (rush)** | `rushingAdvancedExport.csv` | gap/direction splits (ATT/YDS/TD/Success ×3), EXP RUN%, STUFF%, YBCO/YACO | 2024 W1–8 | Name+Team |
| **Route role / efficiency** | `receivingAdvancedExport.csv` | RTE%, TPRR, YPRR, 1READ%, DESIGN%, CTGT%, XFP/RR | 2024 W1–8 | Name+Team |
| **Red zone** | receiving `i20 TGT`/`EZTGT`/`EZTD`; rushing `i5 %` | RZ & goal-line opportunity | 2024 W1–8 | Name+Team |
| **O-line ("linemen")** | `ol-rankings__pass-blocking.csv`, `__run-blocking.csv` | Grade%, Win Rate% | 2026 team | Team |
| **Pressure (PROXY only)** | OL pass-block `Win Rate %` | team pass-pro quality | proxy, not charted pressure | Team |
| **Matchup** | `def-rankings.csv`, `strength-of-schedule__*` | Pass/Run Def tiers, SOS | 2026 team | Team |
| **Real game environment** | `weekly-vegas-lines.csv` | team, week, opp, teamImplied, total, spread | 2026, **weeks 1–18 incl. playoffs** | Team+Week |
| **Scheme tendencies** | `pass-catcher-offenses.csv`, `pace-stats.csv` | heavy personnel, play-action, motion, sec/play, plays/g | 2026 team | Team |
| **Coordinator change** | `backfield-opportunity.csv` (`New HC+OC 2026`), articles | flag + prose | 2026 team | Team |
| **Vacated/incoming volume** | `vacated-targets.csv` | vac/inc/ret tgt & rush by position | 2026 team | Team |
| **Expected points / spike** | `fantasy-xfp__*`, `predicted-spike-weeks.csv` | xFP, FPOE, spikeWeeks | mixed | Name |
| **Fusion weighting** | `metric-correlations__{pos}_*` | which metrics predict next-year fantasy | 2016–2025 study | — |
| **man/zone coverage; true QB pressure** | — | — | **NOT IN TREE** | — |

Everything in the current `bestball/pipeline/` (Clay projections, sim distributions, team volume, the weekly `player_games.parquet`) stays as the spine; the table above is the **new** layer to fold in.

---

## 2. Current architecture (as-is)

```
            UPSTREAM PIPELINE (bestball/pipeline)
 parse_clay -> clay_2026.csv
 build_layer2 -> layer2_team_params, player_sim_distributions
 sim_prod / survival_chain -> sim + win-delta
 merge_rankings/build_draft_board -> draft_board_signals.csv (SPINE)
            |
            v
   team_review_build.py   <-- ONLY module that touches raw parquets + does the name->pid join
            |  writes
            v
   team_review_data.json  (TEAM-NESTED — accidental feature hub)
        |          |            |
        v          v            v
   dfs_scenarios  gameplan   personnel        fusion.py (READS THE SPINE DIRECTLY — bypasses the hub)
        \          |            /                  |
         \         |           /                   |
          v        v          v                    v
                command_center.py  -> command_center.html      build_*_pdf -> PDF
```

This session added `core.py` (shared join/norm/IO) and `features.json` (a first flat store) — but `features` still draws only from the narrow pipeline slice, and the agents still mostly read `team_review_data.json`.

---

## 3. Problem areas (ranked by impact)

1. **Narrow feature store.** The store ignores the advanced exports one folder up — the single biggest gap. *Root cause:* the pipeline only knows about its own `pipeline/` outputs.
2. **DFS runs on synthetic game scripts** (hand-set total/spread per scenario) when **real weekly Vegas lines exist for every team incl. the W15–17 finals weeks**. The model is inventing the environment it could look up.
3. **Fusion uses hand-set weights** (0.42 ceiling, 0.23 advancement, …) when `metric-correlations__{pos}` measures which metrics actually predict fantasy — weights should be learned, not guessed.
4. **No matchup layer** despite `def-rankings` + Vegas being present; ceiling/scenario logic is matchup-blind.
5. **Accidental hub.** `team_review_data.json` was built for the written reviews but is now load-bearing for dfs/gameplan/personnel — a schema change for one breaks three.
6. **Duplicated, drifting helpers.** 5 copies of `fn()` and 5 of team-normalization; they already diverged (the LA→LAR Rams bug existed in one and not others). *Now centralized in `core.py`.*
7. **NaN leakage.** `json.dump` emitted `NaN`, which broke the PDF generator (invalid JSON). *Now fixed by `core.safe_json_dump`.*
8. **Name-join collisions** (A.J. Brown↔Amon-Ra, Jeremiyah↔Jordan Love) were fixed in only one module. *Now the single `core.match_usage`.*
9. **Provenance risk in shared dirs.** A WNBA file named `play_by_play_2025.rds` sits in a generic cache; multi-sport data shares the tree, so ingestion must assert sport/season, not trust filenames.
10. **No OL / coordinator-history in personnel** despite OL rankings + a "New HC+OC" flag + coaching-change articles being available.

---

## 4. Improved architecture (to-be)

```
  core.py  (canonical join · team-norm · NaN-safe atomic IO)            [DONE]
      |
  ingest_advanced.py  (NEW)  -- name/team-join the SIS + ffdataroma feeds,
      |                          assert sport=NFL & log match rates
      v
  features.parquet / features.json   (ONE flat source of truth, grouped signals)  [v2]
   identity | projection | sim | usage(PBP) | ROUTE/DEPTH/ALIGNMENT(SIS) |
   RUN-EFFICIENCY/GAP(SIS) | RZ | OL | DEF-MATCHUP | VEGAS(per week) | SCHEME | COORD | xFP
      |            |            |            |
      v            v            v            v
   fusion v2    dfs v2     gameplan     personnel v2     (all import core, read features)
   (corr-      (real      (unchanged    (+OL, +coord
    weighted)   Vegas)     inputs)       history)
      \           |           |              /
       v          v           v             v
              command_center.html   +   GamePlan.pdf
```

Principle: **one ingestion layer, one feature store, thin agents.** No agent re-reads raw files; adding a data source means editing `ingest_advanced.py` only.

---

## 5. DFS v2 — "all data," grounded in real Vegas

- **Replace synthetic scenarios with the actual implied environment per ceiling week.** For W15/W16/W17, look up each team's real `total`/`spread` from `weekly-vegas-lines` and compute P(ceiling) at *that* environment — then keep the 6 what-if scripts as a secondary "leverage" layer.
- **Modulate the ceiling by the player's real profile, not just position:** depth (aDOT) + alignment (slot vs wide vs backfield), route rate/TPRR/YPRR, run success%/stuff%/gap tendency, RZ share (i20/EZ/i5), and the **OL pass/run-block** quality in front of them.
- **Matchup:** shade by opponent `Pass Def`/`Run Def` tier for the ceiling weeks.
- **Pressure** enters only as the OL pass-block proxy, explicitly labeled; **man/zone coverage is omitted and flagged**.
- Keep the directional sanity gate (WRs↑ when trailing/high-total, RBs↑ when leading).

## 6. Fusion v2 — re-weighted by what actually predicts

- Consume `features`; add model votes for **route efficiency (YPRR/TPRR), xFP/FPOE, OL, and matchup**.
- Derive weights from `metric-correlations__{pos}` (data-driven) instead of hand-set constants; keep the **divergence-as-signal** framing and the FADE/DARLING leverage flags. *This is the "re-run fusion after all datasets are exhausted" step.*

## 7. Personnel v2

- Add **O-line** (pass/run-block tiers) and the **coordinator-change flag** (`New HC+OC 2026`) + **historical tendencies** (prior-team pace/pass-rate where the article corpus names the hire). OL + coordinator complete the "offense, defense, and linemen" ask.

---

## 8. Phased build plan (with verification gates)

| Phase | Deliverable | Verification gate |
|---|---|---|
| 1 | `ingest_advanced.py` → `features` v2 | match-rate report per source (≥X% of board joined); sport/season asserted; no NaN |
| 2 | DFS v2 on real Vegas | W15–17 Vegas join 100%; directional sanity still passes; spot-check 6 players |
| 3 | Fusion v2 (corr-weighted) + Personnel v2 (OL/coord) | weights trace to metric-correlations; OL+coord coverage report |
| 4 | Regenerate dashboard + PDF | headless JS exec + cross-artifact invariants (as last build) |

## 9. Limitations carried forward (stated, not hidden)

- **SIS charting is 2024 W1–8** — a partial prior-year tendency signal, not 2025 full-season; it will be weighted as a *profile prior*, not as projection.
- **No man/zone coverage, no charted QB pressure** in-tree — pressure proxied by OL win rate; coverage omitted. (Drop the SIS passing/defense export in `Downloads/` and Phase 1 picks it up automatically.)
- **No NFL play-by-play** in-tree (the `.rds` is WNBA) — directional/run-type come from SIS, not a PBP derive.
- Name joins are high-precision but not perfect across the partial SIS sample; match rates are reported, not assumed.

---

## 10. Open decision for you

The plan above integrates everything actually present. The one true gap is **man/zone coverage + charted pressure**. If you can drop that SIS/PFF passing-or-defense export anywhere in `Downloads/`, Phase 1 will ingest it with no further design changes. Otherwise I proceed with the OL-based pressure proxy and omit coverage, clearly flagged.

**Approve and I start at Phase 1 (ingestion → feature store v2).**

---

## 11. GAP RESOLVED — `NFL-master` ingested (added after the user supplied it)

I was wrong that coverage/pressure weren't available. The user dropped `NFL-master.zip` (35 MB) — a mature SIS/FantasyPoints NFL charting codebase. Corrected mapping:

| Signal | Source (in `Downloads/NFL-master/`) | Scope |
|---|---|---|
| **Coverage scheme (man/zone)** | `FP/2025/Passing/CoverageType/*`, `FP/2025/Receiving/CoverageType/*` (Cover 0-6, Man Cover 2, Screen) | 2025 full season, ~448 players |
| **Coverage — defense (matchup)** | `FP/2025/PassingDef/CoverageType/*`, `ReceivingDef/*` | 2025, per defense |
| **Pressure (outcome)** | SACK%, SK YDS in the `Passing/CoverageType` + `PassingDef` files | 2025 |
| **Directional (pass)** | `FP/2025/Passing/TargetDirection_LRM/{Left,Middle,Right}`, `_SD/{Deep,Short}` | 2025 |
| **Directional (rush)** | `FP/2025/Rushing/RushDirection/*`, `AGG_RUSHDIRECTIONPOOLED_*` (End/Guard/Tackle) | 2025 / last-6 |
| **Run type (scheme)** | `FP/2025/Rushing/RunType/*`, `AGG_COVERAGE_SHEETS_RB_*` (Inside/Outside Zone, Power, Counter, Duo, Trap, Lead) | 2025 / last-6 |
| **Route type** | `FP/2025/Receiving/RouteType/*` | 2025 |
| **Opponent-adjusted expected (matchup-weighted)** | `AGG_*_LAST6/AGG_MASTER_*` (Player, Team, "Week 15 Opponent", Expected /G vs Opp) | **W15 only, ~18 players** |
| **SIS taxonomy** | `lookup_data/` (coverageSchemeTypes, blockingSchemeTypes, runType, motion, pull…) | reference |
| **College (rookies)** | `CFB_SIS_DEF/` (coverage/run/blocking scheme) | reference |
| **Extra scrape / profiles** | `nfl_chat_app/nfl_pro_scraper/*`, `player_profiles/output/json/*` | bonus |

**Updated ingestion (replaces §10's open gap):**
1. `ingest_advanced.py` gains an `NFL-master` reader that, per board player, pulls full-season vs-coverage splits (YPRR/TPRR/aDOT vs Man vs Zone), directional (deep%/L-M-R, rush gap/direction), run-type success (zone vs gap), and the QB pressure (sack%) profile — joined Name+Team.
2. Matchup: each ceiling-week opponent's `*Def/CoverageType` profile → does the defense play man/zone, and how it grades vs that → shade the player's ceiling.
3. DFS v2 ceiling now modulates on **real coverage matchup + the player's vs-coverage strength + directional/run-type fit**, on top of the Vegas environment.
4. Fusion v2 gains coverage-adjusted efficiency dimensions; weights still set by `metric-correlations`.
5. Caveat: `FP/2025` is full-season (primary); the opponent-adjusted `AGG` masters are W15/18-player and can be regenerated for the full board + W16/17 via the repo's own `create_aggregate_*_last6.py`.

**Remaining true caveat:** "pressure" here is sack *outcome* by coverage (and OL win-rate), not snap-level pressures-faced; close enough for fantasy ceiling modulation, labeled as such.
