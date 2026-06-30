#!/usr/bin/env python3
"""Per-defender PFF grades (CB coverage) -> the quality layer that DRIVES funnels.
Lets us project 2026 funnels through roster changes: each team's WR-fortress/funnel is the
aggregate coverage grade of its corners; reassign a CB (Sauce -> IND already shown) and the
team's expected pass funnel re-derives. Seeded with PFF 2025 CB grades (team col = current
roster). COLLEGE/draft-year fields also tag the incoming rookies. PFF team aliases -> our codes."""
import json, os, statistics as st
from collections import defaultdict
B=os.path.join(os.path.dirname(os.path.abspath(__file__)),'boom')
AL={'BLT':'BAL','CLV':'CLE','HST':'HOU','ARZ':'ARI','LA':'LAR','GAVA':'FA'}
def tm(t): return AL.get(t,t)
# name, team, COV grade, DEF grade, age, college, draft_yr  (PFF 2025 CB grades, page 1 = top-50 by overall)
CB=[("Devon Witherspoon","SEA",83.6,90.1,25.5,"Illinois",2023),("James Pierre","MIN",88.9,86.2,29.7,"FAU",2020),
("Mike Jackson","CAR",85.8,83.5,29.4,"Miami FL",2019),("Ja'Quan McMillian","DEN",78.9,80.8,24.0,"E Carolina",2022),
("Jamel Dean","PIT",75.9,80.6,29.6,"Auburn",2019),("Quinyon Mitchell","PHI",80.2,80.3,24.9,"Toledo",2024),
("Kamari Lassiter","HOU",77.0,79.8,23.4,"Georgia",2024),("Cooper DeJean","PHI",79.7,78.0,23.3,"Iowa",2024),
("Charvarius Ward","IND",77.4,77.1,30.1,"Middle TN",2018),("Sauce Gardner","IND",75.6,76.9,24.8,"Cincinnati",2022),
("Chidobe Awuzie","BAL",77.2,76.4,31.0,"Colorado",2017),("Benjamin St-Juste","GB",77.8,76.3,28.7,"Minnesota",2021),
("Trent McDuffie","LAR",74.7,75.6,25.7,"Washington",2022),("Eric Stokes","LV",75.2,75.0,27.3,"Georgia",2021),
("Christian Gonzalez","NE",76.9,75.0,23.9,"Oregon",2023),("Jarrian Jones","JAX",74.5,74.7,25.1,"Florida St",2024),
("Nohl Williams","KC",75.6,74.5,22.0,"Cal",2025),("Jaylen Watson","LAR",68.4,74.1,27.7,"Wash State",2022),
("Carlton Davis III","NE",71.8,74.0,29.4,"Auburn",2018),("Isaiah Rodgers","MIN",74.1,73.8,28.4,"UMass",2020),
("Marcus Jones","NE",74.2,73.4,27.6,"Houston",2022),("Pat Surtain II","DEN",73.3,73.3,26.1,"Alabama",2021),
("DJ Turner II","CIN",78.1,73.3,25.6,"Michigan",2023),("Rasul Douglas","MIA",72.6,72.7,30.8,"W Virginia",2017),
("Roger McCreary","DET",72.0,72.1,26.3,"Auburn",2022),("Montaric Brown","JAX",74.0,72.0,26.8,"Arkansas",2022),
("Donte Jackson","LAC",73.4,70.8,30.6,"LSU",2018),("Joey Porter Jr.","PIT",76.6,70.1,25.9,"Penn State",2023),
("Kool-Aid McKinstry","NO",71.4,69.5,23.7,"Alabama",2024),("Tyson Campbell","CLE",65.7,69.1,26.2,"Georgia",2021),
("Jacob Parrish","TB",65.7,68.5,22.3,"Kansas St",2025),("Marcus Harris","TEN",67.4,68.4,22.0,"Cal",2025),
("Tarheeb Still","LAC",68.6,68.1,24.0,"Maryland",2024),("Jourdan Lewis","JAX",69.0,67.2,30.8,"Michigan",2017),
("Brandon Stephens","NYJ",63.0,67.1,28.4,"SMU",2021),("Christian Benford","BUF",53.9,66.8,25.7,"Villanova",2022),
("Keisean Nixon","GB",68.7,66.7,29.0,"S Carolina",2019),("Kenny Moore II","IND",62.1,66.7,32.4,"Valdosta",2017),
("Tyrique Stevenson","CHI",62.3,66.2,26.0,"Miami FL",2023),("Nahshon Wright","NYJ",64.8,65.9,27.7,"Oregon St",2021),
("Cor'Dale Flott","TEN",68.1,65.6,24.8,"LSU",2022),("Derek Stingley Jr.","HOU",73.5,65.6,25.0,"LSU",2022),
("Cobie Durant","DAL",65.1,65.6,28.3,"SCar State",2022),("DaRon Bland","DAL",64.5,65.3,26.9,"Fresno St",2022),
("D.J. Reed","DET",61.3,65.2,29.6,"Kansas St",2018),("Dax Hill","CIN",67.7,64.9,25.7,"Michigan",2022),
("Darious Williams","LAR",61.4,64.7,33.2,"UAB",2018),("Maxwell Hairston","BUF",68.0,64.3,22.0,"Kentucky",2025),
("Riley Moss","DEN",61.2,64.2,26.3,"Iowa",2023),("Tre'Davious White","BUF",68.2,64.2,31.4,"LSU",2017)]
defenders={}; byteam=defaultdict(list)
for nm,t,cov,dfn,age,col,dy in CB:
    t=tm(t); defenders[nm]={'team':t,'pos':'CB','cov_grade':cov,'def_grade':dfn,'age':age,'college':col,'draft_yr':dy,
                            'tier':'shutdown' if cov>=78 else ('above-avg' if cov>=70 else ('average' if cov>=63 else 'beatable')),
                            'rookie_2025': dy==2025}
    byteam[t].append((nm,cov))
# team CB-coverage profile (drives the expected pass/WR funnel)
team_cov={}
for t,cbs in byteam.items():
    cbs.sort(key=lambda x:-x[1]); covs=[c for _,c in cbs]
    team_cov[t]={'cb1':cbs[0][0],'cb1_cov':cbs[0][1],'cb_room_avg':round(st.mean(covs),1),'n_graded':len(cbs),
                 'cb1_tier':defenders[cbs[0][0]]['tier'],
                 'expected_wr1_funnel':'fortress' if cbs[0][1]>=78 else ('tight' if cbs[0][1]>=70 else 'exploitable')}
out={'defenders':defenders,'team_cb_profile':team_cov,
     'note':'PFF 2025 CB coverage grades; team col = current roster (move-aware). cb1_cov drives WR1 funnel; on a CB move, reassign team + re-derive expected_wr1_funnel. Pages 2-3 (CB depth), S/EDGE, and college (PFF+SIS) = completion.'}
json.dump(out,open(f'{B}/defender_grades.json','w'),indent=1)
print(f"defender grades: {len(defenders)} CBs across {len(byteam)} teams | 2025 rookies tagged: {sum(1 for d in defenders.values() if d['rookie_2025'])}\n")
print("Team CB1 (drives WR1 funnel):")
for t,p in sorted(team_cov.items(), key=lambda x:-x[1]['cb1_cov'])[:8]:
    print(f"  {t}: {p['cb1']} cov={p['cb1_cov']} ({p['cb1_tier']}) -> WR1 {p['expected_wr1_funnel']}")
print("  ...")
for t,p in sorted(team_cov.items(), key=lambda x:x[1]['cb1_cov'])[:5]:
    print(f"  {t}: {p['cb1']} cov={p['cb1_cov']} ({p['cb1_tier']}) -> WR1 {p['expected_wr1_funnel']}")
