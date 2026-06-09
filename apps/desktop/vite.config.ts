import { resolve } from 'node:path';

import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// Tauri expects a fixed dev port and leaves the build to Vite.
export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  // Load VITE_* vars from the repo-root .env (the single source of truth).
  envDir: resolve(__dirname, '../..'),
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      // Workspace packages are TS source; alias them so Vite treats them as app code.
      '@obelisk/types': resolve(__dirname, '../../packages/types/src/index.ts'),
      '@obelisk/api-client': resolve(__dirname, '../../packages/api-client/src/index.ts'),
      '@obelisk/design-tokens': resolve(__dirname, '../../packages/design-tokens/src/index.ts'),
    },
  },
  server: {
    port: 1420,
    strictPort: true,
  },
  build: {
    target: 'es2022',
    outDir: 'dist',
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
  },
});
