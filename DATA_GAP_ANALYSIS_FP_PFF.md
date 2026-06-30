# Data Gap Analysis — FantasyPoints + PFF vs. the Boom Model
*What every FantasyPoints tool offers, what the ceiling model already uses, and the signals we have NOT captured — ranked by ceiling-model value. June 2026.*

---

## How to read this
"Captured" = already in the model (`statmenu` / `adv2` / `chart2` / `cover_spec` / `rz` / `team_env` / `defense_shell`). The boom model is a **ceiling** model, so the highest-value missing signals are the ones that drive **opportunity volume** and **boom variance**, not just efficiency.

---

## FantasyPoints tool suite — coverage map

| Tool | Key signal | Status in model |
|---|---|---|
| **Passing → Advanced** | aDOT, TTT, pressure%, CPOE, turnover-worthy | ✅ `chart2` (QB, 2024) |
| **Passing → Depth of Target** | QB production by depth bucket | ❌ **not captured** |
| **Passing → QB Coverage Matchup** | QB FP/DB vs Cover-2/3/4/6 | ✅ `cover_spec` (QB, 2025) |
| **Rushing → Advanced** | YBC, YAC, MTF, rush concept | ✅ `chart2` (RB, 2024+25) |
| **Rushing → Bell Cow Report** | RB rush+rec usage share | ◑ partial (`usage`/`adv2`) |
| **Receiving → Advanced** | routes, catchable, 1st-read | ✅ `chart2`/`adv2` (2024+25) |
| **Receiving → Routes Run** | routes by alignment (wide/slot/inline/backfield) | ◑ partial (`chart2` slot%/wide% only) |
| **Receiving → Man vs. Zone** | FP/RR vs Man/Zone/Single/Two | ✅ **just added, 2-season** |
| **Receiving → Separation by Coverage** | separation vs Man/Zone/Cover-2/3 | ❌ **not captured** |
| **Receiving → Separation by Alignment** | separation slot/wide/inline | ❌ **not captured** |
| **Receiving → Separation by Route Breaks** | separation horizontal/vertical | ❌ **not captured** |
| **Receiving → Separation by Routes** | production by route type (slant/go/corner) | ❌ **not captured** |
| **Offense → RB+WR Efficiency** | MTF/YAC/explosive per touch | ◑ partial (`chart2`) |
| **Offense → SNAPS REPORT** | offensive snap counts/share by play type | ❌ **not captured — top hole** |
| **Offense → Run/Pass Report** | situational run/pass rate | ◑ partial (team pace only) |
| **Team → Coverage Matrix** | team D coverage usage + O coverage faced | ✅ D usage (`defense_shell`); ❌ O-faced |
| **Team → OL/DL Matchups** | adjusted run/pass block win metrics | ◑ partial (`ol_q`/`pblock` from ffdataroma) |
| **Fantasy → Points Scored/Allowed** | team FP scored/allowed, filterable | ✅ defense tiers (`defense_2026`) |
| **Weekly → Snap Share** | weekly snap % | ❌ **not captured — top hole** |
| **Weekly → Route Share** | weekly route participation % | ❌ **not captured — top hole** |
| **Weekly → Target Share** | weekly target % | ✅ `usage.tgt_share` |
| **Weekly → Pass Rate Over Expectation (PROE)** | team pass tendency above expected | ❌ **not captured — top hole** |

---

## The gaps that matter for a ceiling model (ranked)

**1. Snap share / route participation (HIGHEST).** The model proxies opportunity through target share and `routes_pg` for only ~96 players; it has no clean **snap %** or **route participation %** for the field. This is the #1 hole the architecture audit already flagged. For a ceiling model it's the floor of opportunity: a WR at 95% routes has a structurally higher boom ceiling than one at 60%, independent of efficiency. Rising snap/route share week-over-week is one of the strongest ceiling leading-indicators in fantasy. **Source:** Offense → Snaps Report (season), Receiving → Routes Run (season), Weekly Snap/Route Share. Maps cleanly to a new `opportunity` block (snap_pct, route_pct, alignment split).

**2. Team Pass Rate Over Expectation — PROE (HIGH).** The model has pace/`env_idx` but not **PROE** — how much more (or less) a team passes than game-state expects. High-PROE offenses manufacture pass-catcher ceilings even in neutral scripts; low-PROE (run-heavy) offenses cap their WRs. This is a team-environment multiplier the model is missing. **Source:** Weekly PROE report → aggregate to a team-season PROE → fold into `team_env` as a pass-catcher amplifier / RB suppressor.

**3. Separation by Coverage / Route type (MEDIUM-HIGH).** We now have FP/RR vs Man/Zone/Single/Two (production), but not **separation** vs those coverages, nor production **by route type** (slant/go/corner/post). Route-type and separation-by-coverage tell you *how* a player wins, which sharpens the existing coverage-specialist + the "separator vs technician" skill flags. **Source:** Receiving → Separation by Coverage / by Routes.

**4. QB Passing Depth of Target (MEDIUM).** QB production split by depth bucket (short/intermediate/deep). Complements the existing QB charting; a QB who is elite on deep balls has a higher ceiling and pairs with deep WRs (stack signal). **Source:** Passing → Depth of Target.

**5. OL/DL adjusted block-win (MEDIUM).** The model uses ffdataroma `ol_q`/`pblock`; FP's **adjusted** run/pass block-win rates are a cleaner, charted source and would upgrade the DST trench signal + the QB clean-pocket flag. **Source:** Team → OL/DL Matchups.

**6. Offense coverage faced (LOW-MED).** Team-level "what coverages this offense sees" — useful for opponent-adjusting the coverage-specialist activation, but largely already handled by per-defense `defense_shell`.

---

## PFF — what it adds that FantasyPoints (and the model) lack
PFF requires a separate login (no PFF tab is currently open in the browser). Its genuinely-unique signals, none captured today:

- **PFF player grades** (overall, receiving, rushing, pass-block, run-block, coverage) — a charted *quality* score independent of volume; a strong stable prior, especially for **rookies** with no NFL sample.
- **WAR / WAA** — wins above replacement, a single talent index.
- **Pass-block / run-block grades per OL** — sharper than win-rate for the trench/QB-protection flags.
- **Coverage grades per CB/S** — would enable a true **shadow-corner** matchup signal (the model has none today — it's team-scheme only).
- **Rookie college production / draft-capital-adjusted projections** — directly answers the rookie-projection question.

---

## Recommended ingest order (input back into the model)
1. **Snap share + route participation** → new `opportunity` block; wire a "rising/elite usage" ceiling flag and an opportunity floor into the base. *Biggest expected lift.*
2. **Team PROE** → `team_env` amplifier for pass-catchers/QB, suppressor for RBs.
3. **Separation by coverage + route type** → sharpen the separator/technician skill flags and the coverage specialist.
4. **QB depth-of-target** → QB deep-ball ceiling + stack pairing.
5. **OL/DL adjusted block-win** → DST trench + QB clean-pocket.
6. **PFF grades + coverage grades** (needs login) → quality prior (esp. rookies) + shadow-corner matchup.

Each is a season-level export (pullable the same way as the Man-vs-Zone data) except PROE/snap/route which also have weekly reports. After ingest, re-run `boom_pipeline.py` and `backtest_boom.py` as the gate.

---

# Comprehensive 3-source map (FantasyPoints + FTN + PFF)
*The user added FTN + PFF logins. Below is what each source uniquely adds, what's pullable, and how it folds in — gated by an overfit-safe validation so we only keep signals that actually predict booms.*

## FTN (For The Numbers) — unique adds
| Signal | What it is | Model status | Ceiling value |
|---|---|---|---|
| **DVOA** (team + DVOA-adj FP Against + DVP) | Aaron Schatz situational opponent-adjustment; the gold standard for matchup | ❌ (model uses raw points-allowed tiers) | **HIGH** — replaces/augments the matchup multiplier with a charted opponent adjustment |
| **Shadow Coverage Matrix + WR/CB Matchups** | how often a CB travels to shadow a specific WR, and where each lines up | ❌ (model is team-scheme only) | **HIGH** — the missing per-WR shadow suppressor |
| **Rookie Scouting Guide** (Ratcliffe) | rookie projections + scouting | ❌ | **HIGH** — directly answers rookie projection |
| **NFL Stats hub** (snaps, team targets, RZ, game logs) | snap counts + team target totals | ◑ partial | MED (overlaps FP snap share) |
| **Adjusted Line Yards** | OL responsibility for rush yards | ◑ (`ol_q`) | MED — sharper OL run-block |
| **Ratcliffe Projections** | a 2nd independent projection | ◑ (Clay only) | MED — consensus/divergence vs Clay |
| **DVOA Game Projections** | projected scores per game | ◑ (Vegas) | LOW-MED — environment cross-check |
| **Depth charts (all 32)** | projected role/starter | ◑ | LOW — role confirmation |

## PFF — unique adds (Premium Stats 2.0)
| Signal | What it is | Model status | Ceiling value |
|---|---|---|---|
| **Player grades** (recv/rush/pass-block/run-block/coverage, surroundings-independent) | charted *quality* score | ❌ | **HIGH** — stable talent prior; the single best lever for **rookies** (no NFL sample) |
| **Coverage grades per CB/S** (targets/cov snap, passer rating allowed, yards/cov snap) | how good each corner is | ❌ | **HIGH** — pairs with FTN shadow matrix → a *complete* shadow-corner ceiling suppressor |
| **OL pass/run block grades + pressures allowed** | charted blocking | ◑ (`pblock`) | MED — upgrades QB clean-pocket + DST trench |
| **Rookie grades + college production / draft capital** | pre-NFL profile | ❌ | **HIGH** — rookie projection |
| **Receiving detail** (separation, contested-catch%, drop%, YAC over exp) | charted receiving quality | ◑ (some in `chart2`) | MED |

## The combined high-value fills (cross-source)
1. **Opportunity** (snap% + route% — FP/FTN) → ceiling *floor*; rising-usage flag.
2. **Shadow corner** (FTN *who/how-often* × PFF *how-good*) → per-WR ceiling suppressor vs elite travelling CBs. The model has nothing here today.
3. **Rookies** (FTN scouting + PFF grades/draft capital + Clay baseline) → a real rookie projection instead of the thin prior they get now.
4. **Opponent adjustment** (FTN DVOA / DVOA-adj FP-against) → a charted matchup multiplier, better than raw tiers.
5. **Team pass tendency** (FP PROE) → pass-catcher/QB environment amplifier.
6. **Talent priors** (PFF grades) → stabilize base for low-sample players.

---

# Overfit-safe methodology (how each signal earns its place)
The user's directive — *"don't overfit; see what gives signal for each player, team, position"* — is the gate. For **every** candidate signal:

1. **Hold-out test, not in-sample fit.** Use the existing `backtest_boom.py` frame: define the signal on **2024**, test whether it improves boom prediction on **2025** (or leave-one-week-out). A feature that only helps in-sample is rejected.
2. **Marginal lift, per position.** Add the signal on top of the current model and measure the change in **AUC + calibration (Brier)** for predicting realized booms — **separately for QB/RB/WR/TE/DST**. Keep it only where it adds real lift; a signal can help WR and not RB.
3. **Shrink, don't stack.** New multipliers enter shrunk (the `SHRINK_LAMBDA` discipline that already fixed the over-sized matchup layer), so adding signals can't re-inflate the model.
4. **Collinearity check.** Drop signals that just re-encode something we have (e.g., FTN snaps vs FP snaps) — keep the cleaner one.
5. **Per-entity signal report.** For player / team / position, report which signals actually move its boom probability, so the value is transparent (not a black box of features).

## Execution order (staged; each gated by step 1–2 above)
Opportunity (snap/route) → PROE → DVOA opponent-adjust → Shadow-corner (FTN×PFF) → PFF talent grades (base prior, esp. rookies) → rookie model (FTN+PFF+Clay) → OL grades → separation/route-type detail.

> Reality note: this is a multi-pass build — each signal is a pull (now reliable since the browser was un-minimized) + an ingest + a validation gate. I'll work it in that order and keep only what the backtest says earns its place, reporting the per-position lift at each step so nothing gets added on faith.
