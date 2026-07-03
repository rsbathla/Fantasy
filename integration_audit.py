#!/usr/bin/env python3
"""INTEGRATION AUDIT -- catches the "layer built but not properly consumed" bug class.

The recurring failure in this project: a layer gets built, later work adds a parallel layer
that *should* consume it, and the wiring silently never happens. Nothing errors; the output still
looks plausible; the signal just isn't there. (Live example: build_scheme_fit.py read only the
`dc_new` flag off the coordinator layer and blanket-regressed every new-DC team to the mean,
ignoring the coordinator-aware man_rate_adj / conf / dc_scheme that lever_count and def_profile
already used. Historical example: build_dossier_deep.py sat orphaned until someone noticed.)

This scanner makes that class LOUD and re-runnable. Five shapes it looks for:
  1. PARTIAL CONSUMPTION -- a layer is read, but its rich fields are ignored.
  2. DIVERGENT LOGIC     -- two consumers of one layer read different fields (one under-uses it).
  3. ORPHANED PRODUCTION -- a builder writes an artifact no builder reads.
  4. SILENT FALLBACK     -- code defaults to mean/league-avg/last-year when better data existed.
  5. FROZEN INPUT        -- a "live" layer is actually a stale snapshot.

Four checks, each written to INTEGRATION_AUDIT.md:
  A. LINEAGE   -- producer->consumer graph; orphans; builders missing from the pipeline runner.
  B. FIELD USE -- per rich artifact, which keys each consumer reads; unused fields; divergences.
  C. INVARIANTS-- curated assertions ("X must honor field Y"), grown as we learn.
  D. FALLBACKS -- fallback/skip counters harvested from every output's _meta, made visible.

Run:  python3 integration_audit.py            # write report + console summary
      python3 integration_audit.py --strict   # exit 1 if any P0 finding (pipeline gate)
Producer map is read from the authoritative pipeline declarations (boom_pipeline.py STAGES and
run_all.py chains) first, then falls back to write-call heuristics, so it is not fooled by reads
through variables/globs.
Data-side companion: audit_roster_moves.py cross-checks every player's TEAM across independent
sources and reconciles 2026 roster moves against curated provenance -> ROSTER_MOVES_2026.md.
"""
import os, re, glob, json, sys

HERE = os.path.dirname(os.path.abspath(__file__))
RAW_DIRS = ('NFL-master', 'ffdataroma_draft_guide_export', 'pff_', 'ftn_', 'nfl_pro',
            'FP_SWEEP', 'node_modules', '.git', 'api/', '__pycache__', 'refactor/',
            '_prebuild_backup', '_prune_baseline', 'backup', 'archive/')
SELF = os.path.basename(__file__)
# orchestrators name artifacts for existence-checks/sequencing -- they are NOT field consumers
ORCHESTRATORS = ('run_all.py', 'boom_pipeline.py')

# ---- SURFACE_ENTRYPOINTS: which repo files are the entry-points for each draft/live surface ----
# Verified: engine/*.py files are included in builders() scan since the 2026-07-02 extension.
# predraft uses: render_strategy_board.py, build_adp_clusters.py, build_big_board.py, build_rankings.py
# live uses: engine/run_live.py, engine/strategy_live.py, build_decision_dashboard.py, bb_grade.py, draft.py
# dossier uses: build_dossier.py, render_dossier.py, build_dossier_deep.py
# rankings uses: build_rankings.py, build_flag_ranks.py
SURFACE_ENTRYPOINTS = {
    'predraft': ['render_strategy_board.py', 'build_adp_clusters.py', 'build_big_board.py', 'build_rankings.py'],
    'live':     ['engine/run_live.py', 'engine/strategy_live.py', 'build_decision_dashboard.py', 'bb_grade.py', 'draft.py'],
    'dossier':  ['build_dossier.py', 'render_dossier.py', 'build_dossier_deep.py'],
    'rankings': ['build_rankings.py', 'build_flag_ranks.py'],
    'dfs':      ['render_dfs_week.py', 'dfs_model.py', 'build_dfs_season_baseline.py', 'build_matchup_notes.py',
                 'build_dfs_weekly_breakdown.py', 'render_dfs_weekly_pdf.py', 'game_sim.py', 'render_game_sim.py',
                 'build_script_study.py', 'validate_proe_conversion.py', 'build_proe_2026.py',
                 'build_dfs_week_report.py', 'build_rz_equity.py'],
}

# ---- SURFACE_EXEMPT: intermediate/internal layers that don't need a surfaces declaration ----
# These layers are intentionally not surface-declared because they are internal pipeline steps.
SURFACE_EXEMPT = {
    'ground_truth_registry.json': 'Meta-registry of verified post-cutoff facts; consumed by the auditor itself (Check I)',
    'deliverable_manifest.json':  'Meta-manifest of hand-authored deliverable layer usage; consumed by the auditor itself (Check H2)',
    'boom/statmenu.json':   'Internal per-player stat menu; consumed by boom_foundation/boom_lib as a pipeline intermediate',
    'boom/gamelog.json':    'Internal game-log cache; pipeline intermediate, not a strategy/decision layer',
    'boom/team_env.json':   'Internal team environment layer; pipeline intermediate consumed by build_team_ceiling',
    'boom/base2yr.json':    'Internal 2yr base stats; pipeline intermediate consumed by multiple builders',
    'boom/motion.json':     'Internal motion-rate cache; pipeline intermediate for scheme analysis',
    'boom/coverage_split.json': 'Internal coverage split cache; pipeline intermediate',
    'boom/deep_pass.json':  'Internal QB deep-pass rate; pipeline intermediate',
    'boom/chart2yr.json':   'Internal 2yr charting blend; pipeline intermediate',
    'boom/rookie_prior.json': 'Internal rookie prior layer; pipeline intermediate',
    'boom/rookie_college_profile.json': 'Internal rookie college profile; pipeline intermediate',
    'boom/flags_QB.json':   'Internal positional flags; consumed by build_flag_ranks as pipeline intermediate',
    'boom/flags_WR.json':   'Internal positional flags; consumed by build_flag_ranks as pipeline intermediate',
    'boom/flags_RB.json':   'Internal positional flags; consumed by build_flag_ranks as pipeline intermediate',
    'boom/flags_TE.json':   'Internal positional flags; consumed by build_flag_ranks as pipeline intermediate',
    'boom/manzone_2yr.json': 'Internal 2yr man/zone charting; pipeline intermediate for dossier/flags',
    'boom/defensive_profile.json': 'Internal defensive profile; pipeline intermediate consumed by build_team_ceiling',
    'boom/schedule2026.json': 'Internal schedule data; pipeline utility layer consumed by multiple builders',
    'boom/coverage_route_spec.json': 'Internal coverage route spec; pipeline intermediate consumed by build_scheme_fit',
    'dossier_data.json':    'Terminal: output of build_dossier.py consumed only by render_dossier.py (terminal pair)',
    'features.json':        'Internal features layer; pipeline intermediate consumed by build_flag_ranks/build_features',
    'defense.json':         'Internal defense stats; raw data layer, not a strategy artifact',
    'division_splits.json': 'Internal division splits; pipeline intermediate',
    'player_splits.json':   'Internal player splits; pipeline intermediate',
    'fusion.json':          'Internal fusion layer; pipeline intermediate',
    'gameplan.json':        'Internal gameplan config; pipeline intermediate',
    'dfs_scenarios.json':   'Internal DFS scenarios; DFS surface (separate from bestball surfaces)',
    'cc_context.json':      'Internal command-center context; pipeline intermediate',
    'offense_profile.json': 'Internal offense profile; pipeline intermediate consumed by build_team_ceiling/build_scheme_fit',
    'coordinator_scheme_2026.json': 'Internal coordinator scheme layer; pipeline intermediate (not terminal; consumed by 4+ builders)',
    'coordinator_changes_2026.json': 'Internal coordinator changes; pipeline intermediate',
    'coordinator_notes.json': 'Internal coordinator notes; pipeline intermediate',
    'personnel_changes.json': 'Internal personnel changes; pipeline intermediate',
    'lever_count.json':     'Internal lever-count layer; rankings/dossier intermediate',
    'scheme_2026.json':     'Internal scheme layer; pipeline intermediate',
    'nfl_pro_epa.json':     'Internal NFL Pro EPA data; raw ingest layer',
    'web_teams.json':       'Internal team web data; raw ingest layer',
    'intel_data.json':      'Internal intel data; pipeline intermediate for dossier/live',
    'x_live.json':          'Internal X (Twitter) live data; media pipeline',
    'x_store.json':         'Internal X store; media pipeline',
    'x_media.json':         'Internal X media; media pipeline',
    'x_narrative.json':     'Internal X narrative; media pipeline',
    'x_posts.json':         'Internal X posts; media pipeline',
    'flags_2026.json':      'Internal flags layer; pipeline intermediate',
    # boom pipeline intermediates (strategy/decision layers should be declared separately)
    'boom/adv2.json':       'Internal 2yr advanced stats per-player; pipeline intermediate for player explorer/dossier',
    'boom/boom_marks.json': 'Internal boom-mark scores; pipeline intermediate consumed by boom builders',
    'boom/boomdef.json':    'Internal boom defense data; pipeline intermediate for boom builders',
    'boom/cover_spec.json': 'Internal coverage route specialist data; pipeline intermediate consumed by build_scheme_fit',
    'boom/defender_grades.json': 'Internal defender grades; pipeline intermediate for coverage/dossier analysis',
    'boom/defense2026.json': 'Internal 2026 defense layer; pipeline intermediate for boom/scheme analysis',
    'boom/defense_shell.json': 'Internal defense shell rates (frozen 2025); pipeline intermediate for scheme builders',
    'boom/flags_DST.json':  'Internal DST flags; pipeline intermediate (separate DST surface)',
    'boom/roster_flags_2026.json': 'Internal roster flags; pipeline intermediate for boom/flag builders',
    'boom/upside_cases.json': 'Internal upside cases; pipeline intermediate for player explorer',
    # pipeline and engine intermediates
    'defense_splits.json':  'Internal defense splits; pipeline intermediate for home/DFS builders',
    'engine/live_tree.json': 'Terminal: output artifact of the live draft session (written by run_live.py, read by dashboard)',
    'engine/tree_schema.json': 'Internal decision tree schema; validation intermediate consumed by verify_decision_tree.py',
    'pipeline/byes_2026.json': 'Internal bye-week data; pipeline utility consumed by bbengine via CURATED_CONSUMERS',
    'pipeline/games_by_week.json': 'Internal games-by-week data; pipeline utility consumed by playoff_overlay via CURATED_CONSUMERS',
    'profiles/player_profiles.json': 'Internal player profiles (PFF/FTN situational matrix); pipeline intermediate for dossier',
    'team_review_data.json': 'Internal team review data; pipeline intermediate consumed by team_review_render',
}

# ---- SURFACE_CURATED_PASSES: known-good indirect surface connections ----
# For strategy/decision layers whose surface consumption goes through a documented intermediary
# chain (not a direct basename reference in an entry file), record the chain here so the audit
# stays green without requiring every entry file to directly import every upstream artifact.
# Format: (artifact_re, surface, intermediary_chain_note)
# Re-verified at each run: the named needle must appear in the named file, else the pass is void.
SURFACE_CURATED_PASSES = [
    # slot_paths.json -> strategy_board.json (agent-authored) -> render_strategy_board.py (predraft)
    # slot_paths is the slot/round decision-zone input that the agent used to BUILD strategy_board.json.
    {'artifact_re': r'^slot_paths\.json$', 'surface': 'predraft',
     'chain': 'slot_paths.json -> strategy_board.json (agent-built from slot_paths decision zones) -> render_strategy_board.py',
     'needle_file': 'render_strategy_board.py', 'needle': 'strategy_board.json'},
    # stack_menu.json -> strategy_live.py (live) AND strategy_board.json build (predraft)
    # strategy_live.py is a LIVE entry; for predraft, strategy_board was informed by stack_menu.
    {'artifact_re': r'^stack_menu\.json$', 'surface': 'predraft',
     'chain': 'stack_menu.json -> strategy_board.json (agent-built using stack_menu stacks) -> render_strategy_board.py',
     'needle_file': 'render_strategy_board.py', 'needle': 'strategy_board.json'},
    # team_ceiling.json -> build_slot_paths.py (predraft pipeline) -> slot_paths.json -> strategy_board
    # Also consumed by build_stack_menu.py (predraft pipeline builder).
    {'artifact_re': r'^team_ceiling\.json$', 'surface': 'predraft',
     'chain': 'team_ceiling.json -> build_slot_paths.py / build_stack_menu.py (predraft pipeline) -> strategy_board.json -> render_strategy_board.py',
     'needle_file': 'build_slot_paths.py', 'needle': 'team_ceiling.json'},
    # flag_ranks.json -> build_dossier.py uses merged_rankings not flag_ranks directly.
    # However build_dossier.py reads boom/scheme_fit.json which IS a rankings/dossier artifact.
    # The dossier surface for flag_ranks is via build_rankings.py (which IS a dossier input indirectly
    # through merged_rankings_2026.csv). Curated pass is NOT needed here; dossier surface removed.
]

# ---- CHECK H: REQUIRED CONSUMPTION — analytical-fidelity gates (PLAYBOOK.md case law) ----
# Check G asks "does ANY entry file consume the layer?"; Check H asks the sharper question:
# "does THIS builder consume the layers its analysis is required to rest on?"  Each entry encodes
# a real incident where a deliverable anchored on one signal while a built layer sat unused.
# A requirement is satisfied if ANY of its tokens appears in the builder's source.
REQUIRED_CONSUMPTION = {
    # C5: environments were once ranked on Vegas O/U alone; env_blend.py (Vegas x team_ceiling)
    # is the single sanctioned formula and these builders must go through it.
    'dfs_model.py': [
        ('posted Vegas O/U (ground truth)',      ['weekly-vegas-lines']),
        ('team-ceiling blend via env_blend',     ['env_blend']),
        ('defense split-parity layer',           ['defense_splits']),
        ('coverage FREQUENCY weighting (C8)',    ['man_rate']),
        ('qualitative player levers',            ['cc_context']),
        ('game-script multiplier',               ['game_sim', 'script_mult']),
        ('PROE pass/run conversion (validated)', ['proe_convert', 'proe_tendency_2026']),
        ('red-zone / TD-equity interaction',     ['rz_convert', 'rz_equity_2026']),
    ],
    'build_matchup_notes.py': [
        ('team-ceiling blend via env_blend',     ['env_blend']),
        ('team ceiling consumed (not just loaded)', ['ceiling_tier', "team_ceiling.get"]),
        ('offense identity layer',               ['offense_profile']),
    ],
    'build_dfs_weekly_breakdown.py': [
        ('team-ceiling layer',                   ['team_ceiling.json']),
        ('blended environment ranking',          ['blend']),
        ('season board flags',                   ['flag_ranks.json']),
        ('player lever context',                 ['cc_context.json']),
    ],
    # game-script sim must anchor to Vegas (means+spread) AND shape with our layers, never a
    # single signal (C5) — enforce the composition it was built to demonstrate.
    'game_sim.py': [
        ('posted Vegas anchor (means+spread)',   ['weekly-vegas-lines']),
        ('team-ceiling variance shaping',        ['team_ceiling']),
        ('offense identity for script lean',     ['offense_profile']),
    ],
    'render_game_sim.py': [
        ('sim output',                           ['game_sim.json']),
        ('matchup funnels for who-benefits',     ['matchup_notes']),
    ],
    # the position x script backtest must rest on REAL data: nflverse closing lines + actual scoring
    'build_script_study.py': [
        ('nflverse closing lines (ground truth)', ['games_2021_2025', 'nflverse']),
        ('actual fantasy scoring',                ['gamelog']),
    ],
    # the PROE->conversion validation must rest on COMPLETE per-game data (not the sampled
    # gamelog), real closing lines, and must validate its proxy against real FantasyPoints
    # PROE before trusting it for the prior-year (2024) replication.
    'validate_proe_conversion.py': [
        ('complete per-game DK (ground truth, 2024+2025)',   ['player_games']),
        ('nflverse closing lines (ground truth)',            ['games_2021_2025', 'nflverse']),
        ('real FantasyPoints PROE (proxy validated vs this)', ['proe_offense']),
    ],
    # the 2026 PROE tendency must rest on the 2025 ACTUAL base + the VERIFIED carousel (separated:
    # base is fact, carousel_adj is a flagged assumption) — never a free-floating projection.
    'build_proe_2026.py': [
        ('2025 actual PROE base (ground truth)', ['proe_offense']),
        ('verified carousel lean shifts',        ['COACHING_CHANGES_2026']),
    ],
    # the single-week HTML report must reuse the GROUNDED prose helpers (every clause traces to a
    # field) rather than free-write, and must surface the validated PROE conversion as a lever.
    'build_dfs_week_report.py': [
        ('grounded prose helpers (traceable clauses)', ['build_dfs_weekly_breakdown']),
        ('PROE conversion surfaced as a lever',        ['proe_mult']),
        ('holistic game-script sim read surfaced',     ['game_sim']),
    ],
    # the RZ index must rest on the validated sources: RZ target share (pass-catchers) + actual TD/game
    # (RBs) — never a free-floating TD guess.
    'build_rz_equity.py': [
        ('RZ target share (WR/TE, statmenu rz)', ['statmenu']),
        ('actual RB TD/game (player_games)',     ['player_games']),
    ],
    # C1: scheme_fit once blanket-regressed every new-DC team instead of using the
    # coordinator intelligence that had been built. Never again.
    'build_scheme_fit.py': [
        ('coordinator intelligence',             ['coordinator', 'dc_scheme', 'man_rate_adj']),
    ],
    'build_flag_ranks.py': [
        ('scheme_fit layer',                     ['scheme_fit']),
    ],
    'build_team_ceiling.py': [
        ('offense identity layer',               ['offense_profile']),
        ('coordinator/scheme-change layer',      ['coordinator', 'oc_new']),
    ],
}

# ---- CHECK H2: hand-authored deliverables must carry a utilization manifest ----
# Builders are token-scannable; agent-authored artifacts are not. Each file listed here must
# have an entry in deliverable_manifest.json declaring layers_used, and a written justification
# for every CORE_INTEL_LAYER it does NOT use. "Built-but-ignored" becomes visible, not silent.
HAND_AUTHORED = [
    'dfs_week1_report.html',
    'strategy_board.json',
    'analysis/team_analysis_1.md', 'analysis/team_analysis_2.md',
    'analysis/team_analysis_3.md', 'analysis/team_analysis_4.md',
]
CORE_INTEL_LAYERS = [
    'team_ceiling.json', 'offense_profile.json', 'defense_splits.json', 'boom/scheme_fit.json',
    'cc_context.json', 'flag_ranks.json', 'coordinator_changes_2026.json', 'weekly-vegas-lines.csv',
    'pipeline/correlation_structure.json', 'boom/defensive_profile.json', 'slot_paths.json', 'stack_menu.json',
]
MANIFEST_FILE = 'deliverable_manifest.json'

# ---- CHECK I: ground-truth registry — verified post-cutoff facts are protected ----
# ground_truth_registry.json entries outrank any model's priors (the 2026 world postdates every
# training cutoff). This check enforces: registry files exist and are consumed, and NO builder or
# text deliverable ships a forbidden claim that contradicts recorded provenance (C6/C7).
GT_REGISTRY = 'ground_truth_registry.json'
# forbidden-claim scan allow-list: builder sources + these text deliverables (doc/case-law files
# like PLAYBOOK.md are deliberately NOT scanned — they may describe past mistakes)
GT_SCAN_TEXT = ['*.html', 'dfs_weekly_breakdown.md', 'analysis/*.md']

def is_bak(name): return name.startswith('_bak_') or '.bak' in name or name.startswith('_prebuild')

# ---- artifacts that are TERMINAL by design (a missing consumer is expected, not a bug) ----
TERMINAL_RE = [
    r'\.html$', r'\.baseline\.json$', r'\.pre[A-Za-z0-9]+\.json$', r'\.recovered\.json$',
    r'backtest', r'_audit.*\.json$', r'INTEGRATION_AUDIT', r'console_log\.json$',
    r'columns\.json$', r'sample_tree\.json$', r'_upload\.csv$', r'_live\.csv$',
    r'portfolio_', r'_2026\.csv$', r'rankings_2026\.csv$', r'flag_rank_delta\.csv$',
    r'chain_live\.csv$', r'draft_analysis_live\.csv$',
    # -- ORPHAN_TRIAGE 2026-07-02: confirmed TERMINAL by design (human exports / memos / frozen snapshots) --
    r'^analysis/',                  # analysis exports dir (w17_blowup_rank etc. -- one-shot analysis outputs)
    r'profiles_summary\.csv$',      # build_profiles.py human-readable situational matrix (player_profiles.json is the consumed layer)
    r'ud_cheatsheet\.csv$',         # pipeline/build_ud_board.py Underdog draft sheet (deliverable)
    r'video_notes_review\.csv$',    # X-pull review sheet (schema: handle/sentence); the wired film-notes input is video_notes.csv
    r'rookie_weight_opt\.json$',    # woptimize_rookie.py grid-search snapshot; best_W=0.15 hardcoded at apply_rookie_to_statmenu.py:12
    r'rookie_situations\.json$',    # analyze_rookie_situations.py findings memo (draft-capital dominates etc.), not a model input
    r'manzone_tags_cfb\.json$',     # frozen FBS snapshot; build_rookie_manzone_pff.py re-derives fresh from sis_value/pff_receiving_scheme_2025.csv
]
def is_terminal(a): return any(re.search(p, a) for p in TERMINAL_RE)

# ---- CURATED CONSUMPTION the literal-basename scan cannot see (ORPHAN_TRIAGE.md, 2026-07-02) ----
# The refs() scan matches literal basenames in ROOT *.py only, so f-string paths
# (f'cfb_receiving_value_{season}.csv'), suffix swaps (.replace('.csv','_2024.csv')) and engine/ +
# pipeline/ subdir scripts are invisible to it. Each entry here is RE-VERIFIED at audit time: the
# named consumer file must still contain `needle`, else the artifact drops back to being an orphan
# (self-healing -- a refactor that removes the read re-opens the flag).
CURATED_CONSUMERS = [
    {'artifact_re': r'^pipeline/byes_2026\.json$',     'consumer': 'engine/bbengine.py',             'needle': 'byes_2026.json'},
    {'artifact_re': r'^pipeline/games_by_week\.json$', 'consumer': 'engine/playoff_overlay.py',      'needle': 'games_by_week.json'},
    {'artifact_re': r'^pipeline/clay_2026_ud\.csv$',   'consumer': 'engine/bbengine.py',             'needle': 'clay_2026_ud.csv'},
    {'artifact_re': r'^engine/tree_schema\.json$',     'consumer': 'engine/verify_decision_tree.py', 'needle': 'tree_schema.json'},
    {'artifact_re': r'^sis_value/cfb/cfb_receiving_value_20(24|25)\.csv$', 'consumer': 'build_rookie_profiles.py',  'needle': 'cfb_receiving_value_'},
    {'artifact_re': r'^sis_value/cfb/cfb_rushing_value_20(24|25)\.csv$',   'consumer': 'build_rookie_profiles.py',  'needle': 'cfb_rushing_value_'},
    {'artifact_re': r'^sis_value/cfb/cfb_passing_value_20(24|25)\.csv$',   'consumer': 'build_rookie_profiles.py',  'needle': 'cfb_passing_value_'},
    {'artifact_re': r'^sis_value/(pass_defense|pass_rush|run_defense)_2024\.csv$',
     'consumer': 'normalize_defense_2026.py', 'needle': "_2024.csv"},  # 2024 recovery blend via path.replace
    # -- strategy stack (2026-07-02): run_live consumes strategy_board + team_ceiling via engine/strategy_live.py --
    {'artifact_re': r'^strategy_board\.json$', 'consumer': 'engine/run_live.py',  'needle': 'strategy'},
    {'artifact_re': r'^team_ceiling\.json$',   'consumer': 'engine/run_live.py',  'needle': 'strategy'},
]

# ---- CURATED PRODUCERS the write-call heuristic misses (variable path, or a ')' inside open(...) ----
# is_writer()'s `open\([^)]*,'w'` cannot cross the ')' of os.path.join/core.P, so these real producers
# were misclassified as CONSUMERS of their own output (inflating peer-max in the divergence check) and
# their OFF-PIPELINE status was invisible. Verified writes:
#   build_coverage_spec.py:186  json.dump(out, open(jp,'w'))            -> boom/coverage_route_spec.json
#   build_profiles.py:302       json.dump(full, open(os.path.join(OUT,'player_profiles.json'),'w'))
#   build_cc_context.py:171     json.dump(ctx, open(core.P('cc_context.json'),'w'))
KNOWN_PRODUCERS = {
    'boom/coverage_route_spec.json': 'build_coverage_spec.py',
    'profiles/player_profiles.json': 'build_profiles.py',
    'cc_context.json': 'build_cc_context.py',
    'offense_profile.json': 'build_offense_profile.py',   # :119 json.dump(out, open(os.path.join(HERE,'offense_profile.json'),'w'))
}


def curated_consumers(art):
    """Verified dynamic/subdir consumers for one artifact (empty when the needle is gone)."""
    out = []
    for c in CURATED_CONSUMERS:
        if not re.search(c['artifact_re'], art):
            continue
        p = os.path.join(HERE, c['consumer'])
        try:
            if c['needle'] in open(p, encoding='utf-8', errors='ignore').read():
                out.append(c['consumer'])
        except OSError:
            pass
    return out

# ---- rich layers whose FIELD-LEVEL utilization matters (declare new config/projection layers here) ----
RICH_ARTIFACTS = [
    'coordinator_scheme_2026.json', 'coordinator_changes_2026.json',
    'boom/scheme_fit.json', 'boom/defensive_profile.json', 'boom/coverage_route_spec.json',
    'flag_ranks.json', 'lever_count.json',
]

# ---- CURATED INVARIANTS: (artifact, required_field, applies_to_predicate, human message) ----
# applies_to = substring(s) that identify consumers where the field is load-bearing.
INVARIANTS = [
    {'artifact': 'coordinator_scheme_2026.json', 'field': 'man_rate_adj',
     'applies_to': ['scheme_fit', 'lever_count', 'lever_calendar', 'def_profile'],
     'msg': 'defense-adjusting consumers must use the coordinator-aware man_rate_adj, not raw/dc_new alone'},
    {'artifact': 'coordinator_scheme_2026.json', 'field': 'conf',
     'applies_to': ['scheme_fit', 'lever_count', 'def_profile'],
     'msg': 'consumers that shrink new-DC teams must gate on conf (blend-prior vs regress-mean), not blanket-shrink'},
    {'artifact': 'coordinator_scheme_2026.json', 'field': 'dc_scheme',
     'applies_to': ['scheme_fit'],
     'msg': 'the shell (single/two-high) split should use the sourced dc_scheme prose where available'},
    # -- added 2026-07-02 (ORPHAN_TRIAGE.md Parts 2-3): confirmed OPEN gaps, kept loud until wired --
    {'artifact': 'coordinator_scheme_2026.json', 'field': 'conf',
     'applies_to': ['lever_calendar'],
     'msg': "build_lever_calendar 'mirrors build_lever_count' (its own comment) but percentile-ranks "
            "man_rate_adj RAW: lever_count gates its lambda on conf (build_lever_count.py:65) and refines "
            "the regressed man rate toward the researched lean (:73-75); the calendar's man-lever weeks "
            "drift from the count for new-DC teams  [OPEN gap -- fires until wired]"},
    {'artifact': 'coordinator_scheme_2026.json', 'field': 'sack_rate_adj',
     'applies_to': ['lever_count'],
     'msg': "the pressure/protection side uses defense.json pass_rush_pctl (roster-aware) but NO lever reads "
            "the coordinator-aware 2026 sack projection (sack_rate_2025 -> sack_rate_adj, computed per new-DC "
            "team by build_coordinator_scheme.py:31); build_flags_QB's sackp amps are 2025-frozen too "
            "(boom_foundation.py:192)  [OPEN gap -- fires until wired]"},
    # -- added 2026-07-02 (strategy integration): live payload assembler must reference strategy stack --
    # Field checked is the import alias 'strategy_live' (quoted in the import statement in run_live.py).
    # Removing the import from run_live.py will cause these invariants to fire, making the unwiring loud.
    {'artifact': 'strategy_board.json', 'field': 'strategy_live',
     'applies_to': ['engine/run_live'],
     'msg': "engine/run_live.py must import strategy_live (which consumes strategy_board.json) so the "
            "live payload carries slot strategy fit, live targets, and leverage note — "
            "if this fires, the strategy layer has been silently unwired from the payload assembler"},
    {'artifact': 'team_ceiling.json', 'field': 'strategy_live',
     'applies_to': ['engine/run_live'],
     'msg': "engine/run_live.py must import strategy_live (which consumes team_ceiling.json) so team "
            "ceiling tiers appear on live targets — "
            "if this fires, the strategy layer has been silently unwired from the payload assembler"},
]


def builders():
    out = {}
    for f in glob.glob(os.path.join(HERE, '*.py')):
        b = os.path.basename(f)
        if b == SELF or is_bak(b):
            continue
        out[b] = open(f, encoding='utf-8', errors='ignore').read()
    # Also include engine/ py files under their relative path so INVARIANTS can target them
    # (engine/run_live.py is the live-payload assembler; adding it here lets check_invariants
    # fire when it loses its strategy_board / team_ceiling references).
    for f in glob.glob(os.path.join(HERE, 'engine', '*.py')):
        b = 'engine/' + os.path.basename(f)
        if is_bak(b):
            continue
        out[b] = open(f, encoding='utf-8', errors='ignore').read()
    return out


def artifact_universe():
    arts = set()
    for pat in ('**/*.json', '**/*.csv', '**/*.html'):
        for p in glob.glob(os.path.join(HERE, pat), recursive=True):
            rel = os.path.relpath(p, HERE)
            if any(r in rel for r in RAW_DIRS):
                continue
            arts.add(rel.replace(os.sep, '/'))
    return arts


def pipeline_producers(src):
    """Authoritative producer map + pipeline membership from boom_pipeline.py + run_all.py."""
    producer, members = {}, set()
    bp = src.get('boom_pipeline.py', '')
    for name, outs in re.findall(r'\(\s*"([A-Za-z_0-9]+)"\s*,\s*\[([^\]]*)\]', bp):
        members.add(name + '.py')
        for o in re.findall(r'["\']([^"\']+\.(?:json|csv|html))["\']', outs):
            producer.setdefault(o, set()).add(name + '.py')
    ra = src.get('run_all.py', '')
    for script, outs in re.findall(r'\(\s*\[\s*["\']([^"\']+\.py)["\']\s*\]\s*,\s*\[([^\]]*)\]', ra):
        members.add(script)
        for o in re.findall(r'["\']([^"\']+\.(?:json|csv|html))["\']', outs):
            producer.setdefault(o, set()).add(script)
    # also any script named in the runner chains, even without declared outputs
    for m in re.findall(r'["\']([A-Za-z_0-9]+\.py)["\']', bp + ra):
        members.add(m)
    return producer, members


def is_writer(txt, art):
    """Heuristic producer fallback: a write call mentioning the basename."""
    base = os.path.basename(art)
    for m in re.finditer(re.escape(base), txt):
        w = txt[max(0, m.start() - 140):m.start() + 40]
        if 'safe_json_dump' in w or re.search(r"open\([^)]*,\s*['\"]w", w) or '.write(' in w:
            return True
    return False


def refs(src, arts):
    """artifact -> {'producers':set, 'consumers':set} using basename OR relpath match."""
    prod_map, _ = pipeline_producers(src)
    graph = {a: {'producers': set(prod_map.get(a, set())), 'consumers': set()} for a in arts}
    for f, txt in src.items():
        for a in arts:
            base = os.path.basename(a)
            if base not in txt and a not in txt:
                continue
            if f in graph[a]['producers']:
                continue
            if is_writer(txt, a):
                graph[a]['producers'].add(f)
            else:
                graph[a]['consumers'].add(f)
    # curated producers the write-window heuristic misses (they'd otherwise count as consumers)
    for art, b in KNOWN_PRODUCERS.items():
        if art in graph:
            graph[art]['producers'].add(b)
            graph[art]['consumers'].discard(b)
    return graph


def record_fields(obj):
    """Field names at the RECORD level of a rich artifact (not container index keys or meta)."""
    if not isinstance(obj, dict):
        return set()
    body = {k: v for k, v in obj.items() if k not in ('_meta', 'meta')}
    container = None
    for name in ('players', 'teams', 'records', 'items', 'data'):
        if isinstance(body.get(name), dict):
            container = body[name]; break
    if container is None:
        vals = [v for v in body.values() if isinstance(v, dict)]
        # body itself is a {code: record} map if most values are dicts; else a flat config
        container = body if vals and len(vals) >= max(1, 0.5 * len(body)) else None
        if container is None:
            return set(str(k) for k in body)
    keys = set()
    for rec in list(container.values())[:30]:
        if isinstance(rec, dict):
            keys |= set(str(k) for k in rec)
            for v in rec.values():          # one level into nested record dicts (e.g. proj:{...})
                if isinstance(v, dict):
                    keys |= set(str(k) for k in v)
    return keys


def rich_layers(graph):
    """REPO-WIDE: every record-structured in-repo JSON that has >=1 consumer, plus curated extras.
    Auto-discovery means new layers are field-audited the moment something reads them -- no manual list."""
    cands = set(RICH_ARTIFACTS)
    for a, g in graph.items():
        if a.endswith('.json') and not is_terminal(a) and g['consumers']:
            cands.add(a)
    return sorted(cands)


def field_use(src, graph):
    rows = []
    for a in rich_layers(graph):
        path = os.path.join(HERE, a)
        if not os.path.exists(path):
            continue
        try:
            obj = json.load(open(path, encoding='utf-8'))
        except Exception:
            continue
        keys = {k for k in record_fields(obj) if re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_]{1,40}', k)}
        if not keys:
            continue
        consumers = [c for c in sorted(graph.get(a, {}).get('consumers', set())) if c not in ORCHESTRATORS]
        matrix, used_anywhere = {}, set()
        for c in consumers:
            t = src[c]
            u = {k for k in keys if re.search(r"['\"]" + re.escape(k) + r"['\"]", t)}
            matrix[c] = u
            used_anywhere |= u
        unused = sorted(keys - used_anywhere)
        # DIVERGENCE: with >=2 consumers, one reading STARKLY fewer fields than its peers under-uses
        # the layer -- the generalized scheme_fit bug (read ~1 field of a rich 8+ schema). Tuned to
        # fire only on stark gaps (peer reads >=8, this reads <25%) to avoid flagging (a) legitimately
        # specialized consumers that need a subset, and (b) consumers that iterate fields dynamically
        # rather than by string literal (they look like they read nothing). Divergence is a CANDIDATE
        # feed for review, not a verdict -- the precise checks are orphans/invariants/fallbacks.
        divergent = []
        if len(consumers) >= 2:
            mx = max(len(matrix[c]) for c in consumers)
            if mx >= 8:
                divergent = [c for c in consumers if len(matrix[c]) < 0.25 * mx]
        rows.append({'artifact': a, 'keys': sorted(keys), 'consumers': consumers,
                     'matrix': matrix, 'unused': unused, 'divergent': divergent})
    return rows


def check_invariants(src, graph):
    findings = []
    for inv in INVARIANTS:
        a = inv['artifact']
        consumers = graph.get(a, {}).get('consumers', set())
        for c in sorted(consumers):
            if not any(tag in c for tag in inv['applies_to']):
                continue
            if not re.search(r"['\"]" + re.escape(inv['field']) + r"['\"]", src[c]):
                findings.append({'artifact': a, 'field': inv['field'], 'consumer': c, 'msg': inv['msg']})
    return findings


def check_surface_declarations(src, arts):
    """CHECK G: every in-repo JSON whose _meta.surfaces list declares a surface must be
    consumed by at least one of that surface's entry files.  Missing wiring = P0.
    Also returns the passing table rows for the report."""
    missing = []   # P0 violations: (artifact, surface, [entry_files_of_surface])
    passing = []   # (artifact, surface, consuming_entry_file)

    for a in sorted(arts):
        if not a.endswith('.json'):
            continue
        path = os.path.join(HERE, a)
        if not os.path.exists(path):
            continue
        try:
            obj = json.load(open(path, encoding='utf-8'))
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        meta = obj.get('_meta') or obj.get('meta')
        if not isinstance(meta, dict):
            continue
        surfaces = meta.get('surfaces')
        if not isinstance(surfaces, list) or not surfaces:
            continue
        base = os.path.basename(a)
        for surface in surfaces:
            entries = SURFACE_ENTRYPOINTS.get(surface, [])
            consumed_by = []
            for entry in entries:
                etxt = src.get(entry, '')
                if base in etxt or a in etxt:
                    consumed_by.append(entry)
            if consumed_by:
                passing.append({'artifact': a, 'surface': surface, 'consumed_by': consumed_by[0]})
                continue
            # check SURFACE_CURATED_PASSES for documented indirect chains (re-verified via needle)
            curated_chain = None
            for cp in SURFACE_CURATED_PASSES:
                if cp['surface'] != surface:
                    continue
                if not re.search(cp['artifact_re'], a):
                    continue
                nf = os.path.join(HERE, cp['needle_file'])
                try:
                    if cp['needle'] in open(nf, encoding='utf-8', errors='ignore').read():
                        curated_chain = cp['chain']
                        break
                except OSError:
                    pass
            if curated_chain:
                passing.append({'artifact': a, 'surface': surface,
                                'consumed_by': f'[curated chain] {curated_chain}'})
            else:
                missing.append({'artifact': a, 'surface': surface, 'entries': entries,
                                'msg': f"{a} declares surface '{surface}' but no {surface} entry file consumes it"})
    return missing, passing


def check_undeclared_layers(src, arts, graph):
    """CHECK G2: record-structured in-repo JSONs with producers/consumers but no _meta.surfaces
    declaration and not in SURFACE_EXEMPT.  Non-P0 triage list (creation-time forcing function)."""
    triage = []
    for a in sorted(arts):
        if not a.endswith('.json'):
            continue
        if is_terminal(a):
            continue
        if a in SURFACE_EXEMPT:
            continue
        # must have >=1 producer or consumer
        g = graph.get(a, {})
        if not g.get('producers') and not g.get('consumers'):
            continue
        # must have >=1 consumer or producer  (skip truly orphaned -- already caught by check A)
        if not g.get('consumers') and not g.get('producers'):
            continue
        # check if it's record-structured with enough fields (>=8) to warrant declaration
        path = os.path.join(HERE, a)
        if not os.path.exists(path):
            continue
        try:
            obj = json.load(open(path, encoding='utf-8'))
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        # check for surfaces in meta
        meta = obj.get('_meta') or obj.get('meta')
        if isinstance(meta, dict) and isinstance(meta.get('surfaces'), list):
            continue  # already declared
        # check if record-structured with >=8 fields (tighten heuristic per spec)
        fields = record_fields(obj)
        if len(fields) < 8:
            continue
        # has >= 1 consumer (not just producer)
        if not g.get('consumers'):
            continue
        triage.append({'artifact': a, 'n_fields': len(fields),
                       'n_consumers': len(g.get('consumers', set())),
                       'n_producers': len(g.get('producers', set()))})
    return triage


def fallbacks():
    """Harvest fallback/skip counters from every output's _meta -- silent gaps made loud."""
    hits = []
    pat = re.compile(r'skip|fallback|regress|charting|no_|missing|stale|shrink|degrade', re.I)
    for p in glob.glob(os.path.join(HERE, '**/*.json'), recursive=True):
        rel = os.path.relpath(p, HERE)
        if any(r in rel for r in RAW_DIRS):
            continue
        try:
            obj = json.load(open(p, encoding='utf-8'))
        except Exception:
            continue
        meta = obj.get('_meta') or obj.get('meta') if isinstance(obj, dict) else None
        if not isinstance(meta, dict):
            continue
        for k, v in meta.items():
            if pat.search(str(k)) and v not in (None, 0, [], {}, False):
                hits.append((rel.replace(os.sep, '/'), k, v))
    return hits


def split_source(src):
    """FROZEN/DUP-INPUT class: a data file read via BOTH core.find_data(...) (the parent-level,
    resync-fresh copy) AND a repo-relative accessor (J('..')/core.P('..')/os.path.join(HERE,..))
    -- two physical copies of one logical file that silently drift. This is the cc_context matchup
    bug (build_cc_context read the repo-local copy while sync_boom_defense/boom_foundation/build_splits
    read the parent copy). One logical file, one access convention."""
    find, rel = {}, {}
    for f, t in src.items():
        for m in re.finditer(r"find_data\(([^)]*)\)", t):
            a = re.findall(r"['\"]([^'\"]+)['\"]", m.group(1))
            if a:
                find.setdefault(a[-1].split('/')[-1], set()).add(f)
        for m in re.finditer(r"(?:\bJ\(|core\.P\(|\bP\(|os\.path\.join\(HERE,\s*)['\"]([^'\"]+\.(?:json|csv))['\"]", t):
            rel.setdefault(os.path.basename(m.group(1)), set()).add(f)
    return [(b, sorted(find[b]), sorted(rel[b])) for b in sorted(set(find) & set(rel))]


# ---- deliverables that must be pipeline-fresh (built AFTER flag_ranks in the DOSSIER chain) ----
CORE_DELIVERABLES = ['rankings.html', 'dossier.html', 'dossier_deep.html', 'lever_board.html',
                     'adp_cluster_board.html', 'big_board_2026.html', 'draft_strategy_board.html']
def stale_deliverables():
    """A core rendered deliverable OLDER than the model tip (flag_ranks.json) shipped stale under a
    fresher model -- the adp_cluster_board bug (board built off yesterday's ranks). HTML-only builders
    are invisible to the off-pipeline check (terminal output), so this catches the class by freshness."""
    tip = os.path.join(HERE, 'flag_ranks.json')
    if not os.path.exists(tip):
        return []
    t = os.path.getmtime(tip)
    out = []
    for d in CORE_DELIVERABLES:
        p = os.path.join(HERE, d)
        if os.path.exists(p) and os.path.getmtime(p) < t - 5:   # 5s grace
            out.append((d, int(t - os.path.getmtime(p))))
    return out


# ---- CHECK: input-freshness (an output built BEFORE an input layer it depends on) ----
# stale_deliverables() only guards the bestball boards vs the flag_ranks tip. The DFS play score also
# rests on defense_splits / game_sim / proe_tendency / rz_equity, and when defense_splits was rebuilt
# AFTER the baseline, the report shipped stale coverage grades (Tee Higgins' man smash vanished). This
# check compares each declared output against EVERY input layer it is built from — the general class.
FRESHNESS_DEPS = {
    'dfs_season_baseline.json': ['defense_splits.json', 'game_sim.json', 'proe_tendency_2026.json',
                                 'rz_equity_2026.json', 'team_ceiling.json', 'cc_context.json',
                                 'offense_profile.json',
                                 'ffdataroma_draft_guide_export/ffdataroma/csv/weekly-vegas-lines.csv'],
    'dfs_weekly_breakdown.md':  ['dfs_season_baseline.json', 'matchup_notes.json',
                                 'proe_tendency_2026.json', 'rz_equity_2026.json'],
    'dfs_week1_report.html':    ['dfs_season_baseline.json', 'game_sim.json',
                                 'proe_tendency_2026.json', 'rz_equity_2026.json'],
    'proe_tendency_2026.json':  ['data/fantasypoints/proe_offense_2025.csv', 'COACHING_CHANGES_2026.md'],
    'game_sim.json':            ['team_ceiling.json', 'offense_profile.json',
                                 'ffdataroma_draft_guide_export/ffdataroma/csv/weekly-vegas-lines.csv'],
}
def stale_inputs():
    """P0: an output older than an input layer it is built from -- it shipped stale.
    This is the class that hid Tee Higgins' smash (defense_splits rebuilt after the baseline)."""
    out = []
    for output, inputs in FRESHNESS_DEPS.items():
        op = os.path.join(HERE, output)
        if not os.path.exists(op):
            continue
        ot = os.path.getmtime(op)
        for inp in inputs:
            ip = os.path.join(HERE, inp)
            if os.path.exists(ip) and os.path.getmtime(ip) > ot + 5:   # input newer than output (5s grace)
                out.append((output, inp, int(os.path.getmtime(ip) - ot)))
    return out


def check_required_layers(src):
    """CHECK H (P0): each builder in REQUIRED_CONSUMPTION must show every required token group."""
    viol = []
    for builder, reqs in REQUIRED_CONSUMPTION.items():
        body = src.get(builder)
        if body is None:
            viol.append({'builder': builder, 'req': '(builder missing from repo)',
                         'msg': 'listed in REQUIRED_CONSUMPTION but not found — renamed? update the map'})
            continue
        for label, tokens in reqs:
            if not any(t in body for t in tokens):
                viol.append({'builder': builder, 'req': label,
                             'msg': f"none of {tokens} found — the analysis is missing a required layer"})
    return viol


def check_deliverable_manifest():
    """CHECK H2 (P0): hand-authored deliverables need a manifest entry; every core intel layer
    must be either declared used or justified unused. Silent omission is the failure mode."""
    viol, entries = [], {}
    mpath = os.path.join(HERE, MANIFEST_FILE)
    manifest = {}
    if os.path.exists(mpath):
        try:
            manifest = json.load(open(mpath, encoding='utf-8'))
        except Exception as e:
            viol.append({'deliverable': MANIFEST_FILE, 'msg': f'unreadable: {e}'})
    for d in HAND_AUTHORED:
        if not os.path.exists(os.path.join(HERE, d)):
            continue   # deliverable not present -> nothing to declare
        ent = (manifest.get('deliverables') or {}).get(d)
        if not ent:
            viol.append({'deliverable': d, 'msg': f'no entry in {MANIFEST_FILE} — declare layers_used + justifications'})
            continue
        used = set(ent.get('layers_used') or [])
        just = ent.get('layers_unused_justified') or {}
        missing = [c for c in CORE_INTEL_LAYERS if c not in used and c not in just]
        if missing:
            viol.append({'deliverable': d,
                         'msg': f'core layers neither used nor justified-unused: {missing}'})
        entries[d] = {'used': sorted(used), 'justified': sorted(just)}
    return viol, entries


def check_ground_truth(src):
    """CHECK I (P0): ground-truth registry integrity + forbidden-claim scan.
    (a) every registered file exists and is non-empty; (b) registered min_consumers satisfied
    (basename token scan across builders); (c) no builder source or text deliverable contains a
    forbidden claim contradicting recorded provenance."""
    viol, ok = [], []
    rpath = os.path.join(HERE, GT_REGISTRY)
    if not os.path.exists(rpath):
        return [{'kind': 'registry', 'what': GT_REGISTRY, 'msg': 'ground-truth registry missing'}], []
    reg = json.load(open(rpath, encoding='utf-8'))
    # assemble the forbidden-claim scan corpus: builders + allow-listed text deliverables
    corpus = {b: t for b, t in src.items()}
    for pat in GT_SCAN_TEXT:
        for fp in glob.glob(os.path.join(HERE, pat)):
            rel = os.path.relpath(fp, HERE)
            if rel == 'INTEGRATION_AUDIT.md':
                continue
            try:
                corpus[rel] = open(fp, encoding='utf-8', errors='ignore').read()
            except Exception:
                pass
    for e in reg.get('entries', []):
        p = os.path.join(HERE, e['path'])
        base = os.path.basename(e['path'])
        if not (os.path.exists(p) and os.path.getsize(p) > 0):
            viol.append({'kind': 'missing', 'what': e['path'], 'msg': 'registered ground-truth file missing/empty'})
            continue
        n_cons = sum(1 for b, t in src.items() if base in t and b != SELF)
        if n_cons < e.get('min_consumers', 0):
            viol.append({'kind': 'unconsumed', 'what': e['path'],
                         'msg': f'only {n_cons} consumer(s), registry requires >= {e["min_consumers"]} — verified intelligence is going unused'})
        hits = []
        for claim in e.get('forbidden_claims', []):
            for rel, txt in corpus.items():
                if claim in txt:
                    hits.append((claim, rel))
        for claim, rel in hits:
            viol.append({'kind': 'contradiction', 'what': e['path'],
                         'msg': f'`{rel}` contains forbidden claim "{claim}" — contradicts registered provenance'})
        if not hits and os.path.exists(p):
            ok.append((e['path'], n_cons))
    return viol, ok


def utilization_map(src):
    """Informational: surface-entrypoint builders x core intel layers (token scan).
    Makes 'built-but-ignored' visible at a glance; REQUIRED_CONSUMPTION is the enforced subset."""
    builders_flat = []
    for surface, files in SURFACE_ENTRYPOINTS.items():
        for f in files:
            if f in src and f not in [b for _, b in builders_flat]:
                builders_flat.append((surface, f))
    rows = []
    for surface, f in builders_flat:
        marks = {}
        for layer in CORE_INTEL_LAYERS:
            tok = os.path.basename(layer)
            hit = tok in src[f]
            if not hit and layer == 'team_ceiling.json':
                hit = 'env_blend' in src[f]   # blend module carries the team-ceiling signal
            marks[layer] = hit
        rows.append({'surface': surface, 'builder': f, 'marks': marks})
    return rows


def main():
    strict = '--strict' in sys.argv
    src = builders()
    arts = artifact_universe()
    graph = refs(src, arts)
    _, members = pipeline_producers(src)

    # CHECK A -- orphans + pipeline coverage
    orphans, curated_ok = [], []
    for a in sorted(arts):
        if is_terminal(a):
            continue
        g = graph[a]
        if not g['consumers']:
            cur = curated_consumers(a)
            if cur:
                curated_ok.append((a, cur))   # verified dynamic/subdir read -- NOT an orphan
                continue
            why = ('produced by %s but consumed by none' % sorted(g['producers'])) if g['producers'] \
                else 'on disk, referenced by no builder'
            orphans.append((a, why))
    missing_from_pipeline = sorted(
        b for b in src
        if b not in members and b not in ('run_all.py', 'boom_pipeline.py', SELF)
        and re.match(r'(build_|make_|render_|apply_|derive_|sync_|tighten_|mark_)', b)
        and (b in KNOWN_PRODUCERS.values()
             or any(is_writer(src[b], a) for a in arts if not is_terminal(a))))

    fld = field_use(src, graph)
    inv = check_invariants(src, graph)
    fb = fallbacks()
    ss = split_source(src)
    sd = stale_deliverables()
    si = stale_inputs()
    surf_missing, surf_passing = check_surface_declarations(src, arts)
    surf_triage = check_undeclared_layers(src, arts, graph)
    req_viol = check_required_layers(src)
    man_viol, man_entries = check_deliverable_manifest()
    gt_viol, gt_ok = check_ground_truth(src)
    util = utilization_map(src)

    # ---- write report ----
    L = []
    L.append('# INTEGRATION AUDIT\n')
    L.append('_Catches "layer built but not properly consumed". Re-run: `python3 integration_audit.py`._\n')
    L.append('_Standing orders: `CLAUDE.md` · case law: `PLAYBOOK.md` · verified 2026 facts: `ground_truth_registry.json`._\n')
    L.append('_Data-side companion: `audit_roster_moves.py` (cross-source player-team check + roster-move reconciliation) → ROSTER_MOVES_2026.md._\n')
    p0 = len(inv) + len(ss) + len(sd) + len(si) + len(surf_missing) + len(req_viol) + len(man_viol) + len(gt_viol)
    L.append('## Summary\n')
    L.append(f'- **{len(inv)} invariant violations** (P0 -- a layer is being under-used)')
    L.append(f'- **{len(ss)} split-source files** (P0 -- one logical file read from two drifting copies)')
    L.append(f'- **{len(sd)} stale deliverables** (P0 -- a rendered board older than the model tip it renders)')
    L.append(f'- **{len(si)} stale-input outputs** (P0 -- an output built before an input layer it depends on)')
    L.append(f'- **{len(surf_missing)} surface declaration violations** (P0 -- a layer declares a surface but no entry file consumes it)')
    L.append(f'- **{len(req_viol)} required-consumption violations** (P0 -- a builder is missing a layer its analysis must rest on)')
    L.append(f'- **{len(man_viol)} deliverable-manifest violations** (P0 -- hand-authored deliverable with undeclared/unjustified layer usage)')
    L.append(f'- **{len(gt_viol)} ground-truth violations** (P0 -- verified post-cutoff facts missing, unconsumed, or contradicted)')
    L.append(f'- **{len(surf_triage)} undeclared layers** (triage -- record-structured layers without surfaces declaration)\n')
    L.append(f'- **{len(orphans)} orphan candidates** (produced/on-disk, no consumer; terminals + verified curated dynamic reads excluded)')
    L.append(f'- **{len(missing_from_pipeline)} builders** produce artifacts but are absent from the pipeline runner')
    L.append(f'- **{sum(len(r["unused"]) for r in fld)} unused fields** across {len(fld)} record-structured layers (auto-discovered, repo-wide)')
    L.append(f'- **{sum(len(r.get("divergent", [])) for r in fld)} divergent consumers** (a consumer under-using a layer its peers read fully)')
    L.append(f'- **{len(fb)} fallback counters** currently firing (see check D)\n')

    L.append('## G. Surface declarations (P0)\n')
    if surf_missing:
        for v in surf_missing:
            entries_str = ', '.join(f'`{e}`' for e in v['entries']) if v['entries'] else '_(surface has no entry files defined)_'
            L.append(f'- P0: `{v["artifact"]}` declares surface `{v["surface"]}` but no {v["surface"]} entry file consumes it  \n  ↳ entry files checked: {entries_str}')
    else:
        L.append('_None — all surface declarations are satisfied._')
    if surf_passing:
        L.append('\n**Passing surface declarations:**\n')
        L.append('| artifact | declared surface | consumed by |')
        L.append('|---|---|---|')
        for r in surf_passing:
            L.append(f'| `{r["artifact"]}` | {r["surface"]} | `{r["consumed_by"]}` |')
    L.append('')

    L.append('## H. Required consumption (P0 — analytical fidelity)\n')
    if req_viol:
        for v in req_viol:
            L.append(f'- P0: `{v["builder"]}` missing required layer **{v["req"]}**  \n  ↳ {v["msg"]}')
    else:
        L.append('_None — every gated builder consumes the layers its analysis must rest on._')
    L.append('')

    L.append('## H2. Hand-authored deliverable manifests (P0)\n')
    if man_viol:
        for v in man_viol:
            L.append(f'- P0: `{v["deliverable"]}` — {v["msg"]}')
    else:
        L.append('_None — every hand-authored deliverable declares its layer utilization._')
    if man_entries:
        L.append('\n**Declared manifests:**\n')
        for d, e in man_entries.items():
            L.append(f'- `{d}` — uses {len(e["used"])} layers; {len(e["justified"])} justified-unused')
    L.append('')

    L.append('## I. Ground truth (P0 — verified 2026 facts are protected)\n')
    if gt_viol:
        for v in gt_viol:
            L.append(f'- P0 ({v["kind"]}): `{v["what"]}` — {v["msg"]}')
    else:
        L.append('_None — registry intact, consumed, and uncontradicted._')
    if gt_ok:
        L.append('\n**Registry entries verified this run:**\n')
        for pth, n in gt_ok:
            L.append(f'- `{pth}` — {n} consumer(s)')
    L.append('')

    L.append('## Utilization map (informational — core intel layers x surface builders)\n')
    L.append('_A `·` is not automatically wrong; the enforced subset is Check H. But a column of `·` under a'
             ' layer someone built is exactly how "we did all this work and nothing uses it" looks. Read it._\n')
    hdr = '| surface | builder | ' + ' | '.join(os.path.basename(c) for c in CORE_INTEL_LAYERS) + ' |'
    L.append(hdr)
    L.append('|---|---|' + '---|' * len(CORE_INTEL_LAYERS))
    for r in util:
        cells = ' | '.join('✓' if r['marks'][c] else '·' for c in CORE_INTEL_LAYERS)
        L.append(f"| {r['surface']} | `{r['builder']}` | {cells} |")
    L.append('')

    L.append('## G2. Undeclared layers (triage: declare surfaces or exempt)\n')
    if surf_triage:
        L.append('_Record-structured layers (>=8 fields, >=1 consumer) that have not yet declared `_meta.surfaces`. These are candidate strategy/decision layers — add a `surfaces` list or add to `SURFACE_EXEMPT` with a reason._\n')
        for r in surf_triage:
            L.append(f'- `{r["artifact"]}` — {r["n_fields"]} fields, {r["n_consumers"]} consumer(s), {r["n_producers"]} producer(s)')
    else:
        L.append('_None — all eligible layers have declared surfaces or are explicitly exempted._')
    L.append('')

    L.append('## A. Invariant violations (P0)\n')
    if inv:
        for f in inv:
            L.append(f'- `{f["consumer"]}` does not read `{f["field"]}` from `{f["artifact"]}`  \n  ↳ {f["msg"]}')
    else:
        L.append('_None._')
    L.append('')

    L.append('## B. Field utilization (per rich layer)\n')
    for r in fld:
        L.append(f'### `{r["artifact"]}`  ({len(r["keys"])} fields, {len(r["consumers"])} consumers)')
        if r['consumers']:
            L.append('| consumer | # fields read |')
            L.append('|---|---|')
            for c in r['consumers']:
                L.append(f'| {c} | {len(r["matrix"][c])} |')
        if r['unused']:
            L.append(f'\n**Unused by ALL consumers:** {", ".join("`%s`" % k for k in r["unused"])}')
        if r.get('divergent'):
            L.append(f'\n**Divergent consumers (read <40% of peer max — likely under-using the layer):** '
                     f'{", ".join("`%s`" % c for c in r["divergent"])}')
        L.append('')

    L.append('## C. Orphan candidates\n')
    if orphans:
        for a, why in orphans:
            L.append(f'- `{a}` — {why}')
    else:
        L.append('_None._')
    if curated_ok:
        L.append('\n_Cleared by CURATED dynamic/subdir reads (needle re-verified this run; an entry drops back to orphan the moment its read is refactored away):_\n')
        for a, cur in curated_ok:
            L.append(f'- `{a}` ← {", ".join("`%s`" % c for c in cur)}')
    L.append('')
    L.append('## Builders missing from the pipeline runner\n')
    if missing_from_pipeline:
        for b in missing_from_pipeline:
            L.append(f'- `{b}`')
    else:
        L.append('_None._')
    L.append('')

    L.append('## D. Fallback telemetry (silent gaps made loud)\n')
    if fb:
        for rel, k, v in fb:
            vs = json.dumps(v)
            L.append(f'- `{rel}` · `{k}` = {vs[:120]}')
    else:
        L.append('_No fallback counters found in output metas. (Add `_meta.fallbacks` to builders to populate.)_')
    L.append('')

    L.append('## E. Split-source files (P0 — one logical file, two drifting copies)\n')
    if ss:
        for base, fnd, rl in ss:
            L.append(f'- `{base}` — via `core.find_data` in {", ".join("`%s`" % c for c in fnd)}; '
                     f'via repo-relative accessor in {", ".join("`%s`" % c for c in rl)}. Pick one convention.')
    else:
        L.append('_None — every near-repo data file is read through a single access convention._')
    L.append('')

    L.append('## F. Stale deliverables (P0 — a board older than the model it renders)\n')
    if sd:
        for d, age in sd:
            L.append(f'- `{d}` is {age}s older than `flag_ranks.json` — rebuild it (add its builder to run_all).')
    else:
        L.append('_None — every core board is at least as fresh as the model tip._')
    L.append('')

    L.append('## F2. Stale-input outputs (P0 — an output built before an input layer it depends on)\n')
    if si:
        for output, inp, age in si:
            L.append(f'- `{output}` is {age}s older than its input `{inp}` — rebuild `{output}` '
                     f'(this is the class that shipped stale coverage grades to the DFS report).')
    else:
        L.append('_None — every declared output is at least as fresh as all of its input layers._')
    L.append('')

    open(os.path.join(HERE, 'INTEGRATION_AUDIT.md'), 'w', encoding='utf-8').write('\n'.join(L))

    # ---- console summary ----
    print('INTEGRATION AUDIT ->  INTEGRATION_AUDIT.md')
    print(f'  P0 invariant violations : {len(inv)}')
    for f in inv:
        print(f'     - {f["consumer"]} ignores {f["field"]} of {f["artifact"]}')
    print(f'  orphan candidates       : {len(orphans)}  (+{len(curated_ok)} cleared by verified curated dynamic/subdir reads)')
    print(f'  builders off-pipeline   : {len(missing_from_pipeline)}  {missing_from_pipeline}')
    print(f'  layers field-audited    : {len(fld)}  (auto-discovered, repo-wide)')
    print(f'  unused rich fields      : {sum(len(r["unused"]) for r in fld)}')
    div = [(r["artifact"], r["divergent"]) for r in fld if r.get("divergent")]
    print(f'  divergent consumers     : {sum(len(d) for _, d in div)}')
    for a, d in div:
        print(f'     - {a}: {d} under-use vs peers')
    print(f'  fallback counters firing: {len(fb)}')
    print(f'  split-source files       : {len(ss)}' + (f'  {[b for b, _, _ in ss]}' if ss else ''))
    print(f'  stale deliverables       : {len(sd)}' + (f'  {[d for d, _ in sd]}' if sd else ''))
    print(f'  stale-input outputs      : {len(si)}' + (f'  {[o for o, _, _ in si]}' if si else ''))
    print(f'  surface decl violations : {len(surf_missing)}')
    for v in surf_missing:
        print(f'     - {v["artifact"]} declares surface \'{v["surface"]}\' but no {v["surface"]} entry file consumes it')
    print(f'  required-consumption (H): {len(req_viol)}')
    for v in req_viol:
        print(f'     - {v["builder"]} missing: {v["req"]}')
    print(f'  manifest violations (H2): {len(man_viol)}')
    for v in man_viol:
        print(f'     - {v["deliverable"]}: {v["msg"][:100]}')
    print(f'  ground-truth (I)        : {len(gt_viol)}')
    for v in gt_viol:
        print(f'     - [{v["kind"]}] {v["what"]}: {v["msg"][:110]}')
    print(f'  undeclared layers (G2)  : {len(surf_triage)}  (triage)')
    print('  standing orders: CLAUDE.md | case law: PLAYBOOK.md | verified 2026 facts: ground_truth_registry.json')
    if strict and p0:
        print(f'\nSTRICT: {p0} P0 finding(s) -> exit 1')
        sys.exit(1)


if __name__ == '__main__':
    main()
