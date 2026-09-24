# JARVIS Owner's Guide

Everything you need to run and use JARVIS, in plain language.

## Start and stop

| What | How |
|---|---|
| Start | `npm run jarvis` (or double-click `jarvis.cmd`) — checks Ollama, warms the model, starts the server once, opens the browser |
| Stop | `npm run jarvis:stop` |
| Status | `npm run jarvis:status` |
| After pulling new code | `node scripts/launch.mjs restart --rebuild` |

If Ollama or the model is missing, the launcher tells you the exact command
to fix it (e.g. `ollama pull qwen3:8b-q4_K_M`).

## Talking to JARVIS

- **Type** in the command bar, or **hold the mic button** (push-to-talk),
  speak, and release — the transcript submits automatically.
- **Esc** interrupts anything: listening, thinking, or speaking.
- **Auto-speak**, the **voice**, and the **speaking speed** live in
  Settings. Replies that look like they contain secrets are never read aloud.
- **Explanation depth** (status strip or Settings): `simple` for plain
  language, `normal` for everyday, `technical` for exact detail.

## Memory

Say "Remember that …" or use the Memory panel. JARVIS:
- classifies what you save (preference, task, decision, lesson, personal fact…),
- refuses duplicates and never silently stores anything that looks sensitive
  (passwords, card numbers…) — you must confirm deliberately,
- shows where and when each memory came from, and lets you search, edit, or
  forget (forgetting archives rather than destroys).

## Projects

Register any local folder in the Projects panel. JARVIS scans it read-only
(secrets and build output are always skipped), profiles it, and can then
explain it in chat: *"What is jarvis-os and what changed recently?"*
JARVIS never edits project files.

## Mail and Calendar

One-time Google setup: [INTEGRATIONS.md](INTEGRATIONS.md). Connecting starts
**read-only**; enabling send/modify is a separate button. Every send,
archive, delete, or calendar change shows an approval card first — nothing
touches your account without your explicit yes, and everything lands in the
Tasks panel audit trail.

## Trading bot

The Trading panel reads a status file your future bot writes
([TRADING_MONITOR_INTERFACE.md](TRADING_MONITOR_INTERFACE.md)). JARVIS
explains it honestly — and can never trade.

## Choosing the model

In `.env`:

| Setup | Meaning |
|---|---|
| `MODEL_PROVIDER=ollama` (default) | Free, fully local answers |
| `MODEL_PROVIDER=ollama` + `CLAUDE_CLI_ENABLED=true` | Local for everyday; your Claude Code login for deep analysis (asks approval before sending project content) |
| `MODEL_PROVIDER=claude_cli` | Everything via your Claude Code login |
| `MODEL_PROVIDER=mock` | Demo Provider (no model, clearly labeled) |
| `MODEL_PROVIDER=anthropic` | Claude API (needs a paid API key — optional) |

The status strip always tells you truthfully which provider is active, and
every reply is attributed to the provider that produced it.

## Backups

See [BACKUP_AND_RESTORE.md](BACKUP_AND_RESTORE.md). Short version:
stop JARVIS, `npm run backup -- --output <folder>`.
