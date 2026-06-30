"""Personnel business logic: all-team summary + per-team detail."""
from __future__ import annotations

from typing import Any, Dict, List

from app.errors import NotFound
from app.repositories.store import DataStore


def list_personnel(store: DataStore) -> Dict[str, Any]:
    teams = store.teams("personnel")
    rows: List[Dict[str, Any]] = []
    for code, t in teams.items():
        off = t.get("offense") or {}
        rows.append({
            "team": t.get("team", code),
            "name": t.get("name"),
            "vac_tgt": off.get("vac_tgt"),
            "d_pa": off.get("d_pa"),
            "volume_shift": off.get("volume_shift"),
            "n_departures": len(off.get("departures") or []),
            "n_arrivals": len(off.get("arrivals") or []),
            "n_beneficiaries": len(off.get("beneficiaries") or []),
        })
    rows.sort(key=lambda r: r["team"])
    return {"data": rows, "count": len(rows)}


def get_personnel(store: DataStore, team: str) -> Dict[str, Any]:
    teams = store.teams("personnel")
    t = teams.get(team)
    if t is None:
        raise NotFound(f"No personnel record for team '{team}'.", code="team_not_found")
    return t
