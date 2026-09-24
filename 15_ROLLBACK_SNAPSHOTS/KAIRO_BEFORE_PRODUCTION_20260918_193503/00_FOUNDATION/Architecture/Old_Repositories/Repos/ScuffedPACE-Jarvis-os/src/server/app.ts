import path from 'node:path';
import fs from 'node:fs';
import { PassThrough } from 'node:stream';
import Fastify, { type FastifyInstance } from 'fastify';
import fastifyStatic from '@fastify/static';
import { APP_VERSION } from '../shared/constants';
import {
  actionDecisionRequestSchema,
  assistantRequestSchema,
  bootstrapResponseSchema,
  createMemoryRequestSchema,
  updateMemoryRequestSchema,
  healthResponseSchema,
  updateSettingsRequestSchema,
} from '../shared/contracts/api';
import { detectSensitive } from '../shared/security/sensitive';
import { validateProjectRoot } from './security/paths';
import { buildProjectProfile } from './projects/profile';
import { pendingActionStatusSchema } from '../shared/schemas/entities';
import type { ServerConfig } from './config/env';
import { openDatabase } from './persistence/db';
import { currentSchemaVersion, runMigrations } from './persistence/migrate';
import { seedDatabase } from './persistence/seed';
import { createRepositories, type Repositories } from './repositories';
import { createProviderSetup, type ClaudeCliProvider, type ModelProvider } from './providers/model';
import { createDefaultActionRegistry } from './actions/registry';
import { createClaudeCliSendExecutor } from './actions/claudeCliSend';
import { createFileTradingAdapter } from './trading/fileAdapter';
import { GoogleAuthManager } from './google/oauth';
import { GmailClient } from './google/gmail';
import { CalendarClient } from './google/calendar';
import { createGoogleExecutors } from './actions/googleActions';
import { registerGoogleRoutes } from './routes/google';
import { RuleBasedRouter } from './orchestration/router';
import { runAssistantRequest } from './orchestration/assistant';
import { sendError } from './security/errors';

export interface BuildAppResult {
  app: FastifyInstance;
  repos: Repositories;
  provider: ModelProvider;
}

export function buildApp(
  config: ServerConfig,
  overrides: { provider?: ModelProvider; claudeCli?: ClaudeCliProvider } = {},
): BuildAppResult {
  const db = openDatabase(config.dataDir);
  runMigrations(db);
  const repos = createRepositories(db);
  seedDatabase(repos);
  const setup = createProviderSetup(config);
  const provider = overrides.provider ?? setup.provider;
  const router = new RuleBasedRouter();
  const actionRegistry = createDefaultActionRegistry();
  const claudeCli = overrides.claudeCli ?? (overrides.provider ? null : setup.claudeCli);
  if (claudeCli) {
    actionRegistry.register(createClaudeCliSendExecutor(repos, claudeCli));
  }

  // Google (Gmail + Calendar): official OAuth, tokens in the gitignored data
  // dir. Executors only exist behind the approval system.
  const googleAuth = new GoogleAuthManager(
    config.googleClientId,
    config.googleClientSecret,
    config.dataDir,
    `http://${config.host}:${config.port}/api/google/oauth/callback`,
  );
  const gmail = new GmailClient(googleAuth);
  const calendar = new CalendarClient(googleAuth);
  for (const executor of createGoogleExecutors(gmail, calendar)) {
    actionRegistry.register(executor);
  }

  const app = Fastify({
    logger: false,
    bodyLimit: 64 * 1024, // sensible request-body limit for a local prototype
  });

  app.addHook('onClose', async () => {
    db.close();
  });

  // Local-API hardening: browsers attach Origin to cross-site requests and
  // Host to everything. Rejecting foreign origins blocks CSRF against this
  // powerful local API; rejecting foreign hosts blocks DNS-rebinding. The
  // Vite dev server (5173) is the only additional allowed origin.
  const loopbackHost = /^(127\.0\.0\.1|localhost|\[::1\])(:\d+)?$/i;
  const allowedOrigins = new Set([
    `http://127.0.0.1:${config.port}`,
    `http://localhost:${config.port}`,
    'http://127.0.0.1:5173',
    'http://localhost:5173',
  ]);
  app.addHook('onRequest', async (request, reply) => {
    if (!request.url.startsWith('/api/')) return;
    const host = request.headers.host ?? '';
    if (!loopbackHost.test(host)) {
      return sendError(reply, 403, 'forbidden_host', 'This API only accepts local requests.');
    }
    const origin = request.headers.origin;
    if (origin && !allowedOrigins.has(origin.toLowerCase())) {
      return sendError(reply, 403, 'forbidden_origin', 'Cross-origin requests are not allowed.');
    }
  });

  // Normalized safe errors; no stack traces reach the browser in production.
  app.setErrorHandler((error: unknown, _request, reply) => {
    const err = error as { statusCode?: number; message?: string };
    const status = err.statusCode && err.statusCode >= 400 ? err.statusCode : 500;
    const message =
      config.isProduction && status >= 500
        ? 'Internal server error'
        : (err.message ?? 'Internal server error');
    void sendError(reply, status, status >= 500 ? 'internal_error' : 'request_error', message);
  });

  app.get('/api/health', async () => {
    return healthResponseSchema.parse({
      status: 'ok',
      appVersion: APP_VERSION,
      schemaVersion: currentSchemaVersion(db),
      time: new Date().toISOString(),
    });
  });

  app.get('/api/bootstrap', async () => {
    const conversation = repos.conversations.findMostRecent();
    // Provider status derives from real configuration and never contains
    // secrets — validated against the shared schema on the way out.
    return bootstrapResponseSchema.parse({
      appVersion: APP_VERSION,
      schemaVersion: currentSchemaVersion(db),
      provider: provider.status(),
      activeProject: repos.projects.findActive(),
      conversation,
      messages: conversation ? repos.conversations.listMessages(conversation.id, 50) : [],
      settings: repos.settings.get(),
      pendingActions: repos.pendingActions.listPending(),
    });
  });

  app.post('/api/assistant/stream', async (request, reply) => {
    const parsed = assistantRequestSchema.safeParse(request.body);
    if (!parsed.success) {
      const issue = parsed.error.issues[0];
      return sendError(reply, 400, 'invalid_request', issue?.message ?? 'Invalid request');
    }

    const stream = new PassThrough();
    const abort = new AbortController();
    // Cancel on real client disconnect only. IncomingMessage 'close' fires on
    // normal request completion in modern Node, which would abort every
    // request before the provider runs — the socket closes only when the
    // client actually goes away (tab closed, fetch aborted, Esc interrupt).
    const socket = request.raw.socket;
    const onSocketClose = () => abort.abort();
    socket.once('close', onSocketClose);

    void reply
      .header('content-type', 'application/x-ndjson')
      .header('cache-control', 'no-store')
      .send(stream);

    try {
      await runAssistantRequest(
        { repos, provider, router },
        {
          input: parsed.data.input,
          conversationId: parsed.data.conversationId,
          signal: abort.signal,
        },
        (event) => {
          stream.write(`${JSON.stringify(event)}\n`);
        },
      );
    } finally {
      socket.off('close', onSocketClose);
      stream.end();
    }
    return reply;
  });

  app.get('/api/memories', async (request) => {
    const { q } = request.query as { q?: string };
    const memories =
      q && q.trim().length > 0 ? repos.memories.search(q.trim()) : repos.memories.listActive();
    return { memories };
  });

  app.post('/api/memories', async (request, reply) => {
    const parsed = createMemoryRequestSchema.safeParse(request.body);
    if (!parsed.success) {
      return sendError(reply, 400, 'invalid_request', 'Invalid memory payload');
    }
    const duplicate = repos.memories.findActiveDuplicate(parsed.data.value);
    if (duplicate && !parsed.data.allowDuplicate) {
      return sendError(
        reply,
        409,
        'duplicate_memory',
        `A memory with the same content already exists: "${duplicate.value}"`,
      );
    }
    // Sensitive content is never stored silently — the owner must confirm.
    const sensitiveMatch = detectSensitive(parsed.data.value);
    if (sensitiveMatch && !parsed.data.confirmSensitive) {
      return sendError(
        reply,
        409,
        'sensitive_confirmation_required',
        `This looks sensitive (${sensitiveMatch.reason}). Confirm before JARVIS stores it.`,
      );
    }
    const memory = repos.memories.create({
      kind: parsed.data.kind,
      value: parsed.data.value,
      memoryKey: parsed.data.memoryKey ?? null,
      tags: parsed.data.tags ?? [],
      projectId: parsed.data.projectId ?? null,
      source: 'user_explicit',
      sourceDetail: 'memory panel',
      sensitive: sensitiveMatch !== null,
    });
    return reply.status(201).send({ memory });
  });

  app.patch('/api/memories/:id', async (request, reply) => {
    const { id } = request.params as { id: string };
    const parsed = updateMemoryRequestSchema.safeParse(request.body);
    if (!parsed.success) {
      return sendError(reply, 400, 'invalid_request', 'Invalid memory update');
    }
    const memory = repos.memories.update(id, parsed.data);
    if (!memory) {
      return sendError(reply, 404, 'not_found', 'Memory not found or archived');
    }
    return { memory };
  });

  // DELETE archives — "forget" never destroys historical references.
  app.delete('/api/memories/:id', async (request, reply) => {
    const { id } = request.params as { id: string };
    const existing = repos.memories.findById(id);
    if (!existing) {
      return sendError(reply, 404, 'not_found', 'Memory not found');
    }
    const memory = repos.memories.archive(id);
    return { memory };
  });

  // ---- Project inspection (read-only, owner-registered directories) ----

  app.get('/api/projects/registered', async () => {
    return { projects: repos.registeredProjects.listActive() };
  });

  app.post('/api/projects/register', async (request, reply) => {
    const body = (request.body ?? {}) as { path?: string; name?: string };
    const validation = validateProjectRoot(body.path ?? '');
    if (!validation.ok) {
      return sendError(reply, 400, 'invalid_project_path', validation.message);
    }
    const existing = repos.registeredProjects.findByPath(validation.root);
    if (existing && !existing.archivedAt) {
      return sendError(reply, 409, 'already_registered', 'That directory is already registered.');
    }
    const profile = await buildProjectProfile(validation.root);
    const name =
      (body.name ?? '').trim() || path.basename(validation.root) || validation.root;
    const project = existing
      ? repos.registeredProjects.updateProfile(existing.id, profile)
      : repos.registeredProjects.create({ name, rootPath: validation.root, profile });
    return reply.status(existing ? 200 : 201).send({ project });
  });

  app.post('/api/projects/registered/:id/refresh', async (request, reply) => {
    const { id } = request.params as { id: string };
    const existing = repos.registeredProjects.findById(id);
    if (!existing || existing.archivedAt) {
      return sendError(reply, 404, 'not_found', 'Registered project not found');
    }
    const validation = validateProjectRoot(existing.rootPath);
    if (!validation.ok) {
      return sendError(
        reply,
        409,
        'project_path_missing',
        `The registered directory is no longer readable: ${validation.message}`,
      );
    }
    const profile = await buildProjectProfile(validation.root);
    return { project: repos.registeredProjects.updateProfile(id, profile) };
  });

  app.delete('/api/projects/registered/:id', async (request, reply) => {
    const { id } = request.params as { id: string };
    const existing = repos.registeredProjects.findById(id);
    if (!existing) return sendError(reply, 404, 'not_found', 'Registered project not found');
    return { project: repos.registeredProjects.archive(id) };
  });

  app.put('/api/settings', async (request, reply) => {
    const parsed = updateSettingsRequestSchema.safeParse(request.body);
    if (!parsed.success) {
      return sendError(reply, 400, 'invalid_request', 'Invalid settings payload');
    }
    return { settings: repos.settings.update(parsed.data) };
  });

  app.post('/api/actions/:actionId/decision', async (request, reply) => {
    const { actionId } = request.params as { actionId: string };
    const parsed = actionDecisionRequestSchema.safeParse(request.body);
    if (!parsed.success) {
      return sendError(reply, 400, 'invalid_request', 'Decision must be "approve" or "cancel"');
    }
    // The stored payload is authoritative; the client cannot substitute one.
    // "local-owner" is a local actor label — no authentication exists, so
    // this is a local event history, not a production audit trail.
    const outcome = repos.pendingActions.decide(actionId, parsed.data.decision, 'local-owner');
    if (!outcome.ok) {
      switch (outcome.reason) {
        case 'not_found':
          return sendError(reply, 404, 'not_found', 'Action not found');
        case 'expired':
          return sendError(reply, 410, 'action_expired', 'This action has expired');
        case 'already_decided':
          return sendError(reply, 409, 'already_decided', 'This action was already decided');
      }
    }
    if (outcome.action.status !== 'approved') {
      return { action: outcome.action }; // cancelled — nothing executes
    }

    // Approval applies to exactly this action; execution happens exactly
    // once, and a missing or failing executor is recorded honestly.
    const executor = actionRegistry.get(outcome.action.actionType);
    if (!executor) {
      const failed = repos.pendingActions.recordExecution(actionId, {
        status: 'failed',
        error: `No executor is enabled for "${outcome.action.actionType}". Nothing was done.`,
      });
      return { action: failed ?? outcome.action };
    }
    try {
      const result = await executor.execute(outcome.action);
      const executed = repos.pendingActions.recordExecution(actionId, { status: result.status });
      return { action: executed ?? outcome.action };
    } catch (error) {
      // Only known, safe error types surface their message; anything else
      // gets a generic line (never a stack trace).
      const SAFE_ERROR_NAMES = new Set([
        'ActionExecutionError',
        'GoogleAuthError',
        'GmailError',
        'CalendarError',
        'ModelProviderError',
      ]);
      const failed = repos.pendingActions.recordExecution(actionId, {
        status: 'failed',
        error:
          error instanceof Error && SAFE_ERROR_NAMES.has(error.name)
            ? error.message
            : 'The action failed while executing. Nothing may have been changed — check the target.',
      });
      return { action: failed ?? outcome.action };
    }
  });

  registerGoogleRoutes(app, { auth: googleAuth, gmail, calendar, repos, provider });

  // Trading-bot monitoring (read-only; no execution path exists).
  const tradingAdapter = createFileTradingAdapter(config.tradingReportPath);
  app.get('/api/trading/status', async () => {
    return await tradingAdapter.fetchStatus();
  });

  // Unified action audit trail (pending, executed, failed, cancelled, expired).
  app.get('/api/actions', async (request, reply) => {
    const { status, limit } = request.query as { status?: string; limit?: string };
    const parsedStatus = status ? pendingActionStatusSchema.safeParse(status) : undefined;
    if (parsedStatus && !parsedStatus.success) {
      return sendError(reply, 400, 'invalid_request', 'Unknown action status filter');
    }
    const parsedLimit = Math.min(Math.max(Number(limit ?? 50) || 50, 1), 200);
    return {
      actions: repos.pendingActions.listHistory(parsedLimit, parsedStatus?.data),
    };
  });

  // Production: serve the built client from Fastify.
  if (config.isProduction) {
    const clientDir = path.resolve(process.cwd(), 'dist/client');
    if (fs.existsSync(clientDir)) {
      void app.register(fastifyStatic, { root: clientDir });
      app.setNotFoundHandler((request, reply) => {
        if (request.url.startsWith('/api/')) {
          void sendError(reply, 404, 'not_found', 'Unknown API route');
          return;
        }
        void reply.sendFile('index.html');
      });
    }
  }

  return { app, repos, provider };
}
