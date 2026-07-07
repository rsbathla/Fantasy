# BRAIN PLAN AUDIT — holes vs the goal (2026-07-04)

**The goal:** a second brain over articles / videos / tweets that can produce **extremely
comprehensive notes on each player, team, coach, and matchup.**

**The audit trigger (case study, now case law):** the repo's verified canon
(`ground_truth_registry.json`, `web_teams.json`) recorded Jesse Minter as **BAL HC** — yet
`scheme_2026.json` and `coordinator_changes_2026.json` still carried the pre-ruling "DC" label,
and the integration audit never fired. Diagnosis: every existing check audits **wiring**
(who reads what) or **freshness** (mtimes); none audited **value agreement** between two layers
asserting the same fact, and Check I's forbidden-claim scan reads builder `.py` + allow-listed
text only — JSON layers were outside the corpus. A second, behavioral failure: the working agent
asserted "Minter is a DC" from **stale model priors** without consulting the registry — the exact
actor the registry's own `_meta` warns about ("a pre-2026 model will not know").

**Closed today:** `integration_audit.py` **Check J — coaching-fact consistency.**
`web_teams.json` is the structured coaching canon, reconciled against the registry's asserts
prose; every layer that names a coach role must agree (scheme_2026 playcaller/dc,
coordinator_changes oc/dc, coordinator_scheme dc, defensive_profile dc.name, scheme_fit
player-level dc). "HC calls the defense" is now **declared, not implied**
(`def_caller` + `dc_title` in coordinator_changes — BAL: Minter calls D, Weaver holds the title;
dials untouched). The NFL-Brain resolver is itself audited: it must load coaches from the same
canon or Check J fires. Verified this run: 0 violations across ~93 claim sites.
Residual: `boom/scheme_fit.json` currently populates `dc` on 0 player records, so that site
verifies 0 — the count is printed, not hidden; the membership rule arms the moment it populates.

---

## Hole inventory vs the goal

**1. Coaches were not entities — CLOSED today.** The resolver now loads all 96 hc/oc/dc from
`web_teams.json` (70 safe on bare surname — Shanahan, McVay, Minter, Monken, Slowik; 26
collision-prone names require the full name — Ben Johnson, Kellen Moore, Zac Taylor, both
Harbaughs/LaFleurs/Kubiaks). A coach mention backlinks the coach **and folds in his team**, so
"Monken's offense feasts" files under `[[Todd Monken]]` and `[[Cleveland Browns]]`. Re-classifying
the 134 tweets the Heath preview skipped recovered exactly the scheme/playcaller signal (Daboll RB
usage, LaFleur/Monken early-down rates, the ANY/A playcaller leaderboard) while keeping all
replies/banter out. Numbered leaderboards ("1. … 2. …") are no longer mis-read as polls.

**2. Coaching canon drift — CLOSED (Check J above).** One fact, N layers, zero drift, mechanical.

**3. Matchups have no entity anywhere in the vault — OPEN, the biggest structural gap.** The goal
names matchups; nothing produces them. The repo already holds every ingredient:
`pipeline/schedule_2026.csv` + `games_by_week.json` (who plays whom), `scheme_2026.json` dials,
`boom/defensive_profile.json` (shells, funnels, CB rooms), `boom/cover_spec.json` (player
coverage-split specialties), `game_sim.json`, PROE/RZ layers. Proposal: `brain_matchup.py` —
per-week matchup notes that merge the model layers with the narrative intel that backlinks carry
for both teams. Build AFTER the backfill populates the vault.

**4. Model ↔ vault fusion missing — OPEN, the payoff layer.** The prototype vault's `## Model
read` zones are unpopulated; player/team/coach notes don't yet embed the quant layers
(statmenu, flags, cspec, team_env). `brain_link.py` (next build) generates the profile pages:
auto-generated Model read + distilled sourced Intel log + the backlink index. This is what turns
raw capture into "extremely comprehensive notes."

**5. Defensive players can't link — OPEN, medium.** statmenu is offense+DST, so matchup-critical
names (Sauce Gardner, Surtain, Kyle Hamilton — already appearing in ingested transcripts) resolve
to nothing. Cleanest source: `boom/defender_grades.json` as a second roster for the resolver.

**6. URL normalization — OPEN, small.** The backlog run ingested `http://ftnfantasy.com/almanac`
and `https://ftnfantasy.com/almanac` as two documents. Normalize scheme/host and strip tracking
params (`utm_*`) before the manifest check in the orchestrator.

**7. Historical retweets — ACCEPTED LIMIT.** The search API's retweet operators only reach back
~7–10 days, so the May-15 backfill is originals-only (Twitter's constraint). The daily run DOES
capture retweets and dedupes them against their original, so amplified charts flow in from now on.

**8. Known capture edges — OPEN, small fixes.** ESPN articles fail anonymously (paywall/JS) —
either test the cookie path with an ESPN+ login or drop the domain knowingly. Apple-podcast SHOW
pages (not episodes) should be skipped outright. `yt-dlp -U` occasionally needed as platforms
shift. X-native video remains out of scope (needs login).

**9. Concept-only scheme tweets — ACCEPTED for now.** League-wide baselines with no named entity
("QB FP/dropback when pressured vs not") still drop under the no-entity gate. If that starts
stinging, add a `tweet/concept` tag gated on stat vocabulary; deliberately not opened today to
protect signal-to-noise.

**10. The vault itself has no audit — OPEN.** The repo audit now guards the canon the brain reads,
but nothing yet watches the vault: last-run age, recurring error hosts, manifest-vs-notes drift,
orphaned `_media` files. A small `brain_audit.py` (or a section in the daily status card) closes
the loop later.

**11. Alias upkeep lives in code — OPEN, small.** Player/coach short-forms (`jsn`, `cmc`, `koc`)
are Python constants; moving them to a gitignored-or-committed `brain/aliases.json` lets Ramneik
extend them without code edits.

**12. Chart OCR at ingest — PARKED deliberately.** Chart text usually repeats the numbers (they're
captured); images are saved and vision-readable on demand. Revisit only if text-sparse charts
prove common.

## Sequencing

Re-preview @RyanJ_Heath (verify coach recovery live) → **backfill all 48 since 2026-05-15** →
`brain_link.py` profile pages (players/teams/coaches, Model read + Intel log) →
`brain_matchup.py` weekly matchup notes → query playbook for the combing agent
(vault backlinks + `ask_data.py` quant bridge answered together).
