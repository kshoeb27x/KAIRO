# Repository Migration Process

## Phase A — Inventory
Record repository name, source, language, framework, entrypoints, dependencies, services, data access and license.

## Phase B — Audit
Check duplicate functionality, abandoned dependencies, secrets, unsafe permissions, network access, destructive operations, test coverage and build reproducibility.

## Phase C — Decision
Assign exactly one primary strategy:
- KEEP: retain an existing KAIRO-owned component with minimal changes.
- EXTRACT: copy a small, bounded, approved component into KAIRO with provenance,
  a dependency review, and new tests. This replaces the former `MERGE` label.
- ADAPT: use the repository as an upstream dependency or design reference behind
  a KAIRO-owned interface; do not copy its implementation wholesale.
- REWRITE: preserve the useful requirements, but build a clean KAIRO-owned
  implementation.
- ARCHIVE: retain the repository for evidence and reference only; do not run,
  depend on, or integrate it.

If a later security, license, or compatibility gate fails, record `REJECT` in
the risk register. A rejection supersedes the primary strategy and blocks
integration.

## Phase D — Sandbox
Run builds and tests in isolation. Never connect an untrusted repository directly to production credentials or production data.

## Phase E — Integration
Move only approved components into the relevant KAIRO layer. Pin dependencies and add tests.

## Phase F — Verification
Run unit, integration, security and regression tests. Record provenance and changes.

## Phase G — Promotion
Promote development -> staging -> production using explicit policy gates and rollback capability.
