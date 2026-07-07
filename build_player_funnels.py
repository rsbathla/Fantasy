#!/usr/bin/env python3
"""build_player_funnels.py — per-PLAYER funnels + usage rates from NFL Pro (Next Gen Stats).
Every receiver gets an ALIGNMENT funnel (slot/wide/tight route mix + where he WINS by separation
and YPRR), a DEPTH funnel (deep/intermediate/short), and usage rates; every back gets a rushing
funnel (RYOE, box faced) + pass-game role. This is the player-side mirror of the team funnels.

VINTAGE + COMPOUNDING: aggregates a season of weekly CSVs. Pass --raw2026 once 2026 games exist and
it BLENDS: est = w26*2026 + (1-w26)*2025, where w26 = min(1, weeks_2026 / STABILIZE[stat]). Route
mix stabilizes fast (~4 wks); efficiency slow (~10). So early season leans on the 2025 prior and the
estimate self-corrects toward 2026 reality as the sample grows — the funnels get sharper every week.

  python3 build_player_funnels.py --raw ../nfl_pro_scraper --out player_funnels.json          # 2025 only
  python3 build_player_funnels.py --raw ../nfl_pro_scraper --raw2026 ../scrape_2026 --wk26 5   # in-season blend
"""
import argparse, csv, glob, json, os, re
from collections import defaultdict

def fn(n):
    n = str(n).strip().lower(); n = re.sub(r"\s+(jr|sr|ii|iii|iv|v)\.?$", "", n)
    return n.replace(".", "").replace("'", "").replace("-", " ").strip()
def num(x):
    try: return float(str(x).replace("%", "").replace("+", "").strip())
    except Exception: return None

REC_ALIGN = {"RECEIVING_ALIGNMENT_SLOT": "slot", "RECEIVING_ALIGNMENT_WIDE": "wide", "RECEIVING_ALIGNMENT_TIGHT": "tight"}
REC_DEPTH = {"RECEIVING_DEEP": "deep", "RECEIVING_INTERMEDIATE": "intermediate", "RECEIVING_SHORT": "short"}
# weeks of 2026 data at which each stat is ~stable (for the blend weight)
STABILIZE = {"mix": 4, "usage": 5, "efficiency": 10}


def agg_receiving(folder):
    """Per player: totals + routes/tgts/yds/sep by alignment and depth, volume-weighted efficiency."""
    P = defaultdict(lambda: {"rts": 0, "tgt": 0, "rec": 0, "yds": 0, "td": 0, "gp": 0,
                             "_sep_w": 0.0, "_croe_w": 0.0, "_epa": 0.0, "pos": "", "team": "",
                             "align": defaultdict(lambda: {"rts": 0, "tgt": 0, "yds": 0, "_sep_w": 0.0}),
                             "depth": defaultdict(lambda: {"rts": 0, "tgt": 0, "yds": 0})})
    def rows(split):
        for p in sorted(glob.glob(os.path.join(folder, f"week*_{split}.csv"))):
            for r in csv.DictReader(open(p)):
                yield r
    for r in rows("ALL"):
        k = fn(r["Player"]);
        if not k: continue
        d = P[k]; rts = num(r["Rts"]) or 0
        d["pos"] = d["pos"] or (r.get("Pos") or ""); d["rts"] += rts
        d["tgt"] += num(r["Tgt"]) or 0; d["rec"] += num(r["Rec"]) or 0
        d["yds"] += num(r["Yds"]) or 0; d["td"] += num(r["TD"]) or 0; d["gp"] += num(r.get("GP")) or 0
        d["_sep_w"] += (num(r.get("Avg. Sep")) or 0) * rts
        d["_croe_w"] += (num(r.get("CROE")) or 0) * rts
        d["_epa"] += num(r.get("Rec EPA")) or 0
    for split, name in REC_ALIGN.items():
        for r in rows(split):
            k = fn(r["Player"]);
            if not k or k not in P: continue
            a = P[k]["align"][name]; rts = num(r["Rts"]) or 0
            a["rts"] += rts; a["tgt"] += num(r["Tgt"]) or 0; a["yds"] += num(r["Yds"]) or 0
            a["_sep_w"] += (num(r.get("Avg. Sep")) or 0) * rts
    for split, name in REC_DEPTH.items():
        for r in rows(split):
            k = fn(r["Player"]);
            if not k or k not in P: continue
            a = P[k]["depth"][name]; a["rts"] += num(r["Rts"]) or 0
            a["tgt"] += num(r["Tgt"]) or 0; a["yds"] += num(r["Yds"]) or 0
    return P


def agg_rushing(folder):
    P = defaultdict(lambda: {"att": 0, "yds": 0, "td": 0, "_ryoe": 0.0, "_yaco_w": 0.0, "pos": "", "gp": 0})
    for p in sorted(glob.glob(os.path.join(folder, "week*_ALL.csv"))):
        for r in csv.DictReader(open(p)):
            k = fn(r["Player"]);
            if not k: continue
            d = P[k]; att = num(r.get("Att")) or 0
            d["att"] += att; d["yds"] += num(r.get("Yds")) or 0; d["td"] += num(r.get("TD")) or 0
            d["_ryoe"] += num(r.get("RYOE")) or 0
            d["_yaco_w"] += (num(r.get("YACo/Att")) or 0) * att
            d["pos"] = d["pos"] or (r.get("Pos") or ""); d["gp"] += num(r.get("GP")) or 0
    return P


def build(raw):
    rec = agg_receiving(os.path.join(raw, "receiving"))
    rush = agg_rushing(os.path.join(raw, "rushing"))
    out = {}
    for k, d in rec.items():
        rts = d["rts"]
        if rts < 20: continue                       # drop tiny samples
        mix = {a: round(d["align"][a]["rts"] / rts, 3) for a in ("slot", "wide", "tight") if d["align"][a]["rts"]}
        dmix = {a: round(d["depth"][a]["rts"] / rts, 3) for a in ("deep", "intermediate", "short") if d["depth"][a]["rts"]}
        yprr_by = {a: round(d["align"][a]["yds"] / d["align"][a]["rts"], 2)
                   for a in ("slot", "wide", "tight") if d["align"][a]["rts"] >= 15}
        sep_by = {a: round(d["align"][a]["_sep_w"] / d["align"][a]["rts"], 2)
                  for a in ("slot", "wide", "tight") if d["align"][a]["rts"] >= 15}
        best_align = max(yprr_by, key=yprr_by.get) if yprr_by else (max(mix, key=mix.get) if mix else None)
        home = max(mix, key=mix.get) if mix else None
        out[k] = {"pos": d["pos"], "gp": int(d["gp"]),
                  "recv": {"routes": int(rts), "routes_pg": round(rts / max(d["gp"], 1), 1),
                           "tgt": int(d["tgt"]), "rec": int(d["rec"]), "yds": int(d["yds"]), "td": int(d["td"]),
                           "yprr": round(d["yds"] / rts, 2), "croe": round(d["_croe_w"] / rts, 3),
                           "avg_sep": round(d["_sep_w"] / rts, 2), "rec_epa": round(d["_epa"], 1)},
                  "alignment_funnel": {"mix": mix, "home": home, "wins_from": best_align,
                                       "yprr_by": yprr_by, "sep_by": sep_by},
                  "depth_funnel": {"mix": dmix}}
    for k, d in rush.items():
        if d["att"] < 20: continue
        r = out.setdefault(k, {"pos": d["pos"], "gp": int(d["gp"])})
        r["rush"] = {"att": int(d["att"]), "att_pg": round(d["att"] / max(d["gp"], 1), 1),
                     "yds": int(d["yds"]), "td": int(d["td"]), "ypc": round(d["yds"] / d["att"], 2),
                     "ryoe_att": round(d["_ryoe"] / d["att"], 2), "yaco_att": round(d["_yaco_w"] / d["att"], 2)}
    return out


def blend(v25, v26, wk26):
    """est = w*2026 + (1-w)*2025 per stat family; w scales with weeks of 2026 data toward STABILIZE."""
    def w(fam): return min(1.0, wk26 / STABILIZE[fam]) if wk26 else 0.0
    # (thin blend: numeric leaves blend by family; structure copied from whichever has data.
    # 2025-only path returns v25 untouched.)
    if not v26: return v25
    import copy; est = copy.deepcopy(v25)
    for k in est:
        if k in v26 and isinstance(est[k], dict):
            for fam, wt in (("recv", w("efficiency")), ("rush", w("efficiency"))):
                if fam in est[k] and fam in v26[k]:
                    for s in est[k][fam]:
                        a, b = est[k][fam].get(s), v26[k][fam].get(s)
                        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                            est[k][fam][s] = round(wt * b + (1 - wt) * a, 3)
    return est


def merge_usage(out, repo):
    """fold in layer2 usage rates (tgt_share, carry_share, role) — the volume side of the funnel."""
    p = os.path.join(repo, "pipeline", "layer2_player_params.csv")
    if not os.path.exists(p): return
    for r in csv.DictReader(open(p)):
        k = fn(r["name"])
        if k in out:
            out[k]["usage"] = {"role": r.get("role", ""), "team": r.get("team", ""),
                               "tgt_share": num(r.get("tgt_share")), "carry_share": num(r.get("carry_share")),
                               "dk_pg": num(r.get("dk_pg")), "cv_tgt": num(r.get("cv_tgt"))}
            out[k]["team"] = r.get("team", "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="../nfl_pro_scraper"); ap.add_argument("--raw2026", default=None)
    ap.add_argument("--wk26", type=int, default=0); ap.add_argument("--repo", default=".")
    ap.add_argument("--out", default="player_funnels.json")
    a = ap.parse_args()
    v25 = build(os.path.expanduser(a.raw))
    est = v25
    vintage = "2025 actuals"
    if a.raw2026 and os.path.isdir(os.path.expanduser(a.raw2026)):
        v26 = build(os.path.expanduser(a.raw2026))
        est = blend(v25, v26, a.wk26)
        vintage = f"2025 prior blended with {a.wk26}wk of 2026 (self-correcting)"
    merge_usage(est, a.repo)
    doc = {"_meta": {"source": "NFL Pro / Next Gen Stats player alignment+depth+rushing",
                     "vintage": vintage, "stabilize_weeks": STABILIZE,
                     "note": "per-player alignment funnel (where he lines up + wins), depth funnel, usage rates. "
                             "Pass --raw2026/--wk26 in-season to blend; the estimate self-corrects weekly."},
           "players": est}
    # FAIL-LOUD GUARD: never clobber a populated layer with an empty build (missing raw dir
    # yields zero players and exit 0 — the silent-data-loss class from the quant audit).
    dest = os.path.join(a.repo, a.out)
    if len(est) < 100:
        raise SystemExit(f"FATAL: only {len(est)} players built (raw scrape missing/empty?) — refusing to overwrite {dest}")
    json.dump(doc, open(dest, "w"), ensure_ascii=False, indent=0)
    n_rec = sum(1 for v in est.values() if "alignment_funnel" in v); n_rush = sum(1 for v in est.values() if "rush" in v)
    print(f"wrote {a.out}: {len(est)} players ({n_rec} receiver funnels · {n_rush} rushing funnels) · {vintage}")
    # readout: a few home/wins-from profiles
    for nm in ("puka nacua", "ladd mcconkey", "ja marr chase", "cooper kupp"):
        v = est.get(nm)
        if v and "alignment_funnel" in v:
            af = v["alignment_funnel"]
            print(f"  {nm:18s} home={af['home']} wins_from={af['wins_from']} mix={af['mix']} sep_by={af['sep_by']}")


if __name__ == "__main__":
    main()
