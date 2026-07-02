# Best-Ball Pipeline — Consolidated Audit Findings

*Produced by six parallel read-only Fable auditors against `AUDIT_RUBRIC_SAFE.md`, then the four Critical findings were independently re-verified against the live files by the orchestrator. No files were modified and no pipeline stages were run during the audit.*

---

## Executive summary

The codebase is **secure and structurally sound** — the real risk here is not security (it's a local Python pipeline over public NFL stats) but **data-integrity**, and that risk is concentrated in two systems: **name-joins** and the **2026 defense/weighting layer**. Four Critical findings were traced *and* re-verified by me against the actual files:

1. **The 2026 pass-rush ratings are built on corrupted data** — the 2025 SIS `pass_rush.csv` column is a per-rush *rate* mislabeled as a counting stat, and the code divides it by snaps a second time. **This is the true root cause of "Myles Garrett lands at 0.1" and the Rams' pass rush being undervalued** — not a missing trade. *(Re-verified: 2025 file 13 cols, "Points Above Avg" range −0.06…0.14; 2024 file 14 cols, range −10.6…23.4.)*
2. **Two 2026 movers carry a 100% target share** (Chris Rodriguez Jr. `tgt_pg=32.9`, Greg Dortch `tgt_pg=32.0`) — physically impossible values live in `features.json` and feed DFS scoring. *(Re-verified.)*
3. **Two top-50 stars have blank usage** — DJ Moore (BUF) and Mike Evans (SF) join to nothing, yet are stamped `usage_src='2025_actual'` (false provenance). *(Re-verified.)*
4. **A private join key collides A.J. Brown with Amon-Ra St. Brown** in `build_layer2.py` — one star silently gets the other's usage-variance. *(Verified by the auditor; collision reproduced.)*

**Cross-cutting theme:** #1 systemic risk is **name-join fragility** — it independently produced Critical/High findings in four of the six audits (DJ Moore/Evans, A.J./Amon-Ra, the hyphen bug in `team_review_build.py`, the 2025-only-player drop in `build_chart2yr.py`, ~28 drifting private `fn()` copies). This is the recurring bug class the project has been fighting; it is not yet contained.

**Security: effectively clean.** No committed secrets, no injection surface, no path traversal, real dependencies, and the admin/rebuild endpoint is properly auth-gated and passes no caller input to the shell. One Low (a token file lacks a `.gitignore` rule).

**Answers to your specific questions** are in the last section (Rams defense, DVOA/PFF merge status, and a correction to what I told you about `off_q`).

---

## CRITICAL

### C1 — 2026 pass-rush ratings corrupted; elite pass-rush movers (Garrett, Hendrickson, Chubb) land at ~0
`sis_value/pass_rush.csv` (header) · `normalize_defense_2026.py:31,48-52,93` · `defense.json`
The 2024 SIS file has a counting `Points Above Avg` column (range −10.6…23.4); the **2025 file is missing that column** and the `Points Above Avg` header sits over a *per-rush rate* (range −0.06…0.14, median ~0). `normalize_defense_2026.py:52` then computes `rate = paa/snaps`, dividing an already-per-rush number by snaps again → Garrett = 0.08/474 ≈ **0.00017**, logged as `ps=0.1`. In `defense.json`, Garrett is tied with a 69-snap depth DE; Hendrickson→BAL, Chubb→BUF, Verse→CLE all land at `ps≈0.0`. Because unit strength = Σ(rate)/Σ(snaps), the method also **penalizes every-down elite players and rewards low-snap rotations**. A corrected-scale recompute scrambles team pass-rush percentiles by up to ±19 points (BAL 26.6→7.8, KC 60.9→76.6, LAR 67.2→54.7). Blast radius: `opp_pass_rush_pctl` → DFS QB-fade scoring, lever `rushStr`, dossier. Rookie pass-rush curve is also poisoned (pools the corrupted 2025 rates → rookie rate 0.0).
**Fix (propose):** detect the 13-column 2025 layout and use the column directly as the rate (snaps from `Pass Rushes`), or re-pull with the counting column; add a scale assertion so a rate-shaped column can't enter the counting path again; recompute `defense.json`.

### C2 — `reproject_movers` gives two movers a 100% target share
`reproject_movers.py:23-27,60,67-73`
`pct()` does `v*100 if v<=1.0 else v`, but `clay_targ_pct` is already in percent. A mover with a legit 1% Clay share becomes 100%: **Chris Rodriguez Jr.** (WAS→JAX) `tgt_share=100, tgt_pg=32.9, rec_pg=21.9`; **Greg Dortch** (ARI→DET) `tgt_share=100, tgt_pg=32.0`. Both are live in `features.json` and top `boom/movers_reprojection.json`, feeding DFS opportunity scoring.
**Fix (propose):** drop the ≤1.0 auto-scaling (single known unit), or clamp shares to ~40% with a loud warning; regenerate features.

### C3 — Star movers silently dropped by the usage join, with false provenance
`core.py:114-130` (`match_usage`) · `reproject_movers.py:36-46`
`match_usage` hits 303/379. Misses at ADP≤100 include **DJ Moore (ADP 46, →BUF)** and **Mike Evans (ADP 50, →SF)**: the 2025 parquet has two `D.Moore`/`M.Evans` rows, both candidates score identically, and because both players changed teams the team-tiebreak can't fire → returns None → blank `tgt_pg/tgt_share`. Worse, the blank rows are stamped **`usage_src='2025_actual'`** (verified), so a missing join masquerades as real data. *(Re-verified: both blank, both stamped 2025_actual.)*
**Fix (propose):** break exact-score ties by dominant 2025 volume or resolve via pid/roster; distinguish "join miss" from "did not move" and reserve `2025_actual` for rows that actually carry usage.

### C4 — First-initial join key collides distinct stars (re-implemented normalization)
`pipeline/build_layer2.py:5-9,44-47`
Local `norm()` keys on `first_initial + '.' + lastname`: "A.J. Brown" and "Amon-Ra St. Brown" both → `a.brown`; "Jordan Love"/"Jeremiyah Love" both → `j.love`. `drop_duplicates(keep='last')` then hands one star the other's usage-CV (a sim-variance input). This is the exact collision `core.match_usage` documents fixing, re-introduced by a private normalizer.
**Fix (propose):** key on full `core.fn` + pos guard (or call `core.match_usage`); assert no duplicate keys before `.to_dict()`.

---

## HIGH

- **H1 — `build_chart2yr.py` structurally drops every 2025-only player.** `build_chart2yr.py:120-146` iterates 2024 exports only; 2025 data is merged *into* 2024 players. Result: 17 players at ADP≤120 with real 2025 games have `chart2=None` — Ashton Jeanty, Omarion Hampton, Emeka Egbuka, Colston Loveland, Tetairoa McMillan, TreVeyon Henderson — so they fall back to the weaker single-season path. *(These are second-year/2025-active players, not 2026 rookies; their FP charting exists and is discarded.)*
- **H2 — Private usage-join copy in `team_review_build.py` keeps the hyphen bug core already fixed.** `team_review_build.py:36-57` rebuilds the index without `.replace('-',' ')`, so **Jaxon Smith-Njigba (ADP 5.4)**, Croskey-Merritt, JuJu Smith-Schuster, et al. silently lose their usage block in `team_review_data.json`.
- **H3 — SIS mover mechanism carries one injury-tainted 2025 season with no shrinkage; 2024 data on disk goes unused.** `normalize_defense_2026.py:85-94`. Hendrickson→BAL carries a 182-snap injury year (his 514-snap/38.5-PS 2024 file exists but is only read for rookie curves). LAR's three-CB haul (McDuffie down year, Sneed 187-snap injury year) nets **−1.96 PAA → LAR coverage *falls* 64.1→57.8 after signing three starting CBs.** Even with C1 fixed, elite movers stay under-credited. *(This is the deeper half of your Rams question.)*
- **H4 — Vintage desync across the boom chain.** `flags_*.json` are 06-29; `statmenu.json` is 07-01; `flag_ranks.json` (consumed by the live-draft nudge) was rebuilt 07-01 from the **stale** 06-29 flags. 9 RBs at ADP≤120 carry seeded `hist=false` while today's statmenu has real base rates. Enabler: `build_draft_board.py` and `build_flag_ranks.py` are in *no* orchestrator (hand-run only).
- **H5 — Non-atomic writes on features + accumulator JSONs.** `features.csv` is truncate-in-place in 8 stages (a crash + `--from` resume silently loses rows; `integrity_check` compares column *sets*, never row counts). The big accumulators (`statmenu.json`, `dossier_data.json` 3.7 MB) use plain `json.dump` with `allow_nan=True`; a `NaN` pg would silently scramble the rank sort in `build_flags_layer.py:134`. The atomic writer (`refactor/featurestore.py` / `core.safe_json_dump`) exists but is unwired here. *(Latent — disk is clean today.)*
- **H6 — Stale shipped artifacts.** `lever_board.html`, `dossier.html`, `flags_2026.json`, `rankings.html`, and the Josh Allen calendar (all ~19:26) predate the final tempered `lever_count.json` (19:34). **162 of 243 lever-board rows differ** (pre-tempering numbers), and PO-COLD flag membership may be wrong. **Easiest fix in the whole report: re-run `python3 run_all.py`.**
- **H7 — The critical name-resolution machinery has zero tests.** `core.resolve/first_compatible/build_usage_index/match_usage` and `bbengine.canon()` — including the documented accept/reject table (ken/kenneth ✓, keenan/kaytron ✗) — are never asserted. `tests/test_names.py` covers only `fn`/`team_abbr`/`latest`.
- **H8 — `pytest` from repo root mutates a tracked file and errors on half the suite.** No pytest config, so collection picks up `switch_test.py` (writes tracked `boom/switch_audit.json` at import) and `pipeline/_wd_test.py` (runs 1500 sims, crashes on cwd-relative exec). The strongest behavioral tests (`refactor/tests/test_refactor.py`) pin `statlib.py`/`parse.py` — modules **production no longer imports** (live percentile logic is duplicated ~11 times and can drift untested).

---

## MEDIUM

- **M1 — `off_q` double-counts two QBs for 5 teams.** `boom_foundation.py:186-211`. `SKILL` includes QB, and ARI/ATL/CLE/MIN/PHI have two QBs inside their top-8 (ARI: Beck 15.4 + Brissett 12.5 → 3rd-best "offense," inflated by a QB who won't play). Feeds DST matchup flags and `team_env` `env_idx`. *(See correction in final section.)*
- **M2 — DVOA never landed as team data; the team table is a hardcoded 2025 string literal.** `build_def_profile.py:21-52` holds a 32×7 DVOA-FPAA table pasted inline (no source file, no refresh path). Player-level DVOA *is* merged (FTN CSVs → `profiles/player_profiles.json`), but only into the profile/deep-dossier layer, **not** the board rankings or boom flags. No standalone team-DVOA file exists anywhere (incl. uploads).
- **M3 — PFF defense grades pulled-but-unused.** `NFL-master/PFF/{2024,2025}/defense.csv, defense_coverage.csv, defense_run.csv` (+3 more) are referenced by no script. The PFF grades that could *cross-check the very defense unit corrupted by C1* sit unread.
- **M4 — `lev[:6]` cap silently drops the shootout lever (appended last).** `build_dossier.py:404`. Courtland Sutton (7 levers) loses shootout — the only high-volume WR/TE of 86 missing it, understating his scores. Order-dependent and silent.
- **M5 — Calendar diagnostics use un-adjusted scheme data.** `build_lever_calendar.py:25-42` reads raw shell/coordinator files while `build_lever_count.py` applies DC-new-team dials first, so the calendar's "man %ile" / "would light" annotations disagree with the scores they explain for 13 teams.
- **M6 — Three boom ingests overwrite good outputs with `{}` on a missing data root and exit 0.** `ingest_coverage.py`, `ingest_deep_pass.py`, `ingest_motion.py`. If `NFL-master/FP` isn't found, they write empty `coverage_split/deep_pass/motion.json` and every player silently loses those levers. (Fail-soft *with a destructive write* — beyond the sanctioned no-op.)
- **M7 — `integrity_check`'s defense-ordering guard is dead code.** `refactor/pipeline.py:69-74` fires on `reweight_defense_2026` but the pipeline runs `normalize_defense_2026`; the advertised invariant is unenforced.
- **M8 — `--from <typo>` runs zero stages and prints "pipeline OK".** `refactor/pipeline.py:76-88`. No validation that the stage name exists.
- **M9 — Non-atomic writes of `dossier_data.json`/`lever_count.json`** (dedup of H5 for the dossier chain) — `build_lever_count.py:208`, `build_dossier.py:551`, `build_flags_layer.py:153`.
- **M10 — off_q/env-idx and the mover mechanism carry undocumented magic weights** (e.g. `env_idx = (off_q+implied)/2`, lever `TIER/ACT_MIN/SMASH`, dfs_scenarios volume blends). Flag for derivation, not re-tuning.

---

## LOW / INFORMATIONAL

- **L1 — Nickname/alias misses:** Hollywood Brown (→ "Marquise Brown"; gamelog split across both keys), Kyle Williams NE (→ "Kyle T. Williams"). Propose a tiny explicit alias map, not looser fuzzy matching.
- **L2 — ~28 private `fn()` copies**, 13 missing core's whitespace-collapse; a full private duplicate of the fuzzy resolver in `bbengine.py`. Zero drift *today*, but H2/C4 are this class realized. Add a drift test asserting each module's key file == `core.fn`.
- **L3 — `X_BEARER_TOKEN.txt` has no `.gitignore` rule** (`x_fetch.ps1` reads a live bearer token from it). File doesn't exist today, but one `git add -A` from a committed credential. Add the rule.
- **L4 — Wildcard CORS default** (`api/app/config.py:33`, localhost, `allow_credentials=False`, documented "lock down in prod") — informational.
- **L5 — Determinism:** all three samplers are seeded; only string-set iteration order reaches output *layout* (column order, tag order), never ranked values.
- **L6 — Misc:** `derive_boom_threshold` can emit a `NaN` threshold on a single-observation position; `_bak_build_dossier_*.py` is git-tracked and 24 windows identical to the live (uncommitted-edits) `build_dossier.py` — edit-the-wrong-file risk; `normalize_defense_2026.py:22` `exec()`s a string-split of another script's source (fragile coupling).

---

## Checked and clean (verified sound)

- **Security:** `.env` and all credential files gitignored/untracked/never-committed; zero hardcoded secrets across four scans; zero `shell=True`/`eval`/`os.system`/`pickle`; all `subprocess` calls are list-form with fixed paths; no path traversal (whitelist datastore, regex-constrained params); admin/rebuild endpoint auth-gated with constant-time compare, fail-closed, and **no caller input to the shell**; all dependencies real/mainstream PyPI.
- **Determinism:** samplers seeded (`default_rng(3)`, `(11)`); no unseeded randomness on the output path.
- **Boundary handling:** `core.build_usage_index`, `pipeline/build_draft_board.py` (isotonic imputation, join report, fail-soft optional inputs), `gameplan` stack builder, `fusion`, all percentile helpers — empty/NaN-guarded.
- **Lever subsystem (this session's work) is correct:** tempering bounds provably in (0, 0.992] (no negative/overflow); `lever_type()` maps the new strings correctly with no substring collisions; **no double-activation** (0 duplicate lever types across 243 players); shootout non-degenerate (QB playoff-mean spread 0.00–1.80, stdev 0.37, 30 distinct values); deeppass join 58/58, None-handled; end-to-end recompute matches (Lamar W17 = 0.8351 → stored 0.84).
- **Coaching changes** are applied *and* numerically weighted (`build_coordinator_scheme.py`), not just listed.
- **Offensive movers** (apart from C2): Clay-share × new-team-volume with idempotency and provenance is sound; `tm_pass_att` correctly keyed to the 2026 team.
- **Orchestrator guards** (where wired): features csv/json column-desync assert, statmenu clobber/aug-key asserts, run_all/boom_pipeline exists+non-empty gates — all fail-loud.
- **On-disk health today:** features `meta.n == csv rows == 379`; zero `NaN`/`Infinity` literals in the shipped JSONs. The atomicity/NaN findings are latent write-path hazards, not present corruption.

## N/A (correctly skipped — do not re-run these)
SQL injection, IDOR, JWT/token crypto, password hashing, async teardown/race conditions, CORS-as-vuln — no database, user accounts, token issuance, or async surface exist in this batch pipeline.

---

## Answers to your specific questions

- **"The Rams should be the best defense / the Garrett trade wasn't included."** The trade *was* encoded — but **C1 (2025 pass-rush column corruption) + H3 (no shrinkage, injury-year snaps)** make elite pass-rush and coverage movers land at ~replacement level, so the *effect* is as if the Rams' additions never happened. That's the real, root-caused reason LAR isn't rating as elite. Fixing C1 + H3 is what actually moves the Rams.
- **"We pulled DVOA/PFF but never merged it."** Confirmed. **Team-level DVOA never landed** as a file (it's a hardcoded 2025 literal); player-level DVOA reaches only the profile layer, not rankings. **PFF defense grades are pulled-but-unused.** These are exactly the signals that could backstop the corrupted defense layer.
- **Correction on `off_q`.** I told you earlier it *excludes* the QB — that was wrong. `SKILL = ['QB','RB','WR','TE']`, so QBs **are** in the top-8 sum (M1). The ARI-94-vs-BAL-71 gap is therefore driven by skill-corps depth *plus* a two-QB double-count for a handful of teams, not a QB exclusion. Apologies for the earlier misread.

## Suggested fix order (highest value first)
1. **C1** (pass-rush column) + **H3** (shrinkage/snaps) — fixes the Rams and every defensive mover; biggest ranking impact.
2. **C2, C3, C4, H1, H2** — the name-join / mover data-corruption cluster (wrong values feeding rankings *now*).
3. **H6** — re-run `run_all.py` to un-stale the shipped boards (trivial).
4. **H5/M9** — route writes through `core.safe_json_dump`; add a row-count assert to `integrity_check`.
5. **H4** — fold `build_draft_board` + `build_flag_ranks` into an orchestrator with a vintage assert.
6. **H7/H8** — pytest config + tests for name-resolution and defense-reweight.
7. **M2/M3** — land team-DVOA as a versioned file; wire PFF defense grades as a cross-check.

*Every item above is a proposal. Per the sanitized rubric, nothing here was applied — name-resolution, pipeline-ordering, and weighting changes are explicitly human-judgment calls.*
