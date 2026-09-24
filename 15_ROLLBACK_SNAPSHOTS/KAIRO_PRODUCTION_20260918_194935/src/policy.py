"""Validated configuration and policy loading for the KAIRO foundation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, ValidationError


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class KairoConfig(BaseModel):
    """Runtime configuration sourced from an optional local .env file."""

    model_config = ConfigDict(frozen=True)

    environment: str = "development"
    log_level: str = "INFO"
    data_root: str = "./03_DATA"
    require_approval_for_critical: bool = True

    @classmethod
    def from_environment(cls, project_root: Path = PROJECT_ROOT) -> "KairoConfig":
        load_dotenv(project_root / ".env", override=False)
        values = {
            "environment": os.getenv("KAIRO_ENV", "development"),
            "log_level": os.getenv("KAIRO_LOG_LEVEL", "INFO").upper(),
            "data_root": os.getenv("KAIRO_DATA_ROOT", "./03_DATA"),
            "require_approval_for_critical": os.getenv(
                "KAIRO_REQUIRE_APPROVAL_FOR_CRITICAL", "true"
            ),
        }
        return cls.model_validate(values)

    def resolved_data_root(self, project_root: Path = PROJECT_ROOT) -> Path:
        path = Path(self.data_root)
        return path if path.is_absolute() else project_root / path


class ApprovalPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    critical_actions: bool = True
    production_deployments: bool = True
    financial_actions: bool = True
    credential_changes: bool = True
    destructive_operations: bool = True


class SandboxPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    enabled: bool = True
    network_default: str = "restricted"


class AuditPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    enabled: bool = True
    immutable_target_required: bool = True


class KairoPolicy(BaseModel):
    """The controls required before KAIRO performs a higher-risk action."""

    model_config = ConfigDict(frozen=True)

    approval: ApprovalPolicy = Field(default_factory=ApprovalPolicy)
    sandbox: SandboxPolicy = Field(default_factory=SandboxPolicy)
    audit: AuditPolicy = Field(default_factory=AuditPolicy)


def load_policy(policy_path: Path = PROJECT_ROOT / "config" / "policy.yaml") -> KairoPolicy:
    """Read and validate the policy document without executing any repository code."""

    try:
        raw: Any = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ValueError(f"Unable to read policy file: {policy_path}") from error
    except yaml.YAMLError as error:
        raise ValueError(f"Policy file is not valid YAML: {policy_path}") from error

    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ValueError("Policy file must contain a YAML mapping.")

    try:
        return KairoPolicy.model_validate(raw)
    except ValidationError as error:
        raise ValueError(f"Policy file failed validation: {error}") from error
