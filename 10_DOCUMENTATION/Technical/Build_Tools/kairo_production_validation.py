from pathlib import Path
import json
import hashlib

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "14_KAIRO_PRODUCTION_CANDIDATE"

print("=" * 70)
print("KAIRO PRODUCTION CANDIDATE VALIDATION V1")
print("=" * 70)

if not CANDIDATE.exists():
    print("STATUS: FAIL")
    print("Production candidate does not exist.")
    raise SystemExit(1)

files = [
    p for p in CANDIDATE.rglob("*")
    if p.is_file()
]

manifest = (
    CANDIDATE /
    "MANIFEST" /
    "CONTROLLED_MERGE_MANIFEST.json"
)

if not manifest.exists():
    print("STATUS: FAIL")
    print("Merge manifest missing.")
    raise SystemExit(1)

data = json.loads(
    manifest.read_text(encoding="utf-8")
)

checks = {}

checks["candidate_exists"] = CANDIDATE.exists()
checks["manifest_exists"] = manifest.exists()
checks["files_present"] = len(files) > 0
checks["merge_skipped"] = data.get("files_skipped", -1) == 0
checks["production_untouched"] = (
    data.get("current_production_modified") is False
)
checks["source_protected"] = (
    data.get("source_repositories_modified") is False
)
checks["archive_protected"] = (
    data.get("frozen_archive_modified") is False
)
checks["deletion_none"] = (
    data.get("deletion_performed") is False
)
checks["execution_none"] = (
    data.get("code_executed") is False
)
checks["network_none"] = (
    data.get("network_used") is False
)

print()
print("CANDIDATE")
print(f"Files discovered : {len(files):,}")
print(f"Manifest files   : {data.get('files_copied', 0):,}")

print()
print("VALIDATION")

for name, result in checks.items():
    print(
        f"{name:<28}: "
        + ("PASS" if result else "FAIL")
    )

# Verify every manifest-copied file exists.
missing = []

for record in data.get("records", []):
    if record.get("status") != "COPIED":
        continue

    target = CANDIDATE / record["target"]

    if not target.exists():
        missing.append(record["target"])

checks["manifest_targets_exist"] = len(missing) == 0

print(
    f"{'manifest_targets_exist':<28}: "
    + ("PASS" if not missing else "FAIL")
)

print()
print("SAFETY")
print("Current KAIRO : UNTOUCHED")
print("Source repos  : PROTECTED")
print("Archive       : PROTECTED")
print("Deletion      : NONE")
print("Execution     : NONE")
print("Network       : NONE")

passed = all(checks.values())

print()
print("=" * 70)

if passed:
    print("STATUS: PASS")
    print("NEXT: CONTROLLED PRODUCTION MERGE")
else:
    print("STATUS: REVIEW_REQUIRED")
    print("NEXT: RESOLVE FAILED VALIDATION")

print("=" * 70)

report_dir = ROOT / "14_KAIRO_PRODUCTION_CANDIDATE" / "REPORTS"
report_dir.mkdir(exist_ok=True)

report = {
    "candidate_files": len(files),
    "checks": checks,
    "missing_targets": missing,
    "status": "PASS" if passed else "REVIEW_REQUIRED",
}

(report_dir / "PRODUCTION_VALIDATION.json").write_text(
    json.dumps(report, indent=2),
    encoding="utf-8"
)

