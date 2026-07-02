from pathlib import Path

from gw2_legendary_planner.api.local import LocalExportLoader
from gw2_legendary_planner.inventory.aggregator import InventoryAggregator
from gw2_legendary_planner.planner.recipe_evaluator import RecipeEvaluator
from gw2_legendary_planner.planner.recipe_repository import get_default_recipe_repository
from gw2_legendary_planner.planner.shopping_list import build_shopping_list

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "exports"


def test_shopping_list_aggregates_missing_effective_costs_for_one_recipe() -> None:
    snapshot = LocalExportLoader(FIXTURE_DIR).load()
    inventory = InventoryAggregator().aggregate(snapshot)
    repository = get_default_recipe_repository()
    recipe = repository.get_recipe("legendary.bolt")
    assert recipe is not None
    evaluation = RecipeEvaluator(repository).evaluate(recipe, snapshot, inventory)

    report = build_shopping_list([evaluation])
    by_name = {entry.name: entry for entry in report.entries}

    assert report.goal_count == 1
    assert report.missing_entry_count == len(report.entries)
    assert by_name["Mystic Clover"].missing_quantity == 65
    assert by_name["Icy Runestone"].acquisition is not None
    assert by_name["Icy Runestone"].acquisition.label == "Vendor purchase"
    assert "Zap" not in by_name


def test_shopping_list_counts_inventory_once_across_multiple_recipes() -> None:
    snapshot = LocalExportLoader(FIXTURE_DIR).load()
    inventory = InventoryAggregator().aggregate(snapshot)
    repository = get_default_recipe_repository()
    evaluator = RecipeEvaluator(repository)
    recipes = [
        repository.get_recipe("legendary.bolt"),
        repository.get_recipe("legendary.twilight"),
    ]
    assert all(recipe is not None for recipe in recipes)
    evaluations = [
        evaluator.evaluate(recipe, snapshot, inventory)
        for recipe in recipes
        if recipe is not None
    ]

    report = build_shopping_list(evaluations)
    by_name = {entry.name: entry for entry in report.entries}
    clover = by_name["Mystic Clover"]

    assert clover.required_quantity == 154
    assert clover.available_quantity == 12
    assert clover.missing_quantity == 142
    assert {contribution.recipe_id for contribution in clover.contributions} == {
        "legendary.bolt",
        "legendary.twilight",
    }


def test_shopping_list_can_include_complete_entries() -> None:
    snapshot = LocalExportLoader(FIXTURE_DIR).load()
    inventory = InventoryAggregator().aggregate(snapshot)
    repository = get_default_recipe_repository()
    recipe = repository.get_recipe("legendary.bolt")
    assert recipe is not None
    evaluation = RecipeEvaluator(repository).evaluate(recipe, snapshot, inventory)

    report = build_shopping_list([evaluation], include_complete=True)
    by_name = {entry.name: entry for entry in report.entries}

    assert by_name["Zap"].is_complete
    assert by_name["Zap"].missing_quantity == 0
