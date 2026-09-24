import { z } from 'zod';

export const intentSchema = z.enum(['chat', 'project', 'tool', 'deep_reasoning', 'memory']);
export const specialistSchema = z.enum(['general', 'project', 'mail', 'research', 'memory']);
export const executionSchema = z.enum(['direct', 'model', 'mock_tool', 'memory_write']);
export const riskSchema = z.enum(['none', 'reversible', 'consequential']);

/**
 * User-safe, enumerated classification reasons. These are concise labels for
 * why the router chose a path — never hidden chain-of-thought.
 */
export const reasonCodeSchema = z.enum([
  'project_planning_keywords',
  'mail_draft_request',
  'explicit_memory_request',
  'deep_analysis_keywords',
  'general_chat_fallback',
]);

export const routeResultSchema = z.object({
  schemaVersion: z.literal(1),
  requestId: z.string().uuid(),
  intent: intentSchema,
  specialist: specialistSchema,
  execution: executionSchema,
  risk: riskSchema,
  requiresApproval: z.boolean(),
  confidence: z.number().min(0).max(1),
  reasonCode: reasonCodeSchema,
});

export type RouteResult = z.infer<typeof routeResultSchema>;
export type Intent = z.infer<typeof intentSchema>;
export type ReasonCode = z.infer<typeof reasonCodeSchema>;
