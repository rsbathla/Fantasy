#!/usr/bin/env bash
# run_brain_weekly.sh — the WEEKLY MODEL refresh (distinct from run_brain.sh, the DAILY INTEL refresh).
#
# run_brain.sh (daily 7:30am) keeps the QUALITATIVE brain current: tweets, articles, Substack,
# condenser, entity pages, concepts. It does NOT touch the quantitative model layers.
#
# THIS script keeps the QUANTITATIVE model current once the 2026 season starts: it re-pulls the NFL
# Pro / Next Gen Stats data, rebuilds the team + player funnels with a 2025->2026 BLEND that
# self-corrects as weeks accumulate, re-anchors the game sim to current Vegas lines, and regenerates
# the funnel-dependent pages. Run it weekly (e.g., Tuesday after MNF, once box scores settle).
#
# ---------------------------------------------------------------------------------------------------
# STEP 0 — THE SCRAPE (you run this; it needs your NFL Pro access + the nfl_pro_scraper tool):
#   1. Run your NFL Pro scraper for the 2026 weeks played so far, output to:  $SCRAPE_2026
#      (same folder layout as nfl_pro_scraper/: PassingDefense/ RushingDefense/ receiving/ rushing/ ...)
#   2. Set WK26 to the number of 2026 weeks in that scrape (drives the blend weight).
#   3. Refresh Vegas lines into game_sim's line source, then set LINES_UPDATED=1 to re-anchor.
# Until 2026 games exist, leave SCRAPE_2026 unset — everything below refreshes on the 2025 prior
# (blend weight 0), so this is safe to run in the preseason too.
# ---------------------------------------------------------------------------------------------------
set -uo pipefail
cd "$(dirname "$0")/.."
[ -f brain/brain.conf ] && source brain/brain.conf
[ -f .venv/bin/activate ] && source .venv/bin/activate

VAULT="${NFL_BRAIN_VAULT:-$HOME/Downloads/NFL-Brain}"
RAW_2025="${NFL_PRO_2025:-$HOME/Downloads/nfl_pro_scraper}"     # the NJ bundle (2025 actuals)
SCRAPE_2026="${NFL_PRO_2026:-}"                                 # set once 2026 games exist
WK26="${WK26:-0}"
LINES_UPDATED="${LINES_UPDATED:-0}"
LOG="$VAULT/_status/weekly.log"; mkdir -p "$VAULT/_status"

# blend flags: pass 2026 raw + week count to the builders that self-correct (player_funnels today;
# build_nflpro blend is the next extension — until then it refreshes on whichever raw is current).
BLEND=""; [ -n "$SCRAPE_2026" ] && [ -d "$SCRAPE_2026" ] && BLEND="--raw2026 $SCRAPE_2026 --wk26 $WK26"

{
  echo "===== WEEKLY MODEL REFRESH $(date) · 2026 weeks=$WK26 · blend=${BLEND:-none (2025 prior)} ====="

  # 1) team defensive funnels from NGS (2025 now; add 2026 blend to build_nflpro next)
  python3 build_nflpro.py --raw "$RAW_2025" --out nflpro_2025.json --season 2025 --xcheck
  echo "nflpro exit $?"

  # 2) PLAYER funnels + usage rates — self-correcting blend when 2026 data is present
  python3 build_player_funnels.py --raw "$RAW_2025" $BLEND --out player_funnels.json
  echo "player_funnels exit $?"

  # 2b) FantasyPoints cross-checks — alignment (two-source vs NFL Pro) + personnel (if pulled).
  # Both are token-gated pulls YOU run; these consumers turn them into signal (personnel skips
  # gracefully until you've pulled the Personnel dimension).
  python3 build_fp_alignment.py --repo . && echo "fp_alignment exit $?"
  python3 build_fp_personnel.py --repo . ; echo "fp_personnel exit $? (skips if not pulled)"

  # 3) re-anchor the Vegas game sim to current lines (only when you've refreshed the line source)
  LINES_CSV="ffdataroma_draft_guide_export/ffdataroma/csv/weekly-vegas-lines.csv"
  LINES_AGE_D="?"
  if [ -f "$LINES_CSV" ]; then
    LINES_AGE_D=$(( ( $(date +%s) - $(stat -f %m "$LINES_CSV" 2>/dev/null || stat -c %Y "$LINES_CSV") ) / 86400 ))
    [ "$LINES_AGE_D" -gt 14 ] && echo "⚠ VEGAS LINES STALE: ${LINES_AGE_D}d old — game_sim anchors are drifting; refresh the export"
  fi
  if [ "$LINES_UPDATED" = "1" ]; then
    python3 game_sim.py && echo "game_sim re-anchored exit $?"
  else
    echo "game_sim: skipped (set LINES_UPDATED=1 after refreshing the line source; lines file age ${LINES_AGE_D}d)"
  fi

  # 4) rebuild the defensive funnel profile (canonical rookie-aware engine — NOT the legacy writer)
  python3 normalize_defense_2026.py && echo "defense engine exit $?"
  python3 build_def_profile.py && echo "def_profile exit $?"

  # 5) regenerate the concept pages so each team playbook reflects the fresh funnels
  python3 brain/brain_concepts.py --vault "$VAULT" && echo "concepts exit $?"

  # 6) PLAYER pages — the weekly job's only path to what a drafter actually reads.
  # Refresh fast-rotting statmenu fields (ADP as-of, availability, bye/W15-17), re-render.
  python3 brain/brain_refresh_statmenu.py && echo "statmenu refresh exit $?"
  python3 brain/brain_pages.py --vault "$VAULT" && echo "pages exit $?"

  echo "===== weekly refresh done $(date) ====="
} >> "$LOG" 2>&1

echo "weekly model refresh complete -> $LOG"
