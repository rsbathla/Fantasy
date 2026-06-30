"""Defense business logic: 32 team profiles, sortable; detail with contributors+moves."""
from __future__ import annotations

from typing import Any, Dict, List

from app.errors import NotFound
from app.repositories.store import DataStore
from app.schemas.defense import DEFENSE_SORT_FIELDS
from app.services.query import sort_rows

_SUMMARY_FIELDS = [
    "team",
    "pass_cov_pctl_2026", "pass_rush_pctl_2026", "run_def_pctl_2026",
    "pass_cov_pctl_2025", "pass_rush_pctl_2025", "run_def_pctl_2025",
]


def list_defense(store: DataStore, *, sort: str, order: str) -> Dict[str, Any]:
    teams = store.teams("defense")
    rows: List[Dict[str, Any]] = []
    for code, t in teams.items():
        row = {k: t.get(k) for k in _SUMMARY_FIELDS}
        row["team"] = t.get("team", code)
        rows.append(row)

    if sort == "team":
        ordered = sort_rows(rows, "team", order)
    else:
        ordered = sort_rows(rows, DEFENSE_SORT_FIELDS[sort], order)
    return {"data": ordered, "count": len(ordered)}


def get_defense(store: DataStore, team: str) -> Dict[str, Any]:
    teams = store.teams("defense")
    t = teams.get(team)
    if t is None:
        raise NotFound(f"No defense profile for team '{team}'.", code="team_not_found")
    return t  # full record; response model selects + aliases fields
