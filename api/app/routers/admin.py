"""Admin routes: guarded background rebuild + job status. Require X-API-Key."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Path, status

from app.deps import get_rebuild_manager, require_api_key
from app.schemas.admin import JobView, RebuildAccepted
from app.services.rebuild_service import RebuildManager

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_api_key)])


@router.post(
    "/rebuild",
    response_model=RebuildAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start a background pipeline rebuild (one at a time)",
)
def start_rebuild(manager: RebuildManager = Depends(get_rebuild_manager)) -> RebuildAccepted:
    job = manager.start()  # raises Conflict(409) if one is already running
    # The job is accepted in the "queued" state; the worker thread may have already
    # advanced it to "running" by now, but the POST contract reports acceptance.
    return RebuildAccepted(job_id=job.job_id, status="queued")


@router.get("/jobs/{job_id}", response_model=JobView, summary="Rebuild job status or 404")
def get_job(
    job_id: str = Path(..., min_length=1),
    manager: RebuildManager = Depends(get_rebuild_manager),
) -> JobView:
    return JobView(**manager.get(job_id).view())
