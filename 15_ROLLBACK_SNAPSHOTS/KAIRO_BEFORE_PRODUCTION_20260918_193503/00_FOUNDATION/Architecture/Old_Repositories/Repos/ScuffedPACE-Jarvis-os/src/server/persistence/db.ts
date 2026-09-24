import fs from 'node:fs';
import path from 'node:path';
import Database from 'better-sqlite3';

export const DB_FILENAME = 'jarvis.db';

/**
 * Opens (creating if necessary) the SQLite database inside the data
 * directory. Never deletes or recreates an existing database.
 */
export function openDatabase(dataDir: string): Database.Database {
  fs.mkdirSync(dataDir, { recursive: true });
  const db = new Database(path.join(dataDir, DB_FILENAME));
  db.pragma('journal_mode = WAL');
  db.pragma('foreign_keys = ON');
  return db;
}

export function nowIso(): string {
  return new Date().toISOString();
}
