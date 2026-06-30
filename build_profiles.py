#!/usr/bin/env python3
"""
Player Situational Profiles
Synthesizes FantasyPoints + PFF + FTN situational splits into per-player profiles:
"which situations does each player succeed or do poorly in?"

Primary season: 2025 (most recent completed). 2024 available for trend.
Method: for each situational efficiency metric, rank players WITHIN their position
among those clearing a volume threshold; convert to percentile (0-100).
A player "succeeds" in a situation where they sit high in the percentile, and
"struggles" where they sit low. Volume-gated to avoid small-sample noise.
"""
import csv, os, json, re, math
from collections import defaultdict

ROOT = '/root/bestball/bestball'
NFL = os.path.join(ROOT, 'NFL-master')
SEASON = '2025'

# ---------------- name normalization & player base ----------------
SUFFIX = re.compile(r'\b(jr|sr|ii|iii|iv|v)\b\.?', re.I)
def norm(n):
    if not n: return ''
    n = n.lower().strip()
    n = n.replace('.', '').replace(',', '').replace("'", '').replace('-', ' ')
    n = SUFFIX.sub('', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n

def to_float(x):
    try:
        if x is None or x == '' : return None
        return float(x)
    except: return None

# player base from features.csv (fantasy-relevant universe)
players = {}      # norm_name -> {name,pos,team,pid}
by_pid = {}
with open(os.path.join(ROOT, 'features.csv')) as f:
    for row in csv.DictReader(f):
        nm = row.get('name','');
        if not nm: continue
        rec = {'name':nm, 'pos':row.get('pos',''), 'team':row.get('team',''), 'pid':row.get('pid','')}
        players[norm(nm)] = rec
        if rec['pid']: by_pid[rec['pid']] = rec
print('player universe:', len(players))

# profile store: norm_name -> { 'situations': {situation_key: {'val':v,'pct':p,'metric':label,'n':vol}} }
prof = defaultdict(lambda: {'situations': {}})

# ---------------- helpers ----------------
def load_csv(path):
    if not os.path.exists(path): return []
    with open(path) as f:
        return list(csv.DictReader(f))

def pct_rank(values_by_key, pos_of, lower_is_better=False):
    """values_by_key: {norm_name: value}. Rank within position group -> percentile 0-100."""
    groups = defaultdict(list)
    for k,v in values_by_key.items():
        p = pos_of.get(k)
        if p is None or v is None: continue
        groups[p].append((k,v))
    out = {}
    for p, lst in groups.items():
        lst_sorted = sorted(lst, key=lambda kv: kv[1])
        m = len(lst_sorted)
        if m < 4:
            continue
        for i,(k,v) in enumerate(lst_sorted):
            # percentile of being >= others
            pctile = 100.0 * i/(m-1)
            if lower_is_better: pctile = 100.0 - pctile
            out[k] = round(pctile,1)
    return out

def register(situation_key, label, src_rows, name_field, metric_field, vol_field, vol_min,
             lower_is_better=False, pos_filter=None, season_tag=''):
    """Compute a situational metric across players and store percentile-in-position."""
    vals = {}; vols = {}
    for r in src_rows:
        nm = norm(r.get(name_field,''))
        if nm not in players: continue
        if pos_filter and players[nm]['pos'] not in pos_filter: continue
        v = to_float(r.get(metric_field))
        vol = to_float(r.get(vol_field)) if vol_field else 1
        if v is None: continue
        if vol_field and (vol is None or vol < vol_min): continue
        vals[nm] = v; vols[nm] = vol if vol is not None else 0
    pos_of = {nm: players[nm]['pos'] for nm in vals}
    pcts = pct_rank(vals, pos_of, lower_is_better)
    for nm,p in pcts.items():
        prof[nm]['situations'][situation_key] = {
            'val': round(vals[nm],3), 'pct': p, 'metric': label, 'n': round(vols.get(nm,0),0)
        }
    return len(pcts)

print('engine ready')

# ---------------- FP multi-file efficiency loaders ----------------
def fp_eff(folder, files, num_field, den_field, name_field='Name'):
    """Sum num & den across files for each player -> ratio. Returns {norm:(ratio,den_sum)}."""
    agg = defaultdict(lambda:[0.0,0.0])
    for fn in files:
        for r in load_csv(os.path.join(folder, fn)):
            nm = norm(r.get(name_field,''))
            if nm not in players: continue
            num = to_float(r.get(num_field)); den = to_float(r.get(den_field))
            if num is None or den is None: continue
            agg[nm][0]+=num; agg[nm][1]+=den
    return {nm:(v[0]/v[1], v[1]) for nm,v in agg.items() if v[1]>0}

def register_ratio(situation_key, label, ratio_map, vol_min, lower_is_better=False, pos_filter=None):
    vals={nm:r for nm,(r,d) in ratio_map.items() if d>=vol_min and (not pos_filter or players[nm]['pos'] in pos_filter)}
    vols={nm:d for nm,(r,d) in ratio_map.items()}
    pos_of={nm:players[nm]['pos'] for nm in vals}
    pcts=pct_rank(vals,pos_of,lower_is_better)
    for nm,p in pcts.items():
        prof[nm]['situations'][situation_key]={'val':round(vals[nm],3),'pct':p,'metric':label,'n':round(vols.get(nm,0),0)}
    return len(pcts)

REC='WR,TE'.split(','); RB=['RB']; QB=['QB']
Y=str(SEASON)

# ================= WR/TE RECEIVING =================
scheme=load_csv(f'{NFL}/PFF/{Y}/receiving_scheme.csv')
register('rec_vs_man','vs Man coverage (YPRR)',scheme,'player','man_yprr','man_routes',25,pos_filter=REC)
register('rec_vs_zone','vs Zone coverage (YPRR)',scheme,'player','zone_yprr','zone_routes',40,pos_filter=REC)
register('rec_man_qbr','vs Man (QB rating when targeted)',scheme,'player','man_targeted_qb_rating','man_targets',15,pos_filter=REC)

base=load_csv(f'{NFL}/PFF/{Y}/receiving.csv')
register('rec_yprr','Overall YPRR',base,'player','yprr','routes',100,pos_filter=REC)
register('rec_contested','Contested catch rate',base,'player','contested_catch_rate','contested_targets',8,pos_filter=REC)
register('rec_yac','Yards after catch / reception',base,'player','yards_after_catch_per_reception','receptions',20,pos_filter=REC)
register('rec_adot','Avg depth of target (aDOT)',base,'player','avg_depth_of_target','targets',30,pos_filter=REC)
register('rec_drop','Drop rate (lower=better)',base,'player','drop_rate','targets',30,lower_is_better=True,pos_filter=REC)
register('rec_qbr','QB rating when targeted',base,'player','targeted_qb_rating','targets',30,pos_filter=REC)

ftn=load_csv(f'{NFL}/FTN/{Y}/receiving_player.csv')
# derive efficiency ratios from FTN
def ftn_ratio(rows, num, den):
    out={}
    for r in rows:
        nm=norm(r.get('name','')); 
        if nm not in players: continue
        a=to_float(r.get(num)); b=to_float(r.get(den))
        if a is None or b is None or b==0: continue
        out[nm]=(a/b, b)
    return out
register_ratio('rec_deep','Deep ball (yds/deep target)',ftn_ratio(ftn,'deepYards','deepTargets'),8,pos_filter=REC)
register_ratio('rec_slot','From slot (yds/route)',ftn_ratio(ftn,'slotYards','slotRoutes'),20,pos_filter=REC)
register_ratio('rec_wide','Out wide (yds/route)',ftn_ratio(ftn,'outWideYards','outWideRoutes'),20,pos_filter=REC)
register_ratio('rec_vman_ftn','vs Man (yds/man route, FTN)',ftn_ratio(ftn,'manYards','manCoverage'),25,pos_filter=REC)
register_ratio('rec_vzone_ftn','vs Zone (yds/zone route, FTN)',ftn_ratio(ftn,'zoneYards','zoneCoverage'),40,pos_filter=REC)
register('rec_sep','Separation (step sep at catch pt)',ftn,'name','stepSeparation','manCoverage',25,pos_filter=REC)
register('rec_dvoa','Overall efficiency (DVOA)',ftn,'name','dvoa','catchableTargets',20,pos_filter=REC)
register('rec_success','Success rate',ftn,'name','success','catchableTargets',20,pos_filter=REC)
register_ratio('rec_rz','Red zone TD rate (TD/target)',ftn_ratio(ftn,'redZoneTouchdowns','redZoneTargets'),6,pos_filter=REC)
register('rec_rz_vol','Red zone targets (volume)',ftn,'name','redZoneTargets','catchableTargets',20,pos_filter=REC)

# FP route types -> deep vs short route efficiency (YDS/REC)
deep_routes=['Go-Fly.csv','Post.csv','Corner.csv']; short_routes=['Slant.csv','Flat.csv','Curl.csv','Screen.csv']
register_ratio('rec_deep_routes','Deep routes (yds/route)',fp_eff(f'{NFL}/FP/{Y}/Receiving/RouteType',deep_routes,'YDS','RTE'),15,pos_filter=REC)
register_ratio('rec_short_routes','Short routes (yds/route)',fp_eff(f'{NFL}/FP/{Y}/Receiving/RouteType',short_routes,'YDS','RTE'),20,pos_filter=REC)

print('after WR/TE, players with situations:', sum(1 for k in prof if prof[k]['situations']))

# ================= RB =================
rush=load_csv(f'{NFL}/PFF/{Y}/rushing.csv')
register('rb_elusive','Elusiveness (PFF elusive rating)',rush,'player','elusive_rating','attempts',40,pos_filter=RB)
register('rb_breakaway','Breakaway run rate',rush,'player','breakaway_percent','attempts',40,pos_filter=RB)
register('rb_yco','Yards after contact / attempt',rush,'player','yco_attempt','attempts',40,pos_filter=RB)
register('rb_grade_run','Rushing grade',rush,'player','grades_run','attempts',40,pos_filter=RB)
register('rb_rec_yprr','Receiving YPRR (as RB)',rush,'player','yprr','routes',30,pos_filter=RB)
register('rb_explosive','Explosive run rate',rush,'player','explosive','attempts',40,pos_filter=RB)

rt=f'{NFL}/FP/{Y}/Rushing/RunType'
register_ratio('rb_inside_zone','Inside zone (yds/carry)',fp_eff(rt,['Inside Zone.csv'],'YDS','ATT'),20,pos_filter=RB)
register_ratio('rb_outside_zone','Outside zone (yds/carry)',fp_eff(rt,['Outside Zone.csv'],'YDS','ATT'),15,pos_filter=RB)
register_ratio('rb_gap','Gap/Power scheme (yds/carry)',fp_eff(rt,['Power.csv','Man-Duo.csv','Counter.csv','Trap.csv'],'YDS','ATT'),20,pos_filter=RB)
register_ratio('rb_mtf_rate','Missed tackles forced /carry',fp_eff(rt,['Inside Zone.csv','Outside Zone.csv','Power.csv','Man-Duo.csv','Counter.csv','Draw.csv'],'MTF','ATT'),50,pos_filter=RB)

ftnr=load_csv(f'{NFL}/FTN/{Y}/rushing_player.csv')
register('rb_dvoa','Rushing efficiency (DVOA)',ftnr,'name','dvoa','id',1,pos_filter=RB)
register('rb_success','Rush success rate',ftnr,'name','success','id',1,pos_filter=RB)

# ================= QB =================
pas=load_csv(f'{NFL}/PFF/{Y}/passing.csv')
register('qb_btt','Big-time throw rate',pas,'player','btt_rate','dropbacks',150,pos_filter=QB)
register('qb_twp','Turnover-worthy play rate (lower=better)',pas,'player','twp_rate','dropbacks',150,lower_is_better=True,pos_filter=QB)
register('qb_acc','Accuracy %',pas,'player','accuracy_percent','dropbacks',150,pos_filter=QB)
register('qb_grade','Overall passing grade',pas,'player','grades_pass','dropbacks',150,pos_filter=QB)
register('qb_p2s','Pressure-to-sack rate (lower=better)',pas,'player','pressure_to_sack_rate','dropbacks',150,lower_is_better=True,pos_filter=QB)
register('qb_adot','Avg depth of target',pas,'player','avg_depth_of_target','dropbacks',150,pos_filter=QB)
register('qb_ttt','Time to throw',pas,'player','avg_time_to_throw','dropbacks',150,pos_filter=QB)

press=load_csv(f'{NFL}/PFF/{Y}/passing_pressure.csv')
register('qb_pressure','Under pressure (YPA)',press,'player','pressure_ypa','pressure_passing_snaps',60,pos_filter=QB)
register('qb_clean','Clean pocket (YPA)',press,'player','no_pressure_ypa','no_pressure_passing_snaps',150,pos_filter=QB)
register('qb_blitz','vs Blitz (YPA)',press,'player','blitz_ypa','blitz_attempts',40,pos_filter=QB)
register('qb_pressure_grade','Under pressure (grade)',press,'player','pressure_grades_pass','pressure_passing_snaps',60,pos_filter=QB)

depth=load_csv(f'{NFL}/PFF/{Y}/passing_depth.csv')
register('qb_deep','Deep ball accuracy %',depth,'player','deep_accuracy_percent','deep_attempts',20,pos_filter=QB)
register('qb_deep_grade','Deep ball grade',depth,'player','deep_grades_pass','deep_attempts',20,pos_filter=QB)

concept=load_csv(f'{NFL}/PFF/{Y}/passing_concept.csv')
register('qb_pa','Play-action (YPA)',concept,'player','pa_ypa','dropbacks',100,pos_filter=QB)
register('qb_pa_grade','Play-action grade',concept,'player','pa_grades_pass','dropbacks',100,pos_filter=QB)

ftnp=load_csv(f'{NFL}/FTN/{Y}/passing_player.csv')
register('qb_dvoa','Overall efficiency (DVOA)',ftnp,'name','dvoa','id',1,pos_filter=QB)

# ================= NFL PRO real EPA / NGS (pro.nfl.com) =================
# The headline efficiency layer the user asked for: real Rec EPA/route, separation, CROE, YACOE,
# EPA/dropback, CPOE, Rush EPA/att, RYOE, success — percentile-ranked in position so they fold
# straight into each player's succeed/struggle profile. Only genuine SKILL metrics (no usage/tendency).
_npp=os.path.join(ROOT,'nfl_pro_epa.json')
if os.path.exists(_npp):
    _np=json.load(open(_npp)); _S=_np['seasons'][SEASON]
    _rec=_S['receiving']['rows']; _pas=_S['passing']['rows']; _rus=_S['rushing']['rows']
    for r in _rec:  # per-reception YACOE for a fair rate ranking (yacoe field is a season total)
        _rn=to_float(r.get('rec')); _yc=to_float(r.get('yacoe'))
        r['yacoe_per_rec']=(_yc/_rn) if (_rn and _yc is not None) else None
    # WR/TE receiving
    register('rec_epa_route_pro','Rec EPA / route (NFL Pro)',_rec,'displayName','epaRt','rt',100,pos_filter=REC)
    register('rec_epa_tgt_pro','Rec EPA / target (NFL Pro)',_rec,'displayName','epaTgt','tgt',40,pos_filter=REC)
    register('rec_sep_pro','Avg separation (NFL Pro NGS)',_rec,'displayName','avgSep','tgt',40,pos_filter=REC)
    register('rec_croe_pro','Catch rate over expected (CROE)',_rec,'displayName','croe','tgt',40,pos_filter=REC)
    register('rec_yacoe_pro','YAC over expected / rec (NFL Pro)',_rec,'displayName','yacoe_per_rec','rec',30,pos_filter=REC)
    # RB pass game (from the receiving rows — RBs are charted there)
    register('rb_rec_epa_pro','Receiving EPA / route (NFL Pro, RB)',_rec,'displayName','epaRt','rt',25,pos_filter=RB)
    register('rb_rec_sep_pro','Receiving separation (NFL Pro, RB)',_rec,'displayName','avgSep','tgt',20,pos_filter=RB)
    # QB passing
    register('qb_epa_db_pro','EPA / dropback (NFL Pro)',_pas,'displayName','epaDb','db',150,pos_filter=QB)
    register('qb_cpoe_pro','Completion % over expected (CPOE)',_pas,'displayName','cpoe','db',150,pos_filter=QB)
    # RB rushing
    register('rb_epa_att_pro','Rush EPA / attempt (NFL Pro)',_rus,'displayName','epaAtt','att',50,pos_filter=RB)
    register('rb_ryoe_att_pro','RYOE / attempt (NFL Pro)',_rus,'displayName','ryoeAtt','att',50,pos_filter=RB)
    register('rb_success_pro','Rush success rate (NFL Pro)',_rus,'displayName','success','att',50,pos_filter=RB)
    register('rb_yaco_att_pro','Yards after contact / att (NFL Pro)',_rus,'displayName','yacoAtt','att',50,pos_filter=RB)
    print(f'NFL Pro EPA registered: rec {len(_rec)} · pas {len(_pas)} · rus {len(_rus)}')
else:
    print('NFL Pro EPA file not found — skipping real-EPA situations')

print('total players with situations:', sum(1 for k in prof if prof[k]['situations']))
import collections
cnt=collections.Counter(players[k]['pos'] for k in prof if prof[k]['situations'])
print('by pos:', dict(cnt))

# ================= 2024->2025 TREND (headline efficiency) =================
def headline_map(season):
    out={}
    # WR/TE yprr, RB elusive_rating, QB grades_pass
    for r in load_csv(f'{NFL}/PFF/{season}/receiving.csv'):
        nm=norm(r.get('player','')); v=to_float(r.get('yprr')); vol=to_float(r.get('routes'))
        if nm in players and v is not None and vol and vol>=100: out[nm]=('YPRR',v)
    for r in load_csv(f'{NFL}/PFF/{season}/rushing.csv'):
        nm=norm(r.get('player','')); v=to_float(r.get('elusive_rating')); vol=to_float(r.get('attempts'))
        if nm in players and v is not None and vol and vol>=40 and players[nm]['pos']=='RB': out[nm]=('Elusive',v)
    for r in load_csv(f'{NFL}/PFF/{season}/passing.csv'):
        nm=norm(r.get('player','')); v=to_float(r.get('grades_pass')); vol=to_float(r.get('dropbacks'))
        if nm in players and v is not None and vol and vol>=150: out[nm]=('PassGrade',v)
    return out
h24=headline_map('2024'); h25=headline_map(str(SEASON))
for nm in prof:
    if nm in h25 and nm in h24 and h25[nm][0]==h24[nm][0]:
        d=h25[nm][1]-h24[nm][1]
        prof[nm]['trend']={'metric':h25[nm][0],'y2024':round(h24[nm][1],2),'y2025':round(h25[nm][1],2),'delta':round(d,2)}

# ================= NJ OPPORTUNITY LAYER (FFDataRoma) =================
FFD=f'{ROOT}/ffdataroma_draft_guide_export/ffdataroma/csv'
proj={}
for r in load_csv(f'{FFD}/models-projections.csv'):
    if str(r.get('season'))!='2026' or r.get('modelType')!='projections': continue
    nm=norm(r.get('playerName',''))
    if not nm: continue
    proj[nm]={'fpg':to_float(r.get('projectedFpg')),'tier':(r.get('tier') or '').strip(),
              'pctl':to_float(r.get('percentile')),'breakout':to_float(r.get('breakoutAge'))}
adp={}
for r in load_csv(f'{FFD}/underdog-adp.csv'):
    nm=norm(r.get('name','')); a=to_float(r.get('adp'))
    if nm and a is not None: adp[nm]=a
vac={}
for r in load_csv(f'{FFD}/vacated-targets__players.csv'):
    nm=norm(r.get('name',''))
    if nm: vac[nm]={'dir':(r.get('direction') or '').strip(),'targets':int(to_float(r.get('targets')) or 0),
                    'rushes':int(to_float(r.get('rushes')) or 0),'to':(r.get('currentTeam') or '').strip()}
for nm in prof:
    prof[nm]['proj']=proj.get(nm); prof[nm]['adp']=adp.get(nm); prof[nm]['vac']=vac.get(nm)
print('NJ opportunity layer: proj',len(proj),'| adp',len(adp),'| vacated',len(vac))

# ================= OUTPUTS =================
OUT=os.path.join(ROOT,'profiles'); os.makedirs(OUT,exist_ok=True)

# 1) JSON
full={}
for nm,d in prof.items():
    if not d['situations']: continue
    rec=players[nm]
    full[rec['name']]={'pos':rec['pos'],'team':rec['team'],'situations':d['situations'],'trend':d.get('trend')}
json.dump(full,open(os.path.join(OUT,'player_profiles.json'),'w'),indent=1)

# 2) Percentile matrix CSV
all_sits=[]
for d in prof.values():
    for k in d['situations']:
        if k not in all_sits: all_sits.append(k)
sit_label={k:next((d['situations'][k]['metric'] for d in prof.values() if k in d['situations']),k) for k in all_sits}
with open(os.path.join(OUT,'situational_percentiles.csv'),'w',newline='') as f:
    cols=['name','pos','team','n_situations','trend_metric','trend_2024','trend_2025','trend_delta']+all_sits
    w=csv.writer(f); w.writerow(cols)
    # also a second header row with human labels
    w.writerow(['','','','','','','','']+[sit_label[k] for k in all_sits])
    for nm,d in sorted(prof.items(), key=lambda kv:(players[kv[0]]['pos'],players[kv[0]]['name'])):
        if not d['situations']: continue
        rec=players[nm]; tr=d.get('trend') or {}
        row=[rec['name'],rec['pos'],rec['team'],len(d['situations']),tr.get('metric',''),tr.get('y2024',''),tr.get('y2025',''),tr.get('delta','')]
        for k in all_sits:
            row.append(d['situations'][k]['pct'] if k in d['situations'] else '')
        w.writerow(row)

print('wrote JSON + percentile CSV; situations tracked:', len(all_sits))

# 3) Narrative markdown + summary CSV
def strengths_weaknesses(d, hi=65, lo=35):
    sits=d['situations']
    s=sorted([(k,v) for k,v in sits.items() if v['pct']>=hi], key=lambda kv:-kv[1]['pct'])
    w=sorted([(k,v) for k,v in sits.items() if v['pct']<=lo], key=lambda kv:kv[1]['pct'])
    return s,w
def ordinal(p):
    p=int(round(p))
    if 10<=p%100<=20: suf='th'
    else: suf={1:'st',2:'nd',3:'rd'}.get(p%10,'th')
    return f"{p}{suf}"
def fmt_items(items,n=5):
    return ', '.join(f"{v['metric']} ({ordinal(v['pct'])})" for k,v in items[:n])
def trend_arrow(tr):
    if not tr: return ''
    d=tr['delta']
    a='▲' if d>0.08 else ('▼' if d<-0.08 else '–')
    return f" — {tr['metric']} {tr['y2024']}→{tr['y2025']} {a}"
# headline real NFL Pro EPA line — surfaced explicitly so it never gets crowded out of the top-5 by ties
EPA_KEYS={
 'WR':[('rec_epa_route_pro','EPA/rt'),('rec_epa_tgt_pro','EPA/tgt'),('rec_sep_pro','Sep'),('rec_croe_pro','CROE'),('rec_yacoe_pro','YACOE')],
 'TE':[('rec_epa_route_pro','EPA/rt'),('rec_epa_tgt_pro','EPA/tgt'),('rec_sep_pro','Sep'),('rec_croe_pro','CROE'),('rec_yacoe_pro','YACOE')],
 'RB':[('rb_epa_att_pro','RushEPA/att'),('rb_ryoe_att_pro','RYOE/att'),('rb_success_pro','Succ'),('rb_yaco_att_pro','YACO/att'),('rb_rec_epa_pro','RecEPA/rt')],
 'QB':[('qb_epa_db_pro','EPA/DB'),('qb_cpoe_pro','CPOE')]}
def epa_line(d,pos):
    sits=d['situations']; bits=[]
    for k,lab in EPA_KEYS.get(pos,[]):
        if k in sits:
            v=sits[k]; bits.append(f"{lab} {v['val']:g} ({ordinal(v['pct'])})")
    # EPA/DB is PASSING-only — flag that it understates rushing QBs (Lamar/Daniels/Hurts types)
    suff=' _(passing only — excludes rushing value)_' if pos=='QB' else ''
    return (f"&nbsp;&nbsp;📊 Real EPA (NFL Pro): {' · '.join(bits)}{suff}  ") if bits else ''

OVERALL={'WR':['rec_dvoa','rec_yprr'],'TE':['rec_dvoa','rec_yprr'],'RB':['rb_dvoa','rb_elusive'],'QB':['qb_dvoa','qb_grade']}
POS_ORDER=['QB','RB','WR','TE']; POS_NAME={'QB':'Quarterbacks','RB':'Running Backs','WR':'Wide Receivers','TE':'Tight Ends'}

def sortkey(nm):
    d=prof[nm]; pos=players[nm]['pos']
    for k in OVERALL.get(pos,[]):
        if k in d['situations']: return -d['situations'][k]['pct']
    return -len(d['situations'])

lines=['# Player Situational Profiles — 2025 season',
 '',
 'For each player: the game situations where they **succeed** (high percentile vs positional peers) '
 'and where they **struggle** (low percentile). Built from FantasyPoints, PFF, FTN charting data **and real NFL Pro EPA/NGS** (pro.nfl.com). '
 'The **📊 Real EPA** line surfaces the headline efficiency metrics directly (value + in-position percentile): '
 'Rec EPA/route, separation, CROE, YACOE for pass-catchers; EPA/dropback, CPOE for QBs; Rush EPA/att, RYOE, success, YACO for backs. '
 'Percentiles are within position among players clearing volume thresholds. Trend = year-over-year change in the headline efficiency metric (YPRR / elusiveness / pass grade).',
 '']
def proj_line(d):
    p=d.get('proj'); a=d.get('adp'); bits=[]
    if p and p.get('fpg') is not None:
        t=f" {p['tier']}" if p.get('tier') else ''
        bits.append(f"proj {p['fpg']:.1f} FPG{t}")
    if a is not None: bits.append(f"ADP {a:g}")
    return ('  —  '+' · '.join(bits)) if bits else ''
summary_rows=[]
for pos in POS_ORDER:
    names=[nm for nm in prof if players[nm]['pos']==pos and len(prof[nm]['situations'])>=3]
    names.sort(key=sortkey)
    lines.append(f'\n## {POS_NAME[pos]} ({len(names)})\n')
    for nm in names:
        d=prof[nm]; rec=players[nm]
        s,w=strengths_weaknesses(d)
        lines.append(f"**{rec['name']}** ({rec['team']}){proj_line(d)}{trend_arrow(d.get('trend'))}  ")
        _el=epa_line(d,rec['pos'])
        if _el: lines.append(_el)
        if s: lines.append(f"&nbsp;&nbsp;✓ Excels: {fmt_items(s)}  ")
        if w: lines.append(f"&nbsp;&nbsp;✗ Struggles: {fmt_items(w)}  ")
        if not s and not w: lines.append("&nbsp;&nbsp;~ Middling across tracked situations  ")
        lines.append('')
        pj=d.get('proj') or {}
        summary_rows.append([rec['name'],rec['pos'],rec['team'],
            (pj.get('fpg') if pj.get('fpg') is not None else ''), pj.get('tier',''), (d.get('adp') if d.get('adp') is not None else ''),
            (d.get('trend') or {}).get('delta',''),
            fmt_items(s), fmt_items(w)])
open(os.path.join(OUT,'PLAYER_PROFILES.md'),'w').write('\n'.join(lines))

with open(os.path.join(OUT,'profiles_summary.csv'),'w',newline='') as f:
    w=csv.writer(f); w.writerow(['name','pos','team','proj_fpg','tier','adp','trend_delta','succeeds_in','struggles_in'])
    w.writerows(summary_rows)

print('WROTE profiles:', len(summary_rows),'players')
print(open(os.path.join(OUT,'PLAYER_PROFILES.md')).read()[:1200])
