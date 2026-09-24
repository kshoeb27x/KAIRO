// Usage: npm run restore -- --input <directory> [--force]
// Stop the server first — restoring while the app holds the database is unsafe.
import { parseArgs } from 'node:util';
import { loadConfig } from '../src/server/config/env';
import { restoreBackup } from '../src/server/persistence/backup';

const { values } = parseArgs({
  options: {
    input: { type: 'string' },
    force: { type: 'boolean', default: false },
  },
  args: process.argv.slice(2),
});

if (!values.input) {
  console.error('Usage: npm run restore -- --input <directory> [--force]');
  process.exit(1);
}

const config = loadConfig();
restoreBackup(config.dataDir, values.input, { force: values.force })
  .then((result) => {
    console.log(`Restore complete into ${config.dataDir}`);
    if (result.preRestoreBackupDir) {
      console.log(`Pre-restore backup of the replaced store: ${result.preRestoreBackupDir}`);
    }
    console.log('Validated table counts:', JSON.stringify(result.manifest.tableCounts));
  })
  .catch((error: unknown) => {
    console.error('Restore failed:', error instanceof Error ? error.message : error);
    process.exit(1);
  });
