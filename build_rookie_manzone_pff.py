#!/usr/bin/env python3
"""Rookie man/zone tag from PFF 'Receiving vs Scheme' (NCAA 2025 FBS).

Blends PFF man/zone YPRR + man/zone route grade. Produces TWO percentile lenses:
  *_pctl_fbs  -- vs all qualifying FBS WR/TE (absolute talent context)
  *_pctl      -- vs the 2026 DRAFT-ELIGIBLE class only (discriminates among the rookies)
The tag is computed from the within-class lens so it's useful for draft decisions; the FBS lens
is kept as context. Folds onto every 2026 draft-eligible WR/TE in the rookie profile.
"""
import core, csv, json, collections, os

SRC = core.P(os.path.join('sis_value', 'pff_receiving_scheme_2025.csv'))
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
def tag(m,z):
    if m is None or z is None: return 'NA'
    if m>=60 and z>=60: return 'ALL-AROUND'
    if m>=60: return 'MAN-CAPABLE'
    if z>=55 and m<45: return 'ZONE-RELIANT'
    if m<40 and z<40: return 'LIMITED'
    return 'AVERAGE'

def main():
    rows=list(csv.DictReader(open(SRC, encoding='utf-8-sig')))
    recs=[]
    for r in rows:
        if r.get('position') not in ('WR','TE'): continue
        mr=num(r.get('man_routes')) or 0; zr=num(r.get('zone_routes')) or 0
        if mr+zr < 100: continue
        recs.append({'k':core.fn(r['player']),'player':r['player'],'pos':r['position'],'team':r['team_name'],
                     'man_yprr':num(r.get('man_yprr')),'zone_yprr':num(r.get('zone_yprr')),
                     'man_grade':num(r.get('man_grades_pass_route')),'zone_grade':num(r.get('zone_grades_pass_route'))})
    # FBS-wide percentiles (blend yprr + route grade), within position
    for pos in ('WR','TE'):
        idx=[i for i,r in enumerate(recs) if r['pos']==pos]
        for side in ('man','zone'):
            yp=pctl([recs[i][side+'_yprr'] for i in idx]); gp=pctl([recs[i][side+'_grade'] for i in idx])
            for j,i in enumerate(idx):
                comps=[x for x in (yp[j],gp[j]) if x is not None]
                recs[i][side+'_pctl_fbs']=round(sum(comps)/len(comps),1) if comps else None
    by={r['k']:r for r in recs}
    prof=json.load(open(core.P('boom/rookie_college_profile.json'), encoding='utf-8'))
    # gather the draft-eligible WR/TE cohort that PFF covers
    cohort=[k for k,v in prof['players'].items() if v['pos'] in ('WR','TE') and v.get('draft_eligible_2026') and k in by]
    # within-class percentiles (blend yprr+grade), within position, among the cohort only
    classp={}
    for pos in ('WR','TE'):
        ck=[k for k in cohort if by[k]['pos']==pos]
        for side in ('man','zone'):
            yp=pctl([by[k][side+'_yprr'] for k in ck]); gp=pctl([by[k][side+'_grade'] for k in ck])
            for j,k in enumerate(ck):
                comps=[x for x in (yp[j],gp[j]) if x is not None]
                classp.setdefault(k,{})[side+'_pctl']=round(sum(comps)/len(comps),1) if comps else None
    applied=[]
    for k in cohort:
        t=by[k]; cp=classp.get(k,{})
        m,z=cp.get('man_pctl'),cp.get('zone_pctl')
        v=prof['players'][k]
        v['manzone_tag']=tag(m,z)                       # tag from WITHIN-CLASS lens
        v['man_pctl']=m; v['zone_pctl']=z               # within-class
        v['man_pctl_fbs']=t['man_pctl_fbs']; v['zone_pctl_fbs']=t['zone_pctl_fbs']  # FBS context
        v['man_yprr']=t['man_yprr']; v['zone_yprr']=t['zone_yprr']
        applied.append((v['name'],v['pos'],m,z,t['man_pctl_fbs'],t['zone_pctl_fbs'],v['manzone_tag']))
    core.safe_json_dump(prof, core.P('boom/rookie_college_profile.json'))
    print(f"draft-eligible WR/TE tagged (within-class lens): {len(applied)}")
    print("within-class tag distribution:", dict(collections.Counter(a[6] for a in applied)))
    print(f"\n{'rookie':24}{'pos':4}{'man(cls/fbs)':>14}{'zone(cls/fbs)':>15}  tag")
    for nm,pos,m,z,mf,zf,tg in sorted(applied,key=lambda a:-((a[2] or 0)-(a[3] or 0))):
        print(f"  {nm:22}{pos:4}{str(m)+'/'+str(mf):>14}{str(z)+'/'+str(zf):>15}  {tg}")
    return applied

if __name__=='__main__':
    main()
