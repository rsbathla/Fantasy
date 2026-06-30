# Layer 0/1 Reconciliation Register — 2026 Best Ball Sim Foundation
Source of truth for what is CONFIRMED vs CONSUME-WITH-CAVEAT before any wiring.
Rebuilt from nflfastR PBP 2024–25; cross-checked vs NFL-master repo (FantasyPoints-derived strength profiles + EPA).

## Components rebuilt (match prior session)
| Output | Check | Status |
|---|---|---|
| player_games.parquet (11,223 rows) | DK full-PPR + usage | OK |
| team_volume_model.json | pass_att 27.4 +0.170·total −0.151·spread; script slope −0.0068 | matches prior |
| correlation_structure.json | QB–WR1 0.351, QB–WR2 0.339, QB–WR3 0.256; WR1–WR2 0.042 (≈0 cannibalization); bring-back hi 0.159 > lo 0.062 | matches prior |

## Layer 0 — Opportunity (CONFIRMED)
| Metric | nflfastR vs FantasyPoints | Verdict |
|---|---|---|
| Season targets (161 WR/TE) | r=0.988, median offset +3.2% (nflfastR slightly higher) | PASS — canonical = nflfastR; FP charts out uncatchable targets (~3%) |

## Layer 1 — Efficiency (CONFIRMED)
| Metric | Check | Verdict |
|---|---|---|
| aDOT | nflfastR vs FP r=0.989, ratio 0.97 | PASS — FULL SCALE, **no halving** in strength profiles |
| YPRR | FP Overall_YPRR vs nflfastR rec_yds/FP routes r=0.946, ratio 0.98 | PASS — internally consistent |
| TPRR total-row vs Overall_TPRR | median |diff| 0.009 | PASS — confirms max-RTE row = season total |

## Layer 1 — EPA (RECONCILED — known convention)
| Metric | Check | Verdict |
|---|---|---|
| QB EPA/dropback | nflfastR vs repo r=0.80 (2025) vs 0.33 (2024) -> repo snapshot = 2025 | compute EPA from nflfastR (canonical), uniform definition |
| EPA definition test (4 variants) | repo Pass_General best matches PURE pass-attempt EPA (no sacks/scrambles) r=0.84, D.Jones 0.26 vs 0.28; adding rushing did NOT help (r=0.80) | gap = sack/scramble exclusion, NOT pass-vs-pass+rush. Don't import repo EPA (mixing sack conventions across QBs = silent inconsistency); use qb_epa/dropback uniformly |

## Data-shape traps caught (do not repeat when wiring)
1. Strength-profile **first alphabetical row per Scheme_Type is a mislabeled SEASON-TOTAL row** (e.g. JSN "Cover 0"=534 RTE). Use max-RTE row for counts; Overall_* for rates. NEVER sum across schemes (double-counts).
2. nflfastR `J.Chase` vs FP `Ja'Marr Chase` — name join must split on the period; collapsing it loses the initial.
3. Correlation roles must be FIXED season roles, not per-game top-targets (per-game inflates QB–WR1 0.43→0.35 and WR1–WR2 0→0.18 via selection bias).

## Scope for Layer 2 (2026 assumptions)
- ALL repo data (strength profiles, EPA, coverage splits) = **2025 season incl. playoffs (Week22)**. Do NOT treat as 2026.
- Strength-profile targets are charting-based (~3% below nflfastR); pick ONE target source per metric, don't mix.

## Layer 2 + Sim (built & validated)
- Clay 6/10 parsed (417 players); 2025 backtest vs actual: **r=0.75 overall** (TE .74 > WR .69 > RB .65 > QB .60).
- Team coherence: target shares sum ~99.5%, receiver tgt = 0.98x QB att; carry shares derived from RAW normalized volumes (incl QB rush) — Car% column ambiguous, not used.
- **Compositional sim validated** (K=8, SG=.31, ST=.27, SP=1.0): reproduces QB-WR1 **0.33** (t .35), WR1-WR2 **~0** (t .04), bring-back hi **.065** > lo **.039**. Marginals calibrated to Clay means (linear scale preserves CV+corr); WR CV .85-1.08, QB CV .32-.47 — realistic.
- Output: player_sim_distributions.csv (mean/p50/p85/p95/CV/spike% per player).
- REMAINING: pod P(top-2 of 12) needs the 12 roster lists (user's + 11 opponents) or an ADP-field proxy.
