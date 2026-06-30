"""FastAPI dependencies: shared singletons + validated query/path params + auth.

Singletons (DataStore, RebuildManager) are created once and stored on app.state in
the factory; these providers just hand them back. require_api_key does a
constant-time compare and disables the route entirely when no key is configured.
"""
from __future__ import annotations

import hmac
from typing import Optional

from fastapi import Depends, Path, Query, Request

from app.config import Settings, get_settings as _get_settings_singleton
from app.errors import ServiceUnavailable, Unauthorized
from app.repositories.store import DataStore
from app.services.rebuild_service import RebuildManager


def get_settings(request: Request) -> Settings:
    """Prefer the per-app settings stashed on app.state (so injected test settings
    win); fall back to the cached process singleton."""
    return getattr(request.app.state, "settings", None) or _get_settings_singleton()


def get_store(request: Request) -> DataStore:
    return request.app.state.store


def get_rebuild_manager(request: Request) -> RebuildManager:
    return request.app.state.rebuild_manager


# ---- pagination --------------------------------------------------------------

class Pagination:
    def __init__(self, page: int, page_size: int) -> None:
        self.page = page
        self.page_size = page_size


def pagination_params(
    settings: Settings = Depends(get_settings),
    page: int = Query(1, ge=1, description="Page number (1-based)."),
    page_size: int = Query(50, ge=1, description="Items per page."),
) -> Pagination:
    # Enforce MAX_PAGE_SIZE here (it depends on settings, so it can't be a static Query le=).
    max_size = settings.MAX_PAGE_SIZE
    if page_size > max_size:
        # raise as a validation error so it lands in the 422 envelope
        from fastapi.exceptions import RequestValidationError
        raise RequestValidationError([
            {
                "type": "less_than_equal",
                "loc": ("query", "page_size"),
                "msg": f"Input should be less than or equal to {max_size}",
                "input": page_size,
                "ctx": {"le": max_size},
            }
        ])
    return Pagination(page=page, page_size=page_size)


# ---- team path param ---------------------------------------------------------

def team_code(
    team: str = Path(..., pattern=r"^[A-Z]{2,3}$", description="NFL team code, e.g. KC, DET, LAR."),
) -> str:
    return team


# ---- auth --------------------------------------------------------------------

def require_api_key(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> None:
    """Guard the rebuild routes.

    - If no key is configured -> 503 rebuild_disabled (never run unguarded).
    - Else require X-API-Key to match via constant-time compare -> 401 otherwise.
    """
    configured = settings.REBUILD_API_KEY
    if not configured:
        raise ServiceUnavailable(
            "Rebuild is disabled: no REBUILD_API_KEY is configured.",
            code="rebuild_disabled",
        )
    provided: Optional[str] = request.headers.get("X-API-Key")
    if not provided or not hmac.compare_digest(provided, configured):
        raise Unauthorized("Missing or invalid API key.", code="invalid_api_key")
