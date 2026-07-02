from pathlib import Path

from gw2_legendary_planner.api.local import LocalExportLoader
from gw2_legendary_planner.inventory.aggregator import InventoryAggregator

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "exports"


def test_inventory_aggregates_all_supported_sources() -> None:
    snapshot = LocalExportLoader(FIXTURE_DIR).load()
    inventory = InventoryAggregator().aggregate(snapshot)

    assert inventory.quantity_for(19976) == 77
    assert inventory.quantity_for(19721) == 250
    assert inventory.quantity_for(19678) == 1
    assert inventory.quantity_for(19677) == 2
    assert inventory.quantity_for(19675) == 12
    assert inventory.quantity_for(8932) == 1
    assert inventory.quantity_for(19925) == 50
    assert inventory.quantity_for(29185) == 1
    assert inventory.quantity_for(29181) == 1
    assert inventory.unique_item_count == 9
    assert inventory.total_item_count == 395


def test_inventory_tracks_character_locations() -> None:
    snapshot = LocalExportLoader(FIXTURE_DIR).load()
    inventory = InventoryAggregator().aggregate(snapshot)

    dusk = inventory.items[29185]

    assert dusk.locations[0].source == "character_inventory"
    assert dusk.locations[0].character == "Ariadne Example"
    assert dusk.locations[0].bag_index == 0
    assert dusk.locations[0].slot == 1


def test_inventory_exposes_planner_friendly_query_api() -> None:
    snapshot = LocalExportLoader(FIXTURE_DIR).load()
    inventory = InventoryAggregator().aggregate(snapshot)

    assert inventory.get_item(29185) is not None
    assert inventory.has_item(29185)
    assert inventory.item_ids()[0] == 8932
    assert inventory.quantity_for(29185) == 1
    assert inventory.characters_holding(29185) == ["Ariadne Example"]
    assert inventory.sources_for(29185) == ["character_inventory"]
    assert list(inventory.iter_items())
