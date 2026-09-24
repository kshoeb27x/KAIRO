import { afterEach, describe, expect, it } from 'vitest';
import { MAX_INPUT_LENGTH, SCHEMA_VERSION } from '../../src/shared/constants';
import { activityEventSchema } from '../../src/shared/schemas/activity';
import { bootstrapResponseSchema, healthResponseSchema } from '../../src/shared/contracts/api';
import { createTestApp, parseNdjson, type TestApp } from '../helpers/testApp';

let ctx: TestApp | null = null;
afterEach(async () => {
  await ctx?.close();
  ctx = null;
});

describe('local-API request hardening', () => {
  it('rejects foreign Host headers (DNS-rebinding defense)', async () => {
    ctx = createTestApp();
    const res = await ctx.app.inject({
      method: 'GET',
      url: '/api/health',
      headers: { host: 'evil.example.com' },
    });
    expect(res.statusCode).toBe(403);
    expect(res.json().error.code).toBe('forbidden_host');
  });

  it('rejects cross-origin browser requests (CSRF defense)', async () => {
    ctx = createTestApp();
    const res = await ctx.app.inject({
      method: 'POST',
      url: '/api/settings',
      headers: { host: `127.0.0.1:${8787}`, origin: 'https://evil.example.com' },
      payload: { autoSpeak: false },
    });
    expect(res.statusCode).toBe(403);
    expect(res.json().error.code).toBe('forbidden_origin');
  });

  it('accepts same-origin local requests', async () => {
    ctx = createTestApp();
    const res = await ctx.app.inject({
      method: 'GET',
      url: '/api/health',
      headers: { host: '127.0.0.1:8787', origin: 'http://127.0.0.1:8787' },
    });
    expect(res.statusCode).toBe(200);
  });
});

describe('health and bootstrap', () => {
  it('health matches the shared contract', async () => {
    ctx = createTestApp();
    const res = await ctx.app.inject({ method: 'GET', url: '/api/health' });
    expect(res.statusCode).toBe(200);
    const parsed = healthResponseSchema.parse(res.json());
    expect(parsed.schemaVersion).toBe(SCHEMA_VERSION);
  });

  it('bootstrap matches the contract, reports honest provider status, and leaks no secrets', async () => {
    ctx = createTestApp({
      modelProvider: 'anthropic',
      anthropicApiKey: 'sk-ant-super-secret',
      fastModelName: 'my-fast-model',
    });
    const res = await ctx.app.inject({ method: 'GET', url: '/api/bootstrap' });
    const body = bootstrapResponseSchema.parse(res.json());
    expect(body.provider.mode).toBe('anthropic');
    expect(body.activeProject?.name).toBe('JARVIS OS');
    expect(res.body).not.toContain('sk-ant-super-secret');
    expect(res.body).not.toContain('dataDir');
  });

  it('mock mode reports Demo Provider, never claiming Claude is connected', async () => {
    ctx = createTestApp();
    const res = await ctx.app.inject({ method: 'GET', url: '/api/bootstrap' });
    const body = bootstrapResponseSchema.parse(res.json());
    expect(body.provider.mode).toBe('mock');
    expect(body.provider.label).toContain('Demo');
  });
});

describe('assistant stream', () => {
  it('rejects empty and oversized input', async () => {
    ctx = createTestApp();
    const empty = await ctx.app.inject({
      method: 'POST',
      url: '/api/assistant/stream',
      payload: { input: '   ' },
    });
    expect(empty.statusCode).toBe(400);

    const oversized = await ctx.app.inject({
      method: 'POST',
      url: '/api/assistant/stream',
      payload: { input: 'x'.repeat(MAX_INPUT_LENGTH + 1) },
    });
    expect(oversized.statusCode).toBe(400);
  });

  it('streams ordered, schema-valid NDJSON events for a chat request', async () => {
    ctx = createTestApp();
    const res = await ctx.app.inject({
      method: 'POST',
      url: '/api/assistant/stream',
      payload: { input: 'Good evening, how are you?' },
    });
    expect(res.statusCode).toBe(200);
    expect(res.headers['content-type']).toContain('application/x-ndjson');
    const events = parseNdjson(res.body).map((e) => activityEventSchema.parse(e));
    const types = events.map((e) => e.eventType);
    expect(types).toEqual([
      'request.accepted',
      'route.selected',
      'memory.loaded',
      'model.started',
      'response.completed',
    ]);
    // Chronologically ordered
    const times = events.map((e) => e.occurredAt);
    expect([...times].sort()).toEqual(times);
    // Mock provider is honestly labeled
    const modelStarted = events.find((e) => e.eventType === 'model.started');
    expect(modelStarted?.payload).toMatchObject({ simulated: true });
  });

  it('runs the mail flow: tool events, pending action, permission required', async () => {
    ctx = createTestApp();
    const res = await ctx.app.inject({
      method: 'POST',
      url: '/api/assistant/stream',
      payload: {
        input: 'Draft an email telling my collaborator the prototype will be ready tomorrow.',
      },
    });
    const events = parseNdjson(res.body).map((e) => activityEventSchema.parse(e));
    const types = events.map((e) => e.eventType);
    expect(types).toContain('tool.started');
    expect(types).toContain('tool.completed');
    expect(types).toContain('permission.required');
    const permission = events.find((e) => e.eventType === 'permission.required');
    if (permission?.eventType !== 'permission.required') throw new Error('missing permission');
    expect(ctx.repos.pendingActions.findById(permission.payload.actionId)?.status).toBe('pending');
  });

  it('memory requests persist only after success and emit memory.saved', async () => {
    ctx = createTestApp();
    const res = await ctx.app.inject({
      method: 'POST',
      url: '/api/assistant/stream',
      payload: { input: 'Remember that I prefer approval before any external action.' },
    });
    const events = parseNdjson(res.body).map((e) => activityEventSchema.parse(e));
    expect(events.map((e) => e.eventType)).toContain('memory.saved');
    const memories = ctx.repos.memories.listActive();
    expect(memories).toHaveLength(1);
    expect(memories[0]?.kind).toBe('preference');
  });

  it('anthropic mode without a key emits an honest request.failed event, not a mock fallback', async () => {
    ctx = createTestApp({ modelProvider: 'anthropic', anthropicApiKey: null });
    const res = await ctx.app.inject({
      method: 'POST',
      url: '/api/assistant/stream',
      payload: { input: 'Hello there' },
    });
    const events = parseNdjson(res.body).map((e) => activityEventSchema.parse(e));
    const failed = events.find((e) => e.eventType === 'request.failed');
    expect(failed).toBeDefined();
    if (failed?.eventType === 'request.failed') {
      expect(failed.payload.errorCode).toBe('not_configured');
    }
    expect(events.map((e) => e.eventType)).not.toContain('response.completed');
  });
});

describe('pending action decisions', () => {
  async function createPendingAction(app: TestApp): Promise<string> {
    const res = await app.app.inject({
      method: 'POST',
      url: '/api/assistant/stream',
      payload: { input: 'Draft an email to my collaborator saying hello' },
    });
    const events = parseNdjson(res.body).map((e) => activityEventSchema.parse(e));
    const permission = events.find((e) => e.eventType === 'permission.required');
    if (permission?.eventType !== 'permission.required') throw new Error('no permission event');
    return permission.payload.actionId;
  }

  it('approve records simulated_completed exactly once; duplicates conflict', async () => {
    ctx = createTestApp();
    const actionId = await createPendingAction(ctx);

    const approve = await ctx.app.inject({
      method: 'POST',
      url: `/api/actions/${actionId}/decision`,
      payload: { decision: 'approve' },
    });
    expect(approve.statusCode).toBe(200);
    expect(approve.json().action.status).toBe('simulated_completed');
    expect(approve.json().action.decidedBy).toBe('local-owner');

    const duplicate = await ctx.app.inject({
      method: 'POST',
      url: `/api/actions/${actionId}/decision`,
      payload: { decision: 'approve' },
    });
    expect(duplicate.statusCode).toBe(409);

    const conflicting = await ctx.app.inject({
      method: 'POST',
      url: `/api/actions/${actionId}/decision`,
      payload: { decision: 'cancel' },
    });
    expect(conflicting.statusCode).toBe(409);
  });

  it('cancel records cancelled', async () => {
    ctx = createTestApp();
    const actionId = await createPendingAction(ctx);
    const cancel = await ctx.app.inject({
      method: 'POST',
      url: `/api/actions/${actionId}/decision`,
      payload: { decision: 'cancel' },
    });
    expect(cancel.json().action.status).toBe('cancelled');
  });

  it('unknown actions 404; invalid decisions 400', async () => {
    ctx = createTestApp();
    const missing = await ctx.app.inject({
      method: 'POST',
      url: `/api/actions/${crypto.randomUUID()}/decision`,
      payload: { decision: 'approve' },
    });
    expect(missing.statusCode).toBe(404);

    const actionId = await createPendingAction(ctx);
    const invalid = await ctx.app.inject({
      method: 'POST',
      url: `/api/actions/${actionId}/decision`,
      payload: { decision: 'yes' },
    });
    expect(invalid.statusCode).toBe(400);
  });
});

describe('memories and settings API', () => {
  it('creates, lists, and archives memories through the API', async () => {
    ctx = createTestApp();
    const created = await ctx.app.inject({
      method: 'POST',
      url: '/api/memories',
      payload: { kind: 'preference', value: 'Approval before external actions' },
    });
    expect(created.statusCode).toBe(201);
    const id = created.json().memory.id as string;

    const list = await ctx.app.inject({ method: 'GET', url: '/api/memories' });
    expect(list.json().memories).toHaveLength(1);

    const archived = await ctx.app.inject({ method: 'DELETE', url: `/api/memories/${id}` });
    expect(archived.json().memory.archivedAt).not.toBeNull();

    const after = await ctx.app.inject({ method: 'GET', url: '/api/memories' });
    expect(after.json().memories).toHaveLength(0);
  });

  it('searches memories, rejects duplicates, and edits via PATCH', async () => {
    ctx = createTestApp();
    await ctx.app.inject({
      method: 'POST',
      url: '/api/memories',
      payload: { kind: 'note', value: 'The trading bot demo is on Friday' },
    });
    const duplicate = await ctx.app.inject({
      method: 'POST',
      url: '/api/memories',
      payload: { kind: 'note', value: 'the trading bot demo is on friday!' },
    });
    expect(duplicate.statusCode).toBe(409);
    expect(duplicate.json().error.code).toBe('duplicate_memory');

    const forced = await ctx.app.inject({
      method: 'POST',
      url: '/api/memories',
      payload: { kind: 'note', value: 'the trading bot demo is on friday!', allowDuplicate: true },
    });
    expect(forced.statusCode).toBe(201);

    const search = await ctx.app.inject({ method: 'GET', url: '/api/memories?q=trading' });
    expect(search.json().memories.length).toBe(2);
    const none = await ctx.app.inject({ method: 'GET', url: '/api/memories?q=zzz-nomatch' });
    expect(none.json().memories).toHaveLength(0);

    const id = forced.json().memory.id as string;
    const patched = await ctx.app.inject({
      method: 'PATCH',
      url: `/api/memories/${id}`,
      payload: { value: 'Demo moved to Saturday', kind: 'task' },
    });
    expect(patched.statusCode).toBe(200);
    expect(patched.json().memory.value).toBe('Demo moved to Saturday');
    expect(patched.json().memory.kind).toBe('task');
  });

  it('never stores sensitive content without explicit confirmation', async () => {
    ctx = createTestApp();
    const blocked = await ctx.app.inject({
      method: 'POST',
      url: '/api/memories',
      payload: { kind: 'note', value: 'my email password is hunter2' },
    });
    expect(blocked.statusCode).toBe(409);
    expect(blocked.json().error.code).toBe('sensitive_confirmation_required');
    expect((await ctx.app.inject({ method: 'GET', url: '/api/memories' })).json().memories).toHaveLength(0);

    const confirmed = await ctx.app.inject({
      method: 'POST',
      url: '/api/memories',
      payload: { kind: 'note', value: 'my email password is hunter2', confirmSensitive: true },
    });
    expect(confirmed.statusCode).toBe(201);
    expect(confirmed.json().memory.sensitive).toBe(true);
  });

  it('conversation memory writes block sensitive content and duplicates honestly', async () => {
    ctx = createTestApp();
    const sensitive = await ctx.app.inject({
      method: 'POST',
      url: '/api/assistant/stream',
      payload: { input: 'Remember that my banking password is hunter2' },
    });
    const sensitiveEvents = parseNdjson(sensitive.body).map((e) => activityEventSchema.parse(e));
    expect(sensitiveEvents.map((e) => e.eventType)).not.toContain('memory.saved');
    expect(ctx.repos.memories.listActive()).toHaveLength(0);

    await ctx.app.inject({
      method: 'POST',
      url: '/api/assistant/stream',
      payload: { input: 'Remember that the demo starts at nine' },
    });
    const repeat = await ctx.app.inject({
      method: 'POST',
      url: '/api/assistant/stream',
      payload: { input: 'Remember that the demo starts at nine' },
    });
    const repeatEvents = parseNdjson(repeat.body).map((e) => activityEventSchema.parse(e));
    expect(repeatEvents.map((e) => e.eventType)).not.toContain('memory.saved');
    expect(ctx.repos.memories.listActive()).toHaveLength(1);
  });

  it('registers, lists, refreshes, and unregisters an inspectable project', async () => {
    ctx = createTestApp();
    const fs = await import('node:fs');
    const os = await import('node:os');
    const path = await import('node:path');
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'jarvis-regproj-'));
    fs.writeFileSync(path.join(dir, 'package.json'), '{"name":"demo","scripts":{"test":"x"}}');
    try {
      const bad = await ctx.app.inject({
        method: 'POST',
        url: '/api/projects/register',
        payload: { path: 'C:\\Windows' },
      });
      expect(bad.statusCode).toBe(400);

      const created = await ctx.app.inject({
        method: 'POST',
        url: '/api/projects/register',
        payload: { path: dir },
      });
      expect(created.statusCode).toBe(201);
      const id = created.json().project.id as string;
      expect(created.json().project.profile.projectType).toBe('Node.js');

      const duplicate = await ctx.app.inject({
        method: 'POST',
        url: '/api/projects/register',
        payload: { path: dir },
      });
      expect(duplicate.statusCode).toBe(409);

      const list = await ctx.app.inject({ method: 'GET', url: '/api/projects/registered' });
      expect(list.json().projects).toHaveLength(1);

      const refreshed = await ctx.app.inject({
        method: 'POST',
        url: `/api/projects/registered/${id}/refresh`,
      });
      expect(refreshed.statusCode).toBe(200);

      const removed = await ctx.app.inject({
        method: 'DELETE',
        url: `/api/projects/registered/${id}`,
      });
      expect(removed.json().project.archivedAt).not.toBeNull();
      const after = await ctx.app.inject({ method: 'GET', url: '/api/projects/registered' });
      expect(after.json().projects).toHaveLength(0);
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });

  it('gates registered-project content behind approval before it reaches the Claude CLI', async () => {
    const { ClaudeCliProvider } = await import('../../src/server/providers/model');
    const { loadConfig } = await import('../../src/server/config/env');
    const cliCalls: string[] = [];
    const fakeCli = new ClaudeCliProvider(
      loadConfig({
        dataDir: 'unused',
        modelProvider: 'claude_cli',
        claudeCliEnabled: true,
        claudeCliCommand: 'claude',
      }),
      async ({ stdin }) => {
        cliCalls.push(stdin);
        return {
          exitCode: 0,
          stdout: JSON.stringify({ result: 'Deep analysis from Claude CLI.' }),
          stderr: '',
          timedOut: false,
        };
      },
    );
    ctx = createTestApp(
      { modelProvider: 'claude_cli', claudeCliEnabled: true },
      { provider: fakeCli, claudeCli: fakeCli },
    );

    // Register a project so its profile would be part of the context.
    const fs = await import('node:fs');
    const os = await import('node:os');
    const path = await import('node:path');
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'jarvis-cligate-'));
    fs.writeFileSync(path.join(dir, 'package.json'), '{"name":"tradebot"}');
    try {
      await ctx.app.inject({
        method: 'POST',
        url: '/api/projects/register',
        payload: { path: dir, name: 'tradebot' },
      });

      const res = await ctx.app.inject({
        method: 'POST',
        url: '/api/assistant/stream',
        payload: { input: 'Analyze the tradebot project in depth please' },
      });
      const events = parseNdjson(res.body).map((e) => activityEventSchema.parse(e));
      const permission = events.find((e) => e.eventType === 'permission.required');
      expect(permission).toBeDefined();
      if (permission?.eventType !== 'permission.required') throw new Error('no permission');
      expect(permission.payload.actionType).toBe('claude_cli_context_send');
      // Nothing was sent to the CLI before approval.
      expect(cliCalls).toHaveLength(0);

      const approve = await ctx.app.inject({
        method: 'POST',
        url: `/api/actions/${permission.payload.actionId}/decision`,
        payload: { decision: 'approve' },
      });
      expect(approve.json().action.status).toBe('completed');
      expect(cliCalls).toHaveLength(1);
      expect(cliCalls[0]).toContain('tradebot');

      // The CLI reply landed in the conversation, honestly attributed.
      const bootstrap = await ctx.app.inject({ method: 'GET', url: '/api/bootstrap' });
      const messages = bootstrap.json().messages as Array<{ content: string; provider: string | null }>;
      const reply = messages.find((m) => m.content.includes('Deep analysis from Claude CLI.'));
      expect(reply?.provider).toContain('Claude CLI');
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });

  it('a cancelled CLI-send approval sends nothing', async () => {
    const { ClaudeCliProvider } = await import('../../src/server/providers/model');
    const { loadConfig } = await import('../../src/server/config/env');
    const cliCalls: string[] = [];
    const fakeCli = new ClaudeCliProvider(
      loadConfig({ dataDir: 'unused', claudeCliEnabled: true, claudeCliCommand: 'claude' }),
      async ({ stdin }) => {
        cliCalls.push(stdin);
        return { exitCode: 0, stdout: '{"result":"x"}', stderr: '', timedOut: false };
      },
    );
    ctx = createTestApp(
      { modelProvider: 'claude_cli', claudeCliEnabled: true },
      { provider: fakeCli, claudeCli: fakeCli },
    );
    const fs = await import('node:fs');
    const os = await import('node:os');
    const path = await import('node:path');
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'jarvis-cligate2-'));
    fs.writeFileSync(path.join(dir, 'package.json'), '{"name":"secretproj"}');
    try {
      await ctx.app.inject({
        method: 'POST',
        url: '/api/projects/register',
        payload: { path: dir, name: 'secretproj' },
      });
      const res = await ctx.app.inject({
        method: 'POST',
        url: '/api/assistant/stream',
        payload: { input: 'Tell me about secretproj' },
      });
      const events = parseNdjson(res.body).map((e) => activityEventSchema.parse(e));
      const permission = events.find((e) => e.eventType === 'permission.required');
      if (permission?.eventType !== 'permission.required') throw new Error('no permission');
      await ctx.app.inject({
        method: 'POST',
        url: `/api/actions/${permission.payload.actionId}/decision`,
        payload: { decision: 'cancel' },
      });
      expect(cliCalls).toHaveLength(0);
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });

  it('trading status is honestly disconnected by default and trade execution is impossible', async () => {
    ctx = createTestApp();
    const status = await ctx.app.inject({ method: 'GET', url: '/api/trading/status' });
    expect(status.json().connected).toBe(false);
    expect(status.json().setupMessage).toContain('TRADING_REPORT_PATH');

    // Even an approved trade_execute action fails: no executor exists.
    const action = ctx.repos.pendingActions.create({
      requestId: crypto.randomUUID(),
      toolName: 'trading',
      actionType: 'trade_execute',
      payload: { symbol: 'BTC-USD', side: 'buy', quantity: 1 },
      summary: 'Buy 1 BTC',
      ttlMs: 60_000,
    });
    const approve = await ctx.app.inject({
      method: 'POST',
      url: `/api/actions/${action.id}/decision`,
      payload: { decision: 'approve' },
    });
    expect(approve.json().action.status).toBe('failed');
    expect(approve.json().action.executionError).toContain('No executor');
  });

  it('google endpoints report honest disconnected states', async () => {
    ctx = createTestApp();
    const status = await ctx.app.inject({ method: 'GET', url: '/api/google/status' });
    expect(status.json().configured).toBe(false);
    expect(status.json().setupMessage).toContain('GOOGLE_CLIENT_ID');

    const mail = await ctx.app.inject({ method: 'GET', url: '/api/mail/messages' });
    expect(mail.statusCode).toBe(409);
    expect(mail.json().error.code).toBe('google_not_connected');

    const events = await ctx.app.inject({ method: 'GET', url: '/api/calendar/events' });
    expect(events.statusCode).toBe(409);
  });

  it('mail/calendar actions only create approval records; execution without a connection fails honestly', async () => {
    ctx = createTestApp();
    const proposal = await ctx.app.inject({
      method: 'POST',
      url: '/api/mail/actions',
      payload: { type: 'send', to: 'a@b.com', subject: 'Hi', body: 'Hello there' },
    });
    expect(proposal.statusCode).toBe(201);
    const action = proposal.json().action;
    expect(action.status).toBe('pending');
    expect(action.actionType).toBe('email_send');
    expect(action.summary).toContain('a@b.com');
    expect(action.consequences).toContain('cannot be unsent');

    // Approving without a Google connection records an honest failure.
    const approve = await ctx.app.inject({
      method: 'POST',
      url: `/api/actions/${action.id}/decision`,
      payload: { decision: 'approve' },
    });
    expect(approve.json().action.status).toBe('failed');
    expect(approve.json().action.executionError).toContain('not connected');

    const calProposal = await ctx.app.inject({
      method: 'POST',
      url: '/api/calendar/actions',
      payload: {
        type: 'respond',
        eventId: 'evt1',
        eventSummary: 'Standup',
        response: 'accepted',
      },
    });
    expect(calProposal.statusCode).toBe(201);
    expect(calProposal.json().action.actionType).toBe('calendar_respond');
  });

  it('persists settings updates', async () => {
    ctx = createTestApp();
    const res = await ctx.app.inject({
      method: 'PUT',
      url: '/api/settings',
      payload: { autoSpeak: false },
    });
    expect(res.json().settings.autoSpeak).toBe(false);
    const bootstrap = await ctx.app.inject({ method: 'GET', url: '/api/bootstrap' });
    expect(bootstrap.json().settings.autoSpeak).toBe(false);
  });
});
