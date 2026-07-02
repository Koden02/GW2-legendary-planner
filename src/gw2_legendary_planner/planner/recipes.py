from __future__ import annotations

from collections.abc import Sequence
from typing import Literal, Protocol

from pydantic import BaseModel, Field, model_validator

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


class RecipeMetadata(BaseModel):
    """Optional classification for planner/report surfaces."""

    generation: str | None = None
    family: str | None = None
    expansion: str | None = None
    weapon_type: str | None = None
    variant_group: str | None = None
    source_urls: list[str] = Field(default_factory=list)


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
    metadata: RecipeMetadata = Field(default_factory=RecipeMetadata)

    @model_validator(mode="after")
    def infer_metadata_from_tags(self) -> Recipe:
        if self.metadata.generation is None:
            self.metadata.generation = next(
                (tag for tag in self.tags if tag.startswith("generation_")),
                None,
            )
        if self.metadata.family is None and self.metadata.generation is not None:
            self.metadata.family = self.metadata.generation
        if self.metadata.weapon_type is None and "weapon" in self.tags:
            known_tags = {
                "api_verified",
                "gift",
                "legendary",
                "mystic_forge",
                "weapon",
                "weapon_gift",
                "wiki_verified",
            }
            self.metadata.weapon_type = next(
                (
                    tag
                    for tag in self.tags
                    if tag not in known_tags and not tag.startswith("generation_")
                ),
                None,
            )
        return self


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
