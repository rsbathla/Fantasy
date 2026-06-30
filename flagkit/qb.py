#!/usr/bin/env python3
"""flagkit/qb.py — QB position semantics (ports build_flags_QB.py onto flagkit.engine).

ONLY the QB-specific logic lives here: the base seed, the skill-flag cascade, the per-week
condition list (with the coverage-specialist per-week label rewrite), the one-line thesis,
and the empirical summary. Every piece of shared scaffolding (player loop, BYE, grading,
record/week assembly, write) is in flagkit/engine.py and is NOT duplicated.

The logic below is transcribed verbatim from build_flags_QB.py so the output is
byte-for-byte identical (verified by diffing boom/flags_QB.json).

QB uses the FUNCTIONAL `activate` style (not static `conditions`) because its
coverage-specialist per-week flag rewrites its lit-flag label using the real opponent
coverage percentages — week-specific text that a static condition key cannot express.
The activation copies the legacy week-loop body verbatim.
"""
import json
import os
from boom_lib import reg_base, prob, label, cap

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repo root (flagkit/ is one level down)
POS = 'QB'

# Team environment lookup (own=statmenu[k]['team_env'], opp=TENV[opp] per week)
TENV = json.load(open(os.path.join(HERE, 'boom', 'team_env.json')))

# Defense coverage shell (real single/two-high rates; keyed by team abbrev)
# SHELL['_LEAGUE'] = league-mean usage per coverage {man,c2,c3,c4,c6}
SHELL = json.load(open(os.path.join(HERE, 'boom', 'defense_shell.json')))

# Defense matchup inputs the per-week condition fns read (legacy passed de.get(opp, {}))
DE = json.load(open(os.path.join(HERE, 'boom', 'defense2026.json')))

# === Branch-2 anti-overfit prune (evidence: AUDIT_OVERFIT_2026.md) ==========
# 2024->2025 stability: QB aDOT/deep_pct -> boom SIGN-FLIPS (noise) => DROP;
# pass-volume (patt) corr +0.05/+0.25 (weak) => SHRINK; coverage-specialist
# split r~0.2 => DEMOTE. KEEP (untouched): rushing (rush corr +0.32/+0.27),
# SIS efficiency, spike, O-line/pressure, tier/funnel/env/pace/script.
# Restore the pre-prune model by setting all three factors to 1.0.
DEEP_SHRINK    = 0.0    # aDOT-driven deep/explosive passing ceiling: DROP
PASSVOL_SHRINK = 0.35   # pass-volume / usage-value multipliers: SHRINK
COV_SHRINK     = 0.5    # coverage-specialist: DEMOTE (halve)
def _shr(mult, lam):
    """Shrink a multiplier toward 1.0 by factor lam (0=neutralize, 1=unchanged)."""
    return 1.0 + (mult - 1.0) * lam


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fget(v, key, default=0.0):
    val = v.get('fus', {}).get(key)
    return val if val is not None else default

def uget(v, key, default=0.0):
    val = v.get('usage', {}).get(key)
    return val if val is not None else default


# -- per-week opponent inputs the conditions read --------------------------------
def opp_data(opp):
    return DE.get(opp, {})


# -- empirical summary string ----------------------------------------------------
def empirical(k, gl, bd):
    SPIKE = bd['SPIKE']['QB']
    games = gl.get(k, [])
    if not games:
        return "No 2025 gamelog data."
    n     = len(games)
    booms = [g for g in games if g.get('boom') == 1]
    nb    = len(booms)
    if nb == 0:
        return (f"0 ceiling games (>={SPIKE} DK pts) in {n} active weeks tracked; "
                "small sample or injury-interrupted season.")
    home_b = sum(1 for g in booms if g.get('home'))
    dome_b = sum(1 for g in booms if g.get('dome'))
    sp_b   = sum(1 for g in booms if (g.get('opp_passp') or 99) <= 35)
    sr_b   = sum(1 for g in booms if (g.get('opp_runp')  or 99) <= 35)
    tp_b   = sum(1 for g in booms if (g.get('opp_passp') or 0)  >= 65)
    parts  = [f"{nb}/{n} ceiling games (>={SPIKE} DK pts)"]
    notes  = []
    if home_b >= max(1, nb // 2): notes.append(f"{home_b} at home")
    if dome_b >= max(1, nb // 2): notes.append(f"{dome_b} in a dome")
    if sp_b   >= max(1, nb // 2): notes.append(f"{sp_b} vs soft pass-D (opp_passp<=35)")
    if sr_b   >= max(1, nb // 2): notes.append(f"{sr_b} vs soft run-D (opp_runp<=35)")
    if tp_b == nb and nb >= 1:
        notes.append(f"{tp_b} even vs tough pass-D (>=65) -- scheme-independent ceiling")
    if not notes:
        notes.append("no single condition dominates")
    parts.append("; ".join(notes))
    return ". ".join(parts) + "."


# ---------------------------------------------------------------------------
# One-line thesis
# ---------------------------------------------------------------------------

def _build_line(name, carry_pg, ypc, value_p, ceiling_p, spike_p, boom_p,
                oline_p, protection_p, matchup_p, adv_p, sis_p, dk_pg,
                rush_pg_eff=None, rushyd_pg=None, rushtd_g=None, adv2_g=0,
                has_adv2=False):
    if rush_pg_eff is None:
        rush_pg_eff = carry_pg
    parts = []

    if rush_pg_eff >= 7.0:
        if has_adv2:
            parts.append(
                f"elite rushing (2yr {rush_pg_eff:.1f} rush/g, {rushyd_pg:.1f} yd/g, "
                f"{rushtd_g:.2f} TD/g over {adv2_g}g) is the "
                f"#1 ceiling driver -- designed runs + scrambles add 8-14 pts on soft box/man"
            )
        else:
            parts.append(
                f"elite rushing role ({carry_pg:.1f} carry/g, {ypc:.2f} ypc) is the "
                f"#1 ceiling driver -- designed runs + scrambles add 8-14 pts on soft box/man"
            )
    elif rush_pg_eff >= 5.0:
        if has_adv2:
            parts.append(
                f"strong dual-threat rushing (2yr {rush_pg_eff:.1f} rush/g, "
                f"{rushyd_pg:.1f} yd/g over {adv2_g}g) raises floor AND ceiling every week"
            )
        else:
            parts.append(
                f"strong dual-threat rushing ({carry_pg:.1f} carry/g, {ypc:.2f} ypc) "
                f"raises floor AND ceiling every week"
            )
    elif rush_pg_eff >= 3.5:
        if has_adv2:
            parts.append(
                f"pocket mobility (2yr {rush_pg_eff:.1f} rush/g over {adv2_g}g) "
                f"adds scramble ceiling in pressure-heavy matchups"
            )
        else:
            parts.append(
                f"pocket mobility ({carry_pg:.1f} carry/g) adds scramble ceiling in "
                f"pressure-heavy matchups"
            )

    if ceiling_p >= 80:
        parts.append(
            f"elite passing ceiling (pctl {ceiling_p:.0f}) erupts vs soft coverage / clean pocket"
        )
    elif ceiling_p >= 60:
        parts.append(
            f"above-average passing ceiling (pctl {ceiling_p:.0f}) spikes on soft QB tiers"
        )

    if spike_p >= 85:
        parts.append(
            f"elite outlier-game frequency (spike_pctl {spike_p:.0f}) -- "
            f"dome + home flip ceiling games on"
        )

    if value_p >= 90:
        parts.append(
            f"elite pass volume (value_pctl {value_p:.0f}) -- "
            f"pass-funnels turbocharge DK output"
        )
    elif value_p >= 80:
        parts.append(
            f"strong volume profile (value_pctl {value_p:.0f}) amplified by pass-funnel matchups"
        )

    if oline_p >= 80:
        parts.append(f"elite O-line (pctl {oline_p:.0f}) neutralizes top pass rushers")
    elif oline_p <= 20 and carry_pg < 5.0:
        if protection_p >= 65:
            parts.append(
                f"fragile line (oline {oline_p:.0f}) offset by elite self-protection "
                f"(protection_pctl {protection_p:.0f})"
            )
        else:
            parts.append(
                f"fragile pocket (oline {oline_p:.0f}) -- heavy rush is the ceiling killer"
            )

    if boom_p >= 85 and ceiling_p < 60:
        parts.append(
            f"TD-clustering boom type (boom_pctl {boom_p:.0f}) -- scores come in bunches"
        )

    if sis_p >= 88:
        parts.append(
            f"SIS elite efficiency (pctl {sis_p:.0f}) lifts ceiling in zone / "
            f"soft-coverage weeks"
        )

    if not parts:
        parts.append(
            f"limited sample; model seeded from fusion pctls "
            f"(value {value_p:.0f}, ceiling {ceiling_p:.0f}, boom {boom_p:.0f})"
        )

    return f"{name}: " + "; ".join(parts[:4]) + "."


# ---------------------------------------------------------------------------
# Per-player feature extraction + skill flags + conditions
#   All the legacy build_player() body lives here so it stays a faithful
#   transcription; the engine-facing functions below just read the profile.
# ---------------------------------------------------------------------------

def context(k, v, gl, bd):
    posbase = bd['posbase']

    name        = v['name']
    team        = v.get('team', '')
    adp         = v.get('adp')
    n_games     = v.get('n_games', 0)
    boom_games  = v.get('boom_games', 0)

    # Pull every available stat
    value_p      = fget(v, 'value_pctl')        # overall usage/value composite
    ceiling_p    = fget(v, 'ceiling_pctl')       # passing ceiling / explosive
    spike_p      = fget(v, 'spike_pctl')         # outlier-game frequency
    boom_p       = fget(v, 'boom_pctl')          # boom-game composite
    protection_p = fget(v, 'protection_pctl')    # QB's OWN ball-protection quality
    oline_p      = fget(v, 'oline_pctl')         # O-line unit quality
    matchup_p    = fget(v, 'matchup_pctl')       # matchup exploitation history
    adv_p        = fget(v, 'adv_pctl')           # advanced composite
    sis_p        = fget(v, 'sis_value_pctl')     # SIS efficiency score

    carry_pg     = uget(v, 'carry_pg')
    ypc          = uget(v, 'ypc')
    dk_pg        = uget(v, 'dk_pg')

    # -- Team environment (own; TENV[opp] looked up per week) ----------------
    tenv_own  = v.get('team_env') or {}
    own_env   = tenv_own.get('env_idx',   50)
    own_pace  = tenv_own.get('pace_pctl', 50)
    own_wt    = tenv_own.get('win_total', 8.0)
    has_tenv  = bool(tenv_own)

    # -- 2-season advanced profile (2024+2025 startable games) ---------------
    adv2 = v.get('adv2')   # None for rookies / no history; dict for ~48/53 QBs
    # Determine effective rushing threshold: prefer 2-yr rush_pg if adv2 exists
    rush_pg_eff  = adv2['rush_pg']  if adv2 else carry_pg
    rushyd_pg    = adv2['rushyd_pg'] if adv2 else (carry_pg * ypc if ypc else 0.0)
    rushtd_g     = adv2['rushtd_g']  if adv2 else 0.0
    adv2_g       = adv2['g']         if adv2 else 0
    # 2-yr passing stats (for citation in passing flags)
    adv2_ypa     = adv2['ypa']       if adv2 else None
    adv2_ptd_pg  = adv2['ptd_pg']    if adv2 else None
    adv2_patt_pg = adv2['patt_pg']   if adv2 else None

    # -- 2024 FantasyPoints charting (chart2.blend; QB = 2024-only) ----------
    _c2raw = v.get('chart2')
    chart2 = _c2raw.get('blend') if (_c2raw and _c2raw.get('blend')) else None
    # chart2 is None for rookies / QBs without 2024 data (12 QBs)
    c2_g        = chart2['g']          if chart2 else None
    c2_adot     = chart2['aDOT']       if chart2 else None
    c2_deep     = chart2['deep_pct']   if chart2 else None   # % deep throws
    c2_cpoe     = chart2['cpoe']       if chart2 else None   # completion % over expected
    c2_press    = chart2['press_pct']  if chart2 else None   # % dropbacks under pressure
    c2_ttt      = chart2['ttt']        if chart2 else None   # time-to-throw (sec)
    c2_scrm     = chart2['scrm']       if chart2 else None   # scrambles (2024)
    c2_oneread  = chart2['oneread_pct'] if chart2 else None
    c2_acc      = chart2['acc_pct']    if chart2 else None

    # -- Coverage specialist (cspec) -- present for ~22 QBs; None otherwise --
    cspec = v.get('cspec')   # {best, best_key, z, val, lg, ratio, profile}

    # -- Regularized base ------------------------------------------------
    rb = reg_base(v, posbase)
    if rb is not None:
        base = rb
        hist = True
    else:
        # No sufficient history: seed from ceiling_pctl
        cp   = ceiling_p if ceiling_p != 50.0 else 50.0
        base = posbase['QB'] * (0.75 + 0.5 * cp / 100.0)
        base = round(cap(base, 0.06, 0.45), 3)
        hist = False

    skill_flags = []
    conditions  = []   # {"key", "mult", "fn"}

    # ====================================================================
    # A  RUSHING ROLE -- the dominant QB ceiling driver
    #    Multipliers calibrated so rushing flag alone lifts a typical QB
    #    ~20-28% above base on soft-run week (targeting SWING soft=0.19).
    #    When adv2 exists, use 2-yr rush_pg for threshold + cite 2-yr stats.
    #    When adv2 is None (rookies), fall back to single-season carry_pg.
    # ====================================================================
    # Build scramble citation suffix (chart2 scrm adds specificity to rush flags)
    # High scrm: >=40 (Lamar 46, Allen 43, Daniels 72, Caleb 50, Drake 45)
    _scrm_suffix = ""
    if c2_scrm is not None and c2_scrm >= 30:
        _scrm_suffix = f"; 2024 charting: {c2_scrm:.0f} scrambles (FP)"

    if rush_pg_eff >= 7.0:
        if adv2:
            _rush_d = (f"2yr {rush_pg_eff:.1f} rush/g, {rushyd_pg:.1f} rush yd/g, "
                       f"{rushtd_g:.2f} rush TD/g over {adv2_g}g (2024+2025) -- "
                       f"rushes add 8-14 pts ceiling; designed runs + scrambles dominate boom games"
                       f"{_scrm_suffix}")
            _rush_key = f"rushing upside elite (2yr rush_pg {rush_pg_eff:.1f})"
        else:
            _rush_d = (f"carry_pg {carry_pg:.1f} (top-2 QB rusher), ypc {ypc:.2f} -- "
                       "rushes add 8-14 pts ceiling; designed runs + scrambles dominate boom games")
            _rush_key = f"rushing upside elite (carry_pg {carry_pg:.1f})"
        skill_flags.append({
            "f": "Elite designed-run / rushing ceiling",
            "d": _rush_d,
            "amp": ("soft run-box (runp<=45), man coverage (scramble lanes open), "
                    "red-zone carry opportunities, negative game script")
        })
        conditions.append({
            "key": _rush_key,
            "mult": 1.28,
            "fn": lambda d, w: d.get('runp', 50) <= 45 or d.get('manp', 50) >= 65
        })
    elif rush_pg_eff >= 5.0:
        if adv2:
            _rush_d = (f"2yr {rush_pg_eff:.1f} rush/g, {rushyd_pg:.1f} rush yd/g, "
                       f"{rushtd_g:.2f} rush TD/g over {adv2_g}g (2024+2025) -- "
                       f"dual-threat floor raises boom threshold meaningfully every week"
                       f"{_scrm_suffix}")
            _rush_key = f"rushing upside strong (2yr rush_pg {rush_pg_eff:.1f})"
        else:
            _rush_d = (f"carry_pg {carry_pg:.1f} (top-5 QB rusher), ypc {ypc:.2f} -- "
                       "dual-threat floor raises boom threshold meaningfully every week")
            _rush_key = f"rushing upside strong (carry_pg {carry_pg:.1f})"
        skill_flags.append({
            "f": "Strong dual-threat rushing floor+ceiling",
            "d": _rush_d,
            "amp": ("soft run-D (runp<=45), man coverage (scramble lanes), "
                    "open-field matchups, negative script")
        })
        conditions.append({
            "key": _rush_key,
            "mult": 1.20,
            "fn": lambda d, w: d.get('runp', 50) <= 45 or d.get('manp', 50) >= 65
        })
    elif rush_pg_eff >= 3.5:
        if adv2:
            _rush_d = (f"2yr {rush_pg_eff:.1f} rush/g, {rushyd_pg:.1f} rush yd/g over {adv2_g}g "
                       f"(2024+2025) -- scrambles and designed keepers add ceiling in pressure matchups"
                       f"{_scrm_suffix}")
            _rush_key = f"rushing / scramble element (2yr rush_pg {rush_pg_eff:.1f})"
        else:
            _rush_d = (f"carry_pg {carry_pg:.1f}, ypc {ypc:.2f} -- "
                       "scrambles and designed keepers add ceiling in pressure matchups")
            _rush_key = f"rushing / scramble element (carry_pg {carry_pg:.1f})"
        skill_flags.append({
            "f": "Moderate dual-threat / pocket mobility",
            "d": _rush_d,
            "amp": ("heavy pressure (sackp>=65 forces improvisation), "
                    "open-field matchups (runp<=40)")
        })
        conditions.append({
            "key": _rush_key,
            "mult": 1.10,
            "fn": lambda d, w: d.get('sackp', 50) >= 65 or d.get('runp', 50) <= 40
        })

    # ====================================================================
    # B  DEEP / EXPLOSIVE PASSING CEILING
    #    When chart2 exists: use 2024 aDOT + deep_pct + cpoe for the flag
    #    description and thresholds. Thresholds based on QB distribution:
    #      aDOT>=9.0 = top ~30%, >=10.0 = elite; deep_pct>=13% = top ~30%;
    #      cpoe>=4.0 = accurate, cpoe<0 = inaccurate downfield.
    #    When chart2 is None: fall back to single-season ceiling_pctl / boom_pctl.
    # ====================================================================
    # Determine if this QB qualifies as a deep/downfield threat via chart2
    _c2_deep_threat = (
        chart2 is not None
        and c2_adot is not None
        and (c2_adot >= 8.5 or (c2_deep is not None and c2_deep >= 12.0))
    )
    _c2_acc_good = chart2 is not None and c2_cpoe is not None and c2_cpoe >= 1.5
    _c2_acc_bad  = chart2 is not None and c2_cpoe is not None and c2_cpoe < -1.0

    if _c2_deep_threat and chart2 is not None:
        # Build citation string
        _cpoe_str = f"CPOE {c2_cpoe:+.1f}" if c2_cpoe is not None else ""
        _deep_cite = (
            f"2024 aDOT {c2_adot:.1f}, {c2_deep:.1f}% deep throws, {_cpoe_str} (FP charting)"
        )
        # Multiplier: aDOT>=9.5 + good accuracy = elite; aDOT>=8.5 = solid; bad accuracy caps it
        if c2_adot >= 9.5 and _c2_acc_good:
            _em = 1.25
            _deep_label = "Elite downfield passing / deep-ball accuracy"
            _deep_d = (f"{_deep_cite}, ceiling_pctl {ceiling_p:.0f} -- "
                       "elite aDOT + accurate deep shots generate top-tier explosive ceiling")
        elif c2_adot >= 9.5 or (c2_deep is not None and c2_deep >= 14.0):
            _em = 1.20
            _deep_label = "Elite downfield passing volume (high deep-throw rate)"
            _deep_d = (f"{_deep_cite}, ceiling_pctl {ceiling_p:.0f} -- "
                       "top-tier downfield intent; ceiling erupts vs soft coverage / clean pocket")
            if _c2_acc_bad:
                _deep_d += f"; accuracy concern (CPOE {c2_cpoe:+.1f}) caps ceiling vs tight coverage"
        elif c2_adot >= 8.5 and _c2_acc_good:
            _em = 1.18
            _deep_label = "Downfield passing + above-average accuracy"
            _deep_d = (f"{_deep_cite}, ceiling_pctl {ceiling_p:.0f} -- "
                       "solid aDOT with positive CPOE; finds boom vs clean pocket + soft tier")
        else:
            _em = 1.15
            _deep_label = "Above-average downfield passing"
            _deep_d = (f"{_deep_cite}, ceiling_pctl {ceiling_p:.0f} -- "
                       "above-average aDOT; ceiling fires on soft coverage / dome")
        skill_flags.append({
            "f": _deep_label,
            "d": _deep_d,
            "amp": ("clean pocket (sackp<=35), soft QB tier, dome, "
                    "soft covp (deep shots complete), weak deep-D (covp<=30)")
        })
        conditions.append({
            "key": f"deep/explosive passing (2024 aDOT {c2_adot:.1f}, deep {c2_deep:.1f}%)",
            "mult": _shr(_em, DEEP_SHRINK),   # [PRUNE: DEEP_SHRINK — aDOT sign-flip]
            "fn": lambda d, w, m=_em: (
                d.get('sackp', 50) <= 35 or d.get('covp', 50) <= 30
                or d.get('tiers', {}).get('QB') == 'SOFT'
            )
        })
    else:
        # Fallback: no chart2 or short aDOT -- use single-season fusion pctls
        if ceiling_p >= 80:
            _em = 1.25 if ceiling_p >= 88 else 1.18
            skill_flags.append({
                "f": "Elite explosive passing ceiling",
                "d": (f"ceiling_pctl {ceiling_p:.0f}, boom_pctl {boom_p:.0f} -- "
                      "generates multi-score ceiling games; top-tier big-play passing profile"),
                "amp": ("clean pocket (sackp<=35), soft QB tier, dome, "
                        "soft covp (deep shots complete)")
            })
            conditions.append({
                "key": f"explosive passing ceiling (ceiling_pctl {ceiling_p:.0f})",
                "mult": _em,
                "fn": lambda d, w, m=_em: (
                    d.get('sackp', 50) <= 35 or d.get('covp', 50) <= 30
                    or d.get('tiers', {}).get('QB') == 'SOFT'
                )
            })
        elif ceiling_p >= 60:
            skill_flags.append({
                "f": "Above-average passing ceiling",
                "d": (f"ceiling_pctl {ceiling_p:.0f}, boom_pctl {boom_p:.0f} -- "
                      "solid ceiling that erupts on soft tiers or clean pockets"),
                "amp": "clean pocket (sackp<=40), soft QB tier, pass-funnel matchup"
            })
            conditions.append({
                "key": f"passing ceiling (ceiling_pctl {ceiling_p:.0f})",
                "mult": 1.15,
                "fn": lambda d, w: (
                    d.get('sackp', 50) <= 40
                    or d.get('tiers', {}).get('QB') == 'SOFT'
                )
            })
        elif ceiling_p >= 40 and boom_p >= 70:
            # Mid ceiling_pctl redeemed by boom_pctl
            skill_flags.append({
                "f": "Boom-frequency ceiling (boom_pctl overrides ceiling_pctl)",
                "d": (f"boom_pctl {boom_p:.0f} despite ceiling_pctl {ceiling_p:.0f} -- "
                      "TD-clustering / script-driven boom type; delivers when matchup fits"),
                "amp": "soft QB tier, positive script, pass-funnel matchup"
            })
            conditions.append({
                "key": f"boom-frequency ceiling (boom_pctl {boom_p:.0f})",
                "mult": 1.12,
                "fn": lambda d, w: d.get('tiers', {}).get('QB') == 'SOFT'
            })

    # ====================================================================
    # C  SPIKE / OUTLIER-GAME FREQUENCY
    # ====================================================================
    if spike_p >= 85:
        _sm = 1.14 if spike_p >= 92 else 1.10
        skill_flags.append({
            "f": "Elite outlier-game / spike frequency",
            "d": (f"spike_pctl {spike_p:.0f} -- top-tier overdispersed scorer; "
                  "ceiling games cluster in dome + home environments"),
            "amp": "dome game, home crowd + negative script, soft QB tier"
        })
        conditions.append({
            "key": f"spike / outlier-game (spike_pctl {spike_p:.0f})",
            "mult": _sm,
            "fn": lambda d, w, m=_sm: w.get('home') or w.get('dome')
        })
    elif spike_p >= 70:
        skill_flags.append({
            "f": "Elevated spike / big-game potential",
            "d": (f"spike_pctl {spike_p:.0f} -- above-average outlier game frequency; "
                  "dome + home push this ceiling higher"),
            "amp": "dome game, home environment"
        })
        conditions.append({
            "key": f"spike ceiling (spike_pctl {spike_p:.0f})",
            "mult": 1.08,
            "fn": lambda d, w: w.get('home') or w.get('dome')
        })

    # ====================================================================
    # D  PASS VOLUME / ELITE USAGE VALUE
    #    When adv2 exists, cite 2-yr ypa, ptd_pg, patt_pg in descriptions.
    #    Thresholds still driven by value_pctl (single-season fusion chart).
    # ====================================================================
    # Build 2-yr passing citation string once, reuse below
    if adv2 and adv2_ypa is not None:
        _pass_cite = (f"2yr {adv2_ypa:.2f} YPA, {adv2_ptd_pg:.2f} pass TD/g, "
                      f"{adv2_patt_pg:.1f} att/g over {adv2_g}g")
    else:
        _pass_cite = f"value_pctl {value_p:.0f}, dk_pg {dk_pg:.1f}"

    if value_p >= 90:
        _vm = 1.18 if value_p >= 96 else 1.14
        skill_flags.append({
            "f": "Elite pass volume / usage value",
            "d": (f"{_pass_cite} (value_pctl {value_p:.0f}, adv_pctl {adv_p:.0f}) -- "
                  "maximum passing volume; pass-funnels and negative scripts supercharge DK output"),
            "amp": ("pass-funnel D (runp>=60 + covp<=50), underdog role, "
                    "soft QB tier, high-pace game")
        })
        conditions.append({
            "key": f"elite pass volume (value_pctl {value_p:.0f})",
            "mult": _shr(_vm, PASSVOL_SHRINK),   # [PRUNE: PASSVOL_SHRINK]
            "fn": lambda d, w, m=_vm: (
                (d.get('runp', 50) >= 60 and d.get('covp', 50) <= 50)
                or d.get('tiers', {}).get('QB') == 'SOFT'
            )
        })
    elif value_p >= 80:
        skill_flags.append({
            "f": "Strong pass volume / passing value",
            "d": (f"{_pass_cite} (value_pctl {value_p:.0f}) -- "
                  "high-volume passer; benefits from pass-funnel matchups"),
            "amp": "pass-funnel D (runp>=60 + covp<=50), underdog role forcing throws"
        })
        conditions.append({
            "key": f"strong pass volume (value_pctl {value_p:.0f})",
            "mult": _shr(1.12, PASSVOL_SHRINK),   # [PRUNE: PASSVOL_SHRINK]
            "fn": lambda d, w: (
                d.get('runp', 50) >= 60 and d.get('covp', 50) <= 50
            )
        })
    elif value_p >= 60 and dk_pg >= 13.0:
        skill_flags.append({
            "f": "Above-average passing volume",
            "d": (f"{_pass_cite} (value_pctl {value_p:.0f}) -- "
                  "decent volume base that elevates in heavy-passing game scripts"),
            "amp": "pass-funnel D (runp>=60 + covp<=50), trailing by 7+"
        })
        conditions.append({
            "key": f"passing volume (value_pctl {value_p:.0f})",
            "mult": _shr(1.08, PASSVOL_SHRINK),   # [PRUNE: PASSVOL_SHRINK]
            "fn": lambda d, w: (
                d.get('runp', 50) >= 60 and d.get('covp', 50) <= 50
            )
        })

    # ====================================================================
    # E  O-LINE QUALITY
    # ====================================================================
    if oline_p >= 75:
        _op = 1.12 if oline_p >= 88 else 1.08
        skill_flags.append({
            "f": "Elite O-line / clean pocket",
            "d": (f"oline_pctl {oline_p:.0f} -- elite run-blocking + pass-pro; "
                  "neutralizes top pass rushers, extends plays, expands downfield options"),
            "amp": ("vs heavy pass rush (sackp>=68): protection edge is LARGEST "
                    "when opponent's edge rushers are elite")
        })
        conditions.append({
            "key": f"elite O-line protection (oline_pctl {oline_p:.0f})",
            "mult": _op,
            "fn": lambda d, w, m=_op: d.get('sackp', 50) >= 68
        })
    elif 50 <= oline_p < 75 and protection_p >= 80:
        # Average line -- QB self-protection compensates
        skill_flags.append({
            "f": "Average OL + elite QB protection quality",
            "d": (f"oline_pctl {oline_p:.0f}, protection_pctl {protection_p:.0f} -- "
                  "line is average but QB's quick-release / decision speed compensates"),
            "amp": "vs moderate rush (sackp 50-70); QB neutralizes it with fast reads"
        })
        conditions.append({
            "key": f"QB protection quality (protection_pctl {protection_p:.0f})",
            "mult": 1.08,
            "fn": lambda d, w: d.get('manp', 50) >= 60 or d.get('sackp', 50) <= 40
        })
    elif oline_p <= 25 and carry_pg < 5.0:
        # Fragile pocket -- split by whether QB self-protects
        if protection_p >= 65:
            skill_flags.append({
                "f": "Weak OL -- compensated by elite QB self-protection",
                "d": (f"oline_pctl {oline_p:.0f} (weak unit) but protection_pctl {protection_p:.0f} -- "
                      "QB's quick release and decision-making partially offset the bad line"),
                "amp": ("worst: sackp>=78 + covp>=65 -- dual suppressor; "
                        "best: low sackp, QB dumps off quickly behind this line")
            })
            # Suppressor: only fires when BOTH heavy rush AND tight coverage present
            conditions.append({
                "key": f"weak OL / heavy rush dual-suppressor (oline {oline_p:.0f})",
                "mult": 0.83,
                "fn": lambda d, w: (
                    d.get('sackp', 50) >= 78 and d.get('covp', 50) >= 65
                )
            })
        else:
            skill_flags.append({
                "f": "Fragile pocket -- sack / pressure ceiling suppressor",
                "d": (f"oline_pctl {oline_p:.0f}, protection_pctl {protection_p:.0f} -- "
                      "exposed to heavy rush; forced turnovers / sacks collapse ceiling"),
                "amp": "suppressed by: heavy pass-rush (sackp>=70) -> sacks, throwaways, INTs"
            })
            conditions.append({
                "key": f"fragile pocket suppressor (oline {oline_p:.0f})",
                "mult": 0.80,
                "fn": lambda d, w: d.get('sackp', 50) >= 68
            })

    # ====================================================================
    # E2  POCKET / PRESSURE-HANDLING (chart2 press_pct + ttt)
    #     When chart2 exists, this replaces/refines the OL-only logic with
    #     real 2024 pressure data.  Thresholds from QB distribution:
    #       press_pct: median ~30%, high-pressure QBs >=35%, low <=27%
    #       ttt: median ~2.52s, hold-the-ball QBs >=2.75s, quick <=2.40s
    #     A QB who holds long (high TTT) AND faces heavy pressure (high
    #     press_pct) is acutely sensitive to pass-rush; clean pocket amplifies,
    #     heavy rush suppresses.  Quick-release QBs (low TTT) are more
    #     pressure-neutral.
    # ====================================================================
    if chart2 is not None and c2_press is not None and c2_ttt is not None:
        _pressure_concern = c2_press >= 33.0   # faces pressure frequently
        _holds_ball       = c2_ttt   >= 2.70   # holds the ball = more exposure
        _quick_release    = c2_ttt   <= 2.42   # quick-release = pressure-resistant

        if _pressure_concern and _holds_ball:
            # Amplify vs weak rush, suppress vs heavy rush -- flag is 2-directional
            _pttt_d = (
                f"2024 press_pct {c2_press:.1f}%, TTT {c2_ttt:.2f}s (FP charting) -- "
                "faces above-avg pressure AND holds ball long; "
                "clean pocket is the UNLOCK; heavy rush is ceiling killer"
            )
            skill_flags.append({
                "f": "Pressure-sensitive pocket passer (high TTT + high press%)",
                "d": _pttt_d,
                "amp": ("clean pocket (sackp<=30) = big ceiling unlock; "
                        "heavy rush (sackp>=70) suppresses hard; dome/fast field helps")
            })
            conditions.append({
                "key": (f"pressure-sensitive pocket (2024 press {c2_press:.1f}%, "
                        f"TTT {c2_ttt:.2f}s) -- clean pocket boost"),
                "mult": 1.14,
                "fn": lambda d, w: d.get('sackp', 50) <= 33
            })
            conditions.append({
                "key": (f"pressure-sensitive pocket (2024 press {c2_press:.1f}%, "
                        f"TTT {c2_ttt:.2f}s) -- heavy rush suppressor"),
                "mult": 0.82,
                "fn": lambda d, w: d.get('sackp', 50) >= 70
            })
        elif _pressure_concern and not _holds_ball:
            # High pressure but quick release -- partially neutralized
            _pttt_d = (
                f"2024 press_pct {c2_press:.1f}%, TTT {c2_ttt:.2f}s (FP charting) -- "
                "faces above-avg pressure but quick release partially neutralizes; "
                "still benefits from clean pocket"
            )
            skill_flags.append({
                "f": "Above-avg pressure rate, quick-release mitigated",
                "d": _pttt_d,
                "amp": ("clean pocket (sackp<=35) = modest ceiling lift; "
                        "heavy rush (sackp>=72) still suppresses via disruption")
            })
            conditions.append({
                "key": (f"pressure-quick-release (2024 press {c2_press:.1f}%, "
                        f"TTT {c2_ttt:.2f}s)"),
                "mult": 1.10,
                "fn": lambda d, w: d.get('sackp', 50) <= 35
            })
        elif not _pressure_concern and _holds_ball:
            # Holds the ball but protected -- boom unlocked with clean pocket
            _pttt_d = (
                f"2024 press_pct {c2_press:.1f}%, TTT {c2_ttt:.2f}s (FP charting) -- "
                "holds ball longer (deep-seeking), but is well-protected; "
                "benefits most from any additional pass-rush relief"
            )
            skill_flags.append({
                "f": "Ball-holder pocket passer (high TTT, protected)",
                "d": _pttt_d,
                "amp": ("weak rush (sackp<=30) = extra ceiling lift; "
                        "heavy rush (sackp>=72) = disruption risk amplified by hold time")
            })
            conditions.append({
                "key": (f"ball-holder pocket (2024 press {c2_press:.1f}%, "
                        f"TTT {c2_ttt:.2f}s) -- clean pocket amplifier"),
                "mult": 1.10,
                "fn": lambda d, w: d.get('sackp', 50) <= 32
            })
        elif _quick_release:
            # Low TTT = pressure-neutral; this is a mild positive in heavy-rush weeks
            _pttt_d = (
                f"2024 press_pct {c2_press:.1f}%, TTT {c2_ttt:.2f}s (FP charting) -- "
                "quick-release style makes him relatively pressure-resistant; "
                "boom ceiling is less pass-rush sensitive than average"
            )
            skill_flags.append({
                "f": "Quick-release pressure resistance (low TTT)",
                "d": _pttt_d,
                "amp": ("heavy rush (sackp>=70) hurts less than average; "
                        "clean pocket still a small positive")
            })
            conditions.append({
                "key": (f"quick-release pressure resistance (2024 TTT {c2_ttt:.2f}s, "
                        f"press {c2_press:.1f}%)"),
                "mult": 1.08,
                "fn": lambda d, w: d.get('sackp', 50) >= 68
            })
        # else: average TTT + average press_pct -- no new flag added (OL flags handle it)

    # ====================================================================
    # F  QB SELF-PROTECTION / DECISION-MAKING (standalone, no OL flag yet)
    #    Also: for pocket QBs behind bad OL with good protection_pctl,
    #    a CLEAN-POCKET matchup (weak rush) is their SMASH condition —
    #    the one time their bad OL doesn't suppress them.
    # ====================================================================
    # Clean-pocket opportunity flag: weak-OL QB with decent self-protection
    # gets a BOOST (not suppressed) when facing a weak pass rush (sackp<=30)
    # because QB's quick release fully compensates behind no pressure.
    if oline_p <= 35 and protection_p >= 65 and carry_pg < 5.0:
        skill_flags.append({
            "f": "Clean-pocket opportunity (weak rush removes OL ceiling penalty)",
            "d": (f"oline_pctl {oline_p:.0f} but protection_pctl {protection_p:.0f} -- "
                  "when opponent sack rate is low (sackp<=30), QB's quick release fully "
                  "compensates for the bad OL; this is the boom-unlocking condition"),
            "amp": "weak pass rush (sackp<=30) -- bad OL irrelevant when no pressure"
        })
        conditions.append({
            "key": f"clean pocket opportunity (sackp<=30, protection {protection_p:.0f})",
            "mult": 1.12,
            "fn": lambda d, w: d.get('sackp', 50) <= 30
        })

    already_prot = any(
        'protection' in sf['f'].lower() or 'weak ol' in sf['f'].lower()
        or 'fragile' in sf['f'].lower() or 'clean-pocket' in sf['f'].lower()
        for sf in skill_flags
    )
    if not already_prot and protection_p >= 88 and oline_p <= 70:
        skill_flags.append({
            "f": "Elite QB decision-making / ball-protection",
            "d": (f"protection_pctl {protection_p:.0f}, oline_pctl {oline_p:.0f} -- "
                  "avoids sacks + turnovers at elite rate; extends ceiling even without elite OL"),
            "amp": ("man-heavy coverage (quick reads beat man), "
                    "any sackp<=45 (no real pass rush = elite QB shreds)")
        })
        conditions.append({
            "key": f"QB decision-making / protection (protection_pctl {protection_p:.0f})",
            "mult": 1.10,
            "fn": lambda d, w: d.get('manp', 50) >= 62 or d.get('sackp', 50) <= 35
        })

    # ====================================================================
    # G  MATCHUP EXPLOITATION HISTORY
    # ====================================================================
    if matchup_p >= 75:
        skill_flags.append({
            "f": "Elite matchup exploitation",
            "d": (f"matchup_pctl {matchup_p:.0f} -- "
                  "consistently outperforms vs favorable matchups; boom frequency "
                  "spikes on soft schedules"),
            "amp": "soft QB tier (tiers[QB]==SOFT), pass-funnel, dome + soft coverage"
        })
        conditions.append({
            "key": f"matchup exploitation (matchup_pctl {matchup_p:.0f})",
            "mult": 1.14,
            "fn": lambda d, w: d.get('tiers', {}).get('QB') == 'SOFT'
        })
    elif matchup_p >= 55:
        skill_flags.append({
            "f": "Above-average matchup exploitation",
            "d": (f"matchup_pctl {matchup_p:.0f} -- "
                  "solid history of lifting performance in favorable defensive matchups"),
            "amp": "soft QB tier, pass-funnel matchup"
        })
        conditions.append({
            "key": f"matchup exploitation (matchup_pctl {matchup_p:.0f})",
            "mult": 1.08,
            "fn": lambda d, w: d.get('tiers', {}).get('QB') == 'SOFT'
        })

    # ====================================================================
    # H  SIS ADVANCED EFFICIENCY
    # ====================================================================
    if sis_p >= 85:
        skill_flags.append({
            "f": "SIS elite efficiency / decision-making edge",
            "d": (f"sis_value_pctl {sis_p:.0f} -- "
                  "top-tier SIS composite; elite accuracy + decision speed elevates "
                  "ceiling vs zone and soft coverage"),
            "amp": "zone coverage (manp<=40), clean pocket, soft-tier corners"
        })
        conditions.append({
            "key": f"SIS elite efficiency (sis_value_pctl {sis_p:.0f})",
            "mult": 1.12,
            "fn": lambda d, w: d.get('manp', 50) <= 40 or d.get('covp', 50) <= 35
        })
    elif sis_p >= 65:
        skill_flags.append({
            "f": "SIS above-average efficiency",
            "d": (f"sis_value_pctl {sis_p:.0f} -- "
                  "above-average SIS score; lifts ceiling in zone-heavy / soft-coverage weeks"),
            "amp": "zone coverage (manp<=40), soft pass tier"
        })
        conditions.append({
            "key": f"SIS efficiency (sis_value_pctl {sis_p:.0f})",
            "mult": 1.08,
            "fn": lambda d, w: (
                d.get('manp', 50) <= 40
                or d.get('tiers', {}).get('QB') == 'SOFT'
            )
        })

    # ====================================================================
    # I  BOOM_PCTL (only if not already covered by ceiling/spike flags above,
    #    NOT blocked by OL / protection flags which are different dimensions)
    # ====================================================================
    has_ceiling_boom = any(
        any(w in sf['f'].lower()
            for w in ('explosive passing', 'spike', 'outlier', 'boom-frequency',
                      'above-average passing', 'passing ceiling'))
        for sf in skill_flags
    )
    if boom_p >= 85 and not has_ceiling_boom:
        skill_flags.append({
            "f": "Elite boom-game frequency (boom_pctl)",
            "d": (f"boom_pctl {boom_p:.0f} -- "
                  "elite boom-game composite; TD clustering and big-play rate drive "
                  "frequent ceiling games"),
            "amp": "positive script (near goal-line), soft QB tier, high game-pace / shootout"
        })
        conditions.append({
            "key": f"boom-game frequency (boom_pctl {boom_p:.0f})",
            "mult": 1.12,
            "fn": lambda d, w: d.get('tiers', {}).get('QB') == 'SOFT'
        })

    # ====================================================================
    # J2  COVERAGE SPECIALIST
    #     When cspec present: add a skill flag describing his standout scheme.
    #     Per-week: if opp runs his best coverage notably above league average
    #     (SHELL[opp][best_key] >= SHELL['_LEAGUE'][best_key] + 3) → ×1.10
    #     (×1.13 if z>=2.0), lit flag citing real opp coverage %.
    # ====================================================================
    if cspec:
        _cs_best   = cspec['best']        # e.g. "Cover-3 & Man"
        _cs_key    = cspec['best_key']    # e.g. "c3"
        _cs_pctl   = cspec.get('pctl', 0) or 0
        _cs_rts    = cspec.get('routes', 0) or 0
        _cs_ratio  = cspec['ratio']
        _cs_lg     = cspec.get('lg', SHELL['_LEAGUE'].get(_cs_key, 0))
        _cs_mult   = 1.13 if _cs_pctl >= 95 else 1.10
        _cs_d      = (f"crushes {_cs_best} ({_cs_ratio:.2f}x league FP/DB, {_cs_pctl}th pctl over {_cs_rts} dropbacks) -- "
                      f"lg avg {_cs_key}={_cs_lg:.1f}; his scheme-specific efficiency is a "
                      f"clean matchup signal vs {_cs_best}-heavy defenses")
        skill_flags.append({
            "f": "Coverage specialist",
            "d": _cs_d,
            "amp": (f"vs defenses that run {_cs_best} heavily "
                    f"(opp {_cs_key} >= lg {_cs_lg:.1f}+3)")
        })
        _league_val = SHELL['_LEAGUE'].get(_cs_key, 0)
        conditions.append({
            "key": f"coverage specialist — {_cs_best} heavy D ({_cs_key} >= lg+3)",
            "mult": _shr(_cs_mult, COV_SHRINK),   # [PRUNE: COV_SHRINK]
            "fn": lambda d, w, ck=_cs_key, lv=_league_val, cm=_cs_mult, cb=_cs_best: (
                (lambda sh: (
                    sh is not None
                    and sh.get(ck) is not None
                    and sh[ck] >= lv + 3
                ))(SHELL.get(w.get('opp', '')))
            )
        })
        # Override the lit-flag label to cite real percentages for transparency
        # (done at week-loop time via a wrapper that patches the key string)
        conditions[-1]['_cspec_meta'] = {
            'best': _cs_best,
            'best_key': _cs_key,
            'league_val': _league_val,
        }

    # ====================================================================
    # GLOBAL PER-WEEK CONDITIONS
    # ====================================================================

    # Soft QB tier standalone -- only add if existing conditions don't already
    # test for QB SOFT tier (avoids double-counting same activator)
    soft_in_conds = sum(
        1 for c in conditions
        if 'soft' in c['key'].lower() or 'tier' in c['key'].lower()
        or 'volume' in c['key'].lower()
    )
    if soft_in_conds == 0:
        conditions.append({
            "key": "soft QB tier (pass-friendly defense)",
            "mult": 1.12,
            "fn": lambda d, w: d.get('tiers', {}).get('QB') == 'SOFT'
        })

    # Dome boost for any QB with meaningful passing or rushing
    if ceiling_p >= 35 or carry_pg >= 3.5 or dk_pg >= 12.0:
        conditions.append({
            "key": "dome environment (elements removed)",
            "mult": 1.08,
            "fn": lambda d, w: bool(w.get('dome'))
        })

    # Pass-funnel -- for QBs whose flags don't already cover it
    has_pf = any(
        'funnel' in c['key'].lower() or 'volume' in c['key'].lower()
        for c in conditions
    )
    if not has_pf and value_p >= 45:
        conditions.append({
            "key": "pass-funnel game (runp>=60 + covp<=50)",
            "mult": 1.10,
            "fn": lambda d, w: (
                d.get('runp', 50) >= 60 and d.get('covp', 50) <= 50
            )
        })

    # ----------------------------------------------------------------
    # ENV / PACE / SCRIPT  per-week lit conditions
    # QBs without team_env data skip all three blocks.
    # ----------------------------------------------------------------
    if has_tenv:

        # ENV: shootout setup (own env_idx>=65 AND opp covp<=35)
        conditions.append({
            "key": (f"env shootout (own env_idx {own_env}, opp covp<=35)"),
            "mult": 1.08,
            "fn": lambda d, w, oe=own_env: (
                oe >= 65 and d.get('covp', 50) <= 35
            )
        })

        # PACE: fast game (own pace_pctl>=65 AND opp pace_pctl>=50)
        # slow game suppressor (both pace_pctls<=35)
        conditions.append({
            "key": (f"pace fast-game (own pace_pctl {own_pace}, opp pace>=50) -- more dropbacks"),
            "mult": 1.08,
            "fn": lambda d, w, op=own_pace: (
                op >= 65 and TENV.get(w.get('opp', ''), {}).get('pace_pctl', 50) >= 50
            )
        })
        conditions.append({
            "key": (f"pace slow-game suppressor (both pace_pctls<=35)"),
            "mult": 0.95,
            "fn": lambda d, w, op=own_pace: (
                op <= 35
                and TENV.get(w.get('opp', ''), {}).get('pace_pctl', 50) <= 35
            )
        })

        # SCRIPT: underdog (d<=-2.5) → ×1.10 pass volume/garbage-time ceiling
        # big favorite (d>=2.5) + pocket QB → ×0.97; rushing QBs (rush_pg_eff>=3.5) neutral
        _is_rushing_qb = rush_pg_eff >= 3.5
        conditions.append({
            "key": (f"script underdog (own wt {own_wt} vs opp, d<=-2.5) -- pass volume/garbage-time QB ceiling"),
            "mult": 1.10,
            "fn": lambda d, w, owt=own_wt: (
                owt - TENV.get(w.get('opp', ''), {}).get('win_total', 8.0) <= -2.5
            )
        })
        if not _is_rushing_qb:
            # pocket QB only: suppress when big favorite (fewer dropbacks)
            conditions.append({
                "key": (f"script big-favorite suppressor (pocket QB, own wt {own_wt}, d>=2.5) -- fewer dropbacks"),
                "mult": 0.97,
                "fn": lambda d, w, owt=own_wt: (
                    owt - TENV.get(w.get('opp', ''), {}).get('win_total', 8.0) >= 2.5
                )
            })
        # (rushing QBs are not penalized when favored -- goal-line carries stay productive)

    # -- SUPPRESSORS -------------------------------------------------

    # Tough QB tier
    conditions.append({
        "key": "tough QB tier suppressor",
        "mult": 0.75,
        "fn": lambda d, w: d.get('tiers', {}).get('QB') == 'TOUGH'
    })

    # Heavy rush -- only for pocket QBs behind non-elite lines
    if carry_pg < 5.0 and oline_p < 75:
        sack_thresh = 78 if protection_p >= 65 else 70
        conditions.append({
            "key": f"heavy rush suppressor (pocket, oline_pctl {oline_p:.0f})",
            "mult": 0.84,
            "fn": lambda d, w, t=sack_thresh: d.get('sackp', 50) >= t
        })

    # Run-funnel -- only pure pocket QBs
    if carry_pg < 4.0:
        conditions.append({
            "key": "run-funnel suppressor (pocket QB, soft pass-D + run-first)",
            "mult": 0.88,
            "fn": lambda d, w: (
                d.get('covp', 50) >= 65 and d.get('runp', 50) <= 35
            )
        })

    # ====================================================================
    # J  ENVIRONMENT / PACE / SCRIPT (env/pace/script — no rz/shell for QB)
    #    ENV: standing skill flag if own env_idx>=70 (high-scoring offense).
    #    Per-week conditions added in GLOBAL PER-WEEK CONDITIONS below.
    # ====================================================================
    if has_tenv and own_env >= 70:
        skill_flags.append({
            "f": "High-scoring offense environment",
            "d": (f"env_idx {own_env} (top-tier scoring environment) -- "
                  f"pace_pctl {own_pace}, win_total {own_wt}; "
                  "offense generates ceiling weekly; shootout matchups supercharge QB upside"),
            "amp": "opp covp<=35 (shootout setup), fast-paced opponent game, underdog script"
        })

    # ====================================================================
    # MINIMUM 3 SKILL FLAGS -- exhaust all available stats in tiers
    # ====================================================================
    _added = {sf['f'] for sf in skill_flags}

    # Tier 1: adv_pctl (any QB with a real score, not exact 50 placeholder)
    if len(skill_flags) < 3 and adv_p != 50.0:
        lbl = "Advanced composite upside"
        if lbl not in _added:
            skill_flags.append({
                "f": lbl,
                "d": (f"adv_pctl {adv_p:.0f}, boom_pctl {boom_p:.0f} -- "
                      f"advanced metrics signal ceiling potential; dk_pg {dk_pg:.1f}"),
                "amp": "soft QB tier, pass-funnel, home game"
            })
            conditions.append({
                "key": "advanced composite upside",
                "mult": 1.08,
                "fn": lambda d, w: (
                    w.get('home') or d.get('tiers', {}).get('QB') == 'SOFT'
                )
            })
            _added.add(lbl)

    # Tier 2a: oline_pctl context (21-74, not yet flagged)
    if len(skill_flags) < 3 and 21 <= oline_p < 75:
        lbl = f"O-line context (oline_pctl {oline_p:.0f})"
        if lbl not in _added:
            skill_flags.append({
                "f": lbl,
                "d": (f"oline_pctl {oline_p:.0f}, protection_pctl {protection_p:.0f} -- "
                      "average blocking; pocket quality is a neutral-to-modest factor"),
                "amp": "heavy rush (sackp>=70) mildly suppresses; clean pocket (sackp<=30) helps"
            })
            _added.add(lbl)

    # Tier 2b: elite OL not yet captured above (edge case: high oline, low carry_pg)
    if len(skill_flags) < 3 and oline_p >= 75:
        lbl = "Elite O-line / clean pocket"
        if lbl not in _added:
            _op2 = 1.12 if oline_p >= 88 else 1.08
            skill_flags.append({
                "f": lbl,
                "d": (f"oline_pctl {oline_p:.0f} -- elite blocking; "
                      "clean pocket even without a great rushing threat"),
                "amp": "vs heavy rush (sackp>=68): protection advantage largest vs elite edge"
            })
            conditions.append({
                "key": f"elite O-line protection (oline_pctl {oline_p:.0f})",
                "mult": _op2,
                "fn": lambda d, w, m=_op2: d.get('sackp', 50) >= 68
            })
            _added.add(lbl)

    # Tier 3: protection_pctl
    if len(skill_flags) < 3 and protection_p >= 75:
        lbl = f"QB ball-protection quality (protection_pctl {protection_p:.0f})"
        if lbl not in _added:
            skill_flags.append({
                "f": lbl,
                "d": (f"protection_pctl {protection_p:.0f} -- "
                      "avoids sacks and turnovers at above-average rate; "
                      f"extends drives behind any OL quality (oline_pctl {oline_p:.0f})"),
                "amp": "man-heavy coverage (quick reads beat man), clean pocket (sackp<=35)"
            })
            conditions.append({
                "key": f"QB self-protection (protection_pctl {protection_p:.0f})",
                "mult": 1.08,
                "fn": lambda d, w: d.get('manp', 50) >= 60 or d.get('sackp', 50) <= 35
            })
            _added.add(lbl)

    # Tier 4: dk_pg volume anchor (any QB who actually played)
    if len(skill_flags) < 3 and dk_pg > 0.0:
        lbl = "Game-script passing volume anchor"
        if lbl not in _added:
            skill_flags.append({
                "f": lbl,
                "d": (f"dk_pg {dk_pg:.1f}, value_pctl {value_p:.0f} -- "
                      "volume base when healthy; boom needs script or matchup trigger"),
                "amp": "pass-funnel opponent, negative script (trailing), soft QB tier"
            })
            conditions.append({
                "key": "game-script passing anchor",
                "mult": 1.08,
                "fn": lambda d, w: (
                    d.get('runp', 50) >= 55 and d.get('covp', 50) <= 50
                )
            })
            _added.add(lbl)

    # Tier 4b: matchup_pctl -- any QB has this stat
    if len(skill_flags) < 3 and matchup_p > 0:
        lbl = f"Matchup context (matchup_pctl {matchup_p:.0f})"
        if lbl not in _added:
            skill_flags.append({
                "f": lbl,
                "d": (f"matchup_pctl {matchup_p:.0f} -- "
                      "limited data but fusion matchup metric available as soft signal"),
                "amp": "soft QB tier, favorable schedule weeks"
            })
            _added.add(lbl)

    # Tier 5: absolute fallback for zero-data backups
    if len(skill_flags) < 3:
        lbl = "Ceiling model fusion-seeded"
        if lbl not in _added:
            skill_flags.append({
                "f": lbl,
                "d": (f"ceiling_pctl {ceiling_p:.0f}, boom_pctl {boom_p:.0f}, "
                      f"adv_pctl {adv_p:.0f} -- very limited 2025 data; "
                      "model seeded from fusion pctls and positional base rate"),
                "amp": "soft QB tier, home game, pass-funnel"
            })
            _added.add(lbl)

    # -- One-line thesis -------------------------------------------------
    line = _build_line(
        name, carry_pg, ypc, value_p, ceiling_p, spike_p, boom_p,
        oline_p, protection_p, matchup_p, adv_p, sis_p, dk_pg,
        rush_pg_eff=rush_pg_eff, rushyd_pg=rushyd_pg, rushtd_g=rushtd_g,
        adv2_g=adv2_g, has_adv2=adv2 is not None
    )

    return {
        'base': base, 'hist': hist,
        'skill_flags': skill_flags, 'conditions': conditions, 'line': line,
    }


# -- engine-facing accessors (the heavy lifting is done in context) --------------
def base(v, posbase, prof):
    return prof['base'], prof['hist']


def skill_flags(prof):
    return prof['skill_flags']


def line(prof):
    return prof['line']


# -- per-week activation (copies the legacy week-loop body verbatim) -------------
def activate(prof, base, skill_flags, opp_data, week_ctx):
    conditions = prof['conditions']
    opp_def = opp_data            # engine passes model.opp_data(opp) == DE.get(opp, {})
    opp     = week_ctx['opp']

    lit_flags = []
    lit_mults = []
    for cond in conditions:
        try:
            active = cond["fn"](opp_def, week_ctx)
        except Exception:
            active = False
        if active:
            # For cspec conditions, build a richer label citing real %s
            if '_cspec_meta' in cond:
                _cm = cond['_cspec_meta']
                _sh_opp = SHELL.get(opp, {})
                _opp_pct = _sh_opp.get(_cm['best_key'])
                _lg_pct  = _cm['league_val']
                if _opp_pct is not None:
                    _lf_label = (f"faces {_cm['best']}-heavy D "
                                 f"(opp {_opp_pct:.1f}% vs lg {_lg_pct:.1f}%) "
                                 f"— his best scheme")
                else:
                    _lf_label = cond["key"]
                lit_flags.append(_lf_label)
            else:
                lit_flags.append(cond["key"])
            lit_mults.append(cond["mult"])

    return lit_flags, lit_mults, len(conditions)
