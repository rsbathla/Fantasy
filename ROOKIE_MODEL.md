# Rookie Model — all-position college-ceiling prior (2026)

Forward-looking ceiling model for the 2026 rookie class, built from SIS College Football
**Value** data, **validated** against 2025 NFL rookie outcomes, and wired in as a shrunk prior.

## Data (staged, content-verified — toggles had scrambled the filenames)
`sis_value/cfb/` — SIS CFB Value exports:
- `cfb_receiving_value_{2024,2025}.csv` (WR/TE), `cfb_rushing_value_{2024,2025}.csv` (RB),
  `cfb_passing_value_{2024,2025}.csv` (QB), `cfb_passdef_value_{2024,2025}.csv` (DB),
  plus bonus `cfb_passrush_value_2025.csv`, `cfb_rundef_value_2025.csv`.
- 2025 college = the 2026 class's final season (forward input); 2024 college = backtest input.

## Pipeline (pure CSV/JSON — no parquet/pyarrow)
1. `build_rookie_profiles.py` -> `boom/rookie_college_profile.json`
   All-position college Value profiles (2024+2025). Per player: Points Earned, EPA, Boom%,
   and a within-position **ceiling percentile** (mean of the three metric percentiles).
   Primary position: QB<-passing, WR/TE<-receiving Pos, RB<-rushing. Applies the **draft-
   eligibility filter** by intersecting the 2025 set with `analysis/merged_rankings_2026.csv`
   (board **ADP = draft-capital proxy**), which drops underclassmen + small-school noise.
2. `backtest_rookie.py` -> `boom/rookie_backtest.json`
   Validates 2024 college ceiling -> 2025 NFL rookie boom. Outcome from `boom/base2yr.json`
   (a 2025 rookie = `g24==0 & g25>0`; boom rate = `b25/g25`, min 4 NFL games).
3. `build_rookie_prior.py` -> `boom/rookie_prior.json` (+ merges `boom_prior` into the profile)
   Calibrates a boom prior from the backtest slope, **shrinks** it (0.5) and clamps to
   [0.04, 0.25], then prices every 2026 draft-eligible rookie by their 2025 ceiling.
4. `build_rookie_db_funnel.py` -> `boom/rookie_db_grades.json`
   2025 college pass-defense coverage grades for incoming rookie DBs (WR-funnel input).

## Backtest result (it VALIDATES)
Skill (WR/TE/RB), n=31: **spearman +0.30, AUC 0.62**, top-tertile college-ceiling rookies
boomed **2.2x** the bottom tertile (0.150 vs 0.069). A real but noisy signal — correct to use
as a **prior, not a projection**. Caveats: small sample; QB n=3 (its prior borrows the skill
calibration and is lower-confidence); college ceiling is one input, not destiny (some high-
ceiling rookies bust, some low-ceiling hit).

## Integration hook (wire the prior into the base model)
Rookies have no 2-year NFL history, so `boom_lib.reg_base()` returns `None` (ungradeable) and
falls back to a flat position default. Replace that fallback with the validated prior:

```python
# boom_lib.reg_base(v, posbase, K): after the base_blended / 2025-shrinkage checks, before "return None"
if v.get('rookie_boom_prior') is not None:
    return float(v['rookie_boom_prior'])   # validated college-ceiling prior for 2026 rookies
```
Supply `rookie_boom_prior` by merging `boom/rookie_prior.json` into the statmenu in
`boom_foundation.py` (key by normalized name). Then the flag builders price rookies off their
college ceiling instead of a flat default — high-ceiling rookies (Jeremiyah Love, Carnell Tate,
Makai Lemon) carry a higher base boom rate than low-ceiling ones.

## Funnel (rookie-aware WR matchup) — ready, one input short
`rookie_db_grades.json` grades incoming rookie corners from 2025 college coverage. To finish the
WR-funnel adjustment (a starting rookie CB tightens his team's pass funnel) we need the **2026
defensive-draft mapping (rookie DB -> NFL team)**, which best-ball boards omit. The grades are
ready to apply the moment that mapping is supplied.

## Refresh
Re-pull the SIS CFB Value files into `sis_value/cfb/`, then:
`python3 build_rookie_profiles.py && python3 backtest_rookie.py && python3 build_rookie_prior.py && python3 build_rookie_db_funnel.py`

## APPLIED — prior is LIVE (2026-06-23)
Wired into the model, not just documented:
- **Blend** (`apply_rookie_to_statmenu.py`): each rookie's `base_blended` = 0.65*projection +
  0.35*college_prior (W=0.35). Tempers hot rookie projections toward validated rates
  (Jeremiyah Love 0.218->0.186, J'Mari Taylor 0.331->0.251) and nudges modest ones up
  (Makai Lemon 0.114->0.117). 46 rookies boosted. Original saved as `base_blended_preboost`
  (fully reversible; idempotent on re-run).
- **Safety hook** (`boom_lib.reg_base`): returns `rookie_boom_prior` for any base-less rookie.
- **DAG**: 4 stages added to `boom_pipeline.py` (build_rookie_profiles -> build_rookie_prior ->
  build_rookie_db_funnel -> apply_rookie_to_statmenu), after cover_spec, before the flag builders.
- **Tune**: edit `W` in apply_rookie_to_statmenu.py.  **Revert**: restore `base_blended` from
  `base_blended_preboost`.  **Propagate to flags + dashboards**: `python3 boom_pipeline.py`
  (needs pyarrow — your machine has it; couldn't run in the build sandbox).

## Weight W — now TESTED (2026-06-23)
`woptimize_rookie.py` grid-searched W against a real 2025 preseason baseline (FantasyPros 2025
best-ball ADP, staged at `sis_value/fp_adp_2025.csv`), scoring `(1-W)*ADP + W*college` against
the 30 rookies' actual 2025 NFL boom:
- ADP alone (W=0): spearman **0.517** — the market is the dominant rookie signal.
- College alone (W=1): **0.287** — real but weaker.
- Best blend: **W=0.15 (rho 0.534)** — small marginal lift; curve flat 0->0.2 then declines.
- Bootstrap optimal-W: median 0.15, IQR [0.15,0.45] (low, not tightly pinned).

**W lowered 0.35 -> 0.15.** Takeaway: college efficiency is largely redundant with ADP for
rookies (ADP already encodes production + draft capital); it adds only a marginal edge, so it
gets a small weight. Caveat: optimized vs ADP, which proxies the model's `base_proj` (Clay) but
isn't identical; n=30.
