from pathlib import Path

from gw2_legendary_planner.api.local import LocalExportLoader
from gw2_legendary_planner.inventory.aggregator import InventoryAggregator
from gw2_legendary_planner.planner.legendary_focus import build_legendary_focus_report

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "exports"


def test_legendary_focus_report_detects_items_and_wallet_currencies() -> None:
    snapshot = LocalExportLoader(FIXTURE_DIR).load()
    inventory = InventoryAggregator().aggregate(snapshot)

    report = build_legendary_focus_report(snapshot, inventory, include_zero=False)
    quantities = {entry.name: entry.quantity for entry in report}

    assert quantities["Gift of Exploration"] == 2
    assert quantities["Gift of Battle"] == 1
    assert quantities["Mystic Clover"] == 12
    assert quantities["Mystic Coin"] == 77
    assert quantities["Glob of Ectoplasm"] == 250
    assert quantities["Obsidian Shard"] == 50
    assert quantities["Spirit Shard"] == 321
    assert quantities["Provisioner Token"] == 8
    assert quantities["Dusk"] == 1
    assert quantities["Zap"] == 1


def test_legendary_focus_report_can_include_missing_watch_items() -> None:
    snapshot = LocalExportLoader(FIXTURE_DIR).load()
    inventory = InventoryAggregator().aggregate(snapshot)

    report = build_legendary_focus_report(snapshot, inventory)
    names = {entry.name for entry in report}

    assert "Legendary Weapon Starter Key-Universal" in names
