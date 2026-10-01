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

## Authenticated HTTP API

The HTTP server's API routes require a bearer token and explicit permissions.
Set `KAIRO_API_TOKEN`, `KAIRO_API_IDENTITY`, and a comma-separated
`KAIRO_API_PERMISSIONS` value in an untracked `.env` file or the process
environment. Do not put real tokens in `.env.example` or commit them. An empty
or missing token/permission configuration leaves privileged API calls denied.
The web console keeps the entered token only in the current page and sends it
as an `Authorization: Bearer` header.

Agent and tool routes require both their `api.*` route permission and the
operation permission used by the underlying manager. Task listing additionally
requires `runtime.task.read`; task creation requires `runtime.task.create`.
Memory API access is restricted to the authenticated identity's own memory
scope and requires both the API route permission and `data.read` or
`data.write`. `POST /api/runtime/emergency-stop` requires both
`api.runtime.control` and `runtime.emergency_stop`; there is intentionally no
ordinary API reset operation because reset requires administrator authority.

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

- `03_DATA/Database` and `03_DATA/Memory` provide SQLite-backed records,
  scoped memory, and text recall,
  informed by the memory, database, and retrieval boundaries reviewed in
  `11_ARCHIVE/Original_Repositories/memU`. The composed system stores database
  records, knowledge, vectors, and memory under `<KAIRO_DATA_ROOT>/Database`
  (defaulting to `03_DATA/Database`) and closes persistent stores when the API
  server shuts down. Vector search accepts caller-supplied embeddings; KAIRO
  does not currently provide an embedding model.
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
No model provider is configured by default: model health is reported as
`OFFLINE`, and general model generation raises an explicit unavailable error
instead of returning a fabricated response.
The built-in Coding, Research, and Data agent entry points likewise report
`UNAVAILABLE` until their respective execution backends are integrated; merely
dispatching a task is not reported as completed work.

## Engineering Agent

The Engineering Agent is registered with KAIRO's agent manager and can be
invoked through an explicit engineering objective (for example,
`implement ...` or `fix tests ...`). It discovers project structure, obtains a
structured proposal from its configured backend (including dependencies,
implementation tasks, affected-file changes, validation requirements, risks,
and completion criteria), validates repository-relative changes against file
hashes and an allowlist, runs the discovered test suite, compiles Python,
checks package imports, and retries test/compile failures for up to three
proposal cycles. Filesystem and process approvals are scoped to the repository
or concrete target path. Checkpoint summaries use the durable security audit
store; rollback snapshots are currently process-local.

This capability is deliberately **not unrestricted or ready for unattended
source modification by default**. KAIRO has no model provider or approval
broker configured, and sandbox process execution/filesystem writes default to
disabled. Configure a genuine model backend, grant the caller's
`engineering.*` permissions, enable only necessary sandbox capabilities, and
provide scoped approval handling before expecting a run to modify files.
Tests are never considered verified when discovery reports zero tests, and
blocked commands or missing integrations do not produce `COMPLETED`.
`GET /api/engineering` reports the current authorized agent health state.

## Verification

```powershell
.\.tools\python312\python.exe -m pytest -q
```

See `00_FOUNDATION/Architecture/MASTER_ARCHITECTURE.md`,
`10_DOCUMENTATION/Technical/REPOSITORY_MIGRATION.md`, and
`10_DOCUMENTATION/Technical/REPOSITORY_DECISIONS.md`.
The final archive capability closure is recorded in
`10_DOCUMENTATION/Technical/SOURCE_CAPABILITY_CLOSURE.md`.
