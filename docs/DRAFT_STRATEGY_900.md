# 900-Entry SLOW-DRAFT Plan — Schedule + Portfolio Construction
Built from the survival-chain findings. Goal: 900 entries COMPLETE by **Sept 9** (today Jun 15).
Slow drafts chosen on purpose: hours per pick = time to apply the discipline (anchor build, bye check, news) on every pick.

## 0. Slow-draft mechanics that change the plan
- A slow draft takes ~**5-7 days to fill + complete** (multi-hour clocks). So pacing is by **START date**, and there's a hard **last-start cutoff**: `last_start = Sept 9 - completion_days`. At ~7 days that's **~Sept 1**. (If your clock runs faster, the cutoff slides later: `Sept 9 - your_avg_completion`.)
- You will run **dozens-to-100+ concurrent drafts**. Feasible ONLY because the pre-loaded ranking auto-picks the non-leverage rounds; you hand-manage just the leverage picks.

## 1. START-based pacing (all started by ~Sept 1 so they finish by Sept 9)
| Window | Days | Starts | ~/day | Why |
|---|---|---|---|---|
| Jun 15-30 | 16 | 110 | ~7 | Reps; ADP early -- lighter |
| July | 31 | 290 | ~9 | Build; OTA/news values shift |
| Aug 1-25 | 25 | 420 | ~17 | PEAK -- camp + preseason info, best ADP liquidity |
| Aug 26-Sep 1 | 7 | 80 | ~11 | Final starts; complete by ~Sep 8 |
| Total | 79 | 900 | -- | All started by ~Sep 1 |

Concurrency math: ~12 starts/day x ~6-day life = **~70 open drafts at steady state, ~100+ at the Aug peak**. Each open draft = ~3 of your picks/day -> let the board auto-pick most; actively touch only the leverage rounds.

## 2. The workflow that makes 900 slow drafts feasible
1. **Pre-load `dk_preload_rankings.csv`** as your DK pre-draft rankings (desktop upload). This auto-picks best-available on your board whenever you don't act -- it carries our upside edge (ceiling-tilted, ADP-anchored), so auto-picks are already good.
2. **Check in 2-3x/day.** Most picks will have auto-resolved correctly.
3. **Hand-manage ~5-6 LEVERAGE picks per draft** with the assistant:
   - The rounds where you build your **4-5 piece game-stack anchor** (the one game you concentrate).
   - Any pick where a **bye-cluster** or **news** flag matters.
   - `python draft_assistant.py --pick <N> --mine "<picks>" --gone "<taken>" --anchor-used "<your other recent anchors>"`
4. **Log each entry's W17 anchor** to a running tally so you hit the allocation below.

## 3. Anchor-game allocation across 900 (concentrate within, diversify across)
Each entry = one W17 game stack. Spread anchors by TAIL rank (full file: anchor_allocation_900.csv).
| Tier | Games | Entries each | Total |
|---|---|---|---|
| Elite tail | LAR@TB, BAL@CIN, DAL@NYG, DET@CHI | ~107 | ~428 |
| Strong | SEA@CAR, NE@DEN, MIN@NYJ, SF@PHI, KC@LAC, GB@HOU | ~54 | ~324 |
| Leverage | ATL@NO, JAX@WAS, PIT@TEN, LV@ARI, IND@CLE, BUF@MIA | ~25 | ~150 |
Build anchors TWO-SIDED (QB + catchers on one team AND 1-2 on the opponent), not one-sided team stacks.

## 4. Non-negotiable rules (from the 4-draft audit)
1. **Never stack same-bye teams** (your recurring -EV leak; the assistant flags it -> hard stop).
2. **Advancement first** -- every entry needs floor to clear the 2-of-12 gate (Draft 1 died there at 7%).
3. **Concentrate within / diversify across** -- one anchor per entry, rotate the game across the 900.
4. **Rank finals games by TAIL, not O/U** (ATL@NO: 16th by total, 11th by tail).

## 5. Player exposure caps (so 900 aren't 900 copies)
- Highest-conviction values: up to ~35-40%. Core: ~15-25%. Rest: <15%.
- The pre-load auto-picks will naturally spread exposure (different players fall in different drafts); the leverage picks are where you deliberately concentrate the anchors.

## 6. Make W15/W16/W17 spikes good (your priority)
Assistant weights playoff ceiling (p95) heaviest. Per entry confirm the anchor is high on the TAIL ranking AND you hold startable spike pieces with LIVE games in W15 and W16 too -- a W17-only roster can be bounced in the earlier gates (signals board shows w15_opp / w16_opp).
