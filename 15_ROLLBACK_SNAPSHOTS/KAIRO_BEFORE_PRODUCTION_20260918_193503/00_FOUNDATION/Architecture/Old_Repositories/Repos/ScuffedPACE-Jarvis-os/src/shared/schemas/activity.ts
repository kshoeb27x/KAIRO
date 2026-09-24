import { z } from 'zod';
import { routeResultSchema } from './route';
import { messageSchema, pendingActionSchema } from './entities';

/**
 * Every event streamed over /api/assistant/stream is one of these envelopes,
 * serialized as one JSON object per line (NDJSON). Events are emitted only
 * when the corresponding operation actually occurred.
 */

const envelopeBase = {
  schemaVersion: z.literal(1),
  requestId: z.string().uuid(),
  eventId: z.string().uuid(),
  occurredAt: z.string(),
  /** Safe, user-facing label rendered in the activity rail. */
  label: z.string(),
};

export const activityEventSchema = z.discriminatedUnion('eventType', [
  z.object({
    ...envelopeBase,
    eventType: z.literal('request.accepted'),
    payload: z.object({
      conversationId: z.string().uuid(),
      inputPreview: z.string(),
    }),
  }),
  z.object({
    ...envelopeBase,
    eventType: z.literal('memory.loaded'),
    payload: z.object({
      memoryCount: z.number().int().nonnegative(),
      projectName: z.string().nullable(),
    }),
  }),
  z.object({
    ...envelopeBase,
    eventType: z.literal('route.selected'),
    payload: z.object({ route: routeResultSchema }),
  }),
  z.object({
    ...envelopeBase,
    eventType: z.literal('model.started'),
    payload: z.object({
      provider: z.string(),
      model: z.string(),
      simulated: z.boolean(),
    }),
  }),
  z.object({
    ...envelopeBase,
    eventType: z.literal('tool.started'),
    payload: z.object({ tool: z.string(), simulated: z.boolean() }),
  }),
  z.object({
    ...envelopeBase,
    eventType: z.literal('tool.completed'),
    payload: z.object({
      tool: z.string(),
      simulated: z.boolean(),
      summary: z.string(),
    }),
  }),
  z.object({
    ...envelopeBase,
    eventType: z.literal('permission.required'),
    payload: z.object({
      actionId: z.string().uuid(),
      actionType: z.string(),
      tool: z.string(),
      expiresAt: z.string(),
      action: pendingActionSchema,
    }),
  }),
  z.object({
    ...envelopeBase,
    eventType: z.literal('memory.saved'),
    payload: z.object({
      memoryId: z.string().uuid(),
      memoryKey: z.string().nullable(),
    }),
  }),
  z.object({
    ...envelopeBase,
    eventType: z.literal('response.completed'),
    payload: z.object({ message: messageSchema }),
  }),
  z.object({
    ...envelopeBase,
    eventType: z.literal('request.failed'),
    payload: z.object({
      errorCode: z.string(),
      message: z.string(),
      recoverable: z.boolean(),
    }),
  }),
]);

export type ActivityEvent = z.infer<typeof activityEventSchema>;
export type ActivityEventType = ActivityEvent['eventType'];
