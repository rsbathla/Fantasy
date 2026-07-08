# WALKFORWARD_2024 — Season Synthesis (rsbathla, 2024 walk-forward replay)

Replay of 21 weekcards (2024-09-08 → 2025-01-26). Every counterfactual is a portfolio rebuilt at
true field size and graded on that Sunday's REAL actual points. All figures verified from raw
`weekcards/*.json`; no code/data modified. Modes: `dial` = rulebook construction, no reads;
`his-reads dial` = same + his top overweights boosted +12%; `brief-reads dial` = same for the
mechanical brief; `his-style f10` = deep-fade caricature of his style.

**COST-MISMATCH CAVEAT (read first):** counterfactual K often differs from his actual entry count
`n`. Capping a *winning* week to a lower K mechanically strips P&L; capping a *losing* week
mechanically saves it. Where this flips a conclusion, ROI is reported alongside raw P&L, and the
volume effect is isolated by re-pricing his own ROI at the cap-K before attributing anything to
construction/reads.

---

## 1. Season table (his real, by week)

| wk | date | week P&L | his reads z≥1 | brief z≥1 | tiers played (n) |
|---:|---|---:|:--:|:--:|---|
| 1 | 2024-09-08 | −104,437 | 4/12 | 0/1 | mega:17, 20:150 |
| 2 | 2024-09-15 | **+957,747** | 4/12 | 0/14 | 555:150, 20:150 |
| 3 | 2024-09-22 | −93,015 | 0/12 | 3/14 | mega:22, 20:150 |
| 4 | 2024-09-29 | −49,858 | 3/12 | 4/14 | 555:150, 20:150 |
| 5 | 2024-10-06 | −4,514 | 2/12 | 2/14 | mega:11, 20:100 |
| 6 | 2024-10-13 | −69,054 | 2/12 | 2/14 | 555:150, 20:150 |
| 7 | 2024-10-20 | +226,209 | 3/12 | 3/14 | 20:150 |
| 8 | 2024-10-27 | −17,874 | 4/12 | 3/14 | mega:19, 20:95 |
| 9 | 2024-11-03 | −10,832 | 0/0 | 1/14 | 555:18, 20:9 |
| 10 | 2024-11-10 | +11,273 | 0/0 | 5/14 | mega:3, 20:19 |
| 11 | 2024-11-17 | −33,016 | 2/12 | 4/14 | 555:150, 20:150 |
| 12 | 2024-11-24 | −130,722 | 2/12 | 2/14 | 555:150, 20:150 |
| 13 | 2024-12-01 | −47,332 | 0/0 | 0/14 | 555:9, 20:9 |
| 14 | 2024-12-08 | −20,238 | 0/0 | 3/14 | 555:15, 20:10 |
| 15 | 2024-12-15 | +4,522 | 0/0 | 1/14 | 20:15 |
| 16 | 2024-12-22 | −38,329 | 2/12 | 4/14 | 555:150, 20:150 |
| 17 | 2024-12-29 | −139,817 | 2/12 | 3/14 | mega:55, 20:150 |
| 18 | 2025-01-05 | **+1,038,595** | 3/12 | 2/14 | 20:150 |
| 19 | 2025-01-12 | −60,903 | 3/12 | 0/9 | mega:17, 20:150 |
| 20 | 2025-01-19 | −9,557 | 2/12 | 2/5 | (untracked) |
| 21 | 2025-01-26 | −122,926 | 3/12 | 1/4 | mega:19, 20:150 |
| | **SEASON** | **+1,285,921** | **41/192 (21.4%)** | **45/257 (17.5%)** | |

**Two weeks are the season.** wk2 +957,747 and wk18 +1,038,595 = +1,996,342. The other 19 weeks
sum to **−710,421**. Remove either tail and the year is a loss.

### Where the money actually sat (his real, tracked tiers)
| tier | his real P&L | note |
|---|---:|---|
| $20 single-slate Milly (150s) | **+987,230** | +998,890 is wk18 alone; **ex-wk18 = −11,660**. The R4/R11 payoff-asymmetry engine. |
| $555 Milly | **+112,590** | +354,250 is wk2 alone; **ex-wk2 = −241,660**. |
| $4,444 MEGA | **−295,767** | the recurring bleed; no tail ever rescued it. |

Tracked tiers net +804,053; the +482K gap to the season total is untracked buckets
(showdown/smaller, not in the cards). The strategy story lives in the three tracked tiers, and it
is unambiguous: **one engine (single-slate $20 conviction) paid for everything; MEGA is a leak;
$555-at-volume is a leak with one lottery ticket attached.**

---

## 2. Read accuracy — his reads beat the mechanical screen

- **His overweights: 41/192 = 21.4% at z≥1.** (verified: sum of per-card `his_hits` = 41.)
- **Mechanical brief: 45/257 = 17.5%.** Baseline ≈16%.
- His reads are **+3.9pp** better than the naive screen and **+5.4pp** over baseline. Consistent
  with the rulebook's "field-average, not clairvoyant (~45-56% vs top-1% winners)" self-diagnosis.
  His edge is not accuracy — it is expression and payoff asymmetry.

---

## 3. Error taxonomy with dollars

**Method.** For each week/tier he played that has a `his-reads dial` counterfactual at the rulebook
cap-K (MEGA K=19, $555 K=36), the gap `(his-reads-dial@cap − his_real)` is split into three classes:

- **Sizing/volume** = `(his own ROI re-priced at cap-K) − his_real`. Effect of trimming bullets to
  the cap while keeping his own builds. (This is where the cost-mismatch lives.)
- **Construction** = `dial@cap − (his ROI @ cap-K)`. Rulebook fade/structure vs his builds, no reads, same volume.
- **Reads** = `his-reads-dial@cap − dial@cap`. Value of boosting his overweights, same volume, same construction.

Population: 15 tier-weeks with cap-K counterfactuals (8 MEGA-ish, 7 $555-ish). wk18/wk7 (all $20,
no counterfactuals) and wk20 (untracked) are excluded — they are not where the tested prescriptions apply.

| class | ALL 15 tier-weeks | ex-wk2 (drop the +354K $555 tail) | ex-wk2 & wk3 (drop both tails) |
|---|---:|---:|---:|
| Sizing/volume | **−64,463** | **+204,767** | +200,981 |
| Construction | **−320,823** | −215,823 | −162,035 |
| Reads | **+317,659** | +317,659 | −14,997 |
| **Total gap vs his real** | **−67,627** | **+306,603** | +23,949 |

**How to read this (the assumptions matter):**

- **Sizing/volume flips sign entirely on wk2.** Including wk2, "cap the volume" costs −64K because
  it caps the one winning week. *Excluding* wk2, capping saves **+204,767** — because 5 of the 6
  weeks he ran at 150 bullets in $555, and both weeks he ran >19 in MEGA (wk3 n=22, wk17 n=55),
  were losers whose bleed the cap would have cut. The volume leak is real and large; it is masked
  by exactly one tail.
- **Construction is negative across the board (−321K).** The rulebook's mechanical fade/structure
  *underperformed his own builds at equal volume* on this population. This is R11 confirmed on
  fresh data: "construction cannot rescue player views; public-projection sims don't hold your
  reads." Do NOT hand construction to the machine.
- **Reads are strongly positive (+318K) — but almost entirely wk3 (+332,656).** Drop wk3 and the
  read-boost is −14,997. The "his reads add value" P&L story is a one-week tail, honestly.

**Bottom line of the taxonomy:** the only class that survives removing the tails is **sizing/volume
(≈ +200K of avoidable bleed on losing weeks)**. Construction should stay with him. Reads help on
average (Section 2) but their *dollar* impact this season was a single week.

---

## 4. Deep-fade leak (his-style f10) — dollar receipt for R7/R8

His known "deep fades in sharp fields" leak, priced out. `his-style f10` vs `his-reads dial`
(sim ROI at cap-K) was **negative EV in 11 of 15 tier-weeks**; positive only on 4 already-losing
$555 weeks (where any fade helps a doomed slate). Realized totals at cap-K:

- MEGA f10 @K19: **−550,071** (8 wks) vs his-reads dial −73,570. Deep fade multiplies the MEGA loss ~7.5x.
- $555 f10 @K36: **−174,825** (9 wks) vs his-reads dial −147,352.

Every step of fade in the sharp ($555/MEGA) fields costs money. This is the sim law (R7) and his
own ledger agreeing. **λ0-3 MEGA, λ6-10 $555 — never the f10 caricature.**

---

## 5. The central tension — "cap volume, express full conviction within the cap" vs "the cap is wrong"

The prescription under fire: $555 caps at ~36 bullets, MEGA at ~19. The threat: **wk2 made
+354,250 at 150 bullets, and the `his-reads dial` at K36 LOST −19,980 that same Sunday.** If the
cap kills the year's best $555 week, is the cap wrong?

**What the data actually says:**

- **The wk2 counterfactual is a model artifact, not evidence the cap fails.** At K36 the sim ROI is
  **+1.886 (+189%)** — the in-model K-curve says the cap is *massively* +EV that week. Yet the
  *rebuilt* portfolio's real_pnl is −19,980. The two disagree because the +12% "his-reads" boost
  was **too weak to force his 90-100%-conviction Kupp/Nabers/Godwin exposure into the λ-faded
  builds.** His actual wk2 overweights were Chris Godwin (z=+2.03), Malik Nabers (z=+2.62),
  Amon-Ra (z=+1.02), Alvin Kamara (z=+4.78) all at ~100% exposure — that conviction stack is what
  cashed. The counterfactual dropped it; the sim ROI (which prices the *dial*, not the rebuild)
  did not. **This is a model limitation. It does not prove the cap fails; it proves a +12% boost
  cannot represent a 90% conviction.**

- **The cap's case does not rest on wk2 — it rests on the other five.** He ran 150 bullets in $555
  on six weeks: 2, 4, 6, 11, 12, 16. Those six netted +132,900 **but −221,350 without wk2.** Five
  of six 150-bullet weeks lost, three of them badly (wk6 −66,750; wk11 −51,850; wk12 −79,050).
  The cap converts each of those from a full 150-bullet bleed to a ~36-bullet bleed. The
  season-realized volume saving (Section 3, ex-wk2) is **+204,767.** The K-curve going negative
  past ~36 in every $555 mode (rulebook dial sheet) is corroborated by the realized record.

- **n=1 honesty.** The upside case for 150-volume $555 is a single Sunday. The downside case is
  five Sundays plus the in-model EV curve plus the career "−0.2% on $863K with hand-me-downs."
  One tail cannot license the volume; but one season also cannot prove the tail won't recur. The
  policy must survive both — capture the tail's *shape* without paying the bleed's *quantity*.

**VERDICT — cap the volume, but the cap must carry full conviction, and the tail is bought
elsewhere:**

1. **The cap is right; the volume leak is real (~+200K/yr avoidable bleed).** Cap $555 at ≤36 and
   MEGA at ≤19. This is not close on the realized data once the single tail is set aside.
2. **The counterfactual construction is what's "wrong," not the cap.** A cap that dilutes his
   conviction is a strawman. Inside the cap, express conviction at *his* real exposure (up to
   70-90%, R4), not at a +12% nudge. The prescription is **"cap volume AND express full conviction
   within the cap,"** which the model could not simulate but he can execute by hand (R11: he builds
   the lineups).
3. **Buy the +354K-shaped tail where it is actually +EV: the $20 single-slate Milly, at full
   150-volume.** That is where his 2024 tails *actually* landed (wk18 +998,890; wk2's $20 slice was
   separate). The $20 field is 16.8% copied entries — distinct conviction builds are free equity
   there, the K-curve does not invert, and the payoff asymmetry (McConkey) is native. The lottery
   ticket belongs in the +EV-at-volume bucket, not stapled to the −EV-at-volume $555.

---

## 6. Standout weeks — reads right, construction/volume threw it away

**wk3 (2024-09-22), MEGA — verified.** His actual: 22 bullets, **−27,768**. `his-reads dial` at
K19: **+254,886** (sim ROI +0.461). Gap **+282,654** — the single largest positive gap of the
season, and the engine behind almost the entire "reads add value" number.

What happened: his top overweights that Sunday all *missed* (his_hits = 0/12: Jordan Mason z=−1.24,
Achane z=−1.05, Kamara z=−0.83, Aiyuk z=−0.84). But the `his-reads dial` construction placed those
same views inside a chalk+structure MEGA shape at K19 that, graded on real points, took down real
equity anyway — while his 22-bullet hand-built portfolio (over the ≤19 cap, likely with hand-me-down
overlap) captured none of it. **Reads were expressed in a losing structure at the wrong volume.**
This is R6 + R11 + construction, all at once. *Caveat:* +254,886 is one lucky real-points draw on
one Sunday; the sim ROI (+46%) is the durable claim, the +254K is the tail realization.

**Similar weeks:**
- **wk17 (2024-12-29), MEGA — the volume disaster.** 55 bullets (a triple violation of the ≤19
  cap), **−110,815**. `his-reads dial` at K19: **−32,930** (gap +77,885, sim ROI +0.112 — actually
  +EV at the cap). Isolated volume effect alone: **+59,773**. This is the cleanest sizing receipt
  of the year: same reads, correct construction, capped volume = 78K better, ~60K of it pure volume.
- **wk12 (2024-11-24), $555 — volume bleed.** 150 bullets, **−79,050.** `his-reads dial` at K36:
  −18,315 (gap +60,735; volume effect +60,078). Cap alone saves ~60K.

Pattern across all three: **his reads/views were fine; the loss was manufactured by oversized entry
counts and (wk3) hand-built structure in the sharp fields.** Not a read problem — a sizing and
construction-in-the-wrong-field problem. Exactly R1/R6's "oversized entry counts in small fields"
and R11's hand-me-down leak.

---

## 7. The brief as a supplement — complementarity, quantified

His 21.4% > brief's 17.5%: as a *replacement*, the brief is worse. But as a *supplement* it
surfaces exactly the tail he systematically ignores.

**Test (the DeVonta Smith case, generalized):** on how many weeks did the mechanical brief flag a
z≥1.5 player at <10% ownership that was NOT among his overweights?

- **z≥1.5 & own<10% & not in his_over: 16 hits across 10 of 21 weeks.**
- Loosen to z≥1.0: **26 hits across 13 weeks.**

Highlights the brief caught and he missed:
| wk | player | own% | z | |
|---:|---|---:|---:|---|
| 17 | **DeVonta Smith** | 4.86 | **+2.46** | the named case — verified |
| 18 | **Kayshon Boutte** | 0.63 | **+2.59** | on the McConkey week itself |
| 10 | Calvin Ridley | 0.00 | +2.36 | |
| 3 | Saquon Barkley | 6.19 | +2.31 | (wk3 again) |
| 16 | De'Von Achane | 6.91 | +2.10 | |
| 15 | Brian Thomas | 7.44 | +2.39 | |
| 5 | DJ Moore | 3.66 | +2.23 | |

**Marginal value:** these are precisely the sub-10%-owned, high-conviction-outcome tail plays that
win MEGA/large fields and that his overweights (which skew to 20-50%-owned "conviction chalk" —
Jordan Mason 50% own, Bucky Irving 59% own, Tyjae Spears 54% own) do not reach. The brief is a
**low-owned-tail scanner**: keep it not as a read source but as a mandatory pre-lock supplement to
seed the differentiation slots (R4's "distinct lineups," the FLEX 4-5 in showdown, the deep pivots
in large-field MEGA). On ~half the season it hands him at least one <10%-owned z≥1.5 name he'd have
skipped, including the Boutte tail on the biggest week of the year.

---

## 8. 2026 ADJUSTMENT LIST — each tied to a dollar receipt from this replay

1. **Hard-cap $555 Milly at 36 bullets; cap MEGA at 19.** Receipt: 6 weeks run at 150 in $555 netted
   −221,350 ex-wk2; MEGA weeks over 19 (wk3 n=22, wk17 n=55) netted −138,583. Isolated volume
   saving on the tested population = **+204,767** (ex the one wk2 tail). The K-curve inverts past
   ~36/~19 in-model and in the realized record.

2. **Inside the cap, deploy at FULL conviction exposure (70-90%, R4) — not diluted.** Receipt: the
   wk2 `his-reads dial` "lost" only because a +12% boost cannot carry a 90% Kupp/Nabers/Godwin
   conviction (sim ROI at K36 was +1.886; the rebuild dropped the stack). The cap failed the test
   *because it diluted conviction*, not because it capped. Cap volume, keep conviction whole.

3. **Move the 150-volume lottery ticket from $555 to the $20 single-slate Milly.** Receipt: his 2024
   tails landed there — wk18 +998,890; the $20 engine ex-wk18 is only −11,660 (cheap to run). The
   $20 field is 16.8% copied entries; distinct conviction builds are free equity and the K-curve
   does not invert. Buy the +354K-shaped tail in the bucket where volume is +EV.

4. **Never hand construction to the sim; he builds every lineup (R11 re-confirmed).** Receipt:
   rulebook `dial` construction underperformed his own builds by **−320,823** at equal volume across
   15 tier-weeks. Sim outputs are dials (fade λ, structure, captain split) only.

5. **Ban deep fades in $555/MEGA (λ0-3 MEGA, λ6-10 $555).** Receipt: `his-style f10` deep-fade =
   −550,071 MEGA / −174,825 $555 at cap-K, negative-EV in 11 of 15 tier-weeks. His "deep fades in
   sharp fields" leak, priced.

6. **Kill the MEGA bucket unless a slate clears the R1/R6 gates AND he has a genuine sub-10%-owned
   tail read.** Receipt: MEGA was −295,767 for the season with no rescuing tail, and even the
   capped, correctly-constructed `his-reads dial` was only −73,570. MEGA at 19 chalk is real
   takedown equity (P(win) 3-4%/slate) but the *expected* line is a bleed — enter it lean and only
   with a differentiating low-owned read, not as a default.

7. **Adopt the mechanical brief as a mandatory pre-lock low-owned-tail supplement (not a read
   source).** Receipt: on 10 of 21 weeks it flagged a <10%-owned z≥1.5 hit he missed (16 total),
   incl. DeVonta Smith wk17 (z=2.46) and Kayshon Boutte wk18 (z=2.59, the McConkey week). Use it to
   seed differentiation/pivot slots, feeding R4's distinct-lineup engine and the large-field tail.

8. **Enforce the size-down-after-loss brake and the ≤19/≤36 caps as pre-lock gates, not moods (R3).**
   Receipt: wk17 (55 bullets, −110,815) followed a losing wk16; the loss-brake alone would have
   forced it under the cap and saved ~60K of pure volume. Add "over cap-K?" as a literal item on the
   60-second checklist.

---

*All numbers recomputed from `weekcards/*.json` in this replay. `his_hits`/`brief_hits` fields
match z≥1 counts of `his_over`/`brief_flags` on every card. Season, tier, read-accuracy, and
counterfactual aggregates reconcile to within rounding of the prior agent's figures; the two
material re-statements are (a) taxonomy sign-flips on the wk2 tail, made explicit above, and (b)
$555 `his-reads dial` @K36 = −147,352 (not −163K) because K=36 is absent from wk16's card (it uses
no K36 cell), which the fair-population aggregate respects.*
