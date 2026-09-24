import type { ProviderStatus } from '../../../shared/types';
import type { ServerConfig } from '../../config/env';
import {
  ModelProviderError,
  type ModelCompletionRequest,
  type ModelCompletionResult,
  type ModelProvider,
} from './types';

const LOOPBACK_HOSTS = new Set(['127.0.0.1', 'localhost']);

/**
 * Local Ollama provider. Talks to the Ollama HTTP API (`/api/chat`) on
 * loopback only — no cloud calls, no API keys, and the browser never reaches
 * Ollama directly. Failures surface as honest normalized errors; there is no
 * silent fallback to the demo provider. Hidden reasoning is disabled via
 * `think: false` (default) and defensively stripped from responses so it is
 * never displayed or spoken.
 */
export class OllamaModelProvider implements ModelProvider {
  readonly id = 'ollama' as const;
  readonly label = 'Local Ollama';

  private readonly config: ServerConfig;

  constructor(config: ServerConfig) {
    this.config = config;
  }

  private configurationError(): string | null {
    if (!this.config.ollamaModel) {
      return 'MODEL_PROVIDER=ollama but OLLAMA_MODEL is not set.';
    }
    let url: URL;
    try {
      url = new URL(this.config.ollamaBaseUrl);
    } catch {
      return 'OLLAMA_BASE_URL is not a valid URL.';
    }
    if (!LOOPBACK_HOSTS.has(url.hostname)) {
      return 'OLLAMA_BASE_URL must be a loopback address (http://127.0.0.1:11434 or http://localhost:11434) in this prototype.';
    }
    return null;
  }

  status(): ProviderStatus {
    const configurationError = this.configurationError();
    return {
      mode: 'ollama',
      label: `Local Ollama${this.config.ollamaModel ? ` (${this.config.ollamaModel})` : ''}`,
      configured: configurationError === null,
      configurationError,
      // One local model serves both tiers on this hardware.
      fastModel: this.config.ollamaModel,
      deepModel: this.config.ollamaModel,
    };
  }

  async complete(request: ModelCompletionRequest): Promise<ModelCompletionResult> {
    const configurationError = this.configurationError();
    if (configurationError) {
      throw new ModelProviderError('not_configured', configurationError, false);
    }
    const model = this.config.ollamaModel!;
    const endpoint = new URL('/api/chat', this.config.ollamaBaseUrl);

    // Own controller so a timeout can be told apart from caller cancellation.
    const controller = new AbortController();
    let timedOut = false;
    const timer = setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, this.config.modelTimeoutMs);
    const onCallerAbort = () => controller.abort();
    request.signal?.addEventListener('abort', onCallerAbort, { once: true });
    if (request.signal?.aborted) controller.abort();

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        signal: controller.signal,
        body: JSON.stringify({
          model,
          messages: [{ role: 'system', content: request.system }, ...request.messages],
          stream: true,
          think: this.config.ollamaThink,
          keep_alive: this.config.ollamaKeepAlive,
          options: {
            num_ctx: this.config.ollamaNumCtx,
            num_predict: request.maxTokens ?? 1024,
          },
        }),
      });

      if (!response.ok) {
        throw await this.httpError(response, model);
      }
      if (!response.body) {
        throw new ModelProviderError('api_error', 'Ollama returned an empty response.');
      }

      const text = await this.readStream(response.body);
      return { text, provider: this.label, model, simulated: false };
    } catch (error) {
      throw this.normalizeError(error, timedOut, request.signal, model);
    } finally {
      clearTimeout(timer);
      request.signal?.removeEventListener('abort', onCallerAbort);
    }
  }

  /** Assembles Ollama's newline-delimited JSON stream into the final text. */
  private async readStream(body: ReadableStream<Uint8Array>): Promise<string> {
    const decoder = new TextDecoder();
    let buffered = '';
    let text = '';
    let done = false;

    const handleLine = (line: string): void => {
      const trimmed = line.trim();
      if (!trimmed) return;
      let chunk: { message?: { content?: string }; done?: boolean; error?: string };
      try {
        chunk = JSON.parse(trimmed) as typeof chunk;
      } catch {
        throw new ModelProviderError('api_error', 'Ollama returned a malformed response.');
      }
      if (typeof chunk.error === 'string') {
        throw new ModelProviderError('api_error', `Ollama reported an error: ${truncate(chunk.error, 200)}`);
      }
      if (typeof chunk.message?.content === 'string') {
        text += chunk.message.content;
      }
      if (chunk.done === true) done = true;
    };

    for await (const part of body) {
      buffered += decoder.decode(part as Uint8Array, { stream: true });
      let newline = buffered.indexOf('\n');
      while (newline !== -1) {
        handleLine(buffered.slice(0, newline));
        buffered = buffered.slice(newline + 1);
        newline = buffered.indexOf('\n');
      }
    }
    handleLine(buffered);

    if (!done) {
      throw new ModelProviderError('api_error', 'The Ollama response ended unexpectedly.');
    }
    // Defensive: never surface hidden reasoning even if the model emits it.
    return stripThinkBlocks(text).trim();
  }

  private async httpError(response: Response, model: string): Promise<ModelProviderError> {
    let detail = '';
    try {
      const parsed = (await response.json()) as { error?: string };
      detail = typeof parsed.error === 'string' ? parsed.error : '';
    } catch {
      // Non-JSON error body — fall through to the generic message.
    }
    if (response.status === 404 || /not found|try pulling/i.test(detail)) {
      return new ModelProviderError(
        'api_error',
        `The model "${model}" is not installed in Ollama. Run: ollama pull ${model}`,
      );
    }
    return new ModelProviderError(
      'api_error',
      `Ollama returned an error (HTTP ${response.status})${detail ? `: ${truncate(detail, 200)}` : '.'}`,
    );
  }

  private normalizeError(
    error: unknown,
    timedOut: boolean,
    callerSignal: AbortSignal | undefined,
    model: string,
  ): ModelProviderError {
    if (error instanceof ModelProviderError) return error;
    if (callerSignal?.aborted) {
      return new ModelProviderError('cancelled', 'The request was interrupted.');
    }
    if (timedOut) {
      return new ModelProviderError(
        'timeout',
        `The local model timed out after ${Math.round(this.config.modelTimeoutMs / 1000)}s.`,
      );
    }
    if (error instanceof Error && error.name === 'AbortError') {
      return new ModelProviderError('cancelled', 'The request was interrupted.');
    }
    if (error instanceof TypeError) {
      return new ModelProviderError(
        'network',
        `Could not reach Ollama at ${this.config.ollamaBaseUrl}. ` +
          `Make sure Ollama is running and the model "${model}" is installed (ollama pull ${model}).`,
      );
    }
    return new ModelProviderError('api_error', 'The local model request failed unexpectedly.');
  }
}

function stripThinkBlocks(text: string): string {
  return text.replace(/<think>[\s\S]*?<\/think>/gi, '');
}

function truncate(text: string, max: number): string {
  return text.length <= max ? text : `${text.slice(0, max - 1)}…`;
}
