---
name: Technical Precision
colors:
  surface: '#131315'
  surface-dim: '#131315'
  surface-bright: '#39393b'
  surface-container-lowest: '#0e0e10'
  surface-container-low: '#1b1b1d'
  surface-container: '#1f1f21'
  surface-container-high: '#2a2a2c'
  surface-container-highest: '#353437'
  on-surface: '#e5e1e4'
  on-surface-variant: '#c2c7d0'
  inverse-surface: '#e5e1e4'
  inverse-on-surface: '#303032'
  outline: '#8c9199'
  outline-variant: '#42474f'
  surface-tint: '#a0cafc'
  primary: '#a0cafc'
  on-primary: '#003257'
  primary-container: '#1f4e79'
  on-primary-container: '#95bff1'
  inverse-primary: '#35618d'
  secondary: '#ffb784'
  on-secondary: '#4f2500'
  secondary-container: '#783b00'
  on-secondary-container: '#ffa867'
  tertiary: '#f5bc72'
  on-tertiary: '#462b00'
  tertiary-container: '#6a4300'
  on-tertiary-container: '#e9b268'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#d1e4ff'
  primary-fixed-dim: '#a0cafc'
  on-primary-fixed: '#001d35'
  on-primary-fixed-variant: '#184974'
  secondary-fixed: '#ffdcc6'
  secondary-fixed-dim: '#ffb784'
  on-secondary-fixed: '#301400'
  on-secondary-fixed-variant: '#713700'
  tertiary-fixed: '#ffddb5'
  tertiary-fixed-dim: '#f5bc72'
  on-tertiary-fixed: '#2a1800'
  on-tertiary-fixed-variant: '#643f00'
  background: '#0A0A0B'
  on-background: '#e5e1e4'
  surface-variant: '#353437'
  surface-elevated: '#1C1C1F'
  border-subtle: '#26272B'
  foreground: '#F4F4F5'
  foreground-muted: '#A1A1AA'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '600'
    lineHeight: '1.1'
    letterSpacing: -0.04em
  display-lg-mobile:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.03em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.02em
  body-base:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
    letterSpacing: 0em
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
    letterSpacing: 0em
  data-mono:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: -0.01em
  data-mono-lg:
    fontFamily: JetBrains Mono
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.02em
  label-caps:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.08em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  container-max: 1280px
  gutter: 16px
  margin-desktop: 24px
  margin-mobile: 16px
---

## Brand & Style

This design system is engineered for elite performance and technical authority. It adopts a "Quiet Premium" aesthetic—prioritizing density and information utility over decorative flourishes. The visual language is inspired by professional-grade engineering tools, emphasizing clarity, structured hierarchies, and rapid data ingestion.

The style is characterized by a "Linear-inspired" execution: high-density layouts, surgical 1px borders, and a monochromatic foundation punctuated by deep, meaningful accent colors. The interface feels like a high-performance instrument—cold, precise, and reliable. It avoids soft shadows and organic shapes in favor of geometric rigidity and typographic discipline, ensuring the user feels empowered by the data rather than overwhelmed by the interface.

## Colors

The color strategy for this design system is fundamentally dark, utilizing a "Deep Ink" palette to reduce eye strain during intensive data analysis. 

- **Foundation:** The background uses a near-black ink, while surface and elevated tiers use subtle tonal shifts rather than shadows to define depth.
- **Accents:** "Obelisk Blue" acts as the primary action color, signaling intelligence and stability. "Intensity Copper" is reserved for high-performance markers, milestones, or critical data points that require immediate cognitive attention.
- **Borders:** The primary method of separation is the 1px border color (`#26272B`), which provides a structural skeleton for the high-density layout without adding visual weight.

## Typography

The typography system is split into two distinct roles: **Functional UI** and **Performance Data.**

- **Inter** is the workhorse for all interface elements, navigation, and prose. For headlines, we employ a semi-bold weight (600) with tight tracking to evoke an authoritative, "dense" editorial feel.
- **JetBrains Mono** is used exclusively for numeric data, performance metrics, and technical labels. This ensures that weights, reps, and time intervals remain perfectly legible and tabular, allowing for quick scanning of vertical columns of data.
- All body text should adhere to a 14px baseline to maximize information density on screen without sacrificing readability.

## Layout & Spacing

This design system utilizes a **Fixed Grid** model for desktop to maintain the "instrumental" feel, centered within the viewport. On mobile, the layout transitions to a fluid model with tight 16px horizontal margins.

The spacing rhythm is built on a 4px baseline. To achieve the requested "high density" look, internal padding within components (like cards or list items) should be generous (16px–24px), but the gap between disparate components should be minimal (8px–12px). This creates "clusters" of information that feel unified and professional. Use vertical rules (1px) to separate sidebars or adjacent data columns instead of wide gutters.

## Elevation & Depth

Depth is conveyed through **Tonal Layering** rather than traditional drop shadows. This preserves the "flat" technical aesthetic while ensuring functional hierarchy.

1.  **Level 0 (Base):** The darkest color (`#0A0A0B`), used for the main application background.
2.  **Level 1 (Surface):** The primary container color (`#141416`), used for cards, sidebars, and main content areas.
3.  **Level 2 (Elevated):** The highlight color (`#1C1C1F`), used for hover states, active menu items, or modals.

Separation between these layers is reinforced by a **1px subtle border** (`#26272B`). Avoid blurs or glows unless they are used specifically for "AI-active" states, where a very subtle, low-opacity primary blue glow may be applied.

## Shapes

The shape language is "Soft-Geometric." We use a consistent 4px (0.25rem) corner radius for nearly all components, including cards, inputs, and buttons. 

This minimal rounding softens the harshness of the dark technical UI just enough to feel modern and premium, while maintaining the structural integrity of the grid. Larger elements like main containers may use a slightly increased radius of 8px (0.5rem), but pill-shaped or fully rounded elements are strictly prohibited to avoid a "consumer-grade" or "playful" appearance.

## Components

- **Buttons:** Primary buttons use a solid "Obelisk Blue" fill with white text. Secondary buttons use a ghost style: a 1px border (`#26272B`) with a subtle `#141416` fill on hover. 
- **Data Tables:** These are the core of the experience. Use JetBrains Mono for all cell values. Rows should be separated by 1px horizontal rules with no vertical borders. Use a `label-caps` style for headers.
- **Input Fields:** Flat backgrounds (`#141416`) with a 1px border. On focus, the border changes to "Obelisk Blue." Use monospaced type for numeric inputs.
- **Chips/Status:** Small, rectangular indicators with 2px rounding. Use Intensity Copper for "Peak Performance" or "High Intensity" states.
- **Cards:** Defined by their 1px border. Avoid shadows. When a card is "active," use a 1px "Obelisk Blue" border instead of a shadow.
- **Iconography:** Use 1.5px stroke weight. Icons should be geometric and never filled. Match icon color to the adjacent text (Foreground or Muted).
- **Progress Gauges:** Linear bars only. No circular loaders. Use a thin 2px height for background tracks and a 4px height for the active progress indicator to emphasize technical precision.