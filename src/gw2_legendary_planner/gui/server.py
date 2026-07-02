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
DashboardSetupProvider = Callable[[str], DashboardPayload]
_MAX_JSON_BODY_BYTES = 64 * 1024


class DashboardRefreshUnavailableError(RuntimeError):
    """Raised when refresh is requested for a static dashboard server."""


class DashboardSetupUnavailableError(RuntimeError):
    """Raised when first-run setup is requested for a static dashboard server."""


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
        api_key_setup_provider: DashboardSetupProvider | None = None,
    ) -> None:
        super().__init__(server_address, request_handler_class)
        self._html = html
        self._payload = payload
        self._refresh_provider = refresh_provider
        self._api_key_setup_provider = api_key_setup_provider
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
            raise DashboardRefreshUnavailableError(
                "Dashboard refresh is not available for this server."
            )
        payload = self._refresh_provider()
        html = render_dashboard_html(payload)
        with self._lock:
            self._payload = payload
            self._html = html
        return payload

    def setup_with_api_key(self, api_key: str) -> DashboardPayload:
        if not self._api_key_setup_provider:
            raise DashboardSetupUnavailableError(
                "API key setup is not available for this server."
            )
        payload = self._api_key_setup_provider(api_key)
        html = render_dashboard_html(payload)
        with self._lock:
            self._payload = payload
            self._html = html
        return payload

    def record_refresh_error(self, error: Exception) -> dict[str, Any]:
        error_message = str(error) or error.__class__.__name__
        with self._lock:
            current_status = (
                self._payload.sync_status
                if self._payload
                else DashboardSyncStatus(refresh_available=self._refresh_provider is not None)
            )
            error_status = current_status.model_copy(
                update={
                    "state": "error",
                    "refresh_available": self._refresh_provider is not None,
                    "message": "Refresh failed. Fix the source issue and try again.",
                    "error": error_message,
                }
            )
            if self._payload:
                self._payload.sync_status = error_status
                self._html = render_dashboard_html(self._payload)
            return error_status.model_dump(mode="json")


def create_dashboard_server(
    dashboard: str | DashboardPayload,
    *,
    host: str = "127.0.0.1",
    port: int = 0,
    refresh_provider: DashboardRefreshProvider | None = None,
    api_key_setup_provider: DashboardSetupProvider | None = None,
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
            if path == "/api/refresh":
                self._handle_refresh()
                return
            if path == "/api/setup/api-key":
                self._handle_api_key_setup()
                return
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")

        def _handle_refresh(self) -> None:
            try:
                payload = self.server.refresh_dashboard()
            except DashboardRefreshUnavailableError as exc:
                status_payload = self.server.record_refresh_error(exc)
                self._send_json(status_payload, status=HTTPStatus.METHOD_NOT_ALLOWED)
                return
            except Exception as exc:
                status_payload = self.server.record_refresh_error(exc)
                self._send_json(status_payload, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            self._send_json(payload.sync_status.model_dump(mode="json"))

        def _handle_api_key_setup(self) -> None:
            try:
                request_payload = self._read_json_payload()
                api_key = str(request_payload.get("api_key", "")).strip()
                if not api_key:
                    self._send_json(
                        {"error": "API key is required."},
                        status=HTTPStatus.BAD_REQUEST,
                    )
                    return
                payload = self.server.setup_with_api_key(api_key)
            except ValueError as exc:
                self._send_json(
                    {"error": str(exc)},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            except DashboardSetupUnavailableError as exc:
                self._send_json(
                    {"error": str(exc)},
                    status=HTTPStatus.METHOD_NOT_ALLOWED,
                )
                return
            except Exception as exc:
                self._send_json(
                    {"error": str(exc) or exc.__class__.__name__},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            self._send_json(payload.sync_status.model_dump(mode="json"))

        def log_message(self, format: str, *args: object) -> None:
            return

        def _read_json_payload(self) -> dict[str, Any]:
            try:
                content_length = int(self.headers.get("Content-Length", "0") or "0")
            except ValueError as exc:
                raise ValueError("Content-Length must be a number.") from exc
            if content_length > _MAX_JSON_BODY_BYTES:
                raise ValueError("Request body is too large.")
            raw_payload = self.rfile.read(content_length)
            try:
                payload = json.loads(raw_payload.decode("utf-8") if raw_payload else "{}")
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError("Request body must be valid JSON.") from exc
            if not isinstance(payload, dict):
                raise ValueError("Request body must be a JSON object.")
            return payload

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
        api_key_setup_provider=api_key_setup_provider,
    )
