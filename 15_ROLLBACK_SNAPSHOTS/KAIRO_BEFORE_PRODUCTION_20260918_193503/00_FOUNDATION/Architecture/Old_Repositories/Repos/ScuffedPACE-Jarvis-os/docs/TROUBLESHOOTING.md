# Troubleshooting

## JARVIS won't start

- Run `npm run jarvis:status`. It reports server / Ollama / model state.
- **"Ollama is not running"**: start the Ollama app from the Start Menu (or
  `ollama serve` in a terminal), then `npm run jarvis` again.
- **"model … is not installed"**: run the exact `ollama pull …` command the
  launcher printed.
- **"A JARVIS process exists but is not answering"**: `npm run jarvis:stop`,
  then start again.
- **Build problems after an update**: `node scripts/launch.mjs restart --rebuild`.
- Server log: `.data/logs/jarvis-server.log`.

## Replies are slow

The first reply after ~30 idle minutes reloads the model (~15–25 s on this
hardware). The launcher warms the model at startup; raise
`OLLAMA_KEEP_ALIVE` (e.g. `2h`) in `.env` to keep it loaded longer.

## Replies fail with a provider error

The message says exactly what's wrong (Ollama unreachable, model missing,
timeout…). JARVIS never silently switches provider — fix the cause or change
`MODEL_PROVIDER` yourself. `mock` mode always works for testing the app.

## Voice

- **No transcription**: Chrome/Edge only; recognition needs internet
  (network-backed). Typing always works.
- **No spoken reply**: check Auto-speak in Settings; try another voice
  ("network" voices need internet). If speech can't start, JARVIS shows an
  honest notice instead of staying silent.
- **Esc** always stops listening/speaking and returns to READY.

## Google

- **"Google is not configured"**: follow docs/INTEGRATIONS.md (client ID +
  secret in `.env`, restart).
- **"connection may lack the needed permission tier"**: you connected
  read-only; click "Enable actions" for send/modify features.
- **Session expired**: click Connect again (tokens refresh automatically;
  a revoked grant needs a fresh connect).
- Connected the wrong account? Disconnect (revokes + deletes tokens) and
  connect again.

## Claude CLI bridge

- Verify the CLI works in your own terminal first: `claude --version`, then
  `claude -p "say hi"`.
- If JARVIS reports it missing, set `CLAUDE_CLI_COMMAND` in `.env` to the
  full path (find it with `where claude` in cmd).

## Approvals

- Approval cards expire after 10 minutes — propose the action again.
- A **failed** action shows why in the Tasks panel; nothing was done unless
  the record says completed.

## Something looks wrong with the data

Stop JARVIS and restore a backup: docs/BACKUP_AND_RESTORE.md.
