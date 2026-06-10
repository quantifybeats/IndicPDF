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
        primary: {
          DEFAULT: 'rgb(var(--primary-rgb) / <alpha-value>)',
          hover: 'var(--primary-hover)',
        },
        bg: 'var(--bg)',
        surface: 'var(--surface)',
        'surface-overlay': 'var(--surface-overlay)',
        border: 'rgb(var(--border-rgb) / <alpha-value>)',
        text: {
          DEFAULT: 'var(--text)',
          muted: 'var(--text-muted)',
        },
      },
      borderRadius: {
        'radius': '12px',
        'radius-xl': '16px',
      },
      boxShadow: {
        'shadow': 'var(--shadow)',
        'shadow-lg': 'var(--shadow-lg)',
        'glow': '0 0 15px rgba(255, 75, 75, 0.3)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Plus Jakarta Sans', 'Inter', 'sans-serif'],
        mono: ['DM Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
