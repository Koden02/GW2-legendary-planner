from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    """Base model for GW2 API payloads.

    ArenaNet occasionally adds fields to API responses. The planner should accept
    those fields without needing a release every time the API grows.
    """

    model_config = ConfigDict(extra="allow")


class Account(ApiModel):
    id: str | None = None
    name: str | None = None
    world: int | None = None
    created: str | None = None
    access: list[str] = Field(default_factory=list)
    commander: bool | None = None
    fractal_level: int | None = None
    daily_ap: int | None = None
    monthly_ap: int | None = None
    wvw_rank: int | None = None


class WalletEntry(ApiModel):
    id: int
    value: int = 0


class ItemStack(ApiModel):
    id: int
    count: int = 1
    charges: int | None = None
    binding: str | None = None
    bound_to: str | None = None


class MaterialStorageEntry(ApiModel):
    id: int
    category: int | None = None
    binding: str | None = None
    count: int = 0


class Bag(ApiModel):
    id: int | None = None
    size: int | None = None
    inventory: list[ItemStack | None] = Field(default_factory=list)


class CraftingDiscipline(ApiModel):
    discipline: str
    rating: int = 0
    active: bool = False


class Character(ApiModel):
    name: str
    race: str | None = None
    profession: str | None = None
    level: int | None = None
    crafting: list[CraftingDiscipline] = Field(default_factory=list)
    bags: list[Bag | None] = Field(default_factory=list)
    equipment: list[ItemStack | None] = Field(default_factory=list)


class LegendaryArmoryEntry(ApiModel):
    id: int
    count: int = 0
