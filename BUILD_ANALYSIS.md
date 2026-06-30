# Best Ball Toolkit — Build Analysis
**Run 2026-06-16 · automated QA across all modules + end-to-end pipeline.**

## Verdict
**Functional end-to-end and usable for live drafting.** All 12 Python modules compile, the live pipeline runs from a pasted board to a rendered dashboard, the win-Δ model is built on the validated survival chain, and the qual layer (225 written summaries + the 15% qual_signal) is wired in. Three items are worth addressing before *full* reliance; one is a real bug, the rest are decisions/refreshes.

## Component status
| Piece | Status | Note |
|---|---|---|
| `draft_assistant.py` (engine + `--json`) | ✅ | compiles, runs, emits structured candidates |
| `draft_pick.py` (terminal, clip/file) | ✅ | Windows-safe clipboard + `sys.executable` |
| `dashboard.py` + `_dash_template.html` | ✅ | e2e run renders 24 rows, verdict, win-Δ, expand |
| `win_delta.py` | ✅ | on real `survival_chain`; fast-vs-full ordering ρ=1.0 |
| `merge_rankings.py`, `build_draft_board.py` | ✅ | paths made portable |
| `parse_clay.py` | ⚠️ **bug** | still hardcodes the old machine's session path |
| `qual_summary.csv` | ✅ / partial | 225 real prose; ~145 deep players fall to structural read |
| `overlays.csv` (30) · `qual_signal.csv` (86) | ✅ | risk/trap flags + 15% merge layer active |

## What works (strengths)
- **Compiles & runs:** 12/12 modules OK; e2e `dashboard.py` → `pick_dashboard.html` renders top-10 + toggle + click-to-expand.
- **Win-Δ is grounded:** it *is* `survival_chain` with common random numbers, and the fast setting's ranking matched the full sim exactly (ρ=1.0). Sanity holds — a QB tops Δtitle for a 0-QB roster.
- **Three layers per pick:** quant (board rank, ceiling, reg-season rank, playoff schedule) + qual (225 syntheses + the tweets behind them) + overlay (risk/trap/age flags), with a synthesized verdict banner.
- **Runs off the clipboard**, user clicks every pick, the tool never touches the contest or money.

## Findings & risks (ranked)
1. **🔴 `parse_clay.py` portability bug.** It still references `/sessions/vibrant-kind-heisenberg/…`, so the *weekly Clay rebuild* will fail until patched (same fix already applied to `merge_rankings.py` / `build_draft_board.py`). **Live drafting is unaffected** — this only bites on a board rebuild. One-line fix.
2. **🟠 Two boards still unreconciled (§1 of the master handoff).** The merged ceiling+advancement board vs the survival-p85 board — decide which governs picks. Everything downstream is consistent once you pick.
3. **🟠 Win-Δ absolute % is noisy / NS-sensitive.** Same player can read +0.78% one run and double-digits on a different roster/seed. **Trust the ranking, not the raw number** (your playbook says the same), and bump `--ns` on high-stakes picks for stability.
4. **🟠 Summary coverage is 225/371.** The draftable core is fully prose; the ~145 deep-tail players show the structural-read line. Run `build_qual_summary.py` (needs an API key) to fill the gated remainder in one pass.
5. **🟠 Data freshness.** The tweet corpus is **Apr 24 – May 27**; the summaries and the 15% qual_signal are a snapshot. Refresh `tweets.db` (5 sources were already stale) before drafting for real money.
6. **🟡 `clip` mode unverified on real Windows.** The logic is correct (PowerShell `Get-Clipboard`); just can't be tested from this sandbox. Fallback to `Board.txt` always works.
7. **🟡 Early-draft win-Δ favors empty starting slots** (by design — it correctly screams QB/TE when you have none; weigh that against best-available later).

## Recommendations (priority order)
1. Patch `parse_clay.py` paths (I can do it now — same portability fix).
2. Decide the governing board (§1) so the merge and the survival board don't drift.
3. Refresh `tweets.db`, then re-run `build_qual_summary.py` for full summary coverage + a current qual_signal.
4. Read win-Δ as an **ordering**, not a probability; raise `--ns` when it matters.
