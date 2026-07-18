# Membership Lifecycle Policy

## Effective states

```text
Pending Verification -> Active -> Expiring Soon -> Expired
Active/Expiring Soon -> approved future freeze -> Frozen -> Active/Expiring Soon
Active/Expiring Soon/Frozen -> Cancellation Requested -> Cancelled
Any non-revoked membership -> Revoked
Expired -> Active through renewal
```

Effective status is derived centrally from terminal state, email verification, current freeze window, expiry date, and the seven-day expiring-soon threshold. QR attendance uses the same eligibility service rather than duplicating rules.

## Freeze

- Only an eligible active or expiring-soon member may request a freeze.
- Start date cannot be in the past; end cannot precede start; a request may cover at most 90 calendar days.
- One pending freeze request per membership is enforced in PostgreSQL.
- Manager/admin approval records reviewer, time, and mandatory reason. A future approved period does not freeze access early.

## Cancellation and revocation

- Active, expiring-soon, or frozen membership can request cancellation; stale stored state is re-derived before acceptance.
- One pending cancellation request per membership is enforced in PostgreSQL.
- Approval requires one recorded financial outcome: `refund`, `account_credit`, or `forfeit`. This release records the outcome but does not execute a real gateway refund/credit.
- Rejection cannot include a financial outcome.
- Admin revocation requires a reason and immediately becomes a terminal access state.

## Access consequences

- Pending-verification, frozen, expired, cancelled, and revoked states cannot generate QR access or pass scanner eligibility.
- Cancelled and revoked states remain terminal during scheduled status synchronization.
- The worker periodically synchronizes expiring-soon, expired, active-after-freeze, and pending-verification states.
- Every request, decision, and revocation writes a traceable audit entry.
