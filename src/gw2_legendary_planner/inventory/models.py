from __future__ import annotations

from collections.abc import Iterator

from pydantic import BaseModel, Field


class InventoryLocation(BaseModel):
    source: str
    quantity: int
    character: str | None = None
    bag_index: int | None = None
    slot: int | None = None
    container_item_id: int | None = None


class AggregatedItem(BaseModel):
    item_id: int
    quantity: int = 0
    locations: list[InventoryLocation] = Field(default_factory=list)

    def add_location(self, location: InventoryLocation) -> None:
        self.quantity += location.quantity
        self.locations.append(location)


class Inventory(BaseModel):
    items: dict[int, AggregatedItem] = Field(default_factory=dict)

    @property
    def unique_item_count(self) -> int:
        return len(self.items)

    @property
    def total_item_count(self) -> int:
        return sum(item.quantity for item in self.items.values())

    def add(self, item_id: int, quantity: int, location: InventoryLocation) -> None:
        if quantity <= 0:
            return
        entry = self.items.setdefault(item_id, AggregatedItem(item_id=item_id))
        entry.add_location(location)

    def get_item(self, item_id: int) -> AggregatedItem | None:
        return self.items.get(item_id)

    def iter_items(self) -> Iterator[AggregatedItem]:
        return iter(self.items.values())

    def item_ids(self) -> list[int]:
        return sorted(self.items)

    def has_item(self, item_id: int) -> bool:
        return item_id in self.items

    def quantity_for(self, item_id: int) -> int:
        entry = self.items.get(item_id)
        return entry.quantity if entry else 0

    def locations_for(self, item_id: int) -> list[InventoryLocation]:
        entry = self.items.get(item_id)
        return list(entry.locations) if entry else []

    def characters_holding(self, item_id: int) -> list[str]:
        return sorted(
            {
                location.character
                for location in self.locations_for(item_id)
                if location.character
            }
        )

    def sources_for(self, item_id: int) -> list[str]:
        return sorted({location.source for location in self.locations_for(item_id)})
