import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { afterEach, describe, expect, it } from 'vitest';
import { SCHEMA_VERSION } from '../../src/shared/constants';
import {
  createBackup,
  restoreBackup,
  MANIFEST_FILENAME,
  type BackupManifest,
} from '../../src/server/persistence/backup';
import { DB_FILENAME } from '../../src/server/persistence/db';
import { seedDatabase } from '../../src/server/persistence/seed';
import { createTestDb, type TestDb } from '../helpers/testDb';

let ctx: TestDb | null = null;
const tempDirs: string[] = [];

function tempDir(): string {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'jarvis-backup-'));
  tempDirs.push(dir);
  return dir;
}

afterEach(() => {
  ctx?.cleanup();
  ctx = null;
  for (const dir of tempDirs.splice(0)) {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

function populate(db: TestDb): void {
  seedDatabase(db.repos);
  const conversation = db.repos.conversations.create({ projectId: null, title: 'backup test' });
  db.repos.conversations.addMessage({
    conversationId: conversation.id,
    role: 'user',
    content: 'hello',
  });
  db.repos.memories.create({ kind: 'preference', value: 'approval before actions' });
}

describe('backup', () => {
  it('writes a database copy plus a manifest with counts and checksum', async () => {
    ctx = createTestDb();
    populate(ctx);
    ctx.db.close();

    const out = tempDir();
    const manifest = await createBackup(ctx.dir, out);
    expect(fs.existsSync(path.join(out, DB_FILENAME))).toBe(true);
    expect(manifest.schemaVersion).toBe(SCHEMA_VERSION);
    expect(manifest.tableCounts.projects).toBe(1);
    expect(manifest.tableCounts.messages).toBe(1);
    expect(manifest.tableCounts.memories).toBe(1);
    expect(manifest.databaseChecksum).toMatch(/^[a-f0-9]{64}$/);

    const onDisk = JSON.parse(
      fs.readFileSync(path.join(out, MANIFEST_FILENAME), 'utf8'),
    ) as BackupManifest;
    expect(onDisk).toEqual(manifest);
    ctx = { ...ctx, cleanup: () => fs.rmSync(ctx!.dir, { recursive: true, force: true }) };
  });
});

describe('restore', () => {
  async function makeBackup(): Promise<{ sourceDir: string; backupDir: string }> {
    const source = createTestDb();
    populate(source);
    source.db.close();
    const backupDir = tempDir();
    await createBackup(source.dir, backupDir);
    tempDirs.push(source.dir);
    return { sourceDir: source.dir, backupDir };
  }

  it('restores into an empty data directory and validates counts', async () => {
    const { backupDir } = await makeBackup();
    const target = tempDir();
    const result = await restoreBackup(target, backupDir);
    expect(result.preRestoreBackupDir).toBeNull();
    const reopened = createTestDb(target);
    expect(reopened.repos.projects.findActive()?.name).toBe('JARVIS OS');
    expect(reopened.repos.memories.listActive()).toHaveLength(1);
    reopened.db.close();
  });

  it('rejects a corrupted backup via checksum', async () => {
    const { backupDir } = await makeBackup();
    fs.appendFileSync(path.join(backupDir, DB_FILENAME), 'tamper');
    await expect(restoreBackup(tempDir(), backupDir)).rejects.toThrow(/checksum/i);
  });

  it('rejects unsupported schema versions', async () => {
    const { backupDir } = await makeBackup();
    const manifestPath = path.join(backupDir, MANIFEST_FILENAME);
    const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8')) as BackupManifest;
    manifest.schemaVersion = 99;
    fs.writeFileSync(manifestPath, JSON.stringify(manifest));
    await expect(restoreBackup(tempDir(), backupDir)).rejects.toThrow(/not supported/);
  });

  it('never silently replaces an existing store: requires force and takes a pre-restore backup', async () => {
    const { backupDir } = await makeBackup();

    const existing = createTestDb();
    existing.repos.memories.create({ kind: 'note', value: 'existing operational data' });
    existing.db.close();
    tempDirs.push(existing.dir);

    await expect(restoreBackup(existing.dir, backupDir)).rejects.toThrow(/--force/);

    const result = await restoreBackup(existing.dir, backupDir, { force: true });
    expect(result.preRestoreBackupDir).not.toBeNull();
    expect(fs.existsSync(path.join(result.preRestoreBackupDir!, DB_FILENAME))).toBe(true);
    expect(fs.existsSync(path.join(result.preRestoreBackupDir!, MANIFEST_FILENAME))).toBe(true);

    const reopened = createTestDb(existing.dir);
    const memories = reopened.repos.memories.listActive();
    expect(memories).toHaveLength(1);
    expect(memories[0]?.value).toBe('approval before actions');
    reopened.db.close();
  });
});
