import json
from pathlib import Path

from src.capability_mapper import build_matrix
from src.main import REQUIRED_REPORTS, build_status, validate_foundation
from src.policy import KairoConfig, load_policy


def write_policy(path: Path) -> None:
    path.write_text(
        """approval:
  critical_actions: true
sandbox:
  enabled: true
  network_default: restricted
audit:
  enabled: true
  immutable_target_required: true
""",
        encoding="utf-8",
    )


def write_foundation(project_root: Path) -> None:
    (project_root / "config").mkdir()
    (project_root / "03_DATA").mkdir()
    technical_docs = project_root / "10_DOCUMENTATION" / "Technical"
    technical_docs.mkdir(parents=True)
    write_policy(project_root / "config" / "policy.yaml")

    for report in REQUIRED_REPORTS:
        payload = {"candidates": []} if report == "repository_decisions.json" else {}
        (technical_docs / report).write_text(json.dumps(payload), encoding="utf-8")


def test_critical_actions_default_to_approval(monkeypatch, tmp_path):
    for name in (
        "KAIRO_ENV",
        "KAIRO_LOG_LEVEL",
        "KAIRO_DATA_ROOT",
        "KAIRO_REQUIRE_APPROVAL_FOR_CRITICAL",
    ):
        monkeypatch.delenv(name, raising=False)

    config = KairoConfig.from_environment(tmp_path)

    assert config.environment == "development"
    assert config.require_approval_for_critical is True


def test_config_reads_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("KAIRO_ENV", "test")
    monkeypatch.setenv("KAIRO_LOG_LEVEL", "debug")
    monkeypatch.setenv("KAIRO_DATA_ROOT", "runtime-data")
    monkeypatch.setenv("KAIRO_REQUIRE_APPROVAL_FOR_CRITICAL", "false")

    config = KairoConfig.from_environment(tmp_path)

    assert config.environment == "test"
    assert config.log_level == "DEBUG"
    assert config.require_approval_for_critical is False
    assert config.resolved_data_root(tmp_path) == tmp_path / "runtime-data"


def test_policy_is_loaded_and_validated(tmp_path):
    policy_path = tmp_path / "policy.yaml"
    write_policy(policy_path)

    policy = load_policy(policy_path)

    assert policy.approval.critical_actions is True
    assert policy.sandbox.network_default == "restricted"
    assert policy.audit.immutable_target_required is True


def test_capability_matrix_uses_repository_field_and_decisions():
    deep_audit = {
        "repositories": [
            {"repository": "memU", "capabilities": {"Memory": "HIGH"}},
            {"name": "legacy", "capabilities": {"Agent": "LOW"}},
        ]
    }
    decisions = {
        "candidates": [
            {"repository": "memU", "strategy": "EXTRACT"},
        ]
    }

    matrix = build_matrix(deep_audit, decisions)

    assert matrix["repositories"] == [
        {
            "repository": "memU",
            "capabilities": {"Memory": "HIGH"},
            "decision": "EXTRACT",
        },
        {
            "repository": "legacy",
            "capabilities": {"Agent": "LOW"},
            "decision": "REVIEW",
        },
    ]


def test_status_and_validation_are_read_only(tmp_path):
    write_foundation(tmp_path)

    status = build_status(tmp_path)
    validation = validate_foundation(tmp_path)

    assert status["critical_approval_required"] is True
    assert all(status["reports_present"].values())
    assert validation["valid"] is True
    assert validation["missing_reports"] == []
