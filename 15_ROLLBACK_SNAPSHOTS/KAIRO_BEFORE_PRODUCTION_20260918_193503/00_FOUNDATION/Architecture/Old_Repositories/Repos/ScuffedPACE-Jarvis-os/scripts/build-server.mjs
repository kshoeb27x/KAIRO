// Bundles the Fastify server for production (`npm start` runs the output).
// Dependencies stay external — they resolve from node_modules at runtime.
import { build } from 'esbuild';

await build({
  entryPoints: ['src/server/index.ts'],
  bundle: true,
  platform: 'node',
  format: 'esm',
  target: 'node24',
  packages: 'external',
  outfile: 'dist/server/index.js',
  sourcemap: false,
  banner: {
    js: "import { createRequire } from 'node:module'; const require = createRequire(import.meta.url);",
  },
});

console.log('Server bundle written to dist/server/index.js');
