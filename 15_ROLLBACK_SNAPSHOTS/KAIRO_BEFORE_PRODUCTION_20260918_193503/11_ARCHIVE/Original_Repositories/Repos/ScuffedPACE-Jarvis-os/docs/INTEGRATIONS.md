# Integrations

All integrations are **owner-authorized, least-privilege, and honest about
their state**. When something is not connected, JARVIS says so and shows how
to connect it — it never simulates a connected service.

## Google (Gmail + Calendar)

Official OAuth 2.0 (desktop-app loopback flow with PKCE) and the official
REST APIs. No SDK, no third-party service, no password ever touches JARVIS.

### One-time setup (about 10 minutes)

1. Go to https://console.cloud.google.com and create (or pick) a project.
2. **APIs & Services → Library**: enable **Gmail API** and **Google Calendar API**.
3. **APIs & Services → OAuth consent screen**: External, add yourself as a
   test user (no verification needed for personal use).
4. **APIs & Services → Credentials → Create credentials → OAuth client ID →
   Desktop app**. Copy the client ID and client secret.
5. In `.env` set:
   ```
   GOOGLE_CLIENT_ID=...apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=...
   ```
6. Restart JARVIS (`npm run jarvis`), open **Mail** or **Calendar**, and
   click **Connect Google (read-only)**. Approve in the browser tab that
   opens, then press "Refresh connection state".

### Permission tiers (least privilege)

- **Read-only** (default connect): `gmail.readonly`, `calendar.readonly`,
  your email address. JARVIS can list, read, search, summarize, and extract —
  nothing else.
- **Actions** (separate explicit upgrade button): adds `gmail.send`,
  `gmail.modify`, `calendar.events`. Even then, **every** send, archive,
  delete, event creation/change/response first creates an approval card
  showing exactly what will happen; nothing executes without your explicit,
  single-use approval, and every outcome is recorded in the action audit
  trail (`GET /api/actions`).

### Privacy and safety boundaries

- Tokens are stored in `.data/google-tokens.json` (gitignored, local only)
  and are never included in any API response or log.
- **Disconnect** (button in either panel) revokes the grant at Google and
  deletes the local tokens.
- Email and calendar text is treated as **untrusted data**: it is converted
  to plain text, size-bounded, and wrapped with an explicit instruction that
  the model must never follow instructions found inside it (prompt-injection
  defense). An email can never command JARVIS.
- Email analysis (summaries, extraction, reply drafts) runs on your
  configured model provider — with Ollama that means the content never
  leaves this machine.

## Local Claude CLI (optional)

See `.env.example` — `CLAUDE_CLI_ENABLED=true` routes deep-reasoning
requests through your locally installed, already-logged-in Claude Code CLI.
No API key; your normal Claude limits apply. Sending registered-project
content through the CLI always requires an approval showing what will be
sent. Verify it works with: `claude --version` in a terminal.

## Trading bot (read-only)

See [TRADING_MONITOR_INTERFACE.md](TRADING_MONITOR_INTERFACE.md). JARVIS can
read and explain a bot's status report; it cannot trade — no execution path
exists.

## Registered projects (read-only)

The Projects panel registers local directories for inspection. Scans skip
secrets (`.env`, keys, credentials, databases), binaries, and build output;
all reads stay inside the registered directory; JARVIS never edits project
files.
