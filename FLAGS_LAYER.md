# Flags Layer — total + playoff risk flags (2026)

`build_flags_layer.py` attaches a **data-backed risk flag set** to every player, with a clear split
between flags that affect the **whole season** and flags that specifically threaten the **fantasy-playoff
window (NFL Weeks 15-17)**. Output: `flags_2026.json`, `flag_rank_delta.csv`, plus fields written back
into `dossier_data.json` (per player + per team `flag_rollup`).

## Two headline numbers per player
- **⚑ Total flags** — every risk on the player.
- **◆ Playoff flags** — only the risks that specifically threaten Weeks 15-17.

A flag is *playoff-relevant* when it makes the championship weeks **worse than the rest of the season**.
An early-season injury that resolves by December is a TOTAL flag but **not** a PLAYOFF flag; a player who
is out all year, or who faces a brutal W15-17 slate, **is** a playoff flag.

## Flag types
| Code | Category | Meaning | Playoff? | Source (real/verified) |
|---|---|---|---|---|
| INJ | availability | injury with a cited games-missed estimate; haircuts projection | only if NOT healthy by playoffs | roster_flags_2026.json `availability` (cited) |
| DUR | durability | elevated re-injury risk (e.g., 2nd ACL same knee) | no | cited research |
| OUT | roster | not a usable 2026 asset (unresolved transaction) | **yes** (out all year) | roster_flags_2026.json `non_usable` |
| FA | roster | unsigned free agent, no 2026 team | **yes** | roster_flags_2026.json |
| SCH | scheme | new play-caller's scheme reduces one of his levers | no (season-wide) | scheme_2026.json off dials |
| OL | oline | below-average OL (tier ≤2) caps his deep-shot lever | no (season-wide) | boom/oline_2026.json (verified) |
| PO-SLATE | playoff | tough W15-17 opponent slate (mean opp unit pctl ≥64) | **yes** | defense.json + schedule2026.json |
| PO-COLD | playoff | his matchup-levers cool in W15-17 (vs a normal slate) | **yes** | lever_sum playoff vs season mean |
| PO-BYE | playoff | team bye falls in W15-17 | **yes** | schedule2026.json |

## Availability multiplier (the only flag that changes a number)
`avail_mult = (17 − games_missed_mid) / 17`, using the cited June-2026 reporting midpoint of expected
games missed. `adj_pg = proj.pg × avail`. Current overlay:

| Player | Verdict | ~games missed | avail | healthy by playoffs |
|---|---|---|---|---|
| Zach Charbonnet (RB,SEA) | early-season risk | 5.5 | 0.68 | yes |
| Tank Dell (WR,HOU) | week-1 monitor | 2.5 | 0.85 | yes |
| George Kittle (TE,SF) | week-1 monitor | 2.0 | 0.88 | yes |
| Malik Nabers (WR,NYG) | week-1 monitor | 1.75 | 0.88 | yes |
| Tucker Kraft (TE,GB) | full go (mild) | 0.5 | 0.97 | yes |
| Jonathon Brooks (RB,CAR) | full go + durability | 0.0 | 1.00 | yes |

Other flags (SCH/OL/PO-*) are surfaced as **risk counts, not point haircuts** — we don't invent magnitudes.

## Does it change the ranks? (flag_rank_delta.csv)
Re-sorting each position by availability-adjusted projection moves exactly the discounted players
(others only shift by the cascade). The substantive movers:

| Player | Pos rank (proj → adj) | spots | proj → adj pg |
|---|---|---|---|
| Zach Charbonnet | 24 → 41 | −17 | 12.0 → 8.2 |
| Tank Dell | 69 → 77 | −8 | 6.3 → 5.4 |
| Malik Nabers | 12 → 20 | −8 | 14.7 → 12.9 |
| George Kittle | 3 → 5 | −2 | 12.7 → 11.2 |
| Tucker Kraft | 13 → 15 | −2 | 9.5 → 9.2 |

Note: the headline board rank stays **ADP-anchored** (the market already prices much of this); the
availability overlay (`adj_pg`, `→` on the board) is a *model lens* to read next to ADP — where the model
discount is bigger than the ADP discount, that's a fade signal.

## Where to see it
- **Dossier** (`dossier.html`): each player card shows `⚑N ◆M`, a Risk-flags detail block, and the
  availability-adjusted projection; each team header shows a flag rollup badge.
- **Rankings board** (`rankings.html` / `rankings_2026.csv`): `⚑` and `◆PO` columns + `→adj` proj.
- **Counts** (`flags_2026.json` meta): 359 players, 117 flagged, 100 with playoff flags.

## Pipeline order
`build_dossier.py → build_lever_count.py → build_flags_layer.py → build_lever_board.py → build_rankings.py → render_dossier.py`
