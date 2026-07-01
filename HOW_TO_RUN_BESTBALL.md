# Best Ball Draft Model — does it work, and how to run it

## Short answer: yes, it works here
I ran it end-to-end in this workspace on both platforms, headless:

| Platform | Board | Result | Time |
|---|---|---|---|
| DraftKings | `engine/fixtures/dk_full_board.txt` | Best pick **Rome Odunze** (WR), ΔTitle +14.2 / ΔAdv +18.0, at pick 56 | ~40 s |
| Underdog | `engine/fixtures/ud_real_board.txt` | Best pick **Marvin Harrison Jr.** (WR), ΔTitle +15.67 / ΔAdv +12.9, at pick 69 | ~41 s |

Both produced a valid ~600 KB `decision_dashboard.html`. Environment: Python 3.11, pandas 1.5.3, numpy 1.26.4 (already installed). Nothing was missing.

## The process (one command)
```
python3 bb_grade.py <board.txt> [--mine "Name|Name|..."] [--seat rsbathla] [--platform dk|ud]
```
`bb_grade.py` is a thin wrapper I added over the proven `draft.py`. It:
1. **Auto-detects** DraftKings vs Underdog from the board text (override with `--platform`).
2. Grades every available pick through the Monte-Carlo **survival chain** (advancement × Week 15–17 title), roster-construction aware.
3. Prints a **readable summary to the screen** — pick, why, your roster/construction, and the decision tree with look-aheads — so you get the answer without opening the big HTML.
4. Writes the full **`decision_dashboard.html`** (per-player signals, stacks, scouting, analyst notes).

The original `python3 draft.py <board.txt> --no-open` still works identically; `bb_grade.py` just adds the in-chat summary.

## How to feed it your own board (in this Cowork session)
There's no clipboard or browser in this cloud workspace, so instead of `clip`:
1. **Paste your draft board text to me in chat** (from the DK or Underdog draft room: select-all → copy), or drop it as a `.txt` file. I'll save it as `board.txt` and run the grader for you.
2. I hand back the **summary in chat** + deliver **`decision_dashboard.html`** to download.

That's the whole loop. A grade takes ~40 seconds.

## Notes & caveats (from the deep-dive)
- **Underdog rosters:** auto-detect usually finds your picks, but to be certain *which picks are yours*, pass `--mine "Player A|Player B|..."`. Without it, if your seat handle isn't in the paste, it silently grades the on-the-clock user's roster.
- **It grades on upside**, not projected points — ΔTitle (playoff title-odds lift) and ΔAdvance (advancement-rate lift) are the currency, by design.
- **Durability:** this suite lives only in the ephemeral cloud workspace with no git remote. The dashboards I deliver to your Downloads persist; the *code* does not. If you want to run this yourself on your own machine, say the word and I'll export the whole runnable suite (code + `pipeline/` data) to your Downloads.
- **Data vintage:** signals are 2025 season + 2026 projections/ADP; the 2026 team/ADP data (`dk_adp.csv`) is accurate to real offseason moves as far as I've verified.
