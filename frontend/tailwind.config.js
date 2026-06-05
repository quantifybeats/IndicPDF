/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#e53e3e',
          hover: '#c53030',
        },
        bg: '#f3f3f2',
        text: {
          DEFAULT: '#333333',
          muted: '#666666',
        },
        surface: '#ffffff',
        border: '#e0e0e0',
      },
      borderRadius: {
        'radius': '12px',
      },
      boxShadow: {
        'shadow': '0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06)',
        'shadow-lg': '0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05)',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['DM Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
