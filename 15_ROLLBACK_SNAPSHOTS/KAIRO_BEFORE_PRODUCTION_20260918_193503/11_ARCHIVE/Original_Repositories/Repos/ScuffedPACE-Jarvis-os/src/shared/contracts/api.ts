import { z } from 'zod';
import { MAX_INPUT_LENGTH } from '../constants';
import {
  conversationSchema,
  memoryKindSchema,
  memorySchema,
  messageSchema,
  pendingActionSchema,
  projectSchema,
  settingsSchema,
} from '../schemas/entities';

/** Normalized error shape returned by every API failure. Never a stack trace. */
export const apiErrorSchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
  }),
});

export const healthResponseSchema = z.object({
  status: z.literal('ok'),
  appVersion: z.string(),
  schemaVersion: z.number().int(),
  time: z.string(),
});

/**
 * Provider status shown in the UI. Derived from real configuration — the UI
 * must never claim Claude is connected while the mock provider is active.
 * Never contains the API key or any secret.
 */
export const providerStatusSchema = z.object({
  mode: z.enum(['mock', 'anthropic', 'ollama', 'claude_cli']),
  label: z.string(),
  configured: z.boolean(),
  configurationError: z.string().nullable(),
  fastModel: z.string().nullable(),
  deepModel: z.string().nullable(),
});

export const speechSupportNoteSchema = z.object({
  // Speech feature detection happens in the browser; the server only reports
  // that voice features are client-side and optional.
  note: z.string(),
});

export const bootstrapResponseSchema = z.object({
  appVersion: z.string(),
  schemaVersion: z.number().int(),
  provider: providerStatusSchema,
  activeProject: projectSchema.nullable(),
  conversation: conversationSchema.nullable(),
  messages: z.array(messageSchema),
  settings: settingsSchema,
  pendingActions: z.array(pendingActionSchema),
});

export const assistantRequestSchema = z.object({
  input: z.string().trim().min(1, 'Request must not be empty').max(MAX_INPUT_LENGTH),
  conversationId: z.string().uuid().optional(),
});

export const createMemoryRequestSchema = z.object({
  kind: memoryKindSchema,
  value: z.string().trim().min(1).max(2000),
  memoryKey: z.string().trim().min(1).max(200).optional(),
  tags: z.array(z.string().trim().min(1).max(50)).max(10).optional(),
  projectId: z.string().uuid().nullable().optional(),
  /** Required true to save content the sensitive-data detector flags. */
  confirmSensitive: z.boolean().optional(),
  /** Required true to save a value that duplicates an active memory. */
  allowDuplicate: z.boolean().optional(),
});

export const updateMemoryRequestSchema = z
  .object({
    value: z.string().trim().min(1).max(2000).optional(),
    kind: memoryKindSchema.optional(),
    tags: z.array(z.string().trim().min(1).max(50)).max(10).optional(),
  })
  .refine((patch) => Object.keys(patch).length > 0, { message: 'Empty update' });

export const listMemoriesResponseSchema = z.object({
  memories: z.array(memorySchema),
});

export const updateSettingsRequestSchema = settingsSchema.partial();

export const settingsResponseSchema = z.object({ settings: settingsSchema });

export const actionDecisionRequestSchema = z.object({
  decision: z.enum(['approve', 'cancel']),
});

export const actionDecisionResponseSchema = z.object({
  action: pendingActionSchema,
});

export type ApiError = z.infer<typeof apiErrorSchema>;
export type HealthResponse = z.infer<typeof healthResponseSchema>;
export type ProviderStatus = z.infer<typeof providerStatusSchema>;
export type BootstrapResponse = z.infer<typeof bootstrapResponseSchema>;
export type AssistantRequest = z.infer<typeof assistantRequestSchema>;
export type CreateMemoryRequest = z.infer<typeof createMemoryRequestSchema>;
export type ActionDecisionRequest = z.infer<typeof actionDecisionRequestSchema>;
