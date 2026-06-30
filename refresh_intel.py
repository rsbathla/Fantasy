#!/usr/bin/env python3
"""DAILY refresh: rebuild intel + team/player dossier from the latest tweets.db + model files.
Resilient: if the intel step fails (e.g. tweets.db transiently locked/mid-write during the daily
ingest), the dossier still rebuilds from the existing intel_data.json so the board stays current.
Fast (~6s). Wire to run after the daily tweet ingest, or via a scheduled task."""
import subprocess, sys, os, time
H=os.path.dirname(os.path.abspath(__file__))
def run(s, fatal=False):
    t=time.time(); r=subprocess.run([sys.executable,os.path.join(H,s)],cwd=H,capture_output=True,text=True)
    print((r.stdout or '').strip()[-300:])
    if r.returncode:
        print(f"[WARN] {s} failed:\n"+(r.stderr or '')[-500:])
        if fatal: sys.exit(1)
        return False
    print(f"[OK] {s} ({time.time()-t:.0f}s)"); return True
ok_intel = run('build_intel.py') and run('render_intel.py')
if not ok_intel:
    print("[note] intel step failed — rebuilding dossier from the existing intel_data.json")
# dossier depends only on intel_data.json (+ model CSVs), so it refreshes regardless
run('ingest_motion.py'); run('ingest_coverage.py'); run('build_division_splits.py')  # per-player motion (if exported) + division splits
run('build_manzone_2yr.py')  # 2-yr (2024+2025 FantasyPoints) man/zone confidence overlay (static CSV -> manzone_2yr.json)
run('build_dossier.py', fatal=True); run('build_lever_count.py'); run('build_lever_board.py'); run('render_dossier.py', fatal=True)
print('refreshed ->', os.path.join(H,'intel.html'), '+', os.path.join(H,'dossier.html'))
