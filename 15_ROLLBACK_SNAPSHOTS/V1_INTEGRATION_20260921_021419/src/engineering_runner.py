"""KAIRO engineering runner."""

from __future__ import annotations

import hashlib
import json
import py_compile
import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

ENGINEERING_DIR = ROOT / "01_CORE" / "Engineering"
REPORT_DIR = ROOT / "10_DOCUMENTATION" / "Technical" / "Engineering"
SNAPSHOT_DIR = ROOT / "15_ROLLBACK_SNAPSHOTS"

PROTECTED_PATHS = (
    ROOT / "00_FOUNDATION",
    ROOT / "11_ARCHIVE" / "Original_Repositories",
    ROOT / "15_ROLLBACK_SNAPSHOTS",
)

REQUIRED_PATHS = (
    ROOT / "00_FOUNDATION",
    ROOT / "01_CORE",
    ROOT / "02_AGENTS",
    ROOT / "03_DATA",
    ROOT / "04_TOOLS",
    ROOT / "05_UI",
    ROOT / "06_SECURITY",
    ROOT / "07_RUNTIME",
    ROOT / "08_BUSINESS",
    ROOT / "09_INTELLIGENCE",
    ROOT / "10_INFRASTRUCTURE",
    ROOT / "10_DOCUMENTATION",
    ROOT / "11_ARCHIVE",
    ROOT / "15_ROLLBACK_SNAPSHOTS",
    ROOT / "src",
    ROOT / "tests",
)


def timestamp() -> str:
    return datetime.now().isoformat()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def is_protected(path: Path) -> bool:
    target = path.resolve()

    for protected in PROTECTED_PATHS:
        try:
            target.relative_to(protected.resolve())
            return True
        except ValueError:
            continue

    return False


def validate_required_paths() -> dict:
    missing = [
        relative(path)
        for path in REQUIRED_PATHS
        if not path.exists()
    ]

    return {
        "status": "PASS" if not missing else "FAIL",
        "missing": missing,
    }


def validate_runner() -> dict:
    files = [
        ENGINEERING_DIR / "engineering_runner.py",
        ENGINEERING_DIR / "__init__.py",
    ]

    missing = [
        relative(path)
        for path in files
        if not path.exists()
    ]

    failures = []

    for path in files:
        if not path.exists():
            continue

        try:
            py_compile.compile(
                str(path),
                doraise=True,
            )
        except Exception as exc:
            failures.append(
                {
                    "file": relative(path),
                    "error": str(exc),
                }
            )

    return {
        "status": (
            "PASS"
            if not missing and not failures
            else "FAIL"
        ),
        "missing": missing,
        "syntax_failures": failures,
    }


def validate_protected_paths() -> dict:
    missing = [
        relative(path)
        for path in PROTECTED_PATHS
        if not path.exists()
    ]

    violations = []

    for path in ENGINEERING_DIR.rglob("*"):
        if path.exists() and is_protected(path):
            violations.append(relative(path))

    return {
        "status": (
            "PASS"
            if not missing and not violations
            else "FAIL"
        ),
        "missing": missing,
        "violations": violations,
    }


def create_snapshot() -> dict:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination = SNAPSHOT_DIR / f"ENGINEERING_{stamp}"

    destination.mkdir(
        parents=True,
        exist_ok=True,
    )

    files = []

    if ENGINEERING_DIR.exists():
        for source in ENGINEERING_DIR.rglob("*"):
            if not source.is_file():
                continue

            if is_protected(source):
                continue

            target = (
                destination
                / source.relative_to(ENGINEERING_DIR)
            )

            target.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            shutil.copy2(source, target)

            files.append(
                {
                    "file": relative(source),
                    "sha256": hash_file(source),
                }
            )

    manifest = {
        "created_at": timestamp(),
        "files": files,
    }

    manifest_path = destination / "manifest.json"

    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
        ),
        encoding="utf-8",
    )

    return {
        "status": "PASS",
        "path": relative(destination),
        "files": len(files),
    }


def validate() -> dict:
    structure = validate_required_paths()
    runner = validate_runner()
    protection = validate_protected_paths()

    checks = (
        structure,
        runner,
        protection,
    )

    status = (
        "PASS"
        if all(
            check["status"] == "PASS"
            for check in checks
        )
        else "FAIL"
    )

    return {
        "status": status,
        "structure": structure,
        "runner": runner,
        "protection": protection,
    }


def execute() -> dict:
    started = timestamp()

    snapshot = create_snapshot()
    validation = validate()

    result = {
        "runner": "KAIRO Engineering Runner",
        "started_at": started,
        "completed_at": timestamp(),
        "snapshot": snapshot,
        "validation": validation,
        "status": validation["status"],
    }

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    report = REPORT_DIR / (
        "engineering_run_"
        + datetime.now().strftime("%Y%m%d_%H%M%S")
        + ".json"
    )

    report.write_text(
        json.dumps(
            result,
            indent=2,
        ),
        encoding="utf-8",
    )

    result["report"] = relative(report)

    return result


if __name__ == "__main__":
    result = execute()

    print(
        json.dumps(
            result,
            indent=2,
        )
    )

    raise SystemExit(
        0 if result["status"] == "PASS" else 1
    )
