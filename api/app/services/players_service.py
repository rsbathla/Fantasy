"""Player-facing business logic: join fusion + dfs by slug, then filter/sort/paginate.

The join key is slugify(name). fusion is the spine (it carries adp + flags); dfs is
attached when a matching slug exists.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.errors import NotFound
from app.repositories.store import DataStore
from app.services.query import filter_players, paginate, sort_rows
from app.util import slugify

# API sort token -> underlying field on the joined row
_PLAYER_SORT = {
    "consensus": "consensus",
    "divergence": "divergence",
    "adp": "adp",
    "name": "name",
}
_DFS_SORT = {
    "ceiling_consensus": "ceiling_consensus",
    "ceiling_divergence": "ceiling_divergence",
    "p_w17": "p_w17",
    "adp": "adp",
    "name": "name",
}
_FUSION_SORT = {
    "consensus": "consensus",
    "divergence": "divergence",
    "adp": "adp",
    "name": "name",
}


def _index_by_slug(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        sid = slugify(r.get("name", ""))
        if sid and sid not in out:  # first writer wins (names are unique in practice)
            out[sid] = r
    return out


def _summary_row(fusion_row: Dict[str, Any], dfs_row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    sid = slugify(fusion_row.get("name", ""))
    return {
        "id": sid,
        "name": fusion_row.get("name"),
        "pos": fusion_row.get("pos"),
        "team": fusion_row.get("team"),
        "adp": fusion_row.get("adp"),
        "consensus": fusion_row.get("consensus"),
        "divergence": fusion_row.get("divergence"),
        "flags": fusion_row.get("flags") or [],
        "ceiling_consensus": (dfs_row or {}).get("ceiling_consensus"),
        "p_w17": (dfs_row or {}).get("p_w17"),
        "profile": (dfs_row or {}).get("profile"),
    }


def list_players(
    store: DataStore,
    *,
    pos: str,
    q: Optional[str],
    flag: Optional[str],
    min_consensus: Optional[float],
    sort: str,
    order: str,
    page: int,
    page_size: int,
) -> Dict[str, Any]:
    fusion_rows = store.players("fusion")
    dfs_by_slug = _index_by_slug(store.players("dfs"))

    joined = [_summary_row(fr, dfs_by_slug.get(slugify(fr.get("name", "")))) for fr in fusion_rows]
    filtered = filter_players(
        joined, pos=pos, q=q, flag=flag, min_consensus=min_consensus, consensus_key="consensus"
    )
    ordered = sort_rows(filtered, _PLAYER_SORT[sort], order)
    page_rows, pg = paginate(ordered, page, page_size)
    return {"data": page_rows, "pagination": pg}


def get_player(store: DataStore, player_id: str) -> Dict[str, Any]:
    """Full profile (fusion models + dfs sources + flags) or NotFound."""
    fusion_by_slug = _index_by_slug(store.players("fusion"))
    fusion_row = fusion_by_slug.get(player_id)
    if fusion_row is None:
        raise NotFound(f"No player with id '{player_id}'.", code="player_not_found")

    dfs_by_slug = _index_by_slug(store.players("dfs"))
    dfs_row = dfs_by_slug.get(player_id)

    dfs_payload = None
    if dfs_row is not None:
        dfs_payload = {
            "id": player_id,
            "name": dfs_row.get("name"),
            "pos": dfs_row.get("pos"),
            "team": dfs_row.get("team"),
            "sources": dfs_row.get("sources") or {},
            "ceiling_consensus": dfs_row.get("ceiling_consensus"),
            "ceiling_divergence": dfs_row.get("ceiling_divergence"),
            "n_sources": dfs_row.get("n_sources"),
            "p_w15": dfs_row.get("p_w15"),
            "p_w16": dfs_row.get("p_w16"),
            "p_w17": dfs_row.get("p_w17"),
            "profile": dfs_row.get("profile"),
            "drivers": dfs_row.get("drivers"),
        }

    return {
        "id": player_id,
        "name": fusion_row.get("name"),
        "pos": fusion_row.get("pos"),
        "team": fusion_row.get("team"),
        "adp": fusion_row.get("adp"),
        "consensus": fusion_row.get("consensus"),
        "divergence": fusion_row.get("divergence"),
        "models": fusion_row.get("models") or {},
        "flags": fusion_row.get("flags") or [],
        "dfs": dfs_payload,
    }


def list_dfs(
    store: DataStore,
    *,
    pos: str,
    q: Optional[str],
    sort: str,
    order: str,
    page: int,
    page_size: int,
) -> Dict[str, Any]:
    rows = []
    for r in store.players("dfs"):
        row = dict(r)
        row["id"] = slugify(r.get("name", ""))
        rows.append(row)
    filtered = filter_players(rows, pos=pos, q=q)
    ordered = sort_rows(filtered, _DFS_SORT[sort], order)
    page_rows, pg = paginate(ordered, page, page_size)
    return {"data": page_rows, "pagination": pg}


def list_fusion(
    store: DataStore,
    *,
    pos: str,
    q: Optional[str],
    flag: Optional[str],
    min_consensus: Optional[float],
    sort: str,
    order: str,
    page: int,
    page_size: int,
) -> Dict[str, Any]:
    rows = []
    for r in store.players("fusion"):
        row = dict(r)
        row["id"] = slugify(r.get("name", ""))
        rows.append(row)
    filtered = filter_players(
        rows, pos=pos, q=q, flag=flag, min_consensus=min_consensus, consensus_key="consensus"
    )
    ordered = sort_rows(filtered, _FUSION_SORT[sort], order)
    page_rows, pg = paginate(ordered, page, page_size)
    return {"data": page_rows, "pagination": pg}
