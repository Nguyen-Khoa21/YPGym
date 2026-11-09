Part of the [post-multigym master prompt](../post-multigym-master-prompt.md). Read its sections 0 to 3 first (operating rules, evidence, defaults, cross-cutting rules).

# Package 11: Email verification code

**Goal.** The email mails a short code the user can type on a phone, with the link as an optional extra that is never a localhost link.

### Requirements

| ID | Requirement |
|---|---|
| FR-VER-001 | On registration and on resend, generate a 6-digit numeric code with `secrets` (zero-padded, uniform). Store only an HMAC-SHA256 of the code keyed with a server secret and bound to the user id (a plain hash of a 6-digit value is trivially reversible). Compare with `hmac.compare_digest`. |
| FR-VER-002 | The code and the existing link token live on the **same** `email_verifications` row, so using either one consumes both. Add nullable `code_hash` and `failed_attempts int not null default 0`. Do not add a second table. Keep `token_hash` unique and the `new_email` email-change path working. |
| FR-VER-003 | The verification email is multipart (plain text and HTML, HTML-escaped). The code is the first and largest thing in it, with the expiry time in minutes. A web link is included **only** when `FRONTEND_URL` is not a loopback host (`localhost`, `127.0.0.1`, `::1`). Remove the `ypgym://` link. Reuse `EmailDeliveryService._base_message` and the HTML escaping style instead of hand-building another message. |
| FR-VER-004 | New `POST /auth/verify-email/code` with `{email, code}`. On success it returns the same `VerifyEmailResponse` as the link path. Wrong code: `400 INVALID_VERIFICATION_CODE`. Expired: `400 VERIFICATION_TOKEN_EXPIRED`. Locked after the fifth wrong attempt: `429 VERIFICATION_CODE_LOCKED` (resend required). Use the existing structured error shape. |
| FR-VER-005 | New `POST /auth/verify-email/resend` with `{email}`. It always answers the same generic `200` whether or not the account exists or is already verified (no account enumeration). When it does apply, it invalidates earlier unused codes for that user, creates a new one and sends it. Enforce the 60-second cooldown from the newest row's `created_at`, plus Redis rate limits per hashed IP and per hashed IP+email (add them next to the existing `verify` limits and document them in `docs/policies/security.md`). |
| FR-VER-006 | Keep `GET /auth/verify-email?token=` unchanged for old links. |
| FR-VER-007 | Web `/verify-email`: when `?token=` is present, keep the current behavior. Otherwise show an email field (prefilled from `?email=`), a 6-digit input (`inputMode="numeric"`, `autoComplete="one-time-code"`, paste-friendly), a Verify button, and a Resend button with a visible countdown. The registration success card links to `/verify-email?email=...`. A login rejected with `EMAIL_NOT_VERIFIED` offers a link to the same page. Reuse the shared `Field`, `Input`, `Button`, `FeedbackState` components. |
| FR-VER-008 | Mobile `verify-email.tsx`: replace the token box with a 6-digit code input (`keyboardType="number-pad"`, `textContentType="oneTimeCode"`), show the email, add Resend with countdown, keep accepting a deep-linked `token` param. Show clear messages for wrong, expired, locked and rate-limited. |
| FR-VER-009 | The welcome email must no longer say "separate verification message" if both emails now arrive together. Reword to match. |
| FR-VER-010 | Register response includes `verification_email_sent: boolean`. If the send failed, the UI says so and offers Resend immediately instead of showing a success message that is not true. |
| FR-VER-011 | Document in `RUN_GUIDE.md` / `docs/api/identity-and-membership-email.md`: to test on a phone, set `EMAIL_DELIVERY_MODE=smtp` with real SMTP settings and set `FRONTEND_URL` to an address the phone can reach. State plainly that the development Maildir is not email. |

### Acceptance criteria

- **AC-VER-001.** Given a new registration with SMTP or a fake transport, when the email is sent, then its text and HTML both contain a 6-digit code and no `localhost` or `ypgym://` URL.
- **AC-VER-002.** Given a correct code before expiry, when posted, then `is_email_verified` becomes true, the row is `used_at`-stamped, and the link token for that row no longer works (already-used message).
- **AC-VER-003.** Given five wrong codes, when a sixth (even correct) code is posted, then it is rejected with `VERIFICATION_CODE_LOCKED` until a resend creates a new code.
- **AC-VER-004.** Given resend within 60 seconds, then the request is rejected with a retry-after; given resend for an unknown email, then the response is identical to a real one.
- **AC-VER-005.** Given an expired code, then `VERIFICATION_TOKEN_EXPIRED`; the database holds no plaintext code anywhere (check the row, logs and test fixtures).
- **AC-VER-006.** Given an existing email-change verification (`new_email`), when its link is used, then it still works.
- **AC-VER-007.** A phone user can register, read the code in the mail app, type it on the mobile verify screen, and sign in.

### Tasks

T11-01 spec and decisions D-12. T11-02 migration `0022` (`code_hash`, `failed_attempts`). T11-03 repository and service changes. T11-04 endpoints, schemas, rate limits. T11-05 email message. T11-06 web page and login link. T11-07 mobile screen. T11-08 tests (backend integration, frontend `node --test`, mobile tests). T11-09 docs.

**Out of scope:** changing email-change flow, SMS, OAuth linking emails.

