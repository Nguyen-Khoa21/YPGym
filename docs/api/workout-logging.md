# YPTrain attendance-linked workout logging

Feature 6 uses the existing member JWT, scanner-issued QR and PostgreSQL attendance session. Both member web and Expo call the same API. There is no member-supplied user ID, date, attendance proof or second check-in path.

| Method | Route | Access | Result |
|---|---|---|---|
| GET | `/api/v1/training/workouts/today` | Member | Gym-local `gym_date`, `gym_timezone`, `eligible`, reason, and the member's saved daily session or `null` |
| POST | `/api/v1/training/workouts/today/exercises` | Member | Add one catalogue exercise with 1–10 sets; return the confirmed updated daily session |

POST body:

```json
{
  "exercise_id": "exercise-uuid",
  "idempotency_key": "new-uuid-for-this-form-submission",
  "sets": [{ "reps": 12, "weight": "0", "unit": "kg" }]
}
```

The server derives the current day from the configured IANA `GYM_TIMEZONE` (default `Asia/Ho_Chi_Minh`). It requires a same-day `iot_scanner` attendance session with its recorded `check_in` event and an eligible membership. Scanner check-out or timeout does not remove that proof or saved workout. A QR token's later expiration does not invalidate a previously recorded check-in. Only today's workout can be written; historical reads and their metric are documented in `workout-history.md`. GET still returns saved data if membership is later revoked, but POST is denied.

The first accepted exercise creates one `workout_sessions` row per member/day linked to its qualifying attendance session. Each `workout_exercises` row references the catalogue and snapshots its name and primary/secondary muscles. Ordered `workout_sets` store positive integer reps, non-negative two-decimal external load, and an explicit `kg` or `lb` unit. The default is kg. No conversion or mixed-unit aggregation is performed. `0 kg` means no added external load or a bodyweight movement, not zero effort. Each form submission has a UUID idempotency key; repeating the same key and payload returns the existing saved record, while reusing the key for different details returns 409. Member-row locking and database uniqueness protect concurrent submissions.

Both clients show today's server-confirmed session and the check-in reason before enabling Add Exercise. Set-count controls retain unsaved values in hidden rows as the count changes. The save button is disabled during the request, and a success message appears only after the server responds. Neither client supports editing or deleting saved sets in this feature.

## Manual check

1. Forward-migrate the development backend with `docker compose exec -T backend-api alembic upgrade head`, then open web `/app/train` or Expo's YPTrain tab as a member. Without today's scanner check-in, Add Exercise is unavailable and a direct POST returns 403 `WORKOUT_CHECK_IN_REQUIRED`.
2. Generate the member QR and scan it through the documented device-authenticated scanner API or simulator. Refresh YPTrain and open an active exercise.
3. Enter 1–10 sets with positive reps and a load/unit, save, and confirm the exact exercise/sets appear in today's session on both clients. Retry the same submission key to verify no duplicate.
4. Check out, refresh, and confirm the workout remains. Archive or rename the catalogue exercise as manager; its prior workout name remains intact.

Normal development data should only be used for disposable manual checks. The isolated Compose suite tests these paths against separate PostgreSQL and Redis instances.
