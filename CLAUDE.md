# CLAUDE.md — Standing Orders for this repo

2026 NFL best-ball + DFS analytics. Owner: Ramneik. You are not the first model to work here and
you will not be the last. The rules below were each paid for with a real failure — the case law
lives in `PLAYBOOK.md` (read it once per session, before substantive work). Current wiring state:
`INTEGRATION_AUDIT.md`. Verified 2026 facts: `ground_truth_registry.json`.

Build chain: `python3 run_all.py` (builders → deliverables → `integration_audit.py` FINAL GATE →
`audit_roster_moves.py` DATA GATE). `--check` lists expected outputs. Ship nothing unless
`python3 integration_audit.py --strict` exits 0.

## 1 · The Prime Rule — the 2026 world postdates your training

Whatever your knowledge cutoff, the 2026 league year happened after it. The coaching carousel,
rosters, and posted look-ahead Vegas lines in this repo describe a world you have never seen.
Authority order, strictly:

1. **Verified repo layers** (`ground_truth_registry.json` and anything carrying `verified: true`
   with a source) — ground truth.
2. **Fresh web search** — to confirm or extend, never to overrule a verified layer.
3. **Your priors** — never authoritative for 2026 facts.

If a verified layer contradicts what you "know": assume you are stale, search to confirm, and if a
genuine conflict survives, FLAG it to the user with both sides. Never silently withhold, "correct,"
or re-derive a registered fact. (PLAYBOOK C6: a session once suppressed the real 2026 coaching
carousel because it trusted its own outdated memory. C7: the same session mislabeled real posted
Vegas lines as a projection.)

## 2 · Use the layers — no single-signal anchoring

The edge of this repo IS its layers. A deliverable that anchors on one legible signal while a
built layer for the same dimension sits unused is a defect, even if it looks reasonable.

- **Environment** = `env_blend.py` (posted Vegas O/U anchor × team-ceiling adjustment). The ONLY
  sanctioned environment formula. Never rank environments on O/U alone (C5); never invent totals.
- **Matchup edge** = player strength × defense softness × **coverage frequency**
  (`defense_splits.json` `shell.man_rate`). A rate without exposure is a mirage (C8).
- Before computing any ranking, check the **Utilization map** in `INTEGRATION_AUDIT.md` — Check H
  enforces required layers per builder; Check H2 requires hand-authored deliverables to declare
  layer usage in `deliverable_manifest.json`, with written justification for every core layer unused.
- When you author or regenerate a deliverable, update its manifest entry in the same change.

## 3 · Evidence discipline

- New composite weights require an out-of-sample backtest vs ADP (`backtest_composite_2025.py`).
  ADP is efficient; most signals fail it. Every added weight ships with a documented revert flag.
- ADP is a best-ball draft price. It is NEVER a DFS cost proxy (C9).
- No salary-value or ownership-leverage claims until real 2026 slates exist.
- Distinguish backtest-earned weights from stated priors, in the code comment, every time.
- Change-flags (new OC, scheme shift) must be corroborated before they feed kickers — title-only
  churn is not a scheme change (C3).

## 4 · Deliverable contract

- "Analysis" and "breakdown" mean WRITTEN PROSE reports. Dashboards only when explicitly requested
  (C4 — this was corrected twice; do not make it a third).
- Order of presentation: neutral per-game/per-item notes FIRST, conclusions and picks AFTER —
  never anchor the reader before they can form their own read (C10).
- House style: `ui/COMPONENTS.md` tokens for reports; every factual clause traces to a data field;
  assumptions stated inline, not implied.
- Every safety indicator you add needs a known-bad test proving it fires (C2: a mis-signed
  indicator once reassured the user about the exact thing it was built to expose).

## 5 · Workflow

- **Extend, don't restart.** Before building anything, inventory what exists: PLAYBOOK §Layers,
  `run_all.py --check`, grep. Re-deriving existing verified work is the failure mode the user
  finds most corrosive (C11).
- Large semantic changes (weights, gates, scoring semantics): state what/why and confirm with the
  user BEFORE wiring. Mechanical wiring needs no ceremony.
- Commit only when the user asks. Bundle workflow: user pulls the work branch ref
  (`integration-audit-and-wiring`), NOT `main` — a bundle's `main` may be stale.
- NEVER open, print, or commit credential material: `.env`, `crypto_arb_bot/.env`,
  `pokemon_bot/.env`, `kalshi-key.pem.txt`, `X_BEARER_TOKEN.txt`, `*BEARER*`, `*.pem*`.
- No model identifiers in committed artifacts (commits, code, PRs, docs).
- After any incident: post-mortem → new audit check the same day → removal test proving it fires →
  PLAYBOOK case entry. The auditor is a ratchet; teach it every new failure class immediately (§5
  of PLAYBOOK).

## 6 · Orchestration

Split work by cost of judgment: the orchestrator holds context and decisions; **deep-reasoner**
(Opus-class) does analytical subtasks; **fast-worker** (Sonnet-class) does mechanical sweeps.
Definitions in `.claude/agents/`. EVERY subagent prompt begins with the verbatim contents of
`agents/SUBAGENT_PREAMBLE.md` — a subagent that hasn't read the rules will re-commit C5/C6 by
default, because those mistakes are what an unbriefed model does naturally. Subagents return
findings and decision points; they do not make user-owned decisions.

The domain-GENERAL theory behind all of this — the ten failure modes of "the naturally easy
thing," applicable to any task on any repo — is `agents/UNIVERSAL_DISCIPLINE.md`. It is written
to be portable: copy it to `~/.claude/CLAUDE.md` on any machine to make it global.
