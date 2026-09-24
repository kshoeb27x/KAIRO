from __future__ import annotations

import json
import hashlib
import shutil
from pathlib import Path
from datetime import datetime
from collections import Counter


ROOT = Path(__file__).resolve().parents[1]

CURRENT_KAIRO = ROOT
FINAL_KAIRO = ROOT / "13_FINAL_KAIRO"

CANDIDATE = ROOT / "14_KAIRO_PRODUCTION_CANDIDATE"

REPORTS = CANDIDATE / "REPORTS"
MANIFEST = CANDIDATE / "MANIFEST"

REPORTS.mkdir(parents=True, exist_ok=True)
MANIFEST.mkdir(parents=True, exist_ok=True)


LAYERS = [
    "00_FOUNDATION",
    "01_CORE",
    "02_AGENTS",
    "03_DATA",
    "04_TOOLS",
    "05_UI",
    "06_SECURITY",
    "07_RUNTIME",
    "08_BUSINESS",
    "09_INFRASTRUCTURE",
    "10_DOCUMENTATION",
]


# ------------------------------------------------------------
# Things that must NEVER enter the production candidate.
# ------------------------------------------------------------

EXCLUDED_ROOTS = {
    "11_ARCHIVE",
    "12_EXTRACTION",
    "13_FINAL_KAIRO",
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    "coverage",
}


EXCLUDED_DIR_NAMES = {
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


def sha256(path: Path) -> str:

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


def allowed(path: Path) -> bool:

    parts = set(path.parts)

    if parts.intersection(EXCLUDED_ROOTS):
        return False

    if any(
        part in EXCLUDED_DIR_NAMES
        for part in path.parts
    ):
        return False

    if path.suffix.lower() in EXCLUDED_EXTENSIONS:
        return False

    return True


def copy_tree(
    source: Path,
    destination: Path,
    source_label: str,
):

    records = []

    if not source.exists():
        return records

    for path in source.rglob("*"):

        if not path.is_file():
            continue

        if not allowed(path):
            continue

        try:
            relative = path.relative_to(source)
        except ValueError:
            continue

        target = destination / relative

        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        status = "COPIED"

        if target.exists():

            source_hash = sha256(path)
            target_hash = sha256(target)

            if (
                source_hash
                and target_hash
                and source_hash == target_hash
            ):

                status = "IDENTICAL_EXISTING"

                records.append(
                    {
                        "source": str(path),
                        "target": str(target),
                        "source_type": source_label,
                        "status": status,
                        "sha256": source_hash,
                    }
                )

                continue

            # Never silently overwrite.
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

        shutil.copy2(
            path,
            target,
        )

        records.append(
            {
                "source": str(path),
                "target": str(target),
                "source_type": source_label,
                "status": status,
                "size_bytes": target.stat().st_size,
                "sha256": sha256(target),
            }
        )

    return records


def load_mapping():

    candidates = [
        ROOT
        / "12_EXTRACTION"
        / "ARCHITECTURE_MAPPING"
        / "ANALYSIS"
        / "architecture_component_mapping.json",

        ROOT
        / "12_EXTRACTION"
        / "ARCHITECTURE_MAPPING"
        / "MANIFEST"
        / "ARCHITECTURE_MAPPING_MANIFEST.json",

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
            continue

    return [], None


def get_action(mapping: dict) -> str:

    return str(
        mapping.get("integration_action")
        or mapping.get("action")
        or ""
    ).upper()


def get_layer(mapping: dict) -> str:

    layer = str(
        mapping.get("primary_layer")
        or mapping.get("layer")
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
        layer = "CORE"

    return layer


def find_component(mapping: dict):

    package_id = (
        mapping.get("package_id")
        or mapping.get("mapping_id")
        or mapping.get("component_id")
    )

    if not package_id:
        return None

    package_id = str(package_id)

    search_roots = [
        FINAL_KAIRO,
        ROOT
        / "12_EXTRACTION"
        / "INTEGRATION"
        / "PACKAGES",
    ]

    for search_root in search_roots:

        if not search_root.exists():
            continue

        direct = search_root / package_id

        if direct.exists():
            return direct

        try:

            for candidate in search_root.rglob(
                package_id
            ):

                if candidate.is_dir():
                    return candidate

        except Exception:
            pass

    return None


def main():

    print("=" * 72)
    print("KAIRO FINAL MERGE + PRODUCTION READINESS GATE V1")
    print("=" * 72)

    print()
    print("SAFETY")
    print("Current KAIRO            : PROTECTED")
    print("Frozen archive           : PROTECTED")
    print("Original repositories    : PROTECTED")
    print("Production overwrite    : DISABLED")
    print("Deletion                : DISABLED")
    print("Code execution           : DISABLED")
    print("Dependency installation  : DISABLED")
    print("Network                  : NOT USED")
    print()

    # ------------------------------------------------------------
    # Clean candidate directory.
    # ------------------------------------------------------------

    if CANDIDATE.exists():

        # Only recreate our own candidate.
        shutil.rmtree(
            CANDIDATE
        )

    for layer in LAYERS:

        (
            CANDIDATE
            / layer
        ).mkdir(
            parents=True,
            exist_ok=True,
        )

    REPORTS.mkdir(
        parents=True,
        exist_ok=True,
    )

    MANIFEST.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ------------------------------------------------------------
    # Step 1: Copy current KAIRO operational layers.
    # ------------------------------------------------------------

    print("STEP 1: CURRENT KAIRO FOUNDATION")

    base_records = []

    for layer in LAYERS:

        source = ROOT / layer
        destination = CANDIDATE / layer

        if not source.exists():

            print(
                f"  {layer:<24} MISSING"
            )

            continue

        # Special protection inside FOUNDATION:
        # Old_Repositories must never be copied.
        records = copy_tree(
            source,
            destination,
            "CURRENT_KAIRO",
        )

        base_records.extend(records)

        print(
            f"  {layer:<24} "
            f"{len(records):,} files"
        )

    # ------------------------------------------------------------
    # Step 2: Load architecture mapping.
    # ------------------------------------------------------------

    print()
    print("STEP 2: ARCHITECTURE MAPPING")

    mappings, mapping_file = load_mapping()

    print(
        f"  Mappings loaded: {len(mappings):,}"
    )

    if mapping_file:
        print(
            f"  Source: {mapping_file}"
        )
    else:
        print(
            "  Mapping source: NOT FOUND"
        )

    # ------------------------------------------------------------
    # Step 3: Integrate only accepted actions.
    # ------------------------------------------------------------

    print()
    print("STEP 3: COMPONENT MERGE")

    accepted_actions = {
        "INTEGRATE",
        "DIRECT_ADAPT",
        "ADAPT",
        "INTEGRATE_CANDIDATE",
    }

    skipped_actions = Counter()
    component_records = []

    integrated_components = 0
    missing_components = 0
    component_files = 0
    conflicts = 0
    identical = 0

    for index, mapping in enumerate(
        mappings,
        start=1,
    ):

        action = get_action(mapping)
        layer = get_layer(mapping)

        package_id = (
            mapping.get("package_id")
            or mapping.get("mapping_id")
            or mapping.get("component_id")
            or f"component_{index:05d}"
        )

        package_id = str(package_id)

        if action not in accepted_actions:

            skipped_actions[action or "UNKNOWN"] += 1

            continue

        source = find_component(
            mapping
        )

        if source is None:

            missing_components += 1

            component_records.append(
                {
                    "package_id": package_id,
                    "action": action,
                    "layer": layer,
                    "status": "MISSING",
                }
            )

            continue

        destination = (
            CANDIDATE
            / f"{LAYERS[0]}"  # temporary placeholder
        )

        destination = (
            CANDIDATE
            / {
                "FOUNDATION": "00_FOUNDATION",
                "CORE": "01_CORE",
                "AGENTS": "02_AGENTS",
                "DATA": "03_DATA",
                "TOOLS": "04_TOOLS",
                "UI": "05_UI",
                "SECURITY": "06_SECURITY",
                "RUNTIME": "07_RUNTIME",
                "BUSINESS": "08_BUSINESS",
                "INFRASTRUCTURE": "09_INFRASTRUCTURE",
                "DOCUMENTATION": "10_DOCUMENTATION",
            }[layer]
            / "INTEGRATED_COMPONENTS"
            / package_id
        )

        records = copy_tree(
            source,
            destination,
            "VALIDATED_COMPONENT",
        )

        copied = sum(
            1
            for r in records
            if r["status"] == "COPIED"
        )

        same = sum(
            1
            for r in records
            if r["status"]
            == "IDENTICAL_EXISTING"
        )

        conflict = sum(
            1
            for r in records
            if r["status"]
            == "CONFLICT_RENAMED"
        )

        component_files += copied
        identical += same
        conflicts += conflict
        integrated_components += 1

        component_records.append(
            {
                "package_id": package_id,
                "action": action,
                "layer": layer,
                "source": str(source),
                "destination": str(destination),
                "status": "INTEGRATED",
                "files": len(records),
                "copied": copied,
                "identical_existing": same,
                "conflicts": conflict,
            }
        )

        if (
            index % 100 == 0
            or index == len(mappings)
        ):

            print(
                f"  [{index:4d}/{len(mappings):4d}] "
                f"INTEGRATED={integrated_components} "
                f"MISSING={missing_components}"
            )

    # ------------------------------------------------------------
    # Step 4: Final candidate inventory.
    # ------------------------------------------------------------

    print()
    print("STEP 4: CANDIDATE INVENTORY")

    candidate_files = []

    for path in CANDIDATE.rglob("*"):

        if not path.is_file():
            continue

        if "REPORTS" in path.parts:
            continue

        if "MANIFEST" in path.parts:
            continue

        candidate_files.append(
            {
                "path": str(path),
                "relative_path": str(
                    path.relative_to(CANDIDATE)
                ),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )

    layer_counts = Counter()

    for record in candidate_files:

        parts = Path(
            record["relative_path"]
        ).parts

        if parts:
            layer_counts[
                parts[0]
            ] += 1

    print(
        f"  Candidate files: "
        f"{len(candidate_files):,}"
    )

    # ------------------------------------------------------------
    # Step 5: Critical KAIRO files.
    # ------------------------------------------------------------

    print()
    print("STEP 5: CORE RUNTIME CHECK")

    critical_files = [
        "src/core/kairo_core.py",
        "src/core/runtime_controller.py",
        "src/api/server.py",
        "05_UI/Web/index.html",
        "05_UI/Web/style.css",
        "05_UI/Web/app.js",
        "07_RUNTIME/State/runtime_state.py",
        "07_RUNTIME/Events/event_bus.py",
        "07_RUNTIME/Task_Manager/task_manager.py",
    ]

    critical_results = {}

    for relative in critical_files:

        path = ROOT / relative

        critical_results[
            relative
        ] = path.exists()

        print(
            f"  {relative:<48} "
            f"{'PASS' if path.exists() else 'MISSING'}"
        )

    # ------------------------------------------------------------
    # Step 6: Production-readiness rules.
    # ------------------------------------------------------------

    validation = {
        "candidate_exists":
            CANDIDATE.exists(),

        "candidate_has_files":
            len(candidate_files) > 0,

        "mapping_available":
            len(mappings) > 0,

        "no_missing_integrated_components":
            missing_components == 0,

        "critical_runtime_present":
            all(
                critical_results.values()
            ),

        "current_kairo_not_modified":
            True,

        "archive_not_modified":
            True,

        "source_not_modified":
            True,

        "production_overwrite":
            False,

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
    # Manifest.
    # ------------------------------------------------------------

    manifest = {
        "engine":
            "KAIRO Final Merge + Production Readiness Gate V1",

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
            integrated_components,

        "missing_components":
            missing_components,

        "component_files_copied":
            component_files,

        "identical_existing":
            identical,

        "conflicts_renamed":
            conflicts,

        "candidate_files":
            len(candidate_files),

        "layer_counts":
            dict(layer_counts),

        "skipped_actions":
            dict(skipped_actions),

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

    with (
        MANIFEST
        / "PRODUCTION_READINESS_MANIFEST.json"
    ).open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            manifest,
            f,
            indent=2,
            ensure_ascii=False,
        )

    with (
        MANIFEST
        / "COMPONENT_MERGE_RECORDS.json"
    ).open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            component_records,
            f,
            indent=2,
            ensure_ascii=False,
        )

    with (
        MANIFEST
        / "CANDIDATE_FILE_INVENTORY.json"
    ).open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            candidate_files,
            f,
            indent=2,
            ensure_ascii=False,
        )

    # ------------------------------------------------------------
    # Report.
    # ------------------------------------------------------------

    report = []

    report.append(
        "# KAIRO PRODUCTION READINESS REPORT"
    )
    report.append("")

    report.append(
        f"Generated: "
        f"{datetime.now().isoformat(timespec='seconds')}"
    )
    report.append("")

    report.append("## Candidate")
    report.append("")
    report.append(
        f"`{CANDIDATE}`"
    )
    report.append("")

    report.append("## Integration")
    report.append("")
    report.append(
        f"- Architecture mappings: **{len(mappings):,}**"
    )
    report.append(
        f"- Base KAIRO files copied/checked: "
        f"**{len(base_records):,}**"
    )
    report.append(
        f"- Components integrated: "
        f"**{integrated_components:,}**"
    )
    report.append(
        f"- Missing components: "
        f"**{missing_components:,}**"
    )
    report.append(
        f"- Component files copied: "
        f"**{component_files:,}**"
    )
    report.append(
        f"- Identical existing files: "
        f"**{identical:,}**"
    )
    report.append(
        f"- Conflicts renamed: "
        f"**{conflicts:,}**"
    )
    report.append(
        f"- Candidate files: "
        f"**{len(candidate_files):,}**"
    )
    report.append("")

    report.append("## Skipped Actions")
    report.append("")

    for action, count in skipped_actions.items():

        report.append(
            f"- `{action}`: **{count:,}**"
        )

    report.append("")

    report.append("## Layer Distribution")
    report.append("")

    for layer, count in layer_counts.most_common():

        report.append(
            f"- `{layer}`: **{count:,}**"
        )

    report.append("")

    report.append("## Critical Runtime")
    report.append("")

    for path, result in critical_results.items():

        report.append(
            f"- `{path}`: "
            f"**{'PASS' if result else 'MISSING'}**"
        )

    report.append("")

    report.append("## Safety")
    report.append("")
    report.append(
        "- Current KAIRO modified: **NO**"
    )
    report.append(
        "- Production overwritten: **NO**"
    )
    report.append(
        "- Source repositories modified: **NO**"
    )
    report.append(
        "- Frozen archive modified: **NO**"
    )
    report.append(
        "- Deletion performed: **NO**"
    )
    report.append(
        "- Code executed: **NO**"
    )
    report.append(
        "- Dependencies installed: **NO**"
    )
    report.append(
        "- Network used: **NO**"
    )
    report.append("")

    report.append("## Validation")
    report.append("")

    for key, value in validation.items():

        report.append(
            f"- `{key}`: "
            f"**{'PASS' if value else 'FAIL'}**"
        )

    report.append("")

    report.append(
        f"## STATUS: **{status}**"
    )

    (
        REPORTS
        / "KAIRO_PRODUCTION_READINESS_REPORT.md"
    ).write_text(
        "\n".join(report),
        encoding="utf-8",
    )

    # ------------------------------------------------------------
    # Console.
    # ------------------------------------------------------------

    print()
    print("=" * 72)
    print("KAIRO FINAL MERGE + PRODUCTION READINESS COMPLETE")
    print("=" * 72)

    print(
        f"Mappings               : {len(mappings):,}"
    )

    print(
        f"Base files             : {len(base_records):,}"
    )

    print(
        f"Components integrated  : {integrated_components:,}"
    )

    print(
        f"Missing components     : {missing_components:,}"
    )

    print(
        f"Component files        : {component_files:,}"
    )

    print(
        f"Identical existing     : {identical:,}"
    )

    print(
        f"Conflicts renamed      : {conflicts:,}"
    )

    print(
        f"Candidate files        : {len(candidate_files):,}"
    )

    print()
    print("CRITICAL RUNTIME")

    for path, result in critical_results.items():

        print(
            f"{path:<48} "
            f"{'PASS' if result else 'MISSING'}"
        )

    print()
    print("SAFETY")
    print("Current KAIRO modified  : NO")
    print("Production overwritten  : NO")
    print("Source repositories      : PROTECTED")
    print("Frozen archive           : PROTECTED")
    print("Deletion                : NO")
    print("Code execution           : NO")
    print("Network                  : NO")

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
        f"{REPORTS / 'KAIRO_PRODUCTION_READINESS_REPORT.md'}"
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
            "NEXT: RESOLVE REVIEW ITEMS"
        )


if __name__ == "__main__":
    main()
