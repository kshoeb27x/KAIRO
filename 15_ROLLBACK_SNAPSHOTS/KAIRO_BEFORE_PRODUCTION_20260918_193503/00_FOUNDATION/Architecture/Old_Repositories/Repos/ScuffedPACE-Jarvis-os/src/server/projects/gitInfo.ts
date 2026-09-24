import { execFile } from 'node:child_process';

/**
 * Safe, read-only git inspection. Fixed argument allowlist, no shell, bounded
 * output, per-command timeout. Anything that fails simply yields nulls — a
 * project without git is not an error.
 */

export interface GitInfo {
  isRepo: boolean;
  branch: string | null;
  dirtyFiles: number | null;
  recentCommits: string[];
  lastCommitAt: string | null;
}

const GIT_TIMEOUT_MS = 8000;
const MAX_OUTPUT = 256 * 1024;

function git(root: string, args: string[]): Promise<string | null> {
  return new Promise((resolve) => {
    execFile(
      'git',
      args,
      { cwd: root, timeout: GIT_TIMEOUT_MS, maxBuffer: MAX_OUTPUT, windowsHide: true },
      (error, stdout) => resolve(error ? null : stdout.toString()),
    );
  });
}

export async function readGitInfo(root: string): Promise<GitInfo> {
  const inside = await git(root, ['rev-parse', '--is-inside-work-tree']);
  if (inside === null || !inside.trim().startsWith('true')) {
    return { isRepo: false, branch: null, dirtyFiles: null, recentCommits: [], lastCommitAt: null };
  }
  const [branch, status, log, lastDate] = await Promise.all([
    git(root, ['branch', '--show-current']),
    git(root, ['status', '--porcelain']),
    git(root, ['log', '-n', '10', '--pretty=format:%h %s']),
    git(root, ['log', '-n', '1', '--pretty=format:%cI']),
  ]);
  return {
    isRepo: true,
    branch: branch?.trim() || null,
    dirtyFiles: status === null ? null : status.split('\n').filter((l) => l.trim()).length,
    recentCommits: (log ?? '')
      .split('\n')
      .map((l) => l.trim())
      .filter(Boolean)
      .slice(0, 10),
    lastCommitAt: lastDate?.trim() || null,
  };
}
