# Best-Ball Pipeline — Project-Safe Audit Instruction Set
*(sanitized from the "NextToken AI Auditor Rubric" for autonomous execution by Claude Code)*

---

## 0. READ THIS FIRST — what you are auditing (vetting notes)

The source rubric was written for **"NextToken," an AI-generated web application** (Node/React/Express, SQL, JWT auth, CORS, HTTP endpoints). **This repository is not that.** It is a **Python batch data-analysis pipeline** for NFL best-ball / DFS: it ingests stats (CSV/JSON/parquet), computes projections, flags, matchup levers, and defense ratings, and renders **static self-contained HTML** (dossier, rankings, big board). There is one small **local-only FastAPI read layer** under `api/` (uvicorn bound to `127.0.0.1:8000`, `--reload`, **no authentication**), which serves the already-computed JSON.

Consequences you must internalize before starting:

- There is **no SQL database, no user authentication, no JWT, no multi-tenant resources, no public HTTP surface.** The rubric's SQL-injection / IDOR / JWT / auth-at-resource-level checks are **N/A or narrowly scoped** here. Do not spend the usage window hunting for them.
- The single highest-value target in this repo is **data-integrity and analytical correctness** — name joins, 2026 roster currency (trades/rookies/coaching), weighting sanity, NaN/empty handling, and deterministic outputs. Passes below are **re-scoped to that reality.**
- The report's headline statistics (e.g. "55% secure," "37.6% degradation over 5 iterations," "2.74× vulnerabilities," "53% IDOR") are **unverified third-party claims.** Treat them as motivation only. **Do not cite them as findings** or assert them as fact.

---

## 1. HARD CONSTRAINTS — these override any conflicting rubric step

**You are operating autonomously with no human watching. Default to READ-ONLY.**

1. **Read-only by default.** Produce findings as **one new markdown report** (`AUDIT_FINDINGS.md`). Do **not** modify, move, rename, or delete any existing source or data file during the audit pass.
2. **Non-breaking fixes only, and only if explicitly enabled** (see §3). When in doubt, **propose a diff in the report; do not apply it.**
3. **No side effects:** no `git commit`/`push`, no dependency installs or upgrades, no `rm`/`mv`/hard-delete, no history rewrite, no network writes, no changes to CI or config. Running the code to *observe* is fine; mutating state is not.
4. **Secrets are untouchable** (§2). Never read, print, echo, embed, or transmit the contents of any credential file.
5. **Efficiency:** one structural pass, then targeted reads. **Do not re-run the full pipeline or re-render the 2.6 MB dossier "to verify."** Read the code and the existing outputs. Batch independent reads. Obey the stop rule in §6.

---

## 2. DO-NOT LIST — repo-specific landmines (non-negotiable)

These are real hazards verified in this codebase. Violating them corrupts data silently or breaks the pipeline.

- **NEVER run `build_features.py` standalone.** It is pipeline **stage 1** and rebuilds `features.json`/`.csv` from scratch. The advanced-ingest and defense columns are **accumulated by later stages**, so a lone run silently **drops them**. (This has already happened once and required restoring from a backup.) The only sanctioned run entrypoints are `refactor/pipeline.py`, `run_all.py`, and `boom_pipeline.py`, **in order**. Never run individual `ingest_*` / `build_*` scripts out of sequence.
- **`build_*.py`, `ingest_*.py`, `render_*.py` are CLI ENTRY POINTS, not dead code.** They have "zero importers" by design — they are invoked by the orchestrators or by hand. **Do not flag them as orphan/dead modules, and never delete them.** (The source rubric's Step 1.1/1.5 would false-positive on almost the entire repo; this instruction overrides it.)
- **Do not modify name resolution** in `core.py` (`fn`, `resolve`, `first_compatible`, `build_name_index`, `build_usage_index`, `match_usage`). Silent join drops are invisible and corrupt every downstream metric. Report issues; do not "fix" them.
- **Do not refactor "duplicated" logic.** Some duplication is intentional and some sits on the fragile name-join path. Flag only.
- **Respect output paths.** e.g. `draft_board_signals.csv` writes to the **repo root**; `boom/*.json` to `boom/`. Do not relocate outputs.
- **Secret files — report existence/location only, never contents:** `.env` (repo root), `crypto_arb_bot/.env`, `kalshi-key.pem.txt`, `pokemon_bot/.env`, and any `*.pem` / `*key*` / `.env*`. If a check would surface a value, **skip and record "secret withheld."**
- **`_archive/` is dead-by-design.** Note it exists; do not audit it deeply or "clean" it.

---

## 3. FIX POLICY

**Mode A (default): READ-ONLY.** Emit findings only. Every proposed change is a diff inside `AUDIT_FINDINGS.md`, not an edit on disk.

**Mode B (only if the operator explicitly enabled "non-breaking fixes"):** you may apply a change **only if ALL of these hold**:
- it touches **one file**;
- it is **additive/reversible** (new file, a guard, a comment) OR a one-line obvious-bug fix;
- it changes **no** function signature, output schema, CSV/JSON column set, or name-normalization behavior;
- it is verified by re-running **only the relevant stage** plus its test, confirming **no drop in row/column/player counts** and no new pipeline assert failure;
- the diff is still recorded in the report.

**NEVER auto-fix (propose only, always):** name resolution; pipeline stage ordering; defense-reweight / projection **weighting** (this is active human-judgment work — see Pass 4); dependency versions; anything deleting code; anything under `_archive/`.

---

## 4. AUDIT PASSES (re-scoped for this repo)

Each step says **[APPLIES] / [ADAPTED] / [N-A]** so you don't waste budget. Execute in the **priority order** given in §6, not necessarily 0→6.

### PASS 0 — Inventory & orientation
- **0.1 Structural map [APPLIES].** Enumerate modules; for the *orchestrators* (`refactor/pipeline.py`, `run_all.py`, `boom_pipeline.py`) and `core.py`, list what they import and what reads their outputs. Identify the true DAG (stage → produced columns/files → consumers). `core.py` is the critical shared dependency (imported everywhere) — highest-priority correctness target.
- **0.2 AI-authorship markers [ADAPTED].** Note inconsistent naming or near-duplicate helpers **only as leads for Pass 4 join/consistency risk** — not as defects in themselves. Do not moralize about comment density.
- **0.3 Iteration depth [ADAPTED].** `git log`/`git blame` **read-only** to spot files churned many times (higher regression risk) — feeds Pass 6. Do not act on it.

### PASS 1 — Architecture integrity (FLAG-ONLY)
- **1.1 Orphan modules [ADAPTED, CAUTION].** Reachability is via **CLI invocation**, not imports. Before calling anything "dead," confirm it is not referenced by any orchestrator, `.sh`, README, or `.bat`. Report only high-confidence dead code; **never delete.**
- **1.2 Orphan state [ADAPTED].** No React. Reinterpret as: module-level globals / cached dicts written on one path and read unconditionally elsewhere (esp. the name-index dicts). Flag missing-key/None reads.
- **1.3 Pattern consistency [APPLIES].** Verify all modules join names through `core.resolve`/`core.fn` (not private re-implementations). A private re-implementation of name normalization is a real defect here — flag it.
- **1.4 Abstraction audit [ADAPTED, low priority].** Light touch. Don't propose collapsing abstractions.
- **1.5 Dead code paths [ADAPTED].** Flag genuinely unreachable branches, but remember guard clauses that "look phantom" (e.g. `if file absent: no-op`) are the repo's **deliberate fail-soft** design (`_apply_flag_nudge`, optional inputs). Do not flag those.

### PASS 2 — Concurrency / IO integrity (RE-SCOPED — this is a batch pipeline, not async)
- **2.1 Async inventory [MOSTLY N-A].** The code is synchronous batch Python. Skip promise/await hunting.
- **2.2 Swallowed errors [APPLIES].** Hunt Python equivalents: `except: pass`, `except Exception: continue`, bare `except` that hides a failed join or a missing file and lets a downstream stage run on partial data. These are the real analog of the report's "catch-and-discard." Flag each with its blast radius.
- **2.3 / 2.5 Atomicity & boundary conditions [APPLIES — HIGH VALUE].** Confirm JSON writes use `core.safe_json_dump` (atomic tmp+rename, NaN→null). Trace every join/aggregation for **empty / single-row / all-NaN / missing-team** inputs (pandas `groupby`, `.iloc[0]`, division by count). Empty-collection and divide-by-zero are the realistic failure modes here.
- **2.4 Lifecycle teardown [N-A].** No subscriptions/listeners.

### PASS 3 — Security (SCOPED DOWN to what exists)
- **3.1 Secret scan [APPLIES — but read-only, see §2].** Confirm `.env` and the other credential files are gitignored and **untracked** (`git ls-files`), and that no secret value is hardcoded in `.py`/`.json`. **Report locations and the boolean "tracked?" only — never the value.**
- **3.2 Injection [ADAPTED].** No SQL. Check the ~two dozen `subprocess`/`eval`/`exec`/`pickle.load`/`shell=True` sites — specifically whether **any request-derived or file-derived string** reaches them. The orchestrators run **fixed script paths** (safe); the concern is the `api/` **rebuild/admin** path (`api/app/services/rebuild_service.py`, `schemas/admin.py`) — verify it cannot pass caller input into a shell.
- **3.3 Auth [ADAPTED, localhost].** The FastAPI has **no auth** and binds `127.0.0.1`. That's acceptable for a local dev read API over public NFL stats. **One real note:** if a rebuild/admin endpoint can trigger pipeline runs, flag "must not be exposed off-localhost without auth." No IDOR/JWT work.
- **3.4 CORS/headers [APPLIES, low sev].** `CORS_ORIGINS` defaults to `["*"]` — already documented "lock down in prod." Flag as **informational** (real only if deployed).
- **3.5 Crypto [N-A].** No password hashing / token issuance. (Note: `Date.now()`/`Math.random()` bans are JS; the Python analog `random`-for-security does not apply — this pipeline uses no security randomness.)
- **3.6 Dependency existence [ADAPTED].** Deps are **pip**, not npm: `pandas, numpy, pyarrow, pyperclip, striprtf` (+ `fastapi, uvicorn`). Confirm each exists on PyPI and is mainstream (all are). No `package.json`. Low risk; 5-minute confirm.

### PASS 4 — Logic & DATA-INTEGRITY (⭐ HIGHEST VALUE — spend most of the budget here)
This is where real defects live in this repo. Reframe "business rule integrity" as **analytical correctness**.
- **4.1 Name-join integrity [CRITICAL].** For each major join (draft board ↔ projections ↔ sim ↔ boom flags ↔ usage), quantify **match rate and who's dropped**. A silently unmatched star is the signature bug class here. Cross-check `core.resolve` vs any ad-hoc matching.
- **4.2 2026 roster currency [CRITICAL — aligns with active work].** Verify **trades, free-agent moves, rookies, and coaching changes** are actually applied AND **weighted**, not just listed. Known lead to verify and generalize: in `defense.json`, the Myles Garrett→LAR move is in `moves_2026` but carried at **Points Saved ≈ 0.1** (near-replacement) — trace why an elite mover lands near zero (SIS name-join miss? snap-weighted-mean diluting a single dominant player?). Apply the same trace to every unit (offense, OL, coverage, pass-rush, run-def) and to rookies (imputation path).
- **4.3 Weighting sanity [APPLIES].** Check that per-metric weights reflect **importance to that position/team**, not arbitrary constants. Flag magic numbers with no derivation/comment. (Report; do not re-tune — that's human work.)
- **4.4 Atomicity / partial-write [APPLIES].** Multi-file stage outputs: confirm a mid-stage crash can't leave `features.json` and `features.csv` **desynced** (the pipeline's integrity check exists — verify it actually guards every stage).
- **4.5 Determinism [APPLIES].** Flag any nondeterminism that would make outputs unstable run-to-run (unseeded sampling, dict-ordering reliance, `set` iteration into ranked output).

### PASS 5 — Quality & maintainability (FLAG-ONLY)
- **5.1 Duplication [FLAG-ONLY].** Note ≥10-line clones (esp. re-implemented name normalization). **Do not refactor.**
- **5.2 Complexity [ADAPTED].** Note the few very dense functions; don't enforce a hard threshold or rewrite.
- **5.3 Test quality [APPLIES].** Real tests exist (`engine/test_bbengine.py`, `tests/test_names.py`, `refactor/tests/test_refactor.py`, `api/tests/test_api.py`). Judge whether they assert **behavior** (esp. name-resolution correctness) vs mere "runs without error." Recommend gaps; don't generate circular tests.
- **5.4 Logging [ADAPTED].** `print()` here is **dev telemetry over public stats**, not PII leakage — do **not** flag routine prints. Only flag a log line that would emit a **secret** value.
- **5.5 Env validation [APPLIES].** The `api/` reads env config; confirm required vars are validated at startup (there is a `config.py` validator — verify coverage).

### PASS 6 — Regression / data-contract integrity (read-only)
- **6.1 Security regression [LOW — few security controls].** Light.
- **6.2 Completeness of critical logic [ADAPTED].** Reframe: does a stage claim to apply a 2026 adjustment (moves/rookies) but land it at ~zero effect (see 4.2)? That is this repo's real "surface-level approximation."
- **6.3 Context-boundary integrity [APPLIES — HIGH VALUE].** The highest-probability defect site: two modules built in different sessions that exchange data by **name key or column** with mismatched normalization/units. Enumerate these hand-off points and verify the contract (key format, units, NaN convention) matches on both sides.

---

## 5. OUTPUT FORMAT

Write **one file, `AUDIT_FINDINGS.md`**, with:
- a 10-line executive summary (top 5 findings by impact, all data-integrity-weighted);
- a table: *Finding · Pass · File:line · Severity · Evidence (traced path, not "looks wrong") · Proposed action (diff if Mode B)*;
- an explicit **"checked and clean"** list (so the operator knows coverage);
- an **"N/A here and why"** list (the web-app checks that don't apply), so nobody re-runs them.

**Severity (re-scoped):** Critical = silent data corruption (dropped players, desynced features, mis-weighted 2026 unit that flips rankings) or a hardcoded secret. High = swallowed exception on a production data path; empty/NaN unguarded aggregation feeding rankings. Medium = determinism gap; missing boundary guard off the hot path. Low = duplication, dense function. Informational = wildcard CORS (local), naming drift.

---

## 6. EXECUTION ORDER & STOP RULE (tight usage window)

Do them in this value order and **stop when budget is ~80% spent or findings plateau**:
1. **Pass 0.1** (map the DAG) — cheap, orients everything.
2. **Pass 4** (data integrity — joins, 2026 weighting, determinism) — the reason this repo gets audited.
3. **Pass 6.3** (cross-module data contracts) — where 4's defects originate.
4. **Pass 3.1** (secret hygiene, read-only) — fast, high-consequence.
5. **Pass 2.2/2.3/2.5** (swallowed errors, atomic writes, empty/NaN boundaries).
6. **Pass 1** (architecture, flag-only) and **Pass 5** (quality) — only if budget remains.
7. Skip N/A items (SQL/JWT/IDOR/crypto/async-teardown) entirely.

If you hit ambiguity that would require a breaking change to resolve, **write it up as a finding and move on** — do not attempt the change. Report, don't remediate.
