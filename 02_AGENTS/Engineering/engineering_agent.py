from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Callable, Protocol, cast
from uuid import uuid4

from importlib import import_module

SandboxRequest = import_module(
    "06_SECURITY.Sandbox.provider"
).SandboxRequest


class ProposalBackend(Protocol):
    def generate(self, prompt: str, context: Any) -> Any:
        ...


ApprovalProvider = Callable[[Any], str | None]


@dataclass(frozen=True)
class EngineeringProposal:
    summary: str
    changes: tuple[dict[str, str], ...]
    completion_criteria: tuple[str, ...]
    dependencies: tuple[str, ...]
    implementation_tasks: tuple[str, ...]
    validation_requirements: tuple[str, ...]
    risks: tuple[str, ...] = ()


@dataclass
class EngineeringCycle:
    objective: str
    status: str
    started_at: str
    updated_at: str
    repository: str
    identity: str | None = None
    correlation_id: str | None = None
    checkpoint_status: str = "NOT_CREATED"
    project_map: dict[str, Any] = field(
        default_factory=dict[str, Any],
    )
    plan: dict[str, Any] = field(default_factory=dict[str, Any])
    files_changed: list[str] = field(default_factory=list[str])
    tests: dict[str, Any] = field(default_factory=dict[str, Any])
    compile: dict[str, Any] = field(default_factory=dict[str, Any])
    imports: dict[str, Any] = field(default_factory=dict[str, Any])
    errors: list[str] = field(default_factory=list[str])
    next_action: str = ""


class EngineeringAgent:
    """Approval-gated engineering loop for one explicitly selected repository."""

    name = "engineering"
    _EXCLUDED_DIRS = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        "node_modules",
        "dist",
        "build",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".kairo",
    }
    _EDITABLE_SUFFIXES = {
        ".py",
        ".pyi",
        ".toml",
        ".ini",
        ".cfg",
        ".md",
        ".txt",
        ".json",
        ".yaml",
        ".yml",
        ".js",
        ".ts",
        ".html",
        ".css",
    }
    _MAX_FILE_BYTES = 512_000
    _MAX_CYCLES = 3

    def __init__(
        self,
        security: Any | None = None,
        repository_root: str | Path | None = None,
        proposal_backend: ProposalBackend | None = None,
        approval_provider: ApprovalProvider | None = None,
        runtime: Any | None = None,
        command_runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    ) -> None:
        self.security = security
        self.repository_root = (
            Path(repository_root).resolve()
            if repository_root is not None
            else Path(__file__).resolve().parents[2]
        )
        self.proposal_backend = proposal_backend
        self.approval_provider = approval_provider
        self.runtime = runtime
        self.command_runner = command_runner or subprocess.run
        self._cycles: list[EngineeringCycle] = []
        self._rollback_snapshots: dict[str, dict[str, bytes | None]] = {}

    def execute(
        self,
        task: str,
        context: Any | None = None,
    ) -> dict[str, Any]:
        objective = task.strip()
        if not objective:
            raise ValueError("Engineering objective is required.")
        if self.security is None or context is None:
            self._audit_missing_context(objective)
            raise PermissionError(
                "Engineering requires a security manager and execution context."
            )
        cycle = self._new_cycle(objective)
        cycle.identity = context.caller_identity
        cycle.correlation_id = context.correlation_id
        self._cycles.append(cycle)
        task_id: int | None = None
        checkpoint_authorized = False
        try:
            self._authorize(
                context,
                "engineering.checkpoint",
                "engineering.checkpoint",
                str(self.repository_root),
            )
            checkpoint_authorized = True
            if not self.repository_root.is_dir():
                cycle.status = "BLOCKED_EXTERNAL"
                cycle.errors.append("Repository root is unavailable.")
                cycle.next_action = "Make the repository available and retry."
                self._record_checkpoint(cycle, cycle.status)
                return self._result(cycle)

            if self.runtime is not None:
                task_context = context.derive(
                    permission="runtime.task.create",
                    operation="engineering.task.create",
                    resource=objective,
                )
                runtime_task = self.runtime.create_task(
                    f"Engineering: {objective}",
                    task_context,
                )
                task_id = runtime_task["id"]
                if not isinstance(task_id, int):
                    raise RuntimeError(
                        "Runtime returned an invalid engineering task identifier."
                    )

            cycle.project_map = self._discover(context, cycle)
            if cycle.status == "BLOCKED_EXTERNAL":
                return self._result(cycle)

            if self.proposal_backend is None:
                cycle.status = "BLOCKED_EXTERNAL"
                cycle.next_action = "Configure an authorized engineering proposal backend."
                self._record_checkpoint(cycle, "BLOCKED_EXTERNAL")
                return self._result(cycle)

            self._authorize(
                context,
                "engineering.plan",
                "engineering.plan",
                str(self.repository_root),
            )
            cycle.status = "ANALYZING"
            cycle.tests = self._run_validation(
                context,
                cycle,
                self._test_command(cycle.project_map),
            )
            if cycle.tests["status"] in {
                "BLOCKED_EXTERNAL",
                "REQUIRES_APPROVAL",
                "DENIED",
                "NOT_DISCOVERED",
                "SKIPPED",
            }:
                cycle.status = cycle.tests["status"]
                cycle.next_action = cycle.tests["detail"]
                self._record_checkpoint(cycle, cycle.status)
                return self._result(cycle)

            proposal: EngineeringProposal | None = None
            for attempt in range(self._MAX_CYCLES):
                cycle.status = "PLANNING" if attempt == 0 else "REPAIRING"
                proposal = self._request_proposal(
                    context,
                    cycle,
                    attempt,
                )
                if proposal is None:
                    break
                checkpoint_id = cycle.plan.get("checkpoint_id")
                cycle.plan = {
                    "summary": proposal.summary,
                    "changes": [
                        dict(change)
                        for change in proposal.changes
                    ],
                    "completion_criteria": list(
                        proposal.completion_criteria
                    ),
                    "dependencies": list(proposal.dependencies),
                    "implementation_tasks": list(
                        proposal.implementation_tasks
                    ),
                    "validation_requirements": list(
                        proposal.validation_requirements
                    ),
                    "risks": list(proposal.risks),
                }
                if isinstance(checkpoint_id, str):
                    cycle.plan["checkpoint_id"] = checkpoint_id
                if not proposal.changes:
                    cycle.errors.append(
                        "Proposal contains no file changes; no implementation was performed."
                    )
                    cycle.status = "FAILED"
                    cycle.next_action = "Produce a concrete, testable implementation proposal."
                    break

                apply_result = self._apply_changes(
                    context,
                    cycle,
                    proposal,
                )
                if apply_result != "APPLIED":
                    cycle.status = apply_result
                    break

                cycle.status = "TESTING"
                cycle.tests = self._run_validation(
                    context,
                    cycle,
                    self._test_command(cycle.project_map),
                )
                if cycle.tests["status"] in {
                    "BLOCKED_EXTERNAL",
                    "REQUIRES_APPROVAL",
                    "DENIED",
                    "SKIPPED",
                }:
                    cycle.status = cycle.tests["status"]
                    cycle.next_action = cycle.tests["detail"]
                    break
                if cycle.tests["status"] != "PASS":
                    if cycle.tests["status"] == "NOT_DISCOVERED":
                        cycle.status = "NOT_DISCOVERED"
                        cycle.next_action = "A non-empty test suite is required to verify completion."
                        break
                    cycle.errors.append(cycle.tests["detail"])
                    if attempt + 1 < self._MAX_CYCLES:
                        cycle.project_map = self._discover(context, cycle)
                        continue
                    cycle.status = "FAILED"
                    cycle.next_action = "Repair failing tests and rerun validation."
                    break

                cycle.compile = self._run_validation(
                    context,
                    cycle,
                    "compileall",
                )
                if cycle.compile["status"] in {
                    "BLOCKED_EXTERNAL",
                    "REQUIRES_APPROVAL",
                    "DENIED",
                }:
                    cycle.status = cycle.compile["status"]
                    cycle.next_action = cycle.compile["detail"]
                    break
                if cycle.compile["status"] != "PASS":
                    cycle.errors.append(cycle.compile["detail"])
                    if attempt + 1 < self._MAX_CYCLES:
                        cycle.project_map = self._discover(context, cycle)
                        continue
                    cycle.status = "FAILED"
                    cycle.next_action = "Repair compilation errors and rerun validation."
                    break

                cycle.imports = self._run_validation(
                    context,
                    cycle,
                    "imports",
                )
                if cycle.imports["status"] in {
                    "BLOCKED_EXTERNAL",
                    "REQUIRES_APPROVAL",
                    "DENIED",
                    "NOT_DISCOVERED",
                }:
                    cycle.status = cycle.imports["status"]
                    cycle.next_action = cycle.imports["detail"]
                    break
                if cycle.imports["status"] != "PASS":
                    cycle.errors.append(cycle.imports["detail"])
                    if attempt + 1 < self._MAX_CYCLES:
                        cycle.project_map = self._discover(context, cycle)
                        continue
                    cycle.status = "FAILED"
                    cycle.next_action = "Repair import errors and rerun validation."
                    break

                cycle.status = "CHECKPOINTING"
                self._record_checkpoint(cycle, "VERIFIED")
                cycle.status = "COMPLETED"
                cycle.next_action = (
                    "Objective change passed discovered tests, Python compilation, "
                    "and KAIRO import checks."
                )
                break

            if cycle.status in {"PLANNING", "REPAIRING"}:
                cycle.status = "BLOCKED_EXTERNAL"
                cycle.next_action = "Engineering proposal backend did not produce a usable proposal."
            if cycle.status not in {"COMPLETED", "CHECKPOINTING"}:
                self._record_checkpoint(cycle, cycle.status)
            return self._result(cycle)
        except PermissionError as error:
            lowered_error = str(error).lower()
            cycle.status = (
                "REQUIRES_APPROVAL"
                if "approval" in lowered_error
                else "DENIED"
            )
            cycle.errors.append(str(error))
            cycle.next_action = "Grant the required capability or provide its scoped approval."
            if checkpoint_authorized:
                self._record_checkpoint(cycle, cycle.status)
            return self._result(cycle)
        except (OSError, subprocess.SubprocessError, ValueError) as error:
            cycle.status = "FAILED"
            cycle.errors.append(str(error))
            cycle.next_action = "Inspect the recorded error and retry after correcting its cause."
            self._record_checkpoint(cycle, cycle.status)
            return self._result(cycle)
        finally:
            runtime = self.runtime
            if task_id is not None and runtime is not None:
                task_context = context.derive(
                    permission="runtime.execute",
                    operation=(
                        "engineering.task.complete"
                        if cycle.status == "COMPLETED"
                        else "engineering.task.fail"
                    ),
                    resource=str(task_id),
                )
                if cycle.status == "COMPLETED":
                    runtime.complete_task(
                        task_id,
                        {
                            "status": cycle.status,
                            "files_changed": list(cycle.files_changed),
                        },
                        task_context,
                    )
                else:
                    runtime.fail_task(
                        task_id,
                        cycle.status,
                        task_context,
                    )

    def health(self) -> dict[str, Any]:
        current = self._cycles[-1] if self._cycles else None
        backend_configured = self.proposal_backend is not None
        backend_status: Any = None
        status_method = getattr(self.proposal_backend, "status", None)
        if callable(status_method):
            backend_status = status_method()
        if isinstance(backend_status, dict):
            backend_status_data = cast(dict[str, Any], backend_status)
            backend_configured = backend_status_data.get("status") not in {
                "OFFLINE",
                "UNAVAILABLE",
            }
        status = (
            current.status
            if current is not None
            else "READY"
            if backend_configured
            else "BLOCKED_EXTERNAL"
        )
        return {
            "status": status,
            "repository_available": self.repository_root.is_dir(),
            "proposal_backend_configured": backend_configured,
            "current_objective": current.objective if current else None,
            "current_action": current.next_action if current else None,
            "completed_cycles": sum(
                cycle.status == "COMPLETED" for cycle in self._cycles
            ),
            "failed_cycles": sum(
                cycle.status in {"FAILED", "DENIED"} for cycle in self._cycles
            ),
            "blocked_cycles": sum(
                cycle.status in {"BLOCKED_EXTERNAL", "REQUIRES_APPROVAL"}
                for cycle in self._cycles
            ),
            "last_result": self._result(current) if current else None,
        }

    def rollback(
        self,
        checkpoint_id: str,
        context: Any | None = None,
    ) -> dict[str, Any]:
        if self.security is None or context is None:
            self._audit_missing_context("rollback")
            raise PermissionError("Engineering rollback requires authorization.")
        self._authorize(
            context,
            "engineering.rollback",
            "engineering.rollback",
            checkpoint_id,
        )
        snapshot = self._rollback_snapshots.get(checkpoint_id)
        if snapshot is None:
            raise ValueError("Engineering checkpoint is unavailable.")
        restored: list[str] = []
        for relative_path, content in snapshot.items():
            target = self._safe_target(relative_path)

            def restore(target: Path = target, content: bytes | None = content) -> None:
                if content is None:
                    target.unlink(missing_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(content)

            self._sandbox_operation(
                context,
                "engineering.rollback",
                target,
                "filesystem_write",
                restore,
            )
            restored_content = target.read_bytes() if target.exists() else None
            if restored_content != content:
                raise OSError(
                    f"Rollback verification failed for {relative_path}."
                )
            restored.append(relative_path)
        checkpoint_cycle = next(
            (
                cycle
                for cycle in reversed(self._cycles)
                if cycle.plan.get("checkpoint_id") == checkpoint_id
            ),
            None,
        )
        if checkpoint_cycle is not None:
            checkpoint_cycle.checkpoint_status = "ROLLED_BACK"
            checkpoint_cycle.updated_at = datetime.now(timezone.utc).isoformat()
            self._record_checkpoint(checkpoint_cycle, "ROLLED_BACK")
        self.security.audit.record(
            "ENGINEERING_ROLLBACK",
            context.caller_identity,
            "engineering.rollback",
            "COMPLETED",
            {
                "checkpoint_id": checkpoint_id,
                "files_restored": restored,
                "correlation_id": context.correlation_id,
            },
        )
        return {
            "status": "COMPLETED",
            "checkpoint_id": checkpoint_id,
            "files_restored": restored,
        }

    def _new_cycle(self, objective: str) -> EngineeringCycle:
        now = datetime.now(timezone.utc).isoformat()
        return EngineeringCycle(
            objective,
            "DISCOVERING",
            now,
            now,
            str(self.repository_root),
        )

    def _discover(self, context: Any, cycle: EngineeringCycle) -> dict[str, Any]:
        self._authorize(
            context,
            "engineering.inspect",
            "engineering.inspect",
            str(self.repository_root),
        )
        file_groups: dict[str, list[str]] = {
            "packages": [],
            "tests": [],
            "configuration": [],
            "documentation": [],
            "entry_points": [],
            "dependencies": [],
            "runtime": [],
            "agent_registry": [],
            "tool_registry": [],
            "security": [],
            "api": [],
            "ui": [],
            "model_providers": [],
        }
        files: list[str] = []
        details: list[dict[str, str]] = []
        detail_bytes = 0
        for current, dirs, names in os.walk(self.repository_root):
            dirs[:] = sorted(
                name for name in dirs
                if name not in self._EXCLUDED_DIRS
                and not name.startswith(".")
            )
            current_path = Path(current)
            relative_dir = current_path.relative_to(self.repository_root)
            if "__init__.py" in names:
                file_groups["packages"].append(str(relative_dir))
            for name in sorted(names):
                path = current_path / name
                relative = path.relative_to(self.repository_root).as_posix()
                if path.is_symlink():
                    continue
                files.append(relative)
                suffix = path.suffix.lower()
                if (
                    len(details) < 100
                    and detail_bytes < 100_000
                    and suffix in self._EDITABLE_SUFFIXES
                    and not any(
                        marker in name.lower()
                        for marker in ("secret", "credential", "token", "password", ".env")
                    )
                    and path.stat().st_size <= 12_000
                ):
                    try:
                        content = path.read_text(encoding="utf-8")
                    except (OSError, UnicodeDecodeError):
                        content = ""
                    content = self._redact(content)
                    if detail_bytes + len(content) <= 100_000:
                        details.append(
                            {
                                "path": relative,
                                "sha256": hashlib.sha256(
                                    path.read_bytes()
                                ).hexdigest(),
                                "content": content,
                            }
                        )
                        detail_bytes += len(content)
                if relative.startswith("tests/") or relative.startswith("test"):
                    file_groups["tests"].append(relative)
                if suffix in {".toml", ".ini", ".cfg", ".yaml", ".yml"} or name in {
                    "pyproject.toml", "pytest.ini", "setup.cfg",
                    "requirements.txt", "requirements-dev.txt",
                }:
                    file_groups["configuration"].append(relative)
                if relative.startswith(("10_DOCUMENTATION/", "docs/")) or suffix == ".md":
                    file_groups["documentation"].append(relative)
                if name in {"__main__.py", "main.py", "server.py"}:
                    file_groups["entry_points"].append(relative)
                if name in {"requirements.txt", "requirements-dev.txt", "pyproject.toml"}:
                    file_groups["dependencies"].append(relative)
                if relative.startswith("07_RUNTIME/"):
                    file_groups["runtime"].append(relative)
                if relative.startswith("02_AGENTS/"):
                    file_groups["agent_registry"].append(relative)
                if relative.startswith("04_TOOLS/"):
                    file_groups["tool_registry"].append(relative)
                if relative.startswith("06_SECURITY/"):
                    file_groups["security"].append(relative)
                if relative.startswith("src/api/"):
                    file_groups["api"].append(relative)
                if relative.startswith("05_UI/"):
                    file_groups["ui"].append(relative)
                if (
                    "provider" in path.stem.lower()
                    or "model" in path.stem.lower()
                    or relative.startswith("01_CORE/AI/")
                ):
                    file_groups["model_providers"].append(relative)
        return {
            "root": str(self.repository_root),
            "file_count": len(files),
            "files": files,
            "groups": file_groups,
            "test_framework": (
                "pytest"
                if any(Path(name).name == "pytest.ini" for name in files)
                or any(name.startswith("tests/") for name in files)
                else "unittest"
                if any(name.startswith("test") and name.endswith(".py") for name in files)
                else "unidentified"
            ),
            "file_details": details,
            "discovered_at": datetime.now(timezone.utc).isoformat(),
        }

    def _request_proposal(
        self,
        context: Any,
        cycle: EngineeringCycle,
        attempt: int,
    ) -> EngineeringProposal | None:
        self._authorize(
            context,
            "engineering.plan",
            "engineering.plan",
            str(self.repository_root),
        )
        prompt = json.dumps(
            {
                "objective": cycle.objective,
                "project_map": cycle.project_map,
                "previous_plan": cycle.plan,
                "previous_failures": cycle.errors,
                "failure_output": self._redact(
                    str(cycle.tests.get("output", ""))
                    + "\n"
                    + str(cycle.compile.get("output", ""))
                )[-8000:],
                "validation": {
                    "tests": self._validation_summary(cycle.tests),
                    "compile": self._validation_summary(cycle.compile),
                    "imports": self._validation_summary(cycle.imports),
                },
                "attempt": attempt + 1,
                "constraints": [
                    "Return only one JSON object with summary, changes, completion_criteria, dependencies, implementation_tasks, validation_requirements, and risks.",
                    "Each change must contain path, expected_sha256, and content.",
                    "Use repository-relative paths and minimal changes.",
                    "Do not change tests to weaken assertions.",
                    "A completion claim is valid only after tests and compileall pass.",
                ],
            },
            sort_keys=True,
        )
        backend = self.proposal_backend
        if backend is None:
            cycle.status = "BLOCKED_EXTERNAL"
            cycle.next_action = "Configure an authorized engineering proposal backend."
            return None
        try:
            response = backend.generate(
                prompt,
                context,
            )
        except (OSError, RuntimeError, PermissionError) as error:
            message = str(error)
            lowered_error = message.lower()
            cycle.status = (
                "REQUIRES_APPROVAL"
                if "approval" in lowered_error
                else "DENIED"
                if "permission_not_granted" in lowered_error
                else "BLOCKED_EXTERNAL"
            )
            cycle.errors.append(message)
            cycle.next_action = (
                "Provide the exact scoped model.external approval."
                if cycle.status == "REQUIRES_APPROVAL"
                else "Configure an authorized engineering proposal backend."
            )
            return None
        if hasattr(response, "content"):
            response = response.content
        try:
            raw: Any = json.loads(response)
        except (TypeError, json.JSONDecodeError) as error:
            cycle.status = "FAILED"
            cycle.errors.append(f"Proposal is not valid JSON: {error}")
            cycle.next_action = "Return a JSON engineering proposal using the required schema."
            return None
        if not isinstance(raw, dict):
            cycle.status = "FAILED"
            cycle.errors.append("Proposal must be a JSON object.")
            return None
        # JSON object property names are strings by definition.
        proposal_data = cast(dict[str, Any], raw)
        changes_value: Any = proposal_data.get("changes")
        criteria_value: Any = proposal_data.get("completion_criteria")
        dependencies_value: Any = proposal_data.get("dependencies")
        implementation_tasks_value: Any = proposal_data.get(
            "implementation_tasks"
        )
        validation_requirements_value: Any = proposal_data.get(
            "validation_requirements"
        )
        summary: Any = proposal_data.get("summary")
        if (
            not isinstance(summary, str)
            or not summary.strip()
            or not isinstance(changes_value, list)
            or not isinstance(criteria_value, list)
            or not criteria_value
            or not isinstance(dependencies_value, list)
            or not isinstance(implementation_tasks_value, list)
            or not implementation_tasks_value
            or not isinstance(validation_requirements_value, list)
            or not validation_requirements_value
            or not all(
                isinstance(value, str) and value.strip()
                for value in (
                    cast(list[Any], criteria_value)
                    + cast(list[Any], dependencies_value)
                    + cast(list[Any], implementation_tasks_value)
                    + cast(list[Any], validation_requirements_value)
                )
            )
        ):
            cycle.status = "FAILED"
            cycle.errors.append("Proposal fields do not match the required schema.")
            return None
        changes: list[dict[str, str]] = []
        for change_value in cast(list[Any], changes_value):
            if not isinstance(change_value, dict):
                cycle.status = "FAILED"
                cycle.errors.append("Every proposed change requires path, expected_sha256, and content.")
                return None
            change = cast(dict[str, Any], change_value)
            path_value: Any = change.get("path")
            content_value: Any = change.get("content")
            digest_value: Any = change.get("expected_sha256")
            if not all(
                isinstance(value, str)
                for value in (path_value, content_value, digest_value)
            ):
                cycle.status = "FAILED"
                cycle.errors.append("Every proposed change requires path, expected_sha256, and content.")
                return None
            changes.append(
                {
                    "path": cast(str, path_value),
                    "content": cast(str, content_value),
                    "expected_sha256": cast(str, digest_value),
                }
            )
        risks_value: Any = proposal_data.get("risks", [])
        risks = (
            tuple(
                value
                for value in cast(list[Any], risks_value)
                if isinstance(value, str)
            )
            if isinstance(risks_value, list)
            else ()
        )
        return EngineeringProposal(
            summary=summary,
            changes=tuple(changes),
            completion_criteria=tuple(cast(list[str], criteria_value)),
            dependencies=tuple(cast(list[str], dependencies_value)),
            implementation_tasks=tuple(
                cast(list[str], implementation_tasks_value)
            ),
            validation_requirements=tuple(
                cast(list[str], validation_requirements_value)
            ),
            risks=risks,
        )

    def _apply_changes(
        self,
        context: Any,
        cycle: EngineeringCycle,
        proposal: EngineeringProposal,
    ) -> str:
        approved_contents: dict[str, bytes] = {}
        for change in proposal.changes:
            relative_path = change["path"]
            try:
                target = self._safe_target(relative_path)
                if (
                    relative_path.startswith("tests/")
                    or Path(relative_path).name.startswith("test_")
                ):
                    self._authorize(
                        context,
                        "engineering.modify_tests",
                        "engineering.modify_tests",
                        relative_path,
                    )
                else:
                    self._authorize(
                        context,
                        "engineering.modify",
                        "engineering.modify",
                        relative_path,
                    )
                if target.suffix.lower() not in self._EDITABLE_SUFFIXES:
                    raise ValueError("File type is not allow-listed for engineering edits.")
                current = target.read_bytes() if target.exists() else None
                if current is None and change["expected_sha256"] != "MISSING":
                    raise ValueError(
                        f"New target must use expected_sha256='MISSING': {relative_path}"
                    )
                if current is not None and change["expected_sha256"] == "MISSING":
                    raise ValueError(
                        f"Target already exists: {relative_path}"
                    )
                if current is not None and len(current) > self._MAX_FILE_BYTES:
                    raise ValueError("Target file exceeds the configured edit size.")
                digest = (
                    hashlib.sha256(current).hexdigest()
                    if current is not None
                    else "MISSING"
                )
                if digest != change["expected_sha256"]:
                    raise ValueError(f"Target changed since inspection: {relative_path}")
                new_content = change["content"].encode("utf-8")
                if len(new_content) > self._MAX_FILE_BYTES:
                    raise ValueError("Proposed file exceeds the configured edit size.")
                if target.name.lower() in {
                    ".env", "secrets.json", "credentials.json",
                }:
                    raise ValueError("Sensitive configuration files cannot be modified.")
                approved_contents[relative_path] = new_content
            except PermissionError as error:
                cycle.errors.append(str(error))
                cycle.next_action = (
                    f"Authorize engineering modification for {relative_path}."
                )
                return (
                    "REQUIRES_APPROVAL"
                    if "approval" in str(error).lower()
                    else "DENIED"
                )
            except (OSError, ValueError) as error:
                cycle.errors.append(str(error))
                cycle.next_action = "Produce a valid, bounded change against the current file hash."
                return "FAILED"

        checkpoint_id = cycle.plan.get("checkpoint_id")
        if not isinstance(checkpoint_id, str):
            checkpoint_id = uuid4().hex
            cycle.plan["checkpoint_id"] = checkpoint_id
        snapshot = self._rollback_snapshots.setdefault(checkpoint_id, {})
        for relative in approved_contents:
            if relative not in snapshot:
                target = self._safe_target(relative)
                snapshot[relative] = (
                    target.read_bytes()
                    if target.exists()
                    else None
                )
        for relative, content in approved_contents.items():
            target = self._safe_target(relative)

            def write(target: Path = target, content: bytes = content) -> None:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)

            try:
                self._sandbox_operation(
                    context,
                    "engineering.modify",
                    target,
                    "filesystem_write",
                    write,
                )
            except PermissionError as error:
                cycle.next_action = (
                    f"Approve scoped filesystem modification for {relative}."
                )
                if "approval" in str(error).lower():
                    return "REQUIRES_APPROVAL"
                cycle.errors.append(str(error))
                return "DENIED"
            cycle.files_changed.append(relative)
        return "APPLIED"

    def _run_validation(
        self,
        context: Any,
        cycle: EngineeringCycle,
        validation: str,
    ) -> dict[str, Any]:
        self._authorize(
            context,
            "engineering.test",
            "engineering.test",
            validation,
        )
        if validation == "pytest":
            command = [sys.executable, "-m", "pytest", "-q"]
        elif validation == "unittest":
            command = [sys.executable, "-m", "unittest", "discover", "-v"]
        elif validation == "compileall":
            command = [
                sys.executable,
                "-m",
                "compileall",
                "-q",
                str(self.repository_root),
            ]
        elif validation == "imports":
            modules = self._import_modules(cycle.project_map)
            if not modules:
                return {
                    "status": "NOT_DISCOVERED",
                    "validation": validation,
                    "detail": "No importable Python packages or modules were discovered.",
                }
            module_tuple = repr(tuple(modules))
            command = [
                sys.executable,
                "-c",
                (
                    "from importlib import import_module; "
                    f"modules = {module_tuple}; "
                    "[import_module(name) for name in modules]"
                ),
            ]
        else:
            return {
                "status": "ERROR",
                "detail": f"Unsupported validation: {validation}",
            }
        try:
            completed = self._sandbox_operation(
                context,
                f"engineering.validate.{validation}",
                self.repository_root,
                "process_execution",
                lambda: self.command_runner(
                    command,
                    cwd=self.repository_root,
                    capture_output=True,
                    text=True,
                    timeout=180,
                    check=False,
                ),
            )
        except PermissionError as error:
            message = str(error)
            lowered_error = message.lower()
            blocked_status = (
                "REQUIRES_APPROVAL"
                if "approval_required" in lowered_error
                or "requires approval" in lowered_error
                else "DENIED"
                if any(
                    marker in lowered_error
                    for marker in (
                        "permission_not_granted",
                        "emergency_stop",
                        "capability_disabled",
                    )
                )
                else "BLOCKED_EXTERNAL"
            )
            return {
                "status": blocked_status,
                "detail": message,
            }
        output = self._redact(
            (completed.stdout or "") + (completed.stderr or "")
        )
        if validation == "pytest":
            count = self._pytest_count(output)
            if count == 0:
                return {
                    "status": "NOT_DISCOVERED",
                    "tests_discovered": 0,
                    "exit_code": completed.returncode,
                    "detail": "Pytest discovered zero tests; zero tests cannot verify completion.",
                    "output": output[-8000:],
                }
        elif validation == "unittest":
            match = re.search(r"Ran\s+(\d+)\s+tests?", output)
            count = int(match.group(1)) if match else 0
            if count == 0:
                return {
                    "status": "NOT_DISCOVERED",
                    "tests_discovered": 0,
                    "exit_code": completed.returncode,
                    "detail": "Unittest discovered zero tests; zero tests cannot verify completion.",
                    "output": output[-8000:],
                }
        else:
            count = None
        passed = completed.returncode == 0
        if (
            passed
            and validation in {"pytest", "unittest"}
            and count is not None
        ):
            counts = (
                self._pytest_summary_counts(output)
                if validation == "pytest"
                else self._unittest_summary_counts(output, count)
            )
            if counts.get("tests_passed", 0) == 0:
                return {
                    "status": "SKIPPED",
                    "validation": validation,
                    "tests_discovered": count,
                    "exit_code": completed.returncode,
                    "detail": "Test discovery found cases, but no test passed; this cannot verify completion.",
                    "output": output[-8000:],
                    **counts,
                }
        result: dict[str, Any] = {
            "status": "PASS" if passed else "FAIL",
            "validation": validation,
            "tests_discovered": count,
            "exit_code": completed.returncode,
            "detail": (
                f"{validation} completed successfully."
                if passed
                else f"{validation} failed with exit code {completed.returncode}."
            ),
            "output": output[-8000:],
        }
        if validation == "pytest":
            result.update(self._pytest_summary_counts(output))
        elif validation == "unittest":
            result.update(self._unittest_summary_counts(output, count or 0))
        return result

    @staticmethod
    def _pytest_count(output: str) -> int:
        counts = EngineeringAgent._pytest_summary_counts(output)
        if counts:
            return sum(counts.values())
        collected = re.search(
            r"collected\s+(\d+)\s+items?",
            output,
            re.IGNORECASE,
        )
        return int(collected.group(1)) if collected else 0

    @staticmethod
    def _pytest_summary_counts(output: str) -> dict[str, int]:
        summary_lines = [
            line
            for line in output.splitlines()
            if re.search(r"\bin\s+\d+(?:\.\d+)?s\b", line)
            and re.search(
                r"\d+\s+(?:passed|failed|errors?|skipped|xfailed|xpassed)",
                line,
                re.IGNORECASE,
            )
        ]
        if not summary_lines:
            return {}
        summary = summary_lines[-1]
        result: dict[str, int] = {}
        for category, key in (
            ("passed", "tests_passed"),
            ("failed", "tests_failed"),
            ("errors?", "tests_errors"),
            ("skipped", "tests_skipped"),
            ("xfailed", "tests_xfailed"),
            ("xpassed", "tests_xpassed"),
        ):
            result[key] = sum(
                int(value)
                for value in re.findall(
                    rf"(\d+)\s+{category}",
                    summary,
                    re.IGNORECASE,
                )
            )
        return result

    @staticmethod
    def _unittest_summary_counts(output: str, count: int) -> dict[str, int]:
        summary_match = re.search(
            r"(?:FAILED|OK)\s*(?:\(([^)]*)\))?",
            output,
            re.IGNORECASE,
        )
        summary = summary_match.group(1) if summary_match else ""
        counts: dict[str, int] = {}
        for key in ("failures", "errors", "skipped"):
            match = re.search(rf"{key}=(\d+)", summary)
            counts[f"tests_{key}"] = int(match.group(1)) if match else 0
        counts["tests_passed"] = max(
            0,
            count
            - counts["tests_failures"]
            - counts["tests_errors"]
            - counts["tests_skipped"],
        )
        counts["tests_failed"] = counts.pop("tests_failures")
        return counts

    @staticmethod
    def _test_command(project_map: dict[str, Any]) -> str:
        framework = project_map.get("test_framework")
        return framework if framework in {"pytest", "unittest"} else "pytest"

    def _import_modules(self, project_map: dict[str, Any]) -> list[str]:
        modules = {
            package
            for package in project_map.get("groups", {}).get("packages", [])
            if "/" not in package and package != "tests"
        }
        modules.update(
            Path(path).stem
            for path in project_map.get("files", [])
            if "/" not in path
            and path.endswith(".py")
            and not Path(path).name.startswith("test_")
        )
        if (self.repository_root / "src" / "kairo_system.py").is_file():
            modules.add("src.kairo_system")
        return sorted(modules)

    def _sandbox_operation(
        self,
        context: Any,
        operation: str,
        resource: Path,
        capability: str,
        callback: Callable[[], Any],
    ) -> Any:
        if self.security is None:
            raise PermissionError("Security manager unavailable.")
        permission = (
            "filesystem.write"
            if capability == "filesystem_write"
            else "process.execute"
        )
        operation_context = context.derive(
            permission=permission,
            operation=f"sandbox.{operation}",
            resource=str(resource),
            requested_capability=capability,
        )
        if self.approval_provider is not None:
            approval_id = self.approval_provider(operation_context)
            if approval_id:
                operation_context = operation_context.derive(
                    approval_id=approval_id,
                )
        request = SandboxRequest(
            operation=operation,
            capability=capability,
        )
        return self.security.sandbox_provider.execute(
            request,
            callback,
            operation_context,
        )

    def _authorize(
        self,
        context: Any | None,
        permission: str,
        operation: str,
        resource: str,
    ) -> Any:
        if context is None or self.security is None:
            self._audit_missing_context(operation)
            raise PermissionError("Engineering operation requires authorization context.")
        operation_context = context.derive(
            permission=permission,
            operation=operation,
            resource=resource,
        )
        decision = self.security.authorize_context(
            operation_context,
            permission,
        )
        if not decision.allowed:
            self.security.audit_execution(
                operation_context,
                decision.decision,
                decision.reason,
            )
            raise PermissionError(
                f"Engineering operation denied: {decision.reason}"
            )
        return operation_context

    def _safe_target(self, relative_path: str) -> Path:
        candidate = Path(relative_path)
        if (
            candidate.is_absolute()
            or not relative_path.strip()
            or ".." in candidate.parts
        ):
            raise ValueError("Engineering paths must be repository-relative.")
        lexical_target = self.repository_root / candidate
        target = lexical_target.resolve()
        if not target.is_relative_to(self.repository_root):
            raise ValueError("Engineering path escapes the repository root.")
        if any(
            path.is_symlink()
            for path in (
                lexical_target,
                *lexical_target.parents,
            )
            if path != self.repository_root.parent
            and path != self.repository_root
        ):
            raise ValueError("Engineering changes through symbolic links are denied.")
        return target

    def _record_checkpoint(self, cycle: EngineeringCycle, result: str) -> None:
        if self.security is None:
            return
        cycle.updated_at = datetime.now(timezone.utc).isoformat()
        cycle.checkpoint_status = result
        details: dict[str, Any] = {
            "objective": cycle.objective,
            "status": result,
            "checkpoint_id": cycle.plan.get("checkpoint_id"),
            "repository": cycle.repository,
            "timestamp": cycle.updated_at,
            "files_changed": list(dict.fromkeys(cycle.files_changed)),
            "tests": self._validation_summary(cycle.tests),
            "compile": self._validation_summary(cycle.compile),
            "imports": self._validation_summary(cycle.imports),
            "unresolved_issues": [
                self._redact(message)[:500]
                for message in cycle.errors
            ],
            "next_action": cycle.next_action,
            "correlation_id": cycle.correlation_id,
        }
        self.security.audit.record(
            "ENGINEERING_CHECKPOINT",
            cycle.identity,
            "engineering.checkpoint",
            result,
            details,
        )

    def _blocked_result(self, objective: str, message: str) -> dict[str, Any]:
        cycle = self._new_cycle(objective)
        cycle.status = "BLOCKED_EXTERNAL"
        cycle.errors.append(message)
        cycle.next_action = "Make the repository available and retry."
        self._cycles.append(cycle)
        self._record_checkpoint(cycle, cycle.status)
        return self._result(cycle)

    def _audit_missing_context(self, operation: str) -> None:
        if self.security is not None:
            self.security.audit.record(
                "AUTHORIZATION",
                None,
                operation,
                "DENY",
                {"permission": "engineering.inspect", "reason": "MISSING_CONTEXT"},
            )

    @staticmethod
    def _validation_summary(result: dict[str, Any]) -> dict[str, Any]:
        return {
            key: result[key]
            for key in (
                "validation",
                "status",
                "tests_discovered",
                "tests_passed",
                "tests_failed",
                "tests_errors",
                "tests_skipped",
                "exit_code",
            )
            if key in result
        }

    @staticmethod
    def _redact(content: str) -> str:
        patterns = (
            r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*['\"]?[^'\"\s]+",
            r"\b(?:sk-[A-Za-z0-9_-]{16,}|AIza[A-Za-z0-9_-]{20,})\b",
        )
        for pattern in patterns:
            content = re.sub(pattern, "[REDACTED]", content)
        return content

    @staticmethod
    def _result(cycle: EngineeringCycle | None) -> dict[str, Any]:
        if cycle is None:
            return {"agent": "engineering", "status": "IDLE"}
        result: dict[str, Any] = {
            "objective": cycle.objective,
            "status": cycle.status,
            "started_at": cycle.started_at,
            "updated_at": cycle.updated_at,
            "repository": cycle.repository,
            "identity": cycle.identity,
            "correlation_id": cycle.correlation_id,
            "checkpoint_status": cycle.checkpoint_status,
            "project_map": dict(cycle.project_map),
            "plan": dict(cycle.plan),
            "files_changed": list(cycle.files_changed),
            "tests": dict(cycle.tests),
            "compile": dict(cycle.compile),
            "imports": dict(cycle.imports),
            "errors": list(cycle.errors),
            "next_action": cycle.next_action,
        }
        details = result["project_map"].get("file_details", [])
        result["project_map"]["file_details"] = [
            {
                "path": entry["path"],
                "sha256": entry["sha256"],
            }
            for entry in details
            if isinstance(entry, dict)
        ]
        for validation_key in ("tests", "compile", "imports"):
            validation = result[validation_key]
            if "output" in validation:
                validation["output"] = "[REDACTED FROM ENGINEERING RESULT]"
        changes = result["plan"].get("changes")
        if isinstance(changes, (list, tuple)):
            result["plan"]["changes"] = [
                {
                    "path": change.get("path"),
                    "content_bytes": len(
                        str(change.get("content", "")).encode("utf-8")
                    ),
                    "expected_sha256": change.get("expected_sha256"),
                }
                for change in cast(
                    list[dict[str, str]] | tuple[dict[str, str], ...],
                    changes,
                )
            ]
        return {
            "agent": "engineering",
            "task": cycle.objective,
            "status": cycle.status,
            "next_action": cycle.next_action,
            "result": result,
        }
