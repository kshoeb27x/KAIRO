import { randomUUID } from 'node:crypto';
import type Database from 'better-sqlite3';
import type { PendingAction, PendingActionStatus } from '../../shared/types';
import { nowIso } from '../persistence/db';

interface PendingActionRow {
  id: string;
  request_id: string;
  tool_name: string;
  action_type: string;
  payload_json: string;
  summary: string;
  target: string;
  reason: string;
  consequences: string;
  status: string;
  expires_at: string;
  created_at: string;
  decided_at: string | null;
  decided_by: string | null;
  executed_at: string | null;
  execution_error: string | null;
}

function toPendingAction(row: PendingActionRow): PendingAction {
  return {
    id: row.id,
    requestId: row.request_id,
    toolName: row.tool_name,
    actionType: row.action_type,
    payload: JSON.parse(row.payload_json) as Record<string, unknown>,
    summary: row.summary,
    target: row.target,
    reason: row.reason,
    consequences: row.consequences,
    status: row.status as PendingActionStatus,
    expiresAt: row.expires_at,
    createdAt: row.created_at,
    decidedAt: row.decided_at,
    decidedBy: row.decided_by,
    executedAt: row.executed_at,
    executionError: row.execution_error,
  };
}

export type DecisionOutcome =
  | { ok: true; action: PendingAction }
  | { ok: false; reason: 'not_found' | 'expired' | 'already_decided' };

export function createPendingActionsRepository(db: Database.Database) {
  return {
    findById(id: string): PendingAction | null {
      const row = db.prepare('SELECT * FROM pending_actions WHERE id = ?').get(id) as
        | PendingActionRow
        | undefined;
      return row ? toPendingAction(row) : null;
    },

    listPending(now: string = nowIso()): PendingAction[] {
      const rows = db
        .prepare(
          `SELECT * FROM pending_actions WHERE status = 'pending' AND expires_at > ? ORDER BY created_at DESC`,
        )
        .all(now) as PendingActionRow[];
      return rows.map(toPendingAction);
    },

    /** Audit trail: newest first, optionally filtered by status. */
    listHistory(limit = 50, status?: PendingActionStatus): PendingAction[] {
      const rows = (
        status
          ? db
              .prepare(
                'SELECT * FROM pending_actions WHERE status = ? ORDER BY created_at DESC LIMIT ?',
              )
              .all(status, limit)
          : db.prepare('SELECT * FROM pending_actions ORDER BY created_at DESC LIMIT ?').all(limit)
      ) as PendingActionRow[];
      return rows.map(toPendingAction);
    },

    create(input: {
      requestId: string;
      toolName: string;
      actionType: string;
      payload: Record<string, unknown>;
      summary?: string;
      target?: string;
      reason?: string;
      consequences?: string;
      ttlMs: number;
    }): PendingAction {
      const now = new Date();
      const action: PendingAction = {
        id: randomUUID(),
        requestId: input.requestId,
        toolName: input.toolName,
        actionType: input.actionType,
        payload: input.payload,
        summary: input.summary ?? '',
        target: input.target ?? '',
        reason: input.reason ?? '',
        consequences: input.consequences ?? '',
        status: 'pending',
        expiresAt: new Date(now.getTime() + input.ttlMs).toISOString(),
        createdAt: now.toISOString(),
        decidedAt: null,
        decidedBy: null,
        executedAt: null,
        executionError: null,
      };
      db.prepare(
        `INSERT INTO pending_actions (id, request_id, tool_name, action_type, payload_json, summary, target, reason, consequences, status, expires_at, created_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)`,
      ).run(
        action.id,
        action.requestId,
        action.toolName,
        action.actionType,
        JSON.stringify(action.payload),
        action.summary,
        action.target,
        action.reason,
        action.consequences,
        action.expiresAt,
        action.createdAt,
      );
      return action;
    },

    /**
     * Records a single-use decision. The stored payload is authoritative —
     * the client cannot substitute a different payload at approval time.
     * Approval moves the action to 'approved'; the execution result is
     * recorded separately (recordExecution) so a crash between the two never
     * fakes success. The UPDATE's WHERE clause enforces single-use atomically.
     */
    decide(
      id: string,
      decision: 'approve' | 'cancel',
      actorLabel: string,
      now: string = nowIso(),
    ): DecisionOutcome {
      const existing = this.findById(id);
      if (!existing) return { ok: false, reason: 'not_found' };
      if (existing.status !== 'pending') return { ok: false, reason: 'already_decided' };
      if (existing.expiresAt <= now) {
        db.prepare(
          `UPDATE pending_actions SET status = 'expired', decided_at = ?, decided_by = 'system:expiry'
           WHERE id = ? AND status = 'pending'`,
        ).run(now, id);
        return { ok: false, reason: 'expired' };
      }
      const nextStatus = decision === 'approve' ? 'approved' : 'cancelled';
      const result = db
        .prepare(
          `UPDATE pending_actions SET status = ?, decided_at = ?, decided_by = ?
           WHERE id = ? AND status = 'pending'`,
        )
        .run(nextStatus, now, actorLabel, id);
      if (result.changes !== 1) return { ok: false, reason: 'already_decided' };
      const updated = this.findById(id);
      if (!updated) return { ok: false, reason: 'not_found' };
      return { ok: true, action: updated };
    },

    /**
     * Records the outcome of executing an approved action exactly once.
     * Double execution is impossible: only an 'approved' row with no
     * executed_at can transition.
     */
    recordExecution(
      id: string,
      outcome:
        | { status: 'simulated_completed' | 'completed' }
        | { status: 'failed'; error: string },
      now: string = nowIso(),
    ): PendingAction | null {
      const result = db
        .prepare(
          `UPDATE pending_actions SET status = ?, executed_at = ?, execution_error = ?
           WHERE id = ? AND status = 'approved' AND executed_at IS NULL`,
        )
        .run(outcome.status, now, outcome.status === 'failed' ? outcome.error : null, id);
      if (result.changes !== 1) return null;
      return this.findById(id);
    },
  };
}

export type PendingActionsRepository = ReturnType<typeof createPendingActionsRepository>;
