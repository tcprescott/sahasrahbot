import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// `process` is provided by Node when Vite loads this config. Declared locally so
// the config type-checks without pulling in `@types/node`.
declare const process: { env: Record<string, string | undefined> };

// SPA build output is served by Quart from `alttprbot/presentation/web/spa/dist/`.
// assetsDir is 'spa-assets' (not the default 'assets') to avoid colliding with
// Quart's existing /assets/ route that serves alttprbot/presentation/web/static/assets/.
//
// Backend proxy target: the Quart web+API app listens on port 5001 (see
// `sahasrahbot.py` and the default `APP_URL`). Override with VITE_API_PROXY_TARGET
// (e.g. when running the backend on a different host/port).
const apiProxyTarget = process.env.VITE_API_PROXY_TARGET ?? 'http://127.0.0.1:5001';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '127.0.0.1',
    proxy: {
      '/api': apiProxyTarget,
      '/presets': apiProxyTarget,
      '/async': apiProxyTarget,
      '/submit': apiProxyTarget,
    },
  },
  build: {
    outDir: 'dist',
    assetsDir: 'spa-assets',
    sourcemap: true,
  },
});
