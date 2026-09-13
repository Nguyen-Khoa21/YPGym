# PostgreSQL ERD through Day 42

```mermaid
erDiagram
  users ||--o{ email_verifications : has
  users ||--o{ password_resets : has
  users ||--o{ user_memberships : owns
  users ||--o{ membership_freeze_requests : submits
  users ||--o{ membership_cancellation_requests : submits
  users ||--o{ payments : makes
  users ||--o{ invoices : receives
  users ||--o{ notifications : receives
  users ||--|| notification_preferences : configures
  users ||--o{ audit_logs : acts_or_targeted
  users ||--o{ attendance_sessions : attends
  users ||--o{ attendance_events : generates
  users ||--o| personal_trainers : represents
  users ||--o{ class_bookings : books
  users ||--o{ class_waitlists : queues

  membership_plans ||--o{ user_memberships : configures
  membership_plans ||--o{ payments : purchased_as
  user_memberships ||--o{ payments : paid_by
  user_memberships ||--o{ membership_freeze_requests : receives
  user_memberships ||--o{ membership_cancellation_requests : receives
  payments ||--|| invoices : generates

  iot_devices ||--o{ attendance_sessions : records
  attendance_sessions ||--o{ attendance_events : contains

  personal_trainers ||--o{ classes : leads
  classes ||--o{ class_bookings : contains
  classes ||--o{ class_waitlists : contains

  users ||--o{ broadcast_announcements : creates
```

## Migration chain

```text
20260702_0003
  -> 20260716_0004 membership operations, notification, broadcast, audit
  -> 20260716_0005 attendance, devices, trainers, classes, bookings, waitlists
  -> 20260722_0006 trainer bio and availability summary
  -> 20260723_0007 VND billing localization
```

The database and SQLAlchemy metadata are aligned at `20260723_0007`; `alembic check` reports no pending operations.

## Editable Draw.io diagrams

- [`ypgym-domain-relationships.drawio`](../diagrams/ypgym-domain-relationships.drawio) gives a proposal-ready domain relationship overview.
- [`ypgym-erd.drawio`](../diagrams/ypgym-erd.drawio) contains the detailed implemented PostgreSQL ERD with key attributes, foreign keys and cardinalities.

The diagrams intentionally exclude proposal or later-plan concepts that are not persisted through Day 42: chatbot logs, fitness forms, mobile-only entities and permanent QR-token rows.

## Integrity and query notes

- UUID primary keys are used for business tables.
- One pending freeze and one pending cancellation request per membership are enforced by partial unique indexes.
- One active attendance session per member is enforced by a partial unique index; event/user/time/device lookup paths are indexed.
- QR JWTs are not stored as permanent rows; current JTI state lives in Redis with TTL.
- Payments enforce `(user_id, idempotency_key)` uniqueness; invoices are one-to-one with payments.
- Class capacity and time order use check constraints. Booking and waitlist uniqueness prevent duplicate enrollment, and trainer/location overlap is enforced in the class service under a locked update flow.
- Capacity-changing booking, waitlist, cancellation, and promotion operations serialize on the class row. Waitlist order uses stored position, creation timestamp, and UUID; promotion and notification records commit with the freed slot.
- Trainer bio and availability are nullable profile fields; assigned/upcoming classes remain derived from `classes` rather than duplicated on the trainer row.
- Audit indexes cover timestamp, action, actor, target, and entity lookup.
