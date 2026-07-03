# Data Index — derived analytical layers (behind `ask_data.py` / the `data-librarian` agent)

Every DERIVED layer the model consumes, its **key format**, and its **year vintage**. The vintage
column is the point: the same metric name (e.g. `yprr_man`) appears in several files with *different*
years, and confusing them is the #1 error. For the RAW upstream exports (PFF/FTN/FantasyPoints under
`NFL-master/`) see `DATA_CATALOG.md`. Query with `python3 ask_data.py {player|team|coverage|matchup} …`.

## The one cross-cutting fact
Box-score / PBP actuals span **2024+2025**. NFL **charting** (YPRR, separation, man/zone scheme
splits) is mostly **2025-only** — the sole 2-year charting source is the FantasyPoints CoverageType
data, which feeds `coverage_split`, `coverage_route_spec`, and `manzone_2yr`. Anything YPRR/scheme
from `player_profiles`, `cc_context`, or `sis_value/*` is **2025 only**.

## Player layers

| File | key | records | vintage | what's in it |
|---|---|---|---|---|
| `boom/chart2yr.json` | fn (`jamarr chase`) | 753 | **per-year `y2024`+`y2025`** + blend | YPRR, aDOT, tprr, ay_share, rz_tgt_rate, ez_tgt, i20_pg, slot/wide %, contested/deep %, fp_rr |
| `boom/statmenu.json` | fn | 411 | 2yr agg + per-yr `g24/g25` | master menu: `rz`, `cspec`, `adv2`, `chart2`, base_boom, adp, usage/role (RB) |
| `boom/base2yr.json` | fn | 411 | per-yr `g24/b24/g25/b25` | boom-rate base + 2026 projection |
| `boom/adv2.json` | fn | 311 | **2yr POOLED** | box-score advanced: aDOT, ay_share, td_pg, ypt (charting stays single-season) |
| `boom/redzone.json` | fn | 319 | 2yr pooled | `rz_tgt_share`, `ez_tgt_share`, `ez_td`, `ez_td_pg` |
| `boom/manzone_2yr.json` | **RAW name** | 121 | **2yr blend + per-yr `d24`/`d25`** | `man2y`/`zon2y` YPRR, `d24`/`d25` (ONLY per-year man/zone), `read`, `tier` |
| `boom/coverage_split.json` | fn | 291 | **2yr pooled** | `man_yprr`, `zone_yprr`, `delta` (man=Cov0/1/ManC2; zone=Cov2/3/4/6) |
| `boom/coverage_route_spec.json` | fn (`.key`) | 349 | **2yr pooled** | ⭐ **per-SCHEME** (Cover 0/1/2/3/4/6, Man Cover 2) YPRR+pctl, per-route, rollups |
| `boom/cover_spec.json` / statmenu `cspec` | fn | 81 | **2025-eff.** | best coverage bucket, `profile{man,zone,single_high,two_high}` in **FP/RR (not YPRR)** |
| `boom/motion.json` | fn | 325 | 2yr blend | motion %, YPRR w/ vs w/o motion, motion_lift |
| `boom/deep_pass.json` | fn (QB) | 58 | 2yr pooled | deep_rate, deep_ypa, deep_pctl |
| `profiles/player_profiles.json` | **RAW name** | 273 | **2025 ONLY** | `situations.rec_vs_man/zone` (`val`=YPRR, `pct`=pctl), deep, FTN yds/route |
| `cc_context.json` | fn | 379 | **splits 2025**, matchup 2026 | `splits.yprr_man/yprr_zone/man_route_sh`, opp/matchup (2026 schedule) |
| `flag_ranks.json` | fn (`.players`) | 376 | **2026 projection** | ceil/ceil_pctl, trait_pctl, tgt_sh/car_sh, top_flags, ranking vs market |
| `rz_equity_2026.json` | fn (`.teams`) | 235 | 2yr → 2026 | `rz_role_z` (pos-centered), basis (RZ tgt share / TD-per-game) |
| `pipeline/player_games.parquet` | **pid + nflverse name** | 11223 | **2024+2025 per-game** | box score + `dk`; the atomic actuals table |
| `sis_value/receiving_{value,man,zone}.csv` | RAW name + **nickname team** | 200 | **2025 ONLY** | SIS value overall/vs-man/vs-zone (PE/route, EPA/tgt, Boom%) |

## Team layers

| File | key | vintage | what's in it |
|---|---|---|---|
| `boom/defense_shell.json` | abbr (+`_LEAGUE`) | **2025** | ⭐ **per-shell frequency**: `man`, `c2`, `c3`, `c4`, `c6`, `single_high`, `two_high` (% dropbacks) |
| `defense_splits.json` | abbr | **2025 primary** | `vs_man/vs_zone/deep` softness pctl, `shell{man_rate,single_high,two_high}`, `by_pos` FPAA, `units` |
| `boom/defensive_profile.json` | abbr | 2025 + `lean_2026` | `dvoa_fpaa` allowed by pos, `cb1`, `eng2026`, rookies |
| `offense_profile.json` | abbr | 2025 base + 2026 outlook | pace/plays_pg, pass_rate, identity, playcaller, scheme_dials |
| `team_ceiling.json` | abbr (`.teams`) | **2026 projection** | ceiling_score, drivers, tier (ELITE/HIGH/MID/LOW) |
| `proe_tendency_2026.json` | abbr (`.teams`) | 2025 actual + 2026 assumption | `proe_2025` (actual), `carousel_adj`, `proe_2026` (NOT a fact) |
| `data/fantasypoints/proe_{offense,defense}_2025.csv` | abbr | **2025 per-week** | PROE for/allowed, w1–w18 + season |
| `data/nflverse/games_2021_2025.csv` | abbr + game_id | 2021–2026 | schedule, scores, `spread_line`/`total_line`, roof/temp/wind |

## Key-format resolution (the join gotchas)
- **fn-normalized** (`core.fn`: lowercase, drop Jr/Sr/II–V, strip `.`/`'`, `-`→space): most boom files,
  cc_context, flag_ranks, rz_equity.
- **RAW display name**: `boom/manzone_2yr.json`, `profiles/player_profiles.json` (join via `fn(key)` or `.name`).
- **nflverse** `pid` + abbrev name (`J.Chase`): `pipeline/*.parquet` — `pid` is the only reliable join.
- **SIS**: raw name + **nickname-only** team (`Bengals`,`49ers`; `"2 teams"` for traded).
- Team abbrev variants to normalize (`core.norm_team`): LA→LAR, JAC→JAX, WSH→WAS, ARZ→ARI, TAM→TB, …
- ⚠️ `boom/pff_receiving_scheme_2025.csv` is **college**, not NFL. `cover_spec` values are **FP/RR, not YPRR**.

## Worked examples (both real user questions, answered by the tool)
- *"Is Chase's man YPRR 2025-only or 2024 too?"* → `ask_data.py player "Ja'Marr Chase"`: 2025-only in
  `player_profiles`/`cc_context`; 2yr-pooled in `coverage_split` (1.53) & `manzone_2yr` (`man2y` 1.585),
  with the only per-year split in `manzone_2yr` `d24=-1.52` / `d25=-1.06`.
- *"Which zone does he dominate, and does TB play it?"* → `ask_data.py matchup "Ja'Marr Chase" TB`:
  Cover 3 = his best (3.55 YPRR, 98th pctl, `coverage_route_spec`); TB runs Cover 3 on 36.4% (6th/32,
  `defense_shell`) → flagged EDGE.
