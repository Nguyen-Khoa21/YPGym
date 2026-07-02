# PostgreSQL ERD

Day 11-20 implemented the core authentication, membership, payment, and invoice tables. Later operational modules remain documented as future relationships only.

```mermaid
erDiagram
  users ||--o{ email_verifications : has
  users ||--o{ password_resets : has
  users ||--o{ user_memberships : owns
  membership_plans ||--o{ user_memberships : configures
  users ||--o{ payments : makes
  payments ||--|| invoices : generates
  users ||--o{ invoices : receives
  user_memberships ||--o{ payments : paid_by
  membership_plans ||--o{ payments : purchased_as
  system_configurations ||--|| system_configurations : stores
```

## Implemented Tables

- `users`
- `email_verifications`
- `password_resets`
- `membership_plans`
- `user_memberships`
- `system_configurations`
- `payments`
- `invoices`

## Constraints and Index Notes

- Business tables use UUID primary keys.
- `users.email` and `users.phone` are unique and indexed.
- Membership status and expiry date are indexed for lifecycle checks.
- Token tables store hashed tokens only and index token hashes.
- `payments` enforces idempotency with a unique `(user_id, idempotency_key)` constraint.
- `invoices` are immutable billing metadata linked one-to-one with payments.
