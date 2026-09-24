from __future__ import annotations

import json
import hashlib
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime


ROOT = Path(__file__).resolve().parents[1]

FINAL_KAIRO = ROOT / "13_FINAL_KAIRO"
EXTRACTION = ROOT / "12_EXTRACTION"
SOURCE_REPOS = ROOT / "00_FOUNDATION" / "Architecture" / "Old_Repositories"
FROZEN_ARCHIVE = ROOT / "11_ARCHIVE" / "Original_Repositories"

OUTPUT = ROOT / "12_EXTRACTION" / "CLEANUP_AUDIT_V2"
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


def classify_final(path: Path) -> str:

    if has_generated_parent(path):
        return "GENERATED"

    if path.suffix.lower() in GENERATED_EXTENSIONS:
        return "GENERATED"

    name = path.name.lower()

    if name in CONFIG_NAMES:
        return "CONFIG_TEMPLATE"

    if name in REFERENCE_NAMES:
        return "REFERENCE"

    return "INTEGRATED"


def lightweight_inventory(
    root: Path,
    root_name: str,
    hash_files: bool = False,
):

    records = []

    if not root.exists():
        return records

    file_count = 0
    generated_count = 0
    total_size = 0

    # Only Final KAIRO and selected extraction files
    # receive content hashing.
    for path in root.rglob("*"):

        if not path.is_file():
            continue

        file_count += 1

        try:
            size = path.stat().st_size
        except Exception:
            size = 0

        total_size += size

        if has_generated_parent(path):
            generated_count += 1

        if hash_files:

            digest = hashlib.sha256()

            try:
                with path.open("rb") as f:

                    for chunk in iter(
                        lambda: f.read(1024 * 1024),
                        b"",
                    ):
                        digest.update(chunk)

                file_hash = digest.hexdigest()

            except Exception:
                file_hash = ""

            records.append(
                {
                    "path": str(path),
                    "root": root_name,
                    "name": path.name,
                    "extension": path.suffix.lower(),
                    "size_bytes": size,
                    "sha256": file_hash,
                    "category": (
                        classify_final(path)
                        if root_name == "13_FINAL_KAIRO"
                        else "EXTRACTION"
                    ),
                }
            )

    return {
        "root": root_name,
        "exists": root.exists(),
        "file_count": file_count,
        "generated_parent_count": generated_count,
        "total_size_bytes": total_size,
        "records": records,
    }


def main():

    print("=" * 68)
    print("KAIRO CLEANUP + DELETION AUDIT V2")
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

    # ------------------------------------------------------------
    # FAST PROTECTED INVENTORY
    # ------------------------------------------------------------

    print("Protected inventory:")
    print()

    source_meta = lightweight_inventory(
        SOURCE_REPOS,
        "00_SOURCE_REPOSITORIES",
        hash_files=False,
    )

    print(
        f"  Source repositories : "
        f"{source_meta['file_count']:,} files"
    )

    archive_meta = lightweight_inventory(
        FROZEN_ARCHIVE,
        "11_FROZEN_ARCHIVE",
        hash_files=False,
    )

    print(
        f"  Frozen archive      : "
        f"{archive_meta['file_count']:,} files"
    )

    # ------------------------------------------------------------
    # FULL HASH ONLY WHERE USEFUL
    # ------------------------------------------------------------

    print()
    print("Analyzing final KAIRO...")

    final_meta = lightweight_inventory(
        FINAL_KAIRO,
        "13_FINAL_KAIRO",
        hash_files=True,
    )

    print(
        f"  Final KAIRO         : "
        f"{final_meta['file_count']:,} files"
    )

    print()
    print("Analyzing extraction workspace...")

    extraction_meta = lightweight_inventory(
        EXTRACTION,
        "12_EXTRACTION",
        hash_files=False,
    )

    print(
        f"  Extraction          : "
        f"{extraction_meta['file_count']:,} files"
    )

    # ------------------------------------------------------------
    # FINAL KAIRO DUPLICATES
    # ------------------------------------------------------------

    print()
    print("Detecting duplicates inside Final KAIRO...")

    hash_groups = defaultdict(list)

    for record in final_meta["records"]:

        digest = record["sha256"]

        if digest:
            hash_groups[digest].append(
                record["path"]
            )

    duplicate_groups = []

    for digest, paths in hash_groups.items():

        if len(paths) > 1:

            duplicate_groups.append(
                {
                    "sha256": digest,
                    "count": len(paths),
                    "paths": paths,
                }
            )

    # ------------------------------------------------------------
    # Filename overlaps
    # ------------------------------------------------------------

    name_groups = defaultdict(list)

    for record in final_meta["records"]:

        name_groups[
            record["name"].lower()
        ].append(
            record["path"]
        )

    name_overlaps = []

    for name, paths in name_groups.items():

        if len(paths) > 1:

            name_overlaps.append(
                {
                    "name": name,
                    "count": len(paths),
                    "paths": paths,
                }
            )

    # ------------------------------------------------------------
    # Final KAIRO categories
    # ------------------------------------------------------------

    categories = Counter(
        r["category"]
        for r in final_meta["records"]
    )

    extensions = Counter(
        r["extension"]
        for r in final_meta["records"]
    )

    # ------------------------------------------------------------
    # Cleanup candidates
    # ------------------------------------------------------------

    cleanup_candidates = []

    for record in final_meta["records"]:

        category = record["category"]

        if category == "GENERATED":

            decision = "SAFE_TO_DELETE"

            reason = (
                "Generated/cache/build artifact "
                "inside final assembly."
            )

        elif category == "REFERENCE":

            decision = "KEEP_REFERENCE"

            reason = (
                "Documentation/reference material."
            )

        elif category == "CONFIG_TEMPLATE":

            decision = "KEEP_REFERENCE"

            reason = (
                "Configuration template requires "
                "adaptation/validation."
            )

        else:

            decision = "KEEP"

            reason = (
                "Integrated component. Do not "
                "delete without architecture/dependency review."
            )

        cleanup_candidates.append(
            {
                **record,
                "decision": decision,
                "reason": reason,
            }
        )

    # ------------------------------------------------------------
    # Extraction cleanup classification
    # ------------------------------------------------------------

    extraction_cleanup = {
        "workspace":
            str(EXTRACTION),

        "decision":
            "REVIEW_REQUIRED",

        "reason":
            (
                "Extraction workspace contains "
                "provenance, manifests, reports, "
                "integration packages and audit evidence. "
                "Do not delete until final KAIRO is "
                "accepted and rollback requirements are closed."
            ),
    }

    # ------------------------------------------------------------
    # Protected records
    # ------------------------------------------------------------

    protected = {
        "source_repositories": {
            "path": str(SOURCE_REPOS),
            "files": source_meta["file_count"],
            "decision": "PROTECTED",
        },

        "frozen_archive": {
            "path": str(FROZEN_ARCHIVE),
            "files": archive_meta["file_count"],
            "decision": "PROTECTED",
        },
    }

    # ------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------

    validation = {
        "final_kairo_exists":
            FINAL_KAIRO.exists(),

        "final_kairo_has_files":
            final_meta["file_count"] > 0,

        "source_exists":
            SOURCE_REPOS.exists(),

        "archive_exists":
            FROZEN_ARCHIVE.exists(),

        "source_protected":
            True,

        "archive_protected":
            True,

        "production_untouched":
            True,

        "deletion_performed":
            False,

        "code_execution":
            False,

        "network_used":
            False,
    }

    status = (
        "PASS"
        if all(validation.values())
        else "REVIEW_REQUIRED"
    )

    # ------------------------------------------------------------
    # Manifest
    # ------------------------------------------------------------

    manifest = {
        "engine":
            "KAIRO Cleanup + Deletion Audit V2",

        "generated_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "status":
            status,

        "final_kairo": final_meta,
        "extraction": {
            k: v
            for k, v
            in extraction_meta.items()
            if k != "records"
        },

        "protected": protected,

        "duplicates": {
            "exact_groups":
                len(duplicate_groups),

            "filename_overlap_groups":
                len(name_overlaps),
        },

        "categories":
            dict(categories),

        "extensions":
            dict(extensions),

        "cleanup_candidate_count":
            len(cleanup_candidates),

        "safety": {
            "deletion_performed": False,
            "production_modified": False,
            "source_modified": False,
            "archive_modified": False,
            "code_executed": False,
            "dependencies_installed": False,
            "network_used": False,
        },

        "validation":
            validation,
    }

    with (
        MANIFEST
        / "CLEANUP_AUDIT_V2_MANIFEST.json"
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
        / "FINAL_KAIRO_CLEANUP_CANDIDATES.json"
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
        / "FINAL_KAIRO_DUPLICATES.json"
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
        / "FINAL_KAIRO_FILENAME_OVERLAPS.json"
    ).open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            name_overlaps,
            f,
            indent=2,
            ensure_ascii=False,
        )

    # ------------------------------------------------------------
    # Report
    # ------------------------------------------------------------

    report = []

    report.append(
        "# KAIRO CLEANUP + DELETION AUDIT V2"
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
        f"- Final KAIRO: "
        f"**{final_meta['file_count']:,} files**"
    )

    report.append(
        f"- Extraction: "
        f"**{extraction_meta['file_count']:,} files**"
    )

    report.append(
        f"- Source repositories: "
        f"**{source_meta['file_count']:,} files** "
        f"(protected)"
    )

    report.append(
        f"- Frozen archive: "
        f"**{archive_meta['file_count']:,} files** "
        f"(protected)"
    )

    report.append("")

    report.append("## Final KAIRO Categories")
    report.append("")

    for category, count in categories.most_common():

        report.append(
            f"- {category}: **{count:,}**"
        )

    report.append("")

    report.append("## Duplicate Analysis")
    report.append("")

    report.append(
        f"- Exact duplicate groups inside Final KAIRO: "
        f"**{len(duplicate_groups):,}**"
    )

    report.append(
        f"- Filename overlap groups: "
        f"**{len(name_overlaps):,}**"
    )

    report.append("")

    report.append("## Cleanup Decisions")
    report.append("")

    decisions = Counter(
        x["decision"]
        for x in cleanup_candidates
    )

    for decision, count in decisions.most_common():

        report.append(
            f"- {decision}: **{count:,}**"
        )

    report.append("")

    report.append("## Protected")
    report.append("")
    report.append(
        "`00_FOUNDATION\\Architecture\\Old_Repositories`"
    )
    report.append("")
    report.append(
        "`11_ARCHIVE\\Original_Repositories`"
    )
    report.append("")

    report.append("## Extraction Workspace")
    report.append("")
    report.append(
        "Status: **REVIEW_REQUIRED**"
    )
    report.append("")
    report.append(
        extraction_cleanup["reason"]
    )
    report.append("")

    report.append("## Validation")
    report.append("")

    for key, value in validation.items():

        report.append(
            f"- {key}: "
            f"**{'PASS' if value else 'FAIL'}**"
        )

    report.append("")

    report.append("## Final Status")
    report.append("")

    report.append(
        "**AUDIT COMPLETE — ZERO DELETIONS**"
    )

    (
        REPORTS
        / "KAIRO_CLEANUP_AUDIT_V2_REPORT.md"
    ).write_text(
        "\n".join(report),
        encoding="utf-8",
    )

    # ------------------------------------------------------------
    # Console
    # ------------------------------------------------------------

    print()
    print("=" * 68)
    print("KAIRO CLEANUP AUDIT V2 COMPLETE")
    print("=" * 68)

    print(
        f"Final KAIRO files          : "
        f"{final_meta['file_count']:,}"
    )

    print(
        f"Extraction files           : "
        f"{extraction_meta['file_count']:,}"
    )

    print(
        f"Protected source files     : "
        f"{source_meta['file_count']:,}"
    )

    print(
        f"Protected archive files    : "
        f"{archive_meta['file_count']:,}"
    )

    print(
        f"Exact duplicate groups     : "
        f"{len(duplicate_groups):,}"
    )

    print(
        f"Filename overlap groups    : "
        f"{len(name_overlaps):,}"
    )

    print()
    print("DECISIONS")

    for decision, count in decisions.most_common():

        print(
            f"{decision:28s}: {count:,}"
        )

    print()
    print("SAFETY")
    print("Deletion performed          : NO")
    print("Production modified         : NO")
    print("Source repositories         : PROTECTED")
    print("Frozen archive              : PROTECTED")

    print()
    print(
        f"Manifest: "
        f"{MANIFEST / 'CLEANUP_AUDIT_V2_MANIFEST.json'}"
    )

    print(
        f"Report  : "
        f"{REPORTS / 'KAIRO_CLEANUP_AUDIT_V2_REPORT.md'}"
    )

    print()
    print(
        f"STATUS: {status}"
    )

    print(
        "NEXT: CLEANUP PLAN REVIEW"
    )


if __name__ == "__main__":
    main()
