from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from gw2_legendary_planner.models.account import (
    Account,
    AccountAchievementEntry,
    Character,
    ItemStack,
    LegendaryArmoryEntry,
    MaterialStorageEntry,
    WalletEntry,
)


class AccountSnapshot(BaseModel):
    """Normalized account payload from either local exports or the live GW2 API."""

    account: Account = Field(default_factory=Account)
    wallet: list[WalletEntry] = Field(default_factory=list)
    achievements: list[AccountAchievementEntry] = Field(default_factory=list)
    materials: list[MaterialStorageEntry] = Field(default_factory=list)
    bank: list[ItemStack | None] = Field(default_factory=list)
    shared_inventory: list[ItemStack | None] = Field(default_factory=list)
    legendary_armory: list[LegendaryArmoryEntry] = Field(default_factory=list)
    characters: list[Character] = Field(default_factory=list)

    @classmethod
    def from_raw(cls, payloads: dict[str, Any]) -> AccountSnapshot:
        """Build a snapshot from raw endpoint payloads."""

        return cls(
            account=Account.model_validate(payloads.get("account") or {}),
            wallet=[WalletEntry.model_validate(entry) for entry in payloads.get("wallet") or []],
            achievements=[
                AccountAchievementEntry.model_validate(entry)
                for entry in payloads.get("achievements") or []
                if entry
            ],
            materials=[
                MaterialStorageEntry.model_validate(entry)
                for entry in payloads.get("materials") or []
                if entry
            ],
            bank=[
                ItemStack.model_validate(entry) if entry else None
                for entry in payloads.get("bank") or []
            ],
            shared_inventory=[
                ItemStack.model_validate(entry) if entry else None
                for entry in payloads.get("shared_inventory") or []
            ],
            legendary_armory=[
                LegendaryArmoryEntry.model_validate(entry)
                for entry in payloads.get("legendary_armory") or []
                if entry
            ],
            characters=[
                Character.model_validate(entry)
                for entry in payloads.get("characters") or []
                if entry
            ],
        )

    def wallet_value(self, currency_id: int) -> int:
        return sum(entry.value for entry in self.wallet if entry.id == currency_id)

    def achievement_entry(self, achievement_id: int) -> AccountAchievementEntry | None:
        return next(
            (entry for entry in self.achievements if entry.id == achievement_id),
            None,
        )

    def achievement_current(self, achievement_id: int) -> int:
        entry = self.achievement_entry(achievement_id)
        if entry is None:
            return 0
        if entry.done and entry.max is not None:
            return entry.max
        if entry.current is not None:
            return entry.current
        return 1 if entry.done else 0

    def achievement_done(self, achievement_id: int) -> bool:
        entry = self.achievement_entry(achievement_id)
        if entry is None:
            return False
        if entry.done:
            return True
        if entry.current is not None and entry.max is not None:
            return entry.current >= entry.max
        return False
