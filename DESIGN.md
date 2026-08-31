---
name: Modern Professional
colors:
  surface: '#08141f'
  surface-dim: '#08141f'
  surface-bright: '#2f3a46'
  surface-container-lowest: '#040f1a'
  surface-container-low: '#111d28'
  surface-container: '#15212c'
  surface-container-high: '#1f2b37'
  surface-container-highest: '#2a3642'
  on-surface: '#d7e4f3'
  on-surface-variant: '#bdc8d1'
  inverse-surface: '#d7e4f3'
  inverse-on-surface: '#26323d'
  outline: '#87929a'
  outline-variant: '#3e484f'
  surface-tint: '#7bd0ff'
  primary: '#8ed5ff'
  on-primary: '#00354a'
  primary-container: '#38bdf8'
  on-primary-container: '#004965'
  inverse-primary: '#00668a'
  secondary: '#b7c8e1'
  on-secondary: '#213145'
  secondary-container: '#3a4a5f'
  on-secondary-container: '#a9bad3'
  tertiary: '#ffc174'
  on-tertiary: '#472a00'
  tertiary-container: '#f59e0b'
  on-tertiary-container: '#613b00'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#c4e7ff'
  primary-fixed-dim: '#7bd0ff'
  on-primary-fixed: '#001e2c'
  on-primary-fixed-variant: '#004c69'
  secondary-fixed: '#d3e4fe'
  secondary-fixed-dim: '#b7c8e1'
  on-secondary-fixed: '#0b1c30'
  on-secondary-fixed-variant: '#38485d'
  tertiary-fixed: '#ffddb8'
  tertiary-fixed-dim: '#ffb95f'
  on-tertiary-fixed: '#2a1700'
  on-tertiary-fixed-variant: '#653e00'
  background: '#08141f'
  on-background: '#d7e4f3'
  surface-variant: '#2a3642'
typography:
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
---

# Design System: Modern Professional

## Brand & Style
The brand identity has transitioned from a light "Corporate Modern" feel to a high-contrast, tech-forward aesthetic. It maintains a sense of reliability and precision but shifts toward a more immersive, authoritative presence typical of command centers or high-end fintech dashboards. The visual language is inspired by dark-mode information environments where clarity and immediate focal points are paramount.

## Colors
The palette is built on a "Fidelity" variant, utilizing a professional dark-mode set with vibrant accents.
- **Primary:** #38BDF8 (Sky Blue)
- **Secondary:** #64748B (Slate Blue)
- **Tertiary:** #F59E0B (Amber)
- **Neutral:** #0F1B26 (Deep Navy)

The interface operates in a **Dark** color mode, focusing on high-contrast accents against deep navy surfaces to maintain a sense of order and sophisticated depth.

## Typography
The system uses **Inter** across all levels (Headlines, Body, and Labels). This typeface choice reflects a modern, Swiss-style clarity.
- **Headlines:** Semi-bold, tight tracking, used for clear section anchoring against dark backgrounds.
- **Body:** Standard weight, optimized for readability in data-heavy dark-themed views.
- **Labels:** Medium weight, used for navigation and form metadata.

## Layout & Spacing
The design utilizes a disciplined 8px rhythm. The layout philosophy is a **Fluid Grid** that adapts across breakpoints:
- **Mobile:** 16px gutters and margins.
- **Desktop:** 24px gutters with flexible content containers.
Spacing units scale from 4px (XS) to 32px (XL) to handle everything from micro-interactions to major section breaks.

## Elevation & Depth
Visual hierarchy is conveyed through **Tonal Layers** and **Low-Contrast Outlines**. Instead of aggressive shadows, the system uses subtle background shifts (using the Deep Navy palette) and 1px borders in the Slate secondary color to define boundaries. Elevation for floating elements is handled via soft, dark ambient shadows that blend into the background.

## Shapes
The design employs a **Rounded** shape language (roundedness level 2). 
- **Standard UI elements:** 0.5rem (8px) radius.
- **Large components:** 1rem (16px) radius.
This choice balances the technical nature of the dark theme with an approachable, modern feel.

## Components
- **Buttons:** High-contrast Primary Sky Blue fills with 8px rounding.
- **Input Fields:** Clean borders with internal padding following the 8px grid, set against deep navy surfaces.
- **Cards:** Defined by tonal background shifts and subtle outlines rather than shadows, creating a "layered dark" look.
- **Chips/Badges:** Small, 8px rounded elements using secondary or tertiary accents for categorization and status alerts.