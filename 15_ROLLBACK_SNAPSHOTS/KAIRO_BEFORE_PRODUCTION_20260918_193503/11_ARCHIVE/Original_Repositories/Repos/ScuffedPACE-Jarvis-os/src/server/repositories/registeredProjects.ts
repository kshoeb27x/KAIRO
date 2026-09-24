import { randomUUID } from 'node:crypto';
import type Database from 'better-sqlite3';
import { nowIso } from '../persistence/db';
import type { ProjectProfile } from '../projects/profile';

export interface RegisteredProject {
  id: string;
  name: string;
  rootPath: string;
  profile: ProjectProfile | null;
  lastInspectedAt: string | null;
  createdAt: string;
  updatedAt: string;
  archivedAt: string | null;
}

interface Row {
  id: string;
  name: string;
  root_path: string;
  profile_json: string;
  last_inspected_at: string | null;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
}

function toProject(row: Row): RegisteredProject {
  let profile: ProjectProfile | null;
  try {
    const parsed = JSON.parse(row.profile_json) as ProjectProfile | Record<string, never>;
    profile = parsed && 'projectType' in parsed ? (parsed as ProjectProfile) : null;
  } catch {
    profile = null;
  }
  return {
    id: row.id,
    name: row.name,
    rootPath: row.root_path,
    profile,
    lastInspectedAt: row.last_inspected_at,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    archivedAt: row.archived_at,
  };
}

export function createRegisteredProjectsRepository(db: Database.Database) {
  return {
    findById(id: string): RegisteredProject | null {
      const row = db.prepare('SELECT * FROM registered_projects WHERE id = ?').get(id) as
        | Row
        | undefined;
      return row ? toProject(row) : null;
    },

    findByPath(rootPath: string): RegisteredProject | null {
      const row = db
        .prepare('SELECT * FROM registered_projects WHERE root_path = ?')
        .get(rootPath) as Row | undefined;
      return row ? toProject(row) : null;
    },

    listActive(): RegisteredProject[] {
      const rows = db
        .prepare('SELECT * FROM registered_projects WHERE archived_at IS NULL ORDER BY name')
        .all() as Row[];
      return rows.map(toProject);
    },

    create(input: { name: string; rootPath: string; profile: ProjectProfile }): RegisteredProject {
      const now = nowIso();
      const id = randomUUID();
      db.prepare(
        `INSERT INTO registered_projects (id, name, root_path, profile_json, last_inspected_at, created_at, updated_at)
         VALUES (?, ?, ?, ?, ?, ?, ?)`,
      ).run(id, input.name, input.rootPath, JSON.stringify(input.profile), now, now, now);
      return this.findById(id)!;
    },

    updateProfile(id: string, profile: ProjectProfile): RegisteredProject | null {
      const now = nowIso();
      const result = db
        .prepare(
          `UPDATE registered_projects SET profile_json = ?, last_inspected_at = ?, updated_at = ?, archived_at = NULL
           WHERE id = ?`,
        )
        .run(JSON.stringify(profile), now, now, id);
      return result.changes === 1 ? this.findById(id) : null;
    },

    /** Unregister = archive; the record and its history are never destroyed. */
    archive(id: string): RegisteredProject | null {
      const now = nowIso();
      db.prepare(
        'UPDATE registered_projects SET archived_at = ?, updated_at = ? WHERE id = ? AND archived_at IS NULL',
      ).run(now, now, id);
      return this.findById(id);
    },
  };
}

export type RegisteredProjectsRepository = ReturnType<typeof createRegisteredProjectsRepository>;
