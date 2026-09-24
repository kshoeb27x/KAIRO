from pathlib import Path
from datetime import datetime
import json
import subprocess
import sys
import time
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[1]

HOST = "127.0.0.1"
PORT = 8000
BASE = f"http://{HOST}:{PORT}"

print("=" * 70)
print("KAIRO LIVE API + UI VALIDATION V1")
print("=" * 70)

print()
print("SAFETY")
print("Localhost only         : YES")
print("External network       : DISABLED")
print("Dependency install     : DISABLED")
print("Deletion               : DISABLED")
print("Source repositories    : PROTECTED")
print("Frozen archive         : PROTECTED")
print()

results = {}
server = None


def check(name, fn):
    try:
        value = fn()
        results[name] = bool(value)
        print(
            f"{name:<34}: "
            + ("PASS" if value else "FAIL")
        )
        return bool(value)

    except Exception as exc:
        results[name] = False
        print(
            f"{name:<34}: FAIL | {exc}"
        )
        return False


def http_get(path):
    with urllib.request.urlopen(
        BASE + path,
        timeout=5
    ) as response:

        body = response.read().decode(
            "utf-8",
            errors="replace"
        )

        return response.status, body


def http_post(path, payload):
    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        BASE + path,
        data=data,
        headers={
            "Content-Type": "application/json"
        },
        method="POST",
    )

    with urllib.request.urlopen(
        request,
        timeout=5
    ) as response:

        body = response.read().decode(
            "utf-8",
            errors="replace"
        )

        return response.status, body


# ------------------------------------------------------------
# 1. FILE STRUCTURE
# ------------------------------------------------------------

check(
    "api_server_exists",
    lambda: (
        ROOT / "src" / "api" / "server.py"
    ).exists()
)

check(
    "ui_index_exists",
    lambda: (
        ROOT / "05_UI" / "Web" / "index.html"
    ).exists()
)

check(
    "ui_css_exists",
    lambda: (
        ROOT / "05_UI" / "Web" / "style.css"
    ).exists()
)

check(
    "ui_js_exists",
    lambda: (
        ROOT / "05_UI" / "Web" / "app.js"
    ).exists()
)


# ------------------------------------------------------------
# 2. START LOCAL API SERVER
# ------------------------------------------------------------

print()
print("Starting KAIRO local API server...")

server = subprocess.Popen(
    [
        sys.executable,
        "-m",
        "uvicorn",
        "src.api.server:app",
        "--host",
        HOST,
        "--port",
        str(PORT),
    ],
    cwd=str(ROOT),
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)

time.sleep(2)


# ------------------------------------------------------------
# 3. API STATUS
# ------------------------------------------------------------

status_body = ""


def status_check():
    global status_body

    code, body = http_get("/api/status")

    status_body = body

    data = json.loads(body)

    return (
        code == 200
        and isinstance(data, dict)
    )


check(
    "GET_api_status",
    status_check
)


# ------------------------------------------------------------
# 4. STATUS CONTENT
# ------------------------------------------------------------

def status_content_check():

    data = json.loads(status_body)

    return (
        data.get("system") == "KAIRO"
        and data.get("version") == "V1"
    )


check(
    "api_status_content",
    status_content_check
)


# ------------------------------------------------------------
# 5. TASK LIST
# ------------------------------------------------------------

def tasks_get_check():

    code, body = http_get("/api/tasks")

    data = json.loads(body)

    return (
        code == 200
        and isinstance(data, list)
    )


check(
    "GET_api_tasks",
    tasks_get_check
)


# ------------------------------------------------------------
# 6. EVENT LIST
# ------------------------------------------------------------

def events_get_check():

    code, body = http_get("/api/events")

    data = json.loads(body)

    return (
        code == 200
        and isinstance(data, list)
    )


check(
    "GET_api_events",
    events_get_check
)


# ------------------------------------------------------------
# 7. CREATE TASK
# ------------------------------------------------------------

created_task = {}


def task_create_check():

    global created_task

    code, body = http_post(
        "/api/tasks",
        {
            "name":
                "KAIRO_LIVE_API_VALIDATION"
        },
    )

    data = json.loads(body)

    created_task = data

    return (
        code in {200, 201}
        and isinstance(data, dict)
        and data.get("name")
        == "KAIRO_LIVE_API_VALIDATION"
    )


check(
    "POST_api_tasks",
    task_create_check
)


# ------------------------------------------------------------
# 8. VERIFY TASK
# ------------------------------------------------------------

def task_persisted_check():

    code, body = http_get("/api/tasks")

    data = json.loads(body)

    if not isinstance(data, list):
        return False

    return any(
        isinstance(task, dict)
        and task.get("name")
        == "KAIRO_LIVE_API_VALIDATION"
        for task in data
    )


check(
    "task_persisted_through_api",
    task_persisted_check
)


# ------------------------------------------------------------
# 9. VERIFY EVENT
# ------------------------------------------------------------

def task_event_check():

    code, body = http_get("/api/events")

    data = json.loads(body)

    if not isinstance(data, list):
        return False

    return any(
        isinstance(event, dict)
        and event.get("type")
        == "TASK_CREATED"
        for event in data
    )


check(
    "task_event_through_api",
    task_event_check
)


# ------------------------------------------------------------
# 10. CHAT ENDPOINT
# ------------------------------------------------------------

def chat_check():

    code, body = http_post(
        "/api/chat",
        {
            "message": "status"
        },
    )

    data = json.loads(body)

    return (
        code == 200
        and isinstance(data, dict)
        and (
            "response" in data
            or "message" in data
        )
    )


check(
    "POST_api_chat",
    chat_check
)


# ------------------------------------------------------------
# 11. UI SERVING
# ------------------------------------------------------------

def ui_check():

    code, body = http_get("/")

    return (
        code == 200
        and "KAIRO" in body
    )


check(
    "GET_ui_index",
    ui_check
)


# ------------------------------------------------------------
# 12. STATIC UI ASSETS
# ------------------------------------------------------------

def css_check():

    code, body = http_get("/style.css")

    return (
        code == 200
        and len(body) > 0
    )


check(
    "GET_ui_css",
    css_check
)


def js_check():

    code, body = http_get("/app.js")

    return (
        code == 200
        and len(body) > 0
    )


check(
    "GET_ui_javascript",
    js_check
)


# ------------------------------------------------------------
# 13. API SERVER HEALTH
# ------------------------------------------------------------

def server_health_check():

    code, body = http_get("/api/status")

    return code == 200


check(
    "api_server_health",
    server_health_check
)


# ------------------------------------------------------------
# 14. FINAL STATUS
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
# STOP SERVER
# ------------------------------------------------------------

if server is not None:

    try:
        server.terminate()
        server.wait(timeout=5)

    except Exception:

        try:
            server.kill()
        except Exception:
            pass


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
        "KAIRO_LIVE_API_UI_VALIDATION",

    "generated_at":
        datetime.now().isoformat(
            timespec="seconds"
        ),

    "host":
        HOST,

    "port":
        PORT,

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

    "safety": {
        "external_network": False,
        "dependency_installation": False,
        "deletion": False,
        "source_modified": False,
        "archive_modified": False,
    },
}

(
    report_dir /
    "KAIRO_LIVE_API_UI_VALIDATION.json"
).write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)


print()
print("=" * 70)
print("KAIRO LIVE API + UI VALIDATION COMPLETE")
print("=" * 70)

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
    print("NEXT: FIX API/UI FAILURES")

print("=" * 70)

