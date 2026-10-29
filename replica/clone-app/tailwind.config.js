/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: '#000000',
        surface: '#121212',
        'surface-elevated': '#1E1E1E',
        border: '#282828',
        'border-input': '#3F3F46',
        text: '#FFFFFF',
        'text-muted': '#A1A1AA',
        accent: '#06B6D4',
        'on-accent': '#000000',
        danger: '#EF4444',
        success: '#10B981',
        warning: '#F59E0B',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      animation: {
        'spin-slow': 'spin 8s linear infinite',
      }
    },
  },
  plugins: [],
}
