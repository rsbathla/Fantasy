"""Response models for the meta endpoint."""
from __future__ import annotations

from typing import Dict, Optional

from pydantic import BaseModel, Field


class DatasetInfo(BaseModel):
    available: bool
    count: Optional[int] = Field(None, description="Record count (players or teams), if applicable.")
    last_modified: Optional[str] = Field(None, description="ISO-8601 file mtime (UTC), or null if missing.")


class MetaResponse(BaseModel):
    datasets: Dict[str, DatasetInfo]
    feature_columns: Optional[int] = Field(None, description="Number of feature-store columns.")
    last_build: Optional[str] = Field(None, description="ISO-8601 newest dataset mtime (UTC) = last build.")
