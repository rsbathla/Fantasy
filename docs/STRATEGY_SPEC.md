# STRATEGY_SPEC — Construction Decision Rules (DK Best Ball 2026)

**Owner:** Agent B (Contract 2). **Consumed by:** `engine/decision_tree.py` (Contract 4) and the
draft assistant. Every rule below is grounded in the **format mechanics**, not generic best-ball lore.

---

## 0. The format dictates everything

DraftKings Best Ball, 12-team pods, 18 roster spots, lineup = **QB / 2 RB / 3 WR / 1 TE / 1 FLEX** (9 starters, best ball auto-optimizes weekly).

Two **structurally different** objectives stacked on one roster:

| Gate | Weeks | Rule | What wins it |
|------|-------|------|--------------|
| **Advance** | W1–14 | Top **2 of 12** on **cumulative** points | **VOLUME / floor** — you must *bank* points for 14 weeks. The one gate where "how much you score" matters as much as "how high you spike." |
| **Survive** | W15 | Single week, top **50%** | **CEILING** — one-week spike |
| **Survive** | W16 | Single week, top **50%** | **CEILING** — one-week spike |
| **WIN (finals)** | W17 | Single week, top **10%** | **CEILING, maximized** — this is the money week |

Title equity = `P(advance) × surv_W15 × surv_W16 × win_W17` (the survival chain). Two consequences drive the whole build:

1. **Advancement is the binding gate.** In a 2/12 pod, a great anchor with weak advancement is dead (audit: a 7%-advance roster finished 10th). You cannot ceiling your way out of missing the playoffs. **Floor/volume first, through ~the first 7 rounds.**
2. **You cannot win the money week on floor.** The live $1M entry finished 11th/12 with **zero alpha-ceiling WRs (p95 ≥ 33)** while pod leaders had two. Once advancement is reasonably secured, **every remaining pick is a ceiling pick**, and it should be a ceiling pick **scheduled to fire in W15–17** (that is what `playoff_overlay.csv` prices).

> **One-line mental model:** *Rounds 1–7 buy your way INTO the playoffs (volume + elite ceilings that happen to be early). Rounds 8–18 buy your way to WINNING the playoffs (W15–17 ceiling + correlation).*

---

## 1. Positional build curve over 18 rounds

**Season-long targets (end-of-draft):** **QB 2–3 · RB 5–6 · WR 8–9 · TE 2–3** (= 18). WR-heavy core; never thin at WR.

### Round-by-round target band (snake-agnostic; adjust ±1 to value)

| Rounds | Primary intent | Typical adds | Running target by end of band |
|--------|----------------|--------------|--------------------------------|
| **1–2** | Best ceiling-volume players, position-agnostic | Elite WR or elite dual-threat RB | 0–1 QB, 0–1 TE allowed if elite |
| **3–5** | Fill the engine: secure RB floor + WR core | RB2/RB3, WR2/WR3 | RB ≥ 2, WR ≥ 3 |
| **6–8** | Round out starters; **first QB window opens** | QB1, WR4, RB4, or elite-TE if you waited | QB ≥ 1, RB 3–4, WR 4–6, TE 0–1 |
| **9–11** | **Playoff-ceiling tilt begins** (see §4) | High-`playoff_up` WR/RB, QB2 (preferably stack), TE1/TE2 | QB 1–2, WR 6–7, TE 1–2 |
| **12–15** | Stack completion, bring-backs, upside dart WRs | Same-team pass-catcher #2, opponent bring-back, high-CV "boom" WR | WR 7–8, RB 5, QB 2–3 |
| **16–18** | Pure W15–17 lottery tickets + bye patching | Backup-RB-with-a-path, late TE, ceiling WR on a soft W17 slate | hit final targets |

### Positional rules (grounded)

- **QB — take 2–3, BUY the value tier, mostly mid/late.** QBs as a group have the highest *raw* p95 but the **lowest CV and lowest spike% of any position** (see sim: QB spike ~0.07–0.15 vs WR/RB ~0.16). They are the *most predictable* scorers, so the market overpays the top few and you gain little ceiling edge paying up. Take **one QB in rounds 6–9**, a **second in rounds 11–14 (ideally as a stack — §2)**, and an optional **third in rounds 16–18** only to fix a bye or add a high-`playoff_up` arm. **Do NOT over-invest in 3 mid QBs** — that was an explicit loss driver in the live draft. Exception: an *early* QB is only justified if he is a rushing-ceiling QB whose **playoff slate is soft** (e.g. top of the `playoff_overlay.csv` QB list) AND he anchors a stack you intend to build.
- **RB — take 5–6, FADE the committee, secure the floor early.** RB is your **advancement insurance** (carries = bankable volume, low week-to-week variance in the rushing model — `volr` is script-independent). Lock **2 RBs with a clear lead-back role by round 5**. After that, **fade pure committee backs** (low carry_share, no receiving role) — they have neither floor nor ceiling. Late RBs should be **handcuffs/backups with a standalone path** (pass-down role or one injury from a workhorse), which carry real W15–17 spike equity.
- **WR — take 8–9, this is the core, get an alpha ceiling early.** WR is where single-week ceilings live (top WR p95 38–47 vs mid WR 25–29). **You must own ≥1 alpha-ceiling WR (p95 ≥ ~33), ideally two**, taken in rounds 1–5 — the ceiling-deficit loss is the most repeatable failure mode. Build **depth 8–9 deep** because best ball needs three WR starters + FLEX every week and WR is the highest-variance slot (a thin WR room caps your weekly max). Mid/late WRs should skew **high-CV "boom"** types and, from round ~9 on, **high `playoff_up`**.
- **TE — take 2–3; elite-or-wait, no middle.** TE means correlate best with QBs in the model (Clay backtest r=0.74, highest of any position) and an elite TE is a genuine weekly-ceiling lever (p95 to ~36). **Two clean paths:**
  - **Elite TE early (rounds 2–4):** if a true alpha TE is there at a discount, take him — he is a positional ceiling cheat code and a premium stack partner. Then you only need **one** more TE (a late dart), so 2 total.
  - **Wait (default):** if you pass the alpha tier, **do not pay up for the muddy TE middle** — take **two** TEs in rounds 9–14, prioritizing TEs on **good offenses with soft W15–17 slates** (high `playoff_up`), then optionally a third late.

---

## 2. Stack / anchor logic — built to FIRE in the playoffs

**Why stack at all:** correlation. The sim reproduces real 2024–25 correlations — **QB↔WR1 r≈0.35, QB↔WR2 r≈0.34, QB↔WR3 r≈0.26, QB↔TE strong**, while **WR↔WR ≈ 0** (uncorrelated). Stacking converts one good game script into **multiple** simultaneous booms in the *same week* — exactly the spike shape the single-week playoff gates reward. Whole-lineup game-stack lift is **modest but real (~+3–6% on W17 p95)**, and crucially it raises the **right tail**, which is the only thing W17 (top 10%) pays.

### The anchor (your one concentrated bet per entry)

- **Concentrate WITHIN an entry: 1 anchor game, 4–5 correlated pieces** ≈ **+15% finals tail at equal mean** vs a scattered roster. Pick **one** game to be your "fire in the playoffs" bet and load it.
- **Diversify the anchor game ACROSS the portfolio** (900-entry plan): no single finals game > ~8.6% of entries; spread anchors across all 16 W17 games (`anchor_allocation_900.csv` is the Phase-2 target). Concentrated lineups, diversified portfolio.

### Build the anchor TWO-SIDED

Canonical shape, in priority order:

1. **QB + 1–2 same-team pass-catchers** (WR1/WR2 and/or the TE). This is the core correlation engine.
2. **+ one opponent bring-back** (a pass-catcher or RB from the OTHER team in that game). Bring-back correlation is **positive and total-dependent: r≈0.16 in high-total games vs ≈0.06 in low-total games.** So a bring-back only earns its spot in a game you expect to be **high-scoring** (shootout) — which is precisely what a high combined `playoff_overlay` matchup signals.

**Completion ladder the assistant scores (best → worst):**
`complete (★ has bring-back) > build (QB + catcher, no bring-back yet) > seed (one piece, no QB yet)`.

### Orient the stack to the PLAYOFF weeks

This is the Best-Ball-specific twist: a stack is only worth the concentration cost if it **fires in W15–17**, not W4.

- **Anchor on a game whose W17 (and ideally W15/W16) matchup is favorable** for *both* sides — i.e. both teams have a high `playoff_up` environment (strong offense and/or soft opponent). Use the overlay's per-week multipliers, not season-long talent.
- **Rank candidate finals games by TAIL (blow-up p99), NOT by O/U.** A mid-total game with two volatile offenses can out-ceiling a high-total chalk game. The overlay's matchup multiplier is a tail proxy; prefer the games where *both* sides spike.
- **Over-stack penalty at 5+ same-game pieces** — past 4–5 correlated pieces you are buying redundant variance and starving other roster needs. Stop at 4–5.

---

## 3. Bye-week spread rules

The model's bye finding is specific and counterintuitive: **only UNCORRELATED bye pileups hurt.**

- **Hard rule: never draft a same-bye pileup across DIFFERENT teams.** If three players from three different teams all sit Week 7, your W7 lineup collapses with no upside to compensate. Penalize players on a bye **beyond your single biggest same-team stack**.
- **Stacks are EXEMPT.** Stacking a team means those players *share* a bye by construction — that is the price of correlation and it is already paid for by the upside. Do **not** penalize a stack for its shared bye (`byes_2026.json`: stacked teams all bye the same week; that is fine).
- **Practical:** track byes as you draft; the assistant flags only the *uncorrelated* cluster (`+CLUSTER` warning). Aim to have **no single bye week wipe out > ~2 starters** outside your main stack. Bye weeks are all in **W5–W14** (the *advancement* window), so a bye pileup directly damages the binding gate — another reason to spread.
- **Playoff weeks (W15–17) have NO byes in 2026** — every team plays all three. So bye-spreading is purely an advancement-window concern; it never touches the overlay.

---

## 4. How the W15–17 overlay tilts MID/LATE picks (the core integration)

`engine/playoff_overlay.csv` gives every gradeable player `w15_up, w16_up, w17_up` and a normalized
`playoff_up` (~0..1) = **own single-week ceiling × team's playoff-week matchup quality, W17-weighted heaviest.**

**Rule — the overlay is a TIE-BREAKER early and a DRIVER late, never a floor-replacer:**

- **Rounds 1–7 (advancement window): essentially IGNORE `playoff_up`.** Draft for volume, floor, and best-available ceiling-volume. Banking points to *reach* the playoffs dominates; tilting these picks toward W17 matchups trades away advancement equity you cannot afford to lose. (At most, use `playoff_up` to break a dead-even tie between two otherwise equal players.)
- **Rounds 8–10: `playoff_up` becomes the primary TIE-BREAKER.** When two candidates are within a small band on blended Δtitle/Δadv (or board rank), **take the higher `playoff_up`.** This is the inflection point — your starters are mostly set, so marginal picks should start being scheduled for the weeks that pay.
- **Rounds 11–18: `playoff_up` is a primary DRIVER.** Among players of comparable value, **actively prioritize high `w17_up` first, then `w16_up`/`w15_up`.** Late picks contribute almost nothing to advancement (they rarely crack the weekly best-ball lineup in W1–14) but a late WR/TE/QB on a soft W17 slate is a **cheap finals lottery ticket** — exactly the asset the money week rewards. Prefer **W17-heavy** upside over evenly-spread upside because W17 is the only top-10% gate.
- **Stack interaction:** when completing a stack (§2), filter candidate same-team and bring-back pieces by `playoff_up` — pick the pass-catcher / bring-back whose **game environment is best in W15–17**, so the stack fires in the right weeks.

**Concrete tilt formula for the engine (Contract 4 alignment):**
base score = `0.6·dTitle + 0.4·dAdv` (per CONTRACTS Contract 4). From **round ≥ 8**, add a playoff tilt:
```
score = 0.6*dTitle + 0.4*dAdv + lambda(round) * playoff_up
lambda(round) = 0                         for round <= 7
              = 0.02 * (round - 7)        for 8 <= round <= 18   # 0.02 at R8 ... 0.22 at R18
```
i.e. the playoff_up bonus grows linearly from ~0 in the mid-rounds to a strong tilt in the final rounds,
matching "break ties toward upside at R8–10, drive picks by upside from R11 on." Use `w17_up` as the
tie-breaker within equal `playoff_up` when finishing a finals stack.

---

## 5. Decision checklist (what the tool enforces every pick)

1. **Am I on track to ADVANCE?** (rounds 1–7: volume/floor first; ≥1 alpha-ceiling WR by R5; 2 lead RBs by R5).
2. **Best ceiling-volume available**, valued vs **MERGED RANK** (not raw ADP): bonus if fell ≥ 8, escalating penalty if reaching.
3. **Does it build/complete my anchor?** complete (★bring-back, high-total game) > build > seed; stop at 4–5 pieces.
4. **Bye check:** flag only *uncorrelated* pileups beyond my main stack; stacks exempt.
5. **Positional need** vs targets (QB 2–3 / RB 5–6 / WR 8–9 / TE 2–3); fade committee RBs; elite-TE-or-wait.
6. **From R8 on:** break ties — and from R11 on, actively drive — toward **`playoff_up` (W17-weighted)**.

**North star:** *Get in on volume, then win the money week on scheduled ceiling. Advancement is the gate; W17 is the prize.*
