import { spawn } from 'node:child_process';
import type { ProviderStatus } from '../../../shared/types';
import type { ServerConfig } from '../../config/env';
import {
  ModelProviderError,
  type ModelCompletionRequest,
  type ModelCompletionResult,
  type ModelProvider,
} from './types';

/**
 * Optional bridge to the owner's locally installed, already-authenticated
 * Claude CLI. Boundaries:
 * - No API key is used or required; the CLI's own login and limits apply.
 * - Disabled by default (CLAUDE_CLI_ENABLED=true opts in).
 * - Only the allowlisted `claude` executable is ever spawned, with fixed
 *   literal arguments; the prompt travels via stdin, never through a shell
 *   string, so no shell injection is possible.
 * - Timeout, cancellation, and output-size limits are enforced; failures are
 *   normalized and never silently fall back to another provider.
 * - Registered-project content is approval-gated upstream before it can be
 *   sent through this provider.
 */

const MAX_OUTPUT_BYTES = 1024 * 1024;

/** Bare "claude" or an absolute path ending in claude(.cmd/.exe). */
const COMMAND_PATTERN = /^(claude(\.cmd|\.exe)?|(?:[A-Za-z]:)?[\\/](?:[^<>|?*\n]+[\\/])*claude(\.cmd|\.exe)?)$/i;

export interface CliRunResult {
  exitCode: number | null;
  stdout: string;
  stderr: string;
  timedOut: boolean;
}

export type CliRunner = (options: {
  command: string;
  args: string[];
  stdin: string;
  timeoutMs: number;
  signal?: AbortSignal;
}) => Promise<CliRunResult>;

/** Default runner: controlled subprocess, bounded output, no shell parsing of data. */
export const spawnCliRunner: CliRunner = ({ command, args, stdin, timeoutMs, signal }) =>
  new Promise((resolve, reject) => {
    // Windows .cmd shims need a shell to launch, but every argument is a
    // fixed literal and the prompt goes via stdin — nothing user-controlled
    // is ever interpreted by the shell.
    const child = spawn(command, args, {
      shell: process.platform === 'win32',
      windowsHide: true,
      stdio: ['pipe', 'pipe', 'pipe'],
    });
    let stdout = '';
    let stderr = '';
    let timedOut = false;
    let settled = false;

    const timer = setTimeout(() => {
      timedOut = true;
      child.kill();
    }, timeoutMs);
    const onAbort = (): void => {
      child.kill();
    };
    signal?.addEventListener('abort', onAbort, { once: true });
    if (signal?.aborted) child.kill();

    child.stdout.on('data', (chunk: Buffer) => {
      stdout += chunk.toString('utf8');
      if (stdout.length > MAX_OUTPUT_BYTES) {
        stdout = stdout.slice(0, MAX_OUTPUT_BYTES);
        child.kill();
      }
    });
    child.stderr.on('data', (chunk: Buffer) => {
      if (stderr.length < 64 * 1024) stderr += chunk.toString('utf8');
    });
    child.on('error', (error) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      signal?.removeEventListener('abort', onAbort);
      reject(error);
    });
    child.on('close', (code) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      signal?.removeEventListener('abort', onAbort);
      resolve({ exitCode: code, stdout, stderr, timedOut });
    });

    child.stdin.on('error', () => undefined); // broken pipe if the CLI exits early
    child.stdin.write(stdin);
    child.stdin.end();
  });

export class ClaudeCliProvider implements ModelProvider {
  readonly id = 'claude_cli' as const;
  readonly label = 'Claude CLI (local)';

  private readonly config: ServerConfig;
  private readonly runner: CliRunner;

  constructor(config: ServerConfig, runner: CliRunner = spawnCliRunner) {
    this.config = config;
    this.runner = runner;
  }

  private configurationError(): string | null {
    if (!this.config.claudeCliEnabled) {
      return 'The Claude CLI bridge is disabled. Set CLAUDE_CLI_ENABLED=true in .env to opt in.';
    }
    if (!COMMAND_PATTERN.test(this.config.claudeCliCommand)) {
      return 'CLAUDE_CLI_COMMAND must be "claude" or an absolute path to the claude executable.';
    }
    return null;
  }

  status(): ProviderStatus {
    const configurationError = this.configurationError();
    return {
      mode: 'claude_cli',
      label: 'Claude CLI (local, uses your existing Claude login)',
      configured: configurationError === null,
      configurationError,
      fastModel: 'claude-cli',
      deepModel: 'claude-cli',
    };
  }

  usesLocalCli(): boolean {
    return true;
  }

  async complete(request: ModelCompletionRequest): Promise<ModelCompletionResult> {
    const configurationError = this.configurationError();
    if (configurationError) {
      throw new ModelProviderError('not_configured', configurationError, false);
    }

    // One self-contained prompt document via stdin. The CLI treats it as the
    // user prompt; conversation roles are laid out explicitly.
    const transcript = request.messages
      .map((m) => `${m.role === 'user' ? 'Farhan' : 'JARVIS'}: ${m.content}`)
      .join('\n\n');
    const stdin = `${request.system}\n\n--- Conversation so far ---\n${transcript}\n\n--- Instruction ---\nReply as JARVIS to Farhan's last message above. Reply with the message text only.`;

    let run: CliRunResult;
    try {
      run = await this.runner({
        command: this.config.claudeCliCommand,
        args: ['-p', '--output-format', 'json'],
        stdin,
        timeoutMs: this.config.claudeCliTimeoutMs,
        signal: request.signal,
      });
    } catch (error) {
      if (request.signal?.aborted) {
        throw new ModelProviderError('cancelled', 'The request was interrupted.');
      }
      const code = (error as NodeJS.ErrnoException).code;
      if (code === 'ENOENT') {
        throw new ModelProviderError(
          'not_configured',
          'The Claude CLI is not installed or not on PATH. Install Claude Code and run "claude" once to log in, or set CLAUDE_CLI_COMMAND to its full path.',
          false,
        );
      }
      throw new ModelProviderError('api_error', 'The Claude CLI could not be started.');
    }

    if (request.signal?.aborted) {
      throw new ModelProviderError('cancelled', 'The request was interrupted.');
    }
    if (run.timedOut) {
      throw new ModelProviderError(
        'timeout',
        `The Claude CLI timed out after ${Math.round(this.config.claudeCliTimeoutMs / 1000)}s.`,
      );
    }
    if (run.exitCode !== 0) {
      const hint = /log ?in|auth|credential/i.test(run.stderr)
        ? ' It may not be logged in — run "claude" in a terminal and sign in.'
        : '';
      throw new ModelProviderError(
        'api_error',
        `The Claude CLI exited with an error.${hint} Nothing was retried.`,
      );
    }

    let text: string;
    try {
      const parsed = JSON.parse(run.stdout) as {
        result?: string;
        is_error?: boolean;
        [key: string]: unknown;
      };
      if (parsed.is_error === true || typeof parsed.result !== 'string') {
        throw new Error('cli error payload');
      }
      text = parsed.result.trim();
    } catch {
      throw new ModelProviderError('api_error', 'The Claude CLI returned an unexpected response.');
    }

    return { text, provider: this.label, model: 'claude-cli', simulated: false };
  }
}
