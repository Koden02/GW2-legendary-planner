from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from gw2_legendary_planner.models.account import (
    Account,
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
