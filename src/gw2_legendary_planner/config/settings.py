from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field


class Settings(BaseModel):
    api_key: str | None = None
    config_dir: Path = Field(
        default_factory=lambda: Path.home() / ".config" / "gw2-legendary-planner"
    )
    profile_file: Path = Field(
        default_factory=lambda: Path.home()
        / ".config"
        / "gw2-legendary-planner"
        / "profiles.json"
    )
    cache_dir: Path = Field(
        default_factory=lambda: Path.home() / ".cache" / "gw2-legendary-planner"
    )
    cache_ttl_seconds: int = 3600

    @classmethod
    def from_environment(cls) -> Settings:
        config_dir = Path(
            os.getenv(
                "GW2PLANNER_CONFIG_DIR",
                Path.home() / ".config" / "gw2-legendary-planner",
            )
        )
        return cls(
            api_key=os.getenv("GW2PLANNER_API_KEY") or os.getenv("GW2_API_KEY"),
            config_dir=config_dir,
            profile_file=Path(
                os.getenv("GW2PLANNER_PROFILE_FILE", config_dir / "profiles.json")
            ),
            cache_dir=Path(
                os.getenv("GW2PLANNER_CACHE_DIR", Path.home() / ".cache" / "gw2-legendary-planner")
            ),
            cache_ttl_seconds=int(os.getenv("GW2PLANNER_CACHE_TTL_SECONDS", "3600")),
        )
