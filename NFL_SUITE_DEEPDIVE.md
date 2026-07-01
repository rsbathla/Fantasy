# NFL Fantasy Suite — Deep Dive & Verified Shortcomings
*Generated 2026-07-01. Every claim below was re-checked against the actual code and, where it concerned the 2026 world, against live sources. Where the earlier internal review was wrong, that is called out explicitly (§6). This is the "go deeper + show the shortcomings" document.*

---

## 0. How to read this

Two halves. **§1–§4** is *context* — what the suite actually is and how a number gets from a raw charting file onto a player card, in enough depth that the shortcomings in §5 land. **§5** is the *shortcomings*, prioritized by real (post-verification) severity, with the exact file/line and why it matters. **§6** is the part most reviews skip: the places where the review process itself was wrong, corrected against reality — because a shortcomings doc that fabricates shortcomings is worse than useless. **§7** is what is genuinely strong, so the picture is balanced. **§8** is a prioritized fix list.

A note on method, because it matters for trust: I did not take the four sub-reviews at face value. I opened `core.py`, `fusion.py`, `pipeline/build_draft_board.py`, `boom/backtest_results.json`, `engine/ud_parse.py`, `engine/playoff_overlay.py`, `dfs_model.py` and others, and I web-verified the roster claims. That process **killed several "findings"** (the headline "wrong rosters" alarm was itself wrong) and **confirmed others** (the projection double-count is real). The corrections are in §6.

---

## 1. What the suite is

Roughly **34,000 lines of Python across ~200 files** in `/root/bestball/bestball`, plus a `pipeline/` of derived data and an `engine/` for the best-ball decision logic. It is not one model; it is **three products on one data spine, plus a live analyst-intelligence layer**:

- **Best Ball draft model** (`draft.py` → `engine/`) — paste a DraftKings *or* Underdog board, it auto-detects the platform and grades every available pick through a Monte-Carlo **survival chain** that optimizes *advancement rate × playoff (Week 15–17) title odds*, aware of your existing roster construction. Output: `decision_dashboard.html`.
- **DFS weekly model** (`dfs_model.py --week N`) — for a given week, scores each player's **matchup edge** (their statistically-real strengths — man/zone/deep/slot — against that opponent's specific softness) and emits a who-to-play board plus lineup-construction templates. Output: `dfs_week.html`.
- **Dossier** (`build_dossier.py` / `build_dossier_deep.py`) — a 369-player reference of player/offense/defense/coaching fundamentals, the fusion signal panel, and the analyst layer. Output: `dossier_deep.html`.
- **Live X / analyst intelligence** — the layer built over the last sessions: 48 tracked analyst handles → tweet pulls → an accumulation store → player/team mapping → per-player narrative → article/video index → merged into the dossier. (Full detail in `HANDOFF_X_DOSSIER.md`.)

The unifying design choices are worth stating up front, because the shortcomings are mostly *tensions with* these choices, not violations of them:

1. **Upside-first, not mean-first.** The board grades on p95 ceiling and survival-chain advancement, not projected points. Best ball pays for weeks that win, not for consistency.
2. **No fabrication — abstain on missing data.** The canonical join returns `None` rather than a guess (`core.py:81`); the DFS matchup layer "ABSTAINS if `rec_man_zone_delta` or `opp_w15_man_rate` is missing" (`dfs_scenarios.py:370`). This is a genuinely principled spine. Its failure mode (below) is not *wrong* numbers but *silently missing* ones.
3. **Divergence-as-leverage.** The fusion layer keeps not just a consensus but the *disagreement* among signals, on the theory that where the signals split is where the market is soft.

---

## 2. The data spine — how a number reaches a player card

**Ingest → pipeline.** Raw charting and projection inputs (PFF Premium Stats, FTN, FantasyPoints splits, an NFL-Pro EPA scrape, and `dk_adp.csv` for ADP + 2026 team) are reduced into a small set of derived, **git-tracked** artifacts in `pipeline/`: `player_games.parquet` and `usage_shares.parquet` (2025 per-game aggregates and usage shares), `layer2_team_params.csv` (team pass/rush rates), `games_by_week.json` (the schedule), `correlation_structure.json` (stacking correlations), and `draft_board_signals.csv` (the per-player projection/ceiling/spike signals). This matters for §5: the *operative* inputs the models consume are version-controlled; it is the upstream raw scrapes that are not.

**The canonical join (`core.py`).** The whole suite hinges on one name→player join, deliberately centralized to kill the "5 duplicate `fn()` copies" of the earlier design. `fn()` (`core.py:19`) lowercases, strips Jr/Sr/II–V suffixes, and removes punctuation; `match_usage()` (`core.py:65`) does a position-strict, name-similarity, team-tiebreak match against a `(surname, first-initial)` index, and — crucially — **returns `None` rather than guessing** when it can't disambiguate. This is what fixes the "A.J. Brown = Amon-Ra Brown" and "Jeremiyah Love = Jordan Love" collisions the docstring brags about. It is good engineering. It also has a specific, silent hole (§5, Tier 1).

**Projection → boom subsystem.** `boom_foundation.py` defines a "boom" as a real spike week using **fixed per-position thresholds** (QB ≥ 24, RB ≥ 20, WR ≥ 20, TE ≥ 15 DK points; `boom_foundation.py:4`) and runs a **leak-free, per-game backtest** of which signals actually predict booms — the result of which lives in `boom/backtest_results.json`. That file is unusually honest: it records that the matchup layer helps QB/TE and *hurts* WR/RB, that the "opportunity family" (snap share, route participation) is "CONCLUSIVELY_REDUNDANT" with base rate, and that separation "PASSES_SCREEN" but is an "in-sample upper bound; OOS-confirm pending." The subsystem *knows* what it doesn't know. Whether every downstream consumer honors those verdicts is the open question in §5.

**The fusion consensus (`fusion.py`, ~65 KB).** This is the brain. For each player it assembles up to **20 percentile "votes"** — `market, value, proj, ceiling, spike, adv, coachspeak, route_eff, coverage_proof, run_eff, protection, rec_eff, separation, yac, rush_eff, explosive, oline, matchup, sis_value, boom` (`fusion.py:561–582`) — masks each vote to where its raw input actually exists (so a missing signal doesn't drag a player to the middle), and takes the row-wise mean as **consensus** and the row-wise std as **divergence**. The masking is a genuinely thoughtful touch. The weighting is where the modeling critique bites (§5, Tier 2): it is an *equal-weight* mean, and several of those 20 votes are the same underlying quantity wearing different hats.

**Best Ball engine (`engine/`).** `bbengine.py` + `decision_tree.py` run the survival chain; `dk_parse.py` / `ud_parse.py` turn a pasted board into structured picks; `playoff_overlay.py` shapes Weeks 15–17 by a bounded matchup multiplier (your offense strength blended with opponent softness). `draft.py` is the single entry point.

**DFS model (`dfs_model.py`).** Week-parameterized. It scores a player's ceiling × matchup edge, where the matchup edge is the player's **real SIS man/zone EPA split** interacted with the specific opponent's man/zone lean, and it *abstains* when either side is missing. It emits a who-to-play board and **lineup-construction templates** — not a salary-constrained optimizer (there is no salary column and no ILP; §5, Tier 3).

**Dossier + X layer + serving.** `build_dossier_deep.py` renders the 369-player reference; the X chain (`build_pull_*.py` → `build_x_store.py` → `x_dossier_refresh.py` → `build_x_narrative.py` → `build_x_media.py`) folds in analyst sentiment and an article/video index. A pandas-free **FastAPI read service** in `api/` and a set of self-contained HTML dashboards are the delivery surface.

---

## 3. The philosophy, stated fairly

Before the criticism: this is a *sophisticated* system with a coherent worldview. Upside-first grading is the correct instinct for best ball. Abstaining on missing data instead of imputing is the correct instinct for trust. Keeping divergence as a signal is a real edge idea. The boom backtest is leak-free and self-aware about in-sample vs out-of-sample. The name resolution is better than most commercial tools. None of what follows should be read as "this doesn't work" — all three products run end-to-end and render clean. It is "here is where the seams are."

---

## 4. Where the seams are — the shape of the problem

Four themes recur, and it helps to name them before the list:

- **Durability.** The code has git history but no home. One reclaim of the sandbox and most of it is gone.
- **Silent, not wrong.** The abstain-don't-guess spine means the failure mode is *absence* — a marquee player with no usage data — and absence doesn't announce itself.
- **Diagnosed but not always propagated.** The system frequently *documents* the right fix (shrink the matchup layer per position; separation is in-sample only) without a guarantee that the shipping path applies it.
- **Analysis, not yet a product for a walk-up user.** It is a CLI-and-dashboards system for its author, not a lineup you can click "generate" on.

---

## 5. Shortcomings — prioritized, verified

Severity is my post-verification rating, not the raw sub-review's. Each item has the *real* file/line (several sub-review citations pointed at files that don't exist; those are corrected here).

### Tier 1 — Fix this week

**5.1 No off-box durable copy of the suite. [HIGHEST]**
Verified: the repo has **16 commits and zero git remotes** (`git remote -v` is empty). It lives on a single ephemeral sandbox disk. The only "backup" is a `bestball_handoff_20260628.zip` that is *itself* inside the sandbox (`/root/bestball/`), i.e. equally ephemeral. The files pushed to your `Downloads` (the X store, `dossier_deep.html`, the handoffs) survive; **the ~34k-line codebase and the `pipeline/` parquets do not.** If this session is reclaimed, the suite is gone. This is the single highest-leverage thing to fix, and it is a five-minute fix: push to a private remote (or export the repo to `Downloads`). Everything else in this document is moot if the code evaporates.

**5.2 Hyphenated surnames silently miss the usage join. [HIGH]**
Verified against `core.py`. `fn()` (line 21) replaces hyphens with spaces: `fn("Jaxon Smith-Njigba")` → `"jaxon smith njigba"` → last token `"njigba"` → board key `("njigba","j")`. But `build_usage_index()` (line 59) builds its key from the raw parquet name **without** replacing hyphens: `"Jaxon Smith-Njigba"` → last token `"smith-njigba"` → index key `("smith-njigba","j")`. **The two keys never match**, so every hyphenated-surname player fails the usage join and comes back `None` — no target share, no carry share, no per-game usage. Because the spine *abstains* rather than guessing, this is completely silent: Smith-Njigba simply renders with a hole where his usage should be, and nothing logs it. (Suffix-style names like *Amon-Ra St. Brown* are safe — their last token is "brown" on both sides; the bug is specific to a hyphen *in the last name*.) One-line fix: make both sides normalize identically (`.replace('-',' ')` in `build_usage_index`, or stop splitting the hyphen in `fn`).

**5.3 No dependency manifest. [MED-HIGH]**
Verified: no `requirements.txt`, `pyproject.toml`, `setup.py`, `Pipfile`, or `environment.yml` anywhere. The suite imports pandas, numpy, pyarrow, pdfplumber, striprtf, pyperclip, anthropic, jsonschema, fastapi (in `api/`), and more, all unpinned. A fresh environment cannot reliably reproduce this, and a silent pandas/numpy major-version bump could change `groupby.rank`, parquet reads, or NaN handling under you. Pin the versions you're actually running and commit the manifest.

### Tier 2 — Modeling correctness

**5.4 The consensus double-counts the projection. [MED-HIGH]**
Verified — and this one the sub-review got *right* despite citing the wrong file. At the real location, `pipeline/build_draft_board.py:43`:
```python
for col,new in [('proj_pg','adv_pct'),('p95','ceil_pct')]:
    B[new]=B.groupby('pos')[col].rank(pct=True)
```
So `adv_pct` — the "advancement" vote — is *literally the position-relative percentile of the projection* `proj_pg`. It is not a survival-chain advance rate, despite the name and despite `fusion.py:24` labeling it "advance-rate." That means in the 20-vote equal-weight consensus, `proj` and `adv` are the **same underlying quantity**, and `ceiling`/`spike`/`value`/`market` are all further transforms of the same projection distribution. The upshot: the "consensus" is not 20 independent opinions; it is a projection cluster (≈5–6 collinear votes) plus a genuinely independent charting cluster (route_eff, coverage_proof, separation, yac…), averaged as if all 20 were equals. The projection therefore gets several times its fair weight relative to the charting the whole system is supposedly built on. Fix: collapse the collinear votes into one, or down-weight the cluster, or (best) PCA/whiten the vote matrix before averaging.

**5.5 The boom matchup layer is measured to hurt WR/RB — verify the shrink actually ships. [MED]**
Verified numbers from `boom/backtest_results.json`: adding the matchup layer moves overall boom AUC from **0.7386 → 0.7243** and Brier from 0.1233 → 0.1253 (both worse), and matchup-alone AUC is 0.528 (barely a coin flip). The file's own verdict is `KEEP_SHRUNK_PER_POSITION` — strong for QB (AUC 0.583, soft-vs-tough 17.5% vs 7.2%) and TE, off/shrunk for WR and RB. So the *diagnosis* is correct and documented. The open item the review could not close: confirm that every consumer of the matchup signal (the boom pipeline, the fusion `matchup` vote, the playoff overlay, the DFS edge — four separate applications) actually applies the per-position shrink the backtest prescribes, rather than a full-strength multiplier. This is a "trace it end to end" task, not a proven bug — but given how easy it is for a documented shrink to not reach one of four call sites, it's worth an afternoon.

**5.6 Two different definitions of "boom" coexist. [MED]**
Verified. `boom_foundation.py` uses **fixed** thresholds (QB 24 / RB 20 / WR 20 / TE 15). But `build_player_boom.py:19` defines boom as `act >= 1.5 * proj` — **relative to the player's own projection**. These disagree in the direction that matters: under the relative rule a low-projected player "booms" at a low absolute score, exactly the artifact the fixed-threshold approach was built to avoid. Decide which is canonical and route every consumer to it; right now which one a card sees depends on which builder touched it last.

**5.7 In-sample calibration; no true out-of-sample test. [MED]**
The boom backtest is leak-free *within* its sample and says so, but the system's calibration (the many hand-set thresholds across the ~5,800-line flag builders, the fusion weights) is fit and evaluated on the same 2025 season it trains on. The file even flags separation as an "in-sample upper bound; OOS-confirm pending." A held-out season (train 2024, test 2025) or a forward-walk would tell you how much of the edge is real vs. fit. This is the difference between "looks predictive" and "is predictive."

### Tier 3 — Product completeness / usability

**5.8 There is no DFS lineup optimizer. [MED-HIGH for the stated goal]**
Verified: `dfs_model.py` has no salary column and no solver (no pulp/ILP). It produces who-to-play scores and **lineup-construction *templates*** (`dfs_model.py:160`) — construction rules derived from winning structures — but it cannot assemble a salary-valid, constraint-satisfying lineup. If the intended deliverable is "give me a lineup to enter," that last mile isn't built. If the intended deliverable is "tell me who has an edge this week," it's done.

**5.9 Underdog "which picks are mine" defaults to the wrong roster. [MED]**
Verified at `engine/ud_parse.py:161–162`: if you don't pass `--mine` and your `--seat` handle isn't matched in the parsed board, `my_user` falls back to `otc_user` — the on-the-clock user — and it grades *that* roster. The default `--seat` is `rsbathla`, so if your Underdog handle appears in the paste it resolves correctly; the failure is a *silent fallback* when it doesn't, producing a confident grade of someone else's team. It works reliably via `--mine "Name|Name|…"`. Make the fallback *loud* (warn "couldn't identify your roster, grading on-the-clock user") instead of silent.

**5.10 The player-level DFS edge is only as wide as the SIS charting. [MED]**
Because the matchup engine abstains when man/zone data is missing (the right call), players without a SIS split get no player-level edge and degrade to team-level context. That's honest, but it means the "edge" is uneven across the slate, and the dashboard doesn't loudly say *for which players* it's flying on partial information.

**5.11 CLI-and-dashboards, not walk-up usable. [MED]**
Every entry point is a shell command that writes an HTML file. That's fine for the author; it's a wall for anyone else, and it's friction even for you on a phone mid-draft. A thin web front-end over the existing FastAPI service would close most of this.

**5.12 In-season live stats aren't wired, and the page doesn't say so. [MED]**
The DFS and dossier numbers are built on 2025 season data and 2026 projections; once games start, they don't yet swap to live 2026 production, and the dashboards don't communicate that they're pre-season snapshots. Low stakes today (it's July); date-stamp the pages so it doesn't mislead in September.

### Tier 4 — Known approximations & hygiene

**5.13 Defensive softness in the playoff overlay is a proxy. [LOW — documented]**
`engine/playoff_overlay.py` sets `DEFsoft[o] = -OFFz[o]` — it proxies "how soft is this defense" by the *inverse of the opponent's offense strength*, because "pipeline/ ships no standalone defensive-rating table." The code says this out loud, keeps the weight modest (0.40) and bounds the multiplier to [0.55, 1.55]. So it conflates "bad offense" with "soft defense," but it's a labeled, bounded approximation, not a hidden error. (Note the inconsistency: the *DFS* model uses real defensive data — `dfs_model.py:96` — while the *best-ball playoff overlay* uses this proxy. Unifying them on the real table would be an improvement.)

**5.14 Test coverage is ~2%. [MED]**
Verified: about 3 test files exercise the live suite (`engine/test_bbengine.py`, `api/tests/test_api.py`, `tests/test_names.py`) out of ~200 modules. The fusion consensus, the flag builders, and the join have no regression tests — which is exactly why 5.2 could ship silently. A golden-output test over a fixed board would catch most future regressions cheaply.

**5.15 Some derived data files have no in-repo regenerator. [LOW]**
`pipeline/correlation_structure.json` (and a few peers) ship as data with no committed script that rebuilds them from source. The *values* are sound (§6.2), but "how do I regenerate this if the inputs change" isn't answered in the repo.

**5.16 Per-position vote counts are uneven. [LOW]**
The number of available fusion votes differs by position (QB sees fewer charting signals than WR), so a QB's consensus is averaged over a thinner, more projection-heavy vote set than a WR's — compounding 5.4 at QB specifically.

---

## 6. Corrections to the review itself — where the *review* was wrong

This section exists because the golden rule here is "never assume the 2026 world; verify, then flag." The sub-reviews violated it, and I'd be repeating their mistake if I passed their errors through.

**6.1 The "wrong 2026 rosters" alarm was itself wrong.** The reviews flagged, as a HIGH-severity data-integrity failure, that `dk_adp.csv` lists Kenneth Walker III on Kansas City, A.J. Brown on New England, and DJ Moore on Buffalo — "obviously" wrong because those differ from 2025. I verified all three against live sources. **All three are real 2026 moves:** the Eagles traded A.J. Brown to the Patriots; the Chiefs signed Kenneth Walker III out of Seattle (he was Super Bowl LX MVP); the Bears traded DJ Moore to the Bills. The CSV is *correct*. The reviews assumed the 2026 world instead of checking it — the exact failure mode you've warned against. What survives is a much smaller, architectural point: 2026 team is *single-sourced* from one CSV with no in-code cross-check (`build_features.py:10`), so if that file *were* stale nothing would catch it. That's a LOW-MED hygiene note (add a second source or a sanity diff), **not** the HIGH "wrong data presented as fact" finding it was billed as. The model's rosters are, as far as I can verify, right.

**6.2 The "correlation contradiction" doesn't exist.** One review flagged that `correlation_structure.json` has `wr1_wr2 r=0.042` while the boom audit shows `0.513`, calling it a self-contradiction. These are unrelated quantities. `wr1_wr2 = 0.042` is the game-to-game scoring correlation between a team's WR1 and WR2 (near-zero is *correct* — same-team WRs compete for targets but share game script, netting ~0), and I confirmed the file's neighbors are textbook (qb_wr1 0.351, qb_wr2 0.339, bringback 0.129). The `0.513` is `player_base_spearman` from the boom backtest — the rank-stability of players' boom rates, a completely different measurement. No contradiction; the correlation file is sound.

**6.3 `adv_pct` is a projection percentile — but not for the reason first cited.** The review cited `build_draft_board.py:43` in the repo root; that file is at `pipeline/build_draft_board.py`. And `fusion.py:24`'s comment calls `adv_pct` an "advance-rate," which initially looked like it *refuted* the double-count claim. Reading the actual computation (§5.4) settled it: it really is `rank(proj_pg)`. The finding stands; the paper trail to it was tangled. (Several other citations — `sim_prod.py`, `survival_chain.py`, a root `ud_parse.py` — point to files that don't exist under those names; the real logic is in `boom_foundation.py`, `engine/bbengine.py`, and `engine/ud_parse.py` respectively. The thematic points mostly survived relocation; the line numbers did not.)

The lesson for this suite specifically: its own analysis layers (and any review of them) have to hold themselves to the same abstain-don't-guess standard the *code* holds itself to. The code is more disciplined about 2026 than the review of it was.

---

## 7. What's genuinely strong (so the picture is fair)

The Best Ball draft model is production-functional today: it parses both DraftKings and Underdog boards, auto-detects the platform, and grades in ~40 seconds via the survival chain. The name-resolution/imputation layer is better than most commercial tools — position-strict, similarity-scored, team-tiebroken, and honest enough to return `None` rather than fabricate. The DFS matchup engine is genuinely week-parameterized on real Vegas totals and real SIS coverage splits, and abstains rather than inventing an edge. The boom backtest is leak-free and unusually candid about in-sample limits and signal redundancy. And the 2026 roster data — the thing the review was surest was broken — is in fact accurate. This is a strong system with specific, fixable seams, not a shaky one.

---

## 8. If you fix five things, fix these

1. **Push the repo off-box (5.1).** Five minutes. Removes the risk that everything else here is moot.
2. **Normalize hyphens on both sides of the usage join (5.2).** One line. Restores Smith-Njigba and every other hyphenated name to the board.
3. **Pin dependencies (5.3).** One `requirements.txt` from your current environment. Makes the suite reproducible.
4. **De-collinearize the consensus (5.4).** Collapse `proj`/`adv`/`ceiling`/`spike`/`value` into a single projection factor, or whiten the vote matrix, so the charting signals aren't drowned by five copies of the projection.
5. **Make the two silent fallbacks loud (5.2, 5.9)** and add one golden-output test (5.14) so the next silent regression isn't silent.

Everything above Tier 1 is a durability or correctness issue; Tier 2 is where the modeling edge is being quietly diluted; Tier 3 is the gap between "analysis tool for its author" and "product." None of it is a rewrite.
