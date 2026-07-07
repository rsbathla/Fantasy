# NFL-Brain ingest — setup & flow

Turns tweeted **articles** and **videos** into sourced markdown notes in your Obsidian vault, with
player/team backlinks. Two processes, exactly as you framed it:

- **Automated firehose** — twitterapi.io pulls your tracked handles → every article/video link is
  ingested (`tags: [..., auto]`).
- **Manual picks** — you hand-drop something great with `--star` (`tags: [..., curated]`, ⭐) so it
  stands out and never gets lost in the firehose.

Your vault: **`~/Downloads/NFL-Brain`** (the one with `Players/ Teams/ Sources/`).

## One-time setup
```bash
cd ~/Downloads/Fantasy
bash brain/setup_brain_mac.sh        # ffmpeg + yt-dlp + faster-whisper + trafilatura + requests + browser-cookie3
source .venv/bin/activate
export TWITTERAPI_IO_KEY="your-twitterapi-io-key"   # add to ~/.zshrc to persist
```

## Test the pieces (do this before turning on the schedule)
```bash
# 1. manual capture — one article, one video (proves trafilatura + Whisper work on your Mac)
python3 brain/brain_article.py "https://www.espn.com/nfl/story/…"  --vault ~/Downloads/NFL-Brain
python3 brain/brain_video.py   "https://www.youtube.com/watch?v=…" --vault ~/Downloads/NFL-Brain

# 2. a paywalled article — proves the cookie path (be logged into the site in Chrome first)
python3 brain/brain_article.py "https://www.fantasypoints.com/nfl/articles/…" --vault ~/Downloads/NFL-Brain
#   the note's `fetched_via:` will say browser / cookies file / anonymous

# 3. the puller — lists NEW article/video links from your handles (no ingest yet)
python3 brain/brain_pull.py --vault ~/Downloads/NFL-Brain
```
Open the vault in Obsidian: new notes under `Sources/`, `mentions:` populate backlinks, video notes
carry a timestamped transcript. Re-running any URL is a no-op (idempotent manifest in `_status/`).

**Send me the output of steps 1–3** — especially the video (Whisper) and the paywalled article
(cookies). Once those are green, I add the last, trivial piece:

## Step 2 — the scheduler (built ✅)
`brain_ingest.py` is the orchestrator: it runs the pull, drops junk (promo / affiliate / URL
shorteners / playlists), routes each surviving link to article or video capture, and writes
`_status/last-run.md` — the glance card ("✅ OK · 3 articles · 1 video · 5 junk skipped · 0 errors").

**a. put your key where the scheduler can read it (gitignored, never printed or committed):**
```bash
echo 'export TWITTERAPI_IO_KEY=your-twitterapi-io-key' > brain/brain.conf
```
**b. test one run by hand first:**
```bash
source .venv/bin/activate
python3 brain/brain_ingest.py --vault ~/Downloads/NFL-Brain
```
Open `_status/last-run.md` in the vault — that's your health card. Re-running is cheap (idempotent).

**c. once it looks right, turn on the 7:30am schedule:**
```bash
cp brain/com.nflbrain.ingest.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.nflbrain.ingest.plist
```
Disable anytime: `launchctl unload ~/Library/LaunchAgents/com.nflbrain.ingest.plist`. Logs land in
`~/Downloads/NFL-Brain/_status/run.log` (kept out of the repo). Edit the plist to change the time, or
its `run_brain.sh` path if your repo isn't at `~/Downloads/Fantasy`. (Asleep at 7:30 → it runs shortly
after the Mac next wakes.)

Knobs: `--pages N` (more tweet history per handle), `--max-videos N` (Whisper is the slow step —
default 12/run, overflow rolls to the next run), `--model base.en|small.en|medium.en`.

## Later — claim extraction (next layer, not built yet)
`brain_link.py` will read each new source note and append the sharp bits (injury / role / usage /
scheme) into the mentioned players' `## Intel log`, so a player's note gathers intel automatically.
Deferred on purpose until you've watched the plain firehose for a bit and seen what the notes look like.

## Paywalled sites (FantasyPoints, PFF, 4for4, Establish The Run, FTN…)
The article fetcher reuses **your browser login** — no passwords stored:
1. a per-domain `brain/cookies/<domain>.txt` (Netscape export) if you drop one there, else
2. live cookies from your logged-in Chrome (`browser_cookie3`), else
3. anonymous (fine for free sites).
`brain/cookies/` and `brain/brain.conf` are gitignored. Your cookies/keys stay on your Mac; they're
never printed or committed.

## Notes
- Videos: **YouTube + podcasts** only for now (no login). X-native video is a later add.
- Whisper model defaults to `small.en` (good on player names). `base.en` = faster, `medium.en` = more accurate.
- Cost: ~48 handles × 20 recent tweets/day ≈ $4–8/month on twitterapi.io. Only tweets *with links* get ingested.
