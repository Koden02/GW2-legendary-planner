from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, Field

from gw2_legendary_planner.planner.recipes import Recipe


class RecipeValidationSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class RecipeValidationIssue(BaseModel):
    severity: RecipeValidationSeverity
    code: str
    message: str
    recipe_id: str | None = None
    requirement_index: int | None = None


class RecipeValidationReport(BaseModel):
    issues: list[RecipeValidationIssue] = Field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not any(
            issue.severity == RecipeValidationSeverity.ERROR for issue in self.issues
        )

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == RecipeValidationSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(
            1 for issue in self.issues if issue.severity == RecipeValidationSeverity.WARNING
        )


@dataclass(frozen=True)
class RecipeValidator:
    """Structural validator for recipe data files."""

    allow_duplicate_outputs: bool = False

    def validate(self, recipes: list[Recipe]) -> RecipeValidationReport:
        report = RecipeValidationReport()
        self._validate_duplicate_ids(recipes, report)
        self._validate_duplicate_outputs(recipes, report)
        self._validate_recipe_shapes(recipes, report)
        self._validate_recipe_cycles(recipes, report)
        return report

    def _validate_duplicate_ids(
        self,
        recipes: list[Recipe],
        report: RecipeValidationReport,
    ) -> None:
        counts = Counter(recipe.id for recipe in recipes)
        for recipe_id, count in sorted(counts.items()):
            if count > 1:
                report.issues.append(
                    RecipeValidationIssue(
                        severity=RecipeValidationSeverity.ERROR,
                        code="duplicate_recipe_id",
                        recipe_id=recipe_id,
                        message=f"Recipe id {recipe_id!r} appears {count} times.",
                    )
                )

    def _validate_duplicate_outputs(
        self,
        recipes: list[Recipe],
        report: RecipeValidationReport,
    ) -> None:
        if self.allow_duplicate_outputs:
            return
        outputs: dict[tuple[str, int | str], list[str]] = {}
        for recipe in recipes:
            outputs.setdefault((recipe.output_kind, recipe.output_id), []).append(recipe.id)
        for output, recipe_ids in sorted(outputs.items(), key=lambda item: str(item[0])):
            if len(recipe_ids) > 1:
                report.issues.append(
                    RecipeValidationIssue(
                        severity=RecipeValidationSeverity.ERROR,
                        code="duplicate_recipe_output",
                        message=(
                            f"Output {output[0]}:{output[1]} is produced by multiple "
                            f"recipes: {', '.join(sorted(recipe_ids))}."
                        ),
                    )
                )

    def _validate_recipe_shapes(
        self,
        recipes: list[Recipe],
        report: RecipeValidationReport,
    ) -> None:
        for recipe in recipes:
            if not recipe.id.strip():
                report.issues.append(
                    RecipeValidationIssue(
                        severity=RecipeValidationSeverity.ERROR,
                        code="missing_recipe_id",
                        message="Recipe id cannot be blank.",
                    )
                )
            if not recipe.name.strip():
                report.issues.append(
                    RecipeValidationIssue(
                        severity=RecipeValidationSeverity.ERROR,
                        code="missing_recipe_name",
                        recipe_id=recipe.id,
                        message=f"Recipe {recipe.id!r} must have a display name.",
                    )
                )
            if recipe.output_quantity <= 0:
                report.issues.append(
                    RecipeValidationIssue(
                        severity=RecipeValidationSeverity.ERROR,
                        code="invalid_output_quantity",
                        recipe_id=recipe.id,
                        message=f"Recipe {recipe.id!r} must output at least one item.",
                    )
                )
            if not recipe.requirements:
                report.issues.append(
                    RecipeValidationIssue(
                        severity=RecipeValidationSeverity.WARNING,
                        code="empty_requirements",
                        recipe_id=recipe.id,
                        message=f"Recipe {recipe.id!r} has no requirements.",
                    )
                )

            for index, requirement in enumerate(recipe.requirements):
                if requirement.quantity <= 0:
                    report.issues.append(
                        RecipeValidationIssue(
                            severity=RecipeValidationSeverity.ERROR,
                            code="invalid_requirement_quantity",
                            recipe_id=recipe.id,
                            requirement_index=index,
                            message=(
                                f"Recipe {recipe.id!r} requirement {index} must require "
                                "at least one unit."
                            ),
                        )
                    )
                if requirement.kind in {"item", "currency"} and not isinstance(
                    requirement.id,
                    int,
                ):
                    report.issues.append(
                        RecipeValidationIssue(
                            severity=RecipeValidationSeverity.ERROR,
                            code="invalid_requirement_id_type",
                            recipe_id=recipe.id,
                            requirement_index=index,
                            message=(
                                f"Recipe {recipe.id!r} requirement {index} uses "
                                f"{requirement.kind} id {requirement.id!r}; expected int."
                            ),
                        )
                    )
                if requirement.kind in {"item", "currency"} and not requirement.name:
                    report.issues.append(
                        RecipeValidationIssue(
                            severity=RecipeValidationSeverity.WARNING,
                            code="missing_requirement_name",
                            recipe_id=recipe.id,
                            requirement_index=index,
                            message=(
                                f"Recipe {recipe.id!r} requirement {index} has no "
                                "display name."
                            ),
                        )
                    )
                if requirement.acquisition and not requirement.acquisition.label.strip():
                    report.issues.append(
                        RecipeValidationIssue(
                            severity=RecipeValidationSeverity.ERROR,
                            code="missing_acquisition_label",
                            recipe_id=recipe.id,
                            requirement_index=index,
                            message=(
                                f"Recipe {recipe.id!r} requirement {index} has an "
                                "acquisition hint without a label."
                            ),
                        )
                    )
                source_url = (
                    requirement.acquisition.source_url
                    if requirement.acquisition
                    else None
                )
                if source_url and not source_url.startswith(("https://", "http://")):
                    report.issues.append(
                        RecipeValidationIssue(
                            severity=RecipeValidationSeverity.ERROR,
                            code="invalid_acquisition_source_url",
                            recipe_id=recipe.id,
                            requirement_index=index,
                            message=(
                                f"Recipe {recipe.id!r} requirement {index} has an "
                                f"invalid acquisition source URL: {source_url!r}."
                            ),
                        )
                    )

    def _validate_recipe_cycles(
        self,
        recipes: list[Recipe],
        report: RecipeValidationReport,
    ) -> None:
        by_output = {
            (recipe.output_kind, recipe.output_id): recipe
            for recipe in recipes
        }
        by_id = {recipe.id: recipe for recipe in recipes}
        graph = {
            recipe.id: [
                child.id
                for requirement in recipe.requirements
                if (child := by_output.get((requirement.kind, requirement.id))) is not None
            ]
            for recipe in recipes
        }

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(recipe_id: str, path: list[str]) -> None:
            if recipe_id in visited:
                return
            if recipe_id in visiting:
                cycle_start = path.index(recipe_id)
                cycle = [*path[cycle_start:], recipe_id]
                report.issues.append(
                    RecipeValidationIssue(
                        severity=RecipeValidationSeverity.ERROR,
                        code="recipe_cycle",
                        recipe_id=recipe_id,
                        message=f"Recipe dependency cycle detected: {' -> '.join(cycle)}.",
                    )
                )
                return
            visiting.add(recipe_id)
            for child_id in graph.get(recipe_id, []):
                visit(child_id, [*path, child_id])
            visiting.remove(recipe_id)
            visited.add(recipe_id)

        for recipe_id in by_id:
            visit(recipe_id, [recipe_id])


def validate_recipes(recipes: list[Recipe]) -> RecipeValidationReport:
    return RecipeValidator().validate(recipes)
