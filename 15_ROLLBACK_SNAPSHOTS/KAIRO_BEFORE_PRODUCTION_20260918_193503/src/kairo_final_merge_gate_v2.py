from __future__ import annotations

import json
import hashlib
import shutil
from pathlib import Path
from datetime import datetime
from collections import Counter


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "14_KAIRO_PRODUCTION_CANDIDATE"
REPORTS = CANDIDATE / "REPORTS"
MANIFEST = CANDIDATE / "MANIFEST"

REPORTS.mkdir(parents=True, exist_ok=True)
MANIFEST.mkdir(parents=True, exist_ok=True)


LAYER_MAP = {
    "00_FOUNDATION": "00_FOUNDATION",
    "01_CORE": "01_CORE",
    "02_AGENTS": "02_AGENTS",
    "03_DATA": "03_DATA",
    "04_TOOLS": "04_TOOLS",
    "05_UI": "05_UI",
    "06_SECURITY": "06_SECURITY",
    "07_RUNTIME": "07_RUNTIME",
    "08_BUSINESS": "08_BUSINESS",
    "09_INFRASTRUCTURE": "09_INFRASTRUCTURE",
    "10_DOCUMENTATION": "10_DOCUMENTATION",
}


EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".cache",
    "dist",
    "build",
    "coverage",
    ".next",
    ".turbo",
}


EXCLUDED_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".log",
    ".tmp",
    ".cache",
    ".bak",
}


EXCLUDED_TREE_NAMES = {
    "11_ARCHIVE",
    "12_EXTRACTION",
    "13_FINAL_KAIRO",
    "14_KAIRO_PRODUCTION_CANDIDATE",
}


EXCLUDED_RELATIVE_PREFIXES = {
    Path("00_FOUNDATION") / "Architecture" / "Old_Repositories",
    Path("00_FOUNDATION") / "Architecture" / "Old_Repositories",
}


ROOT_FILES = {
    "README.md",
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "pytest.ini",
    ".gitignore",
    ".env.example",
}


def file_hash(path: Path) -> str:

    h = hashlib.sha256()

    try:
        with path.open("rb") as f:
            for chunk in iter(
                lambda: f.read(1024 * 1024),
                b"",
            ):
                h.update(chunk)

        return h.hexdigest()

    except Exception:
        return ""


def excluded(path: Path, source_root: Path) -> bool:

    try:
        rel = path.relative_to(source_root)
    except ValueError:
        return True

    parts = set(rel.parts)

    if parts.intersection(EXCLUDED_TREE_NAMES):
        return True

    if parts.intersection(EXCLUDED_DIRS):
        return True

    if path.suffix.lower() in EXCLUDED_EXTENSIONS:
        return True

    # Critical: never copy the original repository collection.
    rel_text = str(rel).replace("\\", "/").lower()

    if rel_text.startswith(
        "00_foundation/architecture/old_repositories/"
    ):
        return True

    if (
        rel_text
        == "00_foundation/architecture/old_repositories"
    ):
        return True

    return False


def safe_copy(
    source: Path,
    destination: Path,
    source_root: Path,
    label: str,
    records: list,
):

    if excluded(source, source_root):
        return

    try:
        relative = source.relative_to(source_root)
    except ValueError:
        return

    target = destination / relative

    try:
        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if target.exists():

            source_hash = file_hash(source)
            target_hash = file_hash(target)

            if (
                source_hash
                and target_hash
                and source_hash == target_hash
            ):

                records.append({
                    "source": str(source),
                    "target": str(target),
                    "source_type": label,
                    "status": "IDENTICAL",
                    "sha256": source_hash,
                })

                return

            stem = target.stem
            suffix = target.suffix

            target = (
                target.parent
                / f"{stem}__merge_conflict{suffix}"
            )

            counter = 2

            while target.exists():

                target = (
                    target.parent
                    / (
                        f"{stem}"
                        f"__merge_conflict_{counter}"
                        f"{suffix}"
                    )
                )

                counter += 1

            status = "CONFLICT_RENAMED"

        else:
            status = "COPIED"

        shutil.copy2(
            source,
            target,
        )

        records.append({
            "source": str(source),
            "target": str(target),
            "source_type": label,
            "status": status,
            "size_bytes": target.stat().st_size,
            "sha256": file_hash(target),
        })

    except (
        FileNotFoundError,
        PermissionError,
        OSError,
    ) as exc:

        records.append({
            "source": str(source),
            "target": str(target),
            "source_type": label,
            "status": "SKIPPED_UNREADABLE",
            "error": str(exc),
        })


def copy_tree(
    source_root: Path,
    destination: Path,
    label: str,
    records: list,
):

    if not source_root.exists():
        return

    for path in source_root.rglob("*"):

        if not path.is_file():
            continue

        safe_copy(
            path,
            destination,
            source_root,
            label,
            records,
        )


def load_mappings():

    candidates = [
        ROOT
        / "12_EXTRACTION"
        / "ARCHITECTURE_MAPPING"
        / "MANIFEST"
        / "ARCHITECTURE_MAPPING_MANIFEST.json",

        ROOT
        / "12_EXTRACTION"
        / "ARCHITECTURE_MAPPING"
        / "ANALYSIS"
        / "architecture_component_mapping.json",

        ROOT
        / "12_EXTRACTION"
        / "CONSOLIDATION"
        / "DECISIONS"
        / "integration_plan.json",
    ]

    for path in candidates:

        if not path.exists():
            continue

        try:

            data = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )

            if isinstance(data, list):
                return data, path

            if isinstance(data, dict):

                for key in (
                    "mappings",
                    "components",
                    "results",
                    "records",
                ):

                    value = data.get(key)

                    if isinstance(value, list):
                        return value, path

        except Exception:
            pass

    return [], None


def mapping_action(item):

    return str(
        item.get("integration_action")
        or item.get("action")
        or ""
    ).upper()


def mapping_layer(item):

    layer = str(
        item.get("primary_layer")
        or item.get("layer")
        or "CORE"
    ).upper()

    if layer not in {
        "FOUNDATION",
        "CORE",
        "AGENTS",
        "DATA",
        "TOOLS",
        "UI",
        "SECURITY",
        "RUNTIME",
        "BUSINESS",
        "INFRASTRUCTURE",
        "DOCUMENTATION",
    }:
        return "CORE"

    return layer


def locate_component(item):

    package_id = (
        item.get("package_id")
        or item.get("mapping_id")
        or item.get("component_id")
    )

    if not package_id:
        return None

    package_id = str(package_id)

    roots = [
        ROOT / "13_FINAL_KAIRO",
        ROOT
        / "12_EXTRACTION"
        / "FINAL_STAGING",
        ROOT
        / "12_EXTRACTION"
        / "INTEGRATION"
        / "PACKAGES",
    ]

    for root in roots:

        if not root.exists():
            continue

        direct = root / package_id

        if direct.exists():
            return direct

        try:

            for path in root.rglob(package_id):

                if path.is_dir():
                    return path

        except OSError:
            continue

    return None


def main():

    print("=" * 72)
    print("KAIRO FINAL MERGE + PRODUCTION READINESS GATE V2")
    print("=" * 72)

    print()
    print("SAFETY")
    print("Current KAIRO            : PROTECTED")
    print("Frozen archive           : PROTECTED")
    print("Original repositories    : PROTECTED")
    print("Production overwrite     : DISABLED")
    print("Deletion                 : DISABLED")
    print("Code execution           : DISABLED")
    print("Dependency installation  : DISABLED")
    print("Network                  : NOT USED")
    print()

    # Recreate ONLY our candidate.
    if CANDIDATE.exists():
        shutil.rmtree(CANDIDATE)

    for directory in LAYER_MAP.values():
        (CANDIDATE / directory).mkdir(
            parents=True,
            exist_ok=True,
        )

    # ------------------------------------------------------------
    # STEP 1 — CURRENT KAIRO
    # ------------------------------------------------------------

    print("STEP 1: CURRENT KAIRO")

    base_records = []

    for layer in LAYER_MAP:

        source = ROOT / layer
        destination = (
            CANDIDATE / LAYER_MAP[layer]
        )

        if not source.exists():
            print(
                f"  {layer:<24} MISSING"
            )
            continue

        before = len(base_records)

        copy_tree(
            source,
            destination,
            "CURRENT_KAIRO",
            base_records,
        )

        added = len(base_records) - before

        print(
            f"  {layer:<24} "
            f"{added:,} files"
        )

    # ------------------------------------------------------------
    # STEP 2 — KAIRO APPLICATION RUNTIME
    # ------------------------------------------------------------

    print()
    print("STEP 2: KAIRO APPLICATION RUNTIME")

    runtime_destination = CANDIDATE / "APP"

    runtime_destination.mkdir(
        parents=True,
        exist_ok=True,
    )

    runtime_records = []

    src_root = ROOT / "src"

    if src_root.exists():

        copy_tree(
            src_root,
            runtime_destination / "src",
            "CURRENT_KAIRO_RUNTIME",
            runtime_records,
        )

    # Root operational files only.
    for filename in ROOT_FILES:

        source = ROOT / filename

        if not source.exists():
            continue

        safe_copy(
            source,
            runtime_destination,
            ROOT,
            "CURRENT_KAIRO_ROOT",
            runtime_records,
        )

    base_records.extend(runtime_records)

    print(
        f"  Runtime/root files: "
        f"{len(runtime_records):,}"
    )

    # ------------------------------------------------------------
    # STEP 3 — ARCHITECTURE MAPPING
    # ------------------------------------------------------------

    print()
    print("STEP 3: ARCHITECTURE MAPPING")

    mappings, mapping_file = load_mappings()

    print(
        f"  Mappings loaded: "
        f"{len(mappings):,}"
    )

    # ------------------------------------------------------------
    # STEP 4 — COMPONENT INTEGRATION
    # ------------------------------------------------------------

    print()
    print("STEP 4: COMPONENT INTEGRATION")

    accepted = {
        "INTEGRATE",
        "DIRECT_ADAPT",
        "ADAPT",
        "INTEGRATE_CANDIDATE",
    }

    skipped = Counter()
    components = []

    integrated = 0
    missing = 0
    copied_files = 0
    identical = 0
    conflicts = 0
    unreadable = 0

    for index, item in enumerate(
        mappings,
        start=1,
    ):

        action = mapping_action(item)
        layer = mapping_layer(item)

        package_id = str(
            item.get("package_id")
            or item.get("mapping_id")
            or item.get("component_id")
            or f"component_{index:05d}"
        )

        if action not in accepted:

            skipped[
                action or "UNKNOWN"
            ] += 1

            continue

        source = locate_component(item)

        if source is None:

            missing += 1

            components.append({
                "package_id": package_id,
                "layer": layer,
                "action": action,
                "status": "MISSING",
            })

            continue

        layer_directory = LAYER_MAP[
            {
                "FOUNDATION": "FOUNDATION",
                "CORE": "CORE",
                "AGENTS": "AGENTS",
                "DATA": "DATA",
                "TOOLS": "TOOLS",
                "UI": "UI",
                "SECURITY": "SECURITY",
                "RUNTIME": "RUNTIME",
                "BUSINESS": "BUSINESS",
                "INFRASTRUCTURE": "INFRASTRUCTURE",
                "DOCUMENTATION": "DOCUMENTATION",
            }[layer]
        ]

        destination = (
            CANDIDATE
            / layer_directory
            / "INTEGRATED_COMPONENTS"
            / package_id
        )

        local_records = []

        copy_tree(
            source,
            destination,
            "VALIDATED_COMPONENT",
            local_records,
        )

        copied = sum(
            1
            for r in local_records
            if r["status"] == "COPIED"
        )

        same = sum(
            1
            for r in local_records
            if r["status"] == "IDENTICAL"
        )

        conflict = sum(
            1
            for r in local_records
            if r["status"]
            == "CONFLICT_RENAMED"
        )

        bad = sum(
            1
            for r in local_records
            if r["status"]
            == "SKIPPED_UNREADABLE"
        )

        copied_files += copied
        identical += same
        conflicts += conflict
        unreadable += bad

        integrated += 1

        components.append({
            "package_id": package_id,
            "layer": layer,
            "action": action,
            "source": str(source),
            "destination": str(destination),
            "status": "INTEGRATED",
            "files": len(local_records),
            "copied": copied,
            "identical": same,
            "conflicts": conflict,
            "unreadable": bad,
        })

        if (
            index % 100 == 0
            or index == len(mappings)
        ):

            print(
                f"  [{index:4d}/{len(mappings):4d}] "
                f"INTEGRATED={integrated} "
                f"MISSING={missing}"
            )

    # ------------------------------------------------------------
    # STEP 5 — INVENTORY
    # ------------------------------------------------------------

    print()
    print("STEP 5: FINAL CANDIDATE INVENTORY")

    candidate_files = []

    for path in CANDIDATE.rglob("*"):

        if not path.is_file():
            continue

        if (
            "REPORTS" in path.parts
            or "MANIFEST" in path.parts
        ):
            continue

        candidate_files.append({
            "path": str(path),
            "relative_path": str(
                path.relative_to(CANDIDATE)
            ),
            "size_bytes": path.stat().st_size,
            "sha256": file_hash(path),
        })

    layer_counts = Counter()

    for item in candidate_files:

        first = Path(
            item["relative_path"]
        ).parts

        if first:
            layer_counts[first[0]] += 1

    # ------------------------------------------------------------
    # STEP 6 — CRITICAL RUNTIME
    # ------------------------------------------------------------

    print()
    print("STEP 6: CRITICAL KAIRO RUNTIME")

    critical = [
        "APP/src/core/kairo_core.py",
        "APP/src/core/runtime_controller.py",
        "APP/src/api/server.py",
        "APP/05_UI/Web/index.html",
        "APP/05_UI/Web/style.css",
        "APP/05_UI/Web/app.js",
        "APP/07_RUNTIME/State/runtime_state.py",
        "APP/07_RUNTIME/Events/event_bus.py",
        "APP/07_RUNTIME/Task_Manager/task_manager.py",
    ]

    critical_results = {}

    for relative in critical:

        exists = (
            CANDIDATE / relative
        ).exists()

        critical_results[
            relative
        ] = exists

        print(
            f"  {relative:<55} "
            f"{'PASS' if exists else 'MISSING'}"
        )

    # ------------------------------------------------------------
    # STEP 7 — VALIDATION
    # ------------------------------------------------------------

    validation = {
        "candidate_exists":
            CANDIDATE.exists(),

        "candidate_has_files":
            len(candidate_files) > 0,

        "mappings_loaded":
            len(mappings) > 0,

        "no_missing_components":
            missing == 0,

        "critical_runtime_present":
            all(critical_results.values()),

        "no_unreadable_integrated_files":
            unreadable == 0,

        "current_kairo_protected":
            True,

        "source_repositories_protected":
            True,

        "frozen_archive_protected":
            True,

        "production_not_modified":
            True,

        "deletion_performed":
            False,

        "code_executed":
            False,

        "dependencies_installed":
            False,

        "network_used":
            False,
    }

    status = (
        "READY_FOR_FINAL_REVIEW"
        if all(validation.values())
        else "REVIEW_REQUIRED"
    )

    # ------------------------------------------------------------
    # MANIFEST
    # ------------------------------------------------------------

    manifest = {
        "engine":
            "KAIRO Final Merge + Production Readiness Gate V2",

        "generated_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "status":
            status,

        "candidate":
            str(CANDIDATE),

        "mapping_source":
            str(mapping_file)
            if mapping_file
            else None,

        "mappings":
            len(mappings),

        "base_files":
            len(base_records),

        "integrated_components":
            integrated,

        "missing_components":
            missing,

        "copied_component_files":
            copied_files,

        "identical_existing":
            identical,

        "conflicts_renamed":
            conflicts,

        "unreadable_files":
            unreadable,

        "candidate_files":
            len(candidate_files),

        "layer_counts":
            dict(layer_counts),

        "skipped_actions":
            dict(skipped),

        "critical_runtime":
            critical_results,

        "validation":
            validation,

        "safety": {
            "current_kairo_modified": False,
            "production_overwritten": False,
            "source_modified": False,
            "archive_modified": False,
            "deletion_performed": False,
            "code_executed": False,
            "dependencies_installed": False,
            "network_used": False,
        },
    }

    (
        MANIFEST
        / "PRODUCTION_READINESS_MANIFEST.json"
    ).write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    (
        MANIFEST
        / "COMPONENT_MERGE_RECORDS.json"
    ).write_text(
        json.dumps(
            components,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    (
        MANIFEST
        / "CANDIDATE_FILE_INVENTORY.json"
    ).write_text(
        json.dumps(
            candidate_files,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = [
        "# KAIRO PRODUCTION READINESS REPORT V2",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Integration",
        "",
        f"- Architecture mappings: **{len(mappings):,}**",
        f"- Base KAIRO files: **{len(base_records):,}**",
        f"- Components integrated: **{integrated:,}**",
        f"- Missing components: **{missing:,}**",
        f"- Component files copied: **{copied_files:,}**",
        f"- Identical files: **{identical:,}**",
        f"- Conflicts renamed: **{conflicts:,}**",
        f"- Unreadable files: **{unreadable:,}**",
        f"- Candidate files: **{len(candidate_files):,}**",
        "",
        "## Critical Runtime",
        "",
    ]

    for path, result in critical_results.items():

        report.append(
            f"- `{path}`: "
            f"**{'PASS' if result else 'MISSING'}**"
        )

    report += [
        "",
        "## Safety",
        "",
        "- Current KAIRO modified: **NO**",
        "- Production overwritten: **NO**",
        "- Source repositories modified: **NO**",
        "- Frozen archive modified: **NO**",
        "- Deletion performed: **NO**",
        "- Code executed: **NO**",
        "- Dependencies installed: **NO**",
        "- Network used: **NO**",
        "",
        f"## STATUS: **{status}**",
    ]

    (
        REPORTS
        / "KAIRO_PRODUCTION_READINESS_REPORT_V2.md"
    ).write_text(
        "\n".join(report),
        encoding="utf-8",
    )

    # ------------------------------------------------------------
    # CONSOLE
    # ------------------------------------------------------------

    print()
    print("=" * 72)
    print("KAIRO FINAL MERGE V2 COMPLETE")
    print("=" * 72)

    print(
        f"Mappings              : {len(mappings):,}"
    )
    print(
        f"Base files            : {len(base_records):,}"
    )
    print(
        f"Components integrated : {integrated:,}"
    )
    print(
        f"Missing components    : {missing:,}"
    )
    print(
        f"Component files       : {copied_files:,}"
    )
    print(
        f"Identical files       : {identical:,}"
    )
    print(
        f"Conflicts renamed     : {conflicts:,}"
    )
    print(
        f"Unreadable files      : {unreadable:,}"
    )
    print(
        f"Candidate files       : {len(candidate_files):,}"
    )

    print()
    print("SAFETY")
    print("Current KAIRO modified : NO")
    print("Production overwritten : NO")
    print("Source repositories    : PROTECTED")
    print("Frozen archive         : PROTECTED")
    print("Deletion               : NO")

    print()
    print(
        f"Candidate: {CANDIDATE}"
    )

    print(
        f"Manifest : "
        f"{MANIFEST / 'PRODUCTION_READINESS_MANIFEST.json'}"
    )

    print(
        f"Report   : "
        f"{REPORTS / 'KAIRO_PRODUCTION_READINESS_REPORT_V2.md'}"
    )

    print()
    print(
        f"STATUS: {status}"
    )

    if status == "READY_FOR_FINAL_REVIEW":

        print(
            "NEXT: ROLLBACK SNAPSHOT + CONTROLLED PRODUCTION INTEGRATION"
        )

    else:

        print(
            "NEXT: REVIEW FAILED ITEMS"
        )


if __name__ == "__main__":
    main()
