import { describe, expect, it } from 'vitest';
import { loadConfig } from '../../../src/server/config/env';
import {
  AnthropicModelProvider,
  MockModelProvider,
  ModelProviderError,
  createModelProvider,
} from '../../../src/server/providers/model';

function config(overrides: Parameters<typeof loadConfig>[0] = {}) {
  return loadConfig({
    dataDir: 'unused',
    modelProvider: 'mock',
    anthropicApiKey: null,
    fastModelName: null,
    deepModelName: null,
    ...overrides,
  });
}

describe('provider selection', () => {
  it('selects the mock provider by default', () => {
    expect(createModelProvider(config()).id).toBe('mock');
  });

  it('selects anthropic when configured, without silent fallback', () => {
    const provider = createModelProvider(config({ modelProvider: 'anthropic' }));
    expect(provider.id).toBe('anthropic');
  });
});

describe('MockModelProvider', () => {
  it('labels itself as a demo provider and marks results simulated', async () => {
    const provider = new MockModelProvider();
    const status = provider.status();
    expect(status.mode).toBe('mock');
    expect(status.label).toContain('Demo');
    const result = await provider.complete({
      system: 'x',
      messages: [{ role: 'user', content: 'What are we building today?' }],
      tier: 'fast',
      demoContext: { intent: 'project', projectName: 'JARVIS OS', projectSummary: 'the MVP' },
    });
    expect(result.simulated).toBe(true);
    expect(result.provider).toContain('Demo');
    expect(result.text).toContain('JARVIS OS');
  });

  it('labels deep reasoning responses as simulated', async () => {
    const provider = new MockModelProvider();
    const result = await provider.complete({
      system: 'x',
      messages: [{ role: 'user', content: 'Evaluate whether this architecture will scale.' }],
      tier: 'deep',
    });
    expect(result.text.toLowerCase()).toContain('simulated');
  });
});

describe('AnthropicModelProvider configuration', () => {
  it('reports an honest configuration error when the key is missing', () => {
    const provider = new AnthropicModelProvider(config({ modelProvider: 'anthropic' }));
    const status = provider.status();
    expect(status.configured).toBe(false);
    expect(status.configurationError).toContain('ANTHROPIC_API_KEY');
  });

  it('reports missing model name when only the key is set', () => {
    const provider = new AnthropicModelProvider(
      config({ modelProvider: 'anthropic', anthropicApiKey: 'test-key-not-real' }),
    );
    expect(provider.status().configurationError).toContain('FAST_MODEL_NAME');
  });

  it('rejects completion when unconfigured instead of falling back to mock', async () => {
    const provider = new AnthropicModelProvider(config({ modelProvider: 'anthropic' }));
    await expect(
      provider.complete({ system: 'x', messages: [{ role: 'user', content: 'hi' }], tier: 'fast' }),
    ).rejects.toThrowError(ModelProviderError);
  });

  it('never exposes the API key through status', () => {
    const provider = new AnthropicModelProvider(
      config({
        modelProvider: 'anthropic',
        anthropicApiKey: 'sk-ant-secret-value',
        fastModelName: 'configured-fast-model',
      }),
    );
    const serialized = JSON.stringify(provider.status());
    expect(serialized).not.toContain('sk-ant-secret-value');
    expect(provider.status().configured).toBe(true);
  });
});
