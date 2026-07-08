# DFS System — Full Review (July 8, 2026)

Everything built, everything found, and what's next. Receipts throughout; every number is
reproducible from a script in this repo.

---

## 1. Data assets

**FantasyLabs archive — 3,117 contests, 2021-11-25 → 2025-01-26** (pulled via public
CloudFront endpoints, no auth):
per-contest player pools (salary / FL projection / real ownership / actuals), winner
exposure tiers (top-1% / 10% / 20% vs full field), team & game stack tiers (truncated by an
early puller bug — v6 re-pull pending on your Mac), contest meta (entry, size, cash line,
duplicate/unique lineup counts), and **your complete history: 1,450 contests** with
per-contest lineups, exposures, leverage, percentile finishes, and P&L.

Also: FantasyCruncher decade (players + games), nflverse tendencies (PROE, pace, goal-line,
target shares), 2026 coaching-carousel briefs + personnel-adjusted PROE (SEA −3.8 → −1.8),
divergence docket vs the FantasyPoints playcaller article.

**Tooling:** fl_puller v6 (harvest / pull / winners / users / restacks+id-maps),
dfs_optimizer (ILP + stacking ruleset), contest_sim / season_sim (checkpointed),
showdown_sim v3, highstakes_1to1 (true-field-size), portfolio_150, user_audit, week_leaks,
slate_buckets, milly_divergence, high_autopsy, winner_construction (ready, awaiting
stacks_full), PROJECTION_ERROR.md (new).

## 2. The audit — who you are as a player

Career: **$6.84M entered, +$1.30M net (+19%)**, 2021→2024.

Your conviction reads validate against actual top-1% winners at **~47% — field average**.
2023 lost −40% and 2024 made +117% on the same read accuracy. The edge was never picking
better; it is **(a) WHERE you deploy, (b) HOW you express (one core, many distinct builds),
(c) payoff asymmetry when max-conviction hits.** Top-5 slates = 266% of career net
(Wk18-2024 Milly takedown +$999K on 100% McConkey through 150 distinct lineups; SB LIX +$1.10M).

Buckets: **MAIN +35% · SHOWDOWN multi-entry +39% (no losing season) · SMALLER −40%**
(only 4+-game playoff slates positive, +13% — the edge you remembered) · dome −39%.

Leaks, each with dollar receipts: mass-cloned lineups ≈ **−$700K** career; 2-3-game slates
**−48% on $1.18M**; inverted sizing (spend +19% after losses, −29% after wins → a 13-slate
losing streak, −$393K drawdown); QB over-captaining (39.6% vs winners' 18.5%);
**hand-me-down high-stakes lineups** (86% average overlap between your $20 and $555+ entries;
≥90%-overlap slates −47% vs +112% when differentiated); **$4,444 MEGA −43% on $1.14M**
(faded builds + oversized bullet counts in a chalk-structure arena); 150-bullet $555 weeks
(volume past ~36 is −EV in a 2-5K field).

## 3. The rulebook (R1-R11 + dial sheet — RSBATHLA_RULES.md)

R1 never <4 games · R2 one lineup one entry · R3 loss brake on sizing · R4 conviction via
distinct lineups · R5 bucket budgets (MAIN+SHOWDOWN ≥90%) · R6 big bullets need big slates ·
R7 construction by field softness · R8 60-second pre-lock checklist · R9 captain the boom,
differentiate the bench (QB-CPT ≤25%) · R10 tiny slates fail by under-differentiation ·
**R11 sims set dials, you build lineups** (no machine-built lineup enters play).

## 4. The laws (replication status in parentheses)

| contest | dial | key receipts |
|---|---|---|
| $20 Milly | λ10-15, 150 distinct | 16.8% of field = copies; casual star-chalk to attack; takedown = lottery (0.09% of field) — keep volume cheap |
| $555 Milly | λ6-10, **19-36 bullets** (2 seasons deep + 1 shallow) | K-curve negative past ~36-75; sharp value-convergence 60-85% = the pivot; your −0.2% on hand-me-downs → native builds at right volume = upside |
| $4,444 MEGA | λ0-3, **5-19 bullets** (**4 seasons**) | chalk wins every K, every year; every fade step costs money; sim's fade10×K19 = −33% vs your real −43%; P(win) ≈ 4% at K19 chalk |
| single-entry | fade hard (4 seasons) | everyone submits their best chalk build |
| Thunderdome | λ0 (4 seasons) | fades monotonically destructive |
| small 4-6 games | λ8-14 + bring-back (3 seasons: peaks 337/367/565%) | the wild-card-weekend edge, pressed harder |
| small 2-3 games | R1: $0; else λ6-12 (4 seasons) | archetypes are year-to-year noise (bringback 613→157→268%); chalk inescapable (~20%/player at optimum) |
| showdown | mild-tail majority (see below) | two full seasons v3 |

**Showdown tie economics (your framing, now measured):** the chalk build is co-held by
**10-12 entries in-model** and still posts top ROI after splitting (+52% '23 / +34% '24) —
being in the right tie is priced and correct. **Mild-tail (λ3.5 on the last two FLEX) keeps
the winning shape at ≈1 co-holder** for near-chalk EV (+49% '23 / +16% '24). Deep flex fades
lose every year. New dupe calibration (opus agent): real max-dupe counts run **30-60+**, not
10 — sim was conservative, so real-world ordering likely favors **mild-tail ≥ chalk**.
Portfolio: majority mild-tail, minority pure chalk, a few captain pivots (the dedupe lever).

**$20 vs $555 ownership divergence:** corr 0.938 but 198 players ≥8pp apart (166
sharp-higher — value RBs like Moss 85% vs 65%; 32 casual-higher — stars like Henry 47% vs
33%). Different leverage maps per contest → rebuild per contest, never copy.

**The volume law (new, from true-field-size sims):** in fields ≤5K your own bullets
cannibalize — marginal ROI decays fast and goes negative past ~36 (555) / ~36-75 (MEGA).
Win-probability still rises with K, but each point costs exponentially more: the K choice is
an EV-vs-takedown tradeoff, and it's yours (R11).

## 5. The machine-vs-human verdict

portfolio_150 (sim the slate → each world nominates its optimal legal lineup → pick 150 for
outcome coverage) backtested against your real entries in **all 19 flagship 2024 Millys:
machine −$47,208, zero winning slates; you +$991,242, four winning slates** (ex-jackpot:
−$44.5K vs −$7.6K — you still win). Post-mortem, four failures: it graded its own homework
(optimizer's curse), it modeled variance but not projection error, it treated ownership as
dumb money, and it extrapolated the extreme tail from a 49×-scaled sample.

Capstone measurement: players that top-1% lineups overweight beat their projections by
**+1.26σ on average (61% ≥1σ vs 16% baseline)** — the top of a GPP is made of projection
error, i.e., information that isn't in the projections. Construction can't buy the error
vector; your McConkey week was holding a piece of it. Hence R11.

## 6. Fresh from the delegated agents (today)

**Sonnet agent — replication queue, 9/9 complete:** showdown v3 2023 (61 slates: chalk
+51.5% @ 11.7 co-holders, mild-tail +49.4% @ 0.77, weird-cpt +45.1%); MEGA 1:1 2022 + 2021
(chalk dominates every K — the law is now four-season); 555 2022/2021 (thin data,
consistent); small-slate forks 2022 + 2021 (λ zones hold; archetype noise confirmed).

**Opus agent — projection-error model (PROJECTION_ERROR.md):**
- FL projections are optimistic everywhere (QB −1.29 pts … DST −0.34); error std is linear
  (≈ 4 + 0.3·proj), so the CV model under-disperses cheap players (up to 2.25×) and
  over-disperses studs (0.6-0.75×).
- **The missing piece is correlated slate-level error:** real 9-player lineup residual-sum
  std = 31.8 pts vs 21.6 under independence (**1.47× too tight**) — the exact mechanism
  behind the machine's 22%-claimed / 0-for-19 reality.
- **Chalk is better-projected** — ownership is information, now measured (QB own ≥20%:
  +1.36 vs own <5%: −2.12 pts vs projection). The field's chalk is chalk for a reason.
- Concrete v2 world parameters delivered: per-position bias multipliers k (0.926-0.955),
  correlated slate shock σ_sys (0.216-0.291), reduced idiosyncratic CVs.

## 7. What's next

**My side, in order:**
1. Implement **sim v2 worlds** (bias correction + correlated slate shock, opus parameters) and
   rerun the flagship laws — the orderings should survive honest dispersion; absolute ROIs will
   deflate toward reality. Raise showdown dupe scaling (30-60) and re-settle the showdown split.
2. Finalize the showdown portfolio split with the honest dupes; λ-tail sweep if needed.
3. The moment stacks_full lands: **winner_construction** — top-1% stack shapes (QB+1 / QB+2 /
   naked / bring-back) by year × contest type, the winner-data version of the dial sheet's
   structure column.
4. Exact-history replay: the restacks id-maps let me push your real 1,450-contest lineup
   history through the true-size sims — grading every historical decision against the dials.
5. v2-hybrid falsification (quiet, per R11): your-core + machine-variation + error-model
   worlds; only surfaces if it beats chalk AND your real portfolios out-of-sample, 3+ seasons.

**Blocked on you (Mac, ~40 min, resumable):**
```
cd ~/Downloads/Fantasy
unzip -o ~/Downloads/fl_puller_v6.zip
python3 fl_puller.py --restacks --all-types
python3 winner_construction.py
```
Then paste the printout or ship construction_summary.csv / the stacks_full folder.
(Also still open: SB LIX-window pull if missing, FD harvest test, 2025-season pulls when you
want them.)

**For the 2026 season:** the weekly workflow is R8 + the dial sheet — you make the reads,
build per-contest at the listed λ/K, and the standing analytics (PROE briefs, tendencies,
ownership pulls) feed the read.
