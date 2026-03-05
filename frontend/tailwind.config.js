/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        signal: {
          'strong-buy': '#059669',
          'buy': '#10b981',
          'neutral': '#d97706',
          'sell': '#ea580c',
          'strong-sell': '#dc2626',
        },
        accent: {
          primary: '#2563eb',
          'primary-light': '#3b82f6',
          secondary: '#0891b2',
        },
        bg: {
          primary: '#f8f9fa',
          secondary: '#ffffff',
          card: '#ffffff',
          'card-hover': '#f1f3f4',
          accent: '#e8f4fd',
        },
        text: {
          primary: '#1a1a2e',
          secondary: '#4a5568',
          muted: '#718096',
        },
        border: {
          DEFAULT: '#e2e8f0',
          light: '#f1f5f9',
        }
      },
      fontFamily: {
        sans: ['Pretendard Variable', 'Pretendard', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
      },
      boxShadow: {
        'sm': '0 1px 3px rgba(0, 0, 0, 0.08)',
        'md': '0 4px 12px rgba(0, 0, 0, 0.08)',
        'lg': '0 10px 25px rgba(0, 0, 0, 0.1)',
      },
      keyframes: {
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        shimmer: {
          '0%, 100%': { boxShadow: '0 0 6px 1px rgba(234, 179, 8, 0.25)' },
          '50%': { boxShadow: '0 0 20px 4px rgba(234, 179, 8, 0.5)' },
        },
        'danger-shimmer': {
          '0%, 100%': { boxShadow: '0 0 6px 1px rgba(239, 68, 68, 0.25)' },
          '50%': { boxShadow: '0 0 20px 4px rgba(239, 68, 68, 0.5)' },
        },
        'overheat-shimmer': {
          '0%, 100%': { boxShadow: '0 0 6px 1px rgba(249, 115, 22, 0.25)' },
          '50%': { boxShadow: '0 0 20px 4px rgba(249, 115, 22, 0.5)' },
        },
        'reverse-shimmer': {
          '0%, 100%': { boxShadow: '0 0 6px 1px rgba(139, 92, 246, 0.25)' },
          '50%': { boxShadow: '0 0 20px 4px rgba(139, 92, 246, 0.5)' },
        },
      },
      animation: {
        'fade-in': 'fade-in 0.2s ease-out',
        shimmer: 'shimmer 3s ease-in-out infinite',
        'danger-shimmer': 'danger-shimmer 2s ease-in-out infinite',
        'overheat-shimmer': 'overheat-shimmer 2s ease-in-out infinite',
        'reverse-shimmer': 'reverse-shimmer 2.5s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
