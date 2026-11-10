---
type: spec-package
package: 15
status: committed
date: 2026-11-10
commit: "079740c"
tags:
  - spec
  - package
related:
  - "[[Package 14 - Dashboard UI tweaks]]"
  - "[[Package 16 - Staff workspace and in-person registration]]"
  - "[[Decisions Log]]"
---

# Package 15: Invoice viewer

> [!info] Status
> `committed` · commit `079740c`

## Goal
Invoice PDFs download reliably and open in an in-page viewer, like previewing an attachment in Gmail.

## Key requirements
- Diagnose first: reproduce with a member token for a membership invoice and a class-booking invoice, and write the confirmed root cause in the commit report.
- Regression test for each product type: `200`, `application/pdf`, body starts with `%PDF`; another member's invoice is `404`.
- Structured `503 INVOICE_PDF_UNAVAILABLE` instead of an unhandled `500`; write to a temporary name then rename.
- CSP allows `frame-src 'self' blob:` so the viewer works in the production build.

## Evidence
Commit exists in git log.

## Known gaps
- None recorded in the spec.

## Decisions
- None specific to this package.

## Links
- Repo spec: `specs/package-15-invoice-viewer/spec.md`
- Main code: `invoice_service.py`, `frontend/nginx.production` CSP
- Previous: [[Package 14 - Dashboard UI tweaks]]
- Next: [[Package 16 - Staff workspace and in-person registration]]
