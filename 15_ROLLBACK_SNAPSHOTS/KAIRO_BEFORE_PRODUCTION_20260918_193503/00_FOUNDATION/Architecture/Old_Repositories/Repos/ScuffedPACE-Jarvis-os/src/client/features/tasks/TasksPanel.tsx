import { useCallback, useEffect, useState } from 'react';
import { RefreshCw, X } from 'lucide-react';
import type { PendingAction } from '../../../shared/types';

interface TasksPanelProps {
  onClose: () => void;
  onDecide: (action: PendingAction) => void;
}

const STATUS_STYLE: Record<string, string> = {
  pending: 'var(--warn, #f0b64a)',
  approved: 'var(--warn, #f0b64a)',
  completed: 'var(--ok, #37d99a)',
  simulated_completed: 'var(--ok, #37d99a)',
  failed: 'var(--danger, #ef6a6a)',
  cancelled: 'var(--text-dim)',
  expired: 'var(--text-dim)',
};

/**
 * Unified tasks & approvals view: everything JARVIS has proposed, what was
 * approved/cancelled/failed, and pending items that can be decided now.
 */
export function TasksPanel({ onClose, onDecide }: TasksPanelProps) {
  const [actions, setActions] = useState<PendingAction[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback((): void => {
    fetch('/api/actions?limit=100')
      .then(async (r) => {
        if (!r.ok) throw new Error(String(r.status));
        const body = (await r.json()) as { actions: PendingAction[] };
        setActions(body.actions);
      })
      .catch(() => setError('Could not load the action history.'));
  }, []);
  useEffect(refresh, [refresh]);

  const now = Date.now();

  return (
    <div className="panel-overlay" role="dialog" aria-modal="true" aria-label="Tasks and approvals">
      <div className="panel">
        <header>
          <h2>Tasks &amp; approvals</h2>
          <button type="button" className="btn" onClick={refresh} aria-label="Refresh actions">
            <RefreshCw size={13} />
          </button>
          <button type="button" className="btn" onClick={onClose} aria-label="Close tasks panel">
            <X size={14} />
          </button>
        </header>
        <p style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 0 }}>
          Every consequential action JARVIS proposes lands here. Approval is single-use and applies
          only to the exact action shown; old approvals expire automatically.
        </p>
        {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}

        {actions === null ? (
          <p>Loading…</p>
        ) : actions.length === 0 ? (
          <p style={{ color: 'var(--text-dim)' }}>
            Nothing yet. When JARVIS proposes something consequential (sending an email, changing
            the calendar…), it will appear here for your decision.
          </p>
        ) : (
          <ul className="memory-list">
            {actions.map((action) => {
              const decidable =
                action.status === 'pending' && Date.parse(action.expiresAt) > now;
              return (
                <li key={action.id} className="memory-item" style={{ alignItems: 'flex-start' }}>
                  <span className="kind" style={{ color: STATUS_STYLE[action.status] }}>
                    {action.status.replace('_', ' ')}
                  </span>
                  <span style={{ flex: 1 }}>
                    <strong>{action.summary || action.actionType}</strong>
                    <span style={{ display: 'block', fontSize: 11, color: 'var(--text-dim)' }}>
                      {action.target && `${action.target} · `}
                      {new Date(action.createdAt).toLocaleString()}
                      {action.decidedBy ? ` · decided by ${action.decidedBy}` : ''}
                    </span>
                    {action.executionError && (
                      <span style={{ display: 'block', fontSize: 11, color: 'var(--danger)' }}>
                        {action.executionError}
                      </span>
                    )}
                  </span>
                  {decidable && (
                    <button type="button" className="btn primary" onClick={() => onDecide(action)}>
                      Review
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
