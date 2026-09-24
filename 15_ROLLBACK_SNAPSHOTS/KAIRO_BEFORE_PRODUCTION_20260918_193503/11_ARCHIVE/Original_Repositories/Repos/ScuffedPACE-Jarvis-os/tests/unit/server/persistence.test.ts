import { afterEach, describe, expect, it } from 'vitest';
import { SCHEMA_VERSION } from '../../../src/shared/constants';
import { runMigrations, currentSchemaVersion } from '../../../src/server/persistence/migrate';
import { seedDatabase, SEED_PROJECT_ID } from '../../../src/server/persistence/seed';
import { createTestDb, type TestDb } from '../../helpers/testDb';

let ctx: TestDb | null = null;

afterEach(() => {
  ctx?.cleanup();
  ctx = null;
});

describe('migrations', () => {
  it('creates the current schema version on a fresh database', () => {
    ctx = createTestDb();
    expect(currentSchemaVersion(ctx.db)).toBe(SCHEMA_VERSION);
    const tables = ctx.db
      .prepare(`SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name`)
      .all() as Array<{ name: string }>;
    const names = tables.map((t) => t.name);
    for (const expected of [
      'projects',
      'conversations',
      'messages',
      'memories',
      'pending_actions',
      'activity_events',
      'settings',
      'schema_migrations',
    ]) {
      expect(names).toContain(expected);
    }
  });

  it('is idempotent on repeated startup and preserves existing records', () => {
    ctx = createTestDb();
    ctx.repos.projects.create({ name: 'Existing', summary: 'keep me' });
    const result = runMigrations(ctx.db);
    expect(result.applied).toHaveLength(0);
    expect(result.alreadyApplied.length).toBeGreaterThan(0);
    const row = ctx.db.prepare(`SELECT COUNT(*) AS n FROM projects`).get() as { n: number };
    expect(row.n).toBe(1);
  });

  it('persists data across a database reopen', () => {
    ctx = createTestDb();
    seedDatabase(ctx.repos);
    const conversation = ctx.repos.conversations.create({
      projectId: SEED_PROJECT_ID,
      title: 'Test',
    });
    ctx.repos.conversations.addMessage({
      conversationId: conversation.id,
      role: 'user',
      content: 'hello',
    });
    ctx = ctx.reopen();
    const reloaded = ctx.repos.conversations.findMostRecent();
    expect(reloaded?.id).toBe(conversation.id);
    expect(ctx.repos.conversations.listMessages(conversation.id)).toHaveLength(1);
    expect(ctx.repos.projects.findActive()?.name).toBe('JARVIS OS');
  });
});

describe('seeding', () => {
  it('seeds the JARVIS OS project once and is idempotent', () => {
    ctx = createTestDb();
    expect(seedDatabase(ctx.repos).seededProject).toBe(true);
    expect(seedDatabase(ctx.repos).seededProject).toBe(false);
    const row = ctx.db.prepare('SELECT COUNT(*) AS n FROM projects').get() as { n: number };
    expect(row.n).toBe(1);
  });

  it('does not recreate an archived seed project', () => {
    ctx = createTestDb();
    seedDatabase(ctx.repos);
    ctx.db
      .prepare(`UPDATE projects SET archived_at = ?, is_active = 0 WHERE id = ?`)
      .run(new Date().toISOString(), SEED_PROJECT_ID);
    expect(seedDatabase(ctx.repos).seededProject).toBe(false);
    expect(ctx.repos.projects.findActive()).toBeNull();
  });
});

describe('memories repository', () => {
  it('creates and archives explicit memories; archived excluded from active list', () => {
    ctx = createTestDb();
    const memory = ctx.repos.memories.create({
      kind: 'preference',
      value: 'Prefers approval before any external action',
      memoryKey: 'approval-before-external-actions',
      tags: ['permissions'],
    });
    expect(ctx.repos.memories.listActive()).toHaveLength(1);
    const archived = ctx.repos.memories.archive(memory.id);
    expect(archived?.archivedAt).not.toBeNull();
    expect(ctx.repos.memories.listActive()).toHaveLength(0);
    // Archived, not destroyed: still retrievable by id.
    expect(ctx.repos.memories.findById(memory.id)).not.toBeNull();
  });
});

describe('pending actions repository', () => {
  const draft = { to: 'collaborator@example.com', subject: 'Prototype', body: 'Ready tomorrow.' };

  function createAction(repos: TestDb['repos'], ttlMs = 60_000) {
    return repos.pendingActions.create({
      requestId: crypto.randomUUID(),
      toolName: 'mock_mail',
      actionType: 'simulated_send',
      payload: draft,
      ttlMs,
    });
  }

  it('starts pending and requires an explicit decision', () => {
    ctx = createTestDb();
    const action = createAction(ctx.repos);
    expect(action.status).toBe('pending');
    expect(ctx.repos.pendingActions.listPending()).toHaveLength(1);
  });

  it('approve records the decision, then execution is recorded exactly once', () => {
    ctx = createTestDb();
    const action = createAction(ctx.repos);
    const outcome = ctx.repos.pendingActions.decide(action.id, 'approve', 'local-owner');
    expect(outcome.ok).toBe(true);
    if (outcome.ok) {
      expect(outcome.action.status).toBe('approved');
      expect(outcome.action.decidedAt).not.toBeNull();
      expect(outcome.action.decidedBy).toBe('local-owner');
    }
    const executed = ctx.repos.pendingActions.recordExecution(action.id, {
      status: 'simulated_completed',
    });
    expect(executed?.status).toBe('simulated_completed');
    expect(executed?.executedAt).not.toBeNull();
    // Double execution is impossible.
    expect(
      ctx.repos.pendingActions.recordExecution(action.id, { status: 'completed' }),
    ).toBeNull();
  });

  it('execution failures are recorded honestly and cannot be re-run', () => {
    ctx = createTestDb();
    const action = createAction(ctx.repos);
    ctx.repos.pendingActions.decide(action.id, 'approve', 'local-owner');
    const failed = ctx.repos.pendingActions.recordExecution(action.id, {
      status: 'failed',
      error: 'The mail service was unreachable.',
    });
    expect(failed?.status).toBe('failed');
    expect(failed?.executionError).toContain('unreachable');
    expect(
      ctx.repos.pendingActions.recordExecution(action.id, { status: 'completed' }),
    ).toBeNull();
  });

  it('execution is impossible without a prior approval', () => {
    ctx = createTestDb();
    const action = createAction(ctx.repos);
    expect(
      ctx.repos.pendingActions.recordExecution(action.id, { status: 'completed' }),
    ).toBeNull();
    expect(ctx.repos.pendingActions.findById(action.id)?.status).toBe('pending');
  });

  it('cancel records cancelled', () => {
    ctx = createTestDb();
    const action = createAction(ctx.repos);
    const outcome = ctx.repos.pendingActions.decide(action.id, 'cancel', 'local-owner');
    expect(outcome.ok && outcome.action.status === 'cancelled').toBe(true);
  });

  it('rejects deciding an expired action and marks it expired', () => {
    ctx = createTestDb();
    const action = createAction(ctx.repos, -1000);
    const outcome = ctx.repos.pendingActions.decide(action.id, 'approve', 'local-owner');
    expect(outcome).toEqual({ ok: false, reason: 'expired' });
    expect(ctx.repos.pendingActions.findById(action.id)?.status).toBe('expired');
  });

  it('a decision is single-use; duplicate and conflicting decisions are rejected', () => {
    ctx = createTestDb();
    const action = createAction(ctx.repos);
    expect(ctx.repos.pendingActions.decide(action.id, 'approve', 'local-owner').ok).toBe(true);
    expect(ctx.repos.pendingActions.decide(action.id, 'approve', 'local-owner')).toEqual({
      ok: false,
      reason: 'already_decided',
    });
    expect(ctx.repos.pendingActions.decide(action.id, 'cancel', 'local-owner')).toEqual({
      ok: false,
      reason: 'already_decided',
    });
    expect(ctx.repos.pendingActions.findById(action.id)?.status).toBe('approved');
  });

  it('unknown action ids are not found', () => {
    ctx = createTestDb();
    expect(ctx.repos.pendingActions.decide(crypto.randomUUID(), 'approve', 'x')).toEqual({
      ok: false,
      reason: 'not_found',
    });
  });
});

describe('settings repository', () => {
  it('returns defaults, persists partial updates', () => {
    ctx = createTestDb();
    expect(ctx.repos.settings.get()).toEqual({
      autoSpeak: true,
      voiceUri: null,
      speechRate: 1,
      explanationDepth: 'normal',
    });
    const updated = ctx.repos.settings.update({ autoSpeak: false, explanationDepth: 'simple' });
    expect(updated.autoSpeak).toBe(false);
    expect(updated.explanationDepth).toBe('simple');
    ctx = ctx.reopen();
    expect(ctx.repos.settings.get().autoSpeak).toBe(false);
    expect(ctx.repos.settings.get().explanationDepth).toBe('simple');
  });
});
