---
type: spec-package
package: 7
status: implemented-verified
date: 2026-11-10
tags:
  - spec
  - package
related:
  - "[[Package 06 - Management workspaces]]"
  - "[[Package 08 - Documentation]]"
  - "[[Decisions Log]]"
---

# Package 7: Form reliability

> [!info] Status
> `implemented-verified`

## Goal
Operators can type into every management form. The broadcast Message box looked unstyled, so the fix goes into the shared form module once.

Business goals: G4.

## Key requirements
- Add a shared `Textarea` to `components/ui/Form.tsx` that matches `Input`.
- Tie labels to controls (`htmlFor`, `id`) and wire `aria-invalid` and `aria-describedby` to `FieldError`.
- Replace the 14 raw `<textarea>` elements in 8 files; record the raw controls that stay custom on purpose.

## Evidence
Shared controls, the broadcast form and the member request forms are verified. Remaining raw controls are recorded as intentionally custom in the spec.

## Known gaps
- Browser-level typing and layout checks depend on the Playwright setup from D-02.

## Decisions
- D-02 in [[Decisions Log]]

## Links
- Repo spec: `specs/package-07-form-reliability/spec.md`
- Main code: `components/ui/Form.tsx`, `AdminBroadcastsPage.tsx`, `index.css` (`.ops-modal__panel`)
- Previous: [[Package 06 - Management workspaces]]
- Next: [[Package 08 - Documentation]]
