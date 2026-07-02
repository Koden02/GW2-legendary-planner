from gw2_legendary_planner.planner.recipe_repository import get_default_recipe_repository
from gw2_legendary_planner.planner.recipe_validator import validate_recipes
from gw2_legendary_planner.planner.recipes import (
    AcquisitionHint,
    Recipe,
    RecipeMetadata,
    RecipeRequirement,
)


def test_packaged_recipe_data_validates_cleanly() -> None:
    recipes = list(get_default_recipe_repository().list_recipes())

    report = validate_recipes(recipes)

    assert report.is_valid
    assert report.error_count == 0


def test_recipe_validator_reports_duplicate_ids_and_outputs() -> None:
    recipes = [
        Recipe(
            id="duplicate",
            output_id=1,
            name="First",
            requirements=[RecipeRequirement(id=2, quantity=1, name="Material")],
        ),
        Recipe(
            id="duplicate",
            output_id=1,
            name="Second",
            requirements=[RecipeRequirement(id=3, quantity=1, name="Other Material")],
        ),
    ]

    report = validate_recipes(recipes)
    codes = {issue.code for issue in report.issues}

    assert not report.is_valid
    assert "duplicate_recipe_id" in codes
    assert "duplicate_recipe_output" in codes


def test_recipe_validator_reports_bad_requirements_and_cycles() -> None:
    recipes = [
        Recipe(
            id="cycle.a",
            output_id=1,
            name="Cycle A",
            requirements=[RecipeRequirement(id=2, quantity=1, name="Cycle B Output")],
        ),
        Recipe(
            id="cycle.b",
            output_id=2,
            name="Cycle B",
            requirements=[
                RecipeRequirement(id=1, quantity=1, name="Cycle A Output"),
                RecipeRequirement(id="bad-item-id", quantity=1),
            ],
        ),
    ]

    report = validate_recipes(recipes)
    codes = {issue.code for issue in report.issues}

    assert not report.is_valid
    assert "recipe_cycle" in codes
    assert "invalid_requirement_id_type" in codes
    assert "missing_requirement_name" in codes


def test_recipe_validator_reports_bad_acquisition_hints() -> None:
    recipes = [
        Recipe(
            id="bad.acquisition",
            output_id=1,
            name="Bad Acquisition",
            requirements=[
                RecipeRequirement(
                    id=2,
                    quantity=1,
                    name="Material",
                    acquisition=AcquisitionHint(
                        kind="vendor",
                        label="",
                        source_url="wiki.guildwars2.com/wiki/Material",
                    ),
                ),
            ],
        ),
    ]

    report = validate_recipes(recipes)
    codes = {issue.code for issue in report.issues}

    assert not report.is_valid
    assert "missing_acquisition_label" in codes
    assert "invalid_acquisition_source_url" in codes


def test_recipe_validator_reports_bad_recipe_metadata_source_urls() -> None:
    recipes = [
        Recipe(
            id="bad.source",
            output_id=1,
            name="Bad Source",
            metadata=RecipeMetadata(source_urls=["wiki.guildwars2.com/wiki/Bad_Source"]),
            requirements=[RecipeRequirement(id=2, quantity=1, name="Material")],
        ),
    ]

    report = validate_recipes(recipes)
    codes = {issue.code for issue in report.issues}

    assert not report.is_valid
    assert "invalid_recipe_source_url" in codes
