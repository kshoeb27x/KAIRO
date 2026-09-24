import path from 'node:path';
import fs from 'node:fs';

export interface ServerConfig {
  host: string;
  port: number;
  dataDir: string;
  modelProvider: 'mock' | 'anthropic' | 'ollama' | 'claude_cli';
  anthropicApiKey: string | null;
  fastModelName: string | null;
  deepModelName: string | null;
  modelTimeoutMs: number;
  ollamaBaseUrl: string;
  ollamaModel: string | null;
  ollamaNumCtx: number;
  ollamaThink: boolean;
  /** Ollama keep_alive value (e.g. "30m") so the model stays warm between requests. */
  ollamaKeepAlive: string;
  /** Optional local Claude CLI bridge (no API key). Disabled by default. */
  claudeCliEnabled: boolean;
  claudeCliCommand: string;
  claudeCliTimeoutMs: number;
  /** Absolute path to a bot-written JSON trading report; null = not connected. */
  tradingReportPath: string | null;
  /** Google OAuth desktop-app client (owner-created; see docs/INTEGRATIONS.md). */
  googleClientId: string | null;
  googleClientSecret: string | null;
  isProduction: boolean;
}

let envLoaded = false;

/** Loads .env once if present. Missing .env is fine — defaults apply. */
function loadDotEnv(projectRoot: string): void {
  if (envLoaded) return;
  envLoaded = true;
  const envPath = path.join(projectRoot, '.env');
  if (fs.existsSync(envPath)) {
    process.loadEnvFile(envPath);
  }
}

export function loadConfig(overrides: Partial<ServerConfig> = {}): ServerConfig {
  const projectRoot = process.cwd();
  loadDotEnv(projectRoot);

  const rawDataDir = process.env.JARVIS_DATA_DIR ?? '.data';
  const dataDir = path.isAbsolute(rawDataDir) ? rawDataDir : path.resolve(projectRoot, rawDataDir);

  const providerRaw = (process.env.MODEL_PROVIDER ?? 'mock').toLowerCase();
  const modelProvider =
    providerRaw === 'anthropic'
      ? 'anthropic'
      : providerRaw === 'ollama'
        ? 'ollama'
        : providerRaw === 'claude_cli'
          ? 'claude_cli'
          : 'mock';

  const timeout = Number(process.env.MODEL_TIMEOUT_MS ?? 45000);
  const numCtx = Number(process.env.OLLAMA_NUM_CTX ?? 4096);
  const cliTimeout = Number(process.env.CLAUDE_CLI_TIMEOUT_MS ?? 120000);

  return {
    host: process.env.HOST ?? '127.0.0.1',
    port: Number(process.env.PORT ?? 8787),
    dataDir,
    modelProvider,
    anthropicApiKey: process.env.ANTHROPIC_API_KEY?.trim() || null,
    fastModelName: process.env.FAST_MODEL_NAME?.trim() || null,
    deepModelName: process.env.DEEP_MODEL_NAME?.trim() || null,
    modelTimeoutMs: Number.isFinite(timeout) && timeout > 0 ? timeout : 45000,
    ollamaBaseUrl: process.env.OLLAMA_BASE_URL?.trim() || 'http://127.0.0.1:11434',
    ollamaModel: process.env.OLLAMA_MODEL?.trim() || null,
    ollamaNumCtx: Number.isFinite(numCtx) && numCtx > 0 ? Math.floor(numCtx) : 4096,
    ollamaThink: (process.env.OLLAMA_THINK ?? 'false').trim().toLowerCase() === 'true',
    ollamaKeepAlive: process.env.OLLAMA_KEEP_ALIVE?.trim() || '30m',
    claudeCliEnabled: (process.env.CLAUDE_CLI_ENABLED ?? 'false').trim().toLowerCase() === 'true',
    claudeCliCommand: process.env.CLAUDE_CLI_COMMAND?.trim() || 'claude',
    claudeCliTimeoutMs: Number.isFinite(cliTimeout) && cliTimeout > 0 ? cliTimeout : 120000,
    tradingReportPath: process.env.TRADING_REPORT_PATH?.trim() || null,
    googleClientId: process.env.GOOGLE_CLIENT_ID?.trim() || null,
    googleClientSecret: process.env.GOOGLE_CLIENT_SECRET?.trim() || null,
    isProduction: process.env.NODE_ENV === 'production',
    ...overrides,
  };
}
