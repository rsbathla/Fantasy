# Run the Best Ball grader on your PC (Windows) — no Claude in the loop

This is the whole suite, runnable locally. During a draft you copy the board and double-click one file; the graded dashboard opens in ~10 seconds. Nothing leaves your machine.

## One-time setup (about 3 minutes)

1. **Install Python 3.11** from [python.org/downloads](https://www.python.org/downloads/release/python-3119/). On the first install screen, **check "Add python.exe to PATH."** (3.11 is what this was built and tested on; newer versions may work but 3.11 is the safe choice.)
2. **Unzip this folder** somewhere permanent — e.g. `C:\Users\ramne\Downloads\bestball\`. Keep all the files together.
3. **Install the libraries.** Open the folder, click the address bar, type `cmd`, press Enter, then run:
   ```
   pip install -r requirements.txt
   ```
   (One time only. Takes a minute.)

That's it. You never touch the command line again.

## Each pick (during a live draft)

1. In the DraftKings **or** Underdog draft room, select all (**Ctrl+A**) and copy (**Ctrl+C**).
2. Double-click **`DRAFT_FAST.bat`**.
3. In ~10 seconds a terminal shows the best pick + why, and `decision_dashboard.html` opens in your browser with the full detail (per-player signals, stacks, scouting, analyst notes).

The platform (DK vs UD) is auto-detected from what you copied. It grades on **upside** — ΔTitle (playoff-title-odds lift) and ΔAdvance (advancement-rate lift), not raw projected points.

## The two runners

| File | Speed | What it does |
|---|---|---|
| **`DRAFT_FAST.bat`** | ~10 s | On-the-clock. 600 sims, no look-ahead. Same top pick as full mode in testing. |
| **`DRAFT_FULL.bat`** | ~40 s | Slow drafts. Adds the 2-ply look-ahead ("if you take X now, then take Y next pick"). |

## Underdog note (important)
Auto-detect usually finds your picks, but to be **certain** which roster is graded as yours, run it from a terminal with your picks listed:
```
py -3 bb_grade.py clip --fast --open --mine "Ja'Marr Chase|Brock Bowers|DeVonta Smith"
```
Without `--mine`, if your handle isn't in the copied text it silently grades the on-the-clock user's roster instead. (For DraftKings this isn't an issue — it reads your roster directly.)

## If something goes wrong
- **"python is not recognized"** → Python isn't on PATH. Re-run the installer and tick "Add python.exe to PATH," or use the `py -3 ...` form.
- **`pip install` fails to build pandas** → you're likely on Python 3.13+. Install **3.11** specifically (link above); old pandas has no wheels for the newest Pythons.
- **"Board file not found" / empty** → you didn't copy the board first. Ctrl+A, Ctrl+C in the draft room, then run.
- **Blank/odd dashboard** → make sure you unzipped the *whole* folder (the `pipeline\`, `engine\`, and the `.csv`/`.json` data files must sit next to `bb_grade.py`).

## What's inside (for reference)
`bb_grade.py` (the runner) → `draft.py` → `engine\` (survival-chain grader) + `pipeline\` (the 2025/2026 data). Raw build data and the big rendered HTMLs were left out to keep this small; the grader rebuilds `decision_dashboard.html` each run. Signals are 2025 season + 2026 projections/ADP; the 2026 team/ADP data (`dk_adp.csv`) reflects real offseason moves.

## Keeping it current
This is a snapshot. If you want refreshed ADP/projections or in-season live stats later, that's a data update on top of this same code — ask and I'll regenerate the `pipeline\` files for you to drop in.
