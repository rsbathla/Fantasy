# File manifest — key files (full set in the git bundle / zip)

## Deliverables (open in browser)
- `dossier.html` — team-by-team dossier with per-player ⚑total/◆playoff flags + availability-adjusted proj
- `rankings.html` + `rankings_2026.csv` — draft board with flag columns (⚑, ◆PO) and `→adj` proj/g
- `lever_board.html` — sortable matchup-lever favorability board
- `command_center.html`, `intel.html`, `upside_cases.html`, `player_explorer.html` — broader engine boards

## Orchestrators
- `run_all.py` — one-shot rebuild of the dossier+flags+rankings chain (`--full`, `--check`)
- `rebuild.sh` -> `refactor/pipeline.py` — core feature/defense/fusion engine (18 stages)
- `boom_pipeline.py` — boom/ceiling subsystem (foundation -> flags -> command_center)

## Flags layer (NEW this session)
- `build_flags_layer.py` — computes total+playoff risk flags, availability multiplier, rank movement
- `flags_2026.json` — per-player flags + meta counts (359 players, 117 flagged, 100 playoff)
- `flag_rank_delta.csv` — the availability-driven projection-rank movers
- `FLAGS_LAYER.md` — the flag taxonomy + definitions

## Verified 2026 inputs (real data / cited research — the "never assume" set)
- `boom/roster_flags_2026.json` — non-usable, unsigned FAs, injury watch + **availability multipliers** (cited)
- `boom/oline_2026.json` — **verified 2026 OL tiers** (Sharp/4for4/PFN), replaces broken oline_pctl
- `scheme_2026.json` — 2026 play-caller scheme dials (off) + new-DC shells (def), web-verified
- `coordinator_scheme_2026.json` — DC scheme / man-rate projection
- `defense.json` — 2026 unit strength (snap-weighted PAA, movers + rookie priors)
- `boom/schedule2026.json` — 2026 weekly schedule (structure verified + 4-team spot-check vs PFR)
- `web_teams.json` — 2026 HC/OC/DC + win totals + scheme outlook prose

## Core builders
- `build_dossier.py` -> dossier_data.json (player + team profiles; verified OL wired in)
- `build_lever_count.py` -> lever_count.json (tier-weighted per-week ceiling-lever count)
- `build_rankings.py` -> rankings board; `render_dossier.py` -> dossier.html
- `core.py` — shared identity/path/glob helpers (`core.P`, `core.fn`)

## Docs to read (in order)
1. `HANDOFF_2026_CONTINUATION.md` — how to continue
2. `CONTEXT_FOR_NEXT_SESSION.md` — the why + decisions + user style
3. `ASSUMPTIONS_AUDIT.md` — every input: VERIFIED / MODELING / FLAGGED
4. `FLAGS_LAYER.md` — flag definitions
5. `DOSSIER_PROGRESS.md`, `GAMEPLAN.md`, `PERSONNEL.md` — deeper history

## Portable snapshots
- `bestball_full_2026-06-28.bundle` — `git clone` it for the full repo with history
- `../bestball_handoff_2026-06-28.zip` (in Downloads) — unzip for the whole repo
