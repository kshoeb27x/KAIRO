from __future__ import annotations

import json
import re
import hashlib
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[1]

INTEGRATION_ROOT = ROOT / "12_EXTRACTION" / "INTEGRATION"
PACKAGES_ROOT = INTEGRATION_ROOT / "PACKAGES"

OUT_ROOT = ROOT / "12_EXTRACTION" / "DEPENDENCY_GATE"
REPORT_ROOT = OUT_ROOT / "REPORTS"
MANIFEST_ROOT = OUT_ROOT / "MANIFEST"

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


DEP_FILES = {
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "poetry.lock",
    "Pipfile",
    "Pipfile.lock",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "go.mod",
    "Cargo.toml",
    "Cargo.lock",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(text: str) -> str:
    return hashlib.sha256(
        text.encode("utf-8", errors="ignore")
    ).hexdigest()


def normalize_name(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"[-_.]+", "-", name)
    return name


def should_skip(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def parse_requirement_line(line: str):
    line = line.strip()

    if not line or line.startswith("#"):
        return None

    if line.startswith(("-r ", "--", "git+", "http://", "https://")):
        return None

    line = line.split("#", 1)[0].strip()

    match = re.match(
        r"^([A-Za-z0-9_.-]+)\s*(.*)$",
        line,
    )

    if not match:
        return None

    name = normalize_name(match.group(1))
    constraint = match.group(2).strip()

    return name, constraint


def parse_requirements(path: Path):
    dependencies = []

    try:
        text = path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except Exception:
        return dependencies

    for line in text.splitlines():
        item = parse_requirement_line(line)

        if item:
            name, constraint = item

            dependencies.append(
                {
                    "ecosystem": "python",
                    "name": name,
                    "constraint": constraint,
                    "source_file": str(path),
                }
            )

    return dependencies


def parse_package_json(path: Path):
    dependencies = []

    try:
        data = json.loads(
            path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        )
    except Exception:
        return dependencies

    for section in (
        "dependencies",
        "devDependencies",
        "peerDependencies",
        "optionalDependencies",
    ):
        values = data.get(section, {})

        if not isinstance(values, dict):
            continue

        for name, constraint in values.items():
            dependencies.append(
                {
                    "ecosystem": "node",
                    "name": normalize_name(name),
                    "constraint": str(constraint),
                    "section": section,
                    "source_file": str(path),
                }
            )

    return dependencies


def parse_go_mod(path: Path):
    dependencies = []

    try:
        lines = path.read_text(
            encoding="utf-8",
            errors="ignore",
        ).splitlines()
    except Exception:
        return dependencies

    inside = False

    for raw in lines:
        line = raw.strip()

        if line == "require (":
            inside = True
            continue

        if inside and line == ")":
            inside = False
            continue

        if inside and line and not line.startswith("//"):
            parts = line.split()

            if len(parts) >= 2:
                dependencies.append(
                    {
                        "ecosystem": "go",
                        "name": parts[0],
                        "constraint": parts[1],
                        "source_file": str(path),
                    }
                )

    return dependencies


def parse_cargo_toml(path: Path):
    dependencies = []

    try:
        text = path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except Exception:
        return dependencies

    in_dependencies = False

    for raw in text.splitlines():
        line = raw.strip()

        if line.startswith("["):
            in_dependencies = (
                line == "[dependencies]"
                or line == "[dev-dependencies]"
                or line == "[build-dependencies]"
            )
            continue

        if not in_dependencies:
            continue

        if "=" not in line or line.startswith("#"):
            continue

        name, constraint = line.split("=", 1)

        dependencies.append(
            {
                "ecosystem": "rust",
                "name": normalize_name(name.strip()),
                "constraint": constraint.strip(),
                "source_file": str(path),
            }
        )

    return dependencies


def parse_dependency_file(path: Path):
    name = path.name.lower()

    if name in {
        "requirements.txt",
        "requirements-dev.txt",
    }:
        return parse_requirements(path)

    if name == "package.json":
        return parse_package_json(path)

    if name == "go.mod":
        return parse_go_mod(path)

    if name == "cargo.toml":
        return parse_cargo_toml(path)

    return []


def discover_dependency_files():
    files = []

    if not PACKAGES_ROOT.exists():
        return files

    for path in PACKAGES_ROOT.rglob("*"):
        if not path.is_file():
            continue

        if should_skip(path):
            continue

        if path.name in DEP_FILES:
            files.append(path)

    return files


def package_id_for(path: Path):
    try:
        relative = path.relative_to(PACKAGES_ROOT)
        parts = relative.parts

        if parts:
            return parts[0]
    except Exception:
        pass

    return path.parent.name


def collect_dependencies():
    dependency_files = discover_dependency_files()

    all_dependencies = []

    for path in dependency_files:
        deps = parse_dependency_file(path)

        package_id = package_id_for(path)

        for dep in deps:
            dep["package_id"] = package_id
            dep["dependency_file"] = str(
                path.relative_to(PACKAGES_ROOT)
            )

            all_dependencies.append(dep)

    return dependency_files, all_dependencies


def detect_duplicate_dependencies(dependencies):
    groups = defaultdict(list)

    for dep in dependencies:
        key = (
            dep["ecosystem"],
            dep["name"],
        )

        groups[key].append(dep)

    duplicates = []

    for key, items in groups.items():
        packages = sorted(
            {
                item["package_id"]
                for item in items
            }
        )

        constraints = sorted(
            {
                item["constraint"]
                for item in items
            }
        )

        if len(packages) > 1:
            duplicates.append(
                {
                    "ecosystem": key[0],
                    "name": key[1],
                    "packages": packages,
                    "constraints": constraints,
                    "constraint_count": len(constraints),
                }
            )

    return duplicates


def detect_constraint_conflicts(dependencies):
    groups = defaultdict(list)

    for dep in dependencies:
        groups[
            (
                dep["ecosystem"],
                dep["name"],
            )
        ].append(dep)

    conflicts = []

    for key, items in groups.items():
        constraints = sorted(
            {
                item["constraint"]
                for item in items
                if item["constraint"]
            }
        )

        if len(constraints) <= 1:
            continue

        exact_versions = []

        for constraint in constraints:
            match = re.search(
                r"(?<![0-9])(\d+\.\d+(?:\.\d+)?)(?![0-9])",
                constraint,
            )

            if match:
                exact_versions.append(
                    match.group(1)
                )

        if len(set(exact_versions)) > 1:
            conflicts.append(
                {
                    "ecosystem": key[0],
                    "name": key[1],
                    "constraints": constraints,
                    "detected_versions": sorted(
                        set(exact_versions)
                    ),
                    "packages": sorted(
                        {
                            item["package_id"]
                            for item in items
                        }
                    ),
                }
            )

    return conflicts


def detect_cross_ecosystem_overlap(dependencies):
    by_name = defaultdict(list)

    for dep in dependencies:
        by_name[dep["name"]].append(dep)

    overlaps = []

    for name, items in by_name.items():
        ecosystems = sorted(
            {
                item["ecosystem"]
                for item in items
            }
        )

        if len(ecosystems) > 1:
            overlaps.append(
                {
                    "name": name,
                    "ecosystems": ecosystems,
                    "packages": sorted(
                        {
                            item["package_id"]
                            for item in items
                        }
                    ),
                }
            )

    return overlaps


def detect_lockfile_presence(dependency_files):
    lockfiles = []

    for path in dependency_files:
        name = path.name.lower()

        if name in {
            "package-lock.json",
            "pnpm-lock.yaml",
            "yarn.lock",
            "poetry.lock",
            "pipfile.lock",
            "cargo.lock",
        }:
            lockfiles.append(
                str(path.relative_to(PACKAGES_ROOT))
            )

    return sorted(lockfiles)


def main() -> int:
    print("=" * 68)
    print(" KAIRO DEPENDENCY + CONFLICT GATE V1")
    print("=" * 68)
    print()
    print("Mode        : READ-ONLY ANALYSIS")
    print("Production  : PROTECTED")
    print("Archive     : PROTECTED")
    print("Source      : PROTECTED")
    print()

    if not PACKAGES_ROOT.exists():
        print("ERROR: Integration packages directory not found.")
        return 1

    dependency_files, dependencies = collect_dependencies()

    print(
        f"Dependency files discovered : {len(dependency_files):,}"
    )
    print(
        f"Dependency entries          : {len(dependencies):,}"
    )
    print()

    duplicates = detect_duplicate_dependencies(
        dependencies
    )

    conflicts = detect_constraint_conflicts(
        dependencies
    )

    overlaps = detect_cross_ecosystem_overlap(
        dependencies
    )

    lockfiles = detect_lockfile_presence(
        dependency_files
    )

    package_count = len(
        {
            dep["package_id"]
            for dep in dependencies
        }
    )

    packages_without_dependencies = []

    all_package_dirs = [
        path
        for path in PACKAGES_ROOT.iterdir()
        if path.is_dir()
    ]

    dependency_packages = {
        dep["package_id"]
        for dep in dependencies
    }

    for path in all_package_dirs:
        if path.name not in dependency_packages:
            packages_without_dependencies.append(
                path.name
            )

    status = "CLEAR"

    if conflicts:
        status = "REVIEW_REQUIRED"

    if not dependencies:
        status = "REVIEW_REQUIRED"

    manifest = {
        "generated_at": utc_now(),
        "engine": "KAIRO DEPENDENCY + CONFLICT GATE V1",
        "mode": "READ_ONLY",
        "production_modified": False,
        "archive_modified": False,
        "source_repositories_modified": False,
        "dependency_files": len(dependency_files),
        "dependency_entries": len(dependencies),
        "packages_with_dependencies": package_count,
        "packages_without_dependencies": len(
            packages_without_dependencies
        ),
        "duplicate_dependency_groups": len(duplicates),
        "conflict_groups": len(conflicts),
        "cross_ecosystem_overlaps": len(overlaps),
        "lockfiles_detected": len(lockfiles),
        "status": status,
        "duplicates": duplicates,
        "conflicts": conflicts,
        "cross_ecosystem_overlaps": overlaps,
        "lockfiles": lockfiles,
        "packages_without_dependencies": sorted(
            packages_without_dependencies
        ),
    }

    manifest_path = (
        MANIFEST_ROOT
        / "DEPENDENCY_GATE_MANIFEST.json"
    )

    report_path = (
        REPORT_ROOT
        / "KAIRO_DEPENDENCY_GATE_REPORT.md"
    )

    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = [
        "# KAIRO DEPENDENCY + CONFLICT GATE V1",
        "",
        f"Generated: {utc_now()}",
        "",
        "## Protection",
        "",
        "- Production KAIRO: PROTECTED",
        "- Frozen archive: PROTECTED",
        "- Source repositories: PROTECTED",
        "- Analysis mode: READ-ONLY",
        "",
        "## Summary",
        "",
        f"- Dependency files: {len(dependency_files):,}",
        f"- Dependency entries: {len(dependencies):,}",
        f"- Packages with dependencies: {package_count:,}",
        f"- Packages without dependency metadata: {len(packages_without_dependencies):,}",
        f"- Duplicate dependency groups: {len(duplicates):,}",
        f"- Conflict groups: {len(conflicts):,}",
        f"- Cross-ecosystem overlaps: {len(overlaps):,}",
        f"- Lockfiles detected: {len(lockfiles):,}",
        f"- Status: **{status}**",
        "",
        "## Dependency conflicts",
        "",
    ]

    if conflicts:
        for conflict in conflicts[:500]:
            report.append(
                f"- `{conflict['ecosystem']}` / "
                f"`{conflict['name']}` — "
                f"versions: "
                f"{', '.join(conflict['detected_versions'])}"
            )
    else:
        report.append(
            "No exact-version conflicts were detected "
            "by the configured static parser."
        )

    report.extend(
        [
            "",
            "## Duplicate dependencies",
            "",
        ]
    )

    if duplicates:
        for item in duplicates[:500]:
            report.append(
                f"- `{item['ecosystem']}` / "
                f"`{item['name']}` — "
                f"{len(item['packages'])} packages"
            )
    else:
        report.append(
            "No cross-package duplicate dependency groups detected."
        )

    report.extend(
        [
            "",
            "## Lockfiles",
            "",
        ]
    )

    if lockfiles:
        for lockfile in lockfiles:
            report.append(f"- `{lockfile}`")
    else:
        report.append("No recognized lockfiles detected.")

    report.extend(
        [
            "",
            "## Final protection check",
            "",
            "- Production modified: NO",
            "- Frozen archive modified: NO",
            "- Source repositories modified: NO",
        ]
    )

    report_path.write_text(
        "\n".join(report),
        encoding="utf-8",
    )

    print("RESULTS")
    print("-" * 68)
    print(
        f"Duplicate dependency groups : {len(duplicates):,}"
    )
    print(
        f"Conflict groups              : {len(conflicts):,}"
    )
    print(
        f"Cross-ecosystem overlaps     : {len(overlaps):,}"
    )
    print(
        f"Lockfiles detected            : {len(lockfiles):,}"
    )
    print()
    print(f"Manifest : {manifest_path}")
    print(f"Report   : {report_path}")
    print()
    print("Production modified         : NO")
    print("Frozen archive modified     : NO")
    print("Source repositories         : NO")
    print()

    if conflicts:
        print("DEPENDENCY STATUS: REVIEW REQUIRED")
        print("NEXT: REVIEW CONFLICTS BEFORE TESTING")
        return 2

    print("DEPENDENCY STATUS: PASS")
    print("NEXT: AUTOMATED TESTING")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
