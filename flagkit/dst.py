#!/usr/bin/env python3
"""flagkit/dst.py — DST position semantics (ports build_flags_DST.py onto flagkit.engine).

ONLY the DST-specific logic lives here: the base seed, the skill-flag cascade, the per-week
condition list, the one-line thesis, and the empirical summary. Every piece of shared
scaffolding (player loop, per-week activation, BYE, grading, record/week assembly, write)
is in flagkit/engine.py and is NOT duplicated.

The logic below is transcribed verbatim from build_flags_DST.py so the output is
byte-for-byte identical (verified by diffing boom/flags_DST.json).
"""
import json
import os
from boom_lib import reg_base, cap

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repo root (flagkit/ is one level down)
OPP = json.load(open(os.path.join(HERE, 'boom', 'opp_offense.json')))
POS = 'DST'


# -- per-week opponent inputs the conditions read --------------------------------
def opp_data(opp):
    return OPP.get(opp, {})


def get_own_off_q(team):
    return OPP.get(team, {}).get('off_q', 50)


# -- profile (position-specific feature extraction) ------------------------------
def context(k, v, gl, bd):
    df = v.get('def', {})
    return {
        'k': k, 'name': v['name'], 'team': v.get('team', ''), 'adp': v.get('adp'),
        'n_games': v.get('n_games', 0), 'boom_games': v.get('boom_games', 0),
        'df': df,
        'covp': df.get('covp') or 50,        # pass coverage percentile (higher = tougher D)
        'runp': df.get('runp') or 50,        # run defense percentile
        'sackp': df.get('sackp') or 50,      # pass-rush percentile
        'manp': df.get('manp') or 50,        # man-coverage rate percentile
        'sack_rate': df.get('sack_rate') or 5.5,
        'man_rate': df.get('man_rate') or 20.0,
        'tiers': df.get('tiers') or {},
        'own_off_q': get_own_off_q(v.get('team', '')),
    }


# -- regularized base (with the DST seed fallback) -------------------------------
def base(v, posbase, prof):
    rb = reg_base(v, posbase)
    if rb is not None:
        return rb, True
    sackp, covp, runp = prof['sackp'], prof['covp'], prof['runp']
    pctl_avg = (sackp * 0.5 + covp * 0.35 + runp * 0.15) / 100.0
    b = posbase['DST'] * (0.75 + 0.5 * pctl_avg)
    return round(cap(b, 0.06, 0.45), 3), False


# -- empirical summary string ----------------------------------------------------
def empirical(k, gl, bd):
    SPIKE = bd['SPIKE']['DST']
    games = gl.get(k, [])
    if not games:
        return "No 2025 gamelog data."
    n = len(games)
    booms = [g for g in games if g.get('boom') == 1]
    nb = len(booms)
    if nb == 0:
        return (f"0 ceiling games (>={SPIKE} DK pts) in {n} active weeks tracked; "
                "small sample or no boom games recorded.")
    home_b = sum(1 for g in booms if g.get('home'))
    dome_b = sum(1 for g in booms if g.get('dome'))
    weak_b = sum(1 for g in booms if g.get('opp_off_q', 100) <= 35)
    bad_qb = sum(1 for g in booms if g.get('opp_qb_q', 100) <= 45)
    parts = [f"{nb}/{n} ceiling games (>={SPIKE} DK pts)"]
    notes = []
    if home_b >= max(1, nb // 2):
        notes.append(f"{home_b} at home")
    if dome_b >= max(1, nb // 2):
        notes.append(f"{dome_b} in a dome")
    if weak_b >= max(1, nb // 2):
        notes.append(f"{weak_b} vs weak offense (opp_off_q≤35)")
    if bad_qb >= max(1, nb // 2):
        notes.append(f"{bad_qb} vs low-quality QB (qb_q≤45)")
    if not notes:
        notes.append("no single condition dominates — small sample")
    parts.append("; ".join(notes))
    return ". ".join(parts) + "."


# -- one-line thesis -------------------------------------------------------------
def line(prof):
    name, team = prof['name'], prof['team']
    covp, runp, sackp = prof['covp'], prof['runp'], prof['sackp']
    manp, sack_rate, man_rate = prof['manp'], prof['sack_rate'], prof['man_rate']
    own_off_q = prof['own_off_q']
    parts = []
    if sackp >= 90:
        parts.append(f"elite pass rush (sackp {sackp}th pctl, {sack_rate}% sack rate) "
                     f"detonates vs weak OLs (ol_q≤35)")
    elif sackp >= 75:
        parts.append(f"strong pass rush (sackp {sackp}th pctl) combined with "
                     f"weak-OL matchups (ol_q≤35) is the trench ceiling lever")
    elif sackp >= 60:
        parts.append(f"above-average pass rush (sackp {sackp}th pctl) unlocked by weak OL opponents")
    else:
        parts.append(f"limited pass rush (sackp {sackp}th pctl) means ceiling relies on "
                     f"coverage/turnovers rather than sack accumulation")
    if covp >= 85:
        parts.append(f"elite ball-hawk coverage (covp {covp}th pctl) generates INTs vs any weak QB")
    elif covp >= 65:
        parts.append(f"above-average coverage (covp {covp}th pctl) creates takeaway ceiling vs off_q≤50")
    if runp >= 85:
        parts.append(f"elite run stop (runp {runp}th pctl) forces opponents one-dimensional → sack/INT pipeline")
    elif runp >= 65:
        parts.append(f"solid run defense (runp {runp}th pctl) funnels opponents into pass-first scripts")
    parts.append(f"ceiling peaks vs weak offenses (off_q≤35) and poor QBs (qb_q≤45)")
    if own_off_q >= 65:
        parts.append(f"own offense (off_q {own_off_q}) creates trailing-opponent script")
    return f"{name}: " + "; ".join(parts[:4]) + "."


# -- skill flags (the {f,d,amp} cascade) -----------------------------------------
def skill_flags(prof):
    covp, runp, sackp = prof['covp'], prof['runp'], prof['sackp']
    manp, sack_rate, man_rate = prof['manp'], prof['sack_rate'], prof['man_rate']
    sf = []

    # SKILL 1: Pass rush quality
    if sackp >= 90:
        sf.append({"f": "Elite pass rush / dominant DL",
                   "d": (f"sackp {sackp}th pctl, sack_rate {sack_rate}% — "
                         "top-3 pass-rush unit; generates sacks, strip-sacks, forced fumbles "
                         "and collapsed-pocket INTs at an elite rate"),
                   "amp": ("weak opp OL (ol_q≤35) — trench dominance; "
                           "vs any offense when own rush is this elite; "
                           "dome / home crowd (false starts compound pressure)")})
    elif sackp >= 75:
        sf.append({"f": "Strong pass rush / above-average DL pressure",
                   "d": (f"sackp {sackp}th pctl, sack_rate {sack_rate}% — "
                         "top-tier rush unit that wins in one-on-ones; sack ceiling is real "
                         "every week, especially vs leaky OLs"),
                   "amp": ("weak opp OL (ol_q≤35) magnifies this; "
                           "facing poor-protection teams unlocks sack/strip-sack ceiling")})
    elif sackp >= 60:
        sf.append({"f": "Above-average pass rush",
                   "d": (f"sackp {sackp}th pctl, sack_rate {sack_rate}% — "
                         "pass rush is a real strength, performs best when opp OL is weak "
                         "or opp offense is forced into obvious passing situations"),
                   "amp": ("weak opp OL (ol_q≤35): trench wins; "
                           f"run-stop forces passing (runp {runp})")})
    elif sackp <= 20:
        sf.append({"f": "Weak pass rush — ceiling relies on turnovers/coverage",
                   "d": (f"sackp {sackp}th pctl, sack_rate {sack_rate}% — "
                         "limited pass rush; DST ceiling must come from INTs, forced fumbles, "
                         "return TDs rather than sack-based scoring"),
                   "amp": (f"ball-hawk coverage (covp {covp}) and bad opposing QBs "
                           "are the ceiling unlocks, not the pass rush")})

    # SKILL 2: Ball-hawk coverage
    if covp >= 85:
        sf.append({"f": "Elite ball-hawk coverage / takeaway unit",
                   "d": (f"covp {covp}th pctl, manp {manp}th pctl — "
                         "top-tier coverage that generates INTs, pass deflections, and short fields; "
                         "ceiling explodes vs inaccurate QBs who force throws into coverage"),
                   "amp": ("low qb_q (≤35) opponent: throws into coverage = takeaways; "
                           f"man-heavy scheme (manp {manp}) creates bracket jams and tipped balls")})
    elif covp >= 65:
        sf.append({"f": "Strong coverage / above-average takeaway upside",
                   "d": (f"covp {covp}th pctl, manp {manp}th pctl — "
                         "above-average coverage creates turnovers and negative plays; "
                         "ceiling amplified by weak or inaccurate opposing QB"),
                   "amp": ("low qb_q (≤45) opponent forces bad decisions into this coverage; "
                           "dome helps CBs (no wind on deep shots)")})
    elif covp >= 45 and manp >= 70:
        sf.append({"f": "Man-coverage specialist unit",
                   "d": (f"covp {covp}th pctl but manp {manp}th pctl — "
                         f"below-average overall coverage but plays heavy man (man_rate {man_rate:.1f}%); "
                         "generates pressure-through-coverage TFLs and coverage sacks"),
                   "amp": ("vs short-area routes / poor-route QBs (qb_q≤45); "
                           "man rate means scheme-specific DST leverage")})
    elif covp <= 20:
        sf.append({"f": "Poor coverage — ceiling capped unless pass rush fires",
                   "d": (f"covp {covp}th pctl — opposing QBs find open receivers easily; "
                         "ceiling requires heavy pass-rush or opponent self-destruction "
                         "(fumbles, bad-weather throws)"),
                   "amp": (f"sackp {sackp} must carry the ceiling weight; "
                           "weak offense (off_q≤35) still creates ceiling via sheer volume of "
                           "negative plays")})

    # SKILL 3: Run defense
    if runp >= 85:
        sf.append({"f": "Elite run defense — forces one-dimensional offense",
                   "d": (f"runp {runp}th pctl — "
                         "top-tier run-stopping; forces opponents to abandon the run early, "
                         "creating obvious passing situations that amplify the pass rush and coverage"),
                   "amp": ("run-heavy opponents (who want to run): forced into pass → sacks/INTs; "
                           "completes the trench triangle: stop-run → pass → sack/INT ceiling")})
    elif runp >= 65:
        sf.append({"f": "Stout run defense — creates pass-first game scripts",
                   "d": (f"runp {runp}th pctl — "
                         "solid run-stop that forces opponents one-dimensional; "
                         "pipeline effect: run stop → opponent passes → sack/INT opportunities"),
                   "amp": (f"pairs with sackp {sackp} and covp {covp} to chain "
                           "run stop → pass attempt → ceiling play")})
    elif runp <= 20:
        sf.append({"f": "Porous run defense — allows rushing ceiling to opponents",
                   "d": (f"runp {runp}th pctl — "
                         "run defense is a liability; opponents can stay in run game, "
                         "limiting pass-rush and coverage ceiling opportunities for this DST"),
                   "amp": ("need pass-happy offense (high off_q) to bypass own run-D weakness; "
                           "aerial offense opponents are the ONLY setup")})

    # SKILL 4: Scheme / coverage type (only if not redundant)
    if len(sf) < 4:
        if manp >= 80 and covp >= 55:
            sf.append({"f": "Aggressive man-coverage scheme",
                       "d": (f"manp {manp}th pctl, man_rate {man_rate:.1f}% — "
                             "plays man at elite rate; aggressive scheme creates forced incompletions "
                             "and batted balls in the backfield"),
                       "amp": ("vs poor route-running QBs (qb_q≤45); "
                               "home crowd amplifies false starts in man vs tight windows")})
        elif manp <= 20 and (covp >= 55 or runp >= 55):
            sf.append({"f": "Zone-heavy scheme with coverage safety net",
                       "d": (f"manp {manp}th pctl (zone-heavy), covp {covp}th / runp {runp}th — "
                             "reads + zone coverage creates INT opportunities and erases routes; "
                             "zone DSTs boom when QB hesitates and takes sacks"),
                       "amp": ("vs decision-slow QBs (qb_q≤50); "
                               "deep zones erase downfield shots → checkdowns → sacks/punts")})

    # at least 3 skill flags
    if len(sf) < 3:
        sf.append({"f": f"Composite defense profile (covp {covp} / runp {runp} / sackp {sackp})",
                   "d": (f"covp {covp}th pctl, runp {runp}th pctl, sackp {sackp}th pctl — "
                         "mixed defensive profile; ceiling depends primarily on opponent quality "
                         f"(off_q/qb_q) rather than unit-specific dominance"),
                   "amp": ("vs weak offense (off_q≤35): low-quality throws into coverage = turnovers; "
                           "home crowd noise adds false-start sacks")})

    return sf[:6]   # trim to 6 max


# -- per-week conditions ---------------------------------------------------------
def conditions(prof):
    sackp, covp, runp = prof['sackp'], prof['covp'], prof['runp']
    own_off_q = prof['own_off_q']
    conds = []

    # Trench: own DL strength (standalone)
    if sackp >= 75:
        conds.append({"key": f"own elite pass rush (sackp {sackp})", "mult": 1.15,
                      "fn": lambda opp_data, w: True})
    elif sackp >= 60:
        conds.append({"key": f"own strong pass rush (sackp {sackp})", "mult": 1.10,
                      "fn": lambda opp_data, w: True})

    # Trench: opp OL weakness / strength
    conds.append({"key": "opp weak OL (ol_q≤35) — trench mismatch favors DST", "mult": 1.30,
                  "fn": lambda opp_data, w: opp_data.get('ol_q', 50) <= 35})
    conds.append({"key": "opp strong OL suppressor (ol_q≥70) — neutralizes pass rush", "mult": 0.78,
                  "fn": lambda opp_data, w: opp_data.get('ol_q', 50) >= 70})

    # Matchup: weak offense
    conds.append({"key": "vs weak offense (off_q≤35) — low pts allowed + turnovers", "mult": 1.38,
                  "fn": lambda opp_data, w: opp_data.get('off_q', 50) <= 35})

    # Matchup: low-quality QB / mid-tier
    conds.append({"key": "vs low-quality QB (qb_q≤35) — forced throws into coverage", "mult": 1.20,
                  "fn": lambda opp_data, w: opp_data.get('qb_q', 50) <= 35})
    conds.append({"key": "vs below-average QB (qb_q 36-50)", "mult": 1.10,
                  "fn": lambda opp_data, w: 36 <= opp_data.get('qb_q', 51) <= 50})

    # Suppressors: elite offense / elite QB
    conds.append({"key": "vs elite offense suppressor (off_q≥75) — ceiling capped", "mult": 0.72,
                  "fn": lambda opp_data, w: opp_data.get('off_q', 50) >= 75})
    conds.append({"key": "vs elite QB suppressor (qb_q≥80) — shreds coverage", "mult": 0.80,
                  "fn": lambda opp_data, w: opp_data.get('qb_q', 50) >= 80})

    # Ball-hawk coverage
    if covp >= 65:
        conds.append({"key": f"ball-hawk coverage (covp {covp}) vs weak/avg offense", "mult": 1.20,
                      "fn": lambda opp_data, w: opp_data.get('off_q', 50) <= 50})
    elif covp >= 45:
        conds.append({"key": f"coverage unit (covp {covp}) vs manageable offense", "mult": 1.10,
                      "fn": lambda opp_data, w: opp_data.get('off_q', 50) <= 45})

    # Run-stop pipeline
    if runp >= 65:
        conds.append({"key": f"run-stop pipeline (runp {runp}) forces one-dimensional offense", "mult": 1.12,
                      "fn": lambda opp_data, w: opp_data.get('off_q', 50) <= 60})

    # Script flag
    if own_off_q >= 65:
        conds.append({"key": f"positive script — own off_q {own_off_q} favors DST (opp trails, passes more)",
                      "mult": 1.15,
                      "fn": lambda opp_data, w, own_q=own_off_q: (own_q >= 65 and opp_data.get('off_q', 50) <= 40)})
    elif own_off_q >= 40:
        conds.append({"key": f"moderate script edge — own off_q {own_off_q} vs weak opponent",
                      "mult": 1.08,
                      "fn": lambda opp_data, w, own_q=own_off_q: (own_q >= 40 and opp_data.get('off_q', 50) <= 30)})

    # Home / dome
    conds.append({"key": "home game (crowd noise → false starts → sacks)", "mult": 1.08,
                  "fn": lambda opp_data, w: bool(w.get('home'))})
    conds.append({"key": "dome game (controlled environment → crowd noise amplified indoors)", "mult": 1.06,
                  "fn": lambda opp_data, w: bool(w.get('dome'))})

    return conds
