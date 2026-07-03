# HANDOFF — Tweet / Video Intel Pipeline (for the NJ computer)

**Read this first.** This is the pickup point for continuing the X (Twitter) tweet-ingest and
video→transcript work. Everything referenced here is committed to GitHub on the branch below. Your
job, in the user's words: turn best-ball / analyst / week-1-contest **videos into transcripts**, be
**more thorough** with the ingest, and **actually utilize** it across the model's layers.

Prepared this session (2026-07-03) after a full read-only review of the ingest + video process.

---

## 0 · Locked decisions (from the user, this session)
- **Build order:** *transcription pipeline first* (the headline capability) — not the wiring-first path.
- **ASR location:** *decide later* — recommendation is your PC (the proven whisper stack; see §5).
- **Signal scope:** *display-only, always.* Transcript/analyst signal appears as attributed, timestamped
  callouts in reports/dossiers and **never moves a ranking, score, or flag** unless a human promotes it
  through the sanctioned gates (§6). This is a hard rule.

---

## 1 · How to get everything

```
git clone https://github.com/rsbathla/Fantasy.git
cd Fantasy
git checkout integration-audit-and-wiring     # <-- all the work is on this branch
```
The branch is 5 commits ahead of `main` (clean history; `main` @ 301ca2a is the common ancestor).
Latest commit is the one carrying this file.

**Verify you have it all (run these — see §8 for expected counts):**
```
git ls-files | wc -l                      # ~1255 tracked files
git ls-files NFL-master/ | wc -l          # 524 raw-export files (PFF/FTN/FantasyPoints), 18 MB
du -sh NFL-master boom data profiles sis_value
python3 ask_data.py player "Ja'Marr Chase"  # sanity: the data librarian resolves
```

---

## 2 · What is on GitHub right now (the tweet/video + intel inventory)

Everything downloaded/ingested that exists in this workspace is committed. The raw source exports
(`NFL-master/`, 524 files) and every derived layer are tracked. Tweet/video specifically:

| File | tracked | what it is | vintage |
|---|---|---|---|
| `x_store.json` | ✅ | **accumulated** browser-pull tweet store — 94 posts, dedup by id, high-water likes | pulls 2026-06-30→07-01 |
| `x_posts.json` | ✅ (added this session) | latest raw pull (48 posts) — **all 48 already inside `x_store.json`**, kept for completeness | 2026-07-01 |
| `x_live.json` | ✅ | store→player/team map (33 players, 32 teams) | derived |
| `x_narrative.json` | ✅ | 33 hand-authored per-player takes (sentiment+themes) | derived |
| `x_media.json` | ✅ | 7 media items (4 video/2 article/1 podcast)→20 players + an `unresolved` bucket | derived |
| `intel_data.json` | ✅ | 2.9 MB — 371 players, 1,593 "about" + 2,535 "comp" tweets, source tiers A/B, graded claims | **built Jun 28 from the now-absent `tweets.db`** |
| `video_notes.csv` | ✅ | 100 players × 331 clip quotes (≤320 chars, no timestamps) — legacy, quality-flagged | Jun 17 |
| `qual_signal.csv` | ✅ | 86 players coachspeak score — the ONLY analyst-text→model path (feeds `fusion.py`) | Jun 17 |
| `x_handles.txt` | ✅ | 48 tracked handles | — |
| `_archive/player_tweets.json` | ✅ | full per-player tweet text — **lives only in `_archive/`** (see §7 dark panel) | — |
| Builders | ✅ | `build_x_store.py`, `build_x_posts.py`, `build_x_narrative.py`, `build_x_media.py`, `x_dossier_refresh.py`, `build_intel.py`, `refresh_intel.py`, `x_fetch.py`, `render_intel.py`, `ctx_panel.py` | — |

`.env` and any `*BEARER*`/`*.pem*` are gitignored and were **never** read/printed/committed — keep it that way.

---

## 3 · ⚠️ CRITICAL — data that is NOT here and must be recovered

The single most important gap. The legacy pipeline ran on the **original PC** and its database is
**absent from this workspace**:

- **`tweets.db`** (was at `../Downloads/tweet-bot_3/tweets.db`) — held **63 tweet sources + 237
  transcribed videos** with source reliability tiers. `build_intel.py:11` still points at it.
- **The 237 whisper transcripts** — gone with the DB. `intel_data.json` (Jun 28) was the last thing
  built from it and is the only surviving distillation.
- **The scroller / `tweet-bot_3/` ingest tool** and `run_ingest.bat` — not in this repo.

**Action for NJ:** locate `tweets.db` + the transcript files on the original machine and restore them
into the repo (or a known path), OR treat them as lost and re-ingest going forward. Until then,
`build_intel.py` cannot be re-run — it reads a DB that isn't here. This is why the transcript pipeline
(§5) is being rebuilt rather than resumed.

---

## 4 · What I did this session (context)

Three things, all committed:
1. **DFS conversion stack** — game-script Monte Carlo (`game_sim.py`), PROE pass/run conversion
   (`validate_proe_conversion.py`, `build_proe_2026.py`, wired in `dfs_model.py`), red-zone/TD-equity
   lever (`build_rz_equity.py`), all backtested on 2024-25 actuals; Week-1 written report
   (`build_dfs_week_report.py`). See the commit `DFS conversion stack…`.
2. **Data librarian** — `ask_data.py` (grounded player/team/coverage/matchup lookups with `[file·year]`
   provenance), `DATA_INDEX.md` (derived-layer index), `.claude/agents/data-librarian.md` (a persistent
   agent). Use this to answer data questions while working.
3. **This tweet/video review** — Fable did a full read-only architecture review →
   **`X_VIDEO_INTEL_REVIEW.md`** (the plan you execute). The current file is the handoff wrapper around it.

---

## 5 · The job — video→transcript pipeline (execute this)

Full detail + effort estimates in **`X_VIDEO_INTEL_REVIEW.md`**. Summary of the five stages (extend the
named files — do NOT restart):

- **Stage 0** — capture media identity at ingest: add `media:[{type,url,duration}]` to the store merge
  (`build_x_store.py`); make `x_fetch.py:search()` actually emit the `attachments.media_keys` it
  requests; turn `x_media.json`'s `unresolved` bucket into a drainable work-queue.
- **Stage 1** — **ASR: new `x_transcribe.py`.** yt-dlp/ffmpeg → 16 kHz wav → faster-whisper →
  timestamped segments → `x_transcripts.json` (accumulate, never overwrite). *Tooling: this repo's
  sandbox has ffmpeg but NOT whisper/yt-dlp, and cannot reach X-native video; your PC is the reliable
  place to run this — recreate the stack that made the original 237. See `HANDOFF_X_DOSSIER.md`,
  `SETUP_WINDOWS.md`, `X_MCP_SETUP.md`.*
- **Stage 2** — entity linking: reuse `x_dossier_refresh.map_post` per transcript segment; add
  `x_aliases.json` ("JSN"→"jaxon smith njigba", "CMC"…) — also fixes tweet-side recall. Honor the
  key-format rules in `DATA_INDEX.md` (everything keys on `core.fn`).
- **Stage 3** — claim extraction: lift the 11 claim regexes + the claim-backtest verdict/stability
  table that already exist in `build_intel.py:51-88`; add `injury/role/usage_trend/coaching_scheme/
  draft_intent` dims → `x_video_intel.json` (each claim: quote, speaker, `url#t=` timestamp, verdict).
- **Stage 4** — synthesis: make `build_x_narrative.py` evidence-grounded (write the take from a
  machine-collected digest instead of hand-typing).

Then **utilization** (priority order, from the review): dossier → `intel_data.json` → player_explorer →
DFS weekly "analyst read" callout (display-only) → flag/registry **promotion queues** → (only if later
approved + backtested) fusion coachspeak → audit staleness/dead-input ratchets.

---

## 6 · The rules — follow these as hard constraints

Read before touching anything (all committed):
- **`CLAUDE.md`** — standing orders: Prime Rule (verified repo layers > web search > priors), no
  single-signal anchoring, evidence discipline (ADP≠DFS cost), deliverable contract, extend-don't-restart.
- **`PLAYBOOK.md`** — case law C1–C11 (the specific mistakes not to repeat).
- **`agents/UNIVERSAL_DISCIPLINE.md`** — the ten failure modes of "the naturally easy thing" (domain-agnostic).
- **`ground_truth_registry.json`** — verified post-cutoff facts that OUTRANK model priors; anything
  a transcript claim contradicts gets **flagged**, never silently adopted.
- **Integrity for this work specifically (from the review §5):** analyst claims are tier-2 evidence —
  confirm/extend verified layers, never overrule. Every claim carries status {reported | analyst-take |
  speculation} + corroboration count + the against-our-data verdict. **Likes ≠ reliability.** Hard wall
  between display (auto-flow OK, always attributed) and scoring (only through the two gated paths).
- **Security:** never read/print/commit `.env`, `*BEARER*`, `*.pem*`, or any credential file. Don't
  surface cookie/session/auth data. Don't commit tokens.

---

## 7 · Missing steps / open items to audit (checklist for NJ)

- [ ] **Recover `tweets.db` + the 237 transcripts** from the original PC (§3) — or accept re-ingest.
- [ ] **Restore `player_tweets.json` to repo root** — `build_player_explorer.py:25` reads it, but it
      exists only in `_archive/`, so the explorer's tweet panel renders **empty with no warning**.
- [ ] **`build_intel.py:11` path is dead** (`../Downloads/tweet-bot_3/tweets.db`) — repoint or gate.
- [ ] **`x_fetch.py` discards the media fields it pays for** — never activated; fix before any paid run.
- [ ] **Year-less dates** — `build_intel.py:105` stores `created_at[:16]` ("Sun Jun 21 13:14"), which
      sorts meaninglessly; store the full timestamp.
- [ ] **`kind=='news'` section in `build_dossier_deep.py:37` never fires** — no producer emits that kind.
- [ ] **No staleness gate** on any x_/intel artifact — add to `integration_audit.py` (the review §4.8).
- [ ] **Decide ASR location** (PC / sandbox-YouTube-only / hybrid) — recommend PC.
- [ ] **Decide whether to activate the paid `x_fetch.py` backfill** (7-day window, ~tens of $).
- [ ] Confirm `faster-whisper` + `yt-dlp` install on the chosen ASR machine; model weights available.

---

## 8 · Audit — confirm the handoff is complete

Expected on a fresh clone of `integration-audit-and-wiring`:
- `git ls-files | wc -l` → ~1255
- `git ls-files NFL-master/ | wc -l` → 524 ; `du -sh NFL-master` → ~18M
- tweet/video files from §2 all present; `x_store.json` has 94 posts; `intel_data.json` ~2.9M
- `python3 integration_audit.py` → **0 P0 violations** (data-integrity self-check passes)
- `python3 ask_data.py matchup "Ja'Marr Chase" TB` → prints the Cover-3 edge (librarian works)
- **Known-absent (expected):** `tweets.db`, the 237 transcripts, `tweet-bot_3/` (§3) — these are the
  work to recover, not a broken clone.

Questions about any data layer while you work: `python3 ask_data.py …`, or read `DATA_INDEX.md`
(derived layers) / `DATA_CATALOG.md` (raw `NFL-master/` sources).
