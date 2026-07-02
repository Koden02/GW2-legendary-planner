from datetime import UTC, datetime
from pathlib import Path
from threading import Thread

import httpx

from gw2_legendary_planner.api.local import LocalExportLoader
from gw2_legendary_planner.gui.dashboard import (
    DashboardSyncStatus,
    build_dashboard_payload,
    render_dashboard_html,
    write_dashboard_html,
)
from gw2_legendary_planner.gui.server import create_dashboard_server
from gw2_legendary_planner.gui.setup import render_api_key_setup_html
from gw2_legendary_planner.inventory.aggregator import InventoryAggregator
from gw2_legendary_planner.models.commerce import CommercePrice
from gw2_legendary_planner.planner.achievements import (
    build_achievement_report,
    load_achievement_goal_definitions_from_path,
)
from gw2_legendary_planner.planner.activities import build_activity_report
from gw2_legendary_planner.planner.collections import (
    evaluate_collections,
    load_collection_definitions_from_path,
)
from gw2_legendary_planner.planner.goal_comparison import build_goal_comparison_report
from gw2_legendary_planner.planner.legendary_focus import build_legendary_focus_report
from gw2_legendary_planner.planner.market import price_shopping_list
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
    assert "Current Goals" in html
    assert "Goal Comparison" in html
    assert "Shopping List" in html
    assert "Mystic Clover" in html
    assert "Sample Weekly Achievement Progress" in html
    assert "Gift of Battle" in html
    assert "Sync Status" in html
    assert "Dashboard built from a saved account snapshot." in html
    assert 'data-run-meta' in html
    assert "<b>Source</b>" in html
    assert "<b>Version</b>" in html
    assert 'role="tablist"' in html
    assert 'aria-controls="panel-recommendations"' in html
    assert 'aria-controls="panel-current-goals"' in html
    assert 'aria-labelledby="tab-recommendations"' in html
    assert 'data-panel-target="recommendations"' in html
    assert "No recommendations match this filter." in html
    assert "Ariadne Example" in html
    assert "character_inventory (Ariadne Example, bag 0, slot 0)" in html
    assert "legendary.bolt" in html
    assert "Shared Materials" in html


def test_dashboard_html_renders_live_sync_metadata() -> None:
    payload = _sample_dashboard_payload(
        sync_status=DashboardSyncStatus(
            mode="live",
            source_kind="gw2_api",
            cache_enabled=False,
            refresh_available=True,
            loaded_at=datetime(2026, 7, 2, 12, 0, tzinfo=UTC),
            last_refresh_at=datetime(2026, 7, 2, 12, 5, tzinfo=UTC),
            message="Ready for live refresh.",
        )
    )

    html = render_dashboard_html(payload)

    assert 'data-sync-bar' in html
    assert 'data-sync-message' in html
    assert 'data-sync-last-refresh' in html
    assert "Ready for live refresh." in html
    assert "2026-07-02 12:05 UTC" in html
    assert "cache off" in html
    assert "Refresh" in html


def test_dashboard_html_uses_polished_empty_states() -> None:
    payload = _sample_dashboard_payload()
    payload.shopping_list = None
    payload.focus_items = []

    html = render_dashboard_html(payload)

    assert "No crafting target is loaded for this snapshot." in html
    assert "No tracked legendary materials are present in this snapshot." in html
    assert 'role="status"' in html
    assert "Add --shopping-list-recipe" not in html


def test_dashboard_html_can_include_shopping_list_prices() -> None:
    payload = _sample_dashboard_payload(include_prices=True)

    html = render_dashboard_html(payload)

    assert payload.shopping_list_prices is not None
    assert "Market" in html
    assert "priced entries" in html
    assert "0g 81s 25c estimated buy cost" in html
    assert "priced" in html


def test_write_dashboard_html_creates_parent_directories(tmp_path: Path) -> None:
    payload = _sample_dashboard_payload()
    output = tmp_path / "nested" / "dashboard.html"

    write_dashboard_html(output, payload)

    assert output.exists()
    assert "GW2 Legendary Planner" in output.read_text(encoding="utf-8")


def test_api_key_setup_page_explains_memory_only_key() -> None:
    html = render_api_key_setup_html()

    assert "Guild Wars 2 API key" in html
    assert "Load Account" in html
    assert "kept in memory for this session" in html
    assert "Local setup" in html
    assert "data-api-key-form" in html
    assert "data-api-key-input" in html


def test_dashboard_server_default_port_uses_free_port() -> None:
    server = create_dashboard_server("<!doctype html><html>ok</html>")
    try:
        host, port = server.server_address
    finally:
        server.server_close()

    assert host == "127.0.0.1"
    assert port > 0


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


def test_dashboard_server_reports_status_and_static_refresh_unavailable() -> None:
    payload = _sample_dashboard_payload()
    server = create_dashboard_server(payload, port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        status = httpx.get(f"http://{host}:{port}/api/status", timeout=5)
        refresh = httpx.post(f"http://{host}:{port}/api/refresh", timeout=5)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert status.status_code == 200
    assert status.json()["mode"] == "static"
    assert status.json()["refresh_available"] is False
    assert refresh.status_code == 405


def test_dashboard_server_refreshes_from_provider() -> None:
    calls = 0

    def refresh_provider():
        nonlocal calls
        calls += 1
        return _sample_dashboard_payload(
            sync_status=DashboardSyncStatus(
                mode="live",
                source_kind="local_exports",
                refresh_available=True,
                message=f"Refresh {calls}",
            )
        )

    payload = _sample_dashboard_payload(
        sync_status=DashboardSyncStatus(
            mode="live",
            source_kind="local_exports",
            refresh_available=True,
            message="Initial",
        )
    )
    server = create_dashboard_server(payload, port=0, refresh_provider=refresh_provider)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        refresh = httpx.post(f"http://{host}:{port}/api/refresh", timeout=5)
        page = httpx.get(f"http://{host}:{port}/", timeout=5)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert refresh.status_code == 200
    assert refresh.json()["message"] == "Refresh 1"
    assert "Refresh 1" in page.text


def test_dashboard_server_refresh_error_updates_status_and_page() -> None:
    def refresh_provider():
        raise RuntimeError("fixture refresh failure")

    payload = _sample_dashboard_payload(
        sync_status=DashboardSyncStatus(
            mode="live",
            source_kind="local_exports",
            refresh_available=True,
            message="Initial",
        )
    )
    server = create_dashboard_server(payload, port=0, refresh_provider=refresh_provider)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        refresh = httpx.post(f"http://{host}:{port}/api/refresh", timeout=5)
        status = httpx.get(f"http://{host}:{port}/api/status", timeout=5)
        page = httpx.get(f"http://{host}:{port}/", timeout=5)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert refresh.status_code == 500
    assert refresh.json()["state"] == "error"
    assert refresh.json()["error"] == "fixture refresh failure"
    assert status.json()["state"] == "error"
    assert status.json()["error"] == "fixture refresh failure"
    assert "Refresh failed. Fix the source issue and try again." in page.text
    assert "fixture refresh failure" in page.text


def test_dashboard_server_static_refresh_unavailable_remains_method_error() -> None:
    payload = _sample_dashboard_payload()
    server = create_dashboard_server(payload, port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        refresh = httpx.post(f"http://{host}:{port}/api/refresh", timeout=5)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert refresh.status_code == 405
    assert refresh.json()["state"] == "error"
    assert refresh.json()["error"] == "Dashboard refresh is not available for this server."


def test_dashboard_server_api_key_setup_loads_dashboard_from_provider() -> None:
    captured_api_keys: list[str] = []

    def setup_provider(api_key: str):
        captured_api_keys.append(api_key)
        return _sample_dashboard_payload(
            sync_status=DashboardSyncStatus(
                mode="live",
                source_kind="gw2_api",
                refresh_available=True,
                message="Loaded from setup.",
            )
        )

    server = create_dashboard_server(
        render_api_key_setup_html(),
        port=0,
        api_key_setup_provider=setup_provider,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        setup = httpx.post(
            f"http://{host}:{port}/api/setup/api-key",
            json={"api_key": " fixture-key "},
            timeout=5,
        )
        status = httpx.get(f"http://{host}:{port}/api/status", timeout=5)
        page = httpx.get(f"http://{host}:{port}/", timeout=5)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert setup.status_code == 200
    assert setup.json()["message"] == "Loaded from setup."
    assert captured_api_keys == ["fixture-key"]
    assert status.json()["state"] == "ready"
    assert status.json()["source_kind"] == "gw2_api"
    assert "Example.1234" in page.text
    assert "Loaded from setup." in page.text


def test_dashboard_server_api_key_setup_validates_json_payload() -> None:
    server = create_dashboard_server(
        render_api_key_setup_html(),
        port=0,
        api_key_setup_provider=lambda api_key: _sample_dashboard_payload(),
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        missing = httpx.post(
            f"http://{host}:{port}/api/setup/api-key",
            json={"api_key": "  "},
            timeout=5,
        )
        malformed = httpx.post(
            f"http://{host}:{port}/api/setup/api-key",
            content="{bad json",
            timeout=5,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert missing.status_code == 400
    assert missing.json()["error"] == "API key is required."
    assert malformed.status_code == 400
    assert malformed.json()["error"] == "Request body must be valid JSON."


def _sample_dashboard_payload(
    sync_status: DashboardSyncStatus | None = None,
    *,
    include_prices: bool = False,
):
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
    repository = get_default_recipe_repository()
    bolt = repository.get_recipe("legendary.bolt")
    twilight = repository.get_recipe("legendary.twilight")
    assert bolt is not None
    assert twilight is not None
    evaluator = RecipeEvaluator(repository)
    goal_evaluations = [
        evaluator.evaluate(recipe, snapshot, inventory)
        for recipe in [bolt, twilight]
    ]
    goal_comparison_report = build_goal_comparison_report(
        goal_evaluations,
        selected_goal_ids=["legendary.bolt"],
    )
    shopping_list = build_shopping_list(
        [evaluator.evaluate(bolt, snapshot, inventory)]
    )
    shopping_list_prices = (
        price_shopping_list(
            shopping_list,
            {
                19675: CommercePrice(
                    id=19675,
                    buys={"quantity": 20, "unit_price": 80},
                    sells={"quantity": 12, "unit_price": 125},
                )
            },
        )
        if include_prices
        else None
    )
    return build_dashboard_payload(
        summary,
        focus_items=focus_items,
        activities=activities,
        progression_report=progression,
        goal_comparison_report=goal_comparison_report,
        shopping_list=shopping_list,
        shopping_list_prices=shopping_list_prices,
        source_label="fixtures",
        sync_status=sync_status,
        generated_at=datetime(2026, 7, 2, 12, 0, tzinfo=UTC),
    )
