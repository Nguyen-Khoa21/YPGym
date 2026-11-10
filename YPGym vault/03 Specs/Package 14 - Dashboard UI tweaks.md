---
type: spec-package
package: 14
status: committed
date: 2026-11-10
commit: "561cd53"
tags:
  - spec
  - package
related:
  - "[[Package 13 - Expired membership and location separation]]"
  - "[[Package 15 - Invoice viewer]]"
  - "[[Decisions Log]]"
---

# Package 14: Dashboard UI tweaks

> [!info] Status
> `committed` · commit `561cd53`

## Goal
Rearrange the web and mobile dashboards from the owner's annotated screenshots, staying inside the existing white-and-green system.

## Key requirements
- Web: prominent gym label near the greeting, compact `OccupancyCard`, and a two-tab card (Important, Membership).
- Web: heading becomes "YPGym {current gym}'s Occupancy".
- Mobile: live capacity hero card first, equal-size Show QR and Membership tiles, upcoming classes visible without scrolling, red unread badge on the bell.

## Evidence
Commit exists in git log.

## Known gaps
- None recorded in the spec.

## Decisions
- D-18 in [[Decisions Log]]

## Links
- Repo spec: `specs/package-14-dashboard-ui-tweaks/spec.md`
- Main code: `OccupancyCard`, `docs/design/route-screen-map.md`
- Previous: [[Package 13 - Expired membership and location separation]]
- Next: [[Package 15 - Invoice viewer]]
