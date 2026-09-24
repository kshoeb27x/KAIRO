import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Frontend dev server. All /api traffic is proxied to the local Fastify server.
export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8787',
        changeOrigin: false,
      },
    },
  },
  build: {
    outDir: 'dist/client',
    emptyOutDir: true,
  },
});
