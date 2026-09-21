# YPGym workout visual system

The post-Day-60 visual system uses white as the primary canvas, deep gym green for actions and identity, a lighter green for positive states, near-black text and semantic warning/error colors. It applies first to the Expo member app and to the reusable web shell. It does not change API behavior or authorization.

## Shared semantic tokens

| Purpose | Mobile token | Mobile value | Web token |
|---|---|---:|---|
| Main canvas | `colors.background` | `#FFFFFF` | `--background` |
| Primary surface | `colors.primarySurface` | `#E8F4EC` | primary at low opacity |
| Neutral surface | `colors.surface` | `#F3F7F4` | `--muted` |
| Border | `colors.border` | `#D5E2D9` | `--border` |
| Deep gym green | `colors.primary` | `#0E4D2B` | `--primary` |
| Positive green | `colors.positive` | `#4EA96B` | `--secondary` |
| Near-black text | `colors.text` | `#142019` | `--foreground` |
| Secondary text | `colors.muted` | `#526159` | `--muted-foreground` |
| Destructive/error | `colors.danger` | `#B42318` | `--destructive` |
| Warning | `colors.warning` | `#8A4B08` | warning-specific component styles |

Mobile radii, spacing and card shadows are centralized beside the colors in `mobile/src/lib/theme.ts`. Web tokens remain in `frontend/src/index.css` and are consumed through the existing Tailwind theme.

## Component rules

- Use a white canvas and reserve deep green for primary actions, links, focus, icons and brand identity.
- Use the pale green surfaces and barbell motif for training emphasis rather than dark or neon panels.
- Keep primary touch controls at least 48 logical pixels on mobile and 44 CSS pixels on web.
- Buttons compress slightly on press to provide immediate feedback; routine navigation has no delaying animation.
- Status badges always include readable text and an icon. Color is supporting information only.
- Loading states combine an activity indicator with a card skeleton. Empty and error states include an icon, explicit copy and a recovery action when one exists.
- Form validation appears beside the affected field. API errors remain a separate alert state.
- Mobile content is centered with a bounded width and responsive horizontal padding for phone, tablet and web layouts. The four existing member tabs retain their order and routes.

## Accessibility checks

The automated mobile theme test checks WCAG AA contrast for primary button labels, body copy, muted copy and destructive messages. Screen-reader labels, selected/disabled states and visible text continue to identify status independently of color.
