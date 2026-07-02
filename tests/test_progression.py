from pathlib import Path

from gw2_legendary_planner.api.local import LocalExportLoader
from gw2_legendary_planner.inventory.aggregator import InventoryAggregator
from gw2_legendary_planner.planner.achievements import (
    build_achievement_report,
    load_achievement_goal_definitions_from_path,
)
from gw2_legendary_planner.planner.activities import build_activity_report
from gw2_legendary_planner.planner.collections import (
    evaluate_collections,
    load_collection_definitions_from_path,
)
from gw2_legendary_planner.planner.progression import build_account_progression_report
from gw2_legendary_planner.planner.recipe_repository import get_default_recipe_repository
from gw2_legendary_planner.planner.recurring import (
    build_recurring_task_report,
    load_recurring_task_definitions_from_path,
)
from gw2_legendary_planner.planner.starter_kits import evaluate_starter_kit_sets
from gw2_legendary_planner.planner.wizards_vault import (
    load_wizard_vault_seasons_from_path,
    optimize_wizard_vault_rewards,
)

EXPORT_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "exports"
ACHIEVEMENT_FIXTURE = (
    Path(__file__).parent / "fixtures" / "achievements" / "sample_achievements.json"
)
COLLECTION_FIXTURE = (
    Path(__file__).parent / "fixtures" / "collections" / "sample_collections.json"
)
RECURRING_FIXTURE = Path(__file__).parent / "fixtures" / "recurring" / "sample_tasks.json"
WIZARD_VAULT_FIXTURE = (
    Path(__file__).parent / "fixtures" / "wizards_vault" / "sample_season.json"
)


def test_progression_report_scores_available_planner_outputs() -> None:
    snapshot = LocalExportLoader(EXPORT_FIXTURE_DIR).load()
    inventory = InventoryAggregator().aggregate(snapshot)
    repository = get_default_recipe_repository()
    collection_progress = evaluate_collections(
        snapshot,
        inventory,
        definitions=load_collection_definitions_from_path(COLLECTION_FIXTURE),
    )
    achievement_statuses = build_achievement_report(
        snapshot,
        definitions=load_achievement_goal_definitions_from_path(ACHIEVEMENT_FIXTURE),
    )
    recurring_tasks = build_recurring_task_report(
        snapshot,
        inventory,
        definitions=load_recurring_task_definitions_from_path(RECURRING_FIXTURE),
    )

    report = build_account_progression_report(
        snapshot,
        inventory,
        repository,
        achievement_statuses=achievement_statuses,
        activity_statuses=build_activity_report(snapshot, inventory),
        collection_progress=collection_progress,
        recurring_tasks=recurring_tasks,
    )
    component_ids = {component.id for component in report.score.components}

    assert report.score.overall_score_percent > 0
    assert "legendary_recipe_readiness" in component_ids
    assert "achievement_progress" in component_ids
    assert "activity_readiness" in component_ids
    assert "collection_progress" in component_ids
    assert "recurring_task_progress" in component_ids
    assert report.recommendations
    assert report.recommendations == sorted(
        report.recommendations,
        key=lambda recommendation: (
            -recommendation.priority_score,
            recommendation.kind,
            recommendation.title,
        ),
    )


def test_progression_report_includes_optional_starter_kit_and_vault_recommendations() -> None:
    snapshot = LocalExportLoader(EXPORT_FIXTURE_DIR).load()
    inventory = InventoryAggregator().aggregate(snapshot)
    repository = get_default_recipe_repository()
    starter_kit_evaluations = evaluate_starter_kit_sets(
        snapshot,
        inventory,
        repository,
        set_numbers={1},
    )
    wizard_vault_report = optimize_wizard_vault_rewards(
        snapshot,
        load_wizard_vault_seasons_from_path(WIZARD_VAULT_FIXTURE),
    )

    report = build_account_progression_report(
        snapshot,
        inventory,
        repository,
        activity_statuses=build_activity_report(snapshot, inventory),
        starter_kit_evaluations=starter_kit_evaluations,
        wizard_vault_report=wizard_vault_report,
    )
    recommendation_kinds = {recommendation.kind for recommendation in report.recommendations}

    assert "starter_kit" in recommendation_kinds
    assert "wizard_vault" in recommendation_kinds


def test_progression_report_includes_achievement_recommendations() -> None:
    snapshot = LocalExportLoader(EXPORT_FIXTURE_DIR).load()
    inventory = InventoryAggregator().aggregate(snapshot)
    achievement_statuses = build_achievement_report(
        snapshot,
        definitions=load_achievement_goal_definitions_from_path(ACHIEVEMENT_FIXTURE),
    )

    report = build_account_progression_report(
        snapshot,
        inventory,
        get_default_recipe_repository(),
        achievement_statuses=achievement_statuses,
    )

    assert any(recommendation.kind == "achievement" for recommendation in report.recommendations)


def test_progression_report_includes_recurring_recommendations() -> None:
    snapshot = LocalExportLoader(EXPORT_FIXTURE_DIR).load()
    inventory = InventoryAggregator().aggregate(snapshot)
    recurring_tasks = build_recurring_task_report(
        snapshot,
        inventory,
        definitions=load_recurring_task_definitions_from_path(RECURRING_FIXTURE),
    )

    report = build_account_progression_report(
        snapshot,
        inventory,
        get_default_recipe_repository(),
        recurring_tasks=recurring_tasks,
    )
    kinds = {recommendation.kind for recommendation in report.recommendations}

    assert "weekly" in kinds


def test_progression_report_limits_recommendations() -> None:
    snapshot = LocalExportLoader(EXPORT_FIXTURE_DIR).load()
    inventory = InventoryAggregator().aggregate(snapshot)

    report = build_account_progression_report(
        snapshot,
        inventory,
        get_default_recipe_repository(),
        max_recommendations=1,
    )

    assert len(report.recommendations) == 1
