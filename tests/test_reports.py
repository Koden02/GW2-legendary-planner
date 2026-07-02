from pathlib import Path

from gw2_legendary_planner.api.local import LocalExportLoader
from gw2_legendary_planner.inventory.aggregator import InventoryAggregator
from gw2_legendary_planner.planner.recipe_evaluator import RecipeEvaluator
from gw2_legendary_planner.planner.recipe_repository import get_default_recipe_repository
from gw2_legendary_planner.reports.exporters import (
    focus_rows,
    inventory_rows,
    recipe_cost_rows,
    rows_to_csv,
    summary_rows,
)
from gw2_legendary_planner.reports.summary import build_account_summary

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "exports"


def test_account_summary_uses_wallet_characters_crafting_and_inventory() -> None:
    snapshot = LocalExportLoader(FIXTURE_DIR).load()
    inventory = InventoryAggregator().aggregate(snapshot)
    summary = build_account_summary(snapshot, inventory)

    assert summary.account_name == "Example.1234"
    assert str(summary.gold) == "1234.5678"
    assert summary.gems == 400
    assert len(summary.characters) == 1
    assert len(summary.crafting_disciplines) == 2
    assert summary.legendary_armory_entries == 2
    assert summary.legendary_armory_total == 3
    assert summary.unique_item_count == 9
    assert summary.total_item_count == 395


def test_export_rows_are_flat() -> None:
    snapshot = LocalExportLoader(FIXTURE_DIR).load()
    inventory = InventoryAggregator().aggregate(snapshot)
    summary = build_account_summary(snapshot, inventory)

    assert inventory_rows(inventory)[0].keys() == {"item_id", "quantity", "locations"}
    assert summary_rows(summary)[0] == {"metric": "account_name", "value": "Example.1234"}
    assert focus_rows([]) == []


def test_csv_output_quotes_comma_fields() -> None:
    rows = [{"name": "Gift", "tags": "account_bound,gift"}]

    assert rows_to_csv(rows).splitlines()[1] == 'Gift,"account_bound,gift"'


def test_recipe_cost_rows_can_filter_missing_only() -> None:
    snapshot = LocalExportLoader(FIXTURE_DIR).load()
    inventory = InventoryAggregator().aggregate(snapshot)
    repository = get_default_recipe_repository()
    recipe = repository.get_recipe("legendary.bolt")
    assert recipe is not None

    evaluation = RecipeEvaluator(repository).evaluate(recipe, snapshot, inventory)
    rows = recipe_cost_rows(evaluation, missing_only=True)
    names = {row["name"] for row in rows}

    assert "Mystic Clover" in names
    assert "Zap" not in names
    assert all(row["missing_quantity"] > 0 for row in rows)
    icy_runestone = next(row for row in rows if row["name"] == "Icy Runestone")
    assert icy_runestone["acquisition"] == "Vendor purchase"
    assert icy_runestone["source_url"] == "https://wiki.guildwars2.com/wiki/Icy_Runestone"
