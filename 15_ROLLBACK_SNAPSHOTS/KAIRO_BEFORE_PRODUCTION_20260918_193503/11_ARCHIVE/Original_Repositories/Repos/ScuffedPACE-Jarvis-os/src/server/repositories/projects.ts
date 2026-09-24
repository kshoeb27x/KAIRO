import { randomUUID } from 'node:crypto';
import type Database from 'better-sqlite3';
import type { Project } from '../../shared/types';
import { nowIso } from '../persistence/db';

interface ProjectRow {
  id: string;
  name: string;
  summary: string;
  status: string;
  is_active: number;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
}

function toProject(row: ProjectRow): Project {
  return {
    id: row.id,
    name: row.name,
    summary: row.summary,
    status: row.status as Project['status'],
    isActive: row.is_active === 1,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    archivedAt: row.archived_at,
  };
}

export function createProjectsRepository(db: Database.Database) {
  return {
    /** Includes archived rows so callers can decide not to reseed them. */
    findById(id: string): Project | null {
      const row = db.prepare('SELECT * FROM projects WHERE id = ?').get(id) as
        | ProjectRow
        | undefined;
      return row ? toProject(row) : null;
    },

    findActive(): Project | null {
      const row = db
        .prepare('SELECT * FROM projects WHERE is_active = 1 AND archived_at IS NULL LIMIT 1')
        .get() as ProjectRow | undefined;
      return row ? toProject(row) : null;
    },

    create(input: { id?: string; name: string; summary: string; isActive?: boolean }): Project {
      const now = nowIso();
      const project: Project = {
        id: input.id ?? randomUUID(),
        name: input.name,
        summary: input.summary,
        status: 'active',
        isActive: input.isActive ?? false,
        createdAt: now,
        updatedAt: now,
        archivedAt: null,
      };
      db.prepare(
        `INSERT INTO projects (id, name, summary, status, is_active, created_at, updated_at, archived_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, NULL)`,
      ).run(
        project.id,
        project.name,
        project.summary,
        project.status,
        project.isActive ? 1 : 0,
        now,
        now,
      );
      return project;
    },
  };
}

export type ProjectsRepository = ReturnType<typeof createProjectsRepository>;
