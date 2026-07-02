from __future__ import annotations

from collections import defaultdict

from pydantic import BaseModel, Field

from gw2_legendary_planner.planner.recipe_evaluator import RecipeEvaluation
from gw2_legendary_planner.planner.recipes import AcquisitionHint, RequirementKind


class ShoppingListGoal(BaseModel):
    """One recipe target represented in a shopping list."""

    recipe_id: str
    recipe_name: str
    requested_quantity: int
    readiness_percent: float
    missing_entries: int


class ShoppingListContribution(BaseModel):
    """How much one recipe contributes to one shopping-list entry."""

    recipe_id: str
    recipe_name: str
    required_quantity: int


class ShoppingListEntry(BaseModel):
    """One aggregated missing cost across all requested recipe goals."""

    kind: RequirementKind
    id: int | str
    name: str | None = None
    required_quantity: int
    available_quantity: int
    missing_quantity: int
    readiness_percent: float
    acquisition: AcquisitionHint | None = None
    contributions: list[ShoppingListContribution] = Field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        return self.missing_quantity == 0


class ShoppingListReport(BaseModel):
    """Aggregated, price-free shopping list for one or more recipe goals."""

    goals: list[ShoppingListGoal] = Field(default_factory=list)
    entries: list[ShoppingListEntry] = Field(default_factory=list)
    goal_count: int = 0
    entry_count: int = 0
    missing_entry_count: int = 0
    total_missing_quantity: int = 0


def build_shopping_list(
    evaluations: list[RecipeEvaluation],
    *,
    include_complete: bool = False,
) -> ShoppingListReport:
    """Build a combined shopping list from recipe effective-cost evaluations."""

    required_by_key: dict[tuple[RequirementKind, int | str], int] = defaultdict(int)
    available_by_key: dict[tuple[RequirementKind, int | str], int] = defaultdict(int)
    names_by_key: dict[tuple[RequirementKind, int | str], str | None] = {}
    acquisitions_by_key: dict[tuple[RequirementKind, int | str], AcquisitionHint | None] = {}
    contributions_by_key: dict[
        tuple[RequirementKind, int | str],
        list[ShoppingListContribution],
    ] = defaultdict(list)

    goals = [
        ShoppingListGoal(
            recipe_id=evaluation.recipe.id,
            recipe_name=evaluation.recipe.name,
            requested_quantity=evaluation.requested_quantity,
            readiness_percent=evaluation.readiness_percent,
            missing_entries=sum(1 for cost in evaluation.costs if cost.missing_quantity),
        )
        for evaluation in evaluations
    ]

    for evaluation in evaluations:
        for cost in evaluation.costs:
            key = (cost.kind, cost.id)
            required_by_key[key] += cost.required_quantity
            available_by_key[key] = max(available_by_key[key], cost.available_quantity)
            names_by_key[key] = cost.name
            if key not in acquisitions_by_key or acquisitions_by_key[key] is None:
                acquisitions_by_key[key] = cost.acquisition
            contributions_by_key[key].append(
                ShoppingListContribution(
                    recipe_id=evaluation.recipe.id,
                    recipe_name=evaluation.recipe.name,
                    required_quantity=cost.required_quantity,
                )
            )

    entries: list[ShoppingListEntry] = []
    for key, required_quantity in required_by_key.items():
        available_quantity = available_by_key[key]
        missing_quantity = max(required_quantity - available_quantity, 0)
        if missing_quantity == 0 and not include_complete:
            continue
        readiness = (
            min(available_quantity / required_quantity, 1.0)
            if required_quantity
            else 1.0
        )
        kind, requirement_id = key
        entries.append(
            ShoppingListEntry(
                kind=kind,
                id=requirement_id,
                name=names_by_key[key],
                required_quantity=required_quantity,
                available_quantity=available_quantity,
                missing_quantity=missing_quantity,
                readiness_percent=round(readiness * 100, 2),
                acquisition=acquisitions_by_key.get(key),
                contributions=contributions_by_key[key],
            )
        )

    sorted_entries = sorted(
        entries,
        key=lambda entry: (
            entry.missing_quantity == 0,
            entry.acquisition.kind if entry.acquisition else "",
            entry.kind,
            entry.name or str(entry.id),
        ),
    )
    missing_entries = [entry for entry in sorted_entries if entry.missing_quantity]
    return ShoppingListReport(
        goals=goals,
        entries=sorted_entries,
        goal_count=len(goals),
        entry_count=len(sorted_entries),
        missing_entry_count=len(missing_entries),
        total_missing_quantity=sum(entry.missing_quantity for entry in missing_entries),
    )
