#!/usr/bin/env python3
"""Per-player CEILING-BY-SITUATION quantifier. Grounds 'this player spikes vs X' in real data:
  - base boom rate = each player's historical share of games with actual >= 1.5x projection (boom_proj.csv)
  - matchup swing  = measured soft-vs-tough boom rates by position (defense_variance.py)
  - favorable conditions = the scheme/funnel/strength reads from build_splits (player_splits.json)
Produces a plain-language line + numbers per player. -> player_boom.json"""
import csv, json, re, os
HERE = os.path.dirname(os.path.abspath(__file__)); DL = os.path.dirname(HERE)
def fn(n):
    n = str(n).strip().lower(); n = re.sub(r'\s+(jr|sr|ii|iii|iv|v)\.?$', '', n)
    return n.replace('.', '').replace("'", "").replace('-', ' ')

# 1) per-player historical base boom rate + position baseline (boom = actual >= 1.5x proj)
games = {}; posg = {}
for r in csv.DictReader(open(f"{DL}/dfs_review/out/boom_proj.csv", encoding='utf-8')):
    try: proj = float(r['proj']); act = float(r['actual'])
    except Exception: continue
    if proj <= 4: continue
    b = 1 if act >= 1.5 * proj else 0
    games.setdefault(fn(r['name']), []).append(b)
    posg.setdefault((r.get('pos') or '').upper(), []).append(b)
base = {k: sum(v) / len(v) for k, v in games.items() if len(v) >= 4}
posbase = {p: (sum(v) / len(v) if v else 0.16) for p, v in posg.items()}

# 2) measured soft-vs-tough boom rate by position (defense_variance.py: actual >= 1.5x proj)
SWING = {'QB': (0.06, 0.19), 'RB': (0.14, 0.25), 'WR': (0.13, 0.29), 'TE': (0.08, 0.33)}  # (tough, soft)

splits = json.load(open(f"{HERE}/player_splits.json", encoding='utf-8')) if os.path.exists(f"{HERE}/player_splits.json") else {}

def unit(pos): return "pass defenses" if pos in ('WR', 'TE', 'QB') else "run defenses"

OUT = {}
for r in csv.DictReader(open(f"{HERE}/draft_board_signals.csv", encoding='utf-8')):
    k = fn(r['name']); pos = (r.get('pos') or '').upper()
    if pos not in SWING: continue
    hist = k in base
    b = base.get(k, posbase.get(pos, 0.16))
    pov = max(0.04, posbase.get(pos, 0.18))
    toughp, softp = SWING[pos]
    fav = min(0.66, b * softp / pov); tuf = max(0.01, b * toughp / pov)
    sp = splits.get(k, {}); prof = sp.get('profile', []); lean = sp.get('man_lean')
    # build the plain-language condition phrase
    cond = "soft / funnel " + unit(pos)
    extra = []
    if lean == 'man': extra.append("man-heavy looks (separation edge)")
    elif lean == 'zone': extra.append("zone-heavy looks")
    if pos == 'RB' and 'big-play' in prof: extra.append("light boxes")
    line = ("Spikes vs " + cond + (" + " + " + ".join(extra) if extra else "")
            + ": ~%d%% boom rate there vs ~%d%% baseline (~%d%% vs tough), a %.1fx matchup swing for %ss."
            % (round(fav * 100), round(b * 100), round(tuf * 100), softp / toughp, pos))
    OUT[k] = {'pos': pos, 'base': round(b * 100), 'fav': round(fav * 100), 'tuf': round(tuf * 100),
              'lift': round((fav - b) * 100), 'hist': hist, 'profile': prof, 'lean': lean, 'line': line,
              'unit': unit(pos)}
json.dump(OUT, open(f"{HERE}/player_boom.json", 'w', encoding='utf-8'), ensure_ascii=False)
print("wrote player_boom.json:", len(OUT), "players |", sum(1 for v in OUT.values() if v['hist']), "with real game history")
for nm in ['Puka Nacua', 'Tee Higgins', 'Jonathan Taylor', 'Trey McBride', 'Alec Pierce', 'Josh Allen']:
    v = OUT.get(fn(nm))
    if v: print(f"  {nm}: {v['line']}")
