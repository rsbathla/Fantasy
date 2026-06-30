#!/usr/bin/env python3
"""Man/zone aptitude tagger for pass-catchers.

Parses a FantasyPros 'Man vs Zone' receiving export (block layout: overall | vs MAN | vs ZONE |
... by route count, man = the smaller-route block since the NFL is zone-dominant). Computes
within-position percentiles for man-YPRR and zone-YPRR and assigns a tag:
  MAN-CAPABLE  (man_pctl>=60)       -- can win vs man; the rarer, higher-ceiling trait
  ZONE-RELIANT (zone_pctl>=55 & man_pctl<45) -- eats zone, struggles vs man (typical rookie)
  ALL-AROUND   (both>=60)           -- wins everywhere
  LIMITED      (both<40)            -- wins neither
  AVERAGE      otherwise
Reusable for college data too — feed the same script a college man/zone export and it tags the
2026 class identically. NOTE: the file here is NFL 2025, so it tags vets + the 2025 rookie class
(2nd-years now), NOT the 2026 college class (which needs a college man/zone pull).
"""
import core, csv, collections

def num(x):
    try: return float(x)
    except (TypeError, ValueError): return None

def pctl(vals):
    pres=[v for v in vals if v is not None]; out=[None]*len(vals); n=len(pres)
    if not n: return out
    for i,v in enumerate(vals):
        if v is None: continue
        less=sum(1 for x in pres if x<v); eq=sum(1 for x in pres if x==v); out[i]=round((less+0.5*eq)/n*100)
    return out

def main():
    rows=list(csv.reader(open(core.find_data('receivingManVsZone_2025.csv'),encoding='utf-8-sig')))[1:]
    P=[]
    for r in rows:
        if len(r)<17 or r[3] not in ('WR','TE'): continue
        ov_rte=num(r[6])
        if not ov_rte or ov_rte<100: continue                  # need a real route sample
        P.append({'name':r[1].strip(),'pos':r[3],
                  'man_yprr':num(r[12]),'man_tprr':num(r[11]),'man_rte':num(r[10]),
                  'zone_yprr':num(r[16]),'zone_tprr':num(r[15]),'zone_rte':num(r[14])})
    for pos in ('WR','TE'):
        idx=[i for i,p in enumerate(P) if p['pos']==pos]
        for key,src in [('man_pctl','man_yprr'),('zone_pctl','zone_yprr')]:
            ps=pctl([P[i][src] for i in idx])
            for i,v in zip(idx,ps): P[i][key]=v
    def tag(p):
        m,z=p.get('man_pctl'),p.get('zone_pctl')
        if m is None or z is None: return 'NA'
        if m>=60 and z>=60: return 'ALL-AROUND'
        if m>=60: return 'MAN-CAPABLE'
        if z>=55 and m<45: return 'ZONE-RELIANT'
        if m<40 and z<40: return 'LIMITED'
        return 'AVERAGE'
    out={}
    for p in P:
        p['manzone_tag']=tag(p)
        out[core.fn(p['name'])]=p
    core.safe_json_dump({'note':'NFL 2025 man/zone aptitude tags (WR/TE, >=100 routes). man=smaller-route block. '
        'For the 2026 college class, feed this same tagger a college man/zone export.',
        'n':len(out),'tags':out}, core.P('boom/manzone_tags.json'))
    print(f"manzone_tags.json: {len(out)} WR/TE tagged")
    print("tag distribution:", dict(collections.Counter(p['manzone_tag'] for p in P)))
    return out

if __name__=='__main__':
    out=main()
    # show the 2025 ROOKIE class (g24==0,g25>0) tags
    import json
    b=json.load(open(core.P('boom/base2yr.json'),encoding='utf-8'))
    rk={k for k,v in b.items() if (not v.get('g24')) and (v.get('g25') or 0)>0}
    print("\n2025 ROOKIE WR/TE man/zone tags (their rookie-year NFL coverage profile):")
    rks=sorted((out[k] for k in rk if k in out), key=lambda p:-(p.get('man_pctl') or 0))
    for p in rks:
        print(f"  {p['name']:22} {p['pos']:3} man_pctl={str(p.get('man_pctl')):>3} zone_pctl={str(p.get('zone_pctl')):>3}  manYPRR={p.get('man_yprr')} zoneYPRR={p.get('zone_yprr')}  -> {p['manzone_tag']}")
