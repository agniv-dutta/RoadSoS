/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#000000',
        primary: {
          DEFAULT: '#E8A020',
          glow: 'rgba(232, 160, 32, 0.15)',
        },
        danger: {
          DEFAULT: '#E63946',
          glow: 'rgba(230, 57, 70, 0.25)',
        },
        safe: {
          DEFAULT: '#2ECC71',
          glow: 'rgba(46, 204, 113, 0.15)',
        },
        info: {
          DEFAULT: '#3A86FF',
          glow: 'rgba(58, 134, 255, 0.15)',
        },
        textPrimary: '#FFFFFF',
        textSecondary: '#A0A0A0',
        textTertiary: '#555555',
        cardSurface: 'rgba(255, 255, 255, 0.04)',
        cardBorder: 'rgba(255, 255, 255, 0.08)',
      },
      fontFamily: {
        heading: ['Space Grotesk', 'sans-serif'],
        bebas: ['Bebas Neue', 'sans-serif'],
        space: ['Space Grotesk', 'sans-serif'],
        body: ['DM Sans', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      borderRadius: {
        card: '8px',
        pill: '999px',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'bounce-gentle': 'bounceGentle 3s ease-in-out infinite',
        'blink': 'blink 1.5s step-end infinite',
      },
      keyframes: {
        bounceGentle: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-8px)' },
        },
        blink: {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0 },
        }
      }
    },
  },
  plugins: [],
}
