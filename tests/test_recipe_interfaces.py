from typing import Protocol

from gw2_legendary_planner.planner.recipes import (
    AcquisitionHint,
    DependencyNode,
    Goal,
    Recipe,
    RecipeMetadata,
    RecipeProvider,
    RecipeRepository,
    RecipeRequirement,
)


def test_recipe_interface_models_are_data_only_shapes() -> None:
    acquisition = AcquisitionHint(
        kind="mystic_forge",
        label="Mystic Forge or mode rewards",
    )
    requirement = RecipeRequirement(
        id=19675,
        quantity=77,
        name="Mystic Clover",
        acquisition=acquisition,
    )
    recipe = Recipe(
        id="legendary.example",
        output_id=123,
        name="Example Legendary",
        requirements=[requirement],
    )
    goal = Goal(id="goal.example", kind="item", target_id=123, name="Craft Example")
    node = DependencyNode(
        id="node.example",
        label="Example Legendary",
        requirement=requirement,
        recipe_id=recipe.id,
    )

    assert recipe.requirements == [requirement]
    assert recipe.requirements[0].acquisition == acquisition
    assert goal.target_id == 123
    assert node.child_ids == []
    assert issubclass(RecipeProvider, Protocol)
    assert issubclass(RecipeRepository, Protocol)


def test_recipe_metadata_can_be_explicit_or_inferred_from_tags() -> None:
    explicit = Recipe(
        id="legendary.aurene_example",
        output_id=456,
        name="Aurene Example",
        tags=["legendary", "generation_3", "weapon", "sword"],
        metadata=RecipeMetadata(family="aurene", expansion="end_of_dragons"),
    )
    inferred = Recipe(
        id="legendary.gen1_example",
        output_id=789,
        name="Generation One Example",
        tags=["legendary", "generation_1", "weapon", "greatsword"],
    )

    assert explicit.metadata.generation == "generation_3"
    assert explicit.metadata.family == "aurene"
    assert explicit.metadata.weapon_type == "sword"
    assert inferred.metadata.generation == "generation_1"
    assert inferred.metadata.family == "generation_1"
    assert inferred.metadata.weapon_type == "greatsword"
