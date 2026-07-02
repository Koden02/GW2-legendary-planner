from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated, Literal

import typer
from rich.console import Console

from gw2_legendary_planner import __version__
from gw2_legendary_planner.api.client import GW2ApiClient
from gw2_legendary_planner.api.local import LocalExportError, LocalExportLoader
from gw2_legendary_planner.cache.local import ApiCache
from gw2_legendary_planner.config.settings import Settings
from gw2_legendary_planner.diagnostics import build_doctor_report, render_doctor_report
from gw2_legendary_planner.inventory.aggregator import InventoryAggregator
from gw2_legendary_planner.inventory.models import Inventory
from gw2_legendary_planner.models.snapshot import AccountSnapshot
from gw2_legendary_planner.planner.achievements import (
    AchievementDataError,
    AchievementGoalStatus,
    build_achievement_report,
    filter_achievement_goals,
    load_achievement_goal_definitions,
    load_achievement_goal_definitions_from_path,
)
from gw2_legendary_planner.planner.activities import (
    ActivityGoalStatus,
    build_activity_report,
    filter_activity_goals,
)
from gw2_legendary_planner.planner.collections import (
    CollectionDataError,
    CollectionProgress,
    evaluate_collections,
    filter_collections,
    load_collection_definitions,
    load_collection_definitions_from_path,
)
from gw2_legendary_planner.planner.legendary_focus import build_legendary_focus_report
from gw2_legendary_planner.planner.progression import (
    AccountProgressionReport,
    build_account_progression_report,
)
from gw2_legendary_planner.planner.recipe_evaluator import RecipeEvaluation, RecipeEvaluator
from gw2_legendary_planner.planner.recipe_repository import get_default_recipe_repository
from gw2_legendary_planner.planner.recipe_validator import validate_recipes
from gw2_legendary_planner.planner.recipes import Recipe
from gw2_legendary_planner.planner.recurring import (
    RecurringTaskDataError,
    RecurringTaskStatus,
    build_recurring_task_report,
    filter_recurring_tasks,
    load_recurring_task_definitions,
    load_recurring_task_definitions_from_path,
)
from gw2_legendary_planner.planner.starter_kits import (
    StarterKitSetEvaluation,
    evaluate_starter_kit_sets,
)
from gw2_legendary_planner.planner.wizards_vault import (
    WizardVaultDataError,
    WizardVaultOptimizationReport,
    WizardVaultSeason,
    WizardVaultValidationReport,
    filter_wizard_vault_seasons,
    load_wizard_vault_seasons,
    load_wizard_vault_seasons_from_path,
    optimize_wizard_vault_rewards,
    validate_wizard_vault_seasons,
)
from gw2_legendary_planner.reports.exporters import (
    achievement_rows,
    activity_rows,
    collection_rows,
    focus_rows,
    inventory_rows,
    model_to_json,
    progression_report_rows,
    progression_score_rows,
    recipe_cost_rows,
    recipe_graph_rows,
    recipe_rows,
    recipe_validation_rows,
    recurring_task_rows,
    rows_to_csv,
    starter_kit_rows,
    summary_rows,
    wizard_vault_optimization_rows,
    wizard_vault_rows,
    wizard_vault_validation_rows,
    write_csv,
    write_json,
)
from gw2_legendary_planner.reports.rich_console import (
    render_account_summary,
    render_achievement_report,
    render_activity_report,
    render_collection_progress,
    render_focus_report,
    render_progression_report,
    render_progression_score,
    render_recipe_detail,
    render_recipe_evaluation,
    render_recipe_graph,
    render_recipe_list,
    render_recipe_validation_report,
    render_recurring_task_report,
    render_starter_kit_evaluations,
    render_wizard_vault_optimization,
    render_wizard_vault_seasons,
    render_wizard_vault_validation_report,
)
from gw2_legendary_planner.reports.summary import build_account_summary

app = typer.Typer(help="Guild Wars 2 account progression and legendary planner.")
export_app = typer.Typer(help="Export planner data.")
recipe_app = typer.Typer(help="Inspect and evaluate data-defined recipes.")
activity_app = typer.Typer(help="Inspect legendary activity planners.")
progress_app = typer.Typer(help="Score account progression and recommend next steps.")
app.add_typer(export_app, name="export")
app.add_typer(recipe_app, name="recipes")
app.add_typer(activity_app, name="activities")
app.add_typer(progress_app, name="progress")
console = Console()

Format = Literal["json", "csv"]
RecipeFormat = Literal["rich", "json", "csv"]


def _load_snapshot(
    *,
    api_key: str | None,
    input_dir: Path | None,
    use_cache: bool = True,
) -> AccountSnapshot:
    settings = Settings.from_environment()
    resolved_key = api_key or settings.api_key

    if input_dir:
        try:
            return LocalExportLoader(input_dir).load()
        except LocalExportError as exc:
            _render_local_export_error(exc)
            raise typer.Exit(1) from exc

    if not resolved_key:
        raise typer.BadParameter("Provide --api-key, set GW2PLANNER_API_KEY, or use --input.")

    cache = (
        ApiCache(settings.cache_dir, ttl_seconds=settings.cache_ttl_seconds)
        if use_cache
        else None
    )
    return GW2ApiClient(resolved_key, cache=cache).load_account_snapshot()


@app.command()
def analyze(
    api_key: Annotated[
        str | None,
        typer.Option("--api-key", help="Guild Wars 2 API key. Defaults to GW2PLANNER_API_KEY."),
    ] = None,
    input_dir: Annotated[
        Path | None,
        typer.Option("--input", "-i", help="Directory containing local GW2 API JSON exports."),
    ] = None,
    no_cache: Annotated[
        bool,
        typer.Option("--no-cache", help="Disable API response cache."),
    ] = False,
) -> None:
    """Analyze an account and print summary and legendary focus tables."""

    snapshot = _load_snapshot(api_key=api_key, input_dir=input_dir, use_cache=not no_cache)
    inventory = InventoryAggregator().aggregate(snapshot)
    summary = build_account_summary(snapshot, inventory)
    focus_report = build_legendary_focus_report(snapshot, inventory)
    render_account_summary(console, summary)
    render_focus_report(console, focus_report)


@export_app.command("inventory")
def export_inventory(
    api_key: Annotated[str | None, typer.Option("--api-key")] = None,
    input_dir: Annotated[Path | None, typer.Option("--input", "-i")] = None,
    output_format: Annotated[Format, typer.Option("--format", "-f")] = "json",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
) -> None:
    """Export flattened account inventory."""

    snapshot = _load_snapshot(api_key=api_key, input_dir=input_dir)
    inventory = InventoryAggregator().aggregate(snapshot)
    if output_format == "csv":
        rows = inventory_rows(inventory)
        _write_or_print_csv(rows, output)
        return

    payload = {
        str(item_id): item.model_dump(mode="json")
        for item_id, item in sorted(inventory.items.items())
    }
    _write_or_print_json(payload, output)


@export_app.command("summary")
def export_summary(
    api_key: Annotated[str | None, typer.Option("--api-key")] = None,
    input_dir: Annotated[Path | None, typer.Option("--input", "-i")] = None,
    output_format: Annotated[Format, typer.Option("--format", "-f")] = "json",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
) -> None:
    """Export account summary."""

    snapshot = _load_snapshot(api_key=api_key, input_dir=input_dir)
    inventory = InventoryAggregator().aggregate(snapshot)
    summary = build_account_summary(snapshot, inventory)
    if output_format == "csv":
        _write_or_print_csv(summary_rows(summary), output)
        return
    _write_or_print_text(model_to_json(summary), output)


@export_app.command("focus")
def export_focus(
    api_key: Annotated[str | None, typer.Option("--api-key")] = None,
    input_dir: Annotated[Path | None, typer.Option("--input", "-i")] = None,
    output_format: Annotated[Format, typer.Option("--format", "-f")] = "json",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
    include_zero: Annotated[bool, typer.Option("--include-zero/--present-only")] = True,
) -> None:
    """Export the legendary focus report."""

    snapshot = _load_snapshot(api_key=api_key, input_dir=input_dir)
    inventory = InventoryAggregator().aggregate(snapshot)
    focus_report = build_legendary_focus_report(snapshot, inventory, include_zero=include_zero)
    if output_format == "csv":
        _write_or_print_csv(focus_rows(focus_report), output)
        return
    _write_or_print_text(model_to_json(focus_report), output)


@export_app.command("activities")
def export_activities(
    api_key: Annotated[str | None, typer.Option("--api-key")] = None,
    input_dir: Annotated[Path | None, typer.Option("--input", "-i")] = None,
    output_format: Annotated[Format, typer.Option("--format", "-f")] = "json",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
    include_ready: Annotated[bool, typer.Option("--include-ready/--missing-only")] = True,
) -> None:
    """Export legendary activity planner readiness."""

    statuses = _load_activity_statuses(
        api_key=api_key,
        input_dir=input_dir,
        include_ready=include_ready,
    )
    if output_format == "csv":
        _write_or_print_csv(activity_rows(statuses), output)
        return
    _write_or_print_text(model_to_json(statuses), output)


@export_app.command("achievements")
def export_achievements(
    api_key: Annotated[str | None, typer.Option("--api-key")] = None,
    input_dir: Annotated[Path | None, typer.Option("--input", "-i")] = None,
    output_format: Annotated[Format, typer.Option("--format", "-f")] = "json",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
    data_path: Annotated[
        Path | None,
        typer.Option("--data", help="Load achievement goal definitions from JSON."),
    ] = None,
    include_complete: Annotated[bool, typer.Option("--include-complete/--missing-only")] = True,
    goals: Annotated[
        list[str] | None,
        typer.Option("--goal", help="Filter by achievement goal id. Repeat for multiple."),
    ] = None,
    tags: Annotated[
        list[str] | None,
        typer.Option("--tag", help="Filter by achievement tag. Repeat to require multiple tags."),
    ] = None,
) -> None:
    """Export data-defined achievement progress."""

    statuses = _load_achievement_statuses(
        api_key=api_key,
        input_dir=input_dir,
        data_path=data_path,
        include_complete=include_complete,
        goals=goals,
        tags=tags,
    )
    if output_format == "csv":
        _write_or_print_csv(achievement_rows(statuses), output)
        return
    _write_or_print_text(model_to_json(statuses), output)


@export_app.command("collections")
def export_collections(
    api_key: Annotated[str | None, typer.Option("--api-key")] = None,
    input_dir: Annotated[Path | None, typer.Option("--input", "-i")] = None,
    output_format: Annotated[Format, typer.Option("--format", "-f")] = "json",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
    data_path: Annotated[
        Path | None,
        typer.Option("--data", help="Load collection definitions from a JSON file."),
    ] = None,
    include_complete: Annotated[bool, typer.Option("--include-complete/--missing-only")] = True,
    collections: Annotated[
        list[str] | None,
        typer.Option("--collection", help="Filter by collection id. Repeat for multiple."),
    ] = None,
    tags: Annotated[
        list[str] | None,
        typer.Option("--tag", help="Filter by collection tag. Repeat to require multiple tags."),
    ] = None,
) -> None:
    """Export data-defined collection progress."""

    progress_entries = _load_collection_progress(
        api_key=api_key,
        input_dir=input_dir,
        data_path=data_path,
        include_complete=include_complete,
        collections=collections,
        tags=tags,
    )
    if output_format == "csv":
        _write_or_print_csv(collection_rows(progress_entries), output)
        return
    _write_or_print_text(model_to_json(progress_entries), output)


@export_app.command("progression")
def export_progression(
    api_key: Annotated[str | None, typer.Option("--api-key")] = None,
    input_dir: Annotated[Path | None, typer.Option("--input", "-i")] = None,
    output_format: Annotated[Format, typer.Option("--format", "-f")] = "json",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
    collections_data: Annotated[
        Path | None,
        typer.Option("--collections-data", help="Load collection definitions from JSON."),
    ] = None,
    achievements_data: Annotated[
        Path | None,
        typer.Option("--achievements-data", help="Load achievement goal definitions from JSON."),
    ] = None,
    recurring_data: Annotated[
        Path | None,
        typer.Option("--recurring-data", help="Load daily/weekly task definitions from JSON."),
    ] = None,
    wizard_vault_data: Annotated[
        Path | None,
        typer.Option("--wizard-vault-data", help="Load Wizard's Vault season data from JSON."),
    ] = None,
    starter_kit_sets: Annotated[
        list[int] | None,
        typer.Option("--starter-kit-set", min=1, help="Include specific starter-kit sets."),
    ] = None,
    max_recommendations: Annotated[int, typer.Option("--max", min=1)] = 10,
) -> None:
    """Export account progression score and recommendations."""

    report = _load_progression_report(
        api_key=api_key,
        input_dir=input_dir,
        collections_data=collections_data,
        achievements_data=achievements_data,
        recurring_data=recurring_data,
        wizard_vault_data=wizard_vault_data,
        starter_kit_sets=starter_kit_sets,
        max_recommendations=max_recommendations,
    )
    if output_format == "csv":
        _write_or_print_csv(progression_report_rows(report), output)
        return
    _write_or_print_text(model_to_json(report), output)


@export_app.command("recurring")
def export_recurring(
    api_key: Annotated[str | None, typer.Option("--api-key")] = None,
    input_dir: Annotated[Path | None, typer.Option("--input", "-i")] = None,
    output_format: Annotated[Format, typer.Option("--format", "-f")] = "json",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
    data_path: Annotated[
        Path | None,
        typer.Option("--data", help="Load recurring task definitions from JSON."),
    ] = None,
    periods: Annotated[
        list[str] | None,
        typer.Option("--period", help="Filter by period: daily or weekly."),
    ] = None,
    include_complete: Annotated[bool, typer.Option("--include-complete/--missing-only")] = True,
    tasks: Annotated[
        list[str] | None,
        typer.Option("--task", help="Filter by recurring task id. Repeat for multiple."),
    ] = None,
    tags: Annotated[
        list[str] | None,
        typer.Option(
            "--tag",
            help="Filter by recurring task tag. Repeat to require multiple tags.",
        ),
    ] = None,
) -> None:
    """Export data-defined daily and weekly task progress."""

    statuses = _load_recurring_task_statuses(
        api_key=api_key,
        input_dir=input_dir,
        data_path=data_path,
        periods=periods,
        include_complete=include_complete,
        tasks=tasks,
        tags=tags,
    )
    if output_format == "csv":
        _write_or_print_csv(recurring_task_rows(statuses), output)
        return
    _write_or_print_text(model_to_json(statuses), output)


@export_app.command("starter-kits")
def export_starter_kits(
    api_key: Annotated[str | None, typer.Option("--api-key")] = None,
    input_dir: Annotated[Path | None, typer.Option("--input", "-i")] = None,
    output_format: Annotated[Format, typer.Option("--format", "-f")] = "json",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
    set_numbers: Annotated[
        list[int] | None,
        typer.Option("--set", min=1, help="Evaluate only specific starter-kit set numbers."),
    ] = None,
) -> None:
    """Export Legendary Weapon Starter Kit evaluations."""

    evaluations = _load_starter_kit_evaluations(
        api_key=api_key,
        input_dir=input_dir,
        set_numbers=set_numbers,
    )
    if output_format == "csv":
        _write_or_print_csv(starter_kit_rows(evaluations), output)
        return
    _write_or_print_text(model_to_json(evaluations), output)


@export_app.command("wizard-vault")
def export_wizard_vault(
    output_format: Annotated[Format, typer.Option("--format", "-f")] = "json",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
    data_path: Annotated[
        Path | None,
        typer.Option(
            "--data",
            help="Load Wizard's Vault seasonal reward data from a JSON file.",
        ),
    ] = None,
    seasons: Annotated[
        list[str] | None,
        typer.Option("--season", help="Filter by Wizard's Vault season id."),
    ] = None,
    statuses: Annotated[
        list[str] | None,
        typer.Option("--status", help="Filter by season status."),
    ] = None,
    tags: Annotated[
        list[str] | None,
        typer.Option("--tag", help="Filter rewards by tag. Repeat to require multiple tags."),
    ] = None,
) -> None:
    """Export Wizard's Vault seasonal reward data."""

    season_data = _load_wizard_vault_seasons(
        data_path=data_path,
        seasons=seasons,
        statuses=statuses,
        tags=tags,
    )
    if output_format == "csv":
        _write_or_print_csv(wizard_vault_rows(season_data), output)
        return
    _write_or_print_text(model_to_json(season_data), output)


@export_app.command("wizard-vault-optimization")
def export_wizard_vault_optimization(
    api_key: Annotated[str | None, typer.Option("--api-key")] = None,
    input_dir: Annotated[Path | None, typer.Option("--input", "-i")] = None,
    output_format: Annotated[Format, typer.Option("--format", "-f")] = "json",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
    data_path: Annotated[
        Path | None,
        typer.Option(
            "--data",
            help="Load Wizard's Vault seasonal reward data from a JSON file.",
        ),
    ] = None,
    seasons: Annotated[
        list[str] | None,
        typer.Option("--season", help="Filter by Wizard's Vault season id."),
    ] = None,
    statuses: Annotated[
        list[str] | None,
        typer.Option("--status", help="Filter by season status."),
    ] = None,
    tags: Annotated[
        list[str] | None,
        typer.Option("--tag", help="Filter rewards by tag. Repeat to require multiple tags."),
    ] = None,
) -> None:
    """Export Wizard's Vault reward optimization."""

    report = _load_wizard_vault_optimization(
        api_key=api_key,
        input_dir=input_dir,
        data_path=data_path,
        seasons=seasons,
        statuses=statuses,
        tags=tags,
    )
    if output_format == "csv":
        _write_or_print_csv(wizard_vault_optimization_rows(report), output)
        return
    _write_or_print_text(model_to_json(report), output)


@recipe_app.command("list")
def list_recipes(
    output_format: Annotated[RecipeFormat, typer.Option("--format", "-f")] = "rich",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
    tags: Annotated[
        list[str] | None,
        typer.Option(
            "--tag",
            help="Filter recipes by tag. Repeat to require multiple tags.",
        ),
    ] = None,
) -> None:
    """List packaged legendary recipe definitions."""

    recipes = _filter_recipes_by_tags(
        list(get_default_recipe_repository().list_recipes()),
        tags,
    )
    if output_format == "rich":
        render_recipe_list(console, recipes)
    elif output_format == "csv":
        _write_or_print_csv(recipe_rows(recipes), output)
    else:
        _write_or_print_text(model_to_json(recipes), output)


@recipe_app.command("show")
def show_recipe(
    recipe_id: Annotated[str, typer.Argument(help="Recipe id, such as legendary.twilight.")],
    output_format: Annotated[Literal["rich", "json"], typer.Option("--format", "-f")] = "rich",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
) -> None:
    """Show one recipe definition."""

    recipe = _load_recipe_or_exit(recipe_id)
    if output_format == "rich":
        render_recipe_detail(console, recipe)
    else:
        _write_or_print_text(model_to_json(recipe), output)


@recipe_app.command("evaluate")
def evaluate_recipe(
    recipe_id: Annotated[str, typer.Argument(help="Recipe id, such as legendary.twilight.")],
    api_key: Annotated[str | None, typer.Option("--api-key")] = None,
    input_dir: Annotated[Path | None, typer.Option("--input", "-i")] = None,
    output_format: Annotated[RecipeFormat, typer.Option("--format", "-f")] = "rich",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
    quantity: Annotated[int, typer.Option("--quantity", "-q", min=1)] = 1,
    graph: Annotated[
        bool,
        typer.Option("--graph", help="Include dependency graph output."),
    ] = False,
    missing_only: Annotated[
        bool,
        typer.Option(
            "--missing-only",
            help="Show only missing effective costs in rich, CSV, and JSON cost output.",
        ),
    ] = False,
) -> None:
    """Evaluate recipe readiness against an account."""

    repository = get_default_recipe_repository()
    recipe = _load_recipe_or_exit(recipe_id, repository=repository)
    snapshot = _load_snapshot(api_key=api_key, input_dir=input_dir)
    inventory = InventoryAggregator().aggregate(snapshot)
    evaluation = RecipeEvaluator(repository).evaluate(
        recipe,
        snapshot,
        inventory,
        quantity=quantity,
    )

    if output_format == "rich":
        render_recipe_evaluation(console, evaluation, missing_only=missing_only)
        if graph:
            render_recipe_graph(console, evaluation)
    elif output_format == "csv":
        rows = (
            recipe_graph_rows(evaluation)
            if graph
            else recipe_cost_rows(evaluation, missing_only=missing_only)
        )
        _write_or_print_csv(rows, output)
    else:
        _write_or_print_text(
            model_to_json(_evaluation_for_export(evaluation, missing_only=missing_only)),
            output,
        )


@recipe_app.command("validate")
def validate_recipe_data(
    output_format: Annotated[RecipeFormat, typer.Option("--format", "-f")] = "rich",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
) -> None:
    """Validate packaged recipe data for structural problems."""

    recipes = list(get_default_recipe_repository().list_recipes())
    report = validate_recipes(recipes)
    if output_format == "rich":
        render_recipe_validation_report(console, report)
    elif output_format == "csv":
        _write_or_print_csv(recipe_validation_rows(report), output)
    else:
        _write_or_print_text(model_to_json(report), output)

    if not report.is_valid:
        raise typer.Exit(1)


@activity_app.command("report")
def report_activities(
    api_key: Annotated[str | None, typer.Option("--api-key")] = None,
    input_dir: Annotated[Path | None, typer.Option("--input", "-i")] = None,
    output_format: Annotated[RecipeFormat, typer.Option("--format", "-f")] = "rich",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
    include_ready: Annotated[bool, typer.Option("--include-ready/--missing-only")] = True,
    goals: Annotated[
        list[str] | None,
        typer.Option("--goal", help="Filter by activity goal id. Repeat for multiple goals."),
    ] = None,
    tags: Annotated[
        list[str] | None,
        typer.Option("--tag", help="Filter by activity tag. Repeat to require multiple tags."),
    ] = None,
) -> None:
    """Evaluate legendary activity readiness against an account."""

    statuses = _load_activity_statuses(
        api_key=api_key,
        input_dir=input_dir,
        include_ready=include_ready,
        goals=goals,
        tags=tags,
    )
    _write_activity_statuses(statuses, output_format=output_format, output=output)


@activity_app.command("collections")
def report_collections(
    api_key: Annotated[str | None, typer.Option("--api-key")] = None,
    input_dir: Annotated[Path | None, typer.Option("--input", "-i")] = None,
    output_format: Annotated[RecipeFormat, typer.Option("--format", "-f")] = "rich",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
    data_path: Annotated[
        Path | None,
        typer.Option("--data", help="Load collection definitions from a JSON file."),
    ] = None,
    include_complete: Annotated[bool, typer.Option("--include-complete/--missing-only")] = True,
    collections: Annotated[
        list[str] | None,
        typer.Option("--collection", help="Filter by collection id. Repeat for multiple."),
    ] = None,
    tags: Annotated[
        list[str] | None,
        typer.Option("--tag", help="Filter by collection tag. Repeat to require multiple tags."),
    ] = None,
) -> None:
    """Evaluate data-defined collection progress against an account."""

    progress_entries = _load_collection_progress(
        api_key=api_key,
        input_dir=input_dir,
        data_path=data_path,
        include_complete=include_complete,
        collections=collections,
        tags=tags,
    )
    _write_collection_progress(
        progress_entries,
        output_format=output_format,
        output=output,
    )


@activity_app.command("gift-of-battle")
def plan_gift_of_battle(
    api_key: Annotated[str | None, typer.Option("--api-key")] = None,
    input_dir: Annotated[Path | None, typer.Option("--input", "-i")] = None,
    output_format: Annotated[RecipeFormat, typer.Option("--format", "-f")] = "rich",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
) -> None:
    """Evaluate Gift of Battle readiness."""

    statuses = _load_activity_statuses(
        api_key=api_key,
        input_dir=input_dir,
        goals=["gift-of-battle"],
    )
    _write_activity_statuses(statuses, output_format=output_format, output=output)


@activity_app.command("gift-of-exploration")
def plan_gift_of_exploration(
    api_key: Annotated[str | None, typer.Option("--api-key")] = None,
    input_dir: Annotated[Path | None, typer.Option("--input", "-i")] = None,
    output_format: Annotated[RecipeFormat, typer.Option("--format", "-f")] = "rich",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
) -> None:
    """Evaluate Gift of Exploration readiness."""

    statuses = _load_activity_statuses(
        api_key=api_key,
        input_dir=input_dir,
        goals=["gift-of-exploration"],
    )
    _write_activity_statuses(statuses, output_format=output_format, output=output)


@activity_app.command("starter-kits")
def plan_starter_kits(
    api_key: Annotated[str | None, typer.Option("--api-key")] = None,
    input_dir: Annotated[Path | None, typer.Option("--input", "-i")] = None,
    output_format: Annotated[RecipeFormat, typer.Option("--format", "-f")] = "rich",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
    set_numbers: Annotated[
        list[int] | None,
        typer.Option("--set", min=1, help="Evaluate only specific starter-kit set numbers."),
    ] = None,
) -> None:
    """Evaluate Legendary Weapon Starter Kit options against an account."""

    evaluations = _load_starter_kit_evaluations(
        api_key=api_key,
        input_dir=input_dir,
        set_numbers=set_numbers,
    )
    _write_starter_kit_evaluations(
        evaluations,
        output_format=output_format,
        output=output,
    )


@activity_app.command("wizard-vault")
def report_wizard_vault(
    output_format: Annotated[RecipeFormat, typer.Option("--format", "-f")] = "rich",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
    data_path: Annotated[
        Path | None,
        typer.Option(
            "--data",
            help="Load Wizard's Vault seasonal reward data from a JSON file.",
        ),
    ] = None,
    seasons: Annotated[
        list[str] | None,
        typer.Option("--season", help="Filter by Wizard's Vault season id."),
    ] = None,
    statuses: Annotated[
        list[str] | None,
        typer.Option("--status", help="Filter by season status."),
    ] = None,
    tags: Annotated[
        list[str] | None,
        typer.Option("--tag", help="Filter rewards by tag. Repeat to require multiple tags."),
    ] = None,
) -> None:
    """Inspect Wizard's Vault seasonal reward data."""

    season_data = _load_wizard_vault_seasons(
        data_path=data_path,
        seasons=seasons,
        statuses=statuses,
        tags=tags,
    )
    _write_wizard_vault_seasons(
        season_data,
        output_format=output_format,
        output=output,
    )


@activity_app.command("wizard-vault-optimize")
def optimize_wizard_vault(
    api_key: Annotated[str | None, typer.Option("--api-key")] = None,
    input_dir: Annotated[Path | None, typer.Option("--input", "-i")] = None,
    output_format: Annotated[RecipeFormat, typer.Option("--format", "-f")] = "rich",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
    data_path: Annotated[
        Path | None,
        typer.Option(
            "--data",
            help="Load Wizard's Vault seasonal reward data from a JSON file.",
        ),
    ] = None,
    seasons: Annotated[
        list[str] | None,
        typer.Option("--season", help="Filter by Wizard's Vault season id."),
    ] = None,
    statuses: Annotated[
        list[str] | None,
        typer.Option("--status", help="Filter by season status."),
    ] = None,
    tags: Annotated[
        list[str] | None,
        typer.Option("--tag", help="Filter rewards by tag. Repeat to require multiple tags."),
    ] = None,
) -> None:
    """Rank legendary-relevant Wizard's Vault rewards against an account."""

    report = _load_wizard_vault_optimization(
        api_key=api_key,
        input_dir=input_dir,
        data_path=data_path,
        seasons=seasons,
        statuses=statuses,
        tags=tags,
    )
    _write_wizard_vault_optimization(
        report,
        output_format=output_format,
        output=output,
    )


@activity_app.command("wizard-vault-validate")
def validate_wizard_vault_data(
    output_format: Annotated[RecipeFormat, typer.Option("--format", "-f")] = "rich",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
    data_path: Annotated[
        Path | None,
        typer.Option(
            "--data",
            help="Load Wizard's Vault seasonal reward data from a JSON file.",
        ),
    ] = None,
) -> None:
    """Validate Wizard's Vault seasonal reward data."""

    season_data = _load_wizard_vault_seasons(data_path=data_path)
    report = validate_wizard_vault_seasons(season_data)
    _write_wizard_vault_validation_report(
        report,
        output_format=output_format,
        output=output,
    )
    if not report.is_valid:
        raise typer.Exit(1)


@progress_app.command("score")
def progress_score(
    api_key: Annotated[str | None, typer.Option("--api-key")] = None,
    input_dir: Annotated[Path | None, typer.Option("--input", "-i")] = None,
    output_format: Annotated[RecipeFormat, typer.Option("--format", "-f")] = "rich",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
    collections_data: Annotated[
        Path | None,
        typer.Option("--collections-data", help="Load collection definitions from JSON."),
    ] = None,
    achievements_data: Annotated[
        Path | None,
        typer.Option("--achievements-data", help="Load achievement goal definitions from JSON."),
    ] = None,
    recurring_data: Annotated[
        Path | None,
        typer.Option("--recurring-data", help="Load daily/weekly task definitions from JSON."),
    ] = None,
) -> None:
    """Score account progression using available planner data."""

    report = _load_progression_report(
        api_key=api_key,
        input_dir=input_dir,
        collections_data=collections_data,
        achievements_data=achievements_data,
        recurring_data=recurring_data,
    )
    if output_format == "rich":
        render_progression_score(console, report.score)
    elif output_format == "csv":
        _write_or_print_csv(progression_score_rows(report.score), output)
    else:
        _write_or_print_text(model_to_json(report.score), output)


@progress_app.command("achievements")
def progress_achievements(
    api_key: Annotated[str | None, typer.Option("--api-key")] = None,
    input_dir: Annotated[Path | None, typer.Option("--input", "-i")] = None,
    output_format: Annotated[RecipeFormat, typer.Option("--format", "-f")] = "rich",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
    data_path: Annotated[
        Path | None,
        typer.Option("--data", help="Load achievement goal definitions from JSON."),
    ] = None,
    include_complete: Annotated[bool, typer.Option("--include-complete/--missing-only")] = True,
    goals: Annotated[
        list[str] | None,
        typer.Option("--goal", help="Filter by achievement goal id. Repeat for multiple."),
    ] = None,
    tags: Annotated[
        list[str] | None,
        typer.Option("--tag", help="Filter by achievement tag. Repeat to require multiple tags."),
    ] = None,
) -> None:
    """Evaluate achievement progress from account achievement exports."""

    statuses = _load_achievement_statuses(
        api_key=api_key,
        input_dir=input_dir,
        data_path=data_path,
        include_complete=include_complete,
        goals=goals,
        tags=tags,
    )
    _write_achievement_statuses(statuses, output_format=output_format, output=output)


@progress_app.command("dailies")
def progress_dailies(
    api_key: Annotated[str | None, typer.Option("--api-key")] = None,
    input_dir: Annotated[Path | None, typer.Option("--input", "-i")] = None,
    output_format: Annotated[RecipeFormat, typer.Option("--format", "-f")] = "rich",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
    data_path: Annotated[
        Path | None,
        typer.Option("--data", help="Load recurring task definitions from JSON."),
    ] = None,
    include_complete: Annotated[bool, typer.Option("--include-complete/--missing-only")] = True,
    tasks: Annotated[
        list[str] | None,
        typer.Option("--task", help="Filter by recurring task id. Repeat for multiple."),
    ] = None,
    tags: Annotated[
        list[str] | None,
        typer.Option(
            "--tag",
            help="Filter by recurring task tag. Repeat to require multiple tags.",
        ),
    ] = None,
) -> None:
    """Evaluate source-defined daily tasks."""

    statuses = _load_recurring_task_statuses(
        api_key=api_key,
        input_dir=input_dir,
        data_path=data_path,
        periods=["daily"],
        include_complete=include_complete,
        tasks=tasks,
        tags=tags,
    )
    _write_recurring_task_statuses(statuses, output_format=output_format, output=output)


@progress_app.command("weeklies")
def progress_weeklies(
    api_key: Annotated[str | None, typer.Option("--api-key")] = None,
    input_dir: Annotated[Path | None, typer.Option("--input", "-i")] = None,
    output_format: Annotated[RecipeFormat, typer.Option("--format", "-f")] = "rich",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
    data_path: Annotated[
        Path | None,
        typer.Option("--data", help="Load recurring task definitions from JSON."),
    ] = None,
    include_complete: Annotated[bool, typer.Option("--include-complete/--missing-only")] = True,
    tasks: Annotated[
        list[str] | None,
        typer.Option("--task", help="Filter by recurring task id. Repeat for multiple."),
    ] = None,
    tags: Annotated[
        list[str] | None,
        typer.Option(
            "--tag",
            help="Filter by recurring task tag. Repeat to require multiple tags.",
        ),
    ] = None,
) -> None:
    """Evaluate source-defined weekly tasks."""

    statuses = _load_recurring_task_statuses(
        api_key=api_key,
        input_dir=input_dir,
        data_path=data_path,
        periods=["weekly"],
        include_complete=include_complete,
        tasks=tasks,
        tags=tags,
    )
    _write_recurring_task_statuses(statuses, output_format=output_format, output=output)


@progress_app.command("recommend")
def progress_recommend(
    api_key: Annotated[str | None, typer.Option("--api-key")] = None,
    input_dir: Annotated[Path | None, typer.Option("--input", "-i")] = None,
    output_format: Annotated[RecipeFormat, typer.Option("--format", "-f")] = "rich",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
    collections_data: Annotated[
        Path | None,
        typer.Option("--collections-data", help="Load collection definitions from JSON."),
    ] = None,
    achievements_data: Annotated[
        Path | None,
        typer.Option("--achievements-data", help="Load achievement goal definitions from JSON."),
    ] = None,
    recurring_data: Annotated[
        Path | None,
        typer.Option("--recurring-data", help="Load daily/weekly task definitions from JSON."),
    ] = None,
    wizard_vault_data: Annotated[
        Path | None,
        typer.Option("--wizard-vault-data", help="Load Wizard's Vault season data from JSON."),
    ] = None,
    starter_kit_sets: Annotated[
        list[int] | None,
        typer.Option("--starter-kit-set", min=1, help="Include specific starter-kit sets."),
    ] = None,
    max_recommendations: Annotated[int, typer.Option("--max", min=1)] = 10,
) -> None:
    """Recommend the highest-value next account progression steps."""

    report = _load_progression_report(
        api_key=api_key,
        input_dir=input_dir,
        collections_data=collections_data,
        achievements_data=achievements_data,
        recurring_data=recurring_data,
        wizard_vault_data=wizard_vault_data,
        starter_kit_sets=starter_kit_sets,
        max_recommendations=max_recommendations,
    )
    if output_format == "rich":
        render_progression_report(console, report)
    elif output_format == "csv":
        _write_or_print_csv(progression_report_rows(report), output)
    else:
        _write_or_print_text(model_to_json(report), output)


@app.command()
def doctor(
    input_dir: Annotated[
        Path | None,
        typer.Option("--input", "-i", help="Validate a local export directory."),
    ] = None,
    require_api_key: Annotated[
        bool,
        typer.Option("--require-api-key", help="Fail if no API key is configured."),
    ] = False,
    api_key: Annotated[
        str | None,
        typer.Option("--api-key", help="API key to validate as configured for this run."),
    ] = None,
) -> None:
    """Validate the local development and data-loading environment."""

    report = build_doctor_report(
        input_dir=input_dir,
        require_api_key=require_api_key,
        api_key=api_key,
    )
    render_doctor_report(console, report)
    if report.has_errors:
        raise typer.Exit(1)


@app.command()
def version() -> None:
    """Print machine-readable version information."""

    table = {
        "gw2planner": __version__,
    }
    console.print_json(json.dumps(table))


def _write_or_print_json(payload: dict[str, object], output: Path | None) -> None:
    if output:
        write_json(output, payload)
    else:
        console.print_json(json.dumps(payload))


def _write_or_print_text(text: str, output: Path | None) -> None:
    if output:
        output.write_text(text + "\n", encoding="utf-8")
    else:
        sys.stdout.write(text + "\n")


def _write_or_print_csv(rows: list[dict[str, object]], output: Path | None) -> None:
    if output:
        write_csv(output, rows)
        return

    sys.stdout.write(rows_to_csv(rows))


def _render_local_export_error(exc: LocalExportError) -> None:
    console.print("[red]Local export validation failed.[/red]")
    for issue in exc.report.issues:
        subject = issue.endpoint or issue.path or exc.report.export_dir
        console.print(f"- {subject}: {issue.message}")
        console.print(f"  Fix: {issue.fix}")


def _load_recipe_or_exit(recipe_id: str, repository=None):
    resolved_repository = repository or get_default_recipe_repository()
    recipe = resolved_repository.get_recipe(recipe_id)
    if recipe:
        return recipe
    console.print(f"[red]Unknown recipe id:[/red] {recipe_id}")
    console.print("Run `gw2planner recipes list` to see available recipes.")
    raise typer.Exit(1)


def _load_activity_statuses(
    *,
    api_key: str | None,
    input_dir: Path | None,
    include_ready: bool = True,
    goals: list[str] | None = None,
    tags: list[str] | None = None,
) -> list[ActivityGoalStatus]:
    snapshot = _load_snapshot(api_key=api_key, input_dir=input_dir)
    inventory = InventoryAggregator().aggregate(snapshot)
    statuses = build_activity_report(snapshot, inventory, include_ready=include_ready)
    return filter_activity_goals(
        statuses,
        goal_ids=set(goals or []),
        tags=set(tags or []),
    )


def _write_activity_statuses(
    statuses: list[ActivityGoalStatus],
    *,
    output_format: RecipeFormat,
    output: Path | None,
) -> None:
    if output_format == "rich":
        render_activity_report(console, statuses)
    elif output_format == "csv":
        _write_or_print_csv(activity_rows(statuses), output)
    else:
        _write_or_print_text(model_to_json(statuses), output)


def _load_achievement_statuses(
    *,
    api_key: str | None,
    input_dir: Path | None,
    data_path: Path | None = None,
    include_complete: bool = True,
    goals: list[str] | None = None,
    tags: list[str] | None = None,
) -> list[AchievementGoalStatus]:
    snapshot = _load_snapshot(api_key=api_key, input_dir=input_dir)
    statuses = _build_achievement_statuses_for_snapshot(
        snapshot,
        data_path=data_path,
        include_complete=include_complete,
    )
    return filter_achievement_goals(
        statuses,
        goal_ids=set(goals or []),
        tags=set(tags or []),
    )


def _write_achievement_statuses(
    statuses: list[AchievementGoalStatus],
    *,
    output_format: RecipeFormat,
    output: Path | None,
) -> None:
    if output_format == "rich":
        render_achievement_report(console, statuses)
    elif output_format == "csv":
        _write_or_print_csv(achievement_rows(statuses), output)
    else:
        _write_or_print_text(model_to_json(statuses), output)


def _load_recurring_task_statuses(
    *,
    api_key: str | None,
    input_dir: Path | None,
    data_path: Path | None = None,
    periods: list[str] | None = None,
    include_complete: bool = True,
    tasks: list[str] | None = None,
    tags: list[str] | None = None,
) -> list[RecurringTaskStatus]:
    snapshot = _load_snapshot(api_key=api_key, input_dir=input_dir)
    inventory = InventoryAggregator().aggregate(snapshot)
    statuses = _build_recurring_task_statuses_for_snapshot(
        snapshot,
        inventory,
        data_path=data_path,
        periods=set(periods or []),
        include_complete=include_complete,
    )
    return filter_recurring_tasks(
        statuses,
        task_ids=set(tasks or []),
        periods=set(periods or []),
        tags=set(tags or []),
    )


def _write_recurring_task_statuses(
    statuses: list[RecurringTaskStatus],
    *,
    output_format: RecipeFormat,
    output: Path | None,
) -> None:
    if output_format == "rich":
        render_recurring_task_report(console, statuses)
    elif output_format == "csv":
        _write_or_print_csv(recurring_task_rows(statuses), output)
    else:
        _write_or_print_text(model_to_json(statuses), output)


def _load_collection_progress(
    *,
    api_key: str | None,
    input_dir: Path | None,
    data_path: Path | None = None,
    include_complete: bool = True,
    collections: list[str] | None = None,
    tags: list[str] | None = None,
) -> list[CollectionProgress]:
    snapshot = _load_snapshot(api_key=api_key, input_dir=input_dir)
    inventory = InventoryAggregator().aggregate(snapshot)
    try:
        definitions = (
            load_collection_definitions_from_path(data_path)
            if data_path
            else load_collection_definitions()
        )
    except CollectionDataError as exc:
        console.print(f"[red]Collection data failed to load:[/red] {exc}")
        raise typer.Exit(1) from exc
    progress_entries = evaluate_collections(
        snapshot,
        inventory,
        definitions=definitions,
        include_complete=include_complete,
    )
    return filter_collections(
        progress_entries,
        collection_ids=set(collections or []),
        tags=set(tags or []),
    )


def _write_collection_progress(
    progress_entries: list[CollectionProgress],
    *,
    output_format: RecipeFormat,
    output: Path | None,
) -> None:
    if output_format == "rich":
        render_collection_progress(console, progress_entries)
    elif output_format == "csv":
        _write_or_print_csv(collection_rows(progress_entries), output)
    else:
        _write_or_print_text(model_to_json(progress_entries), output)


def _load_progression_report(
    *,
    api_key: str | None,
    input_dir: Path | None,
    collections_data: Path | None = None,
    achievements_data: Path | None = None,
    recurring_data: Path | None = None,
    wizard_vault_data: Path | None = None,
    starter_kit_sets: list[int] | None = None,
    max_recommendations: int = 10,
) -> AccountProgressionReport:
    snapshot = _load_snapshot(api_key=api_key, input_dir=input_dir)
    inventory = InventoryAggregator().aggregate(snapshot)
    repository = get_default_recipe_repository()
    activity_statuses = build_activity_report(snapshot, inventory)
    achievement_statuses = _build_achievement_statuses_for_snapshot(
        snapshot,
        data_path=achievements_data,
    )
    collection_progress = _build_collection_progress_for_snapshot(
        snapshot,
        inventory,
        data_path=collections_data,
    )
    recurring_tasks = _build_recurring_task_statuses_for_snapshot(
        snapshot,
        inventory,
        data_path=recurring_data,
    )
    starter_kit_evaluations = (
        evaluate_starter_kit_sets(
            snapshot,
            inventory,
            repository,
            set_numbers=set(starter_kit_sets or []),
        )
        if starter_kit_sets
        else []
    )
    wizard_vault_report = None
    if wizard_vault_data:
        season_data = _load_wizard_vault_seasons(data_path=wizard_vault_data)
        wizard_vault_report = optimize_wizard_vault_rewards(snapshot, season_data)
    return build_account_progression_report(
        snapshot,
        inventory,
        repository,
        achievement_statuses=achievement_statuses,
        activity_statuses=activity_statuses,
        collection_progress=collection_progress,
        recurring_tasks=recurring_tasks,
        starter_kit_evaluations=starter_kit_evaluations,
        wizard_vault_report=wizard_vault_report,
        max_recommendations=max_recommendations,
    )


def _build_collection_progress_for_snapshot(
    snapshot: AccountSnapshot,
    inventory: Inventory,
    *,
    data_path: Path | None = None,
) -> list[CollectionProgress]:
    try:
        definitions = (
            load_collection_definitions_from_path(data_path)
            if data_path
            else load_collection_definitions()
        )
    except CollectionDataError as exc:
        console.print(f"[red]Collection data failed to load:[/red] {exc}")
        raise typer.Exit(1) from exc
    return evaluate_collections(snapshot, inventory, definitions=definitions)


def _build_achievement_statuses_for_snapshot(
    snapshot: AccountSnapshot,
    *,
    data_path: Path | None = None,
    include_complete: bool = True,
) -> list[AchievementGoalStatus]:
    try:
        definitions = (
            load_achievement_goal_definitions_from_path(data_path)
            if data_path
            else load_achievement_goal_definitions()
        )
    except AchievementDataError as exc:
        console.print(f"[red]Achievement data failed to load:[/red] {exc}")
        raise typer.Exit(1) from exc
    return build_achievement_report(
        snapshot,
        definitions=definitions,
        include_complete=include_complete,
    )


def _build_recurring_task_statuses_for_snapshot(
    snapshot: AccountSnapshot,
    inventory: Inventory,
    *,
    data_path: Path | None = None,
    periods: set[str] | None = None,
    include_complete: bool = True,
) -> list[RecurringTaskStatus]:
    try:
        definitions = (
            load_recurring_task_definitions_from_path(data_path)
            if data_path
            else load_recurring_task_definitions()
        )
    except RecurringTaskDataError as exc:
        console.print(f"[red]Recurring task data failed to load:[/red] {exc}")
        raise typer.Exit(1) from exc
    return build_recurring_task_report(
        snapshot,
        inventory,
        definitions=definitions,
        periods=periods,
        include_complete=include_complete,
    )


def _load_starter_kit_evaluations(
    *,
    api_key: str | None,
    input_dir: Path | None,
    set_numbers: list[int] | None = None,
) -> list[StarterKitSetEvaluation]:
    snapshot = _load_snapshot(api_key=api_key, input_dir=input_dir)
    inventory = InventoryAggregator().aggregate(snapshot)
    return evaluate_starter_kit_sets(
        snapshot,
        inventory,
        get_default_recipe_repository(),
        set_numbers=set(set_numbers or []),
    )


def _write_starter_kit_evaluations(
    evaluations: list[StarterKitSetEvaluation],
    *,
    output_format: RecipeFormat,
    output: Path | None,
) -> None:
    if output_format == "rich":
        render_starter_kit_evaluations(console, evaluations)
    elif output_format == "csv":
        _write_or_print_csv(starter_kit_rows(evaluations), output)
    else:
        _write_or_print_text(model_to_json(evaluations), output)


def _load_wizard_vault_seasons(
    *,
    data_path: Path | None = None,
    seasons: list[str] | None = None,
    statuses: list[str] | None = None,
    tags: list[str] | None = None,
) -> list[WizardVaultSeason]:
    try:
        season_data = (
            load_wizard_vault_seasons_from_path(data_path)
            if data_path
            else load_wizard_vault_seasons()
        )
    except WizardVaultDataError as exc:
        console.print(f"[red]Wizard's Vault data failed to load:[/red] {exc}")
        raise typer.Exit(1) from exc
    return filter_wizard_vault_seasons(
        season_data,
        season_ids=set(seasons or []),
        statuses=set(statuses or []),
        tags=set(tags or []),
    )


def _load_wizard_vault_optimization(
    *,
    api_key: str | None,
    input_dir: Path | None,
    data_path: Path | None = None,
    seasons: list[str] | None = None,
    statuses: list[str] | None = None,
    tags: list[str] | None = None,
) -> WizardVaultOptimizationReport:
    snapshot = _load_snapshot(api_key=api_key, input_dir=input_dir)
    season_data = _load_wizard_vault_seasons(
        data_path=data_path,
        seasons=seasons,
        statuses=statuses,
        tags=tags,
    )
    return optimize_wizard_vault_rewards(snapshot, season_data)


def _write_wizard_vault_seasons(
    seasons: list[WizardVaultSeason],
    *,
    output_format: RecipeFormat,
    output: Path | None,
) -> None:
    if output_format == "rich":
        render_wizard_vault_seasons(console, seasons)
    elif output_format == "csv":
        _write_or_print_csv(wizard_vault_rows(seasons), output)
    else:
        _write_or_print_text(model_to_json(seasons), output)


def _write_wizard_vault_optimization(
    report: WizardVaultOptimizationReport,
    *,
    output_format: RecipeFormat,
    output: Path | None,
) -> None:
    if output_format == "rich":
        render_wizard_vault_optimization(console, report)
    elif output_format == "csv":
        _write_or_print_csv(wizard_vault_optimization_rows(report), output)
    else:
        _write_or_print_text(model_to_json(report), output)


def _write_wizard_vault_validation_report(
    report: WizardVaultValidationReport,
    *,
    output_format: RecipeFormat,
    output: Path | None,
) -> None:
    if output_format == "rich":
        render_wizard_vault_validation_report(console, report)
    elif output_format == "csv":
        _write_or_print_csv(wizard_vault_validation_rows(report), output)
    else:
        _write_or_print_text(model_to_json(report), output)


def _filter_recipes_by_tags(recipes: list[Recipe], tags: list[str] | None) -> list[Recipe]:
    requested_tags = {tag.strip().lower() for tag in tags or [] if tag.strip()}
    if not requested_tags:
        return recipes
    return [
        recipe
        for recipe in recipes
        if requested_tags.issubset({tag.lower() for tag in recipe.tags})
    ]


def _evaluation_for_export(
    evaluation: RecipeEvaluation,
    *,
    missing_only: bool,
) -> RecipeEvaluation:
    if not missing_only:
        return evaluation
    return evaluation.model_copy(
        update={
            "costs": [cost for cost in evaluation.costs if cost.missing_quantity > 0],
        }
    )
