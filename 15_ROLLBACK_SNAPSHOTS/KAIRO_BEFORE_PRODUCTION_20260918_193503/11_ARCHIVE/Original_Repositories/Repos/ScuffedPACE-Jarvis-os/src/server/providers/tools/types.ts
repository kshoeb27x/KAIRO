import type { MailDraft } from '../../../shared/types';

export interface ToolContext {
  projectName: string | null;
  ownerName: string;
}

export interface MailToolResult {
  draft: MailDraft;
  summary: string;
}

/**
 * Tool adapter boundary. MVP tools are simulated and must say so — the
 * `simulated` flag flows into every activity event and UI label.
 */
export interface ToolAdapter<TInput, TResult> {
  readonly name: string;
  readonly simulated: boolean;
  run(input: TInput, context: ToolContext): Promise<TResult>;
}
