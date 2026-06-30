# DraftKings Best Ball Mania 2026 - GAME PLAN

*Module C of the toolkit. Ceiling-first. Built for the tournament shape: top-2 of 12 advance the W1-14 grind, then W15/16/17 playoff gates into a top-heavy W17 final. Everything below is graded on **upside (p95 / spike / advance%)**, not mean projection. Philosophy: **model fusion** - show what each signal says, don't overfit.*

- Players scored: **306** of 371 on the board (deep depth with no ceiling signal excluded from tiers).
- Alpha-ceiling threshold: **p95 >= 33**.
- ceiling_score = 0.50*z(p95) + 0.25*z(spike) + 0.25*z(adv%) - z **within position**.
- W17 bring-back r: **0.159** when the finals game is a shootout (combined team TD/g >= 4.53), else **0.129**. QB-WR1 r = **0.351**.

## 1. Ceiling-First Draft Priority

Tiers are **ADP bands** (a tier = an ADP range worth prioritising for ceiling), ordered **within the band by ceiling_score** so the spike outcomes float to the top. `VALUE` = board model rank beats the market (fell to you); `REACH` = market is paying ahead of the model.

### Tier 1 - ADP 1-11 (R1 anchors) - 11 players

| Ceiling rank | Player | Pos | Team | ADP | p95 | adv% | ceil_score | Flags |
|---:|---|:--:|:--:|---:|---:|---:|---:|---|
| 1 | Puka Nacua | WR | LAR | 3.9 | 49.8 | 100% | 1.578 | CONSENSUS STUD, POLARIZING |
| 2 | Ja'Marr Chase | WR | CIN | 3.1 | 46.7 | 99% | 1.45 | CONSENSUS STUD, POLARIZING |
| 3 | Jaxon Smith-Njigba | WR | SEA | 5.4 | 46.6 | 99% | 1.434 | POLARIZING |
| 4 | Amon-Ra St. Brown | WR | DET | 7.2 | 44.9 | 98% | 1.35 | POLARIZING |
| 5 | Bijan Robinson | RB | ATL | 2.1 | 46.0 | 98% | 1.333 | CONSENSUS STUD, POLARIZING, RB-ZONE-SCHEME |
| 6 | Jahmyr Gibbs | RB | DET | 1.2 | 45.7 | 100% | 1.332 | CONSENSUS STUD, POLARIZING, FLOOR RISK, RB-ZONE-SCHEME |
| 7 | CeeDee Lamb | WR | DAL | 10.4 | 42.5 | 97% | 1.306 | POLARIZING |
| 8 | Justin Jefferson | WR | MIN | 9.0 | 41.2 | 96% | 1.216 | POLARIZING, FLOOR RISK |
| 9 | Christian McCaffrey | RB | SF | 6.3 | 43.9 | 99% | 1.214 | POLARIZING, EFFICIENCY TRAP |
| 10 | Jonathan Taylor | RB | IND | 8.4 | 40.4 | 96% | 1.094 | POLARIZING, RB-GAP-SCHEME |
| 11 | James Cook III | RB | BUF | 11.1 | 37.4 | 94% | 0.972 | POLARIZING |

### Tier 2 - ADP 12-23 (R2) - 11 players

| Ceiling rank | Player | Pos | Team | ADP | p95 | adv% | ceil_score | Flags |
|---:|---|:--:|:--:|---:|---:|---:|---:|---|
| 1 | Brock Bowers | TE | LV | 20.0 | 34.1 | 98% | 1.24 | POLARIZING, EMPTY CALORIES, FLOOR RISK, ZONE-BEATER |
| 2 | De'Von Achane | RB | MIA | 19.1 | 40.3 | 95% | 1.114 | POLARIZING |
| 3 | Drake London | WR | ATL | 17.4 | 38.5 | 95% | 1.107 | POLARIZING, ZONE-BEATER |
| 4 | A.J. Brown | WR | NE | 17.7 | 37.3 | 92% | 1.087 | POLARIZING |
| 5 | Nico Collins | WR | HOU | 22.6 | 37.5 | 94% | 1.074 | POLARIZING |
| 6 | Omarion Hampton | RB | LAC | 15.5 | 36.7 | 93% | 0.982 | POLARIZING |
| 7 | Ashton Jeanty | RB | LV | 12.1 | 37.0 | 92% | 0.969 | POLARIZING, EFFICIENCY TRAP |
| 8 | Derrick Henry | RB | BAL | 20.3 | 37.1 | 86% | 0.957 |  |
| 9 | Chase Brown | RB | CIN | 16.9 | 35.3 | 85% | 0.921 | POLARIZING |
| 10 | Saquon Barkley | RB | PHI | 13.4 | 35.0 | 87% | 0.878 | POLARIZING, EMPTY CALORIES |
| 11 | Kenneth Walker III | RB | KC | 14.8 | nan | nan% | nan |  |

### Tier 3 - ADP 24-41 (R3-mid3) - 19 players

| Ceiling rank | Player | Pos | Team | ADP | p95 | adv% | ceil_score | Flags |
|---:|---|:--:|:--:|---:|---:|---:|---:|---|
| 1 | Josh Allen | QB | BUF | 27.0 | 41.9 | 100% | 1.633 | POLARIZING, QB-ZONE-BEATER |
| 2 | Trey McBride | TE | ARI | 24.2 | 35.9 | 100% | 1.312 | POLARIZING |
| 3 | Malik Nabers | WR | NYG | 37.6 | 36.9 | 93% | 1.09 | POLARIZING, EMPTY CALORIES, ZONE-BEATER |
| 4 | Rashee Rice | WR | KC | 25.1 | 38.1 | 96% | 1.086 | POLARIZING, FLOOR RISK, ZONE-BEATER |
| 5 | Garrett Wilson | WR | NYJ | 39.0 | 36.8 | 94% | 1.037 | POLARIZING, MAN-BEATER |
| 6 | Breece Hall | RB | NYJ | 31.9 | 37.4 | 90% | 1.02 | POLARIZING, RB-ZONE-SCHEME |
| 7 | Zay Flowers | WR | BAL | 32.1 | 35.6 | 91% | 1.003 | POLARIZING |
| 8 | Chris Olave | WR | NO | 28.6 | 35.8 | 91% | 0.999 | POLARIZING, EMPTY CALORIES, MAN-BEATER |
| 9 | Colston Loveland | TE | CHI | 39.8 | 29.9 | 94% | 0.997 | POLARIZING |
| 10 | Jeremiyah Love | RB | ARI | 27.3 | 36.8 | 91% | 0.977 | POLARIZING |
| 11 | George Pickens | WR | DAL | 24.3 | 35.7 | 90% | 0.972 | POLARIZING, MAN-BEATER |
| 12 | DeVonta Smith | WR | PHI | 28.1 | 34.8 | 89% | 0.933 | POLARIZING, ZONE-BEATER |
| ... | *+7 more in band* | | | | | | | |

### Tier 4 - ADP 42-65 (R4-mid5) - 25 players

| Ceiling rank | Player | Pos | Team | ADP | p95 | adv% | ceil_score | Flags |
|---:|---|:--:|:--:|---:|---:|---:|---:|---|
| 1 | Drake Maye | QB | NE | 65.5 | 37.2 | 95% | 1.357 | CONSENSUS STUD, POLARIZING |
| 2 | Lamar Jackson | QB | BAL | 53.3 | 36.8 | 97% | 1.265 | POLARIZING, FLOOR RISK |
| 3 | Tyler Warren | TE | IND | 61.3 | 30.1 | 92% | 1.004 | POLARIZING |
| 4 | Davante Adams | WR | LAR | 47.2 | 34.8 | 88% | 0.976 | POLARIZING |
| 5 | Josh Jacobs | RB | GB | 43.5 | 36.7 | 88% | 0.965 | POLARIZING |
| 6 | Tetairoa McMillan | WR | CAR | 42.9 | 36.4 | 88% | 0.962 | POLARIZING, ZONE-BEATER |
| 7 | Jameson Williams | WR | DET | 52.6 | 32.7 | 84% | 0.888 | POLARIZING |
| 8 | Jaylen Waddle | WR | DEN | 47.4 | 32.8 | 83% | 0.861 | POLARIZING |
| 9 | Terry McLaurin | WR | WAS | 45.2 | 32.4 | 87% | 0.848 | POLARIZING, ZONE-BEATER |
| 10 | Carnell Tate | WR | TEN | 62.7 | 32.4 | 84% | 0.826 | POLARIZING |
| 11 | Rome Odunze | WR | CHI | 58.6 | 31.8 | 82% | 0.806 | POLARIZING, EMPTY CALORIES, MAN-BEATER |
| 12 | DJ Moore | WR | BUF | 46.3 | 31.1 | 81% | 0.797 | POLARIZING, MAN-BEATER |
| ... | *+13 more in band* | | | | | | | |

### Tier 5 - ADP 66-95 (R6-8) - 29 players

| Ceiling rank | Player | Pos | Team | ADP | p95 | adv% | ceil_score | Flags |
|---:|---|:--:|:--:|---:|---:|---:|---:|---|
| 1 | Matthew Stafford | QB | LAR | 89.3 | 37.0 | 80% | 1.403 | MARKET FADE |
| 2 | Jayden Daniels | QB | WAS | 69.3 | 35.6 | 90% | 1.173 | POLARIZING, EMPTY CALORIES, EFFICIENCY TRAP, FLOOR RISK, QB-ZONE-BEATER |
| 3 | Dak Prescott | QB | DAL | 79.6 | 35.1 | 72% | 1.172 |  |
| 4 | Trevor Lawrence | QB | JAX | 84.7 | 35.0 | 77% | 1.152 |  |
| 5 | Patrick Mahomes | QB | KC | 92.9 | 34.3 | 69% | 1.038 |  |
| 6 | Sam LaPorta | TE | DET | 92.2 | 28.8 | 90% | 0.987 | POLARIZING, ZONE-BEATER |
| 7 | Justin Herbert | QB | LAC | 81.9 | 33.6 | 67% | 0.972 | MARKET DARLING, POLARIZING |
| 8 | Caleb Williams | QB | CHI | 70.3 | 33.3 | 64% | 0.945 | MARKET DARLING, POLARIZING |
| 9 | Kyle Pitts Sr. | TE | ATL | 90.6 | 28.2 | 86% | 0.853 | POLARIZING, MAN-BEATER |
| 10 | Courtland Sutton | WR | DEN | 82.6 | 31.4 | 81% | 0.801 | POLARIZING |
| 11 | Jalen Hurts | QB | PHI | 75.9 | 33.1 | 92% | 0.784 | POLARIZING |
| 12 | Alec Pierce | WR | IND | 80.2 | 31.2 | 79% | 0.784 | POLARIZING |
| ... | *+17 more in band* | | | | | | | |

### Tier 6 - ADP 96-125 (R8-mid10) - 30 players

| Ceiling rank | Player | Pos | Team | ADP | p95 | adv% | ceil_score | Flags |
|---:|---|:--:|:--:|---:|---:|---:|---:|---|
| 1 | Brock Purdy | QB | SF | 97.3 | 35.9 | 82% | 1.272 | CONSENSUS STUD, QB-MAN-BEATER |
| 2 | George Kittle | TE | SF | 104.7 | 33.2 | 96% | 1.265 | MARKET FADE, POLARIZING |
| 3 | Jaxson Dart | QB | NYG | 101.9 | 34.6 | 87% | 1.115 | MARKET FADE, FLOOR RISK, QB-ZONE-BEATER |
| 4 | Jared Goff | QB | DET | 104.0 | 33.9 | 59% | 1.077 | POLARIZING |
| 5 | Dallas Goedert | TE | PHI | 124.3 | 27.3 | 85% | 0.865 | POLARIZING, ZONE-BEATER |
| 6 | Baker Mayfield | QB | TB | 121.3 | 32.2 | 56% | 0.849 | QB-ZONE-BEATER |
| 7 | Harold Fannin Jr. | TE | CLE | 100.5 | 27.4 | 88% | 0.828 | POLARIZING, EMPTY CALORIES, FLOOR RISK, MAN-BEATER |
| 8 | Jordan Love | QB | GB | 112.1 | 32.0 | 51% | 0.819 | POLARIZING, EFFICIENCY EDGE |
| 9 | Tyler Shough | QB | NO | 117.1 | 31.6 | 54% | 0.781 | QB-MAN-BEATER |
| 10 | Travis Kelce | TE | KC | 117.9 | 26.8 | 83% | 0.78 | POLARIZING |
| 11 | Dalton Kincaid | TE | BUF | 114.1 | 24.8 | 69% | 0.698 | POLARIZING, ZONE-BEATER |
| 12 | Matthew Golden | WR | GB | 115.1 | 28.9 | 76% | 0.657 | POLARIZING |
| ... | *+18 more in band* | | | | | | | |

### Tier 7 - ADP 126-155 (mid10-13) - 30 players

| Ceiling rank | Player | Pos | Team | ADP | p95 | adv% | ceil_score | Flags |
|---:|---|:--:|:--:|---:|---:|---:|---:|---|
| 1 | Zach Charbonnet | RB | SEA | 146.5 | 31.5 | 73% | 1.009 | MARKET FADE, EMPTY CALORIES, RB-ZONE-SCHEME |
| 2 | Sam Darnold | QB | SEA | 136.5 | 31.2 | 49% | 0.82 | EFFICIENCY EDGE |
| 3 | Jake Ferguson | TE | DAL | 128.3 | 25.4 | 79% | 0.79 | POLARIZING, EMPTY CALORIES, EFFICIENCY TRAP |
| 4 | Mark Andrews | TE | BAL | 131.5 | 25.4 | 81% | 0.733 | POLARIZING, EMPTY CALORIES, EFFICIENCY TRAP, FLOOR RISK, MAN-BEATER |
| 5 | Hunter Henry | TE | NE | 155.5 | 24.4 | 67% | 0.643 | POLARIZING |
| 6 | C.J. Stroud | QB | HOU | 139.8 | 29.7 | 41% | 0.598 | QB-MAN-BEATER |
| 7 | Juwan Johnson | TE | NO | 151.4 | 23.6 | 65% | 0.562 |  |
| 8 | Brenton Strange | TE | JAX | 148.2 | 22.4 | 64% | 0.518 |  |
| 9 | KC Concepcion | WR | CLE | 126.3 | 25.2 | 63% | 0.413 |  |
| 10 | Isiah Pacheco | RB | DET | 144.3 | 20.1 | 52% | 0.384 | POLARIZING, RB-ZONE-SCHEME |
| 11 | Oronde Gadsden II | TE | LAC | 143.5 | 20.1 | 54% | 0.376 | POLARIZING, FLOOR RISK |
| 12 | Malik Willis | QB | MIA | 129.6 | 27.9 | 38% | 0.358 | MARKET DARLING, POLARIZING, EFFICIENCY EDGE, QB-MAN-BEATER |
| ... | *+18 more in band* | | | | | | | |

### Tier 8 - ADP 156-191 (R13-16) - 35 players

| Ceiling rank | Player | Pos | Team | ADP | p95 | adv% | ceil_score | Flags |
|---:|---|:--:|:--:|---:|---:|---:|---:|---|
| 1 | Kenyon Sadiq | TE | NYJ | 159.2 | 25.1 | 75% | 0.728 | POLARIZING |
| 2 | T.J. Hockenson | TE | MIN | 163.0 | 24.2 | 73% | 0.625 | EFFICIENCY TRAP, MAN-BEATER |
| 3 | Aaron Rodgers | QB | PIT | 163.2 | 28.0 | 31% | 0.477 | POLARIZING |
| 4 | Dalton Schultz | TE | HOU | 171.2 | 21.8 | 60% | 0.454 | POLARIZING |
| 5 | Gunnar Helm | TE | TEN | 181.3 | 20.9 | 58% | 0.451 | POLARIZING |
| 6 | Tyjae Spears | RB | TEN | 157.6 | 22.1 | 57% | 0.376 | RB-ZONE-SCHEME |
| 7 | Calvin Ridley | WR | TEN | 191.3 | 23.6 | 61% | 0.376 | MARKET FADE, POLARIZING, EFFICIENCY EDGE, ZONE-BEATER |
| 8 | Jerry Jeudy | WR | CLE | 185.0 | 23.2 | 60% | 0.31 | POLARIZING, MAN-BEATER |
| 9 | Tre Tucker | WR | LV | 159.8 | 22.6 | 58% | 0.291 |  |
| 10 | Denzel Boston | WR | CLE | 165.4 | 21.6 | 58% | 0.272 |  |
| 11 | AJ Barner | TE | SEA | 185.3 | 19.1 | 51% | 0.256 |  |
| 12 | Alvin Kamara | RB | NO | 164.3 | 18.8 | 49% | 0.246 |  |
| ... | *+23 more in band* | | | | | | | |

## 1b. Round-by-Round Targets (12-team snake)

For each round (ADP band of 12), the best **ceiling targets** in-band, plus **values falling** from earlier (model rank says they belong sooner). A star (*) marks a target that is itself a fallen value.

**Round 1** (ADP 1-12)
- Ceiling: Puka Nacua (WR-LAR, p95 49.8); Ja'Marr Chase (WR-CIN, p95 46.7); Jaxon Smith-Njigba (WR-SEA, p95 46.6); Amon-Ra St. Brown (WR-DET, p95 44.9); Bijan Robinson (RB-ATL, p95 46.0)

**Round 2** (ADP 13-24)
- Ceiling: Trey McBride (TE-ARI, p95 35.9); Brock Bowers (TE-LV, p95 34.1); De'Von Achane (RB-MIA, p95 40.3); Drake London (WR-ATL, p95 38.5); A.J. Brown (WR-NE, p95 37.3)

**Round 3** (ADP 25-36)
- Ceiling: Josh Allen (QB-BUF, p95 41.9); Rashee Rice (WR-KC, p95 38.1); Breece Hall (RB-NYJ, p95 37.4); Zay Flowers (WR-BAL, p95 35.6); Chris Olave (WR-NO, p95 35.8)

**Round 4** (ADP 37-48)
- Ceiling: Malik Nabers (WR-NYG, p95 36.9); Garrett Wilson (WR-NYJ, p95 36.8); Colston Loveland (TE-CHI, p95 29.9); Davante Adams (WR-LAR, p95 34.8); Josh Jacobs (RB-GB, p95 36.7)

**Round 5** (ADP 49-60)
- Ceiling: Lamar Jackson (QB-BAL, p95 36.8); Jameson Williams (WR-DET, p95 32.7); Rome Odunze (WR-CHI, p95 31.8); Bucky Irving (RB-TB, p95 32.1); Quinshon Judkins (RB-CLE, p95 31.9)

**Round 6** (ADP 61-72)
- Ceiling: Drake Maye (QB-NE, p95 37.2); Jayden Daniels (QB-WAS, p95 35.6); Tyler Warren (TE-IND, p95 30.1); Caleb Williams (QB-CHI, p95 33.3); Carnell Tate (WR-TEN, p95 32.4)

**Round 7** (ADP 73-84)
- Ceiling: Dak Prescott (QB-DAL, p95 35.1); Trevor Lawrence (QB-JAX, p95 35.0); Justin Herbert (QB-LAC, p95 33.6); Courtland Sutton (WR-DEN, p95 31.4); Jalen Hurts (QB-PHI, p95 33.1)

**Round 8** (ADP 85-96)
- Ceiling: Matthew Stafford (QB-LAR, p95 37.0); Patrick Mahomes (QB-KC, p95 34.3); Sam LaPorta (TE-DET, p95 28.8); Kyle Pitts Sr. (TE-ATL, p95 28.2); Michael Pittman Jr. (WR-PIT, p95 29.4)

**Round 9** (ADP 97-108)
- Ceiling: Brock Purdy (QB-SF, p95 35.9); George Kittle (TE-SF, p95 33.2); Jaxson Dart (QB-NYG, p95 34.6); Jared Goff (QB-DET, p95 33.9); Harold Fannin Jr. (TE-CLE, p95 27.4)

**Round 10** (ADP 109-120)
- Ceiling: Jordan Love (QB-GB, p95 32.0); Tyler Shough (QB-NO, p95 31.6); Travis Kelce (TE-KC, p95 26.8); Dalton Kincaid (TE-BUF, p95 24.8); Matthew Golden (WR-GB, p95 28.9)

**Round 11** (ADP 121-132)
- Ceiling: Dallas Goedert (TE-PHI, p95 27.3); Baker Mayfield (QB-TB, p95 32.2); Jake Ferguson (TE-DAL, p95 25.4); Mark Andrews (TE-BAL, p95 25.4); Isaiah Likely (TE-NYG, p95 24.4)

**Round 12** (ADP 133-144)
- Ceiling: Sam Darnold (QB-SEA, p95 31.2); C.J. Stroud (QB-HOU, p95 29.7); Isiah Pacheco (RB-DET, p95 20.1); Oronde Gadsden II (TE-LAC, p95 20.1); Jalen McMillan (WR-TB, p95 22.3)

**Round 13** (ADP 145-156)
- Ceiling: Zach Charbonnet (RB-SEA, p95 31.5); Hunter Henry (TE-NE, p95 24.4); Juwan Johnson (TE-NO, p95 23.6); Brenton Strange (TE-JAX, p95 22.4); Rashid Shaheed (WR-SEA, p95 22.5)

**Round 14** (ADP 157-168)
- Ceiling: Kenyon Sadiq* (TE-NYJ, p95 25.1); T.J. Hockenson (TE-MIN, p95 24.2); Aaron Rodgers (QB-PIT, p95 28.0); Tyjae Spears (RB-TEN, p95 22.1); Tre Tucker (WR-LV, p95 22.6)

**Round 15** (ADP 169-180)
- Ceiling: Dalton Schultz (TE-HOU, p95 21.8); Greg Dulcich (TE-MIA, p95 19.3); Adonai Mitchell (WR-NYJ, p95 20.3); Brian Robinson Jr. (RB-ATL, p95 15.6); Dylan Sampson (RB-CLE, p95 14.5)

**Round 16** (ADP 181-192)
- Ceiling: Gunnar Helm (TE-TEN, p95 20.9); Calvin Ridley (WR-TEN, p95 23.6); Jerry Jeudy (WR-CLE, p95 23.2); Germie Bernard (WR-PIT, p95 21.3); AJ Barner (TE-SEA, p95 19.1)

**Round 17** (ADP 193-204)
- Ceiling: Pat Freiermuth (TE-PIT, p95 22.7); Terrance Ferguson (TE-LAR, p95 21.4); Colby Parkinson (TE-LAR, p95 13.6); David Njoku (TE-LAC, p95 15.7); Cooper Kupp (WR-SEA, p95 18.4)

**Round 18** (ADP 205-216)
- Ceiling: MarShawn Lloyd (RB-GB, p95 12.0); Mike Gesicki (TE-CIN, p95 19.0); Mike Washington Jr. (RB-LV, p95 11.3); Justice Hill (RB-BAL, p95 17.8); Chris Bell (WR-MIA, p95 18.7)

**Round 19** (ADP 217-228)
- Ceiling: Carson Beck (QB-ARI, p95 30.3); Samaje Perine (RB-CIN, p95 16.8); Rashod Bateman (WR-BAL, p95 21.1); Jordan James (RB-SF, p95 11.2); Evan Engram (TE-DEN, p95 18.3)
- Value falling: Emanuel Wilson (RB-SEA, mrank 207)

**Round 20** (ADP 229-240)
- Ceiling: Emari Demercado (RB-KC, p95 11.6); Dawson Knox (TE-BUF, p95 13.6); Jack Bech (WR-LV, p95 18.1); Dyami Brown (WR-WAS, p95 16.5); Nick Westbrook-Ikhine (WR-IND, p95 17.0)

## 2. Team Priority - Attack Order (32 offenses)

Attack score = 0.42*ceiling-capital + 0.26*scoring-env + 0.18*pass-volume/pace + 0.14*vacated-opportunity (each z-scored across the 32 teams, then scaled 0-100). Attack the top of this list when ceiling capital is scarce on the clock.

| Rank | Team | Attack | a-ceil | Sum p95(a) | TD/g | rk_TD | rk_passvol | vac_tgt | Why |
|---:|:--:|---:|:--:|---:|---:|:--:|:--:|---:|---|
| 1 | LAR | 100.0 | 4 | 155.1 | 3.24 | 1 | 11 | 8.9 | 4 alpha-ceiling bats (sum p95 155); elite scoring env (TD/g 3.24, rk1) |
| 2 | DAL | 95.0 | 4 | 148.4 | 2.76 | 5 | 3 | 5.7 | 4 alpha-ceiling bats (sum p95 148); elite scoring env (TD/g 2.76, rk5); top pass volume (rk3) |
| 3 | DET | 84.0 | 3 | 124.5 | 2.94 | 3 | 15 | 14.8 | 3 alpha-ceiling bats (sum p95 125); elite scoring env (TD/g 2.94, rk3) |
| 4 | SF | 77.6 | 3 | 113.1 | 2.59 | 9 | 20 | 38.6 | 3 alpha-ceiling bats (sum p95 113); good scoring env (TD/g 2.59); huge vacated targets (39) |
| 5 | CIN | 71.4 | 2 | 82.0 | 2.76 | 4 | 1 | 6.7 | 2 alpha ceiling(s) (sum p95 82); elite scoring env (TD/g 2.76, rk4); top pass volume (rk1) |
| 6 | KC | 68.0 | 2 | 72.3 | 2.59 | 9 | 5 | 30.8 | 2 alpha ceiling(s) (sum p95 72); good scoring env (TD/g 2.59); top pass volume (rk5); huge vacated targets (31) |
| 7 | PHI | 66.2 | 3 | 102.9 | 2.65 | 7 | 31 | 33.3 | 3 alpha-ceiling bats (sum p95 103); good scoring env (TD/g 2.65); run-leaning (low pass volume); huge vacated targets (33) |
| 8 | BUF | 61.6 | 2 | 79.3 | 3.06 | 2 | 28 | 16.8 | 2 alpha ceiling(s) (sum p95 79); elite scoring env (TD/g 3.06, rk2); run-leaning (low pass volume) |
| 9 | BAL | 59.4 | 3 | 109.5 | 2.71 | 6 | 32 | 18.3 | 3 alpha-ceiling bats (sum p95 110); elite scoring env (TD/g 2.71, rk6); run-leaning (low pass volume); notable vacated targets (18) |
| 10 | LAC | 58.5 | 3 | 103.8 | 2.41 | 14 | 21 | 22.7 | 3 alpha-ceiling bats (sum p95 104); notable vacated targets (23) |
| 11 | NE | 56.1 | 2 | 74.5 | 2.65 | 8 | 25 | 30.4 | 2 alpha ceiling(s) (sum p95 75); good scoring env (TD/g 2.65); run-leaning (low pass volume); huge vacated targets (30) |
| 12 | ATL | 49.0 | 2 | 84.5 | 1.88 | 23 | 7 | 20.7 | 2 alpha ceiling(s) (sum p95 85); notable vacated targets (21) |
| 13 | SEA | 46.5 | 1 | 46.6 | 2.53 | 11 | 27 | 38.7 | 1 alpha ceiling(s) (sum p95 47); good scoring env (TD/g 2.53); run-leaning (low pass volume); huge vacated targets (39) |
| 14 | NYJ | 45.9 | 2 | 74.2 | 2.0 | 22 | 18 | 40.5 | 2 alpha ceiling(s) (sum p95 74); huge vacated targets (40) |
| 15 | ARI | 44.2 | 2 | 72.7 | 1.71 | 28 | 2 | 23.6 | 2 alpha ceiling(s) (sum p95 73); top pass volume (rk2); notable vacated targets (24) |
| 16 | WAS | 43.8 | 1 | 35.6 | 2.29 | 17 | 25 | 59.5 | 1 alpha ceiling(s) (sum p95 36); run-leaning (low pass volume); huge vacated targets (60) |
| 17 | NYG | 42.2 | 2 | 71.5 | 2.18 | 20 | 30 | 33.8 | 2 alpha ceiling(s) (sum p95 72); run-leaning (low pass volume); huge vacated targets (34) |
| 18 | GB | 41.6 | 1 | 36.7 | 2.47 | 12 | 18 | 28.6 | 1 alpha ceiling(s) (sum p95 37); good scoring env (TD/g 2.47); notable vacated targets (29) |
| 19 | IND | 40.4 | 1 | 40.4 | 2.29 | 17 | 23 | 41.1 | 1 alpha ceiling(s) (sum p95 40); huge vacated targets (41) |
| 20 | CHI | 40.4 | 1 | 33.3 | 2.41 | 14 | 21 | 27.2 | 1 alpha ceiling(s) (sum p95 33); notable vacated targets (27) |
| 21 | MIN | 40.3 | 1 | 41.2 | 2.12 | 21 | 4 | 22.8 | 1 alpha ceiling(s) (sum p95 41); top pass volume (rk4); notable vacated targets (23) |
| 22 | JAX | 35.0 | 1 | 35.0 | 2.35 | 16 | 10 | 15.0 | 1 alpha ceiling(s) (sum p95 35) |
| 23 | LV | 34.4 | 2 | 71.1 | 1.71 | 28 | 8 | 12.0 | 2 alpha ceiling(s) (sum p95 71) |
| 24 | TB | 32.6 | 1 | 33.1 | 2.24 | 19 | 23 | 29.6 | 1 alpha ceiling(s) (sum p95 33); notable vacated targets (30) |
| 25 | NO | 27.0 | 1 | 35.8 | 1.88 | 23 | 14 | 13.4 | 1 alpha ceiling(s) (sum p95 36) |
| 26 | DEN | 26.3 | 0 | 0.0 | 2.47 | 13 | 9 | 9.8 | thin on alpha ceilings |
| 27 | PIT | 26.0 | 0 | 0.0 | 1.76 | 27 | 6 | 44.8 | thin on alpha ceilings; top pass volume (rk6); huge vacated targets (45) |
| 28 | HOU | 22.6 | 1 | 37.5 | 1.88 | 23 | 13 | 10.8 | 1 alpha ceiling(s) (sum p95 37) |
| 29 | CAR | 18.5 | 1 | 36.4 | 1.82 | 26 | 17 | 20.0 | 1 alpha ceiling(s) (sum p95 36); notable vacated targets (20) |
| 30 | MIA | 13.0 | 1 | 40.3 | 1.35 | 32 | 29 | 44.0 | 1 alpha ceiling(s) (sum p95 40); run-leaning (low pass volume); huge vacated targets (44) |
| 31 | TEN | 9.5 | 0 | 0.0 | 1.71 | 30 | 11 | 25.7 | thin on alpha ceilings; notable vacated targets (26) |
| 32 | CLE | 0.0 | 0 | 0.0 | 1.47 | 31 | 15 | 15.2 | thin on alpha ceilings |

## 3. Stacks - QB + WR1 (+WR2/TE) + Week-17 Bring-Back

A stack pairs a QB with his top pass-catcher(s) and a **bring-back** receiver from the **Week-17 finals opponent** (the correlated game where the title is decided). WR1 = the team's highest-p95 pass-catcher (the alpha the QB-WR1 r was measured on). Combined ceiling = sum of members' p95. Stack score = combined ceiling x correlation factor, lightly penalised by total ADP cost; top-tail (rk<=6) shootouts get a small bonus. `LEVERAGE` = cheaper / lower-profile; `CHALK` = premium; `SHOOTOUT` = high-total game.

| Rank | QB | Team | Pieces | Bring-back | W17 game | Tail | r(bb) | Comb. ceil | ADP cost | Lev | Score |
|---:|---|:--:|---|---|:--:|:--:|---:|---:|---:|---|---:|
| 1 | Joe Burrow | CIN | Joe Burrow + Ja'Marr Chase + Tee Higgins | Zay Flowers (BAL) | BAL@CIN | 2 | 0.159 | 144.9 | 129.7 | CHALK/SHOOTOUT | 161.87 |
| 2 | Dak Prescott | DAL | Dak Prescott + CeeDee Lamb + George Pickens | Malik Nabers (NYG) | DAL@NYG | 3 | 0.159 | 150.2 | 151.9 | MID/SHOOTOUT | 160.27 |
| 3 | Matthew Stafford | LAR | Matthew Stafford + Puka Nacua + Davante Adams | Emeka Egbuka (TB) | LAR@TB | 1 | 0.159 | 154.7 | 173.0 | MID/SHOOTOUT | 157.71 |
| 4 | Caleb Williams | CHI | Caleb Williams + Rome Odunze + Luther Burden III | Amon-Ra St. Brown (DET) | CHI@DET | 4 | 0.159 | 140.4 | 178.0 | MID/SHOOTOUT | 141.55 |
| 5 | Jared Goff | DET | Jared Goff + Amon-Ra St. Brown + Jameson Williams | Rome Odunze (CHI) | CHI@DET | 4 | 0.159 | 143.3 | 222.4 | LEVERAGE/SHOOTOUT | 130.12 |
| 6 | Lamar Jackson | BAL | Lamar Jackson + Zay Flowers | Ja'Marr Chase (CIN) | BAL@CIN | 2 | 0.159 | 119.1 | 88.5 | CHALK/SHOOTOUT | 117.7 |
| 7 | Tyler Shough | NO | Tyler Shough + Chris Olave + Jordyn Tyson | Drake London (ATL) | ATL@NO | 11 | 0.129 | 134.9 | 232.3 | LEVERAGE | 114.12 |
| 8 | Bo Nix | DEN | Bo Nix + Jaylen Waddle + Courtland Sutton | A.J. Brown (NE) | DEN@NE | 6 | 0.159 | 131.9 | 260.4 | LEVERAGE/SHOOTOUT | 108.47 |
| 9 | Brock Purdy | SF | Brock Purdy + George Kittle + Mike Evans | DeVonta Smith (PHI) | PHI@SF | 8 | 0.159 | 133.4 | 280.6 | LEVERAGE/SHOOTOUT | 100.61 |
| 10 | Jaxson Dart | NYG | Jaxson Dart + Malik Nabers | CeeDee Lamb (DAL) | DAL@NYG | 3 | 0.159 | 114.0 | 149.9 | LEVERAGE/SHOOTOUT | 99.76 |
| 11 | Baker Mayfield | TB | Baker Mayfield + Emeka Egbuka | Puka Nacua (LAR) | LAR@TB | 1 | 0.159 | 115.1 | 157.8 | LEVERAGE/SHOOTOUT | 99.05 |
| 12 | Drake Maye | NE | Drake Maye + A.J. Brown | Jaylen Waddle (DEN) | DEN@NE | 6 | 0.159 | 107.3 | 130.6 | MID/SHOOTOUT | 97.71 |
| 13 | Jalen Hurts | PHI | Jalen Hurts + DeVonta Smith + Makai Lemon | George Kittle (SF) | PHI@SF | 8 | 0.159 | 129.8 | 296.3 | LEVERAGE/SHOOTOUT | 93.43 |
| 14 | Justin Herbert | LAC | Justin Herbert + Ladd McConkey | Rashee Rice (KC) | KC@LAC | 9 | 0.159 | 105.1 | 141.7 | MID/SHOOTOUT | 90.84 |
| 15 | Sam Darnold | SEA | Sam Darnold + Jaxon Smith-Njigba | Tetairoa McMillan (CAR) | CAR@SEA | 5 | 0.129 | 114.2 | 184.8 | LEVERAGE | 90.76 |

### Stack notes
- **#1 Joe Burrow (CIN)** - Joe Burrow + Ja'Marr Chase (+Tee Higgins) bring-back Zay Flowers (BAL) | shootout-tilted W17, top-2 blow-up tail. Combined ceiling 144.9, ADP cost 129.7, corr factor 1.369, score 161.87.
- **#2 Dak Prescott (DAL)** - Dak Prescott + CeeDee Lamb (+George Pickens) bring-back Malik Nabers (NYG) | shootout-tilted W17, top-3 blow-up tail. Combined ceiling 150.2, ADP cost 151.9, corr factor 1.369, score 160.27.
- **#3 Matthew Stafford (LAR)** - Matthew Stafford + Puka Nacua (+Davante Adams) bring-back Emeka Egbuka (TB) | shootout-tilted W17, top-1 blow-up tail. Combined ceiling 154.7, ADP cost 173.0, corr factor 1.369, score 157.71.
- **#4 Caleb Williams (CHI)** - Caleb Williams + Rome Odunze (+Luther Burden III) bring-back Amon-Ra St. Brown (DET) | shootout-tilted W17, top-4 blow-up tail. Combined ceiling 140.4, ADP cost 178.0, corr factor 1.369, score 141.55.
- **#5 Jared Goff (DET)** - Jared Goff + Amon-Ra St. Brown (+Jameson Williams) bring-back Rome Odunze (CHI) | shootout-tilted W17, top-4 blow-up tail. Combined ceiling 143.3, ADP cost 222.4, corr factor 1.369, score 130.12.
- **#6 Lamar Jackson (BAL)** - Lamar Jackson + Zay Flowers bring-back Ja'Marr Chase (CIN) | shootout-tilted W17, top-2 blow-up tail. Combined ceiling 119.1, ADP cost 88.5, corr factor 1.118, score 117.7.
- **#7 Tyler Shough (NO)** - Tyler Shough + Chris Olave (+Jordyn Tyson) bring-back Drake London (ATL) | moderate-total W17, top-11 blow-up tail. Combined ceiling 134.9, ADP cost 232.3, corr factor 1.346, score 114.12.
- **#8 Bo Nix (DEN)** - Bo Nix + Jaylen Waddle (+Courtland Sutton) bring-back A.J. Brown (NE) | shootout-tilted W17, top-6 blow-up tail. Combined ceiling 131.9, ADP cost 260.4, corr factor 1.369, score 108.47.
- **#9 Brock Purdy (SF)** - Brock Purdy + George Kittle (+Mike Evans) bring-back DeVonta Smith (PHI) | shootout-tilted W17, top-8 blow-up tail. Combined ceiling 133.4, ADP cost 280.6, corr factor 1.369, score 100.61.
- **#10 Jaxson Dart (NYG)** - Jaxson Dart + Malik Nabers bring-back CeeDee Lamb (DAL) | shootout-tilted W17, top-3 blow-up tail. Combined ceiling 114.0, ADP cost 149.9, corr factor 1.118, score 99.76.
- **#11 Baker Mayfield (TB)** - Baker Mayfield + Emeka Egbuka bring-back Puka Nacua (LAR) | shootout-tilted W17, top-1 blow-up tail. Combined ceiling 115.1, ADP cost 157.8, corr factor 1.118, score 99.05.
- **#12 Drake Maye (NE)** - Drake Maye + A.J. Brown bring-back Jaylen Waddle (DEN) | shootout-tilted W17, top-6 blow-up tail. Combined ceiling 107.3, ADP cost 130.6, corr factor 1.118, score 97.71.
- **#13 Jalen Hurts (PHI)** - Jalen Hurts + DeVonta Smith (+Makai Lemon) bring-back George Kittle (SF) | shootout-tilted W17, top-8 blow-up tail. Combined ceiling 129.8, ADP cost 296.3, corr factor 1.369, score 93.43.
- **#14 Justin Herbert (LAC)** - Justin Herbert + Ladd McConkey bring-back Rashee Rice (KC) | shootout-tilted W17, top-9 blow-up tail. Combined ceiling 105.1, ADP cost 141.7, corr factor 1.118, score 90.84.
- **#15 Sam Darnold (SEA)** - Sam Darnold + Jaxon Smith-Njigba bring-back Tetairoa McMillan (CAR) | moderate-total W17, top-5 blow-up tail. Combined ceiling 114.2, ADP cost 184.8, corr factor 1.095, score 90.76.

### Explicit leverage stacks (cheaper / lower-profile)
- **Jared Goff (DET)**, Amon-Ra St. Brown, Jameson Williams + Rome Odunze - ADP cost 222.4, combined ceiling 143.3, LEVERAGE/SHOOTOUT.
- **Tyler Shough (NO)**, Chris Olave, Jordyn Tyson + Drake London - ADP cost 232.3, combined ceiling 134.9, LEVERAGE.
- **Bo Nix (DEN)**, Jaylen Waddle, Courtland Sutton + A.J. Brown - ADP cost 260.4, combined ceiling 131.9, LEVERAGE/SHOOTOUT.
- **Brock Purdy (SF)**, George Kittle, Mike Evans + DeVonta Smith - ADP cost 280.6, combined ceiling 133.4, LEVERAGE/SHOOTOUT.
- **Jaxson Dart (NYG)**, Malik Nabers + CeeDee Lamb - ADP cost 149.9, combined ceiling 114.0, LEVERAGE/SHOOTOUT.
- **Baker Mayfield (TB)**, Emeka Egbuka + Puka Nacua - ADP cost 157.8, combined ceiling 115.1, LEVERAGE/SHOOTOUT.
- **Jalen Hurts (PHI)**, DeVonta Smith, Makai Lemon + George Kittle - ADP cost 296.3, combined ceiling 129.8, LEVERAGE/SHOOTOUT.
- **Sam Darnold (SEA)**, Jaxon Smith-Njigba + Tetairoa McMillan - ADP cost 184.8, combined ceiling 114.2, LEVERAGE.

---
*Generated by `gameplan.py`. Read-only on shared inputs; this module owns `gameplan.py`, `gameplan.json`, `GAMEPLAN.md` only.*