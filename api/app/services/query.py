"""Reusable filter / sort / paginate helpers shared by list services.

Keeps the same semantics everywhere: None values always sort LAST regardless of
order, search is case-insensitive substring on name, and pagination is computed
against the post-filter total.
"""
from __future__ import annotations

import math
from typing import Any, Callable, Dict, List, Optional, Tuple


def filter_players(
    rows: List[Dict[str, Any]],
    *,
    pos: str = "ALL",
    q: Optional[str] = None,
    flag: Optional[str] = None,
    min_consensus: Optional[float] = None,
    consensus_key: str = "consensus",
) -> List[Dict[str, Any]]:
    out = rows
    if pos and pos != "ALL":
        out = [r for r in out if (r.get("pos") or "").upper() == pos]
    if q:
        needle = q.strip().lower()
        if needle:
            out = [r for r in out if needle in (r.get("name") or "").lower()]
    if flag:
        out = [r for r in out if flag in (r.get("flags") or [])]
    if min_consensus is not None:
        out = [
            r for r in out
            if isinstance(r.get(consensus_key), (int, float)) and r[consensus_key] >= min_consensus
        ]
    return out


def _sort_key(field: str) -> Callable[[Dict[str, Any]], Tuple[int, Any]]:
    """Sort helper that pushes missing values to the end (stable for both orders)."""
    def key(row: Dict[str, Any]):
        v = row.get(field)
        if v is None:
            # (1, "") -> always after present values; second element keeps it total-orderable
            return (1, "")
        if isinstance(v, str):
            return (0, v.lower())
        return (0, v)
    return key


def sort_rows(rows: List[Dict[str, Any]], field: str, order: str) -> List[Dict[str, Any]]:
    reverse = order == "desc"
    present = [r for r in rows if r.get(field) is not None]
    missing = [r for r in rows if r.get(field) is None]
    present.sort(key=_sort_key(field), reverse=reverse)
    # missing always last, regardless of order
    return present + missing


def paginate(rows: List[Dict[str, Any]], page: int, page_size: int) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    total = len(rows)
    total_pages = math.ceil(total / page_size) if page_size else 0
    start = (page - 1) * page_size
    end = start + page_size
    page_rows = rows[start:end]
    meta = {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
    }
    return page_rows, meta
