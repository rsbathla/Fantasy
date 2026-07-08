#!/usr/bin/env python3
"""build_sis_personnel.py — SIS offensive personnel usage per team, cross-checked against FantasyPoints.

Gives personnel a SECOND independent source, mirroring what NFL Pro does for alignment. SIS (Sports
Info Solutions) charts offensive personnel; pull it via your existing SIS console flow (SIS_PULLER.md)
with the personnel dimension, then this aggregates it to per-team heavy-rate + mix and DIFFS it against
fp_personnel.json — flagging any team where the two vendors disagree on how heavy an offense plays.

PULL (your authenticated SIS DataHub session — see SIS_PERSONNEL_PULL.md):
  in sis_pull.js, override PersonnelFilters to each grouping (or pull the personnel report), and save
  the rows to:  NFL-master/SIS/personnel_2025.json   (a list of rows; or .csv)
  Each row should carry a TEAM, a PERSONNEL grouping (11/12/13/21…), and a volume count
  (plays / snaps / routes / dropbacks). Wide format (team + pct-per-grouping columns) also works via
  --wide.

  python3 build_sis_personnel.py --sis NFL-master/SIS/personnel_2025.json
  python3 build_sis_personnel.py --sis <file> --team-col Team --grouping-col Personnel --count-col Plays
"""
import argparse, csv, json, os
from collections import defaultdict

def num(x):
    try: return float(str(x).replace("%", "").replace(",", "").strip())
    except Exception: return None

def teamab(t):
    t = str(t).strip().upper()
    return {"JAC": "JAX", "LA": "LAR", "WSH": "WAS", "ARZ": "ARI", "GNB": "GB", "KAN": "KC", "SFO": "SF",
            "TAM": "TB", "NWE": "NE", "NOR": "NO", "BLT": "BAL", "CLV": "CLE", "HST": "HOU"}.get(t, t)

def load_rows(path):
    if path.endswith(".json"):
        d = json.load(open(path))
        if isinstance(d, list):
            return d
        for v in d.values():                       # find the row list inside a wrapper object
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return v
        raise SystemExit("!! couldn't find a row list in the SIS json (expected a list of team/player rows)")
    return list(csv.DictReader(open(path)))

def pick(cols, *kw):
    for c in cols:
        cl = c.lower()
        if all(w in cl for w in kw):
            return c
    return None

GROUPINGS = ("11", "12", "13", "10", "21", "22", "23", "20", "01", "02", "00", "14", "31", "32")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sis", default="NFL-master/SIS/personnel_2025.json")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--team-col", default=None)
    ap.add_argument("--grouping-col", default=None)
    ap.add_argument("--count-col", default=None)
    ap.add_argument("--wide", action="store_true", help="one row/team with a % column per grouping")
    ap.add_argument("--out", default="sis_personnel.json")
    ap.add_argument("--diverge", type=float, default=8.0, help="heavy-rate gap (pts) that flags a DIVERGE")
    a = ap.parse_args()

    path = os.path.join(a.repo, a.sis)
    if not os.path.exists(path):
        print(f"!! no SIS file at {path}\n   Pull it first (SIS_PERSONNEL_PULL.md), save rows there, re-run.")
        return 1
    rows = load_rows(path)
    if not rows:
        print("!! SIS file has no rows"); return 1
    cols = list(rows[0].keys())

    team_totals = defaultdict(lambda: defaultdict(float))     # team -> grouping -> volume
    if a.wide:
        tcol = a.team_col or pick(cols, "team") or pick(cols, "offense")
        gcols = [c for c in cols if any(g == "".join(ch for ch in c if ch.isdigit()) for g in GROUPINGS)]
        if not tcol or not gcols:
            print("!! --wide: couldn't find a team column + per-grouping % columns. Columns present:")
            [print("   ", c) for c in cols]; return 1
        for r in rows:
            t = teamab(r.get(tcol, ""))
            for c in gcols:
                g = "".join(ch for ch in c if ch.isdigit())
                v = num(r.get(c))
                if t and g and v is not None:
                    team_totals[t][g] += v
    else:
        tcol = a.team_col or pick(cols, "team") or pick(cols, "offense")
        gcol = a.grouping_col or pick(cols, "personnel") or pick(cols, "grouping") or pick(cols, "package")
        ccol = (a.count_col or pick(cols, "plays") or pick(cols, "snaps") or pick(cols, "routes")
                or pick(cols, "dropback") or pick(cols, "attempts") or pick(cols, "att"))
        if not (tcol and gcol and ccol):
            print("!! couldn't auto-detect team / grouping / count columns. Columns present:")
            [print("   ", c) for c in cols]
            print(f"\n   detected: team={tcol}  grouping={gcol}  count={ccol}")
            print("   pass --team-col / --grouping-col / --count-col (or --wide for team×grouping% columns).")
            return 1
        for r in rows:
            t = teamab(r.get(tcol, "")); g = str(r.get(gcol, "")).strip(); c = num(r.get(ccol)) or 0
            if t and g and c > 0:
                team_totals[t][g] += c

    teams = {}
    for t, gg in team_totals.items():
        tot = sum(gg.values())
        if tot <= 0: continue
        mix = {g: round(v / tot, 3) for g, v in sorted(gg.items(), key=lambda x: -x[1])}
        heavy = round(sum(v for g, v in gg.items() if g != "11") / tot, 3)
        teams[t] = {"heavy_rate": round(heavy * 100, 1), "personnel_mix": mix}

    # cross-check vs FP (fp_personnel.json heavy_rate is a 0-1 fraction)
    fp_path = os.path.join(a.repo, "fp_personnel.json")
    compare, n_agree, n_div = [], 0, 0
    if os.path.exists(fp_path) and teams:
        fp = json.load(open(fp_path)).get("teams", {})
        for t, rec in sorted(teams.items()):
            f = fp.get(t)
            if not f:
                rec["fp_xcheck"] = "no FP team"; continue
            fp_heavy = round(f.get("heavy_rate", 0) * 100, 1)
            gap = round(abs(rec["heavy_rate"] - fp_heavy), 1)
            diverge = gap > a.diverge
            rec["fp_heavy_rate"] = fp_heavy; rec["gap_vs_fp"] = gap
            rec["fp_xcheck"] = "DIVERGE" if diverge else "agree"
            n_div += diverge; n_agree += (not diverge)
            compare.append((t, rec["heavy_rate"], fp_heavy, gap, rec["fp_xcheck"]))

    doc = {"_meta": {"source": "SIS DataHub — offensive personnel", "vs": "fp_personnel.json heavy_rate",
                     "diverge_threshold_pts": a.diverge, "agree": n_agree, "diverge": n_div},
           "teams": teams}
    json.dump(doc, open(os.path.join(a.repo, a.out), "w"), ensure_ascii=False, indent=0)
    print(f"wrote {a.out}: {len(teams)} teams · vs FP: {n_agree} agree · {n_div} DIVERGE (>{a.diverge}pt heavy-rate gap)")
    for t, sis_h, fp_h, gap, verdict in sorted(compare, key=lambda x: -x[3])[:12]:
        print(f"  {t:4} SIS heavy {sis_h:5.1f}% · FP {fp_h:5.1f}% · gap {gap:4.1f} · {verdict}")
    return 0

if __name__ == "__main__":
    main()
