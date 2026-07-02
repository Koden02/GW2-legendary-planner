from pathlib import Path

from gw2_legendary_planner.api.local import LocalExportLoader
from gw2_legendary_planner.inventory.aggregator import InventoryAggregator
from gw2_legendary_planner.planner.activities import (
    ActivityGoalDefinition,
    build_activity_report,
    filter_activity_goals,
    load_activity_goal_definitions,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "exports"


def test_activity_report_evaluates_gift_activity_readiness() -> None:
    snapshot = LocalExportLoader(FIXTURE_DIR).load()
    inventory = InventoryAggregator().aggregate(snapshot)

    statuses = build_activity_report(snapshot, inventory)
    by_id = {status.id: status for status in statuses}

    assert by_id["gift_of_battle"].is_ready
    assert by_id["gift_of_battle"].available_quantity == 1
    assert by_id["gift_of_battle"].activity_kind == "reward_track"
    assert by_id["gift_of_battle"].locations[0].source == "bank"
    assert by_id["gift_of_exploration"].is_ready
    assert by_id["gift_of_exploration"].available_quantity == 2
    assert by_id["gift_of_exploration"].activity_kind == "world_completion"


def test_activity_report_can_show_missing_goal_progress() -> None:
    snapshot = LocalExportLoader(FIXTURE_DIR).load()
    inventory = InventoryAggregator().aggregate(snapshot)
    definition = ActivityGoalDefinition(
        id="two_gifts_of_battle",
        name="Two Gifts of Battle",
        category="Legendary activity",
        activity_kind="reward_track",
        target_kind="item",
        target_id=19678,
        required_quantity=2,
        action="Complete another Gift of Battle reward track.",
    )

    statuses = build_activity_report(
        snapshot,
        inventory,
        definitions=[definition],
        include_ready=False,
    )

    assert len(statuses) == 1
    assert statuses[0].available_quantity == 1
    assert statuses[0].missing_quantity == 1
    assert statuses[0].readiness_percent == 50.0


def test_activity_goal_filters_accept_goal_ids_and_tags() -> None:
    snapshot = LocalExportLoader(FIXTURE_DIR).load()
    inventory = InventoryAggregator().aggregate(snapshot)
    statuses = build_activity_report(snapshot, inventory)

    by_goal = filter_activity_goals(statuses, goal_ids={"gift-of-battle"})
    by_tag = filter_activity_goals(statuses, tags={"world-completion"})

    assert [status.id for status in by_goal] == ["gift_of_battle"]
    assert [status.id for status in by_tag] == ["gift_of_exploration"]


def test_packaged_activity_goal_definitions_load() -> None:
    definitions = load_activity_goal_definitions()

    assert {definition.id for definition in definitions} == {
        "gift_of_battle",
        "gift_of_exploration",
    }
    assert all(definition.source_url for definition in definitions)
