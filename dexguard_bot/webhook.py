from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .bot import build_runtime, handle_update
from .config import Settings


LOG = logging.getLogger("dexguard_bot.webhook")


class WebhookServer:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.telegram, self.scanner = build_runtime(settings)
        self.executor = ThreadPoolExecutor(max_workers=8)

    def run(self) -> None:
        webhook_url = f"{self.settings.webhook_url}{self.settings.webhook_path}"
        self.telegram.set_webhook(webhook_url)
        LOG.info("Webhook registered at %s", webhook_url)

        server_ref = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if self.path == "/" or self.path == "/health":
                    self._send(200, b"ok")
                    return
                self._send(404, b"not found")

            def do_POST(self) -> None:
                if self.path != server_ref.settings.webhook_path:
                    self._send(404, b"not found")
                    return

                length = int(self.headers.get("Content-Length", "0") or "0")
                raw = self.rfile.read(length)
                try:
                    update = json.loads(raw.decode("utf-8"))
                    server_ref.executor.submit(handle_update, update, server_ref.telegram, server_ref.scanner)
                except Exception:
                    LOG.exception("Webhook update failed")
                self._send(200, b"ok")

            def log_message(self, format: str, *args: object) -> None:
                LOG.debug(format, *args)

            def _send(self, status: int, body: bytes) -> None:
                self.send_response(status)
                self.send_header("Content-Type", "text/plain")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        httpd = ThreadingHTTPServer(("0.0.0.0", self.settings.port), Handler)
        LOG.info("Webhook server listening on port %s", self.settings.port)
        httpd.serve_forever()
