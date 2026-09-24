// Usage: npm run backup -- --output <directory>
import { parseArgs } from 'node:util';
import { loadConfig } from '../src/server/config/env';
import { createBackup } from '../src/server/persistence/backup';

const { values } = parseArgs({
  options: { output: { type: 'string' } },
  args: process.argv.slice(2),
});

if (!values.output) {
  console.error('Usage: npm run backup -- --output <directory>');
  process.exit(1);
}

const config = loadConfig();
createBackup(config.dataDir, values.output)
  .then((manifest) => {
    console.log(`Backup written to ${values.output}`);
    console.log(
      `app v${manifest.appVersion}, schema v${manifest.schemaVersion}, ` +
        `checksum ${manifest.databaseChecksum.slice(0, 12)}…`,
    );
    console.log('Table counts:', JSON.stringify(manifest.tableCounts));
  })
  .catch((error: unknown) => {
    console.error('Backup failed:', error instanceof Error ? error.message : error);
    process.exit(1);
  });
