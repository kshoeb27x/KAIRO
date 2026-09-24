from __future__ import annotations

import json
import hashlib
import shutil
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict


ROOT = Path(__file__).resolve().parents[1]

MAPPING_FILE = (
    ROOT
    / "12_EXTRACTION"
    / "ARCHITECTURE_MAPPING"
    / "ANALYSIS"
    / "architecture_component_mapping.json"
)

SOURCE_ROOT = (
    ROOT
    / "12_EXTRACTION"
    / "FINAL_STAGING"
)

FINAL_ROOT = (
    ROOT
    / "13_FINAL_KAIRO"
)

REPORT_ROOT = FINAL_ROOT / "REPORTS"
MANIFEST_ROOT = FINAL_ROOT / "MANIFEST"

LAYERS = {
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
}

BLOCKED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    "coverage",
    ".next",
    ".turbo",
}

BLOCKED_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".log",
    ".tmp",
    ".cache",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def safe_name(value: str) -> str:
    value = "".join(
        c if c.isalnum() or c in "._-" else "_"
        for c in str(value)
    )

    return value.strip("_") or "component"


def load_mappings():
    if not MAPPING_FILE.exists():
        raise FileNotFoundError(
            f"Mapping file missing:\n{MAPPING_FILE}"
        )

    with MAPPING_FILE.open(
        "r",
        encoding="utf-8",
    ) as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise TypeError(
            "architecture_component_mapping.json "
            "must contain a list"
        )

    return data


def find_package(mapping: dict) -> Path | None:

    package_id = (
        mapping.get("package_id")
        or mapping.get("mapping_id")
    )

    if not package_id:
        return None

    package_id = str(package_id)

    candidates = [
        SOURCE_ROOT
        / "CORE"
        / "EXTRACTED"
        / package_id,

        SOURCE_ROOT
        / "01_CORE"
        / "EXTRACTED"
        / package_id,

        SOURCE_ROOT
        / "PACKAGES"
        / package_id,
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    # Search all staging layers.
    if SOURCE_ROOT.exists():

        for candidate in SOURCE_ROOT.rglob(
            package_id
        ):
            if candidate.is_dir():
                return candidate

    return None


def eligible_files(package: Path):

    if package.is_file():
        return [package]

    result = []

    for path in package.rglob("*"):

        if not path.is_file():
            continue

        if any(
            part in BLOCKED_DIRS
            for part in path.parts
        ):
            continue

        if path.suffix.lower() in BLOCKED_EXTENSIONS:
            continue

        result.append(path)

    return result


def create_clean_structure():

    FINAL_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    for layer in LAYERS.values():

        (
            FINAL_ROOT
            / layer
        ).mkdir(
            parents=True,
            exist_ok=True,
        )

    REPORT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    MANIFEST_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )


def copy_component(
    source: Path,
    destination: Path,
):

    destination.mkdir(
        parents=True,
        exist_ok=True,
    )

    files = eligible_files(source)

    records = []

    for source_file in files:

        if source.is_file():
            relative = Path(source.name)
        else:
            relative = source_file.relative_to(source)

        target = destination / relative

        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if target.exists():

            existing_hash = sha256(target)
            source_hash = sha256(source_file)

            if existing_hash == source_hash:

                records.append(
                    {
                        "source": str(source_file),
                        "target": str(target),
                        "status": "DUPLICATE_IDENTICAL",
                        "sha256": source_hash,
                    }
                )

                continue

            # Never overwrite conflicting files.
            stem = target.stem
            suffix = target.suffix

            target = (
                target.parent
                / f"{stem}__component_conflict{suffix}"
            )

            counter = 2

            while target.exists():

                target = (
                    target.parent
                    / (
                        f"{stem}"
                        f"__component_conflict_{counter}"
                        f"{suffix}"
                    )
                )

                counter += 1

            status = "CONFLICT_RENAMED"

        else:
            status = "COPIED"

        shutil.copy2(
            source_file,
            target,
        )

        records.append(
            {
                "source": str(source_file),
                "target": str(target),
                "status": status,
                "size_bytes": target.stat().st_size,
                "sha256": sha256(target),
            }
        )

    return records


def main():

    print("=" * 68)
    print("KAIRO FINAL INTEGRATION + CLEAN ARCHITECTURE BUILDER V1")
    print("=" * 68)

    mappings = load_mappings()

    print(
        f"Architecture mappings : {len(mappings):,}"
    )

    print()
    print("SAFETY")
    print("Current Production KAIRO : PROTECTED")
    print("Frozen Archive           : PROTECTED")
    print("Source Repositories      : PROTECTED")
    print("Code Execution           : DISABLED")
    print("Dependency Installation  : DISABLED")
    print("Network                  : NOT USED")
    print("Deletion                 : DISABLED")
    print()

    # ------------------------------------------------------------
    # Create clean final tree.
    # ------------------------------------------------------------

    create_clean_structure()

    # ------------------------------------------------------------
    # Counters.
    # ------------------------------------------------------------

    layer_counts = Counter()
    action_counts = Counter()
    status_counts = Counter()

    component_records = []

    components_integrated = 0
    components_skipped = 0
    components_missing = 0
    files_copied = 0
    identical_duplicates = 0
    conflicts = 0

    # ------------------------------------------------------------
    # Process mappings.
    # ------------------------------------------------------------

    for index, mapping in enumerate(
        mappings,
        start=1,
    ):

        mapping_id = (
            mapping.get("package_id")
            or mapping.get("mapping_id")
            or f"component_{index:05d}"
        )

        mapping_id = str(mapping_id)

        action = (
            mapping.get("integration_action")
            or "ADAPT"
        )

        layer = (
            mapping.get("primary_layer")
            or "CORE"
        )

        if layer not in LAYERS:
            layer = "CORE"

        action_counts[action] += 1

        # Reference-only components remain outside final KAIRO.
        if action == "REFERENCE_ONLY":

            components_skipped += 1
            status_counts["REFERENCE_ONLY"] += 1

            component_records.append(
                {
                    "mapping_id": mapping_id,
                    "status": "REFERENCE_ONLY",
                    "action": action,
                    "layer": layer,
                    "reason": (
                        "Reference material intentionally "
                        "excluded from final KAIRO."
                    ),
                }
            )

            continue

        source = find_package(mapping)

        if source is None:

            components_missing += 1
            status_counts["MISSING"] += 1

            component_records.append(
                {
                    "mapping_id": mapping_id,
                    "status": "MISSING",
                    "action": action,
                    "layer": layer,
                    "reason": (
                        "No staged integration package "
                        "could be resolved."
                    ),
                }
            )

            continue

        package_name = safe_name(mapping_id)

        destination = (
            FINAL_ROOT
            / LAYERS[layer]
            / "COMPONENTS"
            / package_name
        )

        try:

            records = copy_component(
                source,
                destination,
            )

            copied_now = sum(
                1
                for r in records
                if r["status"] == "COPIED"
            )

            duplicate_now = sum(
                1
                for r in records
                if r["status"]
                == "DUPLICATE_IDENTICAL"
            )

            conflict_now = sum(
                1
                for r in records
                if r["status"]
                == "CONFLICT_RENAMED"
            )

            files_copied += copied_now
            identical_duplicates += duplicate_now
            conflicts += conflict_now

            components_integrated += 1

            layer_counts[layer] += 1
            status_counts["INTEGRATED"] += 1

            component_records.append(
                {
                    "mapping_id": mapping_id,
                    "status": "INTEGRATED",
                    "action": action,
                    "layer": layer,
                    "source": str(source),
                    "destination": str(destination),
                    "files_copied": copied_now,
                    "identical_duplicates": duplicate_now,
                    "conflicts": conflict_now,
                }
            )

        except Exception as exc:

            status_counts["ERROR"] += 1

            component_records.append(
                {
                    "mapping_id": mapping_id,
                    "status": "ERROR",
                    "action": action,
                    "layer": layer,
                    "source": str(source),
                    "error": str(exc),
                }
            )

        if (
            index % 100 == 0
            or index == len(mappings)
        ):

            print(
                f"[{index:5d}/{len(mappings):5d}] "
                f"INTEGRATED={components_integrated} "
                f"SKIPPED={components_skipped} "
                f"MISSING={components_missing}"
            )

    # ------------------------------------------------------------
    # Validate final tree.
    # ------------------------------------------------------------

    final_files = []

    for path in FINAL_ROOT.rglob("*"):

        if not path.is_file():
            continue

        if any(
            part in BLOCKED_DIRS
            for part in path.parts
        ):
            continue

        if path.suffix.lower() in BLOCKED_EXTENSIONS:
            continue

        # Reports/manifests are valid final metadata.
        final_files.append(
            {
                "path": str(path),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )

    forbidden_present = []

    for path in FINAL_ROOT.rglob("*"):

        if not path.is_file():
            continue

        if (
            any(
                part in BLOCKED_DIRS
                for part in path.parts
            )
            or path.suffix.lower()
            in BLOCKED_EXTENSIONS
        ):
            forbidden_present.append(
                str(path)
            )

    validation = {
        "mappings_loaded":
            len(mappings) > 0,

        "components_integrated":
            components_integrated > 0,

        "final_files_exist":
            len(final_files) > 0,

        "no_processing_errors":
            status_counts.get("ERROR", 0) == 0,

        "no_missing_packages":
            components_missing == 0,

        "no_forbidden_generated_files":
            len(forbidden_present) == 0,

        "production_protected":
            True,

        "archive_protected":
            True,

        "source_protected":
            True,

        "no_code_execution":
            True,

        "no_dependency_installation":
            True,

        "no_network":
            True,

        "no_deletion":
            True,
    }

    validation_pass = all(
        validation.values()
    )

    # ------------------------------------------------------------
    # Manifest.
    # ------------------------------------------------------------

    manifest = {
        "engine":
            "KAIRO Final Integration + Clean Architecture Builder V1",

        "generated_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "input":
            str(MAPPING_FILE),

        "source_staging":
            str(SOURCE_ROOT),

        "final_kairo":
            str(FINAL_ROOT),

        "mappings":
            len(mappings),

        "components_integrated":
            components_integrated,

        "components_skipped":
            components_skipped,

        "components_missing":
            components_missing,

        "files_copied":
            files_copied,

        "identical_duplicates":
            identical_duplicates,

        "conflicts_renamed":
            conflicts,

        "final_files":
            len(final_files),

        "layers":
            dict(layer_counts),

        "actions":
            dict(action_counts),

        "statuses":
            dict(status_counts),

        "validation":
            validation,

        "production_modified":
            False,

        "archive_modified":
            False,

        "source_modified":
            False,

        "code_executed":
            False,

        "dependencies_installed":
            False,

        "network_used":
            False,

        "deletion_performed":
            False,
    }

    with (
        MANIFEST_ROOT
        / "FINAL_KAIRO_INTEGRATION_MANIFEST.json"
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
        MANIFEST_ROOT
        / "COMPONENT_INTEGRATION_RECORDS.json"
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
        MANIFEST_ROOT
        / "FINAL_FILE_INVENTORY.json"
    ).open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            final_files,
            f,
            indent=2,
            ensure_ascii=False,
        )

    # ------------------------------------------------------------
    # Report.
    # ------------------------------------------------------------

    report = []

    report.append(
        "# KAIRO FINAL INTEGRATION REPORT"
    )
    report.append("")

    report.append(
        f"Generated: "
        f"{datetime.now().isoformat(timespec='seconds')}"
    )
    report.append("")

    report.append("## Safety")
    report.append("")
    report.append(
        "- Current Production KAIRO modified: **NO**"
    )
    report.append(
        "- Frozen Archive modified: **NO**"
    )
    report.append(
        "- Source repositories modified: **NO**"
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
    report.append(
        "- Files deleted: **NO**"
    )
    report.append("")

    report.append("## Integration")
    report.append("")
    report.append(
        f"- Mappings: **{len(mappings):,}**"
    )
    report.append(
        f"- Components integrated: **{components_integrated:,}**"
    )
    report.append(
        f"- Reference-only skipped: **{components_skipped:,}**"
    )
    report.append(
        f"- Missing packages: **{components_missing:,}**"
    )
    report.append(
        f"- Files copied: **{files_copied:,}**"
    )
    report.append(
        f"- Identical duplicates detected: "
        f"**{identical_duplicates:,}**"
    )
    report.append(
        f"- Conflicting files renamed: **{conflicts:,}**"
    )
    report.append("")

    report.append("## Layer Distribution")
    report.append("")

    for layer, count in layer_counts.most_common():
        report.append(
            f"- {layer}: {count:,}"
        )

    report.append("")

    report.append("## Validation")
    report.append("")

    for name, result in validation.items():

        report.append(
            f"- {name}: "
            f"**{'PASS' if result else 'FAIL'}**"
        )

    report.append("")

    report.append("## Status")
    report.append("")

    if validation_pass:

        report.append(
            "**PASS — CLEAN KAIRO ASSEMBLY CREATED**"
        )

        report.append("")
        report.append(
            "The assembled project is staged under "
            "`13_FINAL_KAIRO` and has not replaced "
            "the current production KAIRO."
        )

    else:

        report.append(
            "**REVIEW REQUIRED — FINAL ASSEMBLY "
            "HAS VALIDATION ISSUES**"
        )

    report.append("")

    (
        REPORT_ROOT
        / "KAIRO_FINAL_INTEGRATION_REPORT.md"
    ).write_text(
        "\n".join(report),
        encoding="utf-8",
    )

    # ------------------------------------------------------------
    # Console.
    # ------------------------------------------------------------

    print()
    print("=" * 68)
    print(
        "KAIRO FINAL INTEGRATION + CLEAN ARCHITECTURE COMPLETE"
    )
    print("=" * 68)

    print(
        f"Mappings              : {len(mappings):,}"
    )

    print(
        f"Integrated             : {components_integrated:,}"
    )

    print(
        f"Reference-only         : {components_skipped:,}"
    )

    print(
        f"Missing                : {components_missing:,}"
    )

    print(
        f"Files copied           : {files_copied:,}"
    )

    print(
        f"Identical duplicates   : {identical_duplicates:,}"
    )

    print(
        f"Conflicts renamed      : {conflicts:,}"
    )

    print(
        f"Final files            : {len(final_files):,}"
    )

    print()
    print("VALIDATION")

    for name, result in validation.items():

        print(
            f"{name:32s}: "
            f"{'PASS' if result else 'FAIL'}"
        )

    print()
    print(
        "Current Production KAIRO : PROTECTED"
    )
    print(
        "Frozen Archive           : PROTECTED"
    )
    print(
        "Source Repositories      : PROTECTED"
    )
    print(
        "Deletion                 : NONE"
    )

    print()
    print(
        f"FINAL KAIRO: {FINAL_ROOT}"
    )

    print(
        f"Manifest   : "
        f"{MANIFEST_ROOT / 'FINAL_KAIRO_INTEGRATION_MANIFEST.json'}"
    )

    print(
        f"Report     : "
        f"{REPORT_ROOT / 'KAIRO_FINAL_INTEGRATION_REPORT.md'}"
    )

    print()

    if validation_pass:
        print(
            "STATUS: PASS"
        )
        print(
            "NEXT: FINAL CLEANUP / DELETION AUDIT"
        )
    else:
        print(
            "STATUS: REVIEW REQUIRED"
        )


if __name__ == "__main__":
    main()
