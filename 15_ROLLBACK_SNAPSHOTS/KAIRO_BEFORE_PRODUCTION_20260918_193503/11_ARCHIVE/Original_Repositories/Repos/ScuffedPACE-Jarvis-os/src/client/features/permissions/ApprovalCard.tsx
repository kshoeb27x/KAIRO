import { useState } from 'react';
import { ShieldAlert } from 'lucide-react';
import type { PendingAction } from '../../../shared/types';

interface ApprovalCardProps {
  action: PendingAction;
  onDecide: (decision: 'approve' | 'cancel') => Promise<void>;
}

function isMailDraft(
  payload: PendingAction['payload'],
): payload is { to: string; subject: string; body: string } {
  return (
    typeof payload.to === 'string' &&
    typeof payload.subject === 'string' &&
    typeof payload.body === 'string'
  );
}

/**
 * Approval gate for a consequential action. What is shown is the
 * server-stored action record — the proposed change, the affected target,
 * the reason, and the consequences. Deciding calls the server, which records
 * a single-use decision; execution happens only after approval.
 */
export function ApprovalCard({ action, onDecide }: ApprovalCardProps) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const simulated = action.actionType === 'simulated_send';

  const decide = async (decision: 'approve' | 'cancel'): Promise<void> => {
    setBusy(true);
    setError(null);
    try {
      await onDecide(decision);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'The decision could not be recorded.');
      setBusy(false);
    }
  };

  return (
    <div className="approval-overlay" role="dialog" aria-modal="true" aria-label="Approval required">
      <div className="approval-card">
        <h2>
          <ShieldAlert size={17} /> Approval required{' '}
          {simulated && <span className="tag sim">Simulated</span>}
        </h2>
        {action.summary && (
          <p>
            <strong>{action.summary}</strong>
          </p>
        )}
        {action.target && (
          <p style={{ margin: '2px 0' }}>
            <strong>Affects:</strong> {action.target}
          </p>
        )}
        {action.reason && (
          <p style={{ margin: '2px 0' }}>
            <strong>Why:</strong> {action.reason}
          </p>
        )}
        {action.consequences && (
          <p style={{ margin: '2px 0' }}>
            <strong>Consequences:</strong> {action.consequences}
          </p>
        )}
        <p style={{ color: 'var(--text-dim)' }}>
          This request expires {new Date(action.expiresAt).toLocaleTimeString()}. Approval applies
          only to exactly this action.
        </p>
        {isMailDraft(action.payload) ? (
          <div className="draft">
            <div>
              <strong>To:</strong> {action.payload.to}
            </div>
            <div>
              <strong>Subject:</strong> {action.payload.subject}
            </div>
            <hr style={{ border: 'none', borderTop: '1px solid var(--line)' }} />
            {action.payload.body}
          </div>
        ) : (
          <div className="draft">
            {Object.entries(action.payload)
              // Keys prefixed with "_" carry execution data already
              // summarized in the visible fields above.
              .filter(([key]) => !key.startsWith('_'))
              .map(([key, value]) => (
                <div key={key} style={{ whiteSpace: 'pre-wrap' }}>
                  <strong>{key}:</strong>{' '}
                  {typeof value === 'string' ? value : JSON.stringify(value)}
                </div>
              ))}
          </div>
        )}
        {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}
        <div className="approval-actions">
          <button type="button" className="btn" disabled={busy} onClick={() => void decide('cancel')}>
            Cancel
          </button>
          <button
            type="button"
            className="btn primary"
            disabled={busy}
            onClick={() => void decide('approve')}
          >
            {simulated ? 'Approve simulated send' : 'Approve'}
          </button>
        </div>
      </div>
    </div>
  );
}
