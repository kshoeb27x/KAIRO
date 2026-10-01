from __future__ import annotations

import sys
from pathlib import Path
from importlib import import_module


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


security_module = import_module(
    "06_SECURITY"
)

manager_module = import_module(
    "06_SECURITY.security_manager"
)

authority_module = import_module(
    "06_SECURITY.Authority.authority"
)

sandbox_module = import_module(
    "06_SECURITY.Sandbox.sandbox"
)

SecurityManager = (
    manager_module.SecurityManager
)

AuthorityLevel = (
    authority_module.AuthorityLevel
)

SandboxPolicy = (
    sandbox_module.SandboxPolicy
)


def test_security_health():

    security = SecurityManager()

    health = security.health()

    assert health["status"] == "ONLINE"
    assert health["identity"]["status"] == "ONLINE"
    assert health["authority"]["status"] == "ONLINE"
    assert health["permissions"]["status"] == "ONLINE"
    assert health["secrets"]["status"] == "ONLINE"
    assert health["audit"]["status"] == "ONLINE"


def test_identity():

    security = SecurityManager()

    identity = security.identity.create(
        "user-1",
        "Test User",
    )

    assert identity.identity_id == "user-1"
    assert identity.active is True

    assert (
        security.identity.get("user-1")
        is not None
    )


def test_authority():

    security = SecurityManager()

    security.identity.create(
        "operator-1",
        "Operator",
    )

    security.authority.assign(
        "operator-1",
        AuthorityLevel.OPERATOR,
    )

    assert security.authority.allows(
        "operator-1",
        AuthorityLevel.USER,
    )

    assert security.authority.allows(
        "operator-1",
        AuthorityLevel.OPERATOR,
    )

    assert not security.authority.allows(
        "operator-1",
        AuthorityLevel.SYSTEM,
    )


def test_permissions():

    security = SecurityManager()

    security.identity.create(
        "user-1",
        "User",
    )

    security.permissions.grant(
        "user-1",
        "data.read",
    )

    assert security.permissions.allows(
        "user-1",
        "data.read",
    )

    assert not security.permissions.allows(
        "user-1",
        "data.write",
    )


def test_authorization():

    security = SecurityManager()

    security.identity.create(
        "operator-1",
        "Operator",
    )

    security.authority.assign(
        "operator-1",
        AuthorityLevel.OPERATOR,
    )

    security.permissions.grant(
        "operator-1",
        "runtime.execute",
    )

    assert security.authorize(
        "operator-1",
        "runtime.execute",
        AuthorityLevel.OPERATOR,
    )

    assert not security.authorize(
        "operator-1",
        "runtime.admin",
        AuthorityLevel.OPERATOR,
    )


def test_inactive_identity_denied():

    security = SecurityManager()

    security.identity.create(
        "user-1",
        "User",
    )

    security.authority.assign(
        "user-1",
        AuthorityLevel.USER,
    )

    security.permissions.grant(
        "user-1",
        "data.read",
    )

    security.identity.deactivate(
        "user-1"
    )

    assert not security.authorize(
        "user-1",
        "data.read",
    )


def test_secret_metadata():

    security = SecurityManager()

    reference = security.secrets.register(
        "OPENAI_API_KEY",
        "ENVIRONMENT",
    )

    assert reference.name == (
        "OPENAI_API_KEY"
    )

    assert reference.provider == (
        "ENVIRONMENT"
    )

    assert (
        security.secrets.get(
            "OPENAI_API_KEY"
        )
        is not None
    )


def test_secret_store_does_not_store_values():

    security = SecurityManager()

    security.secrets.register(
        "TEST_SECRET"
    )

    references = (
        security.secrets.list_references()
    )

    assert references[0]["name"] == (
        "TEST_SECRET"
    )

    assert "value" not in references[0]


def test_sandbox():

    policy = SandboxPolicy()

    assert not policy.allows(
        "network"
    )

    assert not policy.allows(
        "shell"
    )

    open_policy = SandboxPolicy(
        allow_network=True,
        allow_filesystem_write=True,
    )

    assert open_policy.allows(
        "network"
    )

    assert open_policy.allows(
        "filesystem_write"
    )


def test_audit():

    security = SecurityManager()

    security.audit.record(
        "TEST",
        "user-1",
        "test",
        "ALLOWED",
    )

    entries = security.audit.recent()

    assert len(entries) == 1
    assert entries[0]["event"] == "TEST"


def test_authorization_audit():

    security = SecurityManager()

    security.identity.create(
        "user-1",
        "User",
    )

    security.authority.assign(
        "user-1",
        AuthorityLevel.USER,
    )

    security.permissions.grant(
        "user-1",
        "data.read",
    )

    security.authorize(
        "user-1",
        "data.read",
    )

    entries = security.audit.recent()

    assert len(entries) == 1
    assert entries[0]["status"] == "ALLOW"
