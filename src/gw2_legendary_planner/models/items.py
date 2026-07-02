from __future__ import annotations

from pydantic import Field

from gw2_legendary_planner.models.account import ApiModel


class ItemMetadata(ApiModel):
    id: int
    name: str
    rarity: str | None = None
    type: str | None = None
    icon: str | None = None
    flags: list[str] = Field(default_factory=list)
