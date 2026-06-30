# Model Assumptions Audit — affirm every assumption against real 2026 data
Triggered by a real error (SEA mislabeled "continuity" when its play-caller departed). Principle: nothing
about the 2026 world is assumed; it is either VERIFIED against real data, a transparent MODELING CHOICE
(a parameter, not a fact), or explicitly FLAGGED as a known limitation. **Updated this pass:** OL proxy and
injury availability moved from FLAGGED → VERIFIED/APPLIED; schedule spot-checked; a unified flags layer added.

## A. FACTUAL inputs about the 2026 world

| Input | Source | Status | Notes / action |
|---|---|---|---|
| Player → team (rosters) | fusion_table.csv | **VERIFIED** | 5 parallel web agents (June 2026, cited) checked ~60 top skill players. Highly accurate. Fix: **Brandon Aiyuk** removed (non-usable). A.J. Brown→NE CONFIRMED a real trade (NOT an error). |
| Free agents (unsigned) | roster_flags_2026.json | **VERIFIED** | Diggs, Deebo, Hill, Chubb, Waller all genuinely unsigned as of June 2026 (re-confirmed, cited). Correctly excluded. |
| Injury / availability | roster_flags_2026.json `availability` | **VERIFIED + APPLIED** | 6 players (Charbonnet, Kittle, Nabers, Dell, Kraft, Brooks) verified with cited June-2026 reporting; availability multiplier = (17−games_missed_mid)/17 now haircuts projections. All 6 project healthy by playoffs (W15-17). |
| 2026 play-caller + scheme | scheme_2026.json | **VERIFIED** | Parallel agents, cited. SEA corrected (Fleury). Continuity = the actual play-caller stayed (KC/GB/JAX/BUF/CHI/DAL/NO). 18 genuine scheme-change offenses. |
| DC scheme / coverage shells | scheme_2026.json + research | **VERIFIED** | BAL = Minter's 2025 LAC scheme (80.7% zone→man−1, 49.6% two-high→+1). All 13 new-DC shells from researched lean. |
| Coordinator man-rate | coordinator_scheme_2026 + research | **VERIFIED/REFINED** | blend-prior for known DCs; CLE/MIA higher-man, LAC/WAS lower (research) not blind regress. |
| **Offensive line (2026)** | **boom/oline_2026.json** | **VERIFIED (NEW)** | Web-verified 1-5 tier for all 32 (Sharp 2026 + 4for4 + PFN, cited). **Replaces the broken fusion oline_pctl** (had DET at 6.6 pctl — clearly wrong; only 13 distinct values/32 teams). Gates the deep/vertical lever. |
| 2026 schedule (weekly opp) | boom/schedule2026.json | **VERIFIED (structure + spot-check)** | 32 teams, 17 games + bye, 0 asymmetric. Spot-checked KC/PHI/DET/BUF W1/bye/W15/W16/W17 vs Pro-Football-Reference — **all match exactly**. |
| Defense unit strength (cov/rush/run) | defense.json | **MODELED (2026)** | snap-weighted PAA over projected 2026 roster; movers carry rate, rookies via draft-round prior. |
| FP man/zone/sep/route/rush splits | FantasyPoints 2024+2025 API | **VERIFIED (real)** | pulled programmatically from the live FP Data Suite. |
| Win totals / implied env | web_teams.json (2026) | **VERIFIED (real)** | sourced 2026 win totals. |
| Projections / ADP | Clay + merged_rankings_2026 | **EXTERNAL (real)** | third-party 2026 projections (ADP already prices some risk — flags are an overlay, see note). |

## B. MODELING CHOICES (parameters — not facts; tunable, with rationale)
- Lever tier weights: solid = 1.0, tendency = 0.5 (confidence weighting; tendency = YoY r ~0.3-0.5).
- Activation threshold ACT_MIN = 0.5 ; SMASH week >= 1.5.
- YoY stability tiers / lever sample floors — backed by MEASURED year-over-year r (FP_LEVER_AUDIT_2YR.md).
- DC shell directional push = 50% toward (league mean ± 1 SD) in the researched direction.
- Man-rate research nudge = ±4 pts for new-DC teams with a researched man lean.
- OL tier→pctl map {5:90,4:72,3:50,2:34,1:10}; deep lever suppressed if tier 1 (≤30), rewarded if tier 4-5 (≥70).
- **Flags layer params** (flags_2026.json): PO_SLATE_TOUGH=64 / HARD=72 (mean opp W15-17 unit pctl), OL_TIER_WEAK≤2, PO_COLD ratio 0.6.
- **Availability is the ONLY flag that haircuts a projection** (data-backed games-missed). Scheme/OL/playoff-slate flags are surfaced as RISK COUNTS, not point haircuts — we do not invent magnitudes for them.

## C. FLAGGED — residual limitations (NOT silently trusted)
1. **Tackling-allowed is 2025-only** (boom/defense_tackling.json). YoY persistence unverified; only drives the tendency-tier elusive-RB lever; new-DC teams are conf-regressed. Low stakes — accepted as a single-year input.
2. **Returning-DC coverage shells = 2025 actuals** carried to 2026 (~19 retained DCs). Reasonable (same coordinator) but it is their 2025 tendency, not a 2026 guarantee.
3. **Rookie defensive contribution** in defense.json = draft-round prior curves (modeled, not observed). Inherent for rookies.
4. **Schedule** structurally verified + 4-team spot-check passed; not every one of 272 games cross-checked. (Spot-check found zero errors, so confidence is high.)
5. **Unsigned FAs / unresolved transactions** (Hill, Diggs, Deebo, Chubb, Waller; Aiyuk) can sign in July/Aug camps — re-verify roster_flags_2026.json close to draft.

## D. Resolved this pass (was assumption → now verified/fixed/applied)
- OL proxy (broken fusion oline_pctl, DET=6.6) → **VERIFIED 2026 tiers** (boom/oline_2026.json), wired into build_dossier.
- Injuries recorded-but-not-applied → **availability multipliers applied** to projections + surfaced as flags (cited).
- Schedule "not spot-checked" → **4 teams' W1/bye/W15-17 verified vs PFR, all exact**.
- Added a **unified flags layer** (build_flags_layer.py → flags_2026.json): total + playoff flag counts on every player, surfaced in the dossier and the rankings board (see FLAGS_LAYER.md).
- (Prior pass) SEA continuity error, BAL/Minter, blanket→directional scheme, blanket→researched DC shells, A.J. Brown verified correct, Aiyuk non-usable.
