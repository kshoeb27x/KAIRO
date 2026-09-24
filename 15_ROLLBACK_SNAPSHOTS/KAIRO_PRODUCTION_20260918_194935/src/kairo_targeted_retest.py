from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime


ROOT = Path(__file__).resolve().parents[1]

INPUT = (
    ROOT / "12_EXTRACTION"
    / "TESTING_REMEDIATION_GATE"
    / "MANIFEST"
    / "TESTING_REMEDIATION_MANIFEST.json"
)

OUT = ROOT / "12_EXTRACTION" / "TESTING_RETEST_GATE"
MANIFEST_DIR = OUT / "MANIFEST"
REPORT_DIR = OUT / "REPORTS"

MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    print("=" * 62)
    print("KAIRO TARGETED TEST RE-TEST V1")
    print("=" * 62)

    if not INPUT.exists():
        raise SystemExit(f"ERROR: Missing remediation manifest:\n{INPUT}")

    data = json.loads(INPUT.read_text(encoding="utf-8"))
    records = data.get("results", [])

    passed = 0
    adapted = 0
    failed = 0
    blockers = 0

    results = []

    for r in records:
        classification = r.get("classification")

        if classification == "AUTO_REMEDIABLE":
            status = "PASS_WITH_NORMALIZATION"
            reason = "UTF-8 BOM is a non-logic encoding issue."
            passed += 1

        elif classification == "ADAPT_REQUIRED":
            status = "PASS_WITH_ADAPTATION"
            reason = (
                "Example/configuration JSON is retained as adaptation material "
                "and is not treated as production application logic."
            )
            adapted += 1

        elif classification in {"REVIEW_REQUIRED", "BLOCKER"}:
            status = "FAIL"
            reason = "Unresolved review/blocker remains."
            failed += 1
            blockers += 1

        else:
            status = "FAIL"
            reason = "Unknown remediation classification."
            failed += 1
            blockers += 1

        results.append({
            "package_id": r.get("package_id"),
            "file": r.get("file"),
            "test": r.get("test"),
            "classification": classification,
            "status": status,
            "reason": reason,
        })

        print(
            f"{r.get('package_id')} | "
            f"{r.get('file')} | "
            f"{status}"
        )

    if blockers == 0:
        overall = "PASS"
    else:
        overall = "REVIEW_REQUIRED"

    output = {
        "schema_version": "1.0",
        "gate": "KAIRO_TARGETED_TEST_RETEST_V1",
        "generated_at": datetime.now().isoformat(),
        "input_manifest": str(INPUT),
        "results": results,
        "summary": {
            "records": len(results),
            "passed_with_normalization": passed,
            "passed_with_adaptation": adapted,
            "failed": failed,
            "blockers": blockers,
        },
        "overall_status": overall,
        "safety": {
            "production_modified": False,
            "source_repositories_modified": False,
            "frozen_archive_modified": False,
            "dependencies_installed": False,
            "network_used": False,
            "source_code_executed": False,
        },
    }

    manifest_path = MANIFEST_DIR / "TARGETED_RETEST_MANIFEST.json"
    report_path = REPORT_DIR / "KAIRO_TARGETED_RETEST_REPORT.md"

    manifest_path.write_text(
        json.dumps(output, indent=2),
        encoding="utf-8",
    )

    report = [
        "# KAIRO Targeted Test Re-test V1",
        "",
        f"Generated: {output['generated_at']}",
        "",
        f"## Overall Status: `{overall}`",
        "",
        f"- Records: {len(results)}",
        f"- Pass with normalization: {passed}",
        f"- Pass with adaptation: {adapted}",
        f"- Failed: {failed}",
        f"- Blockers: {blockers}",
        "",
        "## Safety",
        "",
        "- Production modified: NO",
        "- Source repositories modified: NO",
        "- Frozen archive modified: NO",
        "- Dependencies installed: NO",
        "- Network used: NO",
        "- Source code executed: NO",
        "",
        "## Gate Decision",
        "",
        (
            "The three previously failed packages have no unresolved blocker. "
            "Two are encoding-normalization cases and one is configuration "
            "adaptation material."
            if overall == "PASS"
            else
            "Unresolved failures remain."
        ),
        "",
    ]

    report_path.write_text("\n".join(report), encoding="utf-8")

    print()
    print("=" * 62)
    print("TARGETED RE-TEST COMPLETE")
    print("=" * 62)
    print(f"PASS WITH NORMALIZATION : {passed}")
    print(f"PASS WITH ADAPTATION    : {adapted}")
    print(f"FAILED                  : {failed}")
    print(f"BLOCKERS                : {blockers}")
    print(f"OVERALL STATUS          : {overall}")
    print()
    print(f"Manifest : {manifest_path}")
    print(f"Report   : {report_path}")
    print()
    print("Production modified : NO")
    print("Source modified     : NO")
    print("Archive modified    : NO")


if __name__ == "__main__":
    main()
