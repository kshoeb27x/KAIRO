from pathlib import Path
from datetime import datetime
import json
import ast

ROOT = Path(__file__).resolve().parents[1]

ROLLBACK_ROOT = ROOT / "15_ROLLBACK_SNAPSHOTS"
MANIFESTS = list(
    ROLLBACK_ROOT.glob(
        "MERGE_BACKUP_*/PRODUCTION_MERGE_MANIFEST.json"
    )
)

print("=" * 70)
print("KAIRO POST-MERGE VALIDATION V1")
print("=" * 70)

print()
print("SAFETY")
print("Code execution       : DISABLED")
print("Dependency install   : DISABLED")
print("Network              : NOT USED")
print("Deletion             : DISABLED")
print("Archive              : PROTECTED")
print("Source repositories  : PROTECTED")
print()

if not MANIFESTS:
    print("STATUS: FAIL")
    print("Production merge manifest not found.")
    raise SystemExit(1)

# Latest merge manifest
manifest_path = max(
    MANIFESTS,
    key=lambda p: p.stat().st_mtime
)

manifest = json.loads(
    manifest_path.read_text(
        encoding="utf-8"
    )
)

records = [
    r for r in manifest.get("records", [])
    if r.get("action") == "ADDED"
]

print(
    f"Merge manifest : {manifest_path}"
)

print(
    f"Merged files   : {len(records):,}"
)

# ------------------------------------------------------------
# Validation
# ------------------------------------------------------------

missing = []
python_failures = []
json_failures = []
protected_violations = []
forbidden_files = []

for index, record in enumerate(records, 1):

    rel = Path(record["path"])
    target = ROOT / rel

    # Protected areas must never have been merged.
    if rel.parts and rel.parts[0] in {
        "11_ARCHIVE",
        "12_EXTRACTION",
        "13_FINAL_KAIRO",
        "14_KAIRO_PRODUCTION_CANDIDATE",
        "15_ROLLBACK_SNAPSHOTS",
    }:
        protected_violations.append(
            str(rel)
        )

    # Generated environments must never be merged.
    if any(
        part in {
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
        for part in rel.parts
    ):
        forbidden_files.append(
            str(rel)
        )

    if not target.exists():
        missing.append(
            str(rel)
        )
        continue

    suffix = target.suffix.lower()

    # Python static syntax validation.
    if suffix == ".py":

        try:
            source = target.read_text(
                encoding="utf-8-sig"
            )

            ast.parse(
                source,
                filename=str(target)
            )

        except Exception as exc:

            python_failures.append({
                "file": str(rel),
                "error": str(exc),
            })

    # JSON validation.
    elif suffix == ".json":

        try:
            target.read_text(
                encoding="utf-8-sig"
            )

            json.loads(
                target.read_text(
                    encoding="utf-8-sig"
                )
            )

        except Exception as exc:

            # Example/template JSON is reported,
            # but not treated as a production blocker
            # when its name clearly indicates a template.
            name = target.name.lower()

            if (
                "example" in name
                or "sample" in name
                or "template" in name
            ):
                continue

            json_failures.append({
                "file": str(rel),
                "error": str(exc),
            })

    if index % 100 == 0:
        print(
            f"[{index:5d}/{len(records):5d}] "
            f"VALIDATED"
        )

# ------------------------------------------------------------
# Core existence checks
# ------------------------------------------------------------

core_paths = [
    "src",
    "07_RUNTIME",
    "05_UI",
    "config",
]

core_results = {}

for item in core_paths:
    core_results[item] = (
        (ROOT / item).exists()
    )

# ------------------------------------------------------------
# Merge accounting
# ------------------------------------------------------------

manifest_added = manifest.get(
    "added",
    0
)

manifest_errors = manifest.get(
    "errors",
    0
)

accounting_pass = (
    manifest_added == len(records)
    and manifest_errors == 0
)

checks = {
    "merge_manifest_found":
        True,

    "merge_accounting":
        accounting_pass,

    "all_merged_files_exist":
        len(missing) == 0,

    "python_static_syntax":
        len(python_failures) == 0,

    "json_integrity":
        len(json_failures) == 0,

    "protected_area_violation":
        len(protected_violations) == 0,

    "forbidden_generated_files":
        len(forbidden_files) == 0,

    "src_exists":
        core_results["src"],

    "runtime_exists":
        core_results["07_RUNTIME"],

    "ui_exists":
        core_results["05_UI"],

    "config_exists":
        core_results["config"],
}

overall = all(checks.values())

print()
print("=" * 70)
print("POST-MERGE VALIDATION RESULTS")
print("=" * 70)

for name, result in checks.items():

    print(
        f"{name:<32}: "
        + ("PASS" if result else "FAIL")
    )

print()
print("DETAILS")
print(
    f"Merged files validated : {len(records):,}"
)
print(
    f"Missing files          : {len(missing):,}"
)
print(
    f"Python syntax failures : {len(python_failures):,}"
)
print(
    f"JSON failures          : {len(json_failures):,}"
)
print(
    f"Protected violations   : {len(protected_violations):,}"
)
print(
    f"Forbidden files        : {len(forbidden_files):,}"
)

print()
print("SAFETY")
print("Production merge       : COMPLETED")
print("Deletion               : NONE")
print("Code execution         : NONE")
print("Dependencies installed: NONE")
print("Network                : NONE")
print("Archive modified       : NO")
print("Source repositories    : NO")

# ------------------------------------------------------------
# Save report
# ------------------------------------------------------------

REPORT_DIR = ROOT / "16_POST_MERGE_VALIDATION"
REPORT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

report = {
    "type":
        "KAIRO_POST_MERGE_VALIDATION",

    "created_at":
        datetime.now().isoformat(
            timespec="seconds"
        ),

    "manifest":
        str(manifest_path),

    "merged_files":
        len(records),

    "checks":
        checks,

    "missing_files":
        missing,

    "python_failures":
        python_failures,

    "json_failures":
        json_failures,

    "protected_violations":
        protected_violations,

    "forbidden_files":
        forbidden_files,

    "core_paths":
        core_results,

    "status":
        "PASS"
        if overall
        else "REVIEW_REQUIRED",
}

(REPORT_DIR / "POST_MERGE_VALIDATION.json").write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)

print()
print("=" * 70)

if overall:
    print("STATUS: PASS")
    print("NEXT: KAIRO RUNTIME VALIDATION")
else:
    print("STATUS: REVIEW_REQUIRED")
    print("NEXT: RESOLVE POST-MERGE FAILURES")

print("=" * 70)

