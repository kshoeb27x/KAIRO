from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime


PROJECT_ROOT = Path(__file__).resolve().parents[1]

TEST_MANIFEST = (
    PROJECT_ROOT
    / "12_EXTRACTION"
    / "TESTING_GATE"
    / "MANIFEST"
    / "TESTING_GATE_MANIFEST.json"
)

OUTPUT_ROOT = PROJECT_ROOT / "12_EXTRACTION" / "TESTING_REMEDIATION_GATE"

REPORT_DIR = OUTPUT_ROOT / "REPORTS"
MANIFEST_DIR = OUTPUT_ROOT / "MANIFEST"

REPORT_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST_DIR.mkdir(parents=True, exist_ok=True)


def classify_failure(result: dict) -> tuple[str, str]:
    test = result.get("test", "")
    message = result.get("message", "")

    if test == "python_syntax" and "U+FEFF" in message:
        return (
            "AUTO_REMEDIABLE",
            "UTF-8 BOM detected. Source logic is not considered invalid; "
            "integration should normalize encoding to UTF-8 without BOM.",
        )

    if test == "json_parse":
        return (
            "ADAPT_REQUIRED",
            "Example/config JSON is not valid JSON for the static parser. "
            "Treat as configuration-template material and validate/adapt before integration.",
        )

    if test == "python_syntax":
        return (
            "REVIEW_REQUIRED",
            "Python syntax failure requires source-level review.",
        )

    return (
        "BLOCKER",
        "Failure type is not covered by automatic remediation rules.",
    )


def main() -> None:
    print("=" * 62)
    print("KAIRO TESTING REMEDIATION GATE V1")
    print("=" * 62)

    if not TEST_MANIFEST.exists():
        raise SystemExit(
            f"ERROR: Testing manifest not found:\n{TEST_MANIFEST}"
        )

    data = json.loads(TEST_MANIFEST.read_text(encoding="utf-8"))

    failed_packages = [
        package
        for package in data.get("results", [])
        if package.get("status") != "PASS"
    ]

    remediation_results = []

    print(f"Failed packages received : {len(failed_packages)}")
    print()

    for package in failed_packages:
        package_id = package.get("package_id", "UNKNOWN")

        for result in package.get("results", []):
            if result.get("status") not in {"FAIL", "ERROR"}:
                continue

            classification, action = classify_failure(result)

            record = {
                "package_id": package_id,
                "test": result.get("test"),
                "file": result.get("file"),
                "original_status": result.get("status"),
                "original_message": result.get("message"),
                "classification": classification,
                "action": action,
                "production_modified": False,
                "source_modified": False,
                "archive_modified": False,
            }

            remediation_results.append(record)

            print(f"PACKAGE : {package_id}")
            print(f"FILE    : {result.get('file')}")
            print(f"TEST    : {result.get('test')}")
            print(f"STATUS  : {classification}")
            print(f"ACTION  : {action}")
            print("-" * 62)

    counts = {
        "AUTO_REMEDIABLE": 0,
        "ADAPT_REQUIRED": 0,
        "REVIEW_REQUIRED": 0,
        "BLOCKER": 0,
    }

    for record in remediation_results:
        counts[record["classification"]] += 1

    if counts["BLOCKER"] > 0:
        overall_status = "BLOCKED"
    elif counts["REVIEW_REQUIRED"] > 0:
        overall_status = "REVIEW_REQUIRED"
    elif counts["ADAPT_REQUIRED"] > 0:
        overall_status = "ADAPT_REQUIRED"
    else:
        overall_status = "REMEDIATION_READY"

    manifest = {
        "schema_version": "1.0",
        "gate": "KAIRO_TESTING_REMEDIATION_GATE_V1",
        "generated_at": datetime.now().isoformat(),
        "input_manifest": str(TEST_MANIFEST),
        "failed_packages_received": len(failed_packages),
        "failure_records": len(remediation_results),
        "classification_counts": counts,
        "overall_status": overall_status,
        "results": remediation_results,
        "safety": {
            "production_modified": False,
            "source_repositories_modified": False,
            "frozen_archive_modified": False,
            "dependencies_installed": False,
            "network_used": False,
            "code_executed": False,
        },
    }

    manifest_path = MANIFEST_DIR / "TESTING_REMEDIATION_MANIFEST.json"
    report_path = REPORT_DIR / "KAIRO_TESTING_REMEDIATION_REPORT.md"

    manifest_path.write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    report_lines = [
        "# KAIRO Testing Remediation Gate V1",
        "",
        f"Generated: {manifest['generated_at']}",
        "",
        "## Result",
        "",
        f"**Overall status:** `{overall_status}`",
        "",
        f"- Failed packages received: {len(failed_packages)}",
        f"- Failure records: {len(remediation_results)}",
        f"- Auto-remediable: {counts['AUTO_REMEDIABLE']}",
        f"- Adapt required: {counts['ADAPT_REQUIRED']}",
        f"- Review required: {counts['REVIEW_REQUIRED']}",
        f"- Blockers: {counts['BLOCKER']}",
        "",
        "## Decisions",
        "",
    ]

    for record in remediation_results:
        report_lines.extend(
            [
                f"### `{record['package_id']}`",
                "",
                f"- File: `{record['file']}`",
                f"- Test: `{record['test']}`",
                f"- Classification: `{record['classification']}`",
                f"- Action: {record['action']}",
                "",
            ]
        )

    report_lines.extend(
        [
            "## Safety",
            "",
            "- Production modified: NO",
            "- Source repositories modified: NO",
            "- Frozen archive modified: NO",
            "- Dependencies installed: NO",
            "- Network used: NO",
            "- Extracted code executed: NO",
            "",
        ]
    )

    report_path.write_text(
        "\n".join(report_lines),
        encoding="utf-8",
    )

    print("=" * 62)
    print("REMEDIATION GATE COMPLETE")
    print("=" * 62)
    print(f"Failed packages : {len(failed_packages)}")
    print(f"Auto-remediable : {counts['AUTO_REMEDIABLE']}")
    print(f"Adapt required  : {counts['ADAPT_REQUIRED']}")
    print(f"Review required : {counts['REVIEW_REQUIRED']}")
    print(f"Blockers        : {counts['BLOCKER']}")
    print(f"STATUS          : {overall_status}")
    print()
    print(f"Manifest : {manifest_path}")
    print(f"Report   : {report_path}")
    print()
    print("Production modified : NO")
    print("Source modified     : NO")
    print("Archive modified    : NO")


if __name__ == "__main__":
    main()
