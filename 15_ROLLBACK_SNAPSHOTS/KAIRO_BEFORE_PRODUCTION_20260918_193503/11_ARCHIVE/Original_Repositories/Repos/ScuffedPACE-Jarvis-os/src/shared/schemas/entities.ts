import { z } from 'zod';

const isoTimestamp = z.string();

export const projectSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  summary: z.string(),
  status: z.enum(['active', 'paused', 'done']),
  isActive: z.boolean(),
  createdAt: isoTimestamp,
  updatedAt: isoTimestamp,
  archivedAt: isoTimestamp.nullable(),
});

export const messageRoleSchema = z.enum(['user', 'assistant']);

export const messageSchema = z.object({
  id: z.string().uuid(),
  conversationId: z.string().uuid(),
  role: messageRoleSchema,
  content: z.string(),
  provider: z.string().nullable(),
  model: z.string().nullable(),
  createdAt: isoTimestamp,
});

export const conversationSchema = z.object({
  id: z.string().uuid(),
  projectId: z.string().uuid().nullable(),
  title: z.string(),
  summary: z.string().nullable(),
  createdAt: isoTimestamp,
  updatedAt: isoTimestamp,
  archivedAt: isoTimestamp.nullable(),
});

export const memoryKindSchema = z.enum([
  'preference',
  'personal_fact',
  'project_fact',
  'fact',
  'decision',
  'task',
  'lesson',
  'working_context',
  'note',
]);
export const memorySourceSchema = z.enum([
  'user_explicit',
  'owner_confirmed',
  'model_inferred',
  'integration',
  'seed',
]);

export const memorySchema = z.object({
  id: z.string().uuid(),
  kind: memoryKindSchema,
  memoryKey: z.string().nullable(),
  value: z.string(),
  tags: z.array(z.string()),
  source: memorySourceSchema,
  /** Human-readable origin, e.g. "conversation" or "memory panel". */
  sourceDetail: z.string().nullable(),
  /** Owner-confirmed sensitive content — never saved without confirmation. */
  sensitive: z.boolean(),
  projectId: z.string().uuid().nullable(),
  createdAt: isoTimestamp,
  updatedAt: isoTimestamp,
  archivedAt: isoTimestamp.nullable(),
});

export const mailDraftSchema = z.object({
  to: z.string(),
  subject: z.string(),
  body: z.string(),
});

export const pendingActionStatusSchema = z.enum([
  'pending',
  'approved',
  'simulated_completed',
  'completed',
  'failed',
  'cancelled',
  'expired',
]);

/** Generic action payload; each executor validates its own shape. */
export const actionPayloadSchema = z.record(z.string(), z.unknown());

export const pendingActionSchema = z.object({
  id: z.string().uuid(),
  requestId: z.string().uuid(),
  toolName: z.string(),
  actionType: z.string(),
  payload: actionPayloadSchema,
  /** One-line human description of exactly what will happen. */
  summary: z.string(),
  /** Affected account, project, or system. */
  target: z.string(),
  /** Why JARVIS proposed this action. */
  reason: z.string(),
  /** Possible consequences the owner should weigh. */
  consequences: z.string(),
  status: pendingActionStatusSchema,
  expiresAt: isoTimestamp,
  createdAt: isoTimestamp,
  decidedAt: isoTimestamp.nullable(),
  decidedBy: z.string().nullable(),
  executedAt: isoTimestamp.nullable(),
  executionError: z.string().nullable(),
});

export const explanationDepthSchema = z.enum(['simple', 'normal', 'technical']);

export const settingsSchema = z.object({
  autoSpeak: z.boolean(),
  voiceUri: z.string().nullable(),
  /** Spoken response rate (0.5–2, browser speechSynthesis range). */
  speechRate: z.number().min(0.5).max(2),
  explanationDepth: explanationDepthSchema,
});

export const defaultSettings: Settings = {
  autoSpeak: true,
  voiceUri: null,
  speechRate: 1,
  explanationDepth: 'normal',
};

export type Project = z.infer<typeof projectSchema>;
export type Message = z.infer<typeof messageSchema>;
export type MessageRole = z.infer<typeof messageRoleSchema>;
export type Conversation = z.infer<typeof conversationSchema>;
export type Memory = z.infer<typeof memorySchema>;
export type MemoryKind = z.infer<typeof memoryKindSchema>;
export type MailDraft = z.infer<typeof mailDraftSchema>;
export type PendingAction = z.infer<typeof pendingActionSchema>;
export type PendingActionStatus = z.infer<typeof pendingActionStatusSchema>;
export type Settings = z.infer<typeof settingsSchema>;
export type ExplanationDepth = z.infer<typeof explanationDepthSchema>;
