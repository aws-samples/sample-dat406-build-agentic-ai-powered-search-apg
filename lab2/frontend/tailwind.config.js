/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class', // Enable class-based dark mode
  theme: {
    extend: {
      colors: {
        // Dark theme backgrounds
        'bg-primary': '#0a0a0f',
        'bg-secondary': '#0d0d1a',
        
        // Purple accent colors (matching prototype)
        'accent-purple': '#6a1b9a',
        'accent-light': '#ba68c8',
        
        // Text colors - will be overridden by CSS variables
        'text-primary': 'var(--text-primary, #ffffff)',
        'text-secondary': 'var(--text-secondary, #a0a0a0)',
        
        // Aurora colors
        'aurora-blue': '#00c8ff',
        'aurora-green': '#00ff88',
        
        // Utility colors
        'border-subtle': 'var(--border-color, rgba(106, 27, 154, 0.2))',
        'success': '#4ade80',
        'warning': '#fbbf24',
        
        // Light mode specific
        'light-bg': '#f8f9fa',
        'light-surface': '#ffffff',
        'light-text': '#1a1a1a',
        'light-text-muted': '#6b7280',
      },
      fontWeight: {
        'light': '300',
        'normal': '400',
        'medium': '500',
      },
      backdropBlur: {
        'xs': '2px',
        'xl': '30px',
      },
      animation: {
        'float': 'float 3s ease-in-out infinite',
        'fadeIn': 'fadeIn 0.6s ease-in-out forwards',
        'slideUp': 'slideUp 0.3s ease-out',
        'pulse-glow': 'pulse 2s infinite',
        'shimmer': 'shimmer 2s linear infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        fadeIn: {
          'to': { opacity: '1' },
        },
        slideUp: {
          'from': { opacity: '0', transform: 'translateY(10px)' },
          'to': { opacity: '1', transform: 'translateY(0)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-1000px 0' },
          '100%': { backgroundPosition: '1000px 0' },
        },
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(ellipse at center, var(--tw-gradient-stops))',
        'gradient-conic': 'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
      },
    },
  },
  plugins: [],
}