import { randomUUID } from 'node:crypto';
import type Database from 'better-sqlite3';
import type { Memory, MemoryKind } from '../../shared/types';
import { nowIso } from '../persistence/db';

interface MemoryRow {
  id: string;
  kind: string;
  memory_key: string | null;
  value: string;
  tags_json: string;
  source: string;
  source_detail: string | null;
  sensitive: number;
  project_id: string | null;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
}

function toMemory(row: MemoryRow): Memory {
  return {
    id: row.id,
    kind: row.kind as MemoryKind,
    memoryKey: row.memory_key,
    value: row.value,
    tags: JSON.parse(row.tags_json) as string[],
    source: row.source as Memory['source'],
    sourceDetail: row.source_detail,
    sensitive: row.sensitive === 1,
    projectId: row.project_id,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    archivedAt: row.archived_at,
  };
}

/** Normalization used for duplicate detection: case/punctuation-insensitive. */
export function normalizeMemoryValue(value: string): string {
  return value
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter(Boolean)
    .join(' ');
}

export function createMemoriesRepository(db: Database.Database) {
  return {
    findById(id: string): Memory | null {
      const row = db.prepare('SELECT * FROM memories WHERE id = ?').get(id) as
        | MemoryRow
        | undefined;
      return row ? toMemory(row) : null;
    },

    /** Active (non-archived) memories, newest first. */
    listActive(): Memory[] {
      const rows = db
        .prepare('SELECT * FROM memories WHERE archived_at IS NULL ORDER BY updated_at DESC')
        .all() as MemoryRow[];
      return rows.map(toMemory);
    },

    /** Case-insensitive substring search over value, tags, and key. */
    search(query: string): Memory[] {
      const like = `%${query.replace(/[%_]/g, ' ')}%`;
      const rows = db
        .prepare(
          `SELECT * FROM memories
           WHERE archived_at IS NULL
             AND (value LIKE ? COLLATE NOCASE
                  OR tags_json LIKE ? COLLATE NOCASE
                  OR memory_key LIKE ? COLLATE NOCASE
                  OR kind LIKE ? COLLATE NOCASE)
           ORDER BY updated_at DESC`,
        )
        .all(like, like, like, like) as MemoryRow[];
      return rows.map(toMemory);
    },

    /** Finds an active memory whose normalized value matches (duplicate guard). */
    findActiveDuplicate(value: string): Memory | null {
      const target = normalizeMemoryValue(value);
      if (!target) return null;
      for (const memory of this.listActive()) {
        if (normalizeMemoryValue(memory.value) === target) return memory;
      }
      return null;
    },

    create(input: {
      kind: MemoryKind;
      value: string;
      memoryKey?: string | null;
      tags?: string[];
      source?: Memory['source'];
      sourceDetail?: string | null;
      sensitive?: boolean;
      projectId?: string | null;
    }): Memory {
      const now = nowIso();
      const memory: Memory = {
        id: randomUUID(),
        kind: input.kind,
        memoryKey: input.memoryKey ?? null,
        value: input.value,
        tags: input.tags ?? [],
        source: input.source ?? 'user_explicit',
        sourceDetail: input.sourceDetail ?? null,
        sensitive: input.sensitive ?? false,
        projectId: input.projectId ?? null,
        createdAt: now,
        updatedAt: now,
        archivedAt: null,
      };
      db.prepare(
        `INSERT INTO memories (id, kind, memory_key, value, tags_json, source, source_detail, sensitive, project_id, created_at, updated_at, archived_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)`,
      ).run(
        memory.id,
        memory.kind,
        memory.memoryKey,
        memory.value,
        JSON.stringify(memory.tags),
        memory.source,
        memory.sourceDetail,
        memory.sensitive ? 1 : 0,
        memory.projectId,
        now,
        now,
      );
      return memory;
    },

    /** Owner edit of value, kind, or tags. Never changes provenance fields. */
    update(
      id: string,
      patch: { value?: string; kind?: MemoryKind; tags?: string[] },
    ): Memory | null {
      const existing = this.findById(id);
      if (!existing || existing.archivedAt) return null;
      const now = nowIso();
      db.prepare(
        'UPDATE memories SET value = ?, kind = ?, tags_json = ?, updated_at = ? WHERE id = ?',
      ).run(
        patch.value ?? existing.value,
        patch.kind ?? existing.kind,
        JSON.stringify(patch.tags ?? existing.tags),
        now,
        id,
      );
      return this.findById(id);
    },

    /** "Forget" archives rather than destroying historical references. */
    archive(id: string): Memory | null {
      const existing = this.findById(id);
      if (!existing || existing.archivedAt) return existing;
      const now = nowIso();
      db.prepare('UPDATE memories SET archived_at = ?, updated_at = ? WHERE id = ?').run(
        now,
        now,
        id,
      );
      return this.findById(id);
    },
  };
}

export type MemoriesRepository = ReturnType<typeof createMemoriesRepository>;
