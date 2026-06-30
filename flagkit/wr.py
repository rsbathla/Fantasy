#!/usr/bin/env python3
"""flagkit/wr.py — WR position semantics (ports build_flags_WR.py onto flagkit.engine).

ONLY the WR-specific logic lives here: the base seed, the skill-flag cascade (3-6 player
flags + activators), the one-line thesis, the empirical summary, the per-week opponent
inputs, and the verbatim per-week activation (boosters AND suppressors, in the legacy's
exact order). Every piece of shared scaffolding (player loop, BYE, grading, record/week
assembly, write) is in flagkit/engine.py and is NOT duplicated.

The logic below is transcribed VERBATIM from build_flags_WR.py so the output is
byte-for-byte identical (verified by diffing boom/flags_WR.json against the golden).

  -- WR quirk: the legacy reports week["lit"] = #boosters only (lit_flags), while
     week["flags"] = lit_flags + suppress and the probability is graded off the FULL
     multiplier product (boosters AND suppressors). The engine's `activate` contract sets
     week["lit"] = len(returned_mults) and grades via prob(base, returned_mults). To honor
     BOTH the boosters-only lit count AND the full suppressed probability through that single
     channel, `activate` returns a `mults` list whose LENGTH equals the booster count and
     whose shrink-space product equals the product of ALL real multipliers: one slot carries
     the entire product and the remaining booster slots are neutral 1.0. Because boom_lib.prob
     multiplies (1 + λ(m-1)) per element (an order-independent product), this reproduces the
     identical graded p while keeping len(returned_mults) == #boosters.

  -- ENGINE-CONTRACT LIMITS (the ONLY residual diffs vs the golden; both require engine edits
     that are out of scope — wr.py only):

     (A) Suppressor-only weeks. When a week has suppressors but ZERO boosters (lit == 0),
         len(returned_mults) MUST be 0 to keep week["lit"] == 0, so the suppressor product
         cannot be carried through the mults channel and the engine grades p == round(base*100)
         instead of the suppressed value. The engine couples the lit-count and the graded-
         multiplier list into ONE return value (week["lit"] = len(mults); p = prob(base, mults)),
         so it structurally cannot express "a multiplier that lowers p but is not counted as lit"
         when there is no lit slot to ride on. Affects 52 weeks across 31 WRs.
         Fix: engine must accept the lit-count and the graded mults as SEPARATE returns.

     (B) FA / unsigned players. The legacy emits 18 FA-sentinel weeks (== flag_engine.fa_week(1..18))
         for WRs with team == 'FA' (no schedule). The engine builds weeks only by iterating
         sch.get(team, []), which is empty for FA, so it emits 0 weeks. DST (the verified template)
         has no FA players, so the engine never wired this in. flag_engine already HAS fa_week();
         the engine just never calls it. Affects 5 WRs (stefon diggs, tyreek hill, deebo samuel,
         deandre hopkins, keenan allen). Fix: engine loop must detect FA teams and emit fa_week()s.

     Everything else — all skill_flags / line / empirical / base / per-week boosters+suppressors
     ordering / of-counts for all 148 rostered WRs, and p/lab for all non-suppressor-only weeks —
     is byte-identical to /tmp/flags_WR.golden.
"""
import json
import os
from boom_lib import reg_base, prob, label, cap, SWING, SHRINK_LAMBDA

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repo root
POS = 'WR'

# -- shared inputs (same files the legacy build_flags_WR.py loads) --------------
de = json.load(open(os.path.join(HERE, 'boom', 'defense2026.json'), encoding='utf-8'))
TENV = json.load(open(os.path.join(HERE, 'boom', 'team_env.json'), encoding='utf-8'))
SHELL = json.load(open(os.path.join(HERE, 'boom', 'defense_shell.json'), encoding='utf-8'))

# gamelog is needed by empirical(); the engine passes (k, gl, bd) but we also keep a
# module ref so helpers match the legacy verbatim.
_GL = json.load(open(os.path.join(HERE, 'boom', 'gamelog.json'), encoding='utf-8'))

# POS_BASE (~0.178) — used by seed_base. Filled lazily from posbase the first time base() runs.
POS_BASE = None

# === Branch-2 anti-overfit prune (evidence: AUDIT_OVERFIT_2026.md) ==========
DEEP_SHRINK = 0.0   # WR deep/aDOT ceiling: DROP (sign-flip across years)
COV_SHRINK  = 0.5   # man/zone + shell + coverage-specialist: DEMOTE (halve)


def _shr(mult, lam):
    """Shrink a multiplier toward 1.0 by factor lam (0=neutralize, 1=unchanged)."""
    return 1.0 + (mult - 1.0) * lam


def g(d, key, default=None):
    v = d.get(key, default) if d else default
    return float(v) if v is not None else default


# -- shrink-space helper: prob multiplies (1 + λ(m-1)) per element (order-independent) ----
def _factor(m):
    return 1.0 + SHRINK_LAMBDA * (m - 1.0)


# -- empirical gamelog analysis (verbatim from legacy empirical_summary) ---------
def empirical(k, gl, bd):
    n_games = 0
    boom_games = 0
    # legacy reads n_games/boom_games off statmenu; but its string only uses them in the
    # "No 2025 gamelog" branch, which is keyed off gl having no entries. The engine passes the
    # same gl; n_games/boom_games for that branch are pulled from the record context below.
    entries = gl.get(k, [])
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


# -- WR archetype flags (verbatim from legacy build_skill_flags) -----------------
def _build_skill_flags(k, v):
    fus   = v.get('fus') or {}
    adot  = v.get('adot') or {}
    sis   = v.get('sis') or {}
    yaco  = v.get('yaco') or {}
    usage = v.get('usage') or {}
    adv2  = v.get('adv2')
    chart2= v.get('chart2')

    c2b = (chart2.get('blend') if chart2 else None) or {}
    c2_g            = g(c2b, 'g')
    c2_adot         = g(c2b, 'aDOT')
    c2_tprr         = g(c2b, 'tprr')
    c2_yprr         = g(c2b, 'yprr')
    c2_yac_rec      = g(c2b, 'yac_rec')
    c2_yaco_rec     = g(c2b, 'yaco_rec')
    c2_mtf_rec      = g(c2b, 'mtf_rec')
    c2_fr_pct       = g(c2b, 'fr_pct')
    c2_deep_pct     = g(c2b, 'deep_pct')
    c2_contested    = g(c2b, 'contested_pct')
    c2_ay_share     = g(c2b, 'ay_share')
    c2_slot_pct     = g(c2b, 'slot_pct')
    c2_wide_pct     = g(c2b, 'wide_pct')
    c2_fp_rr        = g(c2b, 'fp_rr')
    has_chart2      = bool(c2b)

    adot_val   = g(adot, 'aDOT')
    tprr       = g(adot, 'TPRR')
    surplus    = g(adot, 'surplus_TPRR')

    a2_g        = g(adv2, 'g')
    a2_adot     = g(adv2, 'aDOT')
    a2_ay_share = g(adv2, 'ay_share')
    a2_tgt_share= g(adv2, 'tgt_share')
    a2_rec_pg   = g(adv2, 'rec_pg')
    a2_ypt      = g(adv2, 'ypt')
    a2_td_pg    = g(adv2, 'td_pg')
    a2_yptouch  = g(adv2, 'yptouch')

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
    if has_chart2:
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

    is_air = (airyard_p is not None and airyard_p >= 35)

    if is_deep or is_ay_heavy or is_expl or is_air or is_mild_deep or is_deep_tgt:
        if has_chart2 and (is_deep or is_ay_heavy or is_mild_deep or is_deep_tgt):
            g_str    = f"{int(c2_g)}g" if c2_g else "2yr"
            adot_s   = f"2yr aDOT {c2_adot:.1f}" if c2_adot else ""
            ay_s     = f"{c2_ay_share:.0f}% air-yd share" if c2_ay_share else ""
            dpct_s   = f"{c2_deep_pct:.0f}% deep-target rate over {g_str}" if c2_deep_pct else (f"over {g_str}" if g_str else "")
            expl_s   = f"explosive {expl_p:.0f}th pctl" if expl_p >= 55 else ""
            parts    = [x for x in [adot_s, ay_s, dpct_s, expl_s] if x]
        elif adv2 is not None and (is_deep or is_ay_heavy or is_mild_deep):
            g_str     = f"{int(a2_g)}g" if a2_g else "2yr"
            adot_s    = f"2yr aDOT {a2_adot:.1f}" if a2_adot else ""
            ay_s      = f"{a2_ay_share:.0f}% air-yds share over {g_str}" if a2_ay_share else ""
            expl_s    = f"explosive {expl_p:.0f}th pctl" if expl_p >= 55 else ""
            parts     = [x for x in [adot_s, ay_s, expl_s] if x]
        else:
            adot_s  = f"aDOT {adot_val:.1f}" if adot_val else ""
            expl_s  = f"explosive {expl_p:.0f}th pctl" if expl_p >= 55 else ""
            air_s   = f"airyard_pct {airyard_p:.1f}%" if airyard_p else ""
            parts   = [x for x in [adot_s, expl_s, air_s] if x]
        if not parts: parts = [f"explosive {expl_p:.0f}th pctl"]
        amp_parts = ["weak pass-rush (sackp<=30 = clean pocket)", "weak deep-D (covp<=30)", "dome"]
        if sep_p >= 55:
            amp_parts.append("single-high / off coverage")
        if has_chart2 and c2_wide_pct is not None and c2_wide_pct >= 65:
            amp_parts.append(f"boundary-aligned ({c2_wide_pct:.0f}% wide, man defense adds leverage)")
        flags.append({
            "f": "Deep/vertical threat",
            "d": ", ".join(parts),
            "amp": " / ".join(amp_parts)
        })
        activators.append("deep")

    # -- FLAG 2: Separator / route-winner / man-coverage winner --------------
    if has_chart2:
        is_sep    = (c2_yprr is not None and c2_yprr >= 2.0) or (c2_tprr is not None and c2_tprr >= 0.23)
        is_surplus= (c2_fr_pct is not None and c2_fr_pct >= 19)
        is_covp   = (c2_contested is not None and c2_contested >= 12)
        is_sep_any= (c2_yprr is not None and c2_yprr >= 1.7 and
                     (sep_p >= 44 or covproof >= 52 or (c2_tprr is not None and c2_tprr >= 0.20)))
    else:
        is_sep    = sep_p >= 58
        is_surplus= surplus is not None and surplus > 0.03
        is_covp   = covproof >= 58
        is_sep_any= sep_p >= 44 and (covproof >= 52 or (tprr is not None and tprr > 0.24))

    if is_sep or is_surplus or is_covp or is_sep_any:
        if has_chart2:
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
    if has_chart2:
        is_reff  = reff_p >= 62
        is_yprr  = (c2_yprr is not None and c2_yprr >= 1.7)
        is_eff   = eff_comb is not None and eff_comb >= 40
        is_reff2 = reff_p >= 48 and rec_eff >= 55
    else:
        is_reff  = reff_p >= 62
        is_yprr  = yprr is not None and yprr >= 1.8
        is_eff   = eff_comb is not None and eff_comb >= 40
        is_reff2 = reff_p >= 48 and rec_eff >= 55

    if is_reff or is_yprr or is_eff or is_reff2:
        if has_chart2 and is_yprr:
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
    if has_chart2:
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
            g_str    = f"{int(c2_g)}g" if c2_g else "2yr"
            yac_s    = f"2yr YAC/rec {c2_yac_rec:.1f}" if c2_yac_rec else ""
            yaco_s   = f"YACoe +{c2_yaco_rec:.1f}/rec" if c2_yaco_rec and c2_yaco_rec >= 1.0 else ""
            mtf_s    = f"MTF {c2_mtf_rec:.2f}/rec over {g_str}" if c2_mtf_rec else (f"over {g_str}" if g_str else "")
            leg_yacoe= f"YACoe +{yacoe:.2f}" if (not yac_s and yacoe is not None and yacoe >= 0.3) else ""
            leg_mtf  = f"MTFoe +{mtfoe:.2f}" if (not mtf_s and mtfoe is not None and mtfoe >= 0.03) else ""
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
        if has_chart2 and c2_slot_pct is not None and c2_slot_pct >= 45:
            amp += f" / slot ({c2_slot_pct:.0f}%) = short catches with runway"
        flags.append({
            "f": "YAC / RAC machine",
            "d": ", ".join(parts),
            "amp": amp
        })
        activators.append("yac")

    # -- FLAG 5: Target-volume / target hog ----------------------------------
    if adv2 is not None:
        is_vol  = a2_tgt_share is not None and a2_tgt_share >= 20
        is_tgtw = tgt_share_w is not None and tgt_share_w >= 16
        is_vol2 = (a2_tgt_share is not None and a2_tgt_share >= 16
                   and a2_rec_pg is not None and a2_rec_pg >= 5.0)
    else:
        is_vol  = tgt_share >= 0.20
        is_tgtw = tgt_share_w is not None and tgt_share_w >= 16
        is_vol2 = tgt_share >= 0.16 and tprr is not None and tprr > 0.18 and dk_pg >= 10

    if is_vol or is_tgtw or is_vol2:
        if adv2 is not None and (is_vol or is_vol2):
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
    is_rz  = boom_p >= 40 or ceil_p >= 58
    is_adv = adv_p >= 65
    is_sp  = spike_p >= 45 and adv_p >= 55

    if is_rz or is_adv or is_sp:
        parts = [f"boom_pctl {boom_p:.0f}th", f"ceiling_pctl {ceil_p:.0f}th"]
        if is_adv: parts.append(f"adv_pctl {adv_p:.0f}th")
        if spike_p >= 45: parts.append(f"spike_pctl {spike_p:.0f}th")
        if adv2 is not None and a2_td_pg is not None:
            g_str = f"{int(a2_g)}g" if a2_g else "2yr"
            parts.append(f"2yr {a2_td_pg:.2f} TD/g over {g_str}")
        flags.append({
            "f": "Ceiling / red-zone TD equity",
            "d": ", ".join(parts),
            "amp": "soft WR tier / positive script (scoring opportunities) / goal-line situations"
        })
        activators.append("rz")

    # -- FLAG 6b: RZ/TD SKILL (extra signal — 2yr red-zone profile) ----------
    rz_data = v.get('rz')
    if rz_data is not None:
        rz_ts   = rz_data.get('rz_tgt_share', 0) or 0
        ez_ts   = rz_data.get('ez_tgt_share', 0) or 0
        ez_td   = rz_data.get('ez_td', 0) or 0
        ez_tdpg = rz_data.get('ez_td_pg', 0) or 0
        rz_g    = rz_data.get('g', 0) or 0
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
                if "rz_skill" not in activators:
                    activators.append("rz_skill")
                if flags and flags[-1].get('f') in ('Ceiling variance', 'High usage value', 'Per-route value'):
                    flags[-1] = rz_flag

    # -- EXHAUST: additional fallback flags to ensure >= 3 flags -------------
    if len(flags) < 3 and adot_val and 8 <= adot_val <= 12 and expl_p >= 52:
        parts = [f"aDOT {adot_val:.1f} (slot range)", f"explosive {expl_p:.0f}th pctl"]
        flags.append({
            "f": "Explosive slot / intermediate",
            "d": ", ".join(parts),
            "amp": "zone / soft WR tier / RPO-heavy offense"
        })
        activators.append("slot_expl")

    if len(flags) < 3 and matchup_p >= 58:
        flags.append({
            "f": "Matchup hunter",
            "d": f"matchup_pctl {matchup_p:.0f}th -- finds favorable coverage",
            "amp": "soft WR tier (covp<=30) / pass-funnel / zone"
        })
        if "matchup" not in activators:
            activators.append("matchup")

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

    if len(flags) < 3 and fp_rr is not None and fp_rr >= 0.25:
        flags.append({
            "f": "Per-route value",
            "d": f"FP_RR {fp_rr:.2f} (fantasy points per route run)",
            "amp": "soft WR tier / pass-funnel / zone"
        })
        activators.append("fp_rr")

    if len(flags) < 3 and value_p >= 55:
        flags.append({
            "f": "High usage value",
            "d": f"value_pctl {value_p:.0f}th",
            "amp": "pass-funnel / soft WR tier / high-volume offense"
        })
        activators.append("value")

    if len(flags) < 3:
        parts = [f"ceiling_pctl {ceil_p:.0f}th", f"boom_pctl {boom_p:.0f}th"]
        flags.append({
            "f": "Ceiling variance",
            "d": ", ".join(parts),
            "amp": "soft WR tier / pass-funnel"
        })
        activators.append("ceiling_var")

    # -- FLAG: COVERAGE SPECIALIST -------------------------------------------
    cspec = v.get('cspec')
    if cspec is not None:
        cs_best  = cspec.get('best', '')
        cs_ratio = cspec.get('ratio', 0) or 0
        cs_pctl  = cspec.get('pctl', 0) or 0
        cs_rts   = cspec.get('routes', 0) or 0
        cspec_flag = {
            "f": "Coverage specialist",
            "d": f"crushes {cs_best} ({cs_ratio:.2f}x league FP/RR, {cs_pctl}th pctl over {cs_rts} routes)",
            "amp": f"vs defenses that run {cs_best} heavily"
        }
        flags.append(cspec_flag)
        if 'cspec' not in activators:
            activators.append('cspec')

    sepd = v.get('sep')
    if sepd is not None and sepd.get('elite_man_sep'):
        flags.append({
            "f": "Elite separator",
            "d": f"creates separation vs man ({sepd.get('man_sep_pctl')}th pctl) — gets open on the toughest coverage",
            "amp": "vs press-man defenses (his separation travels)"
        })

    _has_sep = sepd is not None and sepd.get('elite_man_sep')
    max_flags = (7 if cspec is not None else 6) + (1 if _has_sep else 0)
    flags = flags[:max_flags]
    activators = list(dict.fromkeys(activators))[:max_flags]
    return flags, activators


# -- seed base for no-history players (verbatim from legacy seed_base) ------------
def _seed_base(v):
    fus    = v.get('fus') or {}
    ceil_p = g(fus, 'ceiling_pctl', 50) or 50
    raw    = POS_BASE * (0.75 + 0.5 * ceil_p / 100)
    return round(cap(raw, 0.06, 0.45), 3)


# -- build "line" sentence (verbatim from legacy build_line) ----------------------
def _build_line(k, v, skill_flags, activators):
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

    env_note = f" High-scoring offense (env {env_idx})." if env_idx >= 70 else ""

    return f"{name} ({team}) unlocks ceiling via {'; '.join(arch_parts)}{suffix}.{env_note}"


# ================================================================================
# Engine model contract
# ================================================================================

def context(k, v, gl, bd):
    """Position-specific feature extraction. We compute skill_flags+activators here (the
    legacy build_skill_flags returns both), stash them, and carry `v` for downstream hooks."""
    global POS_BASE
    if POS_BASE is None:
        POS_BASE = bd['posbase']['WR']
    sf, activators = _build_skill_flags(k, v)
    return {
        'k': k, 'v': v, 'name': v['name'], 'team': v.get('team', ''),
        'n_games': v.get('n_games', 0) or 0, 'boom_games': v.get('boom_games', 0) or 0,
        'skill_flags': sf, 'activators': activators,
    }


def base(v, posbase, prof):
    global POS_BASE
    if POS_BASE is None:
        POS_BASE = posbase['WR']
    rb = reg_base(v, posbase)
    if rb is not None:
        return rb, True
    return _seed_base(v), False


def skill_flags(prof):
    return prof['skill_flags']


def line(prof):
    return _build_line(prof['k'], prof['v'], prof['skill_flags'], prof['activators'])


def opp_data(opp):
    """Per-week opponent inputs the activation reads: defense2026[opp], team_env[opp],
    defense_shell[opp]. Bundled into one dict so the engine's opp_data(opp) carries them all."""
    return {
        'd': de.get(opp) or {},
        'opp_env': TENV.get(opp) or {},
        'sh_data': SHELL.get(opp) or {},
    }


def activate(prof, base, skill_flags, opp_data, week_ctx):
    """Verbatim transcription of legacy week_prob's body. Returns (all_flags, mults, total_conds)
    where `mults` has LENGTH == #boosters (so the engine reports week["lit"]=#boosters) and its
    shrink-space product equals the FULL product (boosters AND suppressors)."""
    v = prof['v']
    activators = prof['activators']
    opp  = week_ctx['opp']
    home = week_ctx.get('home', False)
    dome = week_ctx.get('dome', False)

    d     = opp_data['d']
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

    chart2      = v.get('chart2')
    c2b         = (chart2.get('blend') if chart2 else None) or {}
    c2_adot     = g(c2b, 'aDOT')
    c2_deep_pct = g(c2b, 'deep_pct')

    own_env      = v.get('team_env') or {}
    opp_env      = opp_data['opp_env']
    own_pace     = own_env.get('pace_pctl', 50) or 50
    own_env_idx  = own_env.get('env_idx', 50) or 50
    own_win_tot  = own_env.get('win_total', 8.5) or 8.5
    opp_pace     = opp_env.get('pace_pctl', 50) or 50
    opp_win_tot  = opp_env.get('win_total', 8.5) or 8.5
    has_own_env  = bool(own_env)
    has_opp_env  = bool(opp_env)

    mults      = []
    lit_flags  = []
    suppress   = []

    # -- 1. WR tier / pass-defense -------------------------------------------
    if wr_tier == 'SOFT':
        mults.append(1.35)
        lit_flags.append(f"soft WR tier ({opp})")
    elif wr_tier == 'TOUGH':
        mults.append(0.73)
        suppress.append(f"tough WR tier ({opp})")
    else:
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

    # -- 3. Man/zone coverage fit  [PRUNE: COV_SHRINK] -----------------------
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
        mults.append(_shr(0.95, COV_SHRINK))
        suppress.append(f"zone ({opp} manp {manp:.0f}) -- no route/YAC edge")

    # -- 4. Deep-ball / clean-pocket  [PRUNE: DEEP_SHRINK] -------------------
    if 'deep' in activators:
        if sackp <= 30:
            mults.append(_shr(1.15, DEEP_SHRINK))
            lit_flags.append(f"clean pocket (sackp {sackp:.0f}) activates deep ball")
        elif sackp >= 75 and oline_p <= 35:
            mults.append(_shr(0.85, DEEP_SHRINK))
            suppress.append(f"heavy rush (sackp {sackp:.0f}) + weak O-line ({oline_p:.0f}th)")
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

    # -- 9. ENV / SHOOTOUT ---------------------------------------------------
    if has_own_env and own_env_idx >= 65 and covp <= 35:
        mults.append(1.08)
        lit_flags.append(f"env/shootout (own env {own_env_idx}, opp covp {covp:.0f})")

    # -- 10. PACE ------------------------------------------------------------
    if has_own_env and has_opp_env:
        if own_pace >= 65 and opp_pace >= 50:
            mults.append(1.08)
            lit_flags.append(f"fast game (own pace {own_pace}, opp pace {opp_pace})")
        elif own_pace <= 35 and opp_pace <= 35:
            mults.append(0.95)
            suppress.append(f"slow game (own pace {own_pace}, opp pace {opp_pace})")

    # -- 11. SCRIPT ----------------------------------------------------------
    if has_own_env and has_opp_env:
        win_delta = own_win_tot - opp_win_tot
        if win_delta <= -2.5:
            mults.append(1.10)
            lit_flags.append(f"trailing script => target volume (own WT {own_win_tot}, opp WT {opp_win_tot})")
        elif win_delta >= 2.5 and 'deep' in activators:
            mults.append(0.97)
            suppress.append(f"big favorite + deep WR (win delta +{win_delta:.1f}) => game-manages")

    # -- 12. COVERAGE SHELL (REAL per-defense single/two-high) ---------------
    sh_data      = opp_data['sh_data']
    sh_pctl      = sh_data.get('single_high_pctl')
    sh_rate      = sh_data.get('single_high')
    th_rate      = sh_data.get('two_high')
    sh_man       = sh_data.get('man')

    fus_inner    = v.get('fus') or {}
    expl_p_inner = g(fus_inner, 'explosive_pctl', 0) or 0
    airyard_p_in = g((v.get('sis') or {}), 'airyard_pct')
    is_deep_wr   = (
        (c2_deep_pct is not None and c2_deep_pct >= 18) or
        (c2_adot     is not None and c2_adot     >= 12) or
        (adot_val    is not None and adot_val    >= 12) or
        (airyard_p_in is not None and airyard_p_in >= 35 and expl_p_inner >= 55)
    )

    is_slot_poss = (
        'volume' in activators or
        'route' in activators or
        'yac' in activators or
        ('separator' in activators and not is_deep_wr)
    )

    if sh_pctl is not None:
        if 'deep' in activators and is_deep_wr and sh_pctl >= 65:
            mults.append(_shr(1.12, DEEP_SHRINK))
            sh_pct_str = f"{sh_rate:.0f}%" if sh_rate is not None else "high"
            lit_flags.append(
                f"single-high shell (opp {sh_pct_str} Cover-1/3) -> deep one-on-ones"
            )
        elif 'deep' in activators and is_deep_wr and sh_pctl <= 35:
            mults.append(_shr(0.90, DEEP_SHRINK))
            th_pct_str = f"{th_rate:.0f}%" if th_rate is not None else "high"
            suppress.append(
                f"two-high brackets the deep ball (opp {th_pct_str} two-high)"
            )

        if 'separator' in activators and sh_pctl >= 65 and sh_man is not None and sh_man >= 32:
            mults.append(_shr(1.10, COV_SHRINK))
            lit_flags.append(
                f"wins man one-on-one (opp {sh_man:.0f}% man)"
            )

        if is_slot_poss and sh_pctl <= 35:
            mults.append(_shr(1.06, COV_SHRINK))
            th_pct_str = f"{th_rate:.0f}%" if th_rate is not None else "high"
            lit_flags.append(
                f"two-high softens underneath (opp {th_pct_str} two-high)"
            )

    # -- 13. COVERAGE SPECIALIST (per-week activation) -----------------------
    cspec = v.get('cspec')
    if cspec is not None and sh_data:
        cs_keys = cspec.get('best_keys') or [cspec.get('best_key')]
        cs_pctl = cspec.get('pctl', 0) or 0
        _NM = {'man':'Man','c2':'Cover-2','c3':'Cover-3','c4':'Cover-4','c6':'Cover-6','single_high':'Single-High','two_high':'Two-High','zone':'Zone'}
        fired = None
        for ck in cs_keys:
            lg_usage = SHELL['_LEAGUE'].get(ck); opp_usage = sh_data.get(ck)
            if ck and lg_usage is not None and opp_usage is not None and opp_usage >= lg_usage + 3:
                if fired is None or (opp_usage - lg_usage) > fired[1]:
                    fired = (ck, opp_usage - lg_usage, opp_usage, lg_usage)
        if fired:
            ck, _, opp_usage, lg_usage = fired
            cs_mult = 1.13 if cs_pctl >= 95 else 1.10
            mults.append(_shr(cs_mult, COV_SHRINK))
            lit_flags.append(
                f"faces {_NM.get(ck, ck)}-heavy D (opp {opp_usage:.0f}% vs lg {lg_usage:.0f}%) "
                f"— his best scheme"
            )

    all_flags = lit_flags + suppress

    # total activatable conditions (verbatim legacy total_conds derivation)
    base_conds  = 4
    extra_conds = (
        (1 if 'deep' in activators else 0) +
        (1 if 'volume' in activators else 0) +
        (1 if dome else 0) +
        (1 if 'yac' in activators else 0) +
        (1 if has_own_env else 0) +
        (1 if (has_own_env and has_opp_env) else 0) +
        (1 if (has_own_env and has_opp_env) else 0) +
        (1 if (sh_pctl is not None and 'deep' in activators and is_deep_wr) else 0) +
        (1 if (sh_pctl is not None and 'separator' in activators) else 0) +
        (1 if (sh_pctl is not None and is_slot_poss) else 0) +
        (1 if (cspec is not None and sh_data) else 0)
    )
    total_conds = base_conds + extra_conds

    # Engine 4-tuple contract (flagkit/engine.py): (displayed flags, FULL grading mults,
    # of_total, lit-count). week["flags"] = all_flags (boosters + suppressors); p is graded
    # off the full mults list (boom_lib.prob is an order-independent product); week["lit"] =
    # #boosters only. The separable lit-count is what makes suppressor-only weeks exact.
    return all_flags, mults, total_conds, len(lit_flags)


def empty_schedule(prof):
    # Free-agent / unsigned WRs (empty schedule) get 18 FA sentinel weeks (lab='FA', of=0).
    return 'FA'
