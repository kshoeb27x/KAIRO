# Source Capability Closure

**Scope:** `11_ARCHIVE/Original_Repositories`  
**Closure date:** 2026-09-25

This review is at project and capability level. No complete upstream repository
was imported into active KAIRO. The original source archive was reviewed before being removed from the active
project. No archived repository is a runtime dependency.

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

The final disposition of every nested project is:

| Project | Disposition | Concrete reason |
| --- | --- | --- |
| `134ertel-JARVIS` | ADAPTED | Confirmation, action-history, and health-check patterns are covered by KAIRO security/audit/runtime contracts. |
| `agent-zero` | REFERENCE_ONLY | Docker/Linux desktop, plugin, and multi-agent surface is too broad and privileged for the Python core. |
| `amanimran786-jarvis-ai` | EXTERNAL_ONLY | AGPL/macOS/PyQt and optional mem0/STT stack are provider-specific. |
| `Ambidiosidad-Jarvis` | ADAPTED | Exact scoped-memory deduplication is now a KAIRO-owned memory behavior; Qdrant/Ollama/voice remain optional. |
| `anything-llm` | REFERENCE_ONLY | Complete document/RAG application overlaps KAIRO data and UI layers. |
| `AstinLinson-JARVIS` | REFERENCE_ONLY | Unlicensed desktop voice implementation with external audio/model dependencies. |
| `browser-use` | INTEGRATED | KAIRO now exposes a provider-neutral browser action contract without faking an external browser runtime. |
| `isair-Jarvis` | REFERENCE_ONLY | Custom license and privileged screen/browser/MCP automation prevent direct reuse. |
| `jmtitan-Jarvis` | EXTERNAL_ONLY | WSL2/GPU/vLLM/Whisper split deployment is optional infrastructure, not core KAIRO runtime. |
| `LibreChat` | ALREADY_COVERED | Provider/chat/tool UX overlaps the existing KAIRO API/UI and tool boundaries. |
| `luccientertainment-Jarvis` | ADAPTED | Calendar/Gmail/research patterns map to KAIRO tool and approval contracts; OAuth providers remain optional. |
| `Nitro70-ai-jarvis` | ALREADY_COVERED | Typed, narrowly scoped tools and deny-by-default actions match KAIRO tool/security contracts. |
| `open-interpreter` | REFERENCE_ONLY | Arbitrary code execution is a high-risk product-specific sandbox. |
| `open-webui` | ALREADY_COVERED | Full self-hosted UI and provider integrations duplicate KAIRO’s active UI/API boundary. |
| `OpenHands` | REFERENCE_ONLY | Broad agent control center and external integrations exceed a bounded KAIRO extraction. |
| `PersonalJarvis` | ADAPTED | MCP/agent/computer-use orchestration maps to existing KAIRO agents, tools, and sandbox provider contract. |
| `ScuffedPACE-Jarvis-os` | ADAPTED | Sandbox decisions now write KAIRO audit entries; approval and disconnected-provider behavior already exist. |
| `SpencerPros-jarvis` | OBSOLETE | Minimal prototype voice loop adds no unique capability to KAIRO. |
| `theinizializer-Jarvis` | UNSUITABLE | SSH, Discord, speaker verification, and multi-provider access create an excessive external attack surface. |

## Remaining source closure

| Source | Disposition | KAIRO destination | Implementation status | Reason and validation |
| --- | --- | --- | --- | --- |
| `MIRA` | REFERENCE_ONLY | `01_CORE`, `04_TOOLS`, `06_SECURITY`, `07_RUNTIME` | Requirements already represented; no AGPL Rust code imported. | Rust multi-channel/voice/backup product with tightly coupled infrastructure. README and Cargo architecture reviewed; existing core/tool/security/runtime tests cover the bounded KAIRO equivalents. |
| `OpenMind` | ADAPTED | `04_TOOLS`, `06_SECURITY` | Provider availability and fail-closed reporting now use KAIRO’s existing optional-provider contract. | Proprietary Electron/Python product; local model, voice, MCP, and permission concepts are external or already covered. Provider-health tests pass. |
| `memU` | INTEGRATED | `03_DATA/Memory` | SQLite scoped memory, recall limits, and duplicate suppression are KAIRO-native. | Apache-2.0 memory service depends on host adapters/cloud embeddings; only bounded memory semantics were adopted. Memory integration tests pass. |
| `OCT-Agent` | REFERENCE_ONLY | `02_AGENTS`, `03_DATA`, `07_RUNTIME` | Existing KAIRO agent/runtime/data contracts cover the useful boundaries. | Apache-2.0 but broad OpenClaw-compatible desktop/CLI platform with hybrid retrieval and parallel agents; no isolated improvement justified beyond current memory/runtime work. Existing agent/runtime tests pass. |
| `Open-Computer-Use` | ADAPTED | `04_TOOLS`, `06_SECURITY` | Provider-neutral browser contract plus approval-controlled sandbox boundary; no Docker executor imported. | FSL-1.1 sandbox/MCP product requires Docker, browser, and external services. Provider refusal, approval, audit, and health tests pass. |
| `VoltAgent` | ADAPTED | `07_RUNTIME`, `02_AGENTS` | Bounded retries, attempt accounting, and execution events are KAIRO-native. | MIT TypeScript framework is too broad to embed; retry/telemetry semantics fit existing runtime. Runtime tests pass. |
| `Awesome-Personal-AI` | REFERENCE_ONLY | `10_DOCUMENTATION` | Catalog used for capability discovery only; no executable source. | Curated list without implementation or runtime contract. No integration required. |

Remaining sources are closed with no `UNKNOWN`, `UNREVIEWED`, `UNDECIDED`, or
`PENDING` disposition.

## Mapped component disposition

The numbered KAIRO layers contain `COMPONENTS/MAP-*` directories from the
earlier mapping process. A current structural and import review found that
these are isolated one-file snapshots: 1,093 MAP directories across
`01_CORE`, `02_AGENTS`, `03_DATA`, `04_TOOLS`, `05_UI`, `06_SECURITY`,
`07_RUNTIME`, and `08_BUSINESS`. They include source excerpts, README files,
plans, examples, and configuration fragments in several languages.

No active Python, TypeScript, JavaScript, Rust, Go, Java, or C# source imports
a MAP component or references a `COMPONENTS/MAP-*` path. The production
implementations remain in the canonical layer directories and are the source
of truth. Therefore the current disposition is:

- **Active/integrated MAP components:** none evidenced.
- **Adapted MAP components:** none identifiable from repository evidence;
  similar names are not proof of adaptation.
- **Reference-only:** all inspected MAP snapshots, retained because unused
  source is not sufficient evidence that deletion is safe.
- **Duplicate/obsolete:** none proven by import, identity, or ownership
  evidence.
- **Unclear:** no operationally distinct component; individual snapshots
  remain untouched rather than being guessed at or removed.

This keeps the mapping material isolated without introducing duplicate
implementations into the canonical architecture.

## Final archive consolidation

The complete `11_ARCHIVE/Original_Repositories` tree was removed from the
active project after dependency checks passed:

- **Archive path:** `11_ARCHIVE/Original_Repositories`
- **Status:** removed from active KAIRO path
- **Rollback storage:** removed during final project cleanup
- **Preserved source size before cleanup:** 99,564 files / 4,854,277,313 bytes

## Closure result

Every major archive source was classified as integrated, already represented,
reference-only, externally dependent, unsuitable for direct integration, or
duplicate/overlapping. No unnecessary archive code was copied into active
KAIRO.

## Repos adaptations and validation

| Source project | Capability | KAIRO destination | Implementation/change | Validation |
| --- | --- | --- | --- | --- |
| `browser-use` | Provider-neutral browser actions | `04_TOOLS/Browser` | Added `BrowserRequest`/`BrowserProvider`; `BrowserTool` supports `navigate`, `click`, and `type` only through an explicitly configured provider. | Fake-provider contract test and refusal test for unconfigured automation |
| `Ambidiosidad-Jarvis` | Scoped memory deduplication | `03_DATA/Memory` | `MemoryStore.remember` suppresses exact duplicate content within the same scope while preserving the original record and metadata. | Focused memory integration test |
| `ScuffedPACE-Jarvis-os` | Approval decision auditability | `06_SECURITY/Sandbox` and `06_SECURITY/Audit` | `SandboxProvider` records denied and allowed operations through the existing `AuditLogger`; `SecurityManager` wires the shared logger into the provider. | Focused denied-operation audit test and full security suite |
| `134ertel-JARVIS` | Health/action-history safety pattern | `06_SECURITY`, `07_RUNTIME` | Reused existing KAIRO health, audit, task, and event contracts; no duplicate action-history subsystem was created. | Existing system/runtime integration tests |
| `luccientertainment-Jarvis` | External calendar/Gmail/research integrations | `04_TOOLS`, `06_SECURITY` | Kept as provider-dependent tool opportunities behind existing tool and approval boundaries; no fake OAuth implementation added. | Existing tool/security contract tests |
| `PersonalJarvis` | MCP/agent/computer-use orchestration | `02_AGENTS`, `04_TOOLS`, `06_SECURITY` | Existing KAIRO agent manager, MCP tool, computer-use tool, and sandbox provider already cover the safe canonical boundary. | Existing agent/tool/system integration tests |
