import type { ProviderStatus } from '../../../shared/types';
import type { ServerConfig } from '../../config/env';
import { MockModelProvider } from './mockProvider';
import { AnthropicModelProvider } from './anthropicProvider';
import { OllamaModelProvider } from './ollamaProvider';
import { ClaudeCliProvider } from './claudeCliProvider';
import type {
  ModelCompletionRequest,
  ModelCompletionResult,
  ModelProvider,
  ModelTier,
} from './types';

/**
 * Ollama stays the everyday provider; when the owner has opted into the
 * Claude CLI bridge, deep-reasoning requests are served by the CLI instead.
 * Every response is attributed to the provider that actually produced it.
 */
class HybridDeepProvider implements ModelProvider {
  readonly id = 'ollama' as const;
  readonly label: string;

  constructor(
    private readonly primary: OllamaModelProvider,
    private readonly deep: ClaudeCliProvider,
  ) {
    this.label = `${primary.label} + ${deep.label} for deep reasoning`;
  }

  status(): ProviderStatus {
    const base = this.primary.status();
    return {
      ...base,
      label: `${base.label} · deep reasoning via Claude CLI`,
      deepModel: 'claude-cli',
    };
  }

  usesLocalCli(tier: ModelTier): boolean {
    return tier === 'deep';
  }

  complete(request: ModelCompletionRequest): Promise<ModelCompletionResult> {
    return request.tier === 'deep' ? this.deep.complete(request) : this.primary.complete(request);
  }
}

export interface ProviderSetup {
  provider: ModelProvider;
  /** Present when the local Claude CLI bridge is configured (any mode). */
  claudeCli: ClaudeCliProvider | null;
}

export function createProviderSetup(config: ServerConfig): ProviderSetup {
  // Explicit selection only. Real providers never silently fall back to
  // mock — misconfiguration surfaces as an honest error at request time.
  switch (config.modelProvider) {
    case 'anthropic':
      return { provider: new AnthropicModelProvider(config), claudeCli: null };
    case 'claude_cli': {
      const cli = new ClaudeCliProvider(config);
      return { provider: cli, claudeCli: cli };
    }
    case 'ollama': {
      const ollama = new OllamaModelProvider(config);
      if (config.claudeCliEnabled) {
        const cli = new ClaudeCliProvider(config);
        return { provider: new HybridDeepProvider(ollama, cli), claudeCli: cli };
      }
      return { provider: ollama, claudeCli: null };
    }
    default:
      return { provider: new MockModelProvider(), claudeCli: null };
  }
}

export function createModelProvider(config: ServerConfig): ModelProvider {
  return createProviderSetup(config).provider;
}

export { MockModelProvider } from './mockProvider';
export { AnthropicModelProvider } from './anthropicProvider';
export { OllamaModelProvider } from './ollamaProvider';
export { ClaudeCliProvider, spawnCliRunner } from './claudeCliProvider';
export type { CliRunner, CliRunResult } from './claudeCliProvider';
export { ModelProviderError } from './types';
export type { ModelProvider, ModelCompletionRequest, ModelCompletionResult } from './types';
