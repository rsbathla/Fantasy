#!/usr/bin/env bash
# Dev server for the BestBall Analytics API.
#   ./run.sh            # http://127.0.0.1:8000  (docs at /docs)
# Run from the `api/` directory (PYTHONPATH=. so `app.main` resolves).
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONPATH="${PYTHONPATH:-.}"
exec uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
