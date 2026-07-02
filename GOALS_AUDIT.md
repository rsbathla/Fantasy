# NFL Suite — Goals Audit (4 Fable agents, read-only) + Fix Plan

_Each of your four goals audited by an independent Fable agent, read-only. Headline claims re-verified by hand before writing this._

## TL;DR

The **analysis engine is more correct than feared** — but the **data plumbing and the board's phase-weighting have real, fixable gaps.** Nothing here is a rewrite; it's repointing paths, adding two terms, and building one missing feature.

- **Best-ball:** the survival-chain engine *does* correctly model advance-then-win (weeks 1–14 top-2, then weeks 15–17). The gap is that the **board/ADP-nudge layer prices only playoff-week schedule (weeks 15–17)** and ignores the weeks 1–14 matchup grades (which are already built) plus any accumulation term. Your instinct was right about the board.
- **DFS:** runs end-to-end today as a strong **who-to-play + stacking advisor**, but it is **not a lineup builder** — no salaries, no cap-valid optimizer, no DST, no ownership.
- **Dossier:** teaches well, but omits big ingested layers (the **PFF/FTN situational matrix**, **rookies**), and the **coverage-specialist layer is currently empty/broken**.
- **Data integrity (headline):** several **pulled data layers are silently dead** because the code reads a `Downloads` path (`{DL}`) that doesn't exist in this checkout; **~95% of the FP_SWEEP pull** and the **FTN defense pull** have no readers at all.

---

## Goal 1 — Best-ball model: regular season + playoffs

**What's correct (verified):** `pipeline/survival_chain.py` models the full season — `padv` = P(finish top-2 of 12 on cumulative weeks 1–14), then `title = padv × s15 × s16 × w17`. The decision tree even over-weights advancement early (`0.6·title + 0.4·adv`; playoff tilt only after round 7). So making the playoffs *is* modeled, and is the dominant early-round driver.

**The real gap (verified myself):** every *schedule/matchup* signal in the board layer is playoff-only. `build_flag_ranks.py` composite = **ceiling 0.50 / traits 0.25 / playoff_mq 0.25**, where `playoff_mq` is the mean of weeks **15–17 only**. The weeks 1–14 matchup grades exist in `boom/flags_*.json` (`weeks[].p`, all 18 weeks) but are read by **zero** ranking component — dashboards only. There is **no regular-season accumulation term** at all.

- Corr(mean week-1–14 grade, mean week-15–17 grade) = **0.978** — so the 3-week window mostly re-expresses the season grade with extra noise, *except* for the ~7 players where it wrongly tilts a 17-week asset.
- Side issues: the sim is matchup-agnostic in **both** phases (schedule never enters `p_adv`); **UD scoring never reaches the sim** (`BB_PROJ_COL` stays `dk_pg` full-PPR → inflates pass-catchers); `run_all.py` never rebuilds `flag_ranks.json` (can go stale).

**Fix:** add a weeks-1–14 matchup term + a mean-projection (accumulation) term to `build_flag_ranks.py`; optionally mirror `playoff_overlay.py` with an advancement overlay + early-round tilt in `decision_tree.py`; set `BB_PROJ_COL=ud_pg` for UD; wire `flag_ranks` into the rebuild chain.

## Goal 2 — DFS model: is it runnable?

**Runs today (agent executed it):** `python3 dfs_model.py --week 15` → `dfs_week.json` + `dfs_week.html` (216 players, 4 stack templates). Genuinely weekly (per-week opponents + Vegas lines), consumes FP/PFF/FTN/NFL-Pro/Vegas data, and has **real 2024–25 correlation-grounded stacking** (QB-WR1 r=0.351; bring-back only when total ≥ 45).

**The gap:** it's an **advisor, not a lineup builder** — no salary column, no cap-constrained optimizer (no ILP/solver anywhere), **DST excluded** from the pool, **no ownership/leverage data**. `dfs_scenarios.py` is hard-coded to weeks 15/16/17; `--week` has no validation (week 25 silently degrades).

**Fix:** add a DK-salaries input + a small ILP (`pulp`) over `dfs_week.json` (max play/ceiling s.t. $50k + roster slots, seeded from the stack templates); add DST from `boom/flags_DST.json`; ingest/estimate ownership; parameterize `dfs_scenarios.py` weeks; validate `--week`.

## Goal 3 — Dossier: all-encompassing for learning?

**Teaches well (verified structure):** archetypes, mechanism-phrased booms/busts, stability tiers with r-values (teaches which stats persist vs are noise), backtested analyst claims, per-team quiz, a **weeks 1–18 lever calendar** + a weeks 15–17 playoff grid, and a click-to-open 4-layer EPA panel.

**Missing ingested layers (biggest first):**
1. **`profiles/player_profiles.json`** — the PFF/FTN situational matrix (285 players × ~46 dims: man/zone, slot/wide, deep/short, contested, pressure/blitz/play-action). **This is where the PFF grades live and it never reaches the main dossier** (only the stale, orphaned `dossier_deep.html`).
2. **Rookies** — `rookie_prior/college_profile/db_grades` unused → 46 rookies sit with near-empty cards.
3. **`cover_spec.json` is empty `{}`** → the coverage-specialist story is running on month-old carried-forward keys and will silently vanish on the next rebuild.
4. Reg-season matchup depth is **asymmetric** — playoff weeks get opponent-defense percentiles; reg-season weeks show only a lever bar (the "why" is a tooltip).
5. Raw usage (`adv2.json`: target share, air-yards, aDOT, catch%) not on the card; X narrative/media deep-only.

**Fix:** wire the deep-dossier sections (situational matrix, rookies, X narrative/media) into the main `render_dossier.py`/`run_all.py`; fix `cover_spec`; add reg-season opponent-percentile parity to the lever calendar; add a raw-usage block.

## Goal 4 — Data ingestion & analysis integrity (headline)

**The `{DL}` dead-path (verified myself):** `core.py` sets `DL = parent(repo) = /root/bestball`, but the pulled files live at repo-root / `repo/NFL-master`. So `boom_foundation.py` reading `{DL}/NFL-master/AGG_COVERAGE_SHEETS_*`, `{DL}/adot-tprr.csv`, `{DL}/ffdataroma_.../adot-adjusted-yac.csv` finds **nothing** → `sis`, `adot`, `yaco` are **empty `{}` for all 379 players**. The SIS last-6 coverage masters, aDOT-TPRR, and YAC-over-expected layers you pulled are **dead in every build**. `cover_spec.json` = empty for the same class of bug (reads man-vs-zone from `{DL}`, and the 2024 file was never pulled).

**Pulled-but-unused:**
- **~95% of FP_SWEEP** (477 files, 13 MB): only defense receiving coverage-scheme + depth are read. Defense_Passing (incl. coverageScheme, both years), Defense_Rushing (run-funnel), and all QB/receiver player splits have **zero readers**.
- **FTN defense CSVs** unused → team DVOA is a **hard-coded 2025 string literal** in `build_def_profile.py`.
- Several PFF files (`receiving_depth/concept`, `defense_coverage`, `defense_run`) unused; the dossier's CB list is **hand-typed** instead of read from the committed `PFF/defense.csv`.
- `defense_coverage.csv`/`defense_shell.json` man-rate layer is **frozen** (Jun 2025) because its FP input isn't in the repo — while FP_SWEEP has the same data unread.

**Live desync:** `features/defense/flag_ranks` rebuilt tonight, but `dossier/flags_2026/rankings` are one rebuild behind — `refresh_all.py` doesn't run the dossier→rankings chain.

**Verified-current (good):** FP_ADVANCED (both years), FP pipeline splits, SIS value/man-zone/defense, PFF `defense.csv`, NFL-Pro EPA, rookie/schedule/2026-Vegas data are genuinely ingested and current; the earlier data-bug fixes (pass-rush rate, mover shares, DJ Moore/Evans usage, chart2yr union) are confirmed fixed; the 2026 defense currency work (moves map, Arnold, injured-starter recovery) is live.

**Fix:** repoint the `{DL}` inputs at in-repo paths via `core.find_data`; assert `sis/adot/yaco > 0` in `boom_pipeline` (fail-loud, no silent empties); fix `cover_spec`; rebuild the man-rate/shell layer from FP_SWEEP `Defense_Passing/coverageScheme`; feed FTN team-defense into `build_def_profile`; read PFF `defense.csv` for the CB table; append the dossier chain to `refresh_all.py`.

---

## Prioritized fix plan (recommended order)

1. **Data plumbing first** — repoint the dead `{DL}` paths, fix `cover_spec`, sync the rebuild chain. *Foundational: the board, dossier, and DFS all read this data; no point reweighting or enriching on dead inputs.*
2. **Best-ball reg-season term** — add weeks 1–14 matchup + accumulation to `build_flag_ranks.py` (and the board/cluster renderers). *Directly fixes the advance-then-win weighting.*
3. **Dossier completeness** — surface the situational matrix, rookies, coverage panel, reg-season parity. *Turns it into the learning tool you want.*
4. **DFS lineup optimizer** — salaries + cap-valid ILP + DST + ownership. *The last mile so you can actually enter lineups.*

Every item is a repoint / added term / one new feature — no architectural rewrite.
