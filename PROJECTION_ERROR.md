# PROJECTION ERROR MODEL + DUPE CALIBRATION

Data: `data/fantasylabs/players/*_main_*.csv`, one obs per (date, name), main-slate only,
largest-contestSize file per date, proj>=3, positions QB/RB/WR/TE/DST (DST stored as `D`).
**123 main dates, 2021-11 to 2025-01. n=16,436** (QB 1913, RB 3804, WR 6294, TE 2541, DST 1884).
Sim baseline: outcome ~ Lognormal(mean=proj, CV) with CV = QB .45 / RB .65 / WR .85 / TE .90 / DST 1.10.

---

## 1. RESIDUAL MODEL  (residual = actual − proj)

| pos | n | bias (mean) | std | std≈a+b·proj (a, b) |
|-----|---|------|-----|------|
| QB  | 1913 | **−1.29** | 8.66 | a=3.98, b=0.271 |
| RB  | 3804 | −0.46 | 7.33 | a=3.76, b=0.331 |
| WR  | 6294 | −0.64 | 7.50 | a=3.94, b=0.353 |
| TE  | 2541 | −0.48 | 6.05 | a=3.59, b=0.335 |
| DST | 1884 | −0.34 | 5.61 | a=5.95, b=−0.052 |

**Every position is biased low** — projections are optimistic (worst at QB, −1.3 pts; larger at high proj).
Strong heteroscedasticity: residual std per proj-bin (pts):

| pos | 3-8 | 8-12 | 12-16 | 16-20 | 20+ |
|-----|-----|------|-------|-------|-----|
| QB  | 5.60 | 7.04 | 7.46 | 8.77 | 10.23 |
| RB  | 5.26 | 7.18 | 8.68 | 9.80 | 10.60 |
| WR  | 5.43 | 7.58 | 9.19 | 10.60 | 11.12 |
| TE  | 4.95 | 7.13 | 8.54 | 9.43 | 10.28 |
| DST | 5.62 | 5.50 | — | — | — |

Real std is roughly **linear** in proj (intercept a≈4, slope b≈0.3), NOT proportional-through-origin.

---

## 2. SIM DISPERSION CHECK  (real std vs sim std = CV·proj)

real/sim ratio of residual std, per proj-bin:

| pos | 3-8 | 8-12 | 12-16 | 16-20 | 20+ | POOLED |
|-----|-----|------|-------|-------|-----|--------|
| QB  | 2.25 | 1.46 | 1.15 | 1.09 | 1.02 | **1.08** |
| RB  | 1.55 | 1.10 | 0.95 | 0.85 | 0.75 | 1.00 |
| WR  | 1.19 | 0.91 | 0.78 | 0.71 | 0.60 | 0.83 |
| TE  | 1.03 | 0.82 | 0.71 | 0.59 | 0.55 | 0.83 |
| DST | 0.80 | 0.59 | — | — | — | 0.78 |

**The CV model is mis-shaped, not merely mis-scaled.** Because sim std is proportional (CV·proj) but real std
is linear-with-a-floor, the sim **under-disperses cheap/low-proj players** (ratio up to 2.25) and
**over-disperses studs** (ratio 0.6–0.75 at 20+). On a pooled marginal basis the CV model already carries
**enough or too much** per-player variance for RB/WR/TE/DST; only QB is short (+8%).

So the "unmodeled projection error" is **not** missing marginal per-player variance.
It is missing **correlation**: see below.

**THE ACTUAL BUG (correlated projection error).** Decomposing residual variance into between-date
(whole-slate, systematic) vs within-date shows a large correlated component the independent-draw sim erases:

| pos | total std | systematic slate σ (pts) | systematic share of var |
|-----|-----------|--------------------------|-------------------------|
| QB  | 8.66 | 4.44 | 31% |
| RB  | 7.33 | 2.19 | 12% |
| WR  | 7.50 | 2.15 | 10% |
| TE  | 6.05 | 2.14 | 17% |
| DST | 5.61 | 1.48 | 14% |

Direct test: real std of a **9-player lineup's residual sum (same slate) = 31.8 pts**, vs **21.6 pts if
residuals were independent → ratio 1.47.** The sim draws players independently, so it makes lineup totals
~1.47× too tightly concentrated around the projected sum. That is exactly why candidates claimed ~22%
field-beat probability and went **0-for-19**: the projection MEAN is treated as truth (zero mean-error),
and what error the CV does add averages out across 9 players. **Implied projection-error σ = the systematic
slate σ above** (QB 4.4 pts, others ~2.1 pts), applied as a *correlated* per-world shift.

---

## 3. IS CHALK BETTER-PROJECTED?  YES.

| pos | corr(own, \|z\|) | own≥20% mean resid | own<5% mean resid | chalk edge |
|-----|------------------|--------------------|--------------------|------------|
| QB  | −0.15 | **+1.36** | −2.12 | **+3.48** |
| RB  | −0.16 | +0.03 | −0.80 | +0.83 |
| WR  | −0.14 | +0.33 | −1.10 | +1.43 |
| TE  | −0.11 | +0.57 | −0.84 | +1.41 |
| DST | −0.05 | −0.25 | −0.73 | +0.49 |

corr(own, |z|) is **negative everywhere** → chalk has smaller error magnitude (better projected).
Chalk **beats** projection; low-owned **trails** it, at every position. QB chalk is dramatic (+3.5 pt edge)
and robust in 4 of 5 seasons. This is the field being right about who is good — the chalk premium is real,
consistent with "top-1% lineups overweight players who beat by +1.26σ."

---

## 4. TAIL CHECK   P(actual ≥ proj·(1+2·CV)) — empirical vs lognormal(mean=proj, CV)

| pos | threshold | empirical P | model P | real/model |
|-----|-----------|-------------|---------|------------|
| QB  | ×1.90 | 3.0% | 4.4% | 0.69 |
| RB  | ×2.30 | 6.1% | 4.5% | **1.37** |
| WR  | ×2.70 | 3.7% | 4.3% | 0.85 |
| TE  | ×2.80 | 3.7% | 4.3% | 0.88 |
| DST | ×3.20 | 1.9% | 4.0% | 0.47 |

Verdict: **real marginal tails do NOT broadly exceed modeled tails.** Only RB shows fat tails (1.37×);
QB/WR/TE are near model (0.7–0.9×) and DST is much thinner (0.47×). The high CVs push the ×2.7–3.2
thresholds so far out that a single lognormal marginal rarely reaches them. Real GPP-winning extremes come
from the **whole slate popping (systematic)**, not one player's marginal blowing up — reinforcing §2.

---

## 5. DUPE CALIBRATION  (`contest_meta.csv`)

Empirical column defs: `uniqueLineups` = # distinct lineups (≤ size, 99.6%); copy-share = 1−unique/size =
redundant-entry share; `duplicateLineups` = entries sitting on any lineup shared by ≥2 entries.

| group | n | size median | copy-share (1−uniq/size) mean / med | dupLineups/size mean / med |
|-------|---|-------------|-------------------------------------|----------------------------|
| (a) showdown | 1364 | 11,890 | −0.02\* / **0.631** | 3.59\* / 0.786 |
| (b) main Millionaire $19–26 | 83 | 176,470 | 0.168 / 0.052 | 0.205 / 0.074 |
| (c) main Millionaire ≥$300 | 59 | 768 | 0.034 / 0.013 | 0.041 / 0.018 |

\*showdown means are skewed by a few tiny/broken contests (unique>size); use medians. Large showdowns
(≥50K entries, n=418): **copy-share mean 0.86, dupLineups/size 0.92.**

**Verdict on sim v3's ~10 co-holders for the chalkiest showdown build: CONSERVATIVE — should increase.**
Reasoning: in 100K–475K showdown fields **~86% of entries are redundant copies**, and the *average*
already-duplicated lineup carries **~22–28 copies** (entries-on-dup ÷ #distinct-dup-lineups). The single
chalkiest build is by construction the **most-duplicated** lineup, so its co-holder count sits at the top of a
heavy-tailed multiplicity distribution — well ABOVE the ~22–28 average. ~10 co-holders is at or below the
*mean* multiplicity of a merely-duplicated lineup, so it understates reality. Recommend the chalkiest
showdown build carry **≥30–60 co-holders** (scale with field size), not ~10.

---

## 6. RECOMMENDATION  (drop-in for world generation; do not treat proj as truth)

Root cause: sim treats projection as a true mean and draws players independently. Fix = restore
(i) the low bias and (ii) the **correlated** slate-level projection error, while keeping each player's total
marginal sd honest by **reallocating** part of the outcome CV into the correlated shift.

Per world `w`, per position `pos`: draw ONE correlated slate shock, then per-player outcome:

```
S_{w,pos}  ~ Normal(0, sigma_sys_pos)                 # ONE draw per pos per world (correlated)
proj_w[i]  = proj[i] * k_pos * exp(S_{w,pos})         # bias-correct + systematic slate error
outcome[i] ~ Lognormal(mean = proj_w[i], cv = cv_idio_pos)   # idiosyncratic; REDUCED CV
```

| pos | k_pos (bias) | sigma_sys_pos (correlated, log) | cv_idio_pos (replaces CV) | old CV |
|-----|-------------|----------------------------------|----------------------------|--------|
| QB  | 0.926 | 0.256 | 0.429 | 0.45 |
| RB  | 0.955 | 0.216 | 0.691 | 0.65 |
| WR  | 0.933 | 0.225 | 0.752 | 0.85 |
| TE  | 0.934 | 0.291 | 0.768 | 0.90 |
| DST | 0.948 | 0.227 | 1.10→0.833 | 1.10 |

- `k_pos` shrinks projections to the observed mean (removes the +overconfidence bias).
- `sigma_sys_pos` is the correlated slate shock — the missing ingredient; it restores lineup-total dispersion
  (a 9-player lineup gains ~11 pts of systematic proj-error the old sim had at 0, closing the 21.6→31.8 gap).
- `cv_idio_pos` = sqrt(total_var − sys_var)/meanproj, so **total marginal sd stays at the real level** while
  correlation is added (WR/TE/DST CV drops because §2 showed they were over-dispersed).
- Optional refinement (better shape than proportional CV): use per-player sd = a_pos + b_pos·proj from §1
  for the idiosyncratic outcome (fixes under-dispersion of cheap players and over-dispersion of studs).
- Showdown dupe model: raise chalkiest-build co-holders from ~10 to ≥30–60.

Net effect: candidates' claimed field-beat probabilities fall by roughly the 1.47× lineup-dispersion factor,
bringing the ~22%/0-for-19 overconfidence into line with reality.
