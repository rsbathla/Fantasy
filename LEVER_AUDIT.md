# Ceiling-Lever Audit — what splits, with what sample/mechanism, and who has them

Built from the tweet corpus (what analysts discuss) + every splittable dataset we hold. Each candidate
dimension is judged on: **sample** (enough per-player data), **mechanism** (real, not coincidence),
**opponent-controllability** (can a matchup activate it), and **stability** (persists year-to-year).

## What analysts actually talk about (tweet frequency, ~5,040 tweets)
volume/usage 246 · deep/aDOT 244 · slot/alignment 221 · **red-zone/TD 199** · QB pressure 124 ·
zone 104 · route-type 103 · man 101 · play-action 47 · motion 46 · script/pace 41 · box-count 18 ·
single/two-high 16 · matchup/CB 16 · home/away 10

## IN THE MODEL (cleared sample + mechanism + opponent-controllable)

### Man-beater (man vs zone YPRR, NFL CoverageType)  — 48 players qualify
*man-coverage skill is population-stable (solid). Activates vs man-heavy defenses.*
- Terry McLaurin (WR) — man 2.69 vs zone 1.24 (Δ+1.45)
- Jordan Addison (WR) — man 1.93 vs zone 0.86 (Δ+1.07)
- Tory Horton (WR) — man 1.21 vs zone 0.14 (Δ+1.07)
- Bucky Irving (RB) — man 2.34 vs zone 1.31 (Δ+1.03)
- Dylan Sampson (RB) — man 2.46 vs zone 1.46 (Δ+0.99)
- Jack Bech (WR) — man 1.21 vs zone 0.23 (Δ+0.98)
- Nico Collins (WR) — man 2.3 vs zone 1.36 (Δ+0.95)
- Greg Dulcich (TE) — man 2.57 vs zone 1.62 (Δ+0.95)

### Zone-beater  — 46 players qualify
*zone splits persist less (tendency). Activates vs zone-heavy defenses.*
- Brashard Smith (RB) — zone 3.57 vs man 1.72 (Δ-1.84)
- Pat Freiermuth (TE) — zone 3.15 vs man 1.44 (Δ-1.71)
- Luke McCaffrey (WR) — zone 3.63 vs man 1.99 (Δ-1.64)
- Rashee Rice (WR) — zone 3.92 vs man 2.45 (Δ-1.47)
- Dalton Kincaid (TE) — zone 4.23 vs man 2.79 (Δ-1.44)
- Jayden Reed (WR) — zone 3.13 vs man 1.69 (Δ-1.44)
- Calvin Ridley (WR) — zone 2.99 vs man 1.87 (Δ-1.12)
- Ben Sinnott (TE) — zone 2.36 vs man 1.32 (Δ-1.05)

### Motion weapon (in vs out of motion YPRR)  — 29 players qualify
*usage-stable; activated by offenses that scheme him in motion.*
- Kyle Williams (WR) — 2.2 vs 0.3 YPRR (49% motion)
- KeAndre Lambert-Smith (WR) — 1.46 vs 0.0 YPRR (51% motion)
- Ben Sinnott (TE) — 1.44 vs 0.33 YPRR (40% motion)
- Alec Pierce (WR) — 2.64 vs 1.56 YPRR (51% motion)
- Rashee Rice (WR) — 3.23 vs 2.16 YPRR (39% motion)
- Kayshon Boutte (WR) — 1.93 vs 0.95 YPRR (52% motion)
- Tank Dell (WR) — 2.17 vs 1.2 YPRR (41% motion)
- Tee Higgins (WR) — 2.42 vs 1.49 YPRR (44% motion)

### Red-zone target hog (inside-20 looks/g)  — 20 players qualify
*TD equity is the #1 ceiling driver; red-zone role is sticky (solid). Activates vs RZ-soft defenses.*
- Davante Adams (WR) — 2.0 i20/g, 42 end-zone
- Amon-Ra St. Brown (WR) — 1.9 i20/g, 20 end-zone
- Ja'Marr Chase (WR) — 1.8 i20/g, 26 end-zone
- Trey McBride (TE) — 1.6 i20/g, 27 end-zone
- Rashee Rice (WR) — 1.6 i20/g, 5 end-zone
- Tee Higgins (WR) — 1.4 i20/g, 27 end-zone
- Drake London (WR) — 1.3 i20/g, 23 end-zone
- George Pickens (WR) — 1.3 i20/g, 31 end-zone

### Slot-dominant (alignment)  — 12 players qualify
*role-stable; activates vs a weak nickel/slot defender.*
- Josh Downs (WR) — 82% slot
- DeMario Douglas (WR) — 79% slot
- KaVontae Turpin (WR) — 75% slot
- Jayden Reed (WR) — 75% slot
- Christian Kirk (WR) — 75% slot
- Wan'Dale Robinson (WR) — 72% slot
- Khalil Shakir (WR) — 71% slot
- Ladd McConkey (WR) — 68% slot

### Fewer ceiling weeks in-division  — 17 players qualify
*multi-year per-game; a real schedule lever (tendency).*
- D'Andre Swift (RB) — ceil 0% in-div vs 43% out
- Khalil Shakir (WR) — ceil 0% in-div vs 38% out
- Josh Allen (QB) — ceil 0% in-div vs 36% out
- Derrick Henry (RB) — ceil 8% in-div vs 36% out
- Ty Johnson (RB) — ceil 8% in-div vs 36% out
- David Montgomery (RB) — ceil 10% in-div vs 38% out
- Darius Slayton (WR) — ceil 9% in-div vs 37% out
- DeVonta Smith (WR) — ceil 9% in-div vs 37% out

## CONSIDERED BUT NOT ADDED (and why) — guarding against overfitting

- **Home/away** — only 10 tweet mentions; small per-player effect, high overfit risk. SKIP.
- **Single-high / two-high shell** — 16 mentions; our own backtests show the split barely persists year-to-year. Kept only as a low-confidence *tendency* inside the vertical read, not a standalone lever.
- **Route type** (slant/dig/post/go) — data exists (FP RouteType) and 103 mentions, but it's **not opponent-controllable** (no clean matchup trigger), so it informs archetype, not a lever. Candidate for a 'route-tree' descriptor later.
- **QB pressure** — 124 mentions, but we only have the *rate faced* (PRESS%), not a clean produced-under-pressure split. Captured as a QB context/bust factor, not a lever. Would need a pressure-split export.
- **Box count (RB)** — 18 mentions; no clean per-player box-count split in our data. Using RB zone/gap scheme fit + pass-catching-back two-high instead.
- **Play-action** — 47 mentions; offense/QB-level, thin per-player. Candidate if a PA split export is added.

## Net result
258/359 players carry >=1 disciplined ceiling lever. A ceiling is flagged when several stack in one matchup; single noisy splits never drive it.
## Empirical data audit (not just tweets — tested the actual data)
Each candidate was tested for **stability/spread**, not assumed:
- **Home/away** — could not establish a stable year-over-year per-player split (insufficient persistent signal). **Verdict: NOISE → not a lever** (matches its near-bottom tweet frequency).
- **Route-type vertical share** (FP RouteType) — across 325 WRs the spread is tiny (std ≈ 2.4%); doesn't differentiate players. **Verdict: weak → archetype color, not a lever.**
- **QB man vs zone** (FP Passing/CoverageType) — strong signal, but *every* QB is better vs zone (man+pressure is harder), so direction is uniform. Reframed as **relative man efficiency** (man Y/A percentile among QBs). **Verdict: ADDED as a QB lever** — top-tier "handles man → exploit man-heavy/blitz D" (e.g. Allen elite vs man); bottom-tier "struggles vs man" (Mahomes 5.4, Burrow 5.1 Y/A → fade vs man-heavy/blitz).
- **Sample discipline tightened:** coverage min raised to 60 routes/side, motion to 60 total + 20/side, coverage lever Δ to 0.5 — killing the small-sample extremes (e.g. 40-route rookies) that were polluting standout lists.

## Final lever set (data + mechanism + opponent-controllable, with confidence)
man-beater / zone-beater (WR, YPRR) · QB handles/struggles-vs-man (relative Y/A) · motion weapon (in/out YPRR) ·
slot-dominant · red-zone target hog (i20/g) · vertical (explosive/deep) · pass-catching back (two-high) ·
fewer-ceilings-in-division · shootout environment. Each tagged solid vs tendency; a ceiling is flagged when several stack.
