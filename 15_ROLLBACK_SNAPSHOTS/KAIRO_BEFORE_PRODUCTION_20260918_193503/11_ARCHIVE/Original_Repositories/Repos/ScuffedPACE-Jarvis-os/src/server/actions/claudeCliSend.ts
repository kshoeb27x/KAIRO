import { z } from 'zod';
import type { Repositories } from '../repositories';
import type { ClaudeCliProvider } from '../providers/model';
import { ActionExecutionError, type ActionExecutor } from './registry';

const payloadSchema = z.object({
  _system: z.string(),
  _messages: z.array(z.object({ role: z.enum(['user', 'assistant']), content: z.string() })),
  _tier: z.enum(['fast', 'deep']),
  _conversationId: z.string().uuid(),
});

/**
 * Executes an approved "send project context to the local Claude CLI"
 * action: runs the CLI with exactly the stored context (the client cannot
 * substitute a different one) and appends the reply to the conversation.
 */
export function createClaudeCliSendExecutor(
  repos: Repositories,
  claudeCli: ClaudeCliProvider,
): ActionExecutor {
  return {
    actionType: 'claude_cli_context_send',
    category: 'send_message',
    async execute(action) {
      const parsed = payloadSchema.safeParse(action.payload);
      if (!parsed.success) {
        throw new ActionExecutionError('The stored action context is invalid; nothing was sent.');
      }
      const result = await claudeCli.complete({
        system: parsed.data._system,
        messages: parsed.data._messages,
        tier: parsed.data._tier,
      });
      repos.conversations.addMessage({
        conversationId: parsed.data._conversationId,
        role: 'assistant',
        content: result.text,
        provider: result.provider,
        model: result.model,
      });
      return { status: 'completed', detail: 'Claude CLI reply added to the conversation.' };
    },
  };
}
