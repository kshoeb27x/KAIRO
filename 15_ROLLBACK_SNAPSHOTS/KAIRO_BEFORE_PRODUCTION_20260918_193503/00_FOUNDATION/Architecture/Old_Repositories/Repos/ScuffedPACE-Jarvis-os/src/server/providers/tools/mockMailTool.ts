import type { MailDraft } from '../../../shared/types';
import type { MailToolResult, ToolAdapter, ToolContext } from './types';

/**
 * Simulated mail tool. Produces a deterministic draft from the request text.
 * Nothing is ever sent externally — approval only records a
 * `simulated_completed` decision.
 */
export class MockMailTool implements ToolAdapter<string, MailToolResult> {
  readonly name = 'mock_mail';
  readonly simulated = true;

  async run(input: string, context: ToolContext): Promise<MailToolResult> {
    const draft = composeDraft(input, context);
    return {
      draft,
      summary: `Draft prepared for ${draft.to} (simulated — nothing sent)`,
    };
  }
}

function composeDraft(input: string, context: ToolContext): MailDraft {
  const lower = input.toLowerCase();
  const project = context.projectName ?? 'the project';

  let body: string;
  if (lower.includes('ready tomorrow') || lower.includes('will be ready tomorrow')) {
    body =
      `Hi,\n\nQuick update on ${project}: the prototype is on track and will be ready tomorrow. ` +
      `I'll share it as soon as it's up.\n\nBest,\n${context.ownerName}`;
  } else {
    body =
      `Hi,\n\nUpdate on ${project}: ${input.trim()}\n\nBest,\n${context.ownerName}`;
  }

  return {
    to: 'collaborator@example.com (demo recipient)',
    subject: `${project} — update`,
    body,
  };
}
