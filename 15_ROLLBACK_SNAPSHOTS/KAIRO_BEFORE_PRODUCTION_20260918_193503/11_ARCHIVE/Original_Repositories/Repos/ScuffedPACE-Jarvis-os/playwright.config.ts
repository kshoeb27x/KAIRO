import { defineConfig, devices } from '@playwright/test';

/**
 * E2E runs against the production build (Fastify serving the built client)
 * with an isolated .data-e2e directory and the mock provider — never against
 * the operational .data directory and never against a paid external model.
 */
export default defineConfig({
  testDir: 'tests/e2e',
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: 0,
  reporter: [['list']],
  timeout: 45000,
  use: {
    baseURL: 'http://127.0.0.1:8790',
    trace: 'off',
  },
  projects: [
    {
      name: 'chromium-1440x900',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } },
    },
    {
      name: 'chromium-1024x768',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1024, height: 768 } },
      testMatch: /responsive\.spec\.ts/,
    },
    {
      name: 'chromium-390x844-smoke',
      use: { ...devices['Desktop Chrome'], viewport: { width: 390, height: 844 } },
      testMatch: /responsive\.spec\.ts/,
    },
  ],
  webServer: {
    command: 'node dist/server/index.js',
    url: 'http://127.0.0.1:8790/api/health',
    reuseExistingServer: false,
    timeout: 30000,
    env: {
      NODE_ENV: 'production',
      HOST: '127.0.0.1',
      PORT: '8790',
      JARVIS_DATA_DIR: '.data-e2e',
      MODEL_PROVIDER: 'mock',
    },
  },
});
