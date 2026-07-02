from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from gw2_legendary_planner import __version__
from gw2_legendary_planner.planner.activities import ActivityGoalStatus
from gw2_legendary_planner.planner.goal_comparison import (
    GoalComparison,
    GoalComparisonReport,
    GoalRequirementComparison,
)
from gw2_legendary_planner.planner.legendary_focus import FocusEntry
from gw2_legendary_planner.planner.market import (
    ShoppingListPriceEntry,
    ShoppingListPriceReport,
)
from gw2_legendary_planner.planner.progression import (
    AccountProgressionReport,
    AccountRecommendation,
    ProgressionScoreComponent,
)
from gw2_legendary_planner.planner.shopping_list import ShoppingListReport
from gw2_legendary_planner.reports.summary import AccountSummary

DashboardSourceKind = Literal["gw2_api", "local_exports"]
DashboardSyncMode = Literal["static", "live"]
DashboardSyncState = Literal["ready", "refreshing", "error"]
DashboardTone = Literal["neutral", "good", "warning", "critical", "info"]


class DashboardMetric(BaseModel):
    """One dashboard summary metric."""

    id: str
    label: str
    value: str
    detail: str | None = None
    tone: DashboardTone = "neutral"


class DashboardSyncStatus(BaseModel):
    """Visible synchronization state for the dashboard."""

    mode: DashboardSyncMode = "static"
    state: DashboardSyncState = "ready"
    source_kind: DashboardSourceKind = "local_exports"
    cache_enabled: bool = True
    refresh_available: bool = False
    loaded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_refresh_at: datetime | None = None
    message: str = "Dashboard built from a saved account snapshot."
    error: str | None = None


class DashboardPayload(BaseModel):
    """Serializable data contract for the browser-based dashboard."""

    app_name: str = "GW2 Legendary Planner"
    app_version: str = __version__
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source_label: str = "account data"
    sync_status: DashboardSyncStatus = Field(default_factory=DashboardSyncStatus)
    account_name: str = "Unknown account"
    metrics: list[DashboardMetric] = Field(default_factory=list)
    score_percent: float | None = None
    score_components: list[ProgressionScoreComponent] = Field(default_factory=list)
    recommendations: list[AccountRecommendation] = Field(default_factory=list)
    goal_comparison_report: GoalComparisonReport | None = None
    shopping_list: ShoppingListReport | None = None
    shopping_list_prices: ShoppingListPriceReport | None = None
    focus_items: list[FocusEntry] = Field(default_factory=list)
    activities: list[ActivityGoalStatus] = Field(default_factory=list)


def build_dashboard_payload(
    summary: AccountSummary,
    *,
    focus_items: list[FocusEntry],
    activities: list[ActivityGoalStatus],
    progression_report: AccountProgressionReport | None = None,
    goal_comparison_report: GoalComparisonReport | None = None,
    shopping_list: ShoppingListReport | None = None,
    shopping_list_prices: ShoppingListPriceReport | None = None,
    source_label: str = "account data",
    sync_status: DashboardSyncStatus | None = None,
    generated_at: datetime | None = None,
) -> DashboardPayload:
    """Build a dashboard view model from reusable planner outputs."""

    visible_focus_items = sorted(
        [entry for entry in focus_items if entry.quantity > 0],
        key=lambda entry: (entry.category, entry.name),
    )
    resolved_generated_at = generated_at or datetime.now(UTC)
    return DashboardPayload(
        generated_at=resolved_generated_at,
        source_label=source_label,
        sync_status=sync_status
        or DashboardSyncStatus(loaded_at=resolved_generated_at),
        account_name=summary.account_name or "Unknown account",
        metrics=_summary_metrics(summary),
        score_percent=(
            progression_report.score.overall_score_percent if progression_report else None
        ),
        score_components=progression_report.score.components if progression_report else [],
        recommendations=progression_report.recommendations if progression_report else [],
        goal_comparison_report=goal_comparison_report,
        shopping_list=shopping_list,
        shopping_list_prices=shopping_list_prices,
        focus_items=visible_focus_items,
        activities=activities,
    )


def write_dashboard_html(path: Path, payload: DashboardPayload) -> None:
    """Write a standalone dashboard HTML file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_dashboard_html(payload), encoding="utf-8")


def render_dashboard_html(payload: DashboardPayload) -> str:
    """Render a standalone HTML dashboard."""

    score_style = _score_style(payload.score_percent)
    payload_json = payload.model_dump_json().replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(payload.app_name)} - {escape(payload.account_name)}</title>
  <style>
{_DASHBOARD_CSS}
  </style>
  <script type="application/json" id="dashboard-data">{payload_json}</script>
</head>
<body>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand">
        <div class="brand-mark" aria-hidden="true">GW2</div>
        <div>
          <p class="eyebrow">Desktop Dashboard</p>
          <h1>{escape(payload.account_name)}</h1>
        </div>
      </div>
      {_render_run_meta(payload)}
    </header>
    {_render_sync_status(payload.sync_status)}

    <nav class="tabs" aria-label="Dashboard views" role="tablist">
      <button
        id="tab-overview"
        class="tab is-active"
        type="button"
        role="tab"
        aria-selected="true"
        aria-controls="panel-overview"
        data-panel-target="overview"
      >
        Overview
      </button>
      <button
        id="tab-current-goals"
        class="tab"
        type="button"
        role="tab"
        aria-selected="false"
        aria-controls="panel-current-goals"
        data-panel-target="current-goals"
      >
        Current Goals
      </button>
      <button
        id="tab-recommendations"
        class="tab"
        type="button"
        role="tab"
        aria-selected="false"
        aria-controls="panel-recommendations"
        data-panel-target="recommendations"
      >
        Recommendations
      </button>
      <button
        id="tab-shopping-list"
        class="tab"
        type="button"
        role="tab"
        aria-selected="false"
        aria-controls="panel-shopping-list"
        data-panel-target="shopping-list"
      >
        Shopping List
      </button>
      <button
        id="tab-materials"
        class="tab"
        type="button"
        role="tab"
        aria-selected="false"
        aria-controls="panel-materials"
        data-panel-target="materials"
      >
        Materials
      </button>
      <button
        id="tab-activities"
        class="tab"
        type="button"
        role="tab"
        aria-selected="false"
        aria-controls="panel-activities"
        data-panel-target="activities"
      >
        Activities
      </button>
    </nav>

    <main>
      <section
        id="panel-overview"
        class="panel is-active"
        data-panel="overview"
        role="tabpanel"
        aria-labelledby="tab-overview"
      >
        <div class="overview-grid">
          <section class="score-band" aria-label="Account progression score">
            <div class="score-ring" style="{score_style}">
              <span>{escape(_format_optional_percent(payload.score_percent))}</span>
            </div>
            <div>
              <p class="eyebrow">Progression Score</p>
              <h2>{escape(_score_heading(payload.score_percent))}</h2>
              <p class="muted">{escape(_score_detail(payload))}</p>
            </div>
          </section>
          <section class="metric-grid" aria-label="Account summary">
            {_render_metrics(payload.metrics)}
          </section>
        </div>
        <section class="section-block">
          <div class="section-heading">
            <p class="eyebrow">Score Components</p>
            <h2>Account Signals</h2>
          </div>
          {_render_score_components(payload.score_components)}
        </section>
      </section>

      <section
        id="panel-current-goals"
        class="panel"
        data-panel="current-goals"
        role="tabpanel"
        aria-labelledby="tab-current-goals"
        hidden
      >
        <div class="section-heading row-heading">
          <div>
            <p class="eyebrow">Current Goals</p>
            <h2>Goal Comparison</h2>
          </div>
          <input
            id="goal-filter"
            type="search"
            placeholder="Filter goals"
            aria-label="Filter goals"
          >
          <select id="goal-generation-filter" aria-label="Filter goals by generation">
            <option value="">All generations</option>
          </select>
          <select id="goal-family-filter" aria-label="Filter goals by family">
            <option value="">All families</option>
          </select>
        </div>
        {_render_current_goals(payload.goal_comparison_report)}
      </section>

      <section
        id="panel-recommendations"
        class="panel"
        data-panel="recommendations"
        role="tabpanel"
        aria-labelledby="tab-recommendations"
        hidden
      >
        <div class="section-heading row-heading">
          <div>
            <p class="eyebrow">Recommendation Engine</p>
            <h2>Next Account Steps</h2>
          </div>
          <input
            id="recommendation-filter"
            type="search"
            placeholder="Filter recommendations"
            aria-label="Filter recommendations"
          >
        </div>
        {_render_recommendations(payload.recommendations)}
      </section>

      <section
        id="panel-shopping-list"
        class="panel"
        data-panel="shopping-list"
        role="tabpanel"
        aria-labelledby="tab-shopping-list"
        hidden
      >
        <div class="section-heading">
          <p class="eyebrow">Crafting Targets</p>
          <h2>Shopping List</h2>
        </div>
        {_render_shopping_list(payload.shopping_list, payload.shopping_list_prices)}
      </section>

      <section
        id="panel-materials"
        class="panel"
        data-panel="materials"
        role="tabpanel"
        aria-labelledby="tab-materials"
        hidden
      >
        <div class="section-heading">
          <p class="eyebrow">Legendary Focus</p>
          <h2>Important Materials</h2>
        </div>
        {_render_focus_items(payload.focus_items)}
      </section>

      <section
        id="panel-activities"
        class="panel"
        data-panel="activities"
        role="tabpanel"
        aria-labelledby="tab-activities"
        hidden
      >
        <div class="section-heading">
          <p class="eyebrow">Activity Planners</p>
          <h2>Tracked Account Work</h2>
        </div>
        {_render_activities(payload.activities)}
      </section>
    </main>
  </div>
  <script>
{_DASHBOARD_JS}
  </script>
</body>
</html>
"""


def _summary_metrics(summary: AccountSummary) -> list[DashboardMetric]:
    return [
        DashboardMetric(
            id="gold",
            label="Gold",
            value=f"{summary.gold:,.2f}",
            detail=f"{summary.copper:,} copper",
            tone="good",
        ),
        DashboardMetric(
            id="gems",
            label="Gems",
            value=f"{summary.gems:,}",
            detail="wallet",
            tone="info",
        ),
        DashboardMetric(
            id="characters",
            label="Characters",
            value=f"{len(summary.characters):,}",
            detail="loaded",
        ),
        DashboardMetric(
            id="crafting",
            label="Crafting",
            value=f"{len(summary.crafting_disciplines):,}",
            detail="disciplines",
        ),
        DashboardMetric(
            id="legendary_armory",
            label="Legendary Armory",
            value=f"{summary.legendary_armory_total:,}",
            detail=f"{summary.legendary_armory_entries:,} entries",
            tone="warning",
        ),
        DashboardMetric(
            id="items",
            label="Items",
            value=f"{summary.total_item_count:,}",
            detail=f"{summary.unique_item_count:,} unique",
        ),
    ]


def _render_run_meta(payload: DashboardPayload) -> str:
    return f"""
      <div class="run-meta" data-run-meta>
        <span class="meta-chip">
          <b>Source</b>
          <strong>{escape(payload.source_label)}</strong>
        </span>
        <span class="meta-chip">
          <b>Generated</b>
          <strong>{escape(_format_datetime(payload.generated_at))}</strong>
        </span>
        <span class="meta-chip">
          <b>Version</b>
          <strong>{escape(payload.app_version)}</strong>
        </span>
      </div>
    """


def _render_sync_status(status: DashboardSyncStatus) -> str:
    error_hidden = "" if status.error else " hidden"
    refresh_button = (
        """
        <button class="sync-refresh" type="button" data-refresh-dashboard>
          Refresh
        </button>
        """
        if status.refresh_available
        else ""
    )
    cache_text = "cache on" if status.cache_enabled else "cache off"
    last_refresh_text = (
        _format_datetime(status.last_refresh_at)
        if status.last_refresh_at
        else "Not yet"
    )
    return f"""
    <section
      class="sync-bar tone-{escape(status.state)}"
      aria-label="Dashboard sync status"
      aria-live="polite"
      data-sync-bar
    >
      <div>
        <p class="eyebrow">Sync Status</p>
        <strong data-sync-state>{escape(status.state.title())}</strong>
        <span id="sync-message" data-sync-message>{escape(status.message)}</span>
        <p class="sync-error" data-sync-error{error_hidden}>{escape(status.error or "")}</p>
      </div>
      <dl>
        <div>
          <dt>Mode</dt>
          <dd>{escape(status.mode)}</dd>
        </div>
        <div>
          <dt>Source</dt>
          <dd>{escape(status.source_kind.replace("_", " "))}</dd>
        </div>
        <div>
          <dt>Loaded</dt>
          <dd data-sync-loaded>{escape(_format_datetime(status.loaded_at))}</dd>
        </div>
        <div>
          <dt>Last Refresh</dt>
          <dd data-sync-last-refresh>{escape(last_refresh_text)}</dd>
        </div>
        <div>
          <dt>Cache</dt>
          <dd>{escape(cache_text)}</dd>
        </div>
      </dl>
      {refresh_button}
    </section>
    """


def _render_metrics(metrics: list[DashboardMetric]) -> str:
    if not metrics:
        return _empty_state("No account summary metrics are available.")
    return "\n".join(
        f"""
            <article class="metric-card tone-{escape(metric.tone)}">
              <span>{escape(metric.label)}</span>
              <strong>{escape(metric.value)}</strong>
              <small>{escape(metric.detail or "")}</small>
            </article>
        """
        for metric in metrics
    )


def _render_score_components(components: list[ProgressionScoreComponent]) -> str:
    if not components:
        return _empty_state("No score component data is available.")
    rows = []
    for component in components:
        width = max(min(component.score_percent, 100), 0)
        rows.append(
            f"""
            <article class="component-row">
              <div class="component-copy">
                <strong>{escape(component.name)}</strong>
                <span>{escape(component.detail)}</span>
              </div>
              <div class="component-meter" aria-label="{escape(component.name)}">
                <span style="width: {width:.2f}%"></span>
              </div>
              <b>{component.score_percent:.2f}%</b>
            </article>
            """
        )
    return "\n".join(rows)


def _render_recommendations(recommendations: list[AccountRecommendation]) -> str:
    if not recommendations:
        return _empty_state("No recommendations are available for this snapshot.")
    rows = []
    for recommendation in recommendations:
        search_text = " ".join(
            [
                recommendation.kind,
                recommendation.priority,
                recommendation.title,
                recommendation.action,
                recommendation.reason,
            ]
        ).lower()
        rows.append(
            f"""
            <tr data-recommendation-row data-search="{escape(search_text, quote=True)}">
              <td><span class="pill tone-{escape(recommendation.priority)}">
                {escape(recommendation.priority)}
              </span></td>
              <td class="numeric">{recommendation.priority_score:.2f}</td>
              <td>{escape(recommendation.kind.replace("_", " "))}</td>
              <td>
                <strong>{escape(recommendation.title)}</strong>
                <span>{escape(recommendation.reason)}</span>
              </td>
              <td>{escape(recommendation.action)}</td>
            </tr>
            """
        )
    return f"""
        <div class="table-shell">
          <table>
            <thead>
              <tr>
                <th>Priority</th>
                <th class="numeric">Score</th>
                <th>Type</th>
                <th>Recommendation</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {"".join(rows)}
            </tbody>
          </table>
        </div>
        <div class="empty-state filter-empty" data-recommendation-empty hidden>
          <strong>No recommendations match this filter.</strong>
        </div>
    """


def _render_current_goals(report: GoalComparisonReport | None) -> str:
    if report is None or not report.goals:
        return _empty_state("No legendary goal comparisons are available for this snapshot.")
    selected_ids = set(report.selected_goal_ids)
    picker_rows = []
    comparison_rows = []
    for goal in report.goals:
        is_selected = goal.recipe_id in selected_ids
        checked = " checked" if is_selected else ""
        search_text = " ".join(
            [
                goal.recipe_id,
                goal.recipe_name,
                goal.generation or "",
                goal.family or "",
                goal.expansion or "",
                goal.weapon_type or "",
                *goal.tags,
            ]
        ).lower()
        meta_text = _format_goal_metadata(goal)
        picker_rows.append(
            f"""
            <label class="goal-picker-row" data-goal-picker-row
              data-search="{escape(search_text, quote=True)}"
              data-generation="{escape(goal.generation or "", quote=True)}"
              data-family="{escape(goal.family or "", quote=True)}">
              <input
                type="checkbox"
                data-goal-toggle
                value="{escape(goal.recipe_id, quote=True)}"
                {checked}
              >
              <span>
                <strong>{escape(goal.recipe_name)}</strong>
                <small>{escape(goal.recipe_id)}</small>
                <em>{escape(meta_text)}</em>
              </span>
              <b>{goal.readiness_percent:.0f}%</b>
            </label>
            """
        )
        comparison_rows.append(
            f"""
            <tr data-goal-comparison-row data-goal-id="{escape(goal.recipe_id, quote=True)}">
              <td>
                <strong>{escape(goal.recipe_name)}</strong>
                <span>{escape(goal.recipe_id)}</span>
              </td>
              <td class="numeric">{goal.readiness_percent:.2f}%</td>
              <td class="numeric">{goal.account_bound_missing_entries:,}</td>
              <td class="numeric">{goal.manual_missing_entries:,}</td>
              <td class="numeric">{goal.tradeable_missing_entries:,}</td>
              <td class="numeric">{escape(_format_optional_copper(goal.estimated_buy_cost))}</td>
              <td>{escape(_format_goal_missing_requirements(goal.missing_requirements))}</td>
              <td>{escape(goal.recommended_action)}</td>
            </tr>
            """
        )
    return f"""
        <div class="current-goals-grid" data-current-goals>
          <section class="goal-picker" aria-label="Available legendary goals">
            <div class="goal-picker-list">
              {"".join(picker_rows)}
            </div>
          </section>
          <section class="goal-comparison" aria-label="Selected goal comparison">
            <div class="summary-strip current-goals-summary">
              <span><b data-selected-goal-count>0</b> selected</span>
              <span><b data-selected-readiness>-</b> average readiness</span>
              <span><b data-selected-bound>0</b> bound</span>
              <span><b data-selected-manual>0</b> manual</span>
              <span><b data-selected-tradeable>0</b> tradeable</span>
              <span><b data-selected-price>-</b> estimated buy</span>
            </div>
            <div class="table-shell">
              <table class="goal-comparison-table">
                <thead>
                  <tr>
                    <th>Goal</th>
                    <th class="numeric">Ready</th>
                    <th class="numeric">Bound</th>
                    <th class="numeric">Manual</th>
                    <th class="numeric">Tradeable</th>
                    <th class="numeric">Est. Buy</th>
                    <th>Missing Focus</th>
                    <th>Next Action</th>
                  </tr>
                </thead>
                <tbody>
                  {"".join(comparison_rows)}
                </tbody>
              </table>
            </div>
            <div class="empty-state current-goals-empty" data-current-goals-empty hidden>
              <strong>No current goals selected.</strong>
            </div>
            <section class="shared-requirements" aria-label="Shared missing materials">
              <div class="section-heading">
                <p class="eyebrow">Shared Materials</p>
                <h2>Overlap</h2>
              </div>
              <div class="table-shell">
                <table class="shared-requirements-table">
                  <thead>
                    <tr>
                      <th>Requirement</th>
                      <th class="numeric">Missing</th>
                      <th>Category</th>
                      <th>Goals</th>
                    </tr>
                  </thead>
                  <tbody data-shared-requirements-body></tbody>
                </table>
              </div>
            </section>
          </section>
        </div>
    """


def _render_shopping_list(
    report: ShoppingListReport | None,
    price_report: ShoppingListPriceReport | None,
) -> str:
    if report is None:
        return _empty_state("No crafting target is loaded for this snapshot.")
    if not report.entries:
        return _empty_state("Selected crafting targets are fully covered by this account.")
    price_by_key = _shopping_price_entries_by_key(price_report)
    has_prices = price_report is not None
    rows = []
    for entry in report.entries:
        price_entry = price_by_key.get((entry.kind, entry.id))
        rows.append(
            f"""
            <tr>
              <td>
                <strong>{escape(entry.name or str(entry.id))}</strong>
                <span>{escape(str(entry.id))}</span>
              </td>
              <td>{escape(entry.kind)}</td>
              <td class="numeric">{entry.required_quantity:,}</td>
              <td class="numeric">{entry.available_quantity:,}</td>
              <td class="numeric">{entry.missing_quantity:,}</td>
              <td>{escape(entry.acquisition.label if entry.acquisition else "-")}</td>
              {_render_shopping_price_cells(price_entry) if has_prices else ""}
              <td>{escape(_format_contributions(entry.contributions))}</td>
            </tr>
            """
        )
    return f"""
        <div class="summary-strip">
          <span>{report.goal_count:,} goals</span>
          <span>{report.missing_entry_count:,} missing entries</span>
          <span>{report.total_missing_quantity:,} total missing quantity</span>
          {_render_shopping_price_summary(price_report)}
        </div>
        <div class="table-shell">
          <table class="shopping-table">
            <thead>
              <tr>
                <th>Requirement</th>
                <th>Kind</th>
                <th class="numeric">Required</th>
                <th class="numeric">Available</th>
                <th class="numeric">Missing</th>
                <th>Acquisition</th>
                {_render_shopping_price_headers() if has_prices else ""}
                <th>Recipes</th>
              </tr>
            </thead>
            <tbody>
              {"".join(rows)}
            </tbody>
          </table>
        </div>
    """


def _shopping_price_entries_by_key(
    price_report: ShoppingListPriceReport | None,
) -> dict[tuple[str, int | str], ShoppingListPriceEntry]:
    if price_report is None:
        return {}
    return {(entry.kind, entry.id): entry for entry in price_report.entries}


def _render_shopping_price_summary(price_report: ShoppingListPriceReport | None) -> str:
    if price_report is None:
        return ""
    buy_cost = escape(_format_copper(price_report.total_estimated_buy_cost))
    return f"""
          <span>{price_report.priced_entry_count:,} priced entries</span>
          <span>{price_report.unpriced_entry_count:,} unpriced entries</span>
          <span>{buy_cost} estimated buy cost</span>
    """


def _render_shopping_price_headers() -> str:
    return """
                <th>Market</th>
                <th class="numeric">Buy Now</th>
                <th class="numeric">Est. Buy</th>
    """


def _render_shopping_price_cells(price_entry: ShoppingListPriceEntry | None) -> str:
    if price_entry is None:
        return """
              <td><span class="pill tone-low">not priced</span></td>
              <td class="numeric">-</td>
              <td class="numeric">-</td>
        """

    tone = "good" if price_entry.is_priced else "warning"
    note = f"<span>{escape(price_entry.note)}</span>" if price_entry.note else ""
    sell_listing = escape(_format_optional_copper(price_entry.sell_listing_unit_price))
    estimated_buy = escape(_format_optional_copper(price_entry.estimated_buy_cost))
    return f"""
              <td>
                <span class="pill tone-{tone}">
                  {escape(price_entry.price_status.replace("_", " "))}
                </span>
                {note}
              </td>
              <td class="numeric">{sell_listing}</td>
              <td class="numeric">{estimated_buy}</td>
    """


def _render_focus_items(items: list[FocusEntry]) -> str:
    if not items:
        return _empty_state("No tracked legendary materials are present in this snapshot.")
    rows = []
    for item in items:
        rows.append(
            f"""
            <tr>
              <td>
                <strong>{escape(item.name)}</strong>
                <span>{escape(item.kind)}</span>
              </td>
              <td>{escape(item.category)}</td>
              <td class="numeric">{item.quantity:,}</td>
              <td>{escape(_format_locations(item.locations))}</td>
            </tr>
            """
        )
    return f"""
        <div class="table-shell">
          <table>
            <thead>
              <tr>
                <th>Item</th>
                <th>Category</th>
                <th class="numeric">Qty</th>
                <th>Locations</th>
              </tr>
            </thead>
            <tbody>
              {"".join(rows)}
            </tbody>
          </table>
        </div>
    """


def _render_activities(activities: list[ActivityGoalStatus]) -> str:
    if not activities:
        return _empty_state("No tracked activity planner data is available.")
    rows = []
    for activity in activities:
        ready_class = "good" if activity.is_ready else "warning"
        rows.append(
            f"""
            <tr>
              <td>
                <strong>{escape(activity.name)}</strong>
                <span>{escape(activity.category)}</span>
              </td>
              <td><span class="pill tone-{ready_class}">
                {activity.readiness_percent:.2f}%
              </span></td>
              <td class="numeric">{activity.available_quantity:,}</td>
              <td class="numeric">{activity.missing_quantity:,}</td>
              <td>{escape(activity.action)}</td>
            </tr>
            """
        )
    return f"""
        <div class="table-shell">
          <table>
            <thead>
              <tr>
                <th>Goal</th>
                <th>Ready</th>
                <th class="numeric">Have</th>
                <th class="numeric">Missing</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {"".join(rows)}
            </tbody>
          </table>
        </div>
    """


def _format_locations(locations) -> str:
    if not locations:
        return "-"
    return "; ".join(_format_location(location) for location in locations)


def _format_location(location) -> str:
    label = location.source
    details = []
    if getattr(location, "character", None):
        details.append(location.character)
    if getattr(location, "bag_index", None) is not None:
        details.append(f"bag {location.bag_index}")
    if getattr(location, "slot", None) is not None:
        details.append(f"slot {location.slot}")
    if details:
        label = f"{label} ({', '.join(str(detail) for detail in details)})"
    return f"{label} x{location.quantity:,}"


def _format_goal_missing_requirements(
    requirements: list[GoalRequirementComparison],
) -> str:
    if not requirements:
        return "No missing requirements."
    shown = requirements[:3]
    text = "; ".join(
        f"{requirement.name or requirement.id} x{requirement.missing_quantity:,}"
        for requirement in shown
    )
    remaining_count = len(requirements) - len(shown)
    if remaining_count > 0:
        text = f"{text}; {remaining_count:,} more"
    return text


def _format_goal_metadata(goal: GoalComparison) -> str:
    parts = [
        _display_metadata_value(goal.generation),
        _display_metadata_value(goal.family),
        _display_metadata_value(goal.expansion),
        _display_metadata_value(goal.weapon_type),
    ]
    return " / ".join(part for part in parts if part) or "Unclassified"


def _display_metadata_value(value: str | None) -> str:
    if not value:
        return ""
    return value.replace("_", " ").title()


def _format_contributions(contributions) -> str:
    if not contributions:
        return "-"
    return "; ".join(
        f"{contribution.recipe_name} x{contribution.required_quantity:,}"
        for contribution in contributions
    )


def _format_optional_copper(value: int | None) -> str:
    return _format_copper(value) if value is not None else "-"


def _format_copper(value: int) -> str:
    gold, remainder = divmod(value, 10_000)
    silver, copper = divmod(remainder, 100)
    return f"{gold:,}g {silver:02d}s {copper:02d}c"


def _format_datetime(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")


def _format_optional_percent(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.0f}%"


def _score_detail(payload: DashboardPayload) -> str:
    if payload.score_percent is None:
        return "Load progression inputs to calculate a score."
    return f"{len(payload.recommendations)} ranked recommendations are available."


def _score_heading(score_percent: float | None) -> str:
    if score_percent is None:
        return "No Score"
    if score_percent >= 75:
        return "Strong Position"
    if score_percent >= 50:
        return "Good Momentum"
    return "Early Progress"


def _score_style(score_percent: float | None) -> str:
    score = max(min(score_percent or 0, 100), 0)
    return f"--score: {score:.2f};"


def _empty_state(message: str) -> str:
    return f'<div class="empty-state" role="status"><strong>{escape(message)}</strong></div>'


_DASHBOARD_CSS = """
:root {
  color-scheme: light;
  --bg: #f5f7f4;
  --surface: #ffffff;
  --surface-strong: #eef3ef;
  --text: #1d2520;
  --muted: #66736b;
  --line: #d8e0da;
  --accent: #1b7f6b;
  --accent-strong: #105f51;
  --gold: #b48a32;
  --danger: #b94b4b;
  --info: #3c6f94;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-width: 320px;
  background: var(--bg);
  color: var(--text);
  font-family: Inter, "Segoe UI", Arial, sans-serif;
  line-height: 1.45;
}

.app-shell {
  width: min(1360px, calc(100% - 32px));
  margin: 0 auto;
  padding: 24px 0 40px;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 0 20px;
  border-bottom: 1px solid var(--line);
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  border: 1px solid #0f4f44;
  background: #123b35;
  color: #f3df9f;
  font-weight: 800;
  border-radius: 8px;
  box-shadow: inset 0 -8px 0 rgb(255 255 255 / 7%);
}

.eyebrow {
  margin: 0 0 4px;
  color: var(--accent-strong);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: uppercase;
}

h1,
h2 {
  margin: 0;
  line-height: 1.1;
}

h1 {
  font-size: clamp(1.7rem, 3vw, 2.4rem);
}

h2 {
  font-size: 1.12rem;
}

.run-meta {
  display: grid;
  grid-template-columns: repeat(3, minmax(120px, max-content));
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
  color: var(--muted);
  font-size: 0.86rem;
}

.meta-chip {
  min-width: 120px;
  padding: 7px 9px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
}

.meta-chip b,
.meta-chip strong {
  display: block;
}

.meta-chip b {
  margin-bottom: 2px;
  color: var(--muted);
  font-size: 0.68rem;
  text-transform: uppercase;
}

.meta-chip strong {
  color: var(--text);
  font-size: 0.82rem;
}

.sync-bar {
  display: grid;
  grid-template-columns: minmax(220px, 1.1fr) minmax(320px, 1.6fr) auto;
  gap: 14px;
  align-items: center;
  margin: 14px 0 0;
  padding: 14px;
  border: 1px solid var(--line);
  border-left: 4px solid var(--accent);
  border-radius: 8px;
  background: var(--surface);
}

.sync-bar.tone-error {
  border-left-color: var(--danger);
}

.sync-bar.tone-refreshing {
  border-left-color: var(--info);
}

.sync-error {
  margin: 8px 0 0;
  color: var(--danger);
  font-size: 0.84rem;
  font-weight: 700;
}

.sync-error[hidden] {
  display: none;
}

.sync-bar strong {
  display: block;
}

.sync-bar span {
  display: block;
  color: var(--muted);
  font-size: 0.86rem;
  margin-top: 3px;
}

.sync-bar dl {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
  margin: 0;
}

.sync-bar dt {
  color: var(--muted);
  font-size: 0.72rem;
  font-weight: 800;
  text-transform: uppercase;
}

.sync-bar dd {
  margin: 3px 0 0;
  font-weight: 700;
}

.sync-refresh {
  min-height: 38px;
  border: 1px solid var(--accent);
  border-radius: 8px;
  background: var(--accent);
  color: white;
  cursor: pointer;
  font: inherit;
  font-weight: 800;
  padding: 8px 12px;
}

.sync-refresh:disabled {
  cursor: wait;
  opacity: 0.72;
}

.tabs {
  display: flex;
  gap: 8px;
  position: sticky;
  top: 0;
  z-index: 10;
  margin: 18px 0;
  padding: 10px 0;
  background: var(--bg);
  overflow-x: auto;
  scrollbar-color: var(--line) transparent;
}

.tab {
  flex: 0 0 auto;
  min-height: 38px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
  color: var(--text);
  padding: 8px 12px;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
}

.tab:hover,
.tab:focus-visible {
  border-color: var(--accent);
  outline: none;
}

.tab.is-active,
.tab[aria-selected="true"] {
  background: var(--accent);
  border-color: var(--accent);
  color: white;
}

.panel {
  display: none;
}

.panel.is-active,
.panel:not([hidden]) {
  display: block;
}

.overview-grid {
  display: grid;
  grid-template-columns: minmax(300px, 0.95fr) minmax(320px, 1.4fr);
  gap: 16px;
  align-items: stretch;
}

.score-band,
.section-block,
.table-shell {
  border: 1px solid var(--line);
  background: var(--surface);
  border-radius: 8px;
}

.score-band {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 22px;
}

.score-ring {
  --score: 0;
  display: grid;
  place-items: center;
  flex: 0 0 132px;
  width: 132px;
  aspect-ratio: 1;
  border-radius: 50%;
  background:
    radial-gradient(circle at center, var(--surface) 58%, transparent 59%),
    conic-gradient(var(--accent) calc(var(--score) * 1%), #d9dfda 0);
}

.score-ring span {
  font-size: 1.5rem;
  font-weight: 800;
}

.muted {
  color: var(--muted);
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.metric-card {
  min-height: 112px;
  border: 1px solid var(--line);
  border-left: 4px solid var(--accent);
  border-radius: 8px;
  background: var(--surface);
  padding: 14px;
}

.metric-card span,
td span {
  display: block;
  color: var(--muted);
  font-size: 0.82rem;
}

.metric-card strong {
  display: block;
  margin: 10px 0 4px;
  font-size: 1.45rem;
}

.metric-card small {
  color: var(--muted);
}

.tone-good {
  border-left-color: var(--accent);
}

.tone-warning {
  border-left-color: var(--gold);
}

.tone-critical {
  border-left-color: var(--danger);
}

.tone-info {
  border-left-color: var(--info);
}

.section-block {
  margin-top: 16px;
  padding: 18px;
}

.section-heading {
  margin: 0 0 14px;
}

.row-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

input[type="search"],
select {
  min-height: 38px;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 8px 10px;
  font: inherit;
  background: #fff;
}

input[type="search"] {
  width: min(340px, 100%);
}

select {
  width: min(190px, 100%);
}

input[type="search"]:focus,
select:focus {
  border-color: var(--accent);
  outline: 2px solid rgb(27 127 107 / 18%);
}

.component-row {
  display: grid;
  grid-template-columns: minmax(220px, 1.2fr) minmax(180px, 1fr) 80px;
  gap: 14px;
  align-items: center;
  padding: 12px 0;
  border-top: 1px solid var(--line);
}

.component-row:first-of-type {
  border-top: 0;
}

.component-copy span {
  display: block;
  margin-top: 3px;
  color: var(--muted);
  font-size: 0.86rem;
}

.component-meter {
  height: 10px;
  overflow: hidden;
  background: var(--surface-strong);
  border-radius: 999px;
}

.component-meter span {
  display: block;
  height: 100%;
  background: var(--accent);
}

.table-shell {
  overflow: auto;
  scrollbar-color: var(--line) transparent;
}

.summary-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.summary-strip span {
  padding: 7px 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
  color: var(--muted);
  font-size: 0.86rem;
  font-weight: 700;
}

.current-goals-grid {
  display: grid;
  grid-template-columns: minmax(260px, 0.78fr) minmax(520px, 1.55fr);
  gap: 16px;
  align-items: start;
}

.goal-picker,
.shared-requirements {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
}

.goal-picker {
  max-height: 660px;
  overflow: auto;
  scrollbar-color: var(--line) transparent;
}

.goal-picker-list {
  display: grid;
  gap: 0;
}

.goal-picker-row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  min-height: 58px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--line);
  cursor: pointer;
}

.goal-picker-row:last-child {
  border-bottom: 0;
}

.goal-picker-row:hover,
.goal-picker-row:has(input:checked) {
  background: #f1f6f2;
}

.goal-picker-row input {
  width: 18px;
  height: 18px;
  accent-color: var(--accent);
}

.goal-picker-row span {
  min-width: 0;
}

.goal-picker-row strong,
.goal-picker-row small {
  display: block;
}

.goal-picker-row strong {
  overflow-wrap: anywhere;
}

.goal-picker-row small {
  color: var(--muted);
  font-size: 0.78rem;
}

.goal-picker-row em {
  display: block;
  color: var(--muted);
  font-size: 0.74rem;
  font-style: normal;
}

.goal-picker-row b {
  color: var(--accent-strong);
}

.goal-comparison {
  min-width: 0;
}

.current-goals-summary b {
  color: var(--text);
}

.current-goals-empty {
  margin-top: 12px;
}

.shared-requirements {
  margin-top: 16px;
  padding: 16px;
}

table {
  width: 100%;
  border-collapse: collapse;
  min-width: 760px;
}

th,
td {
  padding: 11px 12px;
  border-bottom: 1px solid var(--line);
  text-align: left;
  vertical-align: top;
}

th {
  background: var(--surface-strong);
  color: #33423a;
  font-size: 0.8rem;
  text-transform: uppercase;
}

tbody tr:nth-child(even) td {
  background: #fbfcfb;
}

tbody tr:hover td {
  background: #f1f6f2;
}

td strong {
  display: block;
  margin-bottom: 3px;
}

.numeric {
  text-align: right;
  white-space: nowrap;
}

.pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 76px;
  min-height: 26px;
  border-radius: 999px;
  padding: 3px 9px;
  color: white;
  font-size: 0.78rem;
  font-weight: 800;
  text-transform: uppercase;
}

.pill.tone-high,
.pill.tone-good {
  background: var(--accent);
}

.pill.tone-medium,
.pill.tone-warning {
  background: var(--gold);
}

.pill.tone-low {
  background: var(--info);
}

.empty-state {
  margin: 0;
  padding: 18px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
  color: var(--muted);
}

.empty-state strong {
  color: var(--text);
}

.empty-state[hidden],
.filter-empty[hidden] {
  display: none;
}

@media (max-width: 860px) {
  .app-shell {
    width: min(100% - 20px, 1360px);
    padding-top: 12px;
  }

  .topbar,
  .row-heading,
  .score-band {
    align-items: stretch;
    flex-direction: column;
  }

  .run-meta {
    grid-template-columns: 1fr;
    justify-content: flex-start;
  }

  .sync-bar,
  .sync-bar dl {
    grid-template-columns: 1fr;
  }

  .overview-grid,
  .metric-grid,
  .current-goals-grid,
  .component-row {
    grid-template-columns: 1fr;
  }

  .score-ring {
    flex-basis: auto;
    width: 112px;
  }

  table {
    min-width: 680px;
  }
}
"""


_DASHBOARD_JS = """
(function () {
  function formatSyncDate(value) {
    if (!value) {
      return "Not yet";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    const year = date.getUTCFullYear();
    const month = String(date.getUTCMonth() + 1).padStart(2, "0");
    const day = String(date.getUTCDate()).padStart(2, "0");
    const hour = String(date.getUTCHours()).padStart(2, "0");
    const minute = String(date.getUTCMinutes()).padStart(2, "0");
    return `${year}-${month}-${day} ${hour}:${minute} UTC`;
  }

  function titleCase(value) {
    if (!value) {
      return "Ready";
    }
    return `${value.charAt(0).toUpperCase()}${value.slice(1)}`;
  }

  function readDashboardPayload() {
    const data = document.querySelector("#dashboard-data");
    if (!data || !data.textContent) {
      return {};
    }
    try {
      return JSON.parse(data.textContent);
    } catch (error) {
      return {};
    }
  }

  const dashboardPayload = readDashboardPayload();

  function readInitialSyncStatus() {
    return dashboardPayload.sync_status || {};
  }

  function applySyncStatus(status) {
    const nextState = status.state || "ready";
    if (syncBar) {
      ["ready", "refreshing", "error"].forEach((state) => {
        syncBar.classList.toggle(`tone-${state}`, state === nextState);
      });
    }
    if (syncState) {
      syncState.textContent = titleCase(nextState);
    }
    if (syncMessage) {
      syncMessage.textContent = status.message || "";
    }
    if (syncLoaded) {
      syncLoaded.textContent = formatSyncDate(status.loaded_at);
    }
    if (syncLastRefresh) {
      syncLastRefresh.textContent = formatSyncDate(status.last_refresh_at);
    }
    if (syncError) {
      syncError.textContent = status.error || "";
      syncError.hidden = !status.error;
    }
  }

  const tabs = Array.from(document.querySelectorAll("[data-panel-target]"));
  const panels = Array.from(document.querySelectorAll("[data-panel]"));
  const tabTargets = new Set(tabs.map((tab) => tab.getAttribute("data-panel-target")));

  function activeTargetFromHash() {
    const target = window.location.hash.replace(/^#/, "");
    return tabTargets.has(target) ? target : "overview";
  }

  function activatePanel(target, options = {}) {
    const resolvedTarget = tabTargets.has(target) ? target : "overview";
    tabs.forEach((candidate) => {
      const isActive = candidate.getAttribute("data-panel-target") === resolvedTarget;
      candidate.classList.toggle("is-active", isActive);
      candidate.setAttribute("aria-selected", isActive ? "true" : "false");
      candidate.tabIndex = isActive ? 0 : -1;
    });
    panels.forEach((panel) => {
      const isActive = panel.getAttribute("data-panel") === resolvedTarget;
      panel.classList.toggle("is-active", isActive);
      panel.hidden = !isActive;
    });
    if (options.updateHash && window.location.hash !== `#${resolvedTarget}`) {
      window.history.replaceState(null, "", `#${resolvedTarget}`);
    }
  }

  function focusAdjacentTab(currentTab, direction) {
    const currentIndex = tabs.indexOf(currentTab);
    if (currentIndex < 0) {
      return;
    }
    const nextIndex = (currentIndex + direction + tabs.length) % tabs.length;
    const nextTab = tabs[nextIndex];
    nextTab.focus();
    activatePanel(nextTab.getAttribute("data-panel-target"), { updateHash: true });
  }

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      activatePanel(tab.getAttribute("data-panel-target"), { updateHash: true });
    });
    tab.addEventListener("keydown", (event) => {
      if (event.key === "ArrowRight") {
        event.preventDefault();
        focusAdjacentTab(tab, 1);
      } else if (event.key === "ArrowLeft") {
        event.preventDefault();
        focusAdjacentTab(tab, -1);
      } else if (event.key === "Home") {
        event.preventDefault();
        tabs[0].focus();
        activatePanel(tabs[0].getAttribute("data-panel-target"), { updateHash: true });
      } else if (event.key === "End") {
        event.preventDefault();
        const lastTab = tabs[tabs.length - 1];
        lastTab.focus();
        activatePanel(lastTab.getAttribute("data-panel-target"), { updateHash: true });
      }
    });
  });
  window.addEventListener("hashchange", () => {
    activatePanel(activeTargetFromHash(), { updateHash: false });
  });
  activatePanel(activeTargetFromHash(), { updateHash: false });

  const refreshButton = document.querySelector("[data-refresh-dashboard]");
  const syncBar = document.querySelector("[data-sync-bar]");
  const syncState = document.querySelector("[data-sync-state]");
  const syncMessage = document.querySelector("[data-sync-message]");
  const syncError = document.querySelector("[data-sync-error]");
  const syncLoaded = document.querySelector("[data-sync-loaded]");
  const syncLastRefresh = document.querySelector("[data-sync-last-refresh]");
  let syncStatus = readInitialSyncStatus();
  if (refreshButton) {
    refreshButton.addEventListener("click", async () => {
      refreshButton.disabled = true;
      const originalText = refreshButton.textContent.trim();
      refreshButton.textContent = "Refreshing";
      refreshButton.setAttribute("aria-busy", "true");
      applySyncStatus({
        ...syncStatus,
        state: "refreshing",
        message: "Refreshing account data from the selected source.",
        error: null,
      });

      try {
        const response = await fetch("/api/refresh", { method: "POST" });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(
            payload.error || payload.message || `Refresh failed with ${response.status}`
          );
        }
        syncStatus = payload;
        applySyncStatus({
          ...syncStatus,
          message: "Refresh complete. Reloading dashboard.",
          error: null,
        });
        window.location.reload();
      } catch (error) {
        refreshButton.disabled = false;
        refreshButton.removeAttribute("aria-busy");
        refreshButton.textContent = originalText || "Refresh";
        syncStatus = {
          ...syncStatus,
          state: "error",
          message: "Refresh failed. Fix the source issue and try again.",
          error: error instanceof Error ? error.message : String(error),
        };
        applySyncStatus(syncStatus);
      }
    });
  }

  const recommendationFilter = document.querySelector("#recommendation-filter");
  const rows = Array.from(document.querySelectorAll("[data-recommendation-row]"));
  const noRecommendationMatches = document.querySelector("[data-recommendation-empty]");
  if (recommendationFilter && rows.length > 0) {
    recommendationFilter.addEventListener("input", () => {
      const query = recommendationFilter.value.trim().toLowerCase();
      let visibleCount = 0;
      rows.forEach((row) => {
        const haystack = row.getAttribute("data-search") || "";
        const isHidden = query.length > 0 && !haystack.includes(query);
        row.hidden = isHidden;
        if (!isHidden) {
          visibleCount += 1;
        }
      });
      if (noRecommendationMatches) {
        noRecommendationMatches.hidden = query.length === 0 || visibleCount > 0;
      }
    });
  }

  function formatNumber(value) {
    return new Intl.NumberFormat("en-US").format(value || 0);
  }

  function formatPercent(value) {
    if (value == null || Number.isNaN(Number(value))) {
      return "-";
    }
    return `${Number(value).toFixed(0)}%`;
  }

  function formatCopper(value) {
    if (value == null) {
      return "-";
    }
    const total = Number(value);
    const gold = Math.floor(total / 10000);
    const silver = Math.floor((total % 10000) / 100);
    const copper = total % 100;
    const silverText = String(silver).padStart(2, "0");
    const copperText = String(copper).padStart(2, "0");
    return `${formatNumber(gold)}g ${silverText}s ${copperText}c`;
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function categoryLabel(value) {
    return String(value || "").replaceAll("_", " ");
  }

  function setupCurrentGoals() {
    const report = dashboardPayload.goal_comparison_report;
    const root = document.querySelector("[data-current-goals]");
    if (!root || !report || !Array.isArray(report.goals)) {
      return;
    }

    const availableIds = new Set(report.goals.map((goal) => goal.recipe_id));
    const storageKey = `gw2planner.currentGoals.${dashboardPayload.account_name || "account"}`;
    const toggles = Array.from(document.querySelectorAll("[data-goal-toggle]"));
    const pickerRows = Array.from(document.querySelectorAll("[data-goal-picker-row]"));
    const comparisonRows = Array.from(document.querySelectorAll("[data-goal-comparison-row]"));
    const goalFilter = document.querySelector("#goal-filter");
    const goalGenerationFilter = document.querySelector("#goal-generation-filter");
    const goalFamilyFilter = document.querySelector("#goal-family-filter");
    const emptyState = document.querySelector("[data-current-goals-empty]");
    const sharedBody = document.querySelector("[data-shared-requirements-body]");
    const selectedCount = document.querySelector("[data-selected-goal-count]");
    const selectedReadiness = document.querySelector("[data-selected-readiness]");
    const selectedBound = document.querySelector("[data-selected-bound]");
    const selectedManual = document.querySelector("[data-selected-manual]");
    const selectedTradeable = document.querySelector("[data-selected-tradeable]");
    const selectedPrice = document.querySelector("[data-selected-price]");

    function defaultSelectedIds() {
      return (report.selected_goal_ids || []).filter((goalId) => availableIds.has(goalId));
    }

    function readSelectedIds() {
      try {
        const stored = JSON.parse(window.localStorage.getItem(storageKey) || "null");
        if (Array.isArray(stored)) {
          return stored.filter((goalId) => availableIds.has(goalId));
        }
      } catch (error) {
        return defaultSelectedIds();
      }
      return defaultSelectedIds();
    }

    let selectedIds = new Set(readSelectedIds());

    function displayMetadataValue(value) {
      return String(value || "")
        .replaceAll("_", " ")
        .replace(/\\b\\w/g, (letter) => letter.toUpperCase());
    }

    function populateSelect(select, values) {
      if (!select) {
        return;
      }
      values.forEach((value) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = displayMetadataValue(value);
        select.appendChild(option);
      });
    }

    populateSelect(
      goalGenerationFilter,
      Array.from(new Set(report.goals.map((goal) => goal.generation).filter(Boolean))).sort()
    );
    populateSelect(
      goalFamilyFilter,
      Array.from(new Set(report.goals.map((goal) => goal.family).filter(Boolean))).sort()
    );

    function selectedGoals() {
      return report.goals.filter((goal) => selectedIds.has(goal.recipe_id));
    }

    function writeSelectedIds() {
      window.localStorage.setItem(storageKey, JSON.stringify(Array.from(selectedIds)));
    }

    function updateSummary(goals) {
      const count = goals.length;
      const readiness = count
        ? goals.reduce((total, goal) => total + goal.readiness_percent, 0) / count
        : null;
      const bound = goals.reduce(
        (total, goal) => total + goal.account_bound_missing_entries,
        0
      );
      const manual = goals.reduce((total, goal) => total + goal.manual_missing_entries, 0);
      const tradeable = goals.reduce(
        (total, goal) => total + goal.tradeable_missing_entries,
        0
      );
      const pricedGoals = goals.filter((goal) => goal.estimated_buy_cost != null);
      const price = pricedGoals.length
        ? pricedGoals.reduce((total, goal) => total + goal.estimated_buy_cost, 0)
        : null;

      if (selectedCount) selectedCount.textContent = formatNumber(count);
      if (selectedReadiness) selectedReadiness.textContent = formatPercent(readiness);
      if (selectedBound) selectedBound.textContent = formatNumber(bound);
      if (selectedManual) selectedManual.textContent = formatNumber(manual);
      if (selectedTradeable) selectedTradeable.textContent = formatNumber(tradeable);
      if (selectedPrice) selectedPrice.textContent = formatCopper(price);
    }

    function updateSharedRequirements(goals) {
      if (!sharedBody) {
        return;
      }
      const shared = new Map();
      goals.forEach((goal) => {
        (goal.missing_requirements || []).forEach((requirement) => {
          if (requirement.kind !== "item" || requirement.missing_quantity <= 0) {
            return;
          }
          const key = `${requirement.kind}:${requirement.id}`;
          const entry = shared.get(key) || {
            name: requirement.name || requirement.id,
            category: requirement.category,
            total: 0,
            goals: [],
          };
          entry.total += requirement.missing_quantity;
          entry.goals.push(goal.recipe_name);
          shared.set(key, entry);
        });
      });
      const rows = Array.from(shared.values())
        .filter((entry) => new Set(entry.goals).size > 1)
        .sort((left, right) => (
          right.total - left.total
          || String(left.name).localeCompare(String(right.name))
        ));

      if (rows.length === 0) {
        sharedBody.innerHTML = `
          <tr>
            <td colspan="4">No shared missing item requirements for the selected goals.</td>
          </tr>
        `;
        return;
      }

      sharedBody.innerHTML = rows.map((entry) => `
        <tr>
          <td><strong>${escapeHtml(entry.name)}</strong></td>
          <td class="numeric">${formatNumber(entry.total)}</td>
          <td>${escapeHtml(categoryLabel(entry.category))}</td>
          <td>${escapeHtml(Array.from(new Set(entry.goals)).join(", "))}</td>
        </tr>
      `).join("");
    }

    function applySelection() {
      const goals = selectedGoals();
      toggles.forEach((toggle) => {
        toggle.checked = selectedIds.has(toggle.value);
      });
      comparisonRows.forEach((row) => {
        const goalId = row.getAttribute("data-goal-id");
        row.hidden = !goalId || !selectedIds.has(goalId);
      });
      if (emptyState) {
        emptyState.hidden = goals.length > 0;
      }
      updateSummary(goals);
      updateSharedRequirements(goals);
      writeSelectedIds();
    }

    toggles.forEach((toggle) => {
      toggle.addEventListener("change", () => {
        if (toggle.checked) {
          selectedIds.add(toggle.value);
        } else {
          selectedIds.delete(toggle.value);
        }
        applySelection();
      });
    });

    if (goalFilter) {
      goalFilter.addEventListener("input", applyGoalFilters);
    }
    if (goalGenerationFilter) {
      goalGenerationFilter.addEventListener("change", applyGoalFilters);
    }
    if (goalFamilyFilter) {
      goalFamilyFilter.addEventListener("change", applyGoalFilters);
    }
    function applyGoalFilters() {
      const query = goalFilter ? goalFilter.value.trim().toLowerCase() : "";
      const generation = goalGenerationFilter ? goalGenerationFilter.value : "";
      const family = goalFamilyFilter ? goalFamilyFilter.value : "";
      pickerRows.forEach((row) => {
        const haystack = row.getAttribute("data-search") || "";
        const rowGeneration = row.getAttribute("data-generation") || "";
        const rowFamily = row.getAttribute("data-family") || "";
        row.hidden = (
          (query.length > 0 && !haystack.includes(query))
          || (generation && rowGeneration !== generation)
          || (family && rowFamily !== family)
        );
      });
    }
    applySelection();
    applyGoalFilters();
  }

  setupCurrentGoals();
})();
"""
