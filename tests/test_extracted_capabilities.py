from importlib import import_module

from src.kairo_system import KairoSystem


def test_memory_is_integrated_and_retrievable(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("KAIRO_DATA_ROOT", str(tmp_path))
    system = KairoSystem()

    try:
        record = system.memory.remember(
            "KAIRO uses policy-aware orchestration.",
            scope="project",
            metadata={"source": "test"},
        )

        matches = system.memory.recall("policy-aware", scope="project")

        assert matches[0].memory_id == record.memory_id
        assert matches[0].metadata == {"source": "test"}
        assert system.health()["components"]["data"]["memory"]["memories"] == 1
    finally:
        system.close()


def test_system_memory_persists_across_restart(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("KAIRO_DATA_ROOT", str(tmp_path))
    first_system = KairoSystem()
    first_system.memory.remember(
        "Persistent KAIRO project memory.",
        scope="project",
    )
    first_system.close()

    second_system = KairoSystem()
    try:
        matches = second_system.memory.recall(
            "Persistent KAIRO",
            scope="project",
        )
        assert len(matches) == 1
        assert matches[0].content == "Persistent KAIRO project memory."
        assert second_system.memory.health()["durable"] is True
    finally:
        second_system.close()


def test_system_database_persists_across_restart(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("KAIRO_DATA_ROOT", str(tmp_path))
    first_system = KairoSystem()
    first_system.database.insert(
        "settings",
        "theme",
        {"value": "dark"},
    )
    first_system.close()

    second_system = KairoSystem()
    try:
        assert second_system.database.get(
            "settings",
            "theme",
        ) == {"value": "dark"}
        assert second_system.database.health()["durable"] is True
    finally:
        second_system.close()


def test_system_knowledge_persists_across_restart(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("KAIRO_DATA_ROOT", str(tmp_path))
    first_system = KairoSystem()
    first_system.knowledge.add(
        "knowledge-1",
        "KAIRO persistence",
        "Knowledge survives system restart.",
        {"source": "test"},
    )
    first_system.close()

    second_system = KairoSystem()
    try:
        item = second_system.knowledge.get("knowledge-1")
        assert item is not None
        assert item.title == "KAIRO persistence"
        assert item.metadata == {"source": "test"}
        assert second_system.knowledge.health()["durable"] is True
    finally:
        second_system.close()


def test_system_vectors_persist_across_restart(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("KAIRO_DATA_ROOT", str(tmp_path))
    first_system = KairoSystem()
    first_system.vector.add(
        "vector-1",
        [1.0, 0.0],
        {"source": "test"},
    )
    first_system.close()

    second_system = KairoSystem()
    try:
        results = second_system.vector.search([1.0, 0.0])
        assert results[0]["vector_id"] == "vector-1"
        assert results[0]["metadata"] == {"source": "test"}
        assert second_system.vector.health()["durable"] is True
    finally:
        second_system.close()


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
    manager = security.SecurityManager()
    manager.sandbox_provider.policy = policy
    manager.identity.create("user-1", "User")
    authority = import_module(
        "06_SECURITY.Authority.authority"
    ).AuthorityLevel
    manager.authority.assign("user-1", authority.USER)
    manager.permissions.grant("user-1", "network.write")
    manager.identity.create("admin-1", "Admin")
    manager.authority.assign("admin-1", authority.ADMIN)
    manager.permissions.grant("admin-1", "security.approve")
    provider = manager.sandbox_provider
    context = manager.context(
        "user-1",
        "network.write",
        "sandbox.network-read",
        "network",
    )
    approval_id = manager.approve(context, "admin-1")
    context = context.derive(approval_id=approval_id)
    request = security.SandboxRequest(
        operation="network-read",
        capability="network",
        approved=True,
    )

    assert provider.execute(request, lambda: "allowed", context) == "allowed"
    assert provider.health()["operations"] == 1


def test_memory_deduplicates_exact_content_within_scope(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("KAIRO_DATA_ROOT", str(tmp_path))
    system = KairoSystem()

    try:
        first = system.memory.remember("same fact", scope="project")
        second = system.memory.remember("same fact", scope="project")

        assert second.memory_id == first.memory_id
        assert system.memory.health()["memories"] == 1
    finally:
        system.close()


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
