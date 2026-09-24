import type { PendingAction } from '../../shared/types';

/**
 * Unified action-safety layer. Every externally visible action flows through
 * a pending_actions record and is executed here only after an explicit,
 * single-use owner approval. There is no other execution path.
 *
 * Restricted categories (always approval-gated, never autonomous):
 * sending messages, deleting information, moving money, placing trades,
 * purchasing, publishing, changing security settings, and running terminal
 * commands. Action types in a restricted category with no registered
 * executor fail honestly instead of pretending to run.
 */

export type ActionCategory =
  | 'simulated'
  | 'send_message'
  | 'delete_data'
  | 'modify_external'
  | 'money_or_trading'
  | 'publish'
  | 'security_change'
  | 'run_command';

export interface ActionExecutionResult {
  status: 'simulated_completed' | 'completed';
  /** Safe, human-readable note about what actually happened. */
  detail?: string;
}

export interface ActionExecutor {
  actionType: string;
  category: ActionCategory;
  execute(action: PendingAction): Promise<ActionExecutionResult>;
}

export class ActionExecutionError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ActionExecutionError';
  }
}

export class ActionRegistry {
  private readonly executors = new Map<string, ActionExecutor>();

  register(executor: ActionExecutor): void {
    if (this.executors.has(executor.actionType)) {
      throw new Error(`Executor already registered for ${executor.actionType}`);
    }
    this.executors.set(executor.actionType, executor);
  }

  get(actionType: string): ActionExecutor | null {
    return this.executors.get(actionType) ?? null;
  }
}

/** The simulated mail send from the MVP: records an approval, sends nothing. */
export const simulatedSendExecutor: ActionExecutor = {
  actionType: 'simulated_send',
  category: 'simulated',
  async execute(): Promise<ActionExecutionResult> {
    // Nothing external happens by design — the record itself is the outcome.
    return { status: 'simulated_completed', detail: 'Simulated send recorded; nothing was sent.' };
  },
};

export function createDefaultActionRegistry(): ActionRegistry {
  const registry = new ActionRegistry();
  registry.register(simulatedSendExecutor);
  return registry;
}
