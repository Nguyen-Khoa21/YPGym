# Registration email delivery

Registration commits a member, a hashed one-time verification token, and one `registration_welcome` email intent in the same PostgreSQL transaction. Duplicate registration cannot create another intent. Celery beat runs `app.workers.send_welcome_emails` each minute; the worker claims pending rows with PostgreSQL `SKIP LOCKED`, then writes the message to the ignored Maildir development outbox or sends it through SMTP. The welcome message contains no verification token. Its HTML escapes the member name and login URL. The existing separate verification message retains both web and `ypgym://` links, and password-reset links still use hashed, one-time database tokens.

## Local development

The default `EMAIL_DELIVERY_MODE=development` writes welcome and authentication messages under `backend/storage/mail/new/`. The folder contains private links. Do not commit, attach, log, or include it in release packages. After starting the normal Compose stack and applying Alembic migration `20260922_0009`, register a new synthetic member through web or mobile. The verification message appears after registration; the welcome message appears after the next worker run, normally within a minute. The worker can also be exercised against existing pending rows with:

```powershell
docker compose exec -T celery-worker python -c "from app.workers.celery_app import send_welcome_emails; print(send_welcome_emails())"
```

The command prints the number of welcome messages marked delivered. Do not print or paste outbox contents into logs or chat.

## SMTP configuration

Real SMTP delivery has **not** been verified. To test it, the owner must choose the intended YPGym sender address and privately configure these values in the repository-root `.env` used by Docker Compose, or as shell environment variables: `EMAIL_DELIVERY_MODE=smtp`, `EMAIL_SENDER_NAME`, `EMAIL_SENDER_ADDRESS`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_TLS_MODE` (`starttls`, `ssl`, or `none`), and, when required, both `SMTP_USERNAME` and `SMTP_PASSWORD` (an app password/provider token). `FRONTEND_URL` must point to the reachable login/verification site; configure `MOBILE_APP_URL` if the app link differs from `ypgym://`. `backend/.env.example` contains placeholders for backend-only runs, but Compose supplies its own environment defaults. Compose passes the configured values to the API and worker; restart those services after changing them. Never commit credentials or share secret values in a message or screenshot. Authenticated SMTP requires TLS; `none` is only for a trusted unauthenticated test server.

Authentication links are sent directly after their hashed token records are committed. If the mail transport is unavailable, registration still succeeds and the failure log contains only a user ID and exception type. There is currently no member-facing resend endpoint for a failed verification message, so operators must resolve delivery before registering production users. The welcome intent remains pending for retry. Defaults are five attempts, at least five minutes apart, with a batch of up to 25 per minute. Attempts and final state are stored in PostgreSQL; exhausted intents become `skipped` and require operator review. A stable `Message-ID` supports downstream deduplication, but SMTP acknowledgement and the database commit cannot be atomic: a worker crash after SMTP acceptance can deliver a duplicate welcome message. The guarantee is one queue intent per new member, not exactly-once external delivery.
