from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field


class Settings(BaseModel):
    api_key: str | None = None
    cache_dir: Path = Field(
        default_factory=lambda: Path.home() / ".cache" / "gw2-legendary-planner"
    )
    cache_ttl_seconds: int = 3600

    @classmethod
    def from_environment(cls) -> Settings:
        return cls(
            api_key=os.getenv("GW2PLANNER_API_KEY") or os.getenv("GW2_API_KEY"),
            cache_dir=Path(
                os.getenv("GW2PLANNER_CACHE_DIR", Path.home() / ".cache" / "gw2-legendary-planner")
            ),
            cache_ttl_seconds=int(os.getenv("GW2PLANNER_CACHE_TTL_SECONDS", "3600")),
        )
