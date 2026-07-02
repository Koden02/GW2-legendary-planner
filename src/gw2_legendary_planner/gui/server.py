from __future__ import annotations

import json
from collections.abc import Callable
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from typing import Any
from urllib.parse import urlparse

from gw2_legendary_planner.gui.dashboard import (
    DashboardPayload,
    DashboardSyncStatus,
    render_dashboard_html,
)

DashboardRefreshProvider = Callable[[], DashboardPayload]


class DashboardServer(ThreadingHTTPServer):
    """HTTP server for a dashboard page with optional refresh support."""

    allow_reuse_address = True

    def __init__(
        self,
        server_address: tuple[str, int],
        request_handler_class: type[BaseHTTPRequestHandler],
        *,
        html: str,
        payload: DashboardPayload | None = None,
        refresh_provider: DashboardRefreshProvider | None = None,
    ) -> None:
        super().__init__(server_address, request_handler_class)
        self._html = html
        self._payload = payload
        self._refresh_provider = refresh_provider
        self._lock = Lock()

    @property
    def html(self) -> str:
        with self._lock:
            return self._html

    def status_payload(self) -> dict[str, Any]:
        with self._lock:
            if self._payload:
                return self._payload.sync_status.model_dump(mode="json")
            return DashboardSyncStatus().model_dump(mode="json")

    def refresh_dashboard(self) -> DashboardPayload:
        if not self._refresh_provider:
            raise RuntimeError("Dashboard refresh is not available for this server.")
        payload = self._refresh_provider()
        html = render_dashboard_html(payload)
        with self._lock:
            self._payload = payload
            self._html = html
        return payload


def create_dashboard_server(
    dashboard: str | DashboardPayload,
    *,
    host: str = "127.0.0.1",
    port: int = 0,
    refresh_provider: DashboardRefreshProvider | None = None,
) -> DashboardServer:
    """Create a local server for a dashboard HTML page or payload."""

    payload = dashboard if isinstance(dashboard, DashboardPayload) else None
    html = (
        render_dashboard_html(dashboard)
        if isinstance(dashboard, DashboardPayload)
        else dashboard
    )

    class DashboardRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path in {"/", "/index.html"}:
                self._send_html(self.server.html)
                return
            if path == "/api/status":
                self._send_json(self.server.status_payload())
                return
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            if path != "/api/refresh":
                self.send_error(HTTPStatus.NOT_FOUND, "Not found")
                return
            try:
                payload = self.server.refresh_dashboard()
            except RuntimeError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.METHOD_NOT_ALLOWED)
                return
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            self._send_json(payload.sync_status.model_dump(mode="json"))

        def log_message(self, format: str, *args: object) -> None:
            return

        def _send_html(self, html: str) -> None:
            encoded_html = html.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded_html)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(encoded_html)

        def _send_json(
            self,
            payload: dict[str, Any],
            *,
            status: HTTPStatus = HTTPStatus.OK,
        ) -> None:
            encoded_payload = json.dumps(payload, default=str).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded_payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(encoded_payload)

    return DashboardServer(
        (host, port),
        DashboardRequestHandler,
        html=html,
        payload=payload,
        refresh_provider=refresh_provider,
    )
