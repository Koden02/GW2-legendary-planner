from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from gw2_legendary_planner import __version__
from gw2_legendary_planner.planner.activities import ActivityGoalStatus
from gw2_legendary_planner.planner.legendary_focus import FocusEntry
from gw2_legendary_planner.planner.progression import (
    AccountProgressionReport,
    AccountRecommendation,
    ProgressionScoreComponent,
)
from gw2_legendary_planner.planner.shopping_list import ShoppingListReport
from gw2_legendary_planner.reports.summary import AccountSummary

DashboardTone = Literal["neutral", "good", "warning", "critical", "info"]


class DashboardMetric(BaseModel):
    """One dashboard summary metric."""

    id: str
    label: str
    value: str
    detail: str | None = None
    tone: DashboardTone = "neutral"


class DashboardPayload(BaseModel):
    """Serializable data contract for the browser-based dashboard."""

    app_name: str = "GW2 Legendary Planner"
    app_version: str = __version__
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source_label: str = "account data"
    account_name: str = "Unknown account"
    metrics: list[DashboardMetric] = Field(default_factory=list)
    score_percent: float | None = None
    score_components: list[ProgressionScoreComponent] = Field(default_factory=list)
    recommendations: list[AccountRecommendation] = Field(default_factory=list)
    shopping_list: ShoppingListReport | None = None
    focus_items: list[FocusEntry] = Field(default_factory=list)
    activities: list[ActivityGoalStatus] = Field(default_factory=list)


def build_dashboard_payload(
    summary: AccountSummary,
    *,
    focus_items: list[FocusEntry],
    activities: list[ActivityGoalStatus],
    progression_report: AccountProgressionReport | None = None,
    shopping_list: ShoppingListReport | None = None,
    source_label: str = "account data",
    generated_at: datetime | None = None,
) -> DashboardPayload:
    """Build a dashboard view model from reusable planner outputs."""

    visible_focus_items = sorted(
        [entry for entry in focus_items if entry.quantity > 0],
        key=lambda entry: (entry.category, entry.name),
    )
    return DashboardPayload(
        generated_at=generated_at or datetime.now(UTC),
        source_label=source_label,
        account_name=summary.account_name or "Unknown account",
        metrics=_summary_metrics(summary),
        score_percent=(
            progression_report.score.overall_score_percent if progression_report else None
        ),
        score_components=progression_report.score.components if progression_report else [],
        recommendations=progression_report.recommendations if progression_report else [],
        shopping_list=shopping_list,
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
      <div class="run-meta">
        <span>{escape(payload.source_label)}</span>
        <span>{escape(_format_datetime(payload.generated_at))}</span>
      </div>
    </header>

    <nav class="tabs" aria-label="Dashboard views">
      <button class="tab is-active" type="button" data-panel-target="overview">
        Overview
      </button>
      <button class="tab" type="button" data-panel-target="recommendations">
        Recommendations
      </button>
      <button class="tab" type="button" data-panel-target="shopping-list">
        Shopping List
      </button>
      <button class="tab" type="button" data-panel-target="materials">
        Materials
      </button>
      <button class="tab" type="button" data-panel-target="activities">
        Activities
      </button>
    </nav>

    <main>
      <section class="panel is-active" data-panel="overview">
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

      <section class="panel" data-panel="recommendations">
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

      <section class="panel" data-panel="shopping-list">
        <div class="section-heading">
          <p class="eyebrow">Crafting Targets</p>
          <h2>Shopping List</h2>
        </div>
        {_render_shopping_list(payload.shopping_list)}
      </section>

      <section class="panel" data-panel="materials">
        <div class="section-heading">
          <p class="eyebrow">Legendary Focus</p>
          <h2>Important Materials</h2>
        </div>
        {_render_focus_items(payload.focus_items)}
      </section>

      <section class="panel" data-panel="activities">
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


def _render_metrics(metrics: list[DashboardMetric]) -> str:
    if not metrics:
        return _empty_state("No summary metrics are available.")
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
        return _empty_state("No score components are available.")
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
        return _empty_state("No recommendations are available.")
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
    """


def _render_shopping_list(report: ShoppingListReport | None) -> str:
    if report is None:
        return _empty_state("Add --shopping-list-recipe to include crafting targets.")
    if not report.entries:
        return _empty_state("No missing effective costs for the selected recipes.")
    rows = []
    for entry in report.entries:
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
              <td>{escape(_format_contributions(entry.contributions))}</td>
            </tr>
            """
        )
    return f"""
        <div class="summary-strip">
          <span>{report.goal_count:,} goals</span>
          <span>{report.missing_entry_count:,} missing entries</span>
          <span>{report.total_missing_quantity:,} total missing quantity</span>
        </div>
        <div class="table-shell">
          <table>
            <thead>
              <tr>
                <th>Requirement</th>
                <th>Kind</th>
                <th class="numeric">Required</th>
                <th class="numeric">Available</th>
                <th class="numeric">Missing</th>
                <th>Acquisition</th>
                <th>Recipes</th>
              </tr>
            </thead>
            <tbody>
              {"".join(rows)}
            </tbody>
          </table>
        </div>
    """


def _render_focus_items(items: list[FocusEntry]) -> str:
    if not items:
        return _empty_state("No focus items are present in the loaded account data.")
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
        return _empty_state("No activity planner data is available.")
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
    return "; ".join(
        f"{location.source} x{location.quantity:,}"
        for location in locations
    )


def _format_contributions(contributions) -> str:
    if not contributions:
        return "-"
    return "; ".join(
        f"{contribution.recipe_name} x{contribution.required_quantity:,}"
        for contribution in contributions
    )


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
    return f'<p class="empty-state">{escape(message)}</p>'


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
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
  color: var(--muted);
  font-size: 0.86rem;
}

.run-meta span {
  padding: 6px 9px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
}

.tabs {
  display: flex;
  gap: 8px;
  margin: 18px 0;
  overflow-x: auto;
}

.tab {
  min-height: 38px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
  color: var(--text);
  padding: 8px 12px;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

.tab:hover,
.tab:focus-visible {
  border-color: var(--accent);
  outline: none;
}

.tab.is-active {
  background: var(--accent);
  border-color: var(--accent);
  color: white;
}

.panel {
  display: none;
}

.panel.is-active {
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
}

input[type="search"] {
  min-height: 38px;
  width: min(340px, 100%);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 8px 10px;
  font: inherit;
}

input[type="search"]:focus {
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
    justify-content: flex-start;
  }

  .overview-grid,
  .metric-grid,
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
  const tabs = Array.from(document.querySelectorAll("[data-panel-target]"));
  const panels = Array.from(document.querySelectorAll("[data-panel]"));

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const target = tab.getAttribute("data-panel-target");
      tabs.forEach((candidate) => {
        candidate.classList.toggle("is-active", candidate === tab);
      });
      panels.forEach((panel) => {
        panel.classList.toggle("is-active", panel.getAttribute("data-panel") === target);
      });
    });
  });

  const filter = document.querySelector("#recommendation-filter");
  const rows = Array.from(document.querySelectorAll("[data-recommendation-row]"));
  if (!filter || rows.length === 0) {
    return;
  }

  filter.addEventListener("input", () => {
    const query = filter.value.trim().toLowerCase();
    rows.forEach((row) => {
      const haystack = row.getAttribute("data-search") || "";
      row.hidden = query.length > 0 && !haystack.includes(query);
    });
  });
})();
"""
