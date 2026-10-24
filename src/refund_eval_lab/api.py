from __future__ import annotations

import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from .service import RUNS, list_scenarios, run_scenario, run_suite, scenario_detail

WEB_ROOT = Path(__file__).resolve().parents[2] / "web"
MAX_BODY = 64 * 1024


class Handler(BaseHTTPRequestHandler):
    server_version = "RefundEvalLab/1.0"

    def _json(self, status: int, payload: object) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def _error(self, status: int, code: str, message: str) -> None:
        self._json(status, {"error": {"code": code, "message": message}})

    def _serve_static(self, name: str) -> None:
        path = WEB_ROOT / name
        if not path.is_file() or path.parent != WEB_ROOT:
            self._error(404, "not_found", "Resource not found")
            return
        body = path.read_bytes()
        media = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", f"{media}; charset=utf-8" if media.startswith("text/") or media.endswith("javascript") else media)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = unquote(urlparse(self.path).path)
        if path == "/health":
            self._json(200, {"status": "ok", "engine": "deterministic", "dataset": "refund-suite-v1"})
        elif path == "/api/scenarios":
            self._json(200, {"scenarios": list_scenarios()})
        elif path.startswith("/api/scenarios/"):
            item = scenario_detail(path.removeprefix("/api/scenarios/"))
            self._json(200, item) if item else self._error(404, "scenario_not_found", "Unknown scenario")
        elif path.startswith("/api/runs/"):
            item = RUNS.get(path.removeprefix("/api/runs/"))
            self._json(200, item) if item else self._error(404, "run_not_found", "Unknown run")
        elif path in ("/", "/index.html"):
            self._serve_static("index.html")
        elif path in ("/styles.css", "/app.js"):
            self._serve_static(path[1:])
        else:
            self._error(404, "not_found", "Resource not found")

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        length_raw = self.headers.get("Content-Length", "0")
        try:
            length = int(length_raw)
        except ValueError:
            self._error(400, "invalid_length", "Invalid Content-Length")
            return
        if length > MAX_BODY:
            self._error(413, "body_too_large", "Request body exceeds 64 KiB")
            return
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._error(400, "invalid_json", "Request body must be valid JSON")
            return
        if not isinstance(body, dict):
            self._error(400, "invalid_body", "Request body must be a JSON object")
            return
        if path == "/api/evaluate-all":
            if body:
                self._error(400, "unknown_fields", "No fields are accepted for suite evaluation")
                return
            self._json(200, run_suite())
            return
        if path == "/api/evaluate":
            unknown = set(body) - {"scenario_id"}
            if unknown:
                self._error(400, "unknown_fields", "Unsupported fields: " + ", ".join(sorted(unknown)))
                return
            scenario_id = body.get("scenario_id")
            if not isinstance(scenario_id, str) or not scenario_id:
                self._error(400, "scenario_id_required", "scenario_id is required")
                return
            try:
                self._json(200, run_scenario(scenario_id))
            except KeyError:
                self._error(404, "scenario_not_found", "Unknown scenario")
            return
        self._error(404, "not_found", "Resource not found")

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.address_string()} - {fmt % args}")


def make_server(host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), Handler)


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = make_server(host, port)
    print(f"Refund Agent Eval Lab: http://{host}:{server.server_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
