"""Command-line entry point for the KAIRO foundation."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

from src.policy import KairoConfig, PROJECT_ROOT, load_policy


TECHNICAL_DOCS = PROJECT_ROOT / "10_DOCUMENTATION" / "Technical"
DECISIONS_PATH = TECHNICAL_DOCS / "repository_decisions.json"
REQUIRED_REPORTS = (
    "repository_audit.json",
    "repository_capability_audit.json",
    "repository_deep_audit.json",
    "kairo_capability_matrix.json",
    "repository_decisions.json",
)


def read_json(path: Path) -> Any:
    """Read a JSON artifact and return a useful error for the CLI."""

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ValueError(f"Unable to read JSON artifact: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON artifact: {path}: {error.msg}") from error


def decision_summary(decisions_path: Path = DECISIONS_PATH) -> dict[str, int]:
    """Return counts by approved repository strategy."""

    data = read_json(decisions_path)
    candidates = data.get("candidates", [])
    if not isinstance(candidates, list):
        raise ValueError("Decision manifest field 'candidates' must be a list.")

    strategies = Counter()
    for candidate in candidates:
        if not isinstance(candidate, dict):
            raise ValueError("Each decision candidate must be an object.")
        strategy = candidate.get("strategy")
        if not isinstance(strategy, str) or not strategy:
            raise ValueError("Each decision candidate needs a non-empty strategy.")
        strategies[strategy] += 1

    return dict(sorted(strategies.items()))


def build_status(project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    """Build a non-mutating health snapshot of the KAIRO foundation."""

    config = KairoConfig.from_environment(project_root)
    policy = load_policy(project_root / "config" / "policy.yaml")
    report_paths = {
        name: (project_root / "10_DOCUMENTATION" / "Technical" / name).exists()
        for name in REQUIRED_REPORTS
    }
    decisions = decision_summary(
        project_root / "10_DOCUMENTATION" / "Technical" / "repository_decisions.json"
    )

    return {
        "project": "KAIRO",
        "mode": "foundation",
        "environment": config.environment,
        "critical_approval_required": config.require_approval_for_critical,
        "data_root": str(config.resolved_data_root(project_root)),
        "data_root_exists": config.resolved_data_root(project_root).is_dir(),
        "policy": {
            "sandbox_enabled": policy.sandbox.enabled,
            "network_default": policy.sandbox.network_default,
            "audit_enabled": policy.audit.enabled,
            "immutable_target_required": policy.audit.immutable_target_required,
        },
        "reports_present": report_paths,
        "decision_summary": decisions,
    }


def validate_foundation(project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    """Validate configuration and generated artifact shapes without executing code."""

    status = build_status(project_root)
    technical_docs = project_root / "10_DOCUMENTATION" / "Technical"
    missing_reports = [
        name for name, present in status["reports_present"].items() if not present
    ]

    parsed_reports: list[str] = []
    for name in REQUIRED_REPORTS:
        path = technical_docs / name
        if path.exists():
            read_json(path)
            parsed_reports.append(name)

    return {
        "valid": not missing_reports and status["data_root_exists"],
        "missing_reports": missing_reports,
        "data_root_exists": status["data_root_exists"],
        "parsed_reports": parsed_reports,
        "decision_summary": status["decision_summary"],
    }


def _emit(data: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, indent=2, sort_keys=True))
        return

    for key, value in data.items():
        if isinstance(value, dict):
            print(f"{key}:")
            for nested_key, nested_value in value.items():
                print(f"  {nested_key}: {nested_value}")
        elif isinstance(value, list):
            print(f"{key}: {', '.join(map(str, value)) or 'none'}")
        else:
            print(f"{key}: {value}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="KAIRO Foundation CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("status", "validate", "decisions"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("--json", action="store_true", dest="as_json")

    args = parser.parse_args(argv)
    try:
        if args.command == "status":
            result = build_status()
        elif args.command == "validate":
            result = validate_foundation()
        else:
            result = {"decision_summary": decision_summary()}
    except ValueError as error:
        parser.error(str(error))

    _emit(result, args.as_json)
    return 0 if args.command != "validate" or result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
