# Signal Findings — overfit-safe validation log
*Every candidate signal is tested out-of-sample (2024 feature → 2025 realized booms) before it's allowed to change a boom probability. This log is the audit trail. June 2026.*

## Headline
The model is **base-dominated**. A player's modeled base ceiling rate (talent + role) explains the large majority of realized booms (AUC 0.739; Spearman 0.505 base-vs-realized). Layers added on top of the base are, at best, small — and several plausible ones add **nothing** out-of-sample. This is good news (the core is sound) and a strong overfit warning (resist stacking marginal multipliers).

## Gate results
| Signal | Test | Result | Verdict |
|---|---|---|---|
| **Route participation** (snap/route opportunity) | 2024 route% → 2025 boom rate (WR) | corr **+0.06**; residual-vs-base **−0.22**; AUC 0.567 | **CONTEXT ONLY** — redundant with base; not a multiplier |
| **Matchup / environment layer** (existing) | pooled AUC base vs base×matchup | **0.739 → 0.724** (slightly *hurts*); within-player 20% vs 16% (small real signal) | **KEEP, SHRUNK + PER-POSITION** — helps QB/TE, hurts WR/RB |

### Per-position matchup AUC (full vs base-only)
- QB 0.771 vs 0.752 ✅ matchup helps
- TE 0.611 vs 0.587 ✅ matchup helps
- WR 0.757 vs 0.784 ❌ matchup hurts (over-sized)
- RB 0.649 vs 0.693 ❌ matchup hurts (over-sized)
- DST 0.820 vs 0.827 ➖ neutral

## What this means for the "ingest everything" plan
1. **Opportunity signals (snap/route/target share) are already in the base** → keep as *context*, don't multiply. (route participation: done, context-only.)
2. **More matchup multipliers are the wrong direction** — the matchup layer is already marginal and slightly over-sized for WR/RB. Adding PROE/DVOA/coverage as *more* multipliers risks making pooled discrimination worse, not better.
3. **The real, orthogonal lift is in the BASE / talent prior**, especially where the base is thin or stale:
   - **Rookies** (no NFL base) → PFF grades + draft capital + FTN scouting is the single highest-value add, because it improves the layer that actually drives the model.
   - **Low-sample / role-change players** → PFF grades stabilize the base.
4. **Matchup signals should be per-position-gated** (apply where they validate: QB/TE; shrink hard or suppress for WR/RB) rather than applied uniformly — but only after confirming the per-position split holds on more than one season (guard against fitting 2025 noise).

## Revised priority (signal-value, not source-completeness)
1. **PFF grades → base/talent prior** (esp. rookies + low-sample) — orthogonal to volume, improves the dominant layer.
2. **Rookie model** (PFF grades + draft capital + FTN scouting + Clay baseline) — the base is empty here today.
3. **Per-position matchup gating** (use the QB/TE-helps, WR/RB-hurts finding) — a *subtraction*, costs no new data.
4. PROE / DVOA / shadow-corner — only if they show out-of-sample lift *as base or per-position matchup adjusters*, entering shrunk; otherwise context.

## Update — opportunity family closed
| Signal | Test | Result | Verdict |
|---|---|---|---|
| **Snap share** | 2025 snap% → 2025 boom (in-sample upper bound) | raw corr +0.44 RB / +0.22 WR / +0.30 TE; **residual-vs-base −0.03 / +0.06 / +0.09** | CONTEXT ONLY |
| **Red-zone snap share** | same | raw +0.34 RB / +0.22 WR / +0.33 TE (collinear w/ snap% + existing redzone.json) | CONTEXT ONLY |

**Conclusion:** the entire *opportunity* family (route participation, snap share, RZ-snap share) is redundant with the base rate. Even the in-sample residual (an upper bound on out-of-sample signal) is ~0. The base already encodes "who's on the field and gets the ball." These are kept as **context** (every-down role) and will not move a boom probability. Method note: *residual-vs-base on existing-season data is now the cheap first screen* — a signal that adds ~0 beyond base in-sample cannot add out-of-sample, so it's rejected without a 2-season pull. Only signals that pass this screen get the full out-of-sample 2024→2025 treatment.

## Update — separation PASSES (first signal to earn a place)
| Signal | Test | Result | Verdict |
|---|---|---|---|
| **Separation (overall)** | 2025 SEP → 2025 boom, residual-vs-base (WR) | **+0.29** | PASSES — adds beyond base |
| **Separation vs MAN** | same | **+0.32** (strongest orthogonal signal found) | PASSES — wired as "Elite separator" skill flag |

Unlike the opportunity family, **separation is orthogonal to the base** — it measures a skill (getting open, esp. vs the toughest man coverage) the volume/scoring base doesn't capture. Wired conservatively as a skill flag (context), not a sized multiplier, since the test is in-sample (upper bound). 19 WRs flagged (incl. Chase 87th, Puka 82nd vs-man). 43 WRs / 14 TEs are elite-man-sep in `separation.json`.

**Running scoreboard (pull + gate all sources):**
- ✅ Coverage specialist (2-season Man/Zone/Single/Two) — live
- ❌ Route participation — CONTEXT ONLY (residual ~0)
- ❌ Snap share / RZ-snap share — CONTEXT ONLY (residual ~0)
- ✅ **Separation (esp. vs man)** — PASSES, wired (WR)
- ⏳ Depth-of-target, defensive splits (FP Def views + FPA-by-position), DVOA/shadow (FTN), PFF grades — queued

## Update — DEFENSIVE switch test (opponent matchup, per position, leak-free)
Tested per-game: does the player's actual opponent-defense softness predict that game's boom? (`gamelog` opp pass-D pctl for QB/WR/TE, run-D pctl for RB.)

| Position | AUC | boom vs SOFT D | boom vs TOUGH D | lift | verdict |
|---|---|---|---|---|---|
| **QB** | 0.583 | 17.5% | 7.2% | **2.42×** | ADD — strong, the biggest matchup signal in the model |
| **TE** | 0.560 | 21.4% | 16.3% | 1.31× | ADD — moderate |
| **WR** | 0.540 | 19.9% | 16.9% | 1.18× | ADD — small |
| **RB** | 0.430 | 17.8% | 23.8% | **0.75× (inverted)** | OFF — run-D pctl is the wrong defensive lens for RB ceiling |

**Action:** size the defensive matchup multiplier **per position** — strong for QB, moderate TE, small WR, **off for RB**. This is the root cause of the earlier backtest result (matchup layer helps QB/TE, hurts WR/RB pooled): it was applied roughly uniformly, but the *true* defensive signal is highly position-dependent. No new data needed — it's a sizing fix.

Pulled `fpAllowed_TE_2025.csv` (32 teams, per-defense FP allowed to TEs) as the cleaner per-position FP-allowed source; the per-game gate above is the leak-free validator. Genuinely-new defensive adds still queued: **PFF per-CB coverage grades** (shadow quality) + **FTN DVOA-adjusted FP-against** (opponent adjustment).

## Update — funnel WIRED into the boom model (WR)
The opponent-adjusted DVOA funnel was gated as a **better WR matchup signal** than the raw opponent percentile (per-game AUC **0.617 vs 0.540**), and on the full model **base × funnel lifts WR AUC 0.784 → ~0.79–0.80**. Wired as a conservative, alignment-routed per-week overlay (`apply_funnel_overlay.py`, LAM 0.6, mult ±10%, slot-WR→slot-funnel / boundary→WR1·WR2): **1127 week-nudges across 148 WRs**, each carrying a funnel note. Added to the pipeline after `build_flags_WR`. TE was a wash (not wired). This is the first *opponent-side* signal to earn a sized multiplier under the gate.
