from typing import Protocol

from gw2_legendary_planner.planner.recipes import (
    AcquisitionHint,
    DependencyNode,
    Goal,
    Recipe,
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
