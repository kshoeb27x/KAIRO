from importlib import import_module

from src.kairo_system import KairoSystem


def test_memory_is_integrated_and_retrievable() -> None:
    system = KairoSystem()

    record = system.memory.remember(
        "KAIRO uses policy-aware orchestration.",
        scope="project",
        metadata={"source": "test"},
    )

    matches = system.memory.recall("policy-aware", scope="project")

    assert matches[0].memory_id == record.memory_id
    assert matches[0].metadata == {"source": "test"}
    assert system.health()["components"]["data"]["memory"]["memories"] == 1


def test_sandbox_provider_requires_approval_and_policy() -> None:
    security = import_module("06_SECURITY")
    provider = security.SandboxProvider()
    request = security.SandboxRequest(
        operation="network-read",
        capability="network",
        approved=True,
    )

    try:
        provider.execute(request, lambda: "blocked")
    except PermissionError:
        pass
    else:
        raise AssertionError("Disabled sandbox capability was executed.")


def test_sandbox_provider_executes_approved_enabled_operation() -> None:
    security = import_module("06_SECURITY")
    policy = security.SandboxPolicy(allow_network=True)
    provider = security.SandboxProvider(policy)
    request = security.SandboxRequest(
        operation="network-read",
        capability="network",
        approved=True,
    )

    assert provider.execute(request, lambda: "allowed") == "allowed"
    assert provider.health()["operations"] == 1


def test_memory_deduplicates_exact_content_within_scope() -> None:
    system = KairoSystem()

    first = system.memory.remember("same fact", scope="project")
    second = system.memory.remember("same fact", scope="project")

    assert second.memory_id == first.memory_id
    assert system.memory.health()["memories"] == 1


def test_sandbox_provider_records_decisions_in_security_audit() -> None:
    system = KairoSystem()
    request = import_module("06_SECURITY").SandboxRequest(
        operation="network-read",
        capability="network",
        approved=False,
    )

    try:
        system.security.sandbox_provider.execute(request, lambda: "blocked")
    except PermissionError:
        pass
    else:
        raise AssertionError("Unapproved sandbox operation was executed.")

    entries = system.security.audit.recent()
    assert entries[-1]["event"] == "SANDBOX"
    assert entries[-1]["status"] == "DENIED"
