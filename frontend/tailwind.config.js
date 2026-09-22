/** @type {import('tailwindcss').Config} */

// Colours are driven by the CSS custom properties in src/styles/tokens.css
// so that an institution's brand can be themed at runtime without a rebuild.
const token = (name) => `var(--${name})`;

export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: {
          50: token('brand-50'),
          100: token('brand-100'),
          200: token('brand-200'),
          300: token('brand-300'),
          400: token('brand-400'),
          500: token('brand-500'),
          600: token('brand-600'),
          700: token('brand-700'),
          800: token('brand-800'),
          900: token('brand-900'),
          950: token('brand-950'),
        },
        canvas: token('canvas'),
        surface: token('surface'),
        line: token('border'),
        ink: {
          900: token('ink-900'),
          700: token('ink-700'),
          600: token('ink-600'),
          500: token('ink-500'),
        },

        // Compatibility aliases for screens not yet migrated to the brand
        // tokens above. They point at the corrected values, so the contrast
        // failures in the previous palette are fixed everywhere at once
        // rather than only on rewritten screens. Remove once every screen
        // uses brand-*, ink-* and the status tokens.
        primary: {
          50: '#ECFDF5',
          100: '#D1FAE5',
          200: '#A7F3D0',
          300: '#6EE7B7',
          400: '#34D399',
          500: '#0B8A6B',
          600: '#0B6B57',
          700: '#065F46',
          800: '#064E3B',
          900: '#022C22',
          950: '#011811',
        },
        secondary: {
          50: '#ECFDF5',
          100: '#D1FAE5',
          200: '#A7F3D0',
          300: '#6EE7B7',
          400: '#34D399',
          500: '#0B8A6B',
          600: '#0B6B57',
          700: '#065F46',
          800: '#064E3B',
          900: '#022C22',
        },
        // Gold against the green. 200-500 are tokenised so they can be
        // themed with the rest; the remaining steps stay literal because
        // nothing uses them yet.
        accent: {
          50: '#FFFBEB',
          100: '#FEF3C7',
          200: token('accent-200'),
          300: token('accent-300'),
          400: token('accent-400'),
          500: token('accent-500'),
          600: '#8A6508',
          700: '#6B4E06',
          800: '#4A3604',
          900: '#2B1F02',
        },
        neutral: {
          50: '#F7F8FA',
          100: '#F1F3F6',
          200: '#E5E7EB',
          300: '#D4D8DE',
          400: '#9CA3AF',
          500: '#6B7280',
          600: '#4B5563',
          700: '#1F2937',
          800: '#111827',
          900: '#0A0F1A',
          950: '#05080F',
        },
        success: {
          50: '#ECFDF5',
          100: '#D1FAE5',
          200: '#A7F3D0',
          300: '#6EE7B7',
          400: '#34D399',
          500: '#046C4E',
          600: '#046C4E',
          700: '#065F46',
          800: '#064E3B',
          900: '#022C22',
        },
        warning: {
          50: '#FFF7ED',
          100: '#FFEDD5',
          200: '#FED7AA',
          300: '#FDBA74',
          400: '#FB923C',
          500: '#B45309',
          600: '#B45309',
          700: '#92400E',
          800: '#78350F',
          900: '#451A03',
        },
        danger: {
          50: '#FEF2F2',
          100: '#FEE2E2',
          200: '#FECACA',
          300: '#FCA5A5',
          400: '#F87171',
          500: '#B91C1C',
          600: '#B91C1C',
          700: '#991B1B',
          800: '#7F1D1D',
          900: '#450A0A',
        },
        info: {
          50: '#EFF4FF',
          100: '#DBEAFE',
          200: '#BFDBFE',
          300: '#93C5FD',
          400: '#60A5FA',
          500: '#1D4ED8',
          600: '#1D4ED8',
          700: '#1E40AF',
          800: '#1E3A8A',
          900: '#172554',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
        display: ['Outfit', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'SF Mono', 'Menlo', 'monospace'],
      },
      fontSize: {
        // Body never drops below 16px: users read on small screens in
        // bright sunlight.
        base: ['1rem', { lineHeight: '1.625rem' }],
        sm: ['0.875rem', { lineHeight: '1.375rem' }],
        caption: ['0.8125rem', { lineHeight: '1.125rem' }],
        '2xs': ['0.6875rem', { lineHeight: '0.875rem' }],
      },
      borderRadius: {
        sm: 'var(--r-sm)',
        md: 'var(--r-md)',
        lg: 'var(--r-lg)',
        xl: 'var(--r-xl)',
        '2xl': 'var(--r-2xl)',
      },
      boxShadow: {
        e1: 'var(--e1)',
        e2: 'var(--e2)',
        e3: 'var(--e3)',
        e4: 'var(--e4)',
        // Aliases kept for screens not yet migrated to the e1-e4 scale.
        soft: 'var(--e2)',
        'soft-xl': 'var(--e4)',
      },
      transitionTimingFunction: {
        standard: 'cubic-bezier(.2,.8,.2,1)',
      },
      minHeight: {
        touch: '44px',
      },
      minWidth: {
        touch: '44px',
      },
      keyframes: {
        'fade-up': {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pop: {
          '0%': { opacity: '0', transform: 'scale(.6)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
      animation: {
        'fade-up': 'fade-up .22s cubic-bezier(.2,.8,.2,1)',
        pop: 'pop .45s cubic-bezier(.2,.8,.2,1)',
        shimmer: 'shimmer 1.6s infinite linear',
      },
    },
  },
  plugins: [],
};
