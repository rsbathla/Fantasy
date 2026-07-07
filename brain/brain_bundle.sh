#!/usr/bin/env bash
# brain_bundle.sh — snapshot the vault into three bundle files so Claude can pull a FRESH copy
# over the bridge (timestamped names defeat the transfer cache). Run this, then ask anything.
#   bash brain/brain_bundle.sh [vault_path]
set -e
V="${1:-$HOME/Downloads/NFL-Brain}"
O="$V/_status"
TS="$(date +%m%d_%H%M)"

for f in "$V"/Tweets/*/*.md;  do echo "===== $f"; cat "$f"; done > "$O/bundle_tweets_$TS.md"
for f in "$V"/Sources/*.md;   do echo "===== $f"; cat "$f"; done > "$O/bundle_sources_$TS.md"
for f in "$V"/Players/*.md "$V"/Teams/*.md "$V"/Coaches/*.md; do echo "===== $f"; cat "$f"; done > "$O/bundle_pages_$TS.md"

ls -lh "$O"/bundle_*_"$TS".md
echo ""
echo "Bundles ready — tell Claude: bundle $TS"
