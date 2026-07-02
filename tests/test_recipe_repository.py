from gw2_legendary_planner.planner.recipe_repository import get_default_recipe_repository


def test_default_recipe_repository_loads_seed_recipes() -> None:
    repository = get_default_recipe_repository()

    recipes = repository.list_recipes()
    twilight = repository.get_recipe("legendary.twilight")
    gift_mastery = repository.find_recipes_for_output("item", 19674)

    assert len(recipes) >= 65
    assert twilight is not None
    assert twilight.name == "Twilight"
    assert gift_mastery[0].id == "gift.mastery"


def test_default_recipe_repository_covers_generation_one_top_level_weapons() -> None:
    repository = get_default_recipe_repository()
    legendary_recipes = [
        recipe
        for recipe in repository.list_recipes()
        if "legendary" in recipe.tags and "generation_1" in recipe.tags
    ]
    names = {recipe.name for recipe in legendary_recipes}

    assert len(legendary_recipes) == 20
    assert {
        "The Bifrost",
        "Bolt",
        "Frostfang",
        "Kamohoali'i Kotaki",
        "Sunrise",
        "Twilight",
    }.issubset(names)
    assert all(len(recipe.requirements) == 4 for recipe in legendary_recipes)
    assert all(
        {requirement.name for requirement in recipe.requirements}
        >= {"Gift of Mastery", "Gift of Fortune"}
        for recipe in legendary_recipes
    )


def test_default_recipe_repository_loads_api_verified_shared_recipes() -> None:
    repository = get_default_recipe_repository()
    api_verified = [
        recipe for recipe in repository.list_recipes() if "api_verified" in recipe.tags
    ]
    gift_metal = repository.find_recipes_for_output("item", 19621)

    assert len(api_verified) == 21
    assert gift_metal[0].id == "gift.metal"
    assert {requirement.name for requirement in gift_metal[0].requirements} == {
        "Orichalcum Ingot",
        "Mithril Ingot",
        "Darksteel Ingot",
        "Platinum Ingot",
    }


def test_default_recipe_repository_loads_wiki_verified_weapon_gifts() -> None:
    repository = get_default_recipe_repository()
    weapon_gifts = [
        recipe for recipe in repository.list_recipes() if "weapon_gift" in recipe.tags
    ]
    gift_bolt = repository.find_recipes_for_output("item", 19655)
    gift_twilight = repository.find_recipes_for_output("item", 19648)

    assert len(weapon_gifts) == 20
    assert all("wiki_verified" in recipe.tags for recipe in weapon_gifts)
    assert gift_bolt[0].id == "weapon_gift.bolt"
    assert gift_twilight[0].id == "weapon_gift.twilight"
    assert {requirement.name for requirement in gift_bolt[0].requirements} == {
        "Gift of Metal",
        "Gift of Lightning",
        "Icy Runestone",
        "Superior Sigil of Air",
    }


def test_default_recipe_repository_loads_acquisition_hints() -> None:
    repository = get_default_recipe_repository()
    gift_mastery = repository.get_recipe("gift.mastery")
    gift_bolt = repository.get_recipe("weapon_gift.bolt")
    assert gift_mastery is not None
    assert gift_bolt is not None

    mastery_hints = {
        requirement.name: requirement.acquisition
        for requirement in gift_mastery.requirements
    }
    bolt_hints = {
        requirement.name: requirement.acquisition
        for requirement in gift_bolt.requirements
    }

    assert mastery_hints["Gift of Battle"] is not None
    assert mastery_hints["Gift of Battle"].kind == "reward_track"
    assert mastery_hints["Gift of Exploration"] is not None
    assert mastery_hints["Gift of Exploration"].kind == "world_completion"
    assert bolt_hints["Icy Runestone"] is not None
    assert bolt_hints["Icy Runestone"].label == "Vendor purchase"
