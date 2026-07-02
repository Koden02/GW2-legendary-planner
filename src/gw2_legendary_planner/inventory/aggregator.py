from __future__ import annotations

from gw2_legendary_planner.inventory.models import Inventory, InventoryLocation
from gw2_legendary_planner.models.account import ItemStack
from gw2_legendary_planner.models.snapshot import AccountSnapshot


class InventoryAggregator:
    """Flatten account inventory sources into account-wide item totals."""

    def aggregate(self, snapshot: AccountSnapshot) -> Inventory:
        inventory = Inventory()
        self._add_material_storage(snapshot, inventory)
        self._add_bank(snapshot, inventory)
        self._add_shared_inventory(snapshot, inventory)
        self._add_character_bags(snapshot, inventory)
        self._add_character_equipment(snapshot, inventory)
        return inventory

    def _add_material_storage(self, snapshot: AccountSnapshot, inventory: Inventory) -> None:
        for entry in snapshot.materials:
            inventory.add(
                entry.id,
                entry.count,
                InventoryLocation(source="material_storage", quantity=entry.count),
            )

    def _add_bank(self, snapshot: AccountSnapshot, inventory: Inventory) -> None:
        for slot, item in enumerate(snapshot.bank):
            self._add_stack(
                inventory,
                item,
                InventoryLocation(source="bank", quantity=item.count if item else 0, slot=slot),
            )

    def _add_shared_inventory(self, snapshot: AccountSnapshot, inventory: Inventory) -> None:
        for slot, item in enumerate(snapshot.shared_inventory):
            self._add_stack(
                inventory,
                item,
                InventoryLocation(
                    source="shared_inventory", quantity=item.count if item else 0, slot=slot
                ),
            )

    def _add_character_bags(self, snapshot: AccountSnapshot, inventory: Inventory) -> None:
        for character in snapshot.characters:
            for bag_index, bag in enumerate(character.bags):
                if not bag:
                    continue
                if bag.id:
                    inventory.add(
                        bag.id,
                        1,
                        InventoryLocation(
                            source="character_bag",
                            quantity=1,
                            character=character.name,
                            bag_index=bag_index,
                        ),
                    )
                for slot, item in enumerate(bag.inventory):
                    self._add_stack(
                        inventory,
                        item,
                        InventoryLocation(
                            source="character_inventory",
                            quantity=item.count if item else 0,
                            character=character.name,
                            bag_index=bag_index,
                            slot=slot,
                            container_item_id=bag.id,
                        ),
                    )

    def _add_character_equipment(self, snapshot: AccountSnapshot, inventory: Inventory) -> None:
        for character in snapshot.characters:
            for slot, item in enumerate(character.equipment):
                self._add_stack(
                    inventory,
                    item,
                    InventoryLocation(
                        source="character_equipment",
                        quantity=item.count if item else 0,
                        character=character.name,
                        slot=slot,
                    ),
                )

    def _add_stack(
        self,
        inventory: Inventory,
        item: ItemStack | None,
        location: InventoryLocation,
    ) -> None:
        if not item:
            return
        inventory.add(item.id, item.count, location)
