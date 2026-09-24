# JARVIS OS (v0.2.0)

A private, standalone, voice-first personal AI assistant for Farhan Ali,
running entirely on his own computer:

- **Real local intelligence** — Ollama (qwen3-8B) answers everything by
  default; no cloud, no API key, no cost. An optional bridge can use the
  locally installed Claude Code CLI for deep analysis, and the Claude API
  remains an optional paid upgrade.
- **Voice** — push-to-talk with auto-submit, spoken replies (selectable
  voice and speed), Esc interruption, and a guard that never reads
  secret-looking content aloud.
- **Memory with provenance** — categorized, searchable, editable; duplicates
  refused; sensitive content never stored silently.
- **Project understanding** — register any local folder; JARVIS inspects it
  read-only (secrets always skipped) and explains what it does, what changed,
  and what needs attention.
- **Mail & Calendar** — official Google OAuth, read-only first; every send,
  archive, delete, or event change requires an explicit single-use approval
  and lands in an audit trail.
- **Trading-bot monitoring** — reads a bot-written status report and explains
  it honestly; JARVIS cannot trade (no execution path exists).
- **Honesty everywhere** — every answer is attributed to the provider that
  produced it; disconnected services say so; nothing simulates success.

**Single-owner, local machine only.** It binds to 127.0.0.1 (with CSRF and
DNS-rebinding defenses) but has no authentication — do not host it on a
network. See [docs/SECURITY.md](docs/SECURITY.md) and
[docs/PRIVACY.md](docs/PRIVACY.md).

## Prerequisites

- Node.js **24 LTS** (`node --version` should print v24.x)
- npm 10+
- A Chromium-based browser (Chrome/Edge) for the full voice experience —
  speech recognition support varies by browser and may use a network
  recognition service; typed input always works everywhere.

## Installation

```sh
npm install
```

## Configuration

Copy `.env.example` to `.env` and adjust. Everything has a working default —
with no `.env` at all, the app runs in **mock mode** with the Demo Provider.

| Variable | Default | Meaning |
|---|---|---|
| `JARVIS_DATA_DIR` | `.data` | Where the SQLite database lives (gitignored). |
| `HOST` / `PORT` | `127.0.0.1` / `8787` | API server binding. Keep it local. |
| `MODEL_PROVIDER` | `mock` | `mock` (no key needed), `ollama` (local model), or `anthropic`. |
| `ANTHROPIC_API_KEY` | — | Server-side only. Required for `anthropic` mode. |
| `FAST_MODEL_NAME` | — | Claude model for fast responses (required for `anthropic`). |
| `DEEP_MODEL_NAME` | — | Claude model for deep reasoning (falls back to fast). |
| `MODEL_TIMEOUT_MS` | `45000` | Model request timeout (all providers). |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama API address. Loopback only. |
| `OLLAMA_MODEL` | — | Installed Ollama model (required for `ollama` mode). |
| `OLLAMA_NUM_CTX` | `4096` | Context window in tokens. |
| `OLLAMA_THINK` | `false` | Keep `false` so hidden reasoning is never shown or spoken. |

### Choosing a provider

- **Mock mode** (default): every model response comes from the clearly-labeled
  Demo Provider. The full experience — routing, activity feed, approvals,
  memory, voice — works end to end with zero configuration and zero cost.
- **Ollama mode** (real local model, no cloud, no API key): install
  [Ollama](https://ollama.com), pull a model (e.g.
  `ollama pull qwen3:8b-q4_K_M`), make sure Ollama is running, then set
  `MODEL_PROVIDER=ollama` and `OLLAMA_MODEL` in `.env`. The browser never
  talks to Ollama — requests go through the JARVIS server to the Ollama HTTP
  API on loopback (`/api/chat`), so prompts never leave this machine. The UI
  identifies responses truthfully as "Local Ollama (model)". If Ollama is not
  running or the model isn't installed, requests fail with an honest,
  actionable error — there is **no silent fallback to Demo responses**.
  Verified on an AMD Ryzen 7 3700X + Radeon RX 5700 (8 GB VRAM) with
  `qwen3:8b-q4_K_M` at a 4096-token context, running fully on GPU. Expect
  local-model answer quality below Claude; the Anthropic provider remains an
  optional upgrade.
- **Anthropic mode**: set `MODEL_PROVIDER=anthropic`, `ANTHROPIC_API_KEY`, and
  `FAST_MODEL_NAME` (plus optionally `DEEP_MODEL_NAME`). Missing configuration
  produces an honest error — the app never silently falls back to mock, and
  the UI never claims Claude is connected when it isn't. The API key stays on
  the server, is never logged, and never reaches the browser.

## Starting JARVIS (one step)

```sh
npm run jarvis        # or double-click / run: jarvis.cmd
```

The launcher checks Ollama (starting it when possible), verifies the
configured model is installed (printing the exact `ollama pull` command if
not), warms the model so the first reply is fast, builds on first run, starts
the server in production mode exactly once (no duplicates), and opens
http://127.0.0.1:8787 in your browser.

```sh
npm run jarvis:stop     # clean shutdown
npm run jarvis:status   # server / Ollama / model state
node scripts/launch.mjs restart --rebuild   # after pulling code changes
```

Set `OLLAMA_KEEP_ALIVE` (default `30m`) in `.env` to control how long the
model stays loaded between requests.

## Development

```sh
npm run dev
```

Starts the Fastify API (127.0.0.1:8787) and the Vite client
(http://127.0.0.1:5173, proxying `/api`). Open http://127.0.0.1:5173.

## Production build

```sh
npm run build   # builds the client and bundles the server into dist/
npm start       # serves the built client + API from http://127.0.0.1:8787
```

## Tests

```sh
npm run lint        # eslint
npm run typecheck   # tsc --noEmit (strict)
npm test            # vitest unit + integration (isolated temp data dirs)
npm run test:e2e    # builds, then Playwright (Chromium) against .data-e2e
```

Automated tests never call a paid external model, never require a running
Ollama (its HTTP API is mocked), and never touch the operational `.data`
directory.

## Backup and restore

Stop the server first.

```sh
npm run backup -- --output <directory>
npm run restore -- --input <directory> [--force]
```

Backups use SQLite's online backup API and include a manifest (app version,
schema version, creation time, table counts, checksum). Restore validates the
manifest and checksum, rejects unsupported schema versions, refuses to replace
an existing store without `--force`, and takes a pre-restore backup before
replacing anything.

## Voice and browser limitations

- **Push-to-talk only** — the microphone is never activated automatically.
  Hold the mic button (or focus it and hold Space/Enter) to talk.
- Speech recognition uses the browser's Web Speech API. In Chrome this is a
  network-backed service (not local) and is unavailable in some browsers —
  the UI feature-detects and reports this honestly; typing always works.
- Spoken responses use `speechSynthesis`; the speaking animation follows real
  start/boundary/end events (browsers expose no TTS audio stream, so no
  amplitude is faked). Auto-speak can be toggled in the status strip.
- Press **Esc** (or Stop) at any time to interrupt listening, thinking, or
  speaking.

## Security limitations (read before extending)

- Single owner, localhost, no authentication — decision records are a local
  event history, not a production audit trail.
- Mail is simulated: approving records `simulated_completed`; nothing is sent.
- Secrets live only in `.env` (gitignored). Never add credentials to the
  client or commit them.

## Documentation

- `docs/OWNER_GUIDE.md` — how to use everything, in plain language
- `docs/ARCHITECTURE.md` — components, contracts, boundaries (+ plain-English map)
- `docs/INTEGRATIONS.md` — Google setup, Claude CLI bridge, projects, trading
- `docs/PRIVACY.md` — where data lives, what leaves the machine, your controls
- `docs/SECURITY.md` — enforced boundaries and review results
- `docs/TROUBLESHOOTING.md` — fixes for common problems
- `docs/BACKUP_AND_RESTORE.md` — backup, restore, export, delete
- `docs/TRADING_MONITOR_INTERFACE.md` — how a future bot connects
- `docs/DEMO.md` — the three-minute demo script (mock mode)
- `docs/PROJECT_STATE.md` — build state, checkpoints, verification status
