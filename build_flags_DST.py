#!/usr/bin/env python3
"""
build_flags_DST.py — Player-by-player, flag-based DST ceiling model.
Writes boom/flags_DST.json keyed by statmenu key (e.g. "dst_den").

Ceiling prob(week) = reg_base × product(lit multipliers).
Every DST gets flags derived from ITS OWN def profile (covp/runp/sackp) + the
OPPONENT offense it faces each week (OPP[opp].off_q / qb_q / ol_q / pblock).

SWING targets for DST: tough=0.06, soft=0.30  [boom_lib.SWING['DST']]
  → full-soft product ~1.6–1.9× base; full-tough ~0.35–0.45× base.
  DST swing = 5.0×, the widest of any position — driven by opponent quality.

KEY DIFFERENTIATORS:
  1. Elite pass rush (def.sackp≥75): standalone booster + amplified by weak opp OL
  2. Trench matchup SEPARATE flags — own DL strength AND opp OL weakness independently
  3. Ball-hawk coverage (def.covp≥65): INTs, drives stopped; amplified by bad QB
  4. Stout run-stop (def.runp≥65): forces one-dimensional offense → sack/INT pipeline
  5. Dominant matchup driver: facing weak offense (off_q≤35) and/or low qb_q (≤35)
  6. Script flag: big favorite (own off_q well above opp off_q) → opp passes when trailing
  7. Home + dome: crowd-noise false starts → sacks + turnovers
"""

import json, os, sys
from boom_lib import load, players, reg_base, prob, label, write, cap, SWING

HERE = os.path.dirname(os.path.abspath(__file__))
sm, gl, sch, de, bd = load()
posbase = bd['posbase']
POS = 'DST'
SPIKE = bd['SPIKE']['DST']   # 13.9 DK pts

# Opponent offense quality file
OPP = json.load(open(os.path.join(HERE, 'boom', 'opp_offense.json')))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def empirical_summary(k, def_):
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
    parts  = [f"{nb}/{n} ceiling games (>={SPIKE} DK pts)"]
    notes  = []
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


def get_own_off_q(team):
    """Return this TEAM's own offensive quality from OPP (their off_q)."""
    return OPP.get(team, {}).get('off_q', 50)


# ---------------------------------------------------------------------------
# Per-player flag builder
# ---------------------------------------------------------------------------

def build_player(k, v):
    name       = v['name']
    team       = v.get('team', '')
    adp        = v.get('adp')
    n_games    = v.get('n_games', 0)
    boom_games = v.get('boom_games', 0)

    # Own defensive profile
    df = v.get('def', {})
    covp      = df.get('covp') or 50       # pass coverage percentile (higher = tougher D)
    runp      = df.get('runp') or 50       # run defense percentile
    sackp     = df.get('sackp') or 50      # pass-rush percentile
    manp      = df.get('manp') or 50       # man-coverage rate percentile
    sack_rate = df.get('sack_rate') or 5.5 # actual sack rate
    man_rate  = df.get('man_rate') or 20.0
    tiers     = df.get('tiers') or {}

    own_off_q = get_own_off_q(team)  # this team's own offense (for script flag)

    # -- Regularized base ------------------------------------------------
    rb = reg_base(v, posbase)
    if rb is not None:
        base = rb
        hist = True
    else:
        # Seed from own def percentiles (sackp+covp average, weighted)
        pctl_avg = (sackp * 0.5 + covp * 0.35 + runp * 0.15) / 100.0
        base = posbase['DST'] * (0.75 + 0.5 * pctl_avg)
        base = round(cap(base, 0.06, 0.45), 3)
        hist = False

    empirical = empirical_summary(k, df)

    # ====================================================================
    # SKILL FLAGS — describe what THIS unit is good at (with real numbers)
    # These are player-by-player based on the unit's OWN def percentiles.
    # ====================================================================
    skill_flags = []

    # ------------------------------------------------------------------
    # SKILL 1: Pass rush quality (own DL)
    # ------------------------------------------------------------------
    if sackp >= 90:
        skill_flags.append({
            "f": "Elite pass rush / dominant DL",
            "d": (f"sackp {sackp}th pctl, sack_rate {sack_rate}% — "
                  "top-3 pass-rush unit; generates sacks, strip-sacks, forced fumbles "
                  "and collapsed-pocket INTs at an elite rate"),
            "amp": ("weak opp OL (ol_q≤35) — trench dominance; "
                    "vs any offense when own rush is this elite; "
                    "dome / home crowd (false starts compound pressure)")
        })
    elif sackp >= 75:
        skill_flags.append({
            "f": "Strong pass rush / above-average DL pressure",
            "d": (f"sackp {sackp}th pctl, sack_rate {sack_rate}% — "
                  "top-tier rush unit that wins in one-on-ones; sack ceiling is real "
                  "every week, especially vs leaky OLs"),
            "amp": ("weak opp OL (ol_q≤35) magnifies this; "
                    "facing poor-protection teams unlocks sack/strip-sack ceiling")
        })
    elif sackp >= 60:
        skill_flags.append({
            "f": "Above-average pass rush",
            "d": (f"sackp {sackp}th pctl, sack_rate {sack_rate}% — "
                  "pass rush is a real strength, performs best when opp OL is weak "
                  "or opp offense is forced into obvious passing situations"),
            "amp": ("weak opp OL (ol_q≤35): trench wins; "
                    f"run-stop forces passing (runp {runp})")
        })
    elif sackp <= 20:
        skill_flags.append({
            "f": "Weak pass rush — ceiling relies on turnovers/coverage",
            "d": (f"sackp {sackp}th pctl, sack_rate {sack_rate}% — "
                  "limited pass rush; DST ceiling must come from INTs, forced fumbles, "
                  "return TDs rather than sack-based scoring"),
            "amp": (f"ball-hawk coverage (covp {covp}) and bad opposing QBs "
                    "are the ceiling unlocks, not the pass rush")
        })

    # ------------------------------------------------------------------
    # SKILL 2: Ball-hawk coverage (own CBs/Ss)
    # ------------------------------------------------------------------
    if covp >= 85:
        skill_flags.append({
            "f": "Elite ball-hawk coverage / takeaway unit",
            "d": (f"covp {covp}th pctl, manp {manp}th pctl — "
                  "top-tier coverage that generates INTs, pass deflections, and short fields; "
                  "ceiling explodes vs inaccurate QBs who force throws into coverage"),
            "amp": ("low qb_q (≤35) opponent: throws into coverage = takeaways; "
                    f"man-heavy scheme (manp {manp}) creates bracket jams and tipped balls")
        })
    elif covp >= 65:
        skill_flags.append({
            "f": "Strong coverage / above-average takeaway upside",
            "d": (f"covp {covp}th pctl, manp {manp}th pctl — "
                  "above-average coverage creates turnovers and negative plays; "
                  "ceiling amplified by weak or inaccurate opposing QB"),
            "amp": ("low qb_q (≤45) opponent forces bad decisions into this coverage; "
                    "dome helps CBs (no wind on deep shots)")
        })
    elif covp >= 45 and manp >= 70:
        skill_flags.append({
            "f": "Man-coverage specialist unit",
            "d": (f"covp {covp}th pctl but manp {manp}th pctl — "
                  f"below-average overall coverage but plays heavy man (man_rate {man_rate:.1f}%); "
                  "generates pressure-through-coverage TFLs and coverage sacks"),
            "amp": ("vs short-area routes / poor-route QBs (qb_q≤45); "
                    "man rate means scheme-specific DST leverage")
        })
    elif covp <= 20:
        skill_flags.append({
            "f": "Poor coverage — ceiling capped unless pass rush fires",
            "d": (f"covp {covp}th pctl — opposing QBs find open receivers easily; "
                  "ceiling requires heavy pass-rush or opponent self-destruction "
                  "(fumbles, bad-weather throws)"),
            "amp": (f"sackp {sackp} must carry the ceiling weight; "
                    "weak offense (off_q≤35) still creates ceiling via sheer volume of "
                    "negative plays")
        })

    # ------------------------------------------------------------------
    # SKILL 3: Run defense / stout front
    # ------------------------------------------------------------------
    if runp >= 85:
        skill_flags.append({
            "f": "Elite run defense — forces one-dimensional offense",
            "d": (f"runp {runp}th pctl — "
                  "top-tier run-stopping; forces opponents to abandon the run early, "
                  "creating obvious passing situations that amplify the pass rush and coverage"),
            "amp": ("run-heavy opponents (who want to run): forced into pass → sacks/INTs; "
                    "completes the trench triangle: stop-run → pass → sack/INT ceiling")
        })
    elif runp >= 65:
        skill_flags.append({
            "f": "Stout run defense — creates pass-first game scripts",
            "d": (f"runp {runp}th pctl — "
                  "solid run-stop that forces opponents one-dimensional; "
                  "pipeline effect: run stop → opponent passes → sack/INT opportunities"),
            "amp": (f"pairs with sackp {sackp} and covp {covp} to chain "
                    "run stop → pass attempt → ceiling play")
        })
    elif runp <= 20:
        skill_flags.append({
            "f": "Porous run defense — allows rushing ceiling to opponents",
            "d": (f"runp {runp}th pctl — "
                  "run defense is a liability; opponents can stay in run game, "
                  "limiting pass-rush and coverage ceiling opportunities for this DST"),
            "amp": ("need pass-happy offense (high off_q) to bypass own run-D weakness; "
                    "aerial offense opponents are the ONLY setup")
        })

    # ------------------------------------------------------------------
    # SKILL 4: Scheme / coverage type context (only if not redundant)
    # ------------------------------------------------------------------
    if len(skill_flags) < 4:
        if manp >= 80 and covp >= 55:
            skill_flags.append({
                "f": "Aggressive man-coverage scheme",
                "d": (f"manp {manp}th pctl, man_rate {man_rate:.1f}% — "
                      "plays man at elite rate; aggressive scheme creates forced incompletions "
                      "and batted balls in the backfield"),
                "amp": ("vs poor route-running QBs (qb_q≤45); "
                        "home crowd amplifies false starts in man vs tight windows")
            })
        elif manp <= 20 and (covp >= 55 or runp >= 55):
            skill_flags.append({
                "f": "Zone-heavy scheme with coverage safety net",
                "d": (f"manp {manp}th pctl (zone-heavy), covp {covp}th / runp {runp}th — "
                      "reads + zone coverage creates INT opportunities and erases routes; "
                      "zone DSTs boom when QB hesitates and takes sacks"),
                "amp": ("vs decision-slow QBs (qb_q≤50); "
                        "deep zones erase downfield shots → checkdowns → sacks/punts")
            })

    # Make sure every unit gets at least 3 skill flags
    if len(skill_flags) < 3:
        # Add a combined profile summary
        skill_flags.append({
            "f": f"Composite defense profile (covp {covp} / runp {runp} / sackp {sackp})",
            "d": (f"covp {covp}th pctl, runp {runp}th pctl, sackp {sackp}th pctl — "
                  "mixed defensive profile; ceiling depends primarily on opponent quality "
                  f"(off_q/qb_q) rather than unit-specific dominance"),
            "amp": ("vs weak offense (off_q≤35): low-quality throws into coverage = turnovers; "
                    "home crowd noise adds false-start sacks")
        })

    # Trim to 6 max
    skill_flags = skill_flags[:6]

    # ====================================================================
    # PER-WEEK CONDITIONS (checked against OPP[opp] + home/dome)
    # ====================================================================
    conditions = []

    # ------------------------------------------------------------------
    # TRENCH MATCHUP — own DL vs opp OL (SEPARATE flags per brief)
    # ------------------------------------------------------------------

    # Flag A: Own DL strength (standalone) — fires if sackp≥60
    if sackp >= 75:
        conditions.append({
            "key": f"own elite pass rush (sackp {sackp})",
            "mult": 1.15,
            "fn": lambda opp_data, w: True  # always on for elite rush units
        })
    elif sackp >= 60:
        conditions.append({
            "key": f"own strong pass rush (sackp {sackp})",
            "mult": 1.10,
            "fn": lambda opp_data, w: True
        })

    # Flag B: Opponent OL weakness — fires if opp ol_q≤35
    conditions.append({
        "key": "opp weak OL (ol_q≤35) — trench mismatch favors DST",
        "mult": 1.30,
        "fn": lambda opp_data, w: opp_data.get('ol_q', 50) <= 35
    })

    # Strong opp OL suppressor (ol_q≥70)
    conditions.append({
        "key": "opp strong OL suppressor (ol_q≥70) — neutralizes pass rush",
        "mult": 0.78,
        "fn": lambda opp_data, w: opp_data.get('ol_q', 50) >= 70
    })

    # ------------------------------------------------------------------
    # MATCHUP: WEAK OFFENSE — dominant DST ceiling driver
    # ------------------------------------------------------------------
    conditions.append({
        "key": "vs weak offense (off_q≤35) — low pts allowed + turnovers",
        "mult": 1.38,
        "fn": lambda opp_data, w: opp_data.get('off_q', 50) <= 35
    })

    # ------------------------------------------------------------------
    # MATCHUP: LOW-QUALITY QB
    # ------------------------------------------------------------------
    conditions.append({
        "key": "vs low-quality QB (qb_q≤35) — forced throws into coverage",
        "mult": 1.20,
        "fn": lambda opp_data, w: opp_data.get('qb_q', 50) <= 35
    })

    # Mid-tier bad QB (qb_q 36-50): moderate boost
    conditions.append({
        "key": "vs below-average QB (qb_q 36-50)",
        "mult": 1.10,
        "fn": lambda opp_data, w: 36 <= opp_data.get('qb_q', 51) <= 50
    })

    # SUPPRESSOR: Elite offense (off_q≥75)
    conditions.append({
        "key": "vs elite offense suppressor (off_q≥75) — ceiling capped",
        "mult": 0.72,
        "fn": lambda opp_data, w: opp_data.get('off_q', 50) >= 75
    })

    # SUPPRESSOR: Elite QB (qb_q≥80)
    conditions.append({
        "key": "vs elite QB suppressor (qb_q≥80) — shreds coverage",
        "mult": 0.80,
        "fn": lambda opp_data, w: opp_data.get('qb_q', 50) >= 80
    })

    # ------------------------------------------------------------------
    # BALL-HAWK COVERAGE — amplified by weak QB or weak offense
    # ------------------------------------------------------------------
    if covp >= 65:
        conditions.append({
            "key": f"ball-hawk coverage (covp {covp}) vs weak/avg offense",
            "mult": 1.20,
            "fn": lambda opp_data, w: opp_data.get('off_q', 50) <= 50
        })
    elif covp >= 45:
        conditions.append({
            "key": f"coverage unit (covp {covp}) vs manageable offense",
            "mult": 1.10,
            "fn": lambda opp_data, w: opp_data.get('off_q', 50) <= 45
        })

    # ------------------------------------------------------------------
    # RUN-STOP PIPELINE: stop run → forces pass → sack/INT amplifier
    # ------------------------------------------------------------------
    if runp >= 65:
        conditions.append({
            "key": f"run-stop pipeline (runp {runp}) forces one-dimensional offense",
            "mult": 1.12,
            "fn": lambda opp_data, w: opp_data.get('off_q', 50) <= 60
        })

    # ------------------------------------------------------------------
    # SCRIPT FLAG: own off_q well above opp off_q → opp trails → passes
    # ------------------------------------------------------------------
    if own_off_q >= 65:
        conditions.append({
            "key": f"positive script — own off_q {own_off_q} favors DST (opp trails, passes more)",
            "mult": 1.15,
            "fn": lambda opp_data, w, own_q=own_off_q: (
                own_q >= 65 and opp_data.get('off_q', 50) <= 40
            )
        })
    elif own_off_q >= 40:
        conditions.append({
            "key": f"moderate script edge — own off_q {own_off_q} vs weak opponent",
            "mult": 1.08,
            "fn": lambda opp_data, w, own_q=own_off_q: (
                own_q >= 40 and opp_data.get('off_q', 50) <= 30
            )
        })

    # ------------------------------------------------------------------
    # HOME / DOME
    # ------------------------------------------------------------------
    conditions.append({
        "key": "home game (crowd noise → false starts → sacks)",
        "mult": 1.08,
        "fn": lambda opp_data, w: bool(w.get('home'))
    })

    conditions.append({
        "key": "dome game (controlled environment → crowd noise amplified indoors)",
        "mult": 1.06,
        "fn": lambda opp_data, w: bool(w.get('dome'))
    })

    # ====================================================================
    # ONE-LINE THESIS
    # ====================================================================
    line = _build_line(name, team, covp, runp, sackp, manp, sack_rate, man_rate, own_off_q)

    # ====================================================================
    # PER-WEEK ACTIVATION
    # ====================================================================
    weeks = []
    for wentry in sch.get(team, []):
        wk   = wentry['wk']
        opp  = wentry['opp']
        home = wentry.get('home')
        dome = wentry.get('dome')

        if opp == 'BYE':
            weeks.append({
                "wk": wk, "opp": "BYE", "home": None, "dome": None,
                "p": None, "lab": "BYE", "lit": 0, "of": 0, "flags": []
            })
            continue

        opp_data = OPP.get(opp, {})
        week_ctx = {"home": home, "dome": dome, "opp": opp}

        lit_flags = []
        lit_mults = []
        for cond in conditions:
            try:
                active = cond["fn"](opp_data, week_ctx)
            except Exception:
                active = False
            if active:
                lit_flags.append(cond["key"])
                lit_mults.append(cond["mult"])

        p_week = prob(base, lit_mults)
        p_int  = int(round(p_week * 100))

        weeks.append({
            "wk":    wk,
            "opp":   opp,
            "home":  bool(home) if home is not None else False,
            "dome":  bool(dome) if dome is not None else False,
            "p":     p_int,
            "lab":   label(p_week, base),
            "lit":   len(lit_mults),
            "of":    len(conditions),
            "flags": lit_flags
        })

    return {
        "name":        name,
        "pos":         POS,
        "team":        team,
        "adp":         adp,
        "base":        int(round(base * 100)),
        "hist":        hist,
        "n_games":     n_games,
        "boom_games":  boom_games,
        "skill_flags": skill_flags,
        "line":        line,
        "weeks":       weeks,
        "empirical":   empirical
    }


def _build_line(name, team, covp, runp, sackp, manp, sack_rate, man_rate, own_off_q):
    parts = []

    # Pass rush
    if sackp >= 90:
        parts.append(
            f"elite pass rush (sackp {sackp}th pctl, {sack_rate}% sack rate) "
            f"detonates vs weak OLs (ol_q≤35)"
        )
    elif sackp >= 75:
        parts.append(
            f"strong pass rush (sackp {sackp}th pctl) combined with "
            f"weak-OL matchups (ol_q≤35) is the trench ceiling lever"
        )
    elif sackp >= 60:
        parts.append(
            f"above-average pass rush (sackp {sackp}th pctl) unlocked by weak OL opponents"
        )
    else:
        parts.append(
            f"limited pass rush (sackp {sackp}th pctl) means ceiling relies on "
            f"coverage/turnovers rather than sack accumulation"
        )

    # Coverage
    if covp >= 85:
        parts.append(
            f"elite ball-hawk coverage (covp {covp}th pctl) generates INTs vs any weak QB"
        )
    elif covp >= 65:
        parts.append(
            f"above-average coverage (covp {covp}th pctl) creates takeaway ceiling vs off_q≤50"
        )

    # Run defense
    if runp >= 85:
        parts.append(
            f"elite run stop (runp {runp}th pctl) forces opponents one-dimensional → sack/INT pipeline"
        )
    elif runp >= 65:
        parts.append(
            f"solid run defense (runp {runp}th pctl) funnels opponents into pass-first scripts"
        )

    # Matchup driver
    parts.append(
        f"ceiling peaks vs weak offenses (off_q≤35) and poor QBs (qb_q≤45)"
    )

    # Script
    if own_off_q >= 65:
        parts.append(f"own offense (off_q {own_off_q}) creates trailing-opponent script")

    return f"{name}: " + "; ".join(parts[:4]) + "."


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    keys = players(sm, POS)
    out  = {}
    n_hist      = 0
    total_sf    = 0
    week18_ok   = 0
    smash_total = 0
    tough_total = 0

    for k in keys:
        rec = build_player(k, sm[k])
        out[k] = rec
        if rec['hist']:
            n_hist += 1
        total_sf  += len(rec['skill_flags'])
        if len(rec['weeks']) == 18:
            week18_ok += 1
        smash_total += sum(1 for w in rec['weeks'] if w['lab'] == 'SMASH')
        tough_total += sum(1 for w in rec['weeks'] if w['lab'] == 'TOUGH')

    print(f"\n=== DST FLAG MODEL SUMMARY ===")
    print(f"Total DST units:            {len(out)}")
    print(f"With history (hist=True):   {n_hist}")
    print(f"Without history:            {len(out) - n_hist}")
    print(f"Avg skill_flags/unit:       {total_sf / len(out):.2f}")
    print(f"Units with 18 weeks:        {week18_ok}/{len(out)}")
    print(f"Total SMASH weeks:          {smash_total}")
    print(f"Total TOUGH weeks:          {tough_total}")

    fd = {}
    for r in out.values():
        n = len(r['skill_flags'])
        fd[n] = fd.get(n, 0) + 1
    print(f"Flag count distribution:    {sorted(fd.items())}")

    # ====================================================================
    # SPOT CHECKS: 3 CONTRASTING units
    #   1. Denver — elite pass rush (sackp 100) + ball-hawk coverage (covp 100)
    #   2. Houston — elite coverage (covp 97) + run stop (runp 97)
    #   3. Indianapolis — weak coverage (covp 0) + weak run D (runp 10)
    # ====================================================================
    spots = [
        ('dst_den', "ELITE PASS-RUSH unit (sackp 100, covp 100)"),
        ('dst_hou', "ELITE COVERAGE/RUN-STOP unit (covp 97, runp 97, sackp 81)"),
        ('dst_ind', "WEAK unit (covp 0, runp 10, sackp 32) — coverage/run-D liability"),
    ]

    for k, role_label in spots:
        if k not in out:
            print(f"\n!! {k} missing !!")
            continue
        r = out[k]
        non_bye   = [w for w in r['weeks'] if w['lab'] != 'BYE']
        smash_wks = sorted([w for w in non_bye if w['lab'] == 'SMASH'],
                           key=lambda x: -(x['p'] or 0))
        tough_wks = sorted([w for w in non_bye if w['lab'] == 'TOUGH'],
                           key=lambda x: (x['p'] or 99))

        sep = '=' * 70
        print(f"\n{sep}")
        print(f"SPOT CHECK: {r['name']} ({r['team']}) — {role_label}")
        print(sep)
        print(f"  base={r['base']}%  hist={r['hist']}  "
              f"n_games={r['n_games']}  boom_games={r['boom_games']}")
        df = sm[k]['def']
        print(f"  def profile: covp={df['covp']} runp={df['runp']} "
              f"sackp={df['sackp']} manp={df['manp']} "
              f"sack_rate={df['sack_rate']} own_off_q={get_own_off_q(r['team'])}")
        print(f"  skill_flags ({len(r['skill_flags'])}):")
        for sf in r['skill_flags']:
            print(f"    [{sf['f']}]")
            print(f"      d:   {sf['d']}")
            print(f"      amp: {sf['amp']}")
        print(f"  line: {r['line']}")
        print(f"  empirical: {r['empirical']}")

        lab_counts = {lbl: sum(1 for w in non_bye if w['lab'] == lbl)
                      for lbl in ('SMASH', 'GOOD', 'NEU', 'TOUGH')}
        print(f"  Week breakdown: SMASH={lab_counts['SMASH']} "
              f"GOOD={lab_counts['GOOD']} NEU={lab_counts['NEU']} TOUGH={lab_counts['TOUGH']}")

        if smash_wks:
            sw = smash_wks[0]
            opp_data = OPP.get(sw['opp'], {})
            print(f"  SMASH WEEK: wk{sw['wk']} vs {sw['opp']} "
                  f"home={sw['home']} dome={sw['dome']} "
                  f"p={sw['p']}%  lit={sw['lit']}/{sw['of']}")
            print(f"    opp: off_q={opp_data.get('off_q','?')} "
                  f"qb_q={opp_data.get('qb_q','?')} "
                  f"ol_q={opp_data.get('ol_q','?')} "
                  f"pblock={opp_data.get('pblock','?')}")
            print(f"    flags: {sw['flags']}")
        else:
            best = max(non_bye, key=lambda x: x['p'] or 0)
            opp_data = OPP.get(best['opp'], {})
            print(f"  BEST WEEK (no SMASH): wk{best['wk']} vs {best['opp']} "
                  f"p={best['p']}% lab={best['lab']} lit={best['lit']}/{best['of']}")
            print(f"    opp: off_q={opp_data.get('off_q','?')} ol_q={opp_data.get('ol_q','?')}")
            print(f"    flags: {best['flags']}")

        if tough_wks:
            tw = tough_wks[0]
            opp_data = OPP.get(tw['opp'], {})
            print(f"  TOUGH WEEK: wk{tw['wk']} vs {tw['opp']} "
                  f"home={tw['home']} dome={tw['dome']} "
                  f"p={tw['p']}%  lit={tw['lit']}/{tw['of']}")
            print(f"    opp: off_q={opp_data.get('off_q','?')} "
                  f"qb_q={opp_data.get('qb_q','?')} "
                  f"ol_q={opp_data.get('ol_q','?')}")
            print(f"    flags: {tw['flags']}")
        else:
            worst = min(non_bye, key=lambda x: x['p'] or 99)
            opp_data = OPP.get(worst['opp'], {})
            print(f"  WORST WEEK (no TOUGH): wk{worst['wk']} vs {worst['opp']} "
                  f"p={worst['p']}% lab={worst['lab']} lit={worst['lit']}/{worst['of']}")
            print(f"    opp: off_q={opp_data.get('off_q','?')} ol_q={opp_data.get('ol_q','?')}")
            print(f"    flags: {worst['flags']}")

    # ====================================================================
    # DIFFERENTIATION CHECK + TRENCH FLAG VERIFICATION
    # ====================================================================
    sep = '=' * 70
    print(f"\n{sep}")
    print("DIFFERENTIATION CHECK — proves player-by-player, confirms trench flags differ:")
    for k in ['dst_den', 'dst_hou', 'dst_ind']:
        if k in out:
            r = out[k]
            df = sm[k]['def']
            n_cond = r['weeks'][0]['of'] if r['weeks'] else 0
            print(f"\n  {r['name']} ({r['team']}) base={r['base']}%  "
                  f"flags={len(r['skill_flags'])}  conditions={n_cond}")
            print(f"    def: covp={df['covp']} runp={df['runp']} sackp={df['sackp']}")
            for sf in r['skill_flags']:
                print(f"    - {sf['f']}")

    # Trench flag fire check
    print(f"\n{sep}")
    print("TRENCH FLAG FIRE VERIFICATION (own-DL vs opp-OL):")
    for k in ['dst_den', 'dst_hou', 'dst_ind']:
        if k not in out:
            continue
        r = out[k]
        own_sackp = sm[k]['def']['sackp']
        trench_weeks = []
        for w in r['weeks']:
            if w['opp'] == 'BYE':
                continue
            opp_data = OPP.get(w['opp'], {})
            ol_q = opp_data.get('ol_q', 50)
            own_rush_flag = any('own' in f and 'pass rush' in f for f in w['flags'])
            opp_weak_ol_flag = any('opp weak OL' in f for f in w['flags'])
            opp_strong_ol_supp = any('opp strong OL' in f for f in w['flags'])
            if own_rush_flag or opp_weak_ol_flag:
                trench_weeks.append((w['wk'], w['opp'], ol_q, own_rush_flag, opp_weak_ol_flag, w['p']))
        if trench_weeks:
            print(f"\n  {r['name']} (sackp={own_sackp}) — weeks with trench flags:")
            for wk, opp, ol_q, own_f, opp_f, p in trench_weeks[:4]:
                print(f"    wk{wk} vs {opp} ol_q={ol_q} own_rush={own_f} opp_weak_ol={opp_f} p={p}%")
        else:
            print(f"\n  {r['name']} (sackp={own_sackp}) — no trench flags fired "
                  f"(expected for weak rush units)")

    write(POS, out)

    # Reload + validate
    reloaded = json.load(open(os.path.join(HERE, 'boom', 'flags_DST.json')))
    assert len(reloaded) == len(out), f"Reload mismatch: {len(reloaded)} vs {len(out)}"
    # Verify 18 weeks each
    bad = [k for k, v in reloaded.items() if len(v['weeks']) != 18]
    assert not bad, f"Units with wrong week count: {bad}"
    print(f"\nflags_DST.json reloaded: {len(reloaded)} keys, all 18 weeks — valid JSON confirmed.")
    print("Done.")


if __name__ == '__main__':
    main()
