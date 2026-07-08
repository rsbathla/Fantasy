# DELIVERY_DEEP_AUDIT.md — delivery + service layer, line-by-line

*Audit date 2026-07-05. Scope: `build_decision_dashboard.py`, `engine/run_live.py` + `engine/dk_parse.py`
(+ the `bb_grade.py`/`draft.py` launchers that front them), `build_rankings.py`, `build_team_preview.py`,
`render_dossier.py`/`build_dossier*.py`, `render_strategy_board.py`, `command_center.py`, `api/app/`.
Method: full source read of every file in scope; every guard exercised against a known-bad input
(C2); one live-board card re-derived clause-by-clause from raw layers (31/31); freshness
reconstructed from file mtimes + the strict gate (`integration_audit.py --strict`, currently exit 1
with 3 stale-input P0s: `dfs_season_baseline.json`, `game_sim.json`, `coordinator_scheme_2026.json`).
No code was changed; every fix is returned as a proposal (§6).*

---

## §1 · Neutral notes per surface (what each deliverable actually reads and renders)

**Live draft chain** (`DRAFT_FAST.bat`/`DRAFT_FULL.bat` → `bb_grade.py` → `draft.py` →
`engine/run_live.py` → `engine/live_tree.json` → `build_decision_dashboard.py` →
`decision_dashboard.html`). `run_live.py` parses the DK clipboard board (`dk_parse.py`),
reconstructs the 12-team field, grades via the Monte-Carlo survival chain (`bbengine.py` /
`decision_tree.py`, sims read directly from `pipeline/player_sim_distributions.csv`), then enriches
every candidate from twelve sources: `draft_board_signals.csv` (adp/rank/proj/p95/ceil_pct/cv/
spike/bye/W15-17/w17_blowup/adv_pct), `fusion_table.csv` (17-signal model card incl. `matchup_pctl`
= season SOS from the projected-2026 `defense.json`, opponent-correct per position — fusion.py:467-482),
`layer2_player_params.csv` (usage), `qual_summary.csv`, `overlays.csv` (flags), `qual_signal.csv`
(conviction), `video_notes.csv`, `intel_data.json`, `player_splits.json` (W15-17 FAV/TOUGH chips,
coverage softness × man/zone frequency — build_splits.py:26-28 uses `def_man_rate` percentiles),
`brain_intel.json` (forward-2026 only on cards, run_live.py:214-220; 2025 Signal/Noise log shown as
counts only), `boom/boom_marks.json` (joined at dashboard write), plus the advisory strategy layer
(`engine/strategy_live.py` ← `strategy_board.json`, `team_ceiling.json`, `stack_menu.json`).
`ctx_panel.py` injects the full `cc_context.json` 4-layer drilldown (splits+EPA/YoY, playcaller
fit, vacated/opportunity, W15-17 matchup) into the dashboard and `rankings.html`.

Guards present in this chain: field-completeness (run_live.py:298-311, compares captured picks vs
the pick clock, writes `state.board_warning`); zero-drafted hard stop (run_live.py:312-318,
`SystemExit`, previous dashboard untouched); atomic byte-verified writes for both the tree
(run_live.py:263-283) and the HTML (build_decision_dashboard.py:2021-2033); unreadable-tree retry
then exit 2 keeping the previous file (build_decision_dashboard.py:2066-2081; the incident class is
real — `engine/live_tree.json.corrupt_bak` exists); dashboard renders `state.board_warning` as a red
banner (line 756-761), untracked/dropped chips (817-839), and a brain freshness badge with `as_of`
(841-853).

**`build_rankings.py`** orders by `flag_ranks.json adj_rank` (the fused forward composite), enriched
from `merged_rankings_2026.csv`, `fusion.json`, `boom_marks`, `draft_board_signals.csv`,
`intel_data.json`, `flags_2026.json`; `rankings.html` is covered by the gate's `CORE_DELIVERABLES`
mtime check vs the `flag_ranks.json` tip (currently fresh: 21:59:54 vs tip 21:59:36, Jul 2).

**`build_team_preview.py`** fuses thirteen layers (web_teams canon, personnel_2026,
defensive_profile, nflpro_2025, scheme_2026, schedule2026, statmenu, brain_intel,
draft_board_signals, fusion_table, player_splits, defense_splits incl. `shell.man_rate` displayed
on the defensive-identity strip, game_sim). Section order: regime → QB → season environment →
defensive identity → per-player cards → Fantasy Verdict last (neutral-before-conclusion holds).
The season-environment strip is built from `game_sim.json` `vegas` totals/implied only;
`team_ceiling.json` is not loaded (ceiling-ish context enters only via statmenu `team_env` in the
footer). Hand-written `PROSE`/`READS` exist for ARI only; other teams render data-only with empty
prose boxes.

**Dossier chain** (`build_dossier.py` → `dossier_data.json` → `render_dossier.py` → `dossier.html`;
`build_dossier_deep.py` → `dossier_deep.html`) consumes the widest layer set in the repo, includes
a stale-artifact degradation (scheme-fit attaches only when its team matches the record's team —
build_dossier.py: "_sfview … a mismatch means a stale artifact -> degrade by omission"), and both
HTML outputs are in `CORE_DELIVERABLES` (currently fresh vs the tip).

**`render_strategy_board.py`** renders agent-authored `strategy_board.json` without regenerating it;
the hero band prints the ADP snapshot provenance and authored date from `_meta`, plus the
`capital_honesty` line (mean +4.7 picks ahead of ADP on 135 stack picks) and per-pick CAPITAL GAP
chips with the C2 sign fix. Its own docstring (lines 8-10) notes it re-renders each pipeline run
"so the mtime staleness gate passes."

**`command_center.py`** embeds fusion, dfs_scenarios, gameplan, personnel_changes, defense,
defensive_profile, boom_marks and the full `cc_context.json`; stamps build time only.

**`api/app/`** — see §5.

---

## §2 · Findings table

| # | Issue | Severity | Where | Evidence | Why it dents the edge |
|---|---|---|---|---|---|
| 1 | The on-the-clock TEXT summary omits the field-completeness warning, and the launcher discards the engine's stdout warning on success | **HIGH (P0-class)** | `bb_grade.py:113-144` (`summarize()` — no `board_warning` read), `bb_grade.py:176-183` (`subprocess.run(capture_output=True)`; stdout re-emitted only when `returncode != 0`), vs `engine/run_live.py:302-309` (guard prints + embeds warning) | Known-bad run (partial fixture, 10/55 picks captured): summary printed `BEST PICK → Puka Nacua ΔTitle +22.5` with **zero** warning; the tree itself carried `board_warning: "FIELD INCOMPLETE: captured 10 of 55 picks…"`. The artifact currently on disk is the same failure live: `engine/live_tree.json` has `board_warning` "captured 13 of 55" and headlines **Ja'Marr Chase at pick 56** (ADP 3 — uncaptured picks make drafted players look available) | This is the exact "recommends an already-drafted player" money-loser. `--fast` mode exists precisely to answer in text at the clock; the only surviving mitigation is the red banner inside the 600 KB dashboard, which the text user may never open |
| 2 | Dashboard "✓ data complete" banner is unconditional — an indicator that cannot fire | **HIGH** | `build_decision_dashboard.py:2014-2019` | `_banner = '✓ data complete · {:,} players · built {}'.format(nb, _ts)` — no condition. Known-bad tests: empty board → "data complete · 0 players"; embedded fictional sample → "data complete · 2 players". Both render the same green pill | C2 in its purest form: mis-calibrated reassurance. A partial/stale/sample board wears a green "complete" badge; the reader is anchored to trust before the neutral read |
| 3 | Banner time = HTML write time; the payload itself carries **no session timestamp** | **HIGH (structural)** | `build_decision_dashboard.py:2015` (`time.strftime` at write); `run_live.py` writes no `generated_at` (only `brain_meta.as_of`, line 254) | `live_tree.json` from a previous session re-rendered later (e.g. a manual `python3 build_decision_dashboard.py`) is stamped "built <now>" with no way to see the board state is old. `main()` (2061-2084) reads whatever `live_tree.json` exists, any age | A stale board surfaced as current is the delivery layer's cardinal sin; today's on-disk dashboard (fixture-vintage state from 03:17) already demonstrates the ambiguity |
| 4 | Silent EMBEDDED-sample fallback under the same green banner | MEDIUM-HIGH | `build_decision_dashboard.py:2064-2065` (`data = EMBEDDED_DATA; src = "EMBEDDED sample"` when `live_tree.json` missing), banner 2016-2019 | `src` reaches stdout only; the rendered HTML shows the fictional 2-player payload (Nico Collins headline, fabricated quote at line 101) as "✓ data complete · 2 players" | Fabricated-looking data with a green completeness badge; small board size is the only self-revealing cue |
| 5 | The live pricing spine (`draft_board_signals.csv`) sits outside every freshness net | MEDIUM (structural; zero measured drift today) | `pipeline/build_draft_board.py` absent from `run_all.py` and from `FRESHNESS_DEPS` / `CORE_DELIVERABLES` (integration_audit.py:695-748); mtimes: signals Jul 1 21:26 vs `player_sim_distributions.csv` Jul 5 02:17, `flag_ranks.json` Jul 2, `defense_splits.json` Jul 3 | Cards price from the CSV while `bbengine.load_board()` reads the sim CSV directly (engine/bbengine.py:429) — two vintages of the same quantity on one surface. Verified today: p95/cv/spike drift = 0.00 (Jul 5 sim rerun reproduced Jul 1 values), so currently benign | The day a sim/rank rebuild actually moves numbers, the dashboard's card metrics and the engine's deltas silently diverge and no check fires |
| 6 | `build_team_preview.py` consumes stale-flagged `game_sim.json` blind; preview covered by no freshness/manifest guard; footer date hardcoded | MEDIUM | `build_team_preview.py:34` (`GS = json.load(open(f'{HERE}/game_sim.json'))` — no guard); line 339 (literal "Built July 5, 2026."); `team_preview_*.html` absent from `FRESHNESS_DEPS`, `CORE_DELIVERABLES`, and `HAND_AUTHORED` (integration_audit.py:246-256, 695-734) despite embedded hand-written PROSE/READS/verdict | `game_sim.json` (Jul 3) is one of the 3 live stale-input P0s (input `offense_profile.json` rebuilt Jul 5 21:52). A preview rebuilt right now would render the season-environment strip from the pre-update sim, stamped with a hand-frozen date | Environment bars are the preview's pricing spine ("This is the part that prices everything" — its own prose); stale implied totals mis-price the buy list |
| 7 | `rankings.html` subtitle misstates the model's weights | MEDIUM | `build_rankings.py:71` ("2026 ceiling 50 / traits 25 / season matchup 25") vs `flag_ranks.json _meta.weights` = ceiling 0.30 / traits 0.35 / season_mq 0.35 (docstring lines 4-5 of the same file has it right) | Re-derived from `flag_ranks.json` directly | A shipped factual clause that doesn't trace to the data field (C7-adjacent); the owner calibrates trust in the composite on a wrong recipe |
| 8 | `playoff_up` proxies defense softness from opponent OFFENSE strength while the built defense layer sits unread | MEDIUM (C1-adjacent, honestly labeled) | `engine/playoff_overlay.py:42-47` ("pipeline/ ships no standalone defensive-rating table … DEFsoft[o] = -OFFz[o]", CAVEAT block) — but `defense.json` / `defense_splits.json` (real projected-2026, per-position) exist at repo root | `playoff_up` is displayed on every card/roster row (heat-colored) and enters tree tie-breaks; the honest caveat lives in a docstring the dashboard reader never sees | The W15-17 edge is the product's core thesis; its matchup term is the crudest signal in the chain while a purpose-built layer is one path-join away |
| 9 | Strategy-board renderer satisfies the mtime gate by re-rendering, without content re-validation | LOW (disclosed) | `render_strategy_board.py:8-10` ("re-renders it fresh each pipeline run (so the mtime staleness gate passes)"); no check of authored windows vs the CURRENT ADP file | Hero band does show snapshot provenance + authored date + capital-honesty line (render_strategy_board.py:439-457, 652-659) — honest disclosure | Over weeks of ADP drift the authored windows decay with only a vintage line as protection |
| 10 | Gate's freshness DAG is one hop deep | LOW (self-healing over successive strict runs) | `integration_audit.py:718-734`: `dfs_week1_report.html` deps list baseline/game_sim/proe/rz but not `offense_profile.json`; report (Jul 3 18:10) shows fresh while its input `dfs_season_baseline.json` is itself flagged stale | Transitive staleness surfaces only after the intermediate rebuilds | A "green" report can sit one hop above a red input between runs; strict exit 1 does force the chain to move, so this is a latency, not a hole |
| 11 | Headline wording "Best blended d on the board" while board rows show higher raw dTitle | LOW (traceable, explained) | current `live_tree.json`: headline Chase dTitle +5.5 vs board Bijan +6.8, Nacua +6.5; the `why` string does print the blend score (+0.133) and the needs/stack rationale | Every clause traces; the blend (needs + stack + deltas) is the intended semantic | A skim-reader may read "best d" as "best dTitle"; the score in parentheses is the disambiguator |
| 12 | Off-scope but adjacent: `build_week1_report.py:404` footer hardcodes "Built July 5, 2026", same pattern as #6 | LOW | build_week1_report.py:404 | literal string | same misleading-stamp class |

**Freshness verdict:** the pipeline deliverables (`rankings.html`, `dossier.html`, `dossier_deep.html`,
boards) are inside a working mtime net and are currently fresh; the strict gate correctly catches the
3 stale intermediates. The **live-draft chain and the team preview sit outside every net**: no
payload timestamp, an unconditional "complete" banner, an unguarded signals CSV, and a blind
`game_sim.json` read. Of the 3 flagged stale outputs, exactly one is consumed blind by an in-scope
deliverable builder: `game_sim.json` → `build_team_preview.py` (the DFS renderers that consume
`dfs_season_baseline.json` are themselves declared outputs in the gate's DAG and re-flag on rebuild).

**Forward-looking verdict:** clean. Board columns are all 2026-forward (proj/p95/spike/W15-17/
playoff_up/value-vs-ADP); brain cards are forward-2026-only by construction with the 2025 log
reduced to counts (run_live.py:214-220, verified in the payload); no "vs last year" cards anywhere
in scope. The dashboard is headline-first by design — justified under C4 (an explicitly contracted
dashboard, "Agent D / Contract 5"), with flags rendered before outlook inside each card; prose
deliverables in scope (team preview, dossier, strategy board) hold neutral-notes-before-conclusions.
The forward-looking discipline's real exposure is #1/#2: a *backward board state* (missing picks,
old session) presented as a current recommendation.

---

## §3 · Traced card — every clause to a data field (Puka Nacua, current `engine/live_tree.json`)

31/31 clauses re-derived exactly from raw sources (mechanical equality, script in audit log):

- adp 3.92 · rank 1.0 · proj 21.09 · ceiling 49.77 · ceil_pct 1.0 · cv 0.87 · spike 0.16 · bye 11 ·
  w15 DAL · w16 SEA · w17 LAR@TB · w17rank 99 · adv_pct 1.0 ← `draft_board_signals.csv` row (13 fields)
- value 2.9 = adp − rank (3.92 − 1.0, rounded) ← run_live.py:167
- playoff_up 0.939 ← `engine/playoff_overlay.csv`
- scouting "Bullish: the most efficient WR in football by YPRR…" ← `qual_summary.csv.summary`
- flag {risk, "Open NFL off-field review; early-season tail risk (survivable phase). §11"} ← `overlays.csv`
- conviction {score 1.0, 6 sources, 8 tweets} ← `qual_signal.csv`
- model card value 99.68 / ceiling 76.24 / matchup 85.1 / boom 99.5 / separation 55.41 (+12 more) ← `fusion_table.csv`
- usage tgt_share 0.31 · dk_pg 21.09 (+7 more) ← `pipeline/layer2_player_params.csv`
- splits profile [route-tech, big-play, YAC]; W15 DAL FAV "soft pass-D, zone-heavy" · W16 SEA TOUGH ·
  W17 TB FAV ← `player_splits.json`; the "why" clauses cross-check against `defense_splits.json`:
  DAL pass_cov_pctl 23.4 + man_rate 22.5% (soft, zone-heavy ✓), TB 4.7 + 23.5% (✓), SEA 64.1 (tough ✓)
  — coverage frequency present, not a bare rate (C8 satisfied on-card)
- brain n_sig/lean/fwd/tw/src26/coach ← `brain_intel.json` players entry, truncation caps per run_live.py:212-220
- dTitle 6.5 / dAdv 0.0 / dW17 9.9 ← `decision_tree` branch deltas harvested at run_live.py:154-158

No fabricated clause found on the traced card. (The card's one *systemic* caveat is #8: playoff_up's
matchup term is the labeled proxy.)

---

## §4 · Known-bad guard log (C2 — each guard demonstrated, or demonstrated missing)

| Guard | Known-bad input | Result |
|---|---|---|
| Field-completeness (run_live.py:302-309) | Full fixture truncated to 2 of 12 manager columns | **FIRED**: `board_warning` "FIELD INCOMPLETE: captured 10 of 55 picks…" in state; dashboard renders it red (code path 756-761) |
| Zero-drafted hard stop (run_live.py:312-318) | DK menu text ("Lobby/Lineups/Balance") with "On the clock: Pick 56" | **FIRED**: SystemExit, no tree written |
| Text-summary warning (bb_grade.py) | Tree containing `board_warning` | **DID NOT FIRE — no such guard exists** (finding #1); summary printed a clean confident pick |
| "✓ data complete" banner | Empty 0-player board; embedded fictional sample | **DID NOT FIRE — unconditional** (finding #2): green "data complete · 0 players" / "· 2 players" |
| Unreadable live_tree (build_decision_dashboard.py:2066-2081) | Persistent JSON corruption | Code-verified (6 retries → exit 2, previous file kept); incident precedent on disk: `engine/live_tree.json.corrupt_bak` |
| Stale-input gate (integration_audit.py:735-748) | Live repo state | **FIRING NOW**: 3 P0s, strict exit 1 |
| Atomic writes (run_live.py:263-283; dashboard 2021-2033) | Byte-verified read-back loops | Code-verified; both refuse to replace the good file on mismatch |

---

## §5 · api/app posture call

Deep-audited separately (all ~2,076 lines + liveness probes). **Verdict: DORMANT, and safely so.**
FastAPI is not even installed (`import fastapi` → ModuleNotFoundError); no process, no socket, no
systemd; zero code consumers repo-wide (only 5 markdown mentions); api/ untouched since Jun 19-30
vs daily repo activity. Security posture if it were started: wildcard CORS origins
(`config.py:33` `["*"]`, `main.py:82-89`) **but** `allow_credentials=False` and `run.sh` binds
127.0.0.1, so inert as shipped; read routes unauthenticated (fine for localhost/public-stat data);
admin router key-gated with constant-time compare and the rebuild endpoint 503-disabled until a key
is set; `subprocess.run` uses list argv from server config with **no request-derived input** (no
injection path) but no `timeout=`; job registry's claimed memory bound is dead code
(`_order` deque never read, `_jobs` never pruned — the untested-guard pattern again, unreachable
while dormant); no path traversal (6-file whitelist in `repositories/store.py:22-29`); errors don't
leak traces; **no stale-forever caching** — `store.py:62-79` mtime-stats on every call. One footgun:
`env_file=".env"` resolves against CWD (`config.py:24`), so launching from repo root instead of
`api/` would read the credential `.env` (keys discarded via `env_prefix`, but it shouldn't touch the
file at all). Tests (27) are well-aimed incl. a firing known-bad for the rebuild gate, but cannot
execute without deps.

**Options (owner call):** (A) productionize — only if the phone/web front-end is actually planned
this season; minimum: pin real CORS origins, auth on reads if bound off-localhost, subprocess
timeout, prune `_jobs`, non-reload supervised run. (B) **keep dormant untouched** — it cannot start
accidentally (deps absent), binds localhost, rebuild disabled; zero work, zero risk. (C) archive —
breaks nothing (zero consumers) but discards a clean, test-covered service that would be expensive
to recreate. **Recommendation: B during draft season; revisit A only with a concrete front-end.**

---

## §6 · Decision points (returned, not resolved)

1. **Surface the field warning on the text path** (fixes #1): (a) `summarize()` prints
   `state.board_warning` as its first line when present; (b) `bb_grade.main()` echoes captured
   stdout lines containing `FIELD INCOMPLETE` (or simply always streams the engine's stdout).
   Mechanical, no model semantics; recommend doing both, plus a `⚠` prefix on the BEST PICK line
   when the warning is set.
2. **Make the banner honest** (fixes #2/#3/#4): `run_live.py` stamps `tree['state']['generated_at']`
   (write-time UTC); `write_dashboard` renders GREEN only when `src == live_tree` AND no
   `board_warning` AND payload age < a threshold (e.g. 2h), AMBER "partial field" when the warning
   is set, RED "sample/stale data" for the embedded fallback or an old payload, always showing
   payload capture time rather than HTML write time. Schema addition + banner semantics → owner
   sign-off; recommend strongly, with the three known-bad cases from §4 as the acceptance tests.
3. **Extend the freshness net to the live chain and preview** (fixes #5/#6): add
   `FRESHNESS_DEPS['draft_board_signals.csv'] = ['pipeline/player_sim_distributions.csv',
   'pipeline/merged_rankings_2026.csv', 'pipeline/layer2_player_params.csv', 'dk_adp.csv']` and
   `FRESHNESS_DEPS['team_preview_ARI.html'] = ['game_sim.json', 'defense_splits.json',
   'brain_intel.json', 'personnel_2026.json']`; optionally add `pipeline/build_draft_board.py` to
   the `run_all.py` chain. Auditor-map change → propose to owner (it will turn the gate redder
   before it turns the repo greener).
4. **Fix the rankings subtitle** to read the weights from `flag_ranks.json _meta.weights` instead of
   a literal (fixes #7) — one-line mechanical fix; the correct values are already in the same
   file's docstring.
5. **playoff_overlay defense term** (fixes #8): replace `DEFsoft = -OFFz(opp)` with the real layer
   (`defense.json` `pass_cov_pctl`/`run_def_pctl`, or `defense_splits.json` by-pos) — this changes
   scoring semantics of `playoff_up`, so it is gated on the owner + a backtest/lever check per the
   weights rule; until then, consider printing the proxy caveat on the dashboard legend so the
   reader sees what the docstring says.
6. **Compute, don't hardcode, deliverable footer dates** (`build_team_preview.py:339`,
   `build_week1_report.py:404`).
7. **api/app**: adopt Option B (dormant) unless a front-end is scheduled; if A is ever chosen, the
   §5 minimum-hardening list applies.
