#!/usr/bin/env python3
"""Wire the VALIDATED rookie signal into a usable prior.

Calibrates a boom prior from the backtest relationship (2024 college ceiling -> 2025 NFL
rookie boom), shrinks the slope (small-sample), clamps to a sane range, and prices every
2026 draft-eligible rookie by their 2025 college ceiling. Writes boom/rookie_prior.json and
merges boom_prior into rookie_college_profile.json. Consume in boom_lib.reg_base as the base
ceiling rate for players with no 2-year NFL history (the rookie fallback)."""
import core, json
from build_rookie_profiles import build_season

SHRINK = 0.5          # small-sample slope shrinkage (matches boom_lib SHRINK_LAMBDA philosophy)
CLAMP = (0.04, 0.25)  # plausible single-week boom-rate bounds

def fit(rows):
    n = len(rows); mx = sum(r[0] for r in rows) / n; my = sum(r[1] for r in rows) / n
    var = sum((r[0] - mx) ** 2 for r in rows)
    b = (sum((r[0] - mx) * (r[1] - my) for r in rows) / var) if var else 0.0
    return mx, my, b

def main():
    b2 = json.load(open(core.P('boom/base2yr.json'), encoding='utf-8'))
    rookies = {k: v for k, v in b2.items() if (not v.get('g24')) and (v.get('g25') or 0) >= 4}
    p24 = build_season('2024')
    rows = [(p24[k]['ceiling_pctl'], (rookies[k].get('b25') or 0) / rookies[k]['g25'])
            for k in p24 if k in rookies and p24[k].get('ceiling_pctl') is not None and p24[k]['pos'] in ('WR', 'TE', 'RB')]
    mx, my, raw_b = fit(rows); b = raw_b * SHRINK
    def prior(pctl): return round(max(CLAMP[0], min(CLAMP[1], my + b * (pctl - mx))), 3)

    prof = json.load(open(core.P('boom/rookie_college_profile.json'), encoding='utf-8'))
    out = {}
    for k, v in prof['players'].items():
        if not v.get('draft_eligible_2026'): continue
        c = v.get('ceiling_pctl_2025')
        if c is None: continue
        v['boom_prior'] = prior(c)
        out[k] = {'name': v['name'], 'pos': v['pos'], 'college': v['college'],
                  'ceiling_pctl_2025': c, 'board_adp': v.get('board_adp'), 'boom_prior': v['boom_prior']}
    prof['prior_calibration'] = {'basis': f'2024 college ceiling -> 2025 NFL rookie boom (n={len(rows)})',
                                 'mean_ceiling': round(mx, 1), 'mean_boom': round(my, 3),
                                 'slope_per_pctl_shrunk': round(b, 5), 'shrink': SHRINK, 'clamp': list(CLAMP)}
    core.safe_json_dump(prof, core.P('boom/rookie_college_profile.json'))
    core.safe_json_dump({'note': 'validated rookie boom prior for 2026 draft-eligible rookies; '
                                 'consume in boom_lib.reg_base as base ceiling rate when a player has no 2-yr NFL history',
                         'calibration': prof['prior_calibration'], 'n': len(out), 'priors': out},
                        core.P('boom/rookie_prior.json'))
    print(f"rookie_prior.json: {len(out)} draft-eligible 2026 rookies priced")
    print("  calibration: boom = %.3f + %.5f*(ceiling - %.1f); shrink %.1f; clamp %s" % (my, b, mx, SHRINK, CLAMP))
    print("  top by prior:")
    for r in sorted(out.values(), key=lambda r: -r['boom_prior'])[:12]:
        print(f"   {r['name']:24} {r['pos']:3} ceiling25={str(r['ceiling_pctl_2025']):5} adp={str(r['board_adp']):6} -> boom_prior={r['boom_prior']}")

if __name__ == '__main__':
    main()
