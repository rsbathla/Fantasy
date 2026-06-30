import time, copy, sys
sys.path.insert(0,'.')
import survival_chain as sc
sc.NS=1500
ROSTERS={
 "rockinrm802":["Jahmyr Gibbs","De'Von Achane","Josh Allen"],
 "NYThunderZone":["Bijan Robinson","George Pickens","Breece Hall"],
 "jrff":["Puka Nacua","Trey McBride","Chris Olave"],
 "bweb9217":["Ja'Marr Chase","Derrick Henry","Jeremiyah Love"],
 "SUNLINER55":["Christian McCaffrey","Nico Collins","Kyren Williams"],
 "onyxx301":["Jaxon Smith-Njigba","Drake London"],
 "cashceddy77":["Ashton Jeanty","Brock Bowers"],
 "rsbathla":["Amon-Ra St. Brown","A.J. Brown"],
 "pocketduckies0":["Jonathan Taylor","Chase Brown"],
 "AN_IDIOT_SAVANT":["CeeDee Lamb","Omarion Hampton"],
 "Redman352":["Kenneth Walker III","Saquon Barkley"],
 "Barker118":["Justin Jefferson","James Cook III"],
}
ME="rsbathla"
t0=time.time(); base=sc.chain(copy.deepcopy(ROSTERS),ME); bt=time.time()-t0
row=base[base.team==ME].iloc[0]
print(f"one chain() @NS={sc.NS}: {bt:.2f}s | baseline me: adv={row.p_adv*100:.1f}% W17={row.win_W17*100:.1f}% title%={row.title_share*100:.2f}")
cands=["Rashee Rice","Malik Nabers","Emeka Egbuka","Javonte Williams","Cam Skattebo","Drake Maye","Colston Loveland"]
print("cand                 Δtitle%  Δadv%  ΔW17%")
t1=time.time()
for c in cands:
    r2=copy.deepcopy(ROSTERS); r2[ME]=r2[ME]+[c]
    d=sc.chain(r2,ME); rr=d[d.team==ME].iloc[0]
    print(f"{c:20} {(rr.title_share-row.title_share)*100:+6.2f}  {(rr.p_adv-row.p_adv)*100:+5.1f}  {(rr.win_W17-row.win_W17)*100:+5.1f}")
print(f"{len(cands)} cands in {time.time()-t1:.1f}s (~{(time.time()-t1)/len(cands):.2f}s/cand)")
