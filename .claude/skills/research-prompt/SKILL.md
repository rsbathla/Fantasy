---
name: research-prompt
description: Turn a research need into ONE self-contained paragraph a researcher (or a fable research subagent) with zero prior knowledge can act on with no back-and-forth. Use for any fan-out research delegation — coaching/scheme-change corroboration, 2026 roster/personnel verification, X-dossier building, or writing back to ground_truth_registry.json. Produces one tight paragraph with numbered sub-questions, a primary-source hierarchy, a fact/inference/unresolved split, and a per-finding output format.
---

# Research Prompt (bestball project)

Turn a vague research need into ONE self-contained paragraph. Pattern adapted from davidondrej/skills
(MIT); tailored to this repo's evidence discipline (CLAUDE.md Prime Rule; C3 "title-only churn is not a
scheme change"; no single-signal anchoring).

## Rules
- **One paragraph.** No headers/bullets in the deliverable itself.
- **Prompt the job, not the topic.** Give search handles: timeframe (it is the 2026 season — flag that facts post-date the model's cutoff and MUST be web-verified), the decision it feeds, source type, and the ranking/decision logic.
- **Assume zero prior knowledge.** Open with 1–2 plain-English sentences on what this project is (an NFL best-ball/DFS analytics system with a Python pipeline + an Obsidian "second brain") and the current situation, so a fresh researcher needs to ask nothing.
- **Lead with the goal + decision.** State the single question and the decision/use it informs (e.g. "to set `direction_2026` in personnel_2026.json", "to confirm a `ground_truth_registry.json` entry").
- **Embed all context.** Names, dates, the known prior fact, and which repo file the answer writes back to.
- **Number sub-questions inline (1,2,3…), 3–6 of them.** One mission per prompt.
- **Source hierarchy.** Prefer primary sources (team sites, beat reporters, official transactions, Spotrac/OTC contracts, box scores, PBP); forums / X / Reddit are weak signal only, never factual proof.
- **Contradiction handling.** If sources conflict, separate **confirmed fact / inference / unresolved** — do not force a fake consensus. Flag low-confidence claims for verification (this is exactly what caught the SF Juszczyk error).
- **Completion bar.** Don't stop at the first plausible answer: corroborate each key claim with multiple independent primary sources where they exist; say so explicitly where they don't. Cover every numbered sub-question to that bar.
- **Gap round before finishing.** Require a final self-critique pass: list gaps, contradictions, single-source claims — then run another search round to close them, repeating until clean.
- **Per-finding output.** Source link + specific claim + date + one-line "why it matters (which projection/registry field it moves)". Verifiable, citable facts only.
- **Last sentence:** instruct the researcher to write everything into a single detailed markdown file in the repo (name it `*_AUDIT.md` or `*_VERIFICATION.md` to match our convention).

## Process
1. Pull context from the relevant repo files (the `ground_truth_registry.json` entry, `COACHING_CHANGES_2026*.md`, `coordinator_changes_2026.json`, the projection/JSON field to update) and write the plain-English explainer.
2. Identify the ONE question.
3. Draft 3–6 numbered sub-questions that fully cover it.
4. Add include/avoid constraints + the per-finding format.
5. Compress to one clean paragraph; cut filler.

## Template
> [1–2 plain-English sentences: what this project is and the current situation, for a reader who knows nothing.] Research [TOPIC + key identifying facts, with dates] to answer one question: [THE QUESTION] — for [DECISION / which repo field it updates]. It is the 2026 NFL season, so treat all 2026 facts as post-cutoff and web-verify them. Find: (1) …; (2) …; (3) …; (4) …. [Constraints: include X, avoid Y.] Prefer primary sources (team/official/beat/contract/box-score); treat forums and social as weak signal only. If sources conflict, separate confirmed fact from inference from unresolved uncertainty and flag what needs verification — do not force consensus. Don't stop at the first plausible answer: corroborate each key claim with multiple independent primary sources where they exist (and say so where they don't), until every numbered question is covered. Before finishing, run a self-critique gap round — list gaps, contradictions, and single-source claims, then search again to close them, repeating until clean. For each point give the source link, the specific claim, its date, and a one-line "why it matters / which projection or registry field it moves." No fluff — verifiable, citable facts only. Write everything into a single detailed markdown file in the repo (`*_AUDIT.md` / `*_VERIFICATION.md`).

## Running it
Hand the finished paragraph to a fable research subagent (Agent tool, model=fable) — the same pattern used
for the 2026 coordinator, verification, and PERSONNEL.md-audit passes.
