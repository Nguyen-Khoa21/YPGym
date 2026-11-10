---
type: index
status: current
date: 2026-11-10
tags:
  - architecture
  - archify
related:
  - "[[System Architecture]]"
  - "[[Home]]"
  - "[[Packages 01-04 Summary]]"
  - "[[Decisions Log]]"
---

# Archify diagrams

Archify turns a `candidate.json` into a self-contained HTML workflow diagram. The files live in the repo under `.archify/`, outside this vault, so Obsidian cannot open the HTML. Open them in a browser from the paths below. This note is the index and the place to record why a diagram changed.

For the technical map of the stack, see [[YPGym Architecture.canvas]] and [[System Architecture]]. Archify covers the business flow, the canvas covers components. They do not overlap.

## Diagrams

### 1. Overall business flow (VNPay version, old)
- Created: 2026-11-02
- HTML: `.archify/workflow-ypgym-luong-nghiep-vu-20261102-173951/ypgym-luong-nghiep-vu.html`
- Source: `.archify/workflow-ypgym-luong-nghiep-vu-20261102-173951/candidate.json`
- Status: `superseded`. It still shows VNPay sandbox and IPN, which the project replaced with payOS.

### 2. Overall business flow with payOS and Cloudflare Tunnel (latest)
- Created: 2026-11-04 to 2026-11-05
- HTML: `.archify/workflow-ypgym-payos-cloudflare-20261104-230600/ypgym-luong-nghiep-vu-payos-cloudflare.html`
- Source: `.archify/workflow-ypgym-payos-cloudflare-20261104-230600/candidate.json`
- Built from repo revision `e5fe895` (2026-11-05, "replace VNPay with payOS").
- Status: `stale`. HEAD is 23 commits later (`9088536`, 2026-11-09). It was drawn before the multi-gym work and before Packages 11 to 16.

## What the latest diagram covers

Five lanes: member journey, QR and attendance and realtime, payment and benefits, classes and waitlist and YPTrain, operations and data and background jobs. Views include the main journey, payOS payment and attendance.

## Flow to note mapping

| Diagram area | Notes |
|---|---|
| Register, login, verify, authorization | [[Package 11 - Email verification code]], [[Package 12 - Onboarding recommendations]] |
| Dashboard | [[Package 05 - Member dashboard]], [[Package 14 - Dashboard UI tweaks]], [[Package 13 - Expired membership and location separation]] |
| QR, scanner, attendance | [[Package 09 - Scanner gym awareness]], [[Packages 01-04 Summary]] (Package 2) |
| payOS checkout, webhook, benefits, invoice | [[Packages 01-04 Summary]] (Package 4), [[Package 15 - Invoice viewer]], [[Package 16 - Staff workspace and in-person registration]] |
| Classes and waitlist | [[Packages 01-04 Summary]] (Package 4) |
| Manager, admin, staff, realtime | [[Package 06 - Management workspaces]], [[Package 16 - Staff workspace and in-person registration]] |

## Missing from the latest diagram

These came after revision `e5fe895`, so check them when you regenerate:
- Gym choice and gym scope on every flow (Packages 1 to 6, 10).
- Email verification code step (Package 11).
- Onboarding questionnaire after first login (Package 12).
- Expired membership panel, renew or change gym (Package 13).
- In-person registration with payOS QR or cash payment (Package 16).
- Invoice viewer (Package 15).

## Update log

- 2026-11-10: note created. Latest diagram is stale (see above). Add a line here each time a diagram is regenerated: date, repo revision, what changed.
