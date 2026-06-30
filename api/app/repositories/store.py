"""DataStore: the ONLY thing that touches the pipeline's JSON files.

- Loads + caches each dataset.
- Invalidates a cached dataset when its file mtime changes (so a rebuild is picked
  up without restarting the web process).
- Thread-safe (a single RLock guards the cache; FastAPI runs sync handlers in a
  threadpool, so concurrent reads are real).
- Raises NotFound when a requested dataset file is missing.

Deliberately dependency-free beyond the stdlib + app.errors -- NO pandas, NO core.py.
"""
from __future__ import annotations

import json
import os
import threading
from typing import Any, Dict, List, Tuple

from app.errors import NotFound

# logical dataset name -> filename in DATA_DIR
DATASETS: Dict[str, str] = {
    "fusion": "fusion.json",
    "dfs": "dfs_scenarios.json",
    "defense": "defense.json",
    "gameplan": "gameplan.json",
    "personnel": "personnel_changes.json",
    "features": "features.json",
}


class DataStore:
    def __init__(self, data_dir: str) -> None:
        self.data_dir = data_dir
        self._lock = threading.RLock()
        # name -> (mtime_ns, parsed_obj)
        self._cache: Dict[str, Tuple[int, Any]] = {}

    # ---- paths / metadata ----------------------------------------------------

    def path(self, name: str) -> str:
        try:
            filename = DATASETS[name]
        except KeyError:  # pragma: no cover - programmer error, not user input
            raise NotFound(f"Unknown dataset '{name}'.", code="not_found")
        return os.path.join(self.data_dir, filename)

    def mtime(self, name: str) -> float | None:
        """File modification time (epoch seconds) or None if the file is absent."""
        try:
            return os.path.getmtime(self.path(name))
        except OSError:
            return None

    # ---- loading -------------------------------------------------------------

    def load(self, name: str) -> Any:
        """Return the parsed JSON for `name`, using an mtime-validated cache.

        Raises NotFound if the dataset file does not exist.
        """
        p = self.path(name)
        try:
            cur_mtime = os.stat(p).st_mtime_ns
        except OSError:
            raise NotFound(f"Dataset '{name}' is not available.", code="dataset_unavailable")

        with self._lock:
            cached = self._cache.get(name)
            if cached is not None and cached[0] == cur_mtime:
                return cached[1]

        # Parse outside the lock (I/O + json can be slow); re-check under lock to store.
        with open(p, "r", encoding="utf-8") as fh:
            obj = json.load(fh)

        with self._lock:
            self._cache[name] = (cur_mtime, obj)
        return obj

    # ---- typed convenience accessors ----------------------------------------

    def players(self, name: str) -> List[Dict[str, Any]]:
        """Return the `players` list of a player-keyed dataset (fusion/dfs/features)."""
        return self.load(name).get("players", []) or []

    def teams(self, name: str) -> Dict[str, Any]:
        """Return the `teams` map of a team-keyed dataset (defense/personnel)."""
        return self.load(name).get("teams", {}) or {}

    def available(self) -> Dict[str, bool]:
        """Map of dataset name -> whether its file currently exists on disk."""
        return {name: os.path.exists(self.path(name)) for name in DATASETS}
