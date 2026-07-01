#!/usr/bin/env python3
"""build_pull_20260701b.py — pull #3 (X SEARCH scroll, 2026-07-01): combined from: query for analyst
group 1 with -filter:replies, so these are ORIGINAL analytical posts the list virtualized past.
NFL-relevant subset kept (NBA/soccer noise self-filters in the mapper). Emits x_pull_20260701b.json;
build_x_store.py merges it (dedup by id). Raw records verbatim from the search scroll."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))

RAW = [
 {"i":"2072134756083392560","h":"DhananiZain","d":"2026-07-01T01:46:38Z","l":7,"v":0,"lk":[],"s":"","t":"Chiefs rebuilt the offense around more structure, more accountability, and more run game. KC wants a real run game for the first time in years - made a point to get Kenneth Walker. Walker should destroy if he stays healthy. Their breakout pick is Xavier Worthy"},
 {"i":"2072098143894749305","h":"32BeatWriters","d":"2026-06-30T23:21:09Z","l":40,"v":1,"lk":[{"tco":"Qa0vzpAWGn","url":"https://youtu.be/hmhefbdwhyU"}],"s":"","t":"\"Concepcion was the higher draft pick, Denzel Boston was the one who may have stolen the show in the offseason. [Boston] hit the ground running, showing he was more than just a big-bodied target in the red zone\""},
 {"i":"2072095354917421193","h":"32BeatWriters","d":"2026-06-30T23:10:04Z","l":23,"v":0,"lk":[],"s":"","t":"\"Jack Bech and Dont'e Thornton Jr. are both looking to grow in their sophomore campaigns. Despite earning prominent roles in the offense last training camp, rookie pains and team challenges arose. Bech seemed to be more comfortable within the offense late in the season\""},
 {"i":"2072087784827802035","h":"32BeatWriters","d":"2026-06-30T22:40:00Z","l":10,"v":0,"lk":[{"tco":"fSQbu3VO20","url":"https://32beatwriters.com"}],"s":"","t":"The Falcons are a team with a lot of questions around their skill positions. @All22_FF breaks down everything you need to know for fantasy — Falcons Training Camp Preview: QB Battle, Bijan and Brian, WR2 Role and more"},
 {"i":"2072080174070276376","h":"DhananiZain","d":"2026-06-30T22:09:45Z","l":14,"v":0,"lk":[],"s":"","t":"Not in the article, but on a given play a max of 5 players can run a route - it usually averages: 2 short routes, 2 intermediate, 1 deep. Waddle + RB/TE will work short/intermediate; Pat Bryant + Waddle/TE intermediate; Sutton deep"},
 {"i":"2072036754245255638","h":"4for4football","d":"2026-06-30T19:17:13Z","l":0,"v":0,"lk":[{"tco":"tTxhnlxdMJ","url":"https://www.4for4.com/2026/preseason/players-bad-teams-can-be-good-fantasy-football"}],"s":"","t":"Players On Bad Teams Can Be Good For Fantasy Football"},
 {"i":"2072028243255759070","h":"DhananiZain","d":"2026-06-30T18:43:24Z","l":74,"v":0,"lk":[{"tco":"K0McQIqP0F","url":"https://www.fantasypoints.com"}],"s":"","t":"Deep threats are not the fantasy boom players you think they are. Route depth MATTERS for fantasy football. Teasing out how it matters and who to target or fade is what I broke down using @FantasyPtsData"},
 {"i":"2072020823016382870","h":"adamlevitan","d":"2026-06-30T18:13:55Z","l":64,"v":0,"lk":[{"tco":"ysSJEchjoF","url":"https://establishtherun.com"}],"s":"","t":"For anyone interested in improving their contest selection in Best Ball specifically, this free article should help. Rake, contest size, advancement structure, finals size all matters"},
 {"i":"2072018300997910773","h":"DhananiZain","d":"2026-06-30T18:03:53Z","l":35,"v":0,"lk":[],"s":"","t":"For Josh Jacobs I am slightly worried about the pile up of right leg injuries with the amount of touches he's had"},
 {"i":"2072016489276752180","h":"FantasyPts","d":"2026-06-30T17:56:41Z","l":9,"v":1,"lk":[{"tco":"Ffwfh0bPWO","url":"https://podcasts.apple.com"}],"s":"","t":"\"If I told you TreVeyon Henderson had 911 yards and 9 TDs last year, you'd say I'm crazy... but he did\" #Patriots #FantasyFootball"},
 {"i":"2072012167956648051","h":"DBro_FFB","d":"2026-06-30T17:39:31Z","l":27,"v":0,"lk":[],"s":"","t":"ANOTHER Jaylen Waddle tweet"},
 {"i":"2072004355197198356","h":"DhananiZain","d":"2026-06-30T17:08:28Z","l":13,"v":0,"lk":[],"s":"","t":"Really strong discussion from @AlbertBreer and @ConorOrr: How coaches try to copy Shanahan and McVay but can't (learn the why, not just copy). The rise of hybrid players like Kyle Hamilton and Nick Emmanwori (hopefully Caleb Downs too). Defenses dictating"},
 {"i":"2071987661162864971","h":"adamlevitan","d":"2026-06-30T16:02:08Z","l":151,"v":0,"lk":[],"s":"","t":"A quick guide for interpreting beat writer speculation in June: 1. If it confirms your priors, use it to victory lap. 2. If it goes against your priors, dismiss it as meaningless nonsense."},
 {"i":"2071987443121754117","h":"FantasyPts","d":"2026-06-30T16:01:16Z","l":21,"v":0,"lk":[],"s":"","t":"Some receivers just have a knack for finding the soft spot in zone coverages @FantasyPtsData (zone vs man YPRR 2023-2025: Jayden Reed, Ja'Marr Chase, Khalil Shakir, Jaylen Waddle, Gabe Davis best against zone)"},
 {"i":"2071975051088314520","h":"ASchatzNFL","d":"2026-06-30T15:12:02Z","l":3,"v":0,"lk":[{"tco":"CPQm8wIs6S","url":"https://ftnfantasy.com"}],"s":"","t":"More content from @BryKno featuring @FTNFantasy charting from the upcoming Almanac, a look at how WR performed in the slot vs out wide in 2025. 2025 Slot-Wide Stats for WR: More Domination from Nacua and JSN"},
 {"i":"2071966246854066468","h":"DhananiZain","d":"2026-06-30T14:37:03Z","l":16,"v":0,"lk":[],"s":"","t":"Pretty much spot on with what we've said the Packers view MarShawn Lloyd as (similar to Jaydon Blue for the Cowboys): they have to prove it (health for Lloyd, maturity for Blue), something the teams hope for but have contingencies if not"},
 {"i":"2071964559066239077","h":"4for4football","d":"2026-06-30T14:30:20Z","l":9,"v":0,"lk":[],"s":"","t":"Clean pockets. Better rushing lanes. More stable scoring environments. Here's the full 2026 OL rankings board, grouped by tier: Tier 1 Broncos; Tier 2 Rams, Bears, Eagles, Chargers; Tier 3 Bills, Buccaneers, Panthers, 49ers, Vikings, Cowboys, Seahawks; Tier 4 Falcons, Jets, Giants, Patriots, Colts, Lions, Cardinals, Steelers, Ravens, Raiders; Tier 5 Commanders, Chiefs, Jaguars, Packers, Saints, Titans, Bengals; Tier 6 Browns, Dolphins, Texans"},
 {"i":"2071963262489350503","h":"DhananiZain","d":"2026-06-30T14:25:11Z","l":79,"v":0,"lk":[],"s":"","t":"On KC Concepcion - good to hear this is exactly how we WANT him to be used: Concepcion's potential in the offense as a versatile weapon"},
 {"i":"2071960730484523098","h":"DhananiZain","d":"2026-06-30T14:15:07Z","l":11,"v":0,"lk":[{"tco":"jufP0rl3S7","url":"https://www.espn.com"}],"s":"","t":"Sounds like Year 2 in Nick Caley's offense for CJ Stroud is leading to a stronger grasp of the offense - during OTAs and minicamp the pre-snap operation was more in sync. The fourth-year quarterback (Texans) growing much closer"},
 {"i":"2071956401849594327","h":"32BeatWriters","d":"2026-06-30T13:57:55Z","l":10,"v":0,"lk":[],"s":"","t":"What does the addition of Pete Carmichael mean for the offense?"},
]

def main():
    out = []
    for r in RAW:
        links = []
        for lk in r.get("lk", []):
            links.append({"tco": lk.get("tco"), "url": lk.get("url"), "disp": lk.get("url","")})
        out.append({
            "id": r["i"], "handle": r["h"], "name": None, "text": r["t"], "date": r["d"],
            "likes": r["l"], "url": f"https://x.com/{r['h']}/status/{r['i']}",
            "kind": "tweet", "has_media": bool(r["v"]), "social": r.get("s",""),
            "links": links, "source": "x_search_scroll",
        })
    p = os.path.join(HERE, "x_pull_20260701b.json")
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(f"wrote {p} — {len(out)} posts ({sum(1 for x in out if x['links'])} w/ links)")

if __name__ == "__main__":
    main()
