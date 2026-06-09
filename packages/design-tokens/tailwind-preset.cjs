/**
 * Tailwind preset carrying the Obelisk palette + type scale. Consumed by
 * apps/desktop/tailwind.config.ts. Kept as CJS so Tailwind (Node) loads it directly.
 */
module.exports = {
  theme: {
    extend: {
      colors: {
        background: '#0A0A0B',
        surface: '#141416',
        'surface-elevated': '#1C1C1F',
        'border-subtle': '#26272B',
        foreground: '#F4F4F5',
        'foreground-muted': '#A1A1AA',
        primary: { DEFAULT: '#1F4E79', accent: '#A0CAFC' },
        copper: '#FFB784',
        error: '#FFB4AB',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        'label-caps': ['11px', { lineHeight: '16px', letterSpacing: '0.08em', fontWeight: '600' }],
        'body-sm': ['12px', { lineHeight: '16px' }],
        'body-base': ['14px', { lineHeight: '20px' }],
        'headline-md': ['24px', { lineHeight: '32px', letterSpacing: '-0.02em' }],
        'display-lg': ['48px', { lineHeight: '1.1', letterSpacing: '-0.04em' }],
      },
      borderRadius: { DEFAULT: '0.25rem', lg: '0.5rem' },
    },
  },
};
