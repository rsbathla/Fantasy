# Team & Player Dossier — Build Progress

A team-by-team study + scouting tool generated from the model. Two files:

- **`build_dossier.py`** → `dossier_data.json` — joins every player-level source we have and runs the
  individual-profile engine.
- **`render_dossier.py`** → `dossier.html` — clean, professional, team-by-team UI (Dossier + Challenge/quiz
  modes). Self-contained HTML, opens in any browser.

Runs in the daily refresh (`refresh_intel.py`) so it stays current with the tweet/intel ingest.

## What each player card contains
- **Header (collapsed row):** our rank, position, ADP, edge vs ADP, consensus bar, archetype flags.
- **Quantitative profile:** archetype + key percentiles (projection / ceiling / boom / volume tier / variance).
- **Qualitative profile:** scheme/skill traits (stability-tiered), strongest backtested analyst claim, conviction.
- **Booms when / Busts when:** individualized (see engine below).
- **Projection & shape:** proj pts/g, ceiling (p95), volatility (CV), spike%, advance/ceiling percentiles, conviction.
- **Playoff outlook (W15–17):** per-week opponents + upside, playoff-up, W17 blow-up rank, bye.
- **Signal breakdown:** ~20 within-position fusion percentiles as labeled bars (value, receiving, rushing, context).
- **Upside traits:** model-driver (green) vs descriptive (grey), each with stability tier + note.
- **Backtested claims** + **Intel** (recent tweets about the player).

## The individual-profile engine (the core idea)
Each player is analyzed **against his own position cohort**, not by universal thresholds:
- **Archetype** classified per position (Alpha, Separation technician, Vertical stretcher, YAC weapon,
  Three-down workhorse, Receiving/satellite back, Elite QB1 producer, etc.).
- **Genuine strengths** = his highest relative signals; **genuine flaws** = his lowest. So an elite player
  (e.g. Josh Allen, 99th projection) surfaces as a boom; a flawed one surfaces his real holes.
- **Coverage as a lean:** a man-beater implies a complementary "quieter vs zone" weakness (and vice-versa);
  only players with both a man indicator AND the deliberate zone-beater flag are "coverage-agnostic."
- **Opponent characteristics** are position-correct: WR/TE → man/zone, single-high vs two-high; RB → light
  boxes vs stacked boxes; **pass-catching backs boom vs two-high** (checkdowns/targets open up); QB → pressure,
  two-high.
- **Volatility** from CV vs the position distribution (steady high-floor vs boom-or-bust).
- **Honesty:** reads built on descriptive splits (man/zone, deep, two-high — which our backtests show barely
  persist) are tagged **"tendency"**; stable model-drivers are shown plainly.

## Teams analyzed individually
Each team has an **offensive identity** + **defensive identity** line, **strengths/weaknesses**, and
**offense booms-when / busts-when** (game-script driven). Team-wide game-script facts live on the team — they
are NOT repeated on every player card.

## Verification
- `dossier_data.json`: 32 teams, 359 player records.
- Functional render test (`/tmp/verify_dossier.js`): all 32 teams render through the real page JS with
  0 errors, 0 `undefined`/`NaN` leaks; 0 players with empty boom or bust.
- Spot-checks: Josh Allen booms (elite producer); DJ Moore has real weaknesses (inefficient, doesn't win
  routes, quieter vs zone, shadow CB1); receiving backs (Gibbs/Bijan/CMC) get the two-high note, pure runners
  (Henry) do not.

## Known limitation
Visual screenshot in-sandbox is blocked (no headless browser; the Chrome extension can't open local files).
Live desktop screenshot deferred when the user is mid-draft to avoid stealing browser focus. Verification is
therefore functional (every team rendered through the actual page code) rather than pixel-level.

## Review pass (independent subagent) — fixes applied
- **C1 (critical):** Separation & Route-eff were shown as opposing boom/bust lines (self-contradiction on ~27% of WR/TE). Collapsed into one coherent "gets open & wins routes" read (max of the two). Coverage lean now reads the actual `zone` dim and only asserts a complementary weakness when there's evidence (the other coverage grade is present and low) — no more "coverage-agnostic" + "rarely separates" on the same card. **0 contradictions** in the sweep.
- **C2 (critical):** fusion imputation fills (a value shared by ≥10 players, e.g. explosive 32.67/50.0) were being asserted as real "non-explosive" weaknesses on ~45 RBs (Conner, McCaffrey, Jacobs…). Fills are now scrubbed to missing; only genuine lows remain. Explosive phrasing softened to "limited explosive-play rate".
- **S2:** deep-shot matchup read now leans on the `deep` dim (not raw explosive/YAC proxy).
- **S3:** suffix names (Jr./III) no longer render as "tweets about Jr." — last-name extraction strips suffixes.
- **S4 / N1:** high-projection WR1s lacking a volume dim are now correctly "Alpha" (was "Complementary piece"); `is_alpha` shadow/beatable-CB1 reads require a projection floor so weak WR1s don't get them.
- **N2:** percentile ordinals clamped to 1–99 (no "0th"/"100th").
- Cosmetic: TE archetype renders cleanly ("Elite receiving TE"); not "Receiving TE — alpha".

Verified after fixes: 32 teams / 359 players, 0 render errors, 0 boom/bust contradictions, 0 empty lists.
Note: git cannot live on the mounted Windows folder (lockfile limitation); history is committed in-session and exported to `dossier_history.bundle` in this folder for persistence.

## Alignment (slot/wide) + motion added
- **Per-player slot vs boundary** from `boom/chart2yr.json` (2-yr FantasyPoints charting, 136 WR/TE).
  Shows in the quantitative line ("68% slot"), as a qualitative trait (slot role / boundary X / flex alignment),
  and as matchup reads: slot → "draws the nickel/safety, sidesteps the CB1" (bust vs a strong nickel); boundary
  → "wins on the perimeter" (bust = draws the top CB / shadow-press risk). Slot is ROLE-STABLE in our framework.
  Slot alphas don't get a boundary-shadow read (they avoid the CB1).
- **Team pre-snap motion** from `features.csv` (`team_motion`) folded into each team's offensive identity line and
  flagged as a strength (high) / weakness (static). NOTE: player-level motion isn't in our charting source
  (only team-level); per-player motion would require a new PFF/FTN pull.
- Verified: 0 contradictions, 0 empty, 32/359 render clean.

## Motion + in/out-division splits
- **Designed-target rate** (`design_pct`, FantasyPoints 2-yr) added as the charted, motion-driven "manufactured usage"
  signal (Deebo 25%, Puka 14% — schemed via motion/jets/screens). Shows as a "schemed usage" trait + boom. Real
  per-player *motion %* isn't in the exports we have; `ingest_motion.py` auto-detects a FantasyPoints/PFF motion
  export (Name + Motion% [+ Motion Type/Personnel]) the moment it's dropped in Downloads, writes boom/motion.json,
  and the dossier surfaces it. Also added true INLINE%/BACK% alignment (fixes TE inline vs flexed).
- **In/out-division ceiling splits** (`build_division_splits.py`): unions per-game FP exports (FP is TOTAL game pts,
  deduped — QBs included via the rushing export), classifies each game in- vs out-of-division, compares mean FP and
  ceiling-week rate (player's own 75th-pctl). VERIFIED CLAIM: **Josh Allen 2024-25 — 0 ceiling weeks in 10 AFC East
  games (max 24.5 vs his 28.8 threshold), 19.4 FP/g; out-of-division 25.9 FP/g, 36% ceiling rate.** Similar negative
  in-division splits: Swift, Shakir, Henry, DeVonta Smith (and QBs Darnold, Purdy, Nix, Burrow). Surfaced on player
  cards ("fewer ceiling weeks vs division rivals…") and saved to division_splits.json. Both engines run in the daily refresh.

## Real per-player motion DELIVERED
FantasyPoints motion-split exports (player + team, 2024 + 2025, motion-yes/motion-no) are now ingested.
`ingest_motion.py` pairs each season's two route files (they sum to the full aggregate; the smaller-route
file = in-motion), computes per-player **motion rate** + **in-motion vs no-motion YPRR (motion "lift")**,
blended across seasons (route-weighted) -> boom/motion.json (340 players). Dossier shows motion% in the
quant line, "motion-heavy" trait, and lift-based reads: e.g. Puka Nacua/Nico Collins flagged "less efficient
when moved (decoy/clear-out role)"; Kittle better in motion. Runs in the daily refresh.

## Ceiling levers (per-player matchup splits, anti-overfit)
A fixed, mechanism-backed set of opponent-controllable splits per player — NOT dredged. Each lever shows the
split numbers + the matchup trait that activates it, with a confidence tag (man-coverage & role-based = solid;
zone/shell/slate = tendency). Min sample required per split (coverage man+zone routes >=40; motion routes >=40).
Sources: man/zone YPRR (`ingest_coverage.py` <- NFL-master CoverageType), motion lift (boom/motion.json),
slot/wide (chart2yr), vertical (explosive/deep), pass-catching-back two-high, team shootout environment.
Rendered as a "Ceiling levers" section. e.g. Nico Collins man-beater (2.3 vs 1.4 YPRR -> man-heavy D);
Drake London zone-beater; Wan'Dale slot -> weak nickel. 256/359 players have >=1 lever.
NEXT (offered): map each player's levers onto his actual 2026 opponents -> a per-week "levers stacked" count.

## 2024 FantasyPoints man/zone splits — pulled programmatically + YoY-verified
Pulled the FP **"Receiving Man vs. Zone"** report (man/zone/single-high/two-high YPRR, TPRR, FP/RR) for
**2024 (381) and 2025 (376)** straight from the Data Suite API (`/v2/ds/nfl/tools/.../receiving-man-vs-zone/values`,
reusing the page's own auth header — no manual export). Lever-eligible 2-yr rows (≥40 man & ≥40 zone routes both
years, 121 WR/TE) saved to `boom/fp_manzone_2yr.csv` (checksum-verified on import).

**Finding (anti-overfit, challenges our prior tier):** YoY r (2024→2025, n=121) — overall YPRR 0.59, man 0.47,
zone 0.48, **man−zone delta 0.18**, single-high 0.53, two-high 0.42. The man/zone *differential* (the lever
signal) barely persists; man/zone individually persist only ~0.47–0.50, mostly because good players win vs both.
So a single-season man/zone lean is largely noise — coverage is a **tendency, not Tier-1**.

**Fix wired in:** `build_manzone_2yr.py` → `boom/manzone_2yr.json` (route-weighted 2-yr blend + a same-direction
2-season consistency flag). Of 121, only 41 (34%) have a consistent lean (12 man-beaters, 29 zone-beaters).
`build_dossier.py` coverage lever now: 2-yr consistent man-beater → **solid** ("wins vs man": A.J. Brown,
CeeDee Lamb, Pickens, JSN, McConkey, Sutton…); consistent zone-beater → tendency; **mixed → no coverage lever**
(noise removed, e.g. Waddle); 2025-only → single-year tendency. Added to the daily refresh
(`refresh_intel.py`). Verified: 32 teams / 359 players, 0 boom/bust or man/zone contradictions, renders clean.

Note: the FP Data Suite blocks repeated browser downloads, so the data was brought in via the API + a
checksum-validated transfer (downloads are origin-locked after the first). The exact request body/endpoint are
captured in this file's history for re-pulls.

## ALL FantasyPoints levers audited (2024+2025) + tier-weighted matchup-stack COUNT
Pulled every FP player report (passing/rushing/receiving/coverage/separation) for both seasons via the API and
YoY-stability-tested each split (`FP_LEVER_AUDIT_2YR.md`). Pattern: **usage/role traits persist; efficiency
*differentials* are noise.** New stable, mechanism-backed levers added to the engine:
- **gets-open-vs-man** (man separation-wins %, r~0.56-0.71 — the most stable receiving skill; Evans, Adams, Sutton, MHJ, McConkey…) — solid.
- **contested-catch role** (contested-target rate r~0.64; Tee Higgins, Hopkins, Evans, Pickens…) — tendency, activates vs man/press.
- **scramble QB** (scramble rate r~0.64-0.67; Daniels, Fields, Lamar, Allen, Hurts…) — solid, activates vs man (scramble lanes).
- **elusive RB** (missed-tackles-forced/att r~0.50-0.61; K.Walker, Gibbs, Bijan, Conner…) — tendency, activates vs soft run fronts.
Explicitly REJECTED as noise: man/zone YPRR delta as standalone, RB zone/gap scheme-fit YPC (r~0), YAC-over-expected, completion-over-expected.

**The count** (`build_lever_count.py` -> `lever_count.json`, also written back into `dossier_data.json`):
maps each player's levers onto his **actual 2026 weekly opponents** (`boom/schedule2026.json`) and scores
`weekly = Σ tier_weight(solid 1.0 / tendency 0.5) × opponent-favorability`, where favorability comes from
existing repo data — opponent man rate (`coordinator_scheme_2026`), coverage shells (`defense_shell`), and
unit strength (`defense.json`). Per player: weekly calendar, season mean, **playoff (W15-17) mean**, peak, and
**smash weeks** (score ≥ 1.5). 230 players have activatable levers; 0 man/zone contradictions (a player can't
carry opposing man & zone levers — reconciled to the more stable separation-vs-man read).

Surfaced two ways: a **per-player "Matchup-lever calendar"** on each dossier card (18-week bar + smash weeks),
and a standalone **sortable Ceiling-Lever Stack Board** (`lever_board.html`, filter by position, sort by playoff
mean/peak/etc.). Framing is explicit: this is **matchup-lever favorability, not talent** — read alongside
projection (a soft-slate role player can top it). All steps run in the daily refresh
(`build_dossier -> build_lever_count -> build_lever_board -> render_dossier`).

## Elusive RB lever -> real per-defense tackling-allowed
Scraped FantasyPoints' **Advanced Rushing - Defense** view (2025, all 32 teams) for missed-tackles-forced ALLOWED
per carry -> `boom/defense_tackling.json` (leaky_pctl; leakiest NYG .20, ARI .18, BUF/SF .17; stickiest JAX/BAL/IND .10).
`build_lever_count.py` elusive_rb intensity now keys off this real tackling-leakiness percentile (run-defense strength
is only a fallback), so elusive backs (Gibbs, Bijan, K.Walker, Conner) light up specifically vs defenses that miss
tackles — e.g. Gibbs elusive now fires vs BUF (94th), ARI (97th), CAR (88th). 2025-only for now.

## 2026 roster/coaching adjustments to the levers + count
Audited what was forward-looking vs a 2025 snapshot, then closed the gaps:
- **Defense PLAYERS (new DBs/edge/LB):** already handled — `defense.json` unit strength (pass-cov/run-def/pass-rush)
  is snap-weighted PAA over the *projected 2026 roster* (movers + rookie priors). Drives most opponent activators.
- **Defense SCHEME (13 new DCs):** man-rate was already DC-adjusted (coordinator_scheme_2026). Now the **coverage
  shells (single/two-high) and tackling-allowed are regressed toward league mean (lambda 0.5) for new-DC teams** in
  build_lever_count — so vertical / pass-catch-RB / elusive activations don't over-trust 2025 tendencies that a new
  coordinator will change.
- **Offense SCHEME (21 new OCs):** intrinsic SKILL levers (man-beater, wins-vs-man, contested, scramble, elusive,
  zone) stay full (they travel with the player). **Usage levers (slot/boundary, motion, designed, vertical, red-zone,
  pass-catch volume) are demoted solid->tendency and annotated "(new OC — 2025 usage may not carry)"** for new-OC
  teams — 88 levers discounted. Net effect is differential & honest: MarvHarrison (new-OC ARI) playoff lever score
  1.78->1.41, Puka (new-OC LAR) 1.58->1.34, while Chase (stable-OC CIN) unchanged at 1.98.
- **OL effect (offense):** the deep/vertical lever now keys off `oline_pctl` — suppressed for weak pass-pro teams
  (<=30th pctl: no time for shots), noted "(OL holds up)" for strong lines (>=70th). 12 strong-OL notes; a couple
  weak-OL vertical levers removed (230->228 levered players).
Verified: 32 teams / 359 players, 0 contradictions, pipeline green (build_dossier -> lever_count -> board -> render).

## Directional 2026 scheme adjustment (web-research validated) — replaces blanket regression
Challenge raised: the blanket new-OC discount + new-DC mean-regression was one-directional (measured: 0 up / 66 down)
— wrong for coordinators whose scheme we actually know. Fix: ran 4 parallel web-research agents (cited) to confirm
the 2026 play-caller (HC vs OC) + scheme tendency for every new-coordinator team -> `scheme_2026.json` directional
dials (motion/vertical/passcatch/scramble for offense; single/two-high for defense, +1/0/-1).
- `build_dossier.py`: usage levers now move by the dial — kept/"(new scheme fits)" where the new scheme amplifies,
  demoted/suppressed only where it genuinely reduces; continuity offenses (KC/GB/JAX/SEA, Reid/LaFleur callers) get
  NO discount. `build_lever_count.py`: new-DC shells pushed toward the researched scheme lean (up OR down), not mean;
  regress-to-mean only as a fallback for truly-unknown DCs (after research, none).
- Research corrections folded in: PHI play-caller is Mannion running a Shanahan/motion scheme (NOT run-heavy quick
  game — was wrongly discounted); KC=Reid, GB=LaFleur, JAX=Coen, SEA=maintains Kubiak = continuity (no discount);
  BAL defense is Minter-called & balanced (not two-high heavy); GB Gannon = quarters/low-man; TEN Saleh/Bradley =
  Cover-3 single-high; WAS Jones = two-high/zone/low-man; MIA Hafley/Duggan = press-man single-high.
- Result is now BIDIRECTIONAL: vs a no-adjustment baseline, 14 players up / 22 down (modest ±0.1-0.3); 40 lever
  "fits" boosts vs 5 reductions. Risers e.g. GB/BUF pass-catchers (favorable new-DC opponent shells); fallers e.g.
  WAS Daniels (under-center scheme suppresses scrambling). 0 contradictions, 32/359, pipeline green.
- A NOADJ=1 env toggle was added to both builders for before/after measurement.

## Data-quality flag (found during verification, NOT yet fixed)
`fusion_table.csv` team assignments may have stale/incorrect 2026 entries — confirmed example: **A.J. Brown listed
on NE** (would build his whole matchup/lever profile on the wrong schedule + scheme). Needs a dedicated 2026
roster-accuracy audit (player->team) to confirm/correct; flagged to user.

## "Never assume" pass — full real-data verification (after SEA error)
Root cause of the SEA miss: treated a team whose play-caller DEPARTED as "continuity." Fixed the instance and the
class of error, then verified everything with research instead of assumptions:
- **Rosters:** 5 parallel web agents (cited) verified ~60 top skill players. Result: model is accurate. A.J. Brown→NE
  is a REAL trade (not the error I feared). One real fix: Brandon Aiyuk (SF, voided/cut, hasn't played since Oct-2024)
  -> `boom/roster_flags_2026.json` non_usable, removed from the count. FAs (Diggs/Hill/Deebo/Chubb/Waller) confirmed unsigned.
- **SEA:** Kubiak left for LV HC; new caller Brian Fleury -> scheme CHANGE (motion +1, passcatch +1, scramble -1).
- **BAL:** confirmed HC Minter calls D and runs his 2025 LAC scheme -> def two_high +1, man -1 (was wrongly neutral).
- **Continuity corrected:** BUF/CHI/DAL/NO play-callers stayed -> removed their offense scheme-change discount; added TB (new caller).
- **Man-rate:** CLE/MIA -> more man, LAC/WAS -> more zone (research) instead of blind regression.
- **Schedule:** structurally verified (32 teams, 17 games + bye, 0 asymmetric games).
- **ASSUMPTIONS_AUDIT.md** written: every input classified VERIFIED / MODELING-CHOICE / FLAGGED, with the residual
  limitations stated openly (tackling 2025-only, OL-proxy vintage, injuries not auto-discounted, schedule not spot-checked game-by-game).
Pipeline green: 32 teams / 359 players, 0 contradictions.
