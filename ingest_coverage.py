#!/usr/bin/env python3
"""Per-player NFL man-vs-zone production split -> boom/coverage_split.json.
Reads FantasyPoints CoverageType receiving exports (NFL-master/FP/<year>/Receiving/CoverageType),
RTE-weights YPRR within MAN (Cover 0/1/Man Cover 2) vs ZONE (Cover 2/3/4/6) across all available years.
A man/zone YPRR edge is a real, opponent-controllable ceiling lever (man-coverage skill is population-stable)."""
import csv, os, json, glob, re
HERE=os.path.dirname(os.path.abspath(__file__))
def fn(n):
    n=str(n).strip().lower(); n=re.sub(r'\s+(jr|sr|ii|iii|iv|v)\.?$','',n); return n.replace('.','').replace("'","").replace('-',' ').strip()
def num(x):
    try: return float(str(x).replace('%','').replace(',','').strip())
    except: return None
# locate NFL-master/FP
roots=[]
try:
    import core
    try: roots.append(os.path.dirname(core.find_data('NFL-master','FP','2025')))
    except Exception: pass
except Exception: pass
roots += [os.path.join(os.path.dirname(HERE),'NFL-master','FP'), '/sessions/gracious-gallant-edison/mnt/Downloads/NFL-master/FP', os.path.expanduser('~/Downloads/NFL-master/FP')]
base=next((r for r in roots if r and os.path.isdir(r)), None)
MAN=['Cover 0','Cover 1','Man Cover 2']; ZONE=['Cover 2','Cover 3','Cover 4','Cover 6']
agg={}
if base:
    for y in sorted(glob.glob(os.path.join(base,'*'))):
        cd=os.path.join(y,'Receiving','CoverageType')
        if not os.path.isdir(cd): continue
        for ct in MAN+ZONE:
            f=os.path.join(cd,ct+'.csv')
            if not os.path.exists(f): continue
            for r in csv.DictReader(open(f,encoding='utf-8-sig')):
                k=fn(r.get('Name','')); rte=num(r.get('RTE')); yds=num(r.get('YDS'))
                if not k or not rte: continue
                a=agg.setdefault(k,{'name':r['Name'],'mr':0.0,'my':0.0,'zr':0.0,'zy':0.0})
                if ct in MAN: a['mr']+=rte; a['my']+=(yds or 0)
                else: a['zr']+=rte; a['zy']+=(yds or 0)
out={}
for k,a in agg.items():
    if a['mr']>=60 and a['zr']>=60:   # min sample each side
        my=a['my']/a['mr']; zy=a['zy']/a['zr']
        out[k]={'name':a['name'],'man_yprr':round(my,2),'zone_yprr':round(zy,2),'delta':round(my-zy,2),'mr':round(a['mr']),'zr':round(a['zr'])}

# ---- QB man/zone (Passing/CoverageType): everyone is better vs zone, so the lever is RELATIVE man efficiency ----
qa={}
if base:
    for y in sorted(glob.glob(os.path.join(base,'*'))):
        cd=os.path.join(y,'Passing','CoverageType')
        if not os.path.isdir(cd): continue
        for ct in MAN+ZONE:
            f=os.path.join(cd,ct+'.csv')
            if not os.path.exists(f): continue
            for r in csv.DictReader(open(f,encoding='utf-8-sig')):
                k=fn(r.get('Name','')); att=num(r.get('ATT')); ypa=num(r.get('Y/A')) or num(r.get('YPA'))
                if not k or not att or ypa is None: continue
                a=qa.setdefault(k,{'name':r['Name'],'ma':0.0,'my':0.0,'za':0.0,'zy':0.0})
                if ct in MAN: a['ma']+=att; a['my']+=ypa*att
                else: a['za']+=att; a['zy']+=ypa*att
qbs=[(k,a['my']/a['ma'],a['zy']/a['za']) for k,a in qa.items() if a['ma']>=50 and a['za']>=50]
mans=sorted(m for _,m,_ in qbs)
def pctl(v): 
    return round(100*sum(1 for x in mans if x<=v)/len(mans)) if mans else None
for k,m,z in qbs:
    out[k]={'name':qa[k]['name'],'is_qb':True,'man_ypa':round(m,2),'zone_ypa':round(z,2),'man_pctl':pctl(m)}

os.makedirs(os.path.join(HERE,'boom'),exist_ok=True)
json.dump(out,open(os.path.join(HERE,'boom','coverage_split.json'),'w'),ensure_ascii=False,indent=1)
print(f"ingest_coverage: {len(out)} players (base={base})")
