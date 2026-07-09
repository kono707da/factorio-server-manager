/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        factorio: {
          bg: '#0f0f1a',
          surface: '#1a1a2e',
          card: '#16213e',
          border: '#2a2a4a',
          accent: '#e2703a',
          'accent-light': '#f0a500',
          success: '#00b894',
          danger: '#e74c3c',
          info: '#0984e3',
          text: '#e0e0e0',
          'text-muted': '#8888aa',
        }
      },
      fontFamily: {
        display: ['Rajdhani', 'sans-serif'],
        body: ['Source Sans 3', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}
