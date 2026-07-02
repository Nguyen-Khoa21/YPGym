# Membership Lifecycle Policy

## States

```text
Pending Verification -> Active -> Expiring Soon -> Expired
Active -> Frozen -> Active
Active -> Cancellation Requested -> Cancelled
Active -> Revoked
```

## Rules

- New accounts start as pending verification until email verification succeeds.
- Membership purchase activates or extends membership only after a payment record is created.
- Renewals extend from the current expiry date when the membership is active; otherwise they start from today.
- Frozen, expired, cancelled and revoked members cannot generate QR tokens or book classes.
- Cancellation requests require approval and an outcome: refund, account credit or forfeit.
- Revocation requires an admin reason and audit log entry.
- Scheduled workers may mark memberships as expiring soon or expired.

