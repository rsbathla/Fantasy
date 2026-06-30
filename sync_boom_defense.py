#!/usr/bin/env python3
"""BRIDGE: propagate the move-aware 2026 defense (reweight_defense_2026.py -> defense.json canonical
pass_cov_pctl/run_def_pctl) into the boom matchup engine's input (defense_2026_matchup.json).
Previously this bridge lived only in dfs_review/build_guardrail_data.py and was NOT in any pipeline,
so the boom side could silently read a STALE matchup table. Running this as a boom-pipeline stage
(before boom_foundation) guarantees boom matchups == the roster-adjusted fusion defense."""
import core, json, os
dj = json.load(open(core.P('defense.json'), encoding='utf-8'))['teams']
out = {t: {'cov': v.get('pass_cov_pctl'), 'run': v.get('run_def_pctl')} for t, v in dj.items()}
dest = core.find_data('dfs_review', 'out', 'defense_2026_matchup.json')
core.safe_json_dump(out, dest)
print("sync_boom_defense: wrote %d teams -> %s" % (len(out), dest))
miss = [t for t, v in out.items() if v['cov'] is None or v['run'] is None]
print("  teams missing cov/run:", miss or "none")
