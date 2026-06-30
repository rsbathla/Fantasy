"""Response models for the guarded rebuild + job-status endpoints."""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

JobStatus = Literal["queued", "running", "succeeded", "failed"]


class RebuildAccepted(BaseModel):
    job_id: str
    status: JobStatus = Field("queued")


class JobView(BaseModel):
    job_id: str
    status: JobStatus
    started_at: Optional[str] = Field(None, description="ISO-8601 UTC.")
    finished_at: Optional[str] = Field(None, description="ISO-8601 UTC.")
    returncode: Optional[int] = None
    log_tail: List[str] = Field(default_factory=list, description="Last lines of combined stdout/stderr.")
