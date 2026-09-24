from __future__ import annotations

from pathlib import Path
from datetime import datetime
from http.server import HTTPServer
import json
import sys
import threading
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

print("=" * 72)
print("KAIRO LIVE API + UI VALIDATION V2")
print("=" * 72)

print()
print("SAFETY")
print("Real KAIRO HTTPServer  : YES")
print("Localhost only         : YES")
print("External network       : NO")
print("Dependency install     : NO")
print("Deletion               : NO")
print("Source repositories    : PROTECTED")
print("Frozen archive         : PROTECTED")
print()

results = {}


def check(name, fn):
    try:
        value = fn()
        results[name] = bool(value)

        print(
            f"{name:<38}: "
            + ("PASS" if value else "FAIL")
        )

        return bool(value)

    except Exception as exc:

        results[name] = False

        print(
            f"{name:<38}: FAIL | {exc}"
        )

        return False


# ------------------------------------------------------------
# IMPORT REAL KAIRO HTTP SERVER
# ------------------------------------------------------------

server = None
thread = None
base_url = None

try:

    from src.api.server import KairoHandler

    # Bind to an automatically selected localhost port.
    server = HTTPServer(
        ("127.0.0.1", 0),
        KairoHandler
    )

    host, port = server.server_address

    base_url = f"http://{host}:{port}"

    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True
    )

    thread.start()

    print(
        f"Local validation server: {base_url}"
    )

except Exception as exc:

    print(
        f"SERVER START FAILED: {exc}"
    )


# ------------------------------------------------------------
# HTTP HELPERS
# ------------------------------------------------------------

def get_json(path):

    with urllib.request.urlopen(
        base_url + path,
        timeout=5
    ) as response:

        body = response.read().decode(
            "utf-8",
            errors="replace"
        )

        return (
            response.status,
            json.loads(body)
        )


def post_json(path, payload):

    body = json.dumps(payload).encode(
        "utf-8"
    )

    request = urllib.request.Request(
        base_url + path,
        data=body,
        headers={
            "Content-Type":
                "application/json"
        },
        method="POST"
    )

    with urllib.request.urlopen(
        request,
        timeout=5
    ) as response:

        raw = response.read().decode(
            "utf-8",
            errors="replace"
        )

        return (
            response.status,
            json.loads(raw)
        )


# ------------------------------------------------------------
# FILE CHECKS
# ------------------------------------------------------------

check(
    "api_server_exists",
    lambda:
        (
            ROOT /
            "src" /
            "api" /
            "server.py"
        ).exists()
)

check(
    "ui_index_exists",
    lambda:
        (
            ROOT /
            "05_UI" /
            "Web" /
            "index.html"
        ).exists()
)

check(
    "ui_css_exists",
    lambda:
        (
            ROOT /
            "05_UI" /
            "Web" /
            "style.css"
        ).exists()
)

check(
    "ui_js_exists",
    lambda:
        (
            ROOT /
            "05_UI" /
            "Web" /
            "app.js"
        ).exists()
)


# ------------------------------------------------------------
# SERVER
# ------------------------------------------------------------

check(
    "http_server_started",
    lambda:
        server is not None
        and thread is not None
        and thread.is_alive()
)


# ------------------------------------------------------------
# GET STATUS
# ------------------------------------------------------------

status_data = {}


def test_status():

    global status_data

    code, data = get_json(
        "/api/status"
    )

    status_data = data

    return (
        code == 200
        and isinstance(data, dict)
    )


check(
    "GET_api_status",
    test_status
)


check(
    "status_system_KAIRO",
    lambda:
        status_data.get("system")
        == "KAIRO"
)


check(
    "status_core_online",
    lambda:
        status_data.get("core")
        == "ONLINE"
)


check(
    "status_runtime_online",
    lambda:
        status_data.get("runtime")
        == "ONLINE"
)


# ------------------------------------------------------------
# GET TASKS
# ------------------------------------------------------------

tasks_before = {}


def test_tasks_get():

    global tasks_before

    code, data = get_json(
        "/api/tasks"
    )

    tasks_before = data

    return (
        code == 200
        and isinstance(data, dict)
        and isinstance(
            data.get("tasks"),
            list
        )
    )


check(
    "GET_api_tasks",
    test_tasks_get
)


# ------------------------------------------------------------
# GET EVENTS
# ------------------------------------------------------------

events_before = {}


def test_events_get():

    global events_before

    code, data = get_json(
        "/api/events"
    )

    events_before = data

    return (
        code == 200
        and isinstance(data, dict)
        and isinstance(
            data.get("events"),
            list
        )
    )


check(
    "GET_api_events",
    test_events_get
)


# ------------------------------------------------------------
# POST TASK
# ------------------------------------------------------------

created_task = {}


def test_task_post():

    global created_task

    code, data = post_json(
        "/api/tasks",
        {
            "name":
                "KAIRO_LIVE_API_V2_TEST"
        }
    )

    created_task = data

    return (
        code == 201
        and isinstance(data, dict)
        and isinstance(
            data.get("task"),
            dict
        )
        and data["task"].get("name")
        == "KAIRO_LIVE_API_V2_TEST"
    )


check(
    "POST_api_tasks",
    test_task_post
)


# ------------------------------------------------------------
# TASK PERSISTENCE
# ------------------------------------------------------------

def test_task_persistence():

    code, data = get_json(
        "/api/tasks"
    )

    if code != 200:
        return False

    tasks = data.get("tasks", [])

    return any(
        isinstance(task, dict)
        and task.get("name")
        == "KAIRO_LIVE_API_V2_TEST"
        for task in tasks
    )


check(
    "task_persisted_through_api",
    test_task_persistence
)


# ------------------------------------------------------------
# EVENT PERSISTENCE
# ------------------------------------------------------------

def test_task_event():

    code, data = get_json(
        "/api/events"
    )

    if code != 200:
        return False

    events = data.get("events", [])

    return any(
        isinstance(event, dict)
        and event.get("type")
        == "TASK_CREATED"
        for event in events
    )


check(
    "TASK_CREATED_event",
    test_task_event
)


# ------------------------------------------------------------
# CHAT
# ------------------------------------------------------------

chat_data = {}


def test_chat():

    global chat_data

    code, data = post_json(
        "/api/chat",
        {
            "message":
                "status"
        }
    )

    chat_data = data

    return (
        code == 200
        and isinstance(data, dict)
        and isinstance(
            data.get("response"),
            str
        )
        and "KAIRO V1" in
            data.get("response", "")
    )


check(
    "POST_api_chat",
    test_chat
)


# ------------------------------------------------------------
# UI INDEX
# ------------------------------------------------------------

def test_ui_index():

    with urllib.request.urlopen(
        base_url + "/",
        timeout=5
    ) as response:

        body = response.read().decode(
            "utf-8",
            errors="replace"
        )

        return (
            response.status == 200
            and "KAIRO" in body
        )


check(
    "GET_ui_index",
    test_ui_index
)


# ------------------------------------------------------------
# CSS
# ------------------------------------------------------------

def test_css():

    with urllib.request.urlopen(
        base_url + "/style.css",
        timeout=5
    ) as response:

        body = response.read().decode(
            "utf-8",
            errors="replace"
        )

        return (
            response.status == 200
            and len(body) > 0
        )


check(
    "GET_ui_css",
    test_css
)


# ------------------------------------------------------------
# JAVASCRIPT
# ------------------------------------------------------------

def test_js():

    with urllib.request.urlopen(
        base_url + "/app.js",
        timeout=5
    ) as response:

        body = response.read().decode(
            "utf-8",
            errors="replace"
        )

        return (
            response.status == 200
            and len(body) > 0
        )


check(
    "GET_ui_javascript",
    test_js
)


# ------------------------------------------------------------
# 404 HANDLING
# ------------------------------------------------------------

def test_404():

    try:

        urllib.request.urlopen(
            base_url +
            "/api/does-not-exist",
            timeout=5
        )

        return False

    except urllib.error.HTTPError as error:

        return error.code == 404


check(
    "api_404_handling",
    test_404
)


# ------------------------------------------------------------
# SHUTDOWN
# ------------------------------------------------------------

if server is not None:

    server.shutdown()
    server.server_close()

if thread is not None:

    thread.join(timeout=5)


# ------------------------------------------------------------
# FINAL
# ------------------------------------------------------------

passed = sum(
    1
    for value in results.values()
    if value
)

failed = sum(
    1
    for value in results.values()
    if not value
)

overall = failed == 0


# ------------------------------------------------------------
# REPORT
# ------------------------------------------------------------

report_dir = (
    ROOT /
    "18_LIVE_API_UI_VALIDATION"
)

report_dir.mkdir(
    parents=True,
    exist_ok=True
)

report = {
    "type":
        "KAIRO_LIVE_API_UI_VALIDATION_V2",

    "generated_at":
        datetime.now().isoformat(
            timespec="seconds"
        ),

    "checks":
        results,

    "passed":
        passed,

    "failed":
        failed,

    "status":
        "PASS"
        if overall
        else "REVIEW_REQUIRED",

    "architecture": {
        "server":
            "Python HTTPServer",

        "handler":
            "KairoHandler",

        "external_network":
            False,

        "localhost":
            True,
    },

    "safety": {
        "deletion": False,
        "dependency_installation": False,
        "source_modified": False,
        "archive_modified": False,
    }
}

(
    report_dir /
    "KAIRO_LIVE_API_UI_VALIDATION_V2.json"
).write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)


print()
print("=" * 72)
print("KAIRO LIVE API + UI VALIDATION V2 COMPLETE")
print("=" * 72)

print(
    f"Checks passed : {passed}"
)

print(
    f"Checks failed : {failed}"
)

print()
print("External network       : NOT USED")
print("Dependency installation: NONE")
print("Deletion               : NONE")
print("Source modified        : NO")
print("Archive modified       : NO")

print()

if overall:

    print("STATUS: PASS")
    print("NEXT: FINAL CLEANUP + ARCHITECTURE HARDENING")

else:

    print("STATUS: REVIEW_REQUIRED")
    print("NEXT: FIX FAILED CHECKS")

print("=" * 72)

