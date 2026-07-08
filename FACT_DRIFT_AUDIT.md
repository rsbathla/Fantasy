# FACT DRIFT AUDIT — every fact asserted in 2+ layers, ranked by drift risk (2026-07-04)

**The class this register covers:** *fact corrected in canon, stale replica lingers in a sibling
layer.* Discovered via the Minter incident (registry + web_teams said BAL **HC**; scheme_2026 +
coordinator_changes still said DC; no check compared them). The audit's other checks interrogate
wiring, consumption, and freshness — value agreement between layers needed its own machinery.

**Standing policy (adopt at layer-creation time):** any fact asserted in more than one layer must
have exactly one of: (1) a **single source of truth consumed at runtime** (how the brain resolver
reads coaches), (2) an **equality check** in the audit (replicas — Check J/K), or (3) a **declared
transform chain** guarded by F2 freshness (derived values). A new layer that copies a fact without
picking one is a future incident.

Risk = assertion sites × real-world volatility × blast radius. Live findings from the 2026-07-04
sweep are noted per domain.

---

## 1. Coaching roles (hc / oc / dc / play-callers) — COVERED (Check J)
**Sites (7+):** web_teams.json (canon) · ground_truth_registry asserts · scheme_2026 (playcaller,
dc) · coordinator_changes (oc_name, dc_name, def_caller, dc_title) · coordinator_scheme (dc_name)
· boom/defensive_profile (dc.name) · boom/scheme_fit (player-level dc). **Volatility:** extreme in
the offseason carousel; nonzero in-season (firings). **Blast radius:** scheme dials, man/zone
levers, PROE leans, dossier prose, brain coach entities.
**Guard:** Check J — ~93 claim sites verified per run; registry↔canon reconciled; "HC calls the
defense" declared via `def_caller`/`dc_title`, never implied; the brain resolver must load from the
canon or J fires. **Live state:** 0 violations. Residual: scheme_fit's per-player `dc` currently
populates 0 records — the check is armed and its coverage count printed, not hidden.

## 2. Player → team — COVERED (audit_roster_moves.py)
**Sites:** boom/statmenu · boom/roster_flags_2026 · dk_adp.csv Team column · personnel_changes ·
profiles/player_profiles · rankings CSVs. **Volatility:** high (trades, signings, late-August
cuts). **Blast radius:** total — every player fact keys on it.
**Guard:** `audit_roster_moves.py` cross-checks every player's team across independent sources
against the canonical 2025-PBP join and reconciles curated 2026 moves → ROSTER_MOVES_2026.md.
**Action item:** confirm it runs on the same cadence as integration_audit (it is a separate
entry point — if it isn't in the standard run sequence, add it).

## 3. ADP / market prices — COVERED for the replica (Check K3); provenance note for the rest
**Sites:** dk_adp.csv (source) · boom/statmenu `adp` (**byte-identical replica** — 379/379 players
matched exactly in the sweep) · pipeline/clay_2026_ud.csv and merged_rankings (different
platforms/projections — legitimately different numbers, NOT replicas). **Volatility:** daily in
draft season — the fastest-moving fact in the repo. **Blast radius:** value calcs, boards,
strategy surfaces.
**Guard:** K3 — statmenu.adp must equal dk_adp.csv ADP exactly, and statmenu must not be older
than the CSV. **Do NOT** equality-check across platforms; that would manufacture false drift.
**Live state:** 0 drift.

## 4. Schedule / byes — COVERED (Check K1)
**Sites (4 copies):** pipeline/schedule_2026.csv (team×week matrix) · pipeline/games_by_week.json
· pipeline/byes_2026.json · boom/schedule2026.json (per-team, carries explicit BYE rows).
**Volatility:** near-zero post-release (rare flexes/corrections) — but restart-class blast if one
copy is corrected and three aren't: playoff overlay, lever calendar, matchup notes, bye handling
in the engine all read different copies.
**Guard:** K1 four-way — opponent sequences, home/away, byes, and weekly matchup sets must all
agree (csv rows are matched to team codes BY their opponent sequence, so no name-mapping table to
drift). **Live state:** 32/32 teams consistent.

## 5. Win totals / Vegas — COVERED (Check K2 + F2)
**Sites:** web_teams.json `win_total_2026` · boom/statmenu `team_env.win_total` (replica, embedded
per-player) · weekly-vegas-lines.csv (different fact: game lines; F2-guarded into game_sim).
**Volatility:** moves through the summer; weekly once lines post. **Blast radius:** env_idx,
team_ceiling, sim anchors.
**Guard:** K2 — the two replicas must match per team AND statmenu must be internally consistent
across its players. **Live state:** 32/32 consistent.

## 6. Scheme rates (man%, shells, sack%) — PARTIAL BY DESIGN (chain, not replicas)
**Sites:** coordinator_changes `dc_prior_man_rate` (incoming caller's prior-team rate) →
coordinator_scheme `man_rate_adj` (2026 projection) → boom/defensive_profile `man25/man26` →
levers. These are **transforms**, not copies — value-equality checks would be wrong.
**Guard:** names via Check J; propagation via F2 freshness — `coordinator_scheme_2026.json` and
`boom/defensive_profile.json` are now declared downstream of `coordinator_changes_2026.json` (+
web_teams). **Live state:** F2 is FIRING on both right now — correct behavior: today's canon label
edits made upstream newer; the next pipeline run clears it. That firing is the Tee-Higgins class
being prevented, not a bug.

## 7. QB rooms / depth charts — OPEN, UNSTRUCTURED (no check possible yet)
**Sites:** web_teams `offense_outlook` prose (32/32) · cc_context levers · intel/vault narratives.
**Volatility:** high through camp (competitions resolve in August). **Blast radius:** medium —
narrative + some levers.
**Position:** there is no structured canon to check against, and prose can't be value-compared.
Treat outlook prose as color, not canon. **Create `qb_rooms_2026.json` only when a builder starts
consuming QB-room facts** — then register it here and give it a check the same day it's born.

## 8. Injuries / practice status — OUT OF SCOPE deliberately
Ephemeral, hourly-volatile, and belongs to the brain's Intel log (sourced, dated, append-only) —
not to model canon. No repo layer should assert injury status as fact; if one starts to, it enters
this register.

## 9. Team codes / names — COVERED (Check K4)
**Sites:** web_teams codes (canon) · statmenu team fields (`FA` allowed for free agents) · brain
`_TEAMS` display map. **Volatility:** ~zero (relocations/renames are rare but total when they
happen). **Guard:** K4 set-equality. **Live state:** consistent.

## 10. Player identity / spelling — NOTE (guarded indirectly)
Canonical spellings live in statmenu; charting/CSV variants join through
`audit_roster_moves.py`'s canonical join; the brain resolver adds curated aliases. Residual risk
is ad-hoc joins in new builders — **always join through statmenu names**, never raw CSV strings.

---

## Verified this run (2026-07-04)
Check J: 0 violations across ~93 coaching claim sites. Check K: 0 violations — schedule (32
teams, 4 copies), win totals (32), ADP replica (379 players), team codes (33). F2: firing on the
scheme chain pending one pipeline rebuild (expected). Full detail: `INTEGRATION_AUDIT.md`.
