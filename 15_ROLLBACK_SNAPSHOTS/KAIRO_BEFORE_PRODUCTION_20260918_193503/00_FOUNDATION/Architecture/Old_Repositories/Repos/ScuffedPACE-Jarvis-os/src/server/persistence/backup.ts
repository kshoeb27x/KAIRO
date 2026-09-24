import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import Database from 'better-sqlite3';
import { APP_VERSION } from '../../shared/constants';
import { DB_FILENAME, openDatabase } from './db';
import { currentSchemaVersion } from './migrate';

export const MANIFEST_FILENAME = 'manifest.json';
export const SUPPORTED_SCHEMA_VERSIONS = [1, 2, 3, 4];

const COUNTED_TABLES = [
  'projects',
  'conversations',
  'messages',
  'memories',
  'pending_actions',
  'activity_events',
  'settings',
] as const;

export interface BackupManifest {
  appVersion: string;
  schemaVersion: number;
  createdAt: string;
  tableCounts: Record<string, number>;
  databaseChecksum: string;
}

function sha256(filePath: string): string {
  return crypto.createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
}

function countTables(db: Database.Database): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const table of COUNTED_TABLES) {
    const row = db.prepare(`SELECT COUNT(*) AS n FROM ${table}`).get() as { n: number };
    counts[table] = row.n;
  }
  return counts;
}

/**
 * Safe online backup via SQLite's backup API into `outputDir`, plus a
 * manifest with app/schema versions, creation time, per-table counts, and a
 * checksum of the backup file.
 */
export async function createBackup(dataDir: string, outputDir: string): Promise<BackupManifest> {
  const sourcePath = path.join(dataDir, DB_FILENAME);
  if (!fs.existsSync(sourcePath)) {
    throw new Error(`No database found at ${sourcePath} — nothing to back up.`);
  }
  fs.mkdirSync(outputDir, { recursive: true });
  const destinationPath = path.join(outputDir, DB_FILENAME);

  const db = openDatabase(dataDir);
  try {
    await db.backup(destinationPath);
    const manifest: BackupManifest = {
      appVersion: APP_VERSION,
      schemaVersion: currentSchemaVersion(db),
      createdAt: new Date().toISOString(),
      tableCounts: countTables(db),
      databaseChecksum: sha256(destinationPath),
    };
    fs.writeFileSync(
      path.join(outputDir, MANIFEST_FILENAME),
      `${JSON.stringify(manifest, null, 2)}\n`,
    );
    return manifest;
  } finally {
    db.close();
  }
}

export interface RestoreOptions {
  force?: boolean;
}

export interface RestoreResult {
  manifest: BackupManifest;
  preRestoreBackupDir: string | null;
}

/**
 * Restores a backup into the data directory. Validates the manifest and
 * checksum, rejects unsupported schema versions, refuses to replace an
 * existing store without an explicit force flag (after taking a pre-restore
 * backup), and validates record counts afterwards. Never silently resets
 * operational data.
 */
export async function restoreBackup(
  dataDir: string,
  inputDir: string,
  options: RestoreOptions = {},
): Promise<RestoreResult> {
  const backupDbPath = path.join(inputDir, DB_FILENAME);
  const manifestPath = path.join(inputDir, MANIFEST_FILENAME);
  if (!fs.existsSync(backupDbPath) || !fs.existsSync(manifestPath)) {
    throw new Error(`Backup at ${inputDir} is missing ${DB_FILENAME} or ${MANIFEST_FILENAME}.`);
  }

  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8')) as BackupManifest;
  if (!SUPPORTED_SCHEMA_VERSIONS.includes(manifest.schemaVersion)) {
    throw new Error(
      `Backup schema version ${manifest.schemaVersion} is not supported (supported: ${SUPPORTED_SCHEMA_VERSIONS.join(', ')}).`,
    );
  }
  const checksum = sha256(backupDbPath);
  if (checksum !== manifest.databaseChecksum) {
    throw new Error('Backup checksum mismatch — the backup file is corrupt or was modified.');
  }

  const targetPath = path.join(dataDir, DB_FILENAME);
  let preRestoreBackupDir: string | null = null;

  if (fs.existsSync(targetPath)) {
    if (!options.force) {
      throw new Error(
        `A database already exists at ${targetPath}. Re-run with --force to replace it (a pre-restore backup will be taken first).`,
      );
    }
    preRestoreBackupDir = path.join(
      dataDir,
      `pre-restore-${new Date().toISOString().replaceAll(':', '-')}`,
    );
    await createBackup(dataDir, preRestoreBackupDir);
    // Remove WAL/SHM alongside the replaced database.
    for (const suffix of ['', '-wal', '-shm']) {
      fs.rmSync(`${targetPath}${suffix}`, { force: true });
    }
  }

  fs.mkdirSync(dataDir, { recursive: true });
  fs.copyFileSync(backupDbPath, targetPath);

  // Validate the restored store against the manifest counts.
  const db = new Database(targetPath, { readonly: true });
  try {
    const counts = countTables(db);
    for (const [table, expected] of Object.entries(manifest.tableCounts)) {
      if (counts[table] !== expected) {
        throw new Error(
          `Restored table ${table} has ${counts[table]} records; the manifest expected ${expected}.`,
        );
      }
    }
  } finally {
    db.close();
  }

  return { manifest, preRestoreBackupDir };
}
