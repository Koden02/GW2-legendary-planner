from __future__ import annotations

from collections.abc import Sequence
from typing import Literal, Protocol

from pydantic import BaseModel, Field

RequirementKind = Literal["item", "currency", "account_unlock", "achievement", "collection"]
GoalKind = Literal["item", "currency", "achievement", "collection", "account_unlock"]
AcquisitionKind = Literal[
    "crafting",
    "dungeon_vendor",
    "material",
    "mystic_forge",
    "reward_track",
    "vendor",
    "world_completion",
]


class AcquisitionHint(BaseModel):
    """Human-facing acquisition context for a terminal recipe requirement."""

    kind: AcquisitionKind
    label: str
    note: str | None = None
    source_url: str | None = None


class RecipeRequirement(BaseModel):
    """Atomic requirement for a future recipe or account-progression goal."""

    kind: RequirementKind = "item"
    id: int | str
    quantity: int = 1
    name: str | None = None
    acquisition: AcquisitionHint | None = None
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)


class Recipe(BaseModel):
    """Data-only recipe definition reserved for Phase 2 evaluation."""

    id: str
    output_kind: GoalKind = "item"
    output_id: int | str
    output_quantity: int = 1
    name: str
    requirements: list[RecipeRequirement] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class Goal(BaseModel):
    """Target that a future planner can evaluate against account state."""

    id: str
    kind: GoalKind
    target_id: int | str
    quantity: int = 1
    name: str
    tags: list[str] = Field(default_factory=list)


class DependencyNode(BaseModel):
    """Serializable node shape for future recipe dependency graphs."""

    id: str
    label: str
    kind: Literal["recipe", "requirement"] = "requirement"
    requirement: RecipeRequirement | None = None
    recipe_id: str | None = None
    quantity: int = 1
    status: Literal["complete", "partial", "missing", "unknown"] = "unknown"
    child_ids: list[str] = Field(default_factory=list)


class DependencyEdge(BaseModel):
    parent_id: str
    child_id: str


class DependencyGraph(BaseModel):
    nodes: list[DependencyNode] = Field(default_factory=list)
    edges: list[DependencyEdge] = Field(default_factory=list)


class RecipeProvider(Protocol):
    """Read-only source of recipe definitions."""

    def list_recipes(self) -> Sequence[Recipe]:
        """Return all recipes available from this provider."""

    def get_recipe(self, recipe_id: str) -> Recipe | None:
        """Return one recipe by provider-specific recipe id."""


class RecipeRepository(Protocol):
    """Repository abstraction for recipe lookup across providers."""

    def list_recipes(self) -> Sequence[Recipe]:
        """Return all known recipes."""

    def get_recipe(self, recipe_id: str) -> Recipe | None:
        """Return one recipe by recipe id."""

    def find_recipes_for_output(
        self,
        output_kind: GoalKind,
        output_id: int | str,
    ) -> Sequence[Recipe]:
        """Return recipes that can produce the requested output."""
