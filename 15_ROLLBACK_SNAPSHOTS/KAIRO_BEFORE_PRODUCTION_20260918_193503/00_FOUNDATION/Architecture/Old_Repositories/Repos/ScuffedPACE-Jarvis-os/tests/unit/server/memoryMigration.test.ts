import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { afterEach, describe, expect, it } from 'vitest';
import { SCHEMA_VERSION } from '../../../src/shared/constants';
import { openDatabase } from '../../../src/server/persistence/db';
import { currentSchemaVersion, defaultMigrationsDir, runMigrations } from '../../../src/server/persistence/migrate';
import { createRepositories } from '../../../src/server/repositories';
import { normalizeMemoryValue } from '../../../src/server/repositories/memories';

const cleanups: Array<() => void> = [];
afterEach(() => {
  while (cleanups.length > 0) cleanups.pop()?.();
});

function tempDir(prefix: string): string {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), prefix));
  cleanups.push(() => fs.rmSync(dir, { recursive: true, force: true }));
  return dir;
}

describe('migration 002 (memory v2)', () => {
  it('upgrades a v1 database in place, preserving existing memories', () => {
    // Build a genuine v1 database using only the first migration.
    const v1MigrationsDir = tempDir('jarvis-mig-v1-');
    fs.copyFileSync(
      path.join(defaultMigrationsDir(), '001_init.sql'),
      path.join(v1MigrationsDir, '001_init.sql'),
    );
    const dataDir = tempDir('jarvis-migtest-');
    const db = openDatabase(dataDir);
    cleanups.push(() => db.close());
    runMigrations(db, v1MigrationsDir);
    expect(currentSchemaVersion(db)).toBe(1);

    db.prepare(
      `INSERT INTO memories (id, kind, memory_key, value, tags_json, source, project_id, created_at, updated_at, archived_at)
       VALUES ('11111111-1111-4111-8111-111111111111', 'preference', 'legacy-key', 'legacy value', '["a"]', 'user_explicit', NULL, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z', NULL)`,
    ).run();

    // Now run the full migration set — the same code path as server startup.
    const result = runMigrations(db);
    expect(result.applied).toContain('002_memory_v2.sql');
    expect(currentSchemaVersion(db)).toBe(SCHEMA_VERSION);

    const repos = createRepositories(db);
    const migrated = repos.memories.findById('11111111-1111-4111-8111-111111111111');
    expect(migrated).not.toBeNull();
    expect(migrated!.value).toBe('legacy value');
    expect(migrated!.kind).toBe('preference');
    expect(migrated!.tags).toEqual(['a']);
    expect(migrated!.sensitive).toBe(false);
    expect(migrated!.sourceDetail).toBeNull();

    // New categories and provenance fields work after the upgrade.
    const task = repos.memories.create({
      kind: 'task',
      value: 'follow up with the collaborator',
      source: 'user_explicit',
      sourceDetail: 'conversation',
    });
    expect(repos.memories.findById(task.id)!.kind).toBe('task');

    // Re-running migrations is a no-op.
    const rerun = runMigrations(db);
    expect(rerun.applied).toHaveLength(0);
    expect(rerun.alreadyApplied).toContain('002_memory_v2.sql');
  });

  it('rejects unknown kinds at the database level', () => {
    const dataDir = tempDir('jarvis-migtest2-');
    const db = openDatabase(dataDir);
    cleanups.push(() => db.close());
    runMigrations(db);
    expect(() =>
      db
        .prepare(
          `INSERT INTO memories (id, kind, value, tags_json, source, sensitive, created_at, updated_at)
           VALUES ('22222222-2222-4222-8222-222222222222', 'made_up_kind', 'x', '[]', 'user_explicit', 0, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')`,
        )
        .run(),
    ).toThrow(/CHECK/);
  });
});

describe('memory duplicate detection', () => {
  it('normalizes case and punctuation', () => {
    expect(normalizeMemoryValue('I prefer approval, before ANY external action!')).toBe(
      normalizeMemoryValue('i prefer approval before any external action'),
    );
  });
});
