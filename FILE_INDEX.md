# FILE INDEX — NFL Best Ball 2026
All files are under ~/Downloads/bestball/

## ROOT — live draft toolkit (run from here)
draft_pick.py            paste/clip the DK board -> resolve -> recommendations
draft_assistant.py       scoring engine (ceiling / value-vs-rank / anchor / bye / need)
draft_board_signals.csv  per-player signals: p95 ceiling, cv, spike%, bye, W17 game+tail, merged_rank
dk_adp.csv               DK ADP + player IDs  (REPLACE WEEKLY with fresh DK export)
merged_rankings_upload.csv  your DK pre-load board (5-source, +/-6 cap) — upload to DraftKings
anchor_allocation_900.csv   per-game W17 anchor targets (Phase 2 / --portfolio)
HANDOFF_NFL_BestBall_2026_v2.md   master reference (also in /docs)
Board.txt                scratch — your last pasted board

## /docs — reference
HANDOFF_NFL_BestBall_2026_v2.md   full system handoff (9 sections)
DRAFT_STRATEGY_900.md             900-entry slow-draft schedule + rules
RECONCILIATION_REGISTER.md        data-source validation register (Layer 0/1)

## /analysis — results
merged_rankings_2026.csv     full merged board: per-source ranks, vs_adp, opinion vs capped
draft_analysis_live.csv      your $1M live draft survival chain (11th/12)
chain_live.csv               same, raw
portfolio_chain.csv          4-prior-drafts survival summary
portfolio_summary_v2.csv     4-prior-drafts title-share + game-stack lift
w17_blowup_rank.csv          W17 games ranked by TAIL (blowup), not O/U

## /pipeline — rebuild weekly (after re-pulling ADP/BBB/LegUp)
merge_rankings.py        builds merged_rankings_*  (edit SOURCES block to add/weight feeds)
build_layer2.py          Clay -> per-game means + variance params
build_draft_board.py     -> draft_board_signals.csv
parse_clay.py            Clay PDF -> clay_2026.csv
sim_prod.py              compositional Monte Carlo (player distributions)
survival_chain.py        pod analysis: advance x W15 x W16 x W17 x title
+ data: clay_2026.csv, layer2_*_params.csv, player_sim_distributions.csv,
        games_by_week.json, byes_2026.json, schedule_2026.csv,
        correlation_structure.json, team_volume_model.json,
        usage_shares.parquet, player_games.parquet

## SOURCE INPUTS (live in ~/Downloads, refresh these)
DkPreDraftRankings(2).csv        DK ADP template (current)
dk-ranks.csv                     LegUp ranks
DraftKings-Best-Ball-6-12.csv    Beat Best Ball ranks
NFLDK2026_CS_ClayProjections2026 (1).pdf   Clay 6/10
nflfastr_pbp_2024_2025.zip       play-by-play (large; for full rebuild only)
NFL-master.zip                   SIS/FantasyPoints repo
NOT YET PROVIDED: tweets.db      -> activates the 15% qual/coachspeak layer

## WEEKLY REFRESH (one pass)
1. Drop fresh DkPreDraftRankings, dk-ranks, DraftKings-Best-Ball into ~/Downloads
2. cd ~/Downloads/bestball/pipeline
3. python3 build_layer2.py && python3 build_draft_board.py && python3 merge_rankings.py
4. copy new draft_board_signals.csv + merged_rankings_upload.csv up to the root folder
