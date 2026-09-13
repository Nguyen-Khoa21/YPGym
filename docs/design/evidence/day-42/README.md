# Day 42 rendered acceptance evidence

Captured in the local Codex in-app browser against the running Compose web/API and development PostgreSQL on 2026-09-07 and 2026-09-13. Reference viewports: desktop 1440×1000 (the earlier dashboard capture was 1280px wide), tablet 768×1024, phone 390×844. These are real application screens, not mock API responses. The disposable QA records are named in the root handoff.

| Route | Desktop | Tablet | Phone | Additional states |
|---|---|---|---|---|
| `/app/dashboard` | `dashboard-desktop.png` | `dashboard-tablet.png` | `dashboard-phone.png` | `dashboard-no-membership.png`, `dashboard-loading.png`, `dashboard-api-error.png` |
| `/app/classes` | `classes-desktop.png` | `classes-tablet.png` | `classes-phone.png` | `classes-empty.png`, `classes-loading.png`, `classes-api-error.png`, `booking-confirm-phone.png` |
| `/app/bookings` | `bookings-desktop.png` | `bookings-tablet.png` | `bookings-phone.png` | `bookings-empty.png`, `bookings-api-error.png` |
| `/admin/pt-assignments` | `trainers-desktop.png` | `trainers-tablet.png` | `trainers-phone.png` | `trainers-loading.png`, `trainers-api-error.png`, `trainer-form-phone.png`, `trainer-deactivation-conflict-phone.png`, `manager-mobile-navigation.png` |

The browser walkthrough exercised member booking and cancellation, search-empty state, trainer create/edit/validation/deactivation and the assigned-trainer conflict, logout/account switching, and member denial from the manager route. API pause/stop was used to capture loading and recoverable network failures, then restored. The final phone trainer/menu screenshots on September 13 show the role-filtered manager menu; measured document widths were 1425≤1440, 753≤768, and 375≤390. `member-role-denied-phone.png` and `phone-navigation.png` record the other authorization/navigation checks. `dashboard-phone-before.png` documents the tablet-card overlap that was corrected before the final captures.

The files document functional responsive acceptance, not pixel-perfect parity with the BRD images. The design parity pass remains a later milestone.
