#!/usr/bin/env python3
"""
build_flags_RB.py  --  player-by-player, flag-based RB ceiling (boom) model.
REBUILT: exhausts all populated RB fields; avg >=3.0 skill flags per player.

DATA AVAILABILITY (verified):
  POPULATED: usage.{carry_pg,carry_share,tgt_share,ypt,ypc,catch_rate,dk_pg}
             fus.{explosive_pctl,run_eff_pctl,oline_pctl,yac_pctl,rush_eff_pctl,
                  boom_pctl,ceiling_pctl,value_pctl,spike_pctl,matchup_pctl,adv_pctl}
  EMPTY (null for RBs): rush_share, tgt_pg, rz_share, routes_pg, rec_eff_pctl,
                        separation_pctl, adot.*, yaco.*, sis.* (only 4 RBs)

FLAG RULES (8 from brief + 8 extended from populated fus fields):
  1  Workhorse volume        carry_pg>=13 OR carry_share>=0.45
  2  Explosive / big-play    explosive_pctl>=60 OR ypc>=4.6 OR rush_eff_pctl>=70
  3  Receiving back          tgt_share>=0.10 OR ypt>=6.5
  4  Goal-line / TD proxy    carry_share>=0.45 AND (boom_pctl>=55 OR dk_pg>=13)
  5  O-line / run-scheme     oline_pctl>=60 OR run_eff_pctl>=65
  6  Contact / YAC           yac_pctl>=65
  7  Pass-down / satellite   tgt_share>=0.10 AND carry_share<=0.40
  8  Contingent bell-cow     carry_share<0.30 AND (explosive_pctl>=70 OR ceiling_pctl>=60)
  9  Spike / variance ceiling spike_pctl>=55
  10 Advanced value leader   adv_pctl>=65 AND value_pctl>=65
  11 Boom-week concentration boom_pctl>=60 AND ceiling_pctl>=55
  12 Run-efficiency grinder  rush_eff_pctl>=60 AND ypc>=4.3  (no expl flag already)
  13 High scoring floor      dk_pg>=12 AND (carry_pg>=8 OR carry_share>=0.28)
  14 Efficient receiving      ypt>=5.0 AND catch_rate>=0.78 AND tgt_share>=0.05
  15 Matchup-proof value      matchup_pctl>=60 AND adv_pctl>=55
  16 Matchup-favored (alone)  matchup_pctl>=65 (standalone)
Safety net: csh>=0.25 OR tgt>=0.08 => force >=3 flags using best available
"""
import json, os
from boom_lib import load, players, reg_base, prob, label, write, cap, SWING

sm, gl, sch, de, bd = load()
posbase  = bd['posbase']
POS_BASE = posbase['RB']   # ~0.187

# EXTRA SIGNALS: team environment lookup (opponent env per week)
_TENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'boom', 'team_env.json')
TENV = json.load(open(_TENV_PATH))


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


def build_base(v):
    rb = reg_base(v, posbase)
    if rb is not None and (v.get('n_games') or 0) >= 4:
        return rb, True
    cp = sg(v, 'fus', 'ceiling_pctl') or 50
    b  = POS_BASE * (0.75 + 0.50 * cp / 100.0)
    return round(cap(b, 0.06, 0.45), 3), False


def empirical(key):
    games  = gl.get(key, [])
    active = [g for g in games if (g.get('proj') or 0) >= 8]
    if not active:
        return "insufficient history (<4 active games)"
    n  = len(active)
    bo = [g for g in active if g.get('boom')]
    nb = len(bo)
    if nb == 0:
        return "0 ceiling games in {} active (proj>=8); no clustering signal".format(n)
    home_b   = sum(1 for g in bo if g.get('home'))
    dome_b   = sum(1 for g in bo if g.get('dome'))
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


def build_player(key, v):
    u      = v.get('usage') or {}
    fus    = v.get('fus')   or {}
    sis    = v.get('sis')   or {}
    adv2   = v.get('adv2')       # None for rookies / no 2-season history
    chart2 = v.get('chart2')     # None for rookies / no 2-season charting
    tenv_own = v.get('team_env') or {}   # own team environment (may be {})

    carry_pg    = u.get('carry_pg')    or 0
    carry_share = u.get('carry_share') or 0
    tgt_share   = u.get('tgt_share')   or 0
    catch_rate  = u.get('catch_rate')  or 0
    ypt         = u.get('ypt')         or 0
    ypc         = u.get('ypc')         or 0
    dk_pg       = u.get('dk_pg')       or 0

    explosive   = fus.get('explosive_pctl')  or 0
    run_eff     = fus.get('run_eff_pctl')    or 0
    rush_eff    = fus.get('rush_eff_pctl')   or 0
    yac_pctl    = fus.get('yac_pctl')        or 0
    oline_pctl  = fus.get('oline_pctl')      or 0
    boom_pctl   = fus.get('boom_pctl')       or 0
    ceiling_p   = fus.get('ceiling_pctl')    or 50
    value_pctl  = fus.get('value_pctl')      or 0
    spike_pctl  = fus.get('spike_pctl')      or 0
    matchup_p   = fus.get('matchup_pctl')    or 0
    adv_pctl    = fus.get('adv_pctl')        or 0

    mtf_att     = sg(sis, 'MTF_att')
    success     = sg(sis, 'success')
    tgts_g_sis  = sg(sis, 'tgts_g')
    rush_fd_att = sg(sis, 'rush_fd_att')

    # 2-season (2024+2025) advanced values — prefer over single-season when present
    has_adv2 = adv2 is not None
    if has_adv2:
        a2_g           = adv2.get('g')           or 0
        a2_carry_share = adv2.get('carry_share')  or 0   # 0-100 scale
        a2_ypc         = adv2.get('ypc')          or 0
        a2_rush_pg     = adv2.get('rush_pg')      or 0
        a2_tgt_share   = adv2.get('tgt_share')    or 0   # 0-100 scale
        a2_ypt         = adv2.get('ypt')          or 0
        a2_rec_pg      = adv2.get('rec_pg')       or 0
        a2_td_pg       = adv2.get('td_pg')        or 0
        a2_yptouch     = adv2.get('yptouch')      or 0

    # 2-season (2024+2025) FantasyPoints RUSHING charting — prefer for charting-based flags
    # Thresholds calibrated to 65 RBs w/ chart2 (p60/p70 distribution):
    #   exp_run p60=4.8%, p70=5.4%; mtf_att p60=0.16, p70=0.17; yaco_att p60=2.41, p70=2.48
    #   ybco_att p60=2.05, p70=2.17; success p60=51, p70=52; i5_pct p60=39.2, p70=44.9; td_rate p60=3.5, p70=4.1
    has_chart2 = chart2 is not None
    if has_chart2:
        _b             = chart2.get('blend') or {}
        c2_g           = _b.get('g')        or 0
        c2_exp_run     = _b.get('exp_run')   or 0   # explosive-run %
        c2_mtf_att     = _b.get('mtf_att')   or 0   # missed-tackles forced / att
        c2_yaco_att    = _b.get('yaco_att')  or 0   # yards after contact / att
        c2_ybco_att    = _b.get('ybco_att')  or 0   # yards before contact / att (O-line / blocking)
        c2_success     = _b.get('success')   or 0   # success rate %
        c2_stuff       = _b.get('stuff')     or 0   # stuff rate %
        c2_i5_pct      = _b.get('i5_pct')   or 0   # inside-5 carry share %
        c2_td_rate     = _b.get('td_rate')   or 0   # TD rate %
        c2_ypc         = _b.get('ypc')       or 0   # yards per carry

    sf   = []
    cond = []
    seen = set()

    def add(lbl, fn):
        if lbl not in seen:
            seen.add(lbl)
            cond.append((lbl, fn))

    # FLAG 1: WORKHORSE VOLUME
    # Use 2-yr carry_share/rush_pg thresholds when adv2 is present
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
            lit  = tier == 'SOFT' or runp <= 35
            mult = 1.35 if lit else (0.72 if tier == 'TOUGH' and runp >= 70 else 1.0)
            return lit, mult
        add("soft run-D (workhorse volume)", _wh_soft)

        def _rf_wh(od, home, dome):
            covp = di(od, 'covp'); runp = di(od, 'runp')
            lit  = covp >= 60 and runp <= 45
            return lit, 1.18 if lit else 1.0
        add("run-funnel (workhorse volume surge)", _rf_wh)

        def _ps_wh(od, home, dome):
            tier = od.get('tiers', {}).get('RB', 'AVG')
            lit  = home and tier != 'TOUGH'
            return lit, 1.12 if lit else 1.0
        add("positive script (home win = 4th-qtr carries)", _ps_wh)

    # FLAG 2: EXPLOSIVE / BIG-PLAY CEILING
    # When chart2 present: use exp_run + mtf_att + yaco_att (true explosive backs force MTF + rip
    # explosive runs + gain after contact). Thresholds: exp_run>=5.5%, mtf_att>=0.17, yaco_att>=2.45
    # When chart2 absent: fall back to adv2/single-season ypc + explosive pctl + rush_eff.
    if has_chart2:
        f2 = (c2_exp_run >= 5.5 or c2_mtf_att >= 0.17 or c2_yaco_att >= 2.45 or explosive >= 60)
    elif has_adv2:
        f2 = (explosive >= 60 or a2_ypc >= 4.6 or rush_eff >= 70)
    else:
        f2 = (explosive >= 60 or ypc >= 4.6 or rush_eff >= 70)
    if f2:
        parts = []
        if has_chart2 and c2_g > 0:
            # Primary citation: 2-yr FP charting — the most informative source
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
            lit  = tier == 'SOFT' or runp <= 35
            mult = 1.35 if lit else (0.72 if tier == 'TOUGH' and runp >= 70 else 1.0)
            return lit, mult
        add("soft run-D (explosive ceiling)", _sr_expl)

        def _pf_expl(od, home, dome):
            runp = di(od, 'runp'); covp = di(od, 'covp')
            lit  = runp >= 60 and covp <= 45
            return lit, 1.18 if lit else 1.0
        add("pass-funnel (light box -> big runs)", _pf_expl)

        def _dome_expl(od, home, dome):
            return dome, 1.08 if dome else 1.0
        add("dome (explosive ceiling)", _dome_expl)

    # FLAG 3: RECEIVING BACK / PPR CEILING
    # Use 2-yr tgt_share/rec_pg/ypt for threshold + citation when adv2 exists
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
            lit  = runp >= 60 and covp <= 45
            return lit, 1.18 if lit else 1.0
        add("pass-funnel (dump-off lanes)", _pf_recv)

        def _neg_script(od, home, dome):
            covp = di(od, 'covp')
            tier = od.get('tiers', {}).get('RB', 'AVG')
            lit  = (not home and covp >= 60) or tier == 'TOUGH'
            return lit, 1.12 if lit else 1.0
        add("neg-script (trailing -> check-downs)", _neg_script)

        def _man_rb(od, home, dome):
            manp = di(od, 'manp')
            lit  = manp >= 68
            return lit, 1.18 if lit else 1.0
        add("man-cov (RB-on-LB mismatch)", _man_rb)

    # FLAG 4: GOAL-LINE / TD PROXY (rz_share null for RBs)
    # When chart2 present: use i5_pct (inside-5 carry share — cleanest goal-line signal) + td_rate.
    # Thresholds: i5_pct>=39% (p60), td_rate>=3.5% (p60). When chart2 absent: fall back to
    # adv2 carry_share / single-season carry_share + boom_pctl.
    if has_chart2:
        f4 = (c2_i5_pct >= 39 or c2_td_rate >= 3.5) and (boom_pctl >= 55 or dk_pg >= 13)
    elif has_adv2:
        f4 = (a2_carry_share >= 45 and (boom_pctl >= 55 or dk_pg >= 13))
    else:
        f4 = (carry_share >= 0.45 and (boom_pctl >= 55 or dk_pg >= 13))
    if f4:
        parts = []
        if has_chart2 and c2_g > 0:
            # Primary citation: 2-yr FP charting — i5_pct is the cleanest goal-line signal
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
            lit  = tier == 'SOFT' or runp <= 40
            mult = 1.30 if lit else (0.70 if tier == 'TOUGH' else 1.0)
            return lit, mult
        add("soft run-D (goal-line TD ceiling)", _gl_soft)

        def _rf_gl(od, home, dome):
            covp = di(od, 'covp'); runp = di(od, 'runp')
            lit  = covp >= 60 and runp <= 45
            return lit, 1.18 if lit else 1.0
        add("run-funnel (goal-line volume)", _rf_gl)

    # FLAG 5: O-LINE / RUN-SCHEME EFFICIENCY
    # When chart2 present: use success + ypc + ybco_att (ybco = yds before contact = blocking quality).
    # Thresholds: success>=51% (p60), ybco_att>=2.05 (p60), ypc>=4.44 (p60).
    # When chart2 absent: fall back to oline_pctl / run_eff fusion percentiles.
    if has_chart2:
        f5 = (c2_success >= 51 or c2_ybco_att >= 2.05 or oline_pctl >= 60 or run_eff >= 65)
    else:
        f5 = (oline_pctl >= 60 or run_eff >= 65)
    if f5:
        parts = []
        if has_chart2 and c2_g > 0:
            # Primary citation: 2-yr FP charting — ybco_att directly measures blocking quality
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
            lit  = tier == 'SOFT' or runp <= 30
            mult = 1.30 if lit else (0.75 if tier == 'TOUGH' and runp >= 70 else 1.0)
            return lit, mult
        add("soft run-D (O-line payoff)", _oline_soft)

        def _pf_oline(od, home, dome):
            runp = di(od, 'runp'); covp = di(od, 'covp')
            lit  = runp >= 60 and covp <= 45
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
            lit  = tier == 'SOFT' or runp <= 35
            mult = 1.20 if lit else (0.78 if tier == 'TOUGH' else 1.0)
            return lit, mult
        add("soft run-D (YAC ceiling)", _soft_yac)

        def _zone_yac(od, home, dome):
            manp = di(od, 'manp')
            lit  = manp <= 32
            return lit, 1.12 if lit else 1.0
        add("zone-D (open field = YAC lanes)", _zone_yac)

    # FLAG 6B: CONTACT-BALANCE (chart2 only) — yaco_att + mtf_att both above average
    # These two together define a back who breaks tackles AND finishes runs through contact;
    # distinct from the fusion yac_pctl which only covers catches. Only fire when chart2 present
    # and chart2 not already the lead citation in Flag 2 (avoid pure duplication), but they can
    # both exist — explosive is about home-run plays; contact-balance is about every-play grind.
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
            lit  = tier == 'SOFT' or runp <= 35
            mult = 1.20 if lit else (0.78 if tier == 'TOUGH' else 1.0)
            return lit, mult
        add("soft run-D (contact-balance ceiling)", _cb_soft)

        def _cb_zone(od, home, dome):
            manp = di(od, 'manp')
            lit  = manp <= 32
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
            lit  = runp >= 60 and covp <= 45
            return lit, 1.18 if lit else 1.0
        add("pass-funnel (satellite role)", _sat_pf)

        def _sat_neg(od, home, dome):
            covp = di(od, 'covp')
            lit  = not home and covp >= 55
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
            lit  = tier == 'SOFT' or runp <= 40
            mult = 1.25 if lit else (0.80 if tier == 'TOUGH' else 1.0)
            return lit, mult
        add("soft run-D (handcuff potential)", _hc_soft)

    # FLAG 9: SPIKE / VARIANCE CEILING (threshold 55, all 104 RBs have spike_pctl)
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
            lit  = tier == 'SOFT' or runp <= 35
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
            lit  = tier == 'SOFT' or runp <= 35
            mult = 1.25 if lit else (0.78 if tier == 'TOUGH' and runp >= 68 else 1.0)
            return lit, mult
        add("soft run-D (elite value payoff)", _adv_soft)

        def _matchup_adv(od, home, dome):
            runp = di(od, 'runp')
            lit  = runp <= 40
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
            lit  = tier == 'SOFT' or runp <= 40
            mult = 1.25 if lit else (0.75 if tier == 'TOUGH' else 1.0)
            return lit, mult
        add("soft run-D (boom-week trigger)", _boom_soft)

        def _pos_boom(od, home, dome):
            tier = od.get('tiers', {}).get('RB', 'AVG')
            lit  = home and tier != 'TOUGH'
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
            lit  = tier == 'SOFT' or runp <= 35
            mult = 1.20 if lit else (0.80 if tier == 'TOUGH' and runp >= 68 else 1.0)
            return lit, mult
        add("soft run-D (efficiency grinder)", _grind_soft)

        def _rf_grind(od, home, dome):
            covp = di(od, 'covp'); runp = di(od, 'runp')
            lit  = covp >= 55 and runp <= 45
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
            lit  = tier == 'SOFT' or runp <= 35
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
            lit  = runp >= 60 and covp <= 45
            return lit, 1.18 if lit else 1.0
        add("pass-funnel (efficient receiver)", _eff_recv_pf)

        def _eff_recv_neg(od, home, dome):
            covp = di(od, 'covp')
            lit  = not home and covp >= 55
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
            lit  = tier == 'SOFT' or runp <= 40
            mult = 1.20 if lit else (0.82 if tier == 'TOUGH' else 1.0)
            return lit, mult
        add("soft run-D (matchup-proof value)", _matchup_soft)

    # FLAG 16: MATCHUP-FAVORED (standalone, rescues backs with great schedule/matchup model)
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
            lit  = tier == 'SOFT' or runp <= 40
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
            lit  = tier == 'SOFT'
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
                lit  = tier == 'SOFT' or runp <= 40
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
                lit  = tier == 'SOFT' or runp <= 40
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
                lit  = tier == 'SOFT' or runp <= 35
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
                lit  = tier == 'SOFT' or runp <= 40
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
                lit  = tier == 'SOFT' or runp <= 40
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
            lit  = tier == 'SOFT' or runp <= 40
            mult = 1.15 if lit else (0.80 if tier == 'TOUGH' else 1.0)
            return lit, mult
        add("soft run-D (situational)", _sit_soft)

        def _sit_pf(od, home, dome):
            runp = di(od, 'runp'); covp = di(od, 'covp')
            lit  = runp >= 60 and covp <= 45
            return lit, 1.10 if lit else 1.0
        add("pass-funnel (situational)", _sit_pf)

    # ── EXTRA SIGNAL: ENV / SCORING ENVIRONMENT (skill flag + per-week condition) ──────────
    # own env_idx tells us how often this offense scores; >=70 is a standing ceiling raiser
    own_env_idx   = tenv_own.get('env_idx', 0) or 0
    own_pace_pctl = tenv_own.get('pace_pctl', 0) or 0
    own_win_total = tenv_own.get('win_total', 0) or 0
    has_tenv      = bool(tenv_own)   # False for the ~5 RBs without team_env

    if has_tenv and own_env_idx >= 70:
        sf.append({
            "f": "High-scoring offense (ENV signal)",
            "d": "env_idx {:.0f}/100 — top-tier scoring environment (>=70); more possessions, more goal-line chances".format(own_env_idx),
            "amp": "soft run-D / shootout setup (opp covp<=35) / positive script (favored + home)"
        })
        # per-week ENV shootout: own env_idx>=65 AND opp soft pass-D (covp<=35)
        def _env_shootout(od, home, dome, _ei=own_env_idx):
            covp = di(od, 'covp')
            lit  = _ei >= 65 and covp <= 35
            return lit, 1.06 if lit else 1.0
        add("ENV shootout (own env_idx>=65 + opp soft pass-D)", _env_shootout)

    elif has_tenv and own_env_idx >= 65:
        # env flag fires per-week via condition even if skill flag threshold not met
        def _env_shootout(od, home, dome, _ei=own_env_idx):
            covp = di(od, 'covp')
            lit  = _ei >= 65 and covp <= 35
            return lit, 1.06 if lit else 1.0
        add("ENV shootout (own env_idx>=65 + opp soft pass-D)", _env_shootout)

    # ── RB role classification for SCRIPT (used by per-week script condition) ──────────────
    # Receiving back: tgt_share >= 0.12 OR (tgt_share > 0 and tgt_share/carry_share > 0.25)
    # Early-down-only: tgt_share < 0.09 AND carry_share >= 0.45
    _is_recv_back = (tgt_share >= 0.12 or
                     (carry_share > 0 and tgt_share > 0 and tgt_share / carry_share > 0.25))
    _is_early_down = (tgt_share < 0.09 and carry_share >= 0.45)

    # ── SUPPRESSORS (always added) ──────────────────────────────────────────────────────────
    def _tough_run(od, home, dome):
        tier = od.get('tiers', {}).get('RB', 'AVG')
        runp = di(od, 'runp')
        lit  = tier == 'TOUGH' and runp >= 68
        return lit, 0.72 if lit else 1.0
    add("TOUGH RB tier (run-D suppressor)", _tough_run)

    if tgt_share < 0.09 and carry_share >= 0.45 and carry_pg >= 10.0:
        def _neg_ed(od, home, dome):
            covp = di(od, 'covp')
            lit  = not home and covp >= 65
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
    return sf, cond, line, player_meta


def build_weeks(key, v, conditions, player_meta=None):
    team     = v.get('team', '')
    schedule = sch.get(team, [])
    base_rate, hist = build_base(v)
    weeks_out = []

    if player_meta is None:
        player_meta = {}

    has_tenv      = player_meta.get('has_tenv', False)
    own_env_idx   = player_meta.get('own_env_idx', 0)
    own_pace_pctl = player_meta.get('own_pace_pctl', 0)
    own_win_total = player_meta.get('own_win_total', 0)
    is_recv_back  = player_meta.get('is_recv_back', False)
    is_early_down = player_meta.get('is_early_down', False)

    if not schedule:
        for wk in range(1, 19):
            weeks_out.append({"wk": wk, "opp": "BYE", "home": None, "dome": None,
                               "p": None, "lab": "BYE", "lit": 0,
                               "of": len(conditions), "flags": []})
        return weeks_out

    for wk_entry in schedule:
        wk   = wk_entry.get('wk')
        opp  = wk_entry.get('opp')
        home = wk_entry.get('home')
        dome = wk_entry.get('dome')

        if opp == 'BYE':
            weeks_out.append({"wk": wk, "opp": "BYE", "home": None, "dome": None,
                               "p": None, "lab": "BYE", "lit": 0,
                               "of": len(conditions), "flags": []})
            continue

        opp_def  = de.get(opp, {})
        opp_tenv = TENV.get(opp, {}) if has_tenv else {}

        mults = []
        lit_f = []

        for cond_label, fn in conditions:
            try:
                lit, mult = fn(opp_def, bool(home), bool(dome))
            except Exception:
                lit, mult = False, 1.0
            if lit:
                lit_f.append(cond_label)
                if mult != 1.0:
                    mults.append(mult)

        # ── EXTRA SIGNAL: PACE (per week) ──────────────────────────────────────────────
        # own pace_pctl>=65 AND opp pace_pctl>=50 -> fast game, more plays -> more touches
        # both<=35 -> slow game, fewer snaps
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
        # d = own win_total - opp win_total
        # Big favorite (d>=2.5): early-down/GL backs x1.12 (clock-kill carries + goal-line)
        # Underdog (d<=-2.5): receiving backs x1.08 (check-down volume); early-down x0.90
        if has_tenv and opp_tenv:
            opp_wt = opp_tenv.get('win_total', 0) or 0
            d = own_win_total - opp_wt
            if d >= 2.5:
                if is_early_down or (not is_recv_back):
                    lit_f.append("SCRIPT big fav d={:.1f} -> early-down/GL back x1.12 (clock-kill carries)".format(d))
                    mults.append(1.12)
                else:
                    # Receiving back: carry volume neutral but note it (check-downs offset clock-kill)
                    lit_f.append("SCRIPT big fav d={:.1f} -> recv back neutral (clock-kill vs check-down offset)".format(d))
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

        p   = prob(base_rate, mults)
        lab = label(p, base_rate)

        weeks_out.append({"wk": wk, "opp": opp, "home": bool(home), "dome": bool(dome),
                          "p": int(round(p * 100)), "lab": lab,
                          "lit": len(lit_f), "of": len(conditions), "flags": lit_f})

    return weeks_out


def main():
    keys = players(sm, 'RB')
    data = {}

    for key in keys:
        v  = sm[key]
        sf, cond, line, pmeta = build_player(key, v)
        base_rate, hist = build_base(v)
        weeks = build_weeks(key, v, cond, player_meta=pmeta)

        data[key] = {
            "name":        v.get('name', key),
            "pos":         "RB",
            "team":        v.get('team', ''),
            "adp":         round(v.get('adp') or 999, 2),
            "base":        int(round(base_rate * 100)),
            "hist":        hist,
            "n_games":     v.get('n_games', 0),
            "boom_games":  v.get('boom_games', 0),
            "skill_flags": sf,
            "line":        line,
            "weeks":       weeks,
            "empirical":   empirical(key)
        }

    write('RB', data)

    print("\n" + "="*64)
    print("VERIFICATION REPORT")
    print("="*64)
    n_tot  = len(data)
    n_hist = sum(1 for v in data.values() if v['hist'])
    avg_sf = sum(len(v['skill_flags']) for v in data.values()) / n_tot
    bad_wk = [k for k, v in data.items() if len(v['weeks']) != 18]
    lt3    = [k for k, v in data.items() if len(v['skill_flags']) < 3]

    print("  Total RBs:             {}".format(n_tot))
    print("  With hist (>=4 g):     {}".format(n_hist))
    print("  Without hist:          {}".format(n_tot - n_hist))
    print("  Avg skill_flags:       {:.2f}  (target >=3.0)".format(avg_sf))
    print("  Players with <3 flags: {}".format(len(lt3)))
    if lt3:
        real_role_lt3 = []
        bench_lt3 = []
        for k in lt3:
            u = sm[k].get('usage',{}) or {}
            csh = u.get('carry_share',0) or 0
            tgt = u.get('tgt_share',0) or 0
            if csh >= 0.25 or tgt >= 0.08:
                real_role_lt3.append(k)
            else:
                bench_lt3.append(k)
        if real_role_lt3:
            print("    REAL-ROLE under-3: {}".format(real_role_lt3))
        print("    Deep-bench under-3 (expected): {}".format(len(bench_lt3)))
    print("  Players != 18 weeks:   {} {}".format(len(bad_wk), bad_wk if bad_wk else "OK"))

    from collections import Counter
    dist = Counter(len(v['skill_flags']) for v in data.values())
    print("  Flag distribution:     {}".format(dict(sorted(dist.items()))))

    _path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'boom', 'flags_RB.json')
    _rl   = json.load(open(_path))
    print("  JSON reload OK:        {} players".format(len(_rl)))

    n_adv2_avail = sum(1 for k in keys if sm[k].get('adv2') is not None)
    n_adv2_cited = 0
    for k in keys:
        if sm[k].get('adv2') is not None and k in data:
            for sf_item in data[k]['skill_flags']:
                if '2yr' in sf_item.get('d', ''):
                    n_adv2_cited += 1
                    break
    print("  RBs with adv2 data:    {}".format(n_adv2_avail))
    print("  RBs citing adv2:       {}".format(n_adv2_cited))

    n_c2_avail = sum(1 for k in keys if sm[k].get('chart2') is not None)
    n_c2_cited = 0
    for k in keys:
        if sm[k].get('chart2') is not None and k in data:
            for sf_item in data[k]['skill_flags']:
                if 'FP charting' in sf_item.get('d', ''):
                    n_c2_cited += 1
                    break
    print("  RBs with chart2 data:  {}".format(n_c2_avail))
    print("  RBs citing chart2:     {}".format(n_c2_cited))

    # ENV / PACE / SCRIPT citations
    n_env_skill  = sum(1 for v in data.values()
                       for sf_item in v['skill_flags']
                       if 'ENV signal' in sf_item.get('f', '') or 'env_idx' in sf_item.get('d', ''))
    n_env_week   = sum(1 for v in data.values()
                       for w in v['weeks']
                       for fl in w.get('flags', [])
                       if 'ENV shootout' in fl)
    n_pace_week  = sum(1 for v in data.values()
                       for w in v['weeks']
                       for fl in w.get('flags', [])
                       if fl.startswith('PACE'))
    n_script_fav = sum(1 for v in data.values()
                       for w in v['weeks']
                       for fl in w.get('flags', [])
                       if 'SCRIPT big fav' in fl)
    n_script_dog = sum(1 for v in data.values()
                       for w in v['weeks']
                       for fl in w.get('flags', [])
                       if 'SCRIPT underdog' in fl)
    print()
    print("  ENV skill flags:       {}  (RBs with env_idx>=70)".format(n_env_skill))
    print("  ENV week citations:    {}  (weeks: own env>=65 + opp covp<=35)".format(n_env_week))
    print("  PACE week citations:   {}  (fast/slow game weeks)".format(n_pace_week))
    print("  SCRIPT fav citations:  {}  (d>=2.5 early-down/GL backs x1.12)".format(n_script_fav))
    print("  SCRIPT dog citations:  {}  (d<=-2.5 recv x1.08 / early x0.90)".format(n_script_dog))

    def print_player(sp, lbl):
        if sp not in data:
            print("\n!! {} not found".format(sp)); return
        e  = data[sp]
        u  = sm[sp].get('usage') or {}
        fu = sm[sp].get('fus')   or {}
        a2 = sm[sp].get('adv2')
        c2 = sm[sp].get('chart2')
        te = sm[sp].get('team_env') or {}
        print("\n" + "="*64)
        print("SPOT CHECK: {}  {}".format(e['name'], lbl))
        print("="*64)
        print("  base:{}%  hist:{}  n_games:{}  boom_games:{}".format(
              e['base'], e['hist'], e['n_games'], e['boom_games']))
        carry_pg_v = u.get('carry_pg', 0) or 0
        carry_sh_v = u.get('carry_share', 0) or 0
        tgt_sh_v   = u.get('tgt_share', 0) or 0
        dk_pg_v    = u.get('dk_pg', 0) or 0
        print("  carry_pg={:.1f}  carry_share={:.3f}  tgt_share={:.3f}  dk_pg={:.1f}".format(
            carry_pg_v, carry_sh_v, tgt_sh_v, dk_pg_v))
        if te:
            print("  team_env: env_idx={} pace_pctl={} win_total={}".format(
                te.get('env_idx'), te.get('pace_pctl'), te.get('win_total')))
            _tgt = tgt_sh_v; _csh = carry_sh_v
            _recv = _tgt >= 0.12 or (_csh > 0 and _tgt > 0 and _tgt/_csh > 0.25)
            _early = _tgt < 0.09 and _csh >= 0.45
            print("  role: is_recv={} is_early_down={}".format(_recv, _early))
        print("  skill_flags ({}):".format(len(e['skill_flags'])))
        for s in e['skill_flags']:
            print("    [{}]".format(s['f']))
        print("  line: {}".format(e['line'][:110]))

        smash = sorted([w for w in e['weeks'] if w['lab']=='SMASH'], key=lambda x:-x['p'])
        tough = sorted([w for w in e['weeks'] if w['lab']=='TOUGH'], key=lambda x:x['p'])
        good  = sorted([w for w in e['weeks'] if w['lab'] in ('SMASH','GOOD')], key=lambda x:-x['p'])

        if smash:
            w = smash[0]
            print("\n  BEST SMASH: wk{} vs {} (home={},dome={}) p={}%  lit={}/{}".format(
                  w['wk'],w['opp'],w['home'],w['dome'],w['p'],w['lit'],w['of']))
            print("    lit flags: {}".format(w['flags'][:5]))
        elif good:
            w = good[0]
            print("\n  BEST GOOD:  wk{} vs {} (home={},dome={}) p={}%  lit={}/{}".format(
                  w['wk'],w['opp'],w['home'],w['dome'],w['p'],w['lit'],w['of']))
            print("    lit flags: {}".format(w['flags'][:5]))
        if tough:
            w = tough[0]
            print("  TOUGHEST:   wk{} vs {} (home={},dome={}) p={}%  lit={}/{}".format(
                  w['wk'],w['opp'],w['home'],w['dome'],w['p'],w['lit'],w['of']))
            print("    lit flags: {}".format(w['flags'][:4]))

        # SCRIPT / PACE / ENV flags
        sfav = [w for w in e['weeks'] if any('SCRIPT big fav' in fl for fl in w.get('flags', []))]
        sdog = [w for w in e['weeks'] if any('SCRIPT underdog' in fl for fl in w.get('flags', []))]
        pfast= [w for w in e['weeks'] if any(fl.startswith('PACE fast') for fl in w.get('flags', []))]
        pslow= [w for w in e['weeks'] if any(fl.startswith('PACE slow') for fl in w.get('flags', []))]
        envw = [w for w in e['weeks'] if any('ENV shootout' in fl for fl in w.get('flags', []))]
        if sfav:
            w = sfav[0]
            fl = [f for f in w['flags'] if 'SCRIPT' in f]
            print("  SCRIPT FAV (wk{}): vs {} p={}%  {}".format(w['wk'],w['opp'],w['p'], fl[0][:80] if fl else ''))
        if sdog:
            w = sdog[0]
            fl = [f for f in w['flags'] if 'SCRIPT' in f]
            print("  SCRIPT DOG (wk{}): vs {} p={}%  {}".format(w['wk'],w['opp'],w['p'], fl[0][:80] if fl else ''))
        if not sfav and not sdog:
            print("  SCRIPT: no weeks with |d|>=2.5 (schedule mostly even matchups)")
        if pfast:
            w = pfast[0]
            fl = [f for f in w["flags"] if f.startswith("PACE")]
            print("  PACE FAST (wk{}): vs {} p={}%  {}".format(w['wk'],w['opp'],w['p'], fl[0][:70] if fl else ''))
        if pslow:
            w = pslow[0]
            fl = [f for f in w["flags"] if f.startswith("PACE")]
            print("  PACE SLOW (wk{}): vs {} p={}%  {}".format(w['wk'],w['opp'],w['p'], fl[0][:70] if fl else ''))
        if envw:
            w = envw[0]
            fl = [f for f in w['flags'] if 'ENV' in f]
            print("  ENV SHOOT (wk{}): vs {} p={}%  {}".format(w['wk'],w['opp'],w['p'], fl[0][:70] if fl else ''))
        print("  empirical: {}".format(e['empirical']))

    SPOTS = [
        ('david montgomery',    '[WORKHORSE]'),
        ('tony pollard',        '[EXPLOSIVE EARLY-DOWN]'),
        ('jk dobbins',          '[EXPLOSIVE HANDCUFF]'),
        ('blake corum',         '[EXPLOSIVE LOW-ROLE]'),
    ]
    ARCH = [
        ('jahmyr gibbs',        '[RECV BACK -- DET env_idx=84, big fav most weeks]'),
        ('derrick henry',       '[EARLY-DOWN -- BAL env_idx=68, big fav most weeks]'),
        ('kenneth gainwell',    '[COMMITTEE/PASS-DOWN -- PHI mixed role]'),
    ]
    ADV2_SPOTS = [
        ('jahmyr gibbs',    '[chart2: 7.9% exp-run, 0.243 MTF/att over 34g]'),
        ('saquon barkley',  '[chart2: 5.9% exp-run, 0.134 MTF/att over 32g]'),
        ('devon achane',    '[chart2: 7.4% exp-run, 0.170 MTF/att over 33g]'),
    ]

    print("\n" + "="*64)
    print("FIX PROOF -- previously thin players now >=3 flags")
    print("="*64)
    for sp, lbl in SPOTS:
        print_player(sp, lbl)

    print("\n" + "="*64)
    print("ARCHETYPE CONTRAST -- script differentiation proof")
    print("="*64)
    for sp, lbl in ARCH:
        print_player(sp, lbl)

    print("\n" + "="*64)
    print("DIFFERENTIATION SUMMARY")
    print("="*64)
    for sp, lbl in SPOTS + ARCH:
        if sp not in data: continue
        e  = data[sp]
        flags = [s['f'] for s in e['skill_flags']]
        smash_f = set()
        tough_f = set()
        for w in e['weeks']:
            if w['lab'] == 'SMASH': smash_f.update(w['flags'])
            if w['lab'] == 'TOUGH': tough_f.update(w['flags'])
        print("\n  {} {}  flags={}".format(e['name'], lbl, len(flags)))
        for f in flags:
            print("    * {}".format(f))

    print("\n" + "="*64)
    print("CHART2 SPOT CHECK -- Gibbs / Barkley / Achane")
    print("="*64)
    for sp, lbl in ADV2_SPOTS:
        print_player(sp, lbl)

    print("\n" + "="*64)
    print("Done.")


if __name__ == '__main__':
    main()
