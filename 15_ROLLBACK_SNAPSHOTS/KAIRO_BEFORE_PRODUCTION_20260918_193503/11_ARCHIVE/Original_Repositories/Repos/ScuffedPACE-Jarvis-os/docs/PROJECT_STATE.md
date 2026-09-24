# JARVIS OS — Project State

- Application version: 0.2.0 · SQLite schema version: 4 · Branch: main
- Working tree expectation: clean after the Section 13 documentation commit.
- Product lineage: MVP brief v0.1 (July 12, 2026) → Checkpoint 7 local
  Ollama provider (July 14) → **Complete Standalone Assistant Build**
  (July 14, this state).

## Build history

| Stage | Commit |
|---|---|
| MVP checkpoints 1–6 (v0.1.0, schema 1) | 3e9d539 … b358ae5 |
| Checkpoint 7: local Ollama provider | db7d948 |
| Voice fixes: auto-submit, duplicate guard, resilient TTS (owner-verified by ear) | 65c59de |
| Section 1: one-step launcher, keep-alive, clean shutdown | 82215e5 |
| Section 2: identity layer + explanation depth | af4da4d |
| Section 3: memory v2 (categories, provenance, dedupe, sensitive gate; schema 2) | b1d2fe8 |
| Section 8: unified approval/audit system (schema 3) | 0b00ec8 |
| Section 4: read-only project inspection + health dashboard (schema 4) | a529d4a |
| Section 5: optional Claude CLI bridge (disabled by default) | e3567ef |
| Section 9: trading-monitor framework (execution impossible) | 364b226 |
| Sections 6–7: Gmail + Calendar OAuth, approval-gated actions | e9f8ac3 |
| Sections 10–11: voice preferences, sensitive-speech guard, dashboard panels | 76e50f3 |
| Section 12: CSRF/DNS-rebinding hardening, npm audit clean | cad3cb5 |
| Section 13: documentation suite | this commit |

## Verification state

Unattended verification run 2026-07-17: full gate green — lint clean,
typecheck clean (strict), **156 unit/integration tests**, production build,
**16 Playwright e2e** (1440×900 / 1024×768 / 390×844, console asserted
error-free), `npm audit` 0 vulnerabilities. New in that run:
`tests/e2e/voice.spec.ts` — browser-level voice pipeline with mocked speech
APIs (hold-to-talk transcription, exactly-one auto-submission, spoken reply
at the configured rate, Esc interruption of active speech, auto-speak off,
microphone-denial recovery, sensitive-speech guard, rate/preview settings).
Lifecycle re-verified live: duplicate-start guard, clean stop (port freed,
no orphan processes), restart, health/bootstrap/static client.

One notable non-defect from the run: the Demo Provider's fallback reply
mentions the phrase "Anthropic API key", which the sensitive-speech guard
correctly refuses to read aloud (with an honest notice). Expected behavior;
real Ollama replies are unaffected.

Live-verified against real services on the owner's machine:
- Ollama qwen3:8b-q4_K_M end-to-end (typed + voice, honest attribution,
  warm ≈1–3 s); launcher start/stop/status/duplicate-prevention cycle;
- project inspection of this repository (correct profile, health, commits)
  and chat explanation of it via the local model;
- all dashboard panels rendering honest connected/disconnected states with
  a clean browser console;
- operational data migrated v1→v4 in place (pre-migration backup at
  `backups/pre-schema-v2`).

Owner-verified by ear (2026-07-14): push-to-talk, transcription, single
auto-submit, spoken Local Ollama reply, Esc interruption.

## Pending owner verification (environment cannot exercise these)

1. **Google**: complete the one-time OAuth setup (docs/INTEGRATIONS.md),
   connect read-only, browse/summarize real mail and calendar; optionally
   enable actions and approve a real send/event.
2. **Claude CLI bridge**: `claude --version` in a terminal, set
   `CLAUDE_CLI_ENABLED=true`, ask for a deep analysis, approve the context
   card. (The CLI was not on this session's PATH.)
3. **Voice preferences by ear**: pick a voice and rate in Settings, confirm
   the preview and spoken replies.

## Known limitations

- Local model quality (qwen3-8B) is below Claude for hard reasoning; the
  deterministic keyword router and keyword memory relevance remain by design
  (both behind interfaces).
- No authentication / encryption at rest — single-owner machine only.
- Chrome speech recognition is network-backed; local Whisper is a designed,
  not-yet-installed optional module (requires owner approval; ~0.5–1.5 GB).
- Files and Research nav areas remain honestly Planned.
- Trading execution is deliberately impossible until the owner builds and
  registers an executor.

## Continuation point

The standalone-assistant build (Sections 1–14) is complete pending the three
owner verifications above. Natural next steps, only when the owner asks:
local Whisper module, semantic memory retrieval, model-based router,
a real trading-bot adapter, wake word (with explicit privacy consent).
