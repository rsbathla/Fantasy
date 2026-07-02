#!/usr/bin/env python3
"""Individual DEFENDER registry + movement tracking — the player layer under the team funnels.
Shadow corners are the most movement-sensitive defenders: when one moves, his old team's WR1
shifts from fortress->funnel and his new team's tightens. We register each key defender, his
team, role, and a coverage-result proxy, and LINK him to the funnel he drives so that a roster
move can be re-projected. Seeded from FTN Shadow Coverage Matrix (2025); enrich with PFF per-CB
coverage grades for quality. team alias -> our codes."""
import json, os
from collections import defaultdict
B=os.path.join(os.path.dirname(os.path.abspath(__file__)),'boom')
ALIAS={'CLV':'CLE','HST':'HOU','BLT':'BAL','ARZ':'ARI','LA':'LAR'}
def tm(t): return ALIAS.get(t,t)
# (wk, Corner, Def, Receiver, Off, %Rts, Tar, Rec, Yds, TD) — shadow events observed
EV=[("A.J. Terrell","ATL","Mike Evans","TB",53.3,4,2,20,0),
("Pat Surtain II","DEN","Calvin Ridley","TEN",87.5,2,0,0,0),
("L'Jarius Sneed","TEN","Courtland Sutton","DEN",30.0,1,0,0,0),
("Sauce Gardner","NYJ","DK Metcalf","PIT",90.9,4,1,11,0),
("Pat Surtain II","DEN","Michael Pittman","IND",56.7,3,3,28,0),
("Greg Newsome II","CLV","Zay Flowers","BLT",46.4,6,5,59,0),
("Derek Stingley Jr.","HST","Mike Evans","TB",77.5,9,3,36,0),
("Kamari Lassiter","HST","Emeka Egbuka","TB",67.4,1,1,15,1),
("Quinyon Mitchell","PHI","Davante Adams","LA",79.4,5,2,12,0),
("D.J. Reed","DET","Zay Flowers","BLT",61.8,2,1,7,0),
("Pat Surtain II","DEN","Quentin Johnston","LAC",87.8,4,2,39,0),
("Charvarius Ward","IND","Calvin Ridley","TEN",55.6,5,1,27,0),
("Christian Benford","BUF","Tyreek Hill","MIA",65.6,5,2,10,1),
("Tre'Davious White","BUF","Jaylen Waddle","MIA",56.7,4,4,26,1),
("Sauce Gardner","NYJ","Mike Evans","TB",58.3,4,2,22,0),
("Kamari Lassiter","HST","Brian Thomas Jr.","JAX",61.8,1,1,46,0),
("Quinyon Mitchell","PHI","Emeka Egbuka","TB",63.2,6,2,6,0),
("D.J. Reed","DET","Jerry Jeudy","CLV",79.4,7,3,48,0),
("DJ Turner II","CIN","Courtland Sutton","DEN",55.3,1,0,0,0),
("Pat Surtain II","DEN","Ja'Marr Chase","CIN",66.7,1,1,8,0),
("L'Jarius Sneed","TEN","Nico Collins","HST",81.5,3,2,59,0),
("Charvarius Ward","IND","Davante Adams","LA",67.5,2,1,10,1),
("Xavien Howard","IND","Puka Nacua","LA",54.1,5,3,47,1),
("Quinyon Mitchell","PHI","Courtland Sutton","DEN",65.9,7,5,77,0)]
agg=defaultdict(lambda:{'team':None,'shadows':0,'tar':0,'rec':0,'yds':0,'td':0,'rts':[],'vs':[]})
for cb,dfn,wr,off,rts,tar,rec,yds,td in EV:
    a=agg[cb]; a['team']=tm(dfn); a['shadows']+=1; a['tar']+=tar; a['rec']+=rec; a['yds']+=yds; a['td']+=td
    a['rts'].append(rts); a['vs'].append(wr)
prof=json.load(open(f'{B}/defensive_profile.json'))
defenders={}
for cb,a in agg.items():
    ypt=round(a['yds']/a['tar'],1) if a['tar'] else None
    grade='shutdown' if (ypt is not None and ypt<=6 and a['td']==0) else ('tight' if (ypt is not None and ypt<=9) else 'beatable')
    defenders[cb]={'team':a['team'],'role':'shadow CB (travels)','shadow_games_sample':a['shadows'],
                   'avg_route_cover_pct':round(sum(a['rts'])/len(a['rts']),1),'yds_per_tgt_allowed':ypt,
                   'tds_allowed':a['td'],'coverage_grade':grade,'shadowed':sorted(set(a['vs'])),
                   'funnel_link':f"travels -> his team's WR1 stays a fortress; if he leaves {a['team']}, that WR1 opens up"}
out={'defenders':defenders,'note':'shadow CBs are the movement-sensitive nodes; per-CB coverage GRADE enrichment = PFF; full shadow set = FTN CSV (729 rows). On any move: reassign team, re-derive that team funnel.'}
json.dump(out,open(f'{B}/defender_profiles.json','w'),indent=1)
print(f"defender registry: {len(defenders)} shadow corners (movement-sensitive nodes)\n")
for cb,d in sorted(defenders.items(),key=lambda x:-x[1]['shadow_games_sample']):
    print(f"  {cb:20} {d['team']}  cover~{d['avg_route_cover_pct']}%  {d['yds_per_tgt_allowed']} yds/tgt  -> {d['coverage_grade']}")
