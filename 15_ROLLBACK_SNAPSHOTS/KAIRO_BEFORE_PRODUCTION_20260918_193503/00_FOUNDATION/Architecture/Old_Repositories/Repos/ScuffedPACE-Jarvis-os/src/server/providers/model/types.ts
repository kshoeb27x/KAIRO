import type { ProviderStatus } from '../../../shared/types';

export type ModelTier = 'fast' | 'deep';

export interface ModelCompletionRequest {
  /** JARVIS response instruction + selected context. Never contains secrets. */
  system: string;
  messages: Array<{ role: 'user' | 'assistant'; content: string }>;
  tier: ModelTier;
  maxTokens?: number;
  signal?: AbortSignal;
  /**
   * Structured hints used only by the mock provider to produce honest,
   * context-aware demo responses. Real providers ignore this.
   */
  demoContext?: {
    intent: string;
    projectName?: string | null;
    projectSummary?: string | null;
  };
}

export interface ModelCompletionResult {
  text: string;
  provider: string;
  model: string;
  /** True when no real model produced this text. */
  simulated: boolean;
}

export type ModelErrorCode =
  | 'not_configured'
  | 'authentication'
  | 'rate_limited'
  | 'timeout'
  | 'network'
  | 'api_error'
  | 'cancelled';

/** Normalized, safe-to-display model failure. Never includes secrets. */
export class ModelProviderError extends Error {
  readonly code: ModelErrorCode;
  readonly recoverable: boolean;

  constructor(code: ModelErrorCode, message: string, recoverable = true) {
    super(message);
    this.name = 'ModelProviderError';
    this.code = code;
    this.recoverable = recoverable;
  }
}

export interface ModelProvider {
  readonly id: 'mock' | 'anthropic' | 'ollama' | 'claude_cli';
  readonly label: string;
  status(): ProviderStatus;
  complete(request: ModelCompletionRequest): Promise<ModelCompletionResult>;
  /**
   * True when this tier is served by the local Claude CLI subprocess.
   * Requests that would send registered-project content through the CLI are
   * approval-gated by the orchestrator.
   */
  usesLocalCli?(tier: ModelTier): boolean;
}
