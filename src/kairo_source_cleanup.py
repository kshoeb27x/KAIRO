from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
SNAPSHOT_ROOT = PROJECT_ROOT / "15_ROLLBACK_SNAPSHOTS"

STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
SNAPSHOT = SNAPSHOT_ROOT / f"SOURCE_CLEAN_{STAMP}"


# Actual runtime files.
# __init__.py is NOT mandatory.
KEEP = {
    "__main__.py",
    "main.py",
    "kairo.py",
    "policy.py",
    "engineering_runner.py",
}


# Historical construction / audit / validation tooling.
REMOVE = {
    "agent_platform_build.py",
    "command_center_build.py",
    "command_center_live_check.py",
    "core_v2_build.py",
    "data_system_build.py",
    "data_system_live_check.py",
    "kairo_current_state.py",
    "kairo_master_consolidation.py",
    "kairo_state.py",
    "kairo_structure.txt",
    "kairo_v1_integration_build.py",
    "runtime_v2_build.py",
    "runtime_v2_live_check.py",
    "security_system_build.py",
    "security_system_live_check.py",
    "tool_system_build.py",
    "tool_system_live_check.py",
    "capability_mapper.py",
    "component_scanner.py",
    "project_discovery.py",
    "repo_auditor.py",
    "repo_deep_auditor.py",
}


def rel(path: Path) -> str:
    try:
        return str(
            path.resolve().relative_to(PROJECT_ROOT.resolve())
        )
    except Exception:
        return str(path)


def is_protected(path: Path) -> bool:
    target = path.resolve()

    protected_roots = [
        PROJECT_ROOT / "00_FOUNDATION",
        PROJECT_ROOT / "11_ARCHIVE",
        PROJECT_ROOT / "15_ROLLBACK_SNAPSHOTS",
    ]

    for root in protected_roots:
        root = root.resolve()

        if target == root:
            return True

        try:
            target.relative_to(root)
            return True
        except ValueError:
            pass

    return False


def snapshot_file(source: Path) -> None:
    destination = SNAPSHOT / source.name
    SNAPSHOT.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def main() -> int:

    print("=" * 70)
    print("KAIRO SOURCE CLEANUP")
    print("=" * 70)

    if not SRC_ROOT.exists():
        print("ERROR: src directory not found.")
        return 1

    SNAPSHOT.mkdir(parents=True, exist_ok=True)

    report = {
        "runner": "KAIRO Source Cleanup",
        "started_at": datetime.now().isoformat(),
        "snapshot": rel(SNAPSHOT),
        "removed": [],
        "already_missing": [],
        "kept": [],
        "errors": [],
    }

    # --------------------------------------------------------
    # Snapshot all files that actually exist and are targeted.
    # --------------------------------------------------------

    print()
    print("Preparing rollback snapshot...")

    for name in sorted(REMOVE):

        source = SRC_ROOT / name

        if not source.exists():
            report["already_missing"].append(name)
            continue

        if not source.is_file():
            report["errors"].append({
                "file": rel(source),
                "stage": "snapshot",
                "error": "Target exists but is not a file",
            })
            continue

        if is_protected(source):
            report["errors"].append({
                "file": rel(source),
                "stage": "snapshot",
                "error": "Protected path",
            })
            continue

        try:
            snapshot_file(source)

        except Exception as exc:
            report["errors"].append({
                "file": rel(source),
                "stage": "snapshot",
                "error": str(exc),
            })

    # Never delete anything if snapshot preparation failed.
    if report["errors"]:

        report["status"] = "FAIL"
        report["completed_at"] = datetime.now().isoformat()

        (SNAPSHOT / "cleanup_report.json").write_text(
            json.dumps(report, indent=2),
            encoding="utf-8",
        )

        print()
        print("SNAPSHOT FAILED — NO FILES DELETED")
        print()

        for error in report["errors"]:
            print(
                f"ERROR: {error['file']} -> "
                f"{error['error']}"
            )

        print()
        print(f"Snapshot: {SNAPSHOT}")

        return 1

    # --------------------------------------------------------
    # Delete obsolete source tooling.
    # --------------------------------------------------------

    print()
    print("Removing obsolete source tooling...")

    for name in sorted(REMOVE):

        source = SRC_ROOT / name

        if not source.exists():
            continue

        try:
            source.unlink()
            report["removed"].append(name)

            print(f"REMOVED: src\\{name}")

        except Exception as exc:

            report["errors"].append({
                "file": rel(source),
                "stage": "delete",
                "error": str(exc),
            })

    # --------------------------------------------------------
    # Verify actual runtime files.
    # --------------------------------------------------------

    print()
    print("Validating runtime source...")

    for name in sorted(KEEP):

        path = SRC_ROOT / name

        if path.exists() and path.is_file():
            report["kept"].append(name)
            print(f"KEEP: src\\{name}")

        else:
            # These are expected runtime candidates, but don't
            # invent a failure if the project does not currently
            # use one of them.
            print(f"OPTIONAL/MISSING: src\\{name}")

    # --------------------------------------------------------
    # Final validation.
    # --------------------------------------------------------

    report["completed_at"] = datetime.now().isoformat()

    if report["errors"]:
        report["status"] = "FAIL"
    else:
        report["status"] = "PASS"

    report_path = SNAPSHOT / "cleanup_report.json"

    report_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print()
    print("=" * 70)
    print(f"KAIRO SOURCE CLEANUP: {report['status']}")
    print("=" * 70)

    print(f"Removed:         {len(report['removed'])}")
    print(f"Already missing: {len(report['already_missing'])}")
    print(f"Kept:            {len(report['kept'])}")
    print(f"Errors:          {len(report['errors'])}")
    print(f"Snapshot:        {SNAPSHOT}")
    print(f"Report:          {report_path}")

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())