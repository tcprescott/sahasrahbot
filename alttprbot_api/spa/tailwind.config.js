/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  // Theming is driven by [data-theme] + CSS variables (tokens.css), so Tailwind
  // color utilities reference those variables and both themes stay first-class.
  // Preflight is disabled because tokens.css ships its own reset + element base.
  corePlugins: { preflight: false },
  theme: {
    extend: {
      colors: {
        bg0: 'var(--bg-0)',
        bg1: 'var(--bg-1)',
        bg2: 'var(--bg-2)',
        bg3: 'var(--bg-3)',
        line: 'var(--line)',
        'line-glow': 'var(--line-glow)',
        ink: 'var(--ink)',
        'ink-soft': 'var(--ink-soft)',
        'ink-faint': 'var(--ink-faint)',
        gold: 'var(--gold)',
        'gold-deep': 'var(--gold-deep)',
        teal: 'var(--teal)',
        'teal-deep': 'var(--teal-deep)',
        crimson: 'var(--crimson)',
        violet: 'var(--violet)',
      },
      fontFamily: {
        display: ['"Cinzel Decorative"', 'serif'],
        body: ['"Hanken Grotesk"', 'system-ui', 'sans-serif'],
        mono: ['"Space Mono"', 'monospace'],
      },
      maxWidth: { content: '1180px' },
    },
  },
  plugins: [],
};
