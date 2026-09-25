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

## Original repository integration policy

The `11_ARCHIVE/Original_Repositories` tree is a source archive, not a direct import target. KAIRO should map each archived repository to a KAIRO layer before any code is adapted. The current safe mapping is:

- `memU` -> `03_DATA` (`EXTRACT`): memory, knowledge, vector and RAG patterns
- `Open-Computer-Use` -> `04_TOOLS` (`ADAPT`): browser and computer-use automation
- `VoltAgent` -> `07_RUNTIME` (`ADAPT`): workflow and runtime orchestration
- `OCT-Agent` -> `02_AGENTS` (`ADAPT`): agent coordination workflow
- `OpenMind` -> `09_INTELLIGENCE` (`EXTRACT`): planning and reasoning loops
- `Awesome-Personal-AI` -> `05_UI` (`ADAPT`): assistant UX patterns
- `Repos` -> `11_ARCHIVE` (`KEEP`): extraction pool and reference archive

This preserves the original projects while allowing KAIRO to adopt only the components that fit the controlled architecture instead of copying entire repositories into the active codebase.

## Extracted capability adaptations

The active KAIRO implementation contains small, KAIRO-owned adaptations informed
by protected archive source. No upstream repository is imported as an active
package:

- `03_DATA/Memory` provides scoped SQLite-backed memory and text recall,
  informed by the memory, database, and retrieval boundaries reviewed in
  `11_ARCHIVE/Original_Repositories/memU`.
- `06_SECURITY/Sandbox/provider.py` provides an approval- and policy-controlled
  provider contract, informed by the isolation boundaries reviewed in
  `11_ARCHIVE/Original_Repositories/Open-Computer-Use`.
- `07_RUNTIME/Execution/executor.py` provides bounded retries and attempt
  telemetry through KAIRO events, informed by the execution persistence and
  observability patterns reviewed in
  `11_ARCHIVE/Original_Repositories/VoltAgent`.

These adaptations preserve KAIRO's existing component contracts and are tested
through the active KAIRO test suite. Provider-specific Docker, browser, cloud,
and model integrations remain optional and are not copied into the core.

## Verification

```powershell
.\.tools\python312\python.exe -m pytest -q
```

See `00_FOUNDATION/Architecture/MASTER_ARCHITECTURE.md`,
`10_DOCUMENTATION/Technical/REPOSITORY_MIGRATION.md`, and
`10_DOCUMENTATION/Technical/REPOSITORY_DECISIONS.md`.
