#!/usr/bin/env python3
"""SHARED FOUNDATION for the player-by-player FLAG-BASED boom model.
Builds the data every position agent consumes, so all positions stay consistent:
  - NEW boom def: position spike thresholds (QB>=24, RB>=20, WR>=20, TE>=15) -- a real
    ceiling game, NOT scaled to the player's own projection (fixes the Gibbs problem).
  - statmenu.json : per player, the FULL stat menu (fusion pctls + aDOT/TPRR + YACoe/MTF +
    usage/role + SIS efficiency splits) -> the raw material for skill flags.
  - gamelog.json  : per player, 2025 game log with joined context (opp, opp pass/run-D pctl,
    home/away, dome, wind) + boom(0/1) under the new def -> empirical flag confirmation.
  - schedule2026.json : every team's full-season opponents (W1-18) + home/away + dome.
  - defense2026.json  : per team, the matchup profile a player faces (cov/run/man/sack pctls,
    per-position allow tiers, pass-rush) -> the raw material for matchup flags.
Outputs go to bestball/boom/.
"""
import csv, json, re, os, bisect
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__)); DL = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'boom'); os.makedirs(OUT, exist_ok=True)

def fn(n):
    n = str(n).strip().lower(); n = re.sub(r'\s+(jr|sr|ii|iii|iv|v)\.?$', '', n)
    return n.replace('.', '').replace("'", "").replace('-', ' ')
TMAP = {'LA':'LAR','JAC':'JAX','WSH':'WAS','ARZ':'ARI','GNB':'GB','KAN':'KC','SFO':'SF','TAM':'TB','NWE':'NE','NOR':'NO'}
def tm(t):
    t = str(t).strip().upper().lstrip('@'); return TMAP.get(t, t)
def num(x, d=None):
    try: return float(x)
    except Exception: return d
def rows(p):
    return list(csv.DictReader(open(p, encoding='utf-8'))) if os.path.exists(p) else []

# weather-neutral venues (fixed/retractable dome or covered) -> no wind penalty on deep balls
DOME = {'ATL','NO','DET','MIN','LV','ARI','DAL','HOU','IND','LAR','LAC'}
FULL2ABBR = {'Arizona Cardinals':'ARI','Atlanta Falcons':'ATL','Baltimore Ravens':'BAL','Buffalo Bills':'BUF',
 'Carolina Panthers':'CAR','Chicago Bears':'CHI','Cincinnati Bengals':'CIN','Cleveland Browns':'CLE',
 'Dallas Cowboys':'DAL','Denver Broncos':'DEN','Detroit Lions':'DET','Green Bay Packers':'GB','Houston Texans':'HOU',
 'Indianapolis Colts':'IND','Jacksonville Jaguars':'JAX','Kansas City Chiefs':'KC','Los Angeles Chargers':'LAC',
 'Los Angeles Rams':'LAR','Las Vegas Raiders':'LV','Miami Dolphins':'MIA','Minnesota Vikings':'MIN',
 'New England Patriots':'NE','New Orleans Saints':'NO','New York Giants':'NYG','New York Jets':'NYJ',
 'Philadelphia Eagles':'PHI','Pittsburgh Steelers':'PIT','Seattle Seahawks':'SEA','San Francisco 49ers':'SF',
 'Tampa Bay Buccaneers':'TB','Tennessee Titans':'TEN','Washington Commanders':'WAS'}

# ---------- NEW BOOM DEFINITION (position spike thresholds) ----------
# Strict, derived in derive_boom_threshold.py = avg(85th pctl, mean+1sd) of each position's
# active-starter actual distribution (the two anchors agree within 8%). NOT scaled to own proj.
_bd = json.load(open(f"{OUT}/boomdef.json"))
SPIKE = _bd['SPIKE']
SKILL = ['QB', 'RB', 'WR', 'TE']  # skill-player positions (DST handled separately below)

# ---------- 1) game log + base boom rate ----------
sched25 = json.load(open(f"{DL}/dfs_review/schedule_2025.json"))
homeaway = json.load(open(f"{DL}/dfs_review/fl_data/homeaway_2025.json"))
weather = json.load(open(f"{DL}/dfs_review/fl_data/weather_2025.json"))
# opponent-strength proxy (2026 roster-adjusted Points Saved -> percentiles; higher=tougher)
DM = json.load(open(f"{DL}/dfs_review/out/defense_2026_matchup.json"))
covs = sorted(v['cov'] for v in DM.values()); runs = sorted(v['run'] for v in DM.values())
def pctl(sv, x):
    if x is None: return None
    return round(100 * bisect.bisect_left(sv, x) / max(1, len(sv) - 1))
def opp_passp(t): d = DM.get(tm(t)); return pctl(covs, d['cov']) if d else None
def opp_runp(t):  d = DM.get(tm(t)); return pctl(runs, d['run']) if d else None

gamelog = defaultdict(list); base = {}; posg = defaultdict(list)
for r in rows(f"{DL}/dfs_review/out/boom_proj.csv"):
    pos = (r.get('pos') or '').upper()
    if pos not in SKILL: continue
    proj = num(r['proj']); act = num(r['actual'])
    if proj is None or act is None or proj < 8: continue   # active games only
    wk = r['wk']; team = tm(r['team']); opp = tm(sched25.get(wk, {}).get(team, '') or '')
    ha = homeaway.get(wk, {}).get(team) or homeaway.get(wk, {}).get(r['team'])
    home = (ha == 'H')
    venue = team if home else opp
    wx = weather.get(wk, {}).get(venue, {}) if venue else {}
    boom = 1 if act >= SPIKE[pos] else 0
    posg[pos].append(boom)
    gamelog[fn(r['name'])].append({'wk': int(wk) if wk.isdigit() else wk, 'opp': opp, 'home': home,
        'dome': venue in DOME, 'wind': wx.get('wind'), 'precip': wx.get('precip'),
        'proj': round(proj, 1), 'act': round(act, 1), 'boom': boom,
        'opp_passp': opp_passp(opp), 'opp_runp': opp_runp(opp)})
posbase = {p: (sum(v) / len(v) if v else 0.18) for p, v in posg.items()}
for k, g in gamelog.items():
    if len(g) >= 4: base[k] = sum(x['boom'] for x in g) / len(g)

# ---------- 2) stat menu (fusion + aDOT/TPRR + YACoe/MTF + usage + SIS) ----------
FUS = {fn(r['name']): r for r in rows(f"{HERE}/fusion_table.csv")}
ADOT = {}
for r in rows(f"{DL}/adot-tprr.csv"):
    nm = r.get('Name');
    if nm: ADOT[fn(nm)] = {'aDOT': num(r.get('aDOT')), 'TPRR': num(r.get('TPRR')),
        'surplus_TPRR': num(r.get('Surplus TPRR')), 'routes': num(r.get('Routes'))}
YACO = {}
for r in rows(f"{DL}/ffdataroma_draft_guide_export/ffdataroma/csv/adot-adjusted-yac.csv"):
    raw = r.get('Player', '');
    m = re.match(r'^(.*?)([A-Z]{2,3})$', raw)  # "DK MetcalfPIT" -> name, team
    nm = m.group(1) if m else raw
    if nm: YACO[fn(nm)] = {'YACoe': num(str(r.get('YACoeYACoe/Rec', '')).replace('+', '')),
        'MTFoe': num(str(r.get('MTFoeMTFoe/Rec', '')).replace('+', ''))}
L2 = {}
_l2p = f"{HERE}/pipeline/layer2_player_params.csv"
if not os.path.exists(_l2p): _l2p = f"{DL}/pipeline/layer2_player_params.csv"
for r in rows(_l2p): L2[fn(r['name'])] = r
# SIS WR coverage master (last-6 efficiency, opp-weighted)
SISWR = {}
_wr = f"{DL}/NFL-master/AGG_COVERAGE_SHEETS_WR_LAST6/AGG_MASTER_ALL_COVERAGES_WR.csv"
for r in rows(_wr):
    nm = r.get('Player')
    if not nm: continue
    def g(*keys):
        for k in keys:
            for kk in r:
                if kk.replace('\n', ' ').strip().startswith(k): return num(r[kk])
        return None
    SISWR[fn(nm)] = {'YPRR': g('YPRR'), 'TPRR_w': g('TPRR (0-1'), 'airyard_pct': g('Air Yard %'),
        'tgt_share_w': g('Target Share'), 'eff_combined': g('EFFICIENCY COMBINED'), 'FP_RR': g('FP/RR')}
# SIS RB runtypes
SISRB = {}
_rb = f"{DL}/NFL-master/AGG_COVERAGE_SHEETS_RB_LAST6/AGG_MASTER_ALL_RUNTYPES_WITH_TARGETS.csv"
for r in rows(_rb):
    nm = r.get('Player')
    if not nm: continue
    def g2(*keys):
        for k in keys:
            for kk in r:
                if kk.replace('\n', ' ').strip().startswith(k): return num(r[kk])
        return None
    SISRB[fn(nm)] = {'MTF_att': g2('MTF/ATT'), 'success': g2('Success Rate'), 'ypc': g2('YPC'),
        'yaco_pct': g2('YACO %'), 'tgts_g': g2('Targets/Game'), 'rush_fd_att': g2('Rush FD/ATT')}

PCTLS = ['value_pctl','ceiling_pctl','spike_pctl','boom_pctl','route_eff_pctl','coverage_proof_pctl',
    'run_eff_pctl','rec_eff_pctl','separation_pctl','yac_pctl','rush_eff_pctl','explosive_pctl',
    'protection_pctl','oline_pctl','matchup_pctl','adv_pctl','sis_value_pctl']

statmenu = {}
board = rows(f"{HERE}/draft_board_signals.csv")
for r in board:
    pos = (r.get('pos') or '').upper()
    if pos not in SKILL: continue
    k = fn(r['name']); f = FUS.get(k, {}); l2 = L2.get(k, {})
    g = gamelog.get(k, [])
    sm = {'name': r['name'], 'pos': pos, 'team': tm(r.get('team') or ''), 'adp': num(r.get('adp')),
        'base_boom': round(base[k], 3) if k in base else None, 'n_games': len(g),
        'boom_games': sum(x['boom'] for x in g),
        'fus': {p: num(f.get(p)) for p in PCTLS if num(f.get(p)) is not None},
        'adot': ADOT.get(k, {}), 'yaco': YACO.get(k, {}),
        'usage': {kk: num(l2.get(kk)) for kk in ['carry_pg','carry_share','ypc','tgt_share','catch_rate',
            'ypt','dk_pg','routes_pg','rz_share','tgt_pg','rush_share'] if num(l2.get(kk)) is not None},
        'role': str(l2.get('role', '') or ''),
        'sis': (SISWR.get(k, {}) if pos in ('WR','TE') else SISRB.get(k, {}))}
    statmenu[k] = sm

# ---------- 3) full 2026 schedule per team ----------
schedule2026 = {}
import csv as _csv
with open(f"{HERE}/pipeline/schedule_2026.csv", encoding='utf-8') as fh:
    rd = _csv.reader(fh); header = next(rd)
    wkcols = [(i, h.replace('Week ', '').strip()) for i, h in enumerate(header) if h.startswith('Week')]
    for row in rd:
        team = FULL2ABBR.get(row[0].strip())
        if not team: continue
        games = []
        for i, wk in wkcols:
            cell = (row[i] or '').strip()
            if not cell or cell.upper() == 'BYE':
                games.append({'wk': int(wk), 'opp': 'BYE', 'home': None, 'dome': None}); continue
            away = cell.startswith('@'); opp = tm(cell)
            venue = opp if away else team
            games.append({'wk': int(wk), 'opp': opp, 'home': (not away), 'dome': venue in DOME})
        schedule2026[team] = games

# ---------- 4) defense profile each team presents in 2026 ----------
DEFP = json.load(open(f"{DL}/dfs_review/out/defense.json"))
COV = {tm(r['team']): r for r in rows(f"{HERE}/defense_coverage.csv")}
mr = sorted(num(r['def_man_rate']) for r in COV.values() if num(r.get('def_man_rate')) is not None)
sk = sorted(num(r['def_sack_rate']) for r in COV.values() if num(r.get('def_sack_rate')) is not None)
defense2026 = {}
for t in DM:
    dm = DM[t]; sc = COV.get(t, {})
    defense2026[t] = {'covp': pctl(covs, dm['cov']), 'runp': pctl(runs, dm['run']),
        'manp': pctl(mr, num(sc.get('def_man_rate'))) if sc else None,
        'sackp': pctl(sk, num(sc.get('def_sack_rate'))) if sc else None,
        'man_rate': num(sc.get('def_man_rate')), 'sack_rate': num(sc.get('def_sack_rate')),
        'tiers': {p: (DEFP.get(t, {}).get(p, {}) or {}).get('tier', '') for p in ('QB','RB','WR','TE')}}

# ---------- DST: opponent-offense quality + own-unit profile + game log ----------
TEAMS32 = sorted(defense2026.keys())
byteam = defaultdict(lambda: {'val': [], 'qb': [], 'ol': [], 'pp': []})
for r in board:
    pos = (r.get('pos') or '').upper(); k = fn(r['name'])
    t = tm(r.get('team') or ''); adp = num(r.get('adp'))
    if t not in defense2026: continue
    if pos in SKILL and num(r.get('proj_pg')): byteam[t]['val'].append(num(r.get('proj_pg')))
    _olp = num((FUS.get(k, {}) or {}).get('oline_pctl')); _ppp = num((FUS.get(k, {}) or {}).get('protection_pctl'))
    if _olp is not None: byteam[t]['ol'].append(_olp)
    if _ppp is not None: byteam[t]['pp'].append(_ppp)
    if pos == 'QB':
        vq = num((FUS.get(k, {}) or {}).get('value_pctl'))
        byteam[t]['qb'].append((adp if adp else 9999, r['name'], vq if vq is not None else 50))
def off_str(t):
    v = sorted(byteam[t]['val'], reverse=True); return sum(v[:8])
offs_all = sorted(off_str(t) for t in TEAMS32)
def team_ol(t):
    return max(byteam[t]['ol']) if byteam[t]['ol'] else 50   # team OL trait (max is robust to missing)
def team_pp(t):
    return (sorted(byteam[t]['pp'])[len(byteam[t]['pp'])//2] if byteam[t]['pp'] else 50)
ols_all = sorted(team_ol(t) for t in TEAMS32)
opp_offense = {}
for t in TEAMS32:
    qbs = sorted(byteam[t]['qb'])  # starter = lowest ADP
    opp_offense[t] = {'off_q': pctl(offs_all, off_str(t)),
        'qb': qbs[0][1] if qbs else '', 'qb_q': round(qbs[0][2]) if qbs else 50,
        'ol_q': pctl(ols_all, team_ol(t)), 'pblock': round(team_pp(t))}

# DST game log (boom = team DST actual >= DST threshold) + own profile into statmenu
dst_posg = []
for r in rows(f"{DL}/dfs_review/out/boom_proj.csv"):
    if (r.get('pos') or '').upper() != 'DST': continue
    proj = num(r['proj']); act = num(r['actual'])
    if proj is None or act is None: continue
    team = tm(r['team'])
    if team not in defense2026: continue
    wk = r['wk']; opp = tm(sched25.get(wk, {}).get(team, '') or '')
    ha = homeaway.get(wk, {}).get(team); home = (ha == 'H'); venue = team if home else opp
    boom = 1 if act >= SPIKE['DST'] else 0
    dst_posg.append(boom)
    gamelog['dst_' + team.lower()].append({'wk': int(wk) if wk.isdigit() else wk, 'opp': opp,
        'home': home, 'dome': venue in DOME, 'proj': round(proj, 1), 'act': round(act, 1), 'boom': boom,
        'opp_off_q': opp_offense.get(opp, {}).get('off_q'), 'opp_qb_q': opp_offense.get(opp, {}).get('qb_q')})
posbase['DST'] = (sum(dst_posg) / len(dst_posg)) if dst_posg else 0.16
for t in TEAMS32:
    key = 'dst_' + t.lower(); g = gamelog.get(key, [])
    if len(g) >= 4: base[key] = sum(x['boom'] for x in g) / len(g)
    statmenu[key] = {'name': t + ' DST', 'pos': 'DST', 'team': t, 'adp': None,
        'base_boom': round(base[key], 3) if key in base else None, 'n_games': len(g),
        'boom_games': sum(x['boom'] for x in g), 'def': defense2026[t],
        'fus': {}, 'adot': {}, 'yaco': {}, 'usage': {}, 'role': 'DST', 'sis': {}}
json.dump(opp_offense, open(f"{OUT}/opp_offense.json", 'w'), ensure_ascii=False)

# ---------- save ----------
# CLOBBER GUARD: foundation rewrites statmenu.json from scratch, which would wipe the keys the
# augmenter scripts (boom_base2yr / adv2yr / build_chart2yr / build_extra_signals / build_cover_spec)
# add. Carry those forward from the prior file so a foundation re-run is non-destructive. The
# pipeline still re-runs the augmenters afterward to refresh them; this only prevents the silent
# regression window where reg_base() falls back to the 2025-only base.
_AUG_KEYS = ('base_blended','base_hist2','base_proj','g2','b2','g24','b24','g25','b25','hist2',
             'adv2','chart2','rz','team_env','cspec')
_smpath = f"{OUT}/statmenu.json"
if os.path.exists(_smpath):
    try:
        _old = json.load(open(_smpath)); _carried = 0
        for _k, _v in statmenu.items():
            _ov = _old.get(_k)
            if isinstance(_ov, dict):
                for _ak in _AUG_KEYS:
                    if _ak in _ov and _ak not in _v:
                        _v[_ak] = _ov[_ak]; _carried += 1
        print(f"[clobber-guard] carried forward {_carried} augmentation values from prior statmenu.json")
    except Exception as _e:
        print(f"[clobber-guard] could not read prior statmenu.json ({_e}); writing fresh")
json.dump(statmenu, open(f"{OUT}/statmenu.json", 'w'), ensure_ascii=False)
json.dump(gamelog, open(f"{OUT}/gamelog.json", 'w'), ensure_ascii=False)
json.dump(schedule2026, open(f"{OUT}/schedule2026.json", 'w'), ensure_ascii=False)
json.dump(defense2026, open(f"{OUT}/defense2026.json", 'w'), ensure_ascii=False)
_bd['posbase'] = posbase  # merge in, preserve provenance/robustness from the derivation step
json.dump(_bd, open(f"{OUT}/boomdef.json", 'w'), indent=1)

print('SPIKE thresholds:', SPIKE)
print('position base boom rate (active games):', {p: round(v, 3) for p, v in posbase.items()})
print('statmenu players:', len(statmenu), '| with >=4 game history:', sum(1 for v in statmenu.values() if v['base_boom'] is not None))
print('schedule2026 teams:', len(schedule2026), '| defense2026 teams:', len(defense2026))
print('SIS WR enriched:', sum(1 for v in statmenu.values() if v['pos'] in ('WR','TE') and v['sis'].get('YPRR') is not None),
      '| SIS RB enriched:', sum(1 for v in statmenu.values() if v['pos']=='RB' and v['sis'].get('success') is not None),
      '| aDOT enriched:', sum(1 for v in statmenu.values() if v['adot'].get('aDOT') is not None))
for nm in ['Jahmyr Gibbs','Puka Nacua','Josh Allen','Trey McBride']:
    v = statmenu.get(fn(nm))
    if v: print(f"  {nm}: base_boom={v['base_boom']} ({v['boom_games']}/{v['n_games']}) aDOT={v['adot'].get('aDOT')} explosive={v['fus'].get('explosive_pctl')}")
