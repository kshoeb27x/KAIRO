import { describe, expect, it } from 'vitest';
// @ts-expect-error — plain .mjs module without type declarations
import { parseDotEnv, resolveLauncherConfig, modelInstalled } from '../../../scripts/launcher-lib.mjs';

describe('launcher configuration', () => {
  it('parses .env lines and ignores comments and malformed entries', () => {
    const parsed = parseDotEnv(
      '# comment\nMODEL_PROVIDER=ollama\nOLLAMA_MODEL="qwen3:8b-q4_K_M"\nBADLINE\n=nope\n',
    ) as Record<string, string>;
    expect(parsed.MODEL_PROVIDER).toBe('ollama');
    expect(parsed.OLLAMA_MODEL).toBe('qwen3:8b-q4_K_M');
    expect(Object.keys(parsed)).toHaveLength(2);
  });

  it('lets real environment variables win over .env, like the server does', () => {
    const cfg = resolveLauncherConfig(
      { MODEL_PROVIDER: 'ollama', PORT: '9999' },
      { MODEL_PROVIDER: 'mock' },
    );
    expect(cfg.modelProvider).toBe('mock');
    expect(cfg.port).toBe(9999);
    expect(cfg.ollamaKeepAlive).toBe('30m');
  });

  it('falls back to safe defaults for missing or invalid values', () => {
    const cfg = resolveLauncherConfig({ PORT: 'not-a-number' }, {});
    expect(cfg.port).toBe(8787);
    expect(cfg.host).toBe('127.0.0.1');
    expect(cfg.ollamaBaseUrl).toBe('http://127.0.0.1:11434');
  });

  it('detects whether the configured model is installed', () => {
    const tags = { models: [{ name: 'qwen3:8b-q4_K_M' }, { name: 'llama3:latest' }] };
    expect(modelInstalled(tags, 'qwen3:8b-q4_K_M')).toBe(true);
    expect(modelInstalled(tags, 'llama3')).toBe(true);
    expect(modelInstalled(tags, 'missing:7b')).toBe(false);
    expect(modelInstalled(null, 'qwen3:8b-q4_K_M')).toBe(false);
    expect(modelInstalled(tags, '')).toBe(false);
  });
});
