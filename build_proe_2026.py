#!/usr/bin/env python3
"""
build_proe_2026.py — per-team 2026 PROE (Pass Rate Over Expected) TENDENCY, the input
to the DFS pass/run conversion multiplier (dfs_model.proe_convert).

    proe_2026  =  proe_2025_actual  +  carousel_adj

proe_2025_actual : VERIFIED 2025 season PROE (FantasyPoints), from
                   data/fantasypoints/proe_offense_2025.csv. A completed season = GROUND TRUTH,
                   not a projection.
carousel_adj     : a MODELED ASSUMPTION. Applied only where COACHING_CHANGES_2026.md documents a
                   DIRECTIONAL off-lean shift (e.g. RUN->PASS). Small, bounded, directional, flagged.
                   No coaching change, or a single-state lean with no arrow => adj = 0 (2025 retained).

The base (fact) and the adjustment (assumption) are stored in SEPARATE fields so proe_2026 is
never mistaken for a posted/known number.

CONCEPT CAVEAT (documented, not hidden): the carousel "off-lean" labels describe a team's RAW
run/pass identity; PROE is pass-over-EXPECTED (situation-adjusted). They correlate but are not the
same unit (ARI is a run-identity offense yet led the NFL in PROE). That is exactly why the carousel
enters only as a GENTLE nudge (<=2.5 PROE pts) that cannot overpower the measured 2025 base
(league SD ~3.6). Calibration of the multiplier itself: validate_proe_conversion.py.
"""
import json
import os
import re
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PROE_CSV = os.path.join(HERE, "data/fantasypoints/proe_offense_2025.csv")
CAROUSEL = os.path.join(HERE, "COACHING_CHANGES_2026.md")
OUT = os.path.join(HERE, "proe_tendency_2026.json")

STEP = 1.0        # PROE points per one-category lean step (BALANCED<->PASS is one step)
ADJ_CAP = 2.5     # |carousel_adj| ceiling — keeps the assumption subordinate to the measured base
LEAN_RANK = {"RUN": -1, "BALANCED": 0, "PASS": 1}


def parse_carousel():
    """team -> (steps|None, raw_lean_text). steps>0 = shift toward PASS; None = no arrow shift."""
    out = {}
    if not os.path.exists(CAROUSEL):
        return out
    for line in open(CAROUSEL):
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 5:
            continue
        m = re.match(r"([A-Z]{2,3})\b", cells[0])
        if not m:
            continue
        team = m.group(1)
        lean = cells[-1].replace("*", "").strip()
        if "→" in lean or "->" in lean:
            arrow = "→" if "→" in lean else "->"
            a, b = [x.strip().upper() for x in lean.split(arrow)]
            if a in LEAN_RANK and b in LEAN_RANK:
                out[team] = (LEAN_RANK[b] - LEAN_RANK[a], lean)
                continue
        out[team] = (None, lean)
    return out


def main():
    proe = pd.read_csv(PROE_CSV).set_index("team")["proe_season"].to_dict()
    car = parse_carousel()
    teams = {}
    for team, base in sorted(proe.items()):
        steps, lean = car.get(team, (None, None))
        if steps:
            adj = max(-ADJ_CAP, min(ADJ_CAP, steps * STEP))
            note = f"carousel off-lean '{lean}' ({steps:+d} step) -> {adj:+.1f} PROE assumed"
            assumed = True
        else:
            adj = 0.0
            assumed = False
            if team in car:
                note = f"new coordinator; lean noted '{lean}', no directional arrow -> 2025 retained"
            else:
                note = "no 2026 coaching change on file -> 2025 tendency retained"
        teams[team] = {
            "proe_2025": round(base, 1),
            "carousel_adj": round(adj, 1),
            "carousel_assumption": assumed,
            "proe_2026": round(base + adj, 1),
            "note": note,
        }

    doc = {
        "_meta": {
            "purpose": "Per-team 2026 PROE tendency = 2025 ACTUAL PROE + bounded directional carousel "
                       "assumption. Feeds dfs_model.proe_convert (pass-catchers UP / RBs DOWN as team "
                       "PROE rises), calibrated by validate_proe_conversion.py.",
            "base_provenance": "data/fantasypoints/proe_offense_2025.csv — VERIFIED 2025 actual (ground truth).",
            "carousel_provenance": f"COACHING_CHANGES_2026.md off-lean column (verified coaching facts). The "
                                   f"numeric PROE delta is a MODELED ASSUMPTION: STEP={STEP} pt/step, cap +-{ADJ_CAP}.",
            "concept_caveat": "off-lean labels are RAW run/pass identity; PROE is pass-over-EXPECTED. Correlated, "
                              "not identical — hence the carousel is a gentle nudge only, kept subordinate to the "
                              "measured 2025 base (league SD ~3.6).",
            "warning": "proe_2026 is NOT a fact. proe_2025 is actual; carousel_adj is an assumption. Never present "
                       "proe_2026 as a posted/known number.",
            "built_from": ["data/fantasypoints/proe_offense_2025.csv", "COACHING_CHANGES_2026.md"],
        },
        "teams": teams,
    }
    json.dump(doc, open(OUT, "w"), indent=2)

    # console summary — biggest assumed shifts first
    rows = sorted(teams.items(), key=lambda kv: -abs(kv[1]["carousel_adj"]))
    print(f"wrote {OUT}  ({len(teams)} teams)")
    print(f"{'tm':4s} {'2025':>6s} {'adj':>5s} {'2026':>6s}  note")
    for t, d in rows:
        flag = "*" if d["carousel_assumption"] else " "
        print(f"{t:4s} {d['proe_2025']:>6.1f} {d['carousel_adj']:>+5.1f} {d['proe_2026']:>6.1f} {flag} {d['note']}")


if __name__ == "__main__":
    main()
