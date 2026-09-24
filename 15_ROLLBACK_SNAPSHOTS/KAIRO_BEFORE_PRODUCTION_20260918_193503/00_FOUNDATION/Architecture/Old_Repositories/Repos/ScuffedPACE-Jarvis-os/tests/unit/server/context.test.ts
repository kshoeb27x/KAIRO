import { afterEach, describe, expect, it } from 'vitest';
import { CONTEXT_MEMORY_LIMIT, CONTEXT_MESSAGE_LIMIT } from '../../../src/shared/constants';
import {
  buildContext,
  selectRelevantMemories,
} from '../../../src/server/orchestration/contextBuilder';
import { parseMemoryRequest } from '../../../src/server/orchestration/assistant';
import { RuleBasedRouter } from '../../../src/server/orchestration/router';
import { seedDatabase } from '../../../src/server/persistence/seed';
import { createTestDb, type TestDb } from '../../helpers/testDb';

let ctx: TestDb | null = null;
afterEach(() => {
  ctx?.cleanup();
  ctx = null;
});

describe('context construction boundaries', () => {
  it('bounds messages, includes project and relevant memories, excludes archived', () => {
    ctx = createTestDb();
    seedDatabase(ctx.repos);
    const conversation = ctx.repos.conversations.create({ projectId: null, title: 't' });
    for (let i = 0; i < 30; i += 1) {
      ctx.repos.conversations.addMessage({
        conversationId: conversation.id,
        role: i % 2 === 0 ? 'user' : 'assistant',
        content: `message ${i}`,
      });
    }
    ctx.repos.memories.create({ kind: 'preference', value: 'Prefers approval before actions' });
    const archived = ctx.repos.memories.create({ kind: 'note', value: 'prototype secret note' });
    ctx.repos.memories.archive(archived.id);

    const route = new RuleBasedRouter().route(crypto.randomUUID(), 'plan the prototype build');
    const built = buildContext(ctx.repos, route, conversation, 'plan the prototype build');

    expect(built.messages.length).toBeLessThanOrEqual(CONTEXT_MESSAGE_LIMIT);
    expect(built.system).toContain('JARVIS OS');
    expect(built.system).toContain('Prefers approval');
    expect(built.system).not.toContain('prototype secret note');
  });

  it('injects the owner-selected explanation depth into the system prompt', () => {
    ctx = createTestDb();
    seedDatabase(ctx.repos);
    const conversation = ctx.repos.conversations.create({ projectId: null, title: 't' });
    const route = new RuleBasedRouter().route(crypto.randomUUID(), 'hello');

    expect(buildContext(ctx.repos, route, conversation, 'hello').system).toContain(
      'Explanation depth: NORMAL',
    );
    ctx.repos.settings.update({ explanationDepth: 'simple' });
    expect(buildContext(ctx.repos, route, conversation, 'hello').system).toContain(
      'Explanation depth: SIMPLE',
    );
    ctx.repos.settings.update({ explanationDepth: 'technical' });
    expect(buildContext(ctx.repos, route, conversation, 'hello').system).toContain(
      'Explanation depth: TECHNICAL',
    );
  });

  it('separates owner preferences from other memories in the prompt', () => {
    ctx = createTestDb();
    seedDatabase(ctx.repos);
    const conversation = ctx.repos.conversations.create({ projectId: null, title: 't' });
    ctx.repos.memories.create({ kind: 'preference', value: 'Prefers approval before actions' });
    ctx.repos.memories.create({ kind: 'note', value: 'the approval demo runs tonight' });
    const route = new RuleBasedRouter().route(crypto.randomUUID(), 'what about approval tonight?');
    const built = buildContext(ctx.repos, route, conversation, 'what about approval tonight?');
    expect(built.system).toContain("Farhan's saved preferences");
    expect(built.system).toContain('Prefers approval before actions');
    expect(built.system).toContain('[note] the approval demo runs tonight');
  });

  it('keyword relevance is bounded and deterministic', () => {
    const memories = Array.from({ length: 20 }, (_, i) => ({
      id: crypto.randomUUID(),
      kind: 'note' as const,
      memoryKey: null,
      value: `note about prototype topic ${i}`,
      tags: [],
      source: 'user_explicit' as const,
      sourceDetail: null,
      sensitive: false,
      projectId: null,
      createdAt: '',
      updatedAt: '',
      archivedAt: null,
    }));
    const selected = selectRelevantMemories(memories, 'tell me about the prototype');
    expect(selected.length).toBeLessThanOrEqual(CONTEXT_MEMORY_LIMIT);
    expect(selectRelevantMemories(memories, 'unrelated xyz')).toHaveLength(0);
  });
});

describe('parseMemoryRequest', () => {
  it('extracts the fact and classifies preferences', () => {
    const parsed = parseMemoryRequest(
      'Remember that I prefer approval before any external action.',
    );
    expect(parsed.value).toBe('I prefer approval before any external action');
    expect(parsed.kind).toBe('preference');
    expect(parsed.memoryKey).toBeTruthy();
  });

  it('classifies plain facts as notes', () => {
    expect(parseMemoryRequest('remember the demo starts at 9').kind).toBe('note');
  });
});
