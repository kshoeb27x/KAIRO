from __future__ import annotations

import json
from pathlib import Path
from collections import Counter
from datetime import datetime


ROOT = Path(__file__).resolve().parents[1]

EXTRACTION = ROOT / "12_EXTRACTION"
FINAL_KAIRO = ROOT / "13_FINAL_KAIRO"
SOURCE_REPOS = ROOT / "00_FOUNDATION" / "Architecture" / "Old_Repositories"
FROZEN_ARCHIVE = ROOT / "11_ARCHIVE" / "Original_Repositories"

OUTPUT = EXTRACTION / "CLEANUP_PLAN_V1"
REPORTS = OUTPUT / "REPORTS"
MANIFEST = OUTPUT / "MANIFEST"

REPORTS.mkdir(parents=True, exist_ok=True)
MANIFEST.mkdir(parents=True, exist_ok=True)


PROTECTED = {
    SOURCE_REPOS.resolve(),
    FROZEN_ARCHIVE.resolve(),
}

# These are never automatic deletion targets.
PERMANENT_EXTRACTION_AREAS = {
    "REPORTS",
    "MANIFEST",
    "METADATA",
}

# Known extraction areas that are potentially disposable
# after final acceptance.
TEMPORARY_EXTRACTION_AREAS = {
    "STAGING",
    "INTEGRATION",
    "FINAL_STAGING",
}

# These are audit/build evidence and should be retained
# until final production acceptance + rollback closure.
AUDIT_AREAS = {
    "SECURITY_GATE",
    "DEPENDENCY_GATE",
    "TESTING_GATE",
    "TESTING_REMEDIATION_GATE",
    "TESTING_RETEST_GATE",
    "ARCHITECTURE_MAPPING",
    "CONSOLIDATION",
    "CLEANUP_AUDIT",
    "CLEANUP_AUDIT_V2",
    "FINAL_REPORTS",
}


def is_protected(path: Path) -> bool:
    try:
        resolved = path.resolve()

        for protected in PROTECTED:
            try:
                resolved.relative_to(protected)
                return True
            except ValueError:
                pass

        return False

    except Exception:
        return True


def top_level_area(path: Path) -> str:
    try:
        relative = path.relative_to(EXTRACTION)
        parts = relative.parts

        if not parts:
            return ""

        return parts[0]

    except Exception:
        return ""


def classify(path: Path) -> tuple[str, str]:

    if is_protected(path):
        return (
            "PROTECTED",
            "Source repository or frozen archive.",
        )

    area = top_level_area(path)

    if area in PERMANENT_EXTRACTION_AREAS:
        return (
            "KEEP_PROVENANCE",
            "Required provenance/report/manifest material.",
        )

    if area in AUDIT_AREAS:
        return (
            "KEEP_AUDIT_EVIDENCE",
            "Audit evidence retained until final acceptance.",
        )

    if area in TEMPORARY_EXTRACTION_AREAS:
        return (
            "CLEANUP_CANDIDATE",
            "Intermediate staging/build workspace.",
        )

    # Individual known build state files.
    name = path.name.lower()

    if name in {
        "kairo_build_state.json",
        "extraction_manifest.json",
    }:
        return (
            "KEEP_BUILD_STATE",
            "Build state/provenance record.",
        )

    # Generated caches/artifacts.
    if (
        "__pycache__" in path.parts
        or path.suffix.lower() in {
            ".pyc",
            ".pyo",
            ".tmp",
            ".cache",
            ".log",
            ".bak",
        }
    ):
        return (
            "SAFE_TO_DELETE_AFTER_ACCEPTANCE",
            "Generated temporary artifact.",
        )

    return (
        "REVIEW_REQUIRED",
        "Unknown extraction material requires explicit review.",
    )


def scan_tree(root: Path):

    records = []

    if not root.exists():
        return records

    for path in root.rglob("*"):

        if not path.is_file():
            continue

        try:
            size = path.stat().st_size
        except Exception:
            size = 0

        decision, reason = classify(path)

        records.append(
            {
                "path": str(path),
                "relative_path": str(
                    path.relative_to(ROOT)
                ),
                "area": top_level_area(path),
                "name": path.name,
                "extension": path.suffix.lower(),
                "size_bytes": size,
                "decision": decision,
                "reason": reason,
            }
        )

    return records


def main():

    print("=" * 70)
    print("KAIRO CLEANUP PLAN ENGINE V1")
    print("=" * 70)

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

    if not EXTRACTION.exists():
        raise FileNotFoundError(
            f"Extraction workspace missing:\n{EXTRACTION}"
        )

    print("Scanning extraction workspace...")

    records = scan_tree(EXTRACTION)

    print(
        f"Files analyzed: {len(records):,}"
    )

    decisions = Counter(
        r["decision"]
        for r in records
    )

    areas = Counter(
        r["area"]
        for r in records
    )

    # ------------------------------------------------------------
    # Calculate cleanup candidates
    # ------------------------------------------------------------

    cleanup_candidates = [
        r
        for r in records
        if r["decision"]
        in {
            "CLEANUP_CANDIDATE",
            "SAFE_TO_DELETE_AFTER_ACCEPTANCE",
        }
    ]

    review_candidates = [
        r
        for r in records
        if r["decision"]
        == "REVIEW_REQUIRED"
    ]

    protected_records = [
        r
        for r in records
        if r["decision"]
        == "PROTECTED"
    ]

    # ------------------------------------------------------------
    # Directory-level plan
    # ------------------------------------------------------------

    directory_plan = []

    if EXTRACTION.exists():

        for child in sorted(
            EXTRACTION.iterdir(),
            key=lambda x: x.name.lower(),
        ):

            if not child.is_dir():
                continue

            child_files = [
                r
                for r in records
                if r["area"] == child.name
            ]

            child_decisions = Counter(
                r["decision"]
                for r in child_files
            )

            if child.name in PERMANENT_EXTRACTION_AREAS:

                directory_decision = "KEEP"

            elif child.name in AUDIT_AREAS:

                directory_decision = (
                    "KEEP_UNTIL_FINAL_ACCEPTANCE"
                )

            elif child.name in TEMPORARY_EXTRACTION_AREAS:

                directory_decision = (
                    "DELETE_AFTER_FINAL_ACCEPTANCE"
                )

            else:

                directory_decision = (
                    "REVIEW_REQUIRED"
                )

            directory_plan.append(
                {
                    "directory": str(child),
                    "name": child.name,
                    "file_count": len(child_files),
                    "decision": directory_decision,
                    "decision_breakdown":
                        dict(child_decisions),
                }
            )

    # ------------------------------------------------------------
    # Final KAIRO verification
    # ------------------------------------------------------------

    final_exists = FINAL_KAIRO.exists()

    final_file_count = 0

    if final_exists:

        final_file_count = sum(
            1
            for p in FINAL_KAIRO.rglob("*")
            if p.is_file()
        )

    # ------------------------------------------------------------
    # Cleanup sequence
    # ------------------------------------------------------------

    cleanup_sequence = [
        {
            "phase": 1,
            "action": "FINAL_ACCEPTANCE",
            "status": "REQUIRED",
            "description":
                "Accept and validate 13_FINAL_KAIRO before deletion.",
        },
        {
            "phase": 2,
            "action": "ROLLBACK_SNAPSHOT",
            "status": "REQUIRED",
            "description":
                "Create a rollback snapshot of the current production KAIRO.",
        },
        {
            "phase": 3,
            "action": "PROVENANCE_LOCK",
            "status": "REQUIRED",
            "description":
                "Preserve manifests, reports and provenance records.",
        },
        {
            "phase": 4,
            "action": "REMOVE_TEMPORARY_WORKSPACES",
            "status": "PLANNED",
            "description":
                "Remove only disposable extraction/staging workspaces.",
        },
        {
            "phase": 5,
            "action": "REMOVE_GENERATED_ARTIFACTS",
            "status": "PLANNED",
            "description":
                "Remove caches, bytecode and temporary generated artifacts.",
        },
        {
            "phase": 6,
            "action": "FINAL_VALIDATION",
            "status": "REQUIRED",
            "description":
                "Re-run integrity and architecture validation after cleanup.",
        },
        {
            "phase": 7,
            "action": "SOURCE_ARCHIVE_PROTECTION_CHECK",
            "status": "REQUIRED",
            "description":
                "Confirm original repositories and frozen archive remain intact.",
        },
    ]

    # ------------------------------------------------------------
    # Manifest
    # ------------------------------------------------------------

    manifest = {
        "engine":
            "KAIRO Cleanup Plan Engine V1",

        "generated_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "status":
            "PLAN_ONLY",

        "files_analyzed":
            len(records),

        "decision_counts":
            dict(decisions),

        "area_counts":
            dict(areas),

        "cleanup_candidate_count":
            len(cleanup_candidates),

        "review_candidate_count":
            len(review_candidates),

        "protected_record_count":
            len(protected_records),

        "final_kairo": {
            "exists": final_exists,
            "file_count": final_file_count,
            "path": str(FINAL_KAIRO),
        },

        "safety": {
            "deletion_performed": False,
            "production_modified": False,
            "source_modified": False,
            "archive_modified": False,
            "code_executed": False,
            "dependencies_installed": False,
            "network_used": False,
        },

        "directory_plan":
            directory_plan,

        "cleanup_sequence":
            cleanup_sequence,
    }

    # ------------------------------------------------------------
    # Write machine-readable outputs
    # ------------------------------------------------------------

    with (
        MANIFEST
        / "CLEANUP_PLAN_MANIFEST.json"
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
        / "CLEANUP_FILE_DECISIONS.json"
    ).open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            records,
            f,
            indent=2,
            ensure_ascii=False,
        )

    with (
        MANIFEST
        / "CLEANUP_DIRECTORY_PLAN.json"
    ).open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            directory_plan,
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
        / "REVIEW_REQUIRED.json"
    ).open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            review_candidates,
            f,
            indent=2,
            ensure_ascii=False,
        )

    # ------------------------------------------------------------
    # Human-readable report
    # ------------------------------------------------------------

    report = []

    report.append(
        "# KAIRO CLEANUP PLAN V1"
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
        "- **NO DELETIONS PERFORMED**"
    )
    report.append(
        "- Production KAIRO: **PROTECTED**"
    )
    report.append(
        "- Source repositories: **PROTECTED**"
    )
    report.append(
        "- Frozen archive: **PROTECTED**"
    )
    report.append(
        "- Code execution: **DISABLED**"
    )
    report.append(
        "- Dependency installation: **DISABLED**"
    )
    report.append(
        "- Network: **NOT USED**"
    )
    report.append("")

    report.append("## Inventory")
    report.append("")
    report.append(
        f"- Extraction files analyzed: "
        f"**{len(records):,}**"
    )
    report.append(
        f"- Final KAIRO files: "
        f"**{final_file_count:,}**"
    )
    report.append(
        f"- Cleanup candidates: "
        f"**{len(cleanup_candidates):,}**"
    )
    report.append(
        f"- Review required: "
        f"**{len(review_candidates):,}**"
    )
    report.append(
        f"- Protected records: "
        f"**{len(protected_records):,}**"
    )
    report.append("")

    report.append("## Decision Breakdown")
    report.append("")

    for decision, count in decisions.most_common():

        report.append(
            f"- `{decision}`: **{count:,}**"
        )

    report.append("")

    report.append("## Extraction Areas")
    report.append("")

    for item in directory_plan:

        report.append(
            f"### `{item['name']}`"
        )
        report.append("")

        report.append(
            f"- Files: **{item['file_count']:,}**"
        )

        report.append(
            f"- Decision: "
            f"**{item['decision']}**"
        )

        breakdown = item[
            "decision_breakdown"
        ]

        for decision, count in breakdown.items():

            report.append(
                f"- {decision}: {count:,}"
            )

        report.append("")

    report.append("## Planned Cleanup Sequence")
    report.append("")

    for item in cleanup_sequence:

        report.append(
            f"{item['phase']}. "
            f"**{item['action']}** — "
            f"{item['status']}"
        )

        report.append(
            f"   - {item['description']}"
        )

    report.append("")

    report.append("## Protected Forever")
    report.append("")
    report.append(
        f"- `{SOURCE_REPOS}`"
    )
    report.append(
        f"- `{FROZEN_ARCHIVE}`"
    )
    report.append("")

    report.append("## Important")
    report.append("")
    report.append(
        "Temporary extraction material is not deleted "
        "automatically. Final acceptance and rollback "
        "snapshot must occur before destructive cleanup."
    )
    report.append("")

    report.append(
        "**STATUS: PLAN GENERATED — ZERO DELETIONS**"
    )

    (
        REPORTS
        / "KAIRO_CLEANUP_PLAN_V1.md"
    ).write_text(
        "\n".join(report),
        encoding="utf-8",
    )

    # ------------------------------------------------------------
    # Console
    # ------------------------------------------------------------

    print()
    print("=" * 70)
    print("KAIRO CLEANUP PLAN COMPLETE")
    print("=" * 70)

    print(
        f"Extraction files analyzed : {len(records):,}"
    )

    print(
        f"Final KAIRO files         : {final_file_count:,}"
    )

    print(
        f"Cleanup candidates        : {len(cleanup_candidates):,}"
    )

    print(
        f"Review required           : {len(review_candidates):,}"
    )

    print(
        f"Protected records         : {len(protected_records):,}"
    )

    print()
    print("DECISIONS")

    for decision, count in decisions.most_common():

        print(
            f"{decision:32s}: {count:,}"
        )

    print()
    print("DIRECTORY PLAN")

    for item in directory_plan:

        print(
            f"{item['name']:30s} "
            f"{item['file_count']:7,d} "
            f"{item['decision']}"
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
        f"{MANIFEST / 'CLEANUP_PLAN_MANIFEST.json'}"
    )

    print(
        f"Report  : "
        f"{REPORTS / 'KAIRO_CLEANUP_PLAN_V1.md'}"
    )

    print()
    print(
        "STATUS: PLAN GENERATED"
    )

    print(
        "NEXT: REVIEW CLEANUP PLAN"
    )


if __name__ == "__main__":
    main()
