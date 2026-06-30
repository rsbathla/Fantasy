"""Meta + health routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.deps import get_store
from app.repositories.store import DataStore
from app.schemas.meta import MetaResponse
from app.services import meta_service

router = APIRouter(tags=["meta"])


@router.get("/meta", response_model=MetaResponse, summary="Dataset counts, feature columns, last build")
def get_meta(store: DataStore = Depends(get_store)) -> MetaResponse:
    return MetaResponse(**meta_service.get_meta(store))
