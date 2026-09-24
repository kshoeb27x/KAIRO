import type { ActivityEvent } from '../../../shared/schemas/activity';
import type { ProviderStatus } from '../../../shared/types';

interface ActivityRailProps {
  events: ActivityEvent[];
  provider: ProviderStatus | null;
  serverHealthy: boolean;
  speechRecognitionSupported: boolean;
  speechSynthesisSupported: boolean;
  schemaVersion: number | null;
}

function kindClass(eventType: ActivityEvent['eventType']): string {
  switch (eventType) {
    case 'request.failed':
      return 'kind-failed';
    case 'permission.required':
      return 'kind-permission';
    case 'response.completed':
    case 'memory.saved':
    case 'tool.completed':
      return 'kind-done';
    case 'model.started':
    case 'tool.started':
      return 'kind-model';
    case 'route.selected':
      return 'kind-route';
    default:
      return '';
  }
}

/**
 * Renders real routing/tool/model events in arrival order — honest steps
 * only, no decorative animations and no fabricated percentages.
 */
export function ActivityRail({
  events,
  provider,
  serverHealthy,
  speechRecognitionSupported,
  speechSynthesisSupported,
  schemaVersion,
}: ActivityRailProps) {
  // Newest events at the top, preserving in-request ordering.
  const recent = [...events].slice(-40).reverse();

  return (
    <aside className="rail" aria-label="JARVIS activity">
      <div className="rail-section">
        <h2>Jarvis Activity</h2>
      </div>
      {recent.length === 0 ? (
        <p className="activity-empty">
          No activity yet. Ask JARVIS something and every real routing step will appear here.
        </p>
      ) : (
        <ol className="activity-list">
          {recent.map((event) => (
            <li key={event.eventId} className={`activity-item ${kindClass(event.eventType)}`}>
              <span>{event.label}</span>
              <time dateTime={event.occurredAt}>
                {new Date(event.occurredAt).toLocaleTimeString([], {
                  hour12: false,
                  hour: '2-digit',
                  minute: '2-digit',
                  second: '2-digit',
                })}
              </time>
            </li>
          ))}
        </ol>
      )}
      <div className="system-status">
        <h2>System Status</h2>
        <StatusRow
          label="Server"
          ok={serverHealthy}
          text={serverHealthy ? 'Connected' : 'Unreachable'}
        />
        <StatusRow
          label="Model provider"
          ok={provider?.configured ?? false}
          warn={provider?.mode === 'mock'}
          text={
            provider
              ? provider.mode === 'mock'
                ? 'Demo Provider'
                : provider.mode === 'ollama'
                  ? provider.configured
                    ? `Local Ollama (${provider.fastModel ?? 'model unset'})`
                    : 'Ollama not configured'
                  : provider.mode === 'claude_cli'
                    ? provider.configured
                      ? 'Claude CLI (local)'
                      : 'Claude CLI not enabled'
                    : provider.configured
                      ? `Claude (${provider.fastModel ?? 'configured'})`
                      : 'Not configured'
              : 'Unknown'
          }
        />
        <StatusRow
          label="Speech input"
          ok={speechRecognitionSupported}
          text={speechRecognitionSupported ? 'Available' : 'Not supported here'}
        />
        <StatusRow
          label="Speech output"
          ok={speechSynthesisSupported}
          text={speechSynthesisSupported ? 'Available' : 'Not supported here'}
        />
        <StatusRow
          label="Memory store"
          ok={schemaVersion !== null}
          text={schemaVersion !== null ? `SQLite schema v${schemaVersion}` : 'Unknown'}
        />
      </div>
    </aside>
  );
}

function StatusRow({
  label,
  ok,
  warn,
  text,
}: {
  label: string;
  ok: boolean;
  warn?: boolean;
  text: string;
}) {
  const dot = ok ? (warn ? 'warn' : 'ok') : 'err';
  return (
    <div className="status-row">
      <span>{label}</span>
      <span className="status-value">
        <span className={`dot ${dot}`} aria-hidden="true" />
        {text}
      </span>
    </div>
  );
}
