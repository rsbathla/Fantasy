# Defensive Profile + Funnel System — with player-movement tracking
*A two-layer defensive map for tracking 2026. **Team layer** = the funnels each defense currently presents (opponent-adjusted, FTN DVOA). **Player layer** = the individual defenders (shadow corners first) who CAUSE those funnels, so a trade/injury can be re-projected. June 2026.*

## How to read funnels
A *funnel* is a defense that's tough one way and soft another, pushing production to the soft spot. Values are opponent-adjusted fantasy points **above average** allowed to each slot (FTN DVOA-Adjusted FP-Against, 2025): positive = soft (target it), negative = tough (fade it). `WR1/WR2/slot` is the alignment funnel — a defense soft vs slot but tough on the boundary funnels targets inside.

## Team funnels (the actionable map)

| Def | QB | RB | WR | TE | WR1 | WR2 | slot | funnel read |
|---|---|---|---|---|---|---|---|---|
| ARI | -0.3 | +3.6 | -2.5 | +3.3 | -0.1 | -0.6 | -1.8 | RUN funnel; TE funnel |
| ATL | +0.1 | -0.1 | +2.8 | -4.2 | +1.2 | +0.9 | +0.7 | TE fortress |
| BAL | +0.0 | +1.6 | +5.5 | -1.7 | +4.5 | -1.7 | +2.8 | WR1 funnel |
| BUF | -2.3 | +4.1 | -4.1 | -5.6 | -0.4 | -1.3 | -2.4 | RUN funnel; TE fortress; WR fortress |
| CAR | -1.6 | +1.8 | -1.9 | -0.8 | +2.5 | -2.7 | -1.7 | RUN funnel; WR1 funnel |
| CHI | +0.9 | -1.6 | +2.9 | +0.0 | +2.4 | +2.3 | -1.8 | PASS funnel; OUTSIDE funnel |
| CIN | +2.7 | +6.7 | -6.3 | +8.3 | -3.6 | -2.3 | -0.4 | RUN funnel; TE funnel; WR fortress |
| CLE | -2.8 | -1.3 | -5.3 | -2.3 | -2.2 | -2.6 | -0.4 | WR fortress |
| DAL | +8.1 | +3.1 | +9.5 | -0.4 | +4.2 | +1.6 | +3.7 | PASS funnel; WR1 funnel |
| DEN | -1.1 | -3.9 | -1.0 | +1.5 | -4.0 | -0.1 | +3.1 | SLOT funnel |
| DET | +1.7 | -2.1 | +4.9 | -0.3 | +0.8 | +0.7 | +3.4 | PASS funnel; SLOT funnel |
| GB | -1.5 | -3.1 | +0.9 | -0.8 | +0.8 | +0.1 | +0.1 | — |
| HOU | -5.2 | -2.7 | -5.8 | -1.2 | -3.4 | +0.0 | -2.4 | WR fortress |
| IND | +0.0 | -0.8 | +6.2 | +2.7 | -2.6 | +5.0 | +3.8 | PASS funnel; TE funnel |
| JAX | +0.9 | -2.9 | +3.2 | +2.1 | +2.9 | +0.3 | +0.0 | PASS funnel; WR1 funnel |
| KC | -1.4 | -2.9 | -2.1 | -2.0 | -1.5 | -0.1 | -0.4 | — |
| LAC | -3.6 | -2.6 | -4.0 | -2.2 | +0.8 | -2.0 | -2.8 | WR fortress |
| LAR | -1.1 | -3.5 | +2.2 | -1.6 | +2.5 | -0.5 | +0.2 | WR1 funnel |
| LV | -0.3 | +2.1 | +3.4 | -2.9 | -1.2 | +0.6 | +4.0 | SLOT funnel |
| MIA | +1.8 | +0.7 | -1.7 | +3.6 | -0.3 | -1.3 | -0.1 | TE funnel |
| MIN | -4.6 | -2.1 | -8.3 | -1.2 | -3.7 | -1.0 | -3.6 | WR fortress |
| NE | +0.5 | -2.7 | -0.3 | +1.1 | +0.5 | -0.9 | +0.0 | PASS funnel |
| NO | -2.5 | -0.9 | -3.8 | -1.4 | -2.3 | -0.9 | -0.6 | — |
| NYG | +2.5 | +4.9 | +3.0 | -2.3 | +2.1 | +1.4 | -0.5 | RUN funnel |
| NYJ | +3.0 | +3.0 | -0.3 | +0.4 | +2.4 | -0.1 | -2.6 | OUTSIDE funnel |
| PHI | -3.6 | +0.5 | -4.8 | -4.7 | -4.5 | +2.8 | -3.1 | RUN funnel; TE fortress; WR fortress |
| PIT | +2.2 | -2.6 | +3.5 | +3.2 | +0.7 | +0.4 | +2.4 | PASS funnel; TE funnel |
| SEA | -1.6 | -2.9 | -3.1 | +2.7 | -2.1 | -1.0 | +0.0 | TE funnel |
| SF | +1.0 | +1.3 | +2.2 | +1.9 | -1.0 | +2.0 | +1.1 | — |
| TB | +3.5 | +0.7 | +0.1 | +2.2 | +1.3 | -2.0 | +0.9 | — |
| TEN | +1.9 | +1.6 | +2.1 | +0.0 | +3.3 | -0.2 | -1.0 | WR1 funnel |
| WAS | +2.8 | +2.9 | +3.1 | +2.1 | +0.3 | +3.3 | -0.5 | — |

## Player layer — shadow corners (the movement-sensitive nodes)
These corners *travel* with the opponent's top WR. They are why a defense is a WR1-fortress — and the first thing to re-check when rosters move. **Rule: if a shadow corner changes teams, his old team's WR1 shifts fortress→funnel and his new team's tightens.** Coverage grade seeded from FTN shadow results (2025 sample); enrich with PFF per-CB coverage grade for stable quality.

| Corner | Team | Cover% | Yds/Tgt allowed | Grade | Movement impact |
|---|---|---|---|---|---|
| A.J. Terrell | ATL | 53.3% | 5.0 | shutdown | if he leaves ATL, that WR1 opens |
| Christian Benford | BUF | 65.6% | 2.0 | tight | if he leaves BUF, that WR1 opens |
| Tre'Davious White | BUF | 56.7% | 6.5 | tight | if he leaves BUF, that WR1 opens |
| DJ Turner II | CIN | 55.3% | 0.0 | shutdown | if he leaves CIN, that WR1 opens |
| Greg Newsome II | CLE | 46.4% | 9.8 | beatable | if he leaves CLE, that WR1 opens |
| Pat Surtain II | DEN | 74.7% | 7.5 | tight | if he leaves DEN, that WR1 opens |
| D.J. Reed | DET | 70.6% | 6.1 | tight | if he leaves DET, that WR1 opens |
| Derek Stingley Jr. | HOU | 77.5% | 4.0 | shutdown | if he leaves HOU, that WR1 opens |
| Kamari Lassiter | HOU | 64.6% | 30.5 | beatable | if he leaves HOU, that WR1 opens |
| Charvarius Ward | IND | 61.5% | 5.3 | tight | if he leaves IND, that WR1 opens |
| Xavien Howard | IND | 54.1% | 9.4 | beatable | if he leaves IND, that WR1 opens |
| Sauce Gardner | NYJ | 74.6% | 4.1 | shutdown | if he leaves NYJ, that WR1 opens |
| Quinyon Mitchell | PHI | 69.5% | 5.3 | shutdown | if he leaves PHI, that WR1 opens |
| L'Jarius Sneed | TEN | 55.8% | 14.8 | beatable | if he leaves TEN, that WR1 opens |

## How it feeds the boom model
- **Funnels sharpen the matchup switch** (which the defensive switch-test sized per position: QB strong, TE moderate, WR small, RB off). A WR facing a *pass-funnel* defense gets the WR matchup nudge; a WR facing a *WR-fortress* gets faded — and the WR1/slot split routes that nudge to the right *alignment* (a slot WR vs a slot-funnel, not the boundary).
- **The player layer keeps it honest in 2026.** Funnels are downstream of personnel. When a shadow corner or pass-rusher moves, re-assign him and the team funnel re-derives — so the map tracks the season instead of going stale.

## Completion (next pulls)
1. **PFF per-CB coverage grades** (outside vs slot) → stable defender quality + the full slot/boundary funnel.
2. **Full FTN shadow CSV** (729 rows) → every shadow corner + season aggregates.
3. **PFF pass-rush + run-defense grades** → edge/front-seven movers (the other funnel cause).
4. Wire `defensive_profile.json` funnels into the per-week WR/TE alignment matchup nudge; ship a live 2026 funnel dashboard.
---

# Player layer v2 — per-CB PFF coverage grades (the funnel *cause*, move-aware)
*PFF 2025 coverage grade per corner, with the **team column on current rosters** — so a corner who changed teams already sits with his new club. The team's WR1 funnel is driven by its CB1 coverage grade; reassign a corner and `funnel_projection_2026.json` re-derives. Seeded with the top-50 CBs (CB1 for ~27 teams); CB depth (pages 2–3), safeties and edge rushers complete it.*

## Best & worst CB1s (drive the WR1 funnel)

| Team | CB1 | Cov grade | Tier | 2026 WR1 outlook |
|---|---|---|---|---|
| MIN | James Pierre | 88.9 | shutdown | fortress |
| CAR | Mike Jackson | 85.8 | shutdown | fortress |
| SEA | Devon Witherspoon | 83.6 | shutdown | fortress |
| PHI | Quinyon Mitchell | 80.2 | shutdown | fortress |
| DEN | Ja'Quan McMillian | 78.9 | shutdown | fortress |
| CIN | DJ Turner II | 78.1 | shutdown | fortress |
| GB | Benjamin St-Juste | 77.8 | above-avg | tight |
| IND | Charvarius Ward | 77.4 | above-avg | tight |
| BAL | Chidobe Awuzie | 77.2 | above-avg | tight |
| HOU | Kamari Lassiter | 77.0 | above-avg | tight |
| NE | Christian Gonzalez | 76.9 | above-avg | tight |
| PIT | Joey Porter Jr. | 76.6 | above-avg | tight |
| KC | Nohl Williams | 75.6 | above-avg | tight |
| LV | Eric Stokes | 75.2 | above-avg | tight |
| LAR | Trent McDuffie | 74.7 | above-avg | tight |
| JAX | Jarrian Jones | 74.5 | above-avg | tight |
| LAC | Donte Jackson | 73.4 | above-avg | tight |
| MIA | Rasul Douglas | 72.6 | above-avg | tight |
| DET | Roger McCreary | 72.0 | above-avg | tight |
| NO | Kool-Aid McKinstry | 71.4 | above-avg | tight |
| BUF | Tre'Davious White | 68.2 | average | exploitable |
| TEN | Cor'Dale Flott | 68.1 | average | exploitable |
| CLE | Tyson Campbell | 65.7 | average | exploitable |
| TB | Jacob Parrish | 65.7 | average | exploitable |
| DAL | Cobie Durant | 65.1 | average | exploitable |
| NYJ | Nahshon Wright | 64.8 | average | exploitable |
| CHI | Tyrique Stevenson | 62.3 | beatable | exploitable |

## 2026 funnel WATCH — where outcome and talent disagree (regression candidates)
When 2025's allowed production (DVOA) and the corner's grade disagree, the funnel is likely to move toward the talent in 2026:

- **CAR**: WATCH: elite CB1 but soft WR1 in 2025 -> WR1 likely REGRESSES tougher in 2026 — CB1 Mike Jackson (85.8), 2025 WR1 +2.5
- **CLE**: WATCH: weak CB1 but tough WR1 in 2025 -> WR1 likely REGRESSES softer in 2026 — CB1 Tyson Campbell (65.7), 2025 WR1 -2.2
- **HOU**: WATCH: weak CB1 but tough WR1 in 2025 -> WR1 likely REGRESSES softer in 2026 — CB1 Kamari Lassiter (77.0), 2025 WR1 -3.4
- **IND**: WATCH: weak CB1 but tough WR1 in 2025 -> WR1 likely REGRESSES softer in 2026 — CB1 Charvarius Ward (77.4), 2025 WR1 -2.6
- **NO**: WATCH: weak CB1 but tough WR1 in 2025 -> WR1 likely REGRESSES softer in 2026 — CB1 Kool-Aid McKinstry (71.4), 2025 WR1 -2.3

## Rookies tagged in the defender data
The CB grades carry college + draft year, so the 2025 defensive rookies surface automatically: Nohl Williams (Cal), Jacob Parrish (Kansas St), Marcus Harris (Cal), Maxwell Hairston (Kentucky). For **offensive** rookie projection (WR/RB/TE/QB ceiling), the next pull is PFF college receiving/rushing grades + SIS college data (SIS tab not open — needs opening).


---
## 2026 roster adjustments (see ROSTER_ADJUSTMENTS_2026.md)
Defense funnels are now **move-aware**: `reweight_defense_2026.py` reassigns ~72 sourced 2026 moves -> `defense.json` `*_2026` pctls, bridged to the boom matchup engine via `sync_boom_defense.py` (wired before `boom_foundation`). Coverage examples 2025->2026: KC 60.9->20.3, NYJ 1.6->32.8, BUF 54.7->82.8, CLE pass-rush 92.2->67.2.
