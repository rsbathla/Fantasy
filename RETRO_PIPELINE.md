# The Retro Pipeline — walk-forward 2025 dress rehearsal → 2026 turnkey

**Goal.** Build the standing weekly process once, validate it walk-forward on 2025 (strict
no-look-forward), so 2026 is turnkey: same code, live data swapped in for historical.

**The discipline that makes it valid.** For film-room week N of season S, every input is built
from data STRICTLY BEFORE that slate:
- data layers (middle funnels, defense splits, usage/role) → `before=(S, N)` (2024-full for wk1,
  growing each week). No 2025 game informs a pre-lock 2025 read.
- analyst/film content → only items published in the inter-week window
  `[after (S, N-1) Sunday main … before (S, N) lock]`. Analysts wrote it then, so it is inherently
  no-look-forward.
This is exactly what live 2026 will look like — the only difference is *when* the fetch runs.

---

## Stage 1 — INGEST (the reusable machinery; the point of the whole exercise)

For each week, pull every tracked source's inter-week-window content and normalize to the
contract: `retro_raw/{S}/wk{N}/*.txt`, first line `SOURCE\thandle\tYYYY-MM-DD\turl`, body = text.

Source tiers and their adapters (a source MANIFEST, not ad-hoc fetching):

| tier | sources | adapter | who runs it |
|---|---|---|---|
| article / newsletter | Solak(ESPN), Gretch(Substack-free), PFF, FantasyPoints, Harmon(Yahoo) | WebSearch→WebFetch→stance-extract | **agent, cloud** (proven) |
| video | Kollman, Solak-video, video pods | yt-dlp + whisper (`brain_video.py`) | **user Mac** → transcripts to retro_raw |
| X / tweets | the 59 handles, date-filtered | twitterapi.io REST + key | agent cloud (needs key) OR Mac |
| podcast | Stealing Signals, ETR, Yahoo Forecast | RSS + whisper | **user Mac** |

Article tier is fully cloud-automatable now (WebFetch). Video/podcast tier runs on the Mac
(`brain_video.py`, already built). X tier waits on a twitterapi.io key. All tiers write the SAME
contract, so downstream is source-agnostic. **In 2026 the adapters are unchanged — you just run
them live each week instead of on historical URLs.**

## Stage 2 — AS-OF DATA LAYERS (no look forward)

- `build_middle_funnel.py --before (S,N)` → middle funnels + player middle-win (done).
- (roadmap) usage/role, defense splits, target-share trajectory — same `before=` cutoff.

## Stage 3 — SYNTHESIZE (the pre-lock decision pack)

Compose, per player in the slate:
- middle matchup edge (`middle_week`), frequency-weighted (C8);
- analyst film/opportunity signals (`analyst_retro.build_week`), categorized
  (opportunity / film / injury) with attribution;
- the buy-the-dip / fade-the-spike divergence flags (stance vs the box score).
→ the film-room week pack: what the data says + what the film/people saw that the data misses.

## Stage 4 — VALIDATE (only in the 2025 rehearsal; the payoff)

Post-game, grade the pack against actuals: did middle-smash tags beat projection? did buy-the-dip
divergences recover? which analysts' non-obvious calls carried alpha? Frequency-weighted, season-
wide. Whatever survives out-of-sample is what 2026 trusts; whatever doesn't comes off the board.

## 2026 handoff

Same four stages. Stage 1 fetch runs live (or on a weekly scheduled task). Stages 2-3 produce the
pre-lock pack you build lineups from. Stage 4 runs after games to keep refining the analyst weights
and funnel tags. Nothing is rebuilt — the rehearsal already hardened it.

## Status (2026-07-08)

- Stage 1 article adapter: PROVEN (5 real Week 1 2025 sources ingested from the cloud).
- Stage 1 video/X: specified; video via Mac `brain_video.py`, X pending key.
- Stage 2 middle funnel as-of: BUILT + tested. Other layers: roadmap.
- Stage 3 synthesis: middle board + divergence board + ceiling key BUILT; composition = `retro_pipeline.py`.
- Stage 4 validation: not yet run (the season sweep).
