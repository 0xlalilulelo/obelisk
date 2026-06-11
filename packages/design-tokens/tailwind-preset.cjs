/**
 * Tailwind preset carrying the Obelisk palette + type scale. Consumed by
 * apps/desktop/tailwind.config.ts. Kept as CJS so Tailwind (Node) loads it directly.
 */
module.exports = {
  theme: {
    extend: {
      // Channels live in apps/desktop/src/index.css (:root + :root.light) so the
      // theme toggle swaps the variable set; the <alpha-value> form keeps
      // Tailwind opacity modifiers (bg-surface/60) working.
      colors: {
        background: 'rgb(var(--color-background) / <alpha-value>)',
        surface: 'rgb(var(--color-surface) / <alpha-value>)',
        'surface-elevated': 'rgb(var(--color-surface-elevated) / <alpha-value>)',
        'border-subtle': 'rgb(var(--color-border-subtle) / <alpha-value>)',
        foreground: 'rgb(var(--color-foreground) / <alpha-value>)',
        'foreground-muted': 'rgb(var(--color-foreground-muted) / <alpha-value>)',
        primary: {
          DEFAULT: 'rgb(var(--color-primary) / <alpha-value>)',
          accent: 'rgb(var(--color-primary-accent) / <alpha-value>)',
        },
        copper: 'rgb(var(--color-copper) / <alpha-value>)',
        error: 'rgb(var(--color-error) / <alpha-value>)',
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
