# Source Capability Closure

**Scope:** `11_ARCHIVE/Original_Repositories`  
**Closure date:** 2026-09-25

This review is at project and capability level. Original repositories remain
protected source material; no complete upstream repository is imported into
active KAIRO.

## Integrated into KAIRO

| Source | Capability | KAIRO adaptation |
| --- | --- | --- |
| `memU` | Scoped memory, durable storage, text recall | `03_DATA/Memory` SQLite-backed `MemoryStore`, integrated into `DataManager` and `KairoSystem` |
| `Open-Computer-Use` | Approval and isolation boundary | `06_SECURITY/Sandbox/provider.py` approval and policy contract; no FSL server code copied |
| `VoltAgent` | Bounded retries and execution telemetry | Existing `07_RUNTIME` executor now emits attempt/retry events and returns attempt counts |

## Already represented by KAIRO

- **Agent registration and execution:** `02_AGENTS`, including research, coding,
  and data agents.
- **Planning, reasoning, context, and orchestration:** `01_CORE`.
- **Knowledge, vector search, RAG, and database contracts:** `03_DATA`.
- **Tools, MCP boundary, browser/computer-use interfaces, and automation:**
  `04_TOOLS`.
- **Authority, permissions, audit, secrets, and deny-by-default sandbox policy:**
  `06_SECURITY`.
- **Tasks, workflows, scheduling, events, and execution:** `07_RUNTIME`.
- **API and web UI:** `src/api` and `05_UI/Web`.

## Reviewed but reference-only or unsuitable

| Source | Findings | Decision |
| --- | --- | --- |
| `MIRA` | Rust product with channels, proactive companion workflows, voice, MCP, skills, multi-user auth, encrypted secrets, backups, and provider routing. Its AGPL-3.0 license, Rust/React architecture, and external channel/provider infrastructure do not fit the active Python KAIRO core. | Keep protected as requirements/reference; rebuild individual capabilities only when a KAIRO requirement justifies them. |
| `OpenMind` | Python/Electron system with local/cloud model routing, Vosk/Whisper/Kokoro voice, ChromaDB memory, MCP plugins, recipes, sandboxing, and approval queues. It requires large optional model/audio/browser dependencies and a separate WebSocket/Electron process model. | Keep protected as local-first design reference; KAIRO already owns the core agent/tool/security contracts. |
| `OCT-Agent` | Workspace product containing CLI and desktop packages, with broad OpenClaw/UI/runtime coupling rather than a bounded KAIRO component. | Keep protected; no isolated non-privileged capability provided a better fit than existing KAIRO layers. |
| `Awesome-Personal-AI` | Curated catalog, not executable implementation. | Reference-only discovery material. |
| `Repos` nested projects | Independent applications including JARVIS assistants, Agent Zero, AnythingLLM, Browser Use, LibreChat, OpenHands, Open WebUI, Open Interpreter, and other unrelated products. Their capabilities overlap KAIRO or require separate databases, frontends, credentials, model runtimes, and licenses. | Classified individually at project level; retain as protected archive, not a dependency or bulk extraction source. |

## Nested project closure

The `Repos` collection was treated as separate projects rather than one
repository. The meaningful capability groups are:

- **Assistants and voice:** JARVIS variants, PersonalJarvis, Agent Zero.
  Overlap with KAIRO agents/tools/UI; external voice/model stacks are optional.
- **Developer agents:** OpenHands and Open Interpreter. Their execution
  environments are high-risk and product-specific; KAIRO uses its own
  approval-controlled tool and sandbox contracts.
- **Chat/UI products:** AnythingLLM, LibreChat, and Open WebUI. These are
  complete frontends/backends, not reusable KAIRO components.
- **Browser/computer use:** Browser Use and Agent Zero. Their browser drivers
  and model-specific orchestration remain optional providers.
- **Narrow or duplicated assistants:** remaining JARVIS projects do not add a
  unique, license-cleared capability that is missing from KAIRO.

## Closure result

Every major archive source is now classified as integrated, already
represented, reference-only, externally dependent, unsuitable for direct
integration, or duplicate/overlapping. No unnecessary archive code was copied
into active KAIRO, and no protected source was deleted.
