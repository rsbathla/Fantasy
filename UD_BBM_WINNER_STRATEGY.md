# Underdog Best Ball Mania VII — Winner-Calibrated Draft Plan (2026)

Built from documented winner patterns across 5+ years of Best Ball Mania, then wired into the engine.
Use the value board (`ud_cheatsheet.csv`) to know **who** to take; use this page to know **what shape** to build.

## The format (why UD ≠ DK)
- **Half-PPR** (0.5/rec), 4-pt pass TD, no TE premium, no bonuses, no D/K. 18-man rosters.
- **Lineup:** QB / RB / RB / WR / WR / WR / TE / FLEX.
- **Playoffs are win-or-die:** advance top-2 of 12 (Weeks 1–14) → **win Week 15 (1 of 14)** → **win Week 16 (1 of 12)** → 667-team Week 17 finals. You must be the single best team in your pod *each* playoff week, so **weekly ceiling and correlation matter far more than on DK**.

## Winning roster shape (target, 18 rounds)
| Pos | Target | Winner notes |
|---|---|---|
| **WR** | **6–8** (≈7) | Elite teams spend **way more** at WR. Hit **4–5 WR by Round 10**; finish 6–7. |
| **RB** | **4–6** (≈4–5) | Take RB **early**, then go light. The best builds finished with **4 RB**, then 5, 6, 7 — because early-RB teams took fewer. |
| **QB** | **2–3** (cheap) | ~50/50 split 2 vs 3 QB among elite teams, but spend **less** capital. QB2 in **R8–11**, QB3 **R15–18**. |
| **TE** | **2–3** | Not a differentiator — elite and average teams allocate TE similarly. Elite-TE-or-wait both fine. |

These are now the engine's UD targets (`SEASON_TARGET` under `BB_PLATFORM=UD`); DK keeps RB 5-6 / WR 8-9.

## Running back: early, then stop
- Taking an RB in **Round 1 doubled** your advance odds in BBM VI; **two straight RBs to open tripled** it vs teams that passed on RB in the first two rounds. Those early RBs crushed.
- Consensus floor: **at least 2 RBs through Round 5.**
- **Zero-RB has been rough** the last two years. **Hero-RB** (one elite anchor early, then punt to depth) is the cleaner version of going light.
- So: anchor early, then let RB depth come cheap and pour the middle rounds into WR.

## Wide receiver: the engine of winning teams
- Elite teams are **WR-heavy and RB-light** relative to the field — the single clearest structural edge.
- Pace: **4–5 WR by Round 10**, finish **6–7** (6 if you took WR early, 7 if mostly mid-round).
- Half-PPR lowers each receiver's *points*, but WRs still **win the tournament** because they carry the weekly spike ceiling the playoff gates demand. (This is why the board is value-ranked but the *shape* is WR-heavy — don't let the half-PPR RB bump talk you into an RB-heavy roster.)

## Quarterback: cheap, but stacked
- Pay down at QB (elite teams spend less here), but **stack them**. Three stacked QBs were **+23% to make the finals**; zero stacked QBs were **−26%**.
- QB2 around **R8–11**, QB3 **R15–18**.

## Correlation is the whole game (especially for Week 17)
This is where UD titles are actually won:
- A **QB1–WR1–WR2** three-stack advanced to the finals at **2.6× the expected rate** (2023).
- The BBM III winner (Pat Kerrane, $2M) had **3 game stacks — 12 of his 18 players came from just 3 Week-17 games.**
- **Bring-backs work:** the opponent of a QB who scores 30+ outscores projection by 10+ at a **20.8%** clip — so build a game stack, then add a piece from the *other* team in that Week-17 game.
- The logic: double-stacking three QBs with two pass-catchers each = 9 of 18 spots, and you only need **3** offenses to pop, not 9 individuals.

The engine now reflects this in UD mode: **1.4× stack bonus**, onslaught penalty deferred until **6** pieces in one game (you can concentrate harder than on DK), and a **stronger playoff tilt** (λ 0.03·(round−7) vs DK's 0.02).

## How to draft with the tools
1. **Value:** draft off `ud_cheatsheet.csv` (sort `ud_rank`; `value` = where we're higher than UD market).
2. **Shape:** follow the targets above — anchor RB early, hit 4–5 WR by R10, take QBs cheap-but-stacked, don't overthink TE.
3. **Correlate:** by the middle rounds, start building 2–3 Week-17 game stacks (QB + 2 catchers + a bring-back). Aim to concentrate a large share of your roster in a few W17 games.
4. **Grade any UD roster:** run the engine with `BB_PLATFORM=UD BB_PROJ_COL=ud_pg` (half-PPR scoring + BBM cut rates).

## Sources
- [How Winners Draft Running Backs in Underdog Best Ball Mania — 4for4](https://www.4for4.com/2026/preseason/how-winners-draft-running-backs-underdog-best-ball-mania)
- [How Winners Draft Wide Receivers in Underdog Best Ball Mania — 4for4](https://www.4for4.com/2026/preseason/how-winners-draft-wide-receivers-underdog-best-ball-mania)
- [How Winners Draft Tight Ends in Underdog Best Ball Mania — 4for4](https://www.4for4.com/2026/preseason/how-winners-draft-tight-ends-underdog-best-ball-mania)
- [What Has Worked In All 5 Years Of Best Ball Mania — Underdog Network](https://underdognetwork.com/football/best-ball-research/what-has-worked-in-all-5-years-of-best-ball-mania)
- [Underdog Fantasy Best Ball: Optimal Position Allocation — Establish The Run](https://establishtherun.com/underdog-fantasy-best-ball-optimal-position-allocation/)
- [Strategy: How to Win Underdog's Best Ball Mania — Establish The Run](https://establishtherun.com/strategy-how-to-win-underdogs-best-ball-mania/)
- [Best Ball Mania VII rules — Underdog Fantasy](https://help.underdogfantasy.com/en/articles/14785343-best-ball-mania-vii)
