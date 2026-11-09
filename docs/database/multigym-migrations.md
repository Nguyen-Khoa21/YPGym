# Multi-gym migration note

Two Alembic revisions add the multi-gym model. Both ran upgrade, downgrade and `alembic check` cleanly on the test database (see the [verification record](../release/multigym-verification.md)). Back up before running on real data.

## `20261107_0020` (revises `20261103_0019`): multi-gym foundation

Upgrade:

- Creates `gym_locations` (name, unique slug, district, address, timezone, capacity greater than 0, active flag) and seeds YPGym District 1 and YPGym District 11. Capacity comes from the old `gym_capacity` configuration value, or 150.
- Creates `workforce_gym_assignments` with a unique index that allows one active assignment per user, and backfills existing manager, staff and PT users to District 1 (the check constraint allows only those three roles).
- Adds `gym_id` to `iot_devices`, `attendance_sessions`, `attendance_events`, `classes`, `staff_shifts` and `user_memberships.home_gym_id`, each backfilled to District 1 and then made `NOT NULL` with a foreign key and an index.
- Adds nullable `broadcast_announcements.gym_id`. `NULL` means chain-wide for new broadcasts. Existing broadcasts are all set to District 1, so old announcements become District 1 only.

Downgrade drops those indexes, foreign keys and columns, then `workforce_gym_assignments` and `gym_locations`. Any District 11 data (devices, sessions, classes, memberships, assignments) is lost for the gym columns, and every record ends up with no gym again.

## `20261109_0021` (revises `20261107_0020`): payments scoped to gyms

Upgrade adds `payments.gym_id`, backfilled from the linked membership's home gym, then the linked class's gym, then District 1. It then becomes `NOT NULL` with a foreign key and an index on `(gym_id, created_at)`. Payment history is kept.

Downgrade drops that index, foreign key and column.

## Check

```text
alembic downgrade 20261103_0019
alembic upgrade head
alembic check        # No new upgrade operations detected.
```
