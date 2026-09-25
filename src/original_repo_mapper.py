"""Safe mapping of archived original repositories into KAIRO capability domains."""

from __future__ import annotations

from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ORIGINAL_REPOSITORIES_ROOT = PROJECT_ROOT / "11_ARCHIVE" / "Original_Repositories"

REPO_CLASSIFICATION = {
    "memU": {
        "kairo_domain": "03_DATA",
        "capability": "Memory, Knowledge, RAG",
        "recommendation": "EXTRACT",
        "reason": "Strong memory/vector/knowledge patterns fit KAIRO data layer.",
    },
    "Open-Computer-Use": {
        "kairo_domain": "04_TOOLS",
        "capability": "Browser Automation, Computer Use",
        "recommendation": "ADAPT",
        "reason": "Useful browser and computer-use workflows should be adapted into tool runtime wrappers.",
    },
    "VoltAgent": {
        "kairo_domain": "07_RUNTIME",
        "capability": "Workflow Orchestration, Agent Runtime",
        "recommendation": "ADAPT",
        "reason": "Useful orchestration and workflow semantics map cleanly to runtime execution.",
    },
    "OCT-Agent": {
        "kairo_domain": "02_AGENTS",
        "capability": "Agent Coordination, Execution",
        "recommendation": "ADAPT",
        "reason": "Agent coordination patterns can inform KAIRO agent registry and task execution.",
    },
    "OpenMind": {
        "kairo_domain": "09_INTELLIGENCE",
        "capability": "Reasoning, Planning, Self-Improvement",
        "recommendation": "EXTRACT",
        "reason": "Reasoning and planning loops can feed the intelligence layer without copying the full repo.",
    },
    "MIRA": {
        "kairo_domain": "09_INTELLIGENCE",
        "capability": "AI Reasoning, Decision Support",
        "recommendation": "REVIEW",
        "reason": "Potential intelligence patterns worth reviewing, but not a direct import.",
    },
    "Awesome-Personal-AI": {
        "kairo_domain": "05_UI",
        "capability": "Personal assistant UX, interaction patterns",
        "recommendation": "ADAPT",
        "reason": "UI and assistant ergonomics can be adapted into KAIRO presentation layers.",
    },
    "Repos": {
        "kairo_domain": "11_ARCHIVE",
        "capability": "Multi-project source inventory",
        "recommendation": "KEEP",
        "reason": "This is a source archive and extraction pool, not a direct application module.",
    },
}


def discover_original_repositories(root: Path | str = ORIGINAL_REPOSITORIES_ROOT) -> list[str]:
    """Return the known archived repositories that are candidates for integration."""

    repo_root = Path(root)
    if not repo_root.exists():
        return []

    return sorted(
        entry.name
        for entry in repo_root.iterdir()
        if entry.is_dir()
    )


def discover_nested_repositories(
    root: Path | str = ORIGINAL_REPOSITORIES_ROOT / "Repos",
) -> list[str]:
    """Discover independent repositories below an archive collection."""

    repo_root = Path(root)
    if not repo_root.exists():
        return []

    discovered: list[str] = []
    for git_path in repo_root.rglob(".git"):
        project = git_path.parent
        if project == repo_root:
            continue
        discovered.append(str(project.relative_to(repo_root)))

    return sorted(discovered)


def classify_repo(repo_name: str) -> dict[str, str]:
    """Map a repository name to the KAIRO domain that best fits it."""

    classification = REPO_CLASSIFICATION.get(repo_name)
    if classification is not None:
        return {
            "repository": repo_name,
            **classification,
        }

    lowered = repo_name.lower()
    if "memory" in lowered or "rag" in lowered:
        return {
            "repository": repo_name,
            "kairo_domain": "03_DATA",
            "capability": "Memory, RAG",
            "recommendation": "REVIEW",
            "reason": "Repository suggests a memory or retrieval stack.",
        }
    if "agent" in lowered or "assistant" in lowered:
        return {
            "repository": repo_name,
            "kairo_domain": "02_AGENTS",
            "capability": "Agent Workflow",
            "recommendation": "REVIEW",
            "reason": "Repository suggests agent workflows or orchestration patterns.",
        }
    if "browser" in lowered or "computer" in lowered or "tool" in lowered:
        return {
            "repository": repo_name,
            "kairo_domain": "04_TOOLS",
            "capability": "Tools and automation",
            "recommendation": "REVIEW",
            "reason": "Repository suggests browser or computer-use tools.",
        }

    return {
        "repository": repo_name,
        "kairo_domain": "11_ARCHIVE",
        "capability": "Unclassified source",
        "recommendation": "REVIEW",
        "reason": "Keep archived until a targeted review confirms the right KAIRO fit.",
    }


def build_repo_matrix(root: Path | str = ORIGINAL_REPOSITORIES_ROOT) -> list[dict[str, str]]:
    """Create a safe matrix that maps archived repositories to KAIRO architecture domains."""

    repositories = discover_original_repositories(root)
    return [classify_repo(name) for name in repositories]


def recommended_integrations(root: Path | str = ORIGINAL_REPOSITORIES_ROOT) -> list[dict[str, str]]:
    """Return only repositories that are ready for direct adaptation or extraction."""

    return [entry for entry in build_repo_matrix(root) if entry["recommendation"] in {"EXTRACT", "ADAPT"}]
