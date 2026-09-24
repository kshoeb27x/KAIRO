"""Repository capability mapping utilities."""

from __future__ import annotations

from typing import Any


KAIRO_CAPABILITIES = [
    "LLM",
    "Agent",
    "Reasoning",
    "Planning",
    "Memory",
    "RAG",
    "Database",
    "API",
    "Tools",
    "Workflow",
    "Browser",
    "Computer Use",
    "UI",
    "Voice",
    "Security",
    "Container",
    "Automation",
]


def load_json(data: dict[str, Any] | Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object.")
    return data


def get_capabilities(repo: dict[str, Any]) -> dict[str, str]:
    capabilities = repo.get("capabilities", {})
    if not isinstance(capabilities, dict):
        raise ValueError("Repository capability map must be an object.")

    result: dict[str, str] = {}
    for capability in KAIRO_CAPABILITIES:
        value = capabilities.get(capability)
        if value is not None:
            result[capability] = value
    return result


def decision_lookup(decisions: dict[str, Any] | None) -> dict[str, str]:
    if decisions is None:
        return {}
    candidates = decisions.get("candidates", [])
    if not isinstance(candidates, list):
        raise ValueError("Decision manifest field 'candidates' must be a list.")

    lookup: dict[str, str] = {}
    for candidate in candidates:
        if not isinstance(candidate, dict):
            raise ValueError("Every decision candidate must be an object.")
        name = candidate.get("repository")
        strategy = candidate.get("strategy")
        if not isinstance(name, str) or not name:
            raise ValueError("Every decision candidate needs a repository name.")
        if not isinstance(strategy, str) or not strategy:
            raise ValueError("Every decision candidate needs a strategy.")
        lookup[name] = strategy
    return lookup


def build_matrix(data: dict[str, Any], decisions: dict[str, Any] | None = None) -> dict[str, Any]:
    repositories = data.get("repositories", [])
    if not isinstance(repositories, list):
        raise ValueError("Deep audit field 'repositories' must be a list.")

    strategies = decision_lookup(decisions)
    matrix = {
        "project": "KAIRO",
        "purpose": "Map existing repositories against KAIRO capabilities",
        "mode": "READ-ONLY",
        "repositories": [],
    }

    for repo in repositories:
        if not isinstance(repo, dict):
            raise ValueError("Every deep-audit repository must be an object.")
        name = repo.get("repository") or repo.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("Every deep-audit repository needs a name.")

        matrix["repositories"].append(
            {
                "repository": name,
                "capabilities": get_capabilities(repo),
                "decision": strategies.get(name, "REVIEW"),
            }
        )

    return matrix
