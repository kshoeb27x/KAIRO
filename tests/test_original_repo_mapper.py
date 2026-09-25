from src.original_repo_mapper import (
    build_repo_matrix,
    classify_repo,
    discover_nested_repositories,
    discover_original_repositories,
)


def test_original_repository_discovery_handles_missing_archive(tmp_path):
    assert discover_original_repositories(tmp_path) == []


def test_original_repositories_are_discovered_from_an_archive(tmp_path):
    for name in ("memU", "Open-Computer-Use", "Repos"):
        (tmp_path / name).mkdir()

    repos = discover_original_repositories(tmp_path)

    assert repos == ["Open-Computer-Use", "Repos", "memU"]


def test_repo_classification_maps_to_kairo_domains():
    memu = classify_repo("memU")
    open_use = classify_repo("Open-Computer-Use")
    volt = classify_repo("VoltAgent")

    assert memu["kairo_domain"] == "03_DATA"
    assert memu["recommendation"] == "EXTRACT"
    assert open_use["kairo_domain"] == "04_TOOLS"
    assert volt["kairo_domain"] == "07_RUNTIME"


def test_repo_matrix_includes_adaptable_candidates(tmp_path):
    for name in ("memU", "Open-Computer-Use", "VoltAgent", "Repos"):
        (tmp_path / name).mkdir()

    matrix = build_repo_matrix(tmp_path)

    assert any(entry["repository"] == "memU" and entry["recommendation"] == "EXTRACT" for entry in matrix)
    assert any(entry["repository"] == "Open-Computer-Use" and entry["recommendation"] == "ADAPT" for entry in matrix)
    assert any(entry["repository"] == "Repos" and entry["recommendation"] == "KEEP" for entry in matrix)


def test_nested_repository_discovery(tmp_path):
    project = tmp_path / "nested-project"
    project.mkdir()
    (project / ".git").mkdir()

    assert discover_nested_repositories(tmp_path) == ["nested-project"]
