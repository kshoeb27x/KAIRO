from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import sys
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = PROJECT_ROOT / "05_UI" / "Web"

sys.path.insert(0, str(PROJECT_ROOT))

from src.core.kairo_core import KairoCore


kairo = KairoCore()


class KairoHandler(BaseHTTPRequestHandler):
    """HTTP API and Web UI server for KAIRO V1."""

    def send_json(self, data: dict | list, status: int = 200) -> None:
        payload = json.dumps(data, indent=2).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

        self.wfile.write(payload)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))

        if length <= 0:
            return {}

        body = self.rfile.read(length)

        return json.loads(body.decode("utf-8"))

    def do_GET(self) -> None:
        path = urlparse(self.path).path

        # -------------------------
        # KAIRO API
        # -------------------------

        if path == "/api/status":
            self.send_json(kairo.status())
            return

        if path == "/api/tasks":
            self.send_json({
                "tasks": kairo.runtime.tasks.list_tasks()
            })
            return

        if path == "/api/events":
            self.send_json({
                "events": kairo.events()
            })
            return

        # -------------------------
        # WEB UI
        # -------------------------

        if path in {"/", "/index.html"}:
            self.serve_file("index.html", "text/html")
            return

        if path == "/style.css":
            self.serve_file("style.css", "text/css")
            return

        if path == "/app.js":
            self.serve_file("app.js", "application/javascript")
            return

        self.send_json({
            "error": "Not Found",
            "path": path,
        }, 404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path

        try:
            data = self.read_json()

            # -------------------------
            # CHAT
            # -------------------------

            if path == "/api/chat":

                message = str(data.get("message", ""))

                response = kairo.respond(message)

                self.send_json({
                    "response": response
                })

                return

            # -------------------------
            # CREATE TASK
            # -------------------------

            if path == "/api/tasks":

                name = str(data.get("name", "")).strip()

                if not name:
                    self.send_json({
                        "error": "Task name is required."
                    }, 400)
                    return

                task = kairo.create_task(name)

                self.send_json({
                    "task": task
                }, 201)

                return

            self.send_json({
                "error": "Not Found",
                "path": path,
            }, 404)

        except json.JSONDecodeError:
            self.send_json({
                "error": "Invalid JSON."
            }, 400)

        except ValueError as error:
            self.send_json({
                "error": str(error)
            }, 400)

        except Exception as error:
            self.send_json({
                "error": f"Internal server error: {error}"
            }, 500)

    def serve_file(self, filename: str, content_type: str) -> None:
        path = WEB_ROOT / filename

        if not path.exists():
            self.send_json({
                "error": "File not found.",
                "file": filename,
            }, 404)
            return

        payload = path.read_bytes()

        self.send_response(200)
        self.send_header(
            "Content-Type",
            f"{content_type}; charset=utf-8"
        )
        self.send_header(
            "Content-Length",
            str(len(payload))
        )
        self.end_headers()

        self.wfile.write(payload)

    def log_message(self, format: str, *args) -> None:
        print(
            f"[KAIRO API] {self.address_string()} - "
            f"{format % args}"
        )


def main() -> None:
    host = "127.0.0.1"
    port = 8000

    server = HTTPServer((host, port), KairoHandler)

    print("================================")
    print("       KAIRO V1 API SERVER")
    print("================================")
    print(f"URL: http://{host}:{port}")
    print()
    print("API:")
    print("  GET  /api/status")
    print("  GET  /api/tasks")
    print("  POST /api/tasks")
    print("  GET  /api/events")
    print("  POST /api/chat")
    print()
    print("Press CTRL+C to stop.")
    print()

    try:
        server.serve_forever()

    except KeyboardInterrupt:
        print("\nKAIRO > Web server shutting down.")

    finally:
        server.server_close()


if __name__ == "__main__":
    main()