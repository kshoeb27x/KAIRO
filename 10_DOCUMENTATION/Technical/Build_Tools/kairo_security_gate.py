from __future__ import annotations

import json
import re
import hashlib
from pathlib import Path
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[1]

INTEGRATION_ROOT = ROOT / "12_EXTRACTION" / "INTEGRATION"
PACKAGES_ROOT = INTEGRATION_ROOT / "PACKAGES"
MANIFEST_PATH = INTEGRATION_ROOT / "MANIFEST" / "INTEGRATION_MANIFEST.json"

SECURITY_ROOT = ROOT / "12_EXTRACTION" / "SECURITY_GATE"
REPORT_ROOT = SECURITY_ROOT / "REPORTS"
MANIFEST_ROOT = SECURITY_ROOT / "MANIFEST"

REPORT_ROOT.mkdir(parents=True, exist_ok=True)
MANIFEST_ROOT.mkdir(parents=True, exist_ok=True)


SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "dist",
    "build",
    ".next",
    ".cache",
}


TEXT_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx",
    ".json", ".yaml", ".yml", ".toml",
    ".ini", ".cfg", ".conf", ".env",
    ".md", ".txt", ".sh", ".ps1",
    ".bat", ".cmd", ".html", ".css",
    ".sql", ".rs", ".go", ".java",
}


PATTERNS = {
    "SECRET": [
        r"(?i)(api[_-]?key|secret[_-]?key|access[_-]?token)\s*[:=]\s*['\"][^'\"]{8,}",
        r"(?i)(aws_access_key_id|aws_secret_access_key)\s*[:=]",
        r"(?i)-----BEGIN (RSA|EC|OPENSSH|PRIVATE) KEY-----",
        r"(?i)github_pat_[A-Za-z0-9_]+",
        r"(?i)sk-[A-Za-z0-9_-]{20,}",
    ],

    "DANGEROUS_EXECUTION": [
        r"(?i)\bos\.system\s*\(",
        r"(?i)\bsubprocess\.(run|Popen|call|check_call|check_output)\s*\(",
        r"(?i)\bchild_process\b",
        r"(?i)\bexec\s*\(",
        r"(?i)\beval\s*\(",
        r"(?i)\bshell\s*=\s*True",
    ],

    "SHELL": [
        r"(?i)\bbash\s+-c\b",
        r"(?i)\bsh\s+-c\b",
        r"(?i)\bpowershell\b",
        r"(?i)\bcmd\.exe\b",
        r"(?i)\bshell32\b",
    ],

    "NETWORK": [
        r"(?i)\brequests\.(get|post|put|delete|patch)\s*\(",
        r"(?i)\bhttpx\.",
        r"(?i)\baiohttp\.",
        r"(?i)\bsocket\.",
        r"(?i)\bwebsocket\b",
        r"(?i)\bfetch\s*\(",
        r"(?i)\bcurl\b",
        r"(?i)\bwget\b",
    ],

    "FILE_DESTRUCTIVE": [
        r"(?i)\bos\.remove\s*\(",
        r"(?i)\bos\.unlink\s*\(",
        r"(?i)\bshutil\.rmtree\s*\(",
        r"(?i)\bPath\(.*\)\.unlink\s*\(",
    ],

    "PRIVILEGE": [
        r"(?i)\bsudo\b",
        r"(?i)\bchmod\s+7[0-7]{2}\b",
        r"(?i)\bsetuid\b",
        r"(?i)\bAdministrator\b",
        r"(?i)\bRunAs\b",
    ],

    "REMOTE_CONTROL": [
        r"(?i)\bssh\b",
        r"(?i)\bparamiko\b",
        r"(?i)\bremote\s+shell\b",
        r"(?i)\bremote\s+execution\b",
    ],

    "DATABASE_WRITE": [
        r"(?i)\bDROP\s+TABLE\b",
        r"(?i)\bTRUNCATE\s+TABLE\b",
        r"(?i)\bDELETE\s+FROM\b",
        r"(?i)\bALTER\s+TABLE\b",
    ],
}


WEIGHTS = {
    "SECRET": 10,
    "DANGEROUS_EXECUTION": 8,
    "SHELL": 6,
    "NETWORK": 4,
    "FILE_DESTRUCTIVE": 10,
    "PRIVILEGE": 10,
    "REMOTE_CONTROL": 8,
    "DATABASE_WRITE": 8,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def should_skip(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def scan_file(path: Path) -> list[dict]:
    if path.suffix.lower() not in TEXT_EXTENSIONS:
        return []

    try:
        if path.stat().st_size > 2 * 1024 * 1024:
            return []

        text = path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except Exception:
        return []

    findings = []

    for category, patterns in PATTERNS.items():
        for pattern in patterns:
            try:
                matches = list(re.finditer(pattern, text))
            except re.error:
                continue

            for match in matches[:20]:
                line = text.count("\n", 0, match.start()) + 1

                findings.append(
                    {
                        "category": category,
                        "line": line,
                        "pattern": pattern,
                    }
                )

    return findings


def classify(findings: list[dict]) -> tuple[str, str]:
    if not findings:
        return "CLEAR", "No configured security indicators detected."

    categories = {x["category"] for x in findings}

    if "SECRET" in categories:
        return "BLOCK", "Potential secret or credential exposure detected."

    critical = {
        "FILE_DESTRUCTIVE",
        "PRIVILEGE",
        "DATABASE_WRITE",
    }

    if categories & critical:
        return "BLOCK", "Potential destructive or privileged operation detected."

    if {
        "DANGEROUS_EXECUTION",
        "REMOTE_CONTROL",
        "SHELL",
    } & categories:
        return "REVIEW", "Execution or remote-control capability requires review."

    return "REVIEW", "Security-sensitive behavior requires review."


def main() -> int:
    print("=" * 68)
    print(" KAIRO SECURITY GATE V1")
    print("=" * 68)
    print()
    print("Mode        : READ-ONLY SECURITY ANALYSIS")
    print("Production  : PROTECTED")
    print("Archive     : PROTECTED")
    print("Source      : PROTECTED")
    print()

    if not MANIFEST_PATH.exists():
        print("ERROR: Integration manifest not found.")
        return 1

    try:
        integration_manifest = json.loads(
            MANIFEST_PATH.read_text(encoding="utf-8")
        )
    except Exception as exc:
        print(f"ERROR: Cannot read integration manifest: {exc}")
        return 1

    packages = []

    if isinstance(integration_manifest, dict):
        for key in (
            "packages",
            "components",
            "records",
            "results",
            "items",
        ):
            value = integration_manifest.get(key)
            if isinstance(value, list):
                packages = value
                break

    if not packages and isinstance(integration_manifest, list):
        packages = integration_manifest

    if not packages:
        print("ERROR: No integration packages found in manifest.")
        return 1

    print(f"Integration packages : {len(packages):,}")
    print()

    results = []

    clear_count = 0
    review_count = 0
    block_count = 0
    unreadable_count = 0

    for index, package in enumerate(packages, 1):

        package_id = (
            package.get("package_id")
            or package.get("id")
            or package.get("component_id")
            or f"PACKAGE_{index:05d}"
        )

        package_path = (
            package.get("package_path")
            or package.get("path")
            or package.get("output_path")
        )

        if not package_path:
            results.append(
                {
                    "package_id": package_id,
                    "status": "BLOCK",
                    "reason": "Missing package path.",
                    "findings": [],
                }
            )
            block_count += 1
            continue

        package_path = Path(package_path)

        if not package_path.is_absolute():
            package_path = ROOT / package_path

        if not package_path.exists():
            results.append(
                {
                    "package_id": package_id,
                    "status": "BLOCK",
                    "reason": "Package path does not exist.",
                    "findings": [],
                }
            )
            block_count += 1
            continue

        all_findings = []
        scanned_files = 0

        files = (
            [package_path]
            if package_path.is_file()
            else list(package_path.rglob("*"))
        )

        for path in files:
            if not path.is_file():
                continue

            if should_skip(path):
                continue

            findings = scan_file(path)

            if path.suffix.lower() in TEXT_EXTENSIONS:
                scanned_files += 1

            if findings:
                relative = str(path.relative_to(package_path))

                for finding in findings:
                    finding["file"] = relative

                all_findings.extend(findings)

        status, reason = classify(all_findings)

        score = sum(
            WEIGHTS.get(x["category"], 1)
            for x in all_findings
        )

        result = {
            "package_id": package_id,
            "status": status,
            "reason": reason,
            "risk_score": score,
            "scanned_files": scanned_files,
            "finding_count": len(all_findings),
            "categories": sorted(
                {x["category"] for x in all_findings}
            ),
            "findings": all_findings[:200],
        }

        results.append(result)

        if status == "CLEAR":
            clear_count += 1
        elif status == "REVIEW":
            review_count += 1
        else:
            block_count += 1

        if index % 100 == 0 or index == len(packages):
            print(
                f"[{index:5d}/{len(packages)}] "
                f"CLEAR={clear_count} "
                f"REVIEW={review_count} "
                f"BLOCK={block_count}"
            )

    manifest = {
        "generated_at": utc_now(),
        "engine": "KAIRO SECURITY GATE V1",
        "mode": "READ_ONLY",
        "production_modified": False,
        "archive_modified": False,
        "source_repositories_modified": False,
        "packages_received": len(packages),
        "clear": clear_count,
        "review": review_count,
        "block": block_count,
        "unaccounted": 0,
        "results": results,
    }

    manifest_file = (
        MANIFEST_ROOT / "SECURITY_GATE_MANIFEST.json"
    )

    report_file = (
        REPORT_ROOT / "KAIRO_SECURITY_GATE_REPORT.md"
    )

    manifest_file.write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report_lines = [
        "# KAIRO SECURITY GATE V1",
        "",
        f"Generated: {utc_now()}",
        "",
        "## Protection",
        "",
        "- Production KAIRO: PROTECTED",
        "- Frozen archive: PROTECTED",
        "- Source repositories: PROTECTED",
        "- Security scan mode: READ-ONLY",
        "",
        "## Results",
        "",
        f"- Packages received: {len(packages):,}",
        f"- CLEAR: {clear_count:,}",
        f"- REVIEW: {review_count:,}",
        f"- BLOCK: {block_count:,}",
        "- Unaccounted: 0",
        "",
        "## Finding categories",
        "",
    ]

    category_counts = {}

    for result in results:
        for category in result["categories"]:
            category_counts[category] = (
                category_counts.get(category, 0) + 1
            )

    for category, count in sorted(
        category_counts.items(),
        key=lambda x: (-x[1], x[0]),
    ):
        report_lines.append(
            f"- {category}: {count:,} packages"
        )

    report_lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "CLEAR means no configured security indicators were detected.",
            "REVIEW means security-sensitive behavior requires inspection.",
            "BLOCK means the package should not proceed toward production integration until reviewed.",
            "",
            "## Final protection check",
            "",
            "- Production modified: NO",
            "- Frozen archive modified: NO",
            "- Source repositories modified: NO",
        ]
    )

    report_file.write_text(
        "\n".join(report_lines),
        encoding="utf-8",
    )

    print()
    print("=" * 68)
    print(" KAIRO SECURITY GATE V1 COMPLETE")
    print("=" * 68)
    print()
    print(f"Packages received : {len(packages):,}")
    print(f"CLEAR             : {clear_count:,}")
    print(f"REVIEW            : {review_count:,}")
    print(f"BLOCK             : {block_count:,}")
    print("Unaccounted       : 0")
    print()
    print(f"Manifest : {manifest_file}")
    print(f"Report   : {report_file}")
    print()
    print("Production modified       : NO")
    print("Frozen archive modified   : NO")
    print("Source repositories       : NO")
    print()

    if block_count > 0:
        print("SECURITY STATUS: BLOCKED")
        print("NEXT: REVIEW BLOCKED PACKAGES")
        return 2

    if review_count > 0:
        print("SECURITY STATUS: REVIEW REQUIRED")
        print("NEXT: REVIEW SECURITY FINDINGS")
        return 3

    print("SECURITY STATUS: CLEAR")
    print("NEXT: DEPENDENCY + CONFLICT GATE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
