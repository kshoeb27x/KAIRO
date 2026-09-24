import path from 'node:path';
import { readGitInfo, type GitInfo } from './gitInfo';
import { readProjectFile, scanProject, type ScanResult } from './scanner';

/**
 * Deterministic project profile: what the project is, how it is built and
 * tested, and its current health. This bounded summary — never raw secret
 * content — is what JARVIS uses to explain the project in plain English.
 */

export interface ProjectProfile {
  projectType: string;
  languages: string[];
  fileCount: number;
  truncatedScan: boolean;
  keyFiles: string[];
  commands: Record<string, string>;
  hasTests: boolean;
  hasReadme: boolean;
  readmeExcerpt: string | null;
  description: string;
  git: GitInfo;
  health: { level: 'good' | 'attention' | 'unknown'; notes: string[] };
  inspectedAt: string;
}

const LANGUAGE_BY_EXTENSION: Record<string, string> = {
  '.ts': 'TypeScript',
  '.tsx': 'TypeScript',
  '.js': 'JavaScript',
  '.jsx': 'JavaScript',
  '.mjs': 'JavaScript',
  '.py': 'Python',
  '.rs': 'Rust',
  '.go': 'Go',
  '.cs': 'C#',
  '.java': 'Java',
  '.rb': 'Ruby',
  '.php': 'PHP',
  '.sql': 'SQL',
  '.sh': 'Shell',
  '.ps1': 'PowerShell',
};

const KEY_FILE_NAMES = new Set([
  'package.json',
  'pyproject.toml',
  'requirements.txt',
  'cargo.toml',
  'go.mod',
  'readme.md',
  'dockerfile',
  'docker-compose.yml',
  'makefile',
  'tsconfig.json',
  'vite.config.ts',
  'playwright.config.ts',
  'vitest.config.ts',
]);

export async function buildProjectProfile(root: string): Promise<ProjectProfile> {
  const scan = scanProject(root);
  const git = await readGitInfo(root);

  const languages = detectLanguages(scan);
  const keyFiles = scan.files
    .filter((f) => KEY_FILE_NAMES.has(path.basename(f.relativePath).toLowerCase()))
    .map((f) => f.relativePath)
    .slice(0, 20);

  let projectType = 'Unknown';
  let commands: Record<string, string> = {};
  const packageJsonEntry = scan.files.find((f) => f.relativePath === 'package.json');
  if (packageJsonEntry) {
    projectType = 'Node.js';
    const raw = readProjectFile(root, 'package.json');
    if (raw) {
      try {
        const parsed = JSON.parse(raw) as { scripts?: Record<string, string>; description?: string };
        commands = Object.fromEntries(Object.entries(parsed.scripts ?? {}).slice(0, 20));
      } catch {
        // malformed package.json — type stays Node.js, no commands
      }
    }
  } else if (scan.files.some((f) => /^(pyproject\.toml|requirements\.txt)$/i.test(f.relativePath))) {
    projectType = 'Python';
  } else if (scan.files.some((f) => /^cargo\.toml$/i.test(f.relativePath))) {
    projectType = 'Rust';
  } else if (scan.files.some((f) => /^go\.mod$/i.test(f.relativePath))) {
    projectType = 'Go';
  } else if (languages.length > 0) {
    projectType = languages[0]!;
  }

  const hasTests = scan.files.some((f) =>
    /(^|\/)(tests?|__tests__|spec)\//i.test(f.relativePath) || /\.(test|spec)\.[jt]sx?$/i.test(f.relativePath),
  );
  const readmeFile = scan.files.find((f) => /^readme\.md$/i.test(f.relativePath));
  const readmeExcerpt = readmeFile ? (readProjectFile(root, readmeFile.relativePath, 4096) ?? null) : null;

  const notes: string[] = [];
  if (!git.isRepo) notes.push('Not a git repository — no change history available.');
  if (git.isRepo && (git.dirtyFiles ?? 0) > 0) notes.push(`${git.dirtyFiles} uncommitted file change(s).`);
  if (!hasTests) notes.push('No test files detected.');
  if (!readmeFile) notes.push('No README found.');
  if (scan.truncated) notes.push('Large project — the scan was truncated at the file limit.');
  const level: ProjectProfile['health']['level'] =
    git.isRepo || hasTests || readmeFile ? (notes.length > 1 ? 'attention' : 'good') : 'unknown';

  return {
    projectType,
    languages,
    fileCount: scan.files.length,
    truncatedScan: scan.truncated,
    keyFiles,
    commands,
    hasTests,
    hasReadme: Boolean(readmeFile),
    readmeExcerpt,
    description: describe(projectType, languages, scan, git, hasTests),
    git,
    health: { level, notes },
    inspectedAt: new Date().toISOString(),
  };
}

function detectLanguages(scan: ScanResult): string[] {
  const counts = new Map<string, number>();
  for (const file of scan.files) {
    const lang = LANGUAGE_BY_EXTENSION[path.extname(file.relativePath).toLowerCase()];
    if (lang) counts.set(lang, (counts.get(lang) ?? 0) + 1);
  }
  return [...counts.entries()].sort((a, b) => b[1] - a[1]).map(([lang]) => lang).slice(0, 5);
}

function describe(
  projectType: string,
  languages: string[],
  scan: ScanResult,
  git: GitInfo,
  hasTests: boolean,
): string {
  const parts: string[] = [];
  parts.push(
    `A ${projectType} project with ${scan.files.length}${scan.truncated ? '+' : ''} source files` +
      (languages.length > 0 ? ` (mainly ${languages.slice(0, 3).join(', ')})` : '') +
      '.',
  );
  if (git.isRepo) {
    parts.push(
      `On git branch ${git.branch ?? '(detached)'} with ${git.dirtyFiles ?? 0} uncommitted change(s); last commit ${git.lastCommitAt ? git.lastCommitAt.slice(0, 10) : 'unknown'}.`,
    );
  }
  parts.push(hasTests ? 'Automated tests are present.' : 'No automated tests were detected.');
  return parts.join(' ');
}
