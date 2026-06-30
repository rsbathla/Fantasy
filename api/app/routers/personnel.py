"""Personnel routes: all-team summary + per-team detail."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.deps import get_store, team_code
from app.repositories.store import DataStore
from app.schemas.personnel import PersonnelDetail, PersonnelListResponse
from app.services import personnel_service

router = APIRouter(tags=["personnel"])


@router.get("/personnel", response_model=PersonnelListResponse, summary="All-team personnel summary")
def list_personnel(store: DataStore = Depends(get_store)) -> PersonnelListResponse:
    return PersonnelListResponse(**personnel_service.list_personnel(store))


@router.get("/personnel/{team}", response_model=PersonnelDetail, summary="Team personnel detail or 404")
def get_personnel(
    team: str = Depends(team_code),
    store: DataStore = Depends(get_store),
) -> PersonnelDetail:
    return PersonnelDetail.model_validate(personnel_service.get_personnel(store, team))
