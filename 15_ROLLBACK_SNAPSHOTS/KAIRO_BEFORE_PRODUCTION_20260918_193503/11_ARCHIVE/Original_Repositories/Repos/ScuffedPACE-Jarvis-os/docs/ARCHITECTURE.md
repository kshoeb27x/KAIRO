# JARVIS OS — Architecture

Local, single-owner, desktop-first assistant. One npm project with clear
client / server / shared boundaries. Everyday intelligence is fully local
(Ollama); every external integration is owner-authorized, least-privilege,
and approval-gated.

## In plain English

Think of JARVIS as four layers:

1. **The face** (browser): the sphere, the conversation, voice in/out, and
   panels for Memory, Projects, Mail, Calendar, Tasks, Trading, Settings.
   It only ever *shows* what the server says actually happened.
2. **The brain-stem** (Fastify server): routes each request, gathers bounded
   context (personality, preferences, memories, project profiles), calls the
   chosen model provider, and streams honest events back.
3. **The hands** (actions): anything consequential becomes a written
   proposal — what, where, why, consequences — that only you can approve,
   once, before it executes. There is no other way for JARVIS to act.
4. **The memory** (SQLite in `.data`): conversations, memories with
   provenance, the action audit trail, settings, registered projects.

## Components and boundaries

```
Browser (React + Vite, 127.0.0.1:5173 in dev)
  ├─ app state machine (typed reducer; visual state derives from real events)
  ├─ neural sphere (Canvas 2D, driven by app state + measured mic level)
  ├─ voice pipeline (push-to-talk recognition, synthesis w/ voice+rate,
  │                  sensitive-content speech guard, Esc interruption)
  ├─ activity rail (renders NDJSON events from the server, in order)
  └─ panels: Memory · Projects · Mail · Calendar · Tasks · Trading · Settings
        │  /api same-origin (prod) or proxy (dev); foreign Host/Origin rejected
        ▼
Fastify server (127.0.0.1:8787)
  ├─ routes/         core API + Google routes; shared-contract validation
  ├─ orchestration/  route → context → (approval gate) → provider → events
  ├─ providers/model ModelProvider: Mock · Ollama (default) · Anthropic ·
  │                  ClaudeCli (opt-in) · HybridDeep (ollama + CLI deep tier)
  ├─ actions/        ActionRegistry: single-use approvals → executors
  │                  (simulated send · Claude CLI send · Gmail · Calendar);
  │                  trade_execute reserved with NO executor
  ├─ google/         OAuth (PKCE, loopback, scope tiers) · Gmail · Calendar ·
  │                  untrusted-content sanitizer
  ├─ projects/       read-only scanner (ignore/secret rules) · git info ·
  │                  deterministic profiles
  ├─ trading/        TradingMonitorAdapter: file report adapter, honest
  │                  assessment (no execution path)
  ├─ repositories/   prepared-statement access per table
  ├─ persistence/    migrations (v4) · seed · online backup
  └─ security/       path safety · error normalization · shared sensitive
                     detector; tokens/keys never leave the server
        │
        ▼
SQLite (.data/jarvis.db) + .data/google-tokens.json (both gitignored)
```

Shared contracts live in `src/shared` (Zod schemas + inferred types) and are
the single source of truth for the router result, activity-event envelopes,
entities, and every API request/response.

## State machine (client)

States: `booting, idle, listening, transcribing, routing, thinking, executing,
permission, speaking, error`.

Events include: BOOTSTRAP_SUCCEEDED/FAILED, START/STOP_LISTENING,
AUDIO_LEVEL_CHANGED, PARTIAL/FINAL_TRANSCRIPT, SUBMIT_REQUEST, ROUTE_SELECTED,
MODEL_STARTED, TOOL_STARTED, PERMISSION_REQUIRED, ACTION_APPROVED,
ACTION_CANCELLED, RESPONSE_RECEIVED, SPEECH_STARTED, SPEECH_BOUNDARY,
SPEECH_ENDED, INTERRUPT, FAILURE, RECOVER.

Invariants:
- One active assistant request at a time.
- INTERRUPT safely cancels fetch/recognition/speech and preserves transcript.
- A consequential action completes only via a server-recorded decision.
- Errors never silently become success.
- Visual state derives from application events, never from decorative timers.
- Indeterminate progress is allowed; fabricated percentages are not.

## Router contract

One Zod schema (`src/shared/schemas/route.ts`): schemaVersion, requestId,
intent (chat | project | tool | deep_reasoning | memory), specialist,
execution (direct | model | mock_tool | memory_write), risk, requiresApproval,
confidence (0–1), reasonCode (enumerated, user-safe — never chain-of-thought).

MVP router is deterministic and rule-based, behind a `Router` interface so a
model-based router can replace it later.

## Provider interfaces

`ModelProvider`: id/label, `status()` (configured, error — no secrets),
`complete(request)` with timeout + AbortSignal, normalized errors.
- `MockModelProvider` — always available, responses clearly labeled "Demo
  Provider". Used by all automated tests.
- `AnthropicModelProvider` — requires ANTHROPIC_API_KEY + configured model
  names; reports an honest configuration error when missing; never silently
  falls back to mock.
- `OllamaModelProvider` — real local model through the Ollama HTTP API
  (`POST /api/chat`, newline-delimited JSON stream assembled server-side; no
  CLI subprocess). Loopback addresses only (`127.0.0.1`/`localhost`); the
  browser never reaches Ollama directly, so prompts stay on this machine.
  Sends `think: false` and strips `<think>` blocks defensively so hidden
  reasoning is never displayed or spoken; pins `num_ctx` (default 4096).
  One local model serves both fast and deep tiers. Connection failure,
  missing model, timeout, cancellation, malformed responses, and server
  errors are normalized to safe messages — never a silent fallback to the
  Demo provider. Tools/approvals continue through the existing orchestrator
  unchanged (the MVP mail flow is routed before the model provider is
  invoked).

`ToolAdapter`: named tools with `simulated: true` labeling. `MockMailTool`
drafts an email deterministically and never sends anything.

## Persistence model

SQLite is the source of truth; localStorage holds nothing permanent.
Schema v1 tables: schema_migrations, projects, conversations, messages,
memories, pending_actions, activity_events, settings. UUID ids, UTC ISO
timestamps, foreign keys ON, prepared statements everywhere.

Migrations are ordered `.sql` files applied transactionally and recorded in
`schema_migrations`; startup re-runs are no-ops. Seeding uses a fixed project
id and never recreates archived records.

## Approval flow (mock mail)

1. Router selects the mail specialist → MockMailTool creates a draft.
2. Server stores a `pending_actions` row (status `pending`, TTL 10 minutes).
3. UI shows the draft + approval card; the payload shown is the stored one.
4. `POST /api/actions/:id/decision` records `simulated_completed` or
   `cancelled`. Single-use; expired or repeated decisions get 409/410-style
   conflict responses. Approval is never inferred from model text and the
   client cannot substitute a payload.
5. Nothing is ever externally sent. Decision history is a local event history,
   not a production audit trail (no authentication exists).

## Activity stream

`POST /api/assistant/stream` returns NDJSON. Each line is a validated
envelope: schemaVersion, requestId, eventId, eventType, occurredAt, safe
label, typed payload. Events are emitted only when the operation actually
happens, and safe copies are persisted to `activity_events`.

## Security boundaries

- Binds to 127.0.0.1. Single-owner local prototype; not hardened for network
  hosting, multi-user access, or production.
- API keys exist only in server-side env; never in `VITE_` vars, health or
  bootstrap responses, logs, or the repository.
- Request bodies are limited; user input capped at 8,000 characters.
- No filesystem-reading endpoint, no URL-fetching endpoint, no dynamic code
  execution. Production responses carry normalized errors, not stack traces.

## Backup and portability

`npm run backup -- --output <dir>` uses SQLite's online backup API and writes
a manifest (app version, schema version, created time, per-table counts,
sha256 checksum). `npm run restore -- --input <dir> [--force]` validates the
manifest and checksum, rejects unsupported schema versions, requires `--force`
to replace an existing store (taking a pre-restore backup first), and
validates record counts after restoring. Implementation:
`src/server/persistence/backup.ts`; CLI wrappers in `scripts/`.

## Action safety model (Section 8)

`pending_actions` is the unified proposal/approval/audit record. Lifecycle:
`pending → approved → completed | simulated_completed | failed`, or
`cancelled` / `expired`. Decisions are single-use and expiring; execution is
recorded exactly once at the database level; missing/failing executors are
recorded honestly. Executors registered today: simulated mail send, Claude
CLI context send, Gmail send/archive/delete, Calendar create/update/delete/
respond. `trade_execute` is reserved with no executor by design.

## Integration boundaries

- **Google**: official REST + OAuth (PKCE, loopback redirect, CSRF-checked
  state), read-only scope tier by default, action scopes as an explicit
  upgrade. Tokens in `.data`, revocable from the UI. All fetched content is
  sanitized, bounded, and wrapped as untrusted data.
- **Claude CLI**: allowlisted local subprocess, prompt via stdin, disabled by
  default; registered-project content requires per-request approval.
- **Projects**: read-only scans inside validated roots; secrets/binaries/
  build output never read; git via fixed-argument execFile.
- **Trading**: schema-validated report file; adapter interface for future
  transports; no execution path.

## Deferred features (later phases)

Semantic/vector memory retrieval, local Whisper speech-to-text (optional
module, owner-approved install), wake word, model-based router, multi-user
auth, encryption at rest, business dashboards, mobile parity.
