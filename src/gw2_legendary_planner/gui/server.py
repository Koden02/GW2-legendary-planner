from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


class DashboardServer(ThreadingHTTPServer):
    """HTTP server for the generated dashboard page."""

    allow_reuse_address = True


def create_dashboard_server(
    html: str,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
) -> DashboardServer:
    """Create a local server that serves one dashboard HTML page."""

    encoded_html = html.encode("utf-8")

    class DashboardRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path not in {"/", "/index.html"}:
                self.send_error(HTTPStatus.NOT_FOUND, "Not found")
                return

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded_html)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(encoded_html)

        def log_message(self, format: str, *args: object) -> None:
            return

    return DashboardServer((host, port), DashboardRequestHandler)
