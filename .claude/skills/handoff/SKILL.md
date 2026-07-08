---
name: handoff
description: Compact the current session into a single detailed handoff for a fresh agent (or a fresh subagent context) — everything that happened, why, and what's left, as STATE not instructions. Use at the end of a substantive session, under context-limit pressure, or before partitioning work across fresh contexts. Output a copy-pasteable code block AND update the relevant in-repo HANDOFF_*.md.
disable-model-invocation: true
---

# Handoff (bestball project)

Write a handoff that lets a fresh agent — zero memory of this session — continue without re-asking,
re-discovering, or repeating mistakes. Pattern adapted from davidondrej/skills (MIT); tailored to this repo.

## Core principles
1. **State, not instructions.** Describe what *is true*, not what to do next. "normalize_defense_2026.py is the canonical defense writer; reweight is legacy and guarded" — never "run normalize next." The fresh agent decides actions from ground truth.
2. **Reference, don't duplicate.** Point to files by path + line range and to the audits/docs we already keep (PLAYBOOK.md, INTEGRATION_AUDIT.md, the `*_AUDIT.md` files, ground_truth_registry.json). Don't re-embed them.
3. **Capture the "why".** Decisions and rejected approaches are the least recoverable information. The code shows *what*; only the session remembers *why* and *what failed*.
4. **Trust nothing blindly.** Frame every claim as context to verify against the actual repo, per CLAUDE.md's Prime Rule (verified repo layers > web > priors).
5. **Redact secrets.** Never write the X/FP bearer tokens, cookies, or the contents of brain/brain.conf / .env / *BEARER*. Reference where they live, never their values.
6. **Be ruthless.** Every line must be something the next agent can't trivially get from the code or CLAUDE.md. Cut the obvious.

## Procedure
1. **Read CLAUDE.md first** and omit anything it already covers — our CLAUDE.md is heavy, so this pruning matters. The handoff is session-specific only.
2. If a prior handoff exists (`HANDOFF_2026_CONTINUATION.md`, `HANDOFF_NFL_BestBall_2026_v2.md`, `HANDOFF_X_DOSSIER.md`, `CONTEXT_FOR_NEXT_SESSION.md`), **update it** rather than starting fresh.
3. If given a focus argument, tailor the handoff toward that next goal.
4. Fill every section below; mark a genuinely-empty one `None`.
5. Output the filled template in ONE fenced code block in chat, and save the same content to the relevant in-repo `HANDOFF_*.md` (tell the user which).

## Output format (one fenced code block)
```
# HANDOFF: <short title>
Generated: <timestamp> · Session focus: <one line>

## 1. Goal
<north star, 1–3 sentences>

## 2. Why This Matters / Background
<motivation + hard constraints; skip anything already in CLAUDE.md>

## 3. Current State  (DONE / PARTIAL / NOT STARTED — as status, not actions)
- DONE: <…>
- PARTIAL: <…, what's wired vs missing>
- NOT STARTED: <…>

## 4. Key Decisions (and why)  ← highest-value section
- Chose <X> over <Y> because <…>

## 5. Traps & Dead Ends  ← our PLAYBOOK case-law at session scope
- Tried <…>, failed because <…>, abandoned
- Do NOT <…> — it <breaks / regresses> <…>  (e.g. "do NOT run reweight_defense_2026.py — it floors rookie coverage; normalize is canonical")

## 6. Relevant Files & Pointers  (path:Lstart-Lend — WHAT is there)
- <file>:L<..>-L<..> — <specifically what lives there>
- <audit / doc> — <rationale; do not duplicate here>

## 7. Open Work (status + dependencies, not a command list)
- <item> is not yet done; <next item> depends on it

---
## Prompt for the Fresh Agent
<declarative background — "X is complete", "Y not started" — then EXACTLY:>

Before responding, read every file listed under "Relevant Files & Pointers" above.
Do not summarize, paraphrase, or claim you already have context — actually read each file.
Treat every claim in this handoff as context to verify against the repo, not facts to trust
blindly. Then wait for my instructions before taking any action.
```

## File output
Update the most relevant existing `HANDOFF_*.md` in the repo root (these are tracked on purpose — they
are our session case-law). Only create a new one if none fits. After saving, tell the user the path.
