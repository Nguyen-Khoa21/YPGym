---
type: spec-package
package: 8
status: partially-implemented
date: 2026-11-10
tags:
  - spec
  - package
related:
  - "[[Package 07 - Form reliability]]"
  - "[[Package 09 - Scanner gym awareness]]"
  - "[[Decisions Log]]"
---

# Package 8: Documentation

> [!info] Status
> `partially-implemented`

## Goal
Make the multi-gym system explainable and demonstrable, with honest evidence of what was verified. Documentation only, no application code.

Business goals: G1 to G6.

## Key requirements
- Describe gym-scoped roles in `docs/policies/roles.md` (closes G-07).
- Update `route-screen-map.md`, `system-architecture.md` and the diagrams README.
- Keep the demo script and demo seed accounts (`owner@`, `managerdist1@`, `managerdist11@`, `staffdist1@`, `staffdist11@`, `memberdist1@`, `memberdist11@` at `ypgym.dev`) accurate.
- Gym-aware API docs under `docs/api/` and the traceability matrix.

## Evidence
Documents were written and checked against code and a seeded run.

## Known gaps
- `route-screen-map.md`, `system-architecture.md` and `docs/diagrams/README.md` held the owner's uncommitted edits. Package 8 edits them only after the owner commits or approves a merge.

## Decisions
- None specific to this package.

## Links
- Repo spec: `specs/package-08-documentation/spec.md`
- Main code: `docs/policies/roles.md`, `docs/design/route-screen-map.md`, `docs/architecture/system-architecture.md`
- Previous: [[Package 07 - Form reliability]]
- Next: [[Package 09 - Scanner gym awareness]]
