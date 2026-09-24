// JARVIS one-step launcher (Windows-friendly, no extra dependencies).
//
//   node scripts/launch.mjs [start|stop|status|restart] [--rebuild]
//
// start:   checks Ollama + model, warms the model, builds if needed, starts
//          the server in production mode exactly once, opens the browser.
// stop:    cleanly stops the JARVIS server started by this launcher.
// status:  reports server, Ollama, and model state without changing anything.

import fs from 'node:fs';
import path from 'node:path';
import { spawn, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { parseDotEnv, resolveLauncherConfig, modelInstalled } from './launcher-lib.mjs';

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const dataDir = path.join(projectRoot, '.data');
const pidFile = path.join(dataDir, 'jarvis.pid');
const logDir = path.join(dataDir, 'logs');
const logFile = path.join(logDir, 'jarvis-server.log');

const dotEnv = fs.existsSync(path.join(projectRoot, '.env'))
  ? parseDotEnv(fs.readFileSync(path.join(projectRoot, '.env'), 'utf8'))
  : {};
const cfg = resolveLauncherConfig(dotEnv, process.env);
const serverUrl = `http://${cfg.host}:${cfg.port}`;

const args = process.argv.slice(2);
const command = args.find((a) => !a.startsWith('--')) ?? 'start';
const rebuild = args.includes('--rebuild');

function log(msg) {
  console.log(msg);
}
function fail(msg) {
  console.error(`\n  ✗ ${msg}`);
  process.exitCode = 1;
}

async function fetchJson(url, options = {}, timeoutMs = 4000) {
  const response = await fetch(url, { ...options, signal: AbortSignal.timeout(timeoutMs) });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

async function serverHealthy() {
  try {
    const health = await fetchJson(`${serverUrl}/api/health`);
    return health?.status === 'ok';
  } catch {
    return false;
  }
}

async function ollamaTags() {
  try {
    return await fetchJson(`${cfg.ollamaBaseUrl}/api/tags`);
  } catch {
    return null;
  }
}

function readPid() {
  try {
    const pid = Number(fs.readFileSync(pidFile, 'utf8').trim());
    return Number.isInteger(pid) && pid > 0 ? pid : null;
  } catch {
    return null;
  }
}

function processAlive(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

async function waitFor(check, timeoutMs, stepMs = 500) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (await check()) return true;
    await new Promise((r) => setTimeout(r, stepMs));
  }
  return check();
}

function openBrowser(url) {
  // `start` must go through cmd on Windows; harmless fallback elsewhere.
  if (process.platform === 'win32') {
    spawn('cmd', ['/c', 'start', '', url], { detached: true, stdio: 'ignore' }).unref();
  } else {
    spawn('xdg-open', [url], { detached: true, stdio: 'ignore' }).unref();
  }
}

async function ensureOllama() {
  let tags = await ollamaTags();
  if (!tags) {
    log('  • Ollama is not responding — trying to start it…');
    try {
      spawn('ollama', ['serve'], { detached: true, stdio: 'ignore' }).unref();
    } catch {
      // handled by the wait below
    }
    const up = await waitFor(async () => (await ollamaTags()) !== null, 12000, 750);
    if (!up) {
      fail(
        `Ollama is not running and could not be started automatically.\n` +
          `    Start it from the Start Menu (Ollama app) or run "ollama serve" in a terminal,\n` +
          `    then run this launcher again. Install from https://ollama.com if it is missing.`,
      );
      return null;
    }
    tags = await ollamaTags();
  }
  log('  ✓ Ollama is running');

  if (!cfg.ollamaModel) {
    fail('OLLAMA_MODEL is not set in .env — set it (e.g. OLLAMA_MODEL=qwen3:8b-q4_K_M).');
    return null;
  }
  if (!modelInstalled(tags, cfg.ollamaModel)) {
    fail(
      `The configured model "${cfg.ollamaModel}" is not installed.\n` +
        `    Install it with:  ollama pull ${cfg.ollamaModel}\n` +
        `    Then run this launcher again.`,
    );
    return null;
  }
  log(`  ✓ Model ${cfg.ollamaModel} is installed`);
  return tags;
}

async function warmUpModel() {
  log(`  • Warming up ${cfg.ollamaModel} (keep-alive ${cfg.ollamaKeepAlive})…`);
  try {
    // An empty prompt loads the model into memory without generating output.
    await fetchJson(
      `${cfg.ollamaBaseUrl}/api/generate`,
      {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ model: cfg.ollamaModel, prompt: '', keep_alive: cfg.ollamaKeepAlive }),
      },
      120000,
    );
    log('  ✓ Model is loaded and warm');
  } catch {
    log('  ! Warm-up did not finish — the first reply may be slow, but JARVIS will still work.');
  }
}

function ensureBuilt() {
  const bundle = path.join(projectRoot, 'dist', 'server', 'index.js');
  const client = path.join(projectRoot, 'dist', 'client', 'index.html');
  if (!rebuild && fs.existsSync(bundle) && fs.existsSync(client)) return true;
  log(rebuild ? '  • Rebuilding JARVIS…' : '  • First run: building JARVIS (about a minute)…');
  const result = spawnSync('npm', ['run', 'build'], {
    cwd: projectRoot,
    stdio: 'inherit',
    shell: true,
  });
  if (result.status !== 0) {
    fail('The build failed — see the output above.');
    return false;
  }
  return true;
}

function startServer() {
  fs.mkdirSync(logDir, { recursive: true });
  const out = fs.openSync(logFile, 'a');
  const child = spawn(process.execPath, [path.join('dist', 'server', 'index.js')], {
    cwd: projectRoot,
    detached: true,
    stdio: ['ignore', out, out],
    env: { ...process.env, NODE_ENV: 'production' },
  });
  fs.mkdirSync(dataDir, { recursive: true });
  fs.writeFileSync(pidFile, String(child.pid));
  child.unref();
  return child.pid;
}

async function commandStart() {
  log('\nJARVIS launcher');
  log('────────────────');

  if (await serverHealthy()) {
    log(`  ✓ JARVIS is already running at ${serverUrl} — opening it (no second server started).`);
    openBrowser(serverUrl);
    return;
  }
  const stalePid = readPid();
  if (stalePid && processAlive(stalePid)) {
    fail(
      `A JARVIS process (PID ${stalePid}) exists but is not answering on ${serverUrl}.\n` +
        `    Run "npm run jarvis:stop" first, then start again.`,
    );
    return;
  }

  if (cfg.modelProvider === 'ollama') {
    if (!(await ensureOllama())) return;
    await warmUpModel();
  } else {
    log(`  • Model provider is "${cfg.modelProvider}" — skipping Ollama checks.`);
  }

  if (!ensureBuilt()) return;

  log('  • Starting the JARVIS server…');
  const pid = startServer();
  const up = await waitFor(serverHealthy, 15000);
  if (!up) {
    fail(
      `The server (PID ${pid}) did not become healthy on ${serverUrl}.\n` +
        `    Check the log: ${logFile}`,
    );
    return;
  }
  log(`  ✓ JARVIS is running at ${serverUrl} (PID ${pid})`);
  log(`  • Log file: ${logFile}`);
  openBrowser(serverUrl);
  log('\n  Stop later with:  npm run jarvis:stop\n');
}

async function commandStop() {
  const pid = readPid();
  const healthy = await serverHealthy();
  if (!pid && !healthy) {
    log('JARVIS is not running.');
    return;
  }
  if (pid && processAlive(pid)) {
    process.kill(pid);
    const gone = await waitFor(async () => !processAlive(pid), 5000, 250);
    log(gone ? `Stopped JARVIS (PID ${pid}).` : `Sent stop to PID ${pid}; it may take a moment.`);
  } else if (healthy) {
    log(
      `A JARVIS server answers on ${serverUrl} but was not started by this launcher.\n` +
        `Close it in the terminal where it was started (Ctrl+C).`,
    );
  } else {
    log('JARVIS is not running (cleaning up a stale PID file).');
  }
  try {
    fs.rmSync(pidFile, { force: true });
  } catch {
    // best-effort cleanup
  }
}

async function commandStatus() {
  log(`Server:  ${(await serverHealthy()) ? `running at ${serverUrl}` : 'not running'}`);
  const tags = await ollamaTags();
  log(`Ollama:  ${tags ? 'running' : 'not running'}`);
  if (tags && cfg.ollamaModel) {
    log(
      `Model:   ${cfg.ollamaModel} ${modelInstalled(tags, cfg.ollamaModel) ? 'installed' : `MISSING — run: ollama pull ${cfg.ollamaModel}`}`,
    );
  }
}

switch (command) {
  case 'start':
    await commandStart();
    break;
  case 'stop':
    await commandStop();
    break;
  case 'restart':
    await commandStop();
    await commandStart();
    break;
  case 'status':
    await commandStatus();
    break;
  default:
    log(`Unknown command "${command}". Use: start | stop | restart | status`);
    process.exitCode = 1;
}
