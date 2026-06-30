# Context for the next Cowork session (bring yourself up to speed)
Pair this with `HANDOFF_2026_CONTINUATION.md`. This is the "why", the decisions, and the user's working style.

## Who / what
- User: Ramneik. Building a two-model **NFL best-ball + DFS** analytics codebase for the **2026 season**.
- Repo: `C:\Users\...\Downloads\bestball\`. ~440 files: a core feature/defense/fusion engine
  (`refactor/pipeline.py`), a boom/ceiling subsystem (`boom_pipeline.py`), and a presentation layer
  (dossier / rankings / lever board / command center / intel).

## User's working style (honor this)
- Wants **deep, thorough reasoning** and to treat tasks as complex; do NOT over-optimize for brevity in the work.
- Wants concise, direct **prose** in chat (minimal fluff), but rigorous underneath.
- Hard rule he stated repeatedly: **"NEVER assume, we're running with real data here."** When you make a 2026
  claim, verify it (web research agents, cited) or label it a modeling parameter. He caught a real SEA error
  and (rightly) wanted everything re-verified. Run flags on real data; flag, don't assume.

## The arc that got us here (most recent first)
1. **This session**: he asked to (a) adjust every assumption to what's true/data-backed, (b) mark flags into
   the dossier AND best-ball model with clear **total vs playoff** flag counts and see if ranks change, and
   (c) build this Tampa handoff (he's away ~1 week). All done. See HANDOFF §3.
2. Before that: an "affirm every assumption" audit (`ASSUMPTIONS_AUDIT.md`), roster accuracy verification
   (Aiyuk removed; A.J. Brown→NE confirmed a REAL trade), SEA/BAL scheme corrections.
3. Before that: directional 2026 scheme registry (`scheme_2026.json`) replacing a blanket regression;
   FantasyPoints lever audit (YoY-stability-tiered) and a tier-weighted per-week "ceiling-levers" count.

## Key design decisions (so you don't relitigate them)
- **Levers** = opponent-controllable splits where a player has a *stable* edge (usage/role persists YoY;
  efficiency *differentials* are mostly noise). Tiered solid (1.0) / tendency (0.5).
- **Flags**: TOTAL = all risks; PLAYOFF = only risks specific to NFL W15-17 (an early-season injury that
  resolves by December is TOTAL but not PLAYOFF). Only **availability** flags haircut a projection
  (data-backed games-missed); scheme/OL/playoff-slate are surfaced as counts, not invented point penalties.
- **"Continuity"** means the actual **play-caller** stayed (not just same team). Only genuine play-caller
  changes get an `off` scheme dial in `scheme_2026.json`.
- Headline ranks stay **ADP-anchored** (market already prices much risk); flags are an overlay you read next to ADP.

## Single edit points (where to change inputs)
- Injuries / FAs / non-usable: `boom/roster_flags_2026.json` (re-verify before drafting).
- 2026 OL tiers: `boom/oline_2026.json`. 2026 scheme/play-callers: `scheme_2026.json`.
- Flag thresholds: top of `build_flags_layer.py` (PO_SLATE_TOUGH, OL_TIER_WEAK, ...).

## Likely next steps (his backlog, your call to confirm with him)
- Re-verify rosters/FAs/injuries closer to draft; fold any signings into `roster_flags_2026.json` and rerun `run_all.py`.
- If desired, pull 2024 tackling to YoY-validate the elusive-RB lever (currently 2025-only, low stakes).
- Optionally let scheme/OL/playoff-slate flags feed a (separate, clearly-labeled) risk-adjusted board if he wants ranks to move on more than availability.

## How to verify your work (the standard he holds)
Run `python3 run_all.py`, then the integrity check pattern: 32 teams / 359 players, every player has
flag fields, availability multipliers match `roster_flags_2026.json`, counts in `flags_2026.json` match the
dossier. Use parallel cited web-research agents for any 2026-world claim.
