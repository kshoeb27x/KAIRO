from __future__ import annotations

from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import sys
from uuid import uuid4
from urllib.parse import parse_qs, urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = PROJECT_ROOT / "05_UI" / "Web"

sys.path.insert(0, str(PROJECT_ROOT))

from src.kairo_system import KairoSystem


kairo = KairoSystem()


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

        data = json.loads(body.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("JSON request body must be an object.")
        return data

    def authorize_api(self, permission: str, operation: str, resource: str):
        authorization = self.headers.get("Authorization", "")
        scheme, _, token = authorization.partition(" ")
        correlation_id = (
            self.headers.get("X-Request-ID", "").strip()
            or uuid4().hex
        )
        context = kairo.authenticate_api_token(
            token if scheme.lower() == "bearer" else None,
            permission,
            operation,
            resource,
            correlation_id,
        )
        if context is None:
            kairo.security.audit.record(
                "AUTHENTICATION",
                None,
                operation,
                "DENY",
                {
                    "resource": resource,
                    "permission": permission,
                    "correlation_id": correlation_id,
                    "reason": "INVALID_OR_MISSING_BEARER_TOKEN",
                },
            )
            self.send_json({"error": "Authentication required."}, 401)
            return None
        decision = kairo.security.authorize_context(context, permission)
        if not decision.allowed:
            kairo.security.audit_execution(
                context,
                decision.decision,
                decision.reason,
            )
            self.send_json(
                {"error": "Forbidden.", "request_id": correlation_id},
                403,
            )
            return None
        return context

    def do_GET(self) -> None:
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        # -------------------------
        # KAIRO API
        # -------------------------

        if path == "/api/status":
            context = self.authorize_api(
                "api.status.read",
                "api.status.read",
                "system",
            )
            if context is None:
                return
            self.send_json(kairo.status())
            kairo.security.audit_execution(context, "COMPLETED")
            return

        if path == "/api/engineering":
            context = self.authorize_api(
                "api.status.read",
                "api.engineering.status",
                "engineering",
            )
            if context is None:
                return
            self.send_json(kairo.engineering_health())
            kairo.security.audit_execution(context, "COMPLETED")
            return

        if path == "/api/tasks":
            context = self.authorize_api(
                "api.tasks.read",
                "api.tasks.read",
                "tasks",
            )
            if context is None:
                return
            self.send_json({
                "tasks": kairo.runtime.tasks.list_tasks(
                    context.derive(
                        permission="runtime.task.read",
                        operation="task.list",
                        resource="tasks",
                    )
                )
            })
            kairo.security.audit_execution(context, "COMPLETED")
            return

        if path == "/api/events":
            context = self.authorize_api(
                "api.events.read",
                "api.events.read",
                "events",
            )
            if context is None:
                return
            self.send_json({
                "events": kairo.events()
            })
            kairo.security.audit_execution(context, "COMPLETED")
            return

        if path == "/api/memory":
            context = self.authorize_api(
                "api.memory.read",
                "api.memory.read",
                "memory",
            )
            if context is None:
                return
            query = parse_qs(parsed_path.query)
            search = query.get("q", [""])[0].strip()
            if not search:
                self.send_json(
                    {"error": "Memory search query is required."},
                    400,
                )
                return
            try:
                limit = int(query.get("limit", ["10"])[0])
            except ValueError:
                self.send_json(
                    {"error": "Memory limit must be an integer."},
                    400,
                )
                return
            if limit < 1 or limit > 100:
                self.send_json(
                    {"error": "Memory limit must be between 1 and 100."},
                    400,
                )
                return

            records = kairo.recall(
                search,
                context,
                scope=context.caller_identity,
                limit=limit,
            )
            self.send_json({
                "memories": [asdict(record) for record in records],
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

            if path == "/api/runtime/emergency-stop":
                context = self.authorize_api(
                    "api.runtime.control",
                    "api.runtime.emergency_stop",
                    "runtime",
                )
                if context is None:
                    return
                kairo.emergency_stop(context)
                kairo.security.audit_execution(
                    context,
                    "STOPPED",
                )
                self.send_json(
                    {"status": "EMERGENCY_STOP"},
                    202,
                )
                return

            # -------------------------
            # CHAT
            # -------------------------

            if path == "/api/chat":
                context = self.authorize_api(
                    "api.chat",
                    "api.chat",
                    "orchestrator",
                )
                if context is None:
                    return

                message = str(data.get("message", ""))

                response = kairo.respond(message, context)
                kairo.security.audit_execution(context, "COMPLETED")

                self.send_json({
                    "response": response
                })

                return

            # -------------------------
            # CREATE TASK
            # -------------------------

            if path == "/api/tasks":
                context = self.authorize_api(
                    "api.tasks.create",
                    "api.tasks.create",
                    "tasks",
                )
                if context is None:
                    return

                name = str(data.get("name", "")).strip()

                if not name:
                    self.send_json({
                        "error": "Task name is required."
                    }, 400)
                    return

                task = kairo.create_task(name, context)
                kairo.security.audit_execution(context, "CREATED")

                self.send_json({
                    "task": task
                }, 201)

                return

            if path == "/api/memory":
                context = self.authorize_api(
                    "api.memory.write",
                    "api.memory.write",
                    "memory",
                )
                if context is None:
                    return
                content = data.get("content")
                metadata = data.get("metadata", {})
                if not isinstance(content, str) or not content.strip():
                    self.send_json(
                        {"error": "Memory content is required."},
                        400,
                    )
                    return
                if not isinstance(metadata, dict):
                    self.send_json(
                        {"error": "Memory metadata must be an object."},
                        400,
                    )
                    return

                record = kairo.remember(
                    content,
                    context,
                    scope=context.caller_identity,
                    metadata=metadata,
                )
                self.send_json({
                    "memory": asdict(record),
                }, 201)
                return

            path_parts = path.strip("/").split("/")
            if (
                len(path_parts) == 4
                and path_parts[:2] == ["api", "agents"]
                and path_parts[3] == "execute"
            ):
                agent_name = path_parts[2]
                context = self.authorize_api(
                    "api.agents.execute",
                    "api.agents.execute",
                    agent_name,
                )
                if context is None:
                    return
                task = data.get("task")
                if not isinstance(task, str) or not task.strip():
                    self.send_json(
                        {"error": "Agent task is required."},
                        400,
                    )
                    return

                result = kairo.execute_agent(
                    agent_name,
                    task,
                    context,
                )
                result_status = (
                    200
                    if result.status == "COMPLETED"
                    else 503
                    if result.status == "UNAVAILABLE"
                    else 403
                    if result.status in {"DENIED", "REQUIRES_APPROVAL"}
                    else 503
                    if result.status == "BLOCKED_EXTERNAL"
                    else 500
                )
                kairo.security.audit_execution(
                    context,
                    result.status,
                )
                self.send_json({
                    "result": result.__dict__,
                }, result_status)
                return

            if (
                len(path_parts) == 4
                and path_parts[:2] == ["api", "tools"]
            ):
                tool_name, action = path_parts[2], path_parts[3]
                context = self.authorize_api(
                    "api.tools.execute",
                    "api.tools.execute",
                    tool_name,
                )
                if context is None:
                    return
                arguments = data.get("arguments", {})
                if not isinstance(arguments, dict):
                    self.send_json(
                        {"error": "Tool arguments must be an object."},
                        400,
                    )
                    return

                result = kairo.execute_tool(
                    tool_name,
                    action,
                    arguments,
                    context,
                )
                if result.status == "DENIED":
                    self.send_json(
                        {"error": result.error or "Forbidden."},
                        403,
                    )
                    return
                result_status = (
                    200
                    if result.status == "COMPLETED"
                    else 500
                )
                kairo.security.audit_execution(
                    context,
                    result.status,
                    result.error,
                )
                self.send_json({
                    "result": result.__dict__,
                }, result_status)
                return

            self.send_json({
                "error": "Not Found",
                "path": path,
            }, 404)

        except json.JSONDecodeError:
            self.send_json({
                "error": "Invalid JSON."
            }, 400)

        except PermissionError:
            self.send_json({
                "error": "Forbidden."
            }, 403)

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
    print("  GET  /api/memory")
    print("  POST /api/memory")
    print("  POST /api/agents/{name}/execute")
    print("  POST /api/tools/{name}/{action}")
    print("  POST /api/runtime/emergency-stop")
    print()
    print("Press CTRL+C to stop.")
    print()

    try:
        server.serve_forever()

    except KeyboardInterrupt:
        print("\nKAIRO > Web server shutting down.")

    finally:
        server.server_close()
        kairo.close()


if __name__ == "__main__":
    main()