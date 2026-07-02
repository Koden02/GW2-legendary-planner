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
from gw2_legendary_planner.models.snapshot import AccountSnapshot
from gw2_legendary_planner.planner.legendary_focus import build_legendary_focus_report
from gw2_legendary_planner.planner.recipe_evaluator import RecipeEvaluation, RecipeEvaluator
from gw2_legendary_planner.planner.recipe_repository import get_default_recipe_repository
from gw2_legendary_planner.planner.recipe_validator import validate_recipes
from gw2_legendary_planner.planner.recipes import Recipe
from gw2_legendary_planner.reports.exporters import (
    focus_rows,
    inventory_rows,
    model_to_json,
    recipe_cost_rows,
    recipe_graph_rows,
    recipe_rows,
    recipe_validation_rows,
    rows_to_csv,
    summary_rows,
    write_csv,
    write_json,
)
from gw2_legendary_planner.reports.rich_console import (
    render_account_summary,
    render_focus_report,
    render_recipe_detail,
    render_recipe_evaluation,
    render_recipe_graph,
    render_recipe_list,
    render_recipe_validation_report,
)
from gw2_legendary_planner.reports.summary import build_account_summary

app = typer.Typer(help="Guild Wars 2 account progression and legendary planner.")
export_app = typer.Typer(help="Export planner data.")
recipe_app = typer.Typer(help="Inspect and evaluate data-defined recipes.")
app.add_typer(export_app, name="export")
app.add_typer(recipe_app, name="recipes")
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
