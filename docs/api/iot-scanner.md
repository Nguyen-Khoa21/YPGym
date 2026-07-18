# IoT Scanner API Contract

The scanner boundary is hardware-agnostic. ESP32, Raspberry Pi, tablet, and the local simulator all call HTTP; they never connect to PostgreSQL or Redis directly.

## Authentication

Seeded development device:

```text
device_id: local-simulator-1
X-Device-Api-Key: local-iot-key
```

Production deployments must provision a unique key per device over a separate trusted process. The API stores only a SHA-256 key hash. Device credentials are not member JWTs and must not be embedded in the member QR code.

## Check-in and check-out

```http
POST /api/v1/attendance/check-in
POST /api/v1/attendance/check-out
Content-Type: application/json
X-Device-Api-Key: <device key>

{
  "device_id": "local-simulator-1",
  "qr_token": "<short-lived member QR JWT>"
}
```

Success response:

```json
{
  "code": "CHECK_IN_SUCCESS",
  "message": "Check-in recorded.",
  "session_id": "<uuid>",
  "member_id": "<uuid>",
  "occurred_at": "2026-07-18T08:00:00Z",
  "occupancy": {
    "active_count": 1,
    "capacity": 150,
    "percentage": 0.7,
    "status": "Low",
    "calculated_at": "2026-07-18T08:00:00Z"
  }
}
```

Checkout uses `CHECK_OUT_SUCCESS` and closes the member's active session. Clients should branch on `code`, not English `message` text.

## Stable failure responses

Errors use the shared envelope:

```json
{"error":{"code":"DUPLICATE_SCAN","message":"This QR token was scanned too recently.","details":null}}
```

| HTTP | Code | Scanner behavior |
|---:|---|---|
| 401 | `INVALID_DEVICE` | Reject the scan and show device provisioning/support state. |
| 400 | `INVALID_TOKEN` | Ask the member to reopen/refresh My QR. |
| 400 | `EXPIRED_TOKEN` | Ask the member to wait for/trigger QR refresh. |
| 409 | `SUPERSEDED_TOKEN` | A newer token exists; scan the current QR. |
| 403 | `INACTIVE_MEMBERSHIP` | Deny entry and show the returned membership guidance. |
| 409 | `DUPLICATE_SCAN` | Do not retry immediately; honor the configured duplicate window. |
| 409 | `ACTIVE_SESSION_EXISTS` | Treat member as already checked in. |
| 409 | `NO_ACTIVE_SESSION` | Checkout cannot proceed; offer staff assistance. |
| 503 | `QR_STATE_UNAVAILABLE` | Retry later; token state cannot be safely verified. |
| 503 | `SCAN_STATE_UNAVAILABLE` | Retry later; duplicate protection is unavailable. |

Validation failures return `422 VALIDATION_ERROR`; unexpected failures return `500 INTERNAL_SERVER_ERROR` without secrets.

## Token and concurrency behavior

1. The member requests `GET /api/v1/attendance/qr-token/me` with their bearer token.
2. The API validates central membership eligibility, signs a short-lived JWT, and atomically makes its JTI current in Redis.
3. The scanner authenticates the device before parsing the QR.
4. Check-in revalidates JTI and membership, claims a Redis duplicate guard, locks the active-session query, and relies on PostgreSQL's partial unique index as the final race guard.
5. Successful session changes commit before the occupancy projection is reconciled.

## Simulator

From `iot-simulator/`:

```powershell
python -m app.main --scenario valid --token "<QR_TOKEN>"
python -m app.main --scenario duplicate --token "<QR_TOKEN>"
python -m app.main --scenario invalid-token
python -m app.main --scenario unauthorized-device --token "<QR_TOKEN>"
```

Expired and inactive scenarios use deliberately captured development tokens in `EXPIRED_QR_TOKEN` and `INACTIVE_QR_TOKEN`; the simulator does not forge signed tokens.

Optional Compose execution:

```powershell
$env:QR_TOKEN="<QR_TOKEN>"
docker compose --profile iot run --rm iot-simulator python -m app.main --scenario valid --token $env:QR_TOKEN
```
