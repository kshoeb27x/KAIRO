import argparse
import json
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

CAPABILITY_PATTERNS = {
    "LLM": [
        r"\bopenai\b",
        r"\banthropic\b",
        r"\bgemini\b",
        r"\bgoogle\.generativeai\b",
        r"\blangchain\b",
        r"\blitellm\b",
        r"\bvllm\b",
        r"\btransformers\b",
        r"\bhuggingface\b",
        r"\bllama\b",
        r"\bmistral\b",
        r"\bollama\b",
        r"\bchatcompletion\b",
        r"\bchat_completions?\b",
        r"\bcompletion\b",
        r"\binference\b",
        r"\bllm\b",
        r"\bmodel[_-]?provider\b",
    ]
}

TEXT_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".rs",
    ".go",
    ".java",
    ".cs",
    ".cpp",
    ".c",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".md",
    ".txt",
}

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


def scan_file(path, patterns):
    try:
        text = path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except Exception:
        return []

    matches = []

    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            matches.append(pattern)

    return matches


def scan_repository(repo_path, patterns):
    results = []

    for root, dirs, files in __import__("os").walk(repo_path):
        dirs[:] = [
            d for d in dirs
            if d not in SKIP_DIRS
        ]

        for filename in files:
            path = Path(root) / filename

            if path.suffix.lower() not in TEXT_EXTENSIONS:
                continue

            matched = scan_file(path, patterns)

            if matched:
                try:
                    relative_path = path.relative_to(repo_path)
                except ValueError:
                    relative_path = path.name

                results.append(
                    {
                        "file": str(relative_path),
                        "matches": matched,
                    }
                )

    return results


def main():
    parser = argparse.ArgumentParser(
        description="KAIRO read-only component scanner"
    )

    parser.add_argument(
        "repositories_path",
        help="Path containing the repositories",
    )

    parser.add_argument(
        "--capability",
        required=True,
        choices=CAPABILITY_PATTERNS.keys(),
        help="Capability to scan",
    )

    args = parser.parse_args()

    repositories_path = (
        BASE_DIR / args.repositories_path
    ).resolve()

    if not repositories_path.exists():
        print("ERROR: Repository path not found:")
        print(repositories_path)
        return

    patterns = CAPABILITY_PATTERNS[args.capability]

    repositories = [
    p for p in repositories_path.iterdir()
    if p.is_dir() and p.name != "Repos"
]

    print("=" * 60)
    print("KAIRO COMPONENT SCANNER")
    print("=" * 60)
    print("Mode: READ-ONLY")
    print("Repository execution: DISABLED")
    print("Capability:", args.capability)
    print("Repositories:", len(repositories))
    print()

    report = {
        "project": "KAIRO",
        "mode": "READ-ONLY",
        "execution": False,
        "capability": args.capability,
        "repositories": [],
    }

    for index, repo in enumerate(
        sorted(repositories),
        start=1,
    ):
        print(
            f"[{index}/{len(repositories)}] "
            f"Scanning: {repo.name}"
        )

        matches = scan_repository(
            repo,
            patterns,
        )

        print(
            f"    Candidate files: {len(matches)}"
        )

        report["repositories"].append(
            {
                "repository": repo.name,
                "candidate_files": matches,
            }
        )

    output_file = (
        BASE_DIR
        / "10_DOCUMENTATION"
        / "Technical"
        / "llm_component_scan.json"
    )

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_file.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            report,
            f,
            indent=2,
        )

    print()
    print("=" * 60)
    print("SCAN COMPLETE")
    print("=" * 60)
    print("Report created:")
    print(output_file)
    print()
    print("No repository code was executed.")


if __name__ == "__main__":
    main()
    