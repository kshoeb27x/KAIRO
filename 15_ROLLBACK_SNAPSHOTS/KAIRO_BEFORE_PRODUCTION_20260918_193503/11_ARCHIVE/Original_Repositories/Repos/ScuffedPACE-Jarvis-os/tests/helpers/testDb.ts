import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import type Database from 'better-sqlite3';
import { openDatabase } from '../../src/server/persistence/db';
import { runMigrations } from '../../src/server/persistence/migrate';
import { createRepositories, type Repositories } from '../../src/server/repositories';

export interface TestDb {
  dir: string;
  db: Database.Database;
  repos: Repositories;
  reopen(): TestDb;
  cleanup(): void;
}

/**
 * Every test gets its own temporary data directory, isolated from the
 * operational .data directory, and removes it afterwards.
 */
export function createTestDb(existingDir?: string): TestDb {
  const dir = existingDir ?? fs.mkdtempSync(path.join(os.tmpdir(), 'jarvis-test-'));
  const db = openDatabase(dir);
  runMigrations(db);
  const repos = createRepositories(db);
  return {
    dir,
    db,
    repos,
    reopen() {
      db.close();
      return createTestDb(dir);
    },
    cleanup() {
      db.close();
      fs.rmSync(dir, { recursive: true, force: true });
    },
  };
}
