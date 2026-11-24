import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'
import svgr from 'vite-plugin-svgr'

// `npm run dev` serves the app on :5173 and proxies everything the Quart app answers
// itself (the API, Discord sign-in, racetime linking, downloads, the dev server's
// fakes) to it, so the session cookie and API calls share one origin.
// SAHASRAHBOT_API points the proxy at another backend.
const backend = process.env.SAHASRAHBOT_API ?? 'http://localhost:5001'
const proxied = ['/api', '/login', '/callback', '/logout', '/racetime', '/presets/download', '/presets/api', '/_dev', '/_fake']

export default defineConfig({
  plugins: [react(), svgr()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: Object.fromEntries(proxied.map((path) => [path, { target: backend, changeOrigin: false }])),
  },
  build: {
    sourcemap: true,
  },
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.{ts,tsx}'],
    setupFiles: ['src/test/setup.ts'],
    // `npm run test:coverage` (CI) fails below these. Raise them when coverage
    // goes up; don't lower them to get a PR through.
    coverage: {
      provider: 'v8',
      include: ['src/**'],
      exclude: ['src/**/*.test.{ts,tsx}', 'src/test/**', 'src/api/schema.d.ts', 'src/main.tsx'],
      thresholds: { lines: 90, statements: 90, functions: 90, branches: 85 },
    },
  },
})
