from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path


SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".idea",
    ".vscode",
    "dist",
    "build",
    "coverage",
    "site-packages",
}


LANGUAGES = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript/TSX",
    ".jsx": "JavaScript/JSX",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".cpp": "C++",
    ".c": "C",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".dart": "Dart",
    ".sh": "Shell",
    ".ps1": "PowerShell",
    ".sql": "SQL",
    ".html": "HTML",
    ".css": "CSS",
    ".vue": "Vue",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
}


DEPENDENCY_FILES = {
    "requirements.txt",
    "pyproject.toml",
    "poetry.lock",
    "Pipfile",
    "Pipfile.lock",
    "package.json",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "go.mod",
    "go.sum",
    "Cargo.toml",
    "Cargo.lock",
    "Gemfile",
    "Gemfile.lock",
    "pom.xml",
    "build.gradle",
}


SUSPICIOUS_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    "id_rsa",
    "id_ed25519",
    "credentials.json",
    "service-account.json",
    "secrets.json",
}


SECRET_PATTERNS = [
    re.compile(
        r"(?i)(api[_-]?key|secret[_-]?key|access[_-]?token|password)"
        r"\s*[:=]\s*['\"][^'\"]{8,}['\"]"
    ),
    re.compile(
        r"(?i)-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
    ),
    re.compile(
        r"(?i)aws_access_key_id\s*[:=]"
    ),
]


MAX_TEXT_SCAN_SIZE = 2_000_000


def should_skip_dir(name: str) -> bool:
    return name.lower() in SKIP_DIRS


def iter_files(root: Path):
    """
    Fast directory walker.

    Skips large/generated directories before entering them.
    Does NOT execute repository code.
    """

    for current_root, dirs, files in os.walk(
        root,
        topdown=True,
        followlinks=False,
    ):
        # Prune unwanted directories BEFORE walking into them.
        dirs[:] = [
            d for d in dirs
            if not should_skip_dir(d)
        ]

        current_path = Path(current_root)

        for filename in files:
            path = current_path / filename

            try:
                if path.is_file():
                    yield path
            except OSError:
                continue


def sha256_file(path: Path) -> str:
    """Calculate SHA-256 hash without executing the file."""

    digest = hashlib.sha256()

    try:
        with path.open("rb") as file:
            while True:
                chunk = file.read(1024 * 1024)

                if not chunk:
                    break

                digest.update(chunk)

        return digest.hexdigest()

    except OSError:
        return ""


def scan_text_for_secrets(path: Path) -> list[str]:
    """
    Basic secret indicator scan.

    This does not print secret values.
    """

    try:
        size = path.stat().st_size

        if size > MAX_TEXT_SCAN_SIZE:
            return []

        # Only inspect likely text/code files.
        allowed_extensions = set(LANGUAGES.keys()) | {
            ".env",
            ".ini",
            ".cfg",
            ".conf",
            ".txt",
            ".md",
        }

        if path.suffix.lower() not in allowed_extensions:
            return []

        text = path.read_text(
            encoding="utf-8",
            errors="ignore",
        )

    except OSError:
        return []

    matches = []

    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            matches.append(pattern.pattern)

    return matches


def scan_repo(repo: Path) -> dict:
    """Create a read-only inventory for one repository."""

    language_counts = Counter()
    dependency_files = []
    suspicious_files = []
    secret_indicators = []

    file_count = 0
    total_bytes = 0

    for path in iter_files(repo):

        try:
            size = path.stat().st_size
        except OSError:
            continue

        file_count += 1
        total_bytes += size

        extension = path.suffix.lower()

        if extension in LANGUAGES:
            language_counts[
                LANGUAGES[extension]
            ] += 1

        if path.name in DEPENDENCY_FILES:
            dependency_files.append(
                path.relative_to(repo).as_posix()
            )

        filename_lower = path.name.lower()

        if (
            path.name in SUSPICIOUS_NAMES
            or "secret" in filename_lower
            or "credential" in filename_lower
        ):
            suspicious_files.append(
                path.relative_to(repo).as_posix()
            )

        matches = scan_text_for_secrets(path)

        if matches:
            secret_indicators.append(
                {
                    "path": path.relative_to(repo).as_posix(),
                    "patterns": matches,
                }
            )

    return {
        "name": repo.name,
        "path": str(repo),
        "file_count": file_count,
        "total_bytes": total_bytes,
        "languages": dict(
            language_counts.most_common()
        ),
        "dependency_files": sorted(
            dependency_files
        ),
        "suspicious_files": sorted(
            suspicious_files
        ),
        "secret_indicators": secret_indicators,
    }


def find_duplicate_files(repos: list[Path], root: Path) -> list[dict]:
    """
    Find exact duplicate files across repositories.

    Uses file size first, then SHA-256.
    """

    by_size = defaultdict(list)

    print("\nChecking exact duplicate files...")

    for repo in repos:

        for path in iter_files(repo):

            try:
                size = path.stat().st_size
            except OSError:
                continue

            # Empty files are not useful for duplicate analysis.
            if size == 0:
                continue

            by_size[size].append(path)

    duplicate_groups = []

    for size, paths in by_size.items():

        if len(paths) < 2:
            continue

        hashes = defaultdict(list)

        for path in paths:

            digest = sha256_file(path)

            if digest:
                hashes[digest].append(
                    str(path.relative_to(root))
                )

        for digest, same_files in hashes.items():

            if len(same_files) > 1:
                duplicate_groups.append(
                    {
                        "sha256": digest,
                        "size": size,
                        "files": sorted(
                            same_files
                        ),
                    }
                )

    return duplicate_groups


def main() -> None:

    parser = argparse.ArgumentParser(
        description=(
            "KAIRO read-only repository auditor"
        )
    )

    parser.add_argument(
        "root",
        nargs="?",
        default=(
            "00_FOUNDATION/"
            "Architecture/"
            "Old_Repositories"
        ),
    )

    parser.add_argument(
        "--out",
        default=(
            "10_DOCUMENTATION/"
            "Technical/"
            "repository_audit.json"
        ),
    )

    args = parser.parse_args()

    root = Path(args.root).resolve()

    if not root.exists():
        raise SystemExit(
            f"Repository directory not found:\n{root}"
        )

    repos = sorted(
        [
            path
            for path in root.iterdir()
            if path.is_dir()
            and not should_skip_dir(path.name)
        ],
        key=lambda p: p.name.lower(),
    )

    print("=" * 60)
    print("KAIRO REPOSITORY AUDITOR")
    print("=" * 60)
    print("Mode: READ-ONLY")
    print("Repository code execution: DISABLED")
    print(f"Repositories found: {len(repos)}")
    print()

    results = {
        "audit_version": "0.2",
        "mode": "read-only",
        "execution_policy": (
            "Repository code is never executed."
        ),
        "skipped_directories": sorted(
            SKIP_DIRS
        ),
        "root": str(root),
        "repositories": [],
    }

    for index, repo in enumerate(repos, start=1):

        print(
            f"[{index}/{len(repos)}] "
            f"Scanning: {repo.name}"
        )

        result = scan_repo(repo)

        results["repositories"].append(
            result
        )

        print(
            f"    Files: {result['file_count']}"
        )

        print(
            f"    Languages: "
            f"{', '.join(result['languages'].keys()) or 'None'}"
        )

        print(
            f"    Dependencies: "
            f"{len(result['dependency_files'])}"
        )

        print(
            f"    Secret indicators: "
            f"{len(result['secret_indicators'])}"
        )

    duplicate_groups = find_duplicate_files(
        repos,
        root,
    )

    results[
        "cross_repo_duplicate_files"
    ] = duplicate_groups

    out = Path(args.out).resolve()

    out.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    out.write_text(
        json.dumps(
            results,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 60)
    print("AUDIT COMPLETE")
    print("=" * 60)

    print(
        f"Repositories audited: {len(repos)}"
    )

    print(
        f"Exact duplicate groups: "
        f"{len(duplicate_groups)}"
    )

    print(
        f"Report created:\n{out}"
    )

    print()
    print(
        "No repository code was executed."
    )


if __name__ == "__main__":
    main()
    