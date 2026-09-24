from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_package(
    alias: str,
    directory: str,
) -> ModuleType:
    package_root = PROJECT_ROOT / directory
    init_file = package_root / "__init__.py"

    if not init_file.exists():
        raise ImportError(
            f"Package initializer not found: {init_file}"
        )

    existing = sys.modules.get(alias)

    if existing is not None:
        return existing

    spec = importlib.util.spec_from_file_location(
        alias,
        init_file,
        submodule_search_locations=[
            str(package_root)
        ],
    )

    if spec is None or spec.loader is None:
        raise ImportError(
            f"Unable to create package spec: {alias}"
        )

    module = importlib.util.module_from_spec(spec)

    sys.modules[alias] = module

    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(alias, None)
        raise

    return module


def load_components() -> dict[str, object]:
    agents = load_package(
        "kairo_agents",
        "02_AGENTS",
    )

    runtime = load_package(
        "kairo_runtime",
        "07_RUNTIME",
    )

    data = load_package(
        "kairo_data",
        "03_DATA",
    )

    security = load_package(
        "kairo_security",
        "06_SECURITY",
    )

    return {
        "agents": agents.AgentManager,
        "runtime": runtime.RuntimeManager,
        "database": data.Database,
        "knowledge": data.KnowledgeStore,
        "vector": data.VectorStore,
        "data_manager": data.DataManager,
        "security": security.SecurityManager,
    }


def load_original_repo_matrix() -> list[dict[str, str]]:
    """Return a safe repository-to-KAIRO mapping for archived upstream projects."""

    from src.original_repo_mapper import build_repo_matrix

    return build_repo_matrix()


def load_original_repo_classification(repo_name: str) -> dict[str, str]:
    """Return the KAIRO fit for a single archived upstream repository."""

    from src.original_repo_mapper import classify_repo

    return classify_repo(repo_name)