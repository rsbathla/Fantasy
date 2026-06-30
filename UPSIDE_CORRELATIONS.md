# Upside-Correlation Board — what actually drives boom (best ball)

**Outcome:** realized 2-yr boom rate (`base2yr` b2/g2, g2>=8). **Method:** Spearman of each
feature-store signal vs that boom rate, within position. **INPUT** = independent signal
(efficiency/usage/matchup); **OUTPUT/market** = projection or ADP (circular — shown only as a
sanity reference). This is the evidence for **data-driven fusion weights** (replacing the
audit-flagged hand-set 0.42/0.23 constants).

## Top upside drivers by position (INPUT signals)
| Pos (n) | Strongest upside signals (Spearman vs boom) |
|---|---|
| **WR** (94) | recYds/g **.76**, rec/g .71, clay tgt% .70, targets/g .68, **target share .66**, **YPRR vs man .66**, route YPRR .63, EPA .63, SIS PAR .59, 1st-down/route .57, TPRR .55 |
| **RB** (58) | **snap share .64**, TD/g .61, carries/g .56, **RB rec yds/g .55**, rec yds/g .55, targets/g .55, target share .53, carry share .50 |
| **TE** (44) | **TD/g .71**, clay tgt% .61, recYds/g .60, **target share .59**, targets/g .58, snap share .55, SIS PAR/EPA .42, YPRR vs zone .41 |
| **QB** (41) | **team total TDs .59**, **Vegas implied total (W17) .58**, Vegas implied .48, **QB boom vs zone .47**, ANY/A .40, EPA .37 |

(Market/projection refs, all ~.70–.75 as expected since they already encode everything:
WR merged_rank/ADP/dk_mean ≈ .74; QB sim_mean/p85 ≈ .71.)

## Read
- **WR upside = volume + man-coverage efficiency.** Targets/yards/share lead, but **YPRR-vs-man (.66)
  and route YPRR (.63)** are orthogonal edges on top of volume — the man/zone signal pays here.
- **RB upside = snaps + the passing-down role.** Receiving (rec yds/g, targets ~.55) rivals carries
  — pass-catching backs are the ceiling play, not pure early-down rushers.
- **TE upside = touchdowns + target share.** TE ceiling is TD-dependent (.71); efficiency matters less.
- **QB upside = game environment, not volume.** Vegas implied total + team TDs + efficiency drive it;
  raw attempts don't. Stack QBs in high-total spots.

## Cross-reference: ffdataroma metric-correlations (619 WR-seasons, 2016–25)
That study (r² to *next-year FP/G*) ranks Rec Yds/G (.39), Target Share (.29), YPRR (.28), TPRR (.25).
It aligns with this board on volume + YPRR — but it measures *production*; this board measures
*upside/boom* specifically, which additionally surfaces **man-coverage YPRR** (WR) and **Vegas
environment** (QB) as boom-specific levers.

## Implication for fusion weights (replace the hand-set constants)
Weight by position, proportional to these correlations:
- WR: volume (targets/share/recYds) + **YPRR/man-YPRR** + EPA/PAR; de-emphasize generic adot.
- RB: snap share + **receiving role** + TD/workload.
- TE: TD rate + target share (efficiency is secondary).
- QB: **Vegas implied total + team TD environment** + ANY/A/EPA; drop volume-only inputs.

## Caveats
Cross-sectional, single recent window; volume signals are collinear with each other and with boom
(more snaps → more boom chances), so treat the *efficiency* signals (YPRR/man, EPA, PAR) as the
orthogonal edge on top of volume. Market signals (ADP/merged_rank) correlate ~.74 because they
already price most of this — the real edge is where an independent signal **diverges** from the market.
