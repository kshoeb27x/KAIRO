import { useCallback, useEffect, useState } from 'react';
import { RefreshCw, X } from 'lucide-react';
import type { PendingAction } from '../../../shared/types';
import { useGoogleStatus } from './useGoogleStatus';

interface MailPanelProps {
  onClose: () => void;
  onActionCreated: (action: PendingAction) => void;
}

interface MailSummary {
  id: string;
  from: string;
  subject: string;
  date: string;
  snippet: string;
  unread: boolean;
  threadId: string;
}

interface MailBody extends MailSummary {
  to: string;
  text: string;
}

async function parseError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { error?: { message?: string } };
    return body.error?.message ?? `Request failed (${response.status})`;
  } catch {
    return `Request failed (${response.status})`;
  }
}

/**
 * Gmail, read-first: browsing and analysis are read-only; send, archive, and
 * delete only create approval requests — nothing touches the account until
 * the owner approves the exact stored action.
 */
export function MailPanel({ onClose, onActionCreated }: MailPanelProps) {
  const google = useGoogleStatus();
  const [messages, setMessages] = useState<MailSummary[] | null>(null);
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState<MailBody | null>(null);
  const [analysis, setAnalysis] = useState<{ mode: string; text: string; provider: string } | null>(null);
  const [replyDraft, setReplyDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (q?: string): Promise<void> => {
      setError(null);
      const params = q ? `?q=${encodeURIComponent(q)}` : '';
      const response = await fetch(`/api/mail/messages${params}`);
      if (!response.ok) {
        setError(await parseError(response));
        setMessages(null);
        return;
      }
      const body = (await response.json()) as { messages: MailSummary[] };
      setMessages(body.messages);
    },
    [],
  );

  useEffect(() => {
    if (google.status?.connected) void load();
  }, [google.status?.connected, load]);

  const openMessage = async (id: string): Promise<void> => {
    setAnalysis(null);
    setReplyDraft('');
    setError(null);
    const response = await fetch(`/api/mail/messages/${id}`);
    if (!response.ok) {
      setError(await parseError(response));
      return;
    }
    const body = (await response.json()) as { message: MailBody };
    setOpen(body.message);
  };

  const analyze = async (mode: 'summarize' | 'extract' | 'draft_reply'): Promise<void> => {
    if (!open) return;
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(`/api/mail/messages/${open.id}/analyze`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ mode }),
      });
      if (!response.ok) {
        setError(await parseError(response));
        return;
      }
      const body = (await response.json()) as { mode: string; text: string; provider: string };
      if (mode === 'draft_reply') setReplyDraft(body.text);
      else setAnalysis(body);
    } finally {
      setBusy(false);
    }
  };

  const propose = async (payload: Record<string, unknown>): Promise<void> => {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch('/api/mail/actions', {
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
    <div className="panel-overlay" role="dialog" aria-modal="true" aria-label="Mail">
      <div className="panel">
        <header>
          <h2>Mail {status?.accountEmail ? `— ${status.accountEmail}` : ''}</h2>
          <button type="button" className="btn" onClick={onClose} aria-label="Close mail panel">
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
            <p style={{ fontSize: 11, color: 'var(--text-dim)' }}>
              After approving in the browser tab, come back and press refresh.
            </p>
            <button type="button" className="btn" onClick={google.refresh}>
              <RefreshCw size={13} /> Refresh connection state
            </button>
          </div>
        ) : (
          <>
            <div style={{ display: 'flex', gap: 6, marginBottom: 8, flexWrap: 'wrap' }}>
              <input
                className="command-input"
                placeholder="Search mail (e.g. is:unread, from:someone)…"
                aria-label="Search mail"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && void load(query)}
                style={{ flex: '1 1 220px' }}
              />
              <button type="button" className="btn" onClick={() => void load(query)}>
                Search
              </button>
              <button type="button" className="btn" onClick={() => void load()}>
                <RefreshCw size={13} />
              </button>
              {!status.actionsEnabled && (
                <button type="button" className="btn" onClick={() => void google.connect('actions')}>
                  Enable actions (send/archive/delete)
                </button>
              )}
              <button type="button" className="btn forget" onClick={() => void google.disconnect()}>
                Disconnect
              </button>
            </div>
            {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}

            {open ? (
              <div>
                <button type="button" className="btn" onClick={() => setOpen(null)}>
                  ← Back to list
                </button>
                <h3 style={{ margin: '8px 0 2px' }}>{open.subject}</h3>
                <p style={{ fontSize: 11, color: 'var(--text-dim)', margin: 0 }}>
                  From {open.from} · {open.date}
                </p>
                <div className="draft" style={{ maxHeight: 200, overflowY: 'auto', whiteSpace: 'pre-wrap' }}>
                  {open.text || '(no readable text body)'}
                </div>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', margin: '8px 0' }}>
                  <button type="button" className="btn" disabled={busy} onClick={() => void analyze('summarize')}>
                    Summarize
                  </button>
                  <button type="button" className="btn" disabled={busy} onClick={() => void analyze('extract')}>
                    Extract tasks/dates
                  </button>
                  <button type="button" className="btn" disabled={busy} onClick={() => void analyze('draft_reply')}>
                    Draft a reply
                  </button>
                  {status.actionsEnabled && (
                    <>
                      <button
                        type="button"
                        className="btn"
                        disabled={busy}
                        onClick={() => void propose({ type: 'archive', messageId: open.id, subject: open.subject })}
                      >
                        Archive…
                      </button>
                      <button
                        type="button"
                        className="btn forget"
                        disabled={busy}
                        onClick={() => void propose({ type: 'delete', messageId: open.id, subject: open.subject })}
                      >
                        Delete…
                      </button>
                    </>
                  )}
                </div>
                {analysis && (
                  <div className="draft" style={{ whiteSpace: 'pre-wrap' }}>
                    <strong>{analysis.mode === 'extract' ? 'Extracted items' : 'Summary'}</strong>{' '}
                    <span style={{ fontSize: 10, color: 'var(--text-dim)' }}>({analysis.provider})</span>
                    {'\n'}
                    {analysis.text}
                  </div>
                )}
                {replyDraft !== '' && (
                  <div>
                    <p style={{ margin: '8px 0 4px' }}>
                      <strong>Reply draft</strong> — edit freely; sending always asks for approval:
                    </p>
                    <textarea
                      className="command-input"
                      aria-label="Reply draft"
                      rows={5}
                      value={replyDraft}
                      onChange={(e) => setReplyDraft(e.target.value)}
                      style={{ width: '100%' }}
                    />
                    <button
                      type="button"
                      className="btn primary"
                      disabled={busy || !status.actionsEnabled}
                      title={status.actionsEnabled ? undefined : 'Enable actions first'}
                      onClick={() =>
                        void propose({
                          type: 'send',
                          to: open.from,
                          subject: open.subject.startsWith('Re:') ? open.subject : `Re: ${open.subject}`,
                          body: replyDraft,
                          inReplyToMessageId: open.id,
                          threadId: open.threadId,
                        })
                      }
                    >
                      Send (asks for approval)
                    </button>
                  </div>
                )}
              </div>
            ) : messages === null ? (
              <p>Loading…</p>
            ) : messages.length === 0 ? (
              <p style={{ color: 'var(--text-dim)' }}>No messages matched.</p>
            ) : (
              <ul className="memory-list">
                {messages.map((message) => (
                  <li key={message.id} className="memory-item">
                    {message.unread && <span className="kind">unread</span>}
                    <button
                      type="button"
                      className="btn"
                      style={{ flex: 1, textAlign: 'left' }}
                      onClick={() => void openMessage(message.id)}
                    >
                      <strong>{message.subject}</strong>
                      <span style={{ display: 'block', fontSize: 11, color: 'var(--text-dim)' }}>
                        {message.from} · {message.snippet.slice(0, 80)}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </div>
    </div>
  );
}
