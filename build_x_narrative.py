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
  "Xavier Worthy": dict(sentiment="neutral", themes=["offseason buzz","speed"],
    take="Light offseason content rather than analysis: an Underdog clip (reposted by Josh Norris) joked that if that "
         "was really Worthy 'running around in the grass,' Hayden Winks 'owes everyone an apology' — a nod to the "
         "speed/conditioning chatter that follows him. No projection value here, but it confirms Worthy stays "
         "top-of-mind in the FF conversation entering the summer."),
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
