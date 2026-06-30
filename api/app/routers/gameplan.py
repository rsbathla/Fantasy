"""Gameplan routes: tiers, stacks, team-priority."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.deps import get_store
from app.repositories.store import DataStore
from app.schemas.gameplan import StacksResponse, TeamPriorityResponse, TiersResponse
from app.services import gameplan_service

router = APIRouter(prefix="/gameplan", tags=["gameplan"])


@router.get("/tiers", response_model=TiersResponse, summary="Draft tiers")
def get_tiers(store: DataStore = Depends(get_store)) -> TiersResponse:
    return TiersResponse(**gameplan_service.tiers(store))


@router.get("/stacks", response_model=StacksResponse, summary="Correlation stacks")
def get_stacks(store: DataStore = Depends(get_store)) -> StacksResponse:
    return StacksResponse(**gameplan_service.stacks(store))


@router.get("/team-priority", response_model=TeamPriorityResponse, summary="Team attack priority")
def get_team_priority(store: DataStore = Depends(get_store)) -> TeamPriorityResponse:
    return TeamPriorityResponse(**gameplan_service.team_priority(store))
