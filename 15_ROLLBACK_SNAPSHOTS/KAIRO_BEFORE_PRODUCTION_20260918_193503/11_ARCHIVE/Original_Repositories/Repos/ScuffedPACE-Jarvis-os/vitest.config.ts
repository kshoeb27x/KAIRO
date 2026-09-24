import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

// Client component tests opt into jsdom with a `// @vitest-environment jsdom`
// docblock; everything else runs in node.
export default defineConfig({
  plugins: [react()],
  test: {
    include: ['tests/unit/**/*.test.{ts,tsx}', 'tests/integration/**/*.test.ts'],
    environment: 'node',
    setupFiles: ['tests/setup.ts'],
    testTimeout: 15000,
  },
});
