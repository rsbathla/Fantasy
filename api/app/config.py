"""Application settings (pydantic-settings).

All runtime config is centralized here and read from the environment (or a local
.env). Sensible local-dev defaults are provided so the service boots with zero
config, but anything security-relevant (REBUILD_API_KEY) is intentionally unset
by default so the rebuild route stays disabled until explicitly configured.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# repo root = two levels up from this file (api/app/config.py -> api -> repo root)
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BESTBALL_",
        env_file=".env",
        extra="ignore",
    )

    # Where the pipeline's JSON outputs live (the repo root).
    DATA_DIR: str = _REPO_ROOT

    # CORS. Default permissive for local dev.
    # PROD: lock this down to your dashboard origin(s), e.g. ["https://app.example.com"].
    CORS_ORIGINS: List[str] = ["*"]

    # Shared secret for the guarded rebuild route. If unset/empty, the rebuild
    # endpoint refuses to run (503 rebuild_disabled) instead of running unguarded.
    REBUILD_API_KEY: Optional[str] = None

    # The command used to (re)build the pipeline. Runs in a SEPARATE process with
    # cwd=DATA_DIR. This is where pandas/core.py actually load -- never in-process.
    PIPELINE_CMD: List[str] = ["python3", "refactor/pipeline.py"]

    # Pagination guard rail.
    MAX_PAGE_SIZE: int = 200

    @field_validator("CORS_ORIGINS", "PIPELINE_CMD", mode="before")
    @classmethod
    def _split_csv(cls, v):
        """Allow comma-separated env strings for list fields."""
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                return v  # let pydantic parse JSON-style lists
            return [part.strip() for part in v.split(",") if part.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
