"""Browser-based desktop dashboard adapters."""

from gw2_legendary_planner.gui.dashboard import (
    DashboardMetric,
    DashboardPayload,
    build_dashboard_payload,
    render_dashboard_html,
    write_dashboard_html,
)
from gw2_legendary_planner.gui.setup import render_api_key_setup_html

__all__ = [
    "DashboardMetric",
    "DashboardPayload",
    "build_dashboard_payload",
    "render_api_key_setup_html",
    "render_dashboard_html",
    "write_dashboard_html",
]
