# Privacy

## Where your data lives

Everything JARVIS stores is on this computer, in the gitignored `.data`
folder:

| Data | Location |
|---|---|
| Conversations, memories, actions, settings, activity | `.data/jarvis.db` (SQLite) |
| Google OAuth tokens | `.data/google-tokens.json` |
| Server log (startup lines only, no conversation content) | `.data/logs/jarvis-server.log` |
| Backups you make | the folder you choose (default `backups/`, gitignored) |

Nothing is committed to git; `.env` (configuration) and `.data` are ignored.
No telemetry, analytics, or crash reporting exists.

## What leaves this machine, and when

| Feature | What leaves | When |
|---|---|---|
| Ollama answers | Nothing — model runs on your GPU | — |
| Chrome voice input | Microphone audio to the browser's speech service | Only while you hold the mic button |
| Google Mail/Calendar | API calls to Google over HTTPS | Only after you connect via OAuth |
| Claude CLI bridge (off by default) | The prompt shown to you | Only if you enable it; project content additionally requires per-request approval |
| Claude API (optional) | Prompts to Anthropic | Only if you configure an API key |

Email and calendar content fetched from Google is processed by your
configured model provider — with Ollama that processing is fully local.

## Your controls

- **Disconnect Google** (Mail/Calendar/Settings panel): revokes the grant at
  Google and deletes the local tokens.
- **Forget a memory**: Memory panel (archived, excluded from all context).
- **Export / delete everything**: `.data` is a plain folder — back it up
  with `npm run backup`, or stop JARVIS and delete `.data` to erase all
  operational data (the seeded demo project is recreated on next start).
- **Sensitive content**: JARVIS never silently stores content that looks
  like credentials or financial identifiers, and never reads such content
  aloud.
