#!/usr/bin/env python3
"""build_x_posts.py — assemble the live X pull (scrolled from the @rsbatz "FF Analysts" list on
2026-06-30) into the normalized schema x_dossier_refresh.py expects, and write x_posts.json.

This is the FREE "scroller" path: a private X List of the 48 tracked analyst handles is scrolled in
the browser, each rendered tweet harvested from the DOM (id, handle, ISO date, like count, repost
social-context, cleaned text), then emitted here. URLs are reconstructed from the tweet id + handle.
Re-run after each new scroll-pull by replacing POSTS below.
"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))

# (id, handle, iso_date, likes, social_context, text)  — verbatim from the live list scroll
POSTS = [
    ("2072056775952732427","BrettKollmann","2026-06-30T20:36:46Z",314,"","Honestly, not bad. Not great, but certainly not bad. If they end up at like 16th-18th in the league, that's enough."),
    ("2072073074749685891","BrettKollmann","2026-06-30T21:41:32Z",0,"","They need Knight to develop really really badly"),
    ("2072073710836588925","DBro_FFB","2026-06-30T21:44:04Z",0,"","ABSOLUTELY"),
    ("2072070347143176416","ScottBarrettDFB","2026-06-30T21:30:42Z",12,"","If I ever attend a sporting event that ends in 0-0 all of the players should be put to death"),
    ("2072069381832507564","AlfredoABrown","2026-06-30T21:26:52Z",17,"James D Koh reposted","I'm almost done with Caleb Williams' charting for @RecepPerception, and I gotta say... Luther Burden should have a monster season for the Bears"),
    ("2072069430515773779","Clevta","2026-06-30T21:27:04Z",13,"","Being told that barring a last minute change here, Dean Wade will test the market in unrestricted free agency at 6 p.m ET, where Wade is expected to field interest from several playoff teams."),
    ("2072035484268716480","JakobSanderson","2026-06-30T19:12:10Z",92,"","Rome Odunze has a career YPRR of 1.33 Marvin Harrison has a career YPRR of 1.61 If one of these WRs is going to make a Y3 leap I'm betting on the far better prospect -- who has also been better in the NFL despite being talked about as a far larger disappointment"),
    ("2072066008165044321","ScottBarrettDFB","2026-06-30T21:13:28Z",5,"","I'd prefer neither. But if forced to choose I'd bet on the guy who wasn't recently quoted as saying \"my foot don't work no more\""),
    ("2072057869001003201","ooooftw","2026-06-30T20:41:07Z",5,"","the Player Data dashboards just got a nice upgrade these dashboards show fantasy point game logs, BBM advance rates, etc. for 2023-2025 now you can also see player statuses: BYE - on a Bye week SUS - Suspended INJ - Injured OUT - otherwise Out e.g. healthy scratch"),
    ("2072058642493518074","ooooftw","2026-06-30T20:44:12Z",0,"","Underdog version"),
    ("2072058707828175094","ooooftw","2026-06-30T20:44:27Z",0,"","DraftKings version"),
    ("2072056815714488758","Justin_Redwards","2026-06-30T20:36:56Z",0,"4for4 Fantasy Football reposted","Some offenses are going to be prettay prettay bad this year How many of their fantasy pieces actually perform over the years? I took a look @4for4football"),
    ("2072049803710853183","HaydenWinks","2026-06-30T20:09:04Z",29,"","Yards *after* contact per QB carry since 2022: 1. Baker Mayfield (3.8) 2. Jayden Daniels (3.7) 3. Malik Willis (3.7)"),
    ("2072055373045891258","Ihartitz","2026-06-30T20:31:12Z",7,"","dude almost doubled up the next-closest QB in 3rd/4th down scrambles for 1st downs last year lmao"),
    ("2071984585311707397","KevHarlanEffect","2026-06-30T15:49:55Z",8010,"Sean Koerner reposted","“I was just talking to Kevin O'Connell.”"),
    ("2072053867240423897","FFNateJahnke","2026-06-30T20:25:13Z",10,"","My best guess to how the Seahawks backfield goes early in the season Early downs - Jadarian Price Third downs - George Holani Goal line - Emanuel Wilson"),
    ("2072053093345140784","AhaanRungta","2026-06-30T20:22:08Z",6,"","The East just got more competitive but on the bright side, maybe this is what it will take for Scottie Barnes and Collin Murray-Boyles to get their appreciation as one of the best defensive duos in the league."),
    ("2072052644005192039","Ihartitz","2026-06-30T20:20:21Z",470,"","Used a late-round flyer on Aaron Jones in a dynasty startup"),
    ("2072051564236136471","Ihartitz","2026-06-30T20:16:04Z",282,"","Tricking myself into drafting MarShawn Lloyd every summer"),
    ("2072050114915631154","JakobSanderson","2026-06-30T20:10:18Z",9,"","Incredibly happy for Raptors fans"),
    ("2072034685996126241","ohnohedidnt24","2026-06-30T19:09:00Z",4993,"Clevta reposted","Kendrick Perkins: \"Rich Paul, little turtle head snotty nose ass called me all throughout the season every time I'm on TV I get a text message from him. I've been calling him for 2 days now and he been ignoring me. We got a problem\""),
    ("2072049315388723711","smitchell17","2026-06-30T20:07:08Z",4,"","Wondering if they go with the really bad sun burn or light sun burn tbh"),
    ("2072048678617915813","JoshNorris","2026-06-30T20:04:36Z",27,"","I said what I said"),
    ("2072047598119125458","FantasyPts","2026-06-30T20:00:18Z",12,"","\"I will not draft Ladd McConkey over Tee Higgins, no matter what... that's a bridge too far\" #Bengals #BestBall Tee Higgins or Ladd McConkey at the 3/4 turn... where do you stand? @RyanJ_Heath @JakobSanderson"),
    ("2072046795866186203","JoshNorris","2026-06-30T19:57:07Z",11,"","talking malik willis on today's show"),
    ("2072045848167624776","JamesDKoh","2026-06-30T19:53:21Z",0,"","This and Lebron??? My radio show about to go CRAZYYYYYYYY @TheFanLA"),
    ("2072044658360713482","ActionNetworkHQ","2026-06-30T19:48:37Z",7,"Sean Koerner reposted","@The_Oddsmaker has 2 prop picks for tonight's WNBA Commissioner's Cup you don't want to miss... Download the @ActionApp to unlock them!"),
    ("2072045163657265354","SamMonsonNFL","2026-06-30T19:50:38Z",13,"","We had a listener send me a welcome to American citizenship care package. Solid haul of Americana! Thanks, Jared!"),
    ("2072032157749641680","CTM_Show","2026-06-30T18:58:57Z",3,"Sam Monson reposted","Steve and Sam debate where Matthew Stafford falls in the top QB conversation “If you really look at Stafford's five-year career with the Rams, the Super Bowl run was excellent. 2022 was a disappointment, 2023 was excellent and underrated, and 2024 was a disappointment for”"),
    ("2072044508720791625","JakobSanderson","2026-06-30T19:48:02Z",0,"","Bobrovsky isn't definitely worse than Hildeby and Akhtyamov either. But he is definitely pointing in that direction"),
    ("2072044429456609422","JoshNorris","2026-06-30T19:47:43Z",9,"","shoutout Lucas Digne eternal"),
    ("2072043491685708242","Clevta","2026-06-30T19:43:59Z",50,"","What a crappy trade package for the Clippers. There absolutely has to be a big punishment for Aspiration coming soon"),
    ("2072043202014535730","Clevta","2026-06-30T19:42:50Z",79,"","This is eerily similar to when out of nowhere the Cavs traded Jarret Jack to Boston in early July 2014 and at the time nobody really paid attention to it"),
    ("2072043011496956266","RecepPerception","2026-06-30T19:42:05Z",8,"Matt Harmon reposted","Check out the full season analysis from @MattHarmon_BYB and what contributed to the special season"),
    ("2072043004677046392","RecepPerception","2026-06-30T19:42:03Z",11,"Matt Harmon reposted","Best way to describe JSN's breakout season? ELITE"),
    ("2072041998723252247","Clevta","2026-06-30T19:38:03Z",12,"","I'd look to teams like CHI, Brooklyn and Utah in a potential salary shedding trade. CHI could just take Strus for a 2nd rd pick and absorb his contract for ex."),
    ("2072041607805763736","DhananiZain","2026-06-30T19:36:30Z",17,"","Shane Waldron got promoted - added \"Assistant Head Coach\" to his title"),
    ("2072041297993719975","HaydenWinks","2026-06-30T19:35:16Z",102,"","my ankle would look like skattebo's if i tried this"),
    ("2072039196945231997","HaydenWinks","2026-06-30T19:26:55Z",44,"","The 2025 results at QB completely backed up what the data was showing for the previous 5 years of best ball. The math mathed."),
    ("2072038413537362281","JakeLFischer","2026-06-30T19:23:49Z",468,"Clevta reposted","Amid LeBron James' impending exit from Los Angeles, sources say the Cavaliers have held ongoing trade conversations regarding veterans Max Strus and Dennis Schröder, which could help Cleveland free the space to add James, and also benefit the Cavs' effort to retain Dean Wade."),
    ("2072037959491072105","Clevta","2026-06-30T19:22:00Z",120,"","Big move just came on the cavs out of nowhere on kalshi. Must be the Vardon tweet. The Cavs are now the leaders in the clubhouse"),
    ("2072037542568862033","smitchell17","2026-06-30T19:20:21Z",9,"","I'd much rather sweat a little bit than not be able to feel my nose, toes, or fingers No thanks"),
    ("2072037362285019510","Clevta","2026-06-30T19:19:38Z",41,"","Sequence of events if LBJ to the Cavs is actually real. They'd have to dump Strus or Schroeder first to offer the mid level. If that happens then its sirens up from there... Or he signs with GS today and its all moot"),
    ("2072036754245255638","4for4football","2026-06-30T19:17:13Z",0,"","Players On Bad Teams Can Be Good For Fantasy Football"),
    ("2071972456194040235","UDFootballShow","2026-06-30T15:01:43Z",35,"Josh Norris reposted","If that was actually Xavier Worthy running around in the grass, @HaydenWinks owes everyone an apology"),
    ("2072034436040753431","fball_insights","2026-06-30T19:08:00Z",55,"","Defensive play caller efficiency splits vs play action dating back to 2012 Mike Macdonald up there with Belichick"),
    ("2072034255216038148","ScottBarrettDFB","2026-06-30T19:07:17Z",26,"","Killer debut piece by @DhananiZain looking into the importance of route depth for WRs Contrary to public opinion, WRs who run deeper route trees are NOT \"higher-ceiling\" on a weekly basis"),
    ("2072032745115517329","MikeClayNFL","2026-06-30T19:01:17Z",27,"","Will JSN help you roll to another fantasy title in 2026?"),
]

def main():
    out = []
    for (tid, handle, date, likes, social, text) in POSTS:
        out.append({
            'id': tid,
            'handle': handle,
            'name': None,
            'text': text,
            'date': date,
            'likes': likes,
            'url': f"https://x.com/{handle}/status/{tid}",
            'kind': 'tweet',
            'has_media': False,
            'social': social,
            'source': 'x_list_scroll',
        })
    p = os.path.join(HERE, 'x_posts.json')
    json.dump(out, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print(f"wrote {p} — {len(out)} posts")

if __name__ == '__main__':
    main()
