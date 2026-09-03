/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        sentinel: {
          bg: '#0a0d14',          // Near-black charcoal background
          surface: '#121722',     // Panel / card background
          surfaceHover: '#182030',
          border: '#1f293d',      // Subtle border
          borderLight: '#2b3852',
          text: '#f1f5f9',        // Off-white primary text
          muted: '#94a3b8',       // Gray muted text
          dim: '#64748b',         // Dim helper text
          risk: {
            red: '#ef4444',
            redBg: '#450a0a',
            redBorder: '#7f1d1d',
            amber: '#f59e0b',
            amberBg: '#451a03',
            amberBorder: '#78350f',
            green: '#10b981',
            greenBg: '#022c22',
            greenBorder: '#064e3b',
          },
          accent: '#3b82f6',      // Professional steel blue for active tabs/focus
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Menlo', 'Monaco', 'Courier New', 'monospace'],
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
