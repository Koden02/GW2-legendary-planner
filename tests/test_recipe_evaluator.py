from pathlib import Path

from gw2_legendary_planner.api.local import LocalExportLoader
from gw2_legendary_planner.inventory.aggregator import InventoryAggregator
from gw2_legendary_planner.planner.recipe_evaluator import RecipeEvaluator
from gw2_legendary_planner.planner.recipe_repository import get_default_recipe_repository

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "exports"


def test_recipe_evaluator_calculates_readiness_and_missing_costs() -> None:
    snapshot = LocalExportLoader(FIXTURE_DIR).load()
    inventory = InventoryAggregator().aggregate(snapshot)
    repository = get_default_recipe_repository()
    recipe = repository.get_recipe("legendary.twilight")
    assert recipe is not None

    evaluation = RecipeEvaluator(repository).evaluate(recipe, snapshot, inventory)
    costs = {cost.name: cost for cost in evaluation.costs}

    assert evaluation.recipe.name == "Twilight"
    assert not evaluation.is_ready
    assert 0 < evaluation.readiness_percent < 100
    assert costs["Dusk"].missing_quantity == 0
    assert "Gift of Twilight" not in costs
    assert costs["Icy Runestone"].required_quantity == 100
    assert costs["Superior Sigil of Blood"].missing_quantity == 1
    assert costs["Orichalcum Ingot"].required_quantity >= 250
    assert costs["Obsidian Shard"].required_quantity == 250
    assert costs["Obsidian Shard"].available_quantity == 50
    assert costs["Obsidian Shard"].acquisition is not None
    assert costs["Obsidian Shard"].acquisition.label == "Currency vendors"
    assert costs["Mystic Clover"].missing_quantity == 65
    assert costs["Glob of Ectoplasm"].missing_quantity == 0


def test_recipe_evaluator_builds_dependency_graph() -> None:
    snapshot = LocalExportLoader(FIXTURE_DIR).load()
    inventory = InventoryAggregator().aggregate(snapshot)
    repository = get_default_recipe_repository()
    recipe = repository.get_recipe("legendary.twilight")
    assert recipe is not None

    evaluation = RecipeEvaluator(repository).evaluate(recipe, snapshot, inventory)
    recipe_ids = {
        node.recipe_id
        for node in evaluation.dependency_graph.nodes
        if node.recipe_id is not None
    }
    labels = {node.label for node in evaluation.dependency_graph.nodes}

    assert "gift.mastery" in recipe_ids
    assert "gift.fortune" in recipe_ids
    assert "weapon_gift.twilight" in recipe_ids
    assert "Gift of Exploration" in labels
    assert "Icy Runestone" in labels
    assert evaluation.dependency_graph.edges


def test_recipe_evaluator_handles_non_twilight_generation_one_recipe() -> None:
    snapshot = LocalExportLoader(FIXTURE_DIR).load()
    inventory = InventoryAggregator().aggregate(snapshot)
    repository = get_default_recipe_repository()
    recipe = repository.get_recipe("legendary.bolt")
    assert recipe is not None

    evaluation = RecipeEvaluator(repository).evaluate(recipe, snapshot, inventory)
    costs = {cost.name: cost for cost in evaluation.costs}

    assert evaluation.recipe.name == "Bolt"
    assert costs["Zap"].missing_quantity == 0
    assert "Gift of Bolt" not in costs
    assert costs["Icy Runestone"].missing_quantity == 100
    assert costs["Icy Runestone"].acquisition is not None
    assert costs["Icy Runestone"].acquisition.label == "Vendor purchase"
    assert costs["Superior Sigil of Air"].missing_quantity == 1
    assert costs["Charged Lodestone"].missing_quantity == 100
    assert costs["Orichalcum Ingot"].required_quantity >= 500
    assert costs["Mystic Clover"].missing_quantity == 65


def test_recipe_evaluator_handles_api_verified_shared_recipe() -> None:
    snapshot = LocalExportLoader(FIXTURE_DIR).load()
    inventory = InventoryAggregator().aggregate(snapshot)
    repository = get_default_recipe_repository()
    recipe = repository.get_recipe("gift.metal")
    assert recipe is not None

    evaluation = RecipeEvaluator(repository).evaluate(recipe, snapshot, inventory)
    costs = {cost.name: cost for cost in evaluation.costs}

    assert evaluation.recipe.name == "Gift of Metal"
    assert not evaluation.is_ready
    assert costs["Orichalcum Ingot"].required_quantity == 250
    assert costs["Mithril Ingot"].missing_quantity == 250
