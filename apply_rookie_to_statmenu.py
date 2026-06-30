#!/usr/bin/env python3
"""Merge the validated rookie college-ceiling prior into the live stat menu.

For each 2026 draft-eligible rookie (boom/rookie_prior.json) present in statmenu, BLEND the
college-calibrated boom prior into base_blended (which for true rookies is pure projection).
Preserves the original as base_blended_preboost (fully reversible + idempotent on re-run) and
sets rookie_boom_prior for boom_lib.reg_base. Run after boom_foundation + build_rookie_prior,
before the flag builders.
"""
import core, json

W = 0.15  # DATA-DRIVEN: woptimize_rookie.py grid-search vs 2025 ADP baseline (optimum ~0.15; ADP dominates, college marginal)

def main():
    sm = json.load(open(core.P('boom/statmenu.json'), encoding='utf-8'))
    pr = json.load(open(core.P('boom/rookie_prior.json'), encoding='utf-8'))['priors']
    applied = []
    for k, p in pr.items():
        v = sm.get(k)
        if not v: continue
        cp = p.get('boom_prior')
        if cp is None: continue
        base0 = v.get('base_blended_preboost', v.get('base_blended'))  # idempotent: blend from the ORIGINAL
        new = round(cp, 3) if base0 is None else round((1 - W) * float(base0) + W * float(cp), 3)
        v['base_blended_preboost'] = base0
        v['college_boom_prior'] = cp
        v['rookie_boom_prior'] = cp
        v['base_blended'] = new
        v['rookie_boost'] = True
        applied.append((v.get('name') or k, v.get('pos'), base0, cp, new))
    core.safe_json_dump(sm, core.P('boom/statmenu.json'))
    print(f"applied rookie prior to {len(applied)} rookies (W={W} college weight)")
    print(f"  {'rookie':22} {'pos':3} {'proj':>6} {'college':>7} {'blended':>7}")
    for nm, pos, b0, cp, new in sorted(applied, key=lambda r: -(r[4] or 0))[:14]:
        print(f"  {nm:22} {pos or '':3} {str(b0):>6} {str(cp):>7} {str(new):>7}")
    return applied

if __name__ == '__main__':
    main()
