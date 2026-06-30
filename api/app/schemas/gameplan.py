"""Response models for gameplan endpoints. These pass through pipeline shapes
(arbitrary nested content) so the API never silently drops gameplan fields."""
from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class TiersResponse(BaseModel):
    data: List[Dict[str, Any]] = Field(default_factory=list, description="Draft tiers (each with players[]).")
    count: int


class StacksResponse(BaseModel):
    data: List[Dict[str, Any]] = Field(default_factory=list, description="Correlation stacks.")
    count: int


class TeamPriorityResponse(BaseModel):
    data: List[Dict[str, Any]] = Field(default_factory=list, description="Team attack-priority ranking.")
    count: int
