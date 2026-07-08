#!/usr/bin/env bash
# run_brain.sh — one hands-off NFL-Brain ingest run (this is what the launchd schedule calls).
# The twitterapi.io key stays OUT of git and OUT of the plist: it's read from brain/brain.conf.
set -uo pipefail
cd "$(dirname "$0")/.."                                # repo root (brain/ lives under it)

# One-time setup (gitignored):  echo 'export TWITTERAPI_IO_KEY=your-key' > brain/brain.conf
[ -f brain/brain.conf ] && source brain/brain.conf
: "${TWITTERAPI_IO_KEY:?TWITTERAPI_IO_KEY not set — put it in brain/brain.conf}"

if [ ! -f .venv/bin/activate ]; then
  echo "no .venv — run brain/setup_brain_mac.sh first" >&2; exit 1
fi
source .venv/bin/activate

VAULT="${NFL_BRAIN_VAULT:-$HOME/Downloads/NFL-Brain}"
mkdir -p "$VAULT/_status"
LOG="$VAULT/_status/run.log"                           # logs live in the vault, never in the repo

# --- network gate: launchd fires at 07:30, often right as the Mac wakes, before DNS is up.
# Jul 5 + Jul 6 2026 were both silently lost to this (58/58 handles urlopen-failed, script
# exited 0, export re-stamped stale data as fresh). Wait up to 5 min; if the network never
# comes up, write a RED card and exit 1 — a missing day must be loud, not a quiet news day.
net_up() { /usr/bin/nslookup -timeout=3 api.twitterapi.io >/dev/null 2>&1; }
NET_OK=0
for _ in $(seq 1 30); do
  if net_up; then NET_OK=1; break; fi
  sleep 10
done
if [ "$NET_OK" -eq 0 ]; then
  {
    printf '# Ingest — last run\n\n'
    printf '> [!danger] ❌ NETWORK DOWN at %s — NO DATA CAPTURED today. Run manually: `bash brain/run_brain.sh`\n' "$(date '+%Y-%m-%d %H:%M')"
  } > "$VAULT/_status/last-run.md"
  echo "===== $(date) ===== NETWORK DOWN — aborted before ingest" >> "$LOG"
  exit 1
fi

ING_OUT="$VAULT/_status/.last_ingest_out"

run_ingest() {
  python3 brain/brain_ingest.py --vault "$VAULT" --model "${NFL_BRAIN_MODEL:-small.en}" > "$ING_OUT" 2>&1
  local rc=$?
  cat "$ING_OUT"
  return $rc
}

{
  echo "===== $(date) ====="
  run_ingest
  echo "ingest exit $?"
  # dead-feed retry: if the pull mass-failed on DNS/socket errors, the network flapped —
  # wait 5 min and rerun the ingest once before giving up on the day
  if [ "$(grep -c 'urlopen error' "$ING_OUT" 2>/dev/null; true)" -ge 20 ]; then
    echo "MASS NETWORK FAILURE detected — retrying ingest in 300s"
    sleep 300
    run_ingest
    echo "ingest retry exit $?"
    if [ "$(grep -c 'urlopen error' "$ING_OUT" 2>/dev/null; true)" -ge 20 ]; then
      printf '# Ingest — last run\n\n> [!danger] ❌ FEED DEAD %s — pull failed twice (network/API). Today is MISSING. Run manually: `bash brain/run_brain.sh`\n' "$(date '+%Y-%m-%d %H:%M')" > "$VAULT/_status/last-run.md"
      echo "FEED DEAD after retry — skipping condense/pages/export so stale data is not re-stamped fresh"
      exit 1
    fi
  fi
  # direct Substack sweep (last 14 days) — catches posts even when they aren't tweeted
  SINCE_14D="$(date -v-14d +%Y-%m-%d 2>/dev/null || date -d '14 days ago' +%Y-%m-%d)"
  python3 brain/brain_substack.py bengretch.substack.com --since "$SINCE_14D" --vault "$VAULT"
  echo "substack exit $?"
  python3 brain/brain_link.py --vault "$VAULT"
  echo "condense exit $?"
  # vault -> draft-tool bridge FIRST: brain_intel.json carries today's intel, which the
  # statmenu refresh scans for availability flags (injury/suspension/holdout) so the pages
  # rendered below show SAME-DAY availability. (pages and export have no other dependency)
  python3 brain/brain_export.py --vault "$VAULT"
  echo "export exit $?"
  # fast-rotting statmenu fields: ADP (newest DK export, with as-of date), availability,
  # bye + W15-17 opponents — without re-running the heavy boom pipeline
  python3 brain/brain_refresh_statmenu.py
  echo "statmenu refresh exit $?"
  python3 brain/brain_pages.py --vault "$VAULT"
  echo "pages exit $?"
  # concepts/ layer: regenerate the per-team playbook pages (theses + funnels + player leans,
  # wikilinked to teams+players) from the freshly-updated brain_intel.json. Auto-content only;
  # your ## Notes are never overwritten.
  python3 brain/brain_concepts.py --vault "$VAULT"
  echo "concepts exit $?"
  # landing page: one-glance vault home (health, availability watch, today intake, board top, nav)
  python3 brain/brain_home.py --vault "$VAULT"
  python3 brain/brain_warroom.py --vault "$VAULT"
  echo "home exit $?"
} >> "$LOG" 2>&1
