# YPTrain workout history and weekly muscle map

Feature 7 reads the authenticated member's own scanner attendance and authoritative workout sets. Clients never send a member ID or aggregate score. Catalogue edits do not rewrite history because exercise names and muscle roles come from the snapshots recorded when the workout was logged.

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/v1/training/workouts/history?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&page=1&page_size=31` | Paginated activity dates for a bounded range of up to 366 days. Attended-only and workout days remain distinct. |
| GET | `/api/v1/training/workouts/{workout_date}` | Exact exercises, sets, reps, external load and units for one activity date. |
| GET | `/api/v1/training/exercises/{exercise_id}/history` | Paginated prior logs for the exercise with descriptive changes from each older baseline. |
| GET | `/api/v1/training/workouts/muscle-map?week_of=YYYY-MM-DD` | Monday–Sunday day and muscle exposure for the week containing `week_of`; omission selects the current gym-local week. |

All routes require the member role and derive identity from the validated access token. A date with neither attendance nor a workout returns 404. History ranges with the end before the start or more than 366 inclusive days return 422.

## Weighted set exposure

The shared metric is **weighted set exposure**:

- Every completed set contributes `1.0` exposure to each snapshotted primary muscle.
- The same set contributes `0.5` exposure to each snapshotted secondary muscle.
- A bodyweight or zero-external-load set counts normally. Reps and kg/lb loads remain visible as exact set details but do not change this cross-exercise exposure score.
- Day exposure is the sum of its muscle exposures. Weekly muscle exposure is the sum for that muscle from Monday through Sunday in the configured gym timezone.

Intensity uses the same five-level normalization in history and the muscle map: zero is level 0; positive values up to 25%, 50%, and 75% of the highest score in the displayed scope are levels 1, 2, and 3; values above 75% are level 4. Calendar days are normalized against the highest day in the requested range. Weekly muscles are normalized against the highest muscle in that week. Raw exposure scores and text labels remain present, so color is never the only meaning.

This metric describes logged set distribution. It is not kilograms of volume, measured anatomical activation, a diagnosis, or a workout prescription. Feature 8 must reuse the same Monday–Sunday boundary and raw metric if an approved guarded review is later connected.

Exercise comparisons convert only the maximum external load summary to kilograms (`lb × 0.45359237`, rounded to two decimals) so mixed-unit sessions can be described consistently. The API reports whether sets, total reps, and maximum external load were `more`, `same`, or `less` than the next older logged occurrence. It does not recommend a target.

## Manual check

1. Log workouts on two scanner-attended dates and leave one attended date without a workout.
2. Open web `/app/train` and the Expo YPTrain tab. Confirm both calendars distinguish the attended-only day and show the same exact day details.
3. Open the same exercise. Confirm prior sessions preserve the logged name and sets and show descriptive changes only.
4. Confirm the current-week front/back maps, raw muscle list, week dates, intensity labels and exposure scores match on both clients.
5. Rename or archive the catalogue exercise as a manager. Confirm existing history still uses the original snapshot.

The isolated PostgreSQL suite covers empty weeks, a Monday–Sunday year transition, account isolation, bodyweight records, primary/secondary attribution, catalogue edits, comparison baselines, pagination and day/map parity.
