#!/usr/bin/env python3
"""flagkit/rb.py — RB position semantics (ports build_flags_RB.py onto flagkit.engine).

ONLY the RB-specific logic lives here: the base seed, the skill-flag cascade (16 primary
flags + chart2/SIS/ENV extras + safety-net while-loop + fallback), the per-week activation
(condition tuples + PACE + SCRIPT inline logic), the one-line thesis, and the empirical
summary. Every piece of shared scaffolding (player loop, BYE, grading, record/week
assembly, write) is in flagkit/engine.py and is NOT duplicated.

The logic below is transcribed verbatim from build_flags_RB.py so the output is
byte-for-byte identical (verified by diffing boom/flags_RB.json).

RB uses the FUNCTIONAL `activate` style (not static `conditions`) because the legacy
per-week loop appends PACE/SCRIPT flags inline after the condition sweep, and because a
lit condition with mult==1.0 contributes to `flags`/`lit` but NOT to grading. To reproduce
both behaviours exactly, activate returns a `lit` list and a parallel `mults` list of the
SAME length (1.0 placeholders where the legacy skipped the multiplier — a no-op in
boom_lib.prob), so engine's `len(mults)` lit-count equals the legacy `len(lit_f)` while the
grade is unchanged.
"""
import json
import os
from boom_lib import reg_base, prob, label, cap

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repo root (flagkit/ is one level down)
POS = 'RB'

_TENV_PATH = os.path.join(HERE, 'boom', 'team_env.json')
TENV = json.load(open(_TENV_PATH))


# -- helpers (verbatim from legacy) ----------------------------------------------
def sg(d, *keys, default=0):
    v = d
    for k in keys:
        if not isinstance(v, dict):
            return default
        v = v.get(k)
        if v is None:
            return default
    return v if v is not None else default


def di(opp_def, field, default=50):
    val = opp_def.get(field)
    return val if val is not None else default


# -- per-week opponent inputs the conditions read --------------------------------
def opp_data(opp):
    # condition fns read defense2026 fields (tiers/runp/covp/manp). bundled here.
    return de_lookup(opp)


# de is loaded once at module import via the engine's load(); but rb.py needs it for
# opp_data. We resolve it lazily from defense2026.json to avoid coupling to engine state.
_DE = json.load(open(os.path.join(HERE, 'boom', 'defense2026.json')))


def de_lookup(opp):
    return _DE.get(opp, {})


# -- regularized base (with the RB seed fallback) --------------------------------
def base(v, posbase, prof):
    POS_BASE = posbase['RB']
    rb = reg_base(v, posbase)
    if rb is not None and (v.get('n_games') or 0) >= 4:
        return rb, True
    cp = sg(v, 'fus', 'ceiling_pctl') or 50
    b = POS_BASE * (0.75 + 0.50 * cp / 100.0)
    return round(cap(b, 0.06, 0.45), 3), False


# -- empirical summary string ----------------------------------------------------
def empirical(key, gl, bd):
    games = gl.get(key, [])
    active = [g for g in games if (g.get('proj') or 0) >= 8]
    if not active:
        return "insufficient history (<4 active games)"
    n = len(active)
    bo = [g for g in active if g.get('boom')]
    nb = len(bo)
    if nb == 0:
        return "0 ceiling games in {} active (proj>=8); no clustering signal".format(n)
    home_b = sum(1 for g in bo if g.get('home'))
    dome_b = sum(1 for g in bo if g.get('dome'))
    soft_run = sum(1 for g in bo if (g.get('opp_runp') or 100) <= 35)
    soft_pas = sum(1 for g in bo if (g.get('opp_passp') or 100) <= 35)
    hard_run = sum(1 for g in bo if (g.get('opp_runp') or 0) >= 65)
    parts = ["{}/{} ceiling games".format(nb, n)]
    if home_b:
        parts.append("{}/{} at home{}".format(home_b, nb, " (ALL)" if home_b == nb else ""))
    if dome_b:
        parts.append("{}/{} in dome{}".format(dome_b, nb, " (ALL)" if dome_b == nb else ""))
    if soft_run:
        parts.append("{}/{} vs soft run-D (opp_runp<=35)".format(soft_run, nb))
    if soft_pas:
        parts.append("{}/{} vs soft pass-D (passp<=35)".format(soft_pas, nb))
    if hard_run:
        parts.append("{}/{} vs tough run-D (runp>=65)".format(hard_run, nb))
    return "; ".join(parts)


# -- profile (position-specific feature extraction): builds sf, cond, line, meta --
# Transcribed verbatim from legacy build_player(). The engine calls context(k,v,gl,bd)
# once per player; we stash the computed skill_flags / cond list / line / meta in the
# returned profile so skill_flags(), line(), and activate() can read them.
def context(k, v, gl, bd):
    posbase = bd['posbase']
    POS_BASE = posbase['RB']

    u = v.get('usage') or {}
    fus = v.get('fus') or {}
    sis = v.get('sis') or {}
    adv2 = v.get('adv2')             # None for rookies / no 2-season history
    chart2 = v.get('chart2')         # None for rookies / no 2-season charting
    tenv_own = v.get('team_env') or {}   # own team environment (may be {})

    carry_pg = u.get('carry_pg') or 0
    carry_share = u.get('carry_share') or 0
    tgt_share = u.get('tgt_share') or 0
    catch_rate = u.get('catch_rate') or 0
    ypt = u.get('ypt') or 0
    ypc = u.get('ypc') or 0
    dk_pg = u.get('dk_pg') or 0

    explosive = fus.get('explosive_pctl') or 0
    run_eff = fus.get('run_eff_pctl') or 0
    rush_eff = fus.get('rush_eff_pctl') or 0
    yac_pctl = fus.get('yac_pctl') or 0
    oline_pctl = fus.get('oline_pctl') or 0
    boom_pctl = fus.get('boom_pctl') or 0
    ceiling_p = fus.get('ceiling_pctl') or 50
    value_pctl = fus.get('value_pctl') or 0
    spike_pctl = fus.get('spike_pctl') or 0
    matchup_p = fus.get('matchup_pctl') or 0
    adv_pctl = fus.get('adv_pctl') or 0

    mtf_att = sg(sis, 'MTF_att')
    success = sg(sis, 'success')
    tgts_g_sis = sg(sis, 'tgts_g')
    rush_fd_att = sg(sis, 'rush_fd_att')

    # 2-season (2024+2025) advanced values — prefer over single-season when present
    has_adv2 = adv2 is not None
    if has_adv2:
        a2_g = adv2.get('g') or 0
        a2_carry_share = adv2.get('carry_share') or 0   # 0-100 scale
        a2_ypc = adv2.get('ypc') or 0
        a2_rush_pg = adv2.get('rush_pg') or 0
        a2_tgt_share = adv2.get('tgt_share') or 0   # 0-100 scale
        a2_ypt = adv2.get('ypt') or 0
        a2_rec_pg = adv2.get('rec_pg') or 0
        a2_td_pg = adv2.get('td_pg') or 0
        a2_yptouch = adv2.get('yptouch') or 0

    # 2-season (2024+2025) FantasyPoints RUSHING charting
    has_chart2 = chart2 is not None
    if has_chart2:
        _b = chart2.get('blend') or {}
        c2_g = _b.get('g') or 0
        c2_exp_run = _b.get('exp_run') or 0
        c2_mtf_att = _b.get('mtf_att') or 0
        c2_yaco_att = _b.get('yaco_att') or 0
        c2_ybco_att = _b.get('ybco_att') or 0
        c2_success = _b.get('success') or 0
        c2_stuff = _b.get('stuff') or 0
        c2_i5_pct = _b.get('i5_pct') or 0
        c2_td_rate = _b.get('td_rate') or 0
        c2_ypc = _b.get('ypc') or 0

    sf = []
    cond = []
    seen = set()

    def add(lbl, fn):
        if lbl not in seen:
            seen.add(lbl)
            cond.append((lbl, fn))

    # FLAG 1: WORKHORSE VOLUME
    if has_adv2:
        f1 = (a2_carry_share >= 45 or a2_rush_pg >= 13.0)
    else:
        f1 = (carry_pg >= 13.0 or carry_share >= 0.45)
    if f1:
        parts = []
        if has_adv2:
            parts.append("2yr {:g}% carry share, {:.1f} rush/g over {:g}g".format(
                a2_carry_share, a2_rush_pg, a2_g))
            if a2_ypc > 0:
                parts.append("2yr {:.1f} YPC".format(a2_ypc))
        else:
            if carry_pg >= 1:
                parts.append("carry_pg {:.1f}".format(carry_pg))
            if carry_share > 0:
                parts.append("carry_share {:.3f}".format(carry_share))
            if ypc > 0:
                parts.append("ypc {:.2f}".format(ypc))
        if rush_fd_att and rush_fd_att >= 0.20:
            parts.append("SIS rush_fd_att {:.2f}".format(rush_fd_att))
        sf.append({"f": "Workhorse volume",
                   "d": ", ".join(parts),
                   "amp": "soft run tier (runp<=35) / run-funnel (covp>=60 & runp<=45) / positive script (home + favored = 4th-qtr carries)"})

        def _wh_soft(od, home, dome):
            tier = od.get('tiers', {}).get('RB', 'AVG')
            runp = di(od, 'runp')
            lit = tier == 'SOFT' or runp <= 35
            mult = 1.35 if lit else (0.72 if tier == 'TOUGH' and runp >= 70 else 1.0)
            return lit, mult
        add("soft run-D (workhorse volume)", _wh_soft)

        def _rf_wh(od, home, dome):
            covp = di(od, 'covp'); runp = di(od, 'runp')
            lit = covp >= 60 and runp <= 45
            return lit, 1.18 if lit else 1.0
        add("run-funnel (workhorse volume surge)", _rf_wh)

        def _ps_wh(od, home, dome):
            tier = od.get('tiers', {}).get('RB', 'AVG')
            lit = home and tier != 'TOUGH'
            return lit, 1.12 if lit else 1.0
        add("positive script (home win = 4th-qtr carries)", _ps_wh)

    # FLAG 2: EXPLOSIVE / BIG-PLAY CEILING
    if has_chart2:
        f2 = (c2_exp_run >= 5.5 or c2_mtf_att >= 0.17 or c2_yaco_att >= 2.45 or explosive >= 60)
    elif has_adv2:
        f2 = (explosive >= 60 or a2_ypc >= 4.6 or rush_eff >= 70)
    else:
        f2 = (explosive >= 60 or ypc >= 4.6 or rush_eff >= 70)
    if f2:
        parts = []
        if has_chart2 and c2_g > 0:
            parts.append("2yr {:.1f}% explosive runs, {:.2f} MTF/att, {:.2f} YACO/att over {:g}g (FP charting)".format(
                c2_exp_run, c2_mtf_att, c2_yaco_att, c2_g))
            if explosive >= 1:
                parts.append("explosive {:.0f}th pctl".format(explosive))
        else:
            if explosive >= 1:
                parts.append("explosive {:.0f}th pctl".format(explosive))
            if has_adv2 and (a2_ypc > 0 or a2_yptouch > 0):
                parts.append("2yr {:.1f} YPC, {:.1f} yd/touch".format(a2_ypc, a2_yptouch))
            elif ypc > 0:
                parts.append("ypc {:.2f}".format(ypc))
            if rush_eff >= 60:
                parts.append("rush_eff {:.0f}th pctl".format(rush_eff))
            if mtf_att and mtf_att > 0.25:
                parts.append("SIS MTF {:.2f}/att".format(mtf_att))
        sf.append({"f": "Explosive / big-play ceiling",
                   "d": ", ".join(parts),
                   "amp": "soft run-D (runp<=35) / light box via pass-funnel / dome / soft RB tier"})

        def _sr_expl(od, home, dome):
            tier = od.get('tiers', {}).get('RB', 'AVG')
            runp = di(od, 'runp')
            lit = tier == 'SOFT' or runp <= 35
            mult = 1.35 if lit else (0.72 if tier == 'TOUGH' and runp >= 70 else 1.0)
            return lit, mult
        add("soft run-D (explosive ceiling)", _sr_expl)

        def _pf_expl(od, home, dome):
            runp = di(od, 'runp'); covp = di(od, 'covp')
            lit = runp >= 60 and covp <= 45
            return lit, 1.18 if lit else 1.0
        add("pass-funnel (light box -> big runs)", _pf_expl)

        def _dome_expl(od, home, dome):
            return dome, 1.08 if dome else 1.0
        add("dome (explosive ceiling)", _dome_expl)

    # FLAG 3: RECEIVING BACK / PPR CEILING
    if has_adv2:
        f3 = (a2_tgt_share >= 10 or a2_ypt >= 6.5)
    else:
        f3 = (tgt_share >= 0.10 or ypt >= 6.5)
    if f3:
        parts = []
        if has_adv2 and (a2_tgt_share > 0 or a2_rec_pg > 0):
            parts.append("2yr {:g}% tgt share, {:.1f} rec/g, {:.1f} YPT".format(
                a2_tgt_share, a2_rec_pg, a2_ypt))
        else:
            if tgt_share > 0:
                parts.append("tgt_share {:.3f}".format(tgt_share))
            if catch_rate >= 0.65:
                parts.append("catch_rate {:.2f}".format(catch_rate))
            if ypt > 0:
                parts.append("ypt {:.2f}".format(ypt))
        if tgts_g_sis and tgts_g_sis >= 1.5:
            parts.append("SIS tgts_g {:.1f}".format(tgts_g_sis))
        sf.append({"f": "Receiving back / PPR ceiling",
                   "d": ", ".join(parts),
                   "amp": "pass-funnel (runp>=60 & covp<=45) / neg-script (team trailing = check-downs) / man-cov (RB-on-LB mismatch)"})

        def _pf_recv(od, home, dome):
            runp = di(od, 'runp'); covp = di(od, 'covp')
            lit = runp >= 60 and covp <= 45
            return lit, 1.18 if lit else 1.0
        add("pass-funnel (dump-off lanes)", _pf_recv)

        def _neg_script(od, home, dome):
            covp = di(od, 'covp')
            tier = od.get('tiers', {}).get('RB', 'AVG')
            lit = (not home and covp >= 60) or tier == 'TOUGH'
            return lit, 1.12 if lit else 1.0
        add("neg-script (trailing -> check-downs)", _neg_script)

        def _man_rb(od, home, dome):
            manp = di(od, 'manp')
            lit = manp >= 68
            return lit, 1.18 if lit else 1.0
        add("man-cov (RB-on-LB mismatch)", _man_rb)

    # FLAG 4: GOAL-LINE / TD PROXY (rz_share null for RBs)
    if has_chart2:
        f4 = (c2_i5_pct >= 39 or c2_td_rate >= 3.5) and (boom_pctl >= 55 or dk_pg >= 13)
    elif has_adv2:
        f4 = (a2_carry_share >= 45 and (boom_pctl >= 55 or dk_pg >= 13))
    else:
        f4 = (carry_share >= 0.45 and (boom_pctl >= 55 or dk_pg >= 13))
    if f4:
        parts = []
        if has_chart2 and c2_g > 0:
            parts.append("2yr {:.1f}% inside-5 carry share, {:.1f}% TD rate over {:g}g (FP charting)".format(
                c2_i5_pct, c2_td_rate, c2_g))
            if has_adv2 and a2_td_pg > 0:
                parts.append("2yr {:.2f} TD/g".format(a2_td_pg))
        elif has_adv2:
            parts.append("2yr {:g}% carry share".format(a2_carry_share))
            if a2_td_pg > 0:
                parts.append("2yr {:.2f} TD/g over {:g}g".format(a2_td_pg, a2_g))
        else:
            parts.append("carry_share {:.3f}".format(carry_share))
        parts += ["boom_pctl {:.0f}th pctl".format(boom_pctl),
                  "dk_pg {:.1f}".format(dk_pg)]
        if rush_fd_att and rush_fd_att >= 0.20:
            parts.append("SIS rush_fd_att {:.2f}".format(rush_fd_att))
        sf.append({"f": "Goal-line / TD-dependent ceiling",
                   "d": ", ".join(parts) + " (proxy: rz_share N/A for RBs)",
                   "amp": "soft run tier near goal (runp<=40) / positive script / run-funnel"})

        def _gl_soft(od, home, dome):
            tier = od.get('tiers', {}).get('RB', 'AVG')
            runp = di(od, 'runp')
            lit = tier == 'SOFT' or runp <= 40
            mult = 1.30 if lit else (0.70 if tier == 'TOUGH' else 1.0)
            return lit, mult
        add("soft run-D (goal-line TD ceiling)", _gl_soft)

        def _rf_gl(od, home, dome):
            covp = di(od, 'covp'); runp = di(od, 'runp')
            lit = covp >= 60 and runp <= 45
            return lit, 1.18 if lit else 1.0
        add("run-funnel (goal-line volume)", _rf_gl)

    # FLAG 5: O-LINE / RUN-SCHEME EFFICIENCY
    if has_chart2:
        f5 = (c2_success >= 51 or c2_ybco_att >= 2.05 or oline_pctl >= 60 or run_eff >= 65)
    else:
        f5 = (oline_pctl >= 60 or run_eff >= 65)
    if f5:
        parts = []
        if has_chart2 and c2_g > 0:
            parts.append("2yr {:.0f}% success rate, {:.2f} YBCO/att (blocking), {:.2f} YPC over {:g}g (FP charting)".format(
                c2_success, c2_ybco_att, c2_ypc, c2_g))
            if oline_pctl >= 1:
                parts.append("oline_pctl {:.0f}th".format(oline_pctl))
        else:
            if oline_pctl >= 1:
                parts.append("oline_pctl {:.0f}th".format(oline_pctl))
            if run_eff >= 65:
                parts.append("run_eff_pctl {:.0f}th".format(run_eff))
            if rush_eff >= 65:
                parts.append("rush_eff_pctl {:.0f}th".format(rush_eff))
            if not parts:
                parts = ["oline_pctl {:.0f}th".format(oline_pctl)]
        sf.append({"f": "O-line / run-scheme efficiency",
                   "d": ", ".join(parts),
                   "amp": "soft run-D (runp<=30) / run-funnel / light box"})

        def _oline_soft(od, home, dome):
            tier = od.get('tiers', {}).get('RB', 'AVG')
            runp = di(od, 'runp')
            lit = tier == 'SOFT' or runp <= 30
            mult = 1.30 if lit else (0.75 if tier == 'TOUGH' and runp >= 70 else 1.0)
            return lit, mult
        add("soft run-D (O-line payoff)", _oline_soft)

        def _pf_oline(od, home, dome):
            runp = di(od, 'runp'); covp = di(od, 'covp')
            lit = runp >= 60 and covp <= 45
            return lit, 1.18 if lit else 1.0
        add("pass-funnel (O-line payoff)", _pf_oline)

    # FLAG 6: CONTACT / YAC CEILING
    f6 = (yac_pctl >= 65)
    if f6:
        parts = ["yac_pctl {:.0f}th pctl".format(yac_pctl)]
        if mtf_att and mtf_att > 0.25:
            parts.append("SIS MTF {:.2f}/att".format(mtf_att))
        sf.append({"f": "Contact / YAC ceiling",
                   "d": ", ".join(parts),
                   "amp": "spread defense (zone-D / light box) / soft RB tier / open-field situations"})

        def _soft_yac(od, home, dome):
            tier = od.get('tiers', {}).get('RB', 'AVG')
            runp = di(od, 'runp')
            lit = tier == 'SOFT' or runp <= 35
            mult = 1.20 if lit else (0.78 if tier == 'TOUGH' else 1.0)
            return lit, mult
        add("soft run-D (YAC ceiling)", _soft_yac)

        def _zone_yac(od, home, dome):
            manp = di(od, 'manp')
            lit = manp <= 32
            return lit, 1.12 if lit else 1.0
        add("zone-D (open field = YAC lanes)", _zone_yac)

    # FLAG 6B: CONTACT-BALANCE (chart2 only)
    if has_chart2 and c2_g > 0 and c2_yaco_att >= 2.45 and c2_mtf_att >= 0.17:
        parts = ["2yr {:.2f} YACO/att, {:.2f} MTF/att over {:g}g (FP charting)".format(
            c2_yaco_att, c2_mtf_att, c2_g)]
        if c2_stuff < 45:
            parts.append("{:.0f}% stuff rate (low)".format(c2_stuff))
        sf.append({"f": "Contact-balance / tackle-break ceiling",
                   "d": ", ".join(parts) + " -- gains after contact on every carry type",
                   "amp": "soft RB tier / zone-D (open field) / light box / positive script"})

        def _cb_soft(od, home, dome):
            tier = od.get('tiers', {}).get('RB', 'AVG')
            runp = di(od, 'runp')
            lit = tier == 'SOFT' or runp <= 35
            mult = 1.20 if lit else (0.78 if tier == 'TOUGH' else 1.0)
            return lit, mult
        add("soft run-D (contact-balance ceiling)", _cb_soft)

        def _cb_zone(od, home, dome):
            manp = di(od, 'manp')
            lit = manp <= 32
            return lit, 1.10 if lit else 1.0
        add("zone-D (contact-balance open field)", _cb_zone)

    # FLAG 7: PASS-DOWN / SATELLITE SPECIALIST
    f7 = (tgt_share >= 0.10 and carry_share <= 0.40)
    if f7:
        parts = ["tgt_share {:.3f}".format(tgt_share),
                 "carry_share {:.3f} (low)".format(carry_share)]
        if ypt > 0:
            parts.append("ypt {:.2f}".format(ypt))
        if catch_rate >= 0.70:
            parts.append("catch_rate {:.2f}".format(catch_rate))
        sf.append({"f": "Pass-down / satellite specialist",
                   "d": ", ".join(parts) + " -- PPR-first role, minimal ground work",
                   "amp": "pass-funnel / neg-script (more dump-offs) / man-cov (RB-on-LB) / multi-target weeks"})

        def _sat_pf(od, home, dome):
            runp = di(od, 'runp'); covp = di(od, 'covp')
            lit = runp >= 60 and covp <= 45
            return lit, 1.18 if lit else 1.0
        add("pass-funnel (satellite role)", _sat_pf)

        def _sat_neg(od, home, dome):
            covp = di(od, 'covp')
            lit = not home and covp >= 55
            return lit, 1.12 if lit else 1.0
        add("neg-script (satellite dump-offs)", _sat_neg)

    # FLAG 8: CONTINGENT BELL-COW / HANDCUFF
    f8 = (carry_share < 0.30 and (explosive >= 70 or ceiling_p >= 60))
    if f8:
        parts = ["carry_share {:.3f} (handcuff role)".format(carry_share)]
        if explosive >= 70:
            parts.append("explosive {:.0f}th pctl".format(explosive))
        if ceiling_p >= 55:
            parts.append("ceiling_pctl {:.0f}th pctl".format(ceiling_p))
        sf.append({"f": "Contingent bell-cow / handcuff upside",
                   "d": ", ".join(parts) + " -- elite upside, needs starter injury",
                   "amp": "starter injury -> workhorse role / soft run-D / run-funnel"})

        def _hc_soft(od, home, dome):
            tier = od.get('tiers', {}).get('RB', 'AVG')
            runp = di(od, 'runp')
            lit = tier == 'SOFT' or runp <= 40
            mult = 1.25 if lit else (0.80 if tier == 'TOUGH' else 1.0)
            return lit, mult
        add("soft run-D (handcuff potential)", _hc_soft)

    # FLAG 9: SPIKE / VARIANCE CEILING (threshold 55)
    f9 = (spike_pctl >= 55)
    if f9:
        parts = ["spike_pctl {:.0f}th pctl".format(spike_pctl)]
        if boom_pctl >= 40:
            parts.append("boom_pctl {:.0f}th pctl".format(boom_pctl))
        sf.append({"f": "Spike / weekly-variance ceiling",
                   "d": ", ".join(parts) + " -- high game-to-game variance; ceiling outlier weeks",
                   "amp": "soft RB tier / positive script / run-funnel / dome"})

        def _spike_soft(od, home, dome):
            tier = od.get('tiers', {}).get('RB', 'AVG')
            runp = di(od, 'runp')
            lit = tier == 'SOFT' or runp <= 35
            mult = 1.20 if lit else (0.80 if tier == 'TOUGH' else 1.0)
            return lit, mult
        add("soft run-D (spike ceiling)", _spike_soft)

        def _dome_spike(od, home, dome):
            return dome, 1.08 if dome else 1.0
        add("dome (spike ceiling)", _dome_spike)

    # FLAG 10: ADVANCED COMPOSITE VALUE LEADER
    f10 = (adv_pctl >= 65 and value_pctl >= 65)
    if f10:
        parts = ["adv_pctl {:.0f}th".format(adv_pctl),
                 "value_pctl {:.0f}th".format(value_pctl)]
        if matchup_p >= 50:
            parts.append("matchup_pctl {:.0f}th".format(matchup_p))
        sf.append({"f": "Advanced composite value leader",
                   "d": ", ".join(parts) + " -- elite across multiple advanced metrics",
                   "amp": "soft RB tier / favorable matchup / positive script"})

        def _adv_soft(od, home, dome):
            tier = od.get('tiers', {}).get('RB', 'AVG')
            runp = di(od, 'runp')
            lit = tier == 'SOFT' or runp <= 35
            mult = 1.25 if lit else (0.78 if tier == 'TOUGH' and runp >= 68 else 1.0)
            return lit, mult
        add("soft run-D (elite value payoff)", _adv_soft)

        def _matchup_adv(od, home, dome):
            runp = di(od, 'runp')
            lit = runp <= 40
            return lit, 1.15 if lit else 1.0
        add("favorable matchup (advanced value)", _matchup_adv)

    # FLAG 11: BOOM-WEEK CONCENTRATION
    f11 = (boom_pctl >= 60 and ceiling_p >= 55)
    if f11:
        parts = ["boom_pctl {:.0f}th".format(boom_pctl),
                 "ceiling_pctl {:.0f}th".format(ceiling_p)]
        if dk_pg > 0:
            parts.append("dk_pg {:.1f}".format(dk_pg))
        sf.append({"f": "Boom-week concentration",
                   "d": ", ".join(parts) + " -- historically clusters high-score weeks",
                   "amp": "soft run-D / positive script / run-funnel / dome"})

        def _boom_soft(od, home, dome):
            tier = od.get('tiers', {}).get('RB', 'AVG')
            runp = di(od, 'runp')
            lit = tier == 'SOFT' or runp <= 40
            mult = 1.25 if lit else (0.75 if tier == 'TOUGH' else 1.0)
            return lit, mult
        add("soft run-D (boom-week trigger)", _boom_soft)

        def _pos_boom(od, home, dome):
            tier = od.get('tiers', {}).get('RB', 'AVG')
            lit = home and tier != 'TOUGH'
            return lit, 1.12 if lit else 1.0
        add("positive script (home + boom concentration)", _pos_boom)

    # FLAG 12: RUN-EFFICIENCY GRINDER (no expl flag)
    f12 = (rush_eff >= 60 and ypc >= 4.3 and not f2)
    if f12:
        parts = ["rush_eff_pctl {:.0f}th".format(rush_eff),
                 "ypc {:.2f}".format(ypc)]
        if run_eff >= 50:
            parts.append("run_eff_pctl {:.0f}th".format(run_eff))
        sf.append({"f": "Run-efficiency grinder",
                   "d": ", ".join(parts) + " -- consistent yards vs contact",
                   "amp": "soft run-D / run-funnel / volume upside in scheme"})

        def _grind_soft(od, home, dome):
            tier = od.get('tiers', {}).get('RB', 'AVG')
            runp = di(od, 'runp')
            lit = tier == 'SOFT' or runp <= 35
            mult = 1.20 if lit else (0.80 if tier == 'TOUGH' and runp >= 68 else 1.0)
            return lit, mult
        add("soft run-D (efficiency grinder)", _grind_soft)

        def _rf_grind(od, home, dome):
            covp = di(od, 'covp'); runp = di(od, 'runp')
            lit = covp >= 55 and runp <= 45
            return lit, 1.15 if lit else 1.0
        add("run-funnel (efficiency grinder)", _rf_grind)

    # FLAG 13: HIGH SCORING FLOOR
    f13 = (dk_pg >= 12.0 and (carry_pg >= 8.0 or carry_share >= 0.28))
    if f13:
        parts = ["dk_pg {:.1f}".format(dk_pg),
                 "carry_pg {:.1f}".format(carry_pg),
                 "carry_share {:.3f}".format(carry_share)]
        sf.append({"f": "High scoring floor / DK ceiling enabler",
                   "d": ", ".join(parts) + " -- high floor means boom weeks are more frequent",
                   "amp": "soft run-D / run-funnel / dome / positive script"})

        def _floor_soft(od, home, dome):
            tier = od.get('tiers', {}).get('RB', 'AVG')
            runp = di(od, 'runp')
            lit = tier == 'SOFT' or runp <= 35
            mult = 1.25 if lit else (0.78 if tier == 'TOUGH' else 1.0)
            return lit, mult
        add("soft run-D (floor -> ceiling)", _floor_soft)

        def _dome_floor(od, home, dome):
            return dome, 1.08 if dome else 1.0
        add("dome (floor -> ceiling enabler)", _dome_floor)

    # FLAG 14: EFFICIENT RECEIVING (separate from full receiving flag)
    f14 = (ypt >= 5.0 and catch_rate >= 0.78 and tgt_share >= 0.05 and not f3)
    if f14:
        parts = ["ypt {:.2f}".format(ypt),
                 "catch_rate {:.2f}".format(catch_rate),
                 "tgt_share {:.3f}".format(tgt_share)]
        sf.append({"f": "Efficient receiving / catch-and-run",
                   "d": ", ".join(parts) + " -- elite efficiency when targeted",
                   "amp": "pass-funnel / neg-script / man-cov (RB-on-LB)"})

        def _eff_recv_pf(od, home, dome):
            runp = di(od, 'runp'); covp = di(od, 'covp')
            lit = runp >= 60 and covp <= 45
            return lit, 1.18 if lit else 1.0
        add("pass-funnel (efficient receiver)", _eff_recv_pf)

        def _eff_recv_neg(od, home, dome):
            covp = di(od, 'covp')
            lit = not home and covp >= 55
            return lit, 1.10 if lit else 1.0
        add("neg-script (efficient receiver)", _eff_recv_neg)

    # FLAG 15: MATCHUP-PROOF (matchup + adv combined)
    f15 = (matchup_p >= 60 and adv_pctl >= 55)
    if f15:
        parts = ["matchup_pctl {:.0f}th".format(matchup_p),
                 "adv_pctl {:.0f}th".format(adv_pctl)]
        if value_pctl >= 50:
            parts.append("value_pctl {:.0f}th".format(value_pctl))
        sf.append({"f": "Matchup-proof advanced value",
                   "d": ", ".join(parts) + " -- ranks well in both matchup-based and advanced models",
                   "amp": "strong vs all defensive types / amplified by soft tier"})

        def _matchup_soft(od, home, dome):
            tier = od.get('tiers', {}).get('RB', 'AVG')
            runp = di(od, 'runp')
            lit = tier == 'SOFT' or runp <= 40
            mult = 1.20 if lit else (0.82 if tier == 'TOUGH' else 1.0)
            return lit, mult
        add("soft run-D (matchup-proof value)", _matchup_soft)

    # FLAG 16: MATCHUP-FAVORED (standalone)
    f16 = (matchup_p >= 65 and not f15)
    if f16:
        parts = ["matchup_pctl {:.0f}th".format(matchup_p)]
        if spike_pctl >= 40:
            parts.append("spike_pctl {:.0f}th".format(spike_pctl))
        if dk_pg > 0:
            parts.append("dk_pg {:.1f}".format(dk_pg))
        sf.append({"f": "Matchup-favored schedule",
                   "d": ", ".join(parts) + " -- schedule model grades upcoming slate above average",
                   "amp": "soft RB tier weeks / run-funnel matchups / volume opportunity"})

        def _match_fav(od, home, dome):
            tier = od.get('tiers', {}).get('RB', 'AVG')
            runp = di(od, 'runp')
            lit = tier == 'SOFT' or runp <= 40
            mult = 1.20 if lit else (0.82 if tier == 'TOUGH' else 1.0)
            return lit, mult
        add("soft run-D (matchup-favored)", _match_fav)

    # SIS EFFICIENCY (bonus -- only ~4 RBs with real SIS data)
    if success and success >= 55 and rush_fd_att and rush_fd_att >= 0.22:
        parts = ["SIS success {:.1f}%".format(success),
                 "rush_fd_att {:.2f}/att".format(rush_fd_att)]
        if mtf_att and mtf_att > 0.20:
            parts.append("MTF {:.2f}/att".format(mtf_att))
        sf.append({"f": "High success-rate / first-down machine (SIS)",
                   "d": ", ".join(parts),
                   "amp": "soft run tier / run-funnel / positive script"})

        def _sis_soft(od, home, dome):
            tier = od.get('tiers', {}).get('RB', 'AVG')
            lit = tier == 'SOFT'
            return lit, 1.15 if lit else 1.0
        add("SIS high-success x soft run-D", _sis_soft)

    # SAFETY NET: backs with real role (csh>=0.25 OR tgt>=0.08) get >=3 flags
    has_real_role = (carry_share >= 0.25 or tgt_share >= 0.08)
    while has_real_role and len(sf) < 3:
        existing = {s['f'] for s in sf}

        if "Boom-week concentration" not in existing and boom_pctl >= 40:
            parts = ["boom_pctl {:.0f}th".format(boom_pctl)]
            if ceiling_p >= 40:
                parts.append("ceiling_pctl {:.0f}th".format(ceiling_p))
            sf.append({"f": "Boom-week concentration",
                       "d": ", ".join(parts),
                       "amp": "soft run-D / positive script / run-funnel"})

            def _bn_soft(od, home, dome):
                tier = od.get('tiers', {}).get('RB', 'AVG')
                runp = di(od, 'runp')
                lit = tier == 'SOFT' or runp <= 40
                mult = 1.20 if lit else (0.80 if tier == 'TOUGH' else 1.0)
                return lit, mult
            add("soft run-D (boom upside)", _bn_soft)
            continue

        if "Advanced composite value leader" not in existing and adv_pctl >= 40:
            parts = ["adv_pctl {:.0f}th".format(adv_pctl)]
            if value_pctl >= 35:
                parts.append("value_pctl {:.0f}th".format(value_pctl))
            sf.append({"f": "Advanced composite value leader",
                       "d": ", ".join(parts),
                       "amp": "soft RB tier / favorable matchup"})

            def _adv2_soft(od, home, dome):
                tier = od.get('tiers', {}).get('RB', 'AVG')
                runp = di(od, 'runp')
                lit = tier == 'SOFT' or runp <= 40
                mult = 1.20 if lit else (0.80 if tier == 'TOUGH' else 1.0)
                return lit, mult
            add("soft run-D (advanced value)", _adv2_soft)
            continue

        if "Spike / weekly-variance ceiling" not in existing and spike_pctl >= 40:
            parts = ["spike_pctl {:.0f}th".format(spike_pctl)]
            sf.append({"f": "Spike / weekly-variance ceiling",
                       "d": ", ".join(parts),
                       "amp": "soft RB tier / positive script / dome"})

            def _spk2_soft(od, home, dome):
                tier = od.get('tiers', {}).get('RB', 'AVG')
                runp = di(od, 'runp')
                lit = tier == 'SOFT' or runp <= 35
                mult = 1.15 if lit else (0.82 if tier == 'TOUGH' else 1.0)
                return lit, mult
            add("soft run-D (spike)", _spk2_soft)
            continue

        if "High scoring floor / DK ceiling enabler" not in existing and dk_pg >= 5.0:
            parts = ["dk_pg {:.1f}".format(dk_pg),
                     "carry_share {:.3f}".format(carry_share)]
            sf.append({"f": "High scoring floor / DK ceiling enabler",
                       "d": ", ".join(parts),
                       "amp": "soft run-D / run-funnel / positive script"})

            def _fl2_soft(od, home, dome):
                tier = od.get('tiers', {}).get('RB', 'AVG')
                runp = di(od, 'runp')
                lit = tier == 'SOFT' or runp <= 40
                mult = 1.15 if lit else (0.82 if tier == 'TOUGH' else 1.0)
                return lit, mult
            add("soft run-D (floor)", _fl2_soft)
            continue

        if ceiling_p >= 45:
            parts = ["ceiling_pctl {:.0f}th".format(ceiling_p)]
            if adv_pctl > 0:
                parts.append("adv_pctl {:.0f}th".format(adv_pctl))
            sf.append({"f": "Ceiling percentile upside",
                       "d": ", ".join(parts) + " -- model-projected ceiling ability",
                       "amp": "soft run-D / positive script / run-funnel"})

            def _ceil_soft(od, home, dome):
                tier = od.get('tiers', {}).get('RB', 'AVG')
                runp = di(od, 'runp')
                lit = tier == 'SOFT' or runp <= 40
                mult = 1.15 if lit else (0.82 if tier == 'TOUGH' else 1.0)
                return lit, mult
            add("soft run-D (ceiling potential)", _ceil_soft)
            continue

        break

    # FALLBACK: every RB gets at least 1 flag
    if not sf:
        best = max(
            ('rush_eff', rush_eff),
            ('run_eff', run_eff),
            ('ceiling', ceiling_p),
            ('boom', boom_pctl),
            ('spike', spike_pctl),
            key=lambda x: x[1]
        )
        stat_name, stat_val = best
        desc = "{}_pctl {:.0f}th".format(stat_name, stat_val)
        if stat_name in ('rush_eff', 'run_eff') and stat_val >= 30:
            flag_name = "Run-efficiency / scheme contributor"
            amp = "soft run-D / run-funnel"
        elif stat_name == 'spike' and stat_val >= 40:
            flag_name = "Spike / variance upside"
            amp = "soft run-D / positive script"
        elif stat_name == 'boom' and stat_val >= 30:
            flag_name = "Boom-week upside"
            amp = "soft run-D / run-funnel"
        else:
            flag_name = "Situational ceiling / deep-bench upside"
            amp = "soft run-D / pass-funnel / positive script"
        sf.append({"f": flag_name, "d": desc, "amp": amp})

        def _sit_soft(od, home, dome):
            tier = od.get('tiers', {}).get('RB', 'AVG')
            runp = di(od, 'runp')
            lit = tier == 'SOFT' or runp <= 40
            mult = 1.15 if lit else (0.80 if tier == 'TOUGH' else 1.0)
            return lit, mult
        add("soft run-D (situational)", _sit_soft)

        def _sit_pf(od, home, dome):
            runp = di(od, 'runp'); covp = di(od, 'covp')
            lit = runp >= 60 and covp <= 45
            return lit, 1.10 if lit else 1.0
        add("pass-funnel (situational)", _sit_pf)

    # ── EXTRA SIGNAL: ENV / SCORING ENVIRONMENT (skill flag + per-week condition) ──
    own_env_idx = tenv_own.get('env_idx', 0) or 0
    own_pace_pctl = tenv_own.get('pace_pctl', 0) or 0
    own_win_total = tenv_own.get('win_total', 0) or 0
    has_tenv = bool(tenv_own)

    if has_tenv and own_env_idx >= 70:
        sf.append({
            "f": "High-scoring offense (ENV signal)",
            "d": "env_idx {:.0f}/100 — top-tier scoring environment (>=70); more possessions, more goal-line chances".format(own_env_idx),
            "amp": "soft run-D / shootout setup (opp covp<=35) / positive script (favored + home)"
        })

        def _env_shootout(od, home, dome, _ei=own_env_idx):
            covp = di(od, 'covp')
            lit = _ei >= 65 and covp <= 35
            return lit, 1.06 if lit else 1.0
        add("ENV shootout (own env_idx>=65 + opp soft pass-D)", _env_shootout)

    elif has_tenv and own_env_idx >= 65:
        def _env_shootout(od, home, dome, _ei=own_env_idx):
            covp = di(od, 'covp')
            lit = _ei >= 65 and covp <= 35
            return lit, 1.06 if lit else 1.0
        add("ENV shootout (own env_idx>=65 + opp soft pass-D)", _env_shootout)

    # ── RB role classification for SCRIPT (used by per-week script condition) ──────
    _is_recv_back = (tgt_share >= 0.12 or
                     (carry_share > 0 and tgt_share > 0 and tgt_share / carry_share > 0.25))
    _is_early_down = (tgt_share < 0.09 and carry_share >= 0.45)

    # ── SUPPRESSORS (always added) ────────────────────────────────────────────────
    def _tough_run(od, home, dome):
        tier = od.get('tiers', {}).get('RB', 'AVG')
        runp = di(od, 'runp')
        lit = tier == 'TOUGH' and runp >= 68
        return lit, 0.72 if lit else 1.0
    add("TOUGH RB tier (run-D suppressor)", _tough_run)

    if tgt_share < 0.09 and carry_share >= 0.45 and carry_pg >= 10.0:
        def _neg_ed(od, home, dome):
            covp = di(od, 'covp')
            lit = not home and covp >= 65
            return lit, 0.82 if lit else 1.0
        add("neg-script (early-down only -- fewer carries when trailing)", _neg_ed)

    # LINE
    if explosive >= 80 and tgt_share >= 0.15:
        line = ("elite explosive receiving back (expl {:.0f}th pctl, "
                "tgt_share {:.3f}, dk_pg {:.1f}) -- ceiling fires from ANY direction: "
                "soft run-D, pass-funnel, dome, or neg-script.").format(explosive, tgt_share, dk_pg)
    elif explosive >= 70 and tgt_share >= 0.10:
        line = ("explosive dual-threat back (expl {:.0f}th pctl, "
                "tgt_share {:.3f}, {:.1f} cpg) -- hard to scheme away; "
                "soft run-D OR pass-funnel OR dome each independently unlock ceiling.").format(explosive, tgt_share, carry_pg)
    elif explosive >= 70 and carry_pg >= 14.0 and tgt_share < 0.10:
        line = ("explosive early-down bellcow ({:.1f} cpg, {:.3f} share, "
                "expl {:.0f}th pctl) -- ceiling requires soft run-D or run-funnel; "
                "SUPPRESSED when trailing (no target valve).").format(carry_pg, carry_share, explosive)
    elif explosive >= 70 and carry_pg < 12.0:
        line = ("explosive change-of-pace / handcuff (expl {:.0f}th pctl, "
                "only {:.1f} cpg) -- boom-or-bust; needs soft matchup + opportunity.").format(explosive, carry_pg)
    elif carry_pg >= 16.0 and tgt_share <= 0.09:
        line = ("early-down workhorse ({:.1f} cpg, {:.3f} share, "
                "tgt_share only {:.3f}) -- TD-dependent ceiling; soft run-D "
                "+ positive script + run-funnel; hard ceiling vs negative script.").format(carry_pg, carry_share, tgt_share)
    elif tgt_share >= 0.10 and carry_share <= 0.40:
        line = ("satellite / pass-down specialist (tgt_share {:.3f}, "
                "carry_share {:.3f}) -- PPR-driven ceiling; fires vs "
                "pass-funnel + neg-script + man-cov; limited ground upside.").format(tgt_share, carry_share)
    elif carry_pg >= 13.0 and tgt_share >= 0.10:
        line = ("dual-threat back ({:.1f} cpg + {:.3f} tgt_share) -- "
                "pass-funnel or neg-script unlocks PPR surge; soft run-D unlocks ground game.").format(carry_pg, tgt_share)
    elif boom_pctl >= 60 and ceiling_p >= 55:
        line = ("boom-week clusterer (boom_pctl {:.0f}th, ceiling_pctl {:.0f}th"
                ") -- ceiling tracks soft run-D, positive script, and run funnels.").format(boom_pctl, ceiling_p)
    elif oline_pctl >= 70 and carry_pg >= 10.0:
        line = ("elite-blocking scheme back (oline {:.0f}th pctl, {:.1f} cpg) -- "
                "ceiling payoff vs soft run-D and run-funnels where the line dominates.").format(oline_pctl, carry_pg)
    elif spike_pctl >= 70:
        line = ("high-variance spike back (spike_pctl {:.0f}th, dk_pg {:.1f}) -- "
                "wide weekly distribution; outlier ceiling in soft matchups + dome.").format(spike_pctl, dk_pg)
    else:
        line = ("volume/scheme-dependent RB ({:.1f} cpg, {:.3f} share, "
                "dk_pg {:.1f}) -- ceiling tracks soft run-D and weekly usage.").format(carry_pg, carry_share, dk_pg)

    player_meta = {
        'has_tenv':       has_tenv,
        'own_env_idx':    own_env_idx,
        'own_pace_pctl':  own_pace_pctl,
        'own_win_total':  own_win_total,
        'is_recv_back':   _is_recv_back,
        'is_early_down':  _is_early_down,
    }

    return {'sf': sf, 'cond': cond, 'line': line, 'meta': player_meta}


# -- accessors the engine calls (read from the prebuilt profile) -----------------
def skill_flags(prof):
    return prof['sf']


def line(prof):
    return prof['line']


# -- per-week activation (the legacy build_weeks body, verbatim) -----------------
# RB needs `activate` (not static conditions) because the per-week loop appends PACE/SCRIPT
# flags inline and because a lit condition with mult==1.0 contributes to flags/lit but not
# to grading. We return a `mults` list of the SAME length as `lit` (1.0 placeholders where
# the legacy did not append a multiplier), so engine's len(mults) lit-count == legacy
# len(lit_f), and grading via boom_lib.prob is identical (1.0 is a no-op).
def activate(prof, base, skill_flags, opp_d, week_ctx):
    conditions = prof['cond']
    meta = prof['meta']

    has_tenv = meta.get('has_tenv', False)
    own_pace_pctl = meta.get('own_pace_pctl', 0)
    own_win_total = meta.get('own_win_total', 0)
    is_recv_back = meta.get('is_recv_back', False)
    is_early_down = meta.get('is_early_down', False)

    home = bool(week_ctx.get('home'))
    dome = bool(week_ctx.get('dome'))
    opp = week_ctx.get('opp')

    opp_def = opp_d                               # = de.get(opp, {})
    opp_tenv = TENV.get(opp, {}) if has_tenv else {}

    mults = []
    lit_f = []

    for cond_label, fn in conditions:
        try:
            lit, mult = fn(opp_def, home, dome)
        except Exception:
            lit, mult = False, 1.0
        if lit:
            lit_f.append(cond_label)
            # legacy: only appends mult when mult != 1.0. We pad with 1.0 to keep
            # len(mults)==len(lit_f) for engine's lit count; 1.0 is a prob() no-op.
            if mult != 1.0:
                mults.append(mult)
            else:
                mults.append(1.0)

    # ── EXTRA SIGNAL: PACE (per week) ──────────────────────────────────────────────
    if has_tenv and opp_tenv:
        opp_pace = opp_tenv.get('pace_pctl', 50) or 50
        if own_pace_pctl >= 65 and opp_pace >= 50:
            lit_f.append("PACE fast game (own {:.0f}pct + opp {:.0f}pct -> more plays/touches)".format(
                own_pace_pctl, opp_pace))
            mults.append(1.07)
        elif own_pace_pctl <= 35 and opp_pace <= 35:
            lit_f.append("PACE slow game (own {:.0f}pct + opp {:.0f}pct -> fewer snaps)".format(
                own_pace_pctl, opp_pace))
            mults.append(0.95)

    # ── EXTRA SIGNAL: SCRIPT (per week — the big RB lever) ─────────────────────────
    if has_tenv and opp_tenv:
        opp_wt = opp_tenv.get('win_total', 0) or 0
        d = own_win_total - opp_wt
        if d >= 2.5:
            if is_early_down or (not is_recv_back):
                lit_f.append("SCRIPT big fav d={:.1f} -> early-down/GL back x1.12 (clock-kill carries)".format(d))
                mults.append(1.12)
            else:
                lit_f.append("SCRIPT big fav d={:.1f} -> recv back neutral (clock-kill vs check-down offset)".format(d))
                # legacy appends NO mult here; pad with 1.0 so lit count matches.
                mults.append(1.0)
        elif d <= -2.5:
            if is_recv_back:
                lit_f.append("SCRIPT underdog d={:.1f} -> recv back x1.08 (check-down volume when trailing)".format(d))
                mults.append(1.08)
            elif is_early_down:
                lit_f.append("SCRIPT underdog d={:.1f} -> early-down back x0.90 (game-scripted out of carries)".format(d))
                mults.append(0.90)
            else:
                lit_f.append("SCRIPT underdog d={:.1f} -> mixed-role back, mild carry suppression x0.95".format(d))
                mults.append(0.95)

    return lit_f, mults, len(conditions)


# -- engine optional hooks (see flagkit/engine.py) --------------------------------
def adp(v):
    # RB stores adp rounded to 2 decimals (FA/no-adp -> 999); other positions store raw.
    return round((v.get('adp') or 999), 2)


def bye_of(prof):
    # RB carries the player's total flag count on BYE weeks (DST/QB use 0).
    return len(prof['cond'])


def empty_schedule(prof):
    # Free-agent RBs (empty schedule) get 18 BYE sentinel weeks, of = bye_of.
    return 'BYE'
