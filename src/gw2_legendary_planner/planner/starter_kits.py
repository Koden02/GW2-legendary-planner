from __future__ import annotations

import json
from importlib import resources

from pydantic import BaseModel, Field

from gw2_legendary_planner.inventory.models import Inventory, InventoryLocation
from gw2_legendary_planner.models.snapshot import AccountSnapshot
from gw2_legendary_planner.planner.recipe_evaluator import RecipeEvaluation, RecipeEvaluator
from gw2_legendary_planner.planner.recipe_repository import InMemoryRecipeRepository
from gw2_legendary_planner.planner.recipes import Recipe, RecipeRequirement

GIFT_OF_MIGHT_ID = 19672
GIFT_OF_MAGIC_ID = 19673
GIFT_CHOICE_REQUIREMENTS = [
    RecipeRequirement(id=GIFT_OF_MIGHT_ID, quantity=1, name="Gift of Might"),
    RecipeRequirement(id=GIFT_OF_MAGIC_ID, quantity=1, name="Gift of Magic"),
]


class StarterKitSet(BaseModel):
    """Data-only definition of one Legendary Weapon Starter Kit set."""

    id: str
    name: str
    set_number: int
    astral_acclaim_cost: int = 1000
    source_url: str
    recipe_ids: list[str] = Field(default_factory=list)


class StarterKitOptionEvaluation(BaseModel):
    """Account-aware value estimate for one selectable legendary in a kit."""

    set_id: str
    set_number: int
    legendary_recipe_id: str
    legendary_name: str
    readiness_before_percent: float
    readiness_after_percent: float
    readiness_gain_percent: float
    missing_before: int
    missing_after: int
    covered_items: list[str] = Field(default_factory=list)
    recommended_gift_choice: str
    source_url: str


class StarterKitSetEvaluation(BaseModel):
    """Evaluated starter-kit set options, sorted by account-specific gain."""

    set_id: str
    set_number: int
    name: str
    astral_acclaim_cost: int
    source_url: str
    options: list[StarterKitOptionEvaluation] = Field(default_factory=list)


def load_starter_kit_sets() -> list[StarterKitSet]:
    data_path = resources.files("gw2_legendary_planner.data").joinpath(
        "starter_kit_sets.json"
    )
    return [
        StarterKitSet.model_validate(entry)
        for entry in json.loads(data_path.read_text(encoding="utf-8"))
    ]


def evaluate_starter_kit_sets(
    snapshot: AccountSnapshot,
    inventory: Inventory,
    repository: InMemoryRecipeRepository,
    *,
    sets: list[StarterKitSet] | None = None,
    set_numbers: set[int] | None = None,
) -> list[StarterKitSetEvaluation]:
    """Evaluate starter-kit options against the account without market pricing."""

    selected_sets = [
        starter_set
        for starter_set in sets or load_starter_kit_sets()
        if not set_numbers or starter_set.set_number in set_numbers
    ]
    return [
        evaluate_starter_kit_set(snapshot, inventory, repository, starter_set)
        for starter_set in selected_sets
    ]


def evaluate_starter_kit_set(
    snapshot: AccountSnapshot,
    inventory: Inventory,
    repository: InMemoryRecipeRepository,
    starter_set: StarterKitSet,
) -> StarterKitSetEvaluation:
    evaluator = RecipeEvaluator(repository)
    options = [
        _evaluate_option(snapshot, inventory, repository, evaluator, starter_set, recipe_id)
        for recipe_id in starter_set.recipe_ids
    ]
    return StarterKitSetEvaluation(
        set_id=starter_set.id,
        set_number=starter_set.set_number,
        name=starter_set.name,
        astral_acclaim_cost=starter_set.astral_acclaim_cost,
        source_url=starter_set.source_url,
        options=sorted(
            [option for option in options if option],
            key=lambda option: (
                -option.readiness_gain_percent,
                -option.readiness_after_percent,
                option.legendary_name,
            ),
        ),
    )


def _evaluate_option(
    snapshot: AccountSnapshot,
    inventory: Inventory,
    repository: InMemoryRecipeRepository,
    evaluator: RecipeEvaluator,
    starter_set: StarterKitSet,
    recipe_id: str,
) -> StarterKitOptionEvaluation | None:
    recipe = repository.get_recipe(recipe_id)
    if recipe is None:
        return None

    before = evaluator.evaluate(recipe, snapshot, inventory)
    after_by_choice = [
        (
            gift_choice,
            evaluator.evaluate(
                recipe,
                snapshot,
                _inventory_with_starter_kit_items(inventory, starter_set, recipe, gift_choice),
            ),
        )
        for gift_choice in GIFT_CHOICE_REQUIREMENTS
    ]
    gift_choice, after = max(
        after_by_choice,
        key=lambda entry: (
            entry[1].readiness_percent,
            -_missing_entries(entry[1]),
            entry[0].name or "",
        ),
    )
    covered_items = [
        requirement.name or str(requirement.id)
        for requirement in _covered_kit_requirements(recipe, gift_choice)
    ]
    return StarterKitOptionEvaluation(
        set_id=starter_set.id,
        set_number=starter_set.set_number,
        legendary_recipe_id=recipe.id,
        legendary_name=recipe.name,
        readiness_before_percent=before.readiness_percent,
        readiness_after_percent=after.readiness_percent,
        readiness_gain_percent=round(after.readiness_percent - before.readiness_percent, 2),
        missing_before=_missing_entries(before),
        missing_after=_missing_entries(after),
        covered_items=covered_items,
        recommended_gift_choice=gift_choice.name or str(gift_choice.id),
        source_url=starter_set.source_url,
    )


def _inventory_with_starter_kit_items(
    inventory: Inventory,
    starter_set: StarterKitSet,
    recipe: Recipe,
    gift_choice: RecipeRequirement,
) -> Inventory:
    enriched_inventory = inventory.model_copy(deep=True)
    for requirement in _covered_kit_requirements(recipe, gift_choice):
        if requirement.kind != "item" or not isinstance(requirement.id, int):
            continue
        enriched_inventory.add(
            requirement.id,
            requirement.quantity,
            InventoryLocation(
                source=f"starter_kit:{starter_set.id}",
                quantity=requirement.quantity,
            ),
        )
    return enriched_inventory


def _covered_kit_requirements(
    recipe: Recipe,
    gift_choice: RecipeRequirement,
) -> list[RecipeRequirement]:
    top_level_covered = [
        requirement
        for requirement in recipe.requirements
        if requirement.name not in {"Gift of Mastery", "Gift of Fortune"}
    ]
    return [*top_level_covered, gift_choice]


def _missing_entries(evaluation: RecipeEvaluation) -> int:
    return sum(1 for cost in evaluation.costs if cost.missing_quantity > 0)
