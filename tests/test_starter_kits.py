from pathlib import Path

from gw2_legendary_planner.api.local import LocalExportLoader
from gw2_legendary_planner.inventory.aggregator import InventoryAggregator
from gw2_legendary_planner.planner.recipe_repository import get_default_recipe_repository
from gw2_legendary_planner.planner.starter_kits import (
    evaluate_starter_kit_sets,
    load_starter_kit_sets,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "exports"


def test_starter_kit_catalog_loads_rotation_sets() -> None:
    starter_sets = load_starter_kit_sets()
    by_number = {starter_set.set_number: starter_set for starter_set in starter_sets}

    assert len(starter_sets) == 10
    assert by_number[1].recipe_ids == [
        "legendary.meteorlogicus",
        "legendary.the_bifrost",
        "legendary.bolt",
        "legendary.quip",
    ]
    assert by_number[10].recipe_ids == [
        "legendary.kraitkin",
        "legendary.the_flameseeker_prophecies",
        "legendary.meteorlogicus",
        "legendary.the_bifrost",
    ]


def test_starter_kit_evaluator_ranks_account_specific_gain() -> None:
    snapshot = LocalExportLoader(FIXTURE_DIR).load()
    inventory = InventoryAggregator().aggregate(snapshot)
    repository = get_default_recipe_repository()

    evaluations = evaluate_starter_kit_sets(
        snapshot,
        inventory,
        repository,
        set_numbers={1},
    )

    assert len(evaluations) == 1
    assert evaluations[0].set_number == 1
    assert evaluations[0].options[0].legendary_name == "Quip"
    assert evaluations[0].options[0].readiness_gain_percent > 0
    assert evaluations[0].options[-1].legendary_name == "Bolt"
    assert evaluations[0].options[-1].covered_items == [
        "Zap",
        "Gift of Bolt",
        "Gift of Might",
    ]


def test_starter_kit_evaluator_can_filter_sets() -> None:
    snapshot = LocalExportLoader(FIXTURE_DIR).load()
    inventory = InventoryAggregator().aggregate(snapshot)

    evaluations = evaluate_starter_kit_sets(
        snapshot,
        inventory,
        get_default_recipe_repository(),
        set_numbers={9, 10},
    )

    assert [evaluation.set_number for evaluation in evaluations] == [9, 10]
