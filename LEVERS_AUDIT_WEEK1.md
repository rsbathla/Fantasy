# DFS Lever Audit — what the Week 1 model uses, and what it's missing

*Grounded scan of the scoring path (`dfs_model.py` / `edges_for` / `env_blend` / `game_sim` / `build_dfs_weekly_breakdown`) against the data assets actually on disk. "Have but unused" means the data exists in the repo (usually `boom/chart2yr.json` or `sis_value/`) but does not enter the weekly play score.*

## What the play score uses today

The weekly play score is `ceiling × (1 + matchup_edge/250) × (1 + (implied_total − 21)/60) × pass_run_conversion`, sitting on top of these levers:

- **Environment** — posted Vegas O/U anchored, blended with team ceiling (`env_blend`), down to an implied team total.
- **Matchup edge** — man / zone / deep coverage softness (`defense_splits`), frequency-weighted by how often the defense plays that coverage (C8), plus position fantasy-points-allowed (FPAA).
- **Coverage-scheme fit** — man/zone specialist vs the coverage the defense actually plays (added this session).
- **Game script** — the 40k-sim lead/trail/shootout distribution, feeding the PROE **pass/run conversion** (WR/TE up, RB down on pass-lean; RB amplified when the sim projects a lead).
- **Season constants** — team-ceiling tier, player ceiling/trait percentiles, board flags, target share (WR/TE), carry share (RB), vacated-opportunity index, coordinator scheme fit.
- **Housekeeping** — roster/availability flags, dome flag, correlation structure (for stacks).

That is a strong environment-and-matchup core. The gaps below are mostly **opportunity-quality** signals — the data is largely already in the repo, it just isn't wired into the weekly score.

---

## Tier 1 — high fantasy impact, data in hand, not scored

**1. Red-zone / TD equity.** Touchdowns are the highest-variance, highest-value fantasy events, and nothing in the play score references red-zone role. `boom/chart2yr.json` already carries `rz_tgt_rate`, `ez_tgt` (end-zone targets), and `i20_pg` (inside-the-20 opportunities per game) for every pass-catcher; goal-line carry share is derivable for backs. Two players with identical target shares can have very different ceilings if one owns the goal line. This is the single biggest missing lever. *Effort: low-medium (data exists; needs a per-player RZ index folded into the play score, like the conversion multiplier).* 

**2. Pace → neutral play volume.** This one is genuinely absent, not just unused. `offense_profile.json` has a qualitative `pace` label ("fast/avg/slow") but no plays-per-game estimate, and `team_volume_model.json` carries no pace/plays field. The environment lever is entirely **points-based** (implied total) — it never accounts for how many **snaps** produce those points. Two teams both implied for 27 differ materially if one runs ~68 neutral plays and the other ~58; that's ~15% more targets/carries to distribute. A neutral-pace plays estimate would scale raw opportunity independent of the total. *Effort: medium (need to build a plays-per-game model from 2024-25 tempo, then multiply opportunity).* 

**3. Air-yards share / downfield role.** The model uses "deep" coverage softness but not the player's own **air-yards share** (`ay_share`, the dominator metric) or `aDOT`, both present in `chart2yr`. Target share is volume; air-yards share is target *quality* — it separates a 25%-share possession slot from a 25%-share vertical alpha, who has the bigger spike week. *Effort: low (season-constant trait, applied weekly like ceiling).* 

---

## Tier 2 — medium impact, data mostly in hand

**4. Pass rush / pressure → passing game and checkdown funnel.** `pass_rush_pctl` exists in `defense_splits.units` but is only wired into the **QB** edge; `sis_value/pass_rush.csv` + `pass_defense.csv` hold player-level pressure data. Pressure matters two ways the model ignores: a QB facing a heavy rush loses ceiling (sacks, hurries), and a pressured offense **funnels to checkdowns** — RB receptions and TE outlets rise. Neither reaches WR/RB/TE scoring. *Effort: medium.* 

**5. Route participation / snap floor.** `tprr` (targets per route run) and `fp_rr` (fantasy points per route run) are in `chart2yr` but unused weekly. They are the **floor** under the ceiling — an efficient part-time player is riskier than a full-route-share grinder at the same target share. Worth surfacing as a floor/consistency flag. *Effort: low.* 

**6. Slot vs wide alignment matchup.** `slot_pct` / `wide_pct` (player) and the defense `funnels` block both exist, but alignment-specific matchup (a slot specialist vs a defense soft in the slot) isn't scored — only used lightly in the game notes. *Effort: medium.* 

---

## Tier 3 — low priority for Week 1 specifically

**7. Weather (wind/precip).** Only a dome flag is used; there is no wind/precip feed for 2026 games. Early-September weather is usually benign, so this is low-value for Week 1 — but it should be added before the late-season/playoff weeks where wind craters passing. *Effort: medium (needs a weather source at slate time).* 

**8. Individual CB / shadow matchups.** Team-level coverage softness misses a lockdown corner traveling with the WR1 (the classic "shadow" that erases an elite receiver in an otherwise soft secondary). No CB-level data exists in the repo. Real, but needs a new data source. *Effort: high.* 

**9. Rest / travel / short week.** The games file has rest days, but Week 1 has everyone equally rested and no travel history — near-zero variance. Matters later (Thursday games, cross-country trips), not now. *Effort: low, low wk1 value.* 

---

## Infrastructure gap (surfaced by the Chase issue)

**10. Freshness enforcement doesn't cover the DFS input chain.** The audit's `stale_deliverables()` check compares rendered boards against one tip (`flag_ranks.json`), but the DFS play score also depends on `defense_splits`, `game_sim`, and `proe_tendency_2026`. When `defense_splits` was rebuilt *after* the baseline, the report shipped stale coverage grades — Tee Higgins' man smash silently vanished and Chase's edges were off — and the audit did not flag it. The freshness check should compare each surface's outputs against **all** of that surface's declared input layers, not just the model tip. *Effort: low, high leverage — it prevents exactly the class of silent staleness we just hit.* 

---

## Recommendation

Build in this order: **(1) red-zone/TD equity** and **(2) pace→plays** are the two that most change *who you play* in Week 1, and both are largely data-in-hand. Pair them with the **freshness-enforcement fix (10)**, which is cheap and stops silent staleness. Air-yards share (3) is an easy add that sharpens the WR pecking order. Pressure/funnel (4) is the best Tier-2 follow-up. Weather and shadow corners can wait for in-season, when real slates and CB news exist.
