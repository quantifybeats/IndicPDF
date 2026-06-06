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
          DEFAULT: '#6D28D9', // Electric Violet
          hover: '#5B21B6',
        },
        bg: '#0B0B0B',
        surface: '#161616',
        border: '#2A2A2A',
        text: {
          DEFAULT: '#E5E5E5',
          muted: '#A3A3A3',
        },
      },
      borderRadius: {
        'radius': '12px',
      },
      boxShadow: {
        'shadow': '0 4px 6px -1px rgba(0,0,0,0.5)',
        'shadow-lg': '0 10px 15px -3px rgba(0,0,0,0.7)',
        'glow': '0 0 15px rgba(109, 40, 217, 0.3)',
      },
      fontFamily: {
        sans: ['Inter', 'Poppins', 'sans-serif'],
        mono: ['DM Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
