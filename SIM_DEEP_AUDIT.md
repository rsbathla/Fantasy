# SIM_DEEP_AUDIT.md — Monte Carlo / Simulation Subsystem, Line-by-Line
*Scope: `pipeline/sim_prod.py`, `pipeline/survival_chain.py`, `game_sim.py`, `engine/bbengine.py`,
`dfs_model.py`, `dfs_scenarios.py`, plus `pipeline/player_sim_distributions.csv` and `game_sim.json`.
Audited 2026-07-05 against the project objective: the sim must deliver defensible CEILING (p95/boom)
and CORRELATION (stack) signals. Every numeric claim below was re-derived from raw source in this
session; the two headline re-derivations are in §3.*

---

## §1 · Findings table

| # | Issue | Sev | Where | Evidence (re-derived this session) | Why it dents the edge |
|---|-------|-----|-------|-----------------------------------|----------------------|
| F1 | **QB rush-TD Poisson drawn ONCE per batch, not per sim.** `rng.poisson(scalar_lam)` with no `size=n` returns a single integer that is added to ALL 12,000 sims; Clay-mean calibration then rescales the whole array, so the mean is right but the SHAPE is corrupted: within-batch QB rush-TD variance is zero, and the whole distribution is compressed or stretched depending on which scalar happened to be drawn. | **P0** | `pipeline/sim_prod.py:43` (`qrtd=rng.poisson(np.clip(qcar*q['rush_td_rate'],0,None))`) | Demonstrated: `rng.poisson(0.706)` → scalar. Shipped CSV reproduced exactly (seed 3, max diff 0.0000 over 379 players), then rebuilt with the one-token fix (`,n`): **Joe Burrow shipped p95 = 29.8 vs true 37.0 (−7.2 DK pts, −19%); spike% 0.074 vs 0.150 (halved). Jalen Hurts −3.7, Bo Nix −4.3, Daniel Jones −4.2, Josh Allen +1.6. 8 of 32 QBs off by ≥1.0 pt.** Across seeds, bugged Allen p95 ranges 33.8–41.6 (7.7-pt lottery); fixed sim is stable to ±0.1–0.8. | This is THE ceiling signal for THE stack position. Burrow — the board's premier stack QB — ships with a falsely crushed ceiling and halved boom rate. Blast radius: `player_sim_distributions.csv` → `features.csv` p95/cv (`build_features.py:11`) → `dfs_model.py:261` play score + `dfs_scenarios.py` lognormal P(ceiling) via corrupted `cv` (Burrow cv 0.318 shipped vs ~0.45 true) → `engine/playoff_overlay.py:152` within-QB p95 rank → `playoff_up` → `decision_tree.py` late-round tilt → `bbengine.load_board().ceiling_p95`. Live grading is hit too: in `gen_weeks` one scalar spans all NS×nW sims *and all weeks*, so rushing-QB weekly boom variance is deleted from title-equity math. The bug was invisible to the existing correlation validation because a constant offset + linear rescale leaves Pearson r unchanged. |
| F2 | **DK 3-pt yardage bonuses absent from sim scoring** (100+ rec yds, 100+ rush yds, 300+ pass yds). Skill DK = `rec + yds*0.1 + TD*6`; QB DK = `yds*0.04 + TD*4 − INT + rush`. Calibration to Clay means spreads any bonus EV uniformly instead of concentrating it in the tail. | **P1** | `pipeline/sim_prod.py:22,37,44` (no bonus term anywhere; grep confirms) | Re-derived from the model's own yardage components: Ja'Marr Chase P(100+ rec yds)=24.1% overall but **100% in his top-5% (p95) region**; CIN QB P(300+ pass yds)=26.5% overall, 100% in tail. True DK p95 for elite yardage profiles is ~+3 pts above simulated (net ~+2–2.5 after mean absorption). | The product being sold is p95. Understating every elite yardage player's tail by ~2–3 DK pts, non-uniformly (yardage-spike archetypes hurt most vs TD-dependent ones), directly distorts cross-archetype ceiling ordering — the exact comparison best-ball/DFS leverage lives on. |
| F3 | **UD platform never reaches the sim, and the documented remedy crashes.** `sim_prod.py` calibrates to `BB_PROJ_COL` (default `dk_pg`); nothing in the run path (`draft.py`, `engine/run_live.py`, `bb_grade.py`) ever sets it. Worse: `UD_BBM_WINNER_STRATEGY.md` §4 instructs `BB_PROJ_COL=ud_pg`, but `build_layer2.py` never writes a `ud_pg` column into `layer2_player_params.csv`. | **P1** | `pipeline/sim_prod.py:4`; `pipeline/build_layer2.py:65` (`'dk_pg':r['dk_pg']` only); `draft.py:69` (sets `BB_PLATFORM` only) | Executed: `BB_PROJ_COL=ud_pg` → **KeyError: 'ud_pg'**. So UD grades always run full-PPR DK distributions with UD cut rates (`survival_chain.py:14-17`) — the "UD scoring never reaches the sim" note in `GOALS_AUDIT.md:23` is confirmed still open, and its published fix is impossible as written. | UD BBM is explicitly a target format (per-pod, ceiling-heavy cuts are already platform-aware). Full-PPR shapes inflate possession pass-catchers' means/ceilings relative to half-PPR truth, so every UD title-share number is tilted toward the wrong archetype. |
| F4 | **Stale honesty note in shipped `game_sim.json`**: `_meta.built_note` says "dispersion/correlation … = stated priors, not backtested" while SIGMA_TEAM/RHO_BASE are in fact backtest-earned (and verify — see §3-A). Docstring lines 18–22 carry the same stale claim. | **P2** | `game_sim.py:195` (hardcoded string) vs `game_sim.py:33-40` (earned constants) | §3-A: 1,424 nflverse games reproduce sd(margin)=12.65, sd(total)=13.07, ρ=0.033 exactly from `data/nflverse/games_2021_2025.csv`. `PRODUCTION_ARCHITECTURE.md:251` already records the earned status. | C6/C7-class hazard in reverse: a future session reading the artifact's own meta will treat earned parameters as guesses and feel licensed to re-derive or "fix" them. Provenance strings must match the registry of what's earned. |
| F5 | **Player-sim correlation is flat in the game total.** The shared game shock loading is a constant (`SG=0.31`) for every game; the backtest itself (`pipeline/correlation_structure.json`) says bring-back r is total-dependent: 0.062 low-total vs 0.159 high-total (median 45). `game_sim.py` models ρ(total) correctly at the *team-score* level, but the *player-level* sim that prices stacks (survival_chain W15–17, title equity) gives the same ~0.10–0.12 bring-back everywhere. | **P2** (proposal, not defect — magnitude sits between the two buckets) | `pipeline/sim_prod.py:3` (constant `SG`); `pipeline/survival_chain.py:23-26` (same `g` to both teams, no Vegas input anywhere in the player sim) | §3-B: shared-shock bring-back re-derived at 0.103–0.117 vs backtest all-games 0.129; control with independent shocks = 0.000. | A W17 anchor stack in a 53-total game and one in a 39-total game get identical player-level co-movement credit; the market's stack pricing does distinguish them. Fixing this (SG as a function of the posted W15–17 totals) would sharpen exactly the correlation edge the project claims. Needs the backtest gate before wiring (C3). |
| F6 | **Per-QB INT rate ignored** — `qint=rng.poisson(0.65,n)` hardcodes a league-average INT/game for every QB while `layer2_player_params.csv` carries a per-QB `int_rate` column (built and unread). | **P2** | `pipeline/sim_prod.py:42`; unused input at `pipeline/build_layer2.py:69` | Josh Allen's own params imply 29.94 att × 0.0236 = 0.706 INT/g vs the flat 0.65. Spread across QBs is roughly 0.4–1.0. | Flattens a real floor/ceiling differentiator between careful and turnover-prone QBs (−1/INT on DK). Small per-game, but it is a built layer going unconsumed (C1 pattern). |
| F7 | **Reception volume excluded from the game-environment shock.** Targets co-move only with the team shock (`np.exp(0.3*ST*teamz)`, `sim_prod.py:20`) — the shared game shock `Gz` drives yards and TDs but not receptions. Also missing its `−0.5σ²` mean correction (+0.3% bias, absorbed by calibration). | **P2** | `pipeline/sim_prod.py:20` | Code inspection; corr targets still verify at the pair level (§3-B) because yards+TDs dominate the co-movement. | PPR reception points are the floor-ier share of a possession receiver's DK score, so their exclusion from the game shock slightly under-correlates possession-profile stacks relative to deep-threat stacks. Second-order today; worth folding into any F5 rework. |
| F8 | **Survival independence & fixed-bar approximations** in title equity: `title = padv × s15 × s16 × w17` with each survival measured against a pooled fixed percentile bar of the *full* field, not the survivor-conditioned field, and with no same-week field co-movement (opponents' rosters share real games with yours). Code itself flags "relative ranking robust to these". | **P2** (acknowledged in-code) | `pipeline/survival_chain.py:11-17,73-78` | Conditional-independence across weeks is actually valid given iid weekly draws; the field-composition and shared-game effects are the real approximations. | Overstates absolute survival for everyone (W16 bar in reality comes from a 50% better field); mostly cancels in relative ranking, which is what the chain is used for. Keep documented, don't burn backtest budget here first. |
| F9 | Dead code + cosmetic: `survival_chain.py:69-71` — `res=[]` never used; a loop computes `field=np.concatenate(...)` then discards it (immediately superseded by the `fields` dict). | **P2** | `pipeline/survival_chain.py:69-71` | Read of source. | None functionally; costs a redundant concatenate per call and misleads readers into thinking per-week logic lives there. |
| F10 | `game_sim.sim_game` reads only team a's Vegas row; if team a lacks a row but b has one, the game is silently dropped (returns None). Currently moot — 272/272 games present (§3 checks) — but a single missing row would vanish a game with no warning. | **P2** | `game_sim.py:98-100` | `game_sim.json` re-tallied: 272 games / 18 weeks, full slate. | A silently missing game would remove its stacks/scripts from DFS surfaces with no alarm — an untested-guard-shaped hole (C2 family). |

**Explicitly checked and clean** (so nobody re-audits from scratch):
- **Distribution well-formedness**: shipped CSV has 0 NaN in any column, 0 negative means/p95, 0 cases of p95<p50; low-usage players (130 with mean<3) have non-degenerate, non-zero-inflated shapes; extreme CVs (max 6.1) belong to sub-1-point bench names that `dfs_model` floors out (`proj<4` skip).
- **Monte Carlo tail stability at N=12,000**: p95 seed-to-seed range 0.1–0.8 DK pts for QBs (post-fix) and 0.1–0.7 for WR/RB/TE — the sim count is adequate for a stable p95 once F1 is fixed. `game_sim`'s 40k/game is ample.
- **Determinism/reproducibility**: `sim_prod` (seed 3) reproduces the shipped CSV bit-for-bit (max |Δp95| = 0.0000, 379 players); `survival_chain.chain` seeds rng(11) per call (win_delta's common-random-numbers design is correct); `game_sim` seed 20260703, stable iteration order.
- **Vegas anchoring (C5/C7)**: `game_sim` means come from posted implied totals in the registry-anchored `weekly-vegas-lines.csv`; it invents no totals. Gamma-marginal side effect (sim median_total < posted total, over_vegas ≈ 47.5%) **matches reality**, not a bug: nflverse residuals show mean +0.52 / median −0.50 / skew +0.35 / P(actual>close) = 0.480. Mean-anchoring with right skew is the empirically correct shape.
- **games_by_week.json W17 pairs**: 16/16 consistent with the posted Vegas lines file (independent source) — the anchor-game layer under stack decisions is right.
- **ρ wiring**: shipped `game_sim.json` rho spans 0.003–0.065 and correlates 1.000 with the posted total by construction; spot game (DAL/NYG, 50.5) = 0.055 = 0.033 + 0.04·(5.5/10) exactly.
- **C9 (ADP≠DFS)**: zero ADP references in `dfs_model.py` and `dfs_scenarios.py`. ADP appears only in best-ball surfaces (`bbengine.load_board`), where it is the correct domain.
- **script_mult discipline**: the mis-signed stated-prior script tilt was backtest-caught and zeroed (`K_SCRIPT_*=0.0`, `dfs_model.py:45-52`) with plumbing retained and the validated PROE conversion in its place; `_rb_lead_amp` is the one live game_sim→player-scoring feed and its lead-amplification is the direction the interaction probe supports.
- **bbengine consumption**: `grade()` is a faithful chain() wrapper (asserted to 1e-9 in `engine/test_bbengine.py:105`); `canon()` name recovery closes the silent-exclusion hole; `ceiling_p95` flows from the sim CSV as documented. The engine consumes the sim correctly — it is consuming *corrupted QB inputs* (F1), not misusing them.

---

## §2 · The two headline re-derived numeric checks

### A. Is RHO/SIGMA really backtest-earned from nflverse, as `game_sim.py:33-40` claims?
Re-derived from raw `data/nflverse/games_2021_2025.csv` (this session, no intermediate layers):

```
games with scores + closing lines:  1,424        (claim: 1,424)  ✓
sd(margin − closing spread)      =  12.65        (claim: 12.65)  ✓
sd(total  − closing total)       =  13.07        (claim: 13.07)  ✓
corr(home resid, away resid)     =  0.033        (claim: 0.033)  ✓
implied per-team sigma           =  9.10         (SIGMA_TEAM 9.1) ✓
rho by total bucket: <45 → 0.007 ; 46+ → 0.076   (claim "~0 low, 0.06–0.09 at 46+") ✓
```
Verdict: **RHO/SIGMA are genuinely earned and correctly applied** in `game_sim.py`. The only defect is the stale honesty string shipped inside `game_sim.json` (F4).

### B. Does the player sim actually produce the claimed stack correlations?
Re-derived by running `gen_team` directly (40k sims), against the backtested targets in
`pipeline/correlation_structure.json`:

```
teammate (own game shock):
  CIN Burrow × Chase      r = 0.344   (target qb_wr1  0.351)  ✓
  CIN Burrow × Higgins    r = 0.321   (target qb_wr2  0.339)  ✓
  CIN Chase  × Higgins    r = 0.006   (target wr1_wr2 0.042)  ✓ same ≈0 regime
bring-back (shared game shock, survival_chain.gen_weeks mechanism):
  Burrow × opp WR1 (PIT)  r = 0.103–0.117  (target all-games 0.129) ✓ sane sign+size
  control, independent shocks: r = 0.000   → the shared shock IS the mechanism
same-team QB–RB sanity: Purdy×CMC 0.203, Hurts×Barkley 0.093 — small positive, correct direction
```
Verdict: **teammate and game-environment correlation are real, directionally correct, and calibrated
to the earned structure** — with the one structural gap that the loading is total-invariant (F5).

---

## §3 · Does the sim serve the objective? (verdict)

**Architecture: yes. Shipped ceiling numbers: not yet — one line of code is poisoning the QB tail.**

The two signals the project exists to price are handled with real care: correlation is implemented
as a shared per-game lognormal shock, tuned to and verifying against a backtested correlation
structure (§2-B), and the game-script layer is genuinely Vegas-anchored with dispersion/ρ earned
from 1,424 real games (§2-A) — including the subtle over/under skew, which the gamma marginals get
*right*. Reproducibility is exact, the distribution table is well-formed, and 12k sims is enough
for a stable p95. The consumption chain (bbengine → survival chain → win deltas; features → DFS)
uses the sim for exactly what it is good at.

But the ceiling half of the edge is currently shipping corrupted at its most leveraged point: the
one-token F1 bug makes every QB's p95/cv/spike a function of a single Poisson draw, and the worst
casualty is the premier stack QB on the board (Burrow p95 −19%, boom rate halved) — an error that
propagates into best-ball ceiling ranks, playoff overlay, DFS play scores, and title equity, and
that the existing validation could not see because correlation checks are invariant to it. Add the
missing DK yardage bonuses (F2) and the sim systematically understates precisely the right-tail
region that top-heavy formats pay. Fix F1 (mechanical), decide F2/F3 (owner semantics), and the
subsystem is a defensible ceiling+correlation machine rather than one that is right about
correlation and quietly wrong about ceilings.

---

## §4 · Decision points (owner calls — returned, not resolved)

1. **D1 — Fix F1 and rebuild the chain.** The fix is one token (`rng.poisson(lam, n)` at
   `sim_prod.py:43`), but it changes shipped numbers repo-wide: `player_sim_distributions.csv` →
   `build_features.py` → `features.csv/json` → `playoff_overlay.csv` → dfs surfaces → any cached
   board/tree. Recommendation: apply immediately, rebuild via `run_all.py`, re-run
   `integration_audit.py --strict`, and add a machine check that fails when any per-batch QB
   rush-TD array has zero within-batch variance (the removal test: revert the token, watch it fire).
2. **D2 — DK 3-pt yardage/300-yd bonuses in sim scoring (F2).** Semantics change to the scoring
   function; must stay DK-only (UD has no such bonuses), which couples it to D3. Recommendation:
   add platform-conditional bonus terms; gate the effect size by re-checking p95 movement is ~+2–3
   for elite yardage profiles and ~0 for low-volume players.
3. **D3 — Repair the UD path (F3).** Options: (a) `build_layer2.py` also writes `ud_pg` and
   `draft.py`/`run_live.py` derive `BB_PROJ_COL` from `BB_PLATFORM`; (b) keep DK-only and delete
   the UD instructions from `UD_BBM_WINNER_STRATEGY.md`. Recommendation: (a) — the strategy doc
   already promises it.
4. **D4 — Correct the stale `built_note` in `game_sim.py:195` (F4)** to state which parameters are
   earned (SIGMA_TEAM, RHO_BASE/SLOPE vs nflverse 2021-25) and which remain stated priors (K_CEIL,
   SPREAD_SHRINK ramp shape, script shifts), then rebuild `game_sim.json`. Trivial, high
   provenance value.
5. **D5 — Total-dependent shared-shock loading (F5, proposal only).** Make `SG` a bounded function
   of the posted game total in `gen_weeks` (W15–17 totals exist in the registry file), targeted at
   reproducing the 0.062→0.159 bring-back gradient. Requires the C3 gate (backtest vs the earned
   correlation structure) before wiring; do not change semantics without it.
6. **D6 — Consume `int_rate` (F6)**: swap the flat 0.65 for `pass_att_pg × int_rate` per QB.
   Mechanical and mean-preserving in aggregate, but it is a scoring-input change → flagging rather
   than applying.
