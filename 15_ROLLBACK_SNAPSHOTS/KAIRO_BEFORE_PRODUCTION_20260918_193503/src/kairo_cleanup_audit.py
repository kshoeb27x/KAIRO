from __future__ import annotations

import json
import hashlib
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime


ROOT = Path(__file__).resolve().parents[1]

FINAL_KAIRO = ROOT / "13_FINAL_KAIRO"
EXTRACTION = ROOT / "12_EXTRACTION"
SOURCE_REPOS = ROOT / "00_FOUNDATION" / "Architecture" / "Old_Repositories"
FROZEN_ARCHIVE = ROOT / "11_ARCHIVE" / "Original_Repositories"

OUTPUT = ROOT / "12_EXTRACTION" / "CLEANUP_AUDIT"
REPORTS = OUTPUT / "REPORTS"
MANIFEST = OUTPUT / "MANIFEST"

REPORTS.mkdir(parents=True, exist_ok=True)
MANIFEST.mkdir(parents=True, exist_ok=True)


PROTECTED_ROOTS = {
    FROZEN_ARCHIVE.resolve(),
    SOURCE_REPOS.resolve(),
}

GENERATED_DIRS = {
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
    ".parcel-cache",
}

GENERATED_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".log",
    ".tmp",
    ".cache",
    ".bak",
}

REFERENCE_NAMES = {
    "readme.md",
    "readme.txt",
    "license",
    "license.txt",
    "license.md",
    "changelog.md",
    "changes.md",
}

CONFIG_NAMES = {
    ".env.example",
    ".env.template",
    "config.example.json",
    "config.example.yaml",
    "config.example.yml",
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


def is_protected(path: Path) -> bool:
    try:
        resolved = path.resolve()

        for protected in PROTECTED_ROOTS:
            try:
                resolved.relative_to(protected)
                return True
            except ValueError:
                pass

        return False

    except Exception:
        return True


def has_generated_parent(path: Path) -> bool:
    return any(
        part in GENERATED_DIRS
        for part in path.parts
    )


def classify(path: Path, root_name: str) -> str:

    if is_protected(path):
        return "PROTECTED"

    if has_generated_parent(path):
        return "GENERATED"

    if path.suffix.lower() in GENERATED_EXTENSIONS:
        return "GENERATED"

    name = path.name.lower()

    if name in CONFIG_NAMES:
        return "CONFIG_TEMPLATE"

    if name in REFERENCE_NAMES:
        return "REFERENCE"

    if root_name == "13_FINAL_KAIRO":
        return "INTEGRATED"

    if root_name == "12_EXTRACTION":
        return "EXTRACTION_ARTIFACT"

    return "REVIEW"


def collect_files(root: Path, root_name: str):

    records = []

    if not root.exists():
        return records

    for path in root.rglob("*"):

        if not path.is_file():
            continue

        category = classify(
            path,
            root_name,
        )

        try:
            size = path.stat().st_size
        except Exception:
            size = 0

        records.append(
            {
                "path": str(path),
                "root": root_name,
                "category": category,
                "name": path.name,
                "extension": path.suffix.lower(),
                "size_bytes": size,
                "sha256": sha256(path),
            }
        )

    return records


def main():

    print("=" * 68)
    print("KAIRO CLEANUP + DELETION AUDIT V1")
    print("=" * 68)

    print()
    print("SAFETY")
    print("Deletion                  : DISABLED")
    print("Production modification  : DISABLED")
    print("Source repositories      : PROTECTED")
    print("Frozen archive            : PROTECTED")
    print("Code execution            : DISABLED")
    print("Dependency installation   : DISABLED")
    print("Network                   : NOT USED")
    print()

    roots = [
        (FINAL_KAIRO, "13_FINAL_KAIRO"),
        (EXTRACTION, "12_EXTRACTION"),
        (SOURCE_REPOS, "00_SOURCE_REPOSITORIES"),
        (FROZEN_ARCHIVE, "11_FROZEN_ARCHIVE"),
    ]

    all_records = []

    for root, name in roots:

        print(
            f"Scanning: {name}"
        )

        records = collect_files(
            root,
            name,
        )

        print(
            f"  Files: {len(records):,}"
        )

        all_records.extend(records)

    print()
    print(
        f"Total files scanned: {len(all_records):,}"
    )

    # ------------------------------------------------------------
    # Exact duplicates
    # ------------------------------------------------------------

    by_hash = defaultdict(list)

    for record in all_records:

        digest = record["sha256"]

        if digest:
            by_hash[digest].append(
                record["path"]
            )

    duplicate_groups = []

    for digest, paths in by_hash.items():

        if len(paths) < 2:
            continue

        protected = any(
            is_protected(Path(p))
            for p in paths
        )

        duplicate_groups.append(
            {
                "sha256": digest,
                "count": len(paths),
                "protected": protected,
                "paths": paths,
            }
        )

    # ------------------------------------------------------------
    # Category counts
    # ------------------------------------------------------------

    category_counts = Counter(
        r["category"]
        for r in all_records
    )

    root_counts = Counter(
        r["root"]
        for r in all_records
    )

    # ------------------------------------------------------------
    # Cleanup candidates
    # ------------------------------------------------------------

    cleanup_candidates = []

    for record in all_records:

        category = record["category"]
        path = Path(record["path"])

        if category == "GENERATED":

            cleanup_candidates.append(
                {
                    **record,
                    "decision": "SAFE_TO_DELETE",
                    "reason": (
                        "Generated/cache/build artifact."
                    ),
                }
            )

        elif category == "EXTRACTION_ARTIFACT":

            cleanup_candidates.append(
                {
                    **record,
                    "decision": "REVIEW_REQUIRED",
                    "reason": (
                        "Extraction workspace material. "
                        "Must remain until final build "
                        "provenance is confirmed."
                    ),
                }
            )

        elif category == "CONFIG_TEMPLATE":

            cleanup_candidates.append(
                {
                    **record,
                    "decision": "KEEP_REFERENCE",
                    "reason": (
                        "Configuration template may be "
                        "required for deployment/adaptation."
                    ),
                }
            )

        elif category == "REFERENCE":

            cleanup_candidates.append(
                {
                    **record,
                    "decision": "KEEP_REFERENCE",
                    "reason": (
                        "Documentation/reference material."
                    ),
                }
            )

        elif category == "PROTECTED":

            cleanup_candidates.append(
                {
                    **record,
                    "decision": "PROTECTED",
                    "reason": (
                        "Source repository or frozen archive."
                    ),
                }
            )

    # ------------------------------------------------------------
    # Duplicate deletion recommendations
    # ------------------------------------------------------------

    duplicate_delete_candidates = []

    for group in duplicate_groups:

        paths = [
            Path(p)
            for p in group["paths"]
        ]

        # Never recommend deletion from protected trees.
        unprotected = [
            p
            for p in paths
            if not is_protected(p)
        ]

        if len(unprotected) < 2:
            continue

        # Prefer final KAIRO over extraction material.
        def priority(p: Path):

            text = str(p)

            if "13_FINAL_KAIRO" in text:
                return 0

            if "12_EXTRACTION" in text:
                return 1

            return 2

        ordered = sorted(
            unprotected,
            key=priority,
        )

        keep = ordered[0]

        for duplicate in ordered[1:]:

            duplicate_delete_candidates.append(
                {
                    "sha256": group["sha256"],
                    "keep": str(keep),
                    "candidate_delete": str(
                        duplicate
                    ),
                    "decision": "REVIEW_REQUIRED",
                    "reason": (
                        "Identical content exists elsewhere; "
                        "delete only after dependency/provenance "
                        "verification."
                    ),
                }
            )

    # ------------------------------------------------------------
    # Final KAIRO inventory
    # ------------------------------------------------------------

    final_records = [
        r
        for r in all_records
        if r["root"] == "13_FINAL_KAIRO"
    ]

    final_extensions = Counter(
        r["extension"]
        for r in final_records
    )

    final_size = sum(
        r["size_bytes"]
        for r in final_records
    )

    # ------------------------------------------------------------
    # Extraction inventory
    # ------------------------------------------------------------

    extraction_records = [
        r
        for r in all_records
        if r["root"] == "12_EXTRACTION"
    ]

    # ------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------

    manifest = {
        "engine":
            "KAIRO Cleanup + Deletion Audit V1",

        "generated_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "files_scanned":
            len(all_records),

        "category_counts":
            dict(category_counts),

        "root_counts":
            dict(root_counts),

        "duplicate_groups":
            len(duplicate_groups),

        "duplicate_delete_candidates":
            len(duplicate_delete_candidates),

        "cleanup_candidates":
            len(cleanup_candidates),

        "final_kairo_files":
            len(final_records),

        "final_kairo_size_bytes":
            final_size,

        "final_kairo_extensions":
            dict(final_extensions),

        "safety": {
            "deletion_performed": False,
            "production_modified": False,
            "source_modified": False,
            "archive_modified": False,
            "code_executed": False,
            "dependencies_installed": False,
            "network_used": False,
        },
    }

    with (
        MANIFEST
        / "CLEANUP_AUDIT_MANIFEST.json"
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
        / "CLEANUP_CANDIDATES.json"
    ).open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            cleanup_candidates,
            f,
            indent=2,
            ensure_ascii=False,
        )

    with (
        MANIFEST
        / "DUPLICATE_GROUPS.json"
    ).open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            duplicate_groups,
            f,
            indent=2,
            ensure_ascii=False,
        )

    with (
        MANIFEST
        / "DUPLICATE_DELETE_CANDIDATES.json"
    ).open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            duplicate_delete_candidates,
            f,
            indent=2,
            ensure_ascii=False,
        )

    with (
        MANIFEST
        / "FINAL_KAIRO_INVENTORY.json"
    ).open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            final_records,
            f,
            indent=2,
            ensure_ascii=False,
        )

    # ------------------------------------------------------------
    # Human-readable report
    # ------------------------------------------------------------

    report = []

    report.append(
        "# KAIRO CLEANUP + DELETION AUDIT REPORT"
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
        "- Deletion performed: **NO**"
    )
    report.append(
        "- Production modified: **NO**"
    )
    report.append(
        "- Source repositories modified: **NO**"
    )
    report.append(
        "- Frozen archive modified: **NO**"
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

    report.append("## Inventory")
    report.append("")

    report.append(
        f"- Total files scanned: "
        f"**{len(all_records):,}**"
    )

    report.append(
        f"- Final KAIRO files: "
        f"**{len(final_records):,}**"
    )

    report.append(
        f"- Final KAIRO size: "
        f"**{final_size:,} bytes**"
    )

    report.append(
        f"- Extraction files: "
        f"**{len(extraction_records):,}**"
    )

    report.append("")

    report.append("## Categories")
    report.append("")

    for category, count in category_counts.most_common():

        report.append(
            f"- {category}: **{count:,}**"
        )

    report.append("")

    report.append("## Exact Duplicate Analysis")
    report.append("")

    report.append(
        f"- Duplicate groups: "
        f"**{len(duplicate_groups):,}**"
    )

    report.append(
        f"- Potential duplicate cleanup candidates: "
        f"**{len(duplicate_delete_candidates):,}**"
    )

    report.append("")

    report.append("## Cleanup Decisions")
    report.append("")

    decisions = Counter(
        item["decision"]
        for item in cleanup_candidates
    )

    for decision, count in decisions.most_common():

        report.append(
            f"- {decision}: **{count:,}**"
        )

    report.append("")

    report.append("## Final KAIRO File Types")
    report.append("")

    for extension, count in final_extensions.most_common():

        display = extension or "[no extension]"

        report.append(
            f"- `{display}`: **{count:,}**"
        )

    report.append("")

    report.append("## Protected Areas")
    report.append("")

    report.append(
        "The following areas are NEVER cleanup targets:"
    )
    report.append("")
    report.append(
        "- `11_ARCHIVE\\Original_Repositories`"
    )
    report.append(
        "- `00_FOUNDATION\\Architecture\\Old_Repositories`"
    )
    report.append("")

    report.append("## Important")
    report.append("")

    report.append(
        "This audit does not prove that a file is unused "
        "merely because it appears redundant. Deletion "
        "requires dependency/provenance verification."
    )
    report.append("")

    report.append("## Status")
    report.append("")

    report.append(
        "**AUDIT COMPLETE — NO DELETIONS PERFORMED**"
    )
    report.append("")

    (
        REPORTS
        / "KAIRO_CLEANUP_AUDIT_REPORT.md"
    ).write_text(
        "\n".join(report),
        encoding="utf-8",
    )

    # ------------------------------------------------------------
    # Console output
    # ------------------------------------------------------------

    print()
    print("=" * 68)
    print("KAIRO CLEANUP AUDIT COMPLETE")
    print("=" * 68)

    print(
        f"Files scanned              : {len(all_records):,}"
    )

    print(
        f"Final KAIRO files          : {len(final_records):,}"
    )

    print(
        f"Extraction files            : {len(extraction_records):,}"
    )

    print(
        f"Duplicate groups            : {len(duplicate_groups):,}"
    )

    print(
        f"Duplicate cleanup candidates: "
        f"{len(duplicate_delete_candidates):,}"
    )

    print()
    print("DECISIONS")

    for decision, count in decisions.most_common():

        print(
            f"{decision:28s}: {count:,}"
        )

    print()
    print("SAFETY")

    print(
        "Deletion performed          : NO"
    )

    print(
        "Production modified         : NO"
    )

    print(
        "Source repositories         : PROTECTED"
    )

    print(
        "Frozen archive              : PROTECTED"
    )

    print()
    print(
        f"Manifest: "
        f"{MANIFEST / 'CLEANUP_AUDIT_MANIFEST.json'}"
    )

    print(
        f"Report  : "
        f"{REPORTS / 'KAIRO_CLEANUP_AUDIT_REPORT.md'}"
    )

    print()
    print(
        "STATUS: AUDIT COMPLETE"
    )

    print(
        "NEXT: REVIEW CLEANUP PLAN"
    )


if __name__ == "__main__":
    main()
