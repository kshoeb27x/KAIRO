import { describe, expect, it, vi } from 'vitest';
import { loadConfig } from '../../../src/server/config/env';
import type {
  ModelProviderError} from '../../../src/server/providers/model';
import {
  ClaudeCliProvider,
  createProviderSetup,
  type CliRunner,
} from '../../../src/server/providers/model';

function config(overrides: Parameters<typeof loadConfig>[0] = {}) {
  return loadConfig({
    dataDir: 'unused',
    modelProvider: 'claude_cli',
    anthropicApiKey: null,
    fastModelName: null,
    deepModelName: null,
    ollamaBaseUrl: 'http://127.0.0.1:11434',
    ollamaModel: 'test-model',
    claudeCliEnabled: true,
    claudeCliCommand: 'claude',
    claudeCliTimeoutMs: 5000,
    ...overrides,
  });
}

function request() {
  return {
    system: 'You are JARVIS.',
    messages: [{ role: 'user' as const, content: 'hello there' }],
    tier: 'fast' as const,
  };
}

const okRunner: CliRunner = async () => ({
  exitCode: 0,
  stdout: JSON.stringify({ result: 'Hello from Claude CLI.', is_error: false }),
  stderr: '',
  timedOut: false,
});

describe('provider selection with the Claude CLI bridge', () => {
  it('is disabled by default — ollama stays plain ollama', () => {
    const setup = createProviderSetup(config({ modelProvider: 'ollama', claudeCliEnabled: false }));
    expect(setup.provider.id).toBe('ollama');
    expect(setup.claudeCli).toBeNull();
    expect(setup.provider.usesLocalCli?.('deep') ?? false).toBe(false);
  });

  it('ollama + enabled bridge routes only the deep tier to the CLI', () => {
    const setup = createProviderSetup(config({ modelProvider: 'ollama', claudeCliEnabled: true }));
    expect(setup.provider.id).toBe('ollama');
    expect(setup.claudeCli).not.toBeNull();
    expect(setup.provider.usesLocalCli?.('deep')).toBe(true);
    expect(setup.provider.usesLocalCli?.('fast')).toBe(false);
    expect(setup.provider.status().deepModel).toBe('claude-cli');
    expect(setup.provider.status().label).toContain('Claude CLI');
  });

  it('MODEL_PROVIDER=claude_cli selects the CLI for everything', () => {
    const setup = createProviderSetup(config());
    expect(setup.provider.id).toBe('claude_cli');
    expect(setup.provider.usesLocalCli?.('fast')).toBe(true);
  });

  it('mock and anthropic remain unaffected', () => {
    expect(createProviderSetup(config({ modelProvider: 'mock' })).provider.id).toBe('mock');
    expect(createProviderSetup(config({ modelProvider: 'anthropic' })).provider.id).toBe(
      'anthropic',
    );
  });
});

describe('ClaudeCliProvider', () => {
  it('reports an honest disabled status and refuses to run', async () => {
    const provider = new ClaudeCliProvider(config({ claudeCliEnabled: false }), okRunner);
    expect(provider.status().configured).toBe(false);
    expect(provider.status().configurationError).toContain('disabled');
    const error = await provider.complete(request()).catch((e: unknown) => e);
    expect((error as ModelProviderError).code).toBe('not_configured');
  });

  it('rejects arbitrary commands (subprocess allowlist)', async () => {
    const provider = new ClaudeCliProvider(
      config({ claudeCliCommand: 'powershell -c evil' }),
      okRunner,
    );
    expect(provider.status().configured).toBe(false);
    const error = await provider.complete(request()).catch((e: unknown) => e);
    expect((error as ModelProviderError).code).toBe('not_configured');
  });

  it('accepts an absolute path to the claude executable', () => {
    const provider = new ClaudeCliProvider(
      config({ claudeCliCommand: 'C:\\Users\\me\\AppData\\Roaming\\npm\\claude.cmd' }),
      okRunner,
    );
    expect(provider.status().configured).toBe(true);
  });

  it('parses a successful CLI response and labels it honestly', async () => {
    const runner = vi.fn(okRunner);
    const provider = new ClaudeCliProvider(config(), runner);
    const result = await provider.complete(request());
    expect(result.text).toBe('Hello from Claude CLI.');
    expect(result.provider).toContain('Claude CLI');
    expect(result.simulated).toBe(false);
    const call = runner.mock.calls[0]![0];
    expect(call.command).toBe('claude');
    expect(call.args).toEqual(['-p', '--output-format', 'json']);
    expect(call.stdin).toContain('You are JARVIS.');
    expect(call.stdin).toContain('hello there');
  });

  it('reports a missing CLI with install guidance', async () => {
    const runner: CliRunner = async () => {
      throw Object.assign(new Error('spawn claude ENOENT'), { code: 'ENOENT' });
    };
    const provider = new ClaudeCliProvider(config(), runner);
    const error = await provider.complete(request()).catch((e: unknown) => e);
    expect((error as ModelProviderError).code).toBe('not_configured');
    expect((error as ModelProviderError).message).toContain('not installed');
  });

  it('normalizes timeouts', async () => {
    const runner: CliRunner = async () => ({ exitCode: null, stdout: '', stderr: '', timedOut: true });
    const provider = new ClaudeCliProvider(config(), runner);
    const error = await provider.complete(request()).catch((e: unknown) => e);
    expect((error as ModelProviderError).code).toBe('timeout');
  });

  it('normalizes cancellation', async () => {
    const abort = new AbortController();
    const runner: CliRunner = async () => {
      abort.abort();
      throw new Error('killed');
    };
    const provider = new ClaudeCliProvider(config(), runner);
    const error = await provider
      .complete({ ...request(), signal: abort.signal })
      .catch((e: unknown) => e);
    expect((error as ModelProviderError).code).toBe('cancelled');
  });

  it('reports login problems honestly on nonzero exit', async () => {
    const runner: CliRunner = async () => ({
      exitCode: 1,
      stdout: '',
      stderr: 'Error: not logged in. Please run claude login.',
      timedOut: false,
    });
    const provider = new ClaudeCliProvider(config(), runner);
    const error = await provider.complete(request()).catch((e: unknown) => e);
    expect((error as ModelProviderError).code).toBe('api_error');
    expect((error as ModelProviderError).message).toContain('logged in');
  });

  it('rejects malformed CLI output', async () => {
    const runner: CliRunner = async () => ({ exitCode: 0, stdout: 'not json', stderr: '', timedOut: false });
    const provider = new ClaudeCliProvider(config(), runner);
    const error = await provider.complete(request()).catch((e: unknown) => e);
    expect((error as ModelProviderError).code).toBe('api_error');
  });
});
