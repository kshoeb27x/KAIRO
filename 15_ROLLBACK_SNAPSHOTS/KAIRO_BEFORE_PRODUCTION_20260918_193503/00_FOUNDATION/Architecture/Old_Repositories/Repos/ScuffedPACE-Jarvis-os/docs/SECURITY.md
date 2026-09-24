# Security

Single-owner, local-first assistant. These are the enforced boundaries and
the results of the Section 12 review (2026-07-14).

## Network surface

- The server binds to `127.0.0.1` only. Nothing listens on the network.
- `/api` requests with a non-loopback `Host` header are rejected (DNS-rebinding
  defense); cross-origin browser requests are rejected unless they come from
  the app itself or the Vite dev server (CSRF defense).
- There is no authentication layer — anyone with an account on this Windows
  machine could use the API. Do not host JARVIS on a network without adding
  real auth first.

## Action safety (the core invariant)

Every externally visible action — sending email, archiving/deleting mail,
creating/changing/deleting/responding to calendar events, sending project
content to the Claude CLI — exists **only** as an approval-gated action:

1. A tool may *propose* an action (stored record with summary, target,
   reason, consequences, exact payload).
2. Only an explicit, single-use owner decision moves it forward; approvals
   expire (10 minutes) and apply to exactly that stored payload — the client
   cannot substitute another.
3. Execution is recorded exactly once (double execution is impossible at the
   database level); failures are recorded honestly.
4. Restricted categories (send / delete / money / trading / publish /
   security changes / terminal commands) have no autonomous path at all, and
   `trade_execute` has **no executor** — even an approved trade fails.

## Untrusted content

Email bodies, calendar text, project files, and trading reports are data,
never instructions:

- Email/calendar text is stripped to plain text, size-bounded, and wrapped
  with an explicit never-follow-instructions marker before any model sees it.
- Project profiles carry the same marker; scans skip `.env`, keys,
  credentials, databases, binaries, and oversized files entirely.
- Trading reports are schema-validated; malformed data is refused, not guessed.

## Subprocesses and files

- `git` runs with fixed argument lists, no shell, timeouts, bounded output.
- The Claude CLI command is allowlisted (`claude` or an absolute path to it);
  arguments are fixed literals and the prompt travels via stdin — data never
  passes through a shell.
- All project-inspection reads resolve inside the registered root (traversal
  is blocked and tested); symlinks are not followed; system directories
  cannot be registered.
- No API endpoint reads arbitrary files, fetches arbitrary URLs (the server
  talks only to configured loopback Ollama and Google's fixed endpoints), or
  evaluates code.

## Limits, timeouts, redaction

- Request bodies ≤ 64 KB; user input ≤ 8,000 chars; scans, CLI output, mail
  bodies, and trading reports are all size-capped; every outbound call has a
  timeout; every model request is cancellable (Esc).
- Secrets: the API key / tokens exist only server-side and never appear in
  API responses, the UI, or logs (asserted by tests). Fastify logging is
  disabled; the launcher log contains startup lines only. Model responses
  that look like they contain secrets are not spoken aloud.
- Errors sent to the browser are normalized; stack traces never leave the
  server in production.

## Audit

`GET /api/actions` (Tasks panel) is the action audit trail: proposed,
approved, cancelled, failed, expired — with actor label, timestamps, and
execution outcome. Activity events store only safe labels and compact
metadata, never full prompts or drafts.

## Dependency review

`npm audit` (runtime and dev): **0 vulnerabilities** as of 2026-07-14.
Dependencies are few and mainstream (fastify, better-sqlite3, react, zod).

## Known accepted risks

- No auth / encryption at rest: acceptable for a single-owner machine;
  revisit before multi-user or networked use.
- Chrome speech recognition is network-backed (documented in PRIVACY.md).
- The `.env` Google client secret is a desktop-app credential — Google
  treats these as non-confidential by design; the OAuth grant itself is
  protected by PKCE and the loopback redirect.
