import fs from 'node:fs';
import path from 'node:path';
import type Database from 'better-sqlite3';

export interface MigrationResult {
  applied: string[];
  alreadyApplied: string[];
  schemaVersion: number;
}

const BASE_TABLES = [
  'schema_migrations',
  'projects',
  'conversations',
  'messages',
  'memories',
  'pending_actions',
  'activity_events',
  'settings',
];

/** Tables that exist only once a specific later migration has been applied. */
const TABLES_BY_MIGRATION: Record<string, string[]> = {
  '004_registered_projects.sql': ['registered_projects'],
};

export function defaultMigrationsDir(): string {
  return path.resolve(process.cwd(), 'migrations');
}

/**
 * Applies pending .sql migrations in filename order. Each migration runs in
 * its own transaction and is recorded in schema_migrations, so repeated
 * startup is idempotent. Existing data is never deleted or recreated.
 */
export function runMigrations(
  db: Database.Database,
  migrationsDir: string = defaultMigrationsDir(),
): MigrationResult {
  db.exec(`CREATE TABLE IF NOT EXISTS schema_migrations (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    applied_at TEXT NOT NULL
  )`);

  const files = fs
    .readdirSync(migrationsDir)
    .filter((f) => f.endsWith('.sql'))
    .sort();

  const appliedRows = db
    .prepare('SELECT name FROM schema_migrations ORDER BY id')
    .all() as Array<{ name: string }>;
  const appliedSet = new Set(appliedRows.map((r) => r.name));

  const applied: string[] = [];
  const alreadyApplied: string[] = [];

  for (const file of files) {
    if (appliedSet.has(file)) {
      alreadyApplied.push(file);
      continue;
    }
    const sql = fs.readFileSync(path.join(migrationsDir, file), 'utf8');
    const apply = db.transaction(() => {
      db.exec(sql);
      db.prepare('INSERT INTO schema_migrations (name, applied_at) VALUES (?, ?)').run(
        file,
        new Date().toISOString(),
      );
    });
    apply();
    applied.push(file);
  }

  validateSchema(db, new Set([...appliedSet, ...applied]));

  return {
    applied,
    alreadyApplied,
    schemaVersion: currentSchemaVersion(db),
  };
}

export function currentSchemaVersion(db: Database.Database): number {
  const row = db.prepare('SELECT COUNT(*) AS n FROM schema_migrations').get() as { n: number };
  return row.n;
}

function validateSchema(db: Database.Database, appliedMigrations: Set<string>): void {
  const rows = db
    .prepare(`SELECT name FROM sqlite_master WHERE type = 'table'`)
    .all() as Array<{ name: string }>;
  const names = new Set(rows.map((r) => r.name));
  const expected = [...BASE_TABLES];
  for (const [migration, tables] of Object.entries(TABLES_BY_MIGRATION)) {
    if (appliedMigrations.has(migration)) expected.push(...tables);
  }
  const missing = expected.filter((t) => !names.has(t));
  if (missing.length > 0) {
    throw new Error(`Migration validation failed; missing tables: ${missing.join(', ')}`);
  }
}
