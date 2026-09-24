import Anthropic from '@anthropic-ai/sdk';
import type { ProviderStatus } from '../../../shared/types';
import type { ServerConfig } from '../../config/env';
import {
  ModelProviderError,
  type ModelCompletionRequest,
  type ModelCompletionResult,
  type ModelProvider,
} from './types';

/**
 * Real Claude provider. The API key exists only server-side, is never logged,
 * and never appears in status responses. Model names are owner-configured —
 * nothing is hard-coded. When configuration is missing this provider reports
 * an honest error instead of silently falling back to the mock provider.
 */
export class AnthropicModelProvider implements ModelProvider {
  readonly id = 'anthropic' as const;
  readonly label = 'Anthropic Claude';

  private readonly client: Anthropic | null;
  private readonly config: ServerConfig;

  constructor(config: ServerConfig) {
    this.config = config;
    this.client = config.anthropicApiKey
      ? new Anthropic({
          apiKey: config.anthropicApiKey,
          timeout: config.modelTimeoutMs, // milliseconds in the TS SDK
          maxRetries: 1,
        })
      : null;
  }

  private configurationError(): string | null {
    if (!this.config.anthropicApiKey) {
      return 'MODEL_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set.';
    }
    if (!this.config.fastModelName) {
      return 'MODEL_PROVIDER=anthropic but FAST_MODEL_NAME is not set.';
    }
    return null;
  }

  status(): ProviderStatus {
    const configurationError = this.configurationError();
    return {
      mode: 'anthropic',
      label: 'Anthropic Claude',
      configured: configurationError === null,
      configurationError,
      fastModel: this.config.fastModelName,
      deepModel: this.config.deepModelName,
    };
  }

  async complete(request: ModelCompletionRequest): Promise<ModelCompletionResult> {
    const configurationError = this.configurationError();
    if (configurationError || !this.client) {
      throw new ModelProviderError('not_configured', configurationError ?? 'Not configured', false);
    }
    const model =
      request.tier === 'deep'
        ? (this.config.deepModelName ?? this.config.fastModelName!)
        : this.config.fastModelName!;

    try {
      const response = await this.client.messages.create(
        {
          model,
          max_tokens: request.maxTokens ?? 1024,
          system: request.system,
          messages: request.messages,
        },
        { signal: request.signal },
      );
      if (response.stop_reason === 'refusal') {
        return {
          text: 'The model declined this request for safety reasons. Try rephrasing it.',
          provider: this.label,
          model,
          simulated: false,
        };
      }
      const text = response.content
        .filter((block): block is Anthropic.TextBlock => block.type === 'text')
        .map((block) => block.text)
        .join('\n')
        .trim();
      return { text, provider: this.label, model, simulated: false };
    } catch (error) {
      throw normalizeAnthropicError(error);
    }
  }
}

function normalizeAnthropicError(error: unknown): ModelProviderError {
  if (error instanceof ModelProviderError) return error;
  if (error instanceof Anthropic.AuthenticationError) {
    return new ModelProviderError(
      'authentication',
      'The Anthropic API key was rejected. Check ANTHROPIC_API_KEY.',
      false,
    );
  }
  if (error instanceof Anthropic.NotFoundError) {
    return new ModelProviderError(
      'api_error',
      'The configured model name was not found. Check FAST_MODEL_NAME / DEEP_MODEL_NAME.',
      false,
    );
  }
  if (error instanceof Anthropic.RateLimitError) {
    return new ModelProviderError('rate_limited', 'The model is rate-limited. Try again shortly.');
  }
  if (error instanceof Anthropic.APIConnectionTimeoutError) {
    return new ModelProviderError('timeout', 'The model request timed out.');
  }
  if (error instanceof Anthropic.APIConnectionError) {
    return new ModelProviderError('network', 'Could not reach the Anthropic API.');
  }
  if (error instanceof Anthropic.APIError) {
    return new ModelProviderError('api_error', 'The model request failed with an API error.');
  }
  if (error instanceof Error && error.name === 'AbortError') {
    return new ModelProviderError('cancelled', 'The request was interrupted.');
  }
  return new ModelProviderError('api_error', 'The model request failed unexpectedly.');
}
