// Pure helpers for the JARVIS launcher. No side effects — unit tested.

/** Minimal .env parser (KEY=VALUE lines, # comments). Never throws. */
export function parseDotEnv(text) {
  const result = {};
  for (const rawLine of String(text).split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) continue;
    const eq = line.indexOf('=');
    if (eq <= 0) continue;
    const key = line.slice(0, eq).trim();
    let value = line.slice(eq + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    if (/^[A-Za-z_][A-Za-z0-9_]*$/.test(key)) result[key] = value;
  }
  return result;
}

/**
 * Resolves launcher configuration: real environment wins over .env, matching
 * the server's own precedence.
 */
export function resolveLauncherConfig(dotEnv, processEnv) {
  const pick = (key, fallback) => {
    const fromEnv = processEnv[key];
    if (fromEnv !== undefined && String(fromEnv).trim() !== '') return String(fromEnv).trim();
    const fromFile = dotEnv[key];
    if (fromFile !== undefined && String(fromFile).trim() !== '') return String(fromFile).trim();
    return fallback;
  };
  const port = Number(pick('PORT', '8787'));
  return {
    host: pick('HOST', '127.0.0.1'),
    port: Number.isInteger(port) && port > 0 ? port : 8787,
    modelProvider: pick('MODEL_PROVIDER', 'mock').toLowerCase(),
    ollamaBaseUrl: pick('OLLAMA_BASE_URL', 'http://127.0.0.1:11434'),
    ollamaModel: pick('OLLAMA_MODEL', ''),
    ollamaKeepAlive: pick('OLLAMA_KEEP_ALIVE', '30m'),
  };
}

/** True when the Ollama tag list contains the configured model. */
export function modelInstalled(tagsResponse, model) {
  if (!model) return false;
  const models = Array.isArray(tagsResponse?.models) ? tagsResponse.models : [];
  return models.some((m) => m?.name === model || m?.name === `${model}:latest`);
}
