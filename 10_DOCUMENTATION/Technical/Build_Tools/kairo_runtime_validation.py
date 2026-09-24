from pathlib import Path
from datetime import datetime
import json
import sys
import importlib.util

ROOT = Path(__file__).resolve().parents[1]

print("=" * 70)
print("KAIRO RUNTIME VALIDATION V1")
print("=" * 70)

print()
print("SAFETY")
print("Code execution        : CONTROLLED")
print("Dependency install    : DISABLED")
print("Network               : NOT USED")
print("Deletion              : DISABLED")
print("Source repositories   : PROTECTED")
print("Frozen archive        : PROTECTED")
print()

results = {}

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


# ------------------------------------------------------------
# 1. CORE IMPORT
# ------------------------------------------------------------

src_path = ROOT / "src"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

check(
    "src_package_exists",
    lambda: src_path.exists()
)

check(
    "kairo_core_exists",
    lambda: (
        ROOT / "src" / "core" / "kairo_core.py"
    ).exists()
)

check(
    "runtime_controller_exists",
    lambda: (
        ROOT / "src" / "core" /
        "runtime_controller.py"
    ).exists()
)

# ------------------------------------------------------------
# 2. CORE INITIALIZATION
# ------------------------------------------------------------

core = None

def create_core():
    global core

    from src.core.kairo_core import KairoCore

    core = KairoCore()

    return core is not None


check(
    "kairo_core_initialization",
    create_core
)

# ------------------------------------------------------------
# 3. STATUS
# ------------------------------------------------------------

def status_check():

    if core is None:
        return False

    status = core.status()

    return (
        status.get("core") == "ONLINE"
        and status.get("runtime") == "ONLINE"
    )


check(
    "core_runtime_online",
    status_check
)

# ------------------------------------------------------------
# 4. SECURITY
# ------------------------------------------------------------

def security_check():

    status = core.status()

    return (
        status.get("security")
        in {"ACTIVE", "ONLINE"}
    )


check(
    "security_state_active",
    security_check
)

# ------------------------------------------------------------
# 5. DATA / NETWORK STATE
# ------------------------------------------------------------

def data_check():

    status = core.status()

    return status.get("data") in {
        "READY",
        "ONLINE",
        "ACTIVE",
    }


check(
    "data_state_ready",
    data_check
)


def network_check():

    status = core.status()

    return status.get("network") in {
        "RESTRICTED",
        "OFF",
        "DISABLED",
        "ONLINE",
    }


check(
    "network_state_defined",
    network_check
)

# ------------------------------------------------------------
# 6. TASK ENGINE
# ------------------------------------------------------------

task = None

def task_check():

    global task

    task = core.create_task(
        "KAIRO_RUNTIME_VALIDATION"
    )

    return (
        isinstance(task, dict)
        and "id" in task
        and task.get("name")
        == "KAIRO_RUNTIME_VALIDATION"
    )


check(
    "task_creation",
    task_check
)

# ------------------------------------------------------------
# 7. EVENT ENGINE
# ------------------------------------------------------------

def event_check():

    events = core.events(
        limit=20
    )

    if not isinstance(events, list):
        return False

    return any(
        e.get("type")
        == "TASK_CREATED"
        for e in events
        if isinstance(e, dict)
    )


check(
    "task_event_emission",
    event_check
)

# ------------------------------------------------------------
# 8. API FILE
# ------------------------------------------------------------

check(
    "api_server_exists",
    lambda: (
        ROOT / "src" / "api" / "server.py"
    ).exists()
)

# ------------------------------------------------------------
# 9. UI
# ------------------------------------------------------------

ui_files = [
    ROOT / "05_UI" / "Web" / "index.html",
    ROOT / "05_UI" / "Web" / "style.css",
    ROOT / "05_UI" / "Web" / "app.js",
]

for path in ui_files:

    check(
        f"ui_{path.name}_exists",
        lambda p=path: p.exists()
    )

# ------------------------------------------------------------
# 10. RUNTIME MODULES
# ------------------------------------------------------------

runtime_files = [
    ROOT / "07_RUNTIME" /
    "State" / "runtime_state.py",

    ROOT / "07_RUNTIME" /
    "Events" / "event_bus.py",

    ROOT / "07_RUNTIME" /
    "Task_Manager" / "task_manager.py",
]

for path in runtime_files:

    check(
        f"runtime_{path.name}_exists",
        lambda p=path: p.exists()
    )

# ------------------------------------------------------------
# 11. STATUS SNAPSHOT
# ------------------------------------------------------------

status = {}

if core is not None:

    try:
        status = core.status()

        print()
        print("KAIRO STATUS")
        print(
            json.dumps(
                status,
                indent=2,
                default=str
            )
        )

    except Exception as exc:

        results[
            "status_snapshot"
        ] = False

        print(
            f"status_snapshot{'':<19}: "
            f"FAIL | {exc}"
        )

# ------------------------------------------------------------
# 12. FINAL RESULT
# ------------------------------------------------------------

passed = sum(
    1 for value in results.values()
    if value
)

failed = sum(
    1 for value in results.values()
    if not value
)

overall = failed == 0

report_dir = (
    ROOT /
    "17_RUNTIME_VALIDATION"
)

report_dir.mkdir(
    parents=True,
    exist_ok=True
)

report = {
    "type":
        "KAIRO_RUNTIME_VALIDATION",

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

    "safety": {
        "deletion": False,
        "dependency_installation": False,
        "network": False,
        "source_modified": False,
        "archive_modified": False,
    },

    "kairo_status":
        status,
}

(
    report_dir /
    "KAIRO_RUNTIME_VALIDATION.json"
).write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False,
        default=str
    ),
    encoding="utf-8"
)

print()
print("=" * 70)
print("KAIRO RUNTIME VALIDATION COMPLETE")
print("=" * 70)

print(
    f"Checks passed : {passed}"
)

print(
    f"Checks failed : {failed}"
)

print()
print("Deletion              : NONE")
print("Dependencies installed: NONE")
print("Network               : NOT USED")
print("Source modified       : NO")
print("Archive modified      : NO")

print()

if overall:

    print("STATUS: PASS")
    print("NEXT: KAIRO LIVE API + UI VALIDATION")

else:

    print("STATUS: REVIEW_REQUIRED")
    print("NEXT: FIX RUNTIME FAILURES")

print("=" * 70)


