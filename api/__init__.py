"""bestball API package root.

Path bootstrap: importing this package as `api` (e.g. `from api.app.main import app`
when running from the repo root) puts this directory on sys.path so the internal
absolute imports (`from app...`) resolve. Running with PYTHONPATH=api (run.sh, the
test suite) also works without this. No third-party imports here -> stays lightweight.
"""
import os as _os
import sys as _sys

_HERE = _os.path.dirname(_os.path.abspath(__file__))
if _HERE not in _sys.path:
    _sys.path.insert(0, _HERE)
