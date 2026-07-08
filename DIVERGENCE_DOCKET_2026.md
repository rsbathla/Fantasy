# Divergence Docket — Our Model vs. FantasyPoints "2026 New Playcallers" (Heath)

Adjudication of every player where the article's call conflicts with our tags/ranks. Each entry:
our position, their mechanism, what OUR data says when we check it, and a verdict — **HOLD** (keep
our rank), **ADJUST** (move it), or **TRIGGER** (hold, but define the early-season signal that
would flip us). Evidence cited from `dossier_data.json` / `offense_profile.json` — not vibes.

**Meta-lesson from this exercise (see Godwin):** our `motion` split is ALL motion; the article's
edge metric is **during-snap motion** specifically (+43% FP/RR league-wide). The two can point in
opposite directions for the same player. Until the during-snap field is added (fetch list below),
treat our motion lifts as noisy.

---

## 1) Jaxon Smith-Njigba — our rank 3 vs. their FADE ⚠️ biggest conflict
- **Ours:** rank 3, ADP 5.4, CONSENSUS STUD. Projection 19.4 FPG, 99th-pctl ceiling.
- **Theirs:** 26% of his 2025 points came on 16 perfectly-thrown deep balls (92.9 pts, most in NFL);
  of 21 comparable deep-ball-luck seasons, 76% declined (avg −2.3 FPG); only 1.0 RZ tgt/g vs the
  1.45 avg of 18+ FPG seasons; Fleury (first-time caller) explicitly wants run-heavy red zone.
- **Our data check:** *corroborates them on the two testable claims.* Our dossier: **rz i20_pg 0.9,
  ez rate 11%** — thin RZ profile for a top-3 pick, exactly their number. Motion lift mild (+0.14).
  We flag him POLARIZING but still rank him 3 largely on volume (166 proj targets) + efficiency
  persistence, which is precisely the stat their regression study attacks (+5.0 FPOE, tied 5th-most
  ever; non-McVay/Shanahan repeats are rare).
- **Verdict: ADJUST (down a band, ~3 → 6-8 range) + TRIGGER.** Even our own inputs say his profile
  is efficiency-heavy/RZ-light, and his caller changed to an unknown. Triggers to re-upgrade: Week
  1-3 RZ tgt/g ≥1.3, or during-snap motion rate spike with JSN as primary beneficiary.

## 2) Ashton Jeanty — our EFFICIENCY TRAP vs. their strong BULL
- **Ours:** rank 14, POLARIZING + EFFICIENCY TRAP (rookie-year YPC ugly).
- **Theirs:** the trap is the *offensive line's* fault (hit behind LOS on a league-worst 48.5% of
  runs; when NOT hit behind LOS: best-in-class 3.36 YACO/A). Line upgrades (Miller back, Linderbaum
  signed) + Kubiak = bellcow ("best player has got to play") + extreme run-lean inside the 10.
- **Our data check:** our LV profile agrees with the *environment* claim — Kubiak identity
  "slow-paced, balanced, wide/zone-run," dials all +1, and our own brief already ranks Jeanty 14
  despite the trap tag. Their decomposition (trap = line, not player) is the kind of conditioning
  our YPC-based tag doesn't do.
- **Verdict: ADJUST (soften: drop EFFICIENCY TRAP → "TRAP-CONTEXT: OL-driven", hold rank ~12-14).**
  Their causal story is better than our unconditional stat. Don't chase to RB5-7 — 5.5 win total
  still caps the TD ceiling — but the tag as written overstates player risk.

## 3) Brock Bowers — our EMPTY CALORIES/FLOOR RISK vs. their positive
- **Ours:** rank 26, POLARIZING, FLOOR RISK, ZONE-BEATER.
- **Theirs:** Kubiak play-action is elite for pass-catchers; Bowers is the alpha.
- **Our data check:** our rz block: **i20_pg 1.1, ez 19%** — that is NOT empty-calories usage; it's
  real scoring opportunity. Motion lift +0.13. The EMPTY CALORIES tag came from garbage-time-ish
  2025 context that the caller change resets.
- **Verdict: ADJUST (remove EMPTY CALORIES; rank holds ~24-28).** Kubiak's low pass volume is the
  real ceiling limiter (their own Darnold/Carr QB23 note cuts against a huge TE season too).

## 4) De'Von Achane — our rank 16 vs. their FADE
- **Ours:** rank 16, POLARIZING only.
- **Theirs:** 52.5% of his XFP was receiving; Willis has the NFL's LOWEST RB target rate two years
  running (Tua the highest — a first-to-worst QB swap); Slowik backfields rank 20th in FPG; his
  early-down run-stubbornness creates 3rd-and-long scramble drills, not checkdowns.
- **Our data check:** our MIA profile flags the environment (env 22, low total, Slowik playcaller)
  but our rank never propagated the QB-specific RB-target collapse — our RB rz/receiving split
  fields are null (gap). The mechanism is specific, quantified, and matches our own env pessimism.
- **Verdict: ADJUST (down: 16 → low-20s band) + TRIGGER.** Re-upgrade only if Weeks 1-3 show
  Achane ≥15% target share with Willis, or Tua/other QB change.

## 5) Lamar Jackson — our FLOOR RISK vs. their positive
- **Ours:** rank 47 (QB), POLARIZING + FLOOR RISK.
- **Theirs:** best PA passer in football (3 of top-5 PA ANY/A seasons since 2023); his FPG tracks
  his PA rate almost monotonically (20th PA rate → 17.3 FPG in 2025 vs 10th → 25.8 in 2024); Doyle
  (Payton/Ben Johnson tree) telegraphing motion+PA revival; beat reports of Henry screens imply a
  friendlier ecosystem, not a worse one.
- **Our data check:** our deeppass block: **deep_pctl 93, 13.0 deep YPA** — elite arm efficiency
  intact. Our FLOOR RISK tag keyed off the down 2025; their mechanism explains 2025 as a
  scheme-usage artifact, which our own deep data supports.
- **Verdict: ADJUST (up: remove FLOOR RISK, move into the QB4-6 conversation).** The one caution:
  Doyle is a first-time caller (same unknown we penalize SEA for — consistency matters), so not a
  full send to QB1-2.

## 6) Jayden Daniels — our EMPTY CALORIES vs. their positive
- **Ours:** rank 63 overall, EMPTY CALORIES + FLOOR RISK.
- **Theirs:** Blough/Quinn want more under-center → Daniels' UC/pistol scramble rate (21.3%, career
  26.5% UC) exceeds his shotgun rate (12.0%); scrambles = the most predictive QB fantasy input.
- **Our data check:** our deeppass: **deep_pctl 34** — the passing-efficiency skepticism behind our
  tag is real. But their case is rushing-mechanism, not passing — and 91% of 100+ rush-attempt QBs
  finish QB1. Both can be true: mediocre deep passer, elite fantasy floor via legs.
- **Verdict: HOLD rank, RE-LABEL.** EMPTY CALORIES is the wrong tag for a rushing-floor QB; swap to
  "PASS-EFF RISK / RUSH FLOOR". No rank change without UC-rate confirmation (TRIGGER: Week 1 UC%).

## 7) Sam LaPorta — our rank 88 vs. their strong value call
- **Ours:** rank 88, POLARIZING, ZONE-BEATER.
- **Theirs:** Petzing = #1 playcaller in TE FPG since 2021 (19.3, ahead of Reid/Kelce); McBride hit
  75%+ routes in 29 straight games under him; LaPorta averages 15.9 FPG at 75%+ route share.
- **Our data check:** our rz (i20 1.0, ez 10%) is fine-not-elite; our motion lift for LaPorta is
  −0.69 (but see the during-snap caveat — Heath's Lions data shows the opposite with motion ON, so
  our aggregate split is probably mismeasuring the thing that matters).
- **Verdict: ADJUST (up a band: ~88 → 70s; TE8-10).** Playcaller-TE prior is one of the most robust
  tendencies in their whole framework, and it's the exact kind of prior our model is built on.

## 8) Zach Charbonnet — our MARKET FADE vs. their positive
- **Ours:** rank 142, MARKET FADE + EMPTY CALORIES.
- **Theirs:** Fleury run-heavy red zone philosophy (verbatim: "people that can run it in the red
  zone have the most success") + JSN regression frees scoring share; Charbonnet "progressing well."
- **Our data check:** K.Walker's dept... our SEA profile confirms run-lean shift (BALANCED→RUN) and
  slow pace — pace cuts total plays (bearish) while GL run-lean adds TD equity (bullish). Wash-ish.
- **Verdict: HOLD (fade stands, cheap TD-vulture upside noted).** Their case is coachspeak-heavy;
  ours is usage-based. Revisit only on a Walker injury/trade or 3+ GL carries/g early.

## 9) Michael Pittman — our EMPTY CALORIES vs. their positive
- **Theirs:** McCarthy = 3rd-most WR FPG among active callers; pass-heavy inside the 10; Rodgers
  slot/size affinity; personnel piece favors him at cost.
- **Our data check:** rz i20 0.8/g, ez 13% (middling), motion lift ~0. Their case is TD-regression-up
  via caller tendency; ours is current usage. Both defensible; ADP (95.8) is cheap enough that the
  asymmetric error favors them.
- **Verdict: ADJUST (small: remove EMPTY CALORIES, nudge inside ~85).**

## 10) Breece Hall tag audit — semantics, not disagreement
- Our `RB-ZONE-SCHEME` tag reads as "fits zone." Their data: Hall 3.79 YPC on zone (10th-worst),
  5.20 on man/gap (3rd-best) — if our tag asserts zone *fit*, it's backwards; if it means "played
  in a zone scheme," it's stale (Reich ≈ league-avg concepts, Engstrand's 2nd-highest zone rate
  gone). **ACTION: audit the RB-*-SCHEME tag definition repo-wide** (same check: Allgeier, Swift,
  Spears, Gainwell, JCM, Skattebo).
- Separately, their Hall fade is Glenn-committee-driven; our rank 32 already reflects committee
  risk (POLARIZING). HOLD.

---

## Scoreboard
ADJUST 6 (JSN ↓, Achane ↓, Lamar ↑, LaPorta ↑, Pittman ↑, Jeanty/Bowers tag-softening),
HOLD 3 (Daniels re-label, Charbonnet, Hall), plus one repo-wide tag-semantics audit.
Their edge over us: causal decomposition (whose fault was the stat) + caller-specific positional
priors (TE FPG, backfield XFP, GL PROE). Our edge over them: quantified projections, defense/Vegas
integration, and market tags (their Dart/Bucky/JCM/Wilson calls simply agree with our tags).

## Data to add (closes the gap they exploited)
From nflverse pbp (run `fetch_tendencies.py` on the Mac): under-center rate, goal-line (i10) pass
rate & PROE, backfield target share + i5 carry share — per team-season 2023-25, mapped to 2026
callers. From FPDS exports: during-snap motion rate (team + player), designed targets/screens by
caller, route participation %, 1D/RR. Then re-run this docket's triggers automatically.
