# Handoff — X (Twitter) Intelligence Layer for the Fantasy Dossier
*Generated 2026-07-01. Covers everything ingested, every file, and where each lives.*

## 1. What this is
A live layer that pulls fantasy analysts' X posts + the articles/videos they link, maps each to the
player(s) and team(s) it names, forms a per-player **narrative** (what people are saying → the player's
profile), and merges it all into the deep dossier (`dossier_deep.html`). It grows over time via an
**accumulation store** so history builds forward pull-by-pull.

## 2. Two locations — read this first
Nothing here runs on your PC except by copy. There are two separate places files live:

- **The project (cloud workspace):** all the code + data below lives in the project working copy in
  Anthropic's cloud sandbox. **It is ephemeral** — wiped when the session is reclaimed, and there is
  **no git remote**, so it does not persist on its own.
- **Your computer — `C:\Users\ramne\Downloads`** (the folder connected to this session): the only place
  that survives. To make the accumulation durable, the store is copied here as
  **`ff_dossier_x_store.json`**, and this handoff + the dossier are delivered here too (see §7).

## 3. What was ingested (the data, as of this handoff)
- **48 tracked analyst handles** — the source list (`x_handles.txt`). Full list in §8.
- **Accumulation store — 94 unique tweets** across **3 pulls**, spanning **2026-06-30 11:00 → 07-01 01:46
  UTC** (`x_store.json`). De-duplicated by tweet id; keeps max engagement + links; tracks the newest/
  oldest high-water mark.
- **Mapped to 33 players and 32 teams** (`x_live.json`) — only genuine full-name mentions (the mapper
  requires first + last name, so "LeBron **James**" ≠ Jordan James, etc.).
- **33 per-player narratives** (`x_narrative.json`) — sentiment (bullish/bearish/mixed/neutral) + themes
  + a synthesized take, each grounded in that player's actual mapped posts, attributed, never invented.
- **7 indexed media items** (`x_media.json`) — articles/videos/podcasts, classified + summarized (public
  articles fetched in full; paywalled/video items summarized from the posting thread and labelled).

## 4. The pipeline (how a pull becomes dossier content)
```
(browser scroll of the list OR X search)  ->  harvest tweets + links + video flags
   -> build_pull_<date>.py         writes x_pull_<date>.json   (one file per pull)
   -> build_x_store.py             merges ALL pulls -> x_store.json   (dedup, grows)
   -> x_dossier_refresh.py --input x_store.json -> x_live.json   (map to players/teams)
   -> build_x_narrative.py         -> x_narrative.json           (the "what analysts are saying" takes)
   -> build_x_media.py             -> x_media.json               (article/video index + summaries)
   -> build_dossier_deep.py        -> dossier_deep.html          (final dossier, 369 players)
```
Run the whole chain after any new pull; then copy `x_store.json` back to Downloads (§7).

## 5. Every file (in the project working copy)
**Inputs / config**
- `x_handles.txt` — the 48 tracked analyst handles (edit to add/remove).
- `features.csv` — the player universe the mapper matches against (name/pos/team).

**Pull builders → per-pull data**
- `build_x_posts.py` → `x_posts.json` — pull #1 (list scroll, 48 tweets, 2026-06-30).
- `build_pull_20260701.py` → `x_pull_20260701.json` — pull #2 (list, 31 tweets).
- `build_pull_20260701b.py` → `x_pull_20260701b.json` — pull #3 (X-search grab, 20 originals).

**Store + mapping + layers**
- `build_x_store.py` → `x_store.json` — the accumulation store (94 tweets). **The durable artifact.**
- `x_dossier_refresh.py` → `x_live.json` — maps store → players/teams (mapper hardened vs false positives).
- `build_x_narrative.py` → `x_narrative.json` — per-player synthesized takes (33).
- `build_x_media.py` → `x_media.json` — article/video/podcast index + summaries (7).
- `build_dossier_deep.py` → `dossier_deep.html` — the deliverable dossier (adds "What analysts are
  saying", "Articles & video (indexed)", and live-tweet sections to each player card).

**Alternate (paid API) path — not currently used**
- `x_fetch.py` / `x_fetch.ps1` / `run_x_fetch.bat` — pull via the paid X API (App-Only Bearer). Runs on
  your machine (the sandbox is network-blocked from X). This is the ONLY way to get a full week in one shot.
- `X_MCP_SETUP.md` — setup notes for the official X MCP / API path.

**Prior/archived**
- `_archive/build_player_tweets.py` — the original tweet mapper that read the old local `tweets.db`.

## 6. On YOUR computer (`C:\Users\ramne\Downloads`)
- **`ff_dossier_x_store.json`** — the persisted accumulation store (copied here so it survives). This is
  the file to keep; a future session stages it back in to continue accumulating.
- **`HANDOFF_X_DOSSIER.md`** and **`dossier_deep.html`** — delivered here (this doc + the dossier).
- **Your original NFL/fantasy source data** already lived here (the `*-nba-season-*feed.xlsx` files, DFS
  contest standings, etc.). Note: the **old `tweet-bot_1/2/3/` folders and their `tweets.db`** — the
  output of your original local "scroller + faster-whisper" stack (63 tweet sources + 237 transcribed
  videos) — are **no longer present** in this folder.
- The bulk NFL model data (`NFL-master/` — FP/PFF/FTN/nfl_pro_scraper) lives in the **project**, not here.

## 7. How to continue (resume + pull)
- **Resume after a reset:** stage `ff_dossier_x_store.json` from Downloads back into the project as
  `x_store.json`; the builders are in the project. Then pull + run the chain in §4.
- **New pull ("just say pull"):** scroll the list (or an X-search `from:` group) → new `build_pull_*.py`
  → run the §4 chain → copy `x_store.json` back to Downloads. Each pull reaches ~14h and overlaps the
  last, so ~2 pulls/day fills a rolling 7-day window over the coming week.

## 8. The 48 tracked handles
32beatwriters, 4for4_john, 4for4football, adamlevitan, ahaanrungta, aschatznfl, benjaminsolak,
brettkollmann, chessliam, clevta, coachspeakindex, connorallennfl, dbro_ffb, dhananizain, fantasypts,
fantasyptsdata, fball_insights, ffdataroma, ffnatejahnke, grahambarfield, haydenwinks, ihartitz,
jagibbs_23, jakobsanderson, jamesdkoh, johntoddnfl, joshnorris, koalatystats, lateroundqb,
mattharmon_byb, mikeclaynfl, nextgenstats, ooooftw, pat_thorman, patkerrane, pff_fantasy,
rotostreetwolf, ryanj_heath, ryanmc23, sammonsonnfl, scottbarrettdfb, sigmundbloom, smitchell17,
sumersports, superrnova38, syedschemes, tejfbanalytics, the_oddsmaker
*(All 48 are also members of the private X List "FF Analysts", id 2072071516770955274, on @rsbatz.)*

## 9. Confirmed limitations (why it works the way it does)
- **The list timeline serves only a fixed ~14h window** and won't paginate deeper.
- **X search reaches back the full 7 days**, but only via scrolling, which yields ~1-2 tweets/scroll —
  so a full week of 48 analysts (thousands of tweets) isn't feasible by scroll alone.
- **Direct GraphQL replay is blocked** — X requires a per-request `x-client-transaction-id` from
  obfuscated JS; replaying even the exact captured search request returns 404. The old v1.1 APIs are dead.
- **A true one-shot full week needs the paid X API** (`x_fetch.ps1` on your machine) **or a recreated
  local scroller + faster-whisper** stack. Everything else accumulates forward over calendar days.
- **Video transcripts** require the local whisper tool; without it, videos are summarized from the
  posting tweet + title, and say so.

## 10. Sample of what's captured so far (signal highlights)
- **Jaxon Smith-Njigba** — elite/premier route runner (Harmon RP: 77.8% vs man 94th pctl).
- **Aaron Rodgers** — dead deep ball (35th, 9.4%) → caps his WRs' downfield ceiling.
- **Chiefs run game** — Dhanani: KC built for a real run game around Kenneth Walker; **Xavier Worthy** the breakout call.
- **4for4 2026 O-line tiers** — Broncos tier-1; Chiefs/Packers/Saints/Bengals tier-5 (team run-context).
- **Zone-beaters** (Fantasy Points YPRR) — Jayden Reed, Ja'Marr Chase, Khalil Shakir, Jaylen Waddle.
- **Route depth** (Dhanani/FantasyPoints) — shallower trees boom more + bust less than deep threats.
- **Josh Jacobs** — durability caution (right-leg injury pile-up vs touch volume).
- **CJ Stroud** — Year-2 scheme comfort in Nick Caley's offense; **TreVeyon Henderson** — hidden 911/9 line.
- Full detail per player in `dossier_deep.html`.
