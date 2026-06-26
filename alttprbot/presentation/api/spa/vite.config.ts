import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// SPA build output is served by Quart from `alttprbot_api/spa/dist/`.
// assetsDir is 'spa-assets' (not the default 'assets') to avoid colliding with
// Quart's existing /assets/ route that serves alttprbot_api/static/assets/.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '127.0.0.1',
    proxy: {
      '/api': 'http://127.0.0.1:5000',
      '/presets': 'http://127.0.0.1:5000',
      '/async': 'http://127.0.0.1:5000',
      '/submit': 'http://127.0.0.1:5000',
    },
  },
  build: {
    outDir: 'dist',
    assetsDir: 'spa-assets',
    sourcemap: true,
  },
});
