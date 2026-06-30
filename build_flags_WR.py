#!/usr/bin/env python3
"""
build_flags_WR.py — player-by-player, flag-based WR ceiling (boom) model.
Fully exhaustive: aDOT, explosive_pctl, separation_pctl, route_eff_pctl,
yac_pctl, YACoe/MTFoe, tgt_share, TPRR/surplus_TPRR, coverage_proof_pctl,
oline_pctl, boom_pctl/ceiling_pctl, adv_pctl, YPRR/eff_combined/airyard_pct (SIS).
Each WR gets 3-6 PLAYER-SPECIFIC flags. FA/unsigned = 18 blank-week entries.
adv2 (2024+2025) used for deep/volume/YAC/TD thresholds + citations where present.
chart2 (2024+2025 FantasyPoints charting) is the BEST source for charting flags:
  - separator/route-winner: chart2.blend yprr + tprr + fr_pct + contested_pct
  - deep/vertical: chart2.blend aDOT + ay_share + deep_pct
  - YAC: chart2.blend yac_rec + mtf_rec
  - alignment context: slot_pct / wide_pct folded into man/zone amp
  Fallback to single-season fusion when chart2 is None (rookies).
EXTRA SIGNALS (this pass):
  - rz skill_flag: statmenu[k]['rz'] red-zone/TD equity (rz_tgt_share/ez_tgt_share/ez_td_pg).
  - ENV/SHOOTOUT: own team_env.env_idx>=70 noted in line; per-week x1.08 when env_idx>=65 & covp<=35.
  - PACE: per-week x1.08 own pace_pctl>=65 & opp pace_pctl>=50; x0.95 both slow (<=35).
  - SCRIPT: per-week x1.10 underdog (d<=-2.5); x0.97 big-favorite deep WR (d>=2.5).
  - COVERAGE SHELL: deep WR vs man-heavy (manp>=68) x1.10 per week.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from boom_lib import load, players, reg_base, prob, label, write, cap, SWING

sm, gl, sch, de, bd = load()
posbase  = bd['posbase']
POS_BASE = posbase['WR']         # ~0.178

# -- team environment lookup (TENV[team] = {pace_pctl, plays_pg, env_idx, off_q, win_total}) -----
_tenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'boom', 'team_env.json')
TENV = json.load(open(_tenv_path, encoding='utf-8'))

# -- defense coverage shell (REAL single/two-high per defense) ---------------
# SHELL[team] = {man, c2, c3, c4, c6, single_high, two_high, single_high_pctl}
# single_high = man% + Cover3% (one deep safety); two_high = Cover2%+4%+6%.
# Source: FantasyPoints QB Coverage Matchup (2024 charting). All 32 defenses present.
_shell_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'boom', 'defense_shell.json')
SHELL = json.load(open(_shell_path, encoding='utf-8'))

# === Branch-2 anti-overfit prune (evidence: AUDIT_OVERFIT_2026.md) ==========
# Condemned weekly multipliers are shrunk toward neutral (1.0). 2024->2025
# stability tests: WR aDOT/deep_pct -> boom SIGN-FLIPS (noise) => DROP;
# man/zone + coverage-shell + coverage-specialist split r~0.2 (man-beater tail
# retains modest signal) => DEMOTE (halve). Volume/role, efficiency (yprr/tprr),
# team pass-D tier, pass-funnel, home/dome, env/pace/script are KEEP (untouched).
# To restore the pre-prune model set both factors to 1.0.
DEEP_SHRINK = 0.0   # WR deep/aDOT ceiling: DROP (sign-flip across years)
COV_SHRINK  = 0.5   # man/zone + shell + coverage-specialist: DEMOTE (halve)
def _shr(mult, lam):
    """Shrink a multiplier toward 1.0 by factor lam (0=neutralize, 1=unchanged)."""
    return 1.0 + (mult - 1.0) * lam

# -- helper: safe float with default -----------------------------------------
def g(d, key, default=None):
    v = d.get(key, default) if d else default
    return float(v) if v is not None else default

# -- empirical gamelog analysis -----------------------------------------------
def empirical_summary(key, n_games, boom_games):
    entries = gl.get(key, [])
    if not entries:
        return f"No 2025 gamelog. Hist: {n_games} games, {boom_games} boom."
    total = len(entries)
    boom_entries = [e for e in entries if e.get('boom', 0) == 1]
    nb = len(boom_entries)
    if nb == 0:
        return f"0 boom games in {total} 2025 appearances. Insufficient sample for cluster analysis."
    home_boom = sum(1 for e in boom_entries if e.get('home'))
    dome_boom = sum(1 for e in boom_entries if e.get('dome'))
    soft_pass = sum(1 for e in boom_entries if e.get('opp_passp', 100) <= 35)
    home_all  = sum(1 for e in entries if e.get('home'))
    dome_all  = sum(1 for e in entries if e.get('dome'))
    sp_all    = sum(1 for e in entries if e.get('opp_passp', 100) <= 35)
    parts = [f"{nb}/{total} boom games"]
    if home_all > 0:
        parts.append(f"home: {home_boom}/{nb} booms ({home_boom*100//nb}% of booms, vs {home_all*100//total}% of games)")
    if dome_all > 0:
        parts.append(f"dome: {dome_boom}/{nb} booms ({dome_boom*100//nb}% of booms, vs {dome_all*100//total}% of games)")
    if sp_all > 0:
        parts.append(f"vs soft-pass (opp_passp<=35): {soft_pass}/{nb} booms")
    return "; ".join(parts) + "."

# -- WR archetype flags (player-by-player, exhaustive) -----------------------
def build_skill_flags(k, v):
    """
    Returns (flags list, activators list).
    flags: [{f, d, amp}] -- 3-6 per player, grounded in actual stat values.
    activators: tags used in the weekly loop to fire the right multipliers.
    When adv2 exists (2024+2025 advanced profile), prefer its 2-season values
    for deep/volume/YAC/TD thresholds and cite them in the flag detail.
    When chart2 exists (2024+2025 FP charting), PREFER it for charting flags:
      separator/route flag: chart2.blend yprr + tprr + fr_pct + contested_pct
      deep flag: chart2.blend aDOT + ay_share + deep_pct
      YAC flag: chart2.blend yac_rec + mtf_rec
      alignment: slot_pct / wide_pct folded into man/zone amp text
    chart2 is None for rookies; fall back to single-season fusion in that case.
    """
    fus   = v.get('fus') or {}
    adot  = v.get('adot') or {}
    sis   = v.get('sis') or {}
    yaco  = v.get('yaco') or {}
    usage = v.get('usage') or {}
    adv2  = v.get('adv2')    # 2-season advanced profile; None for rookies
    chart2= v.get('chart2')  # 2-season FP charting; None for rookies

    # -- pull chart2.blend fields (2-yr FP charting) when present ------------
    c2b = (chart2.get('blend') if chart2 else None) or {}
    c2_g            = g(c2b, 'g')           # games sampled (2yr charting)
    c2_adot         = g(c2b, 'aDOT')        # 2yr aDOT (FP charting)
    c2_tprr         = g(c2b, 'tprr')        # 2yr target rate per route (FP)
    c2_yprr         = g(c2b, 'yprr')        # 2yr yards per route run (FP)
    c2_yac_rec      = g(c2b, 'yac_rec')     # 2yr YAC per reception (FP)
    c2_yaco_rec     = g(c2b, 'yaco_rec')    # 2yr YAC over expected/rec (FP)
    c2_mtf_rec      = g(c2b, 'mtf_rec')     # 2yr missed-tackle force/rec (FP)
    c2_fr_pct       = g(c2b, 'fr_pct')      # 2yr 1st-read target % (FP)
    c2_deep_pct     = g(c2b, 'deep_pct')    # 2yr deep-target % (FP)
    c2_contested    = g(c2b, 'contested_pct')  # 2yr contested catch % (FP)
    c2_ay_share     = g(c2b, 'ay_share')    # 2yr air-yards share 0-100 (FP)
    c2_slot_pct     = g(c2b, 'slot_pct')    # 2yr slot alignment % (FP)
    c2_wide_pct     = g(c2b, 'wide_pct')    # 2yr boundary alignment % (FP)
    c2_fp_rr        = g(c2b, 'fp_rr')       # 2yr FP per route run (FP)
    has_chart2      = bool(c2b)              # True when chart2 blend present

    adot_val   = g(adot, 'aDOT')
    tprr       = g(adot, 'TPRR')
    surplus    = g(adot, 'surplus_TPRR')

    # -- pull adv2 fields (2-season) when present ----------------------------
    a2_g        = g(adv2, 'g')           # games sampled
    a2_adot     = g(adv2, 'aDOT')        # 2yr avg depth of target
    a2_ay_share = g(adv2, 'ay_share')    # 2yr air-yards share (0-100)
    a2_tgt_share= g(adv2, 'tgt_share')   # 2yr target share (0-100)
    a2_rec_pg   = g(adv2, 'rec_pg')      # 2yr receptions/game
    a2_ypt      = g(adv2, 'ypt')         # 2yr yards per target
    a2_td_pg    = g(adv2, 'td_pg')       # 2yr TDs/game
    a2_yptouch  = g(adv2, 'yptouch')     # 2yr yards per touch

    sep_p     = g(fus, 'separation_pctl', 50)
    reff_p    = g(fus, 'route_eff_pctl', 50)
    yac_p     = g(fus, 'yac_pctl', 50)
    expl_p    = g(fus, 'explosive_pctl', 50)
    covproof  = g(fus, 'coverage_proof_pctl', 50)
    rec_eff   = g(fus, 'rec_eff_pctl', 50)
    oline_p   = g(fus, 'oline_pctl', 50)
    ceil_p    = g(fus, 'ceiling_pctl', 50)
    boom_p    = g(fus, 'boom_pctl', 50)
    matchup_p = g(fus, 'matchup_pctl', 50)
    adv_p     = g(fus, 'adv_pctl', 50)
    value_p   = g(fus, 'value_pctl', 50)
    spike_p   = g(fus, 'spike_pctl', 50)

    yacoe     = g(yaco, 'YACoe')
    mtfoe     = g(yaco, 'MTFoe')

    tgt_share = g(usage, 'tgt_share', 0) or 0
    catch_r   = g(usage, 'catch_rate', 0) or 0
    ypt       = g(usage, 'ypt', 0) or 0
    dk_pg     = g(usage, 'dk_pg', 0) or 0

    yprr        = g(sis, 'YPRR')
    airyard_p   = g(sis, 'airyard_pct')
    eff_comb    = g(sis, 'eff_combined')
    tgt_share_w = g(sis, 'tgt_share_w')
    fp_rr       = g(sis, 'FP_RR')

    flags = []
    activators = []

    # -- FLAG 1: Deep / vertical / air-yards threat --------------------------
    # BEST source: chart2.blend aDOT + ay_share + deep_pct (2-yr FP charting).
    # Fallback when chart2 absent: adv2 aDOT + ay_share, then single-season.
    if has_chart2:
        # chart2 thresholds: aDOT p75=12.9, ay_share p50=26, deep_pct p75=22
        is_deep      = c2_adot is not None and c2_adot >= 12.0
        is_ay_heavy  = c2_ay_share is not None and c2_ay_share >= 30.0
        is_deep_tgt  = c2_deep_pct is not None and c2_deep_pct >= 20
        is_expl      = expl_p >= 62
        is_mild_deep = (c2_adot is not None and c2_adot >= 10.5 and expl_p >= 55)
    elif adv2 is not None:
        is_deep      = a2_adot is not None and a2_adot >= 12.0
        is_ay_heavy  = a2_ay_share is not None and a2_ay_share >= 33
        is_deep_tgt  = False
        is_expl      = expl_p >= 62
        is_mild_deep = (a2_adot is not None and a2_adot >= 10.5 and expl_p >= 55)
    else:
        is_deep      = adot_val is not None and adot_val >= 12.0
        is_ay_heavy  = (airyard_p is not None and airyard_p >= 35)
        is_deep_tgt  = False
        is_expl      = expl_p >= 62
        is_mild_deep = adot_val is not None and adot_val >= 10.5 and expl_p >= 55

    is_air = (airyard_p is not None and airyard_p >= 35)  # SIS always usable

    if is_deep or is_ay_heavy or is_expl or is_air or is_mild_deep or is_deep_tgt:
        if has_chart2 and (is_deep or is_ay_heavy or is_mild_deep or is_deep_tgt):
            # 2-season FP charting citation (BEST source)
            g_str    = f"{int(c2_g)}g" if c2_g else "2yr"
            adot_s   = f"2yr aDOT {c2_adot:.1f}" if c2_adot else ""
            ay_s     = f"{c2_ay_share:.0f}% air-yd share" if c2_ay_share else ""
            dpct_s   = f"{c2_deep_pct:.0f}% deep-target rate over {g_str}" if c2_deep_pct else (f"over {g_str}" if g_str else "")
            expl_s   = f"explosive {expl_p:.0f}th pctl" if expl_p >= 55 else ""
            parts    = [x for x in [adot_s, ay_s, dpct_s, expl_s] if x]
        elif adv2 is not None and (is_deep or is_ay_heavy or is_mild_deep):
            # 2-season adv2 citation
            g_str     = f"{int(a2_g)}g" if a2_g else "2yr"
            adot_s    = f"2yr aDOT {a2_adot:.1f}" if a2_adot else ""
            ay_s      = f"{a2_ay_share:.0f}% air-yds share over {g_str}" if a2_ay_share else ""
            expl_s    = f"explosive {expl_p:.0f}th pctl" if expl_p >= 55 else ""
            parts     = [x for x in [adot_s, ay_s, expl_s] if x]
        else:
            # single-season fallback
            adot_s  = f"aDOT {adot_val:.1f}" if adot_val else ""
            expl_s  = f"explosive {expl_p:.0f}th pctl" if expl_p >= 55 else ""
            air_s   = f"airyard_pct {airyard_p:.1f}%" if airyard_p else ""
            parts   = [x for x in [adot_s, expl_s, air_s] if x]
        if not parts: parts = [f"explosive {expl_p:.0f}th pctl"]
        amp_parts = ["weak pass-rush (sackp<=30 = clean pocket)", "weak deep-D (covp<=30)", "dome"]
        if sep_p >= 55:
            amp_parts.append("single-high / off coverage")
        # alignment context: boundary WRs thrive vs man; note it in amp
        if has_chart2 and c2_wide_pct is not None and c2_wide_pct >= 65:
            amp_parts.append(f"boundary-aligned ({c2_wide_pct:.0f}% wide, man defense adds leverage)")
        flags.append({
            "f": "Deep/vertical threat",
            "d": ", ".join(parts),
            "amp": " / ".join(amp_parts)
        })
        activators.append("deep")

    # -- FLAG 2: Separator / route-winner / man-coverage winner --------------
    # BEST source: chart2.blend yprr + tprr + fr_pct + contested_pct (2-yr FP charting).
    # A true route-winner posts high YPRR, TPRR, and earns 1st-read looks (fr_pct).
    # Fallback when chart2 absent: single-season sep_p, surplus_TPRR, covproof.
    if has_chart2:
        # chart2 thresholds: yprr p75=2.12, tprr p75=0.24, fr_pct p75=20, contested p50=11
        is_sep    = (c2_yprr is not None and c2_yprr >= 2.0) or (c2_tprr is not None and c2_tprr >= 0.23)
        is_surplus= (c2_fr_pct is not None and c2_fr_pct >= 19)   # earns 1st-read = route winner
        is_covp   = (c2_contested is not None and c2_contested >= 12)  # contested = alpha WR
        # mild: yprr >= 1.7 + any of the above
        is_sep_any= (c2_yprr is not None and c2_yprr >= 1.7 and
                     (sep_p >= 44 or covproof >= 52 or (c2_tprr is not None and c2_tprr >= 0.20)))
    else:
        is_sep    = sep_p >= 58
        is_surplus= surplus is not None and surplus > 0.03
        is_covp   = covproof >= 58
        is_sep_any= sep_p >= 44 and (covproof >= 52 or (tprr is not None and tprr > 0.24))

    if is_sep or is_surplus or is_covp or is_sep_any:
        if has_chart2:
            # 2-season FP charting citation (BEST source)
            g_str     = f"{int(c2_g)}g" if c2_g else "2yr"
            yprr_s    = f"2yr YPRR {c2_yprr:.2f}" if c2_yprr else ""
            tprr_s    = f"TPRR {c2_tprr:.3f}" if c2_tprr else ""
            fr_s      = f"1st-read {c2_fr_pct:.0f}% over {g_str}" if c2_fr_pct else (f"over {g_str}" if g_str else "")
            cont_s    = f"contested {c2_contested:.0f}%" if c2_contested else ""
            parts     = [x for x in [yprr_s, tprr_s, fr_s, cont_s] if x]
            parts     = parts or [f"separation {sep_p:.0f}th pctl"]
        else:
            sep_s    = f"separation {sep_p:.0f}th pctl"
            tprr_s   = f"TPRR {tprr:.3f}" if tprr else ""
            surp_s   = f"surplus_TPRR {'+' if surplus and surplus>0 else ''}{surplus:.3f}" if surplus is not None else ""
            cov_s    = f"coverage_proof {covproof:.0f}th pctl" if covproof >= 52 else ""
            parts    = [sep_s]
            for x in [tprr_s, surp_s, cov_s]:
                if x: parts.append(x)
        # alignment context: slot WRs feast vs zone/nickel; boundary WRs feast vs man
        if has_chart2 and c2_slot_pct is not None:
            if c2_slot_pct >= 50:
                amp = f"zone/nickel (slot-heavy {c2_slot_pct:.0f}% slot; manp<=40 exposes LB) / soft WR tier"
            elif c2_wide_pct is not None and c2_wide_pct >= 65:
                amp = f"man-heavy (manp>=68, {c2_wide_pct:.0f}% boundary; single coverage = big play) / soft WR tier"
            else:
                amp = "man-heavy (manp>=68) / soft WR tier / press-heavy scheme"
        elif sep_p >= 70:
            amp = "man-heavy (manp>=68) + single coverage / soft WR tier / off-coverage"
        else:
            amp = "man-heavy (manp>=68) / soft WR tier / press-heavy scheme"
        flags.append({
            "f": "Separator / route-winner",
            "d": ", ".join(parts),
            "amp": amp
        })
        activators.append("separator")

    # -- FLAG 3: Route technician / YPRR / zone-beater -----------------------
    # BEST source: chart2.blend yprr + tprr (2-yr FP charting) when present.
    # Fallback: single-season reff_p, SIS YPRR, eff_combined.
    # Note: if separator flag already fired via chart2, route flag fires when
    # the player also shows strong route-efficiency (medium-aDOT, zone-scheme).
    if has_chart2:
        is_reff  = reff_p >= 62
        is_yprr  = (c2_yprr is not None and c2_yprr >= 1.7)      # chart2 is primary
        is_eff   = eff_comb is not None and eff_comb >= 40
        is_reff2 = reff_p >= 48 and rec_eff >= 55
    else:
        is_reff  = reff_p >= 62
        is_yprr  = yprr is not None and yprr >= 1.8               # SIS fallback
        is_eff   = eff_comb is not None and eff_comb >= 40
        is_reff2 = reff_p >= 48 and rec_eff >= 55

    if is_reff or is_yprr or is_eff or is_reff2:
        if has_chart2 and is_yprr:
            # 2-season FP charting citation
            g_str    = f"{int(c2_g)}g" if c2_g else "2yr"
            yprr_s   = f"2yr YPRR {c2_yprr:.2f} over {g_str} (FP charting)"
            tprr_c   = f"TPRR {c2_tprr:.3f}" if c2_tprr else ""
            reff_s   = f"route_eff {reff_p:.0f}th pctl" if reff_p >= 55 else ""
            eff_s    = f"eff_combined {eff_comb:.0f}" if is_eff else ""
            parts    = [yprr_s]
            for x in [tprr_c, reff_s, eff_s]:
                if x: parts.append(x)
        else:
            parts = [f"route_eff {reff_p:.0f}th pctl"]
            if is_yprr:  parts.append(f"YPRR {yprr:.2f}")
            if is_eff:   parts.append(f"eff_combined {eff_comb:.0f}")
            if tprr and adot_val and adot_val < 12:
                parts.append(f"TPRR {tprr:.3f} (slot/intermediate)")
            elif is_reff2 and rec_eff >= 55:
                parts.append(f"rec_eff {rec_eff:.0f}th pctl")
        # alignment context for route flag
        if has_chart2 and c2_slot_pct is not None and c2_slot_pct >= 45:
            amp = f"zone/nickel ({c2_slot_pct:.0f}% slot; zone coverage exposes seams) / soft WR tier / cushion schemes"
        else:
            amp = "zone coverage (manp<=32) / soft WR tier / cushion schemes / off-man"
        flags.append({
            "f": "Route technician / YPRR / zone-beater",
            "d": ", ".join(parts),
            "amp": amp
        })
        activators.append("route")

    # -- FLAG 4: YAC / RAC machine -------------------------------------------
    # BEST source: chart2.blend yac_rec + mtf_rec (2-yr FP charting).
    # Fallback: single-season yac_pctl + YACoe/MTFoe + adv2 yptouch.
    if has_chart2:
        # chart2 thresholds: yac_rec p75=5.2, mtf_rec p75=0.15
        is_yac   = (c2_yac_rec is not None and c2_yac_rec >= 5.0) or yac_p >= 65
        is_yacoe = (c2_yaco_rec is not None and c2_yaco_rec >= 1.5) or (yacoe is not None and yacoe >= 0.4)
        is_mtf   = (c2_mtf_rec is not None and c2_mtf_rec >= 0.14) or (mtfoe is not None and mtfoe >= 0.03)
        is_yac2  = ((c2_yac_rec is not None and c2_yac_rec >= 4.0) and
                    (yac_p >= 52 or (yacoe is not None and yacoe > 0.10)))
    else:
        is_yac   = yac_p >= 65
        is_yacoe = yacoe is not None and yacoe >= 0.4
        is_mtf   = mtfoe is not None and mtfoe >= 0.03
        is_yac2  = yac_p >= 52 and yacoe is not None and yacoe > 0.15

    if is_yac or is_yacoe or is_mtf or is_yac2:
        if has_chart2 and (is_yac or is_yacoe or is_mtf or is_yac2):
            # 2-season FP charting citation (BEST source)
            g_str    = f"{int(c2_g)}g" if c2_g else "2yr"
            yac_s    = f"2yr YAC/rec {c2_yac_rec:.1f}" if c2_yac_rec else ""
            yaco_s   = f"YACoe +{c2_yaco_rec:.1f}/rec" if c2_yaco_rec and c2_yaco_rec >= 1.0 else ""
            mtf_s    = f"MTF {c2_mtf_rec:.2f}/rec over {g_str}" if c2_mtf_rec else (f"over {g_str}" if g_str else "")
            # supplement with legacy YACoe/MTFoe if chart2 mtf missing
            leg_yacoe= f"YACoe +{yacoe:.2f}" if (not yac_s and yacoe is not None and yacoe >= 0.3) else ""
            leg_mtf  = f"MTFoe +{mtfoe:.2f}" if (not mtf_s and mtfoe is not None and mtfoe >= 0.03) else ""
            # 2yr yptouch from adv2 as additional context
            touch_s  = (f"2yr yptouch {a2_yptouch:.1f}" if adv2 and a2_yptouch else "")
            parts    = [x for x in [yac_s, yaco_s, mtf_s, leg_yacoe, leg_mtf, touch_s] if x]
            parts    = parts or [f"yac_pctl {yac_p:.0f}th"]
        else:
            parts = [f"yac_pctl {yac_p:.0f}th"]
            if is_yacoe: parts.append(f"YACoe +{yacoe:.2f}")
            if is_mtf:   parts.append(f"MTFoe +{mtfoe:.2f}")
            if adv2 is not None and a2_yptouch is not None:
                g_str = f"{int(a2_g)}g" if a2_g else "2yr"
                parts.append(f"2yr yptouch {a2_yptouch:.1f} over {g_str}")
        amp = "zone coverage (space after catch) / soft WR tier / poor-tackling defense"
        if tgt_share >= 0.22 and (yac_p >= 72 or (c2_yac_rec is not None and c2_yac_rec >= 5.5)):
            amp += " / volume + YAC = floor-ceiling combo"
        # alignment context: slot WRs get more YAC opportunities
        if has_chart2 and c2_slot_pct is not None and c2_slot_pct >= 45:
            amp += f" / slot ({c2_slot_pct:.0f}%) = short catches with runway"
        flags.append({
            "f": "YAC / RAC machine",
            "d": ", ".join(parts),
            "amp": amp
        })
        activators.append("yac")

    # -- FLAG 5: Target-volume / target hog ----------------------------------
    # When adv2 present: use 2yr tgt_share (0-100 scale) + rec_pg + ypt for
    # thresholds and cite 2-season values in the flag detail.
    # Fallback: single-season tgt_share, TPRR, tgt_share_w (SIS).
    if adv2 is not None:
        is_vol  = a2_tgt_share is not None and a2_tgt_share >= 20    # 2yr 20%+
        is_tgtw = tgt_share_w is not None and tgt_share_w >= 16      # SIS still valid
        # mild: 2yr 16%+ tgt share + strong rec_pg
        is_vol2 = (a2_tgt_share is not None and a2_tgt_share >= 16
                   and a2_rec_pg is not None and a2_rec_pg >= 5.0)
    else:
        is_vol  = tgt_share >= 0.20
        is_tgtw = tgt_share_w is not None and tgt_share_w >= 16
        is_vol2 = tgt_share >= 0.16 and tprr is not None and tprr > 0.18 and dk_pg >= 10

    if is_vol or is_tgtw or is_vol2:
        if adv2 is not None and (is_vol or is_vol2):
            # 2-season citation
            g_str    = f"{int(a2_g)}g" if a2_g else "2yr"
            tgt_s    = f"2yr {a2_tgt_share:.0f}% tgt share" if a2_tgt_share else f"tgt_share {tgt_share*100:.1f}%"
            rec_s    = f"{a2_rec_pg:.1f} rec/g over {g_str}" if a2_rec_pg else ""
            ypt_s    = f"ypt {a2_ypt:.1f}" if a2_ypt else ""
            tprr_v   = f"TPRR {tprr:.3f}" if tprr else ""
            parts    = [tgt_s]
            for x in [rec_s, ypt_s, tprr_v]:
                if x: parts.append(x)
        else:
            tgt_s  = f"tgt_share {tgt_share*100:.1f}%"
            tprr_v = f"TPRR {tprr:.3f}" if tprr else ""
            tgtw_s = f"tgt_share_w {tgt_share_w:.1f}%" if tgt_share_w else ""
            parts  = [tgt_s]
            for x in [tprr_v, tgtw_s]:
                if x: parts.append(x)
        flags.append({
            "f": "Target-volume hog",
            "d": ", ".join(parts),
            "amp": "pass-funnel (runp>=60 & covp<=45) / negative script (trailing) / high game pace"
        })
        activators.append("volume")

    # -- FLAG 6: Ceiling / red-zone / TD equity ------------------------------
    # boom_pctl, ceiling_pctl, adv_pctl, spike_pctl
    # When adv2 present: also cite 2yr td_pg in the flag detail.
    is_rz  = boom_p >= 40 or ceil_p >= 58
    is_adv = adv_p >= 65
    is_sp  = spike_p >= 45 and adv_p >= 55

    if is_rz or is_adv or is_sp:
        parts = [f"boom_pctl {boom_p:.0f}th", f"ceiling_pctl {ceil_p:.0f}th"]
        if is_adv: parts.append(f"adv_pctl {adv_p:.0f}th")
        if spike_p >= 45: parts.append(f"spike_pctl {spike_p:.0f}th")
        # 2yr td_pg citation
        if adv2 is not None and a2_td_pg is not None:
            g_str = f"{int(a2_g)}g" if a2_g else "2yr"
            parts.append(f"2yr {a2_td_pg:.2f} TD/g over {g_str}")
        flags.append({
            "f": "Ceiling / red-zone TD equity",
            "d": ", ".join(parts),
            "amp": "soft WR tier / positive script (scoring opportunities) / goal-line situations"
        })
        activators.append("rz")

    # -- FLAG 6b: ★ RZ/TD SKILL (extra signal — 2yr red-zone profile) --------
    # Fires when statmenu[k]['rz'] is present AND any threshold met:
    #   rz_tgt_share>=18 OR ez_tgt_share>=6 OR ez_td_pg>=0.35
    # Cites 2-yr inside-20 tgt share, end-zone share, and EZ TDs.
    rz_data = v.get('rz')  # None for players without 2yr RZ data
    if rz_data is not None:
        rz_ts   = rz_data.get('rz_tgt_share', 0) or 0   # % of targets inside-20
        ez_ts   = rz_data.get('ez_tgt_share', 0) or 0   # % of targets in end zone
        ez_td   = rz_data.get('ez_td', 0) or 0          # 2yr end-zone TDs
        ez_tdpg = rz_data.get('ez_td_pg', 0) or 0       # 2yr EZ TDs per game
        rz_g    = rz_data.get('g', 0) or 0              # games in sample
        rz_qualifies = (rz_ts >= 18 or ez_ts >= 6 or ez_tdpg >= 0.35)
        if rz_qualifies:
            rz_parts = []
            if rz_ts > 0:
                rz_parts.append(f"2yr {rz_ts}% inside-20 target share")
            if ez_ts > 0:
                rz_parts.append(f"{ez_ts}% end-zone share")
            if ez_td > 0 and rz_g > 0:
                rz_parts.append(f"{int(ez_td)} EZ TDs over {int(rz_g)}g")
            if not rz_parts:
                rz_parts = [f"2yr EZ TD/g {ez_tdpg:.2f}"]
            rz_flag = {
                "f": "Red-zone / TD skill",
                "d": ", ".join(rz_parts),
                "amp": "soft WR tier / favored script (goal-line looks) / amp vs soft WR tier in scoring position"
            }
            if len(flags) < 6:
                flags.append(rz_flag)
                if "rz_skill" not in activators:
                    activators.append("rz_skill")
            else:
                # Still track activator for weekly loop
                if "rz_skill" not in activators:
                    activators.append("rz_skill")
                # Replace last generic fallback flag if present
                if flags and flags[-1].get('f') in ('Ceiling variance', 'High usage value', 'Per-route value'):
                    flags[-1] = rz_flag

    # -- EXHAUST: additional fallback flags to ensure >= 3 flags -------------

    # Explosive slot (aDOT 8-12 + explosive) -- different from pure deep
    if len(flags) < 3 and adot_val and 8 <= adot_val <= 12 and expl_p >= 52:
        parts = [f"aDOT {adot_val:.1f} (slot range)", f"explosive {expl_p:.0f}th pctl"]
        flags.append({
            "f": "Explosive slot / intermediate",
            "d": ", ".join(parts),
            "amp": "zone / soft WR tier / RPO-heavy offense"
        })
        activators.append("slot_expl")

    # Matchup specialist (matchup_pctl high)
    if len(flags) < 3 and matchup_p >= 58:
        flags.append({
            "f": "Matchup hunter",
            "d": f"matchup_pctl {matchup_p:.0f}th -- finds favorable coverage",
            "amp": "soft WR tier (covp<=30) / pass-funnel / zone"
        })
        if "matchup" not in activators:
            activators.append("matchup")

    # Reception efficiency / contested catch
    if len(flags) < 3 and rec_eff >= 52:
        parts = [f"rec_eff_pctl {rec_eff:.0f}th"]
        if catch_r > 0.60: parts.append(f"catch_rate {catch_r*100:.0f}%")
        if ypt > 0:       parts.append(f"ypt {ypt:.1f}")
        flags.append({
            "f": "Reception efficiency",
            "d": ", ".join(parts),
            "amp": "soft WR tier / zone / pass-funnel"
        })
        activators.append("rec_eff")

    # Value / per-route value (fp_rr from SIS)
    if len(flags) < 3 and fp_rr is not None and fp_rr >= 0.25:
        flags.append({
            "f": "Per-route value",
            "d": f"FP_RR {fp_rr:.2f} (fantasy points per route run)",
            "amp": "soft WR tier / pass-funnel / zone"
        })
        activators.append("fp_rr")

    # Value pctl (last resort)
    if len(flags) < 3 and value_p >= 55:
        flags.append({
            "f": "High usage value",
            "d": f"value_pctl {value_p:.0f}th",
            "amp": "pass-funnel / soft WR tier / high-volume offense"
        })
        activators.append("value")

    # Absolute last fallback -- ceiling percentile
    if len(flags) < 3:
        parts = [f"ceiling_pctl {ceil_p:.0f}th", f"boom_pctl {boom_p:.0f}th"]
        flags.append({
            "f": "Ceiling variance",
            "d": ", ".join(parts),
            "amp": "soft WR tier / pass-funnel"
        })
        activators.append("ceiling_var")

    # -- FLAG: ★ COVERAGE SPECIALIST ------------------------------------------
    # Fires when statmenu[k]['cspec'] is present.
    # cspec = {best, best_key, z, val, lg, ratio, profile{man,c2,c3,c4,c6}}
    # Skill flag: this player crushes his best coverage scheme at a standout rate.
    # ALWAYS added when cspec present — allows up to 7 flags for cspec players.
    cspec = v.get('cspec')
    if cspec is not None:
        cs_best  = cspec.get('best', '')        # e.g. "Cover-3 & Man"
        cs_ratio = cspec.get('ratio', 0) or 0  # e.g. 2.23 (x league FP/RR)
        cs_pctl  = cspec.get('pctl', 0) or 0   # league percentile (the selection method)
        cs_rts   = cspec.get('routes', 0) or 0
        cspec_flag = {
            "f": "Coverage specialist",
            "d": f"crushes {cs_best} ({cs_ratio:.2f}x league FP/RR, {cs_pctl}th pctl over {cs_rts} routes)",
            "amp": f"vs defenses that run {cs_best} heavily"
        }
        # Always append; trim happens after (cap raised to 7 for cspec players).
        flags.append(cspec_flag)
        if 'cspec' not in activators:
            activators.append('cspec')

    # Skill flag: elite SEPARATION (esp. vs man) — the first signal validated to add ceiling
    # beyond the base rate (in-sample residual-vs-base: overall +0.29, vs-man +0.32). Entered
    # CONSERVATIVELY as a skill flag (context), not a sized multiplier — in-sample is an upper bound.
    sepd = v.get('sep')
    if sepd is not None and sepd.get('elite_man_sep'):
        flags.append({
            "f": "Elite separator",
            "d": f"creates separation vs man ({sepd.get('man_sep_pctl')}th pctl) — gets open on the toughest coverage",
            "amp": "vs press-man defenses (his separation travels)"
        })

    # Trim to max 6 (+1 for cspec, +1 for elite-separator so validated flags always survive)
    _has_sep = sepd is not None and sepd.get('elite_man_sep')
    max_flags = (7 if cspec is not None else 6) + (1 if _has_sep else 0)
    flags = flags[:max_flags]
    activators = list(dict.fromkeys(activators))[:max_flags]  # dedupe, preserve order
    return flags, activators

# -- weekly probability logic -------------------------------------------------
def week_prob(k, v, week, base, activators):
    opp  = week['opp']
    home = week.get('home', False)
    dome = week.get('dome', False)

    d     = de.get(opp) or {}
    covp  = g(d, 'covp', 50)
    runp  = g(d, 'runp', 50)
    manp  = g(d, 'manp', 50)
    sackp = g(d, 'sackp', 50)
    tiers = d.get('tiers') or {}
    wr_tier = tiers.get('WR', 'AVG') or 'AVG'

    fus      = v.get('fus') or {}
    adot_d   = v.get('adot') or {}
    sis      = v.get('sis') or {}
    yaco     = v.get('yaco') or {}
    usage    = v.get('usage') or {}

    oline_p  = g(fus, 'oline_pctl', 50)
    adot_val = g(adot_d, 'aDOT')
    sep_p    = g(fus, 'separation_pctl', 50)
    reff_p   = g(fus, 'route_eff_pctl', 50)
    yac_p    = g(fus, 'yac_pctl', 50)
    expl_p   = g(fus, 'explosive_pctl', 50)
    tgt_share= g(usage, 'tgt_share', 0) or 0

    # -- chart2 fields for deep WR / coverage shell check -------------------
    chart2      = v.get('chart2')
    c2b         = (chart2.get('blend') if chart2 else None) or {}
    c2_adot     = g(c2b, 'aDOT')
    c2_deep_pct = g(c2b, 'deep_pct')

    # -- own team env + opponent team env (TENV) for extra signals -----------
    own_env      = v.get('team_env') or {}
    opp_env      = TENV.get(opp) or {}   # {} if opp not in TENV
    own_pace     = own_env.get('pace_pctl', 50) or 50
    own_env_idx  = own_env.get('env_idx', 50) or 50
    own_win_tot  = own_env.get('win_total', 8.5) or 8.5
    opp_pace     = opp_env.get('pace_pctl', 50) or 50
    opp_win_tot  = opp_env.get('win_total', 8.5) or 8.5
    has_own_env  = bool(own_env)
    has_opp_env  = bool(opp_env)

    mults      = []
    lit_flags  = []
    suppress   = []   # suppressor flags (not counted in "lit")

    # -- 1. WR tier / pass-defense -------------------------------------------
    if wr_tier == 'SOFT':
        mults.append(1.35)
        lit_flags.append(f"soft WR tier ({opp})")
    elif wr_tier == 'TOUGH':
        mults.append(0.73)
        suppress.append(f"tough WR tier ({opp})")
    else:
        # No explicit tier: use covp
        if covp <= 28:
            mults.append(1.28)
            lit_flags.append(f"weak pass-D covp {covp:.0f}")
        elif covp >= 72:
            mults.append(0.76)
            suppress.append(f"tough pass-D covp {covp:.0f}")

    # -- 2. Pass-funnel ------------------------------------------------------
    is_pass_funnel = runp >= 60 and covp <= 45
    if is_pass_funnel and any(a in activators for a in ['volume', 'route', 'yac', 'separator']):
        mults.append(1.18)
        lit_flags.append(f"pass-funnel (runp {runp:.0f}, covp {covp:.0f})")

    # -- 3. Man/zone coverage fit  [PRUNE: COV_SHRINK — split r~0.2] ----------
    if manp >= 68 and 'separator' in activators:
        mults.append(_shr(1.18, COV_SHRINK))
        lit_flags.append(f"man-heavy (manp {manp:.0f}) + separation edge")
    elif manp >= 68 and 'separator' not in activators and sep_p < 52:
        mults.append(_shr(0.88, COV_SHRINK))
        suppress.append(f"man-heavy (manp {manp:.0f}) -- limited separation ({sep_p:.0f}th)")
    elif manp <= 32 and any(a in activators for a in ['route', 'yac']):
        mults.append(_shr(1.12, COV_SHRINK))
        lit_flags.append(f"zone ({opp} manp {manp:.0f}) + route/YAC skill")
    elif manp <= 32 and 'route' not in activators and 'yac' not in activators:
        # zone but no route/YAC edge -> minor negative
        mults.append(_shr(0.95, COV_SHRINK))
        suppress.append(f"zone ({opp} manp {manp:.0f}) -- no route/YAC edge")

    # -- 4. Deep-ball / clean-pocket  [PRUNE: DEEP_SHRINK — aDOT/deep sign-flip] --
    if 'deep' in activators:
        if sackp <= 30:
            mults.append(_shr(1.15, DEEP_SHRINK))
            lit_flags.append(f"clean pocket (sackp {sackp:.0f}) activates deep ball")
        elif sackp >= 75 and oline_p <= 35:
            mults.append(_shr(0.85, DEEP_SHRINK))
            suppress.append(f"heavy rush (sackp {sackp:.0f}) + weak O-line ({oline_p:.0f}th)")
        # dome bonus for deep/explosive
        if dome and (adot_val and adot_val >= 12 or expl_p >= 62):
            mults.append(_shr(1.08, DEEP_SHRINK))
            lit_flags.append(f"dome + deep/explosive profile")

    # -- 5. Volume extra: weak pass-D + high target share --------------------
    if 'volume' in activators and covp <= 28 and tgt_share >= 0.23:
        mults.append(1.10)
        lit_flags.append(f"volume vs weak pass-D (covp {covp:.0f}, tgt% {tgt_share*100:.0f}%)")

    # -- 6. Home -------------------------------------------------------------
    if home:
        mults.append(1.04)
        lit_flags.append("home")

    # -- 7. Dome (non-deep) --------------------------------------------------
    if dome and 'deep' not in activators:
        mults.append(1.04)
        lit_flags.append("dome")

    # -- 8. YAC suppressor: press man coverage -------------------------------
    if 'yac' in activators and covp >= 72 and manp >= 72:
        mults.append(0.92)
        suppress.append(f"tight man limits YAC (covp {covp:.0f}, manp {manp:.0f})")

    # =========================================================================
    # -- EXTRA SIGNALS (new pass) -------------------------------------------

    # -- 9. ENV / SHOOTOUT ---------------------------------------------------
    # own env_idx>=65 AND opp soft pass-D (covp<=35) = shootout setup x1.08
    if has_own_env and own_env_idx >= 65 and covp <= 35:
        mults.append(1.08)
        lit_flags.append(f"env/shootout (own env {own_env_idx}, opp covp {covp:.0f})")

    # -- 10. PACE ------------------------------------------------------------
    # own pace_pctl>=65 AND opp pace_pctl>=50 => fast game x1.08
    # both slow (<=35) => x0.95
    if has_own_env and has_opp_env:
        if own_pace >= 65 and opp_pace >= 50:
            mults.append(1.08)
            lit_flags.append(f"fast game (own pace {own_pace}, opp pace {opp_pace})")
        elif own_pace <= 35 and opp_pace <= 35:
            mults.append(0.95)
            suppress.append(f"slow game (own pace {own_pace}, opp pace {opp_pace})")

    # -- 11. SCRIPT ----------------------------------------------------------
    # d = own win_total - opp win_total
    # underdog (d<=-2.5): WR pass volume x1.10 (trailing => more attempts)
    # big favorite deep WR (d>=2.5): slight negative x0.97 (game-manages off deep shots)
    if has_own_env and has_opp_env:
        win_delta = own_win_tot - opp_win_tot
        if win_delta <= -2.5:
            mults.append(1.10)
            lit_flags.append(f"trailing script => target volume (own WT {own_win_tot}, opp WT {opp_win_tot})")
        elif win_delta >= 2.5 and 'deep' in activators:
            mults.append(0.97)
            suppress.append(f"big favorite + deep WR (win delta +{win_delta:.1f}) => game-manages")

    # -- 12. COVERAGE SHELL (REAL per-defense single/two-high) ---------------
    # Source: SHELL[opp] = {man, c2, c3, c4, c6, single_high, two_high, single_high_pctl}
    # single_high = man% + Cover3% (one deep safety behind the box).
    # two_high = Cover2% + Cover4% + Cover6% (two-safety shell).
    # This REPLACES the old man_rate proxy for the deep-coverage signal.
    sh_data      = SHELL.get(opp) or {}
    sh_pctl      = sh_data.get('single_high_pctl')   # 0-100; None if missing
    sh_rate      = sh_data.get('single_high')         # e.g. 69.2 (%)
    th_rate      = sh_data.get('two_high')            # e.g. 30.9 (%)
    sh_man       = sh_data.get('man')                 # man% component

    # Deep WR classifier (same as previous: chart2 deep_pct>=18 OR aDOT>=12 OR air-yards)
    fus_inner    = v.get('fus') or {}
    expl_p_inner = g(fus_inner, 'explosive_pctl', 0) or 0
    airyard_p_in = g((v.get('sis') or {}), 'airyard_pct')
    is_deep_wr   = (
        (c2_deep_pct is not None and c2_deep_pct >= 18) or
        (c2_adot     is not None and c2_adot     >= 12) or
        (adot_val    is not None and adot_val    >= 12) or
        (airyard_p_in is not None and airyard_p_in >= 35 and expl_p_inner >= 55)
    )

    # Slot/possession classifier (defined outside the sh_pctl block so total_conds can use it)
    is_slot_poss = (
        'volume' in activators or
        'route' in activators or
        'yac' in activators or
        ('separator' in activators and not is_deep_wr)
    )

    if sh_pctl is not None:
        # --- 12a. Deep WR vs single-high shell (sh_pctl>=65)  [PRUNE: DEEP_SHRINK] ---
        if 'deep' in activators and is_deep_wr and sh_pctl >= 65:
            mults.append(_shr(1.12, DEEP_SHRINK))
            sh_pct_str = f"{sh_rate:.0f}%" if sh_rate is not None else "high"
            lit_flags.append(
                f"single-high shell (opp {sh_pct_str} Cover-1/3) -> deep one-on-ones"
            )
        # --- 12b. Deep WR vs two-high shell (sh_pctl<=35)  [PRUNE: DEEP_SHRINK] ---
        elif 'deep' in activators and is_deep_wr and sh_pctl <= 35:
            mults.append(_shr(0.90, DEEP_SHRINK))
            th_pct_str = f"{th_rate:.0f}%" if th_rate is not None else "high"
            suppress.append(
                f"two-high brackets the deep ball (opp {th_pct_str} two-high)"
            )

        # --- 12c. Separator / man-winning WR vs high man%  [PRUNE: COV_SHRINK] ---
        # Fires on separator archetype; independent from 12a (additive).
        if 'separator' in activators and sh_pctl >= 65 and sh_man is not None and sh_man >= 32:
            mults.append(_shr(1.10, COV_SHRINK))
            lit_flags.append(
                f"wins man one-on-one (opp {sh_man:.0f}% man)"
            )

        # --- 12d. Slot/possession WR vs two-high (sh_pctl<=35)  [PRUNE: COV_SHRINK] ---
        # Two-high softens underneath / opens middle-of-field for slot/possession WR.
        if is_slot_poss and sh_pctl <= 35:
            mults.append(_shr(1.06, COV_SHRINK))
            th_pct_str = f"{th_rate:.0f}%" if th_rate is not None else "high"
            lit_flags.append(
                f"two-high softens underneath (opp {th_pct_str} two-high)"
            )

    # =========================================================================
    # -- 13. COVERAGE SPECIALIST (per-week activation) -----------------------
    # cspec = {best, best_key, z, val, lg, ratio}
    # Fire when opp runs the player's best coverage >= SHELL['_LEAGUE'][best_key] + 3 pp
    # Multiplier: x1.10; x1.13 if z >= 2.0
    cspec = v.get('cspec')
    if cspec is not None and sh_data:
        cs_keys = cspec.get('best_keys') or [cspec.get('best_key')]
        cs_pctl = cspec.get('pctl', 0) or 0
        _NM = {'man':'Man','c2':'Cover-2','c3':'Cover-3','c4':'Cover-4','c6':'Cover-6','single_high':'Single-High','two_high':'Two-High','zone':'Zone'}
        fired = None  # fire vs whichever of his strong coverages the opponent over-runs most
        for ck in cs_keys:
            lg_usage = SHELL['_LEAGUE'].get(ck); opp_usage = sh_data.get(ck)
            if ck and lg_usage is not None and opp_usage is not None and opp_usage >= lg_usage + 3:
                if fired is None or (opp_usage - lg_usage) > fired[1]:
                    fired = (ck, opp_usage - lg_usage, opp_usage, lg_usage)
        if fired:
            ck, _, opp_usage, lg_usage = fired
            cs_mult = 1.13 if cs_pctl >= 95 else 1.10
            mults.append(_shr(cs_mult, COV_SHRINK))   # [PRUNE: COV_SHRINK]
            lit_flags.append(
                f"faces {_NM.get(ck, ck)}-heavy D (opp {opp_usage:.0f}% vs lg {lg_usage:.0f}%) "
                f"— his best scheme"
            )

    # =========================================================================

    p   = prob(base, mults)
    lab = label(p, base)

    all_flags = lit_flags + suppress
    lit = len(lit_flags)

    # total activatable conditions: each slot we checked
    base_conds  = 4  # tier, passfunnel, man/zone, home
    extra_conds = (
        (1 if 'deep' in activators else 0) +
        (1 if 'volume' in activators else 0) +
        (1 if dome else 0) +
        (1 if 'yac' in activators else 0) +
        (1 if has_own_env else 0) +                          # env/shootout
        (1 if (has_own_env and has_opp_env) else 0) +        # pace
        (1 if (has_own_env and has_opp_env) else 0) +        # script
        # coverage shell (REAL single/two-high): 3 possible checks per week
        (1 if (sh_pctl is not None and 'deep' in activators and is_deep_wr) else 0) +  # 12a/b deep
        (1 if (sh_pctl is not None and 'separator' in activators) else 0) +            # 12c sep
        (1 if (sh_pctl is not None and is_slot_poss) else 0) +                        # 12d slot
        # coverage specialist per-week check
        (1 if (cspec is not None and sh_data) else 0)                                 # 13 cspec
    )
    total_conds = base_conds + extra_conds

    return round(p * 100), lab, lit, total_conds, all_flags

# -- seed base for no-history players -----------------------------------------
def seed_base(v):
    fus    = v.get('fus') or {}
    ceil_p = g(fus, 'ceiling_pctl', 50) or 50
    raw    = POS_BASE * (0.75 + 0.5 * ceil_p / 100)
    return round(cap(raw, 0.06, 0.45), 3)

# -- build "line" sentence ----------------------------------------------------
def build_line(k, v, skill_flags, activators):
    name     = v['name']
    team     = v['team']
    adot_d   = v.get('adot') or {}
    usage    = v.get('usage') or {}
    fus      = v.get('fus') or {}
    yaco     = v.get('yaco') or {}
    adot_val = g(adot_d, 'aDOT')
    tgt_share= g(usage, 'tgt_share', 0) or 0
    sep_p    = g(fus, 'separation_pctl', 50)
    yac_p    = g(fus, 'yac_pctl', 50)
    reff_p   = g(fus, 'route_eff_pctl', 50)
    expl_p   = g(fus, 'explosive_pctl', 50)
    yacoe_v  = g(yaco, 'YACoe')

    # ENV note: high-scoring offense is a standing ceiling raiser -- note it in the line
    own_env = v.get('team_env') or {}
    env_idx = own_env.get('env_idx', 0) or 0

    arch_parts = []
    if 'deep' in activators:
        adot_s = f"aDOT {adot_val:.1f}" if adot_val else ""
        expl_s = f"explosive {expl_p:.0f}th" if expl_p >= 55 else ""
        combo  = ", ".join(filter(None, [adot_s, expl_s]))
        arch_parts.append(f"vertical threat ({combo})")
    if 'separator' in activators:
        arch_parts.append(f"separation edge ({sep_p:.0f}th pctl) wins man coverage")
    if 'route' in activators:
        arch_parts.append(f"route precision finds soft spots (reff {reff_p:.0f}th pctl)")
    if 'yac' in activators:
        yacoe_s = f" YACoe +{yacoe_v:.2f}" if yacoe_v and yacoe_v > 0 else ""
        arch_parts.append(f"YAC upside ({yac_p:.0f}th pctl{yacoe_s})")
    if 'volume' in activators:
        arch_parts.append(f"volume floor drives ceiling ({tgt_share*100:.1f}% tgt share)")
    if 'rz' in activators and 'volume' not in activators:
        arch_parts.append("TD ceiling equity")
    if 'rz_skill' in activators:
        rz_data = v.get('rz') or {}
        rz_ts   = rz_data.get('rz_tgt_share', 0) or 0
        ez_ts   = rz_data.get('ez_tgt_share', 0) or 0
        ez_td   = rz_data.get('ez_td', 0) or 0
        rz_g    = rz_data.get('g', 0) or 0
        if rz_ts > 0 or ez_ts > 0:
            arch_parts.append(f"red-zone TD equity ({rz_ts}% inside-20, {ez_ts}% EZ share, {int(ez_td)} EZ TDs/{int(rz_g)}g)")
    if not arch_parts:
        arch_parts.append("ceiling variance (limited sample)")

    adot_end = f"aDOT {adot_val:.1f}" if adot_val else ""
    tgt_end  = f"{tgt_share*100:.1f}% tgt share" if tgt_share else ""
    suffix   = " -- " + ", ".join(filter(None, [adot_end, tgt_end])) if (adot_end or tgt_end) else ""

    # ENV note appended when own offense is high-scoring (standing ceiling raiser)
    env_note = f" High-scoring offense (env {env_idx})." if env_idx >= 70 else ""

    return f"{name} ({team}) unlocks ceiling via {'; '.join(arch_parts)}{suffix}.{env_note}"

# -- MAIN LOOP ----------------------------------------------------------------
wr_keys    = players(sm, 'WR')
data       = {}
hist_count = 0

for k in wr_keys:
    v        = sm[k]
    n_games  = v.get('n_games', 0) or 0
    boom_g   = v.get('boom_games', 0) or 0
    team     = v.get('team', '') or ''

    # Base rate
    base = reg_base(v, posbase)
    if base is None:
        base = seed_base(v)
        hist = False
    else:
        hist = True
        hist_count += 1

    # Skill flags
    skill_flags, activators = build_skill_flags(k, v)

    # Line sentence
    line = build_line(k, v, skill_flags, activators)

    # Empirical summary
    empirical = empirical_summary(k, n_games, boom_g)

    # Schedule -- FA/unsigned get 18 blank BYE-like entries
    schedule = sch.get(team, [])
    is_fa    = (not team or team == 'FA' or len(schedule) == 0)

    if is_fa:
        weeks_out = [
            {"wk": i+1, "opp": None, "home": None, "dome": None,
             "p": None, "lab": "FA", "lit": 0, "of": 0, "flags": []}
            for i in range(18)
        ]
    else:
        if len(schedule) != 18:
            print(f"WARN: {k} ({team}) has {len(schedule)} schedule weeks")
        weeks_out = []
        for w in schedule:
            wk_num = w['wk']
            opp    = w.get('opp', '')
            home   = w.get('home', False)
            dome   = w.get('dome', False)
            if opp == 'BYE' or not opp:
                weeks_out.append({"wk": wk_num, "opp": "BYE", "home": None, "dome": None,
                                   "p": None, "lab": "BYE", "lit": 0, "of": 0, "flags": []})
                continue
            p_int, lab, lit, of, flags_list = week_prob(k, v, w, base, activators)
            weeks_out.append({
                "wk": wk_num, "opp": opp, "home": home, "dome": dome,
                "p": p_int, "lab": lab, "lit": lit, "of": of, "flags": flags_list
            })

    data[k] = {
        "name":        v['name'],
        "pos":         "WR",
        "team":        team,
        "adp":         v.get('adp'),
        "base":        round(base * 100),
        "hist":        hist,
        "n_games":     n_games,
        "boom_games":  boom_g,
        "skill_flags": skill_flags,
        "line":        line,
        "weeks":       weeks_out,
        "empirical":   empirical
    }

# -- write output -------------------------------------------------------------
ok = write('WR', data)
# Direct fallback write: bypasses boom_lib fsync for FUSE/network mounts.
_out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'boom', 'flags_WR.json')
_payload = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
with open(_out_path, 'w', encoding='utf-8') as _fh:
    _fh.write(_payload)
print(f"direct write flags_WR.json: {len(data)} players, {round(len(_payload)/1024)} KB")

