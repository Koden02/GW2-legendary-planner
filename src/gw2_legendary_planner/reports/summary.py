from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field

from gw2_legendary_planner.constants import COIN_CURRENCY_ID, GEM_CURRENCY_ID
from gw2_legendary_planner.inventory.models import Inventory
from gw2_legendary_planner.models.snapshot import AccountSnapshot


class CharacterSummary(BaseModel):
    name: str
    profession: str | None = None
    level: int | None = None


class CraftingSummary(BaseModel):
    character: str
    discipline: str
    rating: int
    active: bool


class AccountSummary(BaseModel):
    account_name: str | None = None
    gold: Decimal = Decimal("0")
    copper: int = 0
    gems: int = 0
    characters: list[CharacterSummary] = Field(default_factory=list)
    crafting_disciplines: list[CraftingSummary] = Field(default_factory=list)
    legendary_armory_entries: int = 0
    legendary_armory_total: int = 0
    unique_item_count: int = 0
    total_item_count: int = 0


def build_account_summary(snapshot: AccountSnapshot, inventory: Inventory) -> AccountSummary:
    copper = snapshot.wallet_value(COIN_CURRENCY_ID)
    characters = [
        CharacterSummary(
            name=character.name,
            profession=character.profession,
            level=character.level,
        )
        for character in snapshot.characters
    ]
    crafting = [
        CraftingSummary(
            character=character.name,
            discipline=discipline.discipline,
            rating=discipline.rating,
            active=discipline.active,
        )
        for character in snapshot.characters
        for discipline in character.crafting
    ]
    return AccountSummary(
        account_name=snapshot.account.name,
        gold=Decimal(copper) / Decimal(10_000),
        copper=copper,
        gems=snapshot.wallet_value(GEM_CURRENCY_ID),
        characters=characters,
        crafting_disciplines=crafting,
        legendary_armory_entries=len(snapshot.legendary_armory),
        legendary_armory_total=sum(entry.count for entry in snapshot.legendary_armory),
        unique_item_count=inventory.unique_item_count,
        total_item_count=inventory.total_item_count,
    )
