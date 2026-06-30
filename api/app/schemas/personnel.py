"""Response models for personnel endpoints."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PersonnelSummary(BaseModel):
    team: str
    name: Optional[str] = None
    vac_tgt: Optional[float] = Field(None, description="Vacated 2025 target share (%).")
    d_pa: Optional[float] = Field(None, description="Projected change in pass attempts/g vs 2025.")
    volume_shift: Optional[str] = None
    n_departures: int = 0
    n_arrivals: int = 0
    n_beneficiaries: int = 0


class PersonnelListResponse(BaseModel):
    data: List[PersonnelSummary]
    count: int


class PersonnelDetail(BaseModel):
    """Full per-team personnel record, passed through from the pipeline."""
    team: str
    name: Optional[str] = None
    offense: Optional[Dict[str, Any]] = None
    defense: Optional[Dict[str, Any]] = None
    oline: Optional[Dict[str, Any]] = None
    coordinator: Optional[Dict[str, Any]] = None
