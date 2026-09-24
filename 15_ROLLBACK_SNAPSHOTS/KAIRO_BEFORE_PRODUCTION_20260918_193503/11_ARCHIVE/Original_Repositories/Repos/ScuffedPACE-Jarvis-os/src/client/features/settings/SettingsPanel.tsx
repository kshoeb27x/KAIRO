import { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import type { ExplanationDepth, Settings } from '../../../shared/types';
import { updateSettings } from '../../services/api';
import { useGoogleStatus } from '../google/useGoogleStatus';

interface SettingsPanelProps {
  onClose: () => void;
  settings: Settings;
  onSettingsChanged: (settings: Settings) => void;
  providerLabel: string;
}

/**
 * Settings plus the privacy / connected-services overview: what is
 * connected, where data lives, and how to disconnect. Voice preferences
 * (voice, rate, auto-speak) and explanation depth persist server-side.
 */
export function SettingsPanel({ onClose, settings, onSettingsChanged, providerLabel }: SettingsPanelProps) {
  const google = useGoogleStatus();
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!('speechSynthesis' in window)) return;
    const load = (): void => setVoices(window.speechSynthesis.getVoices());
    load();
    window.speechSynthesis.addEventListener('voiceschanged', load);
    return () => window.speechSynthesis.removeEventListener('voiceschanged', load);
  }, []);

  const save = async (patch: Partial<Settings>): Promise<void> => {
    setError(null);
    try {
      onSettingsChanged(await updateSettings(patch));
    } catch {
      setError('Could not save that setting.');
    }
  };

  const preview = (): void => {
    if (!('speechSynthesis' in window)) return;
    const utterance = new SpeechSynthesisUtterance('This is how JARVIS will sound.');
    utterance.rate = settings.speechRate;
    const voice = window.speechSynthesis.getVoices().find((v) => v.voiceURI === settings.voiceUri);
    if (voice) utterance.voice = voice;
    window.speechSynthesis.cancel();
    window.speechSynthesis.resume();
    window.speechSynthesis.speak(utterance);
  };

  return (
    <div className="panel-overlay" role="dialog" aria-modal="true" aria-label="Settings">
      <div className="panel">
        <header>
          <h2>Settings</h2>
          <button type="button" className="btn" onClick={onClose} aria-label="Close settings panel">
            <X size={14} />
          </button>
        </header>
        {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}

        <h3 style={{ fontSize: 13 }}>Voice</h3>
        <div style={{ display: 'grid', gap: 8 }}>
          <label style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <input
              type="checkbox"
              checked={settings.autoSpeak}
              onChange={(e) => void save({ autoSpeak: e.target.checked })}
            />
            Speak replies aloud automatically
          </label>
          <label style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            Voice:
            <select
              className="btn"
              aria-label="Voice"
              value={settings.voiceUri ?? ''}
              onChange={(e) => void save({ voiceUri: e.target.value || null })}
              style={{ maxWidth: 280 }}
            >
              <option value="">Browser default</option>
              {voices.map((voice) => (
                <option key={voice.voiceURI} value={voice.voiceURI}>
                  {voice.name} ({voice.lang}){voice.localService ? '' : ' — network'}
                </option>
              ))}
            </select>
          </label>
          <label style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            Speed:
            <input
              type="range"
              min={0.5}
              max={2}
              step={0.1}
              aria-label="Speaking rate"
              value={settings.speechRate}
              onChange={(e) => void save({ speechRate: Number(e.target.value) })}
            />
            {settings.speechRate.toFixed(1)}×
            <button type="button" className="btn" onClick={preview}>
              Preview
            </button>
          </label>
          <label style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            Explanations:
            <select
              className="btn"
              aria-label="Explanation depth setting"
              value={settings.explanationDepth}
              onChange={(e) => void save({ explanationDepth: e.target.value as ExplanationDepth })}
            >
              <option value="simple">simple — plain language, no jargon</option>
              <option value="normal">normal — everyday language</option>
              <option value="technical">technical — precise detail</option>
            </select>
          </label>
          <p style={{ fontSize: 11, color: 'var(--text-dim)', margin: 0 }}>
            Speech-to-text uses your browser's recognition service (in Chrome this is
            network-backed). A fully local option (Whisper) is possible later — it needs a model
            download of roughly 0.5–1.5 GB and will be offered for approval before anything is
            installed. Replies that look like they contain secrets are never read aloud.
          </p>
        </div>

        <h3 style={{ fontSize: 13, marginTop: 16 }}>Privacy &amp; connected services</h3>
        <ul style={{ fontSize: 12, lineHeight: 1.7, paddingLeft: 18 }}>
          <li>
            <strong>Model provider:</strong> {providerLabel}
          </li>
          <li>
            <strong>Google:</strong>{' '}
            {google.status === null
              ? 'checking…'
              : google.status.connected
                ? `connected as ${google.status.accountEmail ?? 'unknown'} (${google.status.actionsEnabled ? 'read + actions' : 'read-only'})`
                : (google.status.setupMessage ?? 'not connected')}
            {google.status?.connected && (
              <button
                type="button"
                className="btn forget"
                style={{ marginLeft: 8 }}
                onClick={() => void google.disconnect().then(google.refresh)}
              >
                Disconnect &amp; revoke
              </button>
            )}
          </li>
          <li>
            <strong>Your data</strong> lives in the local <code>.data</code> folder (SQLite,
            Google tokens, logs) — gitignored, never uploaded. Back up with{' '}
            <code>npm run backup</code>.
          </li>
          <li>
            <strong>Voice audio</strong> is only captured while you hold the mic button.
          </li>
        </ul>
      </div>
    </div>
  );
}
