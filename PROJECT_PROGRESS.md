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
- **DFS:** `dfs_model.py --week N` → player profile (sig + qual) + defense same-splits + who-to-play + lineup templates from winner structure → `dfs_week.html`.
- **Dossier:** unified `dossier.html` covering player / offense (scheme identity) / defense (one object) / coaching, plus a **by-week "who to press"** slate view.

---

## Work plan & status

Legend: ⬜ todo · 🔄 in progress · ✅ done (tested + committed)

### Phase A — Infrastructure
- ✅ Parallel 4-way audit of all three models + data inventory
- ✅ git init + .gitignore + baseline commit + this progress doc

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
- ✅ Offense scheme-identity profile `build_offense_profile.py` → `offense_profile.json` (all 32): real **zone-vs-gap run identity** from FP RunType attempts, pace, pass-rate, motion/PA where charted, playcaller + dials, environment. Fixes the null-motion / no-scheme gap; charting aliases (BLT/CLV/HST) folded.
- ✅ Unified per-defense object = `defense_splits.json` (Phase C) — fuses man/zone/deep/short softness + FPAA-by-position + shells + unit pctls + funnels into one per-team card, surfaced in the Defense dossier tab.
- ✅ By-week "who to press" pivot = the DFS weekly board (`dfs_model.py --week N`) — per-week opponent + matchup edges, sortable; the slate's smash spots.
- ✅ Single `home.html` landing — routes to the 3 tools + unified Offense/Defense/Coaching dossier tabs. Headless-rendered, 0 errors.

### Phase E — Final review pass
- ✅ Independent adversarial review of all three (end-to-end DK+UD drafts, DFS wks 5/15/17, all renders)
- ✅ Fixed BLOCKER A1: DFS ranked an unprojected 4th-stringer (J'Mari Taylor) #2-3 via a stale dk_max25 ceiling fallback → added a playable-projection floor; top plays now all legit stars
- ✅ Fixed BLOCKER A2: UD round detection grabbed the first "Round N of" (pinned multi-round pastes to round 1) → round now derives from the authoritative current pick
- ✅ Fixed B1/B4: dropped the unreliable `dc` field from defense_splits; fixed the shell man-rate key (now 32/32)
- ✅ Fixed B6: doc drift (dfs.py → dfs_model.py)
- ✅ Re-verified: grade==chain PASS, 0 console errors, 0 visible NaN/undefined on dfs_week + home
- ⚠️ FLAGGED (not changed, per golden rule): `dk_adp.csv` lists Kenneth Walker III on KC (top-15 RB ADP) — could be a real 2026 move or a source error; user to verify rather than override on a 2025 assumption.

### Phase F — Live X (tweets) + analyst narrative layer
Goal (user): "pull the most recent tweets… and start forming ideas and analysis on what people are saying and how that forms the profile of that player." Dossier purpose = aggregate ALL data per player.
- ✅ **Free "scroller" pull (no paid API).** Paid X API is blocked by the sandbox network policy (api.x.com/api.twitter.com → 403 tunnel), so the pull runs in the browser. A private X **List "FF Analysts"** (id `2072071516770955274`) was created on an unused account (@rsbatz) via the X v1.1 API and populated with all **48 tracked analyst handles** (`x_handles.txt`). The list timeline is scrolled with real wheel events (scripted `scrollBy` stalls X's virtualizer) and each rendered tweet harvested from the DOM (id, handle, ISO date, like count, repost social-context, cleaned text).
- ✅ **Pull 1 (2026-06-30):** 48 tweets across ~6h captured → `build_x_posts.py` → `x_posts.json` (normalized schema). Re-run = replace `POSTS` after the next scroll.
- ✅ **Map → players/teams** (`x_dossier_refresh.py --input x_posts.json` → `x_live.json`): **16 players, 12 teams**. Hardened the mapper: it now requires BOTH first AND last name in the post, killing the unique-surname false positives the old `len(plist)==1` bypass produced (LeBron **James**→Jordan James, **Murray**-Boyles→Kyler Murray, to **Boston**→Denzel Boston, third **downs**→Josh Downs all correctly rejected; every true full-name mention kept).
- ✅ **Analyst narrative layer** (`build_x_narrative.py` → `x_narrative.json`): per mapped player a **sentiment** (bullish/bearish/mixed/neutral) + **themes** + a synthesized **take**, each grounded in that pull's actual posts with handle attribution (never invented; players with no mapped posts are skipped). 16/16 mapped players synthesized. e.g. Odunze = contrarian Y3-leap buy (Sanderson, YPRR), Willis = rushing-creation QB2 floor (Winks YAC + Norris), Lloyd = self-aware hype-trap (Hartitz).
- ✅ **Merged into the deep dossier**: `dossier_deep.html` rebuilt (369 players) with a "🧠 What analysts are saying" section (sentiment badge + themes + take) above the raw "Tweets & analyst mentions" evidence. Verified: narrative + live tweets present in the HTML (take/themes ×16; live YPRR + YAC tweets render).
- **Refresh cadence (reproducible):** scroll the list → update `build_x_posts.py` POSTS → `python3 build_x_posts.py && python3 x_dossier_refresh.py --input x_posts.json --no-rebuild && python3 build_x_narrative.py && python3 build_dossier_deep.py`.
- Golden rule respected: narratives attribute claims to analysts and avoid asserting 2026 facts (e.g., Jahnke's "best guess" Seahawks backfield reported as his projection, not endorsed).

---

## Open items (honest)
- **UD auto my-roster**: drafted-set + round/pick auto-detect now work; "which picks are mine" needs one real UD board paste to finalize (works today via `--mine`).
- **In-season DFS**: framework is week-parameterized and runs on projection/Vegas/matchup now; swap to live stats once 2026 games start.
- **Offense motion/PA**: charted for ~17/32 (honest "–" elsewhere); zone/gap run identity is 32/32.
- Optional: promote fusion/boom/EPA into explicit best-ball pick-score levers (currently rich display + projection-driven).

## Change log
- 2026-06-30: Audit → architecture → git init. Phase B (Best Ball: UD + projection fix + canonical entry), Phase C (DFS: defense split-parity + weekly model + lineup templates), Phase D (Dossier: offense scheme identity + unified home), Phase E (independent review + blocker fixes) — all complete & committed. All three products run end-to-end and render clean.
- 2026-06-30: Phase F — live X layer via the free List "scroller" (paid API blocked by sandbox). Created+populated the 48-handle "FF Analysts" list on @rsbatz, scrolled it for 48 recent tweets, mapped to 16 players/12 teams (mapper hardened: require first+last name, false positives eliminated), and added a grounded per-player **analyst narrative** (sentiment+themes+take) merged into `dossier_deep.html`.
