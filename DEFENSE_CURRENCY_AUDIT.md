# 2026 Defense Data-Currency Audit — All 32 Teams

_One mechanical test applied identically to every team. No team hand-picked; DET/LAR were only the examples that surfaced the two error classes._

## Method

The model rates each defensive unit from **SIS 2025 Points-Saved** (a top-200 leaderboard per unit), reweighted onto 2026 rosters. Two failure modes were swept league-wide by cross-referencing that source against **PFF grades (2024 healthy-season + 2025)** and the curated roster-moves map:

1. **False credit** — a 2025 player still counted for a 2026 team he's no longer on (the *Arnold* pattern).

2. **Missing contributor** — a real starter absent from the SIS leaderboard the model reads, so he can't be credited (the *Joseph* pattern).


**Recovery rule (applied to all 32):** A player who was a GOOD 2024 starter (PFF>=74, >=snap_min snaps) with a POSITIVE SIS 2024 rate, absent from SIS-2025 and having played <500 total 2025 def snaps (injured/DNP), is folded onto his 2026 team at 2024 rate x 0.65. Healthy-but-SIS-omitted -> flagged not recovered; PFF-elite absent both SIS years -> flagged.


**Haircut = 0.65 · 2024 snap floor = 400 coverage / 300 rush / 300 run · PFF grade floor = 74 · injured if < 500 total 2025 defensive snaps.**


## A. Recovered — injured-2025 starters folded back from their 2024 SIS reading (×0.65)

These played too little of 2025 to be judged (injury/DNP); their last valid reading is 2024. Positive-rate only, so recovery can only *restore* value, never tank a team.


| Player | 2026 team | Unit | 2024 rate | Used (×0.65) | 2024 snaps |
|---|---|---|---|---|---|
| Fred Warner | SF | coverage | 0.0355 | 0.0231 | 500 |
| Nick Bosa | SF | pass_rush | 0.0206 | 0.0134 | 404 |
| Ed Oliver | BUF | pass_rush | 0.0142 | 0.0093 | 372 |
| Kerby Joseph | DET | run_def | 0.0175 | 0.0114 | 326 |
| Jarvis Brownlee Jr. | TEN | run_def | 0.0162 | 0.0105 | 393 |
| Eric Kendricks | DAL | run_def | 0.0138 | 0.009 | 376 |

## B. Flagged — cannot credit without fabricating (documented, ratings unchanged)

| Player | Team | Unit | Why |
|---|---|---|---|
| Justin Reid | KC | coverage | played a full 2025 (442 snaps) yet SIS ranks him outside top-200; SIS/PFF disagree — 2024 not cherry-picked |
| Julian Love | SEA | coverage | played a full 2025 (403 snaps) yet SIS ranks him outside top-200; SIS/PFF disagree — 2024 not cherry-picked |
| Xavier McKinney | GB | coverage | played a full 2025 (665 snaps) yet SIS ranks him outside top-200; SIS/PFF disagree — 2024 not cherry-picked |
| Julian Love | SEA | run_def | played a full 2025 (217 snaps) yet SIS ranks him outside top-200; SIS/PFF disagree — 2024 not cherry-picked |
| Malik Hooker | DAL | run_def | played a full 2025 (219 snaps) yet SIS ranks him outside top-200; SIS/PFF disagree — 2024 not cherry-picked |
| Jaycee Horn | CAR | run_def | played a full 2025 (430 snaps) yet SIS ranks him outside top-200; SIS/PFF disagree — 2024 not cherry-picked |
| Kerby Joseph | DET | coverage | PFF-elite 2024 (grade 91.5) but absent from SIS **both** years — no reading to fold in |

## C. Removed — verified off their 2026 roster (subtracted)

| Player | Team | Note | Source |
|---|---|---|---|
| Terrion Arnold | DET | Released mid-2026 (legal case); 2025 coverage no longer credited | CBS/FOX/SI/ESPN (web-verified) |

## D. Per-team exposure — top *assumed-staying* contributors (not in the moves map)

These drive each team's rating on the default 'stays unless a confirmed move says otherwise' assumption. Shown so the load-bearing assumptions are visible per team.


| Team | Top assumed-staying contributors (unit, SIS PS) |
|---|---|
| ARI | Josh Sweat (pas 32.2), Budda Baker (cov 13.6), Will Johnson (cov 12.6), Zaven Collins (pas 11.7) |
| ATL | Jessie Bates III (cov 29.3), Xavier Watts (cov 27.6), A.J. Terrell (cov 25.1), James Pearce Jr. (pas 21.0) |
| BAL | Kyle Hamilton (cov 21.6), Nate Wiggins (cov 18.7), Malaki Starks (cov 17.1), Kyle Hamilton (run 16.8) |
| BUF | Cole Bishop (cov 29.8), Christian Benford (cov 25.7), Greg Rousseau (pas 18.9), Jordan Poyer (run 15.8) |
| CAR | Mike Jackson Sr. (cov 35.4), Jaycee Horn (cov 25.3), Tre'von Moehrig (cov 20.8), Derrick Brown (run 20.0) |
| CHI | Montez Sweat (pas 20.7), Jaquan Brisker (cov 19.3), Gervon Dexter Sr. (pas 16.2), Jaquan Brisker (run 14.7) |
| CIN | Jordan Battle (run 23.4), DJ Turner II (cov 19.4), Dax Hill (run 16.8), BJ Hill (run 16.0) |
| CLE | Carson Schwesinger (run 26.9), Grant Delpit (cov 22.9), Denzel Ward (cov 21.5), Ronnie Hickman (run 17.1) |
| DAL | Osa Odighizuwa (pas 13.9), Donovan Wilson (run 13.2), Donovan Wilson (cov 12.3), DaRon Bland (run 12.1) |
| DEN | Pat Surtain II (cov 38.5), Riley Moss (cov 35.1), Brandon Jones (cov 30.7), Nik Bonitto (pas 27.3) |
| DET | Aidan Hutchinson (pas 63.7), Jack Campbell (run 31.9), Jack Campbell (cov 26.9), Brian Branch (run 16.3) |
| GB | Micah Parsons (pas 36.4), Edgerrin Cooper (cov 24.7), Keisean Nixon (cov 18.3), Xavier McKinney (run 17.7) |
| HOU | Will Anderson Jr. (pas 57.4), Danielle Hunter (pas 47.2), Derek Stingley Jr. (cov 41.9), Jalen Pitre (cov 28.3) |
| IND | Laiatu Latu (pas 28.5), DeForest Buckner (pas 16.9), Grover Stewart (run 12.7), Kenny Moore II (cov 11.7) |
| JAX | Antonio Johnson (cov 29.8), Josh Hines-Allen (pas 28.7), Montaric Brown (cov 25.9), Jourdan Lewis (cov 25.8) |
| KC | Chris Jones (pas 34.9), Chamarri Conner (cov 19.6), George Karlaftis (pas 18.5), Nick Bolton (run 16.9) |
| LAC | Tuli Tuipulotu (pas 26.8), Donte Jackson (cov 25.8), Daiyan Henley (cov 18.6), Derwin James Jr. (cov 17.4) |
| LAR | Kam Curl (cov 24.6), Byron Young (run 24.6), Kamren Kinchens (cov 23.4), Nate Landman (cov 19.6) |
| LV | Maxx Crosby (run 34.6), Eric Stokes (cov 24.5), Jeremy Chinn (run 19.7), Maxx Crosby (pas 15.1) |
| MIA | Jordyn Brooks (run 29.8), Rasul Douglas (cov 26.8), Jack Jones (cov 19.6), Jack Jones (run 18.6) |
| MIN | Dallas Turner (pas 26.0), Blake Cashman (run 22.6), Andrew Van Ginkel (pas 21.7), Jalen Redmond (pas 16.8) |
| NE | Christian Gonzalez (cov 28.1), Robert Spillane (cov 26.6), Carlton Davis III (cov 25.9), Marcus Jones (cov 24.4) |
| NO | Chase Young (pas 40.7), Alontae Taylor (cov 23.1), Cameron Jordan (pas 16.4), Kool-Aid McKinstry (cov 13.8) |
| NYG | Brian Burns (pas 47.0), Bobby Okereke (cov 22.3), Bobby Okereke (run 17.6), Abdul Carter (pas 15.7) |
| NYJ | Brandon Stephens (run 21.2), Jamien Sherwood (run 20.6), Malachi Moore (run 19.2), Jowon Briggs (pas 14.8) |
| PHI | Cooper DeJean (cov 36.7), Quinyon Mitchell (cov 27.4), Zack Baun (cov 25.6), Moro Ojomo (pas 20.5) |
| PIT | Nick Herbig (pas 29.8), Cameron Heyward (run 22.4), Alex Highsmith (pas 21.8), T.J. Watt (pas 20.7) |
| SEA | Ernest Jones IV (cov 36.2), Riq Woolen (cov 26.8), Josh Jobe (cov 23.3), Devon Witherspoon (cov 22.2) |
| SF | Deommodore Lenoir (cov 38.2), Ji'Ayir Brown (cov 21.4), Renardo Green (cov 18.4), Renardo Green (run 15.3) |
| TB | Antoine Winfield Jr. (cov 25.2), Yaya Diaby (pas 21.9), Lavonte David (cov 16.5), Zyon McCollum (run 15.8) |
| TEN | Jeffery Simmons (pas 45.6), Cody Barton (cov 29.0), Cedric Gray (run 27.3), Jeffery Simmons (run 23.3) |
| WAS | Mike Sainristil (cov 16.2), Quan Martin (run 15.4), Jer'Zhan Newton (pas 11.1), Daron Payne (pas 9.3) |

## Limitations (honest)

- Recovery assumes a returning player is on the 2026 roster (the model's universal 'rostered players play' convention) and regresses form 35% for injury risk. It does **not** assume they return to peak.

- 'Assumed-staying' players (section D) are credited unless a confirmed move exists; a release/retirement not yet in the moves map would still be counted. The map covers all major 2026 moves found across ESPN/CBS/NFL.com trackers.

- SIS Points Saved structurally under-rates ball-hawk safeties (e.g. Kerby Joseph, elite by PFF, absent from SIS both years). Those are flagged, not overridden, to keep the metric internally consistent.
