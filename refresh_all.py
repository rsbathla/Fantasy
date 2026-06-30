#!/usr/bin/env python3
"""FULL refresh: refactor pipeline -> boom pipeline -> command_center -> intel.
Use when underlying NFL data changes. (Daily tweet-only refresh = refresh_intel.py.)"""
import subprocess, sys, os, time
H=os.path.dirname(os.path.abspath(__file__))
def run(args,label):
    print(f"\n=== {label} ==="); t=time.time()
    r=subprocess.run([sys.executable]+args,cwd=H,capture_output=True,text=True)
    print((r.stdout or '').strip()[-500:])
    if r.returncode: print("STDERR",(r.stderr or '')[-800:]); print(f"[FAIL] {label}"); return False
    print(f"[OK] {label} ({time.time()-t:.0f}s)"); return True
if not run(['refactor/pipeline.py'],'refactor pipeline'): sys.exit(1)
boom_in=os.path.join(os.path.dirname(H),'dfs_review','out','boom_proj.csv')
run(['boom_pipeline.py'] if os.path.exists(boom_in) else ['boom_pipeline.py','--from','sync_boom_defense'],'boom pipeline')
run(['command_center.py'],'command_center (merge fresh boom_marks)')
run(['build_intel.py'],'intel data'); run(['render_intel.py'],'intel html')
print("\nfull refresh done.")
