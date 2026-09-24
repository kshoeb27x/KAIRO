from pathlib import Path
from datetime import datetime
import json

ROOT = Path(__file__).resolve().parents[1]

print("=" * 72)
print("KAIRO CLEANUP AUDIT V2")
print("=" * 72)

print()
print("MODE")
print("Deletion              : DISABLED")
print("Production modification: DISABLED")
print("Source repositories   : PROTECTED")
print("Frozen archive        : PROTECTED")
print("Code execution        : DISABLED")
print("Network               : NOT USED")
print()

# ------------------------------------------------------------
# PROTECTED AREAS
# ------------------------------------------------------------

protected = [
    ROOT / "11_ARCHIVE" / "Original_Repositories",
    ROOT / "00_FOUNDATION" / "Architecture" / "Old_Repositories",
    ROOT / "15_ROLLBACK_SNAPSHOTS",
]

# ------------------------------------------------------------
# KNOWN BUILD / TEMP AREAS
# ------------------------------------------------------------

known_areas = {
    "12_EXTRACTION": ROOT / "12_EXTRACTION",
    "13_FINAL_KAIRO": ROOT / "13_FINAL_KAIRO",
    "14_KAIRO_PRODUCTION_CANDIDATE":
        ROOT / "14_KAIRO_PRODUCTION_CANDIDATE",
}

# ------------------------------------------------------------
# FILE COUNTER
# ------------------------------------------------------------

def count_files(path):
    if not path.exists():
        return 0

    count = 0

    for item in path.rglob("*"):
        if item.is_file():
            count += 1

    return count


# ------------------------------------------------------------
# DIRECTORY REPORT
# ------------------------------------------------------------

areas = {}

for name, path in known_areas.items():

    exists = path.exists()
    files = count_files(path) if exists else 0

    areas[name] = {
        "path": str(path),
        "exists": exists,
        "files": files,
    }

    print(
        f"{name:<38}: "
        f"{files if exists else 'NOT FOUND'} files"
    )


# ------------------------------------------------------------
# PROTECTED AREA CHECK
# ------------------------------------------------------------

print()
print("PROTECTED AREAS")

protected_results = {}

for path in protected:

    exists = path.exists()

    protected_results[str(path)] = exists

    print(
        f"{path.name:<38}: "
        + ("PRESENT / PROTECTED"
           if exists
           else "NOT FOUND")
    )


# ------------------------------------------------------------
# IMPORTANT MANIFESTS
# ------------------------------------------------------------

manifest_patterns = [
    "KAIRO_BUILD_STATE.json",
    "KAIRO_FINAL_BUILD_REPORT.md",
    "INTEGRATION_MANIFEST.json",
    "PRODUCTION_MERGE_MANIFEST.json",
    "KAIRO_RUNTIME_VALIDATION.json",
    "KAIRO_LIVE_API_UI_VALIDATION_V2.json",
]

print()
print("BUILD / VALIDATION MANIFESTS")

manifests = {}

for pattern in manifest_patterns:

    matches = list(
        ROOT.rglob(pattern)
    )

    manifests[pattern] = [
        str(p.relative_to(ROOT))
        for p in matches
    ]

    print(
        f"{pattern:<42}: "
        f"{len(matches)} found"
    )


# ------------------------------------------------------------
# CANDIDATE CLEANUP CLASSIFICATION
# ------------------------------------------------------------

cleanup_candidates = []

for name, info in areas.items():

    if not info["exists"]:
        continue

    path = Path(info["path"])

    # These are temporary build outputs.
    for item in path.iterdir():

        cleanup_candidates.append({
            "area": name,
            "path": str(
                item.relative_to(ROOT)
            ),
            "type":
                "directory"
                if item.is_dir()
                else "file",
            "reason":
                "temporary build/extraction artifact",
        })


# ------------------------------------------------------------
# SAFETY FILTER
# ------------------------------------------------------------

safe_candidates = []

for item in cleanup_candidates:

    path = ROOT / item["path"]

    blocked = False

    for protected_path in protected:

        try:
            path.relative_to(
                protected_path
            )

            blocked = True
            break

        except ValueError:
            pass

    if not blocked:
        safe_candidates.append(item)


# ------------------------------------------------------------
# REPORT
# ------------------------------------------------------------

report_dir = (
    ROOT /
    "19_CLEANUP_AUDIT"
)

report_dir.mkdir(
    parents=True,
    exist_ok=True
)

report = {
    "type":
        "KAIRO_CLEANUP_AUDIT_V2",

    "generated_at":
        datetime.now().isoformat(
            timespec="seconds"
        ),

    "deletion_enabled":
        False,

    "known_areas":
        areas,

    "protected_areas":
        protected_results,

    "manifests":
        manifests,

    "cleanup_candidates":
        safe_candidates,

    "candidate_count":
        len(safe_candidates),

    "safety": {
        "deletion":
            False,

        "production_modified":
            False,

        "source_modified":
            False,

        "archive_modified":
            False,

        "code_execution":
            False,

        "network":
            False,
    },
}

(
    report_dir /
    "KAIRO_CLEANUP_AUDIT_V2.json"
).write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)

# ------------------------------------------------------------
# SUMMARY
# ------------------------------------------------------------

print()
print("=" * 72)
print("KAIRO CLEANUP AUDIT V2 COMPLETE")
print("=" * 72)

print(
    f"Cleanup candidates : {len(safe_candidates)}"
)

print()
print("Deletion              : DISABLED")
print("Production modified   : NO")
print("Source repositories   : PROTECTED")
print("Frozen archive        : PROTECTED")
print("Code execution        : DISABLED")
print("Network               : NOT USED")

print()

if safe_candidates:

    print(
        "STATUS: REVIEW_REQUIRED"
    )

    print(
        "NEXT: CONTROLLED CLEANUP PLAN"
    )

else:

    print(
        "STATUS: NOTHING_TO_CLEAN"
    )

print("=" * 72)

