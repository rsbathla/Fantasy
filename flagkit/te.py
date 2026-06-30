#!/usr/bin/env python3
"""flagkit/te.py -- TE position semantics (ports build_flags_TE.py onto flagkit.engine).

ONLY the TE-specific logic lives here: the base seed, the archetype-driven skill-flag
cascade, the plain-language line, the empirical summary, and the inline per-week
activation (week_mults). Every piece of shared scaffolding (player loop, BYE, grading,
record/week assembly, write) is in flagkit/engine.py and is NOT duplicated.

TE's legacy per-week logic is an inline function (week_mults) with suppressors and an
of_ids accumulator, so this module uses the FUNCTIONAL activation style:

    activate(profile, base, skill_flags, opp_data, week_ctx) -> (lit_flags, lit_mults, of_total)

The logic below is transcribed verbatim from build_flags_TE.py so the output is
byte-for-byte identical (verified by diffing boom/flags_TE.json).
"""
import json
import os
from boom_lib import reg_base, cap

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repo root (flagkit/ is one level down)
POS = 'TE'

# Team environment data (own + opponent lookups per week)
TENV = json.load(open(os.path.join(HERE, 'boom', 'team_env.json')))

# Defense coverage shell: real single/two-high rates per team
SHELL = json.load(open(os.path.join(HERE, 'boom', 'defense_shell.json')))

# Opponent defense (covp/runp/manp/sackp/tiers) -- the engine passes only the opp code
# to opp_data(), so this module loads defense2026.json itself (== boom_lib.load()'s `de`).
DE = json.load(open(os.path.join(HERE, 'boom', 'defense2026.json')))


# ------------------------------------------------------------------------------
# Helper: empirical string from gamelog
# ------------------------------------------------------------------------------
def empirical(k, gl, bd):
    SPIKE = bd['SPIKE'][POS]
    games = gl.get(k, [])
    ng = len(games)
    if ng == 0:
        return "No 2025 active-game history."
    booms = [g for g in games if g.get('boom', 0) == 1]
    nb = len(booms)
    if nb == 0:
        return f"0 ceiling games in {ng} active (no >={SPIKE}-pt game in sample; below boom threshold)."
    home_b  = sum(1 for g in booms if g.get('home'))
    dome_b  = sum(1 for g in booms if g.get('dome'))
    soft_p  = sum(1 for g in booms if g.get('opp_passp', 50) <= 35)
    soft_r  = sum(1 for g in booms if g.get('opp_runp',  50) <= 35)
    avg_proj_boom = round(sum(g.get('proj',0) for g in booms) / nb, 1)
    notes = []
    if home_b >= max(1, nb * 0.5):
        notes.append(f"{home_b}/{nb} at home")
    if dome_b >= max(1, nb * 0.5):
        notes.append(f"{dome_b}/{nb} in dome/neutral")
    if soft_p >= max(1, nb * 0.4):
        notes.append(f"{soft_p}/{nb} vs soft pass-D (opp_passp<=35)")
    if soft_r >= max(1, nb * 0.4):
        notes.append(f"{soft_r}/{nb} vs soft run-D (opp_runp<=35)")
    cluster = "; ".join(notes) if notes else "spread across varied conditions"
    return f"{nb} ceiling games in {ng} active (avg proj on boom days: {avg_proj_boom}): {cluster}."


# ------------------------------------------------------------------------------
# Archetype classifier -- drives which flags are built
# ------------------------------------------------------------------------------
def classify_archetype(tgt_share, boom_pctl, cov_proof_pctl, yac_pctl, YACoe,
                       route_eff_pctl, rec_eff_pctl, YPRR, airyard_pct, oline_pctl):
    """Returns primary archetype label. Players can satisfy multiple; primary = first match."""
    # True #1 read: volume is the dominant driver
    if tgt_share >= 0.22:
        return 'VOLUME_TE1'
    # High boom_pctl + meaningful airyard share = seam/aDOT player
    if YPRR >= 1.3 and airyard_pct >= 12:
        return 'SEAM'
    # Coverage-proof mismatch winner (cov_proof or rec_eff both very high, regardless of volume)
    if cov_proof_pctl >= 85 and rec_eff_pctl >= 70:
        return 'COV_PROOF'
    # YAC threat: positive YACoe AND high yac_pctl
    if yac_pctl >= 78 and YACoe > 0.1:
        return 'YAC_THREAT'
    # Mid-volume with strong TD/boom history
    if tgt_share >= 0.16 and boom_pctl >= 70:
        return 'MIDVOL_BOOM'
    # Pure TD-dependent (high boom, low share)
    if boom_pctl >= 70 and tgt_share < 0.16:
        return 'TD_DEPENDENT'
    # Moderate everything
    if tgt_share >= 0.14:
        return 'MIDVOL'
    # Low-volume TD lightning
    return 'LOW_VOL'


# ------------------------------------------------------------------------------
# Per-player flag builder -- returns (skill_flags, of_ids, line_str)
# ------------------------------------------------------------------------------
def build_skill_flags(key, v, SPIKE):
    fus    = v.get('fus')  or {}
    usage  = v.get('usage') or {}
    yaco   = v.get('yaco') or {}
    adot_d = v.get('adot') or {}
    sis    = v.get('sis')  or {}
    adv2   = v.get('adv2')         # 2-season advanced profile; None for rookies/no history

    # -- usage fields --
    tgt_share  = usage.get('tgt_share',  0)
    rz_share   = usage.get('rz_share',   0)    # almost always 0; use boom_pctl as proxy
    catch_rate = usage.get('catch_rate', 0)
    ypt        = usage.get('ypt',        0)
    tgt_pg     = usage.get('tgt_pg',     0)
    dk_pg      = usage.get('dk_pg',      0)
    routes_pg  = usage.get('routes_pg',  0)

    # -- fus percentile fields --
    boom_pctl      = fus.get('boom_pctl',           50)
    ceiling_pctl   = fus.get('ceiling_pctl',        50)
    spike_pctl     = fus.get('spike_pctl',          50)
    value_pctl     = fus.get('value_pctl',          50)
    route_eff_pctl = fus.get('route_eff_pctl',      50)
    cov_proof_pctl = fus.get('coverage_proof_pctl', 50)
    rec_eff_pctl   = fus.get('rec_eff_pctl',        50)
    sep_pctl       = fus.get('separation_pctl',     50)
    yac_pctl       = fus.get('yac_pctl',            50)
    explo_pctl     = fus.get('explosive_pctl',       0)
    adv_pctl       = fus.get('adv_pctl',            50)
    sis_val_pctl   = fus.get('sis_value_pctl',      50)
    oline_pctl     = fus.get('oline_pctl',          50)
    matchup_pctl   = fus.get('matchup_pctl',        50)

    # -- adot / yaco / sis fields --
    aDOT    = adot_d.get('aDOT',    0)
    YACoe   = yaco.get('YACoe',     0)
    MTFoe   = yaco.get('MTFoe',     0)
    YPRR    = sis.get('YPRR',       0)
    airpct  = sis.get('airyard_pct',0)
    eff_comb= sis.get('eff_combined',0)
    TPRR_w  = sis.get('TPRR_w',    0)
    FP_RR   = sis.get('FP_RR',     0)

    # -- 2-season advanced fields (prefer when available) --
    if adv2:
        adv2_g        = adv2.get('g', 0)
        adv2_tgt_share= adv2.get('tgt_share', 0)   # 0-100 scale
        adv2_rec_pg   = adv2.get('rec_pg', 0)
        adv2_td_pg    = adv2.get('td_pg', 0)
        adv2_aDOT     = adv2.get('aDOT', 0)
        adv2_ay_share = adv2.get('ay_share', 0)    # 0-100 scale
        adv2_yptouch  = adv2.get('yptouch', 0)
        adv2_ypt      = adv2.get('ypt', 0)
        adv2_catch    = adv2.get('catch', 0)       # catch rate 0-100 pctl
    else:
        adv2_g = adv2_tgt_share = adv2_rec_pg = adv2_td_pg = 0
        adv2_aDOT = adv2_ay_share = adv2_yptouch = adv2_ypt = adv2_catch = 0

    # -- 2-season FP charting (chart2) -- prefer blend when present (None for rookies) --
    chart2 = v.get('chart2')
    c2b    = (chart2.get('blend') if isinstance(chart2, dict) else None) or {}
    has_c2 = bool(c2b)
    # chart2 blend fields (WR/TE schema)
    c2_g            = c2b.get('g',             0)
    c2_tprr         = c2b.get('tprr',          0)   # targets per route run
    c2_yprr         = c2b.get('yprr',          0)   # yards per route run
    c2_fr_pct       = c2b.get('fr_pct',        0)   # 1st-read target %
    c2_aDOT         = c2b.get('aDOT',          0)
    c2_ay_share     = c2b.get('ay_share',      0)
    c2_deep_pct     = c2b.get('deep_pct',      0)
    c2_yac_rec      = c2b.get('yac_rec',       0)   # YAC per reception
    c2_mtf_rec      = c2b.get('mtf_rec',       0)   # missed tackles forced per reception
    c2_catch        = c2b.get('catch',         0)   # catch rate percentile (0-100)
    c2_contested_pct= c2b.get('contested_pct', 0)   # contested-catch %
    c2_slot_pct     = c2b.get('slot_pct',      0)   # % snaps in slot
    c2_fp_rr        = c2b.get('fp_rr',         0)

    arch = classify_archetype(tgt_share, boom_pctl, cov_proof_pctl, yac_pctl,
                               YACoe, route_eff_pctl, rec_eff_pctl, YPRR, airpct, oline_pctl)

    flags  = []
    of_ids = []

    # ==========================================================================
    # ARCHETYPE-SPECIFIC FLAGS -- every player gets a unique combination
    # ==========================================================================

    # --- VOLUME_TE1 -----------------------------------------------------------
    if arch == 'VOLUME_TE1':
        # FLAG 1: True target-share domination -- prefer chart2 (tprr+fr_pct+yprr) when present
        pct = round(tgt_share * 100, 1)
        if has_c2:
            vol_d = (f"2yr {c2_fr_pct:.0f}% 1st-read, TPRR {c2_tprr:.3f}, YPRR {c2_yprr:.2f} "
                     f"over {c2_g}g (FP charting); "
                     f"adv2 {adv2_tgt_share}% tgt share, {adv2_rec_pg} rec/g over {adv2_g}g")
        elif adv2:
            vol_d = (f"2yr {adv2_tgt_share}% tgt share, {adv2_rec_pg} rec/g over {adv2_g}g "
                     f"(2024+2025 startable games)")
        else:
            cr_note  = f", catch_rate {round(catch_rate*100,1)}%" if catch_rate > 0 else ""
            rec_note = f", rec_eff {rec_eff_pctl:.0f}th pctl" if rec_eff_pctl >= 65 else ""
            sis_note = f", sis_val {sis_val_pctl:.0f}th pctl" if sis_val_pctl >= 70 else ""
            vol_d = f"tgt_share {pct}% (TE-elite){cr_note}{rec_note}{sis_note}"
        flags.append({"f": "Volume leader -- true #1 read",
            "d": vol_d,
            "amp": "pass-funnel (runp>=60 & covp<=45) / soft TE tier / negative script (team trails, must pass)"})
        of_ids += ["soft_te", "pass_funnel", "neg_script"]

        # FLAG 2: Coverage-proof (if high cov_proof) OR catch-reliability (if not)
        # Prefer chart2 yprr+contested_pct+catch for the coverage-proof citation
        if cov_proof_pctl >= 80:
            sep_note = f", sep {sep_pctl:.0f}th" if sep_pctl >= 40 else ""
            if has_c2:
                cp_d = (f"2yr YPRR {c2_yprr:.2f}, {c2_contested_pct:.0f}% contested-catch, "
                        f"catch {c2_catch:.0f}th pctl over {c2_g}g (FP charting); "
                        f"cov_proof {cov_proof_pctl:.0f}th{sep_note} -- wins any assignment (zone or man)")
            else:
                cp_d = f"cov_proof {cov_proof_pctl:.0f}th pctl{sep_note}; rec_eff {rec_eff_pctl:.0f}th -- wins any assignment (zone or man)"
            flags.append({"f": "Coverage-proof mismatch vs LB/safety",
                "d": cp_d,
                "amp": "man-heavy D (manp>=68, LB/safety on TE = easy mismatch)"})
            of_ids += ["man_mismatch"]
        elif rec_eff_pctl >= 65:
            if has_c2:
                rel_d = (f"2yr YPRR {c2_yprr:.2f}, catch {c2_catch:.0f}th pctl over {c2_g}g "
                         f"(FP charting); rec_eff {rec_eff_pctl:.0f}th -- chains drives, hard to defend short/intermediate")
            else:
                rel_d = f"rec_eff {rec_eff_pctl:.0f}th pctl; catch_rate {round(catch_rate*100,1)}% -- chains drives, hard to defend in short/intermediate"
            flags.append({"f": "Route reliability / catch efficiency",
                "d": rel_d,
                "amp": "man-heavy (manp>=65) / zone underneath"})
            of_ids += ["man_mismatch"]

        # FLAG 3: TD ceiling -- cite 2yr td_pg if available
        if boom_pctl >= 65:
            if adv2:
                td_d = (f"2yr {adv2_td_pg:.2f} TD/g over {adv2_g}g; "
                        f"boom_pctl {boom_pctl:.0f}th -- sustained multi-score ceiling history")
            else:
                td_d = f"boom_pctl {boom_pctl:.0f}th; ceiling_pctl {ceiling_pctl:.0f}th -- history of multi-score ceiling games"
            flags.append({"f": "TD ceiling / boom games",
                "d": td_d,
                "amp": "soft TE tier / positive field position / home crowd near GL"})
            of_ids += ["rz_soft_te", "home_rz"]
        elif boom_pctl >= 40:
            if adv2:
                td_d = (f"2yr {adv2_td_pg:.2f} TD/g over {adv2_g}g; "
                        f"boom_pctl {boom_pctl:.0f}th -- TD upside exists but not primary red-zone threat")
            else:
                td_d = f"boom_pctl {boom_pctl:.0f}th; spike_pctl {spike_pctl:.0f}th -- TD upside exists but not primary red-zone threat"
            flags.append({"f": "Moderate TD ceiling",
                "d": td_d,
                "amp": "soft TE tier / favorable script"})
            of_ids += ["rz_soft_te"]

        # FLAG 4: YAC / after-catch -- prefer chart2 yac_rec+mtf_rec when present
        if yac_pctl >= 68 and YACoe >= 0:
            if has_c2:
                yac_d = (f"2yr {c2_yac_rec:.1f} YAC/rec, {c2_mtf_rec:.2f} MTF/rec "
                         f"over {c2_g}g (FP charting); "
                         f"yac_pctl {yac_pctl:.0f}th -- generates yards after catch in open field")
            elif adv2:
                yac_d = (f"2yr {adv2_yptouch:.1f} yds/touch over {adv2_g}g; "
                         f"yac_pctl {yac_pctl:.0f}th -- generates yards after catch in open field")
            else:
                yacoe_note = f", YACoe +{round(YACoe,2)}" if YACoe > 0 else ""
                yac_d = f"yac_pctl {yac_pctl:.0f}th{yacoe_note} -- generates yards after catch in open field"
            flags.append({"f": "YAC / after-catch value",
                "d": yac_d,
                "amp": "zone coverage (seam holes / YAC lanes) / weak pass-rush (sackp<=32, timing intact)"})
            of_ids += ["zone_yac", "weak_rush_yac"]
        elif yac_pctl >= 55 and YACoe < 0:
            # High pctl but negative YACoe -- note the disconnect
            if has_c2:
                yac_d = (f"2yr {c2_yac_rec:.1f} YAC/rec, {c2_mtf_rec:.2f} MTF/rec "
                         f"over {c2_g}g (FP charting); "
                         f"yac_pctl {yac_pctl:.0f}th -- moderate YAC volume; not explosive after-contact")
            elif adv2:
                yac_d = (f"2yr {adv2_yptouch:.1f} yds/touch over {adv2_g}g; "
                         f"yac_pctl {yac_pctl:.0f}th but YACoe {round(YACoe,2)} -- moderate YAC volume; not an explosive after-contact player")
            else:
                yac_d = f"yac_pctl {yac_pctl:.0f}th but YACoe {round(YACoe,2)} -- moderate YAC volume; not an explosive after-contact player"
            flags.append({"f": "After-catch opportunity (pctl-only; YACoe below expectation)",
                "d": yac_d,
                "amp": "zone / soft TE tier (yardage, not big play)"})
            of_ids += ["zone_yac"]

        # FLAG 5: Advanced composite / adv_pctl
        if adv_pctl >= 90:
            flags.append({"f": "Elite advanced efficiency",
                "d": f"adv_pctl {adv_pctl:.0f}th; value_pctl {value_pctl:.0f}th -- elite composite across all advanced metrics",
                "amp": "any matchup that opens volume (pass-funnel / soft tier / negative script)"})
            of_ids += ["soft_te"]

        # FLAG 6: O-line if excellent
        if oline_pctl >= 75:
            flags.append({"f": "Premium O-line protection",
                "d": f"oline_pctl {oline_pctl:.0f}th -- routes develop fully; seam/dig timing maximized",
                "amp": "heavy pass-rush (own OL neutralizes) / soft TE tier"})
            of_ids += ["weak_rush_oline"]

    # --- SEAM (SIS-based: YPRR + airyard_pct) ---------------------------------
    elif arch == 'SEAM':
        # FLAG 1: Seam / vertical profile -- prefer chart2 aDOT+ay_share+deep_pct
        eff_note = f", eff_combined {eff_comb:.0f}" if eff_comb > 0 else ""
        if has_c2:
            seam_d = (f"2yr aDOT {c2_aDOT:.1f}, {c2_ay_share:.1f}% air-yd share, "
                      f"{c2_deep_pct:.0f}% deep targets over {c2_g}g (FP charting); "
                      f"YPRR {c2_yprr:.2f}, TPRR {c2_tprr:.3f} -- earns downfield targets on per-route basis")
        elif adv2:
            seam_d = (f"2yr aDOT {adv2_aDOT:.1f} over {adv2_g}g, {adv2_ay_share}% air-yd share; "
                      f"YPRR {YPRR} (SIS){eff_note}; FP_RR {FP_RR} -- earns downfield targets on per-route basis")
        else:
            seam_d = f"YPRR {YPRR} (SIS); airyard_pct {airpct}%{eff_note}; FP_RR {FP_RR} -- earns downfield targets on per-route basis"
        flags.append({"f": "Seam threat -- aDOT / air-yard ceiling",
            "d": seam_d,
            "amp": "zone coverage (seam opens vs 2-hi) / weak pass-rush (sackp<=30, needs time for seam routes) / dome"})
        of_ids += ["zone_seam", "weak_rush_seam", "dome_seam"]

        # FLAG 2: Coverage proof (if also high) -- prefer chart2 yprr+contested+catch
        if cov_proof_pctl >= 65:
            if has_c2:
                cp_d = (f"2yr YPRR {c2_yprr:.2f}, {c2_contested_pct:.0f}% contested-catch, "
                        f"catch {c2_catch:.0f}th pctl over {c2_g}g (FP charting); "
                        f"cov_proof {cov_proof_pctl:.0f}th -- wins vs any coverage look")
            else:
                cp_d = f"cov_proof {cov_proof_pctl:.0f}th pctl; rec_eff {rec_eff_pctl:.0f}th -- wins vs any coverage look"
            flags.append({"f": "Coverage-proof reliability",
                "d": cp_d,
                "amp": "man-heavy (manp>=68, earns LB mismatch on seam)"})
            of_ids += ["man_mismatch"]

        # FLAG 3: TD spike profile -- cite 2yr td_pg if available
        if boom_pctl >= 65:
            if adv2:
                td_d = (f"2yr {adv2_td_pg:.2f} TD/g over {adv2_g}g; "
                        f"boom_pctl {boom_pctl:.0f}th -- seam TDs and 20+ yd catches drive ceiling")
            else:
                td_d = f"boom_pctl {boom_pctl:.0f}th; spike_pctl {spike_pctl:.0f}th -- seam TDs and 20+ yd catches drive ceiling"
            flags.append({"f": "TD / big-play ceiling",
                "d": td_d,
                "amp": "soft TE tier / positive field position"})
            of_ids += ["rz_soft_te"]

        # FLAG 4: Volume / usage support
        if tgt_share >= 0.13:
            flags.append({"f": "Functional target share to support ceiling",
                "d": f"tgt_share {round(tgt_share*100,1)}%; tgt_share_w {sis.get('tgt_share_w',0):.1f}% (SIS route-weighted) -- enough volume to hit threshold via big play",
                "amp": "pass-funnel / soft TE tier / negative script"})
            of_ids += ["soft_te", "pass_funnel"]

        # FLAG 5: YAC if positive -- prefer chart2 yac_rec+mtf_rec
        if yac_pctl >= 60 and YACoe > 0:
            if has_c2:
                yac_d = (f"2yr {c2_yac_rec:.1f} YAC/rec, {c2_mtf_rec:.2f} MTF/rec "
                         f"over {c2_g}g (FP charting); "
                         f"yac_pctl {yac_pctl:.0f}th -- turns short crosses into big gains after catch")
            elif adv2:
                yac_d = (f"2yr {adv2_yptouch:.1f} yds/touch over {adv2_g}g; "
                         f"yac_pctl {yac_pctl:.0f}th -- turns short crosses into big gains after catch")
            else:
                yac_d = f"yac_pctl {yac_pctl:.0f}th; YACoe +{round(YACoe,2)} -- turns short crosses into big gains after catch"
            flags.append({"f": "Positive YAC -- extends seam plays",
                "d": yac_d,
                "amp": "zone / open grass post-catch"})
            of_ids += ["zone_yac"]

        # FLAG 6: O-line
        if oline_pctl >= 65:
            flags.append({"f": "Good O-line protection for seam timing",
                "d": f"oline_pctl {oline_pctl:.0f}th -- allows routes to develop on timing; critical for seam depth",
                "amp": "vs heavy pass-rush (own OL insulates)"})
            of_ids += ["weak_rush_oline"]

    # --- COV_PROOF ------------------------------------------------------------
    elif arch == 'COV_PROOF':
        # FLAG 1: Mismatch + coverage-proof -- prefer chart2 yprr+contested+catch
        sep_note = f", sep {sep_pctl:.0f}th" if sep_pctl >= 45 else ""
        if has_c2:
            cp1_d = (f"2yr YPRR {c2_yprr:.2f}, {c2_contested_pct:.0f}% contested-catch, "
                     f"catch {c2_catch:.0f}th pctl over {c2_g}g (FP charting); "
                     f"cov_proof {cov_proof_pctl:.0f}th{sep_note} -- wins reliably vs LB/safety assignment")
        else:
            cp1_d = f"cov_proof {cov_proof_pctl:.0f}th pctl; rec_eff {rec_eff_pctl:.0f}th{sep_note} -- wins reliably vs LB/safety assignment"
        flags.append({"f": "Elite coverage-proof mismatch winner",
            "d": cp1_d,
            "amp": "man-heavy D (manp>=68 -> TE on linebacker = easy win) / blitz (LB pulled from coverage)"})
        of_ids += ["man_mismatch"]

        # FLAG 2: Volume context
        if tgt_share >= 0.16:
            flags.append({"f": "Solid target share for ceiling floor",
                "d": f"tgt_share {round(tgt_share*100,1)}%; catch_rate {round(catch_rate*100,1)}% -- consistent chain-mover, ceiling not pure TD lottery",
                "amp": "pass-funnel / soft TE tier / negative script"})
            of_ids += ["soft_te", "pass_funnel"]
        elif tgt_share >= 0.10:
            flags.append({"f": "Moderate volume -- ceiling is mismatch + TD spiky",
                "d": f"tgt_share {round(tgt_share*100,1)}% -- not a volume TE; ceiling via mismatch exploitation",
                "amp": "soft TE tier / man-heavy"})
            of_ids += ["soft_te"]

        # FLAG 3: TD/boom role -- cite 2yr td_pg if available
        if boom_pctl >= 60:
            if adv2:
                td_d = (f"2yr {adv2_td_pg:.2f} TD/g over {adv2_g}g; "
                        f"boom_pctl {boom_pctl:.0f}th -- mismatch near goal line = TD spike games")
            else:
                td_d = f"boom_pctl {boom_pctl:.0f}th; spike_pctl {spike_pctl:.0f}th -- mismatch near goal line = TD spike games"
            flags.append({"f": "TD ceiling / multi-score potential",
                "d": td_d,
                "amp": "soft TE tier / positive field position"})
            of_ids += ["rz_soft_te", "home_rz"]
        else:
            if adv2:
                td_d = (f"2yr {adv2_td_pg:.2f} TD/g over {adv2_g}g; "
                        f"boom_pctl {boom_pctl:.0f}th -- ceiling is chain-mover + occasional TD")
            else:
                td_d = f"boom_pctl {boom_pctl:.0f}th; ceiling_pctl {ceiling_pctl:.0f}th -- ceiling is chain-mover + occasional TD"
            flags.append({"f": "Consistent scorer (moderate TD upside)",
                "d": td_d,
                "amp": "soft TE tier"})
            of_ids += ["rz_soft_te"]

        # FLAG 4: YAC if positive -- prefer chart2 yac_rec+mtf_rec
        if yac_pctl >= 60 and YACoe >= 0:
            if has_c2:
                yac_d = (f"2yr {c2_yac_rec:.1f} YAC/rec, {c2_mtf_rec:.2f} MTF/rec "
                         f"over {c2_g}g (FP charting); "
                         f"yac_pctl {yac_pctl:.0f}th -- adds ceiling beyond the catch")
            elif adv2:
                yac_d = (f"2yr {adv2_yptouch:.1f} yds/touch over {adv2_g}g; "
                         f"yac_pctl {yac_pctl:.0f}th -- adds ceiling beyond the catch")
            else:
                yacoe_str = f"YACoe +{round(YACoe,2)}" if YACoe > 0 else f"YACoe {round(YACoe,2)}"
                yac_d = f"yac_pctl {yac_pctl:.0f}th; {yacoe_str} -- adds ceiling beyond the catch"
            flags.append({"f": "YAC / after-catch upside",
                "d": yac_d,
                "amp": "zone coverage (YAC lanes) / soft TE tier"})
            of_ids += ["zone_yac"]

        # FLAG 5: Route efficiency
        if route_eff_pctl >= 60:
            flags.append({"f": "Route efficiency -- wins vs zone too",
                "d": f"route_eff {route_eff_pctl:.0f}th pctl -- precise route-runner; not just man-win specialist",
                "amp": "zone coverage (manp<=32) / heavy man"})
            of_ids += ["zone_seam"]

        # FLAG 6: Advanced composite
        if adv_pctl >= 75:
            flags.append({"f": "High advanced composite",
                "d": f"adv_pctl {adv_pctl:.0f}th -- elite score across all advanced metrics supports ceiling case",
                "amp": "soft TE tier / pass-heavy game"})
            of_ids += ["soft_te"]

        # FLAG 7: O-line
        if oline_pctl >= 65:
            flags.append({"f": "Good O-line protection",
                "d": f"oline_pctl {oline_pctl:.0f}th -- route timing preserved",
                "amp": "vs heavy rush (own OL shields)"})
            of_ids += ["weak_rush_oline"]

    # --- YAC_THREAT -----------------------------------------------------------
    elif arch == 'YAC_THREAT':
        # FLAG 1: YAC is the core ceiling driver -- prefer chart2 yac_rec+mtf_rec
        mtf_note  = f", MTFoe +{round(MTFoe,2)}" if MTFoe > 0.02 else ""
        if has_c2:
            yac_d = (f"2yr {c2_yac_rec:.1f} YAC/rec, {c2_mtf_rec:.2f} MTF/rec "
                     f"over {c2_g}g (FP charting); "
                     f"yac_pctl {yac_pctl:.0f}th -- ceiling is catch-and-run; breaks tackles, finds open grass")
        elif adv2:
            yac_d = (f"2yr {adv2_yptouch:.1f} yds/touch over {adv2_g}g; "
                     f"yac_pctl {yac_pctl:.0f}th{mtf_note} -- ceiling is catch-and-run; breaks tackles, finds open grass")
        else:
            yacoe_str = f", YACoe +{round(YACoe,2)}" if YACoe > 0 else ""
            yac_d = f"yac_pctl {yac_pctl:.0f}th{yacoe_str}{mtf_note} -- ceiling is catch-and-run; breaks tackles, finds open grass"
        flags.append({"f": "Elite YAC / after-catch ceiling",
            "d": yac_d,
            "amp": "zone coverage (seam holes, no LOS jam) / weak pass-rush (sackp<=32, clean pocket for timing) / soft TE tier"})
        of_ids += ["zone_yac", "weak_rush_yac", "soft_te"]

        # FLAG 2: Route efficiency (if present) amplifies YAC by creating separation for it
        if route_eff_pctl >= 65:
            flags.append({"f": "Route efficiency -- gets open to maximize YAC",
                "d": f"route_eff {route_eff_pctl:.0f}th pctl -- crisp routes create separation needed to turn catches into yards",
                "amp": "zone (manp<=32) / man-heavy (manp>=68) -- earns catches regardless"})
            of_ids += ["zone_seam", "man_mismatch"]
        elif rec_eff_pctl >= 60:
            flags.append({"f": "Reliable catch efficiency",
                "d": f"rec_eff {rec_eff_pctl:.0f}th pctl -- catches what comes his way; sets up YAC",
                "amp": "zone / soft TE tier"})
            of_ids += ["zone_seam"]

        # FLAG 3: Volume support
        if tgt_share >= 0.18:
            flags.append({"f": "High target volume to enable YAC ceiling",
                "d": f"tgt_share {round(tgt_share*100,1)}%; catch_rate {round(catch_rate*100,1)}% -- enough opportunities to hit threshold via YAC",
                "amp": "pass-funnel / negative script / soft TE tier"})
            of_ids += ["pass_funnel", "neg_script"]
        elif tgt_share >= 0.13:
            flags.append({"f": "Solid volume for ceiling access",
                "d": f"tgt_share {round(tgt_share*100,1)}% -- moderate volume; ceiling requires catching 5+ and converting to big YAC",
                "amp": "pass-funnel / soft TE tier"})
            of_ids += ["pass_funnel"]

        # FLAG 4: TD ceiling -- cite 2yr td_pg if available
        if boom_pctl >= 55:
            if adv2:
                td_d = (f"2yr {adv2_td_pg:.2f} TD/g over {adv2_g}g; "
                        f"boom_pctl {boom_pctl:.0f}th -- YAC near GL converts to TDs")
            else:
                td_d = f"boom_pctl {boom_pctl:.0f}th; spike_pctl {spike_pctl:.0f}th -- YAC near GL converts to TDs"
            flags.append({"f": "TD ceiling / spike potential",
                "d": td_d,
                "amp": "soft TE tier / positive field position"})
            of_ids += ["rz_soft_te", "home_rz"]
        else:
            if adv2:
                td_d = (f"2yr {adv2_td_pg:.2f} TD/g over {adv2_g}g; "
                        f"boom_pctl {boom_pctl:.0f}th -- needs big yardage day to hit threshold")
            else:
                td_d = f"boom_pctl {boom_pctl:.0f}th; ceiling_pctl {ceiling_pctl:.0f}th -- needs big yardage day to hit threshold"
            flags.append({"f": "Modest TD upside -- ceiling is YAC-driven, not score-driven",
                "d": td_d,
                "amp": "soft TE tier / zone"})
            of_ids += ["rz_soft_te"]

        # FLAG 5: Coverage-proof if meaningful
        if cov_proof_pctl >= 60:
            flags.append({"f": "Coverage reliability vs various looks",
                "d": f"cov_proof {cov_proof_pctl:.0f}th pctl -- creates separation even without pure route technique",
                "amp": "man-heavy (manp>=65)"})
            of_ids += ["man_mismatch"]

        # FLAG 6: O-line if premium
        if oline_pctl >= 75:
            flags.append({"f": "Premium O-line -- route timing intact",
                "d": f"oline_pctl {oline_pctl:.0f}th -- pocket stays clean for timing catches that launch YAC",
                "amp": "vs heavy rush"})
            of_ids += ["weak_rush_oline"]

    # --- MIDVOL_BOOM ----------------------------------------------------------
    elif arch == 'MIDVOL_BOOM':
        # FLAG 1: Volume with TD overlay -- prefer chart2 tprr+fr_pct+yprr when present
        pct = round(tgt_share * 100, 1)
        if has_c2:
            mvb_d = (f"2yr {c2_fr_pct:.0f}% 1st-read, TPRR {c2_tprr:.3f}, YPRR {c2_yprr:.2f} "
                     f"over {c2_g}g (FP charting); "
                     f"2yr {adv2_td_pg:.2f} TD/g -- generates explosive (multi-TD) games")
        elif adv2:
            mvb_d = (f"2yr {adv2_tgt_share}% tgt share, {adv2_rec_pg} rec/g over {adv2_g}g; "
                     f"2yr {adv2_td_pg:.2f} TD/g -- not a target hog but generates explosive (multi-TD) games")
        else:
            mvb_d = f"tgt_share {pct}%; boom_pctl {boom_pctl:.0f}th -- not a target hog but generates explosive (multi-TD) games"
        flags.append({"f": "Mid-volume + high TD ceiling",
            "d": mvb_d,
            "amp": "soft TE tier / red-zone (boom history = GL proximity) / pass-funnel"})
        of_ids += ["soft_te", "rz_soft_te", "pass_funnel"]

        # FLAG 2: Coverage-proof if strong
        if cov_proof_pctl >= 70:
            sep_note = f", sep {sep_pctl:.0f}th" if sep_pctl >= 40 else ""
            flags.append({"f": "Coverage-proof -- beats man/LB mismatch",
                "d": f"cov_proof {cov_proof_pctl:.0f}th pctl{sep_note}; rec_eff {rec_eff_pctl:.0f}th",
                "amp": "man-heavy (manp>=68)"})
            of_ids += ["man_mismatch"]
        elif rec_eff_pctl >= 75:
            flags.append({"f": "Catch efficiency / reliable target",
                "d": f"rec_eff {rec_eff_pctl:.0f}th pctl; catch_rate {round(catch_rate*100,1)}%",
                "amp": "man-heavy / zone"})
            of_ids += ["man_mismatch"]

        # FLAG 3: YAC (only if genuinely positive) -- prefer chart2 yac_rec+mtf_rec
        if yac_pctl >= 70 and YACoe >= 0:
            if has_c2:
                yac_d = (f"2yr {c2_yac_rec:.1f} YAC/rec, {c2_mtf_rec:.2f} MTF/rec "
                         f"over {c2_g}g (FP charting); "
                         f"yac_pctl {yac_pctl:.0f}th -- turns catches into chunk plays")
            elif adv2:
                yac_d = (f"2yr {adv2_yptouch:.1f} yds/touch over {adv2_g}g; "
                         f"yac_pctl {yac_pctl:.0f}th -- turns catches into chunk plays")
            else:
                yacoe_str = f", YACoe +{round(YACoe,2)}" if YACoe > 0 else ""
                yac_d = f"yac_pctl {yac_pctl:.0f}th{yacoe_str} -- turns catches into chunk plays"
            flags.append({"f": "YAC / explosive after-catch",
                "d": yac_d,
                "amp": "zone (seam holes) / weak pass-rush (sackp<=32)"})
            of_ids += ["zone_yac", "weak_rush_yac"]

        # FLAG 4: Route efficiency (if above threshold)
        if route_eff_pctl >= 75:
            flags.append({"f": "Elite route efficiency",
                "d": f"route_eff {route_eff_pctl:.0f}th pctl -- precise route-runner that wins consistently",
                "amp": "man-heavy / zone (benefits both coverage types)"})
            of_ids += ["man_sep"]
        elif route_eff_pctl >= 55 and adv_pctl >= 75:
            flags.append({"f": "Advanced composite efficiency",
                "d": f"adv_pctl {adv_pctl:.0f}th; route_eff {route_eff_pctl:.0f}th -- advanced-metric elite",
                "amp": "soft TE tier / heavy usage week"})
            of_ids += ["soft_te"]

        # FLAG 5: Spike_pctl (high spike = multi-yd games even with modest targets)
        if spike_pctl >= 35:
            flags.append({"f": "Spike / big-day potential",
                "d": f"spike_pctl {spike_pctl:.0f}th; boom_pctl {boom_pctl:.0f}th -- history of outsized games vs projection",
                "amp": "soft TE tier / home (crowd / comfortable environment)"})
            of_ids += ["rz_soft_te", "home_rz"]

        # FLAG 6: O-line premium
        if oline_pctl >= 75:
            flags.append({"f": "Premium O-line -- clean pocket for timing",
                "d": f"oline_pctl {oline_pctl:.0f}th -- routes have time to develop; seam/delay concepts thrive",
                "amp": "vs heavy rush / pass-heavy game"})
            of_ids += ["weak_rush_oline"]

    # --- TD_DEPENDENT ---------------------------------------------------------
    elif arch == 'TD_DEPENDENT':
        # FLAG 1: TD/boom is the entire ceiling story -- cite 2yr td_pg if available
        if adv2:
            tdd_d = (f"2yr {adv2_td_pg:.2f} TD/g over {adv2_g}g; "
                     f"boom_pctl {boom_pctl:.0f}th -- almost entire ceiling is scoring plays; few catches can hit {SPIKE} pts")
        else:
            tdd_d = f"boom_pctl {boom_pctl:.0f}th -- almost entire ceiling is scoring plays; few catches can hit {SPIKE} pts"
        flags.append({"f": "TD-dependent boom ceiling",
            "d": tdd_d,
            "amp": "soft TE tier (4.1x swing essential) / positive field position / vs soft run-D (scoring drives easier)"})
        of_ids += ["soft_te", "rz_soft_te"]

        # FLAG 2: Coverage-proof (if high) lets him earn those TD targets
        if cov_proof_pctl >= 65:
            flags.append({"f": "Coverage-proof at point of attack",
                "d": f"cov_proof {cov_proof_pctl:.0f}th pctl; rec_eff {rec_eff_pctl:.0f}th -- earns TD targets by winning in traffic",
                "amp": "man-heavy (manp>=68, LB coverage = mismatch)"})
            of_ids += ["man_mismatch"]

        # FLAG 3: per-route aerial efficiency -- prefer chart2 yprr when present (Henry-type)
        if has_c2 and c2_yprr >= 1.2:
            eff_note = f"; eff_combined {eff_comb:.0f}" if eff_comb > 0 else ""
            flags.append({"f": "Per-route aerial efficiency (FP charting)",
                "d": (f"2yr YPRR {c2_yprr:.2f}, TPRR {c2_tprr:.3f}, {c2_ay_share:.1f}% air-yd share "
                      f"over {c2_g}g (FP charting){eff_note} -- earns yards per route run, concentrated in chunk plays"),
                "amp": "zone / weak pass-rush (sackp<=30, needs clean pocket for seam)"})
            of_ids += ["zone_seam", "weak_rush_seam"]
        elif YPRR >= 1.2:
            eff_note = f"; eff_combined {eff_comb:.0f}" if eff_comb > 0 else ""
            air_note = f"; airyard_pct {airpct:.1f}%" if airpct > 0 else ""
            flags.append({"f": "SIS: per-route aerial efficiency",
                "d": f"YPRR {YPRR} (SIS){air_note}{eff_note}; FP_RR {FP_RR} -- earns yards per route run, concentrated in chunk plays",
                "amp": "zone / weak pass-rush (sackp<=30, needs clean pocket for seam)"})
            of_ids += ["zone_seam", "weak_rush_seam"]

        # FLAG 4: YAC if genuine -- prefer chart2 yac_rec+mtf_rec
        if yac_pctl >= 55 and YACoe >= 0.5:
            if has_c2:
                yac_d = (f"2yr {c2_yac_rec:.1f} YAC/rec, {c2_mtf_rec:.2f} MTF/rec "
                         f"over {c2_g}g (FP charting); "
                         f"yac_pctl {yac_pctl:.0f}th -- even occasional catches become chunk gains")
            elif adv2:
                yac_d = (f"2yr {adv2_yptouch:.1f} yds/touch over {adv2_g}g; "
                         f"yac_pctl {yac_pctl:.0f}th -- even occasional catches become chunk gains")
            else:
                yac_d = f"yac_pctl {yac_pctl:.0f}th; YACoe +{round(YACoe,2)} -- even occasional catches become chunk gains"
            flags.append({"f": "Positive YACoe -- extends limited catches",
                "d": yac_d,
                "amp": "zone / soft TE tier"})
            of_ids += ["zone_yac"]
        elif yac_pctl >= 55:
            if has_c2:
                yac_d = (f"2yr {c2_yac_rec:.1f} YAC/rec, {c2_mtf_rec:.2f} MTF/rec "
                         f"over {c2_g}g (FP charting); "
                         f"yac_pctl {yac_pctl:.0f}th -- meaningful yardage after catch when targets come")
            elif adv2:
                yac_d = (f"2yr {adv2_yptouch:.1f} yds/touch over {adv2_g}g; "
                         f"yac_pctl {yac_pctl:.0f}th -- meaningful yardage after catch when targets come")
            else:
                yac_d = f"yac_pctl {yac_pctl:.0f}th; YACoe {round(YACoe,2)} -- meaningful yardage after catch when targets come"
            flags.append({"f": "Decent YAC profile (limited by volume)",
                "d": yac_d,
                "amp": "zone / soft TE tier"})
            of_ids += ["zone_yac"]

        # FLAG 5: Spike_pctl
        if spike_pctl >= 35:
            flags.append({"f": "High spike potential -- big-game history",
                "d": f"spike_pctl {spike_pctl:.0f}th; boom_pctl {boom_pctl:.0f}th -- stat profile for outsized games",
                "amp": "soft TE tier / home"})
            of_ids += ["home_rz"]

        # FLAG 6: O-line
        if oline_pctl >= 70:
            flags.append({"f": "Premium O-line -- pocket time for TD execution",
                "d": f"oline_pctl {oline_pctl:.0f}th -- protects QB allowing TD concepts to develop",
                "amp": "vs heavy pass-rush"})
            of_ids += ["weak_rush_oline"]

    # --- MIDVOL ---------------------------------------------------------------
    elif arch == 'MIDVOL':
        # FLAG 1: Volume is present but not elite -- prefer chart2 tprr+fr_pct+yprr when present
        pct = round(tgt_share * 100, 1)
        if has_c2:
            vol_d = (f"2yr {c2_fr_pct:.0f}% 1st-read, TPRR {c2_tprr:.3f}, YPRR {c2_yprr:.2f} "
                     f"over {c2_g}g (FP charting); "
                     f"adv2 {adv2_tgt_share}% tgt share, {adv2_rec_pg} rec/g -- steady usage; ceiling requires TD or big yardage day")
        elif adv2:
            vol_d = (f"2yr {adv2_tgt_share}% tgt share, {adv2_rec_pg} rec/g over {adv2_g}g "
                     f"-- steady usage; ceiling requires TD or big yardage day")
        else:
            cr_note = f"; catch_rate {round(catch_rate*100,1)}%" if catch_rate > 0 else ""
            ypt_note = f"; ypt {ypt:.1f}" if ypt > 0 else ""
            vol_d = f"tgt_share {pct}%{cr_note}{ypt_note} -- steady usage; ceiling requires TD or big yardage day"
        flags.append({"f": "Functional mid-tier volume",
            "d": vol_d,
            "amp": "pass-funnel / soft TE tier / negative script"})
        of_ids += ["soft_te", "pass_funnel"]

        # FLAG 2: TD ceiling -- cite 2yr td_pg if available
        if boom_pctl >= 55:
            if adv2:
                td_d = (f"2yr {adv2_td_pg:.2f} TD/g over {adv2_g}g; "
                        f"boom_pctl {boom_pctl:.0f}th -- multi-TD games in history")
            else:
                td_d = f"boom_pctl {boom_pctl:.0f}th; spike_pctl {spike_pctl:.0f}th -- multi-TD games in history"
            flags.append({"f": "TD ceiling / spike potential",
                "d": td_d,
                "amp": "soft TE tier / positive field position"})
            of_ids += ["rz_soft_te", "home_rz"]
        else:
            if adv2:
                td_d = (f"2yr {adv2_td_pg:.2f} TD/g over {adv2_g}g; "
                        f"boom_pctl {boom_pctl:.0f}th -- threshold requires large yardage day without TDs")
            else:
                td_d = f"boom_pctl {boom_pctl:.0f}th; ceiling_pctl {ceiling_pctl:.0f}th -- threshold requires large yardage day without TDs"
            flags.append({"f": "Below-avg TD ceiling -- volume-only path to boom",
                "d": td_d,
                "amp": "soft TE tier / pass-funnel (volume amplifier)"})
            of_ids += ["rz_soft_te"]

        # FLAG 3: Coverage-proof if present
        if cov_proof_pctl >= 65:
            sep_note = f", sep {sep_pctl:.0f}th" if sep_pctl >= 40 else ""
            flags.append({"f": "Coverage-proof / matchup-insensitive",
                "d": f"cov_proof {cov_proof_pctl:.0f}th pctl{sep_note}; rec_eff {rec_eff_pctl:.0f}th",
                "amp": "man-heavy (manp>=68, earns LB mismatch)"})
            of_ids += ["man_mismatch"]
        elif rec_eff_pctl >= 70:
            flags.append({"f": "Catch reliability / route efficiency",
                "d": f"rec_eff {rec_eff_pctl:.0f}th pctl; catch_rate {round(catch_rate*100,1)}%",
                "amp": "man-heavy / zone"})
            of_ids += ["man_mismatch"]

        # FLAG 4: YAC (only if genuinely positive) -- prefer chart2 yac_rec+mtf_rec
        if yac_pctl >= 65 and YACoe >= 0:
            if has_c2:
                yac_d = (f"2yr {c2_yac_rec:.1f} YAC/rec, {c2_mtf_rec:.2f} MTF/rec "
                         f"over {c2_g}g (FP charting); yac_pctl {yac_pctl:.0f}th")
            elif adv2:
                yac_d = (f"2yr {adv2_yptouch:.1f} yds/touch over {adv2_g}g; "
                         f"yac_pctl {yac_pctl:.0f}th")
            else:
                yacoe_str = f", YACoe +{round(YACoe,2)}" if YACoe > 0 else ""
                yac_d = f"yac_pctl {yac_pctl:.0f}th{yacoe_str}"
            flags.append({"f": "YAC / after-catch upside",
                "d": yac_d,
                "amp": "zone (manp<=32, YAC lanes open) / weak pass-rush"})
            of_ids += ["zone_yac"]

        # FLAG 5: Route efficiency
        if route_eff_pctl >= 70:
            flags.append({"f": "Route efficiency -- consistent separator",
                "d": f"route_eff {route_eff_pctl:.0f}th pctl -- crisp routes provide consistent open looks",
                "amp": "man-heavy / zone"})
            of_ids += ["man_sep"]

        # FLAG 6: SIS (if available)
        if YPRR >= 1.2:
            flags.append({"f": "SIS per-route value",
                "d": f"YPRR {YPRR} (SIS); airyard_pct {airpct:.1f}%; eff_combined {eff_comb:.0f}",
                "amp": "zone / weak rush"})
            of_ids += ["zone_seam"]

        # FLAG 7: O-line
        if oline_pctl >= 70:
            flags.append({"f": "Good O-line protection",
                "d": f"oline_pctl {oline_pctl:.0f}th",
                "amp": "vs heavy rush"})
            of_ids += ["weak_rush_oline"]

        # FLAG 8: Advanced / matchup
        if adv_pctl >= 75 or matchup_pctl >= 75:
            flags.append({"f": "High advanced / matchup value",
                "d": f"adv_pctl {adv_pctl:.0f}th; matchup_pctl {matchup_pctl:.0f}th -- advanced signals support ceiling",
                "amp": "soft TE tier"})
            of_ids += ["soft_te"]

    # --- LOW_VOL --------------------------------------------------------------
    else:  # LOW_VOL
        # FLAG 1: Low-volume TD lightning -- honest framing
        pct = round(tgt_share * 100, 1)
        if adv2:
            lv_d = (f"2yr {adv2_tgt_share}% tgt share over {adv2_g}g -- very rare ceiling; "
                    f"almost entirely dependent on multi-TD week")
        else:
            lv_d = f"tgt_share {pct}% -- very rare ceiling; almost entirely dependent on multi-TD week"
        flags.append({"f": "Low-volume TD lightning",
            "d": lv_d,
            "amp": "soft TE tier (essential) / positive field position / favorable script near GL"})
        of_ids += ["soft_te"]

        # FLAG 2: TD / boom profile -- cite 2yr td_pg if available
        if boom_pctl >= 60:
            if adv2:
                td_d = (f"2yr {adv2_td_pg:.2f} TD/g over {adv2_g}g; "
                        f"boom_pctl {boom_pctl:.0f}th -- has produced ceiling games historically")
            else:
                td_d = f"boom_pctl {boom_pctl:.0f}th; spike_pctl {spike_pctl:.0f}th -- has produced ceiling games historically"
            flags.append({"f": "TD history / spike potential",
                "d": td_d,
                "amp": "soft TE tier / home (crowd near GL)"})
            of_ids += ["rz_soft_te", "home_rz"]
        else:
            if adv2:
                td_d = (f"2yr {adv2_td_pg:.2f} TD/g over {adv2_g}g; "
                        f"boom_pctl {boom_pctl:.0f}th -- ceiling is very spiky and rare")
            else:
                td_d = f"boom_pctl {boom_pctl:.0f}th; ceiling_pctl {ceiling_pctl:.0f}th -- ceiling is very spiky and rare"
            flags.append({"f": "Modest TD ceiling",
                "d": td_d,
                "amp": "soft TE tier / home"})
            of_ids += ["rz_soft_te"]

        # FLAG 3: Route efficiency (if high -- e.g., a pass-catching specialist)
        if route_eff_pctl >= 70:
            flags.append({"f": "Route efficiency -- beats coverage when targeted",
                "d": f"route_eff {route_eff_pctl:.0f}th pctl; rec_eff {rec_eff_pctl:.0f}th -- wins looks he gets, limited by snap/target share",
                "amp": "man-heavy / zone seam"})
            of_ids += ["man_mismatch"]

        # FLAG 4: Coverage-proof if strong
        if cov_proof_pctl >= 70:
            flags.append({"f": "Coverage-proof mismatch exploit",
                "d": f"cov_proof {cov_proof_pctl:.0f}th pctl -- earns TD targets by winning vs LB/safety",
                "amp": "man-heavy (manp>=68)"})
            of_ids += ["man_mismatch"]

        # FLAG 5: YAC (only if positive) -- prefer chart2 yac_rec+mtf_rec
        if yac_pctl >= 65 and YACoe > 0:
            if has_c2:
                yac_d = (f"2yr {c2_yac_rec:.1f} YAC/rec, {c2_mtf_rec:.2f} MTF/rec "
                         f"over {c2_g}g (FP charting); "
                         f"yac_pctl {yac_pctl:.0f}th -- catches become big plays")
            elif adv2:
                yac_d = (f"2yr {adv2_yptouch:.1f} yds/touch over {adv2_g}g; "
                         f"yac_pctl {yac_pctl:.0f}th -- catches become big plays")
            else:
                yac_d = f"yac_pctl {yac_pctl:.0f}th; YACoe +{round(YACoe,2)} -- catches become big plays"
            flags.append({"f": "YAC upside -- rare but explosive",
                "d": yac_d,
                "amp": "zone / open grass"})
            of_ids += ["zone_yac"]

        # FLAG 6: O-line if premium
        if oline_pctl >= 75:
            flags.append({"f": "Premium O-line -- catch-route timing",
                "d": f"oline_pctl {oline_pctl:.0f}th",
                "amp": "vs heavy rush"})
            of_ids += ["weak_rush_oline"]

        # FLAG 7: Spike
        if spike_pctl >= 55:
            flags.append({"f": "High spike_pctl -- big-day outlier history",
                "d": f"spike_pctl {spike_pctl:.0f}th -- profile shows capacity for outsized games",
                "amp": "soft TE tier / home"})
            of_ids += ["home_rz"]

    # --- UNIVERSAL SUPPRESSORS (apply to all archetypes) ---------------------
    # These aren't skill_flags (they're week-level suppressors) but we note them
    # The per-week code handles the actual multiplier hits

    # --- RED-ZONE / TD EQUITY SKILL FLAG (universal -- applied before minimum check) ---
    # Central to TE ceiling: TDs are the primary lever for the 4.1x swing
    rz_data  = v.get('rz')   or {}
    team_env = v.get('team_env') or {}
    rz_ts    = rz_data.get('rz_tgt_share', 0)   or 0   # % of team targets inside-20
    ez_ts    = rz_data.get('ez_tgt_share',  0)   or 0   # % in end zone
    ez_td    = rz_data.get('ez_td',         0)   or 0   # 2yr end-zone TDs
    ez_td_pg = rz_data.get('ez_td_pg',      0.0) or 0.0
    rz_g     = rz_data.get('g',             0)   or 0
    own_env  = team_env.get('env_idx',      50)  or 50

    rz_qualifies = rz_data and (rz_ts >= 18 or ez_ts >= 8 or ez_td_pg >= 0.3)
    if rz_qualifies:
        rz_detail = (
            f"2yr {rz_ts}% inside-20 target share, {ez_ts}% end-zone share, "
            f"{ez_td} EZ TDs over {rz_g}g ({ez_td_pg:.2f} EZ TD/g)"
        )
        env_note = "; high-scoring offense (env_idx {})".format(own_env) if own_env >= 70 else ""
        flags.append({
            "f": "Red-zone / TD equity -- EZ target role",
            "d": rz_detail + env_note,
            "amp": (
                "soft TE tier (4.1x swing essential) + favored script near GL (win_total edge) + "
                "vs soft run-D (scoring drives) + home crowd near goal line"
            )
        })
        of_ids += ["rz_soft_te", "home_rz", "script_rz"]

    # ENV / SHOOTOUT note -- add to line if high-scoring offense
    # (env_idx >= 70: standing ceiling raiser; activated per-week in week_mults)

    # --- ENSURE 3-FLAG MINIMUM (never ship with <3) --------------------------
    # If we still don't have 3 flags, fill from available stats
    if len(flags) < 3 and ceiling_pctl >= 50:
        flags.append({"f": "Ceiling / value profile",
            "d": f"ceiling_pctl {ceiling_pctl:.0f}th; value_pctl {value_pctl:.0f}th -- stat composite supports ceiling case",
            "amp": "soft TE tier / home"})
        of_ids += ["soft_te"]
    if len(flags) < 3 and adv_pctl >= 40:
        flags.append({"f": "Advanced efficiency indicator",
            "d": f"adv_pctl {adv_pctl:.0f}th -- advanced metrics show value even in limited usage",
            "amp": "soft TE tier"})
        of_ids += ["soft_te"]
    if len(flags) < 3:
        # Fallback: matchup + schedule dependent
        flags.append({"f": "Schedule-dependent ceiling",
            "d": f"matchup_pctl {matchup_pctl:.0f}th -- ceiling primarily driven by favorable soft-TE-tier matchups",
            "amp": "soft TE tier (sole reliable activator)"})
        of_ids += ["soft_te"]

    # --- COVERAGE SPECIALIST skill flag (cspec) --------------------------------
    cspec = v.get('cspec')
    if cspec:
        best    = cspec.get('best', '')
        ratio   = cspec.get('ratio', 0)
        pctl    = cspec.get('pctl', 0)
        rts     = cspec.get('routes', 0)
        flags.append({
            "f": "Coverage specialist",
            "d": f"crushes {best} ({ratio}x league FP/RR, {pctl}th pctl over {rts} routes)",
            "amp": f"vs defenses that run {best} heavily"
        })
        of_ids += ["cspec_matchup"]

    # --- ELITE SEPARATOR skill flag (validated to add ceiling beyond base) ------
    sepd = v.get('sep')
    if sepd is not None and sepd.get('elite_man_sep'):
        flags.append({
            "f": "Elite separator",
            "d": f"creates separation vs man ({sepd.get('man_sep_pctl')}th pctl) — gets open on the toughest coverage",
            "amp": "vs press-man defenses (his separation travels)"
        })

    # --- SUPPRESS REDUNDANT DUPLICATES ----------------------------------------
    seen_f = set(); deduped = []
    for fl in flags:
        if fl['f'] not in seen_f:
            seen_f.add(fl['f']); deduped.append(fl)
    # keep validated flags (cspec, separator) regardless of list position, then cap
    _PRIO = ('Coverage specialist', 'Elite separator')
    _prio = [f for f in deduped if f['f'] in _PRIO]
    _rest = [f for f in deduped if f['f'] not in _PRIO]
    flags = (_prio + _rest)[:(8 if _prio else 7)]

    line = build_line(v['name'], arch, tgt_share, boom_pctl, cov_proof_pctl,
                      yac_pctl, YACoe, YPRR, airpct, ceiling_pctl, oline_pctl,
                      adv_pctl, spike_pctl, SPIKE)

    return flags, list(dict.fromkeys(of_ids)), line


def build_line(name, arch, tgt_share, boom_pctl, cov_proof, yac_pctl, YACoe,
               YPRR, airpct, ceiling_pctl, oline_pctl, adv_pctl, spike_pctl, SPIKE):
    """Unique plain-language sentence per player -- references their actual stats."""
    tgt_pct = round(tgt_share * 100, 1)
    if arch == 'VOLUME_TE1':
        cv = f"cov_proof {cov_proof:.0f}th pctl" if cov_proof >= 70 else f"boom_pctl {boom_pctl:.0f}th"
        yac = f" + yac {yac_pctl:.0f}th pctl" if yac_pctl >= 68 else ""
        return (f"{name}'s ceiling unlocks via elite target share ({tgt_pct}%) + {cv}{yac}; "
                f"activated by soft TE tier (4.1x swing) + pass-funnel games.")
    elif arch == 'SEAM':
        return (f"{name}'s ceiling is YPRR-driven seam threat ({YPRR} YPRR, {airpct}% air-yard share); "
                f"activated by zone coverage + weak pass-rush + dome.")
    elif arch == 'COV_PROOF':
        vol_str = f"tgt {tgt_pct}% + " if tgt_share >= 0.15 else ""
        return (f"{name}'s ceiling is {vol_str}coverage-proof mismatch (cov_proof {cov_proof:.0f}th pctl); "
                f"peaks in man-heavy weeks + soft TE tier.")
    elif arch == 'YAC_THREAT':
        yacoe_str = f"YACoe +{round(YACoe,2)}" if YACoe > 0 else f"yac_pctl {yac_pctl:.0f}th"
        return (f"{name}'s ceiling is after-catch explosiveness ({yacoe_str}); "
                f"activated by zone coverage + soft TE tier + weak pass-rush.")
    elif arch == 'MIDVOL_BOOM':
        return (f"{name}'s ceiling combines mid-tier volume ({tgt_pct}%) + high boom-game history "
                f"(boom_pctl {boom_pctl:.0f}th); soft TE tier + pass-funnel unlock both paths.")
    elif arch == 'TD_DEPENDENT':
        if YPRR >= 1.2:
            return (f"{name}'s ceiling is TD-dependent (boom_pctl {boom_pctl:.0f}th) + per-route efficiency "
                    f"(YPRR {YPRR}); activated by soft TE tier + zone coverage.")
        return (f"{name}'s ceiling is almost purely TD-dependent (boom_pctl {boom_pctl:.0f}th, tgt {tgt_pct}%); "
                f"requires soft TE tier + favorable script to reach {SPIKE} pts.")
    elif arch == 'MIDVOL':
        best_flag = (f"cov_proof {cov_proof:.0f}th pctl" if cov_proof >= 65
                     else f"boom_pctl {boom_pctl:.0f}th")
        return (f"{name}'s ceiling via functional volume ({tgt_pct}%) + {best_flag}; "
                f"soft TE tier is the key activator.")
    else:  # LOW_VOL
        return (f"{name}'s ceiling is very spiky and rare -- low volume ({tgt_pct}%), "
                f"boom_pctl {boom_pctl:.0f}th; needs soft TE tier + TDs to reach {SPIKE} pts.")


# ------------------------------------------------------------------------------
# Per-week activation logic  (verbatim body of legacy week_mults)
# ------------------------------------------------------------------------------
def week_mults(v, def_data, week_info, skill_flags, of_ids, base, opp=None):
    """Return (mults_list, lit_flags_list) for a single game week."""
    if def_data is None:
        return [1.0], []

    fus    = v.get('fus')  or {}
    usage  = v.get('usage') or {}
    adot_d = v.get('adot') or {}
    sis    = v.get('sis')  or {}
    yaco   = v.get('yaco') or {}

    tgt_share    = usage.get('tgt_share', 0)
    boom_pctl    = fus.get('boom_pctl',           50)
    cov_proof    = fus.get('coverage_proof_pctl', 50)
    yac_pctl     = fus.get('yac_pctl',            50)
    sep_pctl     = fus.get('separation_pctl',     50)
    rec_eff_pctl = fus.get('rec_eff_pctl',        50)
    explo_pctl   = fus.get('explosive_pctl',       0)
    oline_pctl   = fus.get('oline_pctl',          50)
    route_eff    = fus.get('route_eff_pctl',       50)
    adv_pctl     = fus.get('adv_pctl',             50)
    spike_pctl   = fus.get('spike_pctl',           50)
    aDOT         = adot_d.get('aDOT', 0)
    YACoe        = yaco.get('YACoe', 0)
    YPRR         = sis.get('YPRR', 0)
    airpct       = sis.get('airyard_pct', 0)

    covp   = def_data.get('covp',  50) or 50
    runp   = def_data.get('runp',  50) or 50
    manp   = def_data.get('manp',  50) or 50
    sackp  = def_data.get('sackp', 50) or 50
    te_tier = (def_data.get('tiers') or {}).get('TE', 'AVG') or 'AVG'

    home  = week_info.get('home', False)
    dome  = week_info.get('dome', False)

    mults = []
    lit   = []

    # -- 1. TE TIER -- biggest lever (4.1x swing) -----------------------------
    if te_tier == 'SOFT':
        mults.append(1.35)
        lit.append(f"soft TE tier (x1.35)")
    elif te_tier == 'TOUGH':
        mults.append(0.73)
        lit.append(f"tough TE tier (x0.73)")
    elif covp <= 28:
        # No formal tier but coverage is soft
        mults.append(1.15)
        lit.append(f"soft pass-D (covp {covp}th, x1.15)")
    elif covp >= 78:
        mults.append(0.82)
        lit.append(f"strong pass-D (covp {covp}th, x0.82)")

    # -- 2. PASS-FUNNEL (volume TEs benefit most) -----------------------------
    pass_funnel = (runp >= 60 and covp <= 45)
    if pass_funnel and tgt_share >= 0.15:
        mults.append(1.18)
        lit.append(f"pass-funnel (runp {runp}, covp {covp}, x1.18)")
    elif pass_funnel and tgt_share >= 0.10:
        mults.append(1.10)
        lit.append(f"pass-funnel (runp {runp}, covp {covp}, x1.10)")

    # -- 3. MAN-HEAVY -> TE mismatch vs LB/safety ----------------------------
    # Weight by how strong the mismatch potential is
    if manp >= 72 and (cov_proof >= 65 or sep_pctl >= 60):
        mults.append(1.18)
        lit.append(f"man-heavy (manp {manp}, TE on LB mismatch, x1.18)")
    elif manp >= 68 and cov_proof >= 50:
        mults.append(1.12)
        lit.append(f"man-heavy (manp {manp}, coverage-proof edge, x1.12)")
    elif manp >= 55 and cov_proof >= 80:
        # Coverage-proof even vs moderate man
        mults.append(1.08)
        lit.append(f"moderate man-coverage (manp {manp}, elite cov-proof {cov_proof}th, x1.08)")

    # -- 4. ZONE -> YAC / seam (only if player is genuinely a YAC or seam player)
    if manp <= 30:
        if yac_pctl >= 70 and YACoe >= 0:
            mults.append(1.12)
            lit.append(f"zone coverage (manp {manp}, YAC lanes open, yac {yac_pctl}th, x1.12)")
        elif YPRR >= 1.2 or (aDOT >= 9.0 and route_eff >= 60):
            mults.append(1.10)
            lit.append(f"zone coverage (manp {manp}, seam routes open, x1.10)")
        elif yac_pctl >= 60:
            mults.append(1.08)
            lit.append(f"zone coverage (manp {manp}, moderate YAC upside, x1.08)")
    elif manp <= 38 and yac_pctl >= 78 and YACoe > 0.5:
        # Slight zone lean even at moderate manp if YAC is truly elite
        mults.append(1.06)
        lit.append(f"zone lean (manp {manp}, elite YACoe +{round(YACoe,2)}, x1.06)")

    # -- 4b. DEFENSE COVERAGE SHELL (real single/two-high rates) ---------------
    # SHELL[opp] = {man, two_high, single_high, single_high_pctl, ...}
    sh = SHELL.get(opp) if opp else None

    # Classify this TE as seam/vertical: chart2 deep_pct or aDOT or explosive YPRR
    chart2_block = v.get('chart2')
    c2b_wk = (chart2_block.get('blend') if isinstance(chart2_block, dict) else None) or {}
    c2_deep_wk  = c2b_wk.get('deep_pct', 0)
    c2_aDOT_wk  = c2b_wk.get('aDOT', 0)
    is_seam_te  = (c2_deep_wk >= 14 or c2_aDOT_wk >= 9.0 or aDOT >= 9.0 or
                   YPRR >= 1.2 or explo_pctl >= 65)
    # Coverage-proof / man-mismatch TE: high coverage_proof or rec_eff
    is_covproof_te = (cov_proof >= 70 or (rec_eff_pctl >= 70 and cov_proof >= 50))
    # Volume TE: meaningful target share
    is_volume_te   = tgt_share >= 0.15

    if sh:
        sh_sh_pctl  = sh.get('single_high_pctl', 50)
        sh_two_high = sh.get('two_high', 0)
        sh_man      = sh.get('man', 0)
        sh_single   = sh.get('single_high', 0)

        # SEAM TE vs TWO-HIGH shell (single_high_pctl<=35 = MOFO, soft middle for TEs)
        if is_seam_te and sh_sh_pctl <= 35:
            mults.append(1.08)
            lit.append(
                f"two-high shell opens the seam/middle (opp {sh_two_high:.0f}% two-high, "
                f"single_high_pctl {sh_sh_pctl}, MOFO = soft middle for TEs, x1.08)"
            )
        # SEAM TE vs single-high heavy (MOFC = robber/bracket squeezes seam)
        elif is_seam_te and sh_sh_pctl >= 65:
            mults.append(0.97)
            lit.append(
                f"single-high shell compresses seam/middle (opp {sh_single:.0f}% single-high, "
                f"single_high_pctl {sh_sh_pctl}, MOFC = robber/bracket on TE, x0.97)"
            )

        # COVERAGE-PROOF TE vs high man% (TE-on-LB/safety mismatch in man)
        if is_covproof_te and sh_man >= 32:
            mults.append(1.10)
            lit.append(
                f"TE-on-LB/safety mismatch vs man (opp {sh_man:.0f}% man, "
                f"cov_proof {cov_proof:.0f}th pctl, x1.10)"
            )

        # VOLUME TE vs two-high (underneath space opens when safety is deep)
        if is_volume_te and sh_sh_pctl <= 35 and not is_seam_te:
            mults.append(1.04)
            lit.append(
                f"two-high shell opens underneath volume (opp {sh_two_high:.0f}% two-high, "
                f"tgt_share {round(tgt_share*100,1)}%, x1.04)"
            )

    # -- 5. WEAK PASS-RUSH -> seam/YPRR/depth routes open --------------------
    if sackp <= 28:
        if YPRR >= 1.2 or aDOT >= 9.0 or explo_pctl >= 65:
            mults.append(1.15)
            lit.append(f"weak pass-rush (sackp {sackp}, seam/depth routes develop, x1.15)")
        elif yac_pctl >= 68 and YACoe >= 0:
            mults.append(1.10)
            lit.append(f"weak pass-rush (sackp {sackp}, timing intact for YAC, x1.10)")
        elif oline_pctl >= 70:
            mults.append(1.08)
            lit.append(f"weak pass-rush + strong OL (sackp {sackp}, oline {oline_pctl}th, x1.08)")
    elif sackp <= 38 and YPRR >= 1.3:
        mults.append(1.08)
        lit.append(f"moderate rush vs YPRR player (sackp {sackp}, x1.08)")

    # -- 6. HEAVY PASS-RUSH + WEAK O-LINE -> suppressor -----------------------
    if sackp >= 75 and oline_pctl <= 35:
        mults.append(0.85)
        lit.append(f"heavy rush vs weak O-line (sackp {sackp}, oline {oline_pctl}th, x0.85)")
    elif sackp >= 68 and oline_pctl <= 28:
        mults.append(0.88)
        lit.append(f"heavy rush + poor pass pro (sackp {sackp}, oline {oline_pctl}th, x0.88)")

    # -- 7. DOME + YPRR/DEEP (only if player actually has depth/explosive profile)
    if dome and (YPRR >= 1.2 or aDOT >= 11 or explo_pctl >= 70):
        mults.append(1.08)
        lit.append(f"dome + depth/explosive profile (x1.08)")
    elif dome and yac_pctl >= 80 and YACoe > 0:
        # YAC players also benefit in dome (better field conditions)
        mults.append(1.05)
        lit.append(f"dome + elite YAC profile (x1.05)")

    # -- 8. HOME FIELD + high-boom history ------------------------------------
    if home and boom_pctl >= 65:
        mults.append(1.06)
        lit.append(f"home (boom_pctl {boom_pctl:.0f}th, x1.06)")
    elif home and boom_pctl >= 45 and tgt_share >= 0.18:
        mults.append(1.04)
        lit.append(f"home + volume TE (boom {boom_pctl:.0f}th, tgt {round(tgt_share*100,1)}%, x1.04)")

    # -- 9. SOFT RUN-D + high TD profile -> scoring-drive amplifier -----------
    if runp <= 28 and boom_pctl >= 68:
        mults.append(1.10)
        lit.append(f"soft run-D (runp {runp}) + TD profile (boom_pctl {boom_pctl:.0f}th, x1.10)")
    elif runp <= 35 and boom_pctl >= 80:
        mults.append(1.08)
        lit.append(f"soft run-D (runp {runp}) + elite TD history (boom_pctl {boom_pctl:.0f}th, x1.08)")

    # -- 10. HIGH SPIKE_PCTL + soft TE tier -> big-day ceiling ----------------
    if spike_pctl >= 80 and te_tier == 'SOFT':
        mults.append(1.07)
        lit.append(f"high spike_pctl ({spike_pctl:.0f}th) vs soft tier -> big-day alignment (x1.07)")

    # -- 11. ENV / SHOOTOUT -- own env_idx + opp soft pass-D -------------------
    team_env = v.get('team_env') or {}
    own_env_idx   = team_env.get('env_idx',   50) or 50
    own_pace_pctl = team_env.get('pace_pctl', 50) or 50
    own_win_total = team_env.get('win_total', 8.0) or 8.0

    if own_env_idx >= 65 and covp <= 35:
        mults.append(1.08)
        lit.append(f"shootout setup (env_idx {own_env_idx}, opp covp {covp}<=35, x1.08)")
    elif own_env_idx >= 70:
        # High-scoring offense: standing note (already cited in skill_flag), small per-week lift
        pass  # env_idx >=70 gets noted in the skill flag; per-week lift only when paired with soft pass-D

    # -- 12. PACE (per week) -- fast game = more plays -------------------------
    opp_env = TENV.get(opp, {}) if opp else {}
    opp_pace_pctl = opp_env.get('pace_pctl', 50) or 50
    opp_win_total = opp_env.get('win_total', 8.0) or 8.0

    if own_pace_pctl >= 65 and opp_pace_pctl >= 50:
        mults.append(1.08)
        lit.append(
            f"fast game (own pace {own_pace_pctl}, opp pace {opp_pace_pctl}, x1.08)"
        )
    elif own_pace_pctl <= 35 and opp_pace_pctl <= 35:
        mults.append(0.95)
        lit.append(
            f"slow game (own pace {own_pace_pctl}, opp pace {opp_pace_pctl}, x0.95)"
        )

    # -- 13. SCRIPT (per week) -- win-total delta ------------------------------
    rz_data     = v.get('rz') or {}
    rz_ts       = rz_data.get('rz_tgt_share', 0) or 0
    ez_ts_val   = rz_data.get('ez_tgt_share', 0) or 0
    ez_td_pg_v  = rz_data.get('ez_td_pg', 0.0) or 0.0
    has_rz_equity = (rz_ts >= 18 or ez_ts_val >= 8 or ez_td_pg_v >= 0.3)

    d_wt = own_win_total - opp_win_total
    if d_wt <= -2.5:
        # Underdog: target volume rises when team trails; amplify
        mults.append(1.08)
        lit.append(
            f"underdog script (own WT {own_win_total} vs opp {opp_win_total}, d={d_wt:+.1f}, "
            f"trailing -> more targets, x1.08)"
        )
    elif d_wt >= 2.5 and has_rz_equity:
        # Favored: TEs with red-zone role benefit near goal line in positive script
        mults.append(1.05)
        lit.append(
            f"favored script + RZ equity (own WT {own_win_total} vs opp {opp_win_total}, "
            f"d={d_wt:+.1f}, GL looks, x1.05)"
        )

    # -- 14. COVERAGE SPECIALIST per-week activation ---------------------------
    cspec = v.get('cspec')
    if cspec and sh:
        cspec_keys = cspec.get('best_keys') or [cspec.get('best_key')]
        cspec_pctl = cspec.get('pctl', 0) or 0
        _NM = {'man': 'Man', 'c2': 'Cover-2', 'c3': 'Cover-3', 'c4': 'Cover-4', 'c6': 'Cover-6', 'single_high': 'Single-High', 'two_high': 'Two-High', 'zone': 'Zone'}
        fired = None  # fire vs whichever of his strong coverages the opponent over-runs most
        for ck in cspec_keys:
            lg_val = (SHELL.get('_LEAGUE') or {}).get(ck); opp_val = sh.get(ck)
            if ck and opp_val is not None and lg_val is not None and opp_val >= lg_val + 3:
                if fired is None or (opp_val - lg_val) > fired[1]:
                    fired = (ck, opp_val - lg_val, opp_val, lg_val)
        if fired:
            ck, _, opp_val, lg_val = fired
            mult = 1.13 if cspec_pctl >= 95 else 1.10
            mults.append(mult)
            lit.append(
                f"faces {_NM.get(ck, ck)}-heavy D (opp {opp_val:.1f}% vs lg {lg_val:.1f}%) "
                f"— his best scheme (x{mult})"
            )

    return mults, lit


# ==============================================================================
# flagkit.engine model contract
# ==============================================================================
def context(k, v, gl, bd):
    """Position-specific feature extraction. Computes the skill flags / of_ids / line
    ONCE here (the legacy build_skill_flags returns all three together), and stashes the
    raw player record + SPIKE for base()/activate() to reuse."""
    SPIKE = bd['SPIKE'][POS]
    flags, of_ids, line = build_skill_flags(k, v, SPIKE)
    return {
        'k': k, 'v': v, 'SPIKE': SPIKE,
        'flags': flags, 'of_ids': of_ids, 'line': line,
        'of_total': len(of_ids),
    }


def base(v, posbase, prof):
    """Regularized base ceiling rate with the TE ceiling_pctl seed fallback."""
    b = reg_base(v, posbase)
    hist = True
    if b is None:
        fus = v.get('fus') or {}
        ceiling_pctl = fus.get('ceiling_pctl', 50)
        b = cap(posbase['TE'] * (0.75 + 0.5 * ceiling_pctl / 100), 0.06, 0.45)
        b = round(b, 3)
        hist = False
    return b, hist


def skill_flags(prof):
    return prof['flags']


def line(prof):
    return prof['line']


def opp_data(opp):
    """Per-week opponent inputs. week_mults reads def_data (defense2026.json) plus the
    SHELL/TENV globals keyed by `opp`, so bundle def_data + the opp code through here."""
    return {'opp': opp, 'def_data': DE.get(opp)}


def activate(prof, base, skill_flags, opp_data, week_ctx):
    """FUNCTIONAL activation -- delegates to the verbatim legacy week_mults body and maps
    its (mults, lit) return to the engine's (lit_flags, lit_mults, of_total) tuple."""
    v = prof['v']
    opp = opp_data['opp']
    def_data = opp_data['def_data']
    week_info = {'home': week_ctx.get('home', False), 'dome': week_ctx.get('dome', False)}
    mults, lit = week_mults(v, def_data, week_info, skill_flags, prof['of_ids'], base, opp=opp)
    return lit, mults, prof['of_total']


# -- engine optional hooks (see flagkit/engine.py) --------------------------------
def bye_of(prof):
    # TE carries the player's of_total on BYE weeks (DST/QB use 0).
    return prof['of_total']


def empty_schedule(prof):
    # Free-agent TEs (empty schedule) get 18 BYE sentinel weeks, of = bye_of.
    return 'BYE'
