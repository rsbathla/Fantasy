#!/usr/bin/env python3
"""TWO-SEASON CHARTING (FantasyPoints 2024 + 2025, same source) -> boom/chart2yr.json + statmenu['chart2'].
2024 = per-player aggregate exports (fresh). 2025 = per-game exports aggregated to per-player.
Rates recomputed from summed counts where possible; shares games-weighted. These are the charting
signals (YPRR, TPRR, aDOT, air-yard share, YAC/YACO, MTF, 1st-read, contested, alignment; RB
YBCO/explosive/stuff/i5/success; QB aDOT/deep/pressure/CPOE) that single-season fusion lacked for 2024.
"""
import csv, json, os, re
HERE = os.path.dirname(os.path.abspath(__file__)); B = os.path.join(HERE, 'boom')
# FP Advanced exports now live IN-REPO (version-controlled; re-pulled 2026) as SEASON AGGREGATES for BOTH
# years -- so they can't silently vanish from the ephemeral Downloads folder again.
FPADV = os.path.join(HERE, 'NFL-master', 'FP_ADVANCED')
def fn(n):
    n = str(n).strip().lower(); n = re.sub(r'\s+(jr|sr|ii|iii|iv|v)\.?$', '', n)
    return n.replace('.', '').replace("'", "").replace('-', ' ')
def num(x):
    try: return float(str(x).replace('%', '').replace(',', '').strip())
    except Exception: return None
def dr(path):  # DictReader (utf-8-sig strips BOM)
    return list(csv.DictReader(open(os.path.join(FPADV, path), encoding='utf-8-sig')))
def rdr(path):  # raw rows (for dup-header files)
    rows = list(csv.reader(open(os.path.join(FPADV, path), encoding='utf-8-sig'))); return rows[0], rows[1:]

# ---------------- RECEIVING (WR/TE) ----------------
REC24 = dr("receiving_2024.csv")     # per-player season aggregate 2024
REC25 = dr("receiving_2025.csv")     # per-player season aggregate 2025 (now aggregate, was per-game)
def rec_tot_from_agg(r):
    return {'g': num(r['G']) or 0, 'rte': num(r['RTE']) or 0, 'tgt': num(r['TGT']) or 0, 'ay': num(r['AY']) or 0,
        'rec': num(r['REC']) or 0, 'yds': num(r['YDS']) or 0, 'yac': num(r['YAC']) or 0, 'yaco': num(r['YACO']) or 0,
        'mtf': num(r['MTF']) or 0, 'td': num(r['TD']) or 0, 'fr': num(r['1READ']) or 0, 'dp': num(r['DP TGT']) or 0,
        'cc': num(r['CC']) or 0, 'i20': num(r['i20 TGT']) or 0, 'ez': num(r['EZTGT']) or 0, 'ays': num(r['AY Share']), 'slot': num(r['SLOT RTE %']), 'wide': num(r['WIDE RTE %']),
        'design': num(r['DESIGN %']), 'inline': num(r['INLINE RTE %']), 'back': num(r['BACK RTE %']),
        'threat': num(r['THREAT']), 'fprr': num(r['FP/RR'])}
def rec_tot_from_pg(rows):  # sum a player's game rows -> season totals
    t = {k: 0 for k in ['g','rte','tgt','ay','rec','yds','yac','yaco','mtf','td','fr','dp','cc','i20','ez']}
    ays = wsl = wwd = wth = wfp = wds = win = wbk = 0.0; wsum = 0.0
    for r in rows:
        t['g'] += 1
        for k, col in [('rte','RTE'),('tgt','TGT'),('ay','AY'),('rec','REC'),('yds','YDS'),('yac','YAC'),
                       ('yaco','YACO'),('mtf','MTF'),('td','TD'),('fr','1READ'),('dp','DP TGT'),('cc','CC'),('i20','i20 TGT'),('ez','EZTGT')]:
            t[k] += (num(r[col]) or 0)
        w = num(r['RTE']) or 0; wsum += w  # route-weight the share/rate fields
        for acc, col in [('ays','AY Share'),('slot','SLOT RTE %'),('wide','WIDE RTE %'),('threat','THREAT'),('fprr','FP/RR'),('design','DESIGN %'),('inline','INLINE RTE %'),('back','BACK RTE %')]:
            v = num(r[col])
            if v is not None: 
                if acc=='ays': ays += v*w
                elif acc=='slot': wsl += v*w
                elif acc=='wide': wwd += v*w
                elif acc=='threat': wth += v*w
                elif acc=='fprr': wfp += v*w
                elif acc=='design': wds += v*w
                elif acc=='inline': win += v*w
                elif acc=='back': wbk += v*w
    ws = wsum or 1
    t.update({'ays': ays/ws, 'slot': wsl/ws, 'wide': wwd/ws, 'threat': wth/ws, 'fprr': wfp/ws, 'design': wds/ws, 'inline': win/ws, 'back': wbk/ws})
    return t
def rec_rates(t):
    rte = t['rte'] or 1; tgt = t['tgt'] or 1; rec = t['rec'] or 1
    return {'g': round(t['g']), 'aDOT': round(t['ay']/tgt,1), 'tprr': round(t['tgt']/rte,3), 'yprr': round(t['yds']/rte,2),
        'ypt': round(t['yds']/tgt,1), 'catch': round(100*t['rec']/tgt), 'yac_rec': round(t['yac']/rec,1),
        'yaco_rec': round(t['yaco']/rec,1), 'mtf_rec': round(t['mtf']/rec,2), 'fr_pct': round(100*t['fr']/rte),
        'deep_pct': round(100*t['dp']/tgt), 'contested_pct': round(100*t['cc']/rec) if rec else None,
        'i20_pg': round(t.get('i20',0)/(t['g'] or 1),2), 'ez_tgt': round(t.get('ez',0)), 'rz_tgt_rate': round(100*t.get('i20',0)/tgt),
        'ay_share': round(t['ays'],1) if t.get('ays') is not None else None,
        'slot_pct': round(t['slot']) if t.get('slot') is not None else None,
        'wide_pct': round(t['wide']) if t.get('wide') is not None else None,
        'inline_pct': round(t['inline']) if t.get('inline') is not None else None,
        'back_pct': round(t['back']) if t.get('back') is not None else None,
        'design_pct': round(t['design'],1) if t.get('design') is not None else None,
        'threat': round(t['threat'],1) if t.get('threat') is not None else None,
        'fp_rr': round(t['fprr'],2) if t.get('fprr') is not None else None}

# ---------------- RUSHING (RB) — positional (dup headers) ----------------
RU24h, RU24 = rdr("rushing_2024.csv")  # 2024 season aggregate
RU25h, RU25 = rdr("rushing_2025.csv")  # 2025 season aggregate (identical column layout; was per-game +3 offset)
def ru_tot_agg(r):  # 2024 agg col indices
    g=num(r[4]); return {'g':g or 0,'att':num(r[6]) or 0,'yds':num(r[7]) or 0,'td':num(r[10]) or 0,'mtf':num(r[20]) or 0,
        'yaco':num(r[22]) or 0,'ybco_att':num(r[25]),'succ':num(r[18]),'stuff':num(r[19]),'exprun':num(r[13]),
        'i5':num(r[16]),'tdrate':num(r[17]),'ypc':num(r[9])}
def ru_tot_pg(rows):  # 2025 per-game, +3 col offset (Season Type, WEEK, Opponent inserted after Season)
    o=3; t={'g':0,'att':0,'yds':0,'td':0,'mtf':0,'yaco':0}; ww=0.0; wyb=ws=wst=wex=wi5=wtd=0.0
    for r in rows:
        t['g']+=1; a=num(r[6+o]) or 0; t['att']+=a; t['yds']+=num(r[7+o]) or 0; t['td']+=num(r[10+o]) or 0
        t['mtf']+=num(r[20+o]) or 0; t['yaco']+=num(r[22+o]) or 0; ww+=a
        for accname,ci in [('yb',25),('su',18),('st',19),('ex',13),('i5',16),('td',17)]:
            v=num(r[ci+o])
            if v is not None:
                if accname=='yb': wyb+=v*a
                elif accname=='su': ws+=v*a
                elif accname=='st': wst+=v*a
                elif accname=='ex': wex+=v*a
                elif accname=='i5': wi5+=v*a
                elif accname=='td': wtd+=v*a
    w=ww or 1
    return {**t,'ybco_att':wyb/w,'succ':ws/w,'stuff':wst/w,'exprun':wex/w,'i5':wi5/w,'tdrate':wtd/w,'ypc':(t['yds']/(t['att'] or 1))}
def ru_rates(t):
    att=t['att'] or 1; rec_g=t['g'] or 1
    return {'g':round(t['g']),'ypc':round(t['yds']/att,2),'mtf_att':round(t['mtf']/att,3),'yaco_att':round(t['yaco']/att,2),
        'ybco_att':round(t['ybco_att'],2) if t.get('ybco_att') is not None else None,
        'success':round(t['succ']) if t.get('succ') is not None else None,
        'stuff':round(t['stuff']) if t.get('stuff') is not None else None,
        'exp_run':round(t['exprun'],1) if t.get('exprun') is not None else None,
        'i5_pct':round(t['i5'],1) if t.get('i5') is not None else None,
        'td_rate':round(t['tdrate'],1) if t.get('tdrate') is not None else None}

# ---------------- PASSING (QB) — 2024 + 2025 ----------------
PA24 = dr("passing_2024.csv"); PA25 = dr("passing_2025.csv")
def qb_chart(r):
    return {'g':round(num(r['G']) or 0),'aDOT':num(r['aDOT']),'deep_pct':num(r['Deep Throw %']),'cpoe':num(r['CPOE']),
        'press_pct':num(r['PRESS %']),'ttt':num(r['TTT']),'scrm':num(r['SCRM']),'oneread_pct':num(r['1Read %']),'acc_pct':num(r['ACC %'])}

def gw(v24, v25, g24, g25):  # games-weighted blend of two per-year rates
    vals = [(v24, g24), (v25, g25)]; vals = [(v, g) for v, g in vals if v is not None and g]
    if not vals: return None
    return round(sum(v*g for v, g in vals)/sum(g for _, g in vals), 3)

# ---- assemble ----
chart = {}
# receiving: UNION of 2024 + 2025 players (both season aggregates) -> 2025-only sophomores/rookies
# (Egbuka, McMillan, Loveland, ...) are now charted instead of being silently dropped by the old
# 2024-anchored loop. Blend = summed counts (rates recomputed) + games-weighted shares/rate fields.
rec24 = {fn(r['Name']): r for r in REC24}; rec25 = {fn(r['Name']): r for r in REC25}
for k in set(rec24) | set(rec25):
    a24 = rec24.get(k); a25 = rec25.get(k)
    t24 = rec_tot_from_agg(a24) if a24 else None; c24 = rec_rates(t24) if t24 else None
    t25 = rec_tot_from_agg(a25) if a25 else None; c25 = rec_rates(t25) if t25 else None
    comb = {kk: ((t24.get(kk,0) if t24 else 0) + (t25.get(kk,0) if t25 else 0)) for kk in ['rte','tgt','ay','rec','yds','yac','yaco','mtf','td','fr','dp','cc','i20','ez']}
    comb['g'] = (t24['g'] if t24 else 0) + (t25['g'] if t25 else 0)
    blend = rec_rates(comb)
    for shf in ['ay_share','slot_pct','wide_pct','inline_pct','back_pct','design_pct','threat','fp_rr']:
        blend[shf] = gw((c24 or {}).get(shf), (c25 or {}).get(shf), (t24['g'] if t24 else 0), (t25['g'] if t25 else 0))
    disp = a25 or a24
    chart[k] = {'pos': disp['POS'], 'name': disp['Name'], 'g24': (c24['g'] if c24 else 0), 'g25': (c25['g'] if c25 else 0),
                'y2024': c24, 'y2025': c25, 'blend': blend}
# rushing: UNION of 2024 + 2025 (both season aggregates, identical layout)
rush24 = {fn(r[1]): r for r in RU24}; rush25 = {fn(r[1]): r for r in RU25}
for k in set(rush24) | set(rush25):
    b24 = rush24.get(k); b25 = rush25.get(k)
    t24 = ru_tot_agg(b24) if b24 else None; c24 = ru_rates(t24) if t24 else None
    t25 = ru_tot_agg(b25) if b25 else None; c25 = ru_rates(t25) if t25 else None
    comb = {kk: ((t24.get(kk,0) if t24 else 0) + (t25.get(kk,0) if t25 else 0)) for kk in ['att','yds','td','mtf','yaco']}
    comb['g'] = (t24['g'] if t24 else 0) + (t25['g'] if t25 else 0)
    for sh in ['ybco_att','succ','stuff','exprun','i5','tdrate']:
        comb[sh] = gw((t24 or {}).get(sh), (t25 or {}).get(sh), (t24['g'] if t24 else 0), (t25['g'] if t25 else 0))
    blend = ru_rates(comb)
    disp = b25 or b24
    chart[k] = {'pos': disp[3], 'name': disp[1], 'g24': (c24['g'] if c24 else 0), 'g25': (c25['g'] if c25 else 0),
                'y2024': c24, 'y2025': c25, 'blend': blend}
# passing: UNION of 2024 + 2025 -> QBs now get 2-YEAR charting (was 2024-only)
pa24 = {fn(r['Name']): r for r in PA24}; pa25 = {fn(r['Name']): r for r in PA25}
for k in set(pa24) | set(pa25):
    q24 = pa24.get(k); q25 = pa25.get(k)
    c24 = qb_chart(q24) if q24 else None; c25 = qb_chart(q25) if q25 else None
    g24 = (c24['g'] if c24 else 0); g25 = (c25['g'] if c25 else 0)
    blend = {'g': g24 + g25}
    for f in ['aDOT','deep_pct','cpoe','press_pct','ttt','scrm','oneread_pct','acc_pct']:
        blend[f] = gw((c24 or {}).get(f), (c25 or {}).get(f), g24, g25)
    disp = q25 or q24
    chart[k] = {'pos': disp['POS'], 'name': disp['Name'], 'g24': g24, 'g25': g25,
                'y2024': c24, 'y2025': c25, 'blend': blend}

json.dump(chart, open(f"{B}/chart2yr.json", 'w'), ensure_ascii=False)
# augment statmenu
sm = json.load(open(f"{B}/statmenu.json"))
hit = 0
for k, v in sm.items():
    if k in chart: v['chart2'] = chart[k]; hit += 1
json.dump(sm, open(f"{B}/statmenu.json", 'w'), ensure_ascii=False)

print(f"chart2yr: {len(chart)} players | matched into statmenu: {hit}/{len(sm)}")
for nm in ['Puka Nacua','Brian Thomas Jr.','Ja\'Marr Chase','Jahmyr Gibbs','Saquon Barkley','Josh Allen']:
    c = chart.get(fn(nm))
    if c: print(f"  {nm:18s} g24/25={c['g24']}/{c['g25']} blend={json.dumps(c['blend'])[:240]}")
