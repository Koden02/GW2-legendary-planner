import json
from pathlib import Path
from shutil import copytree

from typer.testing import CliRunner

from gw2_legendary_planner.cli import app
from gw2_legendary_planner.config.profiles import ProfileStore

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "exports"
ACHIEVEMENT_FIXTURE = (
    Path(__file__).parent / "fixtures" / "achievements" / "sample_achievements.json"
)
COLLECTION_FIXTURE = Path(__file__).parent / "fixtures" / "collections" / "sample_collections.json"
RECURRING_FIXTURE = Path(__file__).parent / "fixtures" / "recurring" / "sample_tasks.json"
WIZARD_VAULT_FIXTURE = Path(__file__).parent / "fixtures" / "wizards_vault" / "sample_season.json"
runner = CliRunner()


def test_cli_analyze_success() -> None:
    result = runner.invoke(app, ["analyze", "--input", str(FIXTURE_DIR)])

    assert result.exit_code == 0
    assert "Account Summary" in result.output
    assert "Mystic Clover" in result.output


def test_cli_export_inventory_success() -> None:
    result = runner.invoke(app, ["export", "inventory", "--input", str(FIXTURE_DIR)])

    assert result.exit_code == 0
    assert "19976" in result.output
    assert "material_storage" in result.output


def test_cli_export_summary_success() -> None:
    result = runner.invoke(app, ["export", "summary", "--input", str(FIXTURE_DIR)])

    assert result.exit_code == 0
    assert "Example.1234" in result.output
    assert "unique_item_count" in result.output


def test_cli_export_focus_success() -> None:
    result = runner.invoke(
        app,
        ["export", "focus", "--input", str(FIXTURE_DIR), "--format", "csv", "--present-only"],
    )

    assert result.exit_code == 0
    assert "Mystic Clover" in result.output
    assert "Provisioner Token" in result.output


def test_cli_export_activities_success() -> None:
    result = runner.invoke(
        app,
        ["export", "activities", "--input", str(FIXTURE_DIR), "--format", "csv"],
    )

    assert result.exit_code == 0
    assert "Gift of Battle" in result.output
    assert "Gift of Exploration" in result.output
    assert "reward_track" in result.output


def test_cli_export_achievements_json_success() -> None:
    result = runner.invoke(
        app,
        [
            "export",
            "achievements",
            "--input",
            str(FIXTURE_DIR),
            "--data",
            str(ACHIEVEMENT_FIXTURE),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload[0]["id"] == "sample-complete-achievement"
    assert payload[1]["readiness_percent"] == 60.0


def test_cli_export_collections_json_success() -> None:
    result = runner.invoke(
        app,
        [
            "export",
            "collections",
            "--input",
            str(FIXTURE_DIR),
            "--data",
            str(COLLECTION_FIXTURE),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload[0]["id"] == "sample-legendary-readiness"
    assert payload[0]["completed_requirements"] == 3
    assert payload[0]["unsupported_requirements"] == 1


def test_cli_export_recurring_json_success() -> None:
    result = runner.invoke(
        app,
        [
            "export",
            "recurring",
            "--input",
            str(FIXTURE_DIR),
            "--data",
            str(RECURRING_FIXTURE),
            "--period",
            "weekly",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert {entry["period"] for entry in payload} == {"weekly"}
    assert {entry["id"] for entry in payload} == {
        "sample-weekly-achievement-progress",
        "sample-weekly-manual",
    }


def test_cli_export_progression_json_success() -> None:
    result = runner.invoke(
        app,
        [
            "export",
            "progression",
            "--input",
            str(FIXTURE_DIR),
            "--achievements-data",
            str(ACHIEVEMENT_FIXTURE),
            "--collections-data",
            str(COLLECTION_FIXTURE),
            "--recurring-data",
            str(RECURRING_FIXTURE),
            "--wizard-vault-data",
            str(WIZARD_VAULT_FIXTURE),
            "--starter-kit-set",
            "1",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["score"]["overall_score_percent"] > 0
    assert payload["recommendations"]
    assert any(
        component["id"] == "recurring_task_progress"
        for component in payload["score"]["components"]
    )


def test_cli_export_shopping_list_json_success() -> None:
    result = runner.invoke(
        app,
        [
            "export",
            "shopping-list",
            "legendary.bolt",
            "legendary.twilight",
            "--input",
            str(FIXTURE_DIR),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    entries = {entry["name"]: entry for entry in payload["entries"]}
    assert payload["goal_count"] == 2
    assert entries["Mystic Clover"]["missing_quantity"] == 142
    assert {goal["recipe_id"] for goal in payload["goals"]} == {
        "legendary.bolt",
        "legendary.twilight",
    }


def test_cli_export_starter_kits_success() -> None:
    result = runner.invoke(
        app,
        [
            "export",
            "starter-kits",
            "--input",
            str(FIXTURE_DIR),
            "--format",
            "csv",
            "--set",
            "1",
        ],
    )

    assert result.exit_code == 0
    assert "Legendary Weapon Starter Key-Set 1" in result.output
    assert "Quip" in result.output
    assert "Gift of Quip" in result.output


def test_cli_export_wizard_vault_success() -> None:
    result = runner.invoke(app, ["export", "wizard-vault", "--format", "json"])

    assert result.exit_code == 0
    assert json.loads(result.output) == []


def test_cli_export_wizard_vault_external_data_csv_success() -> None:
    result = runner.invoke(
        app,
        [
            "export",
            "wizard-vault",
            "--data",
            str(WIZARD_VAULT_FIXTURE),
            "--format",
            "csv",
        ],
    )

    assert result.exit_code == 0
    assert "Sample Wizard's Vault Season" in result.output
    assert "Legendary Weapon Starter Kit" in result.output
    assert "historical" in result.output
    assert "1000" in result.output


def test_cli_export_wizard_vault_optimization_json_success() -> None:
    result = runner.invoke(
        app,
        [
            "export",
            "wizard-vault-optimization",
            "--input",
            str(FIXTURE_DIR),
            "--data",
            str(WIZARD_VAULT_FIXTURE),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)

    assert payload["astral_acclaim_balance"] == 1200
    assert payload["remaining_astral_acclaim"] == 200
    assert payload["recommendations"][0]["reward_name"] == "Legendary Weapon Starter Kit"
    assert payload["recommendations"][0]["recommended_quantity"] == 1


def test_cli_gui_build_success(tmp_path: Path) -> None:
    output = tmp_path / "dashboard.html"
    result = runner.invoke(
        app,
        [
            "gui",
            "build",
            "--input",
            str(FIXTURE_DIR),
            "--achievements-data",
            str(ACHIEVEMENT_FIXTURE),
            "--collections-data",
            str(COLLECTION_FIXTURE),
            "--recurring-data",
            str(RECURRING_FIXTURE),
            "--shopping-list-recipe",
            "legendary.bolt",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0
    html = output.read_text(encoding="utf-8")
    assert "Dashboard written" in result.output
    assert "Example.1234" in html
    assert "Recommendation Engine" in html
    assert "Sync Status" in html
    assert "Standalone dashboard built from the loaded account snapshot." in html
    assert '<button class="sync-refresh"' not in html
    assert "Shopping List" in html
    assert "Mystic Clover" in html
    assert "Sample Weekly Achievement Progress" in html


def test_cli_gui_build_can_include_shopping_list_prices(tmp_path: Path, monkeypatch) -> None:
    from gw2_legendary_planner.planner.market import (
        ShoppingListPriceEntry,
        ShoppingListPriceReport,
    )

    def fake_price_report(report, *, use_cache: bool = True):
        assert report.entries
        assert use_cache is True
        return ShoppingListPriceReport(
            goals=report.goals,
            entries=[
                ShoppingListPriceEntry(
                    kind="item",
                    id=19675,
                    name="Mystic Clover",
                    missing_quantity=65,
                    price_status="priced",
                    buy_order_unit_price=80,
                    sell_listing_unit_price=125,
                    estimated_buy_cost=8_125,
                    estimated_sell_value=5_200,
                )
            ],
            priced_entry_count=1,
            total_estimated_buy_cost=8_125,
            total_estimated_sell_value=5_200,
        )

    monkeypatch.setattr(
        "gw2_legendary_planner.cli._price_shopping_list_report",
        fake_price_report,
    )
    monkeypatch.setattr(
        "gw2_legendary_planner.cli._price_goal_shopping_list_reports",
        lambda reports_by_recipe, *, use_cache=True: {
            recipe_id: fake_price_report(report, use_cache=use_cache)
            for recipe_id, report in reports_by_recipe.items()
        },
    )

    output = tmp_path / "dashboard.html"
    result = runner.invoke(
        app,
        [
            "gui",
            "build",
            "--input",
            str(FIXTURE_DIR),
            "--shopping-list-recipe",
            "legendary.bolt",
            "--include-shopping-list-prices",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0
    html = output.read_text(encoding="utf-8")
    assert "Market" in html
    assert "1 priced entries" in html
    assert "0g 81s 25c estimated buy cost" in html
    assert "Mystic Clover" in html


def test_cli_gui_build_uses_default_profile_input_dir(tmp_path: Path) -> None:
    profile_file = tmp_path / "profiles.json"
    env = {"GW2PLANNER_PROFILE_FILE": str(profile_file)}
    output = tmp_path / "dashboard.html"
    runner.invoke(
        app,
        ["profiles", "add", "main", "--input", str(FIXTURE_DIR), "--default"],
        env=env,
    )

    result = runner.invoke(app, ["gui", "build", "--output", str(output)], env=env)

    assert result.exit_code == 0
    html = output.read_text(encoding="utf-8")
    assert "Example.1234" in html
    assert str(FIXTURE_DIR) in html


def test_cli_gui_build_fails_without_input_or_api_key(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["gui", "build", "--output", str(tmp_path / "dashboard.html")],
        env={
            "GW2PLANNER_API_KEY": "",
            "GW2_API_KEY": "",
            "GW2PLANNER_PROFILE_FILE": str(tmp_path / "profiles.json"),
        },
    )

    assert result.exit_code != 0
    assert "Provide --api-key" in result.output


def test_cli_gui_serve_without_source_starts_setup_page(tmp_path: Path, monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeDashboardServer:
        server_address = ("127.0.0.1", 8765)

        def serve_forever(self) -> None:
            captured["served"] = True
            raise KeyboardInterrupt

        def server_close(self) -> None:
            captured["closed"] = True

    def fake_create_dashboard_server(dashboard, **kwargs):
        captured["dashboard"] = dashboard
        captured["kwargs"] = kwargs
        return FakeDashboardServer()

    monkeypatch.setattr(
        "gw2_legendary_planner.cli.create_dashboard_server",
        fake_create_dashboard_server,
    )

    result = runner.invoke(
        app,
        ["gui", "serve", "--port", "0"],
        env={
            "GW2PLANNER_API_KEY": "",
            "GW2_API_KEY": "",
            "GW2PLANNER_PROFILE_FILE": str(tmp_path / "profiles.json"),
        },
    )

    assert result.exit_code == 0
    assert "No account source configured" in result.output
    assert "Serving dashboard" in result.output
    assert captured["served"] is True
    assert captured["closed"] is True
    assert "Guild Wars 2 API key" in str(captured["dashboard"])
    kwargs = captured["kwargs"]
    assert isinstance(kwargs, dict)
    assert kwargs["api_key_setup_provider"] is not None
    assert kwargs["refresh_provider"] is not None


def test_cli_gui_serve_can_remember_setup_api_key(tmp_path: Path, monkeypatch) -> None:
    profile_file = tmp_path / "profiles.json"

    class FakeDashboardServer:
        server_address = ("127.0.0.1", 8765)

        def __init__(self, setup_provider) -> None:
            self.setup_provider = setup_provider

        def serve_forever(self) -> None:
            assert self.setup_provider is not None
            self.setup_provider(" remembered-key ", True)
            raise KeyboardInterrupt

        def server_close(self) -> None:
            return

    def fake_create_dashboard_server(dashboard, **kwargs):
        return FakeDashboardServer(kwargs["api_key_setup_provider"])

    monkeypatch.setattr(
        "gw2_legendary_planner.cli.create_dashboard_server",
        fake_create_dashboard_server,
    )
    monkeypatch.setattr(
        "gw2_legendary_planner.cli._load_dashboard_payload",
        lambda **kwargs: object(),
    )

    result = runner.invoke(
        app,
        ["gui", "serve", "--port", "0"],
        env={
            "GW2PLANNER_API_KEY": "",
            "GW2_API_KEY": "",
            "GW2PLANNER_PROFILE_FILE": str(profile_file),
        },
    )

    profile = ProfileStore(profile_file).get_profile()

    assert result.exit_code == 0
    assert profile is not None
    assert profile.name == "local-dashboard"
    assert profile.api_key == "remembered-key"


def test_cli_doctor_success() -> None:
    result = runner.invoke(app, ["doctor", "--input", str(FIXTURE_DIR)])

    assert result.exit_code == 0
    assert "GW2 Legendary Planner Doctor" in result.output
    assert "Python version" in result.output
    assert "All required local exports are valid" in result.output


def test_cli_analyze_fails_without_input_or_api_key(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["analyze"],
        env={
            "GW2PLANNER_API_KEY": "",
            "GW2_API_KEY": "",
            "GW2PLANNER_PROFILE_FILE": str(tmp_path / "profiles.json"),
        },
    )

    assert result.exit_code != 0
    assert "Provide --api-key" in result.output


def test_cli_analyze_reports_missing_exports(tmp_path: Path) -> None:
    export_dir = tmp_path / "exports"
    export_dir.mkdir()

    result = runner.invoke(app, ["analyze", "--input", str(export_dir)])

    assert result.exit_code == 1
    assert "Local export validation failed" in result.output
    assert "Missing account export" in result.output


def test_cli_doctor_reports_malformed_json(tmp_path: Path) -> None:
    export_dir = tmp_path / "exports"
    copytree(FIXTURE_DIR, export_dir)
    (export_dir / "account_wallet.json").write_text("[", encoding="utf-8")

    result = runner.invoke(app, ["doctor", "--input", str(export_dir)])

    assert result.exit_code == 1
    assert "Malformed JSON" in result.output


def test_cli_doctor_can_require_api_key(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["doctor", "--require-api-key"],
        env={
            "GW2PLANNER_API_KEY": "",
            "GW2_API_KEY": "",
            "GW2PLANNER_PROFILE_FILE": str(tmp_path / "profiles.json"),
        },
    )

    assert result.exit_code == 1
    assert "No API key was provided" in result.output


def test_cli_profiles_add_list_show_and_default(tmp_path: Path) -> None:
    profile_file = tmp_path / "profiles.json"
    env = {"GW2PLANNER_PROFILE_FILE": str(profile_file)}

    add_result = runner.invoke(
        app,
        [
            "profiles",
            "add",
            "main",
            "--input",
            str(FIXTURE_DIR),
            "--api-key-env",
            "GW2_MAIN_API_KEY",
            "--default",
        ],
        env=env,
    )
    list_result = runner.invoke(app, ["profiles", "list"], env=env)
    show_result = runner.invoke(app, ["profiles", "show", "main"], env=env)

    assert add_result.exit_code == 0
    assert "Profile saved" in add_result.output
    assert list_result.exit_code == 0
    assert "main" in list_result.output
    assert "env:GW2_MAIN_API_KEY" in list_result.output
    assert show_result.exit_code == 0
    assert str(FIXTURE_DIR) in show_result.output


def test_cli_profiles_show_displays_stored_api_key(tmp_path: Path) -> None:
    profile_file = tmp_path / "profiles.json"
    env = {"GW2PLANNER_PROFILE_FILE": str(profile_file)}

    add_result = runner.invoke(
        app,
        ["profiles", "add", "live", "--api-key", "visible-key", "--default"],
        env=env,
    )
    list_result = runner.invoke(app, ["profiles", "list"], env=env)
    show_result = runner.invoke(app, ["profiles", "show", "live"], env=env)

    assert add_result.exit_code == 0
    assert list_result.exit_code == 0
    assert "visible-key" in list_result.output
    assert show_result.exit_code == 0
    assert "api_key: visible-key" in show_result.output


def test_cli_analyze_uses_default_profile_input_dir(tmp_path: Path) -> None:
    profile_file = tmp_path / "profiles.json"
    env = {"GW2PLANNER_PROFILE_FILE": str(profile_file)}
    runner.invoke(
        app,
        ["profiles", "add", "main", "--input", str(FIXTURE_DIR), "--default"],
        env=env,
    )

    result = runner.invoke(app, ["analyze"], env=env)

    assert result.exit_code == 0
    assert "Account Summary" in result.output
    assert "Example.1234" in result.output


def test_cli_analyze_can_use_named_profile(tmp_path: Path) -> None:
    profile_file = tmp_path / "profiles.json"
    env = {"GW2PLANNER_PROFILE_FILE": str(profile_file)}
    runner.invoke(app, ["profiles", "add", "main"], env=env)
    runner.invoke(app, ["profiles", "add", "alt", "--input", str(FIXTURE_DIR)], env=env)

    result = runner.invoke(app, ["--profile", "alt", "analyze"], env=env)

    assert result.exit_code == 0
    assert "Example.1234" in result.output


def test_cli_recipes_list_success() -> None:
    result = runner.invoke(app, ["recipes", "list"])

    assert result.exit_code == 0
    assert "Legendary Recipes" in result.output
    assert "legendary.twilight" in result.output
    assert "legendary.bolt" in result.output


def test_cli_recipes_list_tag_filter_success() -> None:
    result = runner.invoke(
        app,
        ["recipes", "list", "--format", "csv", "--tag", "generation_1", "--tag", "sword"],
    )

    assert result.exit_code == 0
    assert "legendary.bolt" in result.output
    assert "legendary.twilight" not in result.output
    assert "weapon_gift.bolt" not in result.output


def test_cli_recipes_show_success() -> None:
    result = runner.invoke(app, ["recipes", "show", "legendary.twilight"])

    assert result.exit_code == 0
    assert "Recipe: Twilight" in result.output
    assert "Gift of Fortune" in result.output


def test_cli_recipes_show_api_verified_shared_recipe_success() -> None:
    result = runner.invoke(app, ["recipes", "show", "gift.metal"])

    assert result.exit_code == 0
    assert "Recipe: Gift of Metal" in result.output
    assert "Orichalcum Ingot" in result.output


def test_cli_recipes_show_wiki_verified_weapon_gift_success() -> None:
    result = runner.invoke(app, ["recipes", "show", "weapon_gift.bolt"])

    assert result.exit_code == 0
    assert "Recipe: Gift of Bolt" in result.output
    assert "Superior Sigil of Air" in result.output


def test_cli_recipes_evaluate_success() -> None:
    result = runner.invoke(
        app,
        ["recipes", "evaluate", "legendary.twilight", "--input", str(FIXTURE_DIR)],
    )

    assert result.exit_code == 0
    assert "Recipe Readiness: Twilight" in result.output
    assert "Effective Crafting Cost" in result.output
    assert "Mystic Clover" in result.output


def test_cli_recipes_evaluate_csv_graph_success() -> None:
    result = runner.invoke(
        app,
        [
            "recipes",
            "evaluate",
            "legendary.twilight",
            "--input",
            str(FIXTURE_DIR),
            "--format",
            "csv",
            "--graph",
        ],
    )

    assert result.exit_code == 0
    assert "parent,child,child_kind,quantity,status" in result.output
    assert "Gift of Fortune" in result.output


def test_cli_recipes_evaluate_missing_only_csv_success() -> None:
    result = runner.invoke(
        app,
        [
            "recipes",
            "evaluate",
            "legendary.bolt",
            "--input",
            str(FIXTURE_DIR),
            "--format",
            "csv",
            "--missing-only",
        ],
    )

    assert result.exit_code == 0
    assert "Mystic Clover" in result.output
    assert "Icy Runestone" in result.output
    assert "Vendor purchase" in result.output
    assert "Gift of Battle" not in result.output
    assert "Zap" not in result.output


def test_cli_recipes_evaluate_missing_only_json_success() -> None:
    result = runner.invoke(
        app,
        [
            "recipes",
            "evaluate",
            "legendary.bolt",
            "--input",
            str(FIXTURE_DIR),
            "--format",
            "json",
            "--missing-only",
        ],
    )

    payload = json.loads(result.output)
    names = {cost["name"] for cost in payload["costs"]}

    assert result.exit_code == 0
    assert "Mystic Clover" in names
    assert "Zap" not in names
    assert all(cost["missing_quantity"] > 0 for cost in payload["costs"])
    assert (
        next(cost for cost in payload["costs"] if cost["name"] == "Icy Runestone")[
            "acquisition"
        ]["label"]
        == "Vendor purchase"
    )


def test_cli_recipes_shopping_list_success() -> None:
    result = runner.invoke(
        app,
        ["recipes", "shopping-list", "legendary.bolt", "--input", str(FIXTURE_DIR)],
    )

    assert result.exit_code == 0
    assert "Shopping List" in result.output
    assert "Missing Effective Costs" in result.output
    assert "65" in result.output


def test_cli_recipes_shopping_list_csv_success() -> None:
    result = runner.invoke(
        app,
        [
            "recipes",
            "shopping-list",
            "legendary.bolt",
            "--input",
            str(FIXTURE_DIR),
            "--format",
            "csv",
        ],
    )

    assert result.exit_code == 0
    assert "missing_quantity" in result.output
    assert "Mystic Clover" in result.output
    assert "legendary.bolt" in result.output


def test_cli_recipes_shopping_list_can_include_price_report(monkeypatch) -> None:
    from gw2_legendary_planner.planner.market import (
        ShoppingListPriceEntry,
        ShoppingListPriceReport,
    )

    def fake_price_report(report, *, use_cache: bool = True):
        assert report.entries
        assert use_cache is True
        return ShoppingListPriceReport(
            goals=report.goals,
            entries=[
                ShoppingListPriceEntry(
                    kind="item",
                    id=19976,
                    name="Mystic Coin",
                    missing_quantity=2,
                    price_status="priced",
                    buy_order_unit_price=110,
                    sell_listing_unit_price=125,
                    estimated_buy_cost=250,
                    estimated_sell_value=220,
                )
            ],
            priced_entry_count=1,
            total_estimated_buy_cost=250,
            total_estimated_sell_value=220,
        )

    monkeypatch.setattr(
        "gw2_legendary_planner.cli._price_shopping_list_report",
        fake_price_report,
    )

    result = runner.invoke(
        app,
        [
            "recipes",
            "shopping-list",
            "legendary.bolt",
            "--input",
            str(FIXTURE_DIR),
            "--include-prices",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["priced_entry_count"] == 1
    assert payload["total_estimated_buy_cost"] == 250
    assert payload["entries"][0]["price_status"] == "priced"


def test_cli_recipes_validate_success() -> None:
    result = runner.invoke(app, ["recipes", "validate"])

    assert result.exit_code == 0
    assert "Recipe data validation passed" in result.output


def test_cli_recipes_validate_json_success() -> None:
    result = runner.invoke(app, ["recipes", "validate", "--format", "json"])

    assert result.exit_code == 0
    assert '"issues": []' in result.output


def test_cli_recipes_unknown_id_fails() -> None:
    result = runner.invoke(app, ["recipes", "show", "missing.recipe"])

    assert result.exit_code == 1
    assert "Unknown recipe id" in result.output


def test_cli_activities_report_success() -> None:
    result = runner.invoke(app, ["activities", "report", "--input", str(FIXTURE_DIR)])

    assert result.exit_code == 0
    assert "Legendary Activity Planners" in result.output
    assert "Gift of Battle" in result.output
    assert "Gift of Exploration" in result.output


def test_cli_activities_report_tag_filter_json_success() -> None:
    result = runner.invoke(
        app,
        [
            "activities",
            "report",
            "--input",
            str(FIXTURE_DIR),
            "--format",
            "json",
            "--tag",
            "wvw",
        ],
    )

    payload = json.loads(result.output)

    assert result.exit_code == 0
    assert [entry["id"] for entry in payload] == ["gift_of_battle"]
    assert payload[0]["is_ready"] is True


def test_cli_activities_collections_success() -> None:
    result = runner.invoke(
        app,
        [
            "activities",
            "collections",
            "--input",
            str(FIXTURE_DIR),
            "--data",
            str(COLLECTION_FIXTURE),
        ],
    )

    assert result.exit_code == 0
    assert "Collection Progress" in result.output
    assert "Unsupported" in result.output


def test_cli_activities_collections_reports_missing_data_file(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "activities",
            "collections",
            "--input",
            str(FIXTURE_DIR),
            "--data",
            str(tmp_path / "missing.json"),
        ],
    )

    assert result.exit_code == 1
    assert "Collection data failed to load" in result.output
    assert "does not exist" in result.output


def test_cli_progress_achievements_success() -> None:
    result = runner.invoke(
        app,
        [
            "progress",
            "achievements",
            "--input",
            str(FIXTURE_DIR),
            "--data",
            str(ACHIEVEMENT_FIXTURE),
        ],
    )

    assert result.exit_code == 0
    assert "Achievement Progress" in result.output
    assert "60.00%" in result.output


def test_cli_progress_dailies_success() -> None:
    result = runner.invoke(
        app,
        [
            "progress",
            "dailies",
            "--input",
            str(FIXTURE_DIR),
            "--data",
            str(RECURRING_FIXTURE),
        ],
    )

    assert result.exit_code == 0
    assert "Recurring Tasks" in result.output
    assert "100.00%" in result.output


def test_cli_progress_weeklies_json_success() -> None:
    result = runner.invoke(
        app,
        [
            "progress",
            "weeklies",
            "--input",
            str(FIXTURE_DIR),
            "--data",
            str(RECURRING_FIXTURE),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert {entry["period"] for entry in payload} == {"weekly"}
    assert any(not entry["is_trackable"] for entry in payload)


def test_cli_progress_score_success() -> None:
    result = runner.invoke(
        app,
        [
            "progress",
            "score",
            "--input",
            str(FIXTURE_DIR),
            "--achievements-data",
            str(ACHIEVEMENT_FIXTURE),
            "--collections-data",
            str(COLLECTION_FIXTURE),
            "--recurring-data",
            str(RECURRING_FIXTURE),
        ],
    )

    assert result.exit_code == 0
    assert "Overall" in result.output
    assert "Score Components" in result.output


def test_cli_progress_recommend_json_success() -> None:
    result = runner.invoke(
        app,
        [
            "progress",
            "recommend",
            "--input",
            str(FIXTURE_DIR),
            "--achievements-data",
            str(ACHIEVEMENT_FIXTURE),
            "--collections-data",
            str(COLLECTION_FIXTURE),
            "--wizard-vault-data",
            str(WIZARD_VAULT_FIXTURE),
            "--recurring-data",
            str(RECURRING_FIXTURE),
            "--starter-kit-set",
            "1",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    kinds = {recommendation["kind"] for recommendation in payload["recommendations"]}
    assert "achievement" in kinds
    assert "weekly" in kinds
    assert "wizard_vault" in kinds
    assert "starter_kit" in kinds


def test_cli_activities_gift_of_battle_success() -> None:
    result = runner.invoke(
        app,
        ["activities", "gift-of-battle", "--input", str(FIXTURE_DIR), "--format", "csv"],
    )

    assert result.exit_code == 0
    assert "Gift of Battle" in result.output
    assert "Gift of Exploration" not in result.output


def test_cli_activities_starter_kits_success() -> None:
    result = runner.invoke(
        app,
        ["activities", "starter-kits", "--input", str(FIXTURE_DIR), "--set", "1"],
    )

    assert result.exit_code == 0
    assert "Legendary Weapon Starter Key-Set 1" in result.output
    assert "Quip" in result.output
    assert "Bolt" in result.output


def test_cli_activities_starter_kits_json_success() -> None:
    result = runner.invoke(
        app,
        [
            "activities",
            "starter-kits",
            "--input",
            str(FIXTURE_DIR),
            "--set",
            "1",
            "--format",
            "json",
        ],
    )

    payload = json.loads(result.output)

    assert result.exit_code == 0
    assert payload[0]["set_number"] == 1
    assert payload[0]["options"][0]["legendary_name"] == "Quip"
    assert payload[0]["options"][0]["readiness_gain_percent"] > 0


def test_cli_activities_wizard_vault_success() -> None:
    result = runner.invoke(app, ["activities", "wizard-vault"])

    assert result.exit_code == 0
    assert "No Wizard's Vault seasonal reward data is packaged" in result.output


def test_cli_activities_wizard_vault_external_data_success() -> None:
    result = runner.invoke(
        app,
        ["activities", "wizard-vault", "--data", str(WIZARD_VAULT_FIXTURE)],
    )

    assert result.exit_code == 0
    assert "Wizard's Vault Seasonal Rewards" in result.output
    assert "historical" in result.output
    assert "1,000" in result.output


def test_cli_activities_wizard_vault_optimize_success() -> None:
    result = runner.invoke(
        app,
        [
            "activities",
            "wizard-vault-optimize",
            "--input",
            str(FIXTURE_DIR),
            "--data",
            str(WIZARD_VAULT_FIXTURE),
        ],
    )

    assert result.exit_code == 0
    assert "Wizard's Vault Optimization" in result.output
    assert "Astral Acclaim" in result.output
    assert "1,200" in result.output


def test_cli_activities_wizard_vault_validate_success() -> None:
    result = runner.invoke(app, ["activities", "wizard-vault-validate"])

    assert result.exit_code == 0
    assert "Wizard's Vault data validation passed" in result.output


def test_cli_activities_wizard_vault_validate_external_data_success() -> None:
    result = runner.invoke(
        app,
        [
            "activities",
            "wizard-vault-validate",
            "--data",
            str(WIZARD_VAULT_FIXTURE),
        ],
    )

    assert result.exit_code == 0
    assert "Wizard's Vault data validation passed" in result.output


def test_cli_activities_wizard_vault_reports_missing_data_file(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["activities", "wizard-vault", "--data", str(tmp_path / "missing.json")],
    )

    assert result.exit_code == 1
    assert "Wizard's Vault data failed to load" in result.output
    assert "does not exist" in result.output
