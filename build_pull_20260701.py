#!/usr/bin/env python3
"""build_pull_20260701.py — pull #2 (scrolled 2026-07-01 from the FF Analysts list, ~11:00 06-30 →
01:33 07-01). Emits x_pull_20260701.json in the store schema; build_x_store.py merges it (dedup by id)
into the growing x_store.json. Raw records are verbatim from the list scroll (compact keys expanded)."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))

# compact records: i id, h handle, d date, l likes, v hasVideo, lk [code~display], s social, t text
RAW = [
 {"i":"2072131454528553358","h":"fball_insights","d":"2026-07-01T01:33:31Z","l":0,"v":0,"lk":[],"s":"","t":"Bengals league-worst run stuff% on first and second down last year. Even just regressing to average while maintaining lighter boxes should help defensive floor"},
 {"i":"2072130799810359327","h":"AhaanRungta","d":"2026-07-01T01:30:55Z","l":3,"v":0,"lk":[],"s":"","t":"The New York fanbase booing Cathy Engelbert through her entire postgame speech:"},
 {"i":"2072126975477755933","h":"TheFanLA","d":"2026-07-01T01:15:43Z","l":3,"v":1,"lk":[],"s":"James D Koh reposted","t":"Tune in with @JamesDKoh from 6-10p as a wild NBA offseason explodes: Does a messy exit for less cash cost Lebron James his Lakers statue privileges? LA has $52M in cap space and a broken-up core that went 15-2 with LeBron, Luka, and Reaves."},
 {"i":"2072126416892616877","h":"DBro_FFB","d":"2026-07-01T01:13:30Z","l":2,"v":0,"lk":[],"s":"","t":"Shocking"},
 {"i":"2072126297514582176","h":"HaydenWinks","d":"2026-07-01T01:13:02Z","l":11,"v":1,"lk":[],"s":"","t":"very important message here. please give it a listen."},
 {"i":"2072098207740436935","h":"DrewDavenportFF","d":"2026-06-30T23:21:25Z","l":3,"v":0,"lk":[],"s":"Fantasy Points Data reposted","t":"Aaron Rodgers ranked 35th in the NFL in deep throw percentage in 2025 at just 9.4% (@FantasyPtsData). Michael Pittman's PPR ppg fantasy finishes the last 5 years: 2021 - 28th 2022 - 25th 2023 - 14th 2024 - 47th 2025 - 26th Current ADP: WR41"},
 {"i":"2071911882668064953","h":"FantasyPts","d":"2026-06-30T11:01:01Z","l":20,"v":0,"lk":[],"s":"Fantasy Points Data reposted","t":"As \"washed\" as Alvin Kamara might be, he really hasn't been much worse than Travis Etienne. Hilariously, only the Arizona Cardinals have more money invested in the RB position than the Saints @FantasyPtsData"},
 {"i":"2072125047586668612","h":"smitchell17","d":"2026-07-01T01:08:04Z","l":2,"v":0,"lk":[],"s":"","t":"Just taking it day-by-day"},
 {"i":"2072124195987681417","h":"smitchell17","d":"2026-07-01T01:04:41Z","l":3,"v":0,"lk":[],"s":"","t":"Is Russini also the fish head exec???"},
 {"i":"2072123988139278554","h":"HaydenWinks","d":"2026-07-01T01:03:51Z","l":4,"v":0,"lk":["EFaeVZrCm0~https://youtu.be/pT94M-5niFk"],"s":"","t":"The 2 sleeper QBs to draft in all formats."},
 {"i":"2072122691776315851","h":"AhaanRungta","d":"2026-07-01T00:58:42Z","l":5,"v":0,"lk":[],"s":"","t":"Now we get a full quarter to relax and entertain some greed for more."},
 {"i":"2072028072631472456","h":"MattHarmon_BYB","d":"2026-06-30T18:42:43Z","l":62,"v":0,"lk":[],"s":"Matt Harmon reposted","t":"Jaxon Smith-Njigba 2025 #ReceptionPerception Profile. Some highlights: - 77.8% success rate vs. man coverage (94th percentile) - 82.5% success rate vs. zone - 80% success rate vs. press. RP helps show that JSN was pretty convincingly among the best, if not the premier, route runner"},
 {"i":"2072121628532547729","h":"smitchell17","d":"2026-07-01T00:54:29Z","l":2,"v":0,"lk":[],"s":"","t":"In my best Donald Trump voice: I am a donkey"},
 {"i":"2072121432906084814","h":"Pat_Thorman","d":"2026-07-01T00:53:42Z","l":18,"v":0,"lk":[],"s":"","t":"parasite"},
 {"i":"2072121133734736310","h":"smitchell17","d":"2026-07-01T00:52:31Z","l":0,"v":1,"lk":[],"s":"","t":"Ecuador..."},
 {"i":"2072120788237349204","h":"smitchell17","d":"2026-07-01T00:51:08Z","l":0,"v":0,"lk":[],"s":"","t":"Donation for the night chefs kiss"},
 {"i":"2072120470837625275","h":"smitchell17","d":"2026-07-01T00:49:53Z","l":0,"v":0,"lk":[],"s":"","t":"Alright ONE TIME NO WHAMMIES, LET'S GO ECUADOR"},
 {"i":"2072120054636839377","h":"JoshNorris","d":"2026-07-01T00:48:13Z","l":11,"v":0,"lk":["WlwqZ6wVgd~https://youtu.be/pT94M-5niFk"],"s":"","t":"I love drafting elite QBs this season but if I miss out on them - I'm waiting and waiting.... and waiting for these two perfect late-round QB targets"},
 {"i":"2072119829121695797","h":"Clevta","d":"2026-07-01T00:47:20Z","l":146,"v":1,"lk":[],"s":"","t":"Windy u dirty dog"},
 {"i":"2072112825502515505","h":"JakobSanderson","d":"2026-07-01T00:19:30Z","l":0,"v":0,"lk":[],"s":"","t":"I am in hell"},
 {"i":"2072111125953491443","h":"smitchell17","d":"2026-07-01T00:12:45Z","l":6,"v":0,"lk":[],"s":"","t":"Things you never want to hear when you are 5 beers deep at the Dollar General buying more booze: You look so familiar"},
 {"i":"2072034255216038148","h":"ScottBarrettDFB","d":"2026-06-30T19:07:17Z","l":42,"v":0,"lk":[],"s":"Zain Dhanani reposted","t":"Killer debut piece by @DhananiZain looking into the importance of route depth for WRs. Contrary to public opinion, WRs who run deeper route trees are NOT \"higher-ceiling\" on a weekly basis"},
 {"i":"2072110491996950814","h":"smitchell17","d":"2026-07-01T00:10:13Z","l":0,"v":0,"lk":[],"s":"","t":"It's a survival tactic"},
 {"i":"2072028243255759070","h":"DhananiZain","d":"2026-06-30T18:43:24Z","l":74,"v":0,"lk":["K0McQIqP0F~https://www.fantasypoints.com fantasy factors understanding route depth"],"s":"","t":"Deep threats are not the fantasy boom players you think they are. Route depth MATTERS for fantasy football. Teasing out how it matters and who to target or fade is what I broke down using @FantasyPtsData"},
 {"i":"2072108879173849408","h":"DhananiZain","d":"2026-07-01T00:03:49Z","l":0,"v":0,"lk":[],"s":"","t":"Additional insight as questions arise:"},
 {"i":"2072108002199359833","h":"FantasyPts","d":"2026-07-01T00:00:20Z","l":6,"v":1,"lk":["kAMdQlwNLS~https://youtu.be/sUX3JTCEYBw"],"s":"","t":"\"Zero RB was never alive as far as I'm concerned... it didn't die, it never even had a life\" #FantasyFootball #FantasyDraft. Is zero-RB officially dead in 2026, or are you still loading up on receivers? @Fantasy_Guru @GrahamBarfield @DrakeFantasy"},
 {"i":"2071995113375510828","h":"BackThenFB","d":"2026-06-30T16:31:45Z","l":599,"v":1,"lk":[],"s":"Ian Hartitz reposted","t":"When Dennis Dixon ran the fake Statue of Liberty to perfection #GoDucks"},
 {"i":"2072101051419996649","h":"Ihartitz","d":"2026-06-30T23:32:43Z","l":65,"v":0,"lk":[],"s":"","t":"Not AI @John_Mateer4"},
 {"i":"2072098143894749305","h":"32BeatWriters","d":"2026-06-30T23:21:09Z","l":34,"v":0,"lk":["Qa0vzpAWGn~https://youtu.be/hmhefbdwhyU"],"s":"","t":"\"Concepcion was the higher draft pick, Boston was the one who may have stolen the show in the offseason. [Boston] hit the ground running, showing that he was more than just a big-bodied target in the red zone\" Check out more on Boston with Chris"},
 {"i":"2072097379894075532","h":"Ihartitz","d":"2026-06-30T23:18:07Z","l":211,"v":1,"lk":[],"s":"","t":"Got Burrow 7 picks past ADP stacked with Chase-Higgins but we still got 12 rounds to go"},
 {"i":"2072095354917421193","h":"32BeatWriters","d":"2026-06-30T23:10:04Z","l":19,"v":0,"lk":[],"s":"","t":"\"Jack Bech and Dont'e Thornton Jr. are both looking to grow in their sophomore campaigns. Despite earning prominent roles in the offense last training camp, rookie pains and team challenges arose. Bech seemed to be more comfortable within the offense late in the season\""},
]

def main():
    out = []
    for r in RAW:
        links = []
        for lk in r.get("lk", []):
            code, _, disp = lk.partition("~")
            url = disp if disp.startswith("http") else ("https://t.co/" + code)
            links.append({"tco": code, "url": url, "disp": disp})
        out.append({
            "id": r["i"], "handle": r["h"], "name": None, "text": r["t"], "date": r["d"],
            "likes": r["l"], "url": f"https://x.com/{r['h']}/status/{r['i']}",
            "kind": "tweet", "has_media": bool(r["v"]), "social": r.get("s", ""),
            "links": links, "source": "x_list_scroll",
        })
    p = os.path.join(HERE, "x_pull_20260701.json")
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(f"wrote {p} — {len(out)} posts ({sum(1 for x in out if x['links'])} with links, "
          f"{sum(1 for x in out if x['has_media'])} with video)")

if __name__ == "__main__":
    main()
