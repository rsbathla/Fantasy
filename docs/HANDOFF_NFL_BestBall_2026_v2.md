# NFL Best Ball 2026 — Comprehensive Handoff (v2)
Updated 2026-06-15. DraftKings best ball. Seat varies; user = rsbathla. 12-team pods, top-2 advance (W1-14) -> W15/W16/W17 playoff gates -> W17 finals ($ is top-heavy).
CORE PRINCIPLE: grade and draft on UPSIDE (ceiling / survival chain), never on mean projection.

================================================================
## 1. THE LIVE-DRAFT TOOLKIT  (what you use during drafts)
Folder: ~/Downloads/bestball  — contains everything; run from here.
Files: draft_pick.py, draft_assistant.py, draft_board_signals.csv, dk_adp.csv, anchor_allocation_900.csv, merged_rankings_upload.csv
One-time:  pip3 install pandas striprtf

### Per-pick workflow (clipboard — no files):
  1. On the DK draft page, select the board and ⌘C (copy).
  2. cd ~/Downloads/bestball
  3. python3 draft_pick.py clip --seat rsbathla
(or:  python3 draft_pick.py Board.txt --seat rsbathla   if you saved the screen to a file)

### What it does
- Parses the DK board. LIVE in-draft view has player names -> read directly. Pre-draft/summary view has only pos/team -> resolved via ADP (~95% on meaningful picks).
- Finds your seat, your roster, your next pick (snake math). Override with --pick N if needed.
- Runs the assistant and prints recommendations.

### Reading the output
Header: PICK # · roster counts (QB/RB/WR/TE) · Anchor (your best game to build) · Byes (+CLUSTER warning only for uncorrelated pileups).
"→ TAKE" line = the pick. Then a table:
  RK  = your MERGED-board rank (5-source, ±6 ADP-capped)   ADP = DK market
  PROJ= Clay pts/g (context only)   CEIL = p95 single-week ceiling (THE upside number)   BY = bye week
  WHY = short tags: val+N (fell past YOUR rank) / REACHn / ★2-side GAME / →commit GAME / seed GAME#tail / needPOS / ✗BYE-pileup / boom / no-proj

### Scoring logic (per candidate)
- 0.42*ceiling(p95 pctl) + 0.23*advancement(proj pctl)  [ceiling weighted hardest]
- value vs MERGED RANK (not raw ADP): val if fell >=8, escalating REACH penalty if reaching
- TWO-SIDED anchor: complete (★bring-back) > build > seed; over-stack penalty at 5+; one-sided nudge to the other team
- bye PILEUP penalty = players on a bye BEYOND your biggest single-team stack (stacks never penalized)
- positional need vs targets (QB3/RB6/WR9/TE3); no-proj penalty (FA/no data)
- boom tag for high-CV WRs

### Flags
--pick N   force the pick number (if auto-detect lags / stale board)
--n K      show K candidates (default 10)
--portfolio "BAL@CIN:5,LAR@TB:3,..."   PHASE-2 only: steers toward under-filled anchor games
--seat     your handle or seat number

### PHASES (your chosen sequencing)
Phase 1 (now, entries 1-~20): run WITHOUT --portfolio. Build each lineup as strong as possible.
Phase 2 (after 10-20): add --portfolio tally -> tool balances anchors across the 900.

================================================================
## 2. MERGED RANKINGS (your DK pre-load board)
File: merged_rankings_upload.csv (exact DK template: ID,Name,Position,ADP,Team,,Instructions; all 1568; LF).
Sources & weights: ours_ceiling 25.5% · Clay 18.7% · Beat Best Ball 18.7% · LegUp 13.6% · DK ADP 8.5% · + 15% reserved for QUAL (auto-activates with tweets.db).
ADP-capped: each player within +/-6 spots of ADP (config ADP_CAP in merge_rankings.py).
Character: BUY underpriced QBs, FADE committee RBs.
Upload it as your DK pre-draft rankings so auto-picks follow your edge; the assistant handles the leverage picks.

================================================================
## 3. HOW GRADING WORKS (upside lens — important)
- W15 / W16 / W17 = pure single-week CEILING survival (scheduled; game stacks fire in the right week). Upside.
- Title share = chains advance x W15 x W16 x W17. Upside.
- Advancement P(top-2 of 12) = simulated DISTRIBUTION of your 14-wk total, prob of finishing top-2. It is cumulative, so it leans on volume — the one gate where "how much you score" matters as much as "how high you spike." Legitimate (you must bank points to reach the playoffs).
- NEVER grade a roster by Clay mean projection. Use p95 (ceiling), CV, spike%.
- Player ceiling = p95 in player_sim_distributions.csv. Alpha-ceiling WR ~ p95 38-47; mid WR ~ 25-29.

================================================================
## 4. DATA FOUNDATION + SIM (validated)
- nflfastR PBP 2024-25 -> Component 1 (usage shares, weekly CV, team volume/script model), Component 2 (correlation: QB-WR1 0.35, WR-WR ~0, bring-back hi 0.16 > lo 0.06).
- Layer 0/1 reconciliation vs FantasyPoints/SIS repo: target share r=0.99, aDOT r=0.99 (no halving), YPRR r=0.95, EPA reconciled (use nflfastR qb_epa/dropback uniformly).
- Clay 2026 (6/10) = the swappable MEAN layer. Backtest vs actual 2025: r=0.75 (TE .74 > WR .69 > RB .65 > QB .60).
- Compositional Monte Carlo: shared game-env draw -> team volume -> Dirichlet target/carry split -> per-player DK; QB derived from team passing aggregate so stacks correlate mechanically. Calibrated to Clay means (preserves CV+corr). Schedule-aware (real 2026 schedule). Reproduces Component-2 correlations.

================================================================
## 5. KEY FINDINGS (audits + live draft)
- ADVANCEMENT is the binding gate in a 2/12 pod. Title equity tracks it. A great anchor with weak advancement = dead (Draft 1: 7% advance -> 10th).
- CEILING DEFICIT loses: the live $1M draft finished 11th/12 — 0 alpha-ceiling WRs (p95>=33) vs 2 for pod leaders; over-invested in 3 mid QBs; GB stack on a mid-tail game (#10). RB room was fine.
- BYE rule: only flag UNCORRELATED pileups (players beyond your biggest single-team stack). Stacking a team is free of this penalty.
- CONCENTRATE within an entry (1 anchor, 4-5 pieces ~ +15% finals tail at equal mean); DIVERSIFY the anchor game across the portfolio.
- GAME-STACK lift is real but modest (~+3-6% on W17 p95 at full-lineup level); build anchors TWO-SIDED (QB+catchers one team + 1-2 bring-back).
- Rank finals games by TAIL (blowup p99), not O/U — mid-total games can out-ceiling high-total ones.
- Portfolio audit of 4 prior drafts: 3 of 4 above baseline; strongest in the two $20M Millionaires.

================================================================
## 6. 900-ENTRY SLOW-DRAFT PLAN  (file: DRAFT_STRATEGY_900.md)
- Slow drafts. START-based pacing (each takes ~5-7d; last start ~Sept 1 to finish by Sept 9):
  Jun 15-30 ~110 · July ~290 · Aug 1-25 ~420 (peak info+liquidity) · Aug 26-Sep 1 ~80.
- ~70-100 concurrent drafts at peak. Pre-load (merged_rankings_upload.csv) auto-picks the non-leverage rounds; hand-manage ~5-6 leverage picks/draft with the assistant.
- Anchor allocation across ALL 16 finals games (anchor_allocation_900.csv): top-4 tail games ~8.6% each, mid ~6%, low ~4.8% — none dominant (max 8.6%). This is the Phase-2 --portfolio target.
- Hard rules: never same-bye DIFFERENT-team pileup; advancement floor every entry; concentrate within/diversify across; two-sided anchors; tail not O/U.

================================================================
## 7. OPEN ITEMS / DEPENDENCIES
- tweets.db (15% QUAL / coachspeak): NOT yet provided (binary; not recoverable from pasted chat). Drop the scroller's tweets.db in Downloads OR re-run the scroller -> I build qual_signal.csv (Rule-2 gate, weighted by qualitative_sources.csv tiers) -> auto-folds into the merge at 15%.
- WEEKLY REFRESH: re-pull DK ADP + re-export Beat Best Ball + LegUp -> drop in. Re-run: build_layer2.py -> build_draft_board.py -> merge_rankings.py. (A one-command refresh.sh is not yet built — easy add.)
- Minor: a few name-join misses on suffix names (e.g., Kenneth Walker III) can score 0 in the pod sim; immaterial to ranking but on the cleanup list.

================================================================
## 8. HONEST CAVEATS
- All sim numbers anchor to Clay means -> FLOOR reads. The ONE genuine upside the model cannot price: rookie breakouts (their p95 is calibrated to Clay's low rookie means). A rookie WR who becomes an alpha blows past his shown p95.
- Opponent rosters in pod analyses are ADP-resolved (top picks exact, some mid/late noise).
- Playoff cut rates in the survival chain are configurable proxies; relative ranking is robust, absolute probabilities are not.
- Correlation structure calibrated on 2024-25; one season-pair.

================================================================
## 9. FILE MANIFEST (in ~/Downloads/bestball unless noted)
draft_pick.py            board paste/clip -> resolve -> run assistant
draft_assistant.py       scoring engine (ceiling/value-vs-rank/anchor/bye/need)
draft_board_signals.csv  per-player signals (p95, cv, spike, bye, w17 game+tail, adv/ceil pctl, merged_rank)
dk_adp.csv               DK ADP + player IDs (refresh weekly)
merged_rankings_upload.csv  DK pre-load (5-source, ±6 cap)  [also in outputs]
anchor_allocation_900.csv   per-game anchor targets (Phase 2)
-- in outputs (analysis/build, not needed at the table) --
merge_rankings.py, build_layer2.py, build_draft_board.py, sim_prod.py, survival_chain.py,
player_sim_distributions.csv, layer2_*_params.csv, clay_2026.csv, games_by_week.json, byes_2026.json,
DRAFT_STRATEGY_900.md, RECONCILIATION_REGISTER.md, draft_analysis_live.csv
