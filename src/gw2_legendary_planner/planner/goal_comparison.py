from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from gw2_legendary_planner.planner.market import ShoppingListPriceReport
from gw2_legendary_planner.planner.recipe_evaluator import RecipeEvaluation, RequirementCost
from gw2_legendary_planner.planner.recipes import AcquisitionKind, RequirementKind

RequirementComparisonCategory = Literal["account_bound", "manual", "tradeable"]

_ACCOUNT_BOUND_ACQUISITIONS: set[AcquisitionKind] = {
    "dungeon_vendor",
    "reward_track",
    "world_completion",
}


class GoalRequirementComparison(BaseModel):
    """One missing requirement in a user-selected goal comparison."""

    kind: RequirementKind
    id: int | str
    name: str | None = None
    required_quantity: int
    available_quantity: int
    missing_quantity: int
    category: RequirementComparisonCategory
    acquisition: str | None = None
    estimated_buy_cost: int | None = None


class GoalComparison(BaseModel):
    """Readiness and missing-cost summary for one possible current goal."""

    recipe_id: str
    recipe_name: str
    requested_quantity: int
    tags: list[str] = Field(default_factory=list)
    generation: str | None = None
    family: str | None = None
    expansion: str | None = None
    weapon_type: str | None = None
    variant_group: str | None = None
    source_urls: list[str] = Field(default_factory=list)
    readiness_percent: float
    missing_entry_count: int
    total_missing_quantity: int
    account_bound_missing_entries: int
    manual_missing_entries: int
    tradeable_missing_entries: int
    estimated_buy_cost: int | None = None
    recommended_action: str
    missing_requirements: list[GoalRequirementComparison] = Field(default_factory=list)


class GoalComparisonReport(BaseModel):
    """Available recipe goals plus the user's current selected goal ids."""

    goals: list[GoalComparison] = Field(default_factory=list)
    selected_goal_ids: list[str] = Field(default_factory=list)
    goal_count: int = 0


def build_goal_comparison_report(
    evaluations: list[RecipeEvaluation],
    *,
    selected_goal_ids: list[str] | None = None,
    price_reports_by_recipe: dict[str, ShoppingListPriceReport] | None = None,
) -> GoalComparisonReport:
    """Build comparison data for goal selection surfaces."""

    price_reports = price_reports_by_recipe or {}
    selected_ids = _dedupe_selected_ids(selected_goal_ids or [], evaluations)
    goals = [
        _build_goal_comparison(
            evaluation,
            price_report=price_reports.get(evaluation.recipe.id),
        )
        for evaluation in evaluations
    ]
    return GoalComparisonReport(
        goals=sorted(goals, key=lambda goal: (-goal.readiness_percent, goal.recipe_name)),
        selected_goal_ids=selected_ids,
        goal_count=len(goals),
    )


def _build_goal_comparison(
    evaluation: RecipeEvaluation,
    *,
    price_report: ShoppingListPriceReport | None = None,
) -> GoalComparison:
    price_by_key = (
        {(entry.kind, entry.id): entry for entry in price_report.entries}
        if price_report
        else {}
    )
    missing_requirements = [
        _build_requirement_comparison(cost, price_by_key=price_by_key)
        for cost in evaluation.costs
        if cost.missing_quantity > 0
    ]
    account_bound_count = _count_category(missing_requirements, "account_bound")
    manual_count = _count_category(missing_requirements, "manual")
    tradeable_count = _count_category(missing_requirements, "tradeable")
    estimated_buy_cost = (
        price_report.total_estimated_buy_cost if price_report is not None else None
    )
    return GoalComparison(
        recipe_id=evaluation.recipe.id,
        recipe_name=evaluation.recipe.name,
        requested_quantity=evaluation.requested_quantity,
        tags=evaluation.recipe.tags,
        generation=evaluation.recipe.metadata.generation,
        family=evaluation.recipe.metadata.family,
        expansion=evaluation.recipe.metadata.expansion,
        weapon_type=evaluation.recipe.metadata.weapon_type,
        variant_group=evaluation.recipe.metadata.variant_group,
        source_urls=evaluation.recipe.metadata.source_urls,
        readiness_percent=evaluation.readiness_percent,
        missing_entry_count=len(missing_requirements),
        total_missing_quantity=sum(
            requirement.missing_quantity for requirement in missing_requirements
        ),
        account_bound_missing_entries=account_bound_count,
        manual_missing_entries=manual_count,
        tradeable_missing_entries=tradeable_count,
        estimated_buy_cost=estimated_buy_cost,
        recommended_action=_recommended_action(evaluation, missing_requirements),
        missing_requirements=missing_requirements,
    )


def _build_requirement_comparison(
    cost: RequirementCost,
    *,
    price_by_key: dict[tuple[RequirementKind, int | str], object],
) -> GoalRequirementComparison:
    price_entry = price_by_key.get((cost.kind, cost.id))
    estimated_buy_cost = getattr(price_entry, "estimated_buy_cost", None)
    return GoalRequirementComparison(
        kind=cost.kind,
        id=cost.id,
        name=cost.name,
        required_quantity=cost.required_quantity,
        available_quantity=cost.available_quantity,
        missing_quantity=cost.missing_quantity,
        category=_requirement_category(cost),
        acquisition=cost.acquisition.label if cost.acquisition else None,
        estimated_buy_cost=estimated_buy_cost,
    )


def _requirement_category(cost: RequirementCost) -> RequirementComparisonCategory:
    if cost.kind != "item":
        return "account_bound"
    if cost.acquisition is None:
        return "tradeable"
    if cost.acquisition.kind in _ACCOUNT_BOUND_ACQUISITIONS:
        return "account_bound"
    if cost.acquisition.kind == "material":
        return "tradeable"
    return "manual"


def _recommended_action(
    evaluation: RecipeEvaluation,
    missing_requirements: list[GoalRequirementComparison],
) -> str:
    if evaluation.is_ready:
        return "Craft or account for the completed target."
    for category in ("account_bound", "manual", "tradeable"):
        requirement = next(
            (
                candidate
                for candidate in missing_requirements
                if candidate.category == category
            ),
            None,
        )
        if requirement is None:
            continue
        name = requirement.name or str(requirement.id)
        if category == "account_bound":
            return f"Prioritize account-bound progress for {name}."
        if category == "manual":
            acquisition = requirement.acquisition or "its acquisition source"
            return f"Resolve {name} through {acquisition}."
        return f"Acquire tradeable materials starting with {name}."
    return "Review remaining requirements."


def _count_category(
    requirements: list[GoalRequirementComparison],
    category: RequirementComparisonCategory,
) -> int:
    return sum(1 for requirement in requirements if requirement.category == category)


def _dedupe_selected_ids(
    selected_goal_ids: list[str],
    evaluations: list[RecipeEvaluation],
) -> list[str]:
    available_ids = {evaluation.recipe.id for evaluation in evaluations}
    return [
        goal_id
        for goal_id in dict.fromkeys(selected_goal_ids)
        if goal_id in available_ids
    ]
