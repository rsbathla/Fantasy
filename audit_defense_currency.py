#!/usr/bin/env python3
"""LEAGUE-WIDE defense data-currency audit (all 32 teams, one identical test each).

Motivation: DET (Arnold released / Joseph injured-and-absent) and LAR were only EXAMPLES of two
error classes. This applies the same two tests to every team, mechanically, so nothing is special-cased.

Two sweeps, both cross-referencing the model's source (SIS 2025 Points-Saved leaderboards, which drive
normalize_defense_2026) against PFF grades (2024 healthy-season + 2025) and the curated MOVES map:

  A. MISSING-CONTRIBUTOR (the Joseph pattern): a player who was a clear, well-graded STARTER in 2024
     by PFF but is ABSENT from the 2025 SIS unit leaderboard the model reads -> the model cannot credit
     him. Characterized by his 2025 PFF status (injured? declined? gone?) and MOVES destination so we
     can tell injury-absence (Joseph) from left-the-league.

  B. FALSE-CREDIT EXPOSURE (the Arnold pattern): SIS-2025 contributors still credited to a 2026 team
     because they are ASSUMED to stay (not in MOVES). Ranked by impact so the load-bearing unverified
     assumptions are visible per team.

Read-only: prints a report + writes boom/defense_currency_audit.json. Fabricates nothing.
"""
import csv, os, json, collections
import core
fn = core.fn

HERE = os.path.dirname(os.path.abspath(__file__))
PFF2MODEL = {'ARZ':'ARI','BLT':'BAL','CLV':'CLE','HST':'HOU','LA':'LAR'}
def pteam(t): return PFF2MODEL.get(t, t)

# ---- MOVES map (import head of reweight_defense_2026, same as normalize does) ----
_src = open(core.P('reweight_defense_2026.py'), encoding='utf-8').read().split('UNITS=')[0]
_ns = {}; exec(_src, _ns)
MOVES = _ns['MOVES']; nick = _ns['nick']

# ---- SIS 2025 presence per unit (the model's source of truth) ----
SIS_UNITS = {'coverage':'sis_value/pass_defense.csv',
             'pass_rush':'sis_value/pass_rush.csv',
             'run_def':'sis_value/run_defense.csv'}
def sis_present(path):
    d = {}
    for r in csv.DictReader(open(core.P(path), encoding='utf-8')):
        raw = str(r.get('Team','')).strip()
        d[fn(r['Player'])] = {'name':r['Player'],'team':('2T' if raw=='2 teams' else nick(raw)),
                              'ps':core.num(r.get('Points Saved')) if hasattr(core,'num') else None}
    return d
def _num(x):
    try: return float(str(x).replace('%','').replace('"',''))
    except: return None
SIS = {u: {} for u in SIS_UNITS}
for u,p in SIS_UNITS.items():
    for r in csv.DictReader(open(core.P(p), encoding='utf-8')):
        raw = str(r.get('Team','')).strip()
        SIS[u][fn(r['Player'])] = {'name':r['Player'],'team':('2T' if raw=='2 teams' else nick(raw)),'ps':_num(r.get('Points Saved'))}

# ---- PFF grades (2024 + 2025), per unit, with snaps + position + team ----
# unit -> (grade col, snap col, eligible PFF positions)
PFF_UNIT = {'coverage':('grades_coverage_defense','snap_counts_coverage',{'CB','S','LB'}),
            'pass_rush':('grades_pass_rush_defense','snap_counts_pass_rush',{'ED','DI'}),
            'run_def':('grades_run_defense','snap_counts_run_defense',{'DI','ED','LB','S','CB'})}
def load_pff(yr):
    out = {}
    p = core.P(f'NFL-master/PFF/{yr}/defense.csv')
    for r in csv.DictReader(open(p, encoding='utf-8-sig')):
        out[fn(r['player'])] = r
    return out
PFF = {'2024':load_pff('2024'), '2025':load_pff('2025')}

# thresholds for "a clear, well-graded 2024 starter" per unit
GRADE_MIN = 74.0     # PFF "good" and up
SNAP_MIN  = {'coverage':400,'pass_rush':300,'run_def':300}

def moves_dest(key):
    mv = MOVES.get(key)
    return mv['to'] if mv else None

# ---------------- SWEEP A: missing contributors ----------------
missing = []
for key, r24 in PFF['2024'].items():
    pos = r24.get('position','')
    for unit,(gcol,scol,elig) in PFF_UNIT.items():
        if pos not in elig: continue
        g = _num(r24.get(gcol)); s = _num(r24.get(scol))
        if g is None or s is None or g < GRADE_MIN or s < SNAP_MIN[unit]: continue
        if key in SIS[unit]: continue           # model already has him -> fine
        # he's a graded 2024 starter the model's SIS source omits. Characterize 2025 + 2026.
        r25 = PFF['2025'].get(key)
        g25 = _num(r25.get(gcol)) if r25 else None
        s25 = _num(r25.get(scol)) if r25 else None
        dest = moves_dest(key)
        team24 = pteam(r24.get('team_name',''))
        team26 = ('OUT('+dest+')' if dest in ('UFA','RETIRED') else (dest or team24))
        missing.append({'name':r24['player'],'key':key,'unit':unit,'pos':pos,
                        'team_2024':team24,'grade_2024':round(g,1),'snaps_2024':int(s),
                        'grade_2025':round(g25,1) if g25 is not None else None,
                        'snaps_2025':int(s25) if s25 is not None else None,
                        'in_sis_2025':False,'moves_dest':dest,'team_2026':team26})
# a player can be flagged for 2 units; keep the highest-grade unit per player
best = {}
for m in missing:
    k=(m['key'],)
    if k not in best or m['grade_2024']>best[k]['grade_2024']: best[k]=m
missing = sorted(best.values(), key=lambda m:-m['grade_2024'])

# ---------------- SWEEP B: false-credit exposure (assumed-staying, ranked by impact) ----------------
# per 2026 team, top SIS contributors that are ASSUMED to stay (not in MOVES) -> unverified credit.
exposure = collections.defaultdict(list)
for unit in SIS_UNITS:
    for key, v in SIS[unit].items():
        if v['team'] in (None,'2T'): continue
        if key in MOVES: continue                       # move is accounted (in or out)
        if v['ps'] is None: continue
        exposure[v['team']].append({'name':v['name'],'unit':unit,'ps':round(v['ps'],1),'key':key})
for t in exposure: exposure[t] = sorted(exposure[t], key=lambda x:-x['ps'])[:5]

# ---------------- report ----------------
inj = [m for m in missing if m['grade_2025'] is not None and (m['snaps_2025'] or 0) < 250 and m['team_2026'].startswith(('OUT'))==False]
print(f"=== SWEEP A: MISSING 2024 STARTERS ABSENT FROM SIS-2025 (model can't credit) — {len(missing)} total ===")
print(f"{'player':22} {'pos':3} {'unit':9} {'24g/snaps':11} {'25g/snaps':11} {'2026 team':10}")
for m in missing[:40]:
    g25 = f"{m['grade_2025']}/{m['snaps_2025']}" if m['grade_2025'] is not None else "—(not in PFF25)"
    print(f"  {m['name']:20} {m['pos']:3} {m['unit']:9} {str(m['grade_2024'])+'/'+str(m['snaps_2024']):11} {g25:13} {m['team_2026']:10}")

print(f"\n=== SWEEP B: top ASSUMED-STAYING contributors per team (unverified credit, by SIS PS) ===")
for t in sorted(exposure):
    tops = exposure[t]
    print(f"  {t}: " + ", ".join(f"{x['name']}({x['unit'][:3]} {x['ps']})" for x in tops[:4]))

json.dump({'missing_contributors':missing,'assumed_staying_top':{t:exposure[t] for t in exposure},
           'params':{'grade_min':GRADE_MIN,'snap_min':SNAP_MIN,'note':'read-only currency audit; fabricates nothing'}},
          open(core.P('boom/defense_currency_audit.json'),'w'), indent=1)
print(f"\nwrote boom/defense_currency_audit.json | missing={len(missing)} | teams_with_exposure={len(exposure)}")
