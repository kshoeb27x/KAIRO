from __future__ import annotations

import hashlib
import json
import os
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path


# ============================================================
# KAIRO CLEAN REBUILD
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_ROOT = PROJECT_ROOT / "15_ROLLBACK_SNAPSHOTS"
DOC_ROOT = PROJECT_ROOT / "10_DOCUMENTATION"

STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

SNAPSHOT_DIR = SNAPSHOT_ROOT / f"CLEAN_{STAMP}"
REPORT_DIR = DOC_ROOT / "Technical" / "Cleanup"
REPORT_FILE = REPORT_DIR / f"kairo_clean_{STAMP}.json"


# ============================================================
# PROTECTED AREAS
# ============================================================

PROTECTED_PATHS = [
    PROJECT_ROOT / "00_FOUNDATION",
    PROJECT_ROOT / "11_ARCHIVE",
    PROJECT_ROOT / "15_ROLLBACK_SNAPSHOTS",
]


# ============================================================
# CURRENT KAIRO AREAS
#
# These are expected active areas.
# 09_INTELLIGENCE and 10_INFRASTRUCTURE are NOT forced to
# exist because they are not currently required for V1.
# ============================================================

ACTIVE_ROOTS = [
    "01_CORE",
    "02_AGENTS",
    "03_DATA",
    "04_TOOLS",
    "05_UI",
    "06_SECURITY",
    "07_RUNTIME",
    "08_BUSINESS",
    "10_DOCUMENTATION",
    "19_ARCHITECTURE",
    "config",
    "scripts",
    "src",
    "tests",
]


# ============================================================
# KNOWN OBSOLETE MATERIAL
# ============================================================

OBSOLETE_DIRECTORIES = [
    "12_EXTRACTION",
    "13_FINAL_KAIRO",
    "14_FINAL_KAIRO",
    "14_KAIRO_PRODUCTION_CANDIDATE",
    "16_POST_MERGE_VALIDATION",
    "17_RUNTIME_VALIDATION",
    "18_LIVE_API_UI_VALIDATION",

    # Previous cleanup/audit staging material.
    "19_CLEANUP_AUDIT",
    "99_CLEANUP_REPORT",
    "99_DEEP_SCAN_REPORT",
]


# ============================================================
# SAFE TEMPORARY FILES
# ============================================================

SAFE_TEMP_NAMES = {
    ".DS_Store",
    "Thumbs.db",
}

SAFE_TEMP_SUFFIXES = {
    ".tmp",
    ".bak",
    ".old",
    ".orig",
}


# ============================================================
# HELPERS
# ============================================================

def now_iso() -> str:
    return datetime.now().isoformat()


def relative(path: Path) -> str:
    try:
        return str(
            path.resolve().relative_to(PROJECT_ROOT.resolve())
        )
    except Exception:
        return str(path)


def is_inside_project(path: Path) -> bool:
    try:
        path.resolve().relative_to(PROJECT_ROOT.resolve())
        return True
    except Exception:
        return False


def is_protected(path: Path) -> bool:
    try:
        target = path.resolve()

        for protected in PROTECTED_PATHS:
            protected = protected.resolve()

            if target == protected:
                return True

            try:
                target.relative_to(protected)
                return True
            except ValueError:
                pass

        return False

    except Exception:
        return True


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


# ============================================================
# SNAPSHOT
# ============================================================

def snapshot_file(path: Path) -> None:
    target = SNAPSHOT_DIR / path.resolve().relative_to(
        PROJECT_ROOT.resolve()
    )

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)


def snapshot_directory(path: Path) -> None:
    target = SNAPSHOT_DIR / path.resolve().relative_to(
        PROJECT_ROOT.resolve()
    )

    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists():
        shutil.rmtree(target)

    shutil.copytree(path, target)


def create_snapshot(report: dict) -> None:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

    manifest = {
        "created_at": now_iso(),
        "project_root": str(PROJECT_ROOT),
        "protected_paths": [
            relative(path)
            for path in PROTECTED_PATHS
        ],
    }

    (SNAPSHOT_DIR / "snapshot_manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    report["snapshot"] = {
        "status": "PASS",
        "path": relative(SNAPSHOT_DIR),
    }


# ============================================================
# DELETE OPERATIONS
# ============================================================

def delete_file(path: Path, report: dict) -> None:
    if not path.exists():
        return

    if not is_inside_project(path) or is_protected(path):
        report["protected_skips"].append(relative(path))
        return

    try:
        snapshot_file(path)
        path.unlink()

        report["deleted_files"].append(relative(path))

    except Exception as exc:
        report["errors"].append({
            "path": relative(path),
            "operation": "delete_file",
            "error": str(exc),
        })


def delete_directory(path: Path, report: dict) -> None:
    if not path.exists():
        return

    if not is_inside_project(path) or is_protected(path):
        report["protected_skips"].append(relative(path))
        return

    try:
        snapshot_directory(path)
        shutil.rmtree(path)

        report["deleted_directories"].append(relative(path))

    except Exception as exc:
        report["errors"].append({
            "path": relative(path),
            "operation": "delete_directory",
            "error": str(exc),
        })


# ============================================================
# OBSOLETE DIRECTORIES
# ============================================================

def clean_obsolete_directories(report: dict) -> None:
    for name in OBSOLETE_DIRECTORIES:
        path = PROJECT_ROOT / name

        if not path.exists():
            continue

        delete_directory(path, report)


# ============================================================
# TEMP FILES
# ============================================================

def clean_temp_files(report: dict) -> None:
    for root, dirs, files in os.walk(PROJECT_ROOT):
        root_path = Path(root)

        dirs[:] = [
            directory
            for directory in dirs
            if not is_protected(root_path / directory)
        ]

        if is_protected(root_path):
            continue

        for filename in files:
            path = root_path / filename

            if filename in SAFE_TEMP_NAMES:
                delete_file(path, report)
                continue

            if path.suffix.lower() in SAFE_TEMP_SUFFIXES:
                delete_file(path, report)


# ============================================================
# DUPLICATE PRIORITY
# ============================================================

def duplicate_priority(path: Path) -> tuple:
    value = relative(path).replace("\\", "/")

    preferred = [
        "01_CORE/",
        "02_AGENTS/",
        "03_DATA/",
        "04_TOOLS/",
        "05_UI/",
        "06_SECURITY/",
        "07_RUNTIME/",
        "08_BUSINESS/",
        "src/",
        "tests/",
        "config/",
        "scripts/",
        "10_DOCUMENTATION/",
        "19_ARCHITECTURE/",
    ]

    for index, prefix in enumerate(preferred):
        if value.startswith(prefix):
            return (0, index, len(value), value)

    return (1, 999, len(value), value)


# ============================================================
# EXACT DUPLICATE CLEANUP
# ============================================================

def clean_exact_duplicates(report: dict) -> None:
    groups: dict[str, list[Path]] = defaultdict(list)

    for root, dirs, files in os.walk(PROJECT_ROOT):
        root_path = Path(root)

        # Never scan protected trees.
        dirs[:] = [
            directory
            for directory in dirs
            if not is_protected(root_path / directory)
        ]

        if is_protected(root_path):
            continue

        for filename in files:
            path = root_path / filename

            if is_protected(path):
                continue

            if not is_inside_project(path):
                continue

            if path.resolve() == Path(__file__).resolve():
                continue

            try:
                if path.is_symlink():
                    continue

                if path.is_file():
                    groups[sha256(path)].append(path)

            except Exception as exc:
                report["errors"].append({
                    "path": relative(path),
                    "operation": "hash",
                    "error": str(exc),
                })

    duplicate_groups = 0
    removed = 0

    for digest, paths in groups.items():

        if len(paths) < 2:
            continue

        duplicate_groups += 1

        ordered = sorted(
            paths,
            key=duplicate_priority,
        )

        canonical = ordered[0]

        group = {
            "sha256": digest,
            "canonical": relative(canonical),
            "removed": [],
        }

        for duplicate in ordered[1:]:

            if is_protected(duplicate):
                report["protected_skips"].append(
                    relative(duplicate)
                )
                continue

            if duplicate.exists():
                delete_file(duplicate, report)

                if not duplicate.exists():
                    removed += 1
                    group["removed"].append(
                        relative(duplicate)
                    )

        if group["removed"]:
            report["duplicate_groups"].append(group)

    report["duplicate_groups_found"] = duplicate_groups
    report["duplicate_files_removed"] = removed


# ============================================================
# EMPTY DIRECTORIES
# ============================================================

def clean_empty_directories(report: dict) -> None:
    directories = []

    for root, dirs, files in os.walk(PROJECT_ROOT):
        root_path = Path(root)

        for directory in dirs:
            path = root_path / directory

            if not is_protected(path):
                directories.append(path)

    directories.sort(
        key=lambda path: len(path.parts),
        reverse=True,
    )

    for path in directories:
        if not path.exists():
            continue

        if is_protected(path):
            continue

        try:
            if not any(path.iterdir()):
                path.rmdir()

                report["empty_directories_removed"].append(
                    relative(path)
                )

        except Exception:
            pass


# ============================================================
# VALIDATION
# ============================================================

def validate_active_structure(report: dict) -> None:
    existing = []
    missing = []

    for name in ACTIVE_ROOTS:
        path = PROJECT_ROOT / name

        if path.exists():
            existing.append(name)
        else:
            missing.append(name)

    report["structure_validation"] = {
        "status": "PASS",
        "existing_active_roots": existing,
        "optional_missing_roots": missing,
    }


def validate_protection(report: dict) -> None:
    violations = []

    for path in PROTECTED_PATHS:
        if not path.exists():
            violations.append(
                f"Protected path missing: {relative(path)}"
            )

    report["protection_validation"] = {
        "status": "PASS" if not violations else "FAIL",
        "violations": violations,
    }


# ============================================================
# REPORT
# ============================================================

def write_report(report: dict) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    report["completed_at"] = now_iso()

    REPORT_FILE.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )


# ============================================================
# MAIN
# ============================================================

def main() -> int:

    print("=" * 72)
    print("KAIRO CLEAN REBUILD")
    print("=" * 72)
    print()

    report = {
        "runner": "KAIRO Clean Rebuild",
        "started_at": now_iso(),
        "project_root": str(PROJECT_ROOT),

        "snapshot": {},

        "deleted_files": [],
        "deleted_directories": [],

        "duplicate_groups": [],
        "duplicate_groups_found": 0,
        "duplicate_files_removed": 0,

        "empty_directories_removed": [],

        "protected_skips": [],
        "errors": [],

        "structure_validation": {},
        "protection_validation": {},
    }

    if not PROJECT_ROOT.exists():
        print("ERROR: KAIRO project root not found.")
        return 1

    # --------------------------------------------------------
    # 1. Snapshot
    # --------------------------------------------------------

    print("[1/6] Creating rollback snapshot...")

    create_snapshot(report)

    print(
        f"Snapshot: "
        f"{SNAPSHOT_DIR}"
    )

    # --------------------------------------------------------
    # 2. Obsolete material
    # --------------------------------------------------------

    print()
    print("[2/6] Removing obsolete material...")

    clean_obsolete_directories(report)

    # --------------------------------------------------------
    # 3. Temporary material
    # --------------------------------------------------------

    print()
    print("[3/6] Removing safe temporary files...")

    clean_temp_files(report)

    # --------------------------------------------------------
    # 4. Exact duplicates
    # --------------------------------------------------------

    print()
    print("[4/6] Removing exact duplicates...")

    clean_exact_duplicates(report)

    # --------------------------------------------------------
    # 5. Empty directories
    # --------------------------------------------------------

    print()
    print("[5/6] Removing empty directories...")

    clean_empty_directories(report)

    # --------------------------------------------------------
    # 6. Validation
    # --------------------------------------------------------

    print()
    print("[6/6] Validating cleaned KAIRO...")

    validate_active_structure(report)
    validate_protection(report)

    if report["errors"]:
        report["status"] = "FAIL"

    elif report["protection_validation"]["status"] != "PASS":
        report["status"] = "FAIL"

    else:
        report["status"] = "PASS"

    write_report(report)

    # --------------------------------------------------------
    # Result
    # --------------------------------------------------------

    print()
    print("=" * 72)
    print(f"KAIRO CLEANUP: {report['status']}")
    print("=" * 72)

    print(
        f"Files deleted: "
        f"{len(report['deleted_files'])}"
    )

    print(
        f"Directories deleted: "
        f"{len(report['deleted_directories'])}"
    )

    print(
        f"Exact duplicate groups: "
        f"{report['duplicate_groups_found']}"
    )

    print(
        f"Exact duplicates removed: "
        f"{report['duplicate_files_removed']}"
    )

    print(
        f"Empty directories removed: "
        f"{len(report['empty_directories_removed'])}"
    )

    print(
        f"Protected skips: "
        f"{len(report['protected_skips'])}"
    )

    print(
        f"Errors: "
        f"{len(report['errors'])}"
    )

    print()
    print(f"Snapshot: {SNAPSHOT_DIR}")
    print(f"Report:   {REPORT_FILE}")

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())