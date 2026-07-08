#!/usr/bin/env python3
"""build_fp_alignment.py — FantasyPoints per-player ALIGNMENT, cross-checked against NFL Pro.

FantasyPoints charts each receiver's route alignment (Slot / Wide / Inline / Backfield %). Every FP
receiving row carries AlignmentSlot/Wide/Inline/BackfieldRoutesPercentage — but PER-SPLIT, so a clean
player-SEASON alignment needs the base (unfiltered) receiving pull. Priority of sources:
  1. --base <file>  : the unfiltered season pull (one row/player) — RUN THIS for accuracy:
        FantasyPoints Data Suite -> Receiving -> no dimension filter -> export ->
        NFL-master/FP/2025/Receiving/base_season.csv   (bearer-authenticated; you run it, token never leaves your box)
  2. fallback: route-weighted aggregate of every file under a --dim folder (default depthOfTarget) of
     the existing FP_SWEEP — a proxy season alignment from data already banked (flagged as proxy).

Then it CROSS-CHECKS every player against NFL Pro's alignment (player_funnels.json): consensus where
the two vendors agree, a DIVERGE flag where they disagree by >8pts — so no player funnel rests on one
source's slot/wide definition. Output: fp_alignment.json.

  python3 build_fp_alignment.py --base NFL-master/FP/2025/Receiving/base_season.csv   # accurate
  python3 build_fp_alignment.py                                                        # proxy from FP_SWEEP
"""
import argparse, csv, glob, json, os, re

def fn(n):
    n = str(n).strip().lower(); n = re.sub(r"\s+(jr|sr|ii|iii|iv|v)\.?$", "", n)
    return n.replace(".", "").replace("'", "").replace("-", " ").strip()
def num(x):
    try: return float(str(x).replace("%", "").strip())
    except Exception: return None

ACOLS = {"slot": "AlignmentSlotRoutesPercentage", "wide": "AlignmentWideRoutesPercentage",
         "inline": "AlignmentInlineRoutesPercentage", "backfield": "AlignmentBackfieldRoutesPercentage"}

def from_base(path):
    """clean season alignment: one row per player."""
    out = {}
    for r in csv.DictReader(open(path)):
        k = fn(r.get("Name", ""))
        if not k: continue
        rts = num(r.get("RoutesTotal")) or 0
        out[k] = {"pos": r.get("POS", ""), "routes": int(rts),
                  "align": {a: round(num(r.get(c)) or 0, 3) for a, c in ACOLS.items()}}
    return out, "FP base (season, unfiltered)"

def from_sweep(dim_dir):
    """proxy: route-weight each split's alignment% by its RoutesTotal, sum across the dimension."""
    acc = {}
    for p in glob.glob(os.path.join(dim_dir, "*.csv")):
        for r in csv.DictReader(open(p)):
            k = fn(r.get("Name", ""))
            if not k: continue
            rts = num(r.get("RoutesTotal")) or 0
            if rts <= 0: continue
            d = acc.setdefault(k, {"pos": r.get("POS", ""), "R": 0.0, "w": {a: 0.0 for a in ACOLS}})
            d["R"] += rts
            for a, c in ACOLS.items():
                d["w"][a] += (num(r.get(c)) or 0) * rts
    out = {}
    for k, d in acc.items():
        if d["R"] < 20: continue
        out[k] = {"pos": d["pos"], "routes": int(d["R"]),
                  "align": {a: round(d["w"][a] / d["R"], 3) for a in ACOLS}}
    return out, "FP proxy (route-weighted across depthOfTarget splits — pull --base for accuracy)"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=None)
    ap.add_argument("--dim", default="NFL-master/FP_SWEEP/2025/Receiving/depthOfTarget")
    ap.add_argument("--repo", default="."); ap.add_argument("--out", default="fp_alignment.json")
    a = ap.parse_args()
    if a.base and os.path.exists(a.base):
        fp, src = from_base(a.base)
    else:
        fp, src = from_sweep(os.path.join(a.repo, a.dim))

    # cross-check vs NFL Pro (player_funnels.json). NFL Pro uses slot/wide/tight; FP uses slot/wide/
    # inline/backfield. Compare the two shared, robust axes: SLOT% and WIDE%.
    npro = {}
    pf = os.path.join(a.repo, "player_funnels.json")
    if os.path.exists(pf):
        for k, v in json.load(open(pf))["players"].items():
            mix = (v.get("alignment_funnel") or {}).get("mix")
            if mix: npro[k] = mix

    n_agree = n_div = 0
    for k, d in fp.items():
        np = npro.get(k)
        if not np:
            d["xcheck"] = "no NFL Pro match"; continue
        dslot = abs((d["align"]["slot"] * 100) - (np.get("slot", 0) * 100))
        dwide = abs((d["align"]["wide"] * 100) - (np.get("wide", 0) * 100))
        diverge = dslot > 8 or dwide > 8
        d["xcheck"] = ("DIVERGE" if diverge else "agree")
        d["npro"] = {"slot": np.get("slot"), "wide": np.get("wide"), "tight": np.get("tight")}
        d["consensus_slot"] = round(((d["align"]["slot"]) + (np.get("slot", 0))) / 2, 3)
        n_div += diverge; n_agree += (not diverge)

    doc = {"_meta": {"source": src, "cross_check": "vs NFL Pro player_funnels.json (SLOT%/WIDE% axes)",
                     "flag_threshold": ">8pt slot or wide gap = DIVERGE",
                     "agree": n_agree, "diverge": n_div}, "players": fp}
    json.dump(doc, open(os.path.join(a.repo, a.out), "w"), ensure_ascii=False, indent=0)
    print(f"wrote {a.out}: {len(fp)} players · source={src}")
    print(f"cross-check vs NFL Pro: {n_agree} agree · {n_div} DIVERGE (>8pt slot/wide gap)")
    for k in ("puka nacua", "ladd mcconkey", "jamarr chase", "cooper kupp"):
        v = fp.get(k)
        if v and "npro" in v:
            print(f"  {k:16s} FP slot {v['align']['slot']:.2f}/wide {v['align']['wide']:.2f} · "
                  f"NPro slot {v['npro']['slot']:.2f}/wide {v['npro']['wide']:.2f} · {v['xcheck']}")

if __name__ == "__main__":
    main()
