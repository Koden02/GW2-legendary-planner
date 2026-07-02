from datetime import UTC, datetime
from pathlib import Path
from threading import Thread

import httpx

from gw2_legendary_planner.api.local import LocalExportLoader
from gw2_legendary_planner.gui.dashboard import (
    build_dashboard_payload,
    render_dashboard_html,
    write_dashboard_html,
)
from gw2_legendary_planner.gui.server import create_dashboard_server
from gw2_legendary_planner.inventory.aggregator import InventoryAggregator
from gw2_legendary_planner.planner.achievements import (
    build_achievement_report,
    load_achievement_goal_definitions_from_path,
)
from gw2_legendary_planner.planner.activities import build_activity_report
from gw2_legendary_planner.planner.collections import (
    evaluate_collections,
    load_collection_definitions_from_path,
)
from gw2_legendary_planner.planner.legendary_focus import build_legendary_focus_report
from gw2_legendary_planner.planner.progression import build_account_progression_report
from gw2_legendary_planner.planner.recipe_evaluator import RecipeEvaluator
from gw2_legendary_planner.planner.recipe_repository import get_default_recipe_repository
from gw2_legendary_planner.planner.recurring import (
    build_recurring_task_report,
    load_recurring_task_definitions_from_path,
)
from gw2_legendary_planner.planner.shopping_list import build_shopping_list
from gw2_legendary_planner.reports.summary import build_account_summary

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "exports"
ACHIEVEMENT_FIXTURE = (
    Path(__file__).parent / "fixtures" / "achievements" / "sample_achievements.json"
)
COLLECTION_FIXTURE = Path(__file__).parent / "fixtures" / "collections" / "sample_collections.json"
RECURRING_FIXTURE = Path(__file__).parent / "fixtures" / "recurring" / "sample_tasks.json"


def test_dashboard_payload_and_html_include_account_progression() -> None:
    payload = _sample_dashboard_payload()

    html = render_dashboard_html(payload)

    assert payload.account_name == "Example.1234"
    assert payload.score_percent is not None
    assert "Example.1234" in html
    assert "Recommendation Engine" in html
    assert "Shopping List" in html
    assert "Mystic Clover" in html
    assert "Sample Weekly Achievement Progress" in html
    assert "Gift of Battle" in html
    assert 'data-panel-target="recommendations"' in html


def test_write_dashboard_html_creates_parent_directories(tmp_path: Path) -> None:
    payload = _sample_dashboard_payload()
    output = tmp_path / "nested" / "dashboard.html"

    write_dashboard_html(output, payload)

    assert output.exists()
    assert "GW2 Legendary Planner" in output.read_text(encoding="utf-8")


def test_dashboard_server_serves_index_html() -> None:
    server = create_dashboard_server("<!doctype html><html>ok</html>", port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        response = httpx.get(f"http://{host}:{port}/", timeout=5)
        missing = httpx.get(f"http://{host}:{port}/missing", timeout=5)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert "ok" in response.text
    assert missing.status_code == 404


def _sample_dashboard_payload():
    snapshot = LocalExportLoader(FIXTURE_DIR).load()
    inventory = InventoryAggregator().aggregate(snapshot)
    summary = build_account_summary(snapshot, inventory)
    focus_items = build_legendary_focus_report(snapshot, inventory, include_zero=False)
    activities = build_activity_report(snapshot, inventory)
    achievements = build_achievement_report(
        snapshot,
        definitions=load_achievement_goal_definitions_from_path(ACHIEVEMENT_FIXTURE),
    )
    collections = evaluate_collections(
        snapshot,
        inventory,
        definitions=load_collection_definitions_from_path(COLLECTION_FIXTURE),
    )
    recurring = build_recurring_task_report(
        snapshot,
        inventory,
        definitions=load_recurring_task_definitions_from_path(RECURRING_FIXTURE),
    )
    progression = build_account_progression_report(
        snapshot,
        inventory,
        get_default_recipe_repository(),
        achievement_statuses=achievements,
        activity_statuses=activities,
        collection_progress=collections,
        recurring_tasks=recurring,
    )
    bolt = get_default_recipe_repository().get_recipe("legendary.bolt")
    assert bolt is not None
    shopping_list = build_shopping_list(
        [RecipeEvaluator(get_default_recipe_repository()).evaluate(bolt, snapshot, inventory)]
    )
    return build_dashboard_payload(
        summary,
        focus_items=focus_items,
        activities=activities,
        progression_report=progression,
        shopping_list=shopping_list,
        source_label="fixtures",
        generated_at=datetime(2026, 7, 2, 12, 0, tzinfo=UTC),
    )
