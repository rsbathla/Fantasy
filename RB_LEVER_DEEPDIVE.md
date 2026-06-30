# RB stats deep-dive — FantasyPoints 2024+2025, YoY-tested

What FP gives us for RBs: **Advanced Rushing** (concept zone/gap, run direction, box, missed tackles, explosive,
yards before/after contact, YPC, success/stuff rates) + the **receiving** reports (RBs as pass-catchers: routes,
targets/route, YPRR, and man/zone/single-high/two-high splits). Every metric below is tested for year-over-year
stability (Pearson r, 2024 vs 2025, RBs above the sample floor) — a split is only a lever if it *persists*.

## 1. Rushing — full YoY stability table (n=36 RBs, ≥80 carries both years)

| group | metric | YoY r | read |
|---|---|---|---|
| **Workload (role)** | offensive snaps | 0.69 | very stable — usage is the engine |
| | fantasy pts/g (PPR) | 0.67 | stable |
| | expected FP (xFP) | 0.66 | stable |
| | rush attempts | 0.60 | stable |
| | rush yards / TDs | 0.56 | stable (volume-driven) |
| | first downs | 0.51 | stable |
| **Scheme USAGE** | zone-concept attempts | 0.59 | stable — but it's the OFFENSE's scheme |
| | gap/"man"-concept attempts | 0.60 | stable — offense, not the back |
| | zone att % / man att % | 0.50 / 0.52 | stable share (offense identity) |
| **Skill** | **missed tackles forced (total)** | **0.61** | **STABLE — elusiveness is the #1 RB skill** |
| | missed tackles forced / att | 0.50 | stable skill |
| | explosive-run yards | 0.56 | stable-ish — big-play back |
| | yards before contact / att | 0.33 | moderate (OL + vision) |
| | explosive-run % | 0.39 | moderate |
| **NOISE (reject)** | YPC | 0.18 | does not persist |
| | inside-5 (goal-line) attempts | 0.20 | weak |
| | success % / stuff % | 0.15 / 0.09 | noise |
| | YAC % | 0.12 | noise |
| | **zone YPC** | **0.05** | **NOISE** |
| | zone success % | 0.03 | **NOISE** |
| | **gap/"man" YPC** | **-0.05** | **NOISE** |

## 2. The big anti-overfit kill: RB "scheme fit" is noise
The popular lever "this back is a zone-scheme fit / gap-scheme fit" rests on per-scheme **efficiency**
(zone YPC vs gap YPC). Those carry **r ≈ 0.05 / -0.05** — i.e. **zero** year-to-year signal. The scheme
*volume* is stable only because it's the offense's identity, not the back's edge. So we do **not** build a
zone/gap RB matchup lever. (This also means "great fit for new OC's zone scheme" takes are mostly story, not
a repeatable edge.)

## 3. Receiving (pass-catching back) — mechanism TESTED, not assumed
Across 64 RBs with ≥80 routes (2025), target-earning and production rise monotonically as the box lightens:

| shell | TPRR (targets/route) | YPRR |
|---|---|---|
| vs MAN | 0.136 | 0.97 |
| vs SINGLE-HIGH | 0.169 | 1.08 |
| vs TWO-HIGH | **0.211** | **1.21** |
| vs ZONE | — | 1.24 (highest) |

So the mechanism is **real**: vs two-high / light boxes (and zone), checkdowns and RB targets open up — RBs earn
~25% more targets/route and ~12% more YPRR than vs single-high, and far more than vs man. BUT it's a **role/volume
tendency, not a player trait**: only **58%** of RBs individually post two-high > single-high YPRR (Gibbs +, Achane +,
but **Bijan is a counterexample** — better vs single-high). So we apply it as a *pass-catching-role* lever, not a
claim that a specific back is uniquely two-high-dependent. RB receiving role is moderately stable: routes r=+0.47,
targets/route +0.43, YPRR +0.42.

## 4. The two honest RB levers (what we actually built)
- **Elusive (missed-tackles-forced/att, r 0.50-0.61) — tendency.** Activates vs poor-tackling / soft run fronts
  (opponent run-defense strength as the proxy). Top backs: Kenneth Walker 0.29, Kendre Miller 0.28, James Conner 0.28,
  Cam Skattebo 0.26, Jahmyr Gibbs 0.24, Bijan 0.23.
- **Pass-catching back (volume + the two-high mechanism above) — solid.** Activates vs two-high/light-box teams +
  defenses soft to RB receiving.
- (Explosive-run rate, r 0.39-0.56, is tracked — Derrick Henry 2.23, Gibbs 2.21, Achane 2.06, Saquon 1.89 yds/att —
  but it overlaps elusiveness/big-play and isn't cleanly opponent-activated, so it informs the profile rather than
  adding a separate matchup lever.)
- A handful of pass-catching backs (Jaylen Warren, Travis Etienne) also pick up a single-year RB man/zone receiving
  lean — kept as **tendency** only.

## 5. RBs in the count (and the real takeaway)
55 RBs carry an activatable lever (passcatch 21, shootout 21, elusive 19, man/zone-lean 7/7). But **RB scores are
low** — top playoff-week lever score is Jeremiyah Love 1.13, then Gibbs 0.93 (5 smash weeks), Bijan 0.93, Conner/Benson
0.90 — vs 2.0+ for the top WRs. That is the honest finding, not a bug:

> **RB ceiling is driven by VOLUME/workload (snaps r=0.69, attempts r=0.60), which barely changes by opponent —
> not by matchup levers.** The matchup-lever count is a WR/TE-heavy tool; for RBs, prioritize projected touches and
> pass-game role, and use the levers (elusive vs bad tackling, pass-catcher vs two-high, shootout) as a small
> tie-breaker, not a driver.

## Caveats
- Elusive opponent-activation now uses **real per-defense missed-tackles-allowed** (FantasyPoints 2025 Defense
  rushing view -> `boom/defense_tackling.json`): leakiest tacklers NYG (0.20/carry), ARI (0.18), BUF/SF (0.17);
  stickiest JAX/BAL/IND (0.10). The elusive lever fires vs the top-half leakiest defenses (run-defense strength is
  only a fallback). Caveat: 2025-only (the FP Defense view defaults to current season; 2-yr stability not yet checked).
- The man/zone RB receiving leans are **single-year** (the 2-yr man/zone file is WR/TE); treated as tendency.
- Goal-line/TD equity (inside-5 carries) is **unstable** (r=0.20) and TD-dependent, so it is not a lever — it lives
  in projection variance instead.
