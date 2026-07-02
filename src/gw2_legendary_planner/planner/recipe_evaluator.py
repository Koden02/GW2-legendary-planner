from __future__ import annotations

from collections import defaultdict
from math import ceil

from pydantic import BaseModel, Field

from gw2_legendary_planner.inventory.models import Inventory
from gw2_legendary_planner.models.snapshot import AccountSnapshot
from gw2_legendary_planner.planner.recipe_repository import InMemoryRecipeRepository
from gw2_legendary_planner.planner.recipes import (
    AcquisitionHint,
    DependencyEdge,
    DependencyGraph,
    DependencyNode,
    Recipe,
    RecipeRequirement,
    RequirementKind,
)


class RequirementEvaluation(BaseModel):
    requirement: RecipeRequirement
    required_quantity: int
    available_quantity: int
    missing_quantity: int
    readiness: float
    source_recipe_id: str | None = None
    children: list[RequirementEvaluation] = Field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        return self.missing_quantity == 0


class RequirementCost(BaseModel):
    kind: RequirementKind
    id: int | str
    name: str | None = None
    required_quantity: int
    available_quantity: int
    missing_quantity: int
    readiness: float
    acquisition: AcquisitionHint | None = None


class RecipeEvaluation(BaseModel):
    recipe: Recipe
    requested_quantity: int = 1
    readiness: float
    readiness_percent: float
    is_ready: bool
    requirements: list[RequirementEvaluation]
    costs: list[RequirementCost]
    dependency_graph: DependencyGraph


class RecipeEvaluator:
    """Evaluate data-defined recipes against a neutral account inventory."""

    def __init__(self, repository: InMemoryRecipeRepository) -> None:
        self.repository = repository

    def evaluate(
        self,
        recipe: Recipe,
        snapshot: AccountSnapshot,
        inventory: Inventory,
        *,
        quantity: int = 1,
    ) -> RecipeEvaluation:
        requirements = [
            self._evaluate_requirement(
                requirement,
                snapshot,
                inventory,
                multiplier=quantity,
                seen_recipe_ids={recipe.id},
            )
            for requirement in recipe.requirements
        ]
        costs = self._aggregate_costs(requirements, snapshot, inventory)
        readiness = _average([cost.readiness for cost in costs]) if costs else 1.0
        return RecipeEvaluation(
            recipe=recipe,
            requested_quantity=quantity,
            readiness=readiness,
            readiness_percent=round(readiness * 100, 2),
            is_ready=all(cost.missing_quantity == 0 for cost in costs),
            requirements=requirements,
            costs=costs,
            dependency_graph=self._build_dependency_graph(recipe, requirements),
        )

    def _evaluate_requirement(
        self,
        requirement: RecipeRequirement,
        snapshot: AccountSnapshot,
        inventory: Inventory,
        *,
        multiplier: int,
        seen_recipe_ids: set[str],
    ) -> RequirementEvaluation:
        required_quantity = requirement.quantity * multiplier
        available_quantity = self._available_quantity(requirement, snapshot, inventory)
        direct_missing = max(required_quantity - available_quantity, 0)
        children: list[RequirementEvaluation] = []
        source_recipe_id: str | None = None

        recipe = self._find_source_recipe(requirement)
        if direct_missing and recipe and recipe.id not in seen_recipe_ids:
            source_recipe_id = recipe.id
            child_multiplier = ceil(direct_missing / recipe.output_quantity)
            child_seen = {*seen_recipe_ids, recipe.id}
            children = [
                self._evaluate_requirement(
                    child,
                    snapshot,
                    inventory,
                    multiplier=child_multiplier,
                    seen_recipe_ids=child_seen,
                )
                for child in recipe.requirements
            ]

        if not children:
            readiness = (
                min(available_quantity / required_quantity, 1.0)
                if required_quantity
                else 1.0
            )
            missing_quantity = direct_missing
        else:
            child_readiness = _average([child.readiness for child in children])
            covered_by_available = min(available_quantity, required_quantity)
            covered_by_children = direct_missing * child_readiness
            readiness = min((covered_by_available + covered_by_children) / required_quantity, 1.0)
            missing_quantity = 0 if all(child.is_complete for child in children) else direct_missing

        return RequirementEvaluation(
            requirement=requirement,
            required_quantity=required_quantity,
            available_quantity=available_quantity,
            missing_quantity=missing_quantity,
            readiness=round(readiness, 4),
            source_recipe_id=source_recipe_id,
            children=children,
        )

    def _find_source_recipe(self, requirement: RecipeRequirement) -> Recipe | None:
        recipes = self.repository.find_recipes_for_output(requirement.kind, requirement.id)
        return recipes[0] if recipes else None

    def _available_quantity(
        self,
        requirement: RecipeRequirement,
        snapshot: AccountSnapshot,
        inventory: Inventory,
    ) -> int:
        if requirement.kind == "item" and isinstance(requirement.id, int):
            return inventory.quantity_for(requirement.id)
        if requirement.kind == "currency" and isinstance(requirement.id, int):
            return snapshot.wallet_value(requirement.id)
        return 0

    def _aggregate_costs(
        self,
        requirements: list[RequirementEvaluation],
        snapshot: AccountSnapshot,
        inventory: Inventory,
    ) -> list[RequirementCost]:
        required_by_key: dict[tuple[RequirementKind, int | str], int] = defaultdict(int)
        names_by_key: dict[tuple[RequirementKind, int | str], str | None] = {}
        acquisitions_by_key: dict[tuple[RequirementKind, int | str], AcquisitionHint | None] = {}

        for leaf in _iter_effective_leaf_requirements(requirements):
            key = (leaf.requirement.kind, leaf.requirement.id)
            required_by_key[key] += leaf.required_quantity
            names_by_key[key] = leaf.requirement.name
            if key not in acquisitions_by_key or acquisitions_by_key[key] is None:
                acquisitions_by_key[key] = leaf.requirement.acquisition

        costs: list[RequirementCost] = []
        sorted_requirements = sorted(required_by_key.items(), key=lambda item: str(item[0]))
        for key, required_quantity in sorted_requirements:
            kind, item_id = key
            available_quantity = self._available_quantity(
                RecipeRequirement(kind=kind, id=item_id, quantity=required_quantity),
                snapshot,
                inventory,
            )
            missing_quantity = max(required_quantity - available_quantity, 0)
            readiness = (
                min(available_quantity / required_quantity, 1.0)
                if required_quantity
                else 1.0
            )
            costs.append(
                RequirementCost(
                    kind=kind,
                    id=item_id,
                    name=names_by_key[key],
                    required_quantity=required_quantity,
                    available_quantity=available_quantity,
                    missing_quantity=missing_quantity,
                    readiness=round(readiness, 4),
                    acquisition=acquisitions_by_key.get(key),
                )
            )
        return sorted(
            costs,
            key=lambda cost: (
                cost.missing_quantity == 0,
                cost.readiness,
                cost.name or str(cost.id),
            ),
        )

    def _build_dependency_graph(
        self,
        recipe: Recipe,
        requirements: list[RequirementEvaluation],
    ) -> DependencyGraph:
        nodes: list[DependencyNode] = [
            DependencyNode(
                id=f"recipe:{recipe.id}",
                label=recipe.name,
                kind="recipe",
                recipe_id=recipe.id,
                status="complete" if not requirements else "unknown",
            )
        ]
        edges: list[DependencyEdge] = []
        for index, requirement in enumerate(requirements):
            self._append_requirement_graph(
                nodes,
                edges,
                parent_id=f"recipe:{recipe.id}",
                evaluation=requirement,
                path=f"{recipe.id}.{index}",
            )
        node_by_id = {node.id: node for node in nodes}
        for edge in edges:
            node_by_id[edge.parent_id].child_ids.append(edge.child_id)
        return DependencyGraph(nodes=nodes, edges=edges)

    def _append_requirement_graph(
        self,
        nodes: list[DependencyNode],
        edges: list[DependencyEdge],
        *,
        parent_id: str,
        evaluation: RequirementEvaluation,
        path: str,
    ) -> None:
        requirement_node_id = (
            f"requirement:{path}:{evaluation.requirement.kind}:{evaluation.requirement.id}"
        )
        status = _status_for(evaluation.readiness)
        nodes.append(
            DependencyNode(
                id=requirement_node_id,
                label=evaluation.requirement.name or str(evaluation.requirement.id),
                kind="requirement",
                requirement=evaluation.requirement,
                quantity=evaluation.required_quantity,
                status=status,
            )
        )
        edges.append(DependencyEdge(parent_id=parent_id, child_id=requirement_node_id))

        if not evaluation.source_recipe_id:
            return

        recipe_node_id = f"recipe:{path}:{evaluation.source_recipe_id}"
        source_recipe = self.repository.get_recipe(evaluation.source_recipe_id)
        nodes.append(
            DependencyNode(
                id=recipe_node_id,
                label=(
                    f"Recipe: {source_recipe.name}"
                    if source_recipe
                    else f"Recipe: {evaluation.source_recipe_id}"
                ),
                kind="recipe",
                recipe_id=evaluation.source_recipe_id,
                status=status,
            )
        )
        edges.append(DependencyEdge(parent_id=requirement_node_id, child_id=recipe_node_id))
        for index, child in enumerate(evaluation.children):
            self._append_requirement_graph(
                nodes,
                edges,
                parent_id=recipe_node_id,
                evaluation=child,
                path=f"{path}.{index}",
            )


def _iter_effective_leaf_requirements(
    requirements: list[RequirementEvaluation],
) -> list[RequirementEvaluation]:
    leaves: list[RequirementEvaluation] = []
    for requirement in requirements:
        has_enough_direct_inventory = (
            requirement.available_quantity >= requirement.required_quantity
        )
        if has_enough_direct_inventory or not requirement.children:
            leaves.append(requirement)
        else:
            leaves.extend(_iter_effective_leaf_requirements(requirement.children))
    return leaves


def _average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 1.0


def _status_for(readiness: float) -> str:
    if readiness >= 1:
        return "complete"
    if readiness <= 0:
        return "missing"
    return "partial"
