#!/usr/bin/env python3
"""Backtest the rookie college-ceiling signal: does 2024 COLLEGE Value predict 2025 NFL
rookie boom? Outcome = base2yr.json (g24==0 & g25>0 -> 2025 rookie; boom rate = b25/g25).
Predictor = 2024 college ceiling percentile (build_rookie_profiles). Pure-python stats."""
import core, json
from build_rookie_profiles import build_season

MIN_G25 = 4  # require >=4 NFL games in 2025 so the boom rate isn't 1-game noise

def spearman(xs, ys):
    def rank(a):
        order = sorted(range(len(a)), key=lambda i: a[i]); r = [0.0] * len(a); i = 0
        while i < len(a):
            j = i
            while j < len(a) and a[order[j]] == a[order[i]]: j += 1
            for k in range(i, j): r[order[k]] = (i + j - 1) / 2.0
            i = j
        return r
    rx, ry = rank(xs), rank(ys); n = len(xs)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((rx[i] - mx) * (ry[i] - my) for i in range(n))
    den = (sum((rx[i] - mx) ** 2 for i in range(n)) * sum((ry[i] - my) ** 2 for i in range(n))) ** 0.5
    return num / den if den else 0.0

def auc(scores, labels):
    pos = [s for s, l in zip(scores, labels) if l]; neg = [s for s, l in zip(scores, labels) if not l]
    if not pos or not neg: return None
    wins = sum((1 if a > b else 0.5 if a == b else 0) for a in pos for b in neg)
    return round(wins / (len(pos) * len(neg)), 3)

def collect(profile, rookies):
    out = []
    for k, v in profile.items():
        if v.get('ceiling_pctl') is None: continue
        r = rookies.get(k)
        if not r: continue
        g25 = r.get('g25') or 0
        if g25 < MIN_G25: continue
        out.append((v['name'], v['pos'], v['ceiling_pctl'], (r.get('b25') or 0) / g25))
    return out

def report(name, rows):
    if len(rows) < 6:
        print(f"  {name:16}: n={len(rows)} (too small for stats)")
        return {'n': len(rows), 'note': 'too small'}
    xs = [r[2] for r in rows]; ys = [r[3] for r in rows]
    rho = round(spearman(xs, ys), 3)
    med = sorted(ys)[len(ys) // 2]
    a = auc(xs, [y > med for y in ys])
    srt = sorted(rows, key=lambda r: r[2]); n = len(srt); t = n // 3 or 1
    bot = sum(r[3] for r in srt[:t]) / t; top = sum(r[3] for r in srt[-t:]) / t
    lift = round(top / bot, 2) if bot > 0 else None
    print(f"  {name:16}: n={n:3} | spearman={rho:+.3f} | AUC={a} | top-tertile boom={top:.3f} vs bottom={bot:.3f} (lift {lift}x)")
    return {'n': n, 'spearman': rho, 'auc': a, 'top_tertile_boom': round(top, 3), 'bottom_tertile_boom': round(bot, 3), 'lift': lift}

def main():
    b = json.load(open(core.P('boom/base2yr.json'), encoding='utf-8'))
    rookies = {k: v for k, v in b.items() if (not v.get('g24')) and (v.get('g25') or 0) > 0}
    rows = collect(build_season('2024'), rookies)
    skill = [r for r in rows if r[1] in ('WR', 'TE', 'RB')]
    qb = [r for r in rows if r[1] == 'QB']
    print(f"2025 NFL rookies (g24==0,g25>0): {len(rookies)} | with 2024-college ceiling + >={MIN_G25}g NFL: {len(rows)}\n")
    res = {'min_g25': MIN_G25, 'n_rookies': len(rookies)}
    res['skill'] = report('SKILL WR/TE/RB', skill)
    res['qb'] = report('QB', qb)
    res['all'] = report('ALL', rows)
    srt = sorted(skill, key=lambda r: r[2], reverse=True)
    res['top5'] = [{'name': r[0], 'pos': r[1], 'ceiling': r[2], 'nfl_boom': round(r[3], 3)} for r in srt[:5]]
    res['bottom5'] = [{'name': r[0], 'pos': r[1], 'ceiling': r[2], 'nfl_boom': round(r[3], 3)} for r in srt[-5:]]
    sk = res['skill']
    res['verdict'] = 'VALIDATES' if (sk.get('spearman') or 0) >= 0.15 and (sk.get('lift') or 0) > 1.2 else 'WEAK/INCONCLUSIVE'
    core.safe_json_dump(res, core.P('boom/rookie_backtest.json'))
    print(f"\nVERDICT: {res['verdict']}")
    print("  highest college-ceiling rookies:", [f"{r['name']}({r['nfl_boom']})" for r in res['top5']])
    print("  lowest  college-ceiling rookies:", [f"{r['name']}({r['nfl_boom']})" for r in res['bottom5']])
    return res

if __name__ == '__main__':
    main()
