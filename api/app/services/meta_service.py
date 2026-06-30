"""Meta business logic: dataset counts, feature column count, last-build timestamp."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.repositories.store import DATASETS, DataStore


def _iso(mtime: Optional[float]) -> Optional[str]:
    if mtime is None:
        return None
    return datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()


def _count(store: DataStore, name: str) -> Optional[int]:
    try:
        obj = store.load(name)
    except Exception:
        return None
    if isinstance(obj, dict):
        if isinstance(obj.get("players"), list):
            return len(obj["players"])
        if isinstance(obj.get("teams"), dict):
            return len(obj["teams"])
    return None


def get_meta(store: DataStore) -> Dict[str, Any]:
    datasets: Dict[str, Any] = {}
    mtimes = []
    for name in DATASETS:
        mt = store.mtime(name)
        if mt is not None:
            mtimes.append(mt)
        datasets[name] = {
            "available": store.available()[name],
            "count": _count(store, name),
            "last_modified": _iso(mt),
        }

    feature_cols: Optional[int] = None
    try:
        feats = store.load("features")
        cols = (feats.get("meta") or {}).get("cols")
        if isinstance(cols, list):
            feature_cols = len(cols)
    except Exception:
        feature_cols = None

    last_build = _iso(max(mtimes)) if mtimes else None
    return {"datasets": datasets, "feature_columns": feature_cols, "last_build": last_build}
