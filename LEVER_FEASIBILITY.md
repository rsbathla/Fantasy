# How many ceiling-levers can we honestly build from current data?

A **matchup lever** needs three things to be honest: a **player-side split** (with real sample), an
**opponent-side attribute** to activate it (so a matchup can "turn it on"), and a **mechanism** (not a
coincidence). Best case it's also **year-over-year stable**. Below is every dimension our data can touch,
measured — not assumed.

Stability caveat up front: the FantasyPoints split folders (`NFL-master/FP`) we hold are **2025-only**
(the 2024 split dirs are empty). So coverage / route / run-type / direction / QB splits have adequate
**sample** but are **not YoY-stability-verified**. Only **motion, slot/wide, red-zone, and division** have
two seasons and are stability-checkable. That gap is the single biggest honesty limit.

## Verdict table

| # | Lever (player split) | Player sample | Opponent activator (have?) | Seasons | Mechanism | Verdict |
|---|---|---|---|---|---|---|
| 1 | Man vs zone — WR | 254 WR/TE (≥60 rt/side) | ReceivingDef coverage + coord man-rate ✓ | 2025 | strong (man stable) | **BUILT** |
| 2 | QB handles/struggles vs man | 36 QB | PassingDef coverage + man-rate ✓ | 2025 | strong | **BUILT** |
| 3 | Slot vs boundary alignment | 136 WR/TE | slot funnel + CB1 grade ✓ | 2024-25 | strong (role-stable) | **BUILT** |
| 4 | Red-zone target hog | 381 | *defense RZ-allowed — MISSING* | 2024-25 | strong (TD equity) | **BUILT player-side; opp side partial** |
| 5 | Vertical / deep | have (explosive+deep) | PassingDef Deep-allowed ✓ | 2025 | medium | **BUILT** |
| 6 | Pass-catching back vs two-high | ~90 RB (rec≥40) | light-box / two-high looks ✓ | 2024-25 | strong | **BUILT** |
| 7 | Fewer ceilings in-division | 227 (≥8 div g) | schedule ✓ | 2024-25 | medium (familiarity) | **BUILT** |
| 8 | Shootout / pace environment | all (team) | opp pace + Vegas total ✓ | current | strong | **BUILT** |
| 9 | Motion weapon (in/out YPRR) | 325 | *not opponent-controllable* | 2024-25 | usage lever (stable) | **BUILT (usage, not matchup)** |
| 10 | RB run scheme: zone vs gap | 59 RB (≥20 att/side) | RushingDef RunType ✓ | 2025 | medium (scheme fit) | **BUILDABLE NOW** |
| 11 | QB deep vs short tilt | 39 QB | PassingDef Deep/Short ✓ | 2025 | medium | **BUILDABLE NOW** |
| 12 | RB rush direction: outside vs inside | 24 RB (thin) | RushingDef RushDirection ✓ | 2025 | medium | **BUILDABLE (thin coverage)** |
| 13 | WR route family (vert/inter/quick win) | 276 WR | ReceivingDef RouteType ✓ | 2025 | weak/collinear w/ YPRR | **MARGINAL** |
| — | Contested-catch reliance | have | — | — | does NOT persist (our backtest) | SKIP (noise) |
| — | Single-high / two-high split | have (dim) | shell rate | — | barely persists (our backtest) | SKIP as standalone (tendency only) |
| — | QB under pressure | rate-faced only | — | — | no produced-under-pressure split in data | SKIP (need export) |
| — | RB box count (light/stacked) | none | — | — | no per-player box data | SKIP (no data) |
| — | Home / away | per-game | — | 2024-25 | no stable YoY signal found | SKIP (data = noise) |

## Honest count
- **Built and live: 9 levers** (#1–9 above; #4 is player-side only on the opponent activator).
- **Buildable now with current data: ~3 more** (#10 RB zone/gap, #11 QB deep/short, #12 RB direction — thin), plus #13 route-family if we decide its marginal value is worth it.
- **So: ~12 honest levers** total (9 live + ~3 ready), in two confidence tiers (2-season-stable: motion, slot, red-zone, division; 2025-sample-only: man/zone, QB-man, vertical, run-scheme, QB-deep, direction).
- **4 explicitly rejected** with data/mechanism reasons (contested, box-count, QB-pressure, home/away).

## What would expand the honest set (data we'd need)
1. **2024 FantasyPoints split folders** (CoverageType/RouteType/RunType for 2024) → makes coverage/route/run/QB levers **YoY-stability-verified**, promoting them from Tier-2 to Tier-1.
2. **Defense red-zone-allowed** (EZ/i20 targets & TDs allowed per defense) → completes the opponent activator for the red-zone lever (#4).
3. **QB pressure-split export** (produced clean vs under pressure) → unlocks the pressure lever (124 tweet mentions).

## Recommendation
Build the matchup overlay on the **9 live + 3 ready = 12 levers** now (opponent activators exist for all but
red-zone's defense side). Tag each lever's confidence (2-season-stable vs 2025-sample) on the card so a stacked
"levers in this matchup" count is honest about which legs are firm vs suggestive.

---

## UPDATE — 2024 FantasyPoints splits PULLED (programmatically) + YoY-verified

The 2024 gap noted above is now closed for the coverage lever. The FantasyPoints **"Receiving Man vs. Zone"**
report (man / zone / single-high / two-high YPRR, TPRR, FP/RR per player) was pulled **programmatically**
for **both 2024 (381 players) and 2025 (376)** via the Data Suite API
(`POST /v2/ds/nfl/tools/player/receiving-man-vs-zone/values`, the page's own auth). Lever-eligible 2-yr data
(≥40 man & ≥40 zone routes BOTH years, 121 WR/TE) saved to `boom/fp_manzone_2yr.csv` (checksum-verified).

### The verification result (this CHALLENGES our prior assumption)
Year-over-year correlation (2024 → 2025), n = 121:

| signal | YoY r |
|---|---|
| Overall YPRR | **0.59** |
| Man YPRR | 0.47 |
| Zone YPRR | 0.48 |
| **Man − Zone delta** (the lever signal) | **0.18** (0.27 at ≥60-route floor) |
| Single-high YPRR | 0.53 |
| Two-high YPRR | 0.42 |

**Conclusion:** a player's man-vs-zone *differential* — exactly what "man-beater / zone-beater" rests on —
**barely persists** (r≈0.18). Man & zone efficiency individually persist only moderately (~0.47–0.50) and
mostly because *good players are good vs both* (overall r=0.59 > either split). So the prior label
"man-coverage skill persists (solid, Tier-1)" was **too generous** — a single-season man/zone lean is largely
noise. The coverage split is a **tendency, not a Tier-1 lever.**

### What we did about it (honest fix, not a deletion)
`build_manzone_2yr.py` → `boom/manzone_2yr.json`: route-weighted 2-yr blend + a **consistency flag**
(same-direction meaningful lean in BOTH seasons). Of 121 players, **only 41 (34%) have a consistent lean**
(12 man-beaters, 29 zone-beaters); the other 80 single-year "leans" were noise. The dossier coverage lever now:
- **2-yr consistent man-beater → SOLID** ("wins vs man", e.g. A.J. Brown, CeeDee Lamb, Pickens, JSN, McConkey, Sutton, Jameson Williams).
- 2-yr consistent zone-beater → tendency (common trait; e.g. Chase, Kittle, McLaurin).
- 2-yr **mixed → no coverage lever at all** (Waddle, etc. — removed as noise).
- Players with only 2025 data → single-year "lean", tendency.

Net: the coverage lever is now **YoY-honest** — promoted to solid ONLY for the dozen players whose man edge held
across two seasons, demoted/removed for everyone whose split was a one-year artifact.
