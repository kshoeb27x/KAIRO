import type { AppState } from '../app/stateMachine';
import type { ExplanationDepth, ProviderStatus } from '../../shared/types';

interface StatusStripProps {
  appState: AppState;
  appVersion: string | null;
  provider: ProviderStatus | null;
  serverHealthy: boolean;
  recognitionSupported: boolean;
  synthesisSupported: boolean;
  autoSpeak: boolean;
  onToggleAutoSpeak: () => void;
  explanationDepth: ExplanationDepth;
  onChangeExplanationDepth: (depth: ExplanationDepth) => void;
}

/**
 * Persistent status strip. Every indicator derives from real feature
 * detection, backend health, and provider configuration — never fabricated.
 */
export function StatusStrip({
  appState,
  appVersion,
  provider,
  serverHealthy,
  recognitionSupported,
  synthesisSupported,
  autoSpeak,
  onToggleAutoSpeak,
  explanationDepth,
  onChangeExplanationDepth,
}: StatusStripProps) {
  return (
    <footer className="status-strip" aria-label="System status">
      <span className="item">
        <span className={`dot ${serverHealthy ? 'ok' : 'err'}`} aria-hidden="true" />
        Server {serverHealthy ? 'online' : 'offline'}
      </span>
      <span className="item">
        <span
          className={`dot ${provider ? (provider.mode === 'mock' ? 'warn' : provider.configured ? 'ok' : 'err') : 'off'}`}
          aria-hidden="true"
        />
        {provider
          ? provider.mode === 'mock'
            ? 'Demo Provider (no real model)'
            : provider.mode === 'ollama'
              ? provider.configured
                ? `Local Ollama (${provider.fastModel ?? 'model unset'})${provider.deepModel === 'claude-cli' ? ' + Claude CLI' : ''}`
                : `Ollama: ${provider.configurationError ?? 'not configured'}`
              : provider.mode === 'claude_cli'
                ? provider.configured
                  ? 'Claude CLI (local)'
                  : `Claude CLI: ${provider.configurationError ?? 'not configured'}`
                : provider.configured
                  ? 'Anthropic configured'
                  : `Anthropic: ${provider.configurationError ?? 'not configured'}`
          : 'Provider unknown'}
      </span>
      <span className="item">
        <span className={`dot ${recognitionSupported ? 'ok' : 'off'}`} aria-hidden="true" />
        Speech in {recognitionSupported ? 'ready' : 'unavailable'}
      </span>
      <span className="item">
        <span className={`dot ${synthesisSupported ? 'ok' : 'off'}`} aria-hidden="true" />
        Speech out {synthesisSupported ? 'ready' : 'unavailable'}
      </span>
      <button
        type="button"
        className="btn"
        style={{ padding: '2px 10px', fontSize: 11 }}
        onClick={onToggleAutoSpeak}
        aria-pressed={autoSpeak}
      >
        Auto-speak: {autoSpeak ? 'on' : 'off'}
      </button>
      <label className="item" style={{ gap: 6 }}>
        Explain:
        <select
          aria-label="Explanation depth"
          value={explanationDepth}
          onChange={(e) => onChangeExplanationDepth(e.target.value as ExplanationDepth)}
          style={{
            background: 'transparent',
            color: 'inherit',
            border: '1px solid var(--line, #2a3a4a)',
            borderRadius: 4,
            fontSize: 11,
            padding: '1px 4px',
          }}
        >
          <option value="simple">simple</option>
          <option value="normal">normal</option>
          <option value="technical">technical</option>
        </select>
      </label>
      <span className="item" style={{ marginLeft: 'auto' }}>
        State: {appState}
        {appVersion ? ` · v${appVersion}` : ''}
      </span>
    </footer>
  );
}
