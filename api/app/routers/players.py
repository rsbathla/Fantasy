"""Player routes: list summaries (fusion+dfs join), single profile, dfs, fusion."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Path, Query

from app.deps import Pagination, get_store, pagination_params
from app.repositories.store import DataStore
from app.schemas.players import (
    DfsListResponse,
    DfsSortLiteral,
    FusionListResponse,
    FusionSortLiteral,
    OrderLiteral,
    PlayerListResponse,
    PlayerProfile,
    PlayerSortLiteral,
    PosLiteral,
)
from app.services import players_service

router = APIRouter(tags=["players"])


@router.get("/players", response_model=PlayerListResponse, summary="Paginated player summaries (fusion+dfs)")
def list_players(
    store: DataStore = Depends(get_store),
    page: Pagination = Depends(pagination_params),
    pos: PosLiteral = Query("ALL", description="Position filter."),
    q: Optional[str] = Query(None, description="Case-insensitive substring search on name."),
    flag: Optional[str] = Query(None, description="Keep only players carrying this fusion flag."),
    min_consensus: Optional[float] = Query(None, ge=0, le=100, description="Minimum fusion consensus."),
    sort: PlayerSortLiteral = Query("consensus", description="Sort field."),
    order: OrderLiteral = Query("desc", description="Sort direction."),
) -> PlayerListResponse:
    result = players_service.list_players(
        store, pos=pos, q=q, flag=flag, min_consensus=min_consensus,
        sort=sort, order=order, page=page.page, page_size=page.page_size,
    )
    return PlayerListResponse(**result)


@router.get("/players/{player_id}", response_model=PlayerProfile, summary="Full player profile or 404")
def get_player(
    player_id: str = Path(..., min_length=1, description="Stable player slug, e.g. 'jamarr-chase'."),
    store: DataStore = Depends(get_store),
) -> PlayerProfile:
    return PlayerProfile(**players_service.get_player(store, player_id))


@router.get("/dfs", response_model=DfsListResponse, summary="Paginated DFS scenario reads")
def list_dfs(
    store: DataStore = Depends(get_store),
    page: Pagination = Depends(pagination_params),
    pos: PosLiteral = Query("ALL"),
    q: Optional[str] = Query(None, description="Case-insensitive substring search on name."),
    sort: DfsSortLiteral = Query("ceiling_consensus"),
    order: OrderLiteral = Query("desc"),
) -> DfsListResponse:
    result = players_service.list_dfs(
        store, pos=pos, q=q, sort=sort, order=order, page=page.page, page_size=page.page_size,
    )
    return DfsListResponse(**result)


@router.get("/fusion", response_model=FusionListResponse, summary="Paginated raw fusion votes")
def list_fusion(
    store: DataStore = Depends(get_store),
    page: Pagination = Depends(pagination_params),
    pos: PosLiteral = Query("ALL"),
    q: Optional[str] = Query(None, description="Case-insensitive substring search on name."),
    flag: Optional[str] = Query(None),
    min_consensus: Optional[float] = Query(None, ge=0, le=100),
    sort: FusionSortLiteral = Query("consensus"),
    order: OrderLiteral = Query("desc"),
) -> FusionListResponse:
    result = players_service.list_fusion(
        store, pos=pos, q=q, flag=flag, min_consensus=min_consensus,
        sort=sort, order=order, page=page.page, page_size=page.page_size,
    )
    return FusionListResponse(**result)
