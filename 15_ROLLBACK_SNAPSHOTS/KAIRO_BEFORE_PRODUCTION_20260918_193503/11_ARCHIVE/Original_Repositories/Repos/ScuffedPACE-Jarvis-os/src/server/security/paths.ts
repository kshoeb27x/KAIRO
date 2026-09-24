import fs from 'node:fs';
import path from 'node:path';

/**
 * Path safety for project inspection. Only owner-registered directories are
 * ever read, every read is resolved against the registered root, and system
 * directories can never be registered.
 */

const FORBIDDEN_ROOTS = [
  /^[a-z]:[\\/]?$/i, // a drive root
  /^[a-z]:[\\/]windows([\\/]|$)/i,
  /^[a-z]:[\\/]program files( \(x86\))?([\\/]|$)/i,
  /^[a-z]:[\\/]programdata([\\/]|$)/i,
  /^\/($|etc|usr|bin|sbin|var|boot|proc|sys)([\\/]|$)/,
];

export type PathValidation =
  | { ok: true; root: string }
  | { ok: false; message: string };

/** Validates a directory the owner wants to register for inspection. */
export function validateProjectRoot(rawPath: string): PathValidation {
  if (!rawPath || rawPath.trim().length === 0) {
    return { ok: false, message: 'A project path is required.' };
  }
  const trimmed = rawPath.trim();
  if (!path.isAbsolute(trimmed)) {
    return { ok: false, message: 'Use an absolute path (e.g. C:\\Projects\\my-app).' };
  }
  const resolved = path.resolve(trimmed);
  for (const forbidden of FORBIDDEN_ROOTS) {
    if (forbidden.test(resolved)) {
      return { ok: false, message: 'System directories cannot be registered.' };
    }
  }
  let stat: fs.Stats;
  try {
    stat = fs.statSync(resolved);
  } catch {
    return { ok: false, message: `The path does not exist: ${resolved}` };
  }
  if (!stat.isDirectory()) {
    return { ok: false, message: 'The project path must be a directory.' };
  }
  return { ok: true, root: resolved };
}

/**
 * Resolves a relative entry inside a registered root, rejecting traversal.
 * Every file read during inspection goes through this.
 */
export function resolveInsideRoot(root: string, relative: string): string | null {
  const resolved = path.resolve(root, relative);
  const normalizedRoot = root.endsWith(path.sep) ? root : root + path.sep;
  if (resolved !== root && !resolved.startsWith(normalizedRoot)) return null;
  return resolved;
}
