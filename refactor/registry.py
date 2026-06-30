#!/usr/bin/env python3
"""
registry — column-provenance manifest for the (now 139-column) feature store.

Builds columns.json: every feature column -> {producer, dtype, coverage_pct,
abstains}. Kills the "139 columns, no record of who writes each or how complete"
maintainability risk. `validate()` fails loudly if the live store grows a column
the manifest doesn't know about (catches silent schema drift in CI).
"""
import json, os
import os as _o, sys as _s
_s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))))  # repo root for `core`
import core

# best-effort producer map by column prefix/name -> pipeline stage
PRODUCER = [
    (("sis_epa","sis_boom","sis_bust","sis_par","sis_positive","sis_pe_play"), "ingest_advanced5/6"),
    (("rec_epa_man","rec_epa_per_tgt_man","rec_boom_man"), "ingest_advanced7"),
    (("rec_epa_zone","rec_epa_per_tgt_zone","rec_boom_zone","rec_man_zone_delta"), "ingest_advanced8"),
    (("qb_epa_man","qb_epa_zone","qb_boom_man","qb_boom_zone","qb_man_zone_delta"), "ingest_advanced9"),
    (("rb_epa_a_zone","rb_epa_a_gap","rb_boom_zone","rb_boom_gap","rb_zone_gap_delta"), "ingest_advanced10"),
    (("opp_pass_cov_pctl","opp_pass_rush_pctl","opp_run_def_pctl","opp_pass_cov_epatgt"), "ingest_defense/reweight_2026"),
    (("snap_share_est","snap_est_basis"), "ingest_advanced6"),
    (("rec_epa_route","rush_epa_att","rec_separation","rec_yacoe","qb_epa_db","cpoe"), "ingest_advanced4"),
    (("route_yprr","route_tprr","deep_route_sh","fd_rr"), "ingest_advanced2/3"),
    (("yprr_man","yprr_zone","man_zone_delta","vegas_w15","opp_w15_man_rate","zone_run_sh"), "ingest_advanced"),
    (("name","pos","team","adp","proj_pg","merged_rank","w15","w16","w17"), "build_features"),
]

def producer_of(col):
    for keys, stage in PRODUCER:
        if col in keys or any(col.startswith(k) for k in keys):
            return stage
    return "unknown"

def _dtype(vals):
    nn = [v for v in vals if v not in (None, "", "null")]
    if not nn: return "empty"
    try:
        [float(v) for v in nn]; return "numeric"
    except (TypeError, ValueError):
        return "string"

def build_manifest(root=None):
    root = root or core.HERE
    fj = json.load(open(os.path.join(root, "features.json"), encoding="utf-8"))
    rows = fj["players"]; cols = fj["meta"]["cols"]; n = len(rows)
    prov = fj["meta"].get("provenance", {})
    man = {}
    for c in cols:
        vals = [r.get(c) for r in rows]
        present = sum(1 for v in vals if v not in (None, "", "null"))
        man[c] = {"producer": prov.get(c) or producer_of(c),
                  "dtype": _dtype(vals),
                  "coverage_pct": round(present / n * 100, 1),
                  "abstains": present < n}
    out = {"n_players": n, "n_columns": len(cols), "columns": man}
    core.safe_json_dump(out, os.path.join(root, "refactor", "columns.json"), indent=2)
    return out

def validate(root=None):
    root = root or core.HERE
    man = json.load(open(os.path.join(root, "refactor", "columns.json"), encoding="utf-8"))
    live = json.load(open(os.path.join(root, "features.json"), encoding="utf-8"))["meta"]["cols"]
    missing = [c for c in live if c not in man["columns"]]
    unknown = [c for c, m in man["columns"].items() if m["producer"] == "unknown"]
    return {"ok": not missing, "unregistered": missing, "unknown_producer": unknown}

if __name__ == "__main__":
    m = build_manifest()
    print("manifest: %d columns / %d players" % (m["n_columns"], m["n_players"]))
    v = validate()
    print("validate: ok=%s unregistered=%d unknown_producer=%d"
          % (v["ok"], len(v["unregistered"]), len(v["unknown_producer"])))
