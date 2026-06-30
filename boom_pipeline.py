#!/usr/bin/env python3
"""
boom_pipeline — the SINGLE orchestrator for the boom ceiling subsystem.

Replaces the implicit hand-run chain (foundation -> 5 augmenters -> 5 flag builders ->
explorer) that the audit flagged: no orchestration, and a silent statmenu CLOBBER (re-running
boom_foundation.py wipes the augmentation keys, and reg_base() then quietly falls back to the
2025-only base). Here every ordering hazard becomes a loud failure.

  * ORDER          -> one ordered DAG; augmenters always run after foundation, flags after them.
  * CLOBBER        -> after each augmenter we assert its statmenu key is present (and the
                      foundation carry-forward guard means a stray re-run is non-destructive).
  * MISSING OUTPUT -> each stage asserts its produced files exist and are non-empty.
  * FINAL GATE     -> validate_boom.py must pass (schema + interpolation + ranges + clobber).

Usage:
  python3 boom_pipeline.py            # run full pipeline in order, with checks
  python3 boom_pipeline.py --check    # dry-run: validate current on-disk state only
  python3 boom_pipeline.py --from build_flags_WR   # resume from a stage
"""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); B = os.path.join(HERE, 'boom')

# (stage script, [produced files], statmenu augmentation key to assert or None)
STAGES = [
    ("derive_boom_threshold", ["boom/boomdef.json"], None),
    ("sync_boom_defense",     [], None),  # BRIDGE: refresh move-aware defense_2026_matchup before foundation reads it
    ("boom_foundation",       ["boom/statmenu.json", "boom/gamelog.json",
                               "boom/schedule2026.json", "boom/defense2026.json",
                               "boom/opp_offense.json"], None),
    ("boom_base2yr",          ["boom/base2yr.json"],    "base_blended"),
    ("adv2yr",                ["boom/adv2.json"],        "adv2"),
    ("build_chart2yr",        ["boom/chart2yr.json"],    "chart2"),
    ("build_extra_signals",   ["boom/redzone.json", "boom/team_env.json"], "rz"),
    ("build_defense_shell",   ["boom/defense_shell.json"], None),
    ("build_cover_spec",      ["boom/cover_spec.json"],  "cspec"),
    ("build_rookie_profiles", ["boom/rookie_college_profile.json"], None),
    ("build_rookie_prior",    ["boom/rookie_prior.json"], None),
    ("build_rookie_db_funnel",["boom/rookie_db_grades.json"], None),
    ("apply_rookie_to_statmenu", ["boom/statmenu.json"], None),
    ("build_flags_QB",        ["boom/flags_QB.json"],    None),
    ("build_flags_RB",        ["boom/flags_RB.json"],    None),
    ("build_flags_WR",        ["boom/flags_WR.json"],    None),
    ("build_coordinator_scheme",["coordinator_scheme_2026.json"], None),  # DC scheme projection -> build_def_profile
    ("build_defender_grades",  ["boom/defender_grades.json"], None),       # per-CB1 coverage grades -> build_def_profile
    ("build_def_profile",     ["boom/defensive_profile.json"], None),  # Branch 4: reconcile funnels vs 2026 engine + rookies
    ("apply_funnel_overlay",  ["boom/flags_WR.json"],      None),  # funnel matchup overlay (post WR build)
    ("build_flags_TE",        ["boom/flags_TE.json"],    None),
    ("build_flags_DST",       ["boom/flags_DST.json"],   None),
    ("tighten_flags",         ["boom/flags_WR.json"], None),
    ("build_stack_overlay",   ["boom/flags_WR.json", "boom/flags_TE.json"], None),
    ("mark_fa_players",       ["boom/flags_WR.json"], None),
    ("build_boom_marks",      ["boom/boom_marks.json"], None),
    ("build_upside_cases",    ["upside_cases.html","boom/upside_cases.json"], None),
    ("build_player_explorer", ["player_explorer.html"],  None),
    ("command_center",        ["command_center.html"], None),  # final: refresh board with fresh boom_marks
]

def _exists_nonempty(rel):
    p = os.path.join(HERE, rel)
    return os.path.exists(p) and os.path.getsize(p) > 0

def _aug_present(key):
    sm = json.load(open(os.path.join(B, "statmenu.json")))
    return sum(1 for v in sm.values()
               if v.get('pos') in ('QB', 'RB', 'WR', 'TE') and v.get(key) is not None)

def integrity(stage, produces, augkey):
    for rel in produces:
        if not _exists_nonempty(rel):
            raise SystemExit(f"[{stage}] expected output missing/empty: {rel}")
    if augkey:
        c = _aug_present(augkey)
        if c == 0:
            raise SystemExit(f"[{stage}] statmenu has 0 '{augkey}' -> CLOBBER (augmenter didn't take)")
        print(f"    ok: {augkey} present on {c} skill players; outputs {produces}")
    else:
        print(f"    ok: outputs {produces}")

def run(start=None):
    started = start is None
    for stage, produces, augkey in STAGES:
        if stage == start: started = True
        if not started: continue
        print(f"==> {stage}")
        r = subprocess.run([sys.executable, os.path.join(HERE, stage + ".py")],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"[{stage}] FAILED:\n{r.stderr[-1800:]}")
        integrity(stage, produces, augkey)
    print("==> validate_boom (final gate)")
    r = subprocess.run([sys.executable, os.path.join(HERE, "validate_boom.py")],
                       capture_output=True, text=True)
    print(r.stdout[-1200:])
    if r.returncode != 0:
        raise SystemExit("validate_boom FAILED — see above")
    print("boom_pipeline OK")

def check():
    print("=== boom_pipeline --check (on-disk state) ===")
    allok = True
    for stage, produces, augkey in STAGES:
        miss = [p for p in produces if not _exists_nonempty(p)]
        tag = "OK " if not miss else "MISS"
        if miss: allok = False
        extra = ""
        if augkey and not miss:
            c = _aug_present(augkey); extra = f"  {augkey}={c}"
            if c == 0: allok = False; extra += " CLOBBER"
        print(f"  [{tag}] {stage:24s} {produces}{extra}" + (f"  MISSING {miss}" if miss else ""))
    r = subprocess.run([sys.executable, os.path.join(HERE, "validate_boom.py")],
                       capture_output=True, text=True)
    print(r.stdout[-600:])
    print("check:", "GREEN" if (allok and r.returncode == 0) else "RED")

if __name__ == "__main__":
    if "--check" in sys.argv:
        check()
    elif "--from" in sys.argv:
        run(sys.argv[sys.argv.index("--from") + 1])
    else:
        run()
