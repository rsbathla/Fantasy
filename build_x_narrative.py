#!/usr/bin/env python3
"""build_x_narrative.py — the ANALYSIS layer over the live X pull.

x_dossier_refresh.py maps tweets -> players (x_live.json). This script turns that raw evidence into a
per-player *narrative*: what the tracked analysts are actually saying, the sentiment forming around the
player, the themes driving it, and a synthesized take — each grounded in the mapped posts (attributed,
never invented). Output: x_narrative.json keyed by core.fn(name), merged into the deep dossier as a
"What analysts are saying" section above the raw tweets.

Re-run after every pull:  python3 build_x_narrative.py   (then rebuild the dossier).
Coverage is whatever mapped this pull; players with no mapped posts are skipped (no fabrication).
"""
import core, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
fn = core.fn

# --- the synthesis. Each entry is keyed by display name; `take` is grounded in THIS pull's mapped
#     posts (see x_live.json). sentiment ∈ bullish/bearish/mixed/neutral. Edit per pull. ---
NARR = {
  "Malik Willis": dict(sentiment="bullish", themes=["rushing creation","YAC efficiency","mobile QB2 floor"],
    take="Two tracked analysts surfaced Willis this cycle. Hayden Winks' data has him 3rd in yards-after-contact "
         "per QB carry since 2022 (3.7), tied with Jayden Daniels and a hair behind Baker Mayfield (3.8) — a marker "
         "of real rushing creation, not just designed volume. Josh Norris flagged him as a show topic the same day. "
         "The profile forming: a mobile backup whose contact-balance on the ground gives him a sneaky-high floor if "
         "an injury presses him into starts — a name to stash in deeper/superflex formats, not redraft yet."),
  "Baker Mayfield": dict(sentiment="bullish", themes=["rushing creation underrated","efficiency"],
    take="Hayden Winks' yards-after-contact-per-carry leaderboard (since 2022) has Mayfield 1st at 3.8 — ahead of "
         "Jayden Daniels and Malik Willis. The takeaway analysts are drawing: Mayfield's mobility and off-script "
         "creation are underrated relative to his 'pocket passer' label, quietly adding a rushing/extension element "
         "to an already strong Tampa passing profile."),
  "Jayden Daniels": dict(sentiment="bullish", themes=["elite rushing QB","contact balance"],
    take="Reinforcement, not news: Winks' data slots Daniels 2nd in YAC per QB carry since 2022 (3.7). It corroborates "
         "the rushing-QB thesis that underpins his elite fantasy ceiling — the legs are a structural part of the "
         "scoring profile, and the efficiency (not just volume) holds up against the league's best."),
  "Rome Odunze": dict(sentiment="bullish", themes=["Y3 leap bet","contrarian","prospect pedigree"],
    take="Jakob Sanderson is on the contrarian buy: he'd take Odunze (career 1.33 YPRR) over Marvin Harrison for a "
         "Year-3 leap despite Harrison's higher raw number (1.61), arguing Odunze is the better prospect who has "
         "'been better in the NFL despite being talked about as a far larger disappointment.' The narrative forming: "
         "a market-discounted breakout candidate whose perception lags his on-field profile — exactly the ADP gap "
         "best-ball drafters hunt."),
  "Marvin Harrison": dict(sentiment="mixed", themes=["higher raw YPRR","being faded for Odunze"],
    take="Cited by Sanderson with the better raw efficiency of the pair (1.61 career YPRR vs Odunze's 1.33), but in "
         "the same breath he's the one being faded — Sanderson prefers Odunze for the Year-3 leap. So the read is "
         "split: the underlying receiving efficiency is strong, yet at least one sharp analyst is betting the breakout "
         "capital elsewhere. Worth watching whether that's a lone contrarian or the start of a market cooling."),
  "Luther Burden": dict(sentiment="bullish", themes=["breakout buzz","Bears offense","film-charting"],
    take="Early film-charting buzz: Alfredo Brown (reposted by James D Koh), mid-way through charting Caleb Williams, "
         "volunteered that 'Luther Burden should have a monster season for the Bears.' It's an unsolicited, "
         "process-driven bullish tag from someone in the tape — the kind of pre-ADP signal that tends to precede a "
         "rising best-ball price on a young Bears pass-catcher."),
  "Caleb Williams": dict(sentiment="neutral", themes=["being film-charted","Bears passing game"],
    take="Surfaced via Alfredo Brown's in-progress charting project rather than a verdict — the analysis is still "
         "being built. The adjacent tell is positive, though: the same charting work spun off a 'monster season' "
         "call on his teammate Luther Burden, implying the early read on the Bears' passing-game environment is "
         "constructive. Watch for the finished charting piece."),
  "Tee Higgins": dict(sentiment="bullish", themes=["3/4-turn debate","preferred over McConkey"],
    take="Fantasy Points framed the Tee Higgins vs Ladd McConkey 3/4-turn question, and the quoted stance lands on "
         "Higgins — 'I will not draft Ladd McConkey over Tee Higgins, no matter what... that's a bridge too far.' "
         "Translation: among sharp drafters, Higgins is the firmer hold at that ADP range, a back-of-3rd/top-4th "
         "anchor the room defends."),
  "Ladd McConkey": dict(sentiment="mixed", themes=["3/4-turn debate","ranked behind Higgins"],
    take="In the conversation at the 3/4 turn — which itself signals real value — but on the losing side of this "
         "particular take: Fantasy Points' quoted stance won't draft McConkey over Tee Higgins ('a bridge too far'). "
         "The profile is a quality WR whose price has climbed into a tier where at least some sharps would rather "
         "have the bigger-bodied alpha. A live ADP debate to track, not a settled fade."),
  "Aaron Jones": dict(sentiment="bullish", themes=["dynasty late-round value","ADP discount"],
    take="Ian Hartitz publicly 'used a late-round flyer on Aaron Jones in a dynasty startup' (470 likes) — a "
         "value-at-cost signal. The read: the market's age/role discount has pushed Jones to a price where sharp "
         "drafters are happy to absorb the risk for the standalone touches. A cheap-share, contingent-upside name "
         "rather than a core build piece."),
  "MarShawn Lloyd": dict(sentiment="mixed", themes=["perennial sleeper","hype-trap","unrealized talent"],
    take="Ian Hartitz's self-aware 'tricking myself into drafting MarShawn Lloyd every summer' (282 likes) captures "
         "the whole profile: enough talent/landing-spot appeal that the sharp crowd keeps buying, but a track record "
         "that has repeatedly burned them. He's the canonical zero-cost dart — fine as a last-pick swing, dangerous "
         "if you talk yourself into a real allocation. Sentiment is affectionate skepticism, not conviction."),
  "Matthew Stafford": dict(sentiment="mixed", themes=["top-QB debate","volatile year-to-year"],
    take="Surfaced in a CTM_Show segment (reposted by Sam Monson) debating where Stafford ranks among top QBs, with "
         "an explicitly jagged résumé read: 'the Super Bowl run was excellent, 2022 a disappointment, 2023 excellent "
         "and underrated, 2024 a disappointment.' The forming view is volatility — a ceiling that has won titles next "
         "to floor years — which argues for treating his fantasy outlook as range-wide rather than a stable median."),
  "Xavier Worthy": dict(sentiment="bullish", themes=["Chiefs breakout call","speed"],
    take="The signal firmed up this cycle: in Dhanani's read of a rebuilt Chiefs offense (more structure, real run game), "
         "'their breakout pick is Xavier Worthy' — an explicit breakout call, not just speed chatter. Earlier offseason "
         "content (the Underdog 'running around in the grass' clip) keeps him top-of-mind; now there's a role-based thesis "
         "under it. A rising best-ball target if the KC offense is as re-tooled as described."),
  "Emanuel Wilson": dict(sentiment="neutral", themes=["committee backfield","goal-line role","TD equity"],
    take="Appears in Nathan Jahnke's early backfield role-projection, tagged as the goal-line back. In a committee "
         "that caps any one back's volume, the goal-line tag is the valuable one — it's where the TD equity (and "
         "fantasy spikes) concentrate. Note Jahnke frames this as a 'best guess' for early in the season, so it's a "
         "role read to monitor through camp, not a settled depth chart."),
  "Jadarian Price": dict(sentiment="neutral", themes=["committee backfield","early-down volume"],
    take="In Jahnke's early backfield 'best guess,' Price profiles as the early-down/volume back. Early-down work "
         "means rushing attempts and a snap floor but limited passing-down or goal-line upside in this projection — "
         "a yardage-dependent role whose fantasy value hinges on whether the committee consolidates his way. A "
         "camp-watch name."),
  "George Holani": dict(sentiment="neutral", themes=["committee backfield","third-down/passing role"],
    take="Jahnke's early projection slots Holani into the third-down role. In PPR/best-ball terms that's the "
         "pass-catching niche — useful for reception floor but typically the lowest-ceiling slice of a committee "
         "unless injuries collapse the timeshare. Role clarity is the story; volume is the question."),
  # --- pull #2 (2026-07-01) ---
  "Jaxon Smith-Njigba": dict(sentiment="bullish", themes=["elite route-running","separation vs all coverages"],
    take="Matt Harmon's 2025 Reception Perception profile is a green light: 77.8% success vs man (94th percentile), "
         "82.5% vs zone, 80% vs press — Harmon's read is JSN was 'convincingly among the best, if not the premier' route "
         "runner in the league. Separation that holds up against man, zone AND press is the most stable, coverage-proof "
         "skill a WR can have; the profile forming is a bankable target-earner, not a scheme-dependent one."),
  "Aaron Rodgers": dict(sentiment="bearish", themes=["dead deep ball","downfield ceiling capped"],
    take="Drew Davenport (on FantasyPtsData) flags Rodgers 35th in the NFL in deep-throw rate in 2025 at just 9.4%. "
         "For fantasy that's less about Rodgers himself and more a ceiling-cap on his pass-catchers: a QB who won't push "
         "the ball downfield compresses aDOT and big-play equity for the WRs attached to him. A checkdown-heavy passing "
         "environment to price in."),
  "Michael Pittman": dict(sentiment="mixed", themes=["ADP discount","volatile finishes","QB headwind"],
    take="Surfaced in Davenport's thread as a value case with a caveat: PPR-ppg finishes of 28/25/14/47/26 the last five "
         "years — genuinely volatile — against a current WR41 ADP. The discount is real, but the same thread's point about "
         "a low-deep-ball QB is a headwind on his downfield upside. A floor-priced target-earner bet, not a ceiling bet."),
  "Alvin Kamara": dict(sentiment="mixed", themes=["aging but steady","committee-investment backfield"],
    take="Fantasy Points frames him bluntly: 'as washed as Kamara might be, he really hasn't been much worse than Travis "
         "Etienne' — faint praise that still keeps him in the viable range. Note the team context they flag: only Arizona "
         "has more money invested at RB than the Saints, so expect a committee that caps his ceiling even as he holds the "
         "lead early-down/passing-down role. A steady-but-fading vet, drafted at cost."),
  "Travis Etienne": dict(sentiment="bearish", themes=["efficiency slipped","used as the low bar"],
    take="Used by Fantasy Points as the *low bar* in a Kamara comparison ('Kamara hasn't been much worse than Etienne') — "
         "not where a former high-pick back wants to be cited. The implication is his efficiency has slipped to a level a "
         "declining veteran now matches; a name whose draft price should reflect the fade unless the role/volume argues back."),
  "Denzel Boston": dict(sentiment="bullish", themes=["rookie camp buzz","role beyond red zone"],
    take="32 Beat Writers' offseason profile is an early breakout tell: Boston 'hit the ground running' and showed he's "
         "'more than just a big-bodied target in the red zone,' possibly having 'stolen the show' over higher-drafted "
         "Concepcion. Buzz that he's earning a full route role (not just a goal-line body) is exactly the pre-camp signal "
         "that moves a rookie WR up boards."),
  "Jack Bech": dict(sentiment="neutral", themes=["sophomore leap watch","late-season comfort"],
    take="32 Beat Writers note Bech is looking to grow in Year 2 after rookie growing pains, and 'seemed more comfortable "
         "within the offense late in the season.' A developmental camp-watch profile — the trajectory (late-season comfort) "
         "is encouraging, but the role isn't locked; one to monitor through August, not draft on faith."),
  "Dont'e Thornton": dict(sentiment="neutral", themes=["sophomore leap watch","role uncertain"],
    take="Grouped with Bech in the 32 Beat Writers' sophomore-growth note: prominent role earned last camp, then rookie "
         "pains and team challenges. A field-stretcher archetype whose Year-2 role is still being sorted — deep-league "
         "camp-watch, not a redraft target yet."),
  # --- pull #3 (2026-07-01, search grab) ---
  "Kenneth Walker": dict(sentiment="bullish", themes=["new run-game role","health-gated ceiling"],
    take="Dhanani frames a genuinely new environment: the Chiefs 'made a point to get Kenneth Walker' and want a real "
         "run game 'for the first time in years,' with the read that 'Walker should destroy if he stays healthy.' If the "
         "team/role is as described (the board also lists this KC move — worth confirming, not assuming), it's a volume-"
         "and-efficiency upgrade gated only by his durability. The health caveat is the whole risk."),
  "TreVeyon Henderson": dict(sentiment="bullish", themes=["hidden production","under-radar"],
    take="Fantasy Points' hook does the work: 'if I told you TreVeyon Henderson had 911 yards and 9 TDs last year you'd "
         "say I'm crazy... but he did.' A Patriots back who quietly posted starter-level counting stats while flying under "
         "the ADP radar — the kind of proven-but-unpriced profile that outperforms its cost."),
  "Jaylen Waddle": dict(sentiment="bullish", themes=["coverage-proof underneath","zone-beater"],
    take="Two independent signals converge on Waddle as a stable target-earner: Dhanani's route-depth work slots him in "
         "the short/intermediate role (the shallower, more fantasy-friendly profile that booms more and busts less), and "
         "Fantasy Points' zone-vs-man chart lists him among the best against zone (2.69 zone YPRR, +0.88 over man). A "
         "separation-first WR whose value doesn't hinge on deep shots."),
  "Ja'Marr Chase": dict(sentiment="bullish", themes=["elite vs all coverage","zone-dominant"],
    take="Reinforcement of the obvious with detail: Fantasy Points' chart has Chase elite against both looks (2.69 zone / "
         "1.67 man YPRR, a +1.02 zone delta among the league's best). Coverage-agnostic dominance — no scheme neutralizes "
         "him — which is exactly the foundation of a first-round, every-week WR1."),
  "Jayden Reed": dict(sentiment="bullish", themes=["zone-beater","efficiency"],
    take="Tops Fantasy Points' zone-vs-man YPRR chart (2.64 vs zone, +1.11 delta) — the biggest zone-coverage edge in the "
         "sample. Reads as a receiver who feasts on the soft spots underneath; a stable-floor profile if the target volume "
         "is there in Green Bay's committee."),
  "Khalil Shakir": dict(sentiment="bullish", themes=["zone-beater","slot reliability"],
    take="Featured in Fantasy Points' zone-vs-man chart as a strong zone-beater (2.41 zone YPRR, +0.92 delta). The classic "
         "slot profile — finds the soft spot, moves the chains — which travels well for a PPR floor even without alpha "
         "target share in Buffalo."),
  "Josh Jacobs": dict(sentiment="bearish", themes=["durability risk","touch pile-up"],
    take="Dhanani flags the one thing that can sink a workhorse: he's 'slightly worried about the pile-up of right-leg "
         "injuries with the amount of touches' Jacobs has absorbed. Nothing acute, but a smart, early durability caution on "
         "a high-volume back — a reason to respect the risk at his ADP rather than assume the workload is free."),
  "KC Concepcion": dict(sentiment="bullish", themes=["defined role","versatile weapon","rookie"],
    take="Dhanani likes the fit: reports the team plans to use Concepcion 'exactly how we WANT him to be used' — as a "
         "versatile weapon. Role-clarity buzz for a rookie is the pre-camp signal that precedes an ADP climb; the usage "
         "framing (versatile, not niche) is the bullish part."),
  "CJ Stroud": dict(sentiment="bullish", themes=["Year-2 scheme comfort","pre-snap in sync"],
    take="Dhanani surfaces a quiet-but-real positive: in Year 2 of Nick Caley's offense, Stroud's pre-snap operation "
         "'was more in sync' through OTAs/minicamp. Second-year command of a system usually shows up as cleaner reads and "
         "fewer stalled drives — a bounce-back/step-forward tailwind for Stroud and his pass-catchers."),
  "Jaydon Blue": dict(sentiment="neutral", themes=["prove-it rookie","contingency role"],
    take="Cited by Dhanani as the Cowboys' version of the MarShawn Lloyd bet: a back the team 'has to prove it' with "
         "(maturity, in Blue's case) — 'something the teams hope for but have contingencies if not.' Talent-with-questions; "
         "a cheap upside dart whose path depends on beating out the contingency plan."),
  "Pat Bryant": dict(sentiment="neutral", themes=["deep role","route-depth example"],
    take="Named in Dhanani's route-depth breakdown as the intermediate/deep piece alongside Sutton — i.e., the lower-"
         "floor, boom-or-bust side of the route-depth finding (deeper trees bust more). A big-play flier whose weekly "
         "consistency the data itself cautions against relying on."),
}

def main():
    xlive = json.load(open(os.path.join(HERE, 'x_live.json'), encoding='utf-8'))
    players = xlive.get('players') or {}
    out = {}
    missing = []
    for name, syn in NARR.items():
        k = fn(name)
        posts = players.get(k)
        if not posts:
            missing.append(name); continue
        handles = []
        for p in posts:
            h = p.get('handle')
            if h and h not in handles:
                handles.append(h)
        out[k] = {
            'name': name,
            'sentiment': syn['sentiment'],
            'themes': syn['themes'],
            'take': syn['take'],
            'n_src': len(posts),
            'handles': handles[:6],
        }
    json.dump(out, open(os.path.join(HERE, 'x_narrative.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=0)
    # players that mapped but have no synthesis yet (so we never silently drop coverage)
    unsynth = [k for k in players if k not in out]
    print(f"x_narrative.json: {len(out)} player narratives written")
    if missing:
        print(f"  synthesis present but NOT in this pull (skipped): {', '.join(missing)}")
    if unsynth:
        print(f"  mapped but no synthesis yet: {', '.join(unsynth)}")

if __name__ == '__main__':
    main()
