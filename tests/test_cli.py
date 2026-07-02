import json
from pathlib import Path
from shutil import copytree

from typer.testing import CliRunner

from gw2_legendary_planner.cli import app

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "exports"
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


def test_cli_doctor_success() -> None:
    result = runner.invoke(app, ["doctor", "--input", str(FIXTURE_DIR)])

    assert result.exit_code == 0
    assert "GW2 Legendary Planner Doctor" in result.output
    assert "Python version" in result.output
    assert "All required local exports are valid" in result.output


def test_cli_analyze_fails_without_input_or_api_key() -> None:
    result = runner.invoke(app, ["analyze"])

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


def test_cli_doctor_can_require_api_key() -> None:
    result = runner.invoke(app, ["doctor", "--require-api-key"], env={"GW2PLANNER_API_KEY": ""})

    assert result.exit_code == 1
    assert "No API key was provided" in result.output


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
