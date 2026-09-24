import { loadConfig } from './config/env';
import { buildApp } from './app';

const config = loadConfig();
const { app } = buildApp(config);

app
  .listen({ host: config.host, port: config.port })
  .then(() => {
    // Bound to 127.0.0.1 by default — local single-owner prototype.
    console.log(`JARVIS OS server listening on http://${config.host}:${config.port}`);
    console.log(`Model provider: ${config.modelProvider} | Data dir: ${config.dataDir}`);
  })
  .catch((error) => {
    console.error('Failed to start server:', error instanceof Error ? error.message : error);
    process.exit(1);
  });
