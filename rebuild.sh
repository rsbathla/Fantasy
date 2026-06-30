#!/usr/bin/env bash
# Canonical entry point for the bestball pipeline.
# Runs all 18 stages IN ORDER with per-stage integrity checks (column presence,
# csv/json sync, ingest_defense->reweight ordering). Fails loud on any hazard.
#   ./rebuild.sh           full clean rebuild
#   ./rebuild.sh --check    dry-run: validate current on-disk state only
#   ./rebuild.sh --from dfs_scenarios   resume from a stage
cd "$(dirname "$0")" && exec python3 refactor/pipeline.py "$@"
