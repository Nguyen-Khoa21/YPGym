Part of the [post-multigym master prompt](../post-multigym-master-prompt.md). Read its sections 0 to 3 first (operating rules, evidence, defaults, cross-cutting rules).

# Package 13: Expired membership prompt and per-location account separation

**Goal.** An expired member is clearly asked to renew or change location. Each gym keeps its own manager, staff and PT accounts, and tests prove it.

### Requirements

| ID | Requirement |
|---|---|
| FR-EXP-001 | When the derived membership status is `expired` (not cancelled, revoked or frozen), the web dashboard, `/app/qr` and the mobile dashboard and QR tab show a prominent panel: "Your membership at {gym} expired on {date}." with two actions: **Renew at {gym}** and **Change location**. Reuse existing `membership` data from the dashboard payload; add no new endpoint unless a field is truly missing. |
| FR-EXP-002 | Renew goes to the plan list with the home gym preselected. Change location goes to the same flow with the gym picker open and no gym preselected, except the recommended gym from Package 12 is marked. `BuyMembershipPage` needs a small route or query parameter to accept this (it currently derives the gym from the dashboard). Mobile does the same through the `renew` screens. |
| FR-EXP-003 | The home gym still changes **only after verified payment** (existing Package 4 rule). The panel never changes it. Test this again with an expired member who picks a different gym. |
| FR-EXP-004 | While expired the QR stays blocked, class booking follows the existing `access_snapshot` rule, and the member can still see attendance history and invoices. No new restriction. |
| FR-LOC-001 | Account separation audit. Confirm and test: (a) manager, staff and PT have exactly one active `workforce_gym_assignments` row (partial unique index exists); (b) `POST /admin/staff-accounts` requires a gym (owner chooses, manager is forced to own); (c) moving an account between gyms is owner-only, audited, and closes the old assignment; (d) a District 1 manager or staff cannot read or act on District 11 attendance, members, classes, broadcasts or staff shifts; (e) the owner is the only cross-gym role. Add the missing tests to `test_shift_and_scope_rules.py` or a new file in `backend/app/tests/integration`. Fix any gap found; do not add new roles. |
| FR-LOC-002 | Every workforce page shows the gym the signed-in account belongs to, prominently (name in the page header, same style as Package 14's gym label). The admin staff list shows each account's gym. |

### Acceptance criteria

- **AC-EXP-001.** Given an expired member, then the panel appears with both actions; given an active, frozen or cancelled member, then it does not appear.
- **AC-EXP-002.** Given the member picks another gym and pays, then `home_gym_id` changes only after the verified webhook (payment pending leaves it unchanged).
- **AC-LOC-001.** The scope matrix test (role x gym x endpoint family) passes and covers `403` for cross-gym and `GYM_ASSIGNMENT_REQUIRED` for an unassigned workforce account.

### Tasks

T13-01 spec and decision D-15. T13-02 shared `ExpiredMembershipPanel` (web) and mobile equivalent. T13-03 `BuyMembershipPage` and mobile renew parameter. T13-04 scope matrix tests and fixes. T13-05 gym label on workforce pages. T13-06 docs (`docs/policies/roles.md`).

**Out of scope:** grace periods, auto-renewal, changing expiry rules.

