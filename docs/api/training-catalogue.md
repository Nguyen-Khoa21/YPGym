# YPTrain shared exercise catalogue

Feature 5 adds one PostgreSQL exercise catalogue for the member web and Expo clients. Both read `/api/v1/training/exercises`; there is no client-only catalogue or YPFood data source. Existing equipment seed, admin source, and upload handler were searched before this migration and none existed. Feature 6 workout records reference this catalogue; see `workout-logging.md`.

## Data and access

`training_exercises` stores name, description, `upper`/`lower` region, usage steps, safety note, illustrative and active flags, and timestamps. `training_exercise_muscles` stores controlled muscle names with a primary or secondary role; each muscle appears once per exercise and at least one primary is required by the API. `training_exercise_images` stores one sanitized image per exercise. This is kept separate from catalogue list rows so search never loads image bytes. No workout logs or attendance state are created by Feature 5.

Only members can list and read active exercise JSON. Managers and admins can list all records and create, edit, archive or restore them. Staff, PT and member roles cannot mutate. Archive keeps the record and tags for future workout-history references; no destructive delete route exists. Changes and image replacement add audit records in the same transaction as the catalogue change.

| Method | Route | Access | Behavior |
|---|---|---|---|
| GET | `/api/v1/training/exercises` | Member | Paginated active list; `region`, `muscle`, `search`, `page`, `page_size` |
| GET | `/api/v1/training/exercises/{id}` | Member | Active detail |
| GET | `/api/v1/training/exercises/{id}/image` | Public | JPEG image for an active record only; intended for browser/React Native image elements |
| GET | `/api/v1/admin/training/exercises` | Manager/admin | Paginated list including archived records; same filters |
| GET | `/api/v1/admin/training/exercises/{id}` | Manager/admin | Detail including archived record |
| POST | `/api/v1/admin/training/exercises` | Manager/admin | Validated create; defaults active |
| PATCH | `/api/v1/admin/training/exercises/{id}` | Manager/admin | Validated partial edit; `is_active=false` archives |
| PUT | `/api/v1/admin/training/exercises/{id}/image` | Manager/admin | Multipart `file`; replaces prior image |

`search` matches exercise name or any tagged muscle, case-insensitively, with SQL wildcard characters escaped. The controlled taxonomy is chest, back, shoulders, biceps, triceps, forearms, core, quadriceps, hamstrings, glutes and calves. A muscle may be primary or secondary, but never both on one record.

Image uploads are limited to 2 MB input and 4 megapixels, decoded as PNG/JPEG/WebP with Pillow, re-encoded as JPEG to remove uploaded metadata and other embedded content, and limited to 4 MB output. API image responses use `image/jpeg`, `nosniff`, and a short cache lifetime. Because image URLs are public for native image compatibility, do not upload sensitive or licensed material to the catalogue. The URL includes an update timestamp in both clients to refresh after replacement.

The default development seed adds four **illustrative** examples and never overwrites manager edits on rerun. Lat pulldown and leg press explicitly say that machine availability is unconfirmed. Admins should confirm actual on-site equipment before clearing the illustrative flag or publishing local photos.

Member cards use a branded barbell fallback until a manager uploads an image. Detail shows steps, primary/secondary muscles and safety text. Feature 6 enables Add Exercise only after a server-confirmed same-day scanner check-in and eligible membership.

## Local check

Forward-migrate and seed the existing development stack:

```powershell
docker compose exec -T backend-api alembic upgrade head
docker compose exec -T backend-api python -m app.db.seed
```

Sign in as manager/admin on the web and open `/admin/exercises`. Create an exercise, assign primary and secondary muscles, upload a small PNG/JPEG/WebP, then sign in as a member in the web or Expo app. Open YPTrain, search/filter and open the same detail. Archive the exercise as manager and verify it disappears from member results while staying in management and the audit log. For workout logging, see `workout-logging.md`.
