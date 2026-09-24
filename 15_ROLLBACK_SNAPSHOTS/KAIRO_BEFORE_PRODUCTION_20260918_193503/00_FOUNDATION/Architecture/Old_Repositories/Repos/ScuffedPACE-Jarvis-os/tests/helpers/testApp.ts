import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import type { FastifyInstance } from 'fastify';
import { buildApp, type BuildAppResult } from '../../src/server/app';
import { loadConfig, type ServerConfig } from '../../src/server/config/env';

export interface TestApp extends BuildAppResult {
  app: FastifyInstance;
  dir: string;
  close(): Promise<void>;
}

/**
 * Builds the API against an isolated temporary data directory with the mock
 * provider. Automated tests never call a paid external model.
 */
export function createTestApp(
  overrides: Partial<ServerConfig> = {},
  appOverrides: Parameters<typeof buildApp>[1] = {},
): TestApp {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'jarvis-api-test-'));
  const config = loadConfig({
    dataDir: dir,
    modelProvider: 'mock',
    anthropicApiKey: null,
    claudeCliEnabled: false,
    isProduction: false,
    ...overrides,
  });
  const built = buildApp(config, appOverrides);
  return {
    ...built,
    dir,
    async close() {
      await built.app.close();
      fs.rmSync(dir, { recursive: true, force: true });
    },
  };
}

export function parseNdjson(payload: string): Array<Record<string, unknown>> {
  return payload
    .split('\n')
    .filter((line) => line.trim().length > 0)
    .map((line) => JSON.parse(line) as Record<string, unknown>);
}
