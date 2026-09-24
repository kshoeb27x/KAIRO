from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

EXTRACTION = ROOT / "12_EXTRACTION"
PLAN = EXTRACTION / "CONSOLIDATION" / "DECISIONS" / "integration_plan.json"
OUTPUT = EXTRACTION / "INTEGRATION"
PACKAGES = OUTPUT / "PACKAGES"
MANIFEST = OUTPUT / "MANIFEST" / "INTEGRATION_MANIFEST.json"
REPORT = OUTPUT / "REPORTS" / "KAIRO_INTEGRATION_REPORT.md"

SKIP_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__",
    "dist", "build", ".pytest_cache", ".mypy_cache",
    ".next", "target", "coverage"
}

SKIP_EXTENSIONS = {
    ".pyc", ".pyo", ".class", ".dll", ".exe", ".so",
    ".dylib", ".bin", ".lock"
}

SECRET_PATTERNS = [
    r"api[_-]?key\s*=",
    r"secret[_-]?key\s*=",
    r"password\s*=",
    r"private[_-]?key",
    r"access[_-]?token",
    r"bearer\s+[A-Za-z0-9._-]+",
    r"-----BEGIN .*PRIVATE KEY-----",
]

DANGEROUS_PATTERNS = [
    r"\bos\.system\s*\(",
    r"\bsubprocess\.",
    r"\bshell\s*=\s*True",
    r"\beval\s*\(",
    r"\bexec\s*\(",
    r"\bchild_process\b",
    r"\bspawn\s*\(",
    r"\bexecSync\s*\(",
    r"\brm\s+-rf\b",
    r"\bformat\s+[A-Za-z]:",
]


def now():
    return datetime.now().isoformat(timespec="seconds")


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def safe_name(value: str):
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value)
    return value[:120] or "component"


def read_text(path: Path):
    try:
        if path.stat().st_size > 2 * 1024 * 1024:
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def security_scan(path: Path):
    text = read_text(path)

    secrets = []
    dangerous = []

    for pattern in SECRET_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            secrets.append(pattern)

    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            dangerous.append(pattern)

    if secrets:
        risk = "HIGH"
    elif dangerous:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    return {
        "risk": risk,
        "secret_indicators": len(secrets),
        "dangerous_indicators": len(dangerous),
    }


def find_candidate_list(obj):
    """
    Locate the candidate list without assuming one exact JSON schema.
    """

    if isinstance(obj, list):
        if any(isinstance(x, dict) and (
            "source_file" in x or
            "staging_path" in x or
            "repository_relative_path" in x
        ) for x in obj):
            return obj

        for item in obj:
            result = find_candidate_list(item)
            if result is not None:
                return result

    elif isinstance(obj, dict):
        preferred = [
            "integration_candidates",
            "candidates",
            "items",
            "records",
            "components",
        ]

        for key in preferred:
            if key in obj:
                result = find_candidate_list(obj[key])
                if result is not None:
                    return result

        for value in obj.values():
            result = find_candidate_list(value)
            if result is not None:
                return result

    return None


def resolve_source(candidate: dict):
    """
    Critical fix:
    staging_path is preferred because it is already inside the
    isolated extraction workspace.
    """

    staging = candidate.get("staging_path")

    if staging:
        p = Path(staging)
        if p.exists() and p.is_file():
            return p

        p = ROOT / staging
        if p.exists() and p.is_file():
            return p

    source = candidate.get("source_file")

    if source:
        p = ROOT / "00_FOUNDATION" / "Architecture" / "Old_Repositories" / source
        if p.exists() and p.is_file():
            return p

    relative = candidate.get("repository_relative_path")
    repository = candidate.get("repository")

    if relative and repository:
        p = (
            ROOT
            / "00_FOUNDATION"
            / "Architecture"
            / "Old_Repositories"
            / repository
            / relative
        )

        if p.exists() and p.is_file():
            return p

    return None


def should_skip(path: Path):
    if any(part in SKIP_DIRS for part in path.parts):
        return True

    if path.suffix.lower() in SKIP_EXTENSIONS:
        return True

    return False


def build():
    print("=" * 68)
    print(" KAIRO INTEGRATION BUILDER V2")
    print("=" * 68)
    print()
    print("Mode        : SAFE ISOLATED BUILD")
    print("Production  : PROTECTED")
    print("Archive     : PROTECTED")
    print()

    if not PLAN.exists():
        print("ERROR: integration_plan.json not found.")
        return 1

    data = json.loads(PLAN.read_text(encoding="utf-8"))
    candidates = find_candidate_list(data) or []

    print(f"Integration candidates : {len(candidates):,}")
    print()

    if not candidates:
        print("ERROR: No candidates found in integration plan.")
        return 1

    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)

    PACKAGES.mkdir(parents=True, exist_ok=True)
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)

    results = []

    built = 0
    skipped = 0
    errors = 0

    risk_counts = {
        "LOW": 0,
        "MEDIUM": 0,
        "HIGH": 0,
    }

    for index, candidate in enumerate(candidates, 1):
        source = resolve_source(candidate)

        record = {
            "index": index,
            "repository": candidate.get("repository"),
            "source_file": candidate.get("source_file"),
            "repository_relative_path": candidate.get(
                "repository_relative_path"
            ),
            "staging_path": candidate.get("staging_path"),
            "decision": candidate.get("decision"),
            "score": candidate.get("score"),
            "status": None,
            "reason": None,
            "package_path": None,
            "security": None,
            "built_at": now(),
        }

        if source is None:
            record["status"] = "SKIPPED"
            record["reason"] = "SOURCE_NOT_FOUND"
            skipped += 1
            results.append(record)
            continue

        if should_skip(source):
            record["status"] = "SKIPPED"
            record["reason"] = "GENERATED_OR_UNSUPPORTED_FILE"
            skipped += 1
            results.append(record)
            continue

        try:
            security = security_scan(source)
            record["security"] = security

            risk_counts[security["risk"]] += 1

            digest = candidate.get("sha256") or sha256(source)

            package_id = (
                f"{index:04d}_"
                f"{safe_name(candidate.get('repository', 'repo'))}_"
                f"{digest[:12]}"
            )

            package_dir = PACKAGES / package_id
            package_dir.mkdir(parents=True, exist_ok=True)

            destination = package_dir / source.name

            shutil.copy2(source, destination)

            metadata = dict(record)
            metadata["package_file"] = str(destination)
            metadata["source_sha256"] = digest

            (package_dir / "COMPONENT_METADATA.json").write_text(
                json.dumps(metadata, indent=2),
                encoding="utf-8",
            )

            record["status"] = "BUILT"
            record["package_path"] = str(package_dir)

            built += 1

        except Exception as exc:
            record["status"] = "ERROR"
            record["reason"] = repr(exc)
            errors += 1

        results.append(record)

        if index % 100 == 0 or index == len(candidates):
            print(
                f"[{index:>5}/{len(candidates)}] "
                f"BUILT={built} "
                f"SKIPPED={skipped} "
                f"ERROR={errors}"
            )

    accounted = built + skipped + errors
    unaccounted = len(candidates) - accounted

    manifest = {
        "builder": "KAIRO Integration Builder V2",
        "generated_at": now(),
        "candidate_count": len(candidates),
        "built": built,
        "skipped": skipped,
        "errors": errors,
        "unaccounted": unaccounted,
        "security": risk_counts,
        "production_modified": False,
        "archive_modified": False,
        "source_repositories_modified": False,
        "results": results,
    }

    MANIFEST.write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    report_lines = [
        "# KAIRO Integration Builder V2",
        "",
        f"Generated: `{now()}`",
        "",
        "## Results",
        "",
        f"- Candidates: `{len(candidates):,}`",
        f"- Built: `{built:,}`",
        f"- Skipped: `{skipped:,}`",
        f"- Errors: `{errors:,}`",
        f"- Unaccounted: `{unaccounted:,}`",
        "",
        "## Security",
        "",
        f"- LOW: `{risk_counts['LOW']:,}`",
        f"- MEDIUM: `{risk_counts['MEDIUM']:,}`",
        f"- HIGH: `{risk_counts['HIGH']:,}`",
        "",
        "## Safety",
        "",
        "- Production modified: **NO**",
        "- Frozen archive modified: **NO**",
        "- Source repositories modified: **NO**",
        "",
    ]

    REPORT.write_text(
        "\n".join(report_lines),
        encoding="utf-8",
    )

    print()
    print("=" * 68)
    print(" KAIRO INTEGRATION BUILDER V2 COMPLETE")
    print("=" * 68)
    print()
    print(f"Candidates received : {len(candidates):,}")
    print(f"Packages built      : {built:,}")
    print(f"Skipped             : {skipped:,}")
    print(f"Errors              : {errors:,}")
    print(f"Unaccounted         : {unaccounted:,}")
    print()
    print("SECURITY")
    print("----------------------------------------")
    print(f"LOW            : {risk_counts['LOW']:,}")
    print(f"MEDIUM         : {risk_counts['MEDIUM']:,}")
    print(f"HIGH           : {risk_counts['HIGH']:,}")
    print()
    print(f"Manifest : {MANIFEST}")
    print(f"Report   : {REPORT}")
    print()
    print("Production modified : NO")
    print("Frozen archive modified : NO")
    print("Source repositories modified : NO")
    print()

    if unaccounted != 0:
        print("BUILD STATUS: FAILED")
        print("Every candidate must be accounted for.")
        return 1

    if built == 0:
        print("BUILD STATUS: FAILED")
        print("Zero packages were built.")
        return 1

    print("BUILD STATUS: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
