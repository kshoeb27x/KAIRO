"""
KAIRO Repository Deep Auditor — Optimized / Read-Only

Purpose:
- Deep capability analysis without executing repository code.
- Designed to handle very large collections such as Repos/.
- Treats large collections as multiple projects.
- Scans high-value files instead of running expensive regex checks
  across every file.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path


# ============================================================
# CONFIG
# ============================================================

SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
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
    ".next",
    ".nuxt",
    "target",
    "vendor",
}

MANIFEST_FILES = {
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "Gemfile",
    "composer.json",
    "mix.exs",
}

README_NAMES = {
    "README",
    "README.md",
    "README.rst",
    "README.txt",
}

IMPORTANT_DIRS = {
    "src",
    "app",
    "lib",
    "core",
    "agent",
    "agents",
    "memory",
    "rag",
    "tools",
    "tool",
    "skills",
    "server",
    "api",
    "browser",
    "computer",
    "automation",
    "workflow",
    "workflows",
    "security",
    "database",
    "db",
    "llm",
    "models",
    "model",
    "planning",
    "planner",
    "orchestration",
    "orchestrator",
    "voice",
    "ui",
    "frontend",
    "backend",
}

TEXT_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".rs",
    ".go",
    ".java",
    ".kt",
    ".cs",
    ".rb",
    ".php",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".swift",
    ".sh",
    ".ps1",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".ini",
    ".md",
    ".rst",
    ".txt",
}

MAX_FILE_BYTES = 128 * 1024
MAX_SAMPLE_FILES = 350
MAX_PROJECTS = 250


# ============================================================
# CAPABILITY PATTERNS
# ============================================================

CAPABILITY_PATTERNS = {
    "LLM": [
        r"\bopenai\b",
        r"\banthropic\b",
        r"\bgemini\b",
        r"\bllama\b",
        r"\btransformer\b",
        r"\bhuggingface\b",
        r"\blangchain\b",
        r"\bllm\b",
        r"\bchatmodel\b",
    ],
    "Agent": [
        r"\bagent\b",
        r"\bagents\b",
        r"\bautonomous\b",
        r"\btool.?calling\b",
        r"\bfunction.?calling\b",
        r"\breact.?agent\b",
    ],
    "Memory": [
        r"\bmemory\b",
        r"\bmem0\b",
        r"\bepisodic\b",
        r"\bsemantic.?memory\b",
        r"\bconversation.?history\b",
    ],
    "RAG": [
        r"\brag\b",
        r"\bretrieval\b",
        r"\bvector.?store\b",
        r"\bembedding\b",
        r"\bembeddings\b",
        r"\bchromadb\b",
        r"\bfaiss\b",
        r"\bqdrant\b",
        r"\bweaviate\b",
        r"\bpgvector\b",
    ],
    "Database": [
        r"\bsqlalchemy\b",
        r"\bsqlite\b",
        r"\bpostgres\b",
        r"\bpostgresql\b",
        r"\bmongodb\b",
        r"\bredis\b",
        r"\bdatabase\b",
        r"\bprisma\b",
        r"\bsupabase\b",
    ],
    "Browser": [
        r"\bplaywright\b",
        r"\bselenium\b",
        r"\bpuppeteer\b",
        r"\bbrowser\b",
        r"\bweb.?automation\b",
        r"\bweb.?agent\b",
    ],
    "Computer Use": [
        r"\bcomputer.?use\b",
        r"\bcomputer.?control\b",
        r"\bdesktop.?automation\b",
        r"\bmouse\b",
        r"\bkeyboard\b",
        r"\bscreenshot\b",
        r"\bpyautogui\b",
    ],
    "Tools": [
        r"\btools?\b",
        r"\btool.?registry\b",
        r"\btool.?executor\b",
        r"\bplugin\b",
        r"\bplugins\b",
        r"\bfunction\b",
    ],
    "Workflow": [
        r"\bworkflow\b",
        r"\bworkflows\b",
        r"\borchestrat",
        r"\bpipeline\b",
        r"\btask.?queue\b",
        r"\bjob.?queue\b",
    ],
    "Planning": [
        r"\bplanner\b",
        r"\bplanning\b",
        r"\bplan.?and.?execute\b",
        r"\btask.?planning\b",
        r"\bgoal\b",
    ],
    "Security": [
        r"\bauthentication\b",
        r"\bauthorization\b",
        r"\bpermissions?\b",
        r"\brbac\b",
        r"\bsecurity\b",
        r"\bsecrets?\b",
        r"\bcredential",
        r"\bencryption\b",
        r"\btoken\b",
    ],
    "Voice": [
        r"\bspeech\b",
        r"\bspeech.?to.?text\b",
        r"\btext.?to.?speech\b",
        r"\bwhisper\b",
        r"\bvoice\b",
        r"\baudio\b",
    ],
    "UI": [
        r"\breact\b",
        r"\bnext\.?js\b",
        r"\bvue\b",
        r"\bfrontend\b",
        r"\binterface\b",
        r"\bdashboard\b",
        r"\bweb.?app\b",
    ],
    "Automation": [
        r"\bautomation\b",
        r"\bscheduler\b",
        r"\bcron\b",
        r"\bbackground.?job\b",
        r"\btask.?runner\b",
    ],
    "Container": [
        r"\bdocker\b",
        r"\bcontainer\b",
        r"\bkubernetes\b",
        r"\bk8s\b",
    ],
    "API": [
        r"\bfastapi\b",
        r"\bflask\b",
        r"\bexpress\b",
        r"\bapi\b",
        r"\brest\b",
        r"\bgraphql\b",
    ],
}


COMPILED_PATTERNS = {
    capability: [re.compile(pattern, re.IGNORECASE)
                 for pattern in patterns]
    for capability, patterns in CAPABILITY_PATTERNS.items()
}


# ============================================================
# HELPERS
# ============================================================

def is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS


def safe_read(path: Path) -> str:
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return ""

        return path.read_text(
            encoding="utf-8",
            errors="ignore"
        )
    except (OSError, UnicodeError):
        return ""


def detect_language(path: Path) -> str | None:
    ext = path.suffix.lower()

    mapping = {
        ".py": "Python",
        ".js": "JavaScript",
        ".jsx": "JavaScript/JSX",
        ".ts": "TypeScript",
        ".tsx": "TypeScript/TSX",
        ".rs": "Rust",
        ".go": "Go",
        ".java": "Java",
        ".kt": "Kotlin",
        ".cs": "C#",
        ".rb": "Ruby",
        ".php": "PHP",
        ".c": "C",
        ".cpp": "C++",
        ".h": "C/C++",
        ".hpp": "C++",
        ".swift": "Swift",
        ".sh": "Shell",
        ".ps1": "PowerShell",
        ".yaml": "YAML",
        ".yml": "YAML",
        ".json": "JSON",
        ".toml": "TOML",
        ".md": "Markdown",
    }

    return mapping.get(ext)


def should_skip_dir(name: str) -> bool:
    return name.lower() in {x.lower() for x in SKIP_DIRS}


def find_project_roots(root: Path) -> list[Path]:
    """
    Discover projects without deeply scanning every source file.

    A directory becomes a candidate project when it contains:
    - a known manifest, or
    - a README.

    Once a project root is found, its children are not recursively
    treated as separate projects unless they are clearly independent.
    """

    projects = []

    stack = [root]

    while stack and len(projects) < MAX_PROJECTS:
        current = stack.pop()

        try:
            entries = list(os.scandir(current))
        except OSError:
            continue

        names = {entry.name for entry in entries}

        has_manifest = bool(names.intersection(MANIFEST_FILES))
        has_readme = bool(names.intersection(README_NAMES))

        # Root itself is always considered a project.
        if current == root:
            projects.append(current)
            continue

        if has_manifest or has_readme:
            projects.append(current)

            # Don't explode monorepos into every nested package.
            continue

        for entry in reversed(entries):
            if not entry.is_dir():
                continue

            if should_skip_dir(entry.name):
                continue

            stack.append(Path(entry.path))

    return projects


def select_files(project: Path, max_files: int = MAX_SAMPLE_FILES) -> list[Path]:
    """
    Select high-value files rather than scanning everything.
    """

    selected: list[Path] = []
    seen: set[str] = set()

    def add(path: Path):
        key = str(path).lower()

        if key in seen:
            return

        if len(selected) >= max_files:
            return

        if not path.is_file():
            return

        if not is_text_file(path):
            return

        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                return
        except OSError:
            return

        seen.add(key)
        selected.append(path)

    # --------------------------------------------------------
    # 1. README / manifests
    # --------------------------------------------------------

    try:
        root_entries = list(os.scandir(project))
    except OSError:
        return selected

    for entry in root_entries:
        if not entry.is_file():
            continue

        name = entry.name

        if name in MANIFEST_FILES or name in README_NAMES:
            add(Path(entry.path))

    # --------------------------------------------------------
    # 2. Important directories
    # --------------------------------------------------------

    for important_dir in IMPORTANT_DIRS:

        candidate = project / important_dir

        if not candidate.is_dir():
            continue

        count = 0

        for current, dirs, files in os.walk(candidate):

            dirs[:] = [
                d for d in dirs
                if not should_skip_dir(d)
            ]

            for filename in files:

                if count >= 100:
                    break

                path = Path(current) / filename

                if is_text_file(path):
                    add(path)
                    count += 1

    # --------------------------------------------------------
    # 3. Limited fallback scan
    # --------------------------------------------------------

    if len(selected) < min(50, max_files):

        count = 0

        for current, dirs, files in os.walk(project):

            dirs[:] = [
                d for d in dirs
                if not should_skip_dir(d)
            ]

            for filename in files:

                if len(selected) >= max_files:
                    break

                if count >= max_files:
                    break

                path = Path(current) / filename

                if is_text_file(path):
                    add(path)
                    count += 1

    return selected


def find_capabilities(text: str, path: Path) -> Counter:
    """
    Capability detection.

    Path evidence receives additional weight because files such as
    agents/, memory/, security/, etc. are strong structural signals.
    """

    scores = Counter()

    lowered_path = str(path).lower()

    for capability, patterns in COMPILED_PATTERNS.items():

        score = 0

        for pattern in patterns:

            # Only stop after first matching pattern for this capability.
            if pattern.search(text):
                score += 1

        if score:
            scores[capability] += min(score, 3)

        # Structural evidence.
        path_parts = set(
            re.split(r"[\\/._-]+", lowered_path)
        )

        capability_tokens = {
            "LLM": {"llm", "model", "models"},
            "Agent": {"agent", "agents"},
            "Memory": {"memory"},
            "RAG": {"rag", "retrieval", "embedding"},
            "Database": {"database", "db"},
            "Browser": {"browser"},
            "Computer Use": {"computer", "desktop"},
            "Tools": {"tool", "tools"},
            "Workflow": {"workflow", "workflows"},
            "Planning": {"planner", "planning"},
            "Security": {"security", "auth"},
            "Voice": {"voice", "audio", "speech"},
            "UI": {"ui", "frontend", "dashboard"},
            "Automation": {"automation", "scheduler"},
            "Container": {"docker", "container"},
            "API": {"api", "server"},
        }

        if path_parts.intersection(capability_tokens.get(capability, set())):
            scores[capability] += 2

    return scores


def capability_level(score: int) -> str:
    if score >= 8:
        return "HIGH"

    if score >= 4:
        return "MEDIUM"

    if score >= 1:
        return "LOW"

    return "NONE"


# ============================================================
# PROJECT SCANNER
# ============================================================

def scan_project(project: Path, sample_limit: int = MAX_SAMPLE_FILES) -> dict:

    files = select_files(project, sample_limit)

    languages = Counter()
    capabilities = Counter()

    analyzed_files = 0

    dependency_files = []

    for path in files:

        language = detect_language(path)

        if language:
            languages[language] += 1

        if path.name in MANIFEST_FILES:
            dependency_files.append(str(path.relative_to(project)))

        text = safe_read(path)

        if not text:
            continue

        analyzed_files += 1

        scores = find_capabilities(text, path)

        capabilities.update(scores)

    capability_levels = {
        name: capability_level(score)
        for name, score in capabilities.items()
        if score > 0
    }

    return {
        "project": project.name,
        "path": str(project),
        "files_sampled": len(files),
        "files_analyzed": analyzed_files,
        "languages": dict(languages.most_common()),
        "dependency_files": dependency_files,
        "capabilities": dict(
            sorted(
                capability_levels.items(),
                key=lambda item: (
                    {"HIGH": 3, "MEDIUM": 2, "LOW": 1}[item[1]],
                    item[0],
                ),
                reverse=True,
            )
        ),
        "capability_scores": dict(capabilities),
    }


# ============================================================
# REPOSITORY SCANNER
# ============================================================

def scan_repository(repo: Path) -> dict:

    print(f"    Discovering projects...")

    projects = find_project_roots(repo)

    # Normal repository:
    # scan itself if it looks like one coherent project.
    if repo.name != "Repos":

        projects = [repo]

    print(f"    Projects detected: {len(projects)}")

    project_results = []

    for index, project in enumerate(projects, start=1):

        if repo.name == "Repos":
            print(
                f"      [{index}/{len(projects)}] "
                f"{project.name}"
            )

        result = scan_project(project)

        project_results.append(result)

    # Aggregate languages and capabilities.
    all_languages = Counter()
    all_capabilities = Counter()

    total_sampled = 0

    for result in project_results:

        all_languages.update(result["languages"])
        total_sampled += result["files_sampled"]

        for capability, score in result["capability_scores"].items():
            all_capabilities[capability] += score

    return {
        "repository": repo.name,
        "path": str(repo),
        "projects_detected": len(project_results),
        "files_sampled_total": total_sampled,
        "languages": dict(all_languages.most_common()),
        "capabilities": {
            capability: capability_level(score)
            for capability, score
            in sorted(
                all_capabilities.items(),
                key=lambda x: x[1],
                reverse=True,
            )
            if score > 0
        },
        "projects": project_results,
    }


# ============================================================
# MAIN
# ============================================================

def main():

    if len(sys.argv) < 2:
        print(
            "Usage:\n"
            "  python -m src.repo_deep_auditor "
            '"00_FOUNDATION/Architecture/Old_Repositories"'
        )
        sys.exit(1)

    root = Path(sys.argv[1]).resolve()

    if not root.exists():
        print(f"ERROR: Path does not exist: {root}")
        sys.exit(1)

    repositories = [
        path
        for path in root.iterdir()
        if path.is_dir()
        and not should_skip_dir(path.name)
    ]

    repositories.sort(key=lambda p: p.name.lower())

    print("=" * 60)
    print("KAIRO OPTIMIZED REPOSITORY DEEP AUDITOR")
    print("=" * 60)
    print("Mode: READ-ONLY")
    print("Repository execution: DISABLED")
    print(f"Repositories found: {len(repositories)}")
    print()

    results = []

    for index, repo in enumerate(repositories, start=1):

        print(
            f"[{index}/{len(repositories)}] "
            f"Deep analyzing: {repo.name}"
        )

        result = scan_repository(repo)

        results.append(result)

        print(
            f"    Sampled files: "
            f"{result['files_sampled_total']}"
        )

        print(
            f"    Projects: "
            f"{result['projects_detected']}"
        )

        if result["capabilities"]:
            top = list(result["capabilities"].items())[:8]

            print(
                "    Top capabilities: "
                + ", ".join(
                    f"{name}={level}"
                    for name, level in top
                )
            )

        print()

    report = {
        "tool": "KAIRO Optimized Repository Deep Auditor",
        "mode": "READ-ONLY",
        "repository_execution": False,
        "root": str(root),
        "repositories": results,
    }

    output_path = (
        Path.cwd()
        / "10_DOCUMENTATION"
        / "Technical"
        / "repository_deep_audit.json"
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("=" * 60)
    print("DEEP AUDIT COMPLETE")
    print("=" * 60)
    print(f"Repositories audited: {len(results)}")
    print(f"Report created:")
    print(output_path)
    print()
    print("No repository code was executed.")


if __name__ == "__main__":
    main()