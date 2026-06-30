"""Request + response models for defense endpoints."""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

DefenseSortLiteral = Literal["pass_cov", "pass_rush", "run_def", "team"]
OrderLiteral = Literal["asc", "desc"]

# maps the API's sort token -> the underlying 2026 percentile field
DEFENSE_SORT_FIELDS: Dict[str, str] = {
    "pass_cov": "pass_cov_pctl_2026",
    "pass_rush": "pass_rush_pctl_2026",
    "run_def": "run_def_pctl_2026",
}


class DefenseSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    team: str
    pass_cov_pctl_2026: Optional[float] = None
    pass_rush_pctl_2026: Optional[float] = None
    run_def_pctl_2026: Optional[float] = None
    pass_cov_pctl_2025: Optional[float] = None
    pass_rush_pctl_2025: Optional[float] = None
    run_def_pctl_2025: Optional[float] = None


class DefenseContributor(BaseModel):
    name: str
    pos: Optional[str] = None
    ps: Optional[float] = Field(None, description="Points Saved (SIS).")
    epatgt: Optional[float] = None


class DefenseMove(BaseModel):
    player: str
    unit: Optional[str] = None
    from_team: Optional[str] = Field(None, alias="from")
    to_team: Optional[str] = Field(None, alias="to")
    ps: Optional[float] = None
    src: Optional[str] = None
    conf: Optional[bool] = None
    note: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class DefenseDetail(DefenseSummary):
    # full set of percentile/strength fields are passed through too
    pass_cov_strength_2026: Optional[float] = None
    pass_rush_strength_2026: Optional[float] = None
    run_def_strength_2026: Optional[float] = None
    top_coverage: List[DefenseContributor] = Field(default_factory=list)
    top_pass_rush: List[DefenseContributor] = Field(default_factory=list)
    top_run_def: List[DefenseContributor] = Field(default_factory=list)
    moves_2026: List[DefenseMove] = Field(default_factory=list)


class DefenseListResponse(BaseModel):
    data: List[DefenseSummary]
    count: int
