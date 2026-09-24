import fs from 'node:fs';
import path from 'node:path';
import { resolveInsideRoot } from '../security/paths';

/**
 * Read-only, bounded project scanner. Never follows symlinks, never reads
 * ignored or secret files, never loads more than the configured limits, and
 * never writes anything.
 */

const IGNORED_DIRS = new Set([
  '.git',
  'node_modules',
  'dist',
  'build',
  'out',
  'coverage',
  '.next',
  '.nuxt',
  'target',
  '__pycache__',
  '.venv',
  'venv',
  '.idea',
  '.vscode',
  '.playwright',
  'playwright-report',
  'test-results',
  '.data',
  'backups',
  'logs',
]);

/** Files that must never be read or summarized (secrets / operational data). */
const SECRET_FILE_PATTERNS = [
  /^\.env(\..*)?$/i,
  /\.(pem|key|pfx|p12|crt)$/i,
  /^(id_rsa|id_ed25519)/i,
  /\.(db|sqlite|sqlite3|db-wal|db-shm)$/i,
  /^secrets?\./i,
  /credentials/i,
];

const BINARY_EXTENSIONS = new Set([
  '.png', '.jpg', '.jpeg', '.gif', '.webp', '.ico', '.pdf', '.zip', '.gz',
  '.tar', '.7z', '.rar', '.exe', '.dll', '.so', '.dylib', '.node', '.wasm',
  '.mp3', '.mp4', '.wav', '.ogg', '.woff', '.woff2', '.ttf', '.eot',
]);

export interface ScanLimits {
  maxFiles: number;
  maxDepth: number;
  maxFileBytes: number;
}

export const DEFAULT_SCAN_LIMITS: ScanLimits = {
  maxFiles: 2000,
  maxDepth: 8,
  maxFileBytes: 256 * 1024,
};

export interface ScannedFile {
  relativePath: string;
  bytes: number;
}

export interface ScanResult {
  files: ScannedFile[];
  skipped: { secrets: number; binaries: number; oversized: number; ignoredDirs: string[] };
  truncated: boolean;
}

export function isSecretFile(name: string): boolean {
  return SECRET_FILE_PATTERNS.some((p) => p.test(name));
}

export function scanProject(root: string, limits: ScanLimits = DEFAULT_SCAN_LIMITS): ScanResult {
  const files: ScannedFile[] = [];
  const skipped = { secrets: 0, binaries: 0, oversized: 0, ignoredDirs: [] as string[] };
  let truncated = false;

  const walk = (dir: string, depth: number): void => {
    if (truncated || depth > limits.maxDepth) return;
    let entries: fs.Dirent[];
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      return; // unreadable directory — skip silently, read-only scan
    }
    for (const entry of entries) {
      if (truncated) return;
      if (entry.isSymbolicLink()) continue;
      const full = resolveInsideRoot(root, path.relative(root, path.join(dir, entry.name)));
      if (!full) continue;
      if (entry.isDirectory()) {
        if (IGNORED_DIRS.has(entry.name.toLowerCase())) {
          if (!skipped.ignoredDirs.includes(entry.name)) skipped.ignoredDirs.push(entry.name);
          continue;
        }
        walk(full, depth + 1);
        continue;
      }
      if (!entry.isFile()) continue;
      if (isSecretFile(entry.name)) {
        skipped.secrets += 1;
        continue;
      }
      if (BINARY_EXTENSIONS.has(path.extname(entry.name).toLowerCase())) {
        skipped.binaries += 1;
        continue;
      }
      let bytes: number;
      try {
        bytes = fs.statSync(full).size;
      } catch {
        continue;
      }
      if (bytes > limits.maxFileBytes) {
        skipped.oversized += 1;
        continue;
      }
      files.push({ relativePath: path.relative(root, full).replaceAll('\\', '/'), bytes });
      if (files.length >= limits.maxFiles) truncated = true;
    }
  };

  walk(root, 0);
  return { files, skipped, truncated };
}

/** Bounded, safe read of one scanned file (already ignore-filtered). */
export function readProjectFile(root: string, relativePath: string, maxBytes = 64 * 1024): string | null {
  const full = resolveInsideRoot(root, relativePath);
  if (!full) return null;
  if (isSecretFile(path.basename(full))) return null;
  try {
    const fd = fs.openSync(full, 'r');
    try {
      const buffer = Buffer.alloc(maxBytes);
      const read = fs.readSync(fd, buffer, 0, maxBytes, 0);
      return buffer.subarray(0, read).toString('utf8');
    } finally {
      fs.closeSync(fd);
    }
  } catch {
    return null;
  }
}
