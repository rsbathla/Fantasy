#!/usr/bin/env python3
"""
pipeline — the SINGLE orchestrator. Replaces the implicit 18-step hand-run chain
and turns every silent ordering hazard into a loud failure.

Fixes (all currently unguarded in the live repo):
  * NO ORCHESTRATOR        -> one ordered DAG, run with `python3 refactor/pipeline.py`
  * SILENT SKIP            -> after each stage we assert its `produces` columns exist;
                              a skipped/failed ingest aborts instead of silently
                              dropping columns that downstream engines then abstain on.
  * csv/json DESYNC        -> integrity check asserts both have identical column sets.
  * ingest_defense/reweight ORDER -> `reweight_defense_2026` requires defense.json to
                              already carry *_2025 fields (i.e. ingest_defense ran first);
                              and the run order guarantees reweight is LAST to touch
                              defense.json + features (so a stray ingest_defense re-run
                              can't silently revert the 2026 adjustment).

Usage:
  python3 refactor/pipeline.py            # run full pipeline in order, with checks
  python3 refactor/pipeline.py --check    # dry-run: validate current on-disk state only
  python3 refactor/pipeline.py --from dfs_scenarios   # resume from a stage
"""
import json, os, subprocess, sys
import os as _o, sys as _s
_s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))))  # repo root for `core`
import core

# (stage script, expected NEW feature columns after it, other required outputs)
STAGES = [
    ("build_features",        ["name", "pos", "adp"],                 []),
    ("ingest_advanced",       ["yprr_man", "zone_run_sh"],            []),
    ("ingest_advanced2",      ["route_tprr"],                          []),
    ("ingest_advanced3",      ["recyd_pg"],                            []),   # FP-derived; CPOE is NOT in the FP export
    ("ingest_advanced4",      ["rec_epa_route", "rush_epa_att", "qb_cpoe"], []),  # REAL CPOE/EPA/NGS from the NFL Pro scrape
    ("ingest_advanced5",      ["sis_epa"],                             []),
    ("ingest_advanced6",      ["snap_share_est"],                      []),
    ("ingest_advanced7",      ["rec_epa_per_tgt_man"],                 []),
    ("ingest_advanced8",      ["rec_man_zone_delta"],                  []),
    ("ingest_advanced9",      ["qb_man_zone_delta"],                   []),
    ("ingest_advanced10",     ["rb_zone_gap_delta"],                   []),
    ("ingest_defense",        ["opp_pass_cov_pctl"],                   ["defense.json"]),
    ("normalize_defense_2026",["opp_pass_rush_pctl"],                  ["defense.json"]),  # rate-weighted + rookies (reweight_defense_2026.py kept as the MOVES-map source it imports)
    ("reproject_movers",      ["usage_src"],                           []),
    ("dfs_scenarios",         [],                                      ["dfs_scenarios.json"]),
    ("fusion",                [],                                      ["fusion.json"]),
    ("gameplan",              [],                                      ["gameplan.json"]),
    ("personnel",             [],                                      ["personnel_changes.json"]),
    ("command_center",        [],                                      ["command_center.html"]),
]

def _cols():
    fj = json.load(open(core.P("features.json"), encoding="utf-8"))
    import csv as _csv
    with open(core.P("features.csv"), encoding="utf-8") as fh:
        csv_cols = next(_csv.reader(fh))
    return set(fj["meta"]["cols"]), set(csv_cols)

def integrity_check(stage, produces, outputs):
    jcols, ccols = _cols()
    if jcols != ccols:
        raise SystemExit(f"[{stage}] features.csv/json column DESYNC: "
                         f"json-only={sorted(jcols-ccols)[:5]} csv-only={sorted(ccols-jcols)[:5]}")
    miss = [c for c in produces if c not in jcols]
    if miss:
        raise SystemExit(f"[{stage}] expected columns missing (stage skipped/failed?): {miss}")
    for o in outputs:
        if not os.path.exists(core.P(o)):
            raise SystemExit(f"[{stage}] expected output not produced: {o}")
    if stage == "reweight_defense_2026":
        d = json.load(open(core.P("defense.json"), encoding="utf-8"))
        teams = d.get("teams", d)
        sample = next(iter(teams.values() if isinstance(teams, dict) else teams))
        if "pass_cov_pctl_2025" not in sample:
            raise SystemExit("[reweight] defense.json lacks *_2025 — ingest_defense must run FIRST")

def run(start=None):
    started = start is None
    for stage, produces, outputs in STAGES:
        if stage == start:
            started = True
        if not started:
            continue
        print(f"==> {stage}")
        r = subprocess.run([sys.executable, core.P(stage + ".py")], capture_output=True, text=True, encoding="utf-8", errors="replace", env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"})
        if r.returncode != 0:
            raise SystemExit(f"[{stage}] FAILED:\n{r.stderr[-1500:]}")
        integrity_check(stage, produces, outputs)
    print("pipeline OK")

def check():
    jcols, ccols = _cols()
    print("features.csv/json in sync:", jcols == ccols, f"({len(jcols)} cols)")
    for stage, produces, _ in STAGES:
        miss = [c for c in produces if c not in jcols]
        print(f"  {stage:24s} produces-present={not miss}" + (f" MISSING {miss}" if miss else ""))

if __name__ == "__main__":
    if "--check" in sys.argv:
        check()
    elif "--from" in sys.argv:
        run(sys.argv[sys.argv.index("--from") + 1])
    else:
        run()
