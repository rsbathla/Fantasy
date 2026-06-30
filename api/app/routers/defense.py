"""Defense routes: 32-team list (sortable) + team detail."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.deps import get_store, team_code
from app.repositories.store import DataStore
from app.schemas.defense import DefenseDetail, DefenseListResponse, DefenseSortLiteral, OrderLiteral
from app.services import defense_service

router = APIRouter(tags=["defense"])


@router.get("/defense", response_model=DefenseListResponse, summary="32 team defense profiles")
def list_defense(
    store: DataStore = Depends(get_store),
    sort: DefenseSortLiteral = Query("pass_cov", description="Sort field."),
    order: OrderLiteral = Query("desc"),
) -> DefenseListResponse:
    return DefenseListResponse(**defense_service.list_defense(store, sort=sort, order=order))


@router.get("/defense/{team}", response_model=DefenseDetail, summary="Team defense detail or 404")
def get_defense(
    team: str = Depends(team_code),
    store: DataStore = Depends(get_store),
) -> DefenseDetail:
    return DefenseDetail.model_validate(defense_service.get_defense(store, team))
