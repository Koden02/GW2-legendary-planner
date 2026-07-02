from __future__ import annotations

from rich.console import Console
from rich.table import Table

from gw2_legendary_planner.planner.legendary_focus import FocusEntry
from gw2_legendary_planner.planner.recipe_evaluator import RecipeEvaluation
from gw2_legendary_planner.planner.recipe_validator import RecipeValidationReport
from gw2_legendary_planner.planner.recipes import Recipe
from gw2_legendary_planner.reports.summary import AccountSummary


def render_account_summary(console: Console, summary: AccountSummary) -> None:
    table = Table(title="Account Summary")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("Account", summary.account_name or "Unknown")
    table.add_row("Gold", f"{summary.gold:,.2f}")
    table.add_row("Gems", f"{summary.gems:,}")
    table.add_row("Characters", f"{len(summary.characters):,}")
    table.add_row("Crafting disciplines", f"{len(summary.crafting_disciplines):,}")
    table.add_row("Legendary armory entries", f"{summary.legendary_armory_entries:,}")
    table.add_row("Legendary armory total", f"{summary.legendary_armory_total:,}")
    table.add_row("Unique item count", f"{summary.unique_item_count:,}")
    table.add_row("Total item count", f"{summary.total_item_count:,}")
    console.print(table)


def render_focus_report(console: Console, entries: list[FocusEntry]) -> None:
    table = Table(title="Legendary Focus Report")
    table.add_column("Name")
    table.add_column("Category")
    table.add_column("Qty", justify="right")
    table.add_column("Locations")
    for entry in entries:
        if not entry.is_present:
            continue
        locations = ", ".join(sorted({location.source for location in entry.locations})) or "wallet"
        table.add_row(entry.name, entry.category, f"{entry.quantity:,}", locations)
    console.print(table)


def render_recipe_list(console: Console, recipes: list[Recipe]) -> None:
    table = Table(title="Legendary Recipes")
    table.add_column("ID", no_wrap=True)
    table.add_column("Name")
    table.add_column("Output")
    table.add_column("Reqs", justify="right")
    table.add_column("Tags")
    for recipe in recipes:
        table.add_row(
            recipe.id,
            recipe.name,
            f"{recipe.output_kind}:{recipe.output_id}",
            str(len(recipe.requirements)),
            ", ".join(recipe.tags),
        )
    console.print(table)


def render_recipe_detail(console: Console, recipe: Recipe) -> None:
    table = Table(title=f"Recipe: {recipe.name}")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("ID", recipe.id)
    table.add_row("Output", f"{recipe.output_kind}:{recipe.output_id} x{recipe.output_quantity}")
    table.add_row("Tags", ", ".join(recipe.tags))
    console.print(table)

    requirements = Table(title="Requirements")
    requirements.add_column("Kind")
    requirements.add_column("ID")
    requirements.add_column("Name")
    requirements.add_column("Qty", justify="right")
    requirements.add_column("Acquisition")
    for requirement in recipe.requirements:
        requirements.add_row(
            requirement.kind,
            str(requirement.id),
            requirement.name or "",
            f"{requirement.quantity:,}",
            requirement.acquisition.label if requirement.acquisition else "",
        )
    console.print(requirements)


def render_recipe_evaluation(
    console: Console,
    evaluation: RecipeEvaluation,
    *,
    missing_only: bool = False,
) -> None:
    summary = Table(title=f"Recipe Readiness: {evaluation.recipe.name}")
    summary.add_column("Metric")
    summary.add_column("Value", justify="right")
    summary.add_row("Recipe ID", evaluation.recipe.id)
    summary.add_row("Readiness", f"{evaluation.readiness_percent:.2f}%")
    summary.add_row("Ready", "yes" if evaluation.is_ready else "no")
    missing_entries = sum(1 for cost in evaluation.costs if cost.missing_quantity)
    summary.add_row("Missing entries", str(missing_entries))
    console.print(summary)

    costs = Table(title="Effective Crafting Cost")
    costs.add_column("Requirement")
    costs.add_column("Required", justify="right")
    costs.add_column("Available", justify="right")
    costs.add_column("Missing", justify="right")
    costs.add_column("Ready", justify="right")
    costs.add_column("Acquisition")
    visible_costs = [
        cost for cost in evaluation.costs if not missing_only or cost.missing_quantity > 0
    ]
    if not visible_costs:
        costs.add_row("No missing effective costs", "-", "-", "-", "100.00%", "-")
    for cost in visible_costs:
        costs.add_row(
            cost.name or str(cost.id),
            f"{cost.required_quantity:,}",
            f"{cost.available_quantity:,}",
            f"{cost.missing_quantity:,}",
            f"{cost.readiness * 100:.2f}%",
            cost.acquisition.label if cost.acquisition else "",
        )
    console.print(costs)


def render_recipe_graph(console: Console, evaluation: RecipeEvaluation) -> None:
    nodes_by_id = {node.id: node for node in evaluation.dependency_graph.nodes}
    table = Table(title="Recipe Dependency Graph")
    table.add_column("Parent")
    table.add_column("Child")
    table.add_column("Kind")
    table.add_column("Qty", justify="right")
    table.add_column("Status")
    for edge in evaluation.dependency_graph.edges:
        child = nodes_by_id[edge.child_id]
        table.add_row(
            nodes_by_id[edge.parent_id].label,
            child.label,
            child.kind,
            f"{child.quantity:,}",
            child.status,
        )
    console.print(table)


def render_recipe_validation_report(console: Console, report: RecipeValidationReport) -> None:
    if not report.issues:
        console.print("[green]Recipe data validation passed.[/green]")
        return

    table = Table(title="Recipe Data Validation")
    table.add_column("Severity")
    table.add_column("Code")
    table.add_column("Recipe")
    table.add_column("Req")
    table.add_column("Message")
    for issue in report.issues:
        severity = "[red]error[/red]" if issue.severity == "error" else "[yellow]warning[/yellow]"
        table.add_row(
            severity,
            issue.code,
            issue.recipe_id or "-",
            str(issue.requirement_index) if issue.requirement_index is not None else "-",
            issue.message,
        )
    console.print(table)
