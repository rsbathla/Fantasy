"""Marginal title/advancement/W17 contribution per candidate, vs the field.
Built on survival_chain.chain() (the validated model) with common random numbers:
baseline and each candidate share the same sim, so the delta is a clean apples-to-apples
diff. Field is held fixed; only the user's roster changes."""
import copy, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import survival_chain as sc

def win_deltas(rosters, me, cands, ns=1500):
    sc.NS=ns
    base=sc.chain(copy.deepcopy(rosters), me); b=base[base.team==me].iloc[0]
    bt,ba,bw=float(b.title_share),float(b.p_adv),float(b.win_W17)
    out={}
    for c in cands:
        r2=copy.deepcopy(rosters); r2[me]=list(r2[me])+[c]
        d=sc.chain(r2, me); rr=d[d.team==me].iloc[0]
        out[c]={"dtitle":round((float(rr.title_share)-bt)*100,2),
                "dadv":round((float(rr.p_adv)-ba)*100,1),
                "dw17":round((float(rr.win_W17)-bw)*100,1)}
    return {"title":round(bt*100,2),"adv":round(ba*100,1),"w17":round(bw*100,1)}, out
