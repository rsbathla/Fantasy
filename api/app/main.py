"""Application factory.

Wires: CORS, request-id + response-time middleware, the unified exception handlers,
all routers under /api/v1 (health is unprefixed), and OpenAPI metadata/tags.

LIGHTWEIGHT: this module + everything it imports avoids pandas and the pipeline's
core.py. The only place the pipeline (pandas) runs is the SEPARATE subprocess
launched by the rebuild route.
"""
from __future__ import annotations

import time
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app import __version__
from app.config import Settings, get_settings
from app.errors import register_exception_handlers
from app.repositories.store import DataStore
from app.routers import admin, defense, gameplan, meta, personnel, players
from app.services.rebuild_service import RebuildManager, RunnerFn, subprocess_runner

API_PREFIX = "/api/v1"

OPENAPI_TAGS = [
    {"name": "meta", "description": "Dataset inventory, counts, and last-build timestamps."},
    {"name": "players", "description": "Player summaries (fusion+dfs join), profiles, fusion votes, DFS reads."},
    {"name": "defense", "description": "2026 team defense profiles and contributor/move detail."},
    {"name": "gameplan", "description": "Draft tiers, correlation stacks, and team attack priority."},
    {"name": "personnel", "description": "Off-season personnel changes by team."},
    {"name": "admin", "description": "Guarded background pipeline rebuild (API key required)."},
]

DESCRIPTION = (
    "Read API over the football-analytics pipeline's JSON outputs, plus one guarded "
    "background rebuild. The web process is lightweight (JSON only, no pandas); the "
    "rebuild runs the pipeline in a separate process."
)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assign/propagate X-Request-ID and add X-Response-Time-ms to every response."""

    async def dispatch(self, request, call_next):
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.state.request_id = rid
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        response.headers["X-Request-ID"] = rid
        response.headers["X-Response-Time-ms"] = f"{elapsed_ms:.2f}"
        return response


def create_app(settings: Settings | None = None, rebuild_runner: RunnerFn | None = None) -> FastAPI:
    """Build the app. `rebuild_runner` is injectable so tests mock the pipeline."""
    settings = settings or get_settings()

    app = FastAPI(
        title="BestBall Analytics API",
        version=__version__,
        description=DESCRIPTION,
        openapi_tags=OPENAPI_TAGS,
    )

    # --- shared singletons on app.state ---
    app.state.settings = settings
    app.state.store = DataStore(settings.DATA_DIR)
    app.state.rebuild_manager = RebuildManager(
        cmd=list(settings.PIPELINE_CMD),
        cwd=settings.DATA_DIR,
        runner=rebuild_runner or subprocess_runner,
    )

    # --- middleware (request id + timing) ---
    app.add_middleware(RequestContextMiddleware)

    # --- CORS (permissive default for local dev; LOCK DOWN in prod via CORS_ORIGINS) ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Response-Time-ms"],
    )

    # --- exception handlers (one envelope for everything) ---
    register_exception_handlers(app)

    # --- routes ---
    @app.get("/health", tags=["meta"], summary="Liveness probe")
    def health():
        return {"status": "ok"}

    app.include_router(meta.router, prefix=API_PREFIX)
    app.include_router(players.router, prefix=API_PREFIX)
    app.include_router(defense.router, prefix=API_PREFIX)
    app.include_router(gameplan.router, prefix=API_PREFIX)
    app.include_router(personnel.router, prefix=API_PREFIX)
    app.include_router(admin.router, prefix=API_PREFIX)

    return app


# module-level app for `uvicorn app.main:app`
app = create_app()
