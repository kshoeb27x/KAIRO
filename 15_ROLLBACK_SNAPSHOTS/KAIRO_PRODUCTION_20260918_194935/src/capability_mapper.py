import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    BASE_DIR
    / "10_DOCUMENTATION"
    / "Technical"
    / "repository_deep_audit.json"
)

OUTPUT_FILE = (
    BASE_DIR
    / "10_DOCUMENTATION"
    / "Technical"
    / "kairo_capability_matrix.json"
)

DECISIONS_FILE = (
    BASE_DIR
    / "10_DOCUMENTATION"
    / "Technical"
    / "repository_decisions.json"
)


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


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return data


def get_capabilities(repo: dict[str, Any]) -> dict[str, str]:
    capabilities = repo.get("capabilities", {})

    result = {}

    for capability in KAIRO_CAPABILITIES:
        value = capabilities.get(capability)

        if value is not None:
            result[capability] = value

    return result


def decision_lookup(decisions: dict[str, Any]) -> dict[str, str]:
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


def build_matrix(
    data: dict[str, Any], decisions: dict[str, Any] | None = None
) -> dict[str, Any]:
    repositories = data.get("repositories", [])
    if not isinstance(repositories, list):
        raise ValueError("Deep audit field 'repositories' must be a list.")
    strategies = decision_lookup(decisions) if decisions else {}

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


def save_matrix(matrix: dict[str, Any], output_file: Path = OUTPUT_FILE) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w", encoding="utf-8") as file:
        json.dump(matrix, file, indent=2, ensure_ascii=False)
        file.write("\n")

    print("Capability matrix created:")
    print(output_file)


def main():
    print("=" * 60)
    print("KAIRO CAPABILITY MAPPER")
    print("=" * 60)

    if not INPUT_FILE.exists():
        print("ERROR: Deep audit report not found:")
        print(INPUT_FILE)
        return

    data = load_json(INPUT_FILE)
    decisions = load_json(DECISIONS_FILE) if DECISIONS_FILE.exists() else None
    matrix = build_matrix(data, decisions)

    print()
    print("Repositories mapped:", len(matrix["repositories"]))

    save_matrix(matrix)

    print()
    print("Capability mapping complete.")
    print("No repository code was executed.")


if __name__ == "__main__":
    main()
