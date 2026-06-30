# HANDOFF — 2026 NFL Best-Ball / DFS model (continuation)
**As of 2026-06-28.** Prepping for the **2026 NFL season**. This doc lets a fresh Cowork session on
another machine (Tampa) pick up flawlessly. Read this first, then `CONTEXT_FOR_NEXT_SESSION.md`.

## 0. The golden rule (do not break this)
**NEVER assume anything about the 2026 world. Verify with real data / cited web research, then flag — don't assume.**
This rule exists because of a real error (SEA was mislabeled "continuity" when its play-caller had actually
left). Every roster, coordinator, scheme, OL tier, injury and schedule fact in this model is either
web-verified (cited) or an explicitly labeled modeling parameter. When in doubt, run a research agent and cite.

Security boundary (carried the whole project): FantasyPoints/SIS data is pulled through the user's *own*
authenticated session by **reusing the page's bearer header without ever seeing/printing the token**. Never
enter credentials, never authenticate on the user's behalf, never expose secrets.

## 1. What you get / how to look at it
Open these in a browser (they are self-contained):
- **dossier.html** — team-by-team scouting dossier; every player card now shows **⚑ total / ◆ playoff risk flags**, a Risk-flags detail block, and an availability-adjusted projection. Team headers show a flag rollup.
- **rankings.html** / **rankings_2026.csv** — the draft board with **⚑ / ◆PO** columns and a `→` availability-adjusted proj/g.
- **lever_board.html** — matchup-lever favorability board (sortable).
- **command_center.html**, **intel.html**, **upside_cases.html**, **player_explorer.html** — the broader engine boards.

## 2. How to rebuild everything
```
python3 run_all.py            # rebuilds dossier + flags + rankings chain (~5s, no external data needed)
python3 run_all.py --full     # ALSO runs the upstream engine + boom subsystem first (needs raw inputs)
python3 run_all.py --check    # list which outputs exist, no run
```
Full pipeline order:
```
refactor/pipeline.py   (rebuild.sh)  -> features.csv, defense.json, fusion.json ...   [core engine]
boom_pipeline.py                     -> boom/*.json, command_center.html             [ceiling subsystem]
build_dossier.py                     -> dossier_data.json     (VERIFIED 2026 OL wired in)
build_lever_count.py                 -> lever_count.json      (+ per-week lever_cal/sum)
build_flags_layer.py                 -> flags_2026.json, flag_rank_delta.csv  (+ flags into dossier)   [NEW]
build_lever_board.py                 -> lever_board.html
build_rankings.py                    -> rankings.html, rankings_2026.csv
render_dossier.py                    -> dossier.html
```
Env: Python 3.10+, `pandas` (only hard third-party dep; `pip install pandas`). Everything else is stdlib.
Run from the repo root so `import core` resolves (core.P() builds paths off the repo dir).

## 3. What changed THIS session (the flags work)
1. **Unified, data-backed flags layer** (`build_flags_layer.py` -> `flags_2026.json`): every player gets
   risk flags split into **TOTAL** (all risks) vs **PLAYOFF** (only risks specific to NFL W15-17). See `FLAGS_LAYER.md`.
2. **Injury availability overlay APPLIED** (was recorded-but-unused): 6 players haircut by a cited
   games-missed multiplier (`boom/roster_flags_2026.json` -> `availability`). All 6 project healthy by
   the playoffs, so they are TOTAL flags but NOT playoff flags.
3. **Verified 2026 OL tiers** (`boom/oline_2026.json`) replace the broken fusion `oline_pctl` (it had
   Detroit at the 6.6 percentile — clearly wrong). Wired into `build_dossier.py` (gates the deep lever).
4. **Schedule spot-check**: KC/PHI/DET/BUF W1/bye/W15/W16/W17 verified vs Pro-Football-Reference — all exact.
5. **Surfaced** in both the dossier and the rankings board; **rank movement** quantified in `flag_rank_delta.csv`.
6. `ASSUMPTIONS_AUDIT.md` updated: OL + injuries + schedule moved FLAGGED -> VERIFIED/APPLIED.

Rank impact (availability overlay, projection position-rank): Charbonnet RB 24→41 (−17), Tank Dell WR
69→77, Nabers WR 12→20, Kittle TE 3→5, Kraft TE 13→15. The headline board stays ADP-anchored; the overlay
is a model lens to read next to ADP.

## 4. Open items (from ASSUMPTIONS_AUDIT.md §C — verified-or-flagged, none silently trusted)
- **Re-verify rosters/FAs/injuries close to your draft** — unsigned FAs (Hill, Diggs, Deebo, Chubb, Waller)
  and Aiyuk's situation can change in July/Aug camps. `boom/roster_flags_2026.json` is the single edit point.
- Tackling-allowed is 2025-only (low stakes, tendency-tier elusive-RB lever only).
- Returning-DC coverage shells = 2025 actuals carried forward (same coordinator).
- Rookie defensive contribution = draft-round prior curves (modeled; inherent for rookies).
- Schedule: 4-team spot-check passed; not all 272 games individually re-checked.

## 5. Portability
- **bestball_full_2026-06-28.bundle** — complete clone-able git snapshot (440 files). On Tampa:
  `git clone bestball_full_2026-06-28.bundle bestball`
- **../bestball_handoff_2026-06-28.zip** (in Downloads) — zip of the whole repo; unzip and go.
- The folder also lives in Downloads, so a synced Downloads already carries it.

## 6. Gotcha (important)
Editing **large files through the editor tool truncated their tails twice** this session (build_dossier.py
and roster_flags_2026.json lost their endings on write). Prefer editing big files by running a small
Python script (string-replace) and **always validate after** (`python3 -m py_compile x.py`, or `json.load`).
A backup of the pre-edit dossier logic is preserved in the git bundle and `_bak_build_dossier_*.py`.
