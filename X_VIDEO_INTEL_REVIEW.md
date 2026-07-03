# X / Tweet Ingest + Video Process — Review & Utilization Plan

*Fable architectural review, read-only. No credential files opened, no fetches, nothing modified.
Every figure re-derived from on-disk JSON/CSV.*

## The headline findings

1. **Video content is lost at ingest today.** Zero of the current video/podcast items are transcribed
   — every `x_media.json` item literally says *"not transcribed — needs the local whisper tool."* The
   capability existed before (the legacy PC stack had **237 whisper transcripts** in a `tweets.db`), but
   that DB is **absent from this workspace** — the 237 are gone, and even the ingest half no longer runs
   here. The `unresolved` media bucket is write-only and holds the richest item: a **2h38m AFC West
   projections podcast** — exactly the analyst/contest content to mine.

2. **The dataset dead-ends.** `x_narrative.json` and `x_media.json` each reach exactly one HTML page.
   The DFS layers (`dfs_model`, `matchup_notes`, weekly report) consume **zero** qualitative intel.
   `player_tweets.json` exists only in `_archive/` so the player-explorer tweet panel renders **empty
   with no warning**. `qual_signal.csv` — the *only* analyst-text→model path (feeds `fusion.py`
   coachspeak) — has been static since Jun 17 because its writer is gone.

3. **Three generations of ingest coexist.** Gen-1 local whisper stack (gone), Gen-2 paid X API (built,
   never used, and it *discards the media fields it pays for*), Gen-3 browser-pull (the chosen path:
   94 posts over a ~15h window → 33 players / 32 teams, hand-authored narrative + media literals).

## The video → transcript pipeline (restore + upgrade; extend, don't restart)

Five stages, each extending a named file; only one genuinely new script (`x_transcribe.py`):

- **Stage 0 — capture media identity at ingest.** Add `media:[{type,url,duration}]` to the store merge;
  fix `x_fetch.py` to actually emit the `attachments.media_keys` it requests; promote the `unresolved`
  bucket from strings to a drainable work-queue.
- **Stage 1 — ASR (`x_transcribe.py`).** yt-dlp/ffmpeg → 16kHz wav → faster-whisper → timestamped
  segments → `x_transcripts.json` (accumulate, never overwrite). *Tooling checked: sandbox has ffmpeg
  but not whisper/yt-dlp; pip is allowed but model weights + video download are proxy-gated → this is
  the main infra decision (below).*
- **Stage 2 — entity linking.** Reuse `x_dossier_refresh.map_post` per transcript segment (a 20s window
  names players in full far more than a tweet does); add an `x_aliases.json` ("JSN"→"jaxon smith
  njigba", "CMC"…) which also fixes tweet-side recall for free.
- **Stage 3 — claim extraction.** Lift the machinery that already exists in `build_intel.py` (11 claim
  regexes + the claim-backtest verdict/stability table, currently married to the dead DB) and run it on
  segments; add `injury / role / usage_trend / coaching_scheme / draft_intent` dims → `x_video_intel.json`
  with speaker + `url#t=` timestamp + the same graded verdict tweets get.
- **Stage 4 — synthesis.** Make `build_x_narrative.py` evidence-grounded (agent writes the take from a
  machine-collected digest) instead of hand-typed.

## Utilization — wire it into the layers (priority order)

1. **Player dossier** — replace the stale `video_notes.csv` block with `x_video_intel.json` claims
   (quotes + timestamps + verdict chips). *0.5d, highest value / lowest risk.*
2. **`intel_data.json`** — ingest `x_store` + `x_video_intel` as evidence rows; one insert point
   revives four downstream consumers (dossier, rankings-upside, run_live, intel.html). *1d.*
3. **player_explorer** — repoint the dark tweet panel; add a film panel. *0.25d.*
4. **DFS weekly report — the "analyst read" callout** the DFS side completely lacks: a labeled,
   attributed qualitative line per game side (`Analyst: "<quote>" — @handle (video, W1 preview)`),
   filtered to that week's teams + injury/role/usage dims. **Display-only.** *0.5d.*
5. **Flag / registry promotion queues** — video injury/role claims (≥2 independent sources) emit a
   *review queue*; a human promotes into `roster_flags_2026.json` / `ground_truth_registry.json`.
   Never auto-written. *0.5d.*
6. **Coachspeak revival (model-touching, gated)** — regenerate `qual_signal.csv` from video intel, but
   ship only backtest-gated + revert-flagged + user-approved. *1d+.*
7. **Audit ratchet** — staleness checks on x_/intel artifacts, a dead-input check (would have caught the
   `player_tweets.json` dark panel), each with a known-bad demonstration. *0.5d.*

## Integrity guardrails (non-negotiable)

- Analyst claims are **tier-2 evidence**: may confirm/extend verified layers, never overrule. Anything
  contradicting the ground-truth registry or roster flags is **flagged with both sides**, never silently
  adopted (Prime Rule / C6).
- Every claim carries `status ∈ {reported, analyst-take, speculation}` + corroboration count + the
  against-our-data backtest verdict. **Likes ≠ reliability** — never a credibility proxy.
- **Hard wall:** display/dossier/DFS callouts may auto-flow (always attributed with timestamp
  deep-links). Anything that moves a **ranking/score/flag** flows only through the two sanctioned,
  gated paths (backtest-gated fusion coachspeak; human-promoted roster flags). Injury rumors never
  auto-touch availability.

## Owner decisions before Stage 1 (yours to make)
- **Where ASR runs:** (A, recommended) recreate the proven whisper stack on your PC; (B) in-sandbox for
  YouTube-linked items only, pending a proxy check; (C) hybrid (PC downloads audio, sandbox transcribes).
- Whether to activate the paid `x_fetch.py` path (media fields fixed) for one-shot 7-day backfills.
- Whether transcript signal may ever enter scoring (item 6) or stays display-only permanently.
- Pull / transcribe cadence.
