from __future__ import annotations

import json
from importlib import resources
from typing import Literal

from pydantic import BaseModel, Field

from gw2_legendary_planner.inventory.models import Inventory, InventoryLocation
from gw2_legendary_planner.models.snapshot import AccountSnapshot

FocusKind = Literal["item", "currency"]


class FocusDefinition(BaseModel):
    id: int
    kind: FocusKind
    name: str
    category: str
    note: str | None = None
    tags: list[str] = Field(default_factory=list)


class FocusEntry(BaseModel):
    id: int
    kind: FocusKind
    name: str
    category: str
    quantity: int
    locations: list[InventoryLocation] = Field(default_factory=list)
    note: str | None = None
    tags: list[str] = Field(default_factory=list)

    @property
    def is_present(self) -> bool:
        return self.quantity > 0


def load_focus_definitions() -> list[FocusDefinition]:
    data_path = resources.files("gw2_legendary_planner.data").joinpath("legendary_focus_items.json")
    return [
        FocusDefinition.model_validate(entry)
        for entry in json.loads(data_path.read_text(encoding="utf-8"))
    ]


def build_legendary_focus_report(
    snapshot: AccountSnapshot,
    inventory: Inventory,
    *,
    definitions: list[FocusDefinition] | None = None,
    include_zero: bool = True,
) -> list[FocusEntry]:
    """Summarize high-signal legendary materials and currencies."""

    report: list[FocusEntry] = []
    for definition in definitions or load_focus_definitions():
        if definition.kind == "currency":
            quantity = snapshot.wallet_value(definition.id)
            locations = [
                InventoryLocation(source="wallet", quantity=quantity)
            ] if quantity else []
        else:
            aggregated = inventory.items.get(definition.id)
            quantity = aggregated.quantity if aggregated else 0
            locations = aggregated.locations if aggregated else []

        if quantity or include_zero:
            report.append(
                FocusEntry(
                    id=definition.id,
                    kind=definition.kind,
                    name=definition.name,
                    category=definition.category,
                    quantity=quantity,
                    locations=locations,
                    note=definition.note,
                    tags=definition.tags,
                )
            )
    return report
