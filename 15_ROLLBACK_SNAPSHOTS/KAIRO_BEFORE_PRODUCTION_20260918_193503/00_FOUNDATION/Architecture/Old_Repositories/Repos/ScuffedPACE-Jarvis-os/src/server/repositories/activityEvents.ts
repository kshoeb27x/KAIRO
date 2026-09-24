import { randomUUID } from 'node:crypto';
import type Database from 'better-sqlite3';

/**
 * Local event history of safe operational events. Not a production audit
 * trail: there is no authentication, so actor identity is a local label.
 * Never stores secrets or full model prompts.
 */
export function createActivityEventsRepository(db: Database.Database) {
  return {
    record(input: {
      requestId: string;
      eventType: string;
      safeLabel: string;
      metadata?: Record<string, unknown>;
      occurredAt?: string;
    }): void {
      db.prepare(
        `INSERT INTO activity_events (id, request_id, event_type, safe_label, metadata_json, occurred_at)
         VALUES (?, ?, ?, ?, ?, ?)`,
      ).run(
        randomUUID(),
        input.requestId,
        input.eventType,
        input.safeLabel,
        JSON.stringify(input.metadata ?? {}),
        input.occurredAt ?? new Date().toISOString(),
      );
    },

    listByRequest(requestId: string): Array<{ eventType: string; safeLabel: string; occurredAt: string }> {
      return db
        .prepare(
          `SELECT event_type AS eventType, safe_label AS safeLabel, occurred_at AS occurredAt
           FROM activity_events WHERE request_id = ? ORDER BY occurred_at ASC, id ASC`,
        )
        .all(requestId) as Array<{ eventType: string; safeLabel: string; occurredAt: string }>;
    },

    countAll(): number {
      const row = db.prepare('SELECT COUNT(*) AS n FROM activity_events').get() as { n: number };
      return row.n;
    },
  };
}

export type ActivityEventsRepository = ReturnType<typeof createActivityEventsRepository>;
