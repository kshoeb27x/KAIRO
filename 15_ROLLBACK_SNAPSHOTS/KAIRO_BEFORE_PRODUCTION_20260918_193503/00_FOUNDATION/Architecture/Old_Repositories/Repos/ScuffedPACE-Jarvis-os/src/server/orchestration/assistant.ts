import { randomUUID } from 'node:crypto';
import { PENDING_ACTION_TTL_MS } from '../../shared/constants';
import { activityEventSchema, type ActivityEvent } from '../../shared/schemas/activity';
import type { Memory, MemoryKind, Message, RouteResult } from '../../shared/types';
import type { Repositories } from '../repositories';
import type { ModelProvider } from '../providers/model';
import { ModelProviderError } from '../providers/model';
import { MockMailTool } from '../providers/tools/mockMailTool';
import { detectSensitive } from '../../shared/security/sensitive';
import { buildContext } from './contextBuilder';
import type { Router } from './router';

export interface AssistantDeps {
  repos: Repositories;
  provider: ModelProvider;
  router: Router;
}

export type EmitFn = (event: ActivityEvent) => void;

interface RunInput {
  input: string;
  conversationId?: string;
  signal?: AbortSignal;
}

/**
 * Runs one assistant request end-to-end, emitting validated NDJSON envelopes
 * only when the corresponding operation actually occurred. Safe copies of
 * events are persisted to activity_events (never secrets or full prompts).
 */
export async function runAssistantRequest(
  deps: AssistantDeps,
  run: RunInput,
  emitRaw: EmitFn,
): Promise<void> {
  const { repos, provider, router } = deps;
  const requestId = randomUUID();

  const emit = (event: ActivityEvent): void => {
    const validated = activityEventSchema.parse(event);
    repos.activityEvents.record({
      requestId: validated.requestId,
      eventType: validated.eventType,
      safeLabel: validated.label,
      metadata: safeMetadata(validated),
      occurredAt: validated.occurredAt,
    });
    emitRaw(validated);
  };

  const envelope = (partial: Omit<ActivityEvent, 'schemaVersion' | 'requestId' | 'eventId' | 'occurredAt'>) =>
    ({
      schemaVersion: 1 as const,
      requestId,
      eventId: randomUUID(),
      occurredAt: new Date().toISOString(),
      ...partial,
    }) as ActivityEvent;

  try {
    const input = run.input.trim();

    // Resolve or create the conversation, then persist the user message.
    const project = repos.projects.findActive();
    let conversation = run.conversationId
      ? repos.conversations.findById(run.conversationId)
      : repos.conversations.findMostRecent();
    if (!conversation || conversation.archivedAt) {
      conversation = repos.conversations.create({
        projectId: project?.id ?? null,
        title: truncate(input, 60),
      });
    }
    repos.conversations.addMessage({
      conversationId: conversation.id,
      role: 'user',
      content: input,
    });

    emit(
      envelope({
        eventType: 'request.accepted',
        label: 'Request received',
        payload: { conversationId: conversation.id, inputPreview: truncate(input, 120) },
      }),
    );

    // Route the request (deterministic; always schema-validated).
    const route = router.route(requestId, input);
    // Context is loaded for model executions; memory.loaded is emitted only
    // when a lookup actually happens.
    emit(
      envelope({
        eventType: 'route.selected',
        label: routeLabel(route),
        payload: { route },
      }),
    );

    if (route.execution === 'memory_write') {
      await handleMemoryWrite(deps, emit, envelope, conversation.id, input, project?.id ?? null);
      return;
    }

    if (route.execution === 'mock_tool') {
      await handleMockMail(deps, emit, envelope, conversation.id, requestId, input, project?.name ?? null);
      return;
    }

    // Model execution (chat / project / deep_reasoning).
    const context = buildContext(repos, route, conversation, input);
    emit(
      envelope({
        eventType: 'memory.loaded',
        label:
          context.memoriesUsed.length > 0
            ? `Loaded ${context.memoriesUsed.length} relevant memor${context.memoriesUsed.length === 1 ? 'y' : 'ies'}`
            : 'Checked memory (nothing relevant)',
        payload: {
          memoryCount: context.memoriesUsed.length,
          projectName: context.project?.name ?? null,
        },
      }),
    );

    const tier: 'deep' | 'fast' = route.intent === 'deep_reasoning' ? 'deep' : 'fast';

    // Local project content never leaves for the Claude CLI without an
    // explicit approval showing exactly what would be sent.
    const cliBacked = provider.usesLocalCli?.(tier) ?? false;
    if (cliBacked && context.registeredProjectName) {
      const action = repos.pendingActions.create({
        requestId,
        toolName: 'claude_cli',
        actionType: 'claude_cli_context_send',
        payload: {
          project: context.registeredProjectName,
          contextPreview: truncate(context.system, 800),
          approxCharacters: context.system.length + input.length,
          _system: context.system,
          _messages: context.messages,
          _tier: tier,
          _conversationId: conversation.id,
        },
        summary: `Send this question plus the "${context.registeredProjectName}" project summary to your local Claude CLI`,
        target: 'Claude CLI (your local Claude login)',
        reason: 'The request needs deeper analysis and mentions a registered project.',
        consequences:
          'The shown context (project summary and conversation excerpt) is processed by Claude under your existing Claude account. Nothing is sent anywhere else.',
        ttlMs: PENDING_ACTION_TTL_MS,
      });
      emit(
        envelope({
          eventType: 'permission.required',
          label: 'Approval required before sending project context to Claude CLI',
          payload: {
            actionId: action.id,
            actionType: action.actionType,
            tool: 'claude_cli',
            expiresAt: action.expiresAt,
            action,
          },
        }),
      );
      const text =
        `This request would send the "${context.registeredProjectName}" project summary to your local Claude CLI. ` +
        `Review and approve the request card to continue, or cancel and I'll keep it local.`;
      const message = repos.conversations.addMessage({
        conversationId: conversation.id,
        role: 'assistant',
        content: text,
        provider: 'system',
        model: null,
      });
      emitCompleted(emit, envelope, message);
      return;
    }

    const status = provider.status();
    emit(
      envelope({
        eventType: 'model.started',
        label:
          provider.id === 'mock'
            ? `Demo Provider responding (simulated${route.intent === 'deep_reasoning' ? ' deep reasoning' : ''})`
            : `${route.intent === 'deep_reasoning' ? 'Deep model' : 'Fast model'} responding (${
                route.intent === 'deep_reasoning'
                  ? (status.deepModel ?? status.fastModel ?? 'unconfigured')
                  : (status.fastModel ?? 'unconfigured')
              })`,
        payload: {
          provider: status.label,
          model:
            (route.intent === 'deep_reasoning' ? status.deepModel : status.fastModel) ??
            status.fastModel ??
            'unconfigured',
          simulated: provider.id === 'mock',
        },
      }),
    );

    const result = await provider.complete({
      system: context.system,
      messages: context.messages,
      tier,
      maxTokens: tier === 'deep' ? 2048 : 1024,
      signal: run.signal,
      demoContext: {
        intent: route.intent,
        projectName: context.project?.name ?? null,
        projectSummary: context.project?.summary ?? null,
      },
    });

    const message = repos.conversations.addMessage({
      conversationId: conversation.id,
      role: 'assistant',
      content: result.text,
      provider: result.provider,
      model: result.model,
    });
    emitCompleted(emit, envelope, message);
  } catch (error) {
    emitFailure(emit, envelope, error);
  }
}

async function handleMemoryWrite(
  deps: AssistantDeps,
  emit: EmitFn,
  envelope: (p: Omit<ActivityEvent, 'schemaVersion' | 'requestId' | 'eventId' | 'occurredAt'>) => ActivityEvent,
  conversationId: string,
  input: string,
  projectId: string | null,
): Promise<void> {
  const { repos } = deps;
  const parsed = parseMemoryRequest(input);

  // Duplicate guard: repeating a memory should not create a second copy.
  const duplicate = repos.memories.findActiveDuplicate(parsed.value);
  if (duplicate) {
    const text = `I already have that saved${duplicate.kind === 'preference' ? ' as a preference' : ''}: "${duplicate.value}". Nothing new was stored — you can review it in Memory.`;
    const message = repos.conversations.addMessage({
      conversationId,
      role: 'assistant',
      content: text,
      provider: 'system',
      model: null,
    });
    emitCompleted(emit, envelope, message);
    return;
  }

  // Sensitive content is never stored silently from conversation.
  const sensitiveMatch = detectSensitive(parsed.value);
  if (sensitiveMatch) {
    const text =
      `I didn't save that automatically because ${sensitiveMatch.reason}. ` +
      `If you really want me to keep it, add it deliberately in the Memory panel ` +
      `(it will ask you to confirm), or rephrase it without the sensitive part.`;
    const message = repos.conversations.addMessage({
      conversationId,
      role: 'assistant',
      content: text,
      provider: 'system',
      model: null,
    });
    emitCompleted(emit, envelope, message);
    return;
  }

  // Persist first; only claim success after the database write succeeded.
  const memory: Memory = repos.memories.create({
    kind: parsed.kind,
    value: parsed.value,
    memoryKey: parsed.memoryKey,
    tags: parsed.tags,
    source: 'user_explicit',
    sourceDetail: 'conversation',
    projectId,
  });

  emit(
    envelope({
      eventType: 'memory.saved',
      label: parsed.kind === 'preference' ? 'Preference saved' : 'Memory saved',
      payload: { memoryId: memory.id, memoryKey: memory.memoryKey },
    }),
  );

  const kindLabels: Partial<Record<Memory['kind'], string>> = {
    preference: 'as a preference',
    task: 'as a task',
    decision: 'as a decision',
    lesson: 'as a lesson learned',
    personal_fact: 'as a personal fact',
  };
  const text = `Saved${kindLabels[memory.kind] ? ` ${kindLabels[memory.kind]}` : ''}. I'll remember: "${parsed.value}". You can review or archive this any time in Memory.`;
  const message = repos.conversations.addMessage({
    conversationId,
    role: 'assistant',
    content: text,
    provider: 'system',
    model: null,
  });
  emitCompleted(emit, envelope, message);
}

async function handleMockMail(
  deps: AssistantDeps,
  emit: EmitFn,
  envelope: (p: Omit<ActivityEvent, 'schemaVersion' | 'requestId' | 'eventId' | 'occurredAt'>) => ActivityEvent,
  conversationId: string,
  requestId: string,
  input: string,
  projectName: string | null,
): Promise<void> {
  const { repos } = deps;
  const tool = new MockMailTool();

  emit(
    envelope({
      eventType: 'tool.started',
      label: 'Mail tool drafting (simulated)',
      payload: { tool: tool.name, simulated: true },
    }),
  );

  const result = await tool.run(input, { projectName, ownerName: 'Farhan' });

  emit(
    envelope({
      eventType: 'tool.completed',
      label: result.summary,
      payload: { tool: tool.name, simulated: true, summary: result.summary },
    }),
  );

  // Server-side pending action: sending can only complete via an explicit,
  // single-use, server-recorded approval decision.
  const action = repos.pendingActions.create({
    requestId,
    toolName: tool.name,
    actionType: 'simulated_send',
    payload: result.draft as unknown as Record<string, unknown>,
    summary: `Record a simulated send of "${result.draft.subject}" to ${result.draft.to}`,
    target: 'Simulated mail (no real account connected)',
    reason: 'You asked JARVIS to draft this email.',
    consequences: 'Nothing is actually sent in this prototype; only the decision is recorded.',
    ttlMs: PENDING_ACTION_TTL_MS,
  });

  emit(
    envelope({
      eventType: 'permission.required',
      label: 'Approval required before simulated send',
      payload: {
        actionId: action.id,
        actionType: action.actionType,
        tool: tool.name,
        expiresAt: action.expiresAt,
        action,
      },
    }),
  );

  const text =
    `I've prepared the email draft below (simulated — nothing is actually sent in this prototype). ` +
    `Approve to record a simulated send, or cancel.\n\nTo: ${result.draft.to}\nSubject: ${result.draft.subject}\n\n${result.draft.body}`;
  const message = repos.conversations.addMessage({
    conversationId,
    role: 'assistant',
    content: text,
    provider: 'tool:mock_mail',
    model: null,
  });
  emitCompleted(emit, envelope, message);
}

function emitCompleted(
  emit: EmitFn,
  envelope: (p: Omit<ActivityEvent, 'schemaVersion' | 'requestId' | 'eventId' | 'occurredAt'>) => ActivityEvent,
  message: Message,
): void {
  emit(
    envelope({
      eventType: 'response.completed',
      label: 'Response ready',
      payload: { message },
    }),
  );
}

function emitFailure(
  emit: EmitFn,
  envelope: (p: Omit<ActivityEvent, 'schemaVersion' | 'requestId' | 'eventId' | 'occurredAt'>) => ActivityEvent,
  error: unknown,
): void {
  const normalized =
    error instanceof ModelProviderError
      ? { errorCode: error.code, message: error.message, recoverable: error.recoverable }
      : {
          errorCode: 'internal_error',
          message: 'Something went wrong handling this request. Nothing was sent or deleted.',
          recoverable: true,
        };
  emit(
    envelope({
      eventType: 'request.failed',
      label: 'Request failed',
      payload: normalized,
    }),
  );
}

export function parseMemoryRequest(input: string): {
  kind: MemoryKind;
  value: string;
  memoryKey: string | null;
  tags: string[];
} {
  const value = input
    .replace(/^(please\s+|jarvis[,\s]+)*/i, '')
    .replace(/^remember\s+(that\s+)?/i, '')
    .trim()
    .replace(/[.\s]+$/, '');
  const kind: MemoryKind = classifyMemoryKind(value);
  const memoryKey = value
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter(Boolean)
    .slice(0, 6)
    .join('-');
  return { kind, value, memoryKey: memoryKey || null, tags: [] };
}

/** Deterministic memory-kind classification from the phrasing of the request. */
export function classifyMemoryKind(value: string): MemoryKind {
  const lower = value.toLowerCase();
  if (/^to\s|\bi (need|have) to\b|\bdon'?t forget\b|\btodo\b/.test(lower)) return 'task';
  if (/\b(we|i) decided\b|\bdecision\b/.test(lower)) return 'decision';
  if (/\blesson\b|\b(we|i) learned\b/.test(lower)) return 'lesson';
  if (/\bprefer|approval|always|never\b/.test(lower)) return 'preference';
  if (/\b(my|i am|i'm|i live|i was born|my name)\b/.test(lower)) return 'personal_fact';
  return 'note';
}

function routeLabel(route: RouteResult): string {
  const names: Record<RouteResult['intent'], string> = {
    chat: 'Routed to general chat',
    project: 'Routed to project specialist',
    tool: 'Routed to mail tool (simulated)',
    deep_reasoning: 'Routed to deep reasoning',
    memory: 'Routed to memory',
  };
  return `${names[route.intent]} (${route.reasonCode.replaceAll('_', ' ')})`;
}

function safeMetadata(event: ActivityEvent): Record<string, unknown> {
  // Persist only compact, safe fields — never full prompts or drafts.
  switch (event.eventType) {
    case 'route.selected':
      return { intent: event.payload.route.intent, reasonCode: event.payload.route.reasonCode };
    case 'model.started':
      return { model: event.payload.model, simulated: event.payload.simulated };
    case 'permission.required':
      return { actionId: event.payload.actionId, actionType: event.payload.actionType };
    case 'request.failed':
      return { errorCode: event.payload.errorCode };
    default:
      return {};
  }
}

function truncate(text: string, max: number): string {
  return text.length <= max ? text : `${text.slice(0, max - 1)}…`;
}
