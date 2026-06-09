import preset from '@obelisk/design-tokens/tailwind-preset';
import type { Config } from 'tailwindcss';

export default {
  darkMode: 'class',
  presets: [preset],
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      gridTemplateColumns: {
        // Three-pane: sidebar | center | right (Stitch desktop layout).
        shell: '280px 1fr 360px',
      },
    },
  },
  plugins: [],
} satisfies Config;
