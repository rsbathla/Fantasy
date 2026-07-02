# INTEGRATION AUDIT

_Catches "layer built but not properly consumed". Re-run: `python3 integration_audit.py`._

_Data-side companion: `audit_roster_moves.py` (cross-source player-team check + roster-move reconciliation) → ROSTER_MOVES_2026.md._

## Summary

- **0 invariant violations** (P0 -- a layer is being under-used)
- **0 split-source files** (P0 -- one logical file read from two drifting copies)
- **0 orphan candidates** (produced/on-disk, no consumer; terminals + verified curated dynamic reads excluded)
- **2 builders** produce artifacts but are absent from the pipeline runner
- **462 unused fields** across 70 record-structured layers (auto-discovered, repo-wide)
- **26 divergent consumers** (a consumer under-using a layer its peers read fully)
- **3 fallback counters** currently firing (see check D)

## A. Invariant violations (P0)

_None._

## B. Field utilization (per rich layer)

### `boom/adv2.json`  (18 fields, 1 consumers)
| consumer | # fields read |
|---|---|
| build_player_explorer.py | 5 |

**Unused by ALL consumers:** `aDOT`, `ay_share`, `int_pg`, `patt_pg`, `ptd_pg`, `rec_pg`, `recyd_pg`, `rush_pg`, `rushtd_g`, `rushyd_pg`, `td_pg`, `ypa`, `yptouch`

### `boom/base2yr.json`  (10 fields, 9 consumers)
| consumer | # fields read |
|---|---|
| analyze_rookie_manzone.py | 3 |
| analyze_rookie_situations.py | 2 |
| backtest_rookie.py | 3 |
| build_manzone_tags.py | 2 |
| build_player_explorer.py | 9 |
| build_rookie_prior.py | 3 |
| correlate_upside.py | 4 |
| validate_signal_stability.py | 0 |
| woptimize_rookie.py | 3 |

**Divergent consumers (read <40% of peer max — likely under-using the layer):** `analyze_rookie_situations.py`, `build_manzone_tags.py`, `validate_signal_stability.py`

### `boom/boom_marks.json`  (19 fields, 7 consumers)
| consumer | # fields read |
|---|---|
| build_decision_dashboard.py | 9 |
| build_intel.py | 7 |
| build_rankings.py | 4 |
| build_team_scout.py | 5 |
| build_upside_cases.py | 8 |
| command_center.py | 5 |
| team_dashboard.py | 5 |

**Unused by ALL consumers:** `best_p`, `cspec_ratio`, `good`, `nflags`, `smash`

### `boom/boomdef.json`  (15 fields, 2 consumers)
| consumer | # fields read |
|---|---|
| boom_base2yr.py | 5 |
| boom_lib.py | 5 |

**Unused by ALL consumers:** `N_startable`, `anchors_agree_within_8pct`, `boom_rate_startable`, `booms_per_17g`, `mean`, `mean_plus_1sd`, `n_obs`, `p85`, `sd`, `threshold`

### `boom/chart2yr.json`  (29 fields, 3 consumers)
| consumer | # fields read |
|---|---|
| build_dossier.py | 11 |
| build_intel.py | 9 |
| build_player_explorer.py | 7 |

**Unused by ALL consumers:** `aDOT`, `ay_share`, `fp_rr`, `fr_pct`, `mtf_rec`, `threat`, `y2024`, `y2025`, `yaco_rec`

### `boom/cover_spec.json`  (16 fields, 5 consumers)
| consumer | # fields read |
|---|---|
| analyze_rookie_manzone.py | 9 |
| build_boom_marks.py | 4 |
| build_intel.py | 8 |
| build_player_explorer.py | 2 |
| build_upside_cases.py | 5 |

**Unused by ALL consumers:** `best_keys`, `lg`, `profile`, `routes`, `val`

**Divergent consumers (read <40% of peer max — likely under-using the layer):** `build_player_explorer.py`

### `boom/coverage_route_spec.json`  (13 fields, 1 consumers)
| consumer | # fields read |
|---|---|
| build_scheme_fit.py | 4 |

**Unused by ALL consumers:** `cells`, `elite_pctl`, `min_peers`, `min_rte`, `min_rte_overall`, `min_rte_route`, `routes`, `scheme_groups`, `weak_pctl`

### `boom/coverage_split.json`  (6 fields, 2 consumers)
| consumer | # fields read |
|---|---|
| build_dossier.py | 4 |
| ingest_coverage.py | 6 |

### `boom/deep_pass.json`  (5 fields, 2 consumers)
| consumer | # fields read |
|---|---|
| build_dossier.py | 3 |
| ingest_deep_pass.py | 5 |

### `boom/defender_grades.json`  (42 fields, 1 consumers)
| consumer | # fields read |
|---|---|
| build_def_profile.py | 5 |

**Unused by ALL consumers:** `BAL`, `BUF`, `CAR`, `CHI`, `CIN`, `CLE`, `DAL`, `DEN`, `DET`, `GB`, `HOU`, `IND`, `JAX`, `KC`, `LAC`, `LAR`, `LV`, `MIA`, `MIN`, `NE`, `NO`, `NYJ`, `PHI`, `PIT`, `SEA`, `TB`, `TEN`, `age`, `cb_room_avg`, `college`, `cov_grade`, `def_grade`, `draft_yr`, `n_graded`, `pos`, `rookie_2025`, `team`

### `boom/defense2026.json`  (11 fields, 1 consumers)
| consumer | # fields read |
|---|---|
| boom_lib.py | 4 |

**Unused by ALL consumers:** `covp`, `man_rate`, `manp`, `runp`, `sack_rate`, `sackp`, `tiers`

### `boom/defense_shell.json`  (8 fields, 7 consumers)
| consumer | # fields read |
|---|---|
| build_defense_splits.py | 3 |
| build_flags_QB.py | 1 |
| build_flags_TE.py | 8 |
| build_flags_WR.py | 8 |
| build_lever_calendar.py | 3 |
| build_lever_count.py | 3 |
| build_scheme_fit.py | 3 |

**Divergent consumers (read <40% of peer max — likely under-using the layer):** `build_flags_QB.py`

### `boom/defense_tackling.json`  (4 fields, 1 consumers)
| consumer | # fields read |
|---|---|
| build_lever_count.py | 1 |

**Unused by ALL consumers:** `mtf_allowed`, `mtf_att_allowed`, `rush_att`

### `boom/defensive_profile.json`  (26 fields, 4 consumers)
| consumer | # fields read |
|---|---|
| apply_funnel_overlay.py | 5 |
| build_defense_splits.py | 13 |
| build_intel.py | 13 |
| command_center.py | 12 |

**Unused by ALL consumers:** `eng2026`, `man25`, `man26`, `scheme`, `wr1_funnel`

### `boom/flags_DST.json`  (12 fields, 0 consumers)

**Unused by ALL consumers:** `adp`, `base`, `boom_games`, `empirical`, `hist`, `line`, `n_games`, `name`, `pos`, `skill_flags`, `team`, `weeks`

### `boom/flags_QB.json`  (12 fields, 1 consumers)
| consumer | # fields read |
|---|---|
| build_stack_overlay.py | 5 |

**Unused by ALL consumers:** `adp`, `boom_games`, `empirical`, `hist`, `line`, `n_games`, `pos`

### `boom/flags_RB.json`  (12 fields, 0 consumers)

**Unused by ALL consumers:** `adp`, `base`, `boom_games`, `empirical`, `hist`, `line`, `n_games`, `name`, `pos`, `skill_flags`, `team`, `weeks`

### `boom/flags_TE.json`  (12 fields, 0 consumers)

**Unused by ALL consumers:** `adp`, `base`, `boom_games`, `empirical`, `hist`, `line`, `n_games`, `name`, `pos`, `skill_flags`, `team`, `weeks`

### `boom/flags_WR.json`  (12 fields, 0 consumers)

**Unused by ALL consumers:** `adp`, `base`, `boom_games`, `empirical`, `hist`, `line`, `n_games`, `name`, `pos`, `skill_flags`, `team`, `weeks`

### `boom/fp_levers_extra.json`  (4 fields, 1 consumers)
| consumer | # fields read |
|---|---|
| build_dossier.py | 4 |

### `boom/gamelog.json`  (30 fields, 7 consumers)
| consumer | # fields read |
|---|---|
| analysis_combos.py | 0 |
| analyze_rookie_manzone.py | 0 |
| analyze_rookie_situations.py | 0 |
| backtest_boom.py | 0 |
| boom_lib.py | 0 |
| build_upside_cases.py | 0 |
| switch_test.py | 0 |

**Unused by ALL consumers:** `dst_ari`, `dst_atl`, `dst_bal`, `dst_buf`, `dst_car`, `dst_chi`, `dst_cin`, `dst_cle`, `dst_den`, `dst_det`, `dst_gb`, `dst_hou`, `dst_ind`, `dst_jax`, `dst_kc`, `dst_lac`, `dst_lar`, `dst_lv`, `dst_mia`, `dst_min`, `dst_ne`, `dst_no`, `dst_nyj`, `dst_phi`, `dst_pit`, `dst_sea`, `dst_sf`, `dst_tb`, `dst_ten`, `dst_was`

### `boom/manzone_2yr.json`  (12 fields, 3 consumers)
| consumer | # fields read |
|---|---|
| build_dossier.py | 6 |
| build_manzone_2yr.py | 12 |
| refresh_intel.py | 0 |

**Divergent consumers (read <40% of peer max — likely under-using the layer):** `refresh_intel.py`

### `boom/manzone_tags.json`  (2 fields, 1 consumers)
| consumer | # fields read |
|---|---|
| build_manzone_tags.py | 2 |

### `boom/motion.json`  (6 fields, 2 consumers)
| consumer | # fields read |
|---|---|
| build_dossier.py | 5 |
| ingest_motion.py | 6 |

### `boom/movers_reprojection.json`  (6 fields, 2 consumers)
| consumer | # fields read |
|---|---|
| audit_roster_moves.py | 2 |
| reproject_movers.py | 6 |

### `boom/oline_2026.json`  (3 fields, 2 consumers)
| consumer | # fields read |
|---|---|
| build_dossier.py | 3 |
| build_flags_layer.py | 2 |

### `boom/opp_offense.json`  (5 fields, 3 consumers)
| consumer | # fields read |
|---|---|
| audit_roster_moves.py | 2 |
| build_extra_signals.py | 1 |
| build_flags_DST.py | 4 |

### `boom/opportunity.json`  (5 fields, 2 consumers)
| consumer | # fields read |
|---|---|
| apply_funnel_overlay.py | 1 |
| build_cc_context.py | 5 |

### `boom/redzone.json`  (4 fields, 1 consumers)
| consumer | # fields read |
|---|---|
| build_player_explorer.py | 0 |

**Unused by ALL consumers:** `ez_td`, `ez_td_pg`, `ez_tgt_share`, `rz_tgt_share`

### `boom/rookie_college_profile.json`  (21 fields, 2 consumers)
| consumer | # fields read |
|---|---|
| analyze_rookie_situations.py | 5 |
| build_dossier.py | 7 |

**Unused by ALL consumers:** `board_adp`, `boom_prior`, `college`, `draft_eligible_2026`, `epa`, `man_pctl_fbs`, `manzone_tag`, `pe`, `s2024`, `s2025`, `zone_pctl`, `zone_pctl_fbs`

### `boom/rookie_db_grades.json`  (2 fields, 1 consumers)
| consumer | # fields read |
|---|---|
| normalize_defense_2026.py | 1 |

**Unused by ALL consumers:** `note`

### `boom/rookie_prior.json`  (12 fields, 2 consumers)
| consumer | # fields read |
|---|---|
| apply_rookie_to_statmenu.py | 4 |
| build_dossier.py | 2 |

**Unused by ALL consumers:** `basis`, `board_adp`, `ceiling_pctl_2025`, `clamp`, `mean_boom`, `mean_ceiling`, `shrink`, `slope_per_pctl_shrunk`

### `boom/roster_flags_2026.json`  (16 fields, 2 consumers)
| consumer | # fields read |
|---|---|
| build_flags_layer.py | 11 |
| build_lever_count.py | 5 |

**Unused by ALL consumers:** `CAR`, `CHI`, `MIA`, `PHI`, `src`

### `boom/schedule2026.json`  (32 fields, 6 consumers)
| consumer | # fields read |
|---|---|
| boom_lib.py | 0 |
| build_flags_layer.py | 9 |
| build_lever_calendar.py | 10 |
| build_lever_count.py | 9 |
| build_scheme_fit.py | 1 |
| dfs_model.py | 0 |

**Unused by ALL consumers:** `ATL`, `BUF`, `CAR`, `CHI`, `CIN`, `DAL`, `DEN`, `GB`, `IND`, `KC`, `MIA`, `MIN`, `NE`, `NO`, `NYG`, `NYJ`, `PHI`, `PIT`, `SEA`, `TB`, `TEN`

**Divergent consumers (read <40% of peer max — likely under-using the layer):** `boom_lib.py`, `build_scheme_fit.py`, `dfs_model.py`

### `boom/scheme_fit.json`  (18 fields, 2 consumers)
| consumer | # fields read |
|---|---|
| build_dossier.py | 13 |
| build_flag_ranks.py | 6 |

**Unused by ALL consumers:** `regular`, `single_high`, `team_src`, `two_high`

### `boom/statmenu.json`  (107 fields, 7 consumers)
| consumer | # fields read |
|---|---|
| analyze_rookie_manzone.py | 9 |
| analyze_rookie_situations.py | 10 |
| boom_lib.py | 6 |
| boomutil.py | 0 |
| switch_test.py | 4 |
| tighten_flags.py | 5 |
| validate_boom.py | 7 |

**Unused by ALL consumers:** `FP_RR`, `MTF_att`, `MTFoe`, `TPRR`, `TPRR_w`, `YACoe`, `YPRR`, `adot`, `adv_pctl`, `airyard_pct`, `ay_share`, `b2`, `b24`, `base_blended_preboost`, `best_keys`, `blend`, `boom_pctl`, `carry_pg`, `catch`, `catch_rate`, `ceiling_pctl`, `college_boom_prior`, `coverage_proof_pctl`, `dk_pg`, `eff_combined`, `env_idx`, `explosive_pctl`, `ez_td`, `ez_td_pg`, `ez_tgt_share`, `g2`, `hist2`, `int_pg`, `lg`, `matchup_pctl`, `off_q`, `pace_pctl`, `patt_pg`, `pctl`, `plays_pg`, `profile`, `protection_pctl`, `ptd_pg`, `ratio`, `rec_eff_pctl`, `rec_pg`, `recyd_pg`, `role`, `rookie_boost`, `route_eff_pctl`, `routes`, `run_eff_pctl`, `rush_eff_pctl`, `rush_fd_att`, `rush_pg`, `rushtd_g`, `rushyd_pg`, `rz_tgt_share`, `separation_pctl`, `sis`, `sis_value_pctl`, `spike_pctl`, `success`, `surplus_TPRR`, `team_env`, `tgt_share_w`, `tgts_g`, `val`, `value_pctl`, `win_total`, `y2024`, `y2025`, `yac_pctl`, `yaco`, `yaco_pct`, `ypa`, `ypc`, `ypt`, `yptouch`

**Divergent consumers (read <40% of peer max — likely under-using the layer):** `boomutil.py`

### `boom/team_env.json`  (5 fields, 10 consumers)
| consumer | # fields read |
|---|---|
| build_dossier.py | 2 |
| build_flags_QB.py | 3 |
| build_flags_RB.py | 3 |
| build_flags_TE.py | 3 |
| build_flags_WR.py | 3 |
| build_intel.py | 4 |
| build_lever_calendar.py | 1 |
| build_lever_count.py | 1 |
| build_offense_profile.py | 5 |
| build_player_explorer.py | 0 |

### `boom/upside_cases.json`  (20 fields, 0 consumers)

**Unused by ALL consumers:** `amps`, `boom_games`, `booms`, `ceiling`, `cspec`, `ev`, `fa`, `insight`, `killers`, `name`, `narrative`, `pos`, `rate`, `ratio`, `scheme`, `skills`, `splits`, `stack_qb`, `team`, `tier`

### `boom/upside_correlations.json`  (3 fields, 1 consumers)
| consumer | # fields read |
|---|---|
| correlate_upside.py | 3 |

### `cc_context.json`  (47 fields, 4 consumers)
| consumer | # fields read |
|---|---|
| build_dossier_deep.py | 7 |
| command_center.py | 1 |
| ctx_panel.py | 1 |
| dfs_model.py | 6 |

**Unused by ALL consumers:** `adot25`, `align_pct`, `deep_ball_sh`, `deep_route_sh`, `dials`, `man_route_sh`, `man_zone_delta`, `metric`, `outside_run_sh`, `qb_anya`, `qb_cpoe`, `qb_epa_db`, `qb_pressure_rate`, `qb_rush_ypg`, `qb_scramble`, `qb_ttt`, `rb_rec_ypg`, `rb_topspeed`, `rec_croe`, `rec_epa_route`, `rec_separation`, `rec_yacoe`, `route_pct`, `route_tprr`, `route_yprr`, `routes_2yr`, `rush_epa_att`, `ryoe_att`, `self_moves`, `tgt_share`, `weeks`, `yoy`, `ypa25`, `yprr_man`, `yprr_zone`, `zone_run_sh`

### `coordinator_changes_2026.json`  (11 fields, 5 consumers)
| consumer | # fields read |
|---|---|
| build_coordinator_scheme.py | 7 |
| build_def_profile.py | 3 |
| build_dossier.py | 5 |
| build_intel.py | 3 |
| build_scheme_fit.py | 5 |

**Unused by ALL consumers:** `dc_source`, `src`

### `coordinator_notes.json`  (8 fields, 4 consumers)
| consumer | # fields read |
|---|---|
| build_features.py | 0 |
| build_intel.py | 8 |
| personnel.py | 8 |
| team_review_render.py | 0 |

**Divergent consumers (read <40% of peer max — likely under-using the layer):** `build_features.py`, `team_review_render.py`

### `coordinator_scheme_2026.json`  (10 fields, 4 consumers)
| consumer | # fields read |
|---|---|
| build_def_profile.py | 5 |
| build_lever_calendar.py | 3 |
| build_lever_count.py | 4 |
| build_scheme_fit.py | 6 |

**Unused by ALL consumers:** `oc_new`, `sack_rate_2025`, `verified`

### `defense.json`  (19 fields, 11 consumers)
| consumer | # fields read |
|---|---|
| boom_foundation.py | 1 |
| build_def_profile.py | 4 |
| build_defense_splits.py | 3 |
| build_flags_layer.py | 3 |
| build_intel.py | 9 |
| build_lever_calendar.py | 2 |
| build_lever_count.py | 4 |
| build_team_scout.py | 1 |
| command_center.py | 16 |
| fusion.py | 3 |
| sync_boom_defense.py | 2 |

**Unused by ALL consumers:** `pass_cov_rate_2026`, `pass_rush_rate_2026`, `run_def_rate_2026`

**Divergent consumers (read <40% of peer max — likely under-using the layer):** `boom_foundation.py`, `build_defense_splits.py`, `build_flags_layer.py`, `build_lever_calendar.py`, `build_team_scout.py`, `fusion.py`, `sync_boom_defense.py`

### `defense_splits.json`  (24 fields, 4 consumers)
| consumer | # fields read |
|---|---|
| build_defense_splits.py | 24 |
| build_home.py | 0 |
| dfs_model.py | 13 |
| render_dfs_week.py | 0 |

**Divergent consumers (read <40% of peer max — likely under-using the layer):** `build_home.py`, `render_dfs_week.py`

### `dfs_review/out/defense_2026_matchup.json`  (2 fields, 5 consumers)
| consumer | # fields read |
|---|---|
| boom_foundation.py | 2 |
| build_cc_context.py | 2 |
| build_splits.py | 2 |
| build_team_scout.py | 2 |
| sync_boom_defense.py | 2 |

### `dfs_scenarios.json`  (1 fields, 2 consumers)
| consumer | # fields read |
|---|---|
| command_center.py | 1 |
| dfs_scenarios.py | 1 |

### `dfs_week.json`  (7 fields, 2 consumers)
| consumer | # fields read |
|---|---|
| dfs_model.py | 7 |
| render_dfs_week.py | 2 |

### `division_splits.json`  (3 fields, 2 consumers)
| consumer | # fields read |
|---|---|
| build_division_splits.py | 3 |
| build_dossier.py | 2 |

### `dossier_data.json`  (1 fields, 6 consumers)
| consumer | # fields read |
|---|---|
| build_dossier_deep.py | 1 |
| build_flags_layer.py | 1 |
| build_lever_board.py | 1 |
| build_lever_calendar.py | 1 |
| build_lever_count.py | 1 |
| render_dossier.py | 0 |

### `engine/live_tree.json`  (20 fields, 2 consumers)
| consumer | # fields read |
|---|---|
| bb_grade.py | 18 |
| build_decision_dashboard.py | 20 |

### `features.json`  (1 fields, 13 consumers)
| consumer | # fields read |
|---|---|
| build_features.py | 1 |
| build_intel.py | 1 |
| correlate_upside.py | 1 |
| dfs_scenarios.py | 1 |
| fusion.py | 1 |
| ingest_advanced10.py | 1 |
| ingest_advanced2.py | 1 |
| ingest_advanced5.py | 1 |
| ingest_advanced9.py | 1 |
| ingest_defense.py | 1 |
| reproject_movers.py | 1 |
| reweight_defense_2026.py | 1 |
| validate_signal_stability.py | 1 |

### `flag_ranks.json`  (25 fields, 4 consumers)
| consumer | # fields read |
|---|---|
| audit_roster_moves.py | 4 |
| build_adp_clusters.py | 17 |
| build_big_board.py | 14 |
| build_rankings.py | 7 |

**Unused by ALL consumers:** `adj_order`, `nudge`, `scheme_fit`, `sf_adj`, `smq_pctl_adj`

**Divergent consumers (read <40% of peer max — likely under-using the layer):** `audit_roster_moves.py`

### `flags_2026.json`  (12 fields, 2 consumers)
| consumer | # fields read |
|---|---|
| build_lever_count.py | 4 |
| build_rankings.py | 9 |

**Unused by ALL consumers:** `adj_posrank`, `pg`, `proj_posrank`

### `fusion.json`  (1 fields, 3 consumers)
| consumer | # fields read |
|---|---|
| build_intel.py | 1 |
| build_rankings.py | 1 |
| command_center.py | 1 |

### `gameplan.json`  (4 fields, 3 consumers)
| consumer | # fields read |
|---|---|
| build_dossier.py | 1 |
| command_center.py | 3 |
| gameplan.py | 4 |

### `intel_data.json`  (2 fields, 7 consumers)
| consumer | # fields read |
|---|---|
| build_dossier.py | 2 |
| build_dossier_deep.py | 2 |
| build_intel.py | 2 |
| build_rankings.py | 1 |
| refresh_intel.py | 0 |
| render_intel.py | 2 |
| x_dossier_refresh.py | 2 |

### `lever_count.json`  (11 fields, 1 consumers)
| consumer | # fields read |
|---|---|
| build_lever_board.py | 10 |

**Unused by ALL consumers:** `best_wks`

### `offense_profile.json`  (26 fields, 1 consumers)
| consumer | # fields read |
|---|---|
| build_home.py | 1 |

**Unused by ALL consumers:** `adds`, `env_idx`, `environment`, `identity`, `lean`, `losses`, `motion`, `off_q`, `outlook`, `pace`, `pass_rate`, `passcatch`, `pctl`, `play_action`, `plays_pg`, `rank_band`, `run_scheme`, `scheme_dials`, `scheme_note`, `scramble`, `softness_band`, `vacated_tgt_pct`, `vertical`, `win_total`, `zone_rate`

### `personnel_changes.json`  (22 fields, 3 consumers)
| consumer | # fields read |
|---|---|
| build_offense_profile.py | 3 |
| command_center.py | 3 |
| personnel.py | 22 |

**Divergent consumers (read <40% of peer max — likely under-using the layer):** `build_offense_profile.py`, `command_center.py`

### `pipeline/correlation_structure.json`  (4 fields, 2 consumers)
| consumer | # fields read |
|---|---|
| dfs_model.py | 2 |
| gameplan.py | 1 |

**Unused by ALL consumers:** `all`, `low_total`

### `pipeline/team_volume_model.json`  (4 fields, 1 consumers)
| consumer | # fields read |
|---|---|
| dfs_scenarios.py | 0 |

**Unused by ALL consumers:** `intercept`, `score_diff`, `team_spread`, `total_line`

### `player_splits.json`  (5 fields, 0 consumers)

**Unused by ALL consumers:** `fav`, `man_lean`, `profile`, `tough`, `weeks`

### `profiles/player_profiles.json`  (34 fields, 3 consumers)
| consumer | # fields read |
|---|---|
| build_dossier.py | 5 |
| build_dossier_deep.py | 4 |
| dfs_model.py | 7 |

**Unused by ALL consumers:** `metric`, `rec_adot`, `rec_contested`, `rec_croe_pro`, `rec_drop`, `rec_dvoa`, `rec_epa_route_pro`, `rec_epa_tgt_pro`, `rec_man_qbr`, `rec_qbr`, `rec_rz`, `rec_rz_vol`, `rec_sep`, `rec_sep_pro`, `rec_short_routes`, `rec_slot`, `rec_success`, `rec_vman_ftn`, `rec_vzone_ftn`, `rec_wide`, `rec_yac`, `rec_yacoe_pro`, `rec_yprr`, `y2024`, `y2025`

### `scheme_2026.json`  (13 fields, 10 consumers)
| consumer | # fields read |
|---|---|
| build_cc_context.py | 7 |
| build_coordinator_scheme.py | 0 |
| build_def_profile.py | 1 |
| build_dossier.py | 8 |
| build_flags_layer.py | 6 |
| build_home.py | 6 |
| build_lever_calendar.py | 6 |
| build_lever_count.py | 6 |
| build_offense_profile.py | 4 |
| build_scheme_fit.py | 4 |

**Divergent consumers (read <40% of peer max — likely under-using the layer):** `build_coordinator_scheme.py`, `build_def_profile.py`

### `team_review_data.json`  (36 fields, 4 consumers)
| consumer | # fields read |
|---|---|
| gameplan.py | 15 |
| personnel.py | 10 |
| team_review_build.py | 36 |
| team_review_render.py | 31 |

### `team_review_rendered.json`  (6 fields, 1 consumers)
| consumer | # fields read |
|---|---|
| team_review_render.py | 1 |

**Unused by ALL consumers:** `passatt`, `passyd`, `plays`, `rushyd`, `td`

### `x_media.json`  (3 fields, 2 consumers)
| consumer | # fields read |
|---|---|
| build_dossier_deep.py | 1 |
| build_x_media.py | 3 |

### `x_narrative.json`  (6 fields, 2 consumers)
| consumer | # fields read |
|---|---|
| build_dossier_deep.py | 1 |
| build_x_narrative.py | 6 |

### `x_store.json`  (1 fields, 1 consumers)
| consumer | # fields read |
|---|---|
| build_pull_20260701.py | 0 |

**Unused by ALL consumers:** `posts`

## C. Orphan candidates

_None._

_Cleared by CURATED dynamic/subdir reads (needle re-verified this run; an entry drops back to orphan the moment its read is refactored away):_

- `engine/tree_schema.json` ← `engine/verify_decision_tree.py`
- `pipeline/byes_2026.json` ← `engine/bbengine.py`
- `pipeline/clay_2026_ud.csv` ← `engine/bbengine.py`
- `pipeline/games_by_week.json` ← `engine/playoff_overlay.py`
- `sis_value/cfb/cfb_passing_value_2024.csv` ← `build_rookie_profiles.py`
- `sis_value/cfb/cfb_passing_value_2025.csv` ← `build_rookie_profiles.py`
- `sis_value/cfb/cfb_receiving_value_2024.csv` ← `build_rookie_profiles.py`
- `sis_value/cfb/cfb_receiving_value_2025.csv` ← `build_rookie_profiles.py`
- `sis_value/cfb/cfb_rushing_value_2024.csv` ← `build_rookie_profiles.py`
- `sis_value/cfb/cfb_rushing_value_2025.csv` ← `build_rookie_profiles.py`
- `sis_value/pass_defense_2024.csv` ← `normalize_defense_2026.py`
- `sis_value/pass_rush_2024.csv` ← `normalize_defense_2026.py`
- `sis_value/run_defense_2024.csv` ← `normalize_defense_2026.py`

## Builders missing from the pipeline runner

- `build_profiles.py`
- `build_x_store.py`

## D. Fallback telemetry (silent gaps made loud)

- `fusion.json` · `missing_input_policy` = "Players missing a signal ABSTAIN on that vote: excluded from that signal's coverage count and from their own consensus/
- `boom/scheme_fit.json` · `new_dc_regressed` = ["BUF", "CLE", "DAL", "LAC", "LV", "MIA", "NYJ", "WAS"]
- `boom/scheme_fit.json` · `skipped` = {"no_bucket": 52, "no_pair": 66, "no_team": 6}

## E. Split-source files (P0 — one logical file, two drifting copies)

_None — every near-repo data file is read through a single access convention._
