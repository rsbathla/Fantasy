"""Request + response models for player-facing endpoints (players/fusion/dfs)."""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Pagination

PosLiteral = Literal["ALL", "QB", "RB", "WR", "TE"]
OrderLiteral = Literal["asc", "desc"]
PlayerSortLiteral = Literal["consensus", "divergence", "adp", "name"]
DfsSortLiteral = Literal["ceiling_consensus", "ceiling_divergence", "p_w17", "adp", "name"]
FusionSortLiteral = Literal["consensus", "divergence", "adp", "name"]


# ---- response models ---------------------------------------------------------

class PlayerSummary(BaseModel):
    """Joined fusion + dfs summary for the list endpoint."""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Stable URL-safe player id (slug).")
    name: str
    pos: str
    team: Optional[str] = None
    adp: Optional[float] = None
    consensus: Optional[float] = Field(None, description="Fusion consensus (mean of model votes).")
    divergence: Optional[float] = Field(None, description="Fusion divergence (std of votes); the signal.")
    flags: List[str] = Field(default_factory=list)
    ceiling_consensus: Optional[float] = Field(None, description="DFS ceiling consensus, if available.")
    p_w17: Optional[float] = Field(None, description="DFS week-17 advance probability, if available.")
    profile: Optional[str] = Field(None, description="DFS archetype label, if available.")


class PlayerProfile(BaseModel):
    """Full single-player profile: fusion models + dfs sources + flags."""
    id: str
    name: str
    pos: str
    team: Optional[str] = None
    adp: Optional[float] = None
    # fusion side
    consensus: Optional[float] = None
    divergence: Optional[float] = None
    models: Dict[str, Any] = Field(default_factory=dict, description="Per-model fusion votes (within-pos percentiles).")
    flags: List[str] = Field(default_factory=list)
    # dfs side (may be absent if the player has no DFS row)
    dfs: Optional["DfsRecord"] = Field(None, description="DFS scenario read, if the player has one.")


class DfsRecord(BaseModel):
    """A DFS scenario read for a player."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    pos: str
    team: Optional[str] = None
    sources: Dict[str, Any] = Field(default_factory=dict)
    ceiling_consensus: Optional[float] = None
    ceiling_divergence: Optional[float] = None
    n_sources: Optional[int] = None
    p_w15: Optional[float] = None
    p_w16: Optional[float] = None
    p_w17: Optional[float] = None
    profile: Optional[str] = None
    drivers: Optional[Dict[str, Any]] = None


class FusionRecord(BaseModel):
    """A raw fusion vote record."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    pos: str
    team: Optional[str] = None
    adp: Optional[float] = None
    models: Dict[str, Any] = Field(default_factory=dict)
    consensus: Optional[float] = None
    divergence: Optional[float] = None
    flags: List[str] = Field(default_factory=list)


class PlayerListResponse(BaseModel):
    data: List[PlayerSummary]
    pagination: Pagination


class DfsListResponse(BaseModel):
    data: List[DfsRecord]
    pagination: Pagination


class FusionListResponse(BaseModel):
    data: List[FusionRecord]
    pagination: Pagination


PlayerProfile.model_rebuild()
