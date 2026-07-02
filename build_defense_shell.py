#!/usr/bin/env python3
"""Per-defense SINGLE-HIGH vs TWO-HIGH coverage shell from FantasyPoints QB Coverage Matchup export.
single_high = DEF MAN% + DEF COVER3%  (Cover-1 man + Cover-3 zone = one deep safety)
two_high    = DEF COVER2% + DEF COVER4% + DEF COVER6%  (two deep safeties)
Writes boom/defense_shell.json {TEAM:{man,c2,c3,c4,c6,single_high,two_high,single_high_pctl}}.
Replaces the def_man_rate proxy for the deep-WR-vs-single-high flag.
"""
import csv, json, os, bisect
HERE = os.path.dirname(os.path.abspath(__file__)); DL = os.path.dirname(HERE); B = os.path.join(HERE, 'boom')
from boomutil import team as tm, num   # was: local FPMAP/tm/num (audit B3 dedup; boomutil.team == FPMAP, verified)

_SRC = f"{DL}/qbCoverageMatchupExport.csv"
if not os.path.exists(_SRC) and os.path.exists(os.path.join(B, 'defense_shell.json')):
    print("build_defense_shell: qbCoverageMatchupExport.csv absent -> keeping existing boom/defense_shell.json (static 2025 shells)")
    raise SystemExit(0)
rows = list(csv.reader(open(_SRC, encoding='utf-8-sig')))
hdr, data = rows[0], rows[1:]
# 0-indexed: OPP=6, DEF MAN%=12, DEF C2%=16, DEF C3%=20, DEF C4%=24, DEF C6%=28
by = {}
for r in data:
    if len(r) < 29: continue
    opp = tm(r[6]); man, c2, c3, c4, c6 = num(r[12]), num(r[16]), num(r[20]), num(r[24]), num(r[28])
    if opp and man is not None and opp not in by:
        by[opp] = {'man': man, 'c2': c2, 'c3': c3, 'c4': c4, 'c6': c6,
                   'single_high': round(man + (c3 or 0), 1), 'two_high': round((c2 or 0) + (c4 or 0) + (c6 or 0), 1)}
sh = sorted(v['single_high'] for v in by.values())
def pctl(x): return round(100 * bisect.bisect_left(sh, x) / max(1, len(sh) - 1))
for t, v in by.items(): v['single_high_pctl'] = pctl(v['single_high'])
# league-average coverage usage (consumers e.g. the coverage-specialist activation read this);
# previously added out-of-band, so a builder re-run dropped it -- now self-contained.
import statistics as _st
_LG = {f: round(_st.mean([v[f] for v in by.values() if v.get(f) is not None]), 1) for f in ('man','c2','c3','c4','c6','single_high','two_high')}
json.dump({**by, "_LEAGUE": _LG}, open(f"{B}/defense_shell.json", 'w'), ensure_ascii=False)

print(f"defenses captured: {len(by)} / 32")
miss = [t for t in ['ARI','ATL','BAL','BUF','CAR','CHI','CIN','CLE','DAL','DEN','DET','GB','HOU','IND','JAX','KC','LAC','LAR','LV','MIA','MIN','NE','NO','NYG','NYJ','PHI','PIT','SEA','SF','TB','TEN','WAS'] if t not in by]
print("missing:", miss)
print("MOST single-high (best for deep WRs):", [(t, v['single_high']) for t, v in sorted(by.items(), key=lambda x:-x[1]['single_high'])[:6]])
print("MOST two-high (brackets deep):", [(t, v['two_high']) for t, v in sorted(by.items(), key=lambda x:-x[1]['two_high'])[:6]])
print("DET check:", by.get('DET'))
