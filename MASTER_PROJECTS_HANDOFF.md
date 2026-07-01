# Master Handoff — All Projects
*Generated 2026-07-01. A single reference for every project found in the connected `Downloads` folder and the cloud workspace: what each is, its key files, where it lives, and status.*

---

## 0. How to read this — two locations
Your work spans two places, and it matters which is which:

- **Your computer — `C:\Users\ramne\Downloads`** (the folder connected to this session). Durable. Most standalone projects live here.
- **The cloud workspace** (`/root/bestball/bestball`). Where the NFL suite is actively built. **Ephemeral** — wiped when the session is reclaimed, and there is **no git remote**, so nothing here persists unless copied to your computer.

Scope note: this covers the projects visible in the connected `Downloads` folder plus the cloud NFL suite. If you keep projects in other folders (Desktop, Documents, another drive) that aren't connected to this session, point me at them and I'll fold them in.

---

## 1. NFL Best Ball / DFS / Dossier suite  (+ live X intelligence layer)
**Lives in:** cloud workspace `/root/bestball/bestball` (ephemeral, no remote). Durable copies delivered to `Downloads`: `dossier_deep.html`, `ff_dossier_x_store.json`, `HANDOFF_X_DOSSIER.md`, `MASTER_PROJECTS_HANDOFF.md` (this file). The bulk model data (`NFL-master/` — PFF/FTN/FantasyPoints/nfl_pro_scraper) lives **only in the workspace**, not on your PC.

**What it is:** a production suite of 2026 fantasy-football models (~139 Python files) that ingests advanced charting/projection data, runs Monte-Carlo sims + a multi-signal "fusion" consensus, and renders self-contained HTML dashboards. Drafts and grades on **upside (p95 ceiling / survival chain)**, not mean projection.

**The models & entry points:**
- **Best Ball draft model** — `draft.py` (paste a DraftKings *or* Underdog board → auto-detect → grades every pick via a survival chain optimizing advancement × playoff title) → `decision_dashboard.html`. Live engine in `engine/`.
- **DFS weekly model** — `dfs_model.py --week N` → per-player matchup edge (player strengths vs opponent-defense softness on the same man/zone/deep/slot axes) + who-to-play + lineup templates → `dfs_week.html`.
- **Dossier** — `build_dossier_deep.py` → `dossier_deep.html` (369 players; player/offense/defense/coaching fundamentals).
- **Home page** — `build_home.py` → `home.html` (routes to all three tools).
- **Live X / tweet intelligence** — the layer we've been building: `build_pull_*.py` → `build_x_store.py` (`x_store.json`, 94 tweets) → `x_dossier_refresh.py` → `build_x_narrative.py` → `build_x_media.py` → `build_dossier_deep.py`. 48 tracked analyst handles in `x_handles.txt`. **See `HANDOFF_X_DOSSIER.md` for the full detail.**

**Key subsystems:** `fusion.py` (~65 KB, blends 15+ signals into a consensus, divergence-as-leverage); a **FastAPI read service** in `api/` (`/api/v1`, pandas-free); `ctx_panel.py` (shared 4-layer EPA drilldown injected into the HTML).

**Status:** Phases A–G complete; all three products run end-to-end and render clean. Open: Underdog "which-picks-are-mine" needs one real paste (works via `--mine`); in-season DFS swaps to live stats once games start; X history accumulates forward (list caps ~14h — a true 7-day pull needs the paid API or a local scroller); video transcripts need a local whisper tool. See `PROJECT_PROGRESS.md`, `GOALS_COVERAGE.md`, `ENGINEERING_REVIEW_2026.md`.

---

## 2. Pokémon Grade-Flip Bot
**Lives in:** `C:\Users\ramne\Downloads\bot-platform\pokemon_bot` (+ `pokemon_bot.zip`).

**What it is:** finds underpriced graded/raw Pokémon cards on eBay, ranks **grade-flip EV** against Card Ladder sold-based comps, and includes a card grade-model ML framework. Principle: missing comps → the bot abstains rather than guessing.

**Entry points:**
- `python -m pokemon.morning` (or `run_morning.bat`) — broad BIN + auction scan ($500+ auctions / $1500+ BIN) → sortable HTML dashboard (`reports/morning_dashboard_*.html`).
- `python -m pokemon.build_flips --check` — eBay listings × Card Ladder comps → ranked by EV.
- `python -m pokemon.grademl.cli add-url/stats` — grade model (logs cards by eBay URL, pulls photos, centering via yellow-border detection, edge-whitening, focus).

**Layout:** `pokemon/data/` (eBay Browse API + Card Ladder + comps store), `pokemon/ev/` (grade-and-flip EV), `pokemon/grademl/` (dataset/features/model/ingest), `core/` (config/storage/alerting), `tests/` (pytest). Config via `.env` (eBay + Card Ladder keys — **see §7**).

---

## 3. Crypto Prediction-Market Arbitrage Bot
**Lives in:** `C:\Users\ramne\Downloads\crypto_arb_bot` (+ several `crypto_arb_bot (N).zip` backups, `crypto_arb_bot_usage_guide.pdf`).

**What it is:** cross-platform arbitrage detection + execution across **8 prediction-market platforms** for **crypto pricing events** (e.g. "BTC above $80K today?"). When YES on one platform + NO on another totals < $1.00, it locks guaranteed profit. Monitors **28 cross-platform pairs**.

**Platforms:** Polymarket, Kalshi, Manifold, Drift BET, Robinhood, Coinbase, DraftKings Predictions, FanDuel Predicts (Kalshi-group and CME-group share contracts → resolution risk eliminated within a group).

**Architecture:** `bot.py` (orchestrator) → `modules/` (`multi_platform_fetcher`, `multi_platform_matcher`, `arbitrage_detector` (fee-adjusted), `trade_executor` (paper/live), `alert_manager` (desktop/sound/webhook), `dashboard.py` (live web dashboard at `localhost:8877`), `backtester` + `multi_platform_backtester`, `pnl_simulator`, `platforms/`). Safety guardrail: only trades when net profit > 2% after both platforms' fees (+ more). Logs/alerts in `alerts/*.jsonl`, `logs/`. Config in `config/settings.py`, `.env`, **`kalshi-key.pem.txt` (private key — see §7).** Also present: `Poke Alpha Backup.txt` (887 KB, appears to be an unrelated backup).

---

## 4. DK Pitch Lab v2
**Lives in:** `C:\Users\ramne\Downloads\dk-pitch-lab-v2` (plus many `DK Pitch Lab v2 (N)` and `dk-pitch-lab-v2 (N)` version copies).

**What it is:** a **built web app** (a compiled React/Vite frontend — `index.html` + `assets/index-*.js` (543 KB) + `assets/*.css`), generated via "Perplexity Computer." From the name, a DraftKings **MLB pitching** DFS analysis tool. Note: only the **compiled bundle** is on disk — there is no source project here, so it can be opened/run in a browser but not easily edited without the original source. The many `(N)` copies are repeated downloads of the same build.

---

## 5. Collectabit Scripts (eBay / CGC card scanner)
**Lives in:** `C:\Users\ramne\Downloads\collectabit-scripts`.

**What it is:** a set of Node.js scripts (`.mjs`) for trading-card market analysis (CGC = a card-grading company), a sibling to the Pokémon bot's domain:
- `ebay-active-scanner.mjs` — scans live eBay listings.
- `cgc-analysis-v2.mjs` / `cgc-lowest-listings.mjs` — CGC-graded card analysis / lowest-price finder.
- `listing-validator.mjs` — validates listings.
- `build-report.py` / `build-lowest-report.py` — report generators.

---

## 6. NBA / WNBA DFS data corpus
**Lives in:** `C:\Users\ramne\Downloads` (root) — hundreds of `MM-DD-YYYY-nba-season-{dfs,player,team}-feed.xlsx` (and some `wnba-season-*`) dating back to 2022, the `24-25-season` / `25-26-season` folders (many version copies), and `contest-standings-*` folders.

**What it is:** not a codebase but a **data corpus** — daily DFS projection/player/team feeds and DraftKings contest standings, presumably the raw inputs to an NBA/WNBA DFS workflow. If you want, I can build an NBA DFS model over these the way the NFL suite works.

---

## 7. Credentials & sensitive files — keep private
These hold live keys; I did **not** open or copy their contents, but you should know where they are:
- `crypto_arb_bot/.env` and **`crypto_arb_bot/kalshi-key.pem.txt`** (Kalshi private key).
- `pokemon_bot/.env` (eBay + Card Ladder keys).
- The NFL suite's X Bearer token is handled blind (never stored in the repo; `.env` is gitignored).
Treat these as secrets — don't paste them into chats or commit them anywhere public.

---

## 8. Where everything lives — quick map
| Project | Location | Type | Durable? |
|---|---|---|---|
| NFL Best Ball/DFS/Dossier + X layer | cloud `/root/bestball/bestball` | Python suite + HTML | **No** (copies in Downloads) |
| X accumulation store | `Downloads/ff_dossier_x_store.json` | data (94 tweets) | Yes |
| Deep dossier | `Downloads/dossier_deep.html` | HTML | Yes |
| Pokémon Grade-Flip Bot | `Downloads/bot-platform/pokemon_bot` | Python | Yes |
| Crypto Arb Bot | `Downloads/crypto_arb_bot` | Python | Yes |
| DK Pitch Lab v2 | `Downloads/dk-pitch-lab-v2` | built web app | Yes |
| Collectabit scripts | `Downloads/collectabit-scripts` | Node scripts | Yes |
| NBA/WNBA DFS feeds | `Downloads` (root) | data (xlsx) | Yes |

**Reminder:** the NFL suite is the one project that is *not* durable on its own — it lives in the ephemeral cloud workspace with no git remote. The store, dossier, and handoffs copied to `Downloads` are what survive; to keep the NFL suite itself, it would need to be pushed to a git remote or exported to your computer.
