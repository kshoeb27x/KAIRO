import { z } from 'zod';
import type { GmailClient } from '../google/gmail';
import type { CalendarClient } from '../google/calendar';
import { ActionExecutionError, type ActionExecutor } from './registry';

/**
 * Approval-gated Google executors. Each runs only after an explicit,
 * single-use owner approval of the exact stored payload; failures surface
 * honestly (the action record shows failed + reason, never fake success).
 */

const sendPayload = z.object({
  to: z.string().min(3),
  subject: z.string(),
  body: z.string().min(1),
  inReplyToMessageId: z.string().optional(),
  threadId: z.string().optional(),
});

const messageIdPayload = z.object({ messageId: z.string().min(1) });

const createEventPayload = z.object({
  summary: z.string().min(1),
  startIso: z.string().min(4),
  endIso: z.string().min(4),
  location: z.string().optional(),
  description: z.string().optional(),
  attendees: z.array(z.string()).max(20).optional(),
});

const updateEventPayload = z.object({
  eventId: z.string().min(1),
  summary: z.string().optional(),
  startIso: z.string().optional(),
  endIso: z.string().optional(),
  location: z.string().optional(),
});

const eventIdPayload = z.object({ eventId: z.string().min(1) });

const respondPayload = z.object({
  eventId: z.string().min(1),
  response: z.enum(['accepted', 'declined', 'tentative']),
});

function parsedOrThrow<T>(schema: z.ZodType<T>, payload: unknown): T {
  const parsed = schema.safeParse(payload);
  if (!parsed.success) {
    throw new ActionExecutionError('The stored action payload is invalid; nothing was done.');
  }
  return parsed.data;
}

export function createGoogleExecutors(
  gmail: GmailClient,
  calendar: CalendarClient,
): ActionExecutor[] {
  return [
    {
      actionType: 'email_send',
      category: 'send_message',
      async execute(action) {
        const input = parsedOrThrow(sendPayload, action.payload);
        await gmail.sendMessage(input);
        return { status: 'completed', detail: `Email sent to ${input.to}.` };
      },
    },
    {
      actionType: 'email_archive',
      category: 'modify_external',
      async execute(action) {
        const input = parsedOrThrow(messageIdPayload, action.payload);
        await gmail.archiveMessage(input.messageId);
        return { status: 'completed', detail: 'Message archived (removed from inbox).' };
      },
    },
    {
      actionType: 'email_delete',
      category: 'delete_data',
      async execute(action) {
        const input = parsedOrThrow(messageIdPayload, action.payload);
        await gmail.trashMessage(input.messageId);
        return { status: 'completed', detail: 'Message moved to trash.' };
      },
    },
    {
      actionType: 'calendar_create',
      category: 'modify_external',
      async execute(action) {
        const input = parsedOrThrow(createEventPayload, action.payload);
        const created = await calendar.createEvent(input);
        return { status: 'completed', detail: `Event created (${created.id}).` };
      },
    },
    {
      actionType: 'calendar_update',
      category: 'modify_external',
      async execute(action) {
        const input = parsedOrThrow(updateEventPayload, action.payload);
        await calendar.updateEvent(input.eventId, input);
        return { status: 'completed', detail: 'Event updated.' };
      },
    },
    {
      actionType: 'calendar_delete',
      category: 'delete_data',
      async execute(action) {
        const input = parsedOrThrow(eventIdPayload, action.payload);
        await calendar.deleteEvent(input.eventId);
        return { status: 'completed', detail: 'Event deleted.' };
      },
    },
    {
      actionType: 'calendar_respond',
      category: 'send_message',
      async execute(action) {
        const input = parsedOrThrow(respondPayload, action.payload);
        await calendar.respondToEvent(input.eventId, input.response);
        return { status: 'completed', detail: `Invitation ${input.response}.` };
      },
    },
  ];
}
