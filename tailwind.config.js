/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,jsx,ts,tsx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Segoe UI Variable', 'Segoe UI', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['Cascadia Code', 'Consolas', 'monospace'],
      },
      colors: {
        orion: {
          blue:   '#60a5fa',
          purple: '#a78bfa',
          green:  '#34d399',
          amber:  '#f59e0b',
          red:    '#f87171',
        },
      },
      backdropBlur: {
        mica: '40px',
      },
    },
  },
  plugins: [],
};
