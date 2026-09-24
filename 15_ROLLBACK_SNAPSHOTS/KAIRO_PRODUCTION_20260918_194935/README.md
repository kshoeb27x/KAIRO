# KAIRO

KAIRO is a private AI/agent operating-system foundation. This repository delivers
the safe first stage: policy-aware, read-only discovery, audit, and repository
decision workflows. It does not execute candidate repositories or provide
unbounded autonomous actions.

## First principle

KAIRO is autonomous only within explicit permissions. Critical, irreversible,
financial, security, and production-wide actions require policy controls and/or
human approval.

## Foundation CLI

On a new Windows machine, create the project-local runtime first:

```powershell
.\scripts\bootstrap.ps1
```

Then run the CLI from the repository root:

```powershell
.\.tools\python312\python.exe -m src status
.\.tools\python312\python.exe -m src validate
.\.tools\python312\python.exe -m src decisions --json
```

`status` is non-mutating. `validate` checks the policy document, data root, and
JSON artifacts without running candidate code. `decisions` summarizes the
approved strategy for each candidate repository.

## Build order

1. Inventory existing repositories.
2. Audit dependencies, licenses, security, duplication, and functionality.
3. Assign `KEEP`, `EXTRACT`, `ADAPT`, `REWRITE`, or `ARCHIVE`.
4. Integrate only approved, bounded components.
5. Run builds and tests in an isolated sandbox.
6. Promote through explicit policy gates with rollback capability.

## Verification

```powershell
.\.tools\python312\python.exe -m pytest -q
```

See `00_FOUNDATION/Architecture/MASTER_ARCHITECTURE.md`,
`10_DOCUMENTATION/Technical/REPOSITORY_MIGRATION.md`, and
`10_DOCUMENTATION/Technical/REPOSITORY_DECISIONS.md`.
