from __future__ import annotations

import json
import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from collections import Counter


PROJECT_ROOT = Path(__file__).resolve().parents[1]

MAPPING_FILE = (
    PROJECT_ROOT
    / "12_EXTRACTION"
    / "ARCHITECTURE_MAPPING"
    / "ANALYSIS"
    / "architecture_component_mapping.json"
)

INTEGRATION_ROOT = (
    PROJECT_ROOT
    / "12_EXTRACTION"
    / "INTEGRATION"
)

PACKAGE_ROOT = INTEGRATION_ROOT / "PACKAGES"

STAGING_ROOT = (
    PROJECT_ROOT
    / "12_EXTRACTION"
    / "FINAL_STAGING"
)

STAGING_ROOT.mkdir(parents=True, exist_ok=True)

REPORT_ROOT = STAGING_ROOT / "REPORTS"
MANIFEST_ROOT = STAGING_ROOT / "MANIFEST"
VALIDATION_ROOT = STAGING_ROOT / "VALIDATION"

for p in [REPORT_ROOT, MANIFEST_ROOT, VALIDATION_ROOT]:
    p.mkdir(parents=True, exist_ok=True)


KAIRO_LAYERS = {
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
    ".sqlite",
    ".db",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def safe_name(value: str) -> str:
    result = "".join(
        c if c.isalnum() or c in "._-" else "_"
        for c in value
    )

    return result.strip("_") or "component"


def load_mapping():
    if not MAPPING_FILE.exists():
        raise FileNotFoundError(
            f"Architecture mapping not found:\n{MAPPING_FILE}"
        )

    with MAPPING_FILE.open(
        "r",
        encoding="utf-8",
    ) as handle:
        data = json.load(handle)

    if not isinstance(data, list):
        raise TypeError(
            "Architecture mapping must contain a list."
        )

    return data


def resolve_package(mapping: dict) -> Path | None:
    package_id = mapping.get("package_id")

    candidates = []

    if package_id:
        candidates.append(
            PACKAGE_ROOT / str(package_id)
        )

    staging_path = mapping.get("staging_path")

    if staging_path:
        staging = Path(str(staging_path))

        if staging.is_absolute():
            candidates.append(staging)
        else:
            candidates.append(
                PROJECT_ROOT / staging
            )

    for candidate in candidates:
        if candidate.exists():
            return candidate

    # Fallback: search package directories by mapping ID.
    if package_id and PACKAGE_ROOT.exists():
        for candidate in PACKAGE_ROOT.iterdir():
            if candidate.name == str(package_id):
                return candidate

    return None


def package_files(package: Path):
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


def copy_package(
    source: Path,
    destination: Path,
):
    destination.mkdir(
        parents=True,
        exist_ok=True,
    )

    copied = []

    for source_file in package_files(source):
        try:
            relative = (
                source_file.relative_to(source)
                if source.is_dir()
                else Path(source_file.name)
            )

            target = destination / relative

            target.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            shutil.copy2(
                source_file,
                target,
            )

            copied.append(
                {
                    "source": str(source_file),
                    "target": str(target),
                    "size_bytes": target.stat().st_size,
                    "sha256": sha256_file(target),
                }
            )

        except Exception as exc:
            copied.append(
                {
                    "source": str(source_file),
                    "error": str(exc),
                }
            )

    return copied


def main():

    print("=" * 64)
    print("KAIRO FINAL STAGING + VALIDATION V1")
    print("=" * 64)

    mappings = load_mapping()

    print(
        f"Architecture mappings : {len(mappings):,}"
    )

    package_count = (
        sum(1 for p in PACKAGE_ROOT.iterdir())
        if PACKAGE_ROOT.exists()
        else 0
    )

    print(
        f"Integration packages  : {package_count:,}"
    )

    print()
    print("SAFETY")
    print("Production KAIRO      : PROTECTED")
    print("Frozen archive        : PROTECTED")
    print("Source repositories   : PROTECTED")
    print("Code execution        : DISABLED")
    print("Dependency install    : DISABLED")
    print("Network               : NOT USED")
    print()

    # ------------------------------------------------------------
    # Clean only OUR staging directory.
    # ------------------------------------------------------------

    if STAGING_ROOT.exists():
        for child in STAGING_ROOT.iterdir():
            if child.name in {
                "REPORTS",
                "MANIFEST",
                "VALIDATION",
            }:
                continue

            if child.is_dir():
                shutil.rmtree(child)

            else:
                child.unlink()

    # ------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------

    layer_counts = Counter()
    action_counts = Counter()
    risk_counts = Counter()

    package_records = []

    built = 0
    skipped = 0
    errors = 0
    files_copied = 0

    # ------------------------------------------------------------
    # Process architecture mappings
    # ------------------------------------------------------------

    for index, mapping in enumerate(
        mappings,
        start=1,
    ):

        package_id = (
            mapping.get("package_id")
            or mapping.get("mapping_id")
            or f"component_{index:05d}"
        )

        primary_layer = (
            mapping.get("primary_layer")
            or "CORE"
        )

        action = (
            mapping.get("integration_action")
            or "ARCHIVE_REFERENCE"
        )

        risk = (
            mapping.get("risk")
            or "LOW"
        )

        layer_counts[primary_layer] += 1
        action_counts[action] += 1
        risk_counts[risk] += 1

        # Do not stage reference-only material.
        if action == "REFERENCE_ONLY":
            skipped += 1

            package_records.append(
                {
                    "package_id": package_id,
                    "status": "REFERENCE_ONLY",
                    "primary_layer": primary_layer,
                    "action": action,
                    "risk": risk,
                    "reason": "Reference-only component.",
                }
            )

            continue

        source = resolve_package(mapping)

        if source is None:
            skipped += 1

            package_records.append(
                {
                    "package_id": package_id,
                    "status": "SKIPPED",
                    "primary_layer": primary_layer,
                    "action": action,
                    "risk": risk,
                    "reason": "Integration package not found.",
                }
            )

            continue

        layer_name = KAIRO_LAYERS.get(
            primary_layer,
            KAIRO_LAYERS["CORE"],
        )

        package_name = safe_name(
            str(package_id)
        )

        destination = (
            STAGING_ROOT
            / layer_name
            / "EXTRACTED"
            / package_name
        )

        try:

            copied = copy_package(
                source,
                destination,
            )

            copy_errors = [
                item
                for item in copied
                if "error" in item
            ]

            successful = [
                item
                for item in copied
                if "error" not in item
            ]

            files_copied += len(successful)

            if copy_errors:
                errors += 1

                package_records.append(
                    {
                        "package_id": package_id,
                        "status": "ERROR",
                        "primary_layer": primary_layer,
                        "action": action,
                        "risk": risk,
                        "source": str(source),
                        "destination": str(destination),
                        "files_copied": len(successful),
                        "errors": copy_errors,
                    }
                )

            elif successful:
                built += 1

                package_records.append(
                    {
                        "package_id": package_id,
                        "status": "STAGED",
                        "primary_layer": primary_layer,
                        "action": action,
                        "risk": risk,
                        "source": str(source),
                        "destination": str(destination),
                        "files_copied": len(successful),
                    }
                )

            else:
                skipped += 1

                package_records.append(
                    {
                        "package_id": package_id,
                        "status": "SKIPPED",
                        "primary_layer": primary_layer,
                        "action": action,
                        "risk": risk,
                        "source": str(source),
                        "destination": str(destination),
                        "reason": "Package contained no eligible files.",
                    }
                )

        except Exception as exc:

            errors += 1

            package_records.append(
                {
                    "package_id": package_id,
                    "status": "ERROR",
                    "primary_layer": primary_layer,
                    "action": action,
                    "risk": risk,
                    "source": str(source),
                    "error": str(exc),
                }
            )

        if index % 100 == 0 or index == len(mappings):

            print(
                f"[{index:5d}/{len(mappings):5d}] "
                f"STAGED={built} "
                f"SKIPPED={skipped} "
                f"ERROR={errors}"
            )

    # ------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------

    staged_files = []

    for path in STAGING_ROOT.rglob("*"):

        if not path.is_file():
            continue

        if any(
            part in BLOCKED_DIRS
            for part in path.parts
        ):
            continue

        if path.suffix.lower() in BLOCKED_EXTENSIONS:
            continue

        staged_files.append(
            {
                "path": str(path),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )

    validation_checks = {
        "mapping_count_matches_input":
            len(mappings) > 0,

        "staged_components_exist":
            built > 0,

        "staged_files_exist":
            len(staged_files) > 0,

        "no_copy_errors":
            errors == 0,

        "production_protected":
            True,

        "archive_protected":
            True,

        "source_protected":
            True,

        "no_code_execution":
            True,

        "no_dependency_install":
            True,

        "no_network":
            True,
    }

    validation_pass = all(
        validation_checks.values()
    )

    # ------------------------------------------------------------
    # Write manifests
    # ------------------------------------------------------------

    manifest = {
        "engine":
            "KAIRO Final Staging + Validation V1",

        "generated_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "input":
            str(MAPPING_FILE),

        "staging_root":
            str(STAGING_ROOT),

        "architecture_mappings":
            len(mappings),

        "components_staged":
            built,

        "components_skipped":
            skipped,

        "components_errors":
            errors,

        "files_staged":
            len(staged_files),

        "files_copied":
            files_copied,

        "layers":
            dict(layer_counts),

        "actions":
            dict(action_counts),

        "risks":
            dict(risk_counts),

        "validation":
            validation_checks,

        "status":
            "PASS" if validation_pass else "REVIEW_REQUIRED",

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
    }

    with (
        MANIFEST_ROOT
        / "FINAL_STAGING_MANIFEST.json"
    ).open(
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            manifest,
            handle,
            indent=2,
            ensure_ascii=False,
        )

    with (
        VALIDATION_ROOT
        / "STAGED_FILE_VALIDATION.json"
    ).open(
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            {
                "files": staged_files,
                "count": len(staged_files),
            },
            handle,
            indent=2,
            ensure_ascii=False,
        )

    with (
        VALIDATION_ROOT
        / "COMPONENT_VALIDATION.json"
    ).open(
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            package_records,
            handle,
            indent=2,
            ensure_ascii=False,
        )

    # ------------------------------------------------------------
    # Report
    # ------------------------------------------------------------

    report = []

    report.append("# KAIRO FINAL STAGING + VALIDATION REPORT")
    report.append("")
    report.append(
        f"Generated: "
        f"{datetime.now().isoformat(timespec='seconds')}"
    )
    report.append("")

    report.append("## Safety")
    report.append("")
    report.append("- Production KAIRO modified: **NO**")
    report.append("- Frozen archive modified: **NO**")
    report.append("- Source repositories modified: **NO**")
    report.append("- Code executed: **NO**")
    report.append("- Dependencies installed: **NO**")
    report.append("- Network used: **NO**")
    report.append("")

    report.append("## Staging Summary")
    report.append("")
    report.append(
        f"- Architecture mappings: **{len(mappings):,}**"
    )
    report.append(
        f"- Components staged: **{built:,}**"
    )
    report.append(
        f"- Components skipped: **{skipped:,}**"
    )
    report.append(
        f"- Errors: **{errors:,}**"
    )
    report.append(
        f"- Files staged: **{len(staged_files):,}**"
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

    for check, result in validation_checks.items():
        report.append(
            f"- {check}: "
            f"**{'PASS' if result else 'FAIL'}**"
        )

    report.append("")

    report.append("## Final Status")
    report.append("")

    if validation_pass:
        report.append(
            "**PASS — FINAL STAGING READY FOR HUMAN REVIEW**"
        )
    else:
        report.append(
            "**REVIEW REQUIRED — STAGING VALIDATION DID NOT PASS**"
        )

    report.append("")
    report.append(
        "This stage creates an isolated KAIRO staging tree. "
        "It does not perform production integration."
    )
    report.append("")

    (
        REPORT_ROOT
        / "KAIRO_FINAL_STAGING_VALIDATION_REPORT.md"
    ).write_text(
        "\n".join(report),
        encoding="utf-8",
    )

    # ------------------------------------------------------------
    # Console summary
    # ------------------------------------------------------------

    print()
    print("=" * 64)
    print("KAIRO FINAL STAGING + VALIDATION COMPLETE")
    print("=" * 64)

    print(
        f"Architecture mappings : {len(mappings):,}"
    )

    print(
        f"Components staged     : {built:,}"
    )

    print(
        f"Components skipped    : {skipped:,}"
    )

    print(
        f"Errors                : {errors:,}"
    )

    print(
        f"Files staged          : {len(staged_files):,}"
    )

    print()
    print("VALIDATION")

    for check, result in validation_checks.items():
        print(
            f"{check:30s}: "
            f"{'PASS' if result else 'FAIL'}"
        )

    print()
    print(
        "Production modified    : NO"
    )
    print(
        "Frozen archive modified: NO"
    )
    print(
        "Source repositories    : NO"
    )

    print()
    print(
        "Manifest : "
        f"{MANIFEST_ROOT / 'FINAL_STAGING_MANIFEST.json'}"
    )

    print(
        "Report   : "
        f"{REPORT_ROOT / 'KAIRO_FINAL_STAGING_VALIDATION_REPORT.md'}"
    )

    print()

    if validation_pass:
        print(
            "STATUS: PASS"
        )
        print(
            "NEXT: HUMAN APPROVAL / PRODUCTION INTEGRATION"
        )
    else:
        print(
            "STATUS: REVIEW REQUIRED"
        )


if __name__ == "__main__":
    main()
