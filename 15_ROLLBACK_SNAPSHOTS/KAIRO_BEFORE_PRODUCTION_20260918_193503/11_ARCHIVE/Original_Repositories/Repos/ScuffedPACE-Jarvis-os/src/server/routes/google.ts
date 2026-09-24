import type { FastifyInstance } from 'fastify';
import { z } from 'zod';
import { PENDING_ACTION_TTL_MS } from '../../shared/constants';
import type { Repositories } from '../repositories';
import type { ModelProvider } from '../providers/model';
import { ModelProviderError } from '../providers/model';
import { GoogleAuthError, type GoogleAuthManager } from '../google/oauth';
import type { GmailClient} from '../google/gmail';
import { GmailError } from '../google/gmail';
import type { CalendarClient} from '../google/calendar';
import { CalendarError, findConflicts, suggestFreeSlots } from '../google/calendar';
import { wrapUntrusted } from '../google/sanitize';
import { sendError } from '../security/errors';

export interface GoogleRouteDeps {
  auth: GoogleAuthManager;
  gmail: GmailClient;
  calendar: CalendarClient;
  repos: Repositories;
  provider: ModelProvider;
}

function friendly(error: unknown): { status: number; code: string; message: string } {
  if (error instanceof GoogleAuthError) {
    return { status: 409, code: 'google_not_connected', message: error.message };
  }
  if (error instanceof GmailError || error instanceof CalendarError) {
    return { status: 502, code: 'google_api_error', message: error.message };
  }
  if (error instanceof ModelProviderError) {
    return { status: 502, code: error.code, message: error.message };
  }
  return { status: 500, code: 'internal_error', message: 'The Google request failed unexpectedly.' };
}

export function registerGoogleRoutes(app: FastifyInstance, deps: GoogleRouteDeps): void {
  const { auth, gmail, calendar, repos, provider } = deps;

  // ---- Connection lifecycle ----

  app.get('/api/google/status', async () => auth.status());

  app.post('/api/google/connect', async (request, reply) => {
    const body = (request.body ?? {}) as { tier?: string };
    const tier = body.tier === 'actions' ? 'actions' : 'read';
    try {
      return { authUrl: auth.startAuth(tier), tier };
    } catch (error) {
      const f = friendly(error);
      return sendError(reply, 400, f.code, f.message);
    }
  });

  app.get('/api/google/oauth/callback', async (request, reply) => {
    const { code, state, error } = request.query as {
      code?: string;
      state?: string;
      error?: string;
    };
    let message: string;
    if (error || !code || !state) {
      message = `Google sign-in was cancelled or failed${error ? ` (${error})` : ''}. You can close this tab.`;
    } else {
      try {
        const tokens = await auth.completeAuth(code, state);
        message = `Connected as ${tokens.accountEmail ?? 'your Google account'}. You can close this tab and return to JARVIS.`;
      } catch (err) {
        message =
          err instanceof GoogleAuthError ? err.message : 'The Google sign-in could not be completed.';
      }
    }
    return reply
      .header('content-type', 'text/html; charset=utf-8')
      .send(
        `<!doctype html><meta charset="utf-8"><title>JARVIS — Google</title><body style="font-family:sans-serif;background:#0b1220;color:#dfe9f5;display:grid;place-items:center;height:100vh"><p>${message.replace(/</g, '&lt;')}</p></body>`,
      );
  });

  app.post('/api/google/disconnect', async () => {
    await auth.disconnect();
    return { disconnected: true };
  });

  // ---- Gmail (read-only) ----

  app.get('/api/mail/messages', async (request, reply) => {
    const { q, limit } = request.query as { q?: string; limit?: string };
    try {
      const messages = await gmail.listMessages({ query: q, limit: Number(limit) || undefined });
      return { messages, account: auth.status().accountEmail };
    } catch (error) {
      const f = friendly(error);
      return sendError(reply, f.status, f.code, f.message);
    }
  });

  app.get('/api/mail/messages/:id', async (request, reply) => {
    const { id } = request.params as { id: string };
    try {
      return { message: await gmail.getMessage(id) };
    } catch (error) {
      const f = friendly(error);
      return sendError(reply, f.status, f.code, f.message);
    }
  });

  // Model analysis of one message: summary, action extraction, or a reply
  // draft. Email text is wrapped as untrusted data — never as instructions.
  app.post('/api/mail/messages/:id/analyze', async (request, reply) => {
    const { id } = request.params as { id: string };
    const body = (request.body ?? {}) as { mode?: string; instruction?: string };
    const mode = ['summarize', 'extract', 'draft_reply'].includes(body.mode ?? '')
      ? (body.mode as 'summarize' | 'extract' | 'draft_reply')
      : 'summarize';
    try {
      const message = await gmail.getMessage(id);
      const instructions: Record<typeof mode, string> = {
        summarize:
          'Summarize this email in plain language: who it is from, what they want, and whether a reply seems needed.',
        extract:
          'List any dates, deadlines, commitments, tasks, or follow-ups in this email as short bullet lines. If there are none, say so.',
        draft_reply:
          `Draft a short, polite reply from Farhan.` +
          (body.instruction ? ` Guidance from Farhan (trusted): ${body.instruction.slice(0, 500)}` : '') +
          ' Reply with only the email body text.',
      };
      const result = await provider.complete({
        system:
          'You are JARVIS, analyzing an email for Farhan. Distinguish facts from your interpretation.\n\n' +
          wrapUntrusted('email', `From: ${message.from}\nSubject: ${message.subject}\n\n${message.text}`),
        messages: [{ role: 'user', content: instructions[mode] }],
        tier: 'fast',
        maxTokens: 700,
      });
      return { mode, text: result.text, provider: result.provider, simulated: result.simulated };
    } catch (error) {
      const f = friendly(error);
      return sendError(reply, f.status, f.code, f.message);
    }
  });

  // Approval-gated mail actions: this endpoint only *records a proposal*;
  // execution happens exclusively through the approval decision.
  app.post('/api/mail/actions', async (request, reply) => {
    const schema = z.discriminatedUnion('type', [
      z.object({
        type: z.literal('send'),
        to: z.string().min(3),
        subject: z.string().min(1),
        body: z.string().min(1).max(20000),
        inReplyToMessageId: z.string().optional(),
        threadId: z.string().optional(),
      }),
      z.object({ type: z.literal('archive'), messageId: z.string().min(1), subject: z.string().optional() }),
      z.object({ type: z.literal('delete'), messageId: z.string().min(1), subject: z.string().optional() }),
    ]);
    const parsed = schema.safeParse(request.body);
    if (!parsed.success) {
      return sendError(reply, 400, 'invalid_request', 'Invalid mail action payload');
    }
    const account = auth.status().accountEmail ?? 'your Gmail account';
    const input = parsed.data;
    const action =
      input.type === 'send'
        ? repos.pendingActions.create({
            requestId: crypto.randomUUID(),
            toolName: 'gmail',
            actionType: 'email_send',
            payload: {
              to: input.to,
              subject: input.subject,
              body: input.body,
              inReplyToMessageId: input.inReplyToMessageId,
              threadId: input.threadId,
            },
            summary: `Send an email to ${input.to}: "${input.subject}"`,
            target: account,
            reason: 'You prepared this email in the Mail panel.',
            consequences: 'The email is really sent from your account and cannot be unsent.',
            ttlMs: PENDING_ACTION_TTL_MS,
          })
        : repos.pendingActions.create({
            requestId: crypto.randomUUID(),
            toolName: 'gmail',
            actionType: input.type === 'archive' ? 'email_archive' : 'email_delete',
            payload: { messageId: input.messageId, subject: input.subject ?? '' },
            summary:
              input.type === 'archive'
                ? `Archive the email "${input.subject ?? input.messageId}"`
                : `Move the email "${input.subject ?? input.messageId}" to trash`,
            target: account,
            reason: 'You requested this from the Mail panel.',
            consequences:
              input.type === 'archive'
                ? 'The message leaves your inbox but stays searchable in All Mail.'
                : 'The message goes to Gmail trash (auto-deleted after ~30 days).',
            ttlMs: PENDING_ACTION_TTL_MS,
          });
    return reply.status(201).send({ action });
  });

  // ---- Calendar (read-only) ----

  app.get('/api/calendar/events', async (request, reply) => {
    const { from, to, q } = request.query as { from?: string; to?: string; q?: string };
    const fromIso = from ?? new Date().toISOString();
    const toIso = to ?? new Date(Date.now() + 7 * 24 * 3600 * 1000).toISOString();
    try {
      const events = await calendar.listEvents({ fromIso, toIso, query: q });
      return {
        events,
        conflicts: findConflicts(events).map(([a, b]) => ({
          first: a.summary,
          second: b.summary,
          start: b.start,
        })),
        account: auth.status().accountEmail,
      };
    } catch (error) {
      const f = friendly(error);
      return sendError(reply, f.status, f.code, f.message);
    }
  });

  app.get('/api/calendar/suggest', async (request, reply) => {
    const { from, to, minMinutes } = request.query as {
      from?: string;
      to?: string;
      minMinutes?: string;
    };
    const fromIso = from ?? new Date().toISOString();
    const toIso = to ?? new Date(Date.now() + 24 * 3600 * 1000).toISOString();
    try {
      const events = await calendar.listEvents({ fromIso, toIso });
      return { slots: suggestFreeSlots(events, fromIso, toIso, Number(minMinutes) || 30) };
    } catch (error) {
      const f = friendly(error);
      return sendError(reply, f.status, f.code, f.message);
    }
  });

  // Approval-gated calendar actions (proposal only; execution via approval).
  app.post('/api/calendar/actions', async (request, reply) => {
    const schema = z.discriminatedUnion('type', [
      z.object({
        type: z.literal('create'),
        summary: z.string().min(1),
        startIso: z.string().min(4),
        endIso: z.string().min(4),
        location: z.string().optional(),
        description: z.string().optional(),
        attendees: z.array(z.string()).max(20).optional(),
      }),
      z.object({
        type: z.literal('update'),
        eventId: z.string().min(1),
        eventSummary: z.string().optional(),
        summary: z.string().optional(),
        startIso: z.string().optional(),
        endIso: z.string().optional(),
        location: z.string().optional(),
      }),
      z.object({ type: z.literal('delete'), eventId: z.string().min(1), eventSummary: z.string().optional() }),
      z.object({
        type: z.literal('respond'),
        eventId: z.string().min(1),
        eventSummary: z.string().optional(),
        response: z.enum(['accepted', 'declined', 'tentative']),
      }),
    ]);
    const parsed = schema.safeParse(request.body);
    if (!parsed.success) {
      return sendError(reply, 400, 'invalid_request', 'Invalid calendar action payload');
    }
    const account = auth.status().accountEmail ?? 'your Google Calendar';
    const input = parsed.data;

    // Duplicate-event guard: same title overlapping the same time window.
    if (input.type === 'create') {
      try {
        const nearby = await calendar.listEvents({ fromIso: input.startIso, toIso: input.endIso });
        const duplicate = nearby.find(
          (e) => e.summary.trim().toLowerCase() === input.summary.trim().toLowerCase(),
        );
        if (duplicate) {
          return sendError(
            reply,
            409,
            'duplicate_event',
            `An event named "${duplicate.summary}" already overlaps that time.`,
          );
        }
      } catch {
        // If the check itself fails, the approval card still shows the details.
      }
    }

    const details: Record<string, { actionType: string; summary: string; consequences: string }> = {
      create: {
        actionType: 'calendar_create',
        summary:
          input.type === 'create'
            ? `Create "${input.summary}" from ${input.startIso} to ${input.endIso}${(input.attendees?.length ?? 0) > 0 ? ` with ${input.attendees!.length} attendee(s)` : ''}`
            : '',
        consequences:
          (input.type === 'create' && (input.attendees?.length ?? 0) > 0
            ? 'Invitations are emailed to the attendees. '
            : '') + 'The event appears in your real calendar.',
      },
      update: {
        actionType: 'calendar_update',
        summary: `Update the event "${(input as { eventSummary?: string }).eventSummary ?? (input as { eventId?: string }).eventId}"`,
        consequences: 'Attendees are notified of the change.',
      },
      delete: {
        actionType: 'calendar_delete',
        summary: `Delete the event "${(input as { eventSummary?: string }).eventSummary ?? (input as { eventId?: string }).eventId}"`,
        consequences: 'The event is removed and attendees are notified. This cannot be undone.',
      },
      respond: {
        actionType: 'calendar_respond',
        summary:
          input.type === 'respond'
            ? `Respond "${input.response}" to "${input.eventSummary ?? input.eventId}"`
            : '',
        consequences: 'The organizer sees your response.',
      },
    };
    const meta = details[input.type]!;
    const payload: Record<string, unknown> = { ...input };
    delete payload.type;
    const action = repos.pendingActions.create({
      requestId: crypto.randomUUID(),
      toolName: 'calendar',
      actionType: meta.actionType,
      payload,
      summary: meta.summary,
      target: account,
      reason: 'You requested this from the Calendar panel.',
      consequences: meta.consequences,
      ttlMs: PENDING_ACTION_TTL_MS,
    });
    return reply.status(201).send({ action });
  });
}
