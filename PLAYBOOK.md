# PLAYBOOK.md — Case Law & Judgment for this Repo

*Written by the departing principal architect, 2026-07-03. Purpose: every rule in CLAUDE.md was
paid for with a real failure in this repo. This file records the incidents so my successors run
on judgment, not just compliance. Read once per session. Cite case numbers in reviews ("this is
a C5") — it keeps corrections short and unambiguous.*

The single meta-lesson, if you read nothing else: **the failures were never exotic.** Every one
was the model doing the *naturally easy* thing — trusting its priors, reaching for the one legible
signal, reproducing the format it saw last, restarting instead of reading. The repo's guardrails
exist because "try harder" does not survive a context window. Infrastructure does.

---

## §1 · The operating picture

Two products, one data spine. **Best-ball**: season-long drafts, ADP-anchored ranks
(`flag_ranks.json`), pick-#-specific strategies (`strategy_board.json`), the dossier. **DFS**:
week-parameterized model (`dfs_model.py`), season baseline, matchup notes, written weekly reports.
The spine: charting/EPA features → defense identity → team environment/ceiling → player composite →
deliverables. `run_all.py` rebuilds the chain; `integration_audit.py --strict` is the gate.

The user's working style, learned over many sessions: deep reasoning, real data only, prose
deliverables, hates re-litigating settled decisions, hates watching built work go unused, wants
large semantic changes confirmed before wiring. He reads carefully and catches subtle errors —
assume anything you ship will be checked.

---

## §2 · Case law

**C1 — The unconsumed coordinator layer** (genesis of the auditor).
`build_scheme_fit.py` blanket-regressed every new-DC team to the mean while a coordinator
intelligence layer (man-rate priors, scheme shells, confidence) sat fully built and unread.
*Pattern:* build intelligence, then default to the crude fallback anyway.
*Rule:* a layer that exists for a dimension MUST feed any analysis of that dimension.
*Tripwire:* audit Checks A/G (wiring), and now Check H pins scheme_fit → coordinator explicitly.

**C2 — The reassuring inverted indicator.**
The strategy board was reaching 5–6 picks ahead of market and the capital-gap chip — built to
expose exactly that — had a sign bug and showed green. The user caught it from a screenshot.
*Pattern:* a safety indicator that never fired on a known-bad case was never actually tested.
*Rule:* every guard ships with a demonstration that it fires (removal test / known-bad input).
*Tripwire:* post-mortem ritual (§5); Check G was verified by removal test the day it landed.

**C3 — The false ELITE from title-only churn.**
LAR rode an `oc_new` flag into the ELITE tier when the repo's own notes said the change was
title-only continuity. Gated now (`_TITLE_ONLY_CHURN_TEAMS`).
*Pattern:* a binary change-flag credited as real signal without corroboration.
*Rule:* change-flags feed kickers only when corroborated across sources (real play-caller change).
*Tripwire:* cross-source checks in `audit_roster_moves.py`; ceiling kicker gate in
`build_team_ceiling.py`.

**C4 — The dashboard that was asked to be a report. Twice.**
User asked for "actual breakdowns by week"; got an HTML dashboard. Asked again for "an actual
written report"; got dashboard-shaped output again before the correction landed.
*Pattern:* format anchoring — reproducing the artifact type you produced last, not the one asked for.
*Rule:* "analysis/breakdown/report" = written prose; neutral notes before conclusions; dashboards
only on explicit request. A format correction from the user is a standing rule from that moment.
*Tripwire:* CLAUDE.md §4 (loaded every session).

**C5 — Environments anchored on the O/U alone.**
"Best environments" were ranked purely by Vegas total while `team_ceiling.json` — pace, pass rate,
scheme upgrade, QB ascension, shootout script, built precisely to price upside conditions — went
unused. The user: "why did we do so much work on team dynamics... if team scores is only anchored
by vegas." Blending moved games up to 4 slots (ARI/LAC +4 on a 13-point spread; CIN/TB to #1).
*Pattern:* single-signal collapse — the most legible number quietly becomes the whole analysis.
*Rule:* environment = `env_blend.py` (Vegas anchor × ceiling adjustment). Both numbers always shown.
*Tripwire:* Check H requires `env_blend` in every environment-ranking builder; the Utilization map
makes any built-but-ignored column visible.

**C6 — Withholding the verified coaching carousel.**
The repo carried the real 2026 carousel in at least five layers — `coordinator_changes_2026.json`
(with `verified: true` + CBS source), `COACHING_CHANGES_2026.md` and two detail files,
`offense_profile.json` outlooks — plus a handoff doc stating the user's hard rule ("NEVER assume,
we're running with real data"). A session hit "John Harbaugh, Giants HC," judged it against its
own pre-2026 memory, declared the data scrambled, and suppressed it from a deliverable. The facts
were correct and one web search would have confirmed them.
*Pattern:* priors over verified data — exactly inverted authority; plus orientation docs unread.
*Rule:* the Prime Rule (CLAUDE.md §1). Verified repo facts outrank memory; search confirms, never
overrules; surviving conflicts get flagged to the user, never silently resolved.
*Tripwire:* `ground_truth_registry.json` + Check I (existence, consumption, contradiction scan);
audit console prints the standing-orders pointer every run.

**C7 — Calling the real Vegas lines a projection.**
The same skepticism ran the other way: the posted look-ahead O/U file was confidently described in
a shipped methodology section as a derived projection, "not live" market data. The user corrected
it: they are true posted look-ahead totals (ffdataroma pull, cross-checked against a sportsbook
screenshot).
*Pattern:* when data surprises you, the failure can be doubting real data as easily as accepting
bad data. Provenance is a fact to record, not to guess.
*Rule:* provenance lives in the registry with the user's attestation; deliverables state it from
there.
*Tripwire:* Check I forbidden-claims scan — the exact wrong phrases can no longer ship (it caught
three files on its first run, including the auditor author's own leftover docstring).

**C8 — The man-coverage mirage.**
"97th-percentile vs man meets a defense 81st-percentile soft vs man" — against a defense that
plays man 20% of the time. The headline smash evaporated once weighted by how often the coverage
actually occurs; the honest case (environment + ceiling + volume) remained.
*Pattern:* base-rate neglect — a per-snap rate treated as if exposure were uniform.
*Rule:* any "X is good against Y" claim requires Y's frequency. Strength × softness × exposure.
*Tripwire:* `edges_for()` frequency weighting (`freq_w`, `cov_rate`) + Check H pins `man_rate` in
`dfs_model.py`; smash requires ≥~league-average exposure.

**C9 — ADP leaking into DFS.**
A weekly DFS report used best-ball ADP to frame chalk/leverage. ADP is a season-long draft price;
weekly cost is salary + ownership, which don't exist until slates post.
*Pattern:* cross-domain signal leakage — a number from the adjacent product reused because it was
handy.
*Rule:* domain boundaries are explicit. Until salaries/ownership exist, "leverage" claims are
structural (bring-backs, buried implied totals) and labeled as such.
*Tripwire:* manifest justifications force the exclusion to be written down per deliverable.

**C10 — Anchoring the reader.**
Early report drafts led with "our take," then the games. The user wants the neutral per-game read
first so he can form his own slate before seeing conclusions.
*Rule:* notes → summary → picks, in that order, always.
*Tripwire:* CLAUDE.md §4; report templates already follow it.

**C11 — Restarting instead of reading.**
The recurring meta-failure: re-searching verified facts, re-deriving built layers, re-asking
settled questions. The user: "it seems like you keep restarting from scratch or anchoring and
it's quite frustrating."
*Rule:* first action on any substantive task is inventory: §3 below, `run_all.py --check`,
`INTEGRATION_AUDIT.md`, grep for the concept. Extend what exists; cite what you reuse.
*Tripwire:* this file; the Utilization map making existing layers visible per deliverable.

**C12 — The impossibility asserted without a probe.**
Asked to build a retrospective analyst-narrative layer, a session (this one) told the user
"historical X has no retrieval path from here" — declared an external capability impossible from
priors, with zero checking. One socket probe disproved it: the cloud sandbox reaches
`api.twitterapi.io`, `youtube.com`, `api.spotify.com` on :443. The true constraint was
credentials + where-it-runs, not possibility.
*Pattern:* C6 pointed outward — priors over the world, doubting a real capability instead of a
real fact. "Can't / impossible / no path" is the tell.
*Rule:* "impossible/can't/no path" about anything external is a Known-grade claim and ships only
after the cheapest existence probe (socket, `command -v`, dir listing, docs lookup). Cost: seconds.
*Tripwire:* OPERATING_MANUAL.md §9/§13; retrieval capability matrix recorded there. Before writing
an impossibility, probe first.

*Retrieval capability (verified 2026-07-08, cloud sandbox):* twitterapi.io / YouTube / Spotify all
reachable on :443. ffmpeg present; yt-dlp installable; no source API keys in env yet. The brain
pipeline (`brain_video.py`/`brain_article.py`) already ingests YouTube+podcasts+articles Mac-side.
Constraint = twitterapi.io key (paid) for the X half; free path = YouTube/podcasts via the Mac
pipeline. Respect the web-content restriction: user-directed API/key ingestion ≠ WebFetch
circumvention; when unsure, run the pull Mac-side where the pipeline is authenticated.

---

## §3 · The layers (what exists, so you never rebuild it)

| Layer | The question it answers |
|---|---|
| `features.csv` | per-player charting/EPA/usage feature spine (2yr) |
| `defense.json` / `boom/defensive_profile.json` | defense identity, funnels, fortress/soft axes |
| `defense_splits.json` | split-parity: man/zone/deep softness pctls + `shell.man_rate` (frequency!) + by-pos FPAA |
| `coordinator_changes_2026.json` / `COACHING_CHANGES_2026*.md` | VERIFIED 2026 carousel: OC/DC/HC, scheme priors |
| `scheme_2026.json` | which teams have a REAL play-caller change + offensive dials |
| `boom/scheme_fit.json` | player-route spec × 2026 W15-17 opponents (coordinator-aware) |
| `offense_profile.json` | 2026 offense identity: pace, pass rate, run scheme, motion, outlook |
| `team_ceiling.json` | team season-ceiling probability + drivers (env, pace, pass rate, scheme upgrade, QB ascend, tree, shootout) |
| `env_blend.py` | THE environment formula: Vegas O/U × team ceiling |
| `weekly-vegas-lines.csv` | TRUE posted look-ahead O/U / implied / spread, all 18 weeks (registry) |
| `flag_ranks.json` | ADP-anchored composite: ceiling/trait/season-matchup pctls, flags, RB opportunity |
| `cc_context.json` | per-player 4-layer drilldown: splits/YoY, scheme fit, opportunity/vacated, W15-17 matchup |
| `boom/opportunity.json` + vacated-targets CSVs | route %, alignment, vacated opportunity |
| `pipeline/correlation_structure.json` | real stack correlations (QB-WR1 r≈.35; bring-back by total) |
| `slot_paths.json` | pick-by-pick availability model per draft slot |
| `stack_menu.json` | best-ball stack windows (latest-safe picks) |
| `strategy_board.json` | 12 slots × 3 authored strategies, window contracts (manifested) |
| `dfs_season_baseline.json` | all-18-week DFS model output (play scores, freq-weighted edges, blended anchors) |
| `matchup_notes.json` | 272 game notes: attack angles, smash, pace, blend, stack take |
| `boom/roster_flags_2026.json` / `boom/oline_2026.json` | verified availability + OL tiers (single edit points) |
| `backtest_composite_2025.py` | the weight gate: does a signal beat ADP out of sample? |
| `ground_truth_registry.json` / `deliverable_manifest.json` | protected facts; hand-authored utilization declarations |
| `middle_funnel.json` (`build_middle_funnel.py`) | the MISSING horizontal axis: per-defense middle-of-field softness (EPA/CPOE allowed, funnel-vs-perimeter, softness_pctl) + per-receiver middle-win + exposure. `middle_edge(player,opp)` crosses them C8-style (strength×softness×EXPOSURE). Built 2yr from pbp `pass_location=middle`. TODO consume in the film-room weekly pack + buy-the-dip board (C1). Boundary: target-based, not all-route separation. |

---

## §4 · Pre-ship checklist (human half; the audit is the machine half)

1. `python3 integration_audit.py --strict` → exit 0. Read the Utilization map — is any layer you'd
   expect for THIS deliverable showing `·`? If deliberately unused, is it justified in the manifest?
2. Provenance: does every environment/matchup/coaching claim trace to a layer or the registry?
3. Format: prose? neutral-first ordering? both env numbers (O/U + blend) shown? no ADP in DFS?
4. Weights: anything new backtest-earned or labeled a stated prior with a revert flag?
5. Sanity: pick 2 items you wrote and re-derive them from raw JSON by hand (the Nabers-3-smash test).
6. Large semantic change since last user sign-off? Confirm before wiring, not after.

## §5 · The post-mortem ritual (how the ratchet turns)

When the user catches something — and he will — the fix is not an apology, it is infrastructure,
same day: (1) name the pattern (add a case above), (2) add the machine check to
`integration_audit.py`, (3) prove the check fires (removal test or known-bad input), (4) fix the
instance, re-run `--strict` to green. The auditor only catches what it has been taught; teaching
it immediately is what makes the same mistake structurally unrepeatable. Both prior extensions
(Check G, Checks H/I) caught real violations on their first run — that is the standard.

## §6 · Orchestration doctrine

Fable/orchestrator-class holds the conversation, decomposes work, and owns user-facing decisions.
`deep-reasoner` (Opus-class) takes bounded analytical subtasks: adversarial reviews, scheme
analysis, backtest design. `fast-worker` (Sonnet-class) takes mechanical sweeps: token scans,
format churn, bulk rebuilds. Every subagent prompt starts with `agents/SUBAGENT_PREAMBLE.md`
verbatim — an unbriefed model will re-commit C5/C6 by default; the preamble is what stands between
a fresh context and this repo's history. Subagents RETURN decision points; they never resolve
user-owned questions (weights semantics, spend, publishing, deletion) on their own.
