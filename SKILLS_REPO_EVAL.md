# SKILLS_REPO_EVAL — github.com/davidondrej/skills vs. this repo

**Evaluated:** 2026-07-05 · repo cloned at commit `6261b61` (2026-07-05, MIT license, 31 stars).
**Retrieval note:** GitHub's API was blocked in this session (403), but a full `git clone` succeeded, so every file below was read in full from disk — nothing here is inferred from names. One skill (`browser-harness`) has a 3-byte stub SKILL.md (literally `...`); only its install reference has content.

**What the repo is:** David Ondrej's personal agent-skills library — 29 skills in 5 folders (`agent-orchestration`, `skill-authoring`, `research-and-web`, `thinking-and-docs`, `ops-and-setup`). Roughly half are hard-wired to his personal stack: macOS + cmux terminal, Pi/Codex/Hermes agents, Hostinger VPSes, and his own paid API product (DeepAPI). Those are useless to us as-is. The other half encode genuinely portable disciplines, and 5–6 of those map onto things this repo already does by hand.

---

## SHORTLIST — adopt these

| Skill | One-line use here |
|---|---|
| `handoff` | Replace our ad-hoc `HANDOFF_*.md` files with its state-not-instructions template + "verify, don't trust" closing prompt. |
| `research-prompt` | Standard briefing format for fable research subagents and deep-research runs (dossiers, coaching-change verification, FACT_DRIFT checks). |
| `youtube-transcript` (yt-dlp half) | Captions-first (json3) path + 429 stop-discipline for `brain/brain_video.py` / `brain_film.sh` — most film-room videos have captions; whisper becomes the fallback, not the default. |
| `effective-agent-skills` | The authoring/review rubric for every skill we write and for keeping `agents/SUBAGENT_PREAMBLE.md` lean. |
| `folder-specific-claude-and-agents-md` | Method for splitting our monolithic root CLAUDE.md into folder-scoped ones (`brain/`, `engine/`, `ingest/`). |

**Maybe (steal the pattern, not the skill):** `codex-goal-loop` (5-part contract for long autonomous runs), `fable-safe-prompt` (we run fable subagents over scraper code full of its listed trigger words), `grill-me` (3-line plan stress-test), `interview-style-doc-building`/`brain-to-docs` (strategy extraction from Ramneik), `agent-self-scheduling` ("verify it fires" checklist for the weekly brain job), `cyber-audit` (dependency-advisory check pattern).

**Everything else: no.** Detailed verdicts below.

---

## 1 · agent-orchestration (8 skills)

### handoff — **ADOPT**
**What it is:** "Compact the current conversation into a single, detailed handoff message — everything that happened, why it happened, and what's left" for a fresh agent session. Core principles: *state, not instructions* ("Auth endpoint is implemented; logout is not yet started" — never "Implement logout next"); *reference, don't duplicate*; *capture the why* (decisions + rejected approaches are "the most valuable and least recoverable information"); *trust nothing blindly*; redact secrets. Fixed 7-section template ending with a ready-to-paste fresh-agent prompt that forces the next agent to actually read the listed files.
**Why adopt:** We already do this manually — `HANDOFF_2026_CONTINUATION.md`, `HANDOFF_NFL_BestBall_2026_v2.md`, `HANDOFF_X_DOSSIER.md`, `CONTEXT_FOR_NEXT_SESSION.md` — with no shared structure. This template is strictly better than our ad-hoc versions, and its "Traps & Dead Ends" section is exactly the PLAYBOOK.md case-law instinct applied at session scope.
**How Opus uses it:**
- *Trigger:* end of any substantive session, context-limit pressure, or before partitioning work across fresh subagent contexts.
- *Workflow:* read CLAUDE.md first and omit anything it already covers (the skill mandates this — our CLAUDE.md is heavy, so this pruning rule matters); update the existing `HANDOFF_*.md` rather than writing a new one; fill Goal / Current State (DONE-PARTIAL-NOT STARTED) / Key Decisions / Traps & Dead Ends / Files with line ranges / Open Work; end with the verbatim "read every file listed… treat every claim as context to verify" prompt.
- *Plugs into:* `HANDOFF_2026_CONTINUATION.md` and `CONTEXT_FOR_NEXT_SESSION.md` (consolidate to one file in this format); pairs with the CLAUDE.md rule that `PLAYBOOK.md` is read once per session — dead-ends that are session-specific go in the handoff, ones that are permanent go to PLAYBOOK.
- *Install:* copy the template into a repo skill (e.g. `.claude/skills/handoff/SKILL.md`), stripped of its cmux/temp-dir specifics; default output path = repo-root `HANDOFF_2026_CONTINUATION.md`.

### codex-goal-loop — **NO as-is / MAYBE as a pattern**
**What it is:** How to write contracts for OpenAI Codex's `/goal` persistent loop ("plan → act → test → review → iterate"). Requires Codex v0.128+, ChatGPT auth — none of which we use.
**Worth stealing:** the 5-part contract for any long autonomous run: Objective (one sentence) / Constraints (what must NOT change) / **Validation command** (exact shell command proving progress) / verifiable Stop condition / explicit anti-reward-hacking clause ("Do not delete, skip, weaken, or narrow tests to make the goal pass"). Our equivalent of a validation command already exists: `python3 integration_audit.py --strict` exits 0.
**How Opus uses it (pattern only):** when briefing a fable subagent for a long refactor or builder change, structure the prompt as that 5-part contract, with `integration_audit.py --strict` + `audit_roster_moves.py` as the Validate line and the anti-gaming clause included verbatim. Fold one paragraph into `agents/SUBAGENT_PREAMBLE.md`; don't adopt the skill file.

### fable-safe-prompt — **MAYBE**
**What it is:** Surgical rewriting of prompts so Claude Fable 5's "server-side safety classifiers (cyber/bio guardrails that force-route to Opus 4.8 or return stop_reason 'refusal')" don't false-positive. Claims triggers are "keyword/surface-based, largely intent-independent", lists trigger keywords — *exploit, attack, bypass, stealth, fingerprinting, anti-bot, CAPTCHA* — and says "show your reasoning" instructions trip a `reasoning_extraction` classifier.
**Why it's relevant at all:** we run fable subagents for audits, and our puller/scraper code and docs legitimately contain that vocabulary (authenticated pullers, anti-bot handling, browser cookies in `brain_video.py`, session auth for FantasyPoints/NFL Pro/SIS). A fable audit prompt quoting that code could get flagged for reasons that have nothing to do with intent.
**Caveat:** the classifier behavior is the repo's own claim — we have not verified it. Adopt defensively, not as gospel.
**How Opus uses it:** two lines added to `agents/SUBAGENT_PREAMBLE.md`: (1) when briefing fable subagents about scraper/auth code, describe the task functionally ("review the session-refresh logic in ingest_*.py for missing checks") rather than with attack-framing or scraping-evasion vocabulary; (2) never instruct a fable subagent to "show your reasoning step-by-step" — ask for findings + evidence instead. If a fable subagent returns a refusal on puller code, re-brief per this pattern before escalating.

### agent-self-scheduling — **MAYBE (checklist only)**
**What it is:** Cron/heartbeat patterns for agents: external clocks vs built-in schedulers, "runs are amnesiac", permissions-hang as "the #1 silent failure", heartbeat pattern (one fast tick gates many per-task checks via `last_run` timestamps), and a "verify it fires before reporting success" checklist.
**Why only maybe:** half of it is Hermes/Pi/cmux-specific. But our brain ingest is literally a scheduled job (`brain/com.nflbrain.ingest.plist` launchd + `run_brain_weekly.sh`), and the transferable bits — verify a scheduled job actually fired (log grows after one interval), keep per-source `last_run` state, stay silent when nothing is due — are good hygiene for it.
**How Opus uses it:** when touching `run_brain_weekly.sh`/the launchd plist, apply the verify-it-fires checklist and confirm the idempotent skip path ("URLs already in the manifest skip", per `brain_film.sh`) stays silent on no-op runs. No skill file needed.

### delegating-to-agents — **NO.** Picking between Pi/Codex/Hermes and cmux `send` keystroke mechanics on David's Mac. We delegate via the Agent tool in-harness; none of these CLIs or the cmux terminal exist here.

### cmux — **NO.** 228-line control manual for the cmux macOS terminal app (panes, surfaces, WKWebView browser, socket API). "macOS only." We don't run cmux; zero overlap.

### markdown-rendering — **NO.** Workaround for one cmux markdown-pane rendering bug ("never `move-surface` a markdown viewer — it renders blank"). Meaningless outside cmux.

### run-deep-swe — **NO.** Running the DeepSWE coding-agent benchmark via OpenRouter/Pier to score models. We're not benchmarking models; irrelevant to NFL analytics.

---

## 2 · research-and-web (6 skills)

### research-prompt — **ADOPT**
**What it is:** Turn a research need into "ONE self-contained paragraph that a researcher with zero prior knowledge of the project can act on with zero back-and-forth." Rules: open with a plain-English explainer of the project; lead with the single question + the decision it informs; 3–6 numbered inline sub-questions; include/avoid constraints; "prefer primary sources… forums/X/Reddit are weak signal only, never factual proof"; "if sources conflict, separate confirmed facts / inference / unresolved uncertainty — don't force fake consensus"; a completion bar (corroborate each key claim with multiple independent primary sources); a mandatory "gap round" self-critique pass before finishing; per-finding format = source link + specific claim + one-line why-it-matters.
**Why adopt:** This is our CLAUDE.md evidence discipline (§3, Prime Rule fact-verification, C3 "title-only churn is not a scheme change") expressed as a reusable briefing format. Every research task we already run — coaching-change corroboration, X-dossier building (`HANDOFF_X_DOSSIER.md`), fact-drift audits (`FACT_DRIFT_AUDIT.md`), player-news verification against `ground_truth_registry.json` — currently gets a hand-rolled prompt each time.
**How Opus uses it:**
- *Trigger:* any fan-out research delegation — fable research subagents, the in-harness deep-research skill, or a WebSearch sweep — for 2026 facts, coaching/scheme changes, or brain-intel verification.
- *Workflow:* (1) pull context from the relevant repo files (`ground_truth_registry.json` entry, `COACHING_CHANGES_2026.md` row, the brain note in question); (2) write the one-paragraph brief per the template — sub-questions numbered, "avoid fantasy-site listicles; prefer team announcements, beat-reporter primary posts, league transaction logs" as the include/avoid line; (3) require the fact/inference/unresolved split in the output so results can be written back with `verified: true` only for the confirmed tier.
- *Plugs into:* subagent briefs launched from audits; the corroboration step CLAUDE.md §3 requires before change-flags feed kickers; brain ingest verification before claims land in `brain_intel.json`.
- *Install:* adapt as `.claude/skills/research-brief/SKILL.md` with our source-hierarchy line and the ground-truth-registry write-back rule appended.

### youtube-transcript — **ADOPT (the yt-dlp half; not the DeepAPI half)**
**What it is:** Fetch YouTube transcripts — primary path is David's paid DeepAPI; fallback is yt-dlp with hard-won specifics: `--write-subs --write-auto-subs --sub-format json3` because "**Always use `json3`, never VTT/SRT** — auto VTT repeats every line twice (rolling captions)"; a json3→clean-text flattener script; channel→uploader metadata fallback; "**429 / 'Sign in to confirm you're not a bot'** = IP flagged. STOP — do NOT retry in a loop (makes it worse)"; `yt-dlp -U` once on first failure then stop; note that newer yt-dlp may need `deno`.
**Why adopt:** `brain/brain_video.py` currently downloads full audio and runs faster-whisper for *every* video, with a generic exception-swallowing retry (clean → chrome cookies) and no 429-specific handling — on a Mac launchd job (`com.nflbrain.ingest.plist`) that hits YouTube on a schedule, which is exactly the loop-retry-on-bot-flag scenario this skill warns will get the IP burned. Captions-first would also cut whisper compute for the majority of film-room/podcast channels in `brain/film_sources.tsv` that have auto-captions. (Note the skill's own default is the opposite — "Never fall back to downloading audio for Whisper unless the user explicitly asks" — because David only wants text; for us whisper stays as the fallback for caption-less videos since timestamps feed the brain notes.)
**How Opus uses it:**
- *Trigger:* any maintenance or hardening pass on `brain/brain_video.py` / `brain/brain_film.sh`.
- *Workflow:* (1) add a captions-first branch to `download_audio()`'s caller: try `--skip-download --write-subs --write-auto-subs --sub-langs "en.*" --sub-format json3`, flatten json3 events (port the skill's flattener, keeping `startSecs` for our `fmt_ts` timestamps); (2) fall through to the existing audio+faster-whisper path only when `output` is empty (no captions); (3) add explicit 429/bot-flag detection that aborts the whole `brain_film.sh` channel sweep for the run instead of continuing to hammer, and log it to the manifest; (4) keep the existing `player_client` rotation and chrome-cookie fallback as-is.
- *Plugs into:* `brain_video.py` (`download_audio`, `transcribe`), `brain_film.sh` (channel loop), `setup_brain_mac.sh` (note the possible `deno` dependency for new yt-dlp).

### deep-research — **NO.** The workflow ("prompt + run + report file") is fine, but the execution is 100% DeepAPI (`POST /v1/research/deep`, key in David's `~/.zshrc`, his credits, his idempotency/cost-cap conventions). We already have an in-harness deep-research skill; adopt `research-prompt` (above) as the briefing layer and keep our own executor.

### deepapi — **NO.** 629-line API reference for David's own paid product (scraping, email, image-gen endpoints with his spend caps). It's vendor documentation, not a technique. Our pullers are authenticated first-party sessions to FantasyPoints/NFL Pro/SIS — a generic scrape API doesn't replace them, and we're not buying his credits.

### pi-web-search — **NO.** "ONLY for Pi Agents — all other agents have their own web tools" (its own description). One transferable garnish: hard minimum query counts by phrasing ("deep research" → ≥8 queries across 2–3 refined batches) — a decent anti-laziness floor to mention in research subagent briefs, not worth a skill.

### browser-harness — **NO (can't).** SKILL.md is a 3-byte stub (`...`); only `references/install.md` exists, describing installation of `browser-use/browser-harness` (a CDP daemon). There is no actual skill content to adopt, and we already have claude-in-chrome for browser work. Reported as-is per evidence discipline.

---

## 3 · skill-authoring (3 skills)

### effective-agent-skills — **ADOPT**
**What it is:** A 312-line consolidated guide to writing skills: progressive disclosure (discovery ~100 tokens / activation <5k / execution unbounded); "the description is the only thing the agent sees before deciding to load the skill. If your skill doesn't trigger, the description is wrong 95% of the time"; "never summarize the full workflow in the description" (the agent will follow the summary and skip the body); capability primitives (thin CLI wrappers) vs process primitives (methodologies); "push determinism into code"; validation loops as "the single biggest output quality improvement"; anti-patterns (don't re-teach the model, no human-facing docs in skill folders, no time-sensitive info, no mega-skills); a testing section ("routing fails → description problem; execution fails → body problem"); security checklist for third-party skills; ship checklist.
**Why adopt:** It's the best generic document in the repo and directly serves how this ecosystem defines a skill (folder + SKILL.md). We author and maintain our own skills and subagent discipline docs; this is the review rubric. It also complements (not duplicates) the in-harness skill-creator: skill-creator scaffolds, this one teaches judgment.
**How Opus uses it:**
- *Trigger:* creating or revising any repo skill (e.g. a future `bestball-report` house-style skill wrapping `ui/COMPONENTS.md`, a `funnel-audit` process skill, the `research-brief`/`handoff` skills proposed above), or pruning `agents/SUBAGENT_PREAMBLE.md` / `UNIVERSAL_DISCIPLINE.md`.
- *Workflow:* draft the description first as what+when+differentiator with trigger phrases; keep the body lean and push anything deterministic into a script under the skill's `scripts/`; end every skill with an explicit verify→fix→re-verify loop (for us, usually "run `integration_audit.py --strict`" or "check the deliverable manifest entry"); run its ship checklist before calling a skill done; apply its security checklist before installing anything third-party — including, recursively, anything from this very repo.
- *Plugs into:* `.claude/skills/` authoring; `agents/*.md` maintenance; `deliverable_manifest.json` discipline (its "persistent artifacts for cross-session memory" principle is exactly our manifest/registry pattern — validation that our architecture is right, and a rubric for extending it).

### folder-specific-claude-and-agents-md — **ADOPT (method, with edits)**
**What it is:** Generate a folder-scoped CLAUDE.md (+ AGENTS.md symlink): read every file in the folder first; propose a bullet list before writing; sections include Essential Files, "Constraints (MUST NOT) — explicit hard negatives. Highest-ROI content in the file.", Conventions, "Locked Decisions — things agreed + dated, must not re-litigate"; rules: "No file trees, no directory dumps… Anything an agent can derive from `ls` or `grep` rots fast"; annotate heavy references with "Read when:" triggers; "Maintenance loop: when [the user] corrects the agent on something this file should have prevented, add the rule to the file immediately"; "No absolute ALWAYS/NEVER without explicit exceptions."
**Why adopt:** Our root CLAUDE.md is excellent but monolithic, and subsystems have real folder-local law that doesn't belong at root: `brain/` (ingest conventions, manifest idempotency, Mac-runs-this-not-the-container), `engine/` (sim assumptions, what's backtest-earned vs prior), `ingest/`+`ingest_*.py` (auth/session conventions, rate discipline), `boom/`, `flagkit/`. The maintenance-loop rule is literally how PLAYBOOK.md case law works — same instinct, folder scope.
**How Opus uses it:**
- *Trigger:* Ramneik asks for folder context files, or a subagent repeats a folder-local mistake the root CLAUDE.md is too coarse to prevent.
- *Workflow:* per the skill — read the whole folder first (no skimming), propose the bullet list for approval, write with the "Apply root CLAUDE.md first, then this file." opener for subdirectory files, split Constraints from Conventions, date Locked Decisions, add `AGENTS.md` symlink, and thereafter apply the maintenance loop on every correction.
- *Plugs into:* `brain/CLAUDE.md` first (highest traffic + most environment-specific: launchd, faster-whisper, manifest idempotency), then `engine/` and the ingest layer. Cross-reference PLAYBOOK case IDs (C3/C5/C8…) instead of restating them.
- *Skip:* his personal sections (Avatar, Marketing Angles) and the `~/Documents/code/workspace/` path assumption.

### distribute-skill-to-all-agents — **NO.** Symlink bookkeeping for the four agent skill folders on David's MacBook (`~/.agents/skills` canonical, `~/.pi/agent/skills` trap, Hermes copy). We have one harness and project-local skills; his machine's layout is irrelevant.

---

## 4 · thinking-and-docs (7 skills)

### grill-me — **MAYBE (it's 3 sentences — use the pattern)**
**What it is:** "Interview me relentlessly about every aspect of this plan until we reach a shared understanding… For each question, provide your recommended answer. Ask the questions one at a time. If a question can be answered by exploring the codebase, explore the codebase instead."
**Why maybe:** Genuinely useful posture before locking high-stakes plans — `ARCHITECTURE_AND_REFACTOR_PLAN.md`, sim-engine assumption changes, new composite weights (which CLAUDE.md §3 already forces through backtests). The codebase-first clause fits our repo perfectly. But it's a one-liner prompt, not infrastructure; adopting it means remembering the pattern, not installing a file.
**How Opus uses it:** before executing any plan that touches locked assumptions (`ASSUMPTIONS_AUDIT.md`, `AUDIT_RUBRIC_SAFE.md` territory), run the grill loop on Ramneik one question at a time, answering from the repo (backtest results, PLAYBOOK case law) wherever possible and only escalating true judgment calls to him.

### interview-style-doc-building — **MAYBE**
**What it is:** Build strategic docs by asking ONE question at a time, patching the file after every answer ("receive answer → patch file → ask next question"), never overwriting after the skeleton. Standout rule: "Lists from [the user] are UNORDERED SETS… Never infer rank, priority, or sequence from the order he typed them. If you need ordering, ask explicitly."
**Why maybe:** The unordered-sets rule is directly relevant to draft-strategy work — if Ramneik lists "RB dead zone, stacking, late-round QB" that must not silently become a priority ranking in `docs/STRATEGY_SPEC.md` or `GOALS_COVERAGE.md`. The one-question/patch-after-each-answer loop suits building/refreshing `docs/DRAFT_STRATEGY_900.md`-class documents from his head.
**How Opus uses it:** when Ramneik wants to author strategy priors himself (roster-construction rules, exposure caps, tournament philosophy), run this loop against the target doc in `docs/`; enforce the set-vs-ranking rule for any list of strategies, players, or build types.

### brain-to-docs — **MAYBE (overlaps the above)**
**What it is:** Q&A loop extracting "taste, judgment, knowledge, vision, preferences, and decisions" into README + short numbered ADRs (`docs/adr/NNNN-slug.md`, Status/Context/Decision/Consequences), 5 varied questions per round, docs updated after EVERY answer.
**Why maybe:** We have no `docs/adr/` — our decision record is PLAYBOOK.md case law plus dated Locked Decisions, which works. The 5-varied-questions round is a nice complement to interview-style's one-at-a-time when the goal is breadth (surfacing unstated priors before draft season) rather than filling a known structure. Adopt at most one of these two loops; don't install both.

### read-all-adrs — **NO.** Fourteen lines telling the agent to read every file in `docs/adr/` (including an unfinished `TODO(David)` and profanity). We have no ADR folder, and our CLAUDE.md already mandates the equivalent ("read PLAYBOOK.md once per session"). Nothing to adopt.

### short — **NO.** One line: "rewrite your last response to be simpler & shorter." A user preference, not a skill; the repo's own `effective-agent-skills` anti-patterns section ("Don't write style-only variants") argues against shipping this.

### copywriting — **NO.** David Ondrej's personal public-copy voice (all-lowercase "authentic copy", his positioning principles). Our house style lives in `ui/COMPONENTS.md` and CLAUDE.md §4 (neutral-notes-first ordering, prose deliverables); his voice rules would actively conflict.

### teach — **NO (for this project).** A genuinely well-built multi-session teaching workspace (MISSION.md, `lessons/*.html`, learning-records as "ADRs for learning", spaced-retrieval pedagogy) — but it teaches humans topics, which is not what this repo does. Only revisit if Ramneik ever wants structured tutoring on, say, the Monte Carlo internals; that would be a personal workspace, not part of the pipeline.

---

## 5 · ops-and-setup (5 skills)

### cyber-audit — **MAYBE (pattern)**
**What it is:** "Read-only exposure audit… for a CVE, breach, malicious package, or other security advisory": no sudo, no state changes; parallel checks (global installs, manifest greps across `requirements*.txt`/`pyproject.toml`/lockfiles, running listeners, LaunchAgents); a fixed report with a Check|Result table and a three-tier verdict ("Not affected / Affected / Partially affected"), remediation listed but never executed.
**Why maybe:** It's scoped to David's MacBook, but the pattern is sound and we have a real (if small) attack surface: a Python dependency tree feeding pipelines that hold live session credentials for FantasyPoints/NFL Pro/SIS, plus yt-dlp/faster-whisper on the brain Mac. A supply-chain advisory against any of those warrants exactly this kind of disciplined, read-only, report-producing check.
**How Opus uses it:** on "are we affected by X?" — grep the advisory's package across our `requirements*.txt`/`pyproject.toml`/installed site-packages and `brain/setup_brain_mac.sh` deps, check nothing in `ingest/`/`pipeline/` imports it, write the verdict table to a dated audit `.md` at repo root (matching our existing `*_AUDIT.md` convention), remediation as follow-ups only. No skill install needed; the template is memorable.

### anti-sleep — **NO.** macOS `caffeinate` flag reference. Marginal theoretical relevance (the brain ingest runs on a Mac overnight) but launchd — which `com.nflbrain.ingest.plist` already uses — is the correct wake mechanism, not a caffeinate babysitter.

### setup-help — **NO.** An interaction format (one atomic step + "Still remaining" list ≤8 items) for walking David through installs. Pleasant UX, zero project specificity, nothing our normal interaction doesn't already do.

### pi-custom-model — **NO.** Registering OpenRouter model variants in the Pi agent's `models.json`. We don't run Pi.

### vps-server-management — **NO.** David's three Hostinger VPSes (OpenClaw/n8n/Hermes), with placeholders where his IPs go. Entirely his infrastructure.

---

## Bottom line

The repo is a competent personal library, ~50% locked to one man's Mac/agent-stack/product. For us it yields **five adoptions** — `handoff`, `research-prompt`, the yt-dlp half of `youtube-transcript`, `effective-agent-skills`, `folder-specific-claude-and-agents-md` — of which the youtube-transcript captions-first + 429-stop change to `brain/brain_video.py` is the only one that touches running code; the rest are process templates that formalize things this repo already half-does (handoffs, research briefs, CLAUDE.md law, skill authoring). Six more are worth stealing as one-paragraph patterns without installing anything. The remaining eighteen are a clean **no**. License is MIT, so copying and adapting text is fine; per `effective-agent-skills`' own security checklist, anything adopted should be copied and edited into our tree (pinned to commit `6261b61`), never live-fetched.
