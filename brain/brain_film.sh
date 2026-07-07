#!/usr/bin/env bash
# brain_film.sh — standing film ingestion. Iterates brain/film_sources.tsv and transcribes each
# analyst's recent uploads into the vault via brain_video.py, tagged analyst=<name> for provenance
# (fixes the video_notes.csv "no source" gap). Rows without a channel_url are skipped (tweets-only).
#
#   bash brain/brain_film.sh [N_recent]        # default: 3 most-recent videos per channel
# Needs yt-dlp + faster-whisper (setup_brain_mac.sh). Idempotent: URLs already in the manifest skip.
set -uo pipefail
cd "$(dirname "$0")/.."
[ -f .venv/bin/activate ] && source .venv/bin/activate
VAULT="${NFL_BRAIN_VAULT:-$HOME/Downloads/NFL-Brain}"
N="${1:-3}"
LOG="$VAULT/_status/film.log"; mkdir -p "$VAULT/_status"

{
  echo "===== FILM INGEST $(date) · $N recent per channel ====="
  # tab-separated; skip comments/blank; fields: handle name role channel_url
  while IFS=$'\t' read -r handle name role channel rest; do
    [[ "$handle" =~ ^#|^$ ]] && continue
    [ -z "${channel:-}" ] && { echo "skip $name (no channel — tweets-only)"; continue; }
    echo "--- $name ($handle): $channel"
    # list the N most-recent video URLs from the channel, feed each to brain_video with attribution
    yt-dlp --flat-playlist --playlist-end "$N" --print url "$channel/videos" 2>/dev/null | while read -r url; do
      [ -z "$url" ] && continue
      python3 brain/brain_video.py "$url" --vault "$VAULT" --source "$name" || echo "  (failed: $url)"
    done
  done < brain/film_sources.tsv
  echo "===== film ingest done $(date) ====="
} >> "$LOG" 2>&1
echo "film ingest complete -> $LOG"
