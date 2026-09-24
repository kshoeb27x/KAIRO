import json
import os
from pathlib import Path
from collections import Counter


# ============================================================
# KAIRO REPOSITORY CAPABILITY AUDITOR
# READ-ONLY — NEVER EXECUTES REPOSITORY CODE
# ============================================================

SKIP_DIRS = {
    ".git", ".hg", ".svn",
    ".venv", "venv",
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

TEXT_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx",
    ".rs", ".go", ".java", ".cs",
    ".cpp", ".c", ".h", ".hpp",
    ".rb", ".php", ".swift", ".kt",
    ".yaml", ".yml", ".json", ".toml",
    ".md", ".txt", ".ini", ".cfg",
    ".sh", ".ps1",
}

MANIFEST_FILES = {
    "requirements.txt",
    "pyproject.toml",
    "package.json",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "cargo.toml",
    "go.mod",
    "pom.xml",
    "gemfile",
}

CAPABILITY_PATTERNS = {
    "AI / LLM": [
        "openai", "anthropic", "gemini", "llm",
        "transformer", "huggingface", "langchain",
        "llama", "ollama", "model", "inference",
    ],

    "Agents": [
        "agent", "multi-agent", "autonomous",
        "agentic", "assistant",
    ],

    "Orchestration": [
        "orchestrat", "workflow", "pipeline",
        "task manager", "scheduler", "queue",
    ],

    "Memory": [
        "memory", "long-term memory", "short-term memory",
        "episodic", "semantic memory",
    ],

    "RAG / Knowledge": [
        "rag", "retrieval", "vector",
        "embedding", "knowledge base",
        "chromadb", "pinecone", "weaviate",
        "faiss",
    ],

    "Browser / Web Automation": [
        "browser", "playwright", "selenium",
        "puppeteer", "web automation",
    ],

    "Computer Use": [
        "computer use", "computer-use",
        "desktop", "mouse", "keyboard",
        "pyautogui", "screen control",
    ],

    "MCP": [
        "model context protocol", "mcp",
        "mcp server", "mcp client",
    ],

    "Tools / APIs": [
        "api", "tool", "function calling",
        "webhook", "rest", "graphql",
    ],

    "Voice / Audio": [
        "speech", "voice", "audio",
        "whisper", "tts", "stt",
        "text-to-speech", "speech-to-text",
    ],

    "Vision / OCR": [
        "vision", "ocr", "image",
        "computer vision", "opencv",
        "tesseract",
    ],

    "Planning / Reasoning": [
        "planner", "planning", "reasoning",
        "chain of thought", "reflection",
        "react agent",
    ],

    "Database": [
        "postgres", "postgresql", "mysql",
        "sqlite", "mongodb", "redis",
        "database", "sql",
    ],

    "Security / Auth": [
        "security", "authentication",
        "authorization", "oauth",
        "jwt", "permission", "rbac",
        "secret", "credential",
    ],

    "Automation": [
        "automation", "cron",
        "scheduled", "task", "workflow",
    ],

    "UI / Dashboard": [
        "dashboard", "frontend", "react",
        "next.js", "streamlit", "gradio",
        "electron", "ui",
    ],
}


def read_text_file(path, max_chars=100_000):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(max_chars).lower()
    except Exception:
        return ""


def scan_repository(repo_path):
    repo_path = Path(repo_path)

    files = []
    extensions = Counter()
    manifests = []
    capability_hits = Counter()
    evidence = {}

    for root, dirs, filenames in os.walk(repo_path):

        # Prevent descending into unwanted directories
        dirs[:] = [
            d for d in dirs
            if d.lower() not in SKIP_DIRS
        ]

        for filename in filenames:
            path = Path(root) / filename
            files.append(str(path.relative_to(repo_path)))

            ext = path.suffix.lower()

            if ext:
                extensions[ext] += 1

            if filename.lower() in MANIFEST_FILES:
                manifests.append(str(path.relative_to(repo_path)))

            # Only inspect likely text/source files
            if ext not in TEXT_EXTENSIONS:
                continue

            text = read_text_file(path)

            if not text:
                continue

            for capability, patterns in CAPABILITY_PATTERNS.items():
                hits = []

                for pattern in patterns:
                    if pattern.lower() in text:
                        hits.append(pattern)

                if hits:
                    capability_hits[capability] += len(hits)

                    if capability not in evidence:
                        evidence[capability] = []

                    # Keep evidence manageable
                    for hit in hits[:5]:
                        if hit not in evidence[capability]:
                            evidence[capability].append(hit)

    capabilities = [
        name
        for name, count in capability_hits.most_common()
        if count > 0
    ]

    return {
        "repository": repo_path.name,
        "path": str(repo_path),
        "file_count": len(files),
        "languages": dict(extensions.most_common()),
        "manifests": manifests,
        "capabilities": capabilities,
        "capability_scores": dict(capability_hits.most_common()),
        "evidence": evidence,
    }


def find_repositories(root_path):
    root_path = Path(root_path)

    repositories = []

    for item in sorted(root_path.iterdir()):
        if not item.is_dir():
            continue

        if item.name.lower() in SKIP_DIRS:
            continue

        repositories.append(item)

    return repositories


def main():
    import sys

    if len(sys.argv) < 2:
        print(
            'Usage: python -m src.repo_capability_auditor '
            '"00_FOUNDATION/Architecture/Old_Repositories"'
        )
        return

    root_path = Path(sys.argv[1])

    if not root_path.exists():
        print(f"ERROR: Path does not exist: {root_path}")
        return

    repositories = find_repositories(root_path)

    print("=" * 60)
    print("KAIRO REPOSITORY CAPABILITY AUDITOR")
    print("=" * 60)
    print("Mode: READ-ONLY")
    print("Repository code execution: DISABLED")
    print(f"Repositories found: {len(repositories)}")
    print()

    results = []

    for index, repo in enumerate(repositories, start=1):
        print(
            f"[{index}/{len(repositories)}] "
            f"Analyzing: {repo.name}"
        )

        result = scan_repository(repo)
        results.append(result)

        print(f"    Files: {result['file_count']}")
        print(
            "    Capabilities: "
            + (
                ", ".join(result["capabilities"])
                if result["capabilities"]
                else "None detected"
            )
        )
        print(
            f"    Manifests: {len(result['manifests'])}"
        )
        print()

    output_path = Path(
        "10_DOCUMENTATION/Technical/"
        "repository_capability_audit.json"
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    report = {
        "tool": "KAIRO Repository Capability Auditor",
        "version": "1.0",
        "mode": "READ-ONLY",
        "code_execution": False,
        "source": str(root_path),
        "repositories_audited": len(results),
        "repositories": results,
    }

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            report,
            f,
            indent=2,
            ensure_ascii=False
        )

    print("=" * 60)
    print("CAPABILITY AUDIT COMPLETE")
    print("=" * 60)
    print(f"Repositories audited: {len(results)}")
    print("Report created:")
    print(output_path.resolve())
    print()
    print("No repository code was executed.")


if __name__ == "__main__":
    main()