import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { afterEach, describe, expect, it } from 'vitest';
import { resolveInsideRoot, validateProjectRoot } from '../../../src/server/security/paths';
import { scanProject, readProjectFile } from '../../../src/server/projects/scanner';
import { buildProjectProfile } from '../../../src/server/projects/profile';
import { readGitInfo } from '../../../src/server/projects/gitInfo';

const cleanups: Array<() => void> = [];
afterEach(() => {
  while (cleanups.length > 0) cleanups.pop()?.();
});

function makeFixtureProject(): string {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'jarvis-proj-'));
  cleanups.push(() => fs.rmSync(dir, { recursive: true, force: true }));
  fs.mkdirSync(path.join(dir, 'src'));
  fs.mkdirSync(path.join(dir, 'tests'));
  fs.mkdirSync(path.join(dir, 'node_modules', 'dep'), { recursive: true });
  fs.writeFileSync(path.join(dir, 'src', 'index.ts'), 'export const x = 1;');
  fs.writeFileSync(path.join(dir, 'tests', 'index.test.ts'), 'it("x", () => {});');
  fs.writeFileSync(path.join(dir, 'node_modules', 'dep', 'index.js'), 'module.exports = 1;');
  fs.writeFileSync(path.join(dir, '.env'), 'SECRET=do-not-read');
  fs.writeFileSync(path.join(dir, 'secrets.json'), '{"k":"v"}');
  fs.writeFileSync(path.join(dir, 'logo.png'), Buffer.from([0x89, 0x50, 0x4e, 0x47]));
  fs.writeFileSync(path.join(dir, 'big.txt'), 'x'.repeat(300 * 1024));
  fs.writeFileSync(path.join(dir, 'README.md'), '# Fixture\nA test project.');
  fs.writeFileSync(
    path.join(dir, 'package.json'),
    JSON.stringify({ name: 'fixture', scripts: { test: 'vitest run', build: 'tsc' } }),
  );
  return dir;
}

describe('project path safety', () => {
  it('rejects relative, missing, and system paths', () => {
    expect(validateProjectRoot('relative/path').ok).toBe(false);
    expect(validateProjectRoot('C:\\definitely-missing-jarvis-test-dir-xyz').ok).toBe(false);
    expect(validateProjectRoot('C:\\Windows\\System32').ok).toBe(false);
    expect(validateProjectRoot('C:\\').ok).toBe(false);
    expect(validateProjectRoot('').ok).toBe(false);
  });

  it('accepts a real directory and resolves it', () => {
    const dir = makeFixtureProject();
    const result = validateProjectRoot(dir);
    expect(result.ok).toBe(true);
  });

  it('blocks path traversal out of a registered root', () => {
    const dir = makeFixtureProject();
    expect(resolveInsideRoot(dir, 'src/index.ts')).not.toBeNull();
    expect(resolveInsideRoot(dir, '../outside.txt')).toBeNull();
    expect(resolveInsideRoot(dir, '..\\..\\Windows\\win.ini')).toBeNull();
    expect(resolveInsideRoot(dir, 'src/../../escape')).toBeNull();
  });
});

describe('read-only project scanner', () => {
  it('skips secrets, ignored dirs, binaries, and oversized files', () => {
    const dir = makeFixtureProject();
    const scan = scanProject(dir);
    const paths = scan.files.map((f) => f.relativePath);
    expect(paths).toContain('src/index.ts');
    expect(paths).toContain('tests/index.test.ts');
    expect(paths).toContain('package.json');
    expect(paths.some((p) => p.includes('node_modules'))).toBe(false);
    expect(paths.some((p) => p.includes('.env'))).toBe(false);
    expect(paths.some((p) => p.includes('secrets'))).toBe(false);
    expect(paths.some((p) => p.endsWith('.png'))).toBe(false);
    expect(paths).not.toContain('big.txt');
    expect(scan.skipped.secrets).toBeGreaterThanOrEqual(2);
    expect(scan.skipped.binaries).toBeGreaterThanOrEqual(1);
    expect(scan.skipped.oversized).toBeGreaterThanOrEqual(1);
  });

  it('never reads secret files even when asked directly', () => {
    const dir = makeFixtureProject();
    expect(readProjectFile(dir, '.env')).toBeNull();
    expect(readProjectFile(dir, '../.env')).toBeNull();
    expect(readProjectFile(dir, 'README.md')).toContain('Fixture');
  });
});

describe('project profile', () => {
  it('detects type, commands, tests, README, and produces a plain-English description', async () => {
    const dir = makeFixtureProject();
    const profile = await buildProjectProfile(dir);
    expect(profile.projectType).toBe('Node.js');
    expect(profile.commands.test).toBe('vitest run');
    expect(profile.hasTests).toBe(true);
    expect(profile.hasReadme).toBe(true);
    expect(profile.readmeExcerpt).toContain('A test project');
    expect(profile.description).toContain('Node.js');
    expect(profile.description.toLowerCase()).toContain('tests are present');
    expect(profile.languages).toContain('TypeScript');
  });

  it('reports a non-git directory honestly', async () => {
    const dir = makeFixtureProject();
    const git = await readGitInfo(dir);
    expect(git.isRepo).toBe(false);
    expect(git.recentCommits).toEqual([]);
    const profile = await buildProjectProfile(dir);
    expect(profile.health.notes.join(' ')).toContain('Not a git repository');
  });
});
