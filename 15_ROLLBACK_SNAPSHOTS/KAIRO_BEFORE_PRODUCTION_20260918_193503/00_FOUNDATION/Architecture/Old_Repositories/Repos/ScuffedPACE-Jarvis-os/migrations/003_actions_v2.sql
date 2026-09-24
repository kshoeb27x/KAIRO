-- Schema version 3: generalized approval-gated actions.
-- pending_actions becomes the unified task/approval/audit record: any tool
-- can propose an action with a human-readable summary, target, reason, and
-- consequences; execution happens only after an explicit approval and is
-- recorded exactly once. Existing rows are preserved unchanged.

CREATE TABLE pending_actions_v2 (
  id TEXT PRIMARY KEY,
  request_id TEXT NOT NULL,
  tool_name TEXT NOT NULL,
  action_type TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  summary TEXT NOT NULL DEFAULT '',
  target TEXT NOT NULL DEFAULT '',
  reason TEXT NOT NULL DEFAULT '',
  consequences TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
    'pending', 'approved', 'simulated_completed', 'completed',
    'failed', 'cancelled', 'expired'
  )),
  expires_at TEXT NOT NULL,
  created_at TEXT NOT NULL,
  decided_at TEXT,
  decided_by TEXT,
  executed_at TEXT,
  execution_error TEXT
);

INSERT INTO pending_actions_v2 (
  id, request_id, tool_name, action_type, payload_json,
  status, expires_at, created_at, decided_at, decided_by
)
SELECT
  id, request_id, tool_name, action_type, payload_json,
  status, expires_at, created_at, decided_at, decided_by
FROM pending_actions;

DROP TABLE pending_actions;
ALTER TABLE pending_actions_v2 RENAME TO pending_actions;
CREATE INDEX idx_pending_actions_status ON pending_actions(status, expires_at);
