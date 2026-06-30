# Project Progress — Three Production Models

**Owner:** Ramneik · **Started hardening:** 2026-06-30 · **Target:** every dimension production-grade, a real user can walk in and use it.

This is the central progress log. It is updated after every meaningful step. Each model is built to a bar (architecture + result), tested end-to-end (engine runs + headless browser render), reviewed, and committed.

---

## The three goals (verbatim intent)

1. **Best Ball draft model** — paste the board from **DraftKings AND Underdog** → it populates and shows the best picks based on our analytics + the roster construction + the board I have. Optimize for **advancement rate and playoff winning**.
2. **DFS weekly model** — each player's profile (what's **statistically significant** for their matchup), the **qualitative levers** (not stat-sig but good to know), and the **defense's profile with the same splits**. Then **who to play this week** and **what lineup types** to build based on **historical winners**.
3. **Dossier** — for each **player, offensive team, defensive team, and coaching** — a true fundamental understanding, so I can decide **who to press when they have a good matchup**.

---

## Baseline assessment (2026-06-30, from a 4-way parallel audit + repo self-audit)

| Area | Sub-dimension | Baseline | Target |
|---|---|---|---|
| **Best Ball** | DK paste→recs (Monte-Carlo advancement+playoff) | 80% | 100% |
| | Underdog paste→recs | **15%** | 100% |
| | Advancement/playoff optimization (survival chain) | 75% | 100% |
| | Roster-construction awareness | 80% | 100% |
| | Projection coverage (no ungradeable stars) | ~70% | 100% |
| | One canonical entry point + usability | 40% | 100% |
| **DFS** | (a) Player stat-sig matchup profile | 60% | 100% |
| | (b) Qualitative levers (non-stat-sig) | 75% | 100% |
| | (c) Defense profile w/ SAME splits | **40%** | 100% |
| | (d) Weekly who-to-play + lineup types from winners | **10%** | 100% |
| | Week-to-week parameterization | ~20% | 100% |
| **Dossier** | Player | 82% | 100% |
| | Offensive team (scheme identity) | **45%** | 100% |
| | Defensive team (unified object) | 62% | 100% |
| | Coaching | 80% | 100% |
| | "Who to press" by matchup (by-week pivot) | 62% | 100% |
| | Single home / integration | 50% | 100% |

**Data is rich and current** (both 2024+2025 PFF/FTN/FP charting, real NFL Pro EPA, SIS Points Saved, full FFDataRoma, coaching/scheme). Gaps are **architecture & assembly**, not missing inputs.

---

## Target architecture — three clean products + one home

- **`home.html`** — single landing page routing to the three tools (kills the 13-dashboard fragmentation).
- **Best Ball:** one entry `draft.py` (paste DK *or* UD → auto-detect platform → grade → recs) → `decision_dashboard.html`. Underdog parser + UD scoring/lineup/rounds wired into the survival-chain sim. Projection coverage closed.
- **DFS:** `dfs.py --week N` → player profile (sig + qual) + defense same-splits + who-to-play + lineup templates from winner structure → `dfs_week.html`.
- **Dossier:** unified `dossier.html` covering player / offense (scheme identity) / defense (one object) / coaching, plus a **by-week "who to press"** slate view.

---

## Work plan & status

Legend: ⬜ todo · 🔄 in progress · ✅ done (tested + committed)

### Phase A — Infrastructure
- ✅ Parallel 4-way audit of all three models + data inventory
- 🔄 git init + .gitignore + baseline commit + this progress doc

### Phase B — Best Ball to production
- ✅ Underdog board parser (`engine/ud_parse.py`, name-anchored, apostrophe/round-aware) + platform auto-detect (`draft.py detect_platform`)
- ✅ UD scoring (half-PPR `ud_pg` from clay_2026_ud.csv) wired into projection loader; UD lineup/rounds/cuts already platform-gated in decision_tree/survival_chain
- ✅ Close projection-coverage hole — `_impute_missing_proj` (position-aware ADP→proj curve); all 379 ADP'd players now gradeable (Tyreek Hill/Diggs/Aiyuk no longer silently dropped)
- ✅ DK 20-round handling fix (`ROUNDS` platform-aware: DK=20, UD=18; RUNNING_MIN extended to R19-20)
- ✅ One canonical entry point `draft.py` (paste DK *or* UD → auto-detect → grade → dashboard); regression test grade==chain PASS
- ✅ End-to-end tested: DK fixture → Rome Odunze (dTitle 14.2); synthetic UD → Amon-Ra (half-PPR). **Pending:** validate UD auto my-roster extraction against one real UD paste (works today via `--mine`).
- ⬜ (Optional polish) promote fusion/boom/EPA signals from display-only into explicit pick-score levers

### Phase C — DFS to production
- ✅ Defense split-parity: `build_defense_splits.py` → `defense_splits.json` (32 teams; allowed YPR vs man/zone/deep/short from FP_SWEEP coverageScheme+depthOfTarget, FPAA by position from defensive_profile, shells + unit pctls). Same axes as players.
- ✅ Weekly model `dfs_model.py --week N`: per-player MATCHUP EDGE (player strength pctl vs opp-defense softness pctl on the SAME axis) + qualitative levers + who-to-play ranking. Verified: Puka #1 vs DAL (softest vs man), edges line up correctly.
- ✅ Lineup/winner layer: anchor games by total → QB + 2 same-team catchers + bring-back (high-total only), real correlations (QB-WR1 0.35, bring-back 0.16 high-total), winner rules. Templates render (DAL/LAR → Stafford+Puka+Adams+CeeDee).
- ✅ Week parameterization (`--week N`, reads that week's opponents + Vegas totals); self-provisions defense_splits.
- ✅ `dfs_week.html` page (who-to-play board + lineup templates + defense-splits reference + shared 4-layer drilldown). Headless-rendered, 0 console errors. **Pending:** swap projection-basis for live stats once 2026 games start (framework is week-ready).

### Phase D — Dossier to production
- ⬜ Offense scheme-identity profile (fix broken team-motion join) all 32
- ⬜ Unified per-defense dossier object (fuse 7 files; add pressure proxy)
- ⬜ By-week "who to press" pivot + FAV/TOUGH "why" all 18 weeks
- ⬜ Single `home.html` landing + dossier as unified home · test · commit

### Phase E — Final review pass
- ⬜ One dedicated review pass over all three; end-to-end retest; fix; commit

---

## Change log
- 2026-06-30: Audit complete; architecture defined; git initialized; hardening begun.
