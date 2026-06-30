"""Shared response models: error envelope + pagination."""
from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Machine-readable error code.")
    message: str = Field(..., description="Human-readable message.")
    details: List[Any] = Field(default_factory=list, description="Optional field-level details.")


class ErrorEnvelope(BaseModel):
    """The single shape every error response takes."""
    error: ErrorDetail
    request_id: Optional[str] = Field(None, description="Correlates with the X-Request-ID header.")


class Pagination(BaseModel):
    page: int = Field(..., ge=1, description="Current page (1-based).")
    page_size: int = Field(..., ge=1, description="Items per page.")
    total: int = Field(..., ge=0, description="Total items matching the query.")
    total_pages: int = Field(..., ge=0, description="Total number of pages.")
