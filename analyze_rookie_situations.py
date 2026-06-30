#!/usr/bin/env python3
"""Find the specific situations that let rookies boom.

Pools 2025 ROOKIE-GAMES (gamelog.json) tagged with game conditions (matchup softness, venue,
weather, the model's own projection) and the player's season situation (position, 2025 preseason
ADP tier, usage/role from statmenu, college ceiling). Reports boom rate per situation vs the
rookie base rate (lift), so we can see which conditions actually produce rookie booms.
"""
import core, csv, json, collections

def fnum(x):
    try: return float(x)
    except (TypeError, ValueError): return None

b2 = json.load(open(core.P('boom/base2yr.json'), encoding='utf-8'))
rookies = {k for k, v in b2.items() if (not v.get('g24')) and (v.get('g25') or 0) > 0}
gl = json.load(open(core.P('boom/gamelog.json'), encoding='utf-8'))
sm = json.load(open(core.P('boom/statmenu.json'), encoding='utf-8'))
adp = {core.fn(r['name']): float(r['adp']) for r in csv.DictReader(open(core.P('sis_value/fp_adp_2025.csv'), encoding='utf-8'))}
prof = json.load(open(core.P('boom/rookie_college_profile.json'), encoding='utf-8'))['players']

# build rookie-game rows
games = []
for k in rookies:
    if k not in gl or not isinstance(gl[k], list): continue
    s = sm.get(k, {}); pos = s.get('pos') or (prof.get(k, {}) or {}).get('pos')
    usage = s.get('usage') or {}
    tgtsh = usage.get('tgt_share'); carsh = usage.get('carry_share')
    a = adp.get(k); ceil = (prof.get(k, {}) or {}).get('ceiling_pctl_2025') or (prof.get(k, {}) or {}).get('ceiling_pctl_2024')
    for g in gl[k]:
        if g.get('boom') is None: continue
        games.append({'k': k, 'pos': pos, 'boom': int(g['boom']),
                      'opp_passp': fnum(g.get('opp_passp')), 'opp_runp': fnum(g.get('opp_runp')),
                      'home': g.get('home'), 'dome': g.get('dome'),
                      'wind': fnum(g.get('wind')), 'precip': fnum(g.get('precip')), 'proj': fnum(g.get('proj')),
                      'adp': a, 'tgt_share': tgtsh, 'carry_share': carsh, 'ceil': ceil})

N = len(games); base = sum(g['boom'] for g in games) / N
nplayers = len(set(g['k'] for g in games))
print(f"rookie-games: {N} across {nplayers} rookies | base boom rate = {base:.3f}\n")

def rate(rows):
    n = len(rows); return (sum(r['boom'] for r in rows) / n, n) if n else (0.0, 0)

def show(title, groups):
    print(title)
    for label, rows in groups:
        r, n = rate(rows)
        if n < 8: 
            print(f"   {label:30} boom={r:.3f}  n={n}  (small)"); continue
        print(f"   {label:30} boom={r:.3f}  lift={r/base:4.2f}x  n={n}")
    print()

def tertiles(rows, key):
    vals = sorted(r[key] for r in rows if r.get(key) is not None)
    if len(vals) < 9: return None
    return vals[len(vals)//3], vals[2*len(vals)//3]

out = {'n_games': N, 'n_rookies': nplayers, 'base_boom': round(base, 3), 'situations': {}}

# --- matchup: opponent pass defense (WR/TE/QB) and run defense (RB) ---
passgames = [g for g in games if g['pos'] in ('WR', 'TE', 'QB') and g['opp_passp'] is not None]
t = tertiles(passgames, 'opp_passp')
if t:
    show("PASS-CATCHER vs opponent pass-defense rating (opp_passp):", [
        (f"soft (<= {t[0]:.0f})", [g for g in passgames if g['opp_passp'] <= t[0]]),
        (f"mid", [g for g in passgames if t[0] < g['opp_passp'] <= t[1]]),
        (f"tough (> {t[1]:.0f})", [g for g in passgames if g['opp_passp'] > t[1]]),
    ])
rbgames = [g for g in games if g['pos'] == 'RB' and g['opp_runp'] is not None]
t = tertiles(rbgames, 'opp_runp')
if t:
    show("RB vs opponent run-defense rating (opp_runp):", [
        (f"soft (<= {t[0]:.0f})", [g for g in rbgames if g['opp_runp'] <= t[0]]),
        (f"mid", [g for g in rbgames if t[0] < g['opp_runp'] <= t[1]]),
        (f"tough (> {t[1]:.0f})", [g for g in rbgames if g['opp_runp'] > t[1]]),
    ])
# --- venue / weather ---
show("VENUE & WEATHER:", [
    ("home", [g for g in games if g['home'] is True]),
    ("away", [g for g in games if g['home'] is False]),
    ("dome", [g for g in games if g['dome'] is True]),
    ("outdoor", [g for g in games if g['dome'] is False]),
    ("windy (>=15mph)", [g for g in games if (g['wind'] or 0) >= 15]),
    ("wet (precip>0)", [g for g in games if (g['precip'] or 0) > 0]),
    ("clean (no wind/rain)", [g for g in games if (g['wind'] or 0) < 15 and (g['precip'] or 0) == 0]),
])
# --- the model's own pre-game projection ---
t = tertiles(games, 'proj')
if t:
    show("MODEL PRE-GAME PROJECTION tertile:", [
        (f"low (<= {t[0]:.1f})", [g for g in games if g['proj'] is not None and g['proj'] <= t[0]]),
        ("mid", [g for g in games if g['proj'] is not None and t[0] < g['proj'] <= t[1]]),
        (f"high (> {t[1]:.1f})", [g for g in games if g['proj'] is not None and g['proj'] > t[1]]),
    ])
# --- position ---
show("POSITION:", [(p, [g for g in games if g['pos'] == p]) for p in ('RB', 'WR', 'TE', 'QB')])
# --- draft capital (2025 ADP tier) ---
show("DRAFT CAPITAL (2025 best-ball ADP tier):", [
    ("early (ADP<=60)", [g for g in games if g['adp'] is not None and g['adp'] <= 60]),
    ("mid (61-120)", [g for g in games if g['adp'] is not None and 60 < g['adp'] <= 120]),
    ("late (121+)", [g for g in games if g['adp'] is not None and g['adp'] > 120]),
    ("undrafted (no ADP)", [g for g in games if g['adp'] is None]),
])
# --- usage / role ---
wrte = [g for g in games if g['pos'] in ('WR', 'TE') and g['tgt_share'] is not None]
t = tertiles(wrte, 'tgt_share')
if t:
    show("WR/TE TARGET SHARE tertile (role):", [
        (f"low (<= {t[0]:.2f})", [g for g in wrte if g['tgt_share'] <= t[0]]),
        ("mid", [g for g in wrte if t[0] < g['tgt_share'] <= t[1]]),
        (f"high (> {t[1]:.2f})", [g for g in wrte if g['tgt_share'] > t[1]]),
    ])
rbu = [g for g in games if g['pos'] == 'RB' and g['carry_share'] is not None]
t = tertiles(rbu, 'carry_share')
if t:
    show("RB CARRY SHARE tertile (workload):", [
        (f"low (<= {t[0]:.2f})", [g for g in rbu if g['carry_share'] <= t[0]]),
        ("mid", [g for g in rbu if t[0] < g['carry_share'] <= t[1]]),
        (f"high (> {t[1]:.2f})", [g for g in rbu if g['carry_share'] > t[1]]),
    ])
core.safe_json_dump(out, core.P('boom/rookie_situations.json'))
print("(non-independence caveat: games repeat per player; treat lifts as directional)")
