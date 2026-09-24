import { useCallback, useEffect, useState } from 'react';
import { RefreshCw, X } from 'lucide-react';
import type { PendingAction } from '../../../shared/types';
import { useGoogleStatus } from './useGoogleStatus';

interface CalendarPanelProps {
  onClose: () => void;
  onActionCreated: (action: PendingAction) => void;
}

interface CalendarEvent {
  id: string;
  summary: string;
  start: string;
  end: string;
  allDay: boolean;
  location: string | null;
  attendees: number;
}

interface Conflict {
  first: string;
  second: string;
  start: string;
}

async function parseError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { error?: { message?: string } };
    return body.error?.message ?? `Request failed (${response.status})`;
  } catch {
    return `Request failed (${response.status})`;
  }
}

function formatTime(iso: string, allDay: boolean): string {
  if (allDay) return iso;
  const date = new Date(iso);
  return `${date.toLocaleDateString()} ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
}

/**
 * Calendar, read-first: viewing, conflicts, and free-slot suggestions are
 * read-only. Creating, changing, deleting, or responding to events only
 * creates approval requests with a full preview.
 */
export function CalendarPanel({ onClose, onActionCreated }: CalendarPanelProps) {
  const google = useGoogleStatus();
  const [events, setEvents] = useState<CalendarEvent[] | null>(null);
  const [conflicts, setConflicts] = useState<Conflict[]>([]);
  const [slots, setSlots] = useState<Array<{ startIso: string; endIso: string }> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ summary: '', start: '', end: '' });

  const load = useCallback(async (): Promise<void> => {
    setError(null);
    const response = await fetch('/api/calendar/events');
    if (!response.ok) {
      setError(await parseError(response));
      setEvents(null);
      return;
    }
    const body = (await response.json()) as { events: CalendarEvent[]; conflicts: Conflict[] };
    setEvents(body.events);
    setConflicts(body.conflicts);
  }, []);

  useEffect(() => {
    if (google.status?.connected) void load();
  }, [google.status?.connected, load]);

  const suggest = async (): Promise<void> => {
    setError(null);
    const response = await fetch('/api/calendar/suggest');
    if (!response.ok) {
      setError(await parseError(response));
      return;
    }
    const body = (await response.json()) as { slots: Array<{ startIso: string; endIso: string }> };
    setSlots(body.slots);
  };

  const propose = async (payload: Record<string, unknown>): Promise<void> => {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch('/api/calendar/actions', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        setError(await parseError(response));
        return;
      }
      const body = (await response.json()) as { action: PendingAction };
      onActionCreated(body.action);
    } finally {
      setBusy(false);
    }
  };

  const status = google.status;

  return (
    <div className="panel-overlay" role="dialog" aria-modal="true" aria-label="Calendar">
      <div className="panel">
        <header>
          <h2>Calendar {status?.accountEmail ? `— ${status.accountEmail}` : ''}</h2>
          <button type="button" className="btn" onClick={onClose} aria-label="Close calendar panel">
            <X size={14} />
          </button>
        </header>

        {!status ? (
          <p>Loading…</p>
        ) : !status.connected ? (
          <div>
            <p style={{ color: 'var(--text-dim)' }}>{status.setupMessage}</p>
            {status.configured && (
              <button type="button" className="btn primary" onClick={() => void google.connect('read')}>
                Connect Google (read-only)
              </button>
            )}
            <button type="button" className="btn" onClick={google.refresh} style={{ marginLeft: 6 }}>
              <RefreshCw size={13} /> Refresh connection state
            </button>
          </div>
        ) : (
          <>
            <div style={{ display: 'flex', gap: 6, marginBottom: 8, flexWrap: 'wrap' }}>
              <button type="button" className="btn" onClick={() => void load()}>
                <RefreshCw size={13} /> Next 7 days
              </button>
              <button type="button" className="btn" onClick={() => void suggest()}>
                Suggest free slots (24h)
              </button>
              {!status.actionsEnabled && (
                <button type="button" className="btn" onClick={() => void google.connect('actions')}>
                  Enable actions (create/change events)
                </button>
              )}
              <button type="button" className="btn forget" onClick={() => void google.disconnect()}>
                Disconnect
              </button>
            </div>
            {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}

            {conflicts.length > 0 && (
              <div className="error-banner" role="status">
                <span>
                  Conflicts:{' '}
                  {conflicts.map((c) => `"${c.first}" overlaps "${c.second}"`).join('; ')}
                </span>
              </div>
            )}
            {slots && (
              <div className="draft">
                <strong>Free slots:</strong>
                {slots.length === 0
                  ? ' none of 30+ minutes in the next 24 hours.'
                  : slots.map((s) => (
                      <div key={s.startIso}>
                        {formatTime(s.startIso, false)} → {formatTime(s.endIso, false)}
                      </div>
                    ))}
              </div>
            )}

            {events === null ? (
              <p>Loading…</p>
            ) : events.length === 0 ? (
              <p style={{ color: 'var(--text-dim)' }}>Nothing scheduled in the next 7 days.</p>
            ) : (
              <ul className="memory-list">
                {events.map((event) => (
                  <li key={event.id} className="memory-item">
                    <span style={{ flex: 1 }}>
                      <strong>{event.summary}</strong>
                      <span style={{ display: 'block', fontSize: 11, color: 'var(--text-dim)' }}>
                        {formatTime(event.start, event.allDay)}
                        {event.allDay ? ' (all day)' : ` → ${formatTime(event.end, false)}`}
                        {event.location ? ` · ${event.location}` : ''}
                        {event.attendees > 1 ? ` · ${event.attendees} attendees` : ''}
                      </span>
                    </span>
                    {status.actionsEnabled && (
                      <button
                        type="button"
                        className="btn forget"
                        disabled={busy}
                        onClick={() =>
                          void propose({ type: 'delete', eventId: event.id, eventSummary: event.summary })
                        }
                      >
                        Delete…
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            )}

            {status.actionsEnabled && (
              <div style={{ marginTop: 10 }}>
                <strong style={{ fontSize: 12 }}>New event (asks for approval):</strong>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 4 }}>
                  <input
                    className="command-input"
                    placeholder="Title"
                    aria-label="Event title"
                    value={form.summary}
                    onChange={(e) => setForm({ ...form, summary: e.target.value })}
                    style={{ flex: '2 1 160px' }}
                  />
                  <input
                    className="command-input"
                    type="datetime-local"
                    aria-label="Event start"
                    value={form.start}
                    onChange={(e) => setForm({ ...form, start: e.target.value })}
                  />
                  <input
                    className="command-input"
                    type="datetime-local"
                    aria-label="Event end"
                    value={form.end}
                    onChange={(e) => setForm({ ...form, end: e.target.value })}
                  />
                  <button
                    type="button"
                    className="btn primary"
                    disabled={busy || !form.summary || !form.start || !form.end}
                    onClick={() =>
                      void propose({
                        type: 'create',
                        summary: form.summary,
                        startIso: new Date(form.start).toISOString(),
                        endIso: new Date(form.end).toISOString(),
                      })
                    }
                  >
                    Create…
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
