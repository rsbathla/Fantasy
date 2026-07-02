#!/usr/bin/env python3
"""Per-player MATCHUP-LEVER CALENDAR (single player, week-by-week) -> lever_calendar_<slug>.html.

Reads a player's already-built lever_cal / lever_sum / levers from dossier_data.json and renders the
2026 weekly calendar as a visual grid, color-coded by tier-weighted favorability. For every DARK week it
recomputes the opponent diagnostics (man-rate percentile, single-high percentile, coverage weakness) and
explains *why* it is dark -- and, crucially, whether a lever the player does NOT currently carry (e.g. a
QB vertical/deep lever) WOULD have lit it. This turns "why isn't DET highlighted?" into an auditable answer.

Usage:  python3 build_lever_calendar.py "Josh Allen"
"""
import json, os, sys, html, statistics

H = os.path.dirname(os.path.abspath(__file__))
def J(p):
    fp = os.path.join(H, p)
    return json.load(open(fp, encoding='utf-8')) if os.path.exists(fp) else {}

NORM = {'ARZ':'ARI','BLT':'BAL','CLV':'CLE','HST':'HOU','JAC':'JAX','LA':'LAR','OAK':'LV','SD':'LAC','WSH':'WAS','SL':'LAR','LVR':'LV'}
def nt(t):
    if not t: return t
    t = str(t).upper(); return NORM.get(t, t)

# ---- activator data (mirrors build_lever_count.py) ----
COORD = {nt(k): v for k, v in ((J('coordinator_scheme_2026.json') or {}).get('teams') or {}).items()}
DEF   = {nt(k): v for k, v in ((J('defense.json') or {}).get('teams') or {}).items()}
SHELL = {nt(k): v for k, v in (J('boom/defense_shell.json') or {}).items()}
ENV   = {nt(k): v.get('env_idx') for k, v in (J('boom/team_env.json') or {}).items() if isinstance(v, dict)}
SCHED = {nt(k): v for k, v in (J('boom/schedule2026.json') or {}).items()}

# ---- 2026 DC-scheme adjustment (EXACT mirror of build_lever_count.py's [dc-scheme] block, conf-gated)
# The calendar used to percentile-rank COORD man_rate_adj RAW while lever_count gates its regression
# lambda on `conf` (0.5 'regress-mean' else 0.3) and refines the regressed man rate toward the
# researched scheme_2026 lean -- so the man pctls / why-dark notes shown here drifted from the
# lever_cal scores lever_count actually computed for new-DC teams. Mirror the count's block verbatim.
SCHEME = J('scheme_2026.json') or {}
SCHDEF = {nt(k): (v.get('def') or {}) for k, v in SCHEME.items() if isinstance(v, dict)}
DCNEW = {t for t, v in COORD.items() if isinstance(v, dict) and v.get('dc_new')}
if os.environ.get('NOADJ'): DCNEW = set()
def _lam(t): return 0.5 if (COORD.get(t) or {}).get('conf') == 'regress-mean' else 0.3
def _ms(key):
    vs = [SHELL[t][key] for t in SHELL if isinstance(SHELL[t], dict) and SHELL[t].get(key) is not None]
    return (sum(vs)/len(vs), (statistics.pstdev(vs) if len(vs) > 1 else 0.0)) if vs else (None, None)
_M = {k: _ms(k) for k in ('single_high', 'two_high')}
for t in DCNEW:
    has = t in SCHDEF; d = SCHDEF.get(t) or {}
    _mr = (COORD.get(t) or {}).get('man_rate_adj'); _md = d.get('man', 0) if has else 0  # refine regressed man-rate toward researched lean
    if _mr is not None and _md != 0:
        COORD[t]['man_rate_adj'] = round(_mr + _md*4.0, 1)
    for key in ('single_high', 'two_high'):
        m, sd = _M[key]
        if m is None or not (isinstance(SHELL.get(t), dict) and SHELL[t].get(key) is not None): continue
        if has:
            dial = d.get(key, 0)
            if dial != 0:
                tgt = m + dial*(sd or 0.0); SHELL[t][key] = round(0.5*SHELL[t][key] + 0.5*tgt, 1)
            # dial==0 -> known-neutral, keep 2025
        else:
            SHELL[t][key] = round(m + (1-_lam(t))*(SHELL[t][key]-m), 1)

# percentile bases over the SCHEDULE'S teams -- the same basis lever_count feeds its pctls() -- so the
# displayed percentiles match the count exactly (COORD alone also carries the registry's stray 'ers' key).
_man_vals = sorted(v for v in ((COORD.get(t) or {}).get('man_rate_adj') for t in (SCHED or COORD)) if v is not None)
_sh_vals  = sorted(v for v in ((SHELL.get(t) or {}).get('single_high')  for t in (SCHED or SHELL)) if v is not None)
_env_vals = sorted(v for v in ENV.values() if v is not None)
def _pctl(xs, v):
    return None if (v is None or not xs) else sum(1 for x in xs if x <= v) / len(xs)
def manP(t): return _pctl(_man_vals, (COORD.get(t) or {}).get('man_rate_adj'))
def shP(t):  return _pctl(_sh_vals,  (SHELL.get(t) or {}).get('single_high'))
def envP(v): return _pctl(_env_vals, v)
def covWeak(t):
    v = (DEF.get(t) or {}).get('pass_cov_pctl'); return None if v is None else 1 - v / 100.0
def vertical_intensity(t):
    parts = [x for x in (shP(t), covWeak(t)) if x is not None]
    return sum(parts) / len(parts) if parts else None

def find_player(name):
    dd = J('dossier_data.json')
    for tm in dd.get('teams', []):
        for p in tm['players']:
            if (p.get('name') or '').lower() == name.lower():
                return p, nt(tm.get('team'))
    return None, None

def why_dark(pos, has_man_lever, opp):
    """Explain a dark (score 0) week and flag latent levers that WOULD have lit it."""
    bits = []
    mp = manP(opp)
    if has_man_lever and mp is not None and mp < 0.5:
        bits.append(f"zone-heavy D (man {round(mp*100)}th pctl) → man levers stay dark")
    vi = vertical_intensity(opp); sp = shP(opp)
    if vi is not None and vi >= 0.5 and pos == 'QB':
        bits.append(f"single-high heavy ({round(sp*100)}th pctl) → a QB vertical/deep lever WOULD light here (not currently modeled for QBs)")
    cw = covWeak(opp)
    if cw is not None and cw < 0.5:
        bits.append(f"above-average pass D (cov {round((1-cw)*100)}th pctl)")
    return "; ".join(bits) or "no modeled lever activates"

def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "Josh Allen"
    p, team = find_player(name)
    if not p:
        print(f"player not found: {name}"); return
    pos = p.get('pos'); cal = p.get('lever_cal') or []; summ = p.get('lever_sum') or {}
    levers = p.get('levers') or []
    has_man_lever = any('man' in (lv.get('t','').lower()) for lv in levers)

    # build week cells
    cells = []
    for c in cal:
        wk = c['wk']; opp = c['opp']; score = c['score']; active = c.get('active') or []
        home = c.get('home')
        bye = (opp == 'BYE')
        klass = 'bye' if bye else ('smash' if score >= 1.5 else ('warm' if score > 0 else 'dark'))
        loc = '' if bye else ('vs' if home else '@')
        acts = ', '.join(a['type'].replace('_', ' ') for a in active) if active else ''
        note = '' if (bye or score > 0) else why_dark(pos, has_man_lever, opp)
        po = wk in (15, 16, 17)
        cells.append(dict(wk=wk, opp=opp, loc=loc, score=score, klass=klass, acts=acts, note=note, po=po, bye=bye,
                          manp=(None if bye else manP(opp)), n=c.get('n', 0)))

    lever_rows = ''.join(
        f"<li><span class='tier {lv.get('c','tendency')}'>{html.escape(lv.get('c','tendency'))}</span> {html.escape(lv['t'])}</li>"
        for lv in levers) or "<li>(no activatable levers)</li>"

    def cell_html(c):
        if c['bye']:
            return f"<div class='cell bye'><div class='wk'>W{c['wk']}</div><div class='opp'>BYE</div></div>"
        manln = f"man {round(c['manp']*100)}%ile" if c['manp'] is not None else ""
        actln = f"<div class='acts'>{html.escape(c['acts'])}</div>" if c['acts'] else \
                (f"<div class='note'>{html.escape(c['note'])}</div>" if c['note'] else "")
        star = " ★" if c['po'] else ""
        return (f"<div class='cell {c['klass']}{ ' po' if c['po'] else '' }'>"
                f"<div class='wk'>W{c['wk']}{star}</div>"
                f"<div class='opp'>{c['loc']} {c['opp']}</div>"
                f"<div class='score'>{c['score']:.2f}</div>"
                f"<div class='manln'>{manln}</div>{actln}</div>")

    grid = ''.join(cell_html(c) for c in cells)
    smash = summ.get('smash_weeks', [])

    # dynamic activator note (what opponent traits this player's levers key on)
    fam = set()
    for lv in levers:
        s = lv['t'].lower()
        if 'vertical' in s or 'deep' in s or 'big-play' in s: fam.add('single-high / soft-deep shells (deep ball)')
        elif 'man' in s: fam.add('man-coverage rate')
        if 'shootout' in s or 'high-total' in s: fam.add('opponent implied game total (shootout)')
        if 'red-zone' in s or 'red zone' in s: fam.add('red-zone-soft defenses')
        if 'slot' in s or 'nickel' in s: fam.add('weak nickel/slot')
    activator_note = '; '.join(sorted(fam)) if fam else 'various opponent traits'

    # dynamic spotlight on the weeks the user asked about (DET, LAR) — read straight from the calendar
    by_opp = {c['opp']: c for c in cal}
    spot = ''
    for T in ('DET', 'LAR'):
        c = by_opp.get(T)
        if not c:
            spot += f"<div class=callout><b class=a>{T}</b> is not on the 2026 schedule.</div>"; continue
        acts = ', '.join(a['type'].replace('_', ' ') for a in c.get('active', []))
        env = ENV.get(T)
        state = 'now lights up' if c['score'] > 0 else 'stays dark'
        detail = (f"active levers: <b>{acts}</b>" if acts else "no lever activates")
        envtxt = f" · opponent implied-total env {env} ({round(envP(env)*100)}th pctl)" if env is not None else ""
        spot += (f"<div class=callout>W{c['wk']} vs <b class=a>{T}</b> — score <b>{c['score']:.2f}</b>, {state}. {detail}.{envtxt}</div>")
    doc = f"""<!doctype html><html><head><meta charset=utf-8>
<title>{html.escape(name)} — 2026 Matchup-Lever Calendar</title><style>
:root{{--bg:#0b0f17;--card:#121a29;--line:#233247;--ink:#eef2f8;--ink2:#aab8cc;--ink3:#7286a0;--accent:#5b9dff;--good:#5fd08a;--warm:#e6b34d;--dark:#37445c}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.55 -apple-system,Segoe UI,Roboto,Arial,sans-serif}}
.wrap{{max-width:1080px;margin:0 auto;padding:22px}}
h1{{font-size:22px;margin:0 0 2px}}.sub{{color:var(--ink3);margin-bottom:16px}}
.panel{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin-bottom:16px}}
.panel h2{{font-size:13px;text-transform:uppercase;letter-spacing:.6px;color:var(--ink2);margin:0 0 8px}}
ul.lev{{margin:0;padding-left:18px}}ul.lev li{{margin:3px 0}}
.tier{{display:inline-block;font-size:10px;text-transform:uppercase;letter-spacing:.5px;padding:1px 6px;border-radius:5px;margin-right:6px;vertical-align:middle}}
.tier.solid{{background:rgba(95,208,138,.18);color:var(--good);border:1px solid rgba(95,208,138,.4)}}
.tier.tendency{{background:rgba(230,179,77,.15);color:var(--warm);border:1px solid rgba(230,179,77,.35)}}
.stats{{display:flex;gap:22px;flex-wrap:wrap}}.stat{{}}.stat b{{font-size:20px}}.stat span{{color:var(--ink3);font-size:12px;display:block}}
.grid{{display:grid;grid-template-columns:repeat(6,1fr);gap:9px}}
.cell{{border:1px solid var(--line);border-radius:10px;padding:9px 10px;min-height:96px;position:relative;background:#0e1523}}
.cell .wk{{font-size:11px;color:var(--ink3);font-weight:700}}
.cell .opp{{font-size:15px;font-weight:700;margin:1px 0 3px}}
.cell .score{{font-size:18px;font-variant-numeric:tabular-nums}}
.cell .manln{{font-size:10.5px;color:var(--ink3)}}
.cell .acts{{font-size:10.5px;color:var(--good);margin-top:4px;line-height:1.3}}
.cell .note{{font-size:10px;color:var(--ink3);margin-top:4px;line-height:1.3;font-style:italic}}
.cell.smash{{background:linear-gradient(180deg,rgba(95,208,138,.16),rgba(95,208,138,.05));border-color:rgba(95,208,138,.55)}}
.cell.smash .score{{color:var(--good)}}
.cell.warm{{background:linear-gradient(180deg,rgba(230,179,77,.10),rgba(230,179,77,.03));border-color:rgba(230,179,77,.35)}}
.cell.dark .score{{color:var(--dark)}}
.cell.bye{{opacity:.45;min-height:96px}}
.cell.po{{box-shadow:inset 0 0 0 2px rgba(91,157,255,.5)}}
.legend{{display:flex;gap:16px;flex-wrap:wrap;color:var(--ink3);font-size:12px;margin:12px 0}}
.dot{{display:inline-block;width:11px;height:11px;border-radius:3px;vertical-align:middle;margin-right:5px}}
.callout{{border-left:3px solid var(--accent);padding:4px 0 4px 12px;color:var(--ink2);margin:8px 0}}
b.g{{color:var(--good)}}b.w{{color:var(--warm)}}b.a{{color:var(--accent)}}
</style></head><body><div class=wrap>
<h1>{html.escape(name)} <span style="color:var(--ink3);font-weight:400">— {pos}, {team}</span></h1>
<div class=sub>2026 matchup-lever calendar. Each week is scored only when an <b>opponent's defensive trait turns one of his levers ON</b> (tier-weighted). Smash week = score ≥ 1.5. ★ = fantasy playoff week (15–17).</div>

<div class=panel><h2>His ceiling levers ({len(levers)})</h2><ul class=lev>{lever_rows}</ul>
<div class=callout>Activates on: <b class=a>{activator_note}</b>. A week lights up when the opponent's defense (or game environment) turns one of these on.</div></div>

<div class=panel><h2>Season summary</h2><div class=stats>
<div class=stat><b>{summ.get('mean',0)}</b><span>season mean</span></div>
<div class=stat><b>{summ.get('peak',0)}</b><span>peak week</span></div>
<div class=stat><b class=g>{summ.get('playoff_mean',0)}</b><span>playoff (15–17) mean</span></div>
<div class=stat><b>{len(smash)}</b><span>smash weeks: {', '.join('W'+str(w) for w in smash) or '—'}</span></div>
</div></div>

<div class=legend>
<span><span class=dot style="background:var(--good)"></span>smash (≥1.5)</span>
<span><span class=dot style="background:var(--warm)"></span>partial (0–1.5)</span>
<span><span class=dot style="background:var(--dark)"></span>dark (0 — no lever fires)</span>
<span><span class=dot style="box-shadow:inset 0 0 0 2px rgba(91,157,255,.6)"></span>playoff week</span>
</div>
<div class=grid>{grid}</div>

<div class=panel style="margin-top:16px"><h2>DET (W2) &amp; LAR (W5) — spotlight</h2>
{spot}
<div class=callout style="border-color:var(--good)">Both now register after two lever upgrades: a <b>QB vertical/deep lever</b> (his 2yr deep-throw rate is 76th-pctl among QBs) that lights single-high-heavy defenses like <b class=a>DET</b>, and a <b>game-total layer</b> that credits high implied-total opponents (<b class=a>LAR</b> is the league's #1 environment) regardless of their coverage scheme. Man-coverage rate still drives his biggest smashes (BAL, MIN, KC).</div>
</div>
</div></body></html>"""
    slug = ''.join(ch for ch in name.lower().replace(' ', '_') if ch.isalnum() or ch == '_')
    out = os.path.join(H, f'lever_calendar_{slug}.html')
    open(out, 'w', encoding='utf-8').write(doc)
    print(f"wrote {out} ({len(doc)//1024} KB) — {len(levers)} levers, smash weeks {smash}")

if __name__ == '__main__':
    main()
