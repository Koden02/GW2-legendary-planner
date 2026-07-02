from pathlib import Path

import pytest

from gw2_legendary_planner.api.local import LocalExportLoader
from gw2_legendary_planner.planner.achievements import (
    AchievementDataError,
    build_achievement_report,
    filter_achievement_goals,
    load_achievement_goal_definitions,
    load_achievement_goal_definitions_from_path,
)

EXPORT_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "exports"
ACHIEVEMENT_FIXTURE = (
    Path(__file__).parent / "fixtures" / "achievements" / "sample_achievements.json"
)


def test_packaged_achievement_data_starts_empty() -> None:
    assert load_achievement_goal_definitions() == []


def test_achievement_report_tracks_complete_and_partial_goals() -> None:
    snapshot = LocalExportLoader(EXPORT_FIXTURE_DIR).load()
    definitions = load_achievement_goal_definitions_from_path(ACHIEVEMENT_FIXTURE)

    statuses = build_achievement_report(snapshot, definitions=definitions)
    by_id = {status.id: status for status in statuses}

    assert by_id["sample-complete-achievement"].is_complete
    assert by_id["sample-complete-achievement"].readiness_percent == 100
    assert by_id["sample-partial-achievement"].current_progress == 3
    assert by_id["sample-partial-achievement"].required_progress == 5
    assert by_id["sample-partial-achievement"].readiness_percent == 60
    assert not by_id["sample-partial-achievement"].is_complete


def test_achievement_report_can_hide_complete_goals() -> None:
    snapshot = LocalExportLoader(EXPORT_FIXTURE_DIR).load()
    definitions = load_achievement_goal_definitions_from_path(ACHIEVEMENT_FIXTURE)

    statuses = build_achievement_report(
        snapshot,
        definitions=definitions,
        include_complete=False,
    )

    assert [status.id for status in statuses] == ["sample-partial-achievement"]


def test_achievement_filters_select_by_id_and_tag() -> None:
    snapshot = LocalExportLoader(EXPORT_FIXTURE_DIR).load()
    definitions = load_achievement_goal_definitions_from_path(ACHIEVEMENT_FIXTURE)
    statuses = build_achievement_report(snapshot, definitions=definitions)

    assert filter_achievement_goals(statuses, goal_ids={"sample-partial-achievement"})
    assert filter_achievement_goals(statuses, tags={"partial"})
    assert not filter_achievement_goals(statuses, tags={"missing"})


def test_achievement_loader_reports_malformed_json(tmp_path: Path) -> None:
    data_path = tmp_path / "achievements.json"
    data_path.write_text("[", encoding="utf-8")

    with pytest.raises(AchievementDataError, match="malformed JSON"):
        load_achievement_goal_definitions_from_path(data_path)
