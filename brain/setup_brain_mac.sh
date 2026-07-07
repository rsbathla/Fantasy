#!/usr/bin/env bash
# setup_brain_mac.sh — one-time install of the NFL-Brain ingest dependencies on macOS.
# Installs ffmpeg (Homebrew) + yt-dlp / faster-whisper / trafilatura (pip, into the repo's .venv).
set -e
cd "$(dirname "$0")/.."   # repo root (brain/ lives under the repo)

echo "== NFL-Brain setup =="

# 1. ffmpeg (needed by yt-dlp audio extraction + whisper decode)
if ! command -v ffmpeg >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    echo "installing ffmpeg via Homebrew…"; brew install ffmpeg
  else
    echo "!! ffmpeg missing and Homebrew not found. Install Homebrew (https://brew.sh) then re-run."; exit 1
  fi
else echo "ffmpeg: ok"; fi

# 2. python venv (reuse the repo's .venv if present)
if [ ! -d ".venv" ]; then python3 -m venv .venv; fi
# shellcheck disable=SC1091
source .venv/bin/activate
python3 -m pip install --upgrade pip >/dev/null

# 3. ingest deps  (requests + browser_cookie3 handle paywalled sites via your browser login)
echo "installing yt-dlp, faster-whisper, trafilatura, requests, browser-cookie3…"
python3 -m pip install "yt-dlp>=2024.1" "faster-whisper>=1.0" "trafilatura>=1.8" \
                       "requests>=2.31" "browser-cookie3>=0.19"

# 3b. gitignored cookies dir (for manual per-site cookie files, if the auto browser read misbehaves)
mkdir -p brain/cookies
[ -f brain/cookies/.gitkeep ] || echo "# drop <domain>.txt cookie exports here (gitignored)" > brain/cookies/README.txt
grep -q "brain/cookies/" .gitignore 2>/dev/null || printf "\n# NFL-Brain local secrets — never commit\nbrain/cookies/\nbrain/brain.conf\n" >> .gitignore

# 4. verify
python3 - <<'PY'
import importlib, sys
ok = True
for m in ("yt_dlp", "faster_whisper", "trafilatura", "requests", "browser_cookie3"):
    try: importlib.import_module(m); print(f"  {m}: ok")
    except Exception as e: ok = False; print(f"  {m}: FAILED — {e}")
sys.exit(0 if ok else 1)
PY

echo ""
echo "== done. quick tests (point --vault at your Obsidian vault) =="
echo '  source .venv/bin/activate'
echo '  python3 brain/brain_article.py "<news-url>"  --vault ~/Downloads/NFL-Brain'
echo '  python3 brain/brain_video.py   "<youtube-url>" --vault ~/Downloads/NFL-Brain'
echo ""
echo "First video will download the Whisper model (~0.5 GB, one time)."
