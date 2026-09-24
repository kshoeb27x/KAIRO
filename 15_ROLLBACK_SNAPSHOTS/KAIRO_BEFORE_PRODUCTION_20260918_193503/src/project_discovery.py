from __future__ import annotations

import json
import sys
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
}


PROJECT_MARKERS = {
    "Python": [
        "pyproject.toml",
        "requirements.txt",
        "setup.py",
        "setup.cfg",
    ],
    "Node/TypeScript": [
        "package.json",
    ],
    "Rust": [
        "Cargo.toml",
    ],
    "Go": [
        "go.mod",
    ],
    "C#": [
        "*.csproj",
        "*.sln",
    ],
    "Java": [
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
    ],
}


CAPABILITY_PATTERNS = {
    "LLM": [
        "openai",
        "anthropic",
        "gemini",
        "llm",
        "transformers",
        "huggingface",
        "ollama",
        "vllm",
        "mistral",
    ],
    "Agent": [
        "agent",
        "agents",
        "autonomous",
        "orchestration",
    ],
    "Memory": [
        "memory",
        "memories",
        "context",
        "long_term",
        "short_term",
    ],
    "RAG": [
        "rag",
        "retrieval",
        "embedding",
        "vector",
        "knowledge",
    ],
    "Browser": [
        "browser",
        "playwright",
        "selenium",
        "web_automation",
    ],
    "Computer Use": [
        "computer_use",
        "computer-use",
        "desktop",
        "mouse",
        "keyboard",
        "screenshot",
        "pyautogui",
    ],
    "Tools": [
        "tool",
        "tools",
        "function_call",
        "function-calling",
        "mcp",
    ],
    "Workflow": [
        "workflow",
        "workflows",
        "pipeline",
        "scheduler",
        "orchestration",
    ],
    "Database": [
        "database",
        "sqlite",
        "postgres",
        "mysql",
        "mongodb",
        "redis",
    ],
    "Voice": [
        "voice",
        "speech",
        "audio",
        "tts",
        "stt",
        "whisper",
    ],
    "API": [
        "api",
        "server",
        "endpoint",
        "rest",
        "graphql",
    ],
    "Security": [
        "security",
        "auth",
        "authentication",
        "authorization",
        "permission",
        "secret",
        "sandbox",
    ],
}


def detect_project_type(project_path: Path) -> list[str]:
    detected = []

    try:
        names = {p.name for p in project_path.iterdir()}
    except OSError:
        return detected

    for language, markers in PROJECT_MARKERS.items():
        for marker in markers:
            if marker.startswith("*"):
                suffix = marker.replace("*", "")
                if any(name.endswith(suffix) for name in names):
                    detected.append(language)
                    break
            elif marker in names:
                detected.append(language)
                break

    return detected


def collect_text_files(project_path: Path, limit: int = 80) -> list[Path]:
    files = []

    for current, dirs, filenames in __import__("os").walk(project_path):
        dirs[:] = [
            d for d in dirs
            if d not in SKIP_DIRS
        ]

        current_path = Path(current)

        for filename in filenames:
            path = current_path / filename

            if path.suffix.lower() in {
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
                ".h",
                ".hpp",
                ".yaml",
                ".yml",
                ".json",
                ".toml",
                ".md",
                ".txt",
            }:
                files.append(path)

                if len(files) >= limit:
                    return files

    return files


def detect_capabilities(project_path: Path) -> dict[str, int]:
    scores = {cap: 0 for cap in CAPABILITY_PATTERNS}

    files = collect_text_files(project_path)

    for path in files:
        try:
            text = path.read_text(
                encoding="utf-8",
                errors="ignore",
            ).lower()
        except OSError:
            continue

        for capability, patterns in CAPABILITY_PATTERNS.items():
            for pattern in patterns:
                if pattern in text:
                    scores[capability] += 1

    return {
        capability: score
        for capability, score in scores.items()
        if score > 0
    }


def find_projects(repository_path: Path) -> list[Path]:
    projects = []

    # Repository root itself
    if detect_project_type(repository_path):
        projects.append(repository_path)

    # Search nested project roots
    for current, dirs, filenames in __import__("os").walk(repository_path):
        dirs[:] = [
            d for d in dirs
            if d not in SKIP_DIRS
        ]

        current_path = Path(current)

        # Avoid treating the repository root twice
        if current_path == repository_path:
            continue

        if detect_project_type(current_path):
            projects.append(current_path)

    return projects


def analyze_project(project_path: Path, repository_root: Path) -> dict:
    project_types = detect_project_type(project_path)
    capabilities = detect_capabilities(project_path)

    try:
        relative_path = str(
            project_path.relative_to(repository_root)
        )
    except ValueError:
        relative_path = "."

    return {
        "project": project_path.name,
        "path": relative_path,
        "type": project_types,
        "capabilities": capabilities,
    }


def main() -> None:
    if len(sys.argv) < 2:
        print(
            "Usage: python -m src.project_discovery "
            '"00_FOUNDATION/Architecture/Old_Repositories"'
        )
        sys.exit(1)

    repositories_path = Path(sys.argv[1]).resolve()

    if not repositories_path.exists():
        print(f"Path not found: {repositories_path}")
        sys.exit(1)

    repositories = [
        p for p in repositories_path.iterdir()
        if p.is_dir()
    ]

    print("=" * 60)
    print("KAIRO PROJECT DISCOVERY ENGINE")
    print("=" * 60)
    print("Mode: READ-ONLY")
    print("Repository execution: DISABLED")
    print(f"Repositories found: {len(repositories)}")
    print()

    inventory = {
        "project": "KAIRO",
        "mode": "READ-ONLY",
        "execution": False,
        "repositories": [],
    }

    for index, repository in enumerate(repositories, 1):
        print(
            f"[{index}/{len(repositories)}] "
            f"Discovering: {repository.name}"
        )

        projects = find_projects(repository)

        repo_data = {
            "repository": repository.name,
            "projects": [],
        }

        print(f"    Projects detected: {len(projects)}")

        for project in projects:
            data = analyze_project(project, repository)
            repo_data["projects"].append(data)

            print(
                f"      - {data['project']} "
                f"| {', '.join(data['type']) or 'Unknown'} "
                f"| {len(data['capabilities'])} capabilities"
            )

        inventory["repositories"].append(repo_data)
        print()

    output_path = (
        repositories_path.parent.parent.parent
        / "10_DOCUMENTATION"
        / "Technical"
        / "kairo_project_inventory.json"
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            inventory,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    total_projects = sum(
        len(repo["projects"])
        for repo in inventory["repositories"]
    )

    print("=" * 60)
    print("PROJECT DISCOVERY COMPLETE")
    print("=" * 60)
    print(f"Repositories analyzed: {len(repositories)}")
    print(f"Projects discovered: {total_projects}")
    print()
    print("Inventory created:")
    print(output_path)
    print()
    print("No repository code was executed.")


if __name__ == "__main__":
    main()