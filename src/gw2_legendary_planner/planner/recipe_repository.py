from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from importlib import resources
from pathlib import Path

from gw2_legendary_planner.planner.recipes import GoalKind, Recipe


class JsonRecipeProvider:
    """Read-only recipe provider backed by a JSON file."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._recipes: list[Recipe] | None = None

    def list_recipes(self) -> Sequence[Recipe]:
        if self._recipes is None:
            with self.path.open("r", encoding="utf-8") as handle:
                self._recipes = [Recipe.model_validate(entry) for entry in json.load(handle)]
        return self._recipes

    def get_recipe(self, recipe_id: str) -> Recipe | None:
        return next((recipe for recipe in self.list_recipes() if recipe.id == recipe_id), None)


class PackagedRecipeProvider:
    """Read-only recipe provider backed by package data."""

    def __init__(self, resource_name: str = "legendary_recipes.json") -> None:
        self.resource_name = resource_name
        self._recipes: list[Recipe] | None = None

    def list_recipes(self) -> Sequence[Recipe]:
        if self._recipes is None:
            data_path = resources.files("gw2_legendary_planner.data").joinpath(
                self.resource_name
            )
            self._recipes = [
                Recipe.model_validate(entry)
                for entry in json.loads(data_path.read_text(encoding="utf-8"))
            ]
        return self._recipes

    def get_recipe(self, recipe_id: str) -> Recipe | None:
        return next((recipe for recipe in self.list_recipes() if recipe.id == recipe_id), None)


class InMemoryRecipeRepository:
    """Indexed recipe repository assembled from one or more providers."""

    def __init__(self, recipes: Iterable[Recipe]) -> None:
        self._recipes = {recipe.id: recipe for recipe in recipes}
        self._recipes_by_output: dict[tuple[GoalKind, int | str], list[Recipe]] = {}
        for recipe in self._recipes.values():
            key = (recipe.output_kind, recipe.output_id)
            self._recipes_by_output.setdefault(key, []).append(recipe)

    @classmethod
    def from_providers(cls, providers: Iterable[PackagedRecipeProvider | JsonRecipeProvider]):
        recipes: list[Recipe] = []
        for provider in providers:
            recipes.extend(provider.list_recipes())
        return cls(recipes)

    def list_recipes(self) -> Sequence[Recipe]:
        return sorted(self._recipes.values(), key=lambda recipe: recipe.id)

    def get_recipe(self, recipe_id: str) -> Recipe | None:
        return self._recipes.get(recipe_id)

    def find_recipes_for_output(
        self,
        output_kind: GoalKind,
        output_id: int | str,
    ) -> Sequence[Recipe]:
        return list(self._recipes_by_output.get((output_kind, output_id), []))


def get_default_recipe_repository() -> InMemoryRecipeRepository:
    return InMemoryRecipeRepository.from_providers([PackagedRecipeProvider()])
