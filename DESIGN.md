# Ares Design Contract

Ares creates local-first coding tools, dynamic websites, and desktop-style apps
that feel serious, sharp, and useful from the first screen.

## Product Feel

- Calm, capable, technical, and direct.
- The first screen should be the working app or website experience, not a
  marketing placeholder.
- Prefer dense but readable layouts for tools, dashboards, builders, agents,
  editors, admin panels, and project workspaces.
- Use confident contrast, clear hierarchy, and practical controls.

## UI Rules

- Build responsive layouts for desktop and mobile.
- Use real sections, state, controls, and sample data instead of empty boxes.
- Use buttons only for clear commands; use tabs, toggles, sliders, inputs,
  menus, and segmented controls for settings.
- Keep cards to individual items, modals, and framed tools.
- Avoid nested cards, vague hero gradients, decorative blobs, and one-color
  palettes.
- Use stable dimensions for boards, counters, grids, toolbars, and repeated
  tiles so content does not jump when state changes.
- Keep text inside its container at every viewport.

## Visual Direction

- Primary colors: graphite, silver, white, and controlled red accents.
- Support colors: blue for information, green for success, amber for warnings.
- Avoid interfaces dominated by purple, beige, dark slate, or brown.
- Use border radii of 8px or less unless a component needs to be circular.
- Use shadows sparingly; prefer borders, spacing, and typography.

## Delivery Standard

- Generated website/app artifacts should include:
  - `index.html`
  - `styles.css`
  - `app.js`
  - `README.md`
- The artifact must run by opening `index.html`.
- JavaScript should add real interaction: filters, tabs, generated data,
  saved state, form handling, previews, calculators, or dashboard updates.
- The implementation should be self-contained unless the user explicitly asks
  for a framework.
