#!/usr/bin/env python3
"""build_x_media.py — the ARTICLE/VIDEO index layer for the dossier.

Every pull, tweets carry links to articles, videos, and podcasts. This indexes them: each item is
classified (article/video/podcast), summarized (WebFetched in full when the page is public; otherwise
grounded in the posting analyst's own tweet-thread, clearly labelled), and mapped to the player(s) it
names via the SAME mapper the tweet layer uses. Output: x_media.json (a library) + by_player mapping
that build_dossier_deep.py surfaces as an "Articles & video (indexed)" section.

Honesty: summaries note their source. Full video transcripts require the local faster-whisper tool
(the old scroller stack); where that isn't run, video items are summarized from title + posting tweet
+ any public description, and say so. Never fabricated.

Re-run after each pull:  python3 build_x_media.py
"""
import core, json, os
import x_dossier_refresh as xdr
HERE = os.path.dirname(os.path.abspath(__file__))
fn = core.fn

# Each item: type, by (handle), url, title, summary, summary_src, and the tweet context it came from.
MEDIA = [
  dict(type="article", by="4for4football", url="https://www.4for4.com/2026/preseason/players-bad-teams-can-be-good-fantasy-football",
       title="Players On Bad Teams Can Be Good For Fantasy Football",
       summary_src="fetched (public article)",
       summary=("Justin Edwards analyzed bottom-5 scoring offenses (pts/drive) 2021-2025. Bad offenses badly "
         "underperform expectation: 0 top-12 QBs (vs 9.4 expected), 11 top-24 RBs (vs 18.8), 6 top-24 WRs (vs 18.8). "
         "WHAT SURVIVES a bad offense: (1) volume-monopoly RBs at 70%+ snaps — David Montgomery, Jonathan Taylor, "
         "Saquon Barkley, Tony Pollard, Ashton Jeanty; (2) target-hog WRs — Garrett Wilson (30.4% share), Chris Olave "
         "(27.2%), Malik Nabers (32.2%) — production through concentration, though ceilings stay capped; (3) TEs with "
         "weak WR competition. AVOID on bad offenses: every QB (none finished top-12 in 5 yrs — explicitly flags Malik "
         "Willis); secondary WRs (Wan'Dale Robinson, Jalen Coker, Omar Cooper Jr., Adonai Mitchell); and early-down-only "
         "RBs with no receiving work (the Quinshon Judkins archetype: 50% snaps but 7% target share).")),
  dict(type="article", by="DhananiZain", url="https://x.com/DhananiZain/status/2072028243255759070",
       title="Fantasy Factors: Understanding Route Depth (FantasyPoints)",
       summary_src="grounded in the author's own tweet thread (full article is subscriber-gated)",
       summary=("Zain Dhanani's counterintuitive finding from charting route depth: deep threats are NOT the fantasy "
         "boom players people assume. WRs who run DEEPER route trees are NOT higher-ceiling week to week — those with "
         "SHALLOWER trees both boom MORE and bust LESS. Practical read: for weekly floor+ceiling, favor underneath/"
         "intermediate target-earners over pure deep threats. Route-role examples he cites: Jaylen Waddle works short/"
         "intermediate, Pat Bryant intermediate, Courtland Sutton the deep role — implying Waddle's shallower profile is "
         "the more fantasy-friendly of the group. (RyanJ_Heath amplified the same takeaway.)")),
  dict(type="video", by="FantasyPts", url="https://youtu.be/vMdE3xxd944",
       title="TEE > LADD — Tee Higgins vs Ladd McConkey (Fantasy Points)",
       summary_src="from the posting tweet + video title (not transcribed — needs the local whisper tool)",
       summary=("A Fantasy Points video staking out the Tee Higgins over Ladd McConkey position at the 3/4 draft turn: "
         "\"I will not draft Ladd McConkey over Tee Higgins, no matter what... that's a bridge too far.\" The room's read "
         "is Higgins as the firmer back-of-3rd/top-4th anchor over McConkey.")),
  dict(type="podcast", by="DhananiZain", url="https://x.com/DhananiZain/status/2072078040797245906",
       title="Route depth — companion podcast",
       summary_src="companion to the route-depth article (not transcribed)",
       summary=("Audio companion to Dhanani's route-depth piece — same thesis: shallower route trees are the more "
         "reliable fantasy profile; deep-threat usage is over-valued for weekly scoring.")),
]

# Media seen in the pull but whose link wasn't captured (need a re-scroll to grab the t.co) — logged so
# coverage is never silently dropped.
UNRESOLVED = [
  "Establish the Edge — 'ETE Projections Special Part 3: AFC West with Ben…' (podcast, ~2h38m)",
  "ooooftw — fantasy.vip 'Best Ball Player Data' dashboards (Underdog + DraftKings)",
  "Underdog Fantasy Football (Josh & Hayden) — YouTube: 'Ryan Flournoy might be the most underrated WR in the NFL'",
]

def main():
    players, by_last = xdr.player_index()
    by_player = {}
    out_items = []
    for m in MEDIA:
        # map on title + summary (the substantive text)
        pseudo = {'text': (m['title'] + '. ' + m['summary'])}
        pl, tm = xdr.map_post(pseudo, players, by_last)
        item = {**m, 'players': sorted(pl), 'teams': sorted(tm)}
        out_items.append(item)
        for fk in pl:
            by_player.setdefault(fk, []).append({
                'type': m['type'], 'by': m['by'], 'title': m['title'], 'url': m['url'],
                'summary': m['summary'], 'summary_src': m['summary_src']})
    out = {'_meta': {'n_items': len(out_items), 'n_players': len(by_player), 'unresolved': len(UNRESOLVED)},
           'items': out_items, 'by_player': by_player, 'unresolved': UNRESOLVED}
    json.dump(out, open(os.path.join(HERE, 'x_media.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"x_media.json: {len(out_items)} items -> {len(by_player)} players tagged")
    for it in out_items:
        print(f"  [{it['type']}] {it['title'][:50]} -> {', '.join(it['players']) or '(no player)'}")

if __name__ == '__main__':
    main()
