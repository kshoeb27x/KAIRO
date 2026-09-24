// Removes the isolated e2e data directory before Playwright starts its web
// server (which opens the SQLite file and would lock it on Windows).
import fs from 'node:fs';
import path from 'node:path';

const dir = path.resolve(process.cwd(), '.data-e2e');
fs.rmSync(dir, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 });
console.log('e2e data directory reset:', dir);
