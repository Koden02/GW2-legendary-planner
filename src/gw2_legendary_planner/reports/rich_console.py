from __future__ import annotations

from rich.console import Console
from rich.table import Table

from gw2_legendary_planner.planner.achievements import AchievementGoalStatus
from gw2_legendary_planner.planner.activities import ActivityGoalStatus
from gw2_legendary_planner.planner.collections import CollectionProgress
from gw2_legendary_planner.planner.legendary_focus import FocusEntry
from gw2_legendary_planner.planner.market import ShoppingListPriceReport
from gw2_legendary_planner.planner.progression import (
    AccountProgressionReport,
    AccountRecommendation,
    ProgressionScoreReport,
)
from gw2_legendary_planner.planner.recipe_evaluator import RecipeEvaluation
from gw2_legendary_planner.planner.recipe_validator import RecipeValidationReport
from gw2_legendary_planner.planner.recipes import Recipe
from gw2_legendary_planner.planner.recurring import RecurringTaskStatus
from gw2_legendary_planner.planner.shopping_list import ShoppingListReport
from gw2_legendary_planner.planner.starter_kits import StarterKitSetEvaluation
from gw2_legendary_planner.planner.wizards_vault import (
    WizardVaultOptimizationReport,
    WizardVaultSeason,
    WizardVaultValidationReport,
)
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


def render_activity_report(console: Console, statuses: list[ActivityGoalStatus]) -> None:
    table = Table(title="Legendary Activity Planners")
    table.add_column("Goal", no_wrap=True)
    table.add_column("Kind")
    table.add_column("Have", justify="right")
    table.add_column("Need", justify="right")
    table.add_column("Ready", justify="right")
    table.add_column("Action")
    for status in statuses:
        table.add_row(
            status.name,
            status.activity_kind.replace("_", " "),
            f"{status.available_quantity:,}",
            f"{status.required_quantity:,}",
            f"{status.readiness_percent:.2f}%",
            status.action,
        )
    console.print(table)


def render_achievement_report(
    console: Console,
    statuses: list[AchievementGoalStatus],
) -> None:
    if not statuses:
        console.print("[yellow]No achievement definitions are available.[/yellow]")
        return

    table = Table(title="Achievement Progress")
    table.add_column("Achievement")
    table.add_column("Current", justify="right")
    table.add_column("Required", justify="right")
    table.add_column("Ready", justify="right")
    table.add_column("Done")
    for status in statuses:
        table.add_row(
            status.name,
            f"{status.current_progress:,}",
            f"{status.required_progress:,}",
            f"{status.readiness_percent:.2f}%",
            "yes" if status.is_complete else "no",
        )
    console.print(table)


def render_recurring_task_report(
    console: Console,
    statuses: list[RecurringTaskStatus],
) -> None:
    if not statuses:
        console.print("[yellow]No recurring task definitions are available.[/yellow]")
        return

    table = Table(title="Recurring Tasks")
    table.add_column("Task")
    table.add_column("Period")
    table.add_column("Ready", justify="right")
    table.add_column("Trackable")
    table.add_column("Action")
    for status in statuses:
        table.add_row(
            status.name,
            status.period,
            f"{status.readiness_percent:.2f}%",
            "yes" if status.is_trackable else "manual",
            status.action,
        )
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


def render_collection_progress(
    console: Console,
    progress_entries: list[CollectionProgress],
) -> None:
    if not progress_entries:
        console.print("[yellow]No collection definitions are available.[/yellow]")
        return

    summary = Table(title="Collection Progress")
    summary.add_column("Collection")
    summary.add_column("Ready", justify="right")
    summary.add_column("Done", justify="right")
    summary.add_column("Unsupported", justify="right")
    summary.add_column("Complete")
    for progress in progress_entries:
        summary.add_row(
            progress.name,
            f"{progress.readiness_percent:.2f}%",
            f"{progress.completed_requirements}/{progress.total_requirements}",
            f"{progress.unsupported_requirements:,}",
            "yes" if progress.is_complete else "no",
        )
    console.print(summary)

    details = Table(title="Collection Requirements")
    details.add_column("Collection")
    details.add_column("Requirement")
    details.add_column("Kind")
    details.add_column("Required", justify="right")
    details.add_column("Available", justify="right")
    details.add_column("Missing", justify="right")
    details.add_column("Supported")
    for progress in progress_entries:
        for requirement in progress.requirements:
            details.add_row(
                progress.name,
                requirement.name,
                requirement.target_kind,
                f"{requirement.required_quantity:,}",
                f"{requirement.available_quantity:,}",
                f"{requirement.missing_quantity:,}",
                "yes" if requirement.is_supported else "no",
            )
    console.print(details)


def render_progression_score(console: Console, score: ProgressionScoreReport) -> None:
    summary = Table(title="Account Progression Score")
    summary.add_column("Metric")
    summary.add_column("Value", justify="right")
    summary.add_row("Overall", f"{score.overall_score_percent:.2f}%")
    summary.add_row("Components", f"{len(score.components):,}")
    console.print(summary)

    table = Table(title="Score Components")
    table.add_column("Component")
    table.add_column("Score", justify="right")
    table.add_column("Weight", justify="right")
    table.add_column("Detail")
    for component in score.components:
        table.add_row(
            component.name,
            f"{component.score_percent:.2f}%",
            f"{component.weight:.2f}",
            component.detail,
        )
    console.print(table)


def render_recommendations(
    console: Console,
    recommendations: list[AccountRecommendation],
) -> None:
    if not recommendations:
        console.print("[yellow]No recommendations are available.[/yellow]")
        return

    table = Table(title="What Should I Do Next?")
    table.add_column("Priority")
    table.add_column("Recommendation")
    table.add_column("Kind")
    table.add_column("Score", justify="right")
    table.add_column("Action")
    for recommendation in recommendations:
        table.add_row(
            recommendation.priority,
            recommendation.title,
            recommendation.kind.replace("_", " "),
            f"{recommendation.priority_score:.2f}",
            recommendation.action,
        )
    console.print(table)


def render_progression_report(
    console: Console,
    report: AccountProgressionReport,
) -> None:
    render_progression_score(console, report.score)
    render_recommendations(console, report.recommendations)


def render_starter_kit_evaluations(
    console: Console,
    evaluations: list[StarterKitSetEvaluation],
) -> None:
    for evaluation in evaluations:
        table = Table(title=f"{evaluation.name} ({evaluation.astral_acclaim_cost:,} AA)")
        table.add_column("Legendary", no_wrap=True)
        table.add_column("Before", justify="right")
        table.add_column("After", justify="right")
        table.add_column("Gain", justify="right")
        table.add_column("Missing", justify="right")
        table.add_column("Gift")
        table.add_column("Covered")
        for option in evaluation.options:
            table.add_row(
                option.legendary_name,
                f"{option.readiness_before_percent:.2f}%",
                f"{option.readiness_after_percent:.2f}%",
                f"{option.readiness_gain_percent:.2f}%",
                f"{option.missing_before}->{option.missing_after}",
                option.recommended_gift_choice,
                ", ".join(option.covered_items),
            )
        console.print(table)


def render_wizard_vault_seasons(
    console: Console,
    seasons: list[WizardVaultSeason],
) -> None:
    if not seasons:
        console.print("[yellow]No Wizard's Vault seasonal reward data is packaged.[/yellow]")
        return

    table = Table(title="Wizard's Vault Seasonal Rewards")
    table.add_column("Season")
    table.add_column("Status")
    table.add_column("Reward")
    table.add_column("Kind")
    table.add_column("AA", justify="right")
    table.add_column("Limit", justify="right")
    table.add_column("Verified")
    for season in seasons:
        if not season.rewards:
            table.add_row(
                season.name,
                season.status,
                "No modeled rewards",
                "-",
                "-",
                "-",
                season.last_verified.isoformat(),
            )
            continue
        for reward in season.rewards:
            table.add_row(
                season.name,
                season.status,
                reward.name,
                reward.reward_kind,
                f"{reward.astral_acclaim_cost:,}",
                f"{reward.purchase_limit:,}" if reward.purchase_limit else "-",
                reward.last_verified.isoformat(),
            )
    console.print(table)


def render_wizard_vault_validation_report(
    console: Console,
    report: WizardVaultValidationReport,
) -> None:
    if not report.issues:
        console.print("[green]Wizard's Vault data validation passed.[/green]")
        return

    table = Table(title="Wizard's Vault Data Validation")
    table.add_column("Severity")
    table.add_column("Code")
    table.add_column("Season")
    table.add_column("Reward")
    table.add_column("Message")
    for issue in report.issues:
        severity = "[red]error[/red]" if issue.severity == "error" else "[yellow]warning[/yellow]"
        table.add_row(
            severity,
            issue.code,
            issue.season_id or "-",
            issue.reward_id or "-",
            issue.message,
        )
    console.print(table)


def render_wizard_vault_optimization(
    console: Console,
    report: WizardVaultOptimizationReport,
) -> None:
    summary = Table(title="Wizard's Vault Optimization")
    summary.add_column("Metric")
    summary.add_column("Value", justify="right")
    summary.add_row("Astral Acclaim", f"{report.astral_acclaim_balance:,}")
    summary.add_row("Remaining after plan", f"{report.remaining_astral_acclaim:,}")
    summary.add_row("Recommendations", f"{len(report.recommendations):,}")
    console.print(summary)

    if not report.recommendations:
        console.print("[yellow]No legendary-relevant Wizard's Vault rewards found.[/yellow]")
        return

    table = Table(title="Recommended Rewards")
    table.add_column("Reward")
    table.add_column("Season")
    table.add_column("Cost", justify="right")
    table.add_column("Score", justify="right")
    table.add_column("Buy", justify="right")
    table.add_column("Affordable")
    table.add_column("Reason")
    for recommendation in report.recommendations:
        table.add_row(
            recommendation.reward_name,
            recommendation.season_name,
            f"{recommendation.astral_acclaim_cost:,}",
            f"{recommendation.priority_score:,}",
            f"{recommendation.recommended_quantity:,}",
            "yes" if recommendation.is_affordable else "no",
            recommendation.reason,
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


def render_shopping_list(console: Console, report: ShoppingListReport) -> None:
    summary = Table(title="Shopping List")
    summary.add_column("Metric")
    summary.add_column("Value", justify="right")
    summary.add_row("Goals", f"{report.goal_count:,}")
    summary.add_row("List entries", f"{report.entry_count:,}")
    summary.add_row("Missing entries", f"{report.missing_entry_count:,}")
    summary.add_row("Total missing quantity", f"{report.total_missing_quantity:,}")
    console.print(summary)

    if not report.entries:
        console.print("[green]No missing effective costs for the selected recipes.[/green]")
        return

    table = Table(title="Missing Effective Costs")
    table.add_column("Requirement")
    table.add_column("Kind")
    table.add_column("Required", justify="right")
    table.add_column("Available", justify="right")
    table.add_column("Missing", justify="right")
    table.add_column("Acquisition")
    table.add_column("Recipes")
    for entry in report.entries:
        table.add_row(
            entry.name or str(entry.id),
            entry.kind,
            f"{entry.required_quantity:,}",
            f"{entry.available_quantity:,}",
            f"{entry.missing_quantity:,}",
            entry.acquisition.label if entry.acquisition else "",
            ", ".join(contribution.recipe_name for contribution in entry.contributions),
        )
    console.print(table)


def render_shopping_list_prices(
    console: Console,
    report: ShoppingListPriceReport,
) -> None:
    summary = Table(title="Shopping List Market Prices")
    summary.add_column("Metric")
    summary.add_column("Value", justify="right")
    summary.add_row("Goals", f"{len(report.goals):,}")
    summary.add_row("Priced entries", f"{report.priced_entry_count:,}")
    summary.add_row("Unpriced entries", f"{report.unpriced_entry_count:,}")
    summary.add_row("Estimated buy cost", _format_copper(report.total_estimated_buy_cost))
    summary.add_row("Estimated sell value", _format_copper(report.total_estimated_sell_value))
    console.print(summary)

    if not report.entries:
        console.print("[green]No shopping-list entries are available for pricing.[/green]")
        return

    table = Table(title="Market Price Overlay")
    table.add_column("Requirement")
    table.add_column("Missing", justify="right")
    table.add_column("Status")
    table.add_column("Buy now", justify="right")
    table.add_column("Total", justify="right")
    table.add_column("Note")
    for entry in report.entries:
        table.add_row(
            entry.name or str(entry.id),
            f"{entry.missing_quantity:,}",
            entry.price_status.replace("_", " "),
            _format_optional_copper(entry.sell_listing_unit_price),
            _format_optional_copper(entry.estimated_buy_cost),
            entry.note or "",
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


def _format_optional_copper(value: int | None) -> str:
    return _format_copper(value) if value is not None else "-"


def _format_copper(value: int) -> str:
    gold, remainder = divmod(value, 10_000)
    silver, copper = divmod(remainder, 100)
    return f"{gold:,}g {silver:02d}s {copper:02d}c"
