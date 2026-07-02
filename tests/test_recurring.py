from pathlib import Path

import pytest

from gw2_legendary_planner.api.local import LocalExportLoader
from gw2_legendary_planner.inventory.aggregator import InventoryAggregator
from gw2_legendary_planner.planner.recurring import (
    RecurringTaskDataError,
    build_recurring_task_report,
    filter_recurring_tasks,
    load_recurring_task_definitions,
    load_recurring_task_definitions_from_path,
)

EXPORT_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "exports"
RECURRING_FIXTURE = Path(__file__).parent / "fixtures" / "recurring" / "sample_tasks.json"


def test_packaged_recurring_task_data_starts_empty() -> None:
    assert load_recurring_task_definitions() == []


def test_recurring_task_report_evaluates_daily_weekly_and_manual_tasks() -> None:
    snapshot = LocalExportLoader(EXPORT_FIXTURE_DIR).load()
    inventory = InventoryAggregator().aggregate(snapshot)
    definitions = load_recurring_task_definitions_from_path(RECURRING_FIXTURE)

    statuses = build_recurring_task_report(snapshot, inventory, definitions=definitions)
    by_id = {status.id: status for status in statuses}

    assert by_id["sample-daily-achievement"].is_complete
    assert by_id["sample-daily-achievement"].period == "daily"
    assert by_id["sample-weekly-achievement-progress"].readiness_percent == 60.0
    assert by_id["sample-weekly-achievement-progress"].missing_quantity == 2
    assert by_id["sample-weekly-manual"].is_trackable is False
    assert by_id["sample-weekly-manual"].is_complete is False


def test_recurring_task_report_can_filter_periods_and_hide_complete() -> None:
    snapshot = LocalExportLoader(EXPORT_FIXTURE_DIR).load()
    inventory = InventoryAggregator().aggregate(snapshot)
    definitions = load_recurring_task_definitions_from_path(RECURRING_FIXTURE)

    statuses = build_recurring_task_report(
        snapshot,
        inventory,
        definitions=definitions,
        periods={"weekly"},
        include_complete=False,
    )

    assert {status.period for status in statuses} == {"weekly"}
    assert {status.id for status in statuses} == {
        "sample-weekly-achievement-progress",
        "sample-weekly-manual",
    }


def test_recurring_task_filters_select_by_id_period_and_tag() -> None:
    snapshot = LocalExportLoader(EXPORT_FIXTURE_DIR).load()
    inventory = InventoryAggregator().aggregate(snapshot)
    definitions = load_recurring_task_definitions_from_path(RECURRING_FIXTURE)
    statuses = build_recurring_task_report(snapshot, inventory, definitions=definitions)

    assert filter_recurring_tasks(statuses, task_ids={"sample-daily-achievement"})
    assert filter_recurring_tasks(statuses, periods={"weekly"})
    assert filter_recurring_tasks(statuses, tags={"manual"})
    assert not filter_recurring_tasks(statuses, tags={"missing"})


def test_recurring_loader_reports_malformed_json(tmp_path: Path) -> None:
    data_path = tmp_path / "recurring.json"
    data_path.write_text("[", encoding="utf-8")

    with pytest.raises(RecurringTaskDataError, match="malformed JSON"):
        load_recurring_task_definitions_from_path(data_path)
