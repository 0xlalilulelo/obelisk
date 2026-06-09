/**
 * Obelisk design tokens — the "Technical Precision / Quiet Premium" system from
 * docs/stitch/.../technical_precision/DESIGN.md. Shared by the desktop app
 * (via the Tailwind preset) and hand-translated for iOS.
 */

export const colors = {
  // Elevation (tonal layering, not shadows)
  background: '#0A0A0B', // Level 0 — app background
  surface: '#141416', // Level 1 — cards, sidebars, panes
  surfaceElevated: '#1C1C1F', // Level 2 — hover, active, modals
  borderSubtle: '#26272B', // 1px structural skeleton
  // Text
  foreground: '#F4F4F5',
  foregroundMuted: '#A1A1AA',
  // Accents
  primary: '#1F4E79', // Obelisk Blue (action)
  primaryAccent: '#A0CAFC', // bright blue (AI-active, highlights)
  copper: '#FFB784', // Intensity Copper (peak/high-intensity markers)
  // Semantic
  error: '#FFB4AB',
  success: '#A0CAFC',
} as const;

export const typography = {
  fontSans: "'Inter', system-ui, -apple-system, sans-serif",
  fontMono: "'JetBrains Mono', ui-monospace, monospace",
  displayLg: { size: '48px', weight: 600, tracking: '-0.04em', leading: '1.1' },
  headlineMd: { size: '24px', weight: 600, tracking: '-0.02em', leading: '32px' },
  bodyBase: { size: '14px', weight: 400, tracking: '0', leading: '20px' },
  bodySm: { size: '12px', weight: 400, tracking: '0', leading: '16px' },
  dataMono: { size: '14px', weight: 500, tracking: '-0.01em', leading: '20px' },
  labelCaps: { size: '11px', weight: 600, tracking: '0.08em', leading: '16px' },
} as const;

export const radius = {
  DEFAULT: '0.25rem', // 4px — soft-geometric default
  lg: '0.5rem', // 8px — large containers
} as const;

export const spacing = {
  unit: 4,
  sidebar: 280,
  rightPane: 360,
} as const;

export const tokens = { colors, typography, radius, spacing };
