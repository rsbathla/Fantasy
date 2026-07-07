#!/usr/bin/env python3
"""build_fp_personnel.py — FantasyPoints PERSONNEL groupings, per player and per team.

Personnel (11 / 12 / 13 / 21 / 22 ...) is a documented FantasyPoints dimension that is AVAILABLE
BUT NOT YET PULLED (see FP_SWEEP_CATALOG.md §5). You run the authenticated pull (bearer token never
leaves your box); this consumer turns it into signal:

  PULL (FantasyPoints Data Suite -> Receiving -> filter dimension = Personnel -> export each value):
     -> NFL-master/FP_SWEEP/2025/Receiving/personnel/11.csv  (and 12, 13, 21, 22 ...)
     same one-row-per-player schema as every other FP receiving sweep file.

Then per PLAYER: route share by personnel grouping (who is on the field in heavy sets — the real
version of the ARI 12-personnel discovery, for every team). Per TEAM: personnel usage rate (what %
of routes the offense runs in each grouping). This UPGRADES personnel_2026.json from v1 (team
heavy-rate from a third-party table + vault direction) to FP-charted per-player + per-team personnel.

  python3 build_fp_personnel.py                         # reads Receiving/personnel/*.csv, writes fp_personnel.json + upgrades personnel_2026.json
  python3 build_fp_personnel.py --dir <folder> --dry-run
"""
import argparse, csv, glob, json, os, re
from collections import defaultdict

def fn(n):
    n = str(n).strip().lower(); n = re.sub(r"\s+(jr|sr|ii|iii|iv|v)\.?$", "", n)
    return n.replace(".", "").replace("'", "").replace("-", " ").strip()
def num(x):
    try: return float(str(x).replace("%", "").strip())
    except Exception: return None

def read_rows(path):
    """Read an FP Data Suite export. Handles both the legacy single-header schema and the
    2026 grid export: an extra group-header row ("Player Details","","",...) above the real
    header, and DUPLICATE column names (grid repeats e.g. "Team"/"RTE" in later display
    groups) — first occurrence wins, which is always the Player Details / Receiving column."""
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            raw = list(csv.reader(f))
    except Exception as e:
        print(f"!! unreadable {os.path.basename(path)}: {e}"); return []
    if not raw: return []
    hi = 0
    if "Name" not in raw[0]:   # group-header row on top — real header is the next row
        hi = 1
    if hi >= len(raw) or "Name" not in raw[hi]:
        print(f"!! {os.path.basename(path)}: no 'Name' header found — skipped"); return []
    idx = {}
    for j, h in enumerate(raw[hi]):
        idx.setdefault(h.strip(), j)                  # first occurrence wins
    return [{h: (r[j] if j < len(r) else "") for h, j in idx.items()}
            for r in raw[hi + 1:] if any(c.strip() for c in r)]

# team-name -> abbr (FP uses abbreviations already in most exports; map the few long forms)
def teamab(t):
    t = str(t).strip().upper()
    return {"JAC": "JAX", "LA": "LAR", "WSH": "WAS", "ARZ": "ARI", "GNB": "GB", "KAN": "KC",
            "SFO": "SF", "TAM": "TB", "NWE": "NE", "NOR": "NO",
            "BLT": "BAL", "CLV": "CLE", "HST": "HOU"}.get(t, t)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="NFL-master/FP_SWEEP/2025/Receiving/personnel")
    ap.add_argument("--repo", default="."); ap.add_argument("--out", default="fp_personnel.json")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    d = os.path.join(a.repo, a.dir)
    files = sorted(glob.glob(os.path.join(d, "*.csv")))
    if not files:
        print("!! No personnel files found at", d)
        print("   PULL them first (authenticated, your token): FantasyPoints Data Suite -> Receiving ->")
        print("   dimension = Personnel -> export each value (11,12,13,21,22) to that folder, then re-run.")
        print("   Format = same one-row-per-player as the other FP receiving sweep files.")
        return 1

    per_player = defaultdict(lambda: {"pos": "", "team": "", "by": {}, "tgt": {}, "dk": {}})  # k -> routes/targets/DK FP by grouping
    team_routes = defaultdict(lambda: defaultdict(float))                  # team -> grouping -> routes
    for p in files:
        grouping = os.path.splitext(os.path.basename(p))[0]               # "11", "12", ...
        for r in read_rows(p):
            k = fn(r.get("Name", ""))
            if not k: continue
            rts = num(r.get("RoutesTotal")) or num(r.get("RTE")) or 0     # legacy | 2026 grid export
            if rts <= 0: continue
            tgt = num(r.get("TargetsTotal")) or num(r.get("TGT")) or 0
            # "FP" = fantasy points under the scoring system selected at export time —
            # these files are pulled with Scoring System = DraftKings (see pull note above).
            dk = num(r.get("FP")) or 0
            pp = per_player[k]; pp["pos"] = pp["pos"] or r.get("POS", "")
            # traded players export as "ARZ, DAL" — tag the player with his LAST (most recent)
            # team, but leave him out of team_routes: his routes can't be apportioned per team.
            tms = [t.strip() for t in str(r.get("Team", "")).split(",") if t.strip()]
            pp["team"] = pp["team"] or (teamab(tms[-1]) if tms else "")
            pp["by"][grouping] = pp["by"].get(grouping, 0) + rts
            pp["tgt"][grouping] = pp["tgt"].get(grouping, 0) + tgt
            pp["dk"][grouping] = pp["dk"].get(grouping, 0) + dk
            if len(tms) == 1:
                team_routes[teamab(tms[0])][grouping] += rts

    players = {}
    for k, pp in per_player.items():
        tot = sum(pp["by"].values())
        if tot < 20: continue
        mix = {g: round(v / tot, 3) for g, v in sorted(pp["by"].items(), key=lambda x: -x[1])}
        heavy = round(sum(v for g, v in mix.items() if g not in ("11",)), 3)  # non-11 = heavy sets
        players[k] = {"pos": pp["pos"], "team": pp["team"], "routes": int(tot),
                      "personnel_mix": mix, "heavy_share": heavy}
        # per-route rates, 11 vs heavy (non-11): targets/route + DK fantasy points/route
        r11 = pp["by"].get("11", 0)
        rhv = sum(v for g, v in pp["by"].items() if g != "11")
        if r11 > 0:
            players[k]["tprr_11"] = round(pp["tgt"].get("11", 0) / r11, 3)
            players[k]["dkfp_rr_11"] = round(pp["dk"].get("11", 0) / r11, 3)
        if rhv > 0:
            players[k]["tprr_heavy"] = round(sum(v for g, v in pp["tgt"].items() if g != "11") / rhv, 3)
            players[k]["dkfp_rr_heavy"] = round(sum(v for g, v in pp["dk"].items() if g != "11") / rhv, 3)
    teams = {}
    for t, gr in team_routes.items():
        tot = sum(gr.values())
        if tot <= 0: continue
        teams[t] = {g: round(v / tot, 3) for g, v in sorted(gr.items(), key=lambda x: -x[1])}
        teams[t]["heavy_rate"] = round(sum(v for g, v in gr.items() if g != "11") / tot, 3)

    doc = {"_meta": {"source": "FantasyPoints Data Suite — Personnel dimension (receiving routes)",
                     "note": "per-player route share by grouping + per-team personnel rates. heavy = non-11. "
                             "tprr_*/dkfp_rr_* = targets and DraftKings fantasy points per route, 11 vs heavy.",
                     "groupings": [os.path.splitext(os.path.basename(f))[0] for f in files]},
           "players": players, "teams": teams}
    if a.dry_run:
        print(json.dumps(doc["_meta"], indent=1)); print("players:", len(players), "teams:", len(teams)); return 0
    json.dump(doc, open(os.path.join(a.repo, a.out), "w"), ensure_ascii=False, indent=0)
    print(f"wrote {a.out}: {len(players)} players · {len(teams)} teams")

    # --- upgrade personnel_2026.json: fold FP heavy_rate in next to the v1 (third-party) heavy_2025 ---
    pj = os.path.join(a.repo, "personnel_2026.json")
    if os.path.exists(pj) and teams:
        pdoc = json.load(open(pj))
        for t, rec in pdoc.get("teams", {}).items():
            if t in teams:
                rec["fp_heavy_rate_2025"] = round(teams[t]["heavy_rate"] * 100, 1)
                rec["fp_personnel_mix"] = {g: teams[t][g] for g in teams[t] if g != "heavy_rate"}
        pdoc.setdefault("_meta", {})["fp_personnel_added"] = True
        json.dump(pdoc, open(pj, "w"), ensure_ascii=False, indent=1)
        print("personnel_2026.json upgraded: FP heavy_rate + personnel_mix folded in per team")
    return 0

if __name__ == "__main__":
    main()
