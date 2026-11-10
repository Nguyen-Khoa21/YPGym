---
type: spec-package
package: 11
status: committed
date: 2026-11-10
commit: "69906cb"
tags:
  - spec
  - package
related:
  - "[[Package 10 - Member mobile gyms]]"
  - "[[Package 12 - Onboarding recommendations]]"
  - "[[Decisions Log]]"
---

# Package 11: Email verification code

> [!info] Status
> `committed` · commit `69906cb`

## Goal
The verification email carries a short code the user can type on a phone. The link is optional and never points to localhost.

## Key requirements
- 6-digit code from `secrets`, stored as HMAC-SHA256 bound to the user id, compared with `hmac.compare_digest`.
- Code and link token share one `email_verifications` row; add `code_hash` and `failed_attempts`.
- `POST /auth/verify-email/code`: wrong code `400`, expired `400`, locked after 5 wrong attempts `429 VERIFICATION_CODE_LOCKED`.
- `POST /auth/verify-email/resend`: always the same generic `200`, 60 second cooldown, Redis rate limits.
- Web `/verify-email` and mobile `verify-email.tsx` get a 6-digit input and a Resend button with a countdown.

## Evidence
Commit exists in git log. The spec has no recorded status line, so verification is not confirmed here.

## Known gaps
- None recorded in the spec.

## Decisions
- D-12 in [[Decisions Log]]

## Links
- Repo spec: `specs/package-11-email-verification-code/spec.md`
- Main code: `email_verifications`, `EmailDeliveryService`, web `/verify-email`, mobile `verify-email.tsx`
- Previous: [[Package 10 - Member mobile gyms]]
- Next: [[Package 12 - Onboarding recommendations]]
