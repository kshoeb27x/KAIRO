import { afterEach, describe, expect, it, vi } from 'vitest';
import { loadConfig } from '../../../src/server/config/env';
import {
  OllamaModelProvider,
  ModelProviderError,
  createModelProvider,
} from '../../../src/server/providers/model';

// Every ollama field is set explicitly so a developer's local .env can never
// influence these tests. No test here talks to a real Ollama or any cloud API.
function config(overrides: Parameters<typeof loadConfig>[0] = {}) {
  return loadConfig({
    dataDir: 'unused',
    modelProvider: 'ollama',
    anthropicApiKey: null,
    fastModelName: null,
    deepModelName: null,
    ollamaBaseUrl: 'http://127.0.0.1:11434',
    ollamaModel: 'test-model:latest',
    ollamaNumCtx: 4096,
    ollamaThink: false,
    modelTimeoutMs: 5000,
    ...overrides,
  });
}

function ndjsonResponse(chunks: object[], init: ResponseInit = { status: 200 }): Response {
  return new Response(chunks.map((c) => JSON.stringify(c)).join('\n') + '\n', init);
}

function request(overrides: Partial<Parameters<OllamaModelProvider['complete']>[0]> = {}) {
  return {
    system: 'You are JARVIS.',
    messages: [{ role: 'user' as const, content: 'hello' }],
    tier: 'fast' as const,
    ...overrides,
  };
}

const fetchMock = vi.fn<typeof fetch>();
vi.stubGlobal('fetch', fetchMock);

afterEach(() => {
  fetchMock.mockReset();
});

describe('provider selection with ollama', () => {
  it('selects ollama explicitly', () => {
    expect(createModelProvider(config()).id).toBe('ollama');
  });

  it('keeps mock and anthropic selectable (existing provider compatibility)', () => {
    expect(createModelProvider(config({ modelProvider: 'mock' })).id).toBe('mock');
    expect(createModelProvider(config({ modelProvider: 'anthropic' })).id).toBe('anthropic');
  });
});

describe('OllamaModelProvider status', () => {
  it('reports a truthful local label, never Demo/Simulated', () => {
    const status = new OllamaModelProvider(config()).status();
    expect(status.mode).toBe('ollama');
    expect(status.label).toContain('Local Ollama');
    expect(status.label).toContain('test-model:latest');
    expect(status.label.toLowerCase()).not.toContain('demo');
    expect(status.configured).toBe(true);
  });

  it('reports an honest configuration error when the model is unset', () => {
    const status = new OllamaModelProvider(config({ ollamaModel: null })).status();
    expect(status.configured).toBe(false);
    expect(status.configurationError).toContain('OLLAMA_MODEL');
  });

  it('rejects non-loopback base URLs', () => {
    const provider = new OllamaModelProvider(config({ ollamaBaseUrl: 'http://192.168.1.50:11434' }));
    expect(provider.status().configured).toBe(false);
    expect(provider.status().configurationError).toContain('loopback');
  });
});

describe('OllamaModelProvider completions', () => {
  it('assembles a streamed NDJSON response and marks it not simulated', async () => {
    fetchMock.mockResolvedValueOnce(
      ndjsonResponse([
        { message: { role: 'assistant', content: 'Hello, ' }, done: false },
        { message: { role: 'assistant', content: 'sir.' }, done: false },
        { message: { role: 'assistant', content: '' }, done: true },
      ]),
    );
    const result = await new OllamaModelProvider(config()).complete(request());
    expect(result.text).toBe('Hello, sir.');
    expect(result.simulated).toBe(false);
    expect(result.provider).toBe('Local Ollama');
    expect(result.model).toBe('test-model:latest');

    // Request shape: /api/chat on loopback, think disabled, context pinned.
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(String(url)).toBe('http://127.0.0.1:11434/api/chat');
    const body = JSON.parse((init as RequestInit).body as string);
    expect(body.model).toBe('test-model:latest');
    expect(body.stream).toBe(true);
    expect(body.think).toBe(false);
    expect(body.options.num_ctx).toBe(4096);
    expect(body.messages[0]).toEqual({ role: 'system', content: 'You are JARVIS.' });
  });

  it('strips <think> blocks so hidden reasoning is never shown or spoken', async () => {
    fetchMock.mockResolvedValueOnce(
      ndjsonResponse([
        { message: { content: '<think>secret chain of thought</think>Visible answer.' }, done: true },
      ]),
    );
    const result = await new OllamaModelProvider(config()).complete(request());
    expect(result.text).toBe('Visible answer.');
    expect(result.text).not.toContain('secret');
  });

  it('normalizes connection failure with guidance, without demo fallback', async () => {
    fetchMock.mockRejectedValueOnce(new TypeError('fetch failed'));
    const provider = new OllamaModelProvider(config());
    const error = await provider.complete(request()).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ModelProviderError);
    expect((error as ModelProviderError).code).toBe('network');
    expect((error as ModelProviderError).message).toContain('Ollama is running');
    expect((error as ModelProviderError).message.toLowerCase()).not.toContain('demo');
  });

  it('normalizes a missing model with the pull command', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ error: 'model "test-model:latest" not found, try pulling it first' }), {
        status: 404,
      }),
    );
    const error = await new OllamaModelProvider(config()).complete(request()).catch((e: unknown) => e);
    expect((error as ModelProviderError).code).toBe('api_error');
    expect((error as ModelProviderError).message).toContain('ollama pull test-model:latest');
  });

  it('normalizes timeouts', async () => {
    fetchMock.mockImplementationOnce(
      (_url, init) =>
        new Promise((_resolve, reject) => {
          init?.signal?.addEventListener('abort', () =>
            reject(Object.assign(new Error('aborted'), { name: 'AbortError' })),
          );
        }),
    );
    const provider = new OllamaModelProvider(config({ modelTimeoutMs: 25 }));
    const error = await provider.complete(request()).catch((e: unknown) => e);
    expect((error as ModelProviderError).code).toBe('timeout');
  });

  it('normalizes caller cancellation (interruption)', async () => {
    fetchMock.mockImplementationOnce(
      (_url, init) =>
        new Promise((_resolve, reject) => {
          init?.signal?.addEventListener('abort', () =>
            reject(Object.assign(new Error('aborted'), { name: 'AbortError' })),
          );
        }),
    );
    const abort = new AbortController();
    const pending = new OllamaModelProvider(config()).complete(request({ signal: abort.signal }));
    abort.abort();
    const error = await pending.catch((e: unknown) => e);
    expect((error as ModelProviderError).code).toBe('cancelled');
  });

  it('rejects malformed stream lines honestly', async () => {
    fetchMock.mockResolvedValueOnce(new Response('this is not json\n', { status: 200 }));
    const error = await new OllamaModelProvider(config()).complete(request()).catch((e: unknown) => e);
    expect((error as ModelProviderError).code).toBe('api_error');
    expect((error as ModelProviderError).message).toContain('malformed');
  });

  it('rejects a stream that ends without done', async () => {
    fetchMock.mockResolvedValueOnce(ndjsonResponse([{ message: { content: 'partial' }, done: false }]));
    const error = await new OllamaModelProvider(config()).complete(request()).catch((e: unknown) => e);
    expect((error as ModelProviderError).code).toBe('api_error');
  });

  it('surfaces mid-stream Ollama errors', async () => {
    fetchMock.mockResolvedValueOnce(ndjsonResponse([{ error: 'model requires more system memory' }]));
    const error = await new OllamaModelProvider(config()).complete(request()).catch((e: unknown) => e);
    expect((error as ModelProviderError).code).toBe('api_error');
    expect((error as ModelProviderError).message).toContain('more system memory');
  });

  it('normalizes non-404 server errors', async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ error: 'boom' }), { status: 500 }));
    const error = await new OllamaModelProvider(config()).complete(request()).catch((e: unknown) => e);
    expect((error as ModelProviderError).code).toBe('api_error');
    expect((error as ModelProviderError).message).toContain('500');
  });

  it('refuses to run unconfigured instead of falling back to mock', async () => {
    fetchMock.mockResolvedValueOnce(ndjsonResponse([{ message: { content: 'x' }, done: true }]));
    const provider = new OllamaModelProvider(config({ ollamaModel: null }));
    const error = await provider.complete(request()).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ModelProviderError);
    expect((error as ModelProviderError).code).toBe('not_configured');
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('refuses non-loopback endpoints at request time', async () => {
    const provider = new OllamaModelProvider(config({ ollamaBaseUrl: 'http://10.0.0.9:11434' }));
    const error = await provider.complete(request()).catch((e: unknown) => e);
    expect((error as ModelProviderError).code).toBe('not_configured');
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
