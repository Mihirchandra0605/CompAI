/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        display: ['Syne', 'sans-serif'],
        body: ['DM Sans', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        ink: '#0a0a0f',
        panel: '#11111a',
        card: '#16161f',
        border: '#1e1e2e',
        accent: '#00e5ff',
        'accent-dim': '#00b8cc',
        muted: '#3a3a52',
        faint: '#22223a',
        success: '#00ff9d',
        error: '#ff4d6d',
        warn: '#ffb300',
      },
      boxShadow: {
        'glow': '0 0 20px rgba(0,229,255,0.15)',
        'glow-success': '0 0 20px rgba(0,255,157,0.15)',
        'glow-error': '0 0 20px rgba(255,77,109,0.15)',
      }
    },
  },
  plugins: [],
}
