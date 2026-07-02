from datetime import date
from pathlib import Path

from gw2_legendary_planner.api.local import LocalExportLoader
from gw2_legendary_planner.inventory.aggregator import InventoryAggregator
from gw2_legendary_planner.planner.activities import build_activity_report
from gw2_legendary_planner.planner.collections import (
    CollectionDefinition,
    CollectionRequirement,
    evaluate_collections,
)
from gw2_legendary_planner.planner.recipe_evaluator import RecipeEvaluator
from gw2_legendary_planner.planner.recipe_repository import get_default_recipe_repository
from gw2_legendary_planner.planner.starter_kits import evaluate_starter_kit_sets
from gw2_legendary_planner.planner.wizards_vault import (
    WizardVaultReward,
    WizardVaultSeason,
    optimize_wizard_vault_rewards,
    validate_wizard_vault_seasons,
)
from gw2_legendary_planner.reports.exporters import (
    activity_rows,
    collection_rows,
    focus_rows,
    inventory_rows,
    recipe_cost_rows,
    rows_to_csv,
    starter_kit_rows,
    summary_rows,
    wizard_vault_optimization_rows,
    wizard_vault_rows,
    wizard_vault_validation_rows,
)
from gw2_legendary_planner.reports.summary import build_account_summary

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "exports"


def test_account_summary_uses_wallet_characters_crafting_and_inventory() -> None:
    snapshot = LocalExportLoader(FIXTURE_DIR).load()
    inventory = InventoryAggregator().aggregate(snapshot)
    summary = build_account_summary(snapshot, inventory)

    assert summary.account_name == "Example.1234"
    assert str(summary.gold) == "1234.5678"
    assert summary.gems == 400
    assert len(summary.characters) == 1
    assert len(summary.crafting_disciplines) == 2
    assert summary.legendary_armory_entries == 2
    assert summary.legendary_armory_total == 3
    assert summary.unique_item_count == 9
    assert summary.total_item_count == 395


def test_export_rows_are_flat() -> None:
    snapshot = LocalExportLoader(FIXTURE_DIR).load()
    inventory = InventoryAggregator().aggregate(snapshot)
    summary = build_account_summary(snapshot, inventory)

    assert inventory_rows(inventory)[0].keys() == {"item_id", "quantity", "locations"}
    assert summary_rows(summary)[0] == {"metric": "account_name", "value": "Example.1234"}
    assert focus_rows([]) == []


def test_csv_output_quotes_comma_fields() -> None:
    rows = [{"name": "Gift", "tags": "account_bound,gift"}]

    assert rows_to_csv(rows).splitlines()[1] == 'Gift,"account_bound,gift"'


def test_recipe_cost_rows_can_filter_missing_only() -> None:
    snapshot = LocalExportLoader(FIXTURE_DIR).load()
    inventory = InventoryAggregator().aggregate(snapshot)
    repository = get_default_recipe_repository()
    recipe = repository.get_recipe("legendary.bolt")
    assert recipe is not None

    evaluation = RecipeEvaluator(repository).evaluate(recipe, snapshot, inventory)
    rows = recipe_cost_rows(evaluation, missing_only=True)
    names = {row["name"] for row in rows}

    assert "Mystic Clover" in names
    assert "Zap" not in names
    assert all(row["missing_quantity"] > 0 for row in rows)
    icy_runestone = next(row for row in rows if row["name"] == "Icy Runestone")
    assert icy_runestone["acquisition"] == "Vendor purchase"
    assert icy_runestone["source_url"] == "https://wiki.guildwars2.com/wiki/Icy_Runestone"


def test_activity_rows_are_flat() -> None:
    snapshot = LocalExportLoader(FIXTURE_DIR).load()
    inventory = InventoryAggregator().aggregate(snapshot)

    rows = activity_rows(build_activity_report(snapshot, inventory))
    by_id = {row["id"]: row for row in rows}

    assert by_id["gift_of_battle"]["is_ready"] == "yes"
    assert by_id["gift_of_battle"]["locations"] == "bank x1 (slot=0)"
    assert by_id["gift_of_exploration"]["available_quantity"] == 2


def test_collection_rows_are_flat() -> None:
    snapshot = LocalExportLoader(FIXTURE_DIR).load()
    inventory = InventoryAggregator().aggregate(snapshot)
    progress_entries = evaluate_collections(
        snapshot,
        inventory,
        definitions=[
            CollectionDefinition(
                id="sample",
                name="Sample Collection",
                category="Legendary checklist",
                source_url="https://wiki.guildwars2.com/wiki/Legendary_weapon",
                last_verified=date(2026, 7, 1),
                tags=["legendary"],
                requirements=[
                    CollectionRequirement(
                        id="gift-of-battle",
                        name="Gift of Battle",
                        target_kind="item",
                        target_id=19678,
                        required_quantity=1,
                    )
                ],
            )
        ],
    )

    rows = collection_rows(progress_entries)

    assert rows[0]["collection_name"] == "Sample Collection"
    assert rows[0]["requirement_name"] == "Gift of Battle"
    assert rows[0]["is_complete"] == "yes"
    assert rows[0]["locations"] == "bank x1 (slot=0)"


def test_starter_kit_rows_are_flat() -> None:
    snapshot = LocalExportLoader(FIXTURE_DIR).load()
    inventory = InventoryAggregator().aggregate(snapshot)
    evaluations = evaluate_starter_kit_sets(
        snapshot,
        inventory,
        get_default_recipe_repository(),
        set_numbers={1},
    )

    rows = starter_kit_rows(evaluations)

    assert rows[0]["set_number"] == 1
    assert rows[0]["legendary_name"] == "Quip"
    assert rows[0]["readiness_gain_percent"] > 0
    assert "Gift of Quip" in rows[0]["covered_items"]


def test_wizard_vault_rows_are_flat() -> None:
    season = _wizard_vault_season()

    rows = wizard_vault_rows([season])

    assert rows[0]["season_id"] == "sample-season"
    assert rows[0]["reward_name"] == "Legendary Weapon Starter Kit"
    assert rows[0]["astral_acclaim_cost"] == 1000
    assert rows[0]["tags"] == "legendary,starter_kit"


def test_wizard_vault_validation_rows_are_flat() -> None:
    season = _wizard_vault_season(
        starts_on=date(2026, 9, 1),
        ends_on=date(2026, 8, 1),
    )
    report = validate_wizard_vault_seasons([season], current_date=date(2026, 7, 2))

    rows = wizard_vault_validation_rows(report)

    assert rows[0].keys() == {"severity", "code", "season_id", "reward_id", "message"}
    assert any(row["code"] == "invalid_season_dates" for row in rows)


def test_wizard_vault_optimization_rows_are_flat() -> None:
    snapshot = LocalExportLoader(FIXTURE_DIR).load()
    report = optimize_wizard_vault_rewards(snapshot, [_wizard_vault_season()])

    rows = wizard_vault_optimization_rows(report)

    assert rows[0]["reward_name"] == "Legendary Weapon Starter Kit"
    assert rows[0]["is_affordable"] == "yes"
    assert rows[0]["recommended_quantity"] == 1
    assert rows[0]["remaining_after_purchase"] == 200


def _wizard_vault_season(
    *,
    starts_on: date | None = date(2026, 6, 1),
    ends_on: date | None = date(2026, 9, 1),
) -> WizardVaultSeason:
    return WizardVaultSeason(
        id="sample-season",
        name="Sample Season",
        status="current",
        starts_on=starts_on,
        ends_on=ends_on,
        source_url="https://wiki.guildwars2.com/wiki/Wizard%27s_Vault",
        last_verified=date(2026, 7, 1),
        rewards=[
            WizardVaultReward(
                id="legendary-kit",
                name="Legendary Weapon Starter Kit",
                reward_kind="starter_kit",
                astral_acclaim_cost=1000,
                purchase_limit=1,
                item_id=103847,
                source_url="https://wiki.guildwars2.com/wiki/Legendary_Weapon_Starter_Kit",
                last_verified=date(2026, 7, 1),
                tags=["legendary", "starter_kit"],
            )
        ],
    )
