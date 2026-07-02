from pathlib import Path

from gw2_legendary_planner.api.local import LocalExportLoader
from gw2_legendary_planner.inventory.aggregator import InventoryAggregator
from gw2_legendary_planner.models.commerce import CommercePrice
from gw2_legendary_planner.planner.goal_comparison import build_goal_comparison_report
from gw2_legendary_planner.planner.market import price_shopping_list
from gw2_legendary_planner.planner.recipe_evaluator import RecipeEvaluator
from gw2_legendary_planner.planner.recipe_repository import get_default_recipe_repository
from gw2_legendary_planner.planner.shopping_list import build_shopping_list

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "exports"


def test_goal_comparison_summarizes_selected_recipe_readiness() -> None:
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

    report = build_goal_comparison_report(
        evaluations,
        selected_goal_ids=["legendary.bolt", "legendary.bolt", "missing"],
    )
    bolt = next(goal for goal in report.goals if goal.recipe_id == "legendary.bolt")

    assert report.selected_goal_ids == ["legendary.bolt"]
    assert report.goal_count == 2
    assert bolt.readiness_percent == 18.15
    assert bolt.account_bound_missing_entries == 1
    assert bolt.manual_missing_entries == 4
    assert bolt.tradeable_missing_entries == 15
    assert "Gift of Ascalon" in bolt.recommended_action
    assert {requirement.category for requirement in bolt.missing_requirements} >= {
        "account_bound",
        "manual",
        "tradeable",
    }


def test_goal_comparison_can_include_estimated_price() -> None:
    snapshot = LocalExportLoader(FIXTURE_DIR).load()
    inventory = InventoryAggregator().aggregate(snapshot)
    repository = get_default_recipe_repository()
    recipe = repository.get_recipe("legendary.bolt")
    assert recipe is not None
    evaluation = RecipeEvaluator(repository).evaluate(recipe, snapshot, inventory)
    shopping_list = build_shopping_list([evaluation])
    price_report = price_shopping_list(
        shopping_list,
        {
            19675: CommercePrice(
                id=19675,
                buys={"quantity": 20, "unit_price": 80},
                sells={"quantity": 12, "unit_price": 125},
            )
        },
    )

    report = build_goal_comparison_report(
        [evaluation],
        selected_goal_ids=["legendary.bolt"],
        price_reports_by_recipe={"legendary.bolt": price_report},
    )

    assert report.goals[0].estimated_buy_cost == 8_125
    clover = next(
        requirement
        for requirement in report.goals[0].missing_requirements
        if requirement.name == "Mystic Clover"
    )
    assert clover.estimated_buy_cost == 8_125
