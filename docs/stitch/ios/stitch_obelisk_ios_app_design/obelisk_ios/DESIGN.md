---
name: Obelisk iOS
colors:
  surface: '#121317'
  surface-dim: '#121317'
  surface-bright: '#38393d'
  surface-container-lowest: '#0d0e12'
  surface-container-low: '#1a1b1f'
  surface-container: '#1e1f23'
  surface-container-high: '#292a2e'
  surface-container-highest: '#343539'
  on-surface: '#e3e2e7'
  on-surface-variant: '#c7c6ca'
  inverse-surface: '#e3e2e7'
  inverse-on-surface: '#2f3034'
  outline: '#919094'
  outline-variant: '#46464a'
  surface-tint: '#c8c6c7'
  primary: '#c8c6c7'
  on-primary: '#313031'
  primary-container: '#0a0a0b'
  on-primary-container: '#7a797a'
  inverse-primary: '#5f5e5f'
  secondary: '#a0cafc'
  on-secondary: '#003257'
  secondary-container: '#184974'
  on-secondary-container: '#8eb8ea'
  tertiary: '#ffb784'
  on-tertiary: '#4f2500'
  tertiary-container: '#160600'
  on-tertiary-container: '#b0672d'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#e5e2e3'
  primary-fixed-dim: '#c8c6c7'
  on-primary-fixed: '#1c1b1c'
  on-primary-fixed-variant: '#474647'
  secondary-fixed: '#d1e4ff'
  secondary-fixed-dim: '#a0cafc'
  on-secondary-fixed: '#001d35'
  on-secondary-fixed-variant: '#184974'
  tertiary-fixed: '#ffdcc6'
  tertiary-fixed-dim: '#ffb784'
  on-tertiary-fixed: '#301400'
  on-tertiary-fixed-variant: '#713700'
  background: '#121317'
  on-background: '#e3e2e7'
  surface-variant: '#343539'
typography:
  hero-num:
    fontFamily: JetBrains Mono
    fontSize: 64px
    fontWeight: '600'
    lineHeight: 72px
    letterSpacing: -0.02em
  page-title:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 34px
    letterSpacing: -0.01em
  section-label:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.06em
  body:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  dense-mono:
    fontFamily: JetBrains Mono
    fontSize: 15px
    fontWeight: '500'
    lineHeight: 20px
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  safe-margin: 16px
  gutter: 12px
  stack-sm: 4px
  stack-md: 8px
  stack-lg: 16px
  section-gap: 32px
---

## Brand & Style

The design system is engineered for the high-performance athlete and technical researcher. It rejects the "gamified" fitness trends of bright gradients and celebratory pop-ups in favor of a **technical research-instrument aesthetic**. The UI should feel like a specialized tool—precise, authoritative, and calm.

The visual direction follows a **Technical Minimalism** approach, blending the organizational rigor of Linear with the spatial clarity of Things 3. Every element exists to serve data density and utility. There are no hero photos or decorative illustrations; the data itself is the visual protagonist. The emotional response should be one of focused control and sober analysis.

## Colors

This design system is strictly **Dark Mode**. The palette is anchored by a deep obsidian base to minimize eye strain and maximize the contrast of technical data points.

- **Background (#0A0A0B):** The primary canvas. Use pure black (#000000) for high-level container backgrounds to create depth on OLED displays.
- **Obelisk Blue (#1F4E79):** The primary accent. Used for interactive elements, selection states, and active data streams. It is desaturated to maintain a professional, "instrumental" feel.
- **Intensity Copper (#C97B3F):** A functional utility color dedicated exclusively to Personal Records (PRs) and peak intensity metrics. It provides a warm, metallic contrast to the cool primary palette.
- **Surface Neutrals:** Use a scale of tiered grays (#1C1C1E, #2C2C2E) to define card structures and input fields.

## Typography

The typographic system uses a functional split-role strategy. **Inter** handles all linguistic communication, providing a clean, neutral interface. **JetBrains Mono** is utilized for all numerical data and load-bearing metrics, ensuring that digits are easy to scan and compare across tabular layouts.

- **Numerical Precision:** All percentages, weights, times, and counts must use JetBrains Mono.
- **Section Headers:** Always use the `section-label` style (13pt, Uppercase, Tracking +6%) to provide clear architectural boundaries.
- **Hero Metrics:** The `hero-num` style is reserved for the single most important metric on a screen (e.g., Today's strain or total volume).

## Layout & Spacing

The layout adheres to **iOS 17/18 Human Interface Guidelines**, optimized for the iPhone 15 Pro (393pt width). 

- **The Dense Grid:** Content should feel tightly packed but organized. Use a 4px baseline grid.
- **Margins:** Standard horizontal safe margin of 16px. 
- **Tab Bar:** 5-tab structure (Today, Plan, Coach, Log, Profile) using SF Symbols with 2px stroke weight for a refined, technical appearance.
- **Reflow:** In dense rows (Log/Plan), use the `dense-mono` style for numerical data to ensure tabular alignment across vertical lists.

## Elevation & Depth

This design system uses **Tonal Layering** rather than heavy shadows to indicate hierarchy. 

- **Level 0 (Base):** #000000 (Pure Black) for the main background.
- **Level 1 (Platters):** #1C1C1E (Dark Gray) for primary cards and grouped list sections.
- **Level 2 (In-layer):** #2C2C2E for secondary elements like input fields or nested buttons.
- **Outlines:** Use thin, low-contrast 1px borders (#38383A) for card definitions instead of shadows. This maintains the "instrument" feel.
- **Glass:** A subtle backdrop blur (Material Dark) may be used on the Navigation Bar and Tab Bar to provide a sense of place during scroll.

## Shapes

The shape language is **Soft (0.25rem / 4px base)**. While modern iOS uses very large corner radii, this design system reduces them to evoke professional hardware and laboratory equipment.

- **Small Components:** 4px radius (Checkboxes, small tags).
- **Standard Cards:** 8px radius (`rounded-lg`).
- **Large Containers:** 12px radius (`rounded-xl`).
- **Buttons:** Subtle rounding only; do not use pill-shapes or circular buttons unless for icon-only actions.

## Components

- **Buttons:** High-contrast primary buttons use Obelisk Blue background with White text. Secondary buttons use a #2C2C2E fill with no border. No drop shadows.
- **Data Rows:** Used extensively in 'Log' and 'Today'. Must feature a leading label in Inter and a trailing value in JetBrains Mono.
- **Intensity Chips:** Small, rectangular chips using Intensity Copper (#C97B3F) text on a low-opacity copper background (15% alpha) to highlight PRs.
- **Input Fields:** Inset style with #1C1C1E background and 1px #38383A border. Placeholders in #8E8E93 Inter.
- **Progress Bars:** Thin 4px tracks. The "unfilled" portion should be #2C2C2E; the "filled" portion should be Obelisk Blue. For intensity-based goals, the fill switches to Intensity Copper.
- **Checkboxes:** Square with a 2px radius. When active, fill with Obelisk Blue and use a white checkmark.