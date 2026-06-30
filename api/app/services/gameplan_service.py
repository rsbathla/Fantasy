"""Gameplan business logic: tiers, stacks, team-priority slices."""
from __future__ import annotations

from typing import Any, Dict, List

from app.repositories.store import DataStore


def _slice(store: DataStore, key: str) -> List[Dict[str, Any]]:
    data = store.load("gameplan").get(key, []) or []
    return data


def tiers(store: DataStore) -> Dict[str, Any]:
    data = _slice(store, "draft_tiers")
    return {"data": data, "count": len(data)}


def stacks(store: DataStore) -> Dict[str, Any]:
    data = _slice(store, "stacks")
    return {"data": data, "count": len(data)}


def team_priority(store: DataStore) -> Dict[str, Any]:
    data = _slice(store, "team_priority")
    return {"data": data, "count": len(data)}
