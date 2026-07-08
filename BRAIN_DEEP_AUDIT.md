# BRAIN DEEP AUDIT — entity resolution, scoring, provenance, freshness (2026-07-05)

Scope: the full brain pipeline (`brain/brain_common.py`, `brain_tweet.py`, `brain_pull.py`,
`brain_ingest.py`, `brain_article.py`, `brain_video.py`, `brain_substack.py`, `brain_link.py`,
`brain_pages.py`, `brain_concepts.py`, `brain_export.py`, `brain_repair_mentions.py`,
`run_brain.sh`, `run_brain_weekly.sh`, `brain_film.sh`, `com.nflbrain.ingest.plist`) read line by
line; the resolver and the export scorer then stress-tested by EXECUTION against the live repo
canon (`boom/statmenu.json` 411 players, `web_teams.json` 96 coach slots), and findings
cross-checked against the live `brain_intel.json` (generated 2026-07-05T04:28Z; 4,335 tweets,
122 sources, 972 claims). Method: notes and raw evidence first, conclusions after. Nothing in this
audit changes semantics — every fix is a proposal.

Baseline acknowledged: the classes already fixed this session (common-word surnames incl.
likely/hurts/golden/worthy/pitcher, @handle stripping, Jr/Sr suffix keys, player↔coach surname
collisions via `coach_lasts`, first-name-as-surname blocks via `first_count`, `boston`
never-bare) all HOLD in re-test. This audit is about what remains.

---

## 1 · Entity resolution — evidence (executed battery)

Key inventory produced by `load_players` on the live roster: **211 bare substring surname keys**
(match case-insensitively ANYWHERE), **11 capitalized-only keys**, **69 context pairs**
(first+last anywhere in the same document). The battery below was run through
`bc.detect_entities(text, repo)` verbatim; every line shows the actual output.

### 1a. NEW mis-tag class: unguarded English-word / cross-domain bare surnames

`_COMMON_WORD_SURNAMES` (brain_common.py:109-121) guards 27 words, but the roster generates at
least 13 more bare keys that are ordinary words or famous non-NFL surnames. Because bare keys
match lowercase anywhere (brain_common.py:252), no capitalization gate applies. All of these
FIRED when tested:

| exact input | wrong tag produced |
|---|---|
| "Chiefs fans hope Taylor Swift shows up to training camp again this year." | **D'Andre Swift** |
| "There are real question marks about this Houston offense heading into camp." | **Woody Marks** |
| "The burden of proof is on the coaching staff after that draft." | **Luther Burden III** |
| "The Jaguars get a London game again — two home dates at Wembley." | **Drake London** |
| "Robert Kraft gave Mike Vrabel full roster control this offseason." | **Tucker Kraft** |
| "The Royals dropped another series; at least Chiefs camp opens Tuesday." | **Jalen Royals** |
| "They unveiled the black alternate jerseys for the season opener." | **Kaelon Black** |
| "His arm talent lets him pierce any two-high shell." | **Alec Pierce** |
| "Defenses tremble when he gets a runway downhill." | **Tommy Tremble** |
| "My cousins and I split season tickets again this year." | **Kirk Cousins** |
| "The front office extended an olive branch to the veteran room." | **Zachariah Branch** |
| "Jason Kelce said on New Heights that Philly will run it back." | **Travis Kelce** |
| "Charles Barkley picked the Eagles on the TNT crossover show." | **Saquon Barkley** |

Lower-frequency members of the same class (bare keys confirmed live, not battery-run): `harvey`
(RJ Harvey ← Hurricane/Steve Harvey), `hampton` (Omarion Hampton ← the city), `spears` (Tyjae
Spears ← Britney/the noun), `irving` (Bucky Irving ← Kyrie), `simpson` (Ty Simpson), `rodriguez`
(Chris Rodriguez Jr.), `tracy` (Tyrone Tracy Jr.), `lemon` (Makai Lemon), `montgomery` (David
Montgomery ← the city), `jackson` (Lamar ← any other Jackson), `howard` (Will Howard),
`hopkins`, `franklin`, `parkinson` ("Parkinson's" matches — trailing apostrophe passes the
`(?![a-z])` boundary). Note the 4-letter guard (`len(last) >= 5`, brain_common.py:219)
*silently* saves `love`, `cook`, `hall`, `ward`, `bond`, `hill`, `bell`, `moss` — good luck, not
design; documenting it here so nobody lowers that threshold.

**LIVE CONTAMINATION CONFIRMED in the current export** (re-derived from raw `brain_intel.json`):
- Jalen Royals' top-6 card carries a **baseball tweet**: 2026-07-03 @corbin_young21 "Tampa Bay
  Rays pitcher Ian Seymour…" (the exact cross-sport class as the fixed `pitcher` incident — and
  note @corbin_young21 in `x_handles.txt` is a mixed baseball/football author, so this class is
  structural, not hypothetical).
- Saquon Barkley's card (2 shown tweets) carries **Charles Barkley** media content: 2026-05-26
  @ahaanrungta "Charles Barkley was just a guest on The MacZone…".
- Woody Marks' card carries a 2026-06-23 @RyanJ_Heath Raiders/Tre Tucker play-action tweet —
  likely a `marks` word-hit (full text lives in the vault; flagged for vault-side verification).

### 1b. NEW mis-tag class: defense-vs-offense (and retired/family) same surname

`statmenu.json` is offense+DST, so a defensive star's surname can be a "unique" offensive bare
key. All fired:

| exact input | wrong tag produced |
|---|---|
| "Trevon Diggs locked down that entire side of the field all afternoon." | **Stefon Diggs** |
| "Bradley Chubb had three pressures and a strip sack on Sunday." | **Nick Chubb** + coach **Gus Bradley** + team fold-in (a triple corruption from one defender's name: `bradley` is a bare coach key, brain_common.py:305-310, and detect_entities folds the coach's team in, :329-332) |
| "Aidan Hutchinson wrecked the game off the edge again." | **Xavier Hutchinson** |
| "DeMarcus Lawrence set the edge all day against Seattle." | **Trevor Lawrence** |
| "Marvin Harrison went into the Hall of Fame back in 2016." | **Marvin Harrison Jr.** (the suffix-strip fix at brain_common.py:131-139 makes "marvin harrison" the son's full-name key, so the FATHER now tags the son) |

### 1c. NEW mis-tag class: context-pair document co-occurrence (the highest-volume residual risk)

The `(first, last)` corroboration (brain_common.py:229-233, applied at :256-257) requires only
that both words appear SOMEWHERE in the same document — no adjacency, no ordering. On a 280-char
tweet that is already loose; `brain_video.py:171` runs it over an ENTIRE transcript
(title + full hour) and `brain_book.py:97` over 60,000 characters, where co-occurrence of a
common first name and a common surname is near-guaranteed. Every one of these fired **on a
single-sentence input**:

| exact input | wrong tag produced |
|---|---|
| "Sean McVay raved about what Tucker Kraft put on tape last year." | **Sean Tucker** (TB RB) |
| "Kevin O'Connell and rookie Keon Coleman were both trending after minicamp." | **Kevin Coleman Jr.** (two legitimate entities manufacture a third) |
| "Daniel Jeremiah ranked the class and Jerry Jones promptly disagreed." | **Daniel Jones** |
| "Jonathan Gannon and Zac Taylor swapped notes at the owners meetings." | **Jonathan Taylor** |
| "Denzel Ward shadowed him everywhere; the kid starred at Boston College." | **Denzel Boston** (bypasses the `boston` NEVER-BARE guard) |
| "Derrick Henry ran through Danielle Hunter twice on Sunday." | **Hunter Henry** (cross-product of two other players' names) |
| "Omar Khan traded up while Cooper DeJean blitzed off the slot." | **Omar Cooper Jr.** |
| "Deion Sanders praised Treylon Burks after the joint practice." | **Deion Burks** |

The 69 live pairs include more loaded guns of the same shape: ('parker','washington') — the word
"washington" appears in every Commanders document; ('garrett','wilson') — Myles Garrett + any
Wilson; ('mason','taylor') — Mason Rudolph + Zac Taylor; ('hollywood','brown').
Denzel Boston's card already shows n_tw=24 with 0 claims — plausibly inflated by this class
(vault-side check needed to quantify).

### 1d. Cap-key bypasses (the already-guarded words are only half-guarded)

`_proper_noun_hit` (brain_common.py:159-172) counts ALL-CAPS at ANY position as a proper noun.
Chart titles and some caption tracks are all-caps. Fired:

| exact input | wrong tag produced |
|---|---|
| "PRICE CHECK: BIGGEST WR ADP MOVERS OF THE WEEK" | **Jadarian Price** |
| "The Eagles visited the White House on Tuesday." | **Rachaad White** (mid-sentence Capitalized cross-domain proper noun — same shape as the `boston` rule, but `white` has no NEVER-BARE entry) |

Verified holding: "Likely to play Sunday: the full injury report." → no tag (sentence-start guard
works); "@TaylorSwift13 was at Arrowhead again." → no tag (handle strip works).

### 1e. Team-tag false positives (case-insensitive city/nickname aliases, brain_common.py:264-267)

| exact input | wrong tag |
|---|---|
| "Tennessee beat Alabama 24-17 in Knoxville behind a huge day." | **Tennessee Titans** (college) |
| "The Miami Hurricanes have another first-round quarterback." | **Miami Dolphins** |
| "Washington Huskies produce another top-ten pick." | **Washington Commanders** |
| "He jets past the corner before the safety can rotate." | **New York Jets** (verb) |
| "He commands the lions share of targets in that room." | **Detroit Lions** (typo'd possessive) |

Draft-season college tweets make Tennessee/Miami/Washington/Houston recurring team-buzz
pollution. The Royals baseball tweet above also tags **Tampa Bay** via "Tampa Bay Rays".

### 1f. False NEGATIVES: hyphenated surnames are dead keys

The bare-surname key is letters-only (`_letters`, brain_common.py:193/208) but text keeps
hyphens, so the key can never match. Verified misses (no player detected at all):
- "Smith-Njigba is the WR1 in Seattle and it is not close." → **nothing** (only `jsn` alias or
  the full name links JSN)
- "St. Brown caught 12 of 13 targets in the slot." → **nothing** (alias `st brown` doesn't match
  the period form)
- "Croskey-Merritt looks like the lead back in August." → **nothing**
Same for `westbrookikhine`, `lambertsmith`, `smithschuster`. This is lost signal on
high-frequency shorthand every analyst uses.

---

## 2 · Scoring / condenser — evidence (executed)

`brain_export.tweet_base_score` (brain_export.py:63-87) implements the stats-first rule. Executed
results (kept on a card only if score > 0, per the `_sc > 0` filter at brain_export.py:282):

| tweet | score | card |
|---|---|---|
| "Brutal news: Tank Bigsby tore his ACL at practice and will miss the season, per Ian Rapoport." | **−4** | **DROPPED** |
| "Bigsby suspended six games for PEDs, the league announced." | **−4** | **DROPPED** |
| "In 2025 Tank Bigsby averaged 3.1 YPC but his target share spiked to 12% in December." (stale retro) | **+14** | KEPT, ranks 1st |
| "Tank Bigsby has looked unbelievable in camp. Different player." (content-free hype) | +4 | KEPT |
| "Coaching staff says Bigsby will open camp as the clear RB1…" | +4 | KEPT |
| ADP list tweet (4 names) | −8 | DROPPED (correct) |

- **Injury/availability vocabulary exists NOWHERE in the scorer** — not in `ADV_STAT_RE`
  (:54-59), not in `FWD_MARKERS` (:43-45). Tears/IR/suspensions/surgery/hamstring/PUP score as
  "no numbers, no direction → banter" (−5, :85-86) and vanish from the card, while a March stat
  retrospective is permanently promoted (BACK_MARKERS penalty is waived when stats are present,
  :78-79). For a layer whose stated job is coaching/scheme/INJURY news, this is the largest
  fitness-to-objective gap: the market re-prices injury news within minutes and the card hides it.
- **240-char truncation mis-scores long tweets**: `quote_text(cap=240)` (:132-137) feeds the
  scorer (:242-244). Measured: a 301-char analytical tweet scores 12 on full text, **2 on the
  clipped text** — the stats sat past char 240. Long analytical tweets are exactly the
  highest-substance class; premium X posts run to 4k chars.
- **No recency term anywhere**: sort is `(score, date)` (:281) — date only breaks ties, so a
  +14 May tweet outranks every +4 July development forever; `FWD_SINCE = "2026-02-01"` (:36) is a
  constant, so February takes count as "forward-looking" all season.
- **Subject bonus is substring, not word**: probe "brown" ∈ head "browns fans should…" → True
  (:253-254) — a Browns team tweet grants Amon-Ra/Dyami/Hollywood the +3 ABOUT-bonus.
- **Team `dtw` bypasses the quality gate**: the defense-intel list is built from ALL tweets
  BEFORE `finish()` filters negatives (:297-301) — a −6 joke containing "coverage" is eligible
  for the matchup-research list.
- What WORKS as designed (verified): ADP/dynasty list suppression (−7/−8), multi-player-list
  penalty, leaderboard-vs-poll fix, chart capture, SS Signal/Noise claims parse (972 claims,
  newest-first, capped), position-conflict source filter.

## 3 · Provenance + idempotency — evidence

- **Provenance is genuinely strong.** Re-derived from raw brain_intel.json: claim = `{"s": "SS
  2025 W12 · Signal", "t": "Puka Nacua— 83% routes, 37% TPRR, 11 targets", "g": "Rams 34,
  Buccaneers 7", "n": "2025-11-26 Stealing Signals Week 12 Part 2", "d": "2025-11-26"}` — source
  series, label, game, dated note. Tweets carry date+author+url; articles carry
  outlet/author/date/`fetched_via`; videos carry channel/analyst/`transcript_source`/asr model.
- **Idempotency: solid at the note level** (URL manifest `_status/ingested.json`; brain_link
  SHA-1 claim ledger `_status/intel_claims.json`; retweet→original dedupe incl. reverse
  registration, brain_tweet.py:311-337; backfill checkpoints). Residuals: URL normalization
  still open (BRAIN_PLAN hole 6 — `http://` vs `https://` and `utm_*` variants create dup
  notes; only `utm_campaign=promo` is junk-filtered, brain_ingest.py:28); manifest is
  read-modify-write per item (brain_common.py:65-72) — a manual run concurrent with the 7:30
  launchd run can lose marks.
- **FAIL-LOUD: partial, with two silent holes.**
  1. `brain_pull` per-handle API failures (quota exhausted, key expired-but-present) log to
     stderr, `break`, and **exit 0** with an empty list (brain_pull.py:80-82, 98-103); the
     ingest card's `errors` list never receives them (brain_ingest.py:169-183), so the vault
     card reads "✅ OK · 0 new links". Same for brain_tweet per-handle errors (returned in its
     JSON `errors` field, discarded by ingest). A dead feed looks like a quiet news day.
  2. **`brain_export` on an empty/missing vault writes an EMPTY brain_intel.json and exits 0**
     (verified: `--vault /tmp/emptyvault` → `{"players": 0…}`, exit 0; no minimum-entity guard
     before the unconditional dump at brain_export.py:313-320). A mis-set `NFL_BRAIN_VAULT` or
     unmounted disk in the 7:30 run silently replaces the 1.1MB live export with 373 bytes, and
     both consumers swallow it (`except: pass`, engine/run_live.py:118-124).
  - Also: `bc.write_status` (brain_common.py:348-359) has **zero callers** — a health-card
    guard that has never fired (untested-guard class; brain_ingest has its own `write_card`).

## 4 · Freshness / continuity — evidence

- **Daily intel loop IS scheduled**: launchd plist → run_brain.sh at 07:30 local
  (ingest → substack 14-day sweep → condense → pages → export → concepts). The human is NOT the
  cron daemon for the daily loop. Whether the plist is currently loaded on the Mac is not
  verifiable from this box (decision point below).
- **Weekly model refresh and film ingest are human-cron**: no plist exists for
  `run_brain_weekly.sh` or `brain_film.sh`; film coverage (`film_sources.tsv`, 3 videos/channel)
  runs only when hand-invoked, so Kollmann-class film intel goes stale between manual runs.
- **Consumers get a freshness SIGNAL but no ALARM**: run_live prints "as of <generated>"
  (engine/run_live.py:253-257) and the dashboard renders "as of … UTC"
  (build_decision_dashboard.py:842-849); neither computes age nor warns when the export is N
  days old — combined with the silent-holes above, a dead pipeline shows a quietly aging
  timestamp only.
- **run_brain.sh stage failures are log-only**: `set -uo pipefail` without `-e`; each stage's
  exit code is echoed into `_status/run.log` and nothing aggregates — if brain_export crashes,
  brain_intel.json goes stale with no card, no alarm (the last-run.md card is written by the
  ingest stage only).
- **Trade staleness in entity pages**: `brain_pages.upsert` writes frontmatter (incl. `team:`)
  only at CREATION (brain_pages.py:118-135); brain_export reads that frontmatter team
  (:221-222) to attach the coach line (:289-291). A player traded after his page was created
  keeps his OLD team's "HC x · OC y" on every draft card until the page is hand-deleted — a
  quiet mis-attribution channel in the layer built to prevent exactly that.

## 5 · Fitness to objective — verdict

The architecture is right for the layer-fusion thesis: sourced, dated, annotate-only, canon-fed
(coaches from the Check-J-audited `web_teams.json`, never hardcoded), with real dedupe and a
scheduled daily loop. Provenance is the strongest part of the system. But the two things the
qualitative layer uniquely owns — **correct attribution** and **breaking-news currency** — are
the two places it still leaks: three live false-positive classes (English/cross-domain bare
surnames, defense-vs-offense surnames, context-pair co-occurrence) are demonstrably corrupting
current cards (Royals/baseball, Barkley/NBA in today's brain_intel.json), and the scorer
actively suppresses injury/availability news while permanently promoting stale stat
retrospectives. Noise risk is real but bounded (caps + negative-score filter); MIS-TAG risk is
the one that silently flips decisions, exactly as the roster collision did.

---

## Findings table

| # | issue | severity | file:line | evidence | why it dents the edge |
|---|---|---|---|---|---|
| 1 | Unguarded English-word / cross-domain bare surnames (swift, marks, burden, london, royals, kraft, kelce, barkley, black, pierce, tremble, cousins, branch, + harvey/hampton/spears/irving/montgomery/jackson/…) | **HIGH** | brain_common.py:109-121 (guard set), :219-228 (bare-key branch), :252 (case-insensitive anywhere) | 13/13 battery inputs mis-tagged; live: baseball tweet on Jalen Royals' card, Charles Barkley tweet on Saquon's card (brain_intel.json 2026-07-05) | Wrong-player intel renders on draft cards; cross-sport/celebrity noise floods n_tw buzz counts that the dashboard treats as signal |
| 2 | Context-pair fires on document-wide co-occurrence (69 live pairs; sean+tucker, kevin+coleman, daniel+jones, jonathan+taylor, denzel+boston, hunter+henry, omar+cooper, deion+burks, parker+washington, garrett+wilson) | **HIGH** | brain_common.py:229-233, :256-257; amplified by brain_video.py:171 (whole transcript = one doc), brain_book.py:97 (60k chars) | 8/8 single-sentence battery inputs mis-tagged; two legit entities (KOC + Keon Coleman) manufacture a phantom third; bypasses the `boston` NEVER-BARE guard | Transcripts/articles — the deepest content — are the most likely to mis-attribute; a phantom player inherits claims/buzz he never earned |
| 3 | Defense-vs-offense + retired/family same-surname mis-tags (Trevon→Stefon Diggs, Bradley→Nick Chubb, Aidan→Xavier Hutchinson, DeMarcus→Trevor Lawrence, Harrison Sr.→Jr.); defender names also trigger coach+team fold-in (Gus Bradley) | **HIGH** | brain_common.py:219-228 (statmenu-only uniqueness), :329-332 (team fold-in); BRAIN_PLAN hole 5 (defenders can't link) is the root | 5/5 battery inputs mis-tagged; "Bradley Chubb" produced player+coach+team triple corruption | Matchup research reads defender takes; each one currently files as intel on the wrong offensive player and pollutes team buzz |
| 4 | Scorer suppresses injury/availability news (no injury vocabulary anywhere); stale stat retros permanently outrank fresh role news; no recency decay; FWD_SINCE fixed at 2026-02-01 | **HIGH** | brain_export.py:43-45, :54-59, :85-86 (−5 no-stats-no-fwd), :282 (`_sc>0` drop), :36, :281 | Executed: ACL tear −4 DROPPED, suspension −4 DROPPED, March stat retro +14 top slot | The single most market-moving qualitative event class is hidden from the card the human reads at pick time |
| 5 | brain_export writes an EMPTY brain_intel.json (exit 0) on empty/missing vault; consumers except-pass; no staleness alarm on `as_of` | **MED-HIGH** | brain_export.py:313-320 (no minimum guard); engine/run_live.py:118-124; build_decision_dashboard.py:842-849 | Verified: `--vault /tmp/emptyvault` → 373-byte export, exit 0 | One bad env var in the 07:30 run nukes the whole qualitative layer silently; the dashboard just shows fewer blocks |
| 6 | Silent feed death: brain_pull/brain_tweet per-handle API errors never reach the health card ("✅ OK · 0 new links"); run_brain.sh stage failures are log-only; `bc.write_status` is a never-called guard | **MEDIUM** | brain_pull.py:80-82,98-103; brain_ingest.py:169-183; run_brain.sh:4,20-41; brain_common.py:348-359 | Code-trace: card `errors` receives only capture-subprocess failures | Quota exhaustion or key expiry looks like a quiet news day; intel currency degrades invisibly |
| 7 | 240-char truncation feeds the scorer AND the card | **MEDIUM** | brain_export.py:132-137, :242-244 | Measured: same tweet scores 12 full / 2 clipped | Longest, highest-substance analyst tweets systematically under-ranked and shown clipped |
| 8 | Entity-page frontmatter `team:` written only at creation; export attaches coach context from it | **MEDIUM** | brain_pages.py:118-135; brain_export.py:221-222, :289-291 | Code-trace (vault not on this box) | Traded player carries old team's HC/OC line on every card — quiet mis-attribution in trade season |
| 9 | Weekly model refresh + film ingest unscheduled (human cron); in-season currency depends on remembering | **MEDIUM** | run_brain_weekly.sh (no plist), brain_film.sh (no plist), brain/ contains only com.nflbrain.ingest.plist | File inventory | Film/scheme layer silently ages; the "current" promise of the brain narrows to tweets |
| 10 | Team aliases match college/city/verb homographs (Tennessee, Miami, Washington, jets, lions-share); "Tampa Bay Rays" tags Tampa Bay | **MEDIUM** | brain_common.py:76-93, :264-267 | 5/5 battery inputs mis-tagged; live Royals tweet also team-tags TB | Team buzz lists and dtw absorb college-draft and other-sport chatter |
| 11 | Hyphenated bare-surname keys can never match (letters-only key vs hyphenated text): Smith-Njigba, St. Brown, Croskey-Merritt, Westbrook-Ikhine | **MEDIUM (false-negative)** | brain_common.py:193/208 (`_letters`) vs :252 | Verified misses on 3/3 battery inputs | High-frequency analyst shorthand drops on the floor — lost signal for premium players |
| 12 | ALL-CAPS counts as proper noun at any position → cap-key guard defeated by chart titles / caps captions; auto-captions (all-lowercase) make cap keys dead (false negatives) | **MEDIUM** | brain_common.py:159-172 | "PRICE CHECK: …ADP MOVERS" → Jadarian Price | Chart-heavy accounts are the corpus core; caption-based video notes lose guarded-surname links |
| 13 | Cap-word cross-domain proper nouns mid-sentence ("White House") | LOW-MED | brain_common.py:126 (`_NEVER_BARE` has only boston) | "The Eagles visited the White House" → Rachaad White | Same class as `boston`, unguarded for white/golden/etc. |
| 14 | dtw (team defense-intel list) built before the negative-score filter | LOW | brain_export.py:297-301 | Code-trace | Joke tweets with defense vocabulary reach matchup research |
| 15 | Subject bonus is substring not word ("brown" ∈ "browns") | LOW | brain_export.py:253-254 | Executed: True | Mis-ranks card order |
| 16 | URL normalization still open (dup notes across http/https/utm variants) — BRAIN_PLAN hole 6 | LOW | brain_ingest.py:28 (junk only), brain_pull.py:89 | Code-trace; prior incident (ftnfantasy dup) documented | Dup source notes inflate buzz counts |
| 17 | brain_link files a claim only under the FIRST-mentioned player | LOW (by design, but lossy) | brain_link.py:136-137 | Code-read | A Signal about the second-named player never reaches his card |
| 18 | Manifest read-modify-write per item; concurrent manual + launchd runs can lose marks; detect_entities reloads statmenu/web_teams per tweet (perf only) | LOW | brain_common.py:65-72; brain_tweet.py:320 | Code-trace | Rare dup notes; slow backfills |

## Known-bad inputs that still mis-fire (consolidated deliverable)

Player mis-tags (all verified by execution today, exact inputs):
1. "Chiefs fans hope Taylor Swift shows up to training camp again this year." → D'Andre Swift
2. "There are real question marks about this Houston offense heading into camp." → Woody Marks
3. "The burden of proof is on the coaching staff after that draft." → Luther Burden III
4. "The Jaguars get a London game again — two home dates at Wembley." → Drake London
5. "Robert Kraft gave Mike Vrabel full roster control this offseason." → Tucker Kraft
6. "The Royals dropped another series; at least Chiefs camp opens Tuesday." → Jalen Royals
7. "They unveiled the black alternate jerseys for the season opener." → Kaelon Black
8. "His arm talent lets him pierce any two-high shell." → Alec Pierce
9. "Defenses tremble when he gets a runway downhill." → Tommy Tremble
10. "My cousins and I split season tickets again this year." → Kirk Cousins
11. "The front office extended an olive branch to the veteran room." → Zachariah Branch
12. "Jason Kelce said on New Heights that Philly will run it back." → Travis Kelce
13. "Charles Barkley picked the Eagles on the TNT crossover show." → Saquon Barkley
14. "Trevon Diggs locked down that entire side of the field all afternoon." → Stefon Diggs
15. "Bradley Chubb had three pressures and a strip sack on Sunday." → Nick Chubb + Gus Bradley + team fold-in
16. "Aidan Hutchinson wrecked the game off the edge again." → Xavier Hutchinson
17. "DeMarcus Lawrence set the edge all day against Seattle." → Trevor Lawrence
18. "Marvin Harrison went into the Hall of Fame back in 2016." → Marvin Harrison Jr.
19. "Sean McVay raved about what Tucker Kraft put on tape last year." → Sean Tucker
20. "Kevin O'Connell and rookie Keon Coleman were both trending after minicamp." → Kevin Coleman Jr.
21. "Daniel Jeremiah ranked the class and Jerry Jones promptly disagreed." → Daniel Jones
22. "Jonathan Gannon and Zac Taylor swapped notes at the owners meetings." → Jonathan Taylor
23. "Denzel Ward shadowed him everywhere; the kid starred at Boston College." → Denzel Boston
24. "Derrick Henry ran through Danielle Hunter twice on Sunday." → Hunter Henry
25. "Omar Khan traded up while Cooper DeJean blitzed off the slot." → Omar Cooper Jr.
26. "Deion Sanders praised Treylon Burks after the joint practice." → Deion Burks
27. "PRICE CHECK: BIGGEST WR ADP MOVERS OF THE WEEK" → Jadarian Price
28. "The Eagles visited the White House on Tuesday." → Rachaad White

Team mis-tags: 29. "Tennessee beat Alabama 24-17 in Knoxville…" → Titans · 30. "The Miami
Hurricanes have another first-round quarterback." → Dolphins · 31. "Washington Huskies produce
another top-ten pick." → Commanders · 32. "He jets past the corner…" → Jets · 33. "He commands
the lions share of targets…" → Lions.

False negatives: 34. "Smith-Njigba is the WR1 in Seattle…" → nothing · 35. "St. Brown caught 12
of 13 targets in the slot." → nothing · 36. "Croskey-Merritt looks like the lead back in
August." → nothing.

Guards verified still holding: sentence-start cap words ("Likely to play Sunday…"), @handle
stripping ("@TaylorSwift13…"), lowercase full names in captions ("jalen hurts threw…" → Jalen
Hurts), Mike McCarthy (in canon as PIT HC per web_teams.json — a 2026 fact this audit takes from
the verified layer) blocking bare `mccarthy` from J.J.

## Decision points (owner calls — proposals, not changes)

1. **Resolver hardening order** (recommend all three; #2 is the roster-collision mirror):
   (a) extend `_COMMON_WORD_SURNAMES` with the 13+ confirmed words (swift, marks, burden,
   london, royals, kraft, kelce, barkley, black, pierce, tremble, cousins, branch, harvey,
   hampton, spears, irving, montgomery, jackson, howard, simpson, rodriguez, tracy, lemon) and
   add cross-domain names (kraft/kelce/barkley/white) to a NEVER-BARE-style or
   first-name-corroboration tier; (b) tighten context pairs from document-scope to a proximity
   window (same sentence or ±N words) — this alone kills class 1c; (c) load
   `boom/defender_grades.json` as a negative roster: a bare surname preceded by a known
   defender's first name must not tag the offensive player (BRAIN_PLAN hole 5, now with
   evidence). After any fix: run `brain_repair_mentions.py --dry-run` and review TOP DROPS.
2. **Injury vocabulary in the scorer**: add an availability class (ACL/Achilles/IR/PUP/out
   for/suspended/surgery/hamstring/carted) with a strong positive weight — or a dedicated `inj`
   bucket on the card so it never competes with stat tweets. Your stats-first rule stays intact;
   this is a missing category, not a re-weighting.
3. **Fail-loud floor**: (a) refuse to overwrite brain_intel.json when the new export has 0
   players (or <50% of previous counts) unless `--force`; (b) pass pull/tweet error counts into
   the last-run card; (c) an age check in run_live/dashboard ("brain intel is N days old") with
   a threshold you pick.
4. **Truncation**: score on full tweet text, clip only for display (mechanical, but it changes
   which tweets surface — flagging since ranking semantics shift).
5. **Scheduling**: confirm the launchd plist is actually loaded on the Mac
   (`launchctl list | grep nflbrain`); decide whether film (`brain_film.sh`) joins the daily or
   a weekly schedule, and whether `run_brain_weekly.sh` gets its own plist once the season
   starts.
6. **Recency**: whether to add a small date-decay term to tweet ranking and/or a rolling
   FWD_SINCE — this changes ranking semantics, so it is explicitly your call.
7. **Hyphen keys**: add hyphen-preserving surname variants + `st. brown`/`st brown` alias forms
   (restores lost signal; low risk).
