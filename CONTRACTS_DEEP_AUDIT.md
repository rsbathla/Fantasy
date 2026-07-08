# CONTRACTS DEEP AUDIT — field-level producer→consumer diff of the inter-layer JSON contracts

*Built 2026-07-05. Scope: the 20 contract files named in the tasking (features counted as one
json+csv pair; both coordinator files counted). Method: for every contract, the writer's emitted
fields were diffed against every reader's accessed fields — name, type, scale, nullability, team
key, and identity join — and every claimed mismatch was re-derived from the raw JSON/CSV (not from
code reading alone). Verdicts: **match** / **MISMATCH(kind)** / **orphan** / **dead-read**.*

Neutral per-contract notes come first (§2); the ranked findings, guards, and decision points
follow (§3–§5), per deliverable-form discipline.

---

## §1 · Contract inventory (writer → readers actually found by grep)

| # | Contract | Writer(s) | Reader(s) |
|---|---|---|---|
| 1 | `defense.json` (root) | `normalize_defense_2026.py:284` (canonical), `ingest_defense.py:120` (stage 1), `reweight_defense_2026.py:309` (legacy, refuse-guarded) | `build_defense_splits.py:81`, `build_def_profile.py:10`, `build_flags_layer.py:46`, `build_lever_count.py:50`, `build_lever_calendar.py:26`, `fusion.py:119`, `build_intel.py:34`, `command_center.py:12`, `sync_boom_defense.py:8`, `api/app/repositories/store.py:25` |
| 2 | `dfs_review/out/defense.json` (SECOND file, same basename, different schema) | dfs_review pipeline (parent dir) | `build_team_scout.py:35`, `boom_foundation.py:183` |
| 3 | `defense_splits.json` | `build_defense_splits.py:118` | `dfs_model.py:36`, `build_home.py:9`, `build_team_preview.py:33`, `build_week1_report.py:30`, `render_dfs_week.py:10`, `ask_data.py:207` |
| 4 | `features.json` / `features.csv` | `build_features.py:54-55`, `ingest_advanced*.py` (1–10), `ingest_defense.py:141-143`, `normalize_defense_2026.py:302-304`, `reproject_movers.py:114-115`, `refactor/featurestore.py:92-95` | `fusion.py:270`, `dfs_scenarios.py:99`, `build_flag_ranks.py:152`, `build_intel.py:23`, `backtest_composite_2025.py:68/87/173`, `validate_signal_stability.py:11`, `correlate_upside.py:34`, `build_cc_context.py:17`, `dfs_model.py:149`, `build_offense_profile.py:58`, `build_profiles.py:39`, `build_script_study.py:18`, `x_fetch.py:46`, `x_dossier_refresh.py:52`, `build_dossier.py:34`, `audit_roster_moves.py:133`, `refactor/registry.py:46/64` |
| 5 | `fusion.json` | `fusion.py:1040` | `build_rankings.py:15`, `build_intel.py:27`, `command_center.py:12`, api store |
| 6 | `player_funnels.json` | `build_player_funnels.py` | `build_fp_alignment.py:77` |
| 7 | `fp_alignment.json` | `build_fp_alignment.py:96-97` | **none** (orphan; INTEGRATION_AUDIT.md:138 concurs) |
| 8 | `fp_personnel.json` | `build_fp_personnel.py:87` | `build_sis_personnel.py:111` (teams only; `players` section unconsumed) |
| 9 | `personnel_2026.json` | `build_personnel_layer.py:56` (v1) + in-place upgrade `build_fp_personnel.py:91-100` | `build_team_preview.py:22/143`, `brain/brain_concepts.py:175/96-100` |
| 10 | `nflpro_2025.json` | `build_nflpro.py` | `build_team_preview.py:24/202+`, `brain/brain_concepts.py:174/69-77` |
| 11 | `game_sim.json` | `game_sim.py:210` | `dfs_model.py:54-59`, `render_game_sim.py:10`, `build_dfs_week_report.py:259-262`, `build_week1_report.py:38`, `build_team_preview.py:34/43`, `brain/brain_concepts.py:175/80-92` |
| 12 | `team_review_data.json` | `team_review_build.py:139` | `team_review_render.py:5`, `gameplan.py:83`, `personnel.py:202` |
| 13 | `team_ceiling.json` | `build_team_ceiling.py:610` | `env_blend.py:40`, `game_sim.py:69`, `build_stack_menu.py:97/147`, `build_slot_paths.py:160`, `build_dfs_weekly_breakdown.py:32/218`, `engine/strategy_live.py:57-66`, `build_matchup_notes.py:20`, `ask_data.py:233`, `build_pdf.py:41` |
| 14 | `scheme_2026.json` | hand-authored/agent-authored (web-verified) | `build_flags_layer.py:44/80`, `build_home.py:10/14-16`, `build_offense_profile.py:55/97-112`, `build_cc_context.py:18/112`, `build_lever_count.py:62-64`, `build_lever_calendar.py:36-37`, `brain/brain_pages.py:166`, `build_team_preview.py:25/36` |
| 15 | `coordinator_changes_2026.json` | hand-authored registry | `build_coordinator_scheme.py:19/27`, `build_scheme_fit.py:115`, `build_def_profile.py:12/79`, `build_intel.py:30`, `brain/brain_pages.py:168`, `build_dossier.py:19`, `integration_audit.py:881-907` |
| 16 | `coordinator_scheme_2026.json` | `build_coordinator_scheme.py:34-37` | `build_scheme_fit.py:110-114`, `build_lever_count.py:48`, `build_lever_calendar.py:25`, `build_def_profile.py:11/79`, `build_team_ceiling.py:295/331` |
| 17 | `brain_intel.json` | `brain/brain_export.py:179` | `engine/run_live.py:120-123`, `build_week1_report.py:35-36`, `build_team_preview.py:28-29/38/196`, `brain/brain_concepts.py:177`, `build_decision_dashboard.py` |
| 18 | `ground_truth_registry.json` | hand-authored | `integration_audit.py:816-818` (Check I) |
| 19 | `deliverable_manifest.json` | hand-authored | `integration_audit.py:770-792` (Check H2) |
| 20 | `flag_ranks.json` / `flags_2026.json` | `build_flag_ranks.py:274` / `build_flags_layer.py:171` | flag_ranks: `build_slot_paths.py:131`, `build_stack_menu.py:96`, `build_big_board.py:35`, `build_adp_clusters.py:13`, `build_dfs_weekly_breakdown.py:33`, `engine/bbengine.py:395-405`, `build_rankings.py:22`, `audit_roster_moves.py:135`, `ask_data.py:139`. flags_2026: `build_rankings.py:19-20`, `run_all.py:70` |

---

## §2 · Per-contract field matrix (producer fields vs consumer reads)

### 1. `defense.json` (root)
Producer emits per team (`normalize_defense_2026.py:259-272`): `team`, `pass_cov_pctl`,
`pass_cov_pctl_2025`, `pass_cov_rate_2026`, `pass_rush_pctl`, `pass_rush_pctl_2025`,
`pass_rush_rate_2026`, `run_def_pctl`, `run_def_pctl_2025`, `run_def_rate_2026`,
`pass_cov_epatgt`, `pass_cov_strength`, `pass_rush_strength`, `run_def_strength`,
`rookies_2026` (list of 5-tuples), `top_coverage/top_pass_rush/top_run_def`
(`{name,pos,ps,rate,snaps}`), `moves_2026` (`{player,unit,from,to,ps,conf}`).

| Field | Consumers | Verdict |
|---|---|---|
| `pass_cov_pctl` / `pass_rush_pctl` / `run_def_pctl` (0-100, higher=tougher) | build_defense_splits:110, build_def_profile:16-20, build_flags_layer:69, build_lever_count:127-129 (÷100, correct scale), build_lever_calendar:72, fusion:127, build_intel:156, command_center:29-31, sync_boom_defense:9 | **match** (scale confirmed 0-100 both sides) |
| `*_pctl_2025` | build_intel:157, command_center:31 | match |
| `*_strength` | command_center:29-30 (display only) | match (note: semantics changed from Points-Saved SUM to PAA/play under the normalize writer; only display consumers remain) |
| `rookies_2026` | build_intel:160 `r[0],r[1],r[3]`, command_center:34 same | **match in code / MISMATCH(doc)** — meta `fields` (normalize_defense_2026.py:282) documents `(name,pos,round,proj_rate)` 4-tuple; actual is `(name,pos,unit,round,rate)` 5-tuple. Anyone coding from the meta doc reads `r[2]` as round and gets `'pass_rush'`. |
| `moves_2026` | build_intel:161, command_center:33 (`player,unit,from,to,ps,conf`) | match |
| `top_*` | command_center:32 | match |
| 32 team keys canonical | verified raw: all 32, `JAX` form | match |

### 2. `dfs_review/out/defense.json` (the OTHER defense.json)
Schema: `{TEAM:{QB:{rank,of,tier,ratio,n},RB:…,WR:…,TE:…}}` — 32 canonical keys verified raw.
Readers `build_team_scout.py:87` and `boom_foundation.py:194` read `[pos].tier` — match.
**MISMATCH(latent path/schema)**: `build_team_scout.R()` (`build_team_scout.py:8-14`) resolves, in
order, `DL/rel` → `HERE/rel` → **`HERE/basename`**. The third candidate is the repo-root
`defense.json` — a *different schema* under the same basename. Today `DL/dfs_review/out/defense.json`
exists so the read is correct; on any layout without the parent copy the fallback silently loads the
pctl-schema file and every `.get('QB',{}).get('tier','')` returns `''` — blank tiers, zero errors.
`boom_foundation.py:183` hard-opens the parent path (crashes loudly if absent — acceptable).

### 3. `defense_splits.json`
Producer (`build_defense_splits.py:101-116`) per team: `vs_man/vs_zone/deep/short`
(`{allowed_ypr, softness_pctl}` 0-100 higher=softer), `by_pos` (`qb,rb,wr,te,wr1,wr2,slot` FPAA),
`shell` (`{man_rate, single_high, two_high}` **percent 0-100**, from `boom/defense_shell.json.man`),
`units` (the three defense.json pctls), `funnels`, `lean_2026`.
**Nullability contract: any None field is OMITTED entirely** (`build_defense_splits.py:116`).

| Reader | Reads | Verdict |
|---|---|---|
| dfs_model.py:167-236 | `vs_man/vs_zone.softness_pctl`, `shell.man_rate` (percent, `_mrs` percentile), `by_pos.{wr1,te,rb,qb…}`, `units.*` — all via chained `.get(...) or {}` | match |
| build_week1_report.py:46-56, 112-130, 255-265 | same fields, defaults (`man_rate` default 25, softness 50); thresholds `man_rate >= 30 / <= 22` confirm percent scale | match |
| build_team_preview.py:141-189 | same, `num(...,50)` defaults | match |
| build_home.py:104-107 / render_dfs_week.py:94-96 (JS) | `d.vs_man…` `bp.wr1??bp.wr` | match (JS would throw only if a team key vanished; all 32 present) |
| ask_data.py:211-213 | `softness_pctl` | match |

Raw-verified: all 32 teams present, zero omitted fields in the current build.

### 4. `features.json` / `features.csv`
Producer reality (raw-verified): **140 of 144 player fields are STRINGS** (every ingest is
csv.DictReader→rewrite; only the 4 `opp_*` floats injected by `normalize_defense_2026.py:293-296`
are numeric). The csv/json column-sync guard exists (`refactor/pipeline.py:52-61`).

| Reader | Coercion | Verdict |
|---|---|---|
| fusion.py:277-300 | `pd.to_numeric` over an explicit num_cols list | match |
| dfs_scenarios.py:146 | `_f()` str→float, documented | match |
| build_flag_ranks.py:155-164 | `_num()` on carry_share/tgt_share | match |
| build_cc_context.py:30-102 | `num()` everywhere | match |
| correlate_upside.py:50 | `num(p.get(c))` | match |
| dfs_model.py:149, build_offense_profile.py:58, build_dossier.py:34 | pandas read (auto-numeric) | match |
| backtest_composite_2025 / validate_signal_stability | use features only for pid/name/pos | match |
| **build_intel.py:24,142,148,167** | **NONE** — `'adp':p.get('adp')`, `'proj':p.get('proj_pg')` kept as strings; rosters sorted `key=(adp is None, adp or 9999)` | **MISMATCH(type/scale) — HIGH.** Sort is lexicographic. Raw-verified: all 379 skill adp values are `str`; sorted order begins `'1.1574535','10.389036','100.50972','100.73937','101.924355'…` and `intel_data.json.players` ships in exactly that corrupted order (Gibbs → Lamb → **Fannin ADP 100.5** → Brooks 100.7 → Dart 101.9). Same corrupted sort feeds per-team rosters at :167 and the string `adp`/`proj` values are exported into `intel_data.json` reads. Downstream: `build_dossier.py:102-103` (IPL by-name lookups unaffected; any order-dependent team rendering inherits the wrong order). |

### 5. `fusion.json`
Producer (`fusion.py:879-1040`): players `{name,pos,team,adp(float),models{...scalars},
consensus(float),divergence,flags[]}` (model keys omitted when N/A — documented).
Readers: build_rankings.py:23-24 `cons()` handles scalar-or-dict; build_intel.py:35-38 `mv()/cons()`
same; command_center.py:23-24 `.get` defaults. **match** (incl. nullability: omitted model keys).

### 6. `player_funnels.json` → 7. `fp_alignment.json`
Producer per player: `pos,gp,recv{routes…},alignment_funnel{mix{slot,wide,tight}(0-1),home,
wins_from,yprr_by,sep_by},depth_funnel{mix},usage{role,team,tgt_share(0-1)…},team`.
Reader `build_fp_alignment.py:74-92` reads `alignment_funnel.mix` fractions, ×100 on both sides of
the compare — **scale match**. Team codes raw-verified canonical.
**MISMATCH(identity join) — LOW but live:** join key is each builder's identical `fn()`, but the
vendors spell differently: NFL Pro `Audric Estimé` → key `audric estimé`; FP `Audric Estime` →
`audric estime`. Raw-verified: exactly 1 of 109 "no NFL Pro match" entries is recoverable by
accent-folding (`audric estime` ↔ `audric estimé`). No `fn()` in the repo (incl. `core.fn`) folds
accents, so the class recurs for any future accented name.
**fp_alignment.json itself: orphan** — no reader anywhere (records carry no `team` field either);
its cross-check verdicts (`xcheck`, `consensus_slot`, `npro`) influence no decision.

### 8. `fp_personnel.json` → 9. `personnel_2026.json`
`fp_personnel.teams[T].heavy_rate` is a 0-1 fraction (raw: ARI 0.456); `_meta` says so;
`build_sis_personnel.py:110-120` consumes it as a fraction and ×100 explicitly — **match**.
Upgrade path `build_fp_personnel.py:95-97` writes `fp_heavy_rate_2025 = heavy_rate*100` (percent)
next to v1 `heavy_2025` (percent) — internally consistent (raw: LAR 26.9 vs 28.0).
**Orphans:** `personnel_2026.teams[*].fp_heavy_rate_2025` + `fp_personnel_mix` have **no consumer**
(grep: only the writer); `fp_personnel.players` (403 players, `heavy_share` 0-1) also unconsumed.
Consumers of personnel_2026 (build_team_preview:145-155, brain_concepts:96-100) read only v1 fields
`heavy_2025, heavy_rank_2025, pa_2025, motion_2025, direction_2026, evidence` — all present, all
percent, `.get` defaults — **match**.

### 10. `nflpro_2025.json`
`teams[T] = {season, pass{ALL,slot,wide,tight,deep,intermediate,short,play_action →
{pass_plays,epa_pass,avg_sep,ypp,yacoe,sack_pct,qbp_pct,blitz_pct,soft_pctl,sep_pctl}},
rush{…,soft_pctl}}`. Raw-verified complete for all 32 teams × all keys the consumers touch.
build_team_preview.py:203-224 (`soft_pctl`,`sep_pctl`, `rush.soft_pctl` — direct `[]` but
completeness verified) and brain_concepts.py:69-77 (`soft_pctl` guarded) — **match**.

### 11. `game_sim.json`
`weeks{"1".."18"}.games[] = {game, teams[2], wk, vegas{total,imp{T},spread_fav,spread},
sim{…}, winner{…,fav,fav_win}, total_dist{…}, margin_dist{…}, script{fav,dog,fav_control_run,
dog_comeback_pass,shootout_bothpass,script_pass_lean{T:{base,effective,lead_big_p,trail_p}}},_narr}`.
dfs_model.py:56-59 (`script.shootout_bothpass`, `script_pass_lean.{lead_big_p,trail_p}`, defaults),
build_week1_report.py:38/288-289 (direct `[]`, fields present), build_team_preview.py:43,
build_dfs_week_report.py:259-262 (`frozenset(g['teams'])`), brain_concepts.py:80-92
(`vegas.imp/spread_fav/spread`) — **match** all sides, week keys consistently string.

### 12. `team_review_data.json`
Top level = 32 teams + **`FA` + `_league`** (non-team keys). Per team: `bye,delta,nalpha,name,note,
players[],script,team,tl,w15,w16,w17`.
team_review_render.py:6 pops `_league`, handles FA explicitly (`verdict()` "if not s: # FA");
gameplan.py:249/317/632 filters `("FA","_league")`; personnel.py:243/260 keyed `.get` only —
**match** (nullability handled by all three).
`delta.departures_fix` (team_review_build collision-guard, :106-116) confirmed present — the
abbreviated-PBP-name departure join now drops returning-starter collisions.

### 13. `team_ceiling.json`
`teams[T] = {base_core, ceiling_score(0-100), drivers, flags, inputs, rank, raw, tier}`.
env_blend.py:40-41 (`ceiling_score`, computes league mean), game_sim.py:69, build_stack_menu:147-210
(÷100 — scale confirmed), build_slot_paths:159-165, strategy_live:57-66 (handles both top-level
shapes), build_dfs_weekly_breakdown:218 (`tier`,`flags` with `or []`), build_pdf:534 — **match**.

### 14. `scheme_2026.json`
Top level = 21 team keys + `_meta`. Fields: `playcaller/off/note` on 18, `dc/def/def_note` on 13;
**BUF, DAL, GB intentionally have no `off`** (continuity — documented inside `def_note`).
All consumers reach it with `.get('off')`/`.get('def') or {}` (build_flags_layer:80,
build_lever_count:64, build_lever_calendar:37, build_offense_profile:112, build_cc_context:113,
build_home:14-16 skips `_meta`) — **match**; `_meta` leaks into `SCHDEF` as a garbage `'_META'` key
in lever builders (never looked up — harmless).

### 15. `coordinator_changes_2026.json` → 16. `coordinator_scheme_2026.json`
Registry: 24 team keys + `_README`; fields `oc_name/oc_new/dc_name/dc_new/dc_prior_man_rate/
dc_prior_sack_rate/dc_scheme/source/src/verified` (per-team subsets). All readers filter `_`-keys
or use `.get` — match. integration_audit.py:906-908 reads `oc_name/dc_name` — match.
**MISMATCH(team key) — CRITICAL — the `'ers'` chain, raw-re-derived end to end:**
1. `ingest_advanced.py:14` `ab()` strips leading digits (`re.sub(r'^\d+','',…)`) so Team Name
   `"49ers"` → `"ers"`; the FULL2AB recovery (`'49ers' in 'ers'`) can never match a *shortened*
   string; `core.norm_team` has no `ers` alias → **`defense_coverage.csv` row 32 is `ers,16.2,3.1`**
   (verified raw; SF absent).
2. `build_coordinator_scheme.py:26-27` iterates those keys and does `reg.get('ers')` → misses the
   **verified** SF registry entry (`dc_new: true, dc_name: "Raheem Morris", dc_prior_man_rate: 26,
   dc_prior_sack_rate: 8.0, verified: true`). Output teams therefore: **no `SF` key; an `'ers'`
   record carrying `dc_new:false, man_rate_adj:16.2, sack_rate_adj:3.1, conf:"2025-actual"`.**
   Correct values under the blend rule (`build_coordinator_scheme.py:22`, BLEND=0.5) would be
   `man_rate_adj = 0.5·16.2 + 0.5·26 = 21.1` and `sack_rate_adj = 0.5·3.1 + 0.5·8.0 = 5.6`.
3. Consumer exposure (all silent):
   - `build_scheme_fit.py:112-114` **knows about `'ers'` and re-keys it to SF locally** — but the
     re-keyed record still carries the wrong *values* (dc_new=false, unblended 16.2), so scheme_fit
     treats SF as a no-change zone-lean defense when the registry says Morris = MORE man +
     aggressive pressure. The local patch masks the corruption instead of fixing it.
   - `build_lever_count.py:48/106,127-129` — `nt('ers')='ERS'`; `COORD['SF']` absent → SF man-rate
     and sack-blend activators silently skip for every player whose W15-17 lever crosses SF.
   - `build_lever_calendar.py:25` — same drop.
   - `build_def_profile.py:79` — `_csch.get('SF',{})` → `{}` silently.
   - `build_team_ceiling.py:331` — `coord.get('SF',{})` → `oc_new` False (benign today: SF's 2026
     change is DC-side, and team_ceiling reads only `oc_new`).
   - Direct `defense_coverage.csv` readers also lose SF: `boom_foundation.py:184`,
     `build_splits.py:25`, `build_team_scout.py:36`, `analyze_rookie_manzone.py:18` (their
     `tm()`/TMAP have no `ERS` alias). `build_week1_report.py:25-29` builds `SCH` including the
     `ers` row but `SCH` is **never used** afterwards (dead-read — no W1 impact).

### 17. `brain_intel.json`
`players` keyed by DISPLAY name (`"A.J. Brown"`, `"Aaron Jones Sr."`), `teams` keyed by FULL name,
`coaches` by display name. Consumers all re-key: run_live.py:123 `bb._norm(_nm)`,
build_week1_report.py:36 / build_team_preview.py:29 `fn(k)`, brain_concepts.py:177 `fn(k)` — match.
`build_team_preview.py:38` joins `teams` via TEAM_FULL map and `:196` joins `coaches` on the raw
`web_teams.dc` string — exact-string joins between two curated layers (`"Nick Rallis"` format both
sides today); brittle to punctuation drift but no live miss found.

### 18. `ground_truth_registry.json` / 19. `deliverable_manifest.json`
Registry `entries[] = {path, asserts, provenance, verified_by,…}` — auditor reads `e['path']`
(integration_audit.py:816-818) — match. Manifest `deliverables{name:{authored, layers_used,
layers_unused_justified…}}` — Check H2 (integration_audit.py:770-792) reads those exact fields —
match.

### 20. `flag_ranks.json` / `flags_2026.json`
flag_ranks players (fn-keyed): `adj_order, adj_pos_rank, adj_rank, adp, car_sh, ceil, ceil_pctl,
delta, flag_score, mkt_rank, n_flags, nudge, opp_pctl, pmq(_pctl), pos, rmq(_pctl), scheme_fit,
sf_adj, smq(_pctl,_pctl_adj), team, tgt_sh, top_flags, trait_pctl`. Consumers: build_slot_paths
(`adp`,`adj_rank`), build_stack_menu (`name,pos,team,adp,adj_rank,mkt_rank`; documents tgt_sh-None
and deliberately doesn't use it), bbengine:395-405 (`nudge`, None-gated; `_norm` ≡ core.fn),
build_rankings (`delta`,`adj_rank`), build_dfs_weekly_breakdown, build_big_board, ask_data — all
present, all None-gated — **match**. Note the near-miss naming trap across the two files:
flag_ranks `adj_pos_rank` vs flags_2026 `adj_posrank` — currently every reader reads the right
spelling from the right file (build_rankings.py:41 reads flags_2026 `adj_pg/avail/playoff/total`;
flag_ranks fields only from flag_ranks).
flags_2026 `meta.{n_flagged,n_playoff_flagged}` — consumed by run_all.py:70-72 — match.

### Identity-join residuals beyond the four already-fixed sites
The four named fixes are confirmed in place: `team_review_build.py:106-116` (collision-guarded
departures), `boom_base2yr.py:98-110` and `adv2yr.py:61-70` (pos-filter + pid-group + team
disambiguation), `build_qual_summary.py:12-18` (full-token matcher), plus
`pipeline/build_layer2.py:46-56` C4 CV-collision drop and `engine/bbengine.py:113-114` (refuses
first-initial fallback). Remaining exposure:
- `pipeline/build_layer2.py:9-12` still keys Clay params by first-initial (`p[0][0]+'.'+p[-1]`).
  Raw-verified **15 colliding keys** live in `clay_2026.csv` today — including `a.brown`
  (Amon-Ra St. Brown / A.J. Brown), `b.robinson` (Bijan / Brian Robinson Jr. — same team, same
  position), `j.love`, `t.etienne`, 3-way `j.williams`/`k.williams`/`t.johnson`. Containment:
  downstream sim joins are by full `name` (`pipeline/sim_prod.py:4`, `build_week1_report.py:34`,
  `build_player_explorer.py:33`, `engine/run_live.py:86`), and the CV lookup drops colliders to the
  archetype fallback — so today the collisions cost *precision* (colliding players get archetype CV
  instead of their own), not *identity*. The exported `key` column is a loaded gun for any future
  consumer.
- `boom_base2yr.py:104-107` / `adv2yr.py:69-70` disambiguation **never abstains**: when the team
  match isn't unique it takes `max(bypid, key=startable-games)`. A queried player absent from the
  parquet who shares (initial, last, pos-group) with a real player will inherit that player's 2-yr
  boom/adv history instead of falling back to priors.
- Accent folding: absent from every `fn()` (core.py:19-21 and the four builder copies) —
  the `estimé` miss above is the live instance.

---

## §3 · Ranked findings

| # | Sev | Kind | Producer side | Consumer side | Effect |
|---|---|---|---|---|---|
| F1 | **CRITICAL** | team key + nullability | `ingest_advanced.py:14` (`ab()` digit-strip) → `defense_coverage.csv` row `ers,16.2,3.1`; propagated by `build_coordinator_scheme.py:26-31` which also drops the verified SF registry entry (`coordinator_changes_2026.json` SF: Raheem Morris, dc_new, man 26, sack 8.0) | `build_lever_count.py:48/106`, `build_lever_calendar.py:25`, `build_def_profile.py:79`, `build_team_ceiling.py:331`, `build_scheme_fit.py:112-114` (key patched, values still wrong), `boom_foundation.py:184`, `build_splits.py:25`, `build_team_scout.py:36`, `analyze_rookie_manzone.py:18` | SF defense has NO coordinator-scheme data anywhere downstream; where the `'ers'` record is rescued (scheme_fit) it says dc_new=false / man 16.2 instead of new-DC / man ≈21.1, sack ≈5.6. Every SF-facing matchup/lever read is silently wrong-or-missing. |
| F2 | **HIGH** | type/scale | features.json numerics are strings (all ingest writers; 140/144 cols str, raw-verified) | `build_intel.py:24,142,148,167` — no coercion; lexicographic ADP sort | `intel_data.json` players + per-team rosters ship in corrupted "ADP order" (verified: 1.15 → 10.38 → 100.5 → 100.7 → …); string adp/proj exported downstream (dossier ingest at `build_dossier.py:102-103`). |
| F3 | MED | same-name schema | `dfs_review/out/defense.json` (tier schema) vs root `defense.json` (pctl schema) | `build_team_scout.py:8-14` `R()` basename fallback | Latent: on any layout missing the parent copy, team_scout silently renders blank tiers from the wrong-schema file. |
| F4 | MED | orphan producers (fusion gaps) | `fp_alignment.json` (whole file), `personnel_2026.json.fp_heavy_rate_2025/fp_personnel_mix`, `fp_personnel.json.players`, `build_week1_report.py:28` `SCH` (dead read) | — | Paid-for signal (FP alignment cross-check, FP personnel per-player mixes) reaches no decision. |
| F5 | LOW-MED | identity join | NFL Pro `Audric Estimé` vs FP `Audric Estime`; no accent folding in any `fn()` | `build_fp_alignment.py:85` `npro.get(k)` | Silent "no NFL Pro match"; class recurs for future accented names. |
| F6 | LOW-MED | identity join (residual) | `boom_base2yr.py:104-107` / `adv2yr.py:69-70` never abstain on ambiguous pid | — | Wrong-player 2yr history possible for (initial,last,pos) doppelgängers absent from parquet. |
| F7 | LOW | doc contract | `normalize_defense_2026.py:282` meta documents `rookies_2026` 4-tuple; actual 5-tuple | (current readers use correct indices) | Next consumer coded from the meta doc misreads unit as round. |
| F8 | LOW | naming trap | flag_ranks `adj_pos_rank` vs flags_2026 `adj_posrank`; fp teams `heavy_rate`(0-1) vs personnel `fp_heavy_rate_2025`(0-100) | all current readers correct | Near-miss inventory — one future consumer away from the FP raw-vs-friendly class. |

**Verified-clean (worth recording so it isn't re-audited):** defense.json↔all consumers (fields+
scale), defense_splits omit-if-None ↔ double-`.get` consumers, shell.man_rate percent both sides,
fusion.json models/consensus scalar-or-dict handled, game_sim full field match, team_review FA/
_league handled ×3, team_ceiling 0-100 both sides, scheme_2026 missing-`off` intentional+guarded,
brain_intel display-name keys re-normalized by all consumers, registry/manifest ↔ auditor,
flag_ranks/flags_2026 ↔ all nine consumers, FP team-code maps (BLT/CLV/HST/ARZ/JAC/LA…) — outputs
raw-verified 100% canonical in player_funnels/fp_personnel; `strategy_live` tolerates both
team_ceiling shapes; run_all's flags_2026 meta read matches.

---

## §4 · Proposed guards — each with the known-bad input that makes it fire TODAY

*(proposals only — no code or schema was changed in this audit)*

1. **Canonical-team-key check** (integration_audit): every team-keyed contract's keys ⊆ the 32
   canonical codes (allow `_*`, `FA` where declared). **Fires now** on `defense_coverage.csv` row
   `ers` and `coordinator_scheme_2026.json.teams.ers`.
2. **Registry-consumption check**: every non-`_` key in `coordinator_changes_2026.json` must appear
   in `coordinator_scheme_2026.json.teams` with `verified` carried over. **Fires now** on SF.
3. **Feature-type check**: `features.json` fields consumed as numbers by any non-coercing reader
   (start: `adp`, `proj_pg`) must be numeric or the reader must coerce. **Fires now** (`adp` is
   `str` for all 379 players).
4. **Accent-fold join test**: assert `fold(k)` uniqueness/coverage across player_funnels ↔
   fp_alignment keys. **Fires now** on `audric estime(é)`.
5. **Same-basename schema fingerprint**: loading any `defense.json` asserts expected top-level
   shape (`{meta,teams}` vs per-team tier records). **Fires** by deleting/renaming the parent
   `dfs_review/out/defense.json` and re-running build_team_scout (known-bad simulation), which
   today silently blanks tiers.
6. **Orphan-output check** (extends Check G): a builder that writes a root artifact with zero
   readers and no `terminal` declaration flags. **Fires now** on `fp_alignment.json`.

## §5 · Decision points (returned, not resolved)

1. **F1 fix location** — options: (a) fix `ab()` (`ingest_advanced.py:14`) to check FULL2AB
   *before* digit-stripping (or add `'ers'→SF` to core.TMAP), regenerate `defense_coverage.csv` →
   `coordinator_scheme_2026.json` → lever/scheme/def_profile/team_ceiling chain; (b) also remove
   `build_scheme_fit.py:112-114`'s local patch afterwards or keep as belt-and-braces. Recommend (a)
   at the source + keep the patch one release as a tripwire with a loud print. Note the SF
   man/sack lever direction flips vs today (16.2-no-change → 21.1 new-DC man-lean): W15-17 SF
   matchup reads will move — worth a before/after diff before shipping boards.
2. **F2** — coerce in `build_intel.py` (one `num()` at :24) vs fixing the store to write real
   numbers (bigger change, touches 12 ingest writers + every DictReader consumer). Recommend the
   one-line consumer coercion now + guard #3; store-typing is a separate refactor decision.
3. **F4 orphans** — wire `fp_alignment.json`/`fp_personnel.players` into a consumer (natural home:
   cc_context alignment panel or team_preview), or declare them terminal in the manifest. Owner
   call: they were built to be consumed; declaring terminal contradicts the layer's stated purpose.
4. **F5/F6** — add accent-folding to `core.fn` + the 4 builder copies (join-semantics change:
   needs your sign-off since it alters the ONE canonical join), and make base2yr/adv2yr abstain
   when `len(tmatch)!=1` and no unique startable-max. Recommend both.
5. **F3** — drop the basename fallback for `defense.json` specifically in `build_team_scout.R()`,
   or rename the dfs_review artifact (`defense_tiers.json`). Rename is cleaner; it's a schema-name
   collision, not a path problem.
6. **F7** — one-line meta doc fix in `normalize_defense_2026.py:282`.

## §6 · Re-derivations performed (discipline §7 / preamble #7)

1. `coordinator_scheme_2026.json` loaded raw: `teams` has no `SF`, has `ers` with
   `dc_new:false, man_rate_adj:16.2`; `coordinator_changes_2026.json.SF` loaded raw shows
   `dc_new:true, dc_prior_man_rate:26, verified:true` → blend math re-computed (21.1 / 5.6).
2. `features.json` loaded raw: `adp` type `str` for 379/379 skill players; lexicographic vs numeric
   first-8 diff shown; `intel_data.json` loaded raw and its shipped player order matches the
   lexicographic ordering exactly.
3. `defense_coverage.csv` read raw: final row `ers,16.2,3.1`; 31 canonical rows otherwise.
4. `player_funnels.json` vs `fp_alignment.json` keys loaded raw: exactly one accent-recoverable
   miss (`audric estime` ↔ `audric estimé`); `player_funnels` team codes 100% canonical.
5. `clay_2026.csv` first-initial keys recomputed: 15 collision keys, listed in §2.
