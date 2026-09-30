# KAIRO Current Architecture

**Verified:** 2026-09-30  
**Branch:** `master`  
**Validation:** `python -m src status`, `python -m src validate`, and `python -m pytest -q` all pass; pytest result: 76 passed.

## Architecture map

```text
KAIRO
├── Core
├── Agents
├── Runtime
├── Security
├── Authority
├── Data/Memory
├── Tools
├── Intelligence
├── UI
└── Infrastructure
```

| Component | State | Responsible implementation |
|---|---|---|
| Core | EXISTS | `src/kairo_system.py`, `src/core/kairo_core.py`, `src/integration.py` |
| Agents | EXISTS | `02_AGENTS/manager.py`, `02_AGENTS/execution.py`, `02_AGENTS/{Coding,Data,Research}` |
| Runtime | EXISTS | `07_RUNTIME/runtime_manager.py`, `07_RUNTIME/Execution`, `07_RUNTIME/Tasks`, `07_RUNTIME/Events`, `07_RUNTIME/Workflows`, `07_RUNTIME/Scheduler`, `07_RUNTIME/State` |
| Security | EXISTS | `06_SECURITY/security_manager.py`, `06_SECURITY/Audit`, `06_SECURITY/Sandbox`, `06_SECURITY/Secrets` |
| Authority | EXISTS | `06_SECURITY/Authority/authority.py`, `06_SECURITY/Identity/identity.py`, `06_SECURITY/Permissions/permissions.py` |
| Data/Memory | EXISTS | `03_DATA/Database`, `03_DATA/Knowledge`, `03_DATA/Vector`, `03_DATA/Memory`, `03_DATA/RAG`, `03_DATA/Data_Management` |
| Tools | EXISTS | `04_TOOLS/manager.py`, `04_TOOLS/registry.py`, `04_TOOLS/executor.py`, `04_TOOLS/{API,Automation,Browser,Computer_Use,MCP}` |
| Intelligence | MISSING | `09_INTELLIGENCE/` is absent; reasoning/planning/LLM support currently lives in `01_CORE/{Reasoning,Planning,LLM,AI}` |
| UI | EXISTS | `05_UI/Web`, `05_UI/Command_Center`, `05_UI/Dashboard`, `05_UI/Interfaces`, served by `src/api/server.py` |
| Infrastructure | MISSING | `10_INFRASTRUCTURE/` is absent; no separate deployment/container/monitoring layer was identified |

## Entry points

- `python -m src status`
- `python -m src validate`
- `python -m src.api.server`
- `src/kairo_system.py` (`KairoSystem`)
- `src/main.py` (foundation CLI)

## Composition

`KairoSystem` loads the numbered packages through `src/integration.py`, creates one shared `RuntimeManager`, passes it into `KairoCore`, and composes agents, data, security, and tools. The API server exposes status, tasks, events, chat, and static UI assets on localhost.

## State interpretation

- **EXISTS** means an implemented and exercised capability is present.
- **PARTIAL** means a capability exists only in a limited or provider-neutral form.
- **BROKEN** means a capability is expected but currently fails validation.
- **MISSING** means the requested layer or capability is not present as a canonical implementation.
- **UNKNOWN** means the evidence was insufficient; no component is currently classified as unknown.

