# FantasyPoints lever audit — every split, YoY-tested (2024 -> 2025)

Pulled programmatically from the FP Data Suite (all player reports, both seasons) and tested for
**year-over-year stability** (Pearson r, 2024 vs 2025, players above a per-report sample floor). The rule:
a split is only an honest *lever* if the player-side edge **persists** AND a mechanism + opponent activator exist.

## The headline pattern
**Usage / role traits persist. Efficiency *differentials* (by coverage/scheme) are mostly noise.**
Good players are good vs everything (overall efficiency r~0.5-0.7); the *situational delta* that a "lever"
needs is where the signal collapses. So levers should lean on stable ROLE + a few stable SKILLS, not on
single-season situational efficiency.

## WR/TE (receiving)
| signal | YoY r | verdict |
|---|---|---|
| Separation route-depth % (how deep he's deployed) | 0.84 | role-stable (deep deployment) |
| **Air yards / aDOT** (mktshr 0.89, total 0.81) | 0.81 | **STABLE role — vertical usage** |
| **Separation-WINS %** (Overall) | **0.71** | **STABLE skill — "gets open"** |
| Deep targets (volume) | 0.65 | stable role — deep usage |
| Contested targets (volume) | 0.64 | stable role — jump-ball/contested |
| **Designed-target %** (schemed) | 0.60 | stable role — manufactured usage |
| Separation-wins vs ZONE | 0.59 | moderate |
| TPRR (targets/route) | 0.57 | stable target-earning |
| Separation-wins vs MAN | 0.56 | moderate skill (usable) |
| YPRR overall | 0.53 | moderate |
| YPRR vs zone | 0.47 | moderate |
| YPRR vs man | 0.36 | weak |
| **Man-Zone YPRR delta** (the "man/zone-beater" signal) | **0.18** | **NOISE — tendency only** |
| YAC / yds-per-target over expected | 0.15 | NOISE |

Take: the best receiving levers are **air-yards/aDOT (deep role)**, **designed-target rate**, **contested role**,
**separation-wins (gets-open skill, esp. overall)**, and **slot/wide alignment** (role-stable, separate report).
The man/zone *delta* stays a tendency (only the 12 two-year-consistent man-beaters are "solid").

## QB (passing)
| signal | YoY r | verdict |
|---|---|---|
| **Scramble yards / count** | 0.64-0.67 | **STABLE — mobile/scramble (rush ceiling)** |
| Pressure % faced | 0.54 | stable (OL/hold-ball) — **bust-side** vs pressure D |
| Deep-throw attempt % | 0.40 | moderate — aggressive/deep QB |
| YPA | 0.34 | weak |
| Passer rating | 0.29 | weak |
| Completion % / over-expected | 0.13-0.21 | NOISE |

Take: **scramble-prone QB** (rush ceiling; lanes open vs man) and **deep-ball QB** are the honest QB levers;
**pressure-prone** is a downside lever vs high-pressure defenses. Accuracy metrics don't carry.

## RB (rushing)
| signal | YoY r | verdict |
|---|---|---|
| **Missed tackles forced** (total 0.61, per-att 0.50) | 0.50-0.61 | **STABLE skill — elusiveness** |
| Explosive rush yards / % | 0.39-0.56 | stable-ish — big-play back |
| Concept man/zone ATTEMPT volume & % (offense scheme) | 0.50-0.60 | stable USAGE (it's the offense) |
| Yards before contact / att | 0.33 | moderate (OL) |
| **Zone YPC / Gap(man) YPC / scheme success %** | **-0.05 to 0.05** | **NOISE — scheme-fit efficiency does NOT persist** |
| YPC | 0.18 | NOISE |
| YAC per attempt | -0.22 | NOISE |

Take: the popular **"zone-scheme vs gap-scheme fit" efficiency lever is noise** (kills feasibility item #10 as an
efficiency edge). What persists is **elusiveness (MTF)** and **explosive-run rate** (skills) + the pass-catching
role. RB matchup levers are weak from the rushing side; the pass-catching-back vs light-box/two-high read stays
the main RB lever.

## Net honest FP lever set (stability-tiered)
- **SOLID (role/usage, r>=0.6, or 2-yr-consistent skill):** air-yards/aDOT deep role; designed-target rate;
  contested-target role; slot/wide alignment; pre-snap motion; red-zone target role; separation-wins (gets-open);
  scramble-QB; 2-yr-consistent man-beater; pass-catching-back.
- **TENDENCY (moderate, r~0.35-0.55):** deep-ball QB; separation-wins vs man/zone; zone-lean; elusive/explosive RB;
  pressure-prone QB (bust-side).
- **REJECTED as noise (r<~0.25, do not build):** man-zone YPRR delta as a standalone; RB zone/gap scheme-fit YPC;
  YAC-over-expected; completion-over-expected; per-coverage YPC.
